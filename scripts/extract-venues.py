"""
extract-venues.py — derive Venue nodes from url_paper hosts.

Maps known hostnames to canonical venue labels. Emits Venue nodes and
PUBLISHED_AT edges to graph/venue-edges.csv (then folded in by build-graph.py).

Usage:
    python scripts/extract-venues.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

# Make Windows console accept UTF-8 (avoid cp1252 crashes on Unicode in print)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
CONSOLIDATED = ROOT / "consolidated.jsonl"
OUT_NODES = ROOT / "graph" / "venue-nodes.csv"
OUT_EDGES = ROOT / "graph" / "venue-edges.csv"

# Hostname → (canonical label, kind). Order matters for matches.
HOST_TO_VENUE: list[tuple[str, str, str]] = [
    ("arxiv.org",                    "arXiv",                          "preprint"),
    ("openreview.net",               "OpenReview",                     "review"),
    ("papers.nips.cc",               "NeurIPS",                        "conference"),
    ("proceedings.neurips.cc",       "NeurIPS",                        "conference"),
    ("proceedings.mlr.press",        "PMLR (ICML/AISTATS)",            "conference"),
    ("openaccess.thecvf.com",        "CVF (CVPR/ICCV/ECCV)",           "conference"),
    ("ojs.aaai.org",                 "AAAI",                           "conference"),
    ("ieeexplore.ieee.org",          "IEEE Xplore",                    "publisher"),
    ("dl.acm.org",                   "ACM Digital Library",            "publisher"),
    ("link.springer.com",            "Springer",                       "publisher"),
    ("onlinelibrary.wiley.com",      "Wiley",                          "publisher"),
    ("nature.com",                   "Nature Portfolio",               "publisher"),
    ("science.org",                  "Science",                        "publisher"),
    ("cell.com",                     "Cell Press",                     "publisher"),
    ("sciencedirect.com",            "Elsevier (ScienceDirect)",       "publisher"),
    ("aps.org",                      "American Physical Society",      "publisher"),
    ("ams.org",                      "American Math Society",          "publisher"),
    ("asmedigitalcollection.asme",   "ASME",                           "publisher"),
    ("siam.org",                     "SIAM",                           "publisher"),
    ("aiaa.org",                     "AIAA",                           "publisher"),
    ("github.com",                   "GitHub",                         "code"),
    ("huggingface.co",               "Hugging Face",                   "hosting"),
    ("biorxiv.org",                  "bioRxiv",                        "preprint"),
    ("chemrxiv.org",                 "ChemRxiv",                       "preprint"),
    ("pubs.acs.org",                 "ACS",                            "publisher"),
    ("rsc.org",                      "RSC",                            "publisher"),
    ("mdpi.com",                     "MDPI",                           "publisher"),
    ("iop.org",                      "IOP",                            "publisher"),
    ("frontiersin.org",              "Frontiers",                      "publisher"),
    ("plos.org",                     "PLOS",                           "publisher"),
    ("semanticscholar.org",          "Semantic Scholar",               "index"),
    ("youtube.com",                  "YouTube",                        "media"),
    ("youtu.be",                     "YouTube",                        "media"),
]


def slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")[:80]


# DOI prefix → publisher (covers ~95% of academic DOIs)
DOI_PREFIX_TO_PUBLISHER: dict[str, tuple[str, str]] = {
    "10.1109":   ("IEEE Xplore",                 "publisher"),
    "10.1145":   ("ACM Digital Library",         "publisher"),
    "10.1038":   ("Nature Portfolio",            "publisher"),
    "10.1126":   ("Science",                     "publisher"),
    "10.1016":   ("Elsevier (ScienceDirect)",    "publisher"),
    "10.1115":   ("ASME",                        "publisher"),
    "10.1007":   ("Springer",                    "publisher"),
    "10.1002":   ("Wiley",                       "publisher"),
    "10.1063":   ("AIP",                         "publisher"),
    "10.1103":   ("American Physical Society",   "publisher"),
    "10.1021":   ("ACS",                         "publisher"),
    "10.1039":   ("RSC",                         "publisher"),
    "10.1080":   ("Taylor & Francis",            "publisher"),
    "10.1088":   ("IOP",                         "publisher"),
    "10.1093":   ("Oxford Univ Press",           "publisher"),
    "10.1017":   ("Cambridge Univ Press",        "publisher"),
    "10.1364":   ("Optica",                      "publisher"),
    "10.1186":   ("BMC",                         "publisher"),
    "10.1371":   ("PLOS",                        "publisher"),
    "10.1075":   ("John Benjamins",              "publisher"),
    "10.2514":   ("AIAA",                        "publisher"),
    "10.1137":   ("SIAM",                        "publisher"),
    "10.1101":   ("bioRxiv",                     "preprint"),
    "10.1162":   ("MIT Press",                   "publisher"),
    "10.5555":   ("PMLR (ICML/AISTATS)",         "conference"),
    "10.5281":   ("Zenodo",                      "hosting"),
    # Audit-driven additions (covers another ~200 DOIs)
    "10.48550":  ("arXiv",                       "preprint"),    # arXiv DOI form
    "10.3390":   ("MDPI",                        "publisher"),
    "10.3389":   ("Frontiers",                   "publisher"),
    "10.3233":   ("IOS Press",                   "publisher"),
    "10.1097":   ("Wolters Kluwer Health",       "publisher"),
    "10.1609":   ("AAAI",                        "conference"),
    "10.1146":   ("Annual Reviews",              "publisher"),
    "10.24963":  ("IJCAI",                       "conference"),
    "10.23919":  ("IEEE Xplore",                 "publisher"),   # IEEE conference alt
    "10.1061":   ("ASCE",                        "publisher"),   # civil engineering
    "10.1073":   ("PNAS",                        "publisher"),
    "10.1029":   ("AGU",                         "publisher"),   # geophysical
    "10.1177":   ("SAGE Publishing",             "publisher"),
    "10.1049":   ("IET",                         "publisher"),
    "10.1190":   ("SEG",                         "publisher"),   # geophysics
    "10.2118":   ("SPE",                         "publisher"),   # petroleum eng
    "10.1140":   ("Springer (EPJ)",              "publisher"),
    "10.1023":   ("Springer",                    "publisher"),
    "10.4208":   ("Global Science Press",        "publisher"),
    "10.1615":   ("Begell House",                "publisher"),
    "10.2355":   ("ISIJ International",          "publisher"),   # iron & steel
    "10.32604":  ("Tech Science Press",          "publisher"),
    "10.3934":   ("AIMS Press",                  "publisher"),
    "10.1098":   ("Royal Society",               "publisher"),
    "10.5194":   ("Copernicus",                  "publisher"),   # geosciences
    "10.1287":   ("INFORMS",                     "publisher"),
    "10.1111":   ("Wiley",                       "publisher"),   # Wiley alt
    "10.1142":   ("World Scientific",            "publisher"),
    "10.1130":   ("Geological Society",          "publisher"),
    "10.1175":   ("AMS",                         "publisher"),   # American Meteorological
}


def _resolve_doi(url: str) -> tuple[str, str] | None:
    """If URL is a DOI link, map its prefix to a publisher."""
    m = re.search(r"(?:doi\.org/|/doi/(?:abs/|full/|pdf/)?)([0-9]+\.[0-9]+)/", url)
    if not m:
        return None
    prefix = m.group(1)
    return DOI_PREFIX_TO_PUBLISHER.get(prefix)


def venue_for_url(url: str) -> tuple[str, str] | None:
    if not url:
        return None
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return None
    if not host:
        return None
    host = re.sub(r"^www\.", "", host)

    # DOIs: parse the prefix to get the actual publisher
    if "doi.org" in host:
        v = _resolve_doi(url)
        if v:
            return v
        return ("DOI (unknown publisher)", "publisher")

    for needle, label, kind in HOST_TO_VENUE:
        if needle in host:
            return (label, kind)
    parts = host.split(".")
    if len(parts) >= 2:
        return (parts[-2].title(), "other")
    return (host, "other")


def main() -> int:
    if not CONSOLIDATED.exists():
        print(f"missing {CONSOLIDATED}", file=sys.stderr)
        return 1

    records = [json.loads(l) for l in open(CONSOLIDATED, encoding="utf-8") if l.strip()]
    print(f"Loaded {len(records)} records")

    venue_counts: Counter[str] = Counter()
    edges: list[dict] = []

    for r in records:
        # Try url_paper first, then url_primary, then url_github
        for field in ("url_paper", "url_primary", "url_github"):
            url = r.get(field)
            v = venue_for_url(url)
            if v:
                label, kind = v
                venue_counts[label] += 1
                edges.append({
                    "source": f"project:{r['id']}",
                    "target": f"venue:{slugify(label)}",
                    "type": "PUBLISHED_AT",
                    "weight": 1.0,
                    "evidence": f"{field}={urlparse(url).netloc}",
                })
                break  # one venue per project (the highest-priority url)

    # Write venue nodes
    OUT_NODES.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_NODES, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "type", "label", "props"])
        w.writeheader()
        for label, count in venue_counts.most_common():
            kind = next((k for needle, l, k in HOST_TO_VENUE if l == label), "other")
            w.writerow({
                "id":    f"venue:{slugify(label)}",
                "type":  "Venue",
                "label": label,
                "props": json.dumps({"kind": kind, "count": count}),
            })

    with open(OUT_EDGES, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["source", "target", "type", "weight", "evidence"])
        w.writeheader()
        w.writerows(edges)

    print(f"Wrote {len(venue_counts)} venues, {len(edges)} edges")
    print("\nTop venues:")
    for label, count in venue_counts.most_common(10):
        print(f"  {count:3d}  {label}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
