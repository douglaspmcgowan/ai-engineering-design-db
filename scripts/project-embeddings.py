"""
project-embeddings.py — UMAP 2D projection + k-means cluster labels for the explorer.

Reads embeddings.jsonl + consolidated.jsonl, runs UMAP, k-means, and writes:
  - graph/embed-coords.json   (id -> {x, y, cluster_k, cluster_category})
  - graph/cluster-labels.json (two label sets for user to compare)

Usage:
    python scripts/project-embeddings.py [--k 20] [--neighbors 15] [--dry-run]
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from collections import Counter

import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
EMBEDDINGS = ROOT / "embeddings.jsonl"
CONSOLIDATED = ROOT / "consolidated.jsonl"
OUT_COORDS = ROOT / "graph" / "embed-coords.json"
OUT_LABELS = ROOT / "graph" / "cluster-labels.json"


def load_data():
    records = {}
    for line in open(CONSOLIDATED, encoding="utf-8"):
        if not line.strip(): continue
        r = json.loads(line)
        records[r["id"]] = r

    vecs, ids = [], []
    for line in open(EMBEDDINGS, encoding="utf-8"):
        if not line.strip(): continue
        e = json.loads(line)
        if e["id"] in records:
            ids.append(e["id"])
            vecs.append(e["vector"])

    arr = np.array(vecs, dtype=np.float32)
    norms = np.linalg.norm(arr, axis=1, keepdims=True) + 1e-12
    return ids, arr / norms, records


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=20)
    ap.add_argument("--neighbors", type=int, default=15)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    print("Loading embeddings…")
    ids, vecs, records = load_data()
    print(f"  {len(ids)} project vectors, shape {vecs.shape}")

    # ── UMAP ──────────────────────────────────────────────────────────────────
    print("Running UMAP (this takes ~30s)…")
    import umap  # type: ignore
    reducer = umap.UMAP(
        n_components=2,
        n_neighbors=args.neighbors,
        min_dist=0.08,
        metric="cosine",
        random_state=42,
    )
    coords_2d = reducer.fit_transform(vecs)
    print(f"  UMAP done. Range x=[{coords_2d[:,0].min():.2f},{coords_2d[:,0].max():.2f}] y=[{coords_2d[:,1].min():.2f},{coords_2d[:,1].max():.2f}]")

    # ── K-Means ───────────────────────────────────────────────────────────────
    print(f"Running k-means (k={args.k})…")
    from sklearn.cluster import KMeans  # type: ignore
    km = KMeans(n_clusters=args.k, random_state=42, n_init=10)
    cluster_ids = km.fit_predict(vecs).tolist()
    print(f"  K-means done. Cluster sizes: {sorted(Counter(cluster_ids).values(), reverse=True)}")

    # ── Category-based cluster labels ─────────────────────────────────────────
    # For each k-means cluster, majority-vote category becomes the label
    cluster_cats: dict[int, list[str]] = {i: [] for i in range(args.k)}
    for node_id, cluster in zip(ids, cluster_ids):
        cat = records[node_id].get("category", "unknown")
        cluster_cats[cluster].append(cat)

    # Label A: majority category per cluster
    labels_category = {}
    for c, cats in cluster_cats.items():
        top_cat, top_n = Counter(cats).most_common(1)[0]
        purity = top_n / len(cats)
        labels_category[c] = {
            "label": top_cat.replace("-", " ").title(),
            "top_category": top_cat,
            "purity": round(purity, 2),
            "size": len(cats),
            "breakdown": Counter(cats).most_common(5),
        }

    # ── LLM cluster names ─────────────────────────────────────────────────────
    # Sample 5 record names + descriptions per cluster, ask GPT to name it
    print("Generating k-means cluster names via GPT…")
    from openai import OpenAI  # type: ignore
    client = OpenAI()

    # Build cluster membership
    cluster_members: dict[int, list[str]] = {i: [] for i in range(args.k)}
    for node_id, cluster in zip(ids, cluster_ids):
        cluster_members[cluster].append(node_id)

    labels_kmeans = {}
    for c in range(args.k):
        members = cluster_members[c]
        # Sample up to 8 records for the prompt
        sample = members[:8]
        snippets = []
        for nid in sample:
            r = records[nid]
            desc = (r.get("description") or "")[:120]
            snippets.append(f"- {r['name']} ({r.get('category','')}): {desc}")
        prompt = (
            f"These {len(members)} AI/ML research items form a semantic cluster:\n"
            + "\n".join(snippets)
            + f"\n\nGive this cluster a concise, specific 2-5 word label that a researcher would recognize. "
            f"Return only the label, no explanation."
        )
        try:
            resp = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=20,
            )
            label = resp.choices[0].message.content.strip().strip('"\'')
        except Exception as e:
            label = labels_category[c]["label"]  # fallback
            print(f"  cluster {c} GPT error: {e}", file=sys.stderr)
        labels_kmeans[c] = {
            "label": label,
            "size": len(members),
            "breakdown": Counter(cluster_cats[c]).most_common(5),
        }
        print(f"  cluster {c:2d} ({len(members):3d} nodes): {label}")

    # ── Output ────────────────────────────────────────────────────────────────
    if args.dry_run:
        print("\nDry-run — not writing files.")
        return 0

    coords_out = {}
    for node_id, (x, y), cluster in zip(ids, coords_2d.tolist(), cluster_ids):
        coords_out[node_id] = {
            "x": round(x, 4),
            "y": round(y, 4),
            "cluster_k": cluster,
            "cluster_category": labels_category[cluster]["top_category"],
        }

    OUT_COORDS.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_COORDS, "w", encoding="utf-8") as f:
        json.dump(coords_out, f, ensure_ascii=False)
    print(f"\nWrote {len(coords_out)} coordinates → {OUT_COORDS}")

    label_output = {
        "k": args.k,
        "set_A_category": labels_category,
        "set_B_kmeans": labels_kmeans,
    }
    with open(OUT_LABELS, "w", encoding="utf-8") as f:
        json.dump(label_output, f, indent=2, ensure_ascii=False)
    print(f"Wrote cluster labels → {OUT_LABELS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
