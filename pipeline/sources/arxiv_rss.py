"""arXiv RSS source — pulls recent papers from cs.CG, cs.GR, cs.LG and filters by
AI+engineering-design keywords.

arXiv exposes Atom feeds at:
    http://export.arxiv.org/api/query?search_query=cat:cs.CG&start=0&max_results=200

We use the `feedparser` library; if it's not installed, the module degrades to no-op.
"""
from __future__ import annotations
import re
from datetime import datetime, timezone

CATEGORIES = ["cs.CG", "cs.GR", "cs.LG"]
QUERY_KEYWORDS = [
    "cad", "computer-aided design", "generative design", "topology optim",
    "neural operator", "physics-informed", "diffusion", "b-rep", "boundary repr",
    "implicit modeling", "sketch", "parametric", "additive manufactur",
    "3d shape", "mesh", "geometry", "design automation",
]
# Matches any of the keywords (case-insensitive). Pre-compiled once.
_KEYWORD_RE = re.compile("|".join(re.escape(k) for k in QUERY_KEYWORDS), re.I)

# Hard cap how far back we look on a given run. Pipeline runs every 2 weeks,
# so 21 days gives a 1-week overlap with the previous run for safety.
LOOKBACK_DAYS = 21


def fetch() -> list[dict]:
    """Return a list of candidate entries from arXiv. Empty list on failure."""
    try:
        import feedparser  # type: ignore
        import urllib.request
    except ImportError:
        print("[arxiv_rss] feedparser not installed — skipping. pip install feedparser")
        return []

    cutoff = datetime.now(tz=timezone.utc).timestamp() - (LOOKBACK_DAYS * 86400)
    results: list[dict] = []

    for category in CATEGORIES:
        url = (
            "http://export.arxiv.org/api/query?"
            f"search_query=cat:{category}&start=0&max_results=200"
            "&sortBy=submittedDate&sortOrder=descending"
        )
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ai-eng-design-db/1.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                feed = feedparser.parse(resp.read())
        except Exception as e:
            print(f"[arxiv_rss] failed to fetch {category}: {e}")
            continue

        for entry in feed.entries:
            # Filter to recent
            published = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
            if published is None:
                continue
            ts = datetime(*published[:6], tzinfo=timezone.utc).timestamp()
            if ts < cutoff:
                continue

            title = (entry.title or "").strip()
            summary = (entry.summary or "").strip()
            haystack = f"{title} {summary}"
            if not _KEYWORD_RE.search(haystack):
                continue

            authors = [a.name for a in getattr(entry, "authors", []) if hasattr(a, "name")]
            arxiv_id = (entry.id or "").rsplit("/", 1)[-1].split("v")[0]

            results.append({
                "name": title,
                "category": _guess_category(haystack),
                "year": int(datetime(*published[:6]).year),
                "organization": authors[0].split(" ")[-1] if authors else "",
                "description": summary[:600],
                "url_paper": entry.link,
                "techniques": _guess_techniques(haystack),
                "input_modality": "",
                "output_modality": "",
                "industry_application": [],
                "tags": [f"arxiv-id:{arxiv_id}", f"category:{category}"],
                "entry_type": "paper",
                "source": f"arxiv-rss:{category}",
            })

    return results


# ── Heuristic taggers — used to seed entries; the human reviewer will refine. ──

_CATEGORY_HINTS = {
    "topology-optimization": ["topology optim", "simp", "topopt"],
    "text-to-cad":           ["text-to-cad", "language to cad", "nl2cad"],
    "sketch-to-cad":         ["sketch-to-cad", "sketch to cad"],
    "image-to-cad":          ["image-to-cad", "image to cad"],
    "b-rep-learning":        ["b-rep", "boundary representation", "brep"],
    "neural-operator":       ["neural operator", "fno", "deeponet"],
    "physics-informed-nn":   ["physics-informed", "pinn"],
    "generative-3d-shape":   ["3d shape generation", "shape generative"],
    "implicit-modeling":     ["implicit", "sdf", "signed distance"],
    "generative-materials":  ["materials discovery", "crystal generation"],
    "dfm-ai":                ["design for manufactur", "manufacturability"],
    "dfam-ai":               ["additive manufactur", "design for am"],
    "cad-copilot":           ["cad copilot", "design copilot"],
    "cad-agent":             ["cad agent", "agentic cad"],
}

def _guess_category(text: str) -> str:
    lower = text.lower()
    for cat, hints in _CATEGORY_HINTS.items():
        for h in hints:
            if h in lower:
                return cat
    return "other"


_TECH_HINTS = [
    "transformer", "diffusion", "vae", "gan", "graph neural network",
    "attention", "lstm", "rnn", "cnn", "neural operator",
    "reinforcement learning", "fno", "deeponet", "pinn",
]

def _guess_techniques(text: str) -> list[str]:
    lower = text.lower()
    return [t for t in _TECH_HINTS if t in lower][:5]
