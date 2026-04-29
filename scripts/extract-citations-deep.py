"""
extract-citations-deep.py — second-pass LLM citation extraction using REAL paper
abstracts (from fetch-abstracts.py) instead of our internal descriptions.

For every record that has a fetched abstract, build a prompt with:
  - the abstract (the source of citation language)
  - the top-K nearest neighbors (by embedding cosine) as candidate targets,
    each with their canonical name + a 1-line "card" so the model can ground

Send to GPT-4.1-mini, parse JSON, write CITES / BUILT_ON / BENCHMARKED_AGAINST
edges to graph/deep-citations.csv.

build-graph.py auto-loads any *.csv that we add to its merge list, so this
file is folded into graph-data.json on next rebuild.

Usage:
    python scripts/extract-citations-deep.py [--limit N] [--dry-run]
                                              [--top-k 25]
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
ABSTRACTS = ROOT / "graph" / "paper-abstracts.jsonl"
OUT_FILE = ROOT / "graph" / "deep-citations.csv"


SYSTEM_PROMPT = """\
You extract citation relationships from a research paper's abstract.

Input: one paper's abstract + a list of candidate prior works (with short cards).
Output: a JSON object {"edges": [{"target": "...", "type": "...", "evidence": "..."}, ...]}.

type ∈ {CITES, BUILT_ON, BENCHMARKED_AGAINST}
  CITES                — abstract names the target as prior work or motivation.
  BUILT_ON             — paper EXPLICITLY extends, fine-tunes, or uses the target
                         as a component (e.g. "we extend FNO by...", "based on PINN").
  BENCHMARKED_AGAINST  — paper compares against / outperforms / matches the target
                         (e.g. "outperforms DeepONet", "compared with U-Net").

