"""
structure-inbox.py — parse messy inbox entries into structured project records.

Each line in raw/inbox.jsonl can be:
  - A URL (the page is fetched for title/abstract)
  - Plain text: "NeRF for CAD from MIT 2024", a copy-pasted abstract, notes
  - Partial JSON with some fields filled in
  - A fully-structured record (passed through unchanged)

Uses GPT-4o to fill in all required fields and as many optional fields as
possible, then overwrites raw/inbox.jsonl with properly structured JSONL.

Usage:
    python scripts/structure-inbox.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT / "raw" / "inbox.jsonl"

REQUIRED = {"id", "name", "category", "type", "description"}

VALID_CATEGORIES = [
    "text-to-cad", "sketch-to-cad", "image-to-cad", "prompt-cad",
    "b-rep-learning", "program-cad", "cad-copilot", "cad-agent",
    "topology-optimization", "generative-3d-shape", "text-to-3d", "image-to-3d",
    "neural-operator", "physics-surrogate", "physics-informed-nn",
    "foundation-model-physics", "differentiable-physics", "scientific-ml",
    "dfm-ai", "dfam-ai", "process-monitoring-ml", "ml-quoting",
    "mesh-generation", "generative-materials", "inverse-design-materials",
    "ml-interatomic-potential", "architected-materials",
    "generative-platform", "implicit-modeling", "multi-disciplinary-optimization",
    "optimization", "benchmark-dataset",
    "ai-drawing", "ai-simulation-prep", "ai-plm",
    "cad-reconstruction", "other",
    "eda-chip-design", "pcb-design-ai", "aec-construction-ai",
    "robotics-mfg-ai", "vision-inspection-ml", "engineering-rag-chat",
    "medical-engineering-ai",
    "design-cognition-ai", "human-ai-design-collab",
]

VALID_TYPES = [
    "commercial-product", "academic-paper", "open-source",
    "research-project", "benchmark-dataset",
]

SYSTEM_PROMPT = f"""You are a research database curator for an AI engineering design knowledge graph.
Your job is to take messy, partial, or freeform input about an AI/ML project or paper and return a
fully structured JSON record matching this schema.

REQUIRED fields (must always be present):
  id          - URL-safe slug derived from the name (lowercase, hyphens, no spaces or special chars)
  name        - Full proper name of the project/paper
  category    - One of the valid categories below
  type        - One of the valid types below
  description - 2-5 sentence description of what it does, its approach, and significance

OPTIONAL fields (include when you can infer them):
  organization      - Primary affiliation (university, company, lab)
  country           - ISO 2-letter country code of primary org (e.g. "US", "CN", "DE")
  year              - Publication/release year as integer
  url_primary       - Main URL (homepage, paper DOI, or GitHub)
  url_paper         - Paper/preprint URL if different from primary
  url_github        - GitHub repo URL
  techniques        - List of ML techniques used (e.g. ["transformer", "diffusion", "gnn"])
  input_modality    - What the model takes as input (e.g. "text", "image", "mesh", "sketch")
  output_modality   - What the model outputs (e.g. "cad-model", "mesh", "code", "3d-shape")
  physics_domain    - Physics domain if applicable (e.g. "fluid-dynamics", "structural", "none")
  industry_application - List of industry verticals (e.g. ["automotive", "aerospace", "medical"])
  status            - One of: research-prototype, production, deprecated, dataset-only
  tags              - List of freeform tags

VALID CATEGORIES: {json.dumps(VALID_CATEGORIES, indent=None)}

VALID TYPES: {json.dumps(VALID_TYPES, indent=None)}

Rules:
- Return ONLY valid JSON, no explanation, no markdown code fences.
- The id must be a clean slug: lowercase letters, digits, hyphens only (no underscores, no dots).
- If you are unsure about a field, omit it rather than guessing badly.
- category and type must be from the valid lists above — use "other" / "research-project" as fallbacks.
- description should be factual and specific, not marketing language.
- If the input is already a well-formed record, return it as-is (you may improve the description).
"""


def slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")[:120]


def is_structured(rec: dict) -> bool:
    """Return True if rec already has all required fields populated."""
    return all(rec.get(k) for k in REQUIRED)


def fetch_url_text(url: str, max_chars: int = 3000) -> str:
    """Try to fetch plain text from a URL. Returns empty string on failure."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (research-db-bot/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read(max_chars * 4).decode("utf-8", errors="replace")
        # Strip HTML tags crudely
        text = re.sub(r"<[^>]+>", " ", raw)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars]
    except Exception:
        return ""


def structure_with_gpt(raw_entry: str, client) -> dict | None:
    """Call GPT-4o to structure a single messy entry. Returns dict or None on failure."""
    # If it looks like a URL, try to fetch content to give GPT more context
    url_match = re.match(r"https?://\S+", raw_entry.strip())
    extra = ""
    if url_match:
        url = url_match.group(0)
        print(f"  Fetching {url} …")
        page_text = fetch_url_text(url)
        if page_text:
            extra = f"\n\nPage content (first 3000 chars):\n{page_text}"

    user_msg = f"Structure this into a project record:\n\n{raw_entry}{extra}"

    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0,
            max_tokens=800,
            response_format={"type": "json_object"},
        )
        text = resp.choices[0].message.content.strip()
        rec = json.loads(text)
        # Ensure id is present and clean
        if not rec.get("id") and rec.get("name"):
            rec["id"] = slugify(rec["name"])
        return rec
    except Exception as e:
        print(f"  GPT error: {e}", file=sys.stderr)
        return None


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", help="Print results but don't overwrite inbox")
    args = p.parse_args()

    if not INBOX.exists() or INBOX.stat().st_size == 0:
        print("Inbox is empty — nothing to structure.")
        return 0

    from openai import OpenAI  # type: ignore
    client = OpenAI()

    raw_lines = [l.strip() for l in INBOX.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"Structuring {len(raw_lines)} inbox entries …")

    structured: list[dict] = []
    skipped = 0

    for i, line in enumerate(raw_lines, 1):
        print(f"\n[{i}/{len(raw_lines)}] {line[:80]}{'…' if len(line) > 80 else ''}")

        # Try to parse as JSON first
        rec: dict | None = None
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            pass

        if rec and is_structured(rec):
            print("  Already structured — passing through.")
            structured.append(rec)
            continue

        # Messy or partial — call GPT
        raw_text = line if rec is None else json.dumps(rec)
        result = structure_with_gpt(raw_text, client)

        if result is None:
            print(f"  Failed to structure — keeping raw line as-is.", file=sys.stderr)
            # Keep original line to avoid data loss; consolidate.py will reject it cleanly
            try:
                structured.append(json.loads(line))
            except Exception:
                skipped += 1
            continue

        # Tag it as inbox-structured
        result.setdefault("tags", [])
        if "inbox-structured" not in result["tags"]:
            result["tags"].append("inbox-structured")

        print(f"  → {result.get('name', '?')} [{result.get('category', '?')}] ({result.get('type', '?')})")
        structured.append(result)

    print(f"\n{len(structured)} records structured, {skipped} skipped (unparseable).")

    if args.dry_run:
        print("\nDry-run — not writing. Results:")
        for r in structured:
            print(json.dumps(r, ensure_ascii=False))
        return 0

    with open(INBOX, "w", encoding="utf-8") as f:
        for rec in structured:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"Wrote {len(structured)} structured records back to {INBOX.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
