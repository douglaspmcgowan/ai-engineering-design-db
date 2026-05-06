"""
fix_data_quality.py — DB quality fixes from audit
Run from repo root: python scripts/fix_data_quality.py

Changes made:
1. Remove 2 exact duplicate records (same paper, two IDs)
2. Normalize 4 technique slug synonyms across all records
3. Merge 4 under-populated categories into larger siblings
4. Fix frustum-truesolid: unify into one record

Prints a detailed change log.
"""
import json
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
JSONL = ROOT / "consolidated.jsonl"


# ── 1. Records to remove (exact or near-exact duplicates) ──────────────────
# ml-support-structure-design-am shares the same DOI as the longer-titled record.
# frustum-truesolid-generative-design is the same product as frustum-truesolid (same URL/year).
REMOVE_IDS = {
    "ml-support-structure-design-am",
    "frustum-truesolid-generative-design",
}

# ── 2. Technique slug normalization ─────────────────────────────────────────
# Maps old (minority) slug → canonical (majority) slug.
# Keeps the graph clean by eliminating near-synonym nodes.
TECH_SYNONYMS = {
    "diffusion":        "diffusion-model",      # 2 → joins 60
    "deep-learning":    "machine-learning",     # 2 → joins 21
    "surrogate-model":  "surrogate-modeling",   # 5 → joins 16
    "physics-ai":       "physics-informed-nn",  # 6 → joins 45
}

# ── 3. Category reassignments for under-populated (≤ 3 entry) categories ───
# Maps old category → new category, with reason.
CATEGORY_MERGES = {
    # ai-simulation-prep (2 entries): these are simulation/CAD assistants
    # Ansys Discovery + AI+ → cad-copilot
    # NX CAM AI Copilot → dfm-ai (machining-specific, handled per-ID below)
    "ai-simulation-prep": "cad-copilot",

    # human-ai-design-collab (2 entries): both are design-cognition research
    "human-ai-design-collab": "design-cognition-ai",

    # ai-plm (3 entries): PLM assistants are a type of engineering copilot
    "ai-plm": "cad-copilot",

    # scientific-ml (4 entries): UQ / probabilistic tools — fold into neural-operator
    # as they serve the same "scientific computing ML" niche
    "scientific-ml": "neural-operator",
}

# Per-record category overrides that differ from the bulk merge above
CATEGORY_OVERRIDES = {
    # NX CAM AI Copilot is a machining assistant, not a general CAD copilot
    "nx-cam-ai-copilot": "dfm-ai",
}

# ── 4. Specific field patches for kept records ─────────────────────────────
# frustum-truesolid: update its category to topology-optimization
# (removing the separate frustum-truesolid-generative-design record)
# and add better description scope
FIELD_PATCHES = {
    "frustum-truesolid": {
        "category": "topology-optimization",
        "entry_type": "commercial-product",
        "description": (
            "Frustum TrueSOLID is a commercial topology optimization engine acquired by Siemens "
            "and integrated into NX as NX Topology Optimization. Originally a standalone product, "
            "it uses manufacturing-aware TO to generate optimized geometries for CNC machining, "
            "casting, and additive manufacturing. A pioneer in commercial generative design for "
            "mechanical components."
        ),
    },
}


def main():
    with open(JSONL, encoding="utf-8") as f:
        recs = [json.loads(l) for l in f if l.strip()]

    print(f"Loaded {len(recs)} records\n")
    changes = []

    # ── Pass 1: Remove duplicates ─────────────────────────────────────────
    before = len(recs)
    recs = [r for r in recs if r["id"] not in REMOVE_IDS]
    removed = before - len(recs)
    changes.append(f"REMOVED {removed} duplicate records:")
    changes.append(f"  - ml-support-structure-design-am (same DOI as machine-learning-driven-design-of-support-structures...)")
    changes.append(f"  - frustum-truesolid-generative-design (same product/URL/year as frustum-truesolid)")
    print(f"Pass 1 — Removed {removed} duplicates")

    # ── Pass 2: Technique synonym normalization ───────────────────────────
    tech_changed = 0
    for r in recs:
        techs = r.get("techniques") or []
        new_techs = []
        changed = False
        seen = set()
        for t in techs:
            canonical = TECH_SYNONYMS.get(t, t)
            if canonical not in seen:
                new_techs.append(canonical)
                seen.add(canonical)
            if canonical != t:
                changed = True
        if changed:
            r["techniques"] = new_techs
            tech_changed += 1
    changes.append(f"\nNORMALIZED technique synonyms in {tech_changed} records:")
    for old, new in TECH_SYNONYMS.items():
        changes.append(f"  - '{old}' → '{new}'")
    print(f"Pass 2 — Technique normalization: {tech_changed} records updated")

    # ── Pass 3: Category merges ───────────────────────────────────────────
    cat_changed = 0
    cat_detail = {}
    for r in recs:
        new_cat = CATEGORY_OVERRIDES.get(r["id"]) or CATEGORY_MERGES.get(r.get("category"))
        if new_cat:
            old_cat = r["category"]
            r["category"] = new_cat
            cat_changed += 1
            cat_detail[r["id"]] = (old_cat, new_cat, r["name"])
    changes.append(f"\nREASSIGNED category for {cat_changed} records:")
    for rid, (old, new, name) in cat_detail.items():
        changes.append(f"  - [{rid}] {name[:55]}: '{old}' → '{new}'")
    print(f"Pass 3 — Category reassignment: {cat_changed} records updated")

    # ── Pass 4: Field patches ─────────────────────────────────────────────
    patch_changed = 0
    for r in recs:
        if r["id"] in FIELD_PATCHES:
            for field, value in FIELD_PATCHES[r["id"]].items():
                r[field] = value
            patch_changed += 1
            changes.append(f"\nPATCHED {r['id']}: updated {list(FIELD_PATCHES[r['id']].keys())}")
    print(f"Pass 4 — Field patches: {patch_changed} records updated")

    # ── Write back ────────────────────────────────────────────────────────
    with open(JSONL, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\nDone — {len(recs)} records total (was {before})")

    # ── Category count summary ────────────────────────────────────────────
    print("\nCategory counts after merge:")
    cats = Counter(r.get("category", "?") for r in recs)
    for cat, cnt in sorted(cats.items(), key=lambda x: -x[1])[:15]:
        print(f"  {cnt:4d}  {cat}")

    print("\n=== CHANGE LOG ===")
    for line in changes:
        print(line)


if __name__ == "__main__":
    main()
