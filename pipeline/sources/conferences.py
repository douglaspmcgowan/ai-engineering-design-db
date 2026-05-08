"""Conference RSS / OpenReview source.

NOT YET IMPLEMENTED. Targets:
- SIGGRAPH OpenAccess (https://openaccess.thecvf.com)
- IDETC OpenReview (https://openreview.net)
- NeurIPS workshop pages (ML4PS, AI4Mat, D3S3)

For NeurIPS/ICML workshops we rely on the OpenReview API:
    https://api2.openreview.net/notes?invitation=NeurIPS.cc/2025/Workshop/...
"""
from __future__ import annotations


def fetch() -> list[dict]:
    return []  # stub
