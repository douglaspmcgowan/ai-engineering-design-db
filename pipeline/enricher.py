"""In-flow record enricher.

Called by run.py *after* source.fetch() returns new records, before writing
them to the inbox. Fills in common gaps without blocking the core pipeline:

  1. year         — extracted from an arXiv ID embedded in any URL field.
                    (YYMM.NNNNN → 20YY; zero API calls needed.)
  2. year + abstract + venue
                  — fetched from Semantic Scholar title-search for paper
                    records that are still missing year or description.
  3. description  — fetched from the GitHub repo API for records whose
                    url_github field is populated but description is empty.

Stays under a strict query budget so the CI step adds at most ~90s:
  - MAX_S2_QUERIES (default 20): 20 × 1.1 s ≈ 22 s unauthenticated
  - MAX_GH_QUERIES (default 20): 20 × 0.3 s ≈  6 s

Set env vars to unlock higher throughput:
  S2_API_KEY     — ups Semantic Scholar to 10 req/s
  GITHUB_TOKEN   — ups GitHub from 60 to 5000 req/h

Usage (programmatic):
    from pipeline.enricher import enrich_batch
    new_records = enrich_batch(new_records)

Usage (standalone – dry-run to see what would change):
    python -m pipeline.enricher --dry-run
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONSOLIDATED = ROOT / "consolidated.jsonl"

S2_SEARCH_BASE = "https://api.semanticscholar.org/graph/v1/paper/search"
S2_SEARCH_FIELDS = "title,year,abstract,venue,authors,externalIds"
GH_API_BASE = "https://api.github.com/repos"

MAX_S2_QUERIES = 20
MAX_GH_QUERIES = 20

# ─────────────────────────────────────────────────────────────────────────────
# Regex helpers
# ─────────────────────────────────────────────────────────────────────────────

# arXiv new-style IDs: YYMM.NNNNN (2007 onwards)
_ARXIV_ID_RE = re.compile(r"arxiv\.org/abs/(\d{2})(\d{2})\.\d{4,5}", re.I)
# GitHub owner/repo path
_GH_REPO_RE = re.compile(r"github\.com/([^/]+/[^/?#]+)", re.I)


# ─────────────────────────────────────────────────────────────────────────────
# Year from arXiv URL
# ─────────────────────────────────────────────────────────────────────────────

def _fill_year_from_url(rec: dict) -> bool:
    """If rec has an arXiv URL, extract the 4-digit year from the ID.
    Returns True if year was filled in."""
    for field in ("url_paper", "url_primary", "url", "link"):
        url = rec.get(field) or ""
        if not url:
            continue
        m = _ARXIV_ID_RE.search(url)
        if m:
            yy = int(m.group(1))
            yyyy = 2000 + yy  # arXiv new IDs: 0704 = 2007, 2505 = 2025
            if 2007 <= yyyy <= 2030:
                rec["year"] = yyyy
                return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Semantic Scholar helpers
# ─────────────────────────────────────────────────────────────────────────────

def _s2_headers() -> dict[str, str]:
    h = {"User-Agent": "ai-eng-design-db/1.0"}
    k = os.environ.get("S2_API_KEY", "")
    if k:
        h["x-api-key"] = k
    return h


def _s2_delay() -> float:
    return 0.15 if os.environ.get("S2_API_KEY") else 1.1


def _titles_similar(a: str, b: str, threshold: float = 0.50) -> bool:
    """True when normalised Jaccard ≥ threshold on word sets."""
    def words(s: str) -> set[str]:
        return set(re.sub(r"[^\w]", " ", s.lower()).split()) - {"a", "an", "the", "of", "in"}
    wa, wb = words(a), words(b)
    if not wa or not wb:
        return False
    return len(wa & wb) / len(wa | wb) >= threshold


def _s2_search_by_title(title: str) -> dict | None:
    """Return the best matching Semantic Scholar paper for title, or None."""
    q = urllib.parse.quote(title.strip())
    url = f"{S2_SEARCH_BASE}?query={q}&fields={S2_SEARCH_FIELDS}&limit=1"
    try:
        req = urllib.request.Request(url, headers=_s2_headers())
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        papers = data.get("data", [])
        if not papers:
            return None
        p = papers[0]
        if not _titles_similar(title, p.get("title", "")):
            return None
        return p
    except Exception:
        return None


def _apply_s2(rec: dict, paper: dict) -> None:
    """Merge S2 fields into rec where rec's field is empty."""
    if not rec.get("year") and paper.get("year"):
        rec["year"] = paper["year"]
    if not (rec.get("description") or "").strip() and (paper.get("abstract") or "").strip():
        rec["description"] = paper["abstract"][:600]
    if not (rec.get("venue") or "").strip() and (paper.get("venue") or "").strip():
        rec["venue"] = paper["venue"]
    # Pull arxiv ID from externalIds to populate url_paper if missing
    ext = paper.get("externalIds") or {}
    if not rec.get("url_paper") and ext.get("ArXiv"):
        rec["url_paper"] = f"https://arxiv.org/abs/{ext['ArXiv']}"


