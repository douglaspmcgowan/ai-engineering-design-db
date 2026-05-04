"""
consolidate.py — merge raw/*.jsonl files into consolidated.jsonl, dedupe by id, validate schema.

Usage:
    python scripts/consolidate.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"
OUT_FILE = ROOT / "consolidated.jsonl"
STATS_FILE = ROOT / "consolidated-stats.json"

REQUIRED = ["id", "name", "category", "type", "description"]
VALID_CATEGORY = {
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
    # Wave 3 additions (EDA/PCB/AEC/robotics/vision/RAG/medical)
    "eda-chip-design", "pcb-design-ai", "aec-construction-ai",
    "robotics-mfg-ai", "vision-inspection-ml", "engineering-rag-chat",
    "medical-engineering-ai",
    # Wave 4 additions (AI-in-design research / IDETC design cognition)
    "design-cognition-ai", "human-ai-design-collab",
}

# Wave 3: Codex defaulted to "other" for several files instead of picking
# a real category. Override based on source file. Records that already have
# a meaningful category (not "other") are left alone.
SOURCE_FILE_DEFAULT_CATEGORY = {
    "16-eda-chip-design.jsonl":          "eda-chip-design",
    "17-pcb-electronics-design.jsonl":   "pcb-design-ai",
    "18-aec-construction-ai.jsonl":      "aec-construction-ai",
    "19-robotics-manufacturing.jsonl":   "robotics-mfg-ai",
    "20-vision-inspection-qa-ml.jsonl":  "vision-inspection-ml",
    "21-process-monitoring-am-boost.jsonl": "process-monitoring-ml",
    "22-dfm-machining-molding.jsonl":    "dfm-ai",
    "23-medical-engineering-ai.jsonl":   "medical-engineering-ai",
    "24-engineering-rag-chat.jsonl":     "engineering-rag-chat",
    "25-scan-to-cad-reverse-eng.jsonl":  "cad-reconstruction",
}
VALID_TYPE = {
    "commercial-product", "academic-paper", "open-source",
    "research-project", "benchmark-dataset",
}


def slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:80]


def normalize(rec: dict) -> dict | None:
    """Coerce a record toward the schema. Returns None if hopelessly invalid."""
    if not isinstance(rec, dict):
        return None
    # Required fields
    for k in REQUIRED:
        if k not in rec or rec[k] in (None, "", []):
            if k == "id" and "name" in rec and rec["name"]:
                rec["id"] = slugify(rec["name"])
            else:
                return None
    # Slug the id if it isn't already
    rec["id"] = slugify(str(rec["id"]))
    if not rec["id"]:
        return None
    # Coerce types
    if isinstance(rec.get("year"), str):
        try:
            rec["year"] = int(re.search(r"\d{4}", rec["year"]).group())
        except Exception:
            rec["year"] = None
    # Lists
    for k in ["techniques", "industry_application", "tags"]:
        v = rec.get(k)
        if v is None:
            continue
        if isinstance(v, str):
            rec[k] = [t.strip() for t in re.split(r"[,;]", v) if t.strip()]
        elif not isinstance(v, list):
            rec[k] = [str(v)]
    # Validate enums (warn but keep)
    if rec.get("category") not in VALID_CATEGORY:
        rec.setdefault("tags", []).append(f"unknown-category:{rec.get('category')}")
        rec["category"] = "other"
    if rec.get("type") not in VALID_TYPE:
        rec.setdefault("tags", []).append(f"unknown-type:{rec.get('type')}")
        rec["type"] = "research-project"
    return rec


def merge_records(a: dict, b: dict) -> dict:
    """Merge two records with the same id, preferring non-empty fields from a."""
    out = dict(a)
    for k, v in b.items():
        if k in ("tags", "techniques", "industry_application"):
            out.setdefault(k, [])
            for x in v or []:
                if x not in out[k]:
                    out[k].append(x)
        elif k == "description":
            # Prefer the longer description
            if not out.get("description") or len(str(v)) > len(str(out["description"])):
                out["description"] = v
        elif not out.get(k) and v:
            out[k] = v
    return out


def main() -> int:
    if not RAW_DIR.exists():
        print(f"raw/ dir not found at {RAW_DIR}", file=sys.stderr)
        return 1

    records: dict[str, dict] = {}
    per_file_counts: dict[str, int] = {}
    per_file_dropped: dict[str, int] = defaultdict(int)
    duplicates_merged = 0

    for jsonl in sorted(RAW_DIR.glob("*.jsonl")):
        loaded = 0
        with open(jsonl, "r", encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("//"):
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError as e:
                    per_file_dropped[jsonl.name] += 1
                    print(f"  ! {jsonl.name}:{lineno} JSON error: {e}", file=sys.stderr)
                    continue
                rec = normalize(rec)
                if rec is None:
                    per_file_dropped[jsonl.name] += 1
                    continue
                rec.setdefault("source_files", []).append(jsonl.name)
                # Apply per-file category override when Codex defaulted to "other"
                override = SOURCE_FILE_DEFAULT_CATEGORY.get(jsonl.name)
                if override and rec.get("category") == "other":
                    rec["category"] = override
                if rec["id"] in records:
                    duplicates_merged += 1
                    records[rec["id"]] = merge_records(records[rec["id"]], rec)
                else:
                    records[rec["id"]] = rec
                loaded += 1
        per_file_counts[jsonl.name] = loaded

    # Write consolidated
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        for rid in sorted(records):
            f.write(json.dumps(records[rid], ensure_ascii=False) + "\n")

    # Stats
    by_category: dict[str, int] = defaultdict(int)
    by_type: dict[str, int] = defaultdict(int)
    for r in records.values():
        by_category[r.get("category", "?")] += 1
        by_type[r.get("type", "?")] += 1

    stats = {
        "total_unique": len(records),
        "duplicates_merged": duplicates_merged,
        "per_file_counts": per_file_counts,
        "per_file_dropped": dict(per_file_dropped),
        "by_category": dict(sorted(by_category.items(), key=lambda x: -x[1])),
        "by_type": dict(sorted(by_type.items(), key=lambda x: -x[1])),
    }
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print(f"Wrote {len(records)} unique records to {OUT_FILE.name}")
    print(f"Merged {duplicates_merged} duplicates")
    print(f"By category: {stats['by_category']}")
    print(f"By type: {stats['by_type']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
