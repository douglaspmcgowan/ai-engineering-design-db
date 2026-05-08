"""GitHub trending source — pulls repos under topics relevant to AI-CAD.

NOT YET IMPLEMENTED. Will use the GitHub Search API:
    https://api.github.com/search/repositories?q=topic:cad-generation+topic:ai
    sort=updated&order=desc

Topics to query (union):
- cad-generation
- generative-design
- neural-cad
- topology-optimization
- physics-informed-neural-network
- design-automation

Filter: repos updated in the last 21 days, ≥10 stars (cuts out experiment forks),
description contains AI/ML/neural/learning keywords.
"""
from __future__ import annotations


def fetch() -> list[dict]:
    return []  # stub
