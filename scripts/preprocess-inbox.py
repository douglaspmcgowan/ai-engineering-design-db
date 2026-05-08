"""
preprocess-inbox.py — normalize inbox-*.jsonl agent output into the schema
that consolidate.py expects, then rewrite as 27-* and 28-* raw files.

Maps:
  entry_type → type    (tool→commercial-product, paper→academic-paper, talk→research-project)
  url        → url_primary
  (missing)  → id (slugified name)
  (missing)  → status = "active"

Drops the 'source' field (used only as agent-provenance metadata).

Usage:  python scripts/preprocess-inbox.py
"""
from __future__ import annotations
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"

ENTRY_TYPE_MAP = {
    "tool":    "commercial-product",
    "product": "commercial-product",
    "paper":   "academic-paper",
    "talk":    "research-project",
    "video":   "research-project",
    "demo":    "research-project",
}

# Category remap for unknowns the agents emitted that aren't in VALID_CATEGORY
CATEGORY_REMAP = {
    "agent-cad":         "cad-agent",
    "design-automation": "human-ai-design-collab",
    "simulation-surrogate": "physics-surrogate",
    "materials-discovery":  "generative-materials",
}

def slugify(text: str) -> str:
    s = (text or "").lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:80]

def transform(rec: dict) -> dict | None:
    name = rec.get("name")
    if not name:
        return None
    out = {
        "id":   rec.get("id") or slugify(name),
        "name": name,
        "category": CATEGORY_REMAP.get(rec.get("category"), rec.get("category") or "other"),
        "type": ENTRY_TYPE_MAP.get(rec.get("entry_type", "talk"), "research-project"),
        "description": rec.get("description") or "",
        "year": rec.get("year"),
        "organization": rec.get("organization") or "",
        "techniques": rec.get("techniques") or [],
        "industry_application": rec.get("industry_application") or [],
        "input_modality": rec.get("input_modality") or "",
        "output_modality": rec.get("output_modality") or "",
        "tags": (rec.get("tags") or []) + (
            [f"source:{rec['source']}"] if rec.get("source") else []
        ),
        "status": "active",
        "entry_type": rec.get("entry_type", ""),  # keep for graph-data badge
    }
    # url mapping — agent put it in 'url'; consolidate expects url_primary
    if rec.get("url"):
        # Github URL → url_github; otherwise → url_primary
        if "github.com" in rec["url"]:
            out["url_github"] = rec["url"]
        else:
            out["url_primary"] = rec["url"]
    if rec.get("url_paper"):
        out["url_paper"] = rec["url_paper"]
    return out

def process_file(in_path: Path, out_path: Path) -> int:
    n = 0
    with open(in_path, "r", encoding="utf-8") as fin, open(out_path, "w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = transform(rec)
            if t is None:
                continue
            fout.write(json.dumps(t, ensure_ascii=False) + "\n")
            n += 1
    return n

def main():
    pairs = [
        (RAW / "inbox-youtube-conferences.jsonl", RAW / "27-youtube-conferences.jsonl"),
        (RAW / "inbox-products-nasa.jsonl",        RAW / "28-products-nasa-linkedin.jsonl"),
    ]
    for src, dst in pairs:
        if not src.exists():
            print(f"  skip (no file): {src.name}")
            continue
        n = process_file(src, dst)
        print(f"  {src.name} -> {dst.name}: {n} records")

if __name__ == "__main__":
    main()
