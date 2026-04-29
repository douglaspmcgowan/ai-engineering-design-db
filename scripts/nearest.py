"""
nearest.py — k-nearest-neighbour utility over embeddings.jsonl.

Usage:
    python scripts/nearest.py "deepcad"          # find k nearest to that record
    python scripts/nearest.py --query "neural CFD surrogate"  # query string
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "consolidated.jsonl"
EMB = ROOT / "embeddings.jsonl"


def load() -> tuple[list[dict], np.ndarray, dict[str, int]]:
    records = [json.loads(l) for l in open(DB, encoding="utf-8") if l.strip()]
    vecs = []
    id2idx: dict[str, int] = {}
    by_id_emb: dict[str, list[float]] = {}
    for line in open(EMB, encoding="utf-8"):
        if not line.strip():
            continue
        e = json.loads(line)
        by_id_emb[e["id"]] = e["vector"]
    for i, r in enumerate(records):
        if r["id"] in by_id_emb:
            vecs.append(by_id_emb[r["id"]])
            id2idx[r["id"]] = i
    arr = np.array(vecs, dtype=np.float32)
    # Normalize for cosine
    arr = arr / (np.linalg.norm(arr, axis=1, keepdims=True) + 1e-12)
    return records, arr, id2idx


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("target", nargs="?", help="record id to find neighbours of")
    p.add_argument("--query", help="free-text query (requires backend)")
    p.add_argument("-k", type=int, default=10)
    args = p.parse_args()

    records, vecs, id2idx = load()
    if args.target:
        if args.target not in id2idx:
            print(f"id not found: {args.target}", file=sys.stderr)
            return 1
        i = id2idx[args.target]
        sims = vecs @ vecs[i]
        top = np.argsort(-sims)[: args.k + 1]
        for j in top:
            if j == i:
                continue
            r = records[j]
            print(f"  {sims[j]:.3f}  {r['id']:40s}  {r.get('category', '?')}")
    elif args.query:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore

            m = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            q = m.encode([args.query], normalize_embeddings=True)[0]
        except ImportError:
            print("install sentence-transformers for --query", file=sys.stderr)
            return 1
        sims = vecs @ q
        top = np.argsort(-sims)[: args.k]
        for j in top:
            r = records[j]
            print(f"  {sims[j]:.3f}  {r['id']:40s}  {r.get('name')}")
    else:
        p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
