"""
extract-semantic-edges.py — Pass B: inferred edges for the knowledge graph.

Pass 1 — SEMANTICALLY_NEAR (cosine similarity)
  Load embeddings.jsonl, compute all-pairs cosine similarity, emit edges
  for pairs with similarity >= tau (default 0.82).

Pass 2 — CITES / BUILT_ON / BENCHMARKED_AGAINST (GPT-4.1-mini)
  For each project, send its description + top-20 nearest-neighbor names to
  GPT-4.1-mini. Extract named relationships. Match to known project IDs.
  Uses batching to stay cheap (<$0.20 for 560 records).

Output:
  graph/semantic-edges.csv  — source, target, type, weight, evidence

Usage:
  python scripts/extract-semantic-edges.py [--tau 0.82] [--skip-llm] [--limit N]
  python scripts/extract-semantic-edges.py --skip-cosine   # LLM only
  python scripts/extract-semantic-edges.py --dry-run       # print cost estimate
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path

import numpy as np  # type: ignore

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
CONSOLIDATED = ROOT / "consolidated.jsonl"
EMBEDDINGS = ROOT / "embeddings.jsonl"
OUT_FILE = ROOT / "graph" / "semantic-edges.csv"


# ── Helpers ──────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    s = str(text).lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")[:80]


def node_id(record: dict) -> str:
    return f"project:{record['id']}"


def load_records() -> list[dict]:
    return [json.loads(l) for l in open(CONSOLIDATED, encoding="utf-8") if l.strip()]


def load_embeddings(records: list[dict]) -> tuple[np.ndarray, list[str]]:
    """Returns (matrix of L2-normed vectors, list of record ids in matrix order)."""
    by_id: dict[str, list[float]] = {}
    for line in open(EMBEDDINGS, encoding="utf-8"):
        if not line.strip():
            continue
        e = json.loads(line)
        by_id[e["id"]] = e["vector"]

    ids, vecs = [], []
    for r in records:
        if r["id"] in by_id:
            ids.append(r["id"])
            vecs.append(by_id[r["id"]])

    arr = np.array(vecs, dtype=np.float32)
    norms = np.linalg.norm(arr, axis=1, keepdims=True) + 1e-12
    return arr / norms, ids


# ── Pass 1: cosine similarity ─────────────────────────────────────────────────

def cosine_edges(
    vecs: np.ndarray,
    ids: list[str],
    id_to_rec: dict[str, dict],
    tau: float,
) -> list[dict]:
    """Return SEMANTICALLY_NEAR edges for all pairs with cosine >= tau."""
    edges = []
    # Matrix multiply gives all-pairs cosine (vectors are already L2-normed)
    sim = vecs @ vecs.T
    n = len(ids)
    for i in range(n):
        for j in range(i + 1, n):
            s = float(sim[i, j])
            if s >= tau:
                edges.append({
                    "source": f"project:{ids[i]}",
                    "target": f"project:{ids[j]}",
                    "type": "SEMANTICALLY_NEAR",
                    "weight": round(s, 4),
                    "evidence": f"cosine={s:.3f}",
                })
    return edges


# ── Pass 2: LLM extraction ───────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You extract relationships between AI research projects. Given a project and a list of
candidate projects, return a JSON array of objects with keys:
  "target"   — exact name from the candidate list
  "type"     — one of: CITES, BUILT_ON, BENCHMARKED_AGAINST
  "evidence" — a short quoted phrase from the description (max 20 words)

CITES: the description references or mentions the target as prior work.
BUILT_ON: the project is explicitly built on, extends, or uses the target as a component.
BENCHMARKED_AGAINST: the project is compared against or outperforms the target.

Return [] if no relationships apply. Return only valid JSON, no markdown.\
"""

def llm_prompt(rec: dict, candidates: list[dict]) -> str:
    names = "\n".join(f"- {c['name']}" for c in candidates)
    return (
        f"Project: {rec['name']} ({rec.get('year', '?')})\n"
        f"Organization: {rec.get('organization', '?')}\n"
        f"Description: {rec.get('description', '')}\n\n"
        f"Candidate projects:\n{names}"
    )


def _call_with_retry(client, system_prompt: str, user_msg: str, max_retries: int = 3):
    """OpenAI call with exponential backoff on transient errors."""
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0,
                max_tokens=512,
                response_format={"type": "json_object"},
            )
        except Exception as e:
            last_err = e
            msg = str(e).lower()
            # Retry only on transient errors
            if any(s in msg for s in ("connection", "timeout", "rate", "503", "502", "504")):
                time.sleep(1.5 * (attempt + 1))
                continue
            raise
    raise last_err  # type: ignore


def _match_target(tgt_name: str, name_to_id: dict[str, str]) -> str | None:
    """Match an LLM-emitted name to a known project id.
    Word-boundary match avoids 'GPT' matching 'GPT-4', 'FNO' matching 'F-FNO', etc.
    """
    if not tgt_name:
        return None
    key = tgt_name.lower().strip()
    # 1) exact match
    if key in name_to_id:
        return name_to_id[key]
    # 2) word-boundary regex: target name is a whole-word substring of candidate name
    pattern = re.compile(r"\b" + re.escape(key) + r"\b", re.IGNORECASE)
    for name, nid in name_to_id.items():
        if pattern.search(name):
            return nid
    return None


