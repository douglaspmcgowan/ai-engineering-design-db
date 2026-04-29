"""
fetch-abstracts.py — fetch real paper abstracts for academic-paper records.

Reads consolidated.jsonl, picks records of type academic-paper or
benchmark-dataset, and tries to fetch the actual abstract from:

  - arXiv API   (for arxiv.org URLs and 10.48550 DOIs)
  - OpenAlex    (for any other DOI; free, no key)

Writes graph/paper-abstracts.jsonl, one JSON object per line:
    {"id": "...", "source": "arxiv|openalex|none",
     "title": "...", "abstract": "...", "url": "..."}

The file is APPEND-ONLY across runs. On re-run, records that already
have an abstract are skipped. Records that previously failed (source=
"none") are retried only with --retry-failed.

Usage:
    python scripts/fetch-abstracts.py [--limit N] [--retry-failed]
                                       [--sleep 0.4]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from xml.etree import ElementTree as ET

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
CONSOLIDATED = ROOT / "consolidated.jsonl"
OUT_FILE = ROOT / "graph" / "paper-abstracts.jsonl"

ARXIV_API = "http://export.arxiv.org/api/query?id_list={id}&max_results=1"
OPENALEX_DOI = "https://api.openalex.org/works/doi:{doi}?mailto=douglaspmcgowan@gmail.com"
OPENALEX_TITLE = (
    "https://api.openalex.org/works?per-page=1"
    "&filter=display_name.search:{q}&mailto=douglaspmcgowan@gmail.com"
)
NS = {"a": "http://www.w3.org/2005/Atom"}
UA = "ai-engineering-design-db/1.0 (mailto:douglaspmcgowan@gmail.com)"

ARXIV_ID_RE = re.compile(r"(?:arxiv\.org/(?:abs|pdf)/|10\.48550/arxiv\.)([0-9]{4}\.[0-9]{4,5})", re.I)
DOI_RE = re.compile(r"(10\.\d{4,9}/[^\s\?#]+)", re.I)


def http_json(url: str, timeout: float = 15.0) -> dict | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"    http_json error: {type(e).__name__}: {e}", file=sys.stderr)
        return None


def http_text(url: str, timeout: float = 15.0) -> str | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"    http_text error: {type(e).__name__}: {e}", file=sys.stderr)
        return None


def reconstruct_abstract(inverted_index: dict | None) -> str:
    """OpenAlex ships abstracts as inverted indexes; rebuild a flat string."""
    if not inverted_index:
        return ""
    positions: dict[int, str] = {}
    for word, idxs in inverted_index.items():
        for i in idxs:
            positions[i] = word
    if not positions:
        return ""
    return " ".join(positions[i] for i in sorted(positions))


def fetch_arxiv(arxiv_id: str) -> dict | None:
    body = http_text(ARXIV_API.format(id=arxiv_id))
    if not body:
        return None
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return None
    entry = root.find("a:entry", NS)
    if entry is None:
        return None
    title_el = entry.find("a:title", NS)
    summary_el = entry.find("a:summary", NS)
    if title_el is None or summary_el is None:
        return None
    title = (title_el.text or "").strip().replace("\n", " ")
    abstract = (summary_el.text or "").strip().replace("\n", " ")
    abstract = re.sub(r"\s+", " ", abstract)
    if not abstract:
        return None
    return {"source": "arxiv", "title": title, "abstract": abstract,
            "url": f"https://arxiv.org/abs/{arxiv_id}"}


def fetch_openalex_doi(doi: str) -> dict | None:
    safe = urllib.parse.quote(doi, safe="")
    data = http_json(OPENALEX_DOI.format(doi=safe))
    if not data:
        return None
    abstract = reconstruct_abstract(data.get("abstract_inverted_index"))
    if not abstract:
        return None
    return {"source": "openalex", "title": data.get("title", ""),
            "abstract": abstract, "url": data.get("doi") or data.get("id", "")}


def fetch_openalex_title(name: str) -> dict | None:
    q = urllib.parse.quote(name)
    data = http_json(OPENALEX_TITLE.format(q=q))
    if not data:
        return None
    results = data.get("results") or []
    if not results:
        return None
    top = results[0]
    abstract = reconstruct_abstract(top.get("abstract_inverted_index"))
    if not abstract:
        return None
    # Sanity check: the result's title should overlap meaningfully with our name
    rec_title = (top.get("title") or "").lower()
    name_l = name.lower()
    # Require at least one 5+ char shared token
    name_tokens = {t for t in re.split(r"\W+", name_l) if len(t) >= 5}
    title_tokens = {t for t in re.split(r"\W+", rec_title) if len(t) >= 5}
    if name_tokens and not (name_tokens & title_tokens):
        return None
    return {"source": "openalex-title", "title": top.get("title", ""),
            "abstract": abstract, "url": top.get("doi") or top.get("id", "")}


def best_url(rec: dict) -> str:
    return (rec.get("url_paper") or rec.get("url_primary") or "").strip()


def fetch_one(rec: dict) -> dict:
    """Try arxiv first, then OpenAlex by DOI, then OpenAlex by title."""
    url = best_url(rec)
    # 1. arXiv ID embedded anywhere
    m = ARXIV_ID_RE.search(url)
    if m:
        out = fetch_arxiv(m.group(1))
        if out:
            return out
    # 2. DOI URL — strip query/anchor, send to OpenAlex
    if "doi.org" in url:
        m = DOI_RE.search(url)
        if m:
            doi = m.group(1).rstrip(".,;)")
            out = fetch_openalex_doi(doi)
            if out:
                return out
    # 3. Fallback: title search on OpenAlex
    name = rec.get("name", "")
    if len(name) >= 6:
        out = fetch_openalex_title(name)
        if out:
            return out
    return {"source": "none", "title": rec.get("name", ""), "abstract": "", "url": url}


def load_existing() -> dict[str, dict]:
    if not OUT_FILE.exists():
        return {}
    out: dict[str, dict] = {}
    for line in open(OUT_FILE, encoding="utf-8"):
        if not line.strip():
            continue
        try:
            r = json.loads(line)
            out[r["id"]] = r
        except Exception:
            continue
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None,
                    help="Process at most N records (testing)")
    ap.add_argument("--retry-failed", action="store_true",
                    help="Retry records previously cached as source=none")
    ap.add_argument("--sleep", type=float, default=0.4,
                    help="Seconds to sleep between API calls (default 0.4)")
    args = ap.parse_args()

    if not CONSOLIDATED.exists():
        print(f"missing {CONSOLIDATED}", file=sys.stderr)
        return 1

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    cache = load_existing()
    print(f"Cache loaded: {len(cache)} records, "
          f"{sum(1 for r in cache.values() if r.get('source') != 'none')} with abstracts")

    records = [json.loads(l) for l in open(CONSOLIDATED, encoding="utf-8") if l.strip()]
    targets = [r for r in records if r.get("type") in ("academic-paper", "benchmark-dataset")]
    print(f"Candidate papers: {len(targets)}")

    todo = []
    for r in targets:
        prev = cache.get(r["id"])
        if prev and prev.get("source") != "none":
            continue
        if prev and prev.get("source") == "none" and not args.retry_failed:
            continue
        todo.append(r)

    if args.limit:
        todo = todo[: args.limit]
    print(f"To fetch: {len(todo)}")

    # Append mode for incremental safety; we de-dupe by id when re-loading
    written = 0
    with open(OUT_FILE, "a", encoding="utf-8") as f:
        for i, rec in enumerate(todo, 1):
            print(f"  [{i}/{len(todo)}] {rec['id'][:60]}", end=" ... ", flush=True)
            result = fetch_one(rec)
            result["id"] = rec["id"]
            cache[rec["id"]] = result
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
            f.flush()
            written += 1
            print(f"{result['source']:>15s}  ({len(result['abstract'])}b)")
            time.sleep(args.sleep)

    # Compact: rewrite cache deduped (latest wins) so the file stays clean
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        for rid in sorted(cache):
            f.write(json.dumps(cache[rid], ensure_ascii=False) + "\n")

    got_abstract = sum(1 for r in cache.values() if r.get("source") != "none")
    print(f"\nFetched {written} new. Total in cache: {len(cache)}, "
          f"with abstracts: {got_abstract} ({100*got_abstract/max(1,len(cache)):.1f}%)")
    by_src: dict[str, int] = {}
    for r in cache.values():
        by_src[r.get("source", "?")] = by_src.get(r.get("source", "?"), 0) + 1
    for src, n in sorted(by_src.items(), key=lambda x: -x[1]):
        print(f"  {n:4d}  {src}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
