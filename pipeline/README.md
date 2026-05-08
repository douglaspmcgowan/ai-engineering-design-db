# Automated discovery pipeline

Runs every 2 weeks. Pulls candidate AI-for-engineering-design entries from sources
that aren't covered by the existing arXiv/GitHub-heavy ingest. Output is
`raw/inbox-pipeline.jsonl` for human review before merging into `consolidated.jsonl`.

## Schedule

GitHub Action `.github/workflows/discovery-pipeline.yml` runs:
- Every 2 weeks on Sunday at 14:00 UTC (`0 14 * * 0/14`)
- Manual trigger via `workflow_dispatch`

First scheduled run targets ~2026-05-15 (one week from initial catch-up sweep).

## Sources

| Source | Module | Status | What it pulls |
|---|---|---|---|
| arXiv RSS | `sources/arxiv_rss.py` | ✅ implemented | New papers in cs.CG, cs.GR, cs.LG with AI+CAD keyword filter |
| GitHub trending | `sources/github_trending.py` | 🚧 stub | Topics: cad-generation, generative-design, neural-cad |
| YouTube + Whisper | `sources/youtube_whisper.py` | 🚧 stub | CDFAM, NASA Goddard, AU, nTop, Cool Parts Show channels — transcribe + extract |
| NASA NTRS | `sources/nasa_ntrs.py` | 🚧 stub | Recent generative-design / topology / AI papers |
| Conference RSS | `sources/conferences.py` | 🚧 stub | SIGGRAPH OpenAccess, IDETC, OpenReview NeurIPS workshops |
| Google Scholar Alerts | `sources/scholar_alerts.py` | 🚧 stub | Email-forwarded alerts → parse + ingest |
| Bits-to-Atoms RSS | `sources/substack.py` | 🚧 stub | Newsletter RSS → entries |

The "🚧 stub" sources have a function signature but return an empty list. They're
ordered by implementation priority — arXiv RSS first because it's free and reliable,
YouTube + Whisper last because it requires API keys and disk space.

## Output

Each source returns a list of dicts with the inbox schema. The runner collects
them, dedups against existing `consolidated.jsonl` ids and against the existing
`raw/inbox-pipeline.jsonl` (so re-runs don't re-emit), and appends new items.

After the run, the action posts a summary to the repo: how many new items per source,
top 5 by name, link to the diff.

## Running locally

```bash
cd ai-engineering-design-db
python -m pipeline.run                  # all sources
python -m pipeline.run --source arxiv   # one source
python -m pipeline.run --dry-run        # don't write inbox
```

## Citation-monitoring alerts (Feature 10 from KG-FEATURES-AUDIT)

Each pipeline run that emits ≥1 new item bumps a `last_run_count` entry in
`pipeline/state.json`. The explorer reads this on init and shows a small badge
on the +Add project FAB if there are unreviewed items in the inbox.
(Wiring deferred to a follow-up turn.)