def llm_extract(
    records: list[dict],
    vecs: np.ndarray,
    vec_ids: list[str],
    id_to_rec: dict[str, dict],
    limit: int | None,
) -> list[dict]:
    from openai import OpenAI  # type: ignore

    client = OpenAI()
    # GPT-4.1-mini supports JSON mode; wrap the system prompt to require an object
    sys_prompt = SYSTEM_PROMPT + (
        '\n\nReturn a JSON object: {"edges": [{...}, ...]}. '
        'If no relationships, return {"edges": []}.'
    )
    sim = vecs @ vecs.T

    id_to_idx = {rid: i for i, rid in enumerate(vec_ids)}
    edges: list[dict] = []
    name_to_id: dict[str, str] = {r["name"].lower(): r["id"] for r in records}

    targets = records[:limit] if limit else records
    total = len(targets)
    print(f"  LLM pass: {total} records via GPT-4.1-mini...")

    for i, rec in enumerate(targets):
        if rec["id"] not in id_to_idx:
            continue
        idx = id_to_idx[rec["id"]]
        sims = sim[idx].copy()
        sims[idx] = -1
        top_idxs = np.argsort(-sims)[:20]
        candidates = [id_to_rec[vec_ids[j]] for j in top_idxs if vec_ids[j] in id_to_rec]

        user_msg = llm_prompt(rec, candidates)
        try:
            resp = _call_with_retry(client, sys_prompt, user_msg)
            raw = resp.choices[0].message.content.strip()
            obj = json.loads(raw)
            rels = obj.get("edges", []) if isinstance(obj, dict) else obj
        except Exception as e:
            print(f"    [{i+1}/{total}] {rec['id']}: error after retries - {e}", file=sys.stderr)
            continue

        src = f"project:{rec['id']}"
        for rel in rels or []:
            tgt_id = _match_target(rel.get("target", ""), name_to_id)
            if tgt_id and tgt_id != rec["id"]:
                edges.append({
                    "source": src,
                    "target": f"project:{tgt_id}",
                    "type": rel.get("type", "CITES"),
                    "weight": 1.0,
                    "evidence": rel.get("evidence", "llm-extracted"),
                })

        if (i + 1) % 50 == 0:
            print(f"    {i+1}/{total} done, {len(edges)} edges so far")

    return edges


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--tau", type=float, default=0.82,
                   help="Cosine similarity threshold for SEMANTICALLY_NEAR (default 0.82)")
    p.add_argument("--skip-cosine", action="store_true")
    p.add_argument("--skip-llm", action="store_true")
    p.add_argument("--limit", type=int, default=None,
                   help="Limit LLM pass to first N records (for testing)")
    p.add_argument("--dry-run", action="store_true",
                   help="Print cost estimate and exit")
    args = p.parse_args()

    records = load_records()
    id_to_rec = {r["id"]: r for r in records}
    print(f"Loaded {len(records)} records")

    vecs, vec_ids = load_embeddings(records)
    print(f"Loaded {len(vec_ids)} embeddings ({vecs.shape[1]}-dim)")

    if args.dry_run:
        # Rough token estimate
        avg_desc_tokens = 200
        candidate_tokens = 20 * 8  # 20 names * ~8 tokens each
        tokens_per_record = avg_desc_tokens + candidate_tokens + 100  # system + overhead
        total_input_tokens = len(records) * tokens_per_record
        cost_input = total_input_tokens / 1_000_000 * 0.40  # $0.40/M input
        cost_output = len(records) * 60 / 1_000_000 * 1.60  # ~60 output tokens avg
        print(f"\nDry-run cost estimate for {len(records)} records with GPT-4.1-mini:")
        print(f"  Input tokens:  ~{total_input_tokens:,}  (${cost_input:.3f})")
        print(f"  Output tokens: ~{len(records)*60:,}  (${cost_output:.3f})")
        print(f"  Total estimate: ~${cost_input + cost_output:.2f}")
        return 0

    all_edges: list[dict] = []

    # Pass 1: cosine
    if not args.skip_cosine:
        print(f"\nPass 1: cosine similarity (tau={args.tau})...")
        cosine = cosine_edges(vecs, vec_ids, id_to_rec, args.tau)
        print(f"  Found {len(cosine)} SEMANTICALLY_NEAR edges")
        all_edges.extend(cosine)

    # Pass 2: LLM
    if not args.skip_llm:
        print("\nPass 2: LLM extraction (GPT-4.1-mini)...")
        llm = llm_extract(records, vecs, vec_ids, id_to_rec, args.limit)
        # Deduplicate by (source, target, type)
        seen: set[tuple] = set()
        for e in llm:
            key = (e["source"], e["target"], e["type"])
            if key not in seen:
                seen.add(key)
                all_edges.append(e)
        print(f"  Found {len(llm)} raw LLM edges -> {len(seen)} unique")

    # Write output
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["source", "target", "type", "weight", "evidence"])
        w.writeheader()
        w.writerows(all_edges)

    print(f"\nWrote {len(all_edges)} semantic edges to {OUT_FILE}")

    # Summary
    from collections import Counter
    counts = Counter(e["type"] for e in all_edges)
    for t, c in counts.most_common():
        print(f"  {t}: {c}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
