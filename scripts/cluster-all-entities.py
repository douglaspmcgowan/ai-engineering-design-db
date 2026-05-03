"""
cluster-all-entities.py — K-means cluster all 2405 nodes in the joint UMAP embedding.

Reads:  graph/embed-coords-all.json  (x, y per node-id)
Writes: graph/embed-coords-all.json  (adds cluster_k_all, cluster_label_all per entry)
        graph/cluster-labels-all.json (cluster_id → label dict)

Usage:
  python scripts/cluster-all-entities.py [--k 24]
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
EMBED_ALL  = ROOT / "graph" / "embed-coords-all.json"
LABELS_ALL = ROOT / "graph" / "cluster-labels-all.json"


# ── Helpers ───────────────────────────────────────────────────────────────────

def node_type_from_id(node_id: str) -> str:
    """Extract type prefix from node-id like 'project:foo' → 'Project'."""
    prefix = node_id.split(":")[0].lower()
    return {
        "project": "Project",
        "organization": "Organization",
        "category": "Category",
        "technique": "Technique",
        "modality": "Modality",
        "physicsdomain": "PhysicsDomain",
        "industry": "Industry",
        "year": "Year",
        "venue": "Venue",
        "person": "Person",
    }.get(prefix, prefix.title())


def cluster_label_from_members(node_ids: list[str]) -> str:
    """Generate a readable label for a cluster from its member node IDs."""
    type_counts: Counter = Counter(node_type_from_id(n) for n in node_ids)
    dominant_type, dominant_count = type_counts.most_common(1)[0]

    # For clusters dominated by a single type, describe by type + sample
    samples = [
        nid.split(":", 1)[1].replace("-", " ").title()
        for nid in node_ids
        if node_type_from_id(nid) == dominant_type
    ][:3]

    if dominant_count / len(node_ids) >= 0.6:
        return f"{dominant_type}s · {samples[0][:28]}" if samples else dominant_type
    # Mixed cluster: list top-2 types
    top2 = [t for t, _ in type_counts.most_common(2)]
    return " + ".join(top2)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=24,
                        help="Number of clusters (default: 24)")
    args = parser.parse_args()

    try:
        from sklearn.cluster import KMeans
    except ImportError:
        print("ERROR: scikit-learn not installed. Run: pip install scikit-learn")
        raise SystemExit(1)

    print(f"Loading {EMBED_ALL} …")
    coords: dict[str, dict] = json.loads(EMBED_ALL.read_text(encoding="utf-8"))
    ids = list(coords.keys())
    X = np.array([[coords[i]["x"], coords[i]["y"]] for i in ids], dtype=np.float32)
    print(f"  {len(ids)} nodes loaded.")

    k = args.k
    print(f"Running K-means with k={k} …")
    km = KMeans(n_clusters=k, random_state=42, n_init=10, max_iter=400)
    labels = km.fit_predict(X)
    print(f"  Inertia: {km.inertia_:.1f}")

    # Build cluster → member mapping
    clusters: defaultdict[int, list[str]] = defaultdict(list)
    for node_id, cluster_id in zip(ids, labels):
        clusters[int(cluster_id)].append(node_id)

    # Generate human-readable labels
    cluster_label_map: dict[int, str] = {}
    for cid, members in sorted(clusters.items()):
        cluster_label_map[cid] = cluster_label_from_members(members)

    # Patch coords dict
    for node_id, cluster_id in zip(ids, labels):
        cid = int(cluster_id)
        coords[node_id]["cluster_k_all"] = cid
        coords[node_id]["cluster_label_all"] = cluster_label_map[cid]

    # Write updated embed-coords-all.json
    EMBED_ALL.write_text(json.dumps(coords, ensure_ascii=False), encoding="utf-8")
    print(f"Updated {EMBED_ALL.name} with cluster_k_all / cluster_label_all")

    # Write cluster-labels-all.json
    label_output = {str(k): v for k, v in sorted(cluster_label_map.items())}
    LABELS_ALL.write_text(json.dumps(label_output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {LABELS_ALL.name}  ({len(label_output)} clusters)")

    # Summary
    for cid in sorted(clusters.keys()):
        members = clusters[cid]
        type_counts = Counter(node_type_from_id(n) for n in members)
        print(f"  Cluster {cid:2d} ({len(members):4d} nodes) — {cluster_label_map[cid]}  {dict(type_counts.most_common(3))}")


if __name__ == "__main__":
    main()
