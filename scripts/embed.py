"""
embed.py — generate embeddings for each record in consolidated.jsonl.

Default backend: OpenAI text-embedding-3-large (3072-dim, requires OPENAI_API_KEY).
Falls back to sentence-transformers if --backend sentence-transformers is passed
or if OPENAI_API_KEY is not set.

Output: embeddings.jsonl with one line per record:
    {"id": "...", "model": "...", "dim": 3072, "vector": [...]}

Usage:
    python scripts/embed.py [--backend openai|sentence-transformers]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IN_FILE = ROOT / "consolidated.jsonl"
OUT_FILE = ROOT / "embeddings.jsonl"

OPENAI_EMBED_MODEL = "text-embedding-3-large"


def build_text(rec: dict) -> str:
    """Compose the embedding input from the record."""
    parts = [rec.get("name", "")]
    if rec.get("organization"):
        parts.append(f"by {rec['organization']}")
    if rec.get("category"):
        parts.append(f"[{rec['category']}]")
    if rec.get("year"):
        parts.append(f"({rec['year']})")
    parts.append(rec.get("description", ""))
    if rec.get("techniques"):
        parts.append("Techniques: " + ", ".join(rec["techniques"]))
    if rec.get("physics_domain"):
        parts.append(f"Physics: {rec['physics_domain']}")
    if rec.get("input_modality") or rec.get("output_modality"):
        parts.append(
            f"Modality: {rec.get('input_modality', '?')} -> {rec.get('output_modality', '?')}"
        )
    return " ".join(p for p in parts if p)


def load_records() -> list[dict]:
    if not IN_FILE.exists():
        print(f"missing {IN_FILE} — run consolidate.py first", file=sys.stderr)
        sys.exit(1)
    out = []
    with open(IN_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def embed_openai(records: list[dict]) -> tuple[str, int, list[list[float]]]:
    from openai import OpenAI  # type: ignore

    client = OpenAI()
    texts = [build_text(r) for r in records]
    out: list[list[float]] = []
    BATCH = 100
    for i in range(0, len(texts), BATCH):
        chunk = texts[i : i + BATCH]
        resp = client.embeddings.create(model=OPENAI_EMBED_MODEL, input=chunk)
        out.extend(d.embedding for d in resp.data)
        print(f"  embedded {i + len(chunk)}/{len(texts)}")
    dim = len(out[0]) if out else 0
    return OPENAI_EMBED_MODEL, dim, out


def embed_sentence_transformers(records: list[dict]) -> tuple[str, int, list[list[float]]]:
    from sentence_transformers import SentenceTransformer  # type: ignore

    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    model = SentenceTransformer(model_name)
    texts = [build_text(r) for r in records]
    vectors = model.encode(texts, show_progress_bar=True, batch_size=32, normalize_embeddings=True)
    return model_name, vectors.shape[1], vectors.tolist()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--backend",
        default="openai",
        choices=["openai", "sentence-transformers"],
    )
    args = p.parse_args()

    records = load_records()
    print(f"Loaded {len(records)} records")

    if args.backend == "openai":
        if not os.environ.get("OPENAI_API_KEY"):
            print("OPENAI_API_KEY not set; falling back to sentence-transformers", file=sys.stderr)
            model_name, dim, vectors = embed_sentence_transformers(records)
        else:
            model_name, dim, vectors = embed_openai(records)
    else:
        try:
            model_name, dim, vectors = embed_sentence_transformers(records)
        except ImportError:
            print("sentence-transformers not installed; falling back to openai", file=sys.stderr)
            model_name, dim, vectors = embed_openai(records)

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        for rec, vec in zip(records, vectors):
            f.write(
                json.dumps(
                    {"id": rec["id"], "model": model_name, "dim": dim, "vector": vec}
                )
                + "\n"
            )
    print(f"Wrote {len(records)} embeddings ({dim}-dim) to {OUT_FILE.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
