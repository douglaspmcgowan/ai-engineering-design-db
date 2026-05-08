"""Citation monitor — Semantic Scholar API.

For every arXiv paper already in consolidated.jsonl, polls Semantic Scholar
for papers that *cite* it and emits new citing papers as candidate pipeline
entries.  Tracks seen Semantic Scholar paper IDs in state.json under the key
"citation_seen_ids" so we never surface the same citing paper twice.

Rate limit: Semantic Scholar public API allows ~1 req/s unauthenticated.
We cap at 40 papers per run (~40s) so the CI step stays well under 5 min.
Set the env var S2_API_KEY to get 10 req/s and a larger cap.

Usage:
    python -m pipeline.run --source citations        # run standalone
    python -m pipeline.run --source citations --dry-run
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CONSOLIDATED = ROOT / "consolidated.jsonl"
STATE_FILE = ROOT / "pipeline" / "state.json"

S2_BASE = "https://api.semanticscholar.org/graph/v1"
CITATION_FIELDS = "title,year,externalIds,url,abstract,authors,venue,publicationTypes"

# Hard cap on papers we poll per run (unauthenticated = ~1 req/s).
MAX_PAPERS_PER_RUN = 40
CITATIONS_PER_PAPER = 50   # S2 max per request is 100; 50 is plenty for fresh runs

# Only include citing papers that feel relevant to AI+engineering design.
_RELEVANCE_RE = re.compile(
    r"cad|generative design|topology optim|neural operator|physics.informed"
    r"|diffusion|b.rep|brep|implicit model|sketch|parametric|additive manufactur"
    r"|3d shape|mesh generation|geometry|design automation|shape generat"
    r"|manufacturing|structural optimiz|inverse design",
    re.I,
)

# arXiv ID pattern in URLs — matches new-style IDs (YYMM.NNNNN)
_ARXIV_URL_RE = re.compile(r"arxiv\.org/abs/([0-9]{4}\.[0-9]{4,5})")


# ─────────────────────────────────────────────────────────────────────────────
# State helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_seen_ids() -> set[str]:
    if not STATE_FILE.exists():
        return set()
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            state = json.load(f)
        return set(state.get("citation_seen_ids", []))
    except Exception:
        return set()


def _save_seen_ids(seen: set[str]) -> None:
    """Merge citation_seen_ids into state.json without touching other keys."""
    existing: dict = {}
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            pass
    existing["citation_seen_ids"] = sorted(seen)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# Extract arxiv IDs from consolidated.jsonl
# ─────────────────────────────────────────────────────────────────────────────

def _get_arxiv_ids() -> list[str]:
    """Return unique arxiv IDs from all paper records in consolidated.jsonl."""
    if not CONSOLIDATED.exists():
        return []
    ids: set[str] = set()
    with open(CONSOLIDATED, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            # Explicit field — coerce None to "" to avoid AttributeError on .split()
            arxiv_id: str = rec.get("arxiv_id") or ""
            if arxiv_id:
                ids.add(arxiv_id.split("v")[0].strip())
                continue
            # Scan URL fields — schema uses url_paper, url_primary; also handle url/link
            for field in ("url_paper", "url_primary", "url", "link"):
                raw = rec.get(field) or ""  # coerce None to ""
                m = _ARXIV_URL_RE.search(raw)
                if m:
                    ids.add(m.group(1))
                    break
    return list(ids)


# ─────────────────────────────────────────────────────────────────────────────
# Semantic Scholar API helpers
# ─────────────────────────────────────────────────────────────────────────────

def _build_headers() -> dict[str, str]:
    headers: dict[str, str] = {"User-Agent": "ai-eng-design-db/1.0"}
    api_key = os.environ.get("S2_API_KEY", "")
    if api_key:
        headers["x-api-key"] = api_key
    return headers


def _fetch_citations(arxiv_id: str) -> list[dict]:
    url = (
        f"{S2_BASE}/paper/arXiv:{arxiv_id}/citations"
        f"?fields={CITATION_FIELDS}&limit={CITATIONS_PER_PAPER}"
    )
    headers = _build_headers()
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code in (404, 400):
            return []  # paper not in S2 index — silently skip
        print(f"    [citation_monitor] HTTP {e.code} for arXiv:{arxiv_id}")
        return []
    except Exception as e:
        print(f"    [citation_monitor] error for arXiv:{arxiv_id}: {e}")
        return []
    return [item.get("citingPaper", {}) for item in data.get("data", [])]


# ─────────────────────────────────────────────────────────────────────────────
# Record conversion
# ─────────────────────────────────────────────────────────────────────────────

def _paper_to_record(paper: dict, cited_arxiv_id: str) -> dict | None:
    title = (paper.get("title") or "").strip()
    if not title:
        return None

    abstract = (paper.get("abstract") or "").strip()
    # Relevance filter — only emit papers touching our domain
    haystack = f"{title} {abstract}"
    if not _RELEVANCE_RE.search(haystack):
        return None

    ext = paper.get("externalIds") or {}
    url = paper.get("url") or ""
    if ext.get("ArXiv"):
        url = f"https://arxiv.org/abs/{ext['ArXiv']}"
    elif ext.get("DOI"):
        url = f"https://doi.org/{ext['DOI']}"

    year = paper.get("year") or ""
    authors = [a.get("name", "") for a in (paper.get("authors") or [])]
    venue = (paper.get("venue") or "").strip()
    s2_id = paper.get("paperId") or ""

    return {
        # Use the S2 paper ID as the record's canonical ID so run.py dedup
        # is exact (slug-on-title collides for short generic titles).
        "id": f"s2-{s2_id}" if s2_id else "",
        "name": title,
        "entry_type": "paper",
        "year": str(year) if year else "",
        "url_paper": url,
        "description": abstract[:600] if abstract else "",
        "venue": venue,
        "authors": authors[:4],
        "tags": [f"cites:arxiv:{cited_arxiv_id}", "citation-monitor"],
        "source": "semantic-scholar-citation",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def fetch() -> list[dict]:
    """Return new citing papers not yet in the inbox or consolidated.jsonl."""
    seen = _load_seen_ids()
    arxiv_ids = _get_arxiv_ids()
    total = len(arxiv_ids)
    cap = min(total, MAX_PAPERS_PER_RUN)
    print(f"  citation_monitor: {total} arXiv papers found; polling first {cap}")

    # Sort descending by arXiv ID numeric value so freshest papers come first.
    # Use tuple sort: (YYMM-part, sequence) so we handle IDs correctly.
    def _arxiv_sort_key(aid: str) -> tuple[int, int]:
        parts = aid.split(".")
        try:
            return (int(parts[0]), int(parts[1])) if len(parts) == 2 else (0, 0)
        except ValueError:
            return (0, 0)

    arxiv_ids.sort(key=_arxiv_sort_key, reverse=True)

    api_key = os.environ.get("S2_API_KEY", "")
    delay = 0.15 if api_key else 1.1   # authenticated → 10 req/s, else ~1 req/s

    records: list[dict] = []
    for i, arxiv_id in enumerate(arxiv_ids[:cap]):
        citations = _fetch_citations(arxiv_id)
        for paper in citations:
            s2_id = paper.get("paperId", "")
            # Mark this S2 paper as seen BEFORE the relevance filter so that
            # irrelevant papers aren't re-evaluated on every subsequent run.
            if not s2_id or s2_id in seen:
                continue
            seen.add(s2_id)
            rec = _paper_to_record(paper, arxiv_id)
            if rec:
                records.append(rec)
        if i < cap - 1:
            time.sleep(delay)

    _save_seen_ids(seen)
    print(f"  citation_monitor: {len(records)} new relevant citing papers")
    return records