# ─────────────────────────────────────────────────────────────────────────────
# GitHub helpers
# ─────────────────────────────────────────────────────────────────────────────

def _gh_headers() -> dict[str, str]:
    h = {"User-Agent": "ai-eng-design-db/1.0", "Accept": "application/vnd.github.v3+json"}
    tok = os.environ.get("GITHUB_TOKEN", "")
    if tok:
        h["Authorization"] = f"token {tok}"
    return h


def _fill_from_github(rec: dict) -> None:
    """Populate description (and stars) from GitHub API."""
    gh_url = rec.get("url_github") or ""
    if not gh_url:
        return
    m = _GH_REPO_RE.search(gh_url)
    if not m:
        return
    repo_path = m.group(1).rstrip("/")
    api_url = f"{GH_API_BASE}/{repo_path}"
    try:
        req = urllib.request.Request(api_url, headers=_gh_headers())
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
    except Exception:
        return
    if data.get("description") and not (rec.get("description") or "").strip():
        rec["description"] = data["description"]
    # Bonus: stash star count as enrichment metadata (won't break the schema)
    if data.get("stargazers_count") is not None and "github_stars" not in rec:
        rec["github_stars"] = data["stargazers_count"]


# ─────────────────────────────────────────────────────────────────────────────
# Predicates
# ─────────────────────────────────────────────────────────────────────────────

_PAPER_TYPES = {"paper", "academic-paper", "preprint", "conference-paper"}


def _is_paper(rec: dict) -> bool:
    t = (rec.get("entry_type") or rec.get("type") or "").lower()
    return any(pt in t for pt in _PAPER_TYPES)


def _needs_s2(rec: dict) -> bool:
    return _is_paper(rec) and (
        not str(rec.get("year") or "").strip()
        or not str(rec.get("description") or "").strip()
    )


def _needs_github(rec: dict) -> bool:
    return bool(rec.get("url_github")) and not str(rec.get("description") or "").strip()


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def enrich_batch(
    records: list[dict],
    max_s2: int = MAX_S2_QUERIES,
    max_gh: int = MAX_GH_QUERIES,
    verbose: bool = True,
) -> list[dict]:
    """Enrich records in-place. Returns the same list.

    Steps per record (in order, skip if quota exhausted):
      1. Year from arXiv URL     — free, no quota
      2. Semantic Scholar lookup — uses S2 quota
      3. GitHub API              — uses GH quota
    """
    s2_used = 0
    gh_used = 0
    enriched_count = 0

    for rec in records:
        changed = False

        # Step 1: free year extraction
        if not str(rec.get("year") or "").strip():
            if _fill_year_from_url(rec):
                changed = True

        # Step 2: Semantic Scholar
        if s2_used < max_s2 and _needs_s2(rec):
            title = rec.get("name", "")
            if title:
                paper = _s2_search_by_title(title)
                if paper:
                    before_year = rec.get("year")
                    before_desc = rec.get("description")
                    _apply_s2(rec, paper)
                    if rec.get("year") != before_year or rec.get("description") != before_desc:
                        changed = True
                s2_used += 1
                time.sleep(_s2_delay())

        # Step 3: GitHub
        if gh_used < max_gh and _needs_github(rec):
            before = rec.get("description")
            _fill_from_github(rec)
            if rec.get("description") != before:
                changed = True
            gh_used += 1

        if changed:
            enriched_count += 1

    if verbose:
        print(
            f"  enricher: {enriched_count}/{len(records)} records enriched"
            f" (S2: {s2_used} queries, GitHub: {gh_used} queries)"
        )
    return records


# ─────────────────────────────────────────────────────────────────────────────
# Standalone dry-run mode
# ─────────────────────────────────────────────────────────────────────────────

def _load_inbox() -> list[dict]:
    inbox = ROOT / "raw" / "inbox-pipeline.jsonl"
    if not inbox.exists():
        return []
    records = []
    with open(inbox, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return records


if __name__ == "__main__":
    import argparse
    import copy

    parser = argparse.ArgumentParser(description="Enrich pipeline inbox records")
    parser.add_argument("--dry-run", action="store_true", help="Print diffs but don't write")
    parser.add_argument("--max-s2", type=int, default=MAX_S2_QUERIES)
    parser.add_argument("--max-gh", type=int, default=MAX_GH_QUERIES)
    args = parser.parse_args()

    records = _load_inbox()
    if not records:
        print("Inbox is empty or does not exist.")
    else:
        originals = [copy.deepcopy(r) for r in records]
        enrich_batch(records, max_s2=args.max_s2, max_gh=args.max_gh)

        if args.dry_run:
            for orig, enriched in zip(originals, records):
                diffs = {
                    k: (orig.get(k), enriched.get(k))
                    for k in enriched
                    if enriched.get(k) != orig.get(k)
                }
                if diffs:
                    print(f"\n  [{enriched.get('name','?')}]")
                    for k, (before, after) in diffs.items():
                        print(f"    {k}: {before!r} → {after!r}")
