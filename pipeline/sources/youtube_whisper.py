"""YouTube + Whisper source — pulls recent videos from target channels and
transcribes them, then extracts AI-CAD topics via keyword + LLM tagging.

NOT YET IMPLEMENTED. Heaviest source to build because:
- Needs YouTube Data API v3 key (free tier: 10k units/day = ~100 channel queries)
- Whisper transcription is CPU/GPU-heavy — recommend faster-whisper-base (~1GB)
- Channel list is ~5 channels, ~10 videos per run = ~50 transcripts per cycle

Implementation plan:
1. yt-dlp to fetch metadata + audio for new videos
2. faster-whisper to transcribe
3. Heuristic chunking — keep only segments mentioning CAD/AI keywords
4. Emit one entry per video with description = first matched chunk

Channels to monitor:
- CDFAM (UCh4_oI50UE7lhYofyzVa9YQ — verify ID at runtime)
- NASA Goddard
- Autodesk University
- nTop
- The Cool Parts Show
"""
from __future__ import annotations


def fetch() -> list[dict]:
    return []  # stub
