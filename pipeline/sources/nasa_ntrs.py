"""NASA NTRS source — recent generative-design / topology / AI papers.

NOT YET IMPLEMENTED. NASA NTRS exposes a JSON API:
    https://ntrs.nasa.gov/api/citations/search?q=...&page.size=100

Query: ("generative design" OR "topology optimization" OR "machine learning")
       AND publishedDate:[NOW-21DAYS TO NOW]

Filter to result_type=Paper and result_type=Conference Paper.
"""
from __future__ import annotations


def fetch() -> list[dict]:
    return []  # stub