Rules:
- The target name MUST be copied EXACTLY from the candidate list — no paraphrasing.
- evidence = a short quoted phrase from the abstract (≤ 25 words). Do NOT paraphrase.
- Do not invent relationships not supported by explicit abstract text.
- Do not include the paper itself as its own target.
- Return {"edges": []} if no explicit citation appears.
"""


def slugify(text: str) -> str:
    s = str(text).lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")[:80]


def load_records() -> list[dict]:
    return [json.loads(l) for l in open(CONSOLIDATED, encoding="utf-8") if l.strip()]


def load_abstracts() -> dict[str, str]:
    if not ABSTRACTS.exists():
        return {}
    out: dict[str, str] = {}
    for line in open(ABSTRACTS, encoding="utf-8"):
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        ab = (r.get("abstract") or "").strip()
        if ab:
            out[r["id"]] = ab
    return out


def load_embeddings(records: list[dict]) -> tuple[np.ndarray, list[str]]:
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


def candidate_card(rec: dict) -> str:
    """A one-line card the LLM can use to disambiguate target candidates."""
    bits = [rec["name"]]
    yr = rec.get("year")
    org = rec.get("organization")
    if yr or org:
        bits.append(f"({org or '?'} {yr or '?'})")
    cat = rec.get("category", "")
    if cat:
        bits.append(f"[{cat}]")
    return " ".join(bits)


def build_prompt(rec: dict, abstract: str, candidates: list[dict]) -> str:
    cand_lines = "\n".join(f"  - {c['name']}  ::  {candidate_card(c)}" for c in candidates)
    return (
        f"PAPER: {rec['name']}  ({rec.get('organization', '?')} {rec.get('year', '?')})\n\n"
        f"ABSTRACT:\n{abstract}\n\n"
        f"CANDIDATE PRIOR WORKS (use exact names from the left side of '::'):\n"
        f"{cand_lines}\n\n"
        f"Return only the JSON object."
    )


def call_with_retry(client, sys_msg: str, user_msg: str, max_retries: int = 3):
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0,
                max_tokens=600,
                response_format={"type": "json_object"},
            )
        except Exception as e:
            last_err = e
            if any(s in str(e).lower() for s in
                   ("connection", "timeout", "rate", "503", "502", "504")):
                time.sleep(1.5 * (attempt + 1))
                continue
            raise
    raise last_err  # type: ignore


def match_target(name: str, name_to_id: dict[str, str]) -> str | None:
    if not name:
        return None
    key = name.lower().strip()
    if key in name_to_id:
        return name_to_id[key]
    pattern = re.compile(r"\b" + re.escape(key) + r"\b", re.IGNORECASE)
    for cand_name, cid in name_to_id.items():
        if pattern.search(cand_name):
            return cid
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--top-k", type=int, default=25,
                    help="Number of candidate targets per paper (default 25)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    records = load_records()
    id_to_rec = {r["id"]: r for r in records}
    abstracts = load_abstracts()
    print(f"Loaded {len(records)} records, {len(abstracts)} abstracts")

    targets = [r for r in records if r["id"] in abstracts]
    if args.limit:
        targets = targets[: args.limit]
    print(f"Targets with abstracts to process: {len(targets)}")

    # Cost estimate
    if args.dry_run:
        avg_input = 600  # abstract + cards
        avg_output = 120
        in_cost = len(targets) * avg_input / 1_000_000 * 0.40
        out_cost = len(targets) * avg_output / 1_000_000 * 1.60
        print(f"\nDry-run cost estimate ({len(targets)} records, gpt-4.1-mini):")
        print(f"  Input  ~{len(targets)*avg_input:,} tok  (${in_cost:.3f})")
        print(f"  Output ~{len(targets)*avg_output:,} tok (${out_cost:.3f})")
        print(f"  Total: ${in_cost + out_cost:.2f}")
        return 0

    vecs, vec_ids = load_embeddings(records)
    sim = vecs @ vecs.T
    id_to_idx = {rid: i for i, rid in enumerate(vec_ids)}
    name_to_id = {r["name"].lower(): r["id"] for r in records}

    from openai import OpenAI  # type: ignore
    client = OpenAI()

    edges: list[dict] = []
    written = 0
    for i, rec in enumerate(targets, 1):
        if rec["id"] not in id_to_idx:
            continue
        idx = id_to_idx[rec["id"]]
        sims = sim[idx].copy()
        sims[idx] = -1
        top = np.argsort(-sims)[: args.top_k]
        cand_recs = [id_to_rec[vec_ids[j]] for j in top if vec_ids[j] in id_to_rec]
        if not cand_recs:
            continue

        prompt = build_prompt(rec, abstracts[rec["id"]], cand_recs)
        try:
            resp = call_with_retry(client, SYSTEM_PROMPT, prompt)
            obj = json.loads(resp.choices[0].message.content.strip())
            rels = obj.get("edges", []) if isinstance(obj, dict) else obj
        except Exception as e:
            print(f"  [{i}/{len(targets)}] {rec['id']}: error - {e}", file=sys.stderr)
            continue

        src = f"project:{rec['id']}"
        for rel in rels or []:
            tgt_id = match_target(rel.get("target", ""), name_to_id)
            if not tgt_id or tgt_id == rec["id"]:
                continue
            etype = rel.get("type", "CITES")
            if etype not in ("CITES", "BUILT_ON", "BENCHMARKED_AGAINST"):
                continue
            edges.append({
                "source":   src,
                "target":   f"project:{tgt_id}",
                "type":     etype,
                "weight":   1.0,
                "evidence": (rel.get("evidence", "") or "abstract-derived")[:200],
            })

        if i % 25 == 0:
            print(f"  {i}/{len(targets)} processed, {len(edges)} edges so far")

        written += 1

    # Dedupe by (source, target, type) — keep the longest evidence
    by_key: dict[tuple[str, str, str], dict] = {}
    for e in edges:
        k = (e["source"], e["target"], e["type"])
        if k not in by_key or len(e["evidence"]) > len(by_key[k]["evidence"]):
            by_key[k] = e

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["source", "target", "type", "weight", "evidence"])
        w.writeheader()
        w.writerows(by_key.values())

    print(f"\nProcessed {written} papers, wrote {len(by_key)} unique deep-citation edges")
    counts: dict[str, int] = {}
    for e in by_key.values():
        counts[e["type"]] = counts.get(e["type"], 0) + 1
    for t, c in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {t}: {c}")
    print(f"\nWrote: {OUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
