"""Pipeline runner.

Usage:
    python -m pipeline.run                  # all sources
    python -m pipeline.run --source arxiv   # one source
    python -m pipeline.run --dry-run        # don't write inbox

Reads each source's fetch() function, dedupes against existing consolidated.jsonl
+ existing inbox, and appends new entries to raw/inbox-pipeline.jsonl.
"""
from __future__ import annotations
import argparse, json, re, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT / "raw" / "inbox-pipeline.jsonl"
CONSOLIDATED = ROOT / "consolidated.jsonl"
STATE = ROOT / "pipeline" / "state.json"

# Import source modules. Adding a new source = add to this dict.
from pipeline.sources import arxiv_rss, github_trending, youtube_whisper
from pipeline.sources import nasa_ntrs, conferences, substack, scholar_alerts

SOURCES = {
    "arxiv":            arxiv_rss,
    "github":           github_trending,
    "youtube":          youtube_whisper,
    "nasa":             nasa_ntrs,
    "conferences":      conferences,
    "substack":         substack,
    "scholar":          scholar_alerts,
}


def slugify(text: str) -> str:
    s = (text or "").lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:80]


def load_existing_ids() -> set:
    """Collect all ids that already exist anywhere — consolidated + inbox."""
    ids = set()
    for path in [CONSOLIDATED, INBOX]:
        if not path.exists():
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("//"):
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                rec_id = rec.get("id") or slugify(rec.get("name", ""))
                if rec_id:
                    ids.add(rec_id)
    return ids


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", help="Run only this source (default: all)")
    parser.add_argument("--dry-run", action="store_true", help="Don't write inbox")
    args = parser.parse_args()

    sources_to_run = [args.source] if args.source else list(SOURCES.keys())
    existing_ids = load_existing_ids()
    print(f"Loaded {len(existing_ids)} existing ids for dedup")

    new_records = []
    summary = {}
    for src_name in sources_to_run:
        src = SOURCES.get(src_name)
        if not src:
            print(f"  ! unknown source: {src_name}", file=sys.stderr)
            continue
        try:
            results = src.fetch()
        except Exception as e:
            print(f"  ! {src_name} failed: {e}", file=sys.stderr)
            results = []
        # Dedup against existing ids
        kept = []
        for rec in results:
            rec_id = rec.get("id") or slugify(rec.get("name", ""))
            if not rec_id or rec_id in existing_ids:
                continue
            rec["id"] = rec_id
            existing_ids.add(rec_id)
            kept.append(rec)
        summary[src_name] = {"fetched": len(results), "new": len(kept)}
        new_records.extend(kept)
        print(f"  {src_name}: {len(results)} fetched, {len(kept)} new after dedup")

    if not new_records:
        print("No new entries this run.")
        _save_state(summary, 0)
        return 0

    print(f"\nTotal new entries: {len(new_records)}")
    if args.dry_run:
        print("--dry-run: not writing inbox")
        return 0

    # Append to inbox
    INBOX.parent.mkdir(exist_ok=True)
    with open(INBOX, "a", encoding="utf-8") as f:
        for rec in new_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"Appended {len(new_records)} entries to {INBOX.name}")
    _save_state(summary, len(new_records))
    return 0


def _save_state(summary, new_count):
    state = {
        "last_run": datetime.now().isoformat(timespec="seconds"),
        "last_run_count": new_count,
        "by_source": summary,
    }
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


if __name__ == "__main__":
    sys.exit(main())
