"""Google Scholar Alerts source.

NOT YET IMPLEMENTED. Scholar doesn't expose an API; recommended approach:
1. Configure scholar alerts in the user's Gmail
2. Use Gmail filter to forward matching emails to a label
3. Use IMAP to fetch + parse (BeautifulSoup) → emit entries

OR: skip and rely on arxiv_rss + conferences for academic coverage.
"""
from __future__ import annotations


def fetch() -> list[dict]:
    return []  # stub
