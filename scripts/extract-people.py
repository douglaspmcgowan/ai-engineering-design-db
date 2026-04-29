"""
extract-people.py — extract Person nodes from project descriptions via GPT-4.1-mini.

For each project, we ask the model to extract any researchers, founders, or
authors named in the description. Writes:

  graph/people-nodes.csv   — id, type=Person, label, props
  graph/people-edges.csv   — source=project, target=person, type=AUTHORED

Usage:
    python scripts/extract-people.py [--limit N] [--dry-run]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
IN_FILE = ROOT / "consolidated.jsonl"
OUT_NODES = ROOT / "graph" / "people-nodes.csv"
OUT_EDGES = ROOT / "graph" / "people-edges.csv"

SYSTEM_PROMPT = """\
Extract any people (researchers, founders, principal authors, lab leads) named
in the project description. Return JSON {"people": [{"name": "...", "role": "..."}]}.

role: "author" | "founder" | "lead" | "other"

Rules:
- Only people explicitly named in the description text.
- Use the full name as written, not abbreviations.
- No team names, no company names, no organization names.
- Return {"people": []} if none.
"""

NAME_RE = re.compile(r"^[A-Z][a-zA-Z'\-\.]+(?:\s+[A-Z][a-zA-Z'\-\.]+){1,3}$")


def slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")[:60]


def call_with_retry(client, system_prompt: str, user_msg: str, max_retries: int = 3):
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0,
                max_tokens=300,
                response_format={"type": "json_object"},
            )
        except Exception as e:
            last_err = e
            msg = str(e).lower()
            if any(s in msg for s in ("connection", "timeout", "rate", "503", "502", "504")):
                time.sleep(1.5 * (attempt + 1))
                continue
            raise
    raise last_err  # type: ignore


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    records = [json.loads(l) for l in open(IN_FILE, encoding="utf-8") if l.strip()]
    if args.limit:
        records = records[: args.limit]
    print(f"Loaded {len(records)} records")

    if args.dry_run:
        # Estimate ~250 input tokens + ~50 output tokens per record
        cost = len(records) * (250 / 1_000_000 * 0.40 + 50 / 1_000_000 * 1.60)
        print(f"Estimated cost for {len(records)} records with GPT-4.1-mini: ~${cost:.3f}")
        return 0

    from openai import OpenAI  # type: ignore
    client = OpenAI()

    people: dict[str, dict] = {}  # slug → {label, count, projects}
    edges: list[dict] = []

    total = len(records)
    for i, rec in enumerate(records):
        desc = rec.get("description") or ""
        if len(desc) < 60:
            continue
        try:
            resp = call_with_retry(
                client, SYSTEM_PROMPT,
                f"Project: {rec['name']}\nDescription: {desc}"
            )
            obj = json.loads(resp.choices[0].message.content.strip())
            persons = obj.get("people", []) if isinstance(obj, dict) else []
        except Exception as e:
            print(f"  [{i+1}/{total}] {rec['id']}: error after retries - {e}", file=sys.stderr)
            continue

        for p in persons:
            name = (p.get("name") or "").strip()
            if not name or len(name) < 4 or len(name) > 60:
                continue
            # Sanity check: looks like a real name (Title Case, 2-4 tokens)
            if not NAME_RE.match(name):
                continue
            slug = slugify(name)
            if not slug:
                continue
            entry = people.setdefault(slug, {"label": name, "count": 0, "projects": []})
            entry["count"] += 1
            entry["projects"].append(rec["id"])
            edges.append({
                "source": f"project:{rec['id']}",
                "target": f"person:{slug}",
                "type": "AUTHORED",
                "weight": 1.0,
                "evidence": p.get("role", "author"),
            })

        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{total} done, {len(people)} unique people")

    OUT_NODES.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_NODES, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "type", "label", "props"])
        w.writeheader()
        for slug, entry in sorted(people.items(), key=lambda x: -x[1]["count"]):
            w.writerow({
                "id":    f"person:{slug}",
                "type":  "Person",
                "label": entry["label"],
                "props": json.dumps({"count": entry["count"]}),
            })

    with open(OUT_EDGES, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["source", "target", "type", "weight", "evidence"])
        w.writeheader()
        w.writerows(edges)

    print(f"\nWrote {len(people)} unique people, {len(edges)} AUTHORED edges")
    print("Top 10 most-mentioned:")
    for slug, entry in sorted(people.items(), key=lambda x: -x[1]["count"])[:10]:
        print(f"  {entry['count']:3d}  {entry['label']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
