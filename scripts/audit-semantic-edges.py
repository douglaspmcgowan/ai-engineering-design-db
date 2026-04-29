"""
audit-semantic-edges.py — quality audit of graph/semantic-edges.csv.

Reports edges that are likely wrong or weak so we can decide whether the
LLM pass needs a tighter prompt, a larger candidate pool, or human review.

Checks:
  1. Self-loops (source == target) — should be 0; means LLM emitted the
     project's own name as a target.
  2. Sibling-pair noise — pairs where both ids share a long stem
     (e.g. "alpha3d" and "alpha3d-game-asset-generation"). These are
     mostly the same product split into two records during ingestion;
     SEMANTICALLY_NEAR is technically correct but uninteresting.
  3. Bidirectional CITES — A cites B and B cites A. Usually means the
     LLM matched generic phrasing as a citation in both directions.
  4. Low-evidence edges — evidence string < 12 chars, or evidence equal
     to "llm-extracted" (the fallback when nothing was emitted).
  5. Duplicate (source, target, type) — should be 0 after dedup; canary
     for build-graph.py drift.
  6. Cross-cluster suspects — CITES/BUILT_ON edges where the source and
     target sit in totally different categories (e.g. text-to-cad cites
     a materials paper). Surfaces likely false matches.

Output: prints a summary and writes graph/semantic-edges-audit.csv with
flagged edges and a "reason" column.

Usage:
  py -3 scripts/audit-semantic-edges.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
EDGES_CSV = ROOT / "graph" / "semantic-edges.csv"
CONSOLIDATED = ROOT / "consolidated.jsonl"
OUT_CSV = ROOT / "graph" / "semantic-edges-audit.csv"


def _stem(pid: str) -> str:
    """Approximate stem of a project id — first 3 hyphen-tokens after 'project:'."""
    s = pid.removeprefix("project:")
    parts = s.split("-")
    return "-".join(parts[:3])


def main() -> int:
    if not EDGES_CSV.exists():
        print(f"Missing {EDGES_CSV}. Run extract-semantic-edges.py first.", file=sys.stderr)
        return 1

    # Load record metadata so we can flag cross-category edges
    cat_by_id: dict[str, str] = {}
    name_by_id: dict[str, str] = {}
    if CONSOLIDATED.exists():
        for line in open(CONSOLIDATED, encoding="utf-8"):
            if not line.strip():
                continue
            r = json.loads(line)
            cat_by_id[f"project:{r['id']}"] = r.get("category", "")
            name_by_id[f"project:{r['id']}"] = r.get("name", r["id"])

    edges: list[dict] = []
    with open(EDGES_CSV, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            edges.append(row)

    print(f"Loaded {len(edges)} semantic edges")
    print(f"Loaded {len(cat_by_id)} project categories from consolidated.jsonl")

    flagged: list[dict] = []
    by_type = Counter(e["type"] for e in edges)
    print("\n--- Edge type breakdown ---")
    for t, c in by_type.most_common():
        print(f"  {c:5d}  {t}")

    # 1. Self-loops
    self_loops = [e for e in edges if e["source"] == e["target"]]
    print(f"\n[1] Self-loops: {len(self_loops)}")
    for e in self_loops:
        flagged.append({**e, "reason": "self-loop"})

    # 2. Sibling-pair noise
    sib = [e for e in edges
           if e["type"] == "SEMANTICALLY_NEAR"
           and _stem(e["source"]) == _stem(e["target"])]
    print(f"[2] Sibling SEMANTICALLY_NEAR (likely duplicate records): {len(sib)}")
    for e in sib[:10]:
        a, b = e["source"].removeprefix("project:"), e["target"].removeprefix("project:")
        print(f"      {a}  ~~  {b}")
    for e in sib:
        flagged.append({**e, "reason": "sibling-pair (likely dup record)"})

    # 3. Bidirectional CITES
    cite_pairs = defaultdict(set)
    for e in edges:
        if e["type"] in ("CITES", "BUILT_ON", "BENCHMARKED_AGAINST"):
            cite_pairs[(e["source"], e["target"], e["type"])] = e
    bidir: list[tuple] = []
    seen_bidir: set = set()
    for (s, t, ty), e in list(cite_pairs.items()):
        rev = (t, s, ty)
        if rev in cite_pairs:
            key = tuple(sorted([s, t])) + (ty,)
            if key not in seen_bidir:
                seen_bidir.add(key)
                bidir.append((e, cite_pairs[rev]))
    print(f"[3] Bidirectional CITES/BUILT_ON pairs: {len(bidir)}")
    for a, b in bidir[:5]:
        print(f"      {a['source']} <-> {a['target']} ({a['type']})")
    for a, b in bidir:
        flagged.append({**a, "reason": "bidirectional"})
        flagged.append({**b, "reason": "bidirectional"})

    # 4. Low-evidence edges
    weak = [e for e in edges
            if e["type"] in ("CITES", "BUILT_ON", "BENCHMARKED_AGAINST")
            and (len(e.get("evidence", "")) < 12
                 or e.get("evidence", "").strip().lower() == "llm-extracted")]
    print(f"[4] Low-evidence directional edges: {len(weak)}")
    for e in weak[:5]:
        print(f"      {e['source']} -> {e['target']} ({e['type']})  ev={e.get('evidence','')!r}")
    for e in weak:
        flagged.append({**e, "reason": "low-evidence"})

    # 5. Duplicate keys
    seen: Counter = Counter()
    for e in edges:
        seen[(e["source"], e["target"], e["type"])] += 1
    dups = [(k, c) for k, c in seen.items() if c > 1]
    print(f"[5] Duplicate (source, target, type) rows: {len(dups)}")
    for (s, t, ty), c in dups[:5]:
        print(f"      x{c}  {s} -> {t} ({ty})")

    # 6. Cross-category CITES / BUILT_ON
    cross = []
    for e in edges:
        if e["type"] not in ("CITES", "BUILT_ON"):
            continue
        cs = cat_by_id.get(e["source"])
        ct = cat_by_id.get(e["target"])
        if cs and ct and cs != ct:
            # Only suspicious if categories are far apart, not just adjacent.
            # Heuristic: flag only if neither category is "other" / "ai-platform".
            if cs not in ("other", "ai-platform") and ct not in ("other", "ai-platform"):
                cross.append({**e, "src_cat": cs, "tgt_cat": ct})
    print(f"[6] Cross-category CITES/BUILT_ON (heuristic suspect): {len(cross)}")
    cat_pairs = Counter((e["src_cat"], e["tgt_cat"]) for e in cross)
    print("    Top cross-category pairs:")
    for (a, b), c in cat_pairs.most_common(8):
        print(f"      {c:3d}  {a}  ->  {b}")
    for e in cross:
        flagged.append({
            "source": e["source"], "target": e["target"], "type": e["type"],
            "weight": e["weight"], "evidence": e["evidence"],
            "reason": f"cross-category ({e['src_cat']} -> {e['tgt_cat']})",
        })

    # Write flagged CSV
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["source", "target", "type", "weight", "evidence", "reason"])
        w.writeheader()
        for row in flagged:
            w.writerow({k: row.get(k, "") for k in
                        ["source", "target", "type", "weight", "evidence", "reason"]})

    total_flagged = len({(r["source"], r["target"], r["type"], r["reason"]) for r in flagged})
    print(f"\nWrote {total_flagged} flagged edges to {OUT_CSV}")
    print(f"  Flagged share: {total_flagged}/{len(edges)} = {100*total_flagged/max(1,len(edges)):.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
