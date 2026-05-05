#!/usr/bin/env python3
"""Generate novelty report for newly ingested records using embedding similarity."""

import json
import math
import pathlib
import datetime

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

ROOT = pathlib.Path(__file__).parent.parent
EMBEDDINGS_PATH  = ROOT / "embeddings.jsonl"
INBOX_PATH       = ROOT / "raw" / "inbox.jsonl"
CONSOLIDATED_PATH = ROOT / "consolidated.jsonl"
REPORTS_DIR      = ROOT / "reports"


def cosine_sim(a, b):
    if HAS_NUMPY:
        av, bv = np.array(a, dtype=float), np.array(b, dtype=float)
        denom = np.linalg.norm(av) * np.linalg.norm(bv)
        return float(np.dot(av, bv) / denom) if denom > 0 else 0.0
    dot   = sum(x * y for x, y in zip(a, b))
    na    = math.sqrt(sum(x * x for x in a))
    nb    = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na * nb > 0 else 0.0


def load_jsonl(path):
    rows = []
    if not path.exists():
        return rows
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return rows


def main():
    today = datetime.date.today().isoformat()
    REPORTS_DIR.mkdir(exist_ok=True)

    inbox        = load_jsonl(INBOX_PATH)
    embeddings   = load_jsonl(EMBEDDINGS_PATH)
    consolidated = load_jsonl(CONSOLIDATED_PATH)

    embed_by_id = {r["id"]: r["embedding"] for r in embeddings if "id" in r and "embedding" in r}
    meta_by_id  = {r["id"]: r for r in consolidated if "id" in r}

    lines = [
        f"# Embedding Report — {today}",
        "",
        f"*Generated: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*",
        "",
    ]

    if not inbox:
        lines += ["## Summary", "", "No new records in inbox — nothing to analyze.", ""]
        _write(lines, today)
        return

    new_ids = [r["id"] for r in inbox if r.get("id") and r["id"] in embed_by_id]
    all_ids = list(embed_by_id.keys())

    if not new_ids:
        lines += [
            "## Summary", "",
            f"{len(inbox)} records in inbox but none have embeddings yet.",
            "Run `python scripts/embed.py` first.", "",
        ]
        _write(lines, today)
        return

    novelty_scores = []
    details = []

    for nid in new_ids:
        new_emb  = embed_by_id[nid]
        new_meta = meta_by_id.get(nid, next((r for r in inbox if r.get("id") == nid), {}))

        sims = []
        for oid in all_ids:
            if oid == nid:
                continue
            sim = cosine_sim(new_emb, embed_by_id[oid])
            m   = meta_by_id.get(oid, {})
            sims.append((sim, oid, m.get("name", oid), m.get("organization", "")))

        sims.sort(reverse=True)
        top5     = sims[:5]
        avg_sim  = sum(s for s, *_ in top5) / len(top5) if top5 else 0.0
        novelty  = round(1.0 - avg_sim, 2)
        novelty_scores.append(novelty)

        details.append({
            "id":      nid,
            "name":    new_meta.get("name",         nid),
            "org":     new_meta.get("organization", ""),
            "cat":     new_meta.get("category",     ""),
            "novelty": novelty,
            "top5":    top5,
        })

    avg_nov = round(sum(novelty_scores) / len(novelty_scores), 2) if novelty_scores else 0.0
    high    = sum(1 for s in novelty_scores if s > 0.6)
    mid     = sum(1 for s in novelty_scores if 0.3 <= s <= 0.6)
    low     = sum(1 for s in novelty_scores if s < 0.3)

    lines += [
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| New records processed | {len(details)} |",
        f"| Average novelty score | {avg_nov} / 1.0 |",
        f"| Highly novel  (> 0.6) | {high} |",
        f"| Moderate (0.3 – 0.6)  | {mid}  |",
        f"| Similar to existing   | {low}  |",
        "",
        "## New Records",
        "",
    ]

    for d in sorted(details, key=lambda x: x["novelty"], reverse=True):
        bar = "█" * int(d["novelty"] * 10) + "░" * (10 - int(d["novelty"] * 10))
        lines += [
            f"### {d['name']}",
            f"**{d['org']}** · `{d['cat']}` · Novelty: `{d['novelty']}` `[{bar}]`",
            "",
            "Top-5 nearest existing entries:",
            "",
            "| Similarity | Name | Organization |",
            "|-----------|------|--------------|",
        ]
        for sim, _, name, org in d["top5"]:
            lines.append(f"| {sim:.3f} | {name} | {org} |")
        lines += ["", "---", ""]

    _write(lines, today)


def _write(lines, today):
    text = "\n".join(lines)
    dated  = REPORTS_DIR / f"{today}.md"
    latest = REPORTS_DIR / "latest.md"
    dated.write_text(text,  encoding="utf-8")
    latest.write_text(text, encoding="utf-8")
    print(f"[embedding-report] Written to {dated}")


if __name__ == "__main__":
    main()
