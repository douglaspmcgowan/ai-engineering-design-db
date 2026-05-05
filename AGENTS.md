# AGENTS.md — ai-engineering-design-db

Instructions for Codex and other agents working in this project.

## Project overview

Vercel-deployed knowledge graph of AI/ML engineering design tools (~800+ records).
Live at: https://ai-engineering-design-db.vercel.app

Key files:
- `explorer.html` — single-file graph explorer SPA (~6850 lines, vis-network)
- `browse.html` — card/table browse view with filters
- `ingest.html` — submission form for new records
- `api/ingest.js` — Vercel serverless function (OpenAI GPT-5.4 + GitHub API)
- `graph/graph-data.json` — runtime graph data (loaded by explorer.html)
- `graph/embed-coords.json` — UMAP 2D positions for nodes
- `consolidated.jsonl` — canonical record database (one JSON object per line)
- `raw/inbox.jsonl` — staging queue for new ingest submissions
- `embeddings.jsonl` — pre-computed embeddings per record
- `scripts/embedding-report.py` — cosine novelty report generator
- `.github/workflows/rebuild.yml` — cron pipeline (every 2 days, 3 AM UTC)

## Writing files on this machine (CRITICAL — Windows/PowerShell)

**Use the Write tool for every new file.** Bash heredocs, `echo` with backticks, and
`echo` with `$VAR` all fail on PowerShell — corrupted or empty output guaranteed.

Full reference (why it fails, PowerShell here-strings, Python fallback, safe vs. unsafe
file types): **`~/.codex/windows-file-writing.md`**

## API and environment

- **OpenAI API** — `api/ingest.js` uses `OPENAI_API_KEY` + model `gpt-5.4`
  - Endpoint: `api.openai.com/v1/chat/completions`
  - Auth: `Authorization: Bearer <key>`
  - Image support: multimodal messages with `image_url` content blocks
- **GitHub API** — uses `GITHUB_TOKEN` (PAT with repo scope)
  - Reads/writes `raw/inbox.jsonl` via Contents API
- **No npm dependencies in api/** — `api/ingest.js` uses Node built-in `https` only.
  Adding npm packages requires `package.json` changes and Vercel rebuild.

Environment variables required in Vercel dashboard:
- `OPENAI_API_KEY`
- `GITHUB_TOKEN`

## Testing

```bash
# Playwright unit tests (browse page, mock data)
npx playwright test tests/browse.spec.js

# Playwright visual tests (explorer, real data — start server first)
python -m http.server 8770 &
npx playwright test tests/visual.spec.js --headed

# Verify ingest API loads (no runtime, just module check)
node -e "require('./api/ingest.js'); console.log('ok')"

# Verify embedding report runs (needs Python)
python scripts/embedding-report.py
```

## Physics rules for explorer.html (do not break)

- Solver: `barnesHut` (NOT ForceAtlas2Based — causes square packing with 2000+ nodes)
- `avoidOverlap: 0.15–0.25` — higher values create square boundary packing
- `centralGravity: 0.005–0.01` — weak pull lets cluster islands form
- `springLength: 180–220`, `springConstant: 0.08–0.12`
- Physics timer ≤ 3500ms — UMAP positions are already organic, long physics destroys them
- Always call `network.fit()` after physics stops

## Vercel deploy

Push to `main` on GitHub → auto-deploys. `vercel.json` has `cleanUrls: true` — do NOT
add explicit redirects from `/foo` → `/foo.html` (creates infinite redirect loops).
The `/ingest` route is handled by a redirect to `/ingest.html`.
