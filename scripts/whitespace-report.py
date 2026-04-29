"""
whitespace-report.py — find sparse cells in the (modality × physics × industry) space.

Produces:
  graph/whitespace-modality.csv      — input × output modality counts
  graph/whitespace-physics-industry.csv  — physics_domain × industry counts
  graph/whitespace-category-year.csv — category × year heat map
  Console summary: top empty cells = candidate whitespace

Usage:
    python scripts/whitespace-report.py
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict, Counter
from pathlib import Path

# Force UTF-8 stdout (Windows console defaults to cp1252 which can't print → × etc.)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
IN_FILE = ROOT / "consolidated.jsonl"
OUT_DIR = ROOT / "graph"


def main() -> int:
    if not IN_FILE.exists():
        print(f"missing {IN_FILE}", file=sys.stderr)
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    records = [json.loads(l) for l in open(IN_FILE, encoding="utf-8") if l.strip()]
    print(f"Loaded {len(records)} records\n")

    # ── 1. input × output modality ───────────────────────────────────────────
    mod_counts: dict[tuple[str, str], int] = defaultdict(int)
    inputs: set[str] = set()
    outputs: set[str] = set()
    for r in records:
        i = (r.get("input_modality") or "").strip() or "?"
        o = (r.get("output_modality") or "").strip() or "?"
        mod_counts[(i, o)] += 1
        inputs.add(i)
        outputs.add(o)

    inputs_sorted = sorted(inputs - {"?"}) + (["?"] if "?" in inputs else [])
    outputs_sorted = sorted(outputs - {"?"}) + (["?"] if "?" in outputs else [])
    with open(OUT_DIR / "whitespace-modality.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["input ↓ \\ output →"] + outputs_sorted)
        for i in inputs_sorted:
            row = [i] + [mod_counts.get((i, o), 0) for o in outputs_sorted]
            w.writerow(row)

    # ── 2. physics × industry ─────────────────────────────────────────────────
    pi_counts: dict[tuple[str, str], int] = defaultdict(int)
    physics: set[str] = set()
    industries: set[str] = set()
    for r in records:
        p = (r.get("physics_domain") or "").strip() or "?"
        physics.add(p)
        for ind in r.get("industry_application") or []:
            ind = ind.strip()
            if not ind:
                continue
            industries.add(ind)
            pi_counts[(p, ind)] += 1

    physics_sorted = sorted(physics - {"?"}) + (["?"] if "?" in physics else [])
    industries_sorted = sorted(industries)
    with open(OUT_DIR / "whitespace-physics-industry.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["physics ↓ \\ industry →"] + industries_sorted)
        for p in physics_sorted:
            row = [p] + [pi_counts.get((p, ind), 0) for ind in industries_sorted]
            w.writerow(row)

    # ── 3. category × year ────────────────────────────────────────────────────
    cy_counts: dict[tuple[str, int], int] = defaultdict(int)
    cats: set[str] = set()
    years: set[int] = set()
    for r in records:
        c = (r.get("category") or "").strip() or "other"
        y = r.get("year")
        if isinstance(y, int):
            cy_counts[(c, y)] += 1
            cats.add(c)
            years.add(y)

    cats_sorted = sorted(cats)
    years_sorted = sorted(years)
    with open(OUT_DIR / "whitespace-category-year.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["category ↓ \\ year →"] + [str(y) for y in years_sorted])
        for c in cats_sorted:
            row = [c] + [cy_counts.get((c, y), 0) for y in years_sorted]
            w.writerow(row)

    # ── Console summary ───────────────────────────────────────────────────────
    print(f"  Modality matrix: {len(inputs_sorted)} inputs × {len(outputs_sorted)} outputs"
          f" → {sum(mod_counts.values())} records")
    print(f"  Physics × industry: {len(physics_sorted)} × {len(industries_sorted)}")
    print(f"  Category × year: {len(cats_sorted)} × {len(years_sorted)}")
    print()

    # Densest modality cells
    print("Top 10 most-populated (input → output) cells:")
    for (i, o), n in sorted(mod_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {n:3d}  {i:20s} -> {o}")

    print("\nBottom 10 sparsest non-empty (input → output) cells (≤2):")
    sparse = sorted(((k, v) for k, v in mod_counts.items() if v <= 2 and k[0] != "?" and k[1] != "?"),
                    key=lambda x: x[1])[:10]
    for (i, o), n in sparse:
        print(f"  {n:3d}  {i:20s} -> {o}")

    # Empty (physics, industry) candidates — pairs we have NO records for
    empties = []
    for p in physics_sorted:
        if p == "?":
            continue
        for ind in industries_sorted:
            if pi_counts.get((p, ind), 0) == 0:
                empties.append((p, ind))
    print(f"\nEmpty (physics × industry) cells: {len(empties)} (out of "
          f"{(len(physics_sorted)-1)*len(industries_sorted)})")
    print("Sample (first 15):")
    for p, ind in empties[:15]:
        print(f"  {p:20s} × {ind}")

    print(f"\nWrote 3 CSV reports to {OUT_DIR}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
