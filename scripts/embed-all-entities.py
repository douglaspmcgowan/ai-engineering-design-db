"""
embed-all-entities.py — UMAP 2D projection for ALL graph nodes (Option B).

Unlike project-embeddings.py (projects only), this script embeds every node
type (Project, Organization, Category, Technique, Modality, PhysicsDomain,
Industry, Year, Venue, Person) in a joint embedding space, then runs UMAP on
all ~2405 nodes together. The resulting embed-coords.json covers the full graph
so embed mode can show every node type with semantic placement.

Pipeline:
  1. Load graph/graph-data.json (all node IDs + labels + props)
  2. Build a short text description per node based on type
  3. Embed all texts with sentence-transformers/all-MiniLM-L6-v2
     (or OpenAI text-embedding-3-small if --backend openai)
  4. Run UMAP(n_components=2, metric='cosine') on joint vector matrix
  5. Write graph/embed-coords-all.json — same format as embed-coords.json
     but keyed by FULL node ID (e.g. 'project:3d-gaussian-splatting',
     'category:generative-3d-shape')

After running, re-run build-graph.py to inject coords into graph-data.json.

Usage:
    python scripts/embed-all-entities.py [--backend sentence-transformers|openai]
    python scripts/embed-all-entities.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
GRAPH_DATA = ROOT / "graph" / "graph-data.json"
OUT_COORDS = ROOT / "graph" / "embed-coords-all.json"


# ── Text builder per node type ─────────────────────────────────────────────────

def build_text(node: dict) -> str:
    """Return a short embedding-ready string for any node type."""
    ntype = node.get("type", "")
    label = node.get("label", "").strip()
    props = node.get("props", {}) or {}

    if ntype == "Project":
        parts = [label]
        if props.get("organization"):
            parts.append(f"by {props['organization']}")
        if props.get("category"):
            parts.append(f"[{props['category']}]")
        if props.get("year"):
            parts.append(f"({props['year']})")
        desc = (props.get("description") or "")[:300]
        if desc:
            parts.append(desc)
        techniques = props.get("techniques") or []
        if techniques:
            parts.append("Techniques: " + ", ".join(techniques[:6]))
        return " ".join(p for p in parts if p)

    elif ntype == "Organization":
        return f"Organization: {label}"

    elif ntype == "Category":
        readable = label.replace("-", " ").title()
        return f"AI research category: {readable}"

    elif ntype == "Technique":
        readable = label.replace("-", " ").title()
        return f"AI/ML technique: {readable}"

    elif ntype == "Modality":
        readable = label.replace("-", " ").title()
        return f"Data modality: {readable}"

    elif ntype == "PhysicsDomain":
        readable = label.replace("-", " ").title()
        return f"Physics domain: {readable}"

    elif ntype == "Industry":
        readable = label.replace("-", " ").title()
        return f"Industry sector: {readable}"

    elif ntype == "Year":
        return f"Year {label}"

    elif ntype == "Venue":
        return f"Publication venue: {label}"

    elif ntype == "Person":
        count = props.get("count", "")
        suffix = f" ({count} papers)" if count else ""
        return f"Researcher: {label}{suffix}"

    else:
        return f"{ntype}: {label}"


# ── Embedding backends ─────────────────────────────────────────────────────────

def embed_sentence_transformers(texts: list[str]) -> tuple[str, list[list[float]]]:
    from sentence_transformers import SentenceTransformer  # type: ignore
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    print(f"Loading model {model_name}…")
    model = SentenceTransformer(model_name)
    vecs = model.encode(
        texts,
        show_progress_bar=True,
        batch_size=64,
        normalize_embeddings=True,
    )
    return model_name, vecs.tolist()


def embed_openai(texts: list[str]) -> tuple[str, list[list[float]]]:
    from openai import OpenAI  # type: ignore
    client = OpenAI()
    model_name = "text-embedding-3-small"
    out: list[list[float]] = []
    BATCH = 100
    for i in range(0, len(texts), BATCH):
        chunk = texts[i : i + BATCH]
        resp = client.embeddings.create(model=model_name, input=chunk)
        out.extend(d.embedding for d in resp.data)
        print(f"  embedded {min(i + BATCH, len(texts))}/{len(texts)}")
    return model_name, out


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--backend",
        default="sentence-transformers",
        choices=["sentence-transformers", "openai"],
    )
    ap.add_argument("--neighbors", type=int, default=15,
                    help="UMAP n_neighbors (default 15)")
    ap.add_argument("--min-dist", type=float, default=0.08,
                    help="UMAP min_dist (default 0.08)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Embed + UMAP but don't write output file")
    args = ap.parse_args()

    # Load graph data
    if not GRAPH_DATA.exists():
        print(f"Missing {GRAPH_DATA} — run build-graph.py first", file=sys.stderr)
        return 1

    with open(GRAPH_DATA, encoding="utf-8") as f:
        gdata = json.load(f)

    nodes = gdata["nodes"]
    print(f"Loaded {len(nodes)} nodes from graph-data.json")

    # Count by type
    from collections import Counter
    type_counts = Counter(n["type"] for n in nodes)
    for t, c in sorted(type_counts.items()):
        print(f"  {t}: {c}")

    # Build texts
    ids = [n["id"] for n in nodes]
    texts = [build_text(n) for n in nodes]

    # Sanity check
    empty = sum(1 for t in texts if not t.strip())
    if empty:
        print(f"Warning: {empty} nodes produced empty text", file=sys.stderr)

    # Embed
    print(f"\nEmbedding {len(texts)} texts with backend={args.backend}…")
    if args.backend == "sentence-transformers":
        try:
            model_name, vectors = embed_sentence_transformers(texts)
        except ImportError:
            print("sentence-transformers not installed, falling back to openai",
                  file=sys.stderr)
            model_name, vectors = embed_openai(texts)
    else:
        model_name, vectors = embed_openai(texts)

    print(f"  ✓ {len(vectors)} vectors ({len(vectors[0])}-dim) via {model_name}")

    # UMAP
    import numpy as np  # type: ignore
    arr = np.array(vectors, dtype=np.float32)

    print(f"\nRunning UMAP (n={len(arr)}, neighbors={args.neighbors}, "
          f"min_dist={args.min_dist})…")
    import umap  # type: ignore
    reducer = umap.UMAP(
        n_components=2,
        n_neighbors=args.neighbors,
        min_dist=args.min_dist,
        metric="cosine",
        random_state=42,
        verbose=False,
    )
    coords_2d = reducer.fit_transform(arr)
    xs, ys = coords_2d[:, 0], coords_2d[:, 1]
    print(f"  ✓ UMAP done. x∈[{xs.min():.2f},{xs.max():.2f}]  "
          f"y∈[{ys.min():.2f},{ys.max():.2f}]")

    if args.dry_run:
        print("\nDry-run — skipping file write.")
        return 0

    # Write output — keyed by full node ID
    coords_out: dict[str, dict] = {}
    for node_id, (x, y) in zip(ids, coords_2d.tolist()):
        coords_out[node_id] = {
            "x": round(x, 4),
            "y": round(y, 4),
        }

    OUT_COORDS.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_COORDS, "w", encoding="utf-8") as f:
        json.dump(coords_out, f, ensure_ascii=False)
    print(f"\n✓ Wrote {len(coords_out)} coordinates → {OUT_COORDS.name}")
    print("\nNext steps:")
    print("  1. Inspect embed-coords-all.json (should have all node types)")
    print("  2. Update build-graph.py to inject coords for non-Project nodes too")
    print("  3. Run: python scripts/build-graph.py")
    print("  4. The explorer embed mode will then show all node types")

    return 0


if __name__ == "__main__":
    sys.exit(main())
