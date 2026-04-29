# Playbook — AI Engineering Design DB

How to extend, rebuild, and explore this database in a future session. Written for a Claude session that walks in cold and needs to know what's here, what to run, and how to add to it.

---

## 1. What this project is

A flat-file JSONL database of AI/ML projects, papers, products, and datasets relevant to engineering design (CAD, simulation, materials, manufacturing, optimization). Plus a knowledge-graph layer and a graph explorer app on top.

**Current scale:** 831 records → 2,405 graph nodes, 8,795 edges (7,940 structural + 583 semantic-from-descriptions + 109 deep-citations-from-abstracts + 76 authored + venue/cosine).
Categories: 40. Venues: 242. People: 75. Paper abstracts cached: 437/491 (89%). Top citations: FNO (40 in-edges), PINN (27), DreamFusion (7).

---

## 2. Repo layout

```
ai-engineering-design-db/
├── SCHEMA.md                  — record schema (READ FIRST)
├── README.md                  — project overview
├── KNOWLEDGE-GRAPH.md         — graph design rationale
├── PLAYBOOK.md                — this file
├── BACKGROUND-TASKS.md        — log of dispatched async agents
│
├── raw/                       — one JSONL file per domain, append-only
│   ├── 00-seed-from-training.jsonl
│   ├── 01-text-to-cad-commercial.jsonl
│   ├── …                       (15 domain files currently)
│
├── consolidated.jsonl         — merged + deduped, OUTPUT of consolidate.py
├── consolidated-stats.json
├── embeddings.jsonl           — 1536-dim vectors, OUTPUT of embed.py
│
├── graph/
│   ├── nodes.csv
│   ├── edges.csv
│   ├── graph.gexf             — Gephi-importable
│   ├── graph-data.json        — what the explorer loads
│   ├── semantic-edges.csv     — Pass B output (LLM-over-descriptions + cosine)
│   ├── paper-abstracts.jsonl  — fetched abstracts cache (arXiv + OpenAlex)
│   ├── deep-citations.csv     — Pass C: LLM-over-abstracts citations
│   └── graph.html             — pyvis auto-render (legacy)
│
├── explorer.html              — the graph explorer app
│
└── scripts/
    ├── consolidate.py
    ├── embed.py
    ├── nearest.py             — kNN over embeddings (CLI)
    ├── build-graph.py         — Pass A structural + auto-load Pass B/C/venue/people CSVs
    ├── extract-semantic-edges.py  — Pass B (cosine + LLM over descriptions)
    ├── fetch-abstracts.py     — fetch real abstracts from arXiv + OpenAlex
    ├── extract-citations-deep.py — Pass C (LLM over real abstracts)
    └── serve.py               — local HTTP server for the explorer
```

---

## 3. The pipeline

```
raw/*.jsonl
   │
   │   consolidate.py            (dedup by id, validate enums, merge fields)
   ▼
consolidated.jsonl
   │
   │   embed.py                  (OpenAI text-embedding-3-small, 1536-dim)
   ▼
embeddings.jsonl
   │   ┌──────────────────────────────────────────────────────────────┐
   │   │ extract-venues.py        → graph/venue-{nodes,edges}.csv      │
   │   │ extract-people.py (LLM)  → graph/people-{nodes,edges}.csv     │
   │   │ extract-semantic-edges.py (Pass B: cosine + LLM/descriptions) │
   │   │   → graph/semantic-edges.csv                                  │
   │   │ fetch-abstracts.py       → graph/paper-abstracts.jsonl        │
   │   │   (arXiv API + OpenAlex API; cached, append-only)             │
   │   │ extract-citations-deep.py (Pass C: LLM over real abstracts)   │
   │   │   → graph/deep-citations.csv                                  │
   │   └──────────────────────────────────────────────────────────────┘
   ▼
build-graph.py             (Pass A: structural edges from JSON,
                            auto-merges every CSV in graph/)
   ▼
graph/nodes.csv, edges.csv, graph-data.json, graph.gexf
   │
   │   serve.py
   ▼
http://localhost:8765/explorer.html
```

**Standard rebuild after any raw/ change:**
```bash
py -3 scripts/consolidate.py
py -3 scripts/embed.py
py -3 scripts/extract-venues.py
py -3 scripts/extract-people.py             # ~$0.10
py -3 scripts/extract-semantic-edges.py     # Pass B: ~$0.20
py -3 scripts/fetch-abstracts.py            # free; arXiv+OpenAlex; ~3-5 min
py -3 scripts/extract-citations-deep.py     # Pass C: ~$0.20
py -3 scripts/build-graph.py --no-html      # folds all CSVs into graph-data.json
py -3 scripts/serve.py
```

---

## 4. Schema (the single source of truth)

Each record is one line of JSON in a `raw/*.jsonl` file:

```json
{
  "id": "kebab-slug-unique",
  "name": "Display Name",
  "category": "neural-operator",         // see SCHEMA.md for valid set
  "type": "academic-paper",              // commercial-product | academic-paper | open-source | research-project | benchmark-dataset
  "organization": "MIT CSAIL",
  "country": "US",
  "year": 2024,
  "url_primary": "https://…",
  "url_paper": "https://arxiv.org/…",
  "url_github": "https://github.com/…",
  "description": "80–250 word substantive paragraph (technique + result).",
  "techniques": ["transformer", "diffusion-model"],
  "input_modality": "text",
  "output_modality": "b-rep",
  "physics_domain": "fluid",
  "industry_application": ["aerospace"],
  "status": "released",
  "tags": ["wave-3", "manually-verified"]
}
```

`consolidate.py` validates `category` and `type` against fixed enums (see `SCHEMA.md` and `scripts/consolidate.py:VALID_CATEGORY`). Unknown values get retagged to `other` / `research-project`.

---

## 5. Adding a new domain (Wave N)

The dataset is grown by adding new files to `raw/`. Each file = one domain. **Do not edit existing files** — append-only avoids merge conflicts when multiple agents run.

### Recipe

1. Pick a domain not yet covered (see "Coverage gaps" below).
2. Create `raw/NN-domain-name.jsonl`.
3. Either write entries by hand, or **dispatch a Codex agent** with this template:

```
RESEARCH TASK — extend the AI engineering design JSONL DB.

CONTEXT
Base dir: "C:\…\ai-engineering-design-db\"
Schema: SCHEMA.md (READ FIRST)
Existing files in raw/: <list 00–NN, agent must avoid duplicate IDs>

MISSION
Write raw/NN-domain-name.jsonl with TARGET 30+ entries on <domain>.
Use web search aggressively. One JSON object per line.

[Insert seed list of project/paper names you want covered]

QUALITY:
- description ≥ 80 words, substantive
- real URLs, year + organization required
- skip rather than stub
- IDs kebab-case, unique vs all existing files

[Inline the schema spec from SCHEMA.md]
```

4. Dispatch via `Agent(subagent_type="codex:codex-rescue", run_in_background=true)`.
5. **Immediately** write the agent ID + expected output file to `BACKGROUND-TASKS.md`.
6. When notified of completion, run the standard rebuild pipeline (Section 3).

### Coverage gaps (priority order, as of 2026-04)

Big missing domains:
- **EDA / chip design AI** (Synopsys.ai, Cadence Cerebrus, NVIDIA NVCell, Google RL chip placement)
- **PCB design AI** (Flux, JITX, Quilter, AutoPCB, Cofactr)
- **AEC / construction AI** (Autodesk Forma, Hypar, Buildots, OpenSpace, Rendered.ai)
- **Robotics for manufacturing** (Path Robotics, Bright Machines, Covariant assembly)
- **Vision / inspection ML** (defect detection, dimensional QA, surface roughness CV)
- **Manufacturing process surrogates** beyond CFD/FEA (welding, casting, forging, IM)
- **Engineering RAG / chat** (Augie, Hexagon NEXUS AI, spec chatbots)
- **Reverse engineering / scan-to-CAD** beyond b-rep papers
- **Drawing generation** (GD&T inference, schematic gen, technical drawing AI)

Underrepresented (current count in parens):
- `process-monitoring-ml` (8) — should be ~25 with full L-PBF melt-pool literature
- `dfm-ai` (2) vs `dfam-ai` (20) — machining/molding DfM is undercaptured
- `implicit-modeling` (2), `ai-plm` (3), `cad-agent` (4), `ai-simulation-prep` (2)
- Industries: medical (8), construction (1), defense (2), semiconductor (0)

---

## 6. Working with background agents (Codex)

Codex is invoked via `Agent(subagent_type="codex:codex-rescue", run_in_background=true)`.

### Hard rules (these protect you across compactions)

1. **Write `BACKGROUND-TASKS.md` the same turn you dispatch the agent.** Include:
   - Codex job ID (from `codex-companion.mjs status --all`)
   - Expected output file paths
   - Re-dispatch prompt
   - Rebuild commands to run when it finishes
2. **On every session resume**, read `BACKGROUND-TASKS.md` first. Glob for the expected output files. If missing, re-dispatch.
3. **Codex has zombie jobs.** Process IDs from prior sessions can show as "running" in the companion's state file even when the OS process is dead. Cross-reference `Get-Process -Id <pid>` before assuming a job is alive. Kill stale PIDs before dispatching new work to avoid duplicate file writes.
4. **The completion notification is unreliable.** A Codex task can finish writing files and then exit before stamping itself "completed" — the companion will still report "running." Check the actual files (`raw/*.jsonl` line counts) as the source of truth, not job status.
5. **Each Wave writes to its own files.** Never let two concurrent agents target the same file path.

### Status / cancel commands

```bash
node "C:/Users/dougl/.claude/plugins/cache/openai-codex/codex/1.0.4/scripts/codex-companion.mjs" status --all --json
# Manual kill if cancel command misbehaves on Windows:
powershell.exe -Command "Stop-Process -Id <pid> -Force"
```

---

## 7. The graph explorer (`explorer.html`)

Standalone HTML, loads `graph/graph-data.json` over HTTP. Run `python scripts/serve.py` to serve at `http://localhost:8765/explorer.html`.

### Key UX

- Default visible: Project + Organization + Category nodes; BUILT_BY + IN_CATEGORY edges.
- Toggle node/edge types in the left sidebar to expand the view.
- Filter by category, year range, search.
- Click a node → right panel with description, techniques, links, neighbors.
- "Load dataset" or drag-drop any other JSON in the same shape:
  ```json
  {
    "meta": {"name": "...", "version": "...", "nodeCount": N, "edgeCount": M},
    "categories": [...],
    "yearRange": [yMin, yMax],
    "nodes": [{"id", "type", "label", "props"}, …],
    "edges": [{"source", "target", "type", "weight", "evidence"}, …]
  }
  ```

### Implementation notes (gotchas)

- `nodeById = new Map()` is built once per dataset load. **Do not** revert to `rawNodes.find()` in hot paths — clicks become O(n²).
- Vis-network silently ignores per-node `opacity` in `DataSet.update()`. Use `color.background` to dim instead.
- Filter changes use diff-update (remove ∆, add ∆), not `clear()` + `add()`, so existing nodes keep positions.
- Physics is disabled after first stabilization, then re-enabled briefly (800ms) when new nodes are added.
- Edge IDs are deduped by `(source, target, type)` — vis-network throws on collisions.

---

## 8. Pass B semantic edges

`scripts/extract-semantic-edges.py` produces:
- `SEMANTICALLY_NEAR` from cosine similarity (default τ=0.82)
- `CITES`, `BUILT_ON`, `BENCHMARKED_AGAINST` from GPT-4.1-mini batched over each project's description

Cost: ~$0.16 for 560 records. Use `--dry-run` to estimate before paying. Use `--limit N` for testing.

The LLM call uses **JSON mode** (`response_format={"type": "json_object"}`) and **word-boundary matching** when resolving target names → IDs (so "GPT" doesn't match "GPT-4"). Has retry-with-backoff for transient connection errors.

To rerun after a Wave-N update, run the script again — it overwrites `semantic-edges.csv`. Then `build-graph.py` to fold into `graph-data.json`.

---

## 9. Common operations

| Goal | Command |
|---|---|
| Add a domain | write `raw/NN-x.jsonl` → run pipeline |
| Search by free text | `py -3 scripts/nearest.py --query "neural CFD surrogate"` |
| Search by record ID | `py -3 scripts/nearest.py "deepcad" -k 10` |
| Re-extract semantic edges | `py -3 scripts/extract-semantic-edges.py --tau 0.82` |
| Estimate LLM cost | `py -3 scripts/extract-semantic-edges.py --dry-run` |
| Open the explorer | `py -3 scripts/serve.py` |
| Stats by category | `cat consolidated-stats.json` |
| Extract Venue nodes | `py -3 scripts/extract-venues.py` |
| Extract Person nodes (LLM) | `py -3 scripts/extract-people.py` (~$0.10 for 560 records) |
| Whitespace heat-map CSVs | `py -3 scripts/whitespace-report.py` |
| Run saved graph queries | `py -3 scripts/query-graph.py` |
| Drop into REPL with G loaded | `py -3 scripts/query-graph.py --shell` |
| Audit semantic-edges quality | `py -3 scripts/audit-semantic-edges.py` |
| Cypher via Kuzu (when wheels avail.) | `py -3 scripts/load-kuzu.py` |
| Fetch real paper abstracts | `py -3 scripts/fetch-abstracts.py` |
| Deep citations (over abstracts) | `py -3 scripts/extract-citations-deep.py` |

---

## 10. What I'd do next (open work)

### Done in 2026-04 sprint
- ✅ Wave 3: EDA, PCB, AEC, robotics-mfg, vision-inspection, process-monitoring, DfM-machining, medical, RAG, scan-to-CAD (10 files, 271 entries)
- ✅ People nodes (`extract-people.py` — 75 unique people, 76 AUTHORED edges)
- ✅ Venue nodes (`extract-venues.py` — 242 venues, with DOI prefix mapping for 30+ publishers)
- ✅ Cluster view in explorer (`Cluster` button groups Project nodes by Category)
- ✅ Whitespace report (`whitespace-report.py` — modality, physics×industry, category×year)
- ✅ NetworkX query interface (`query-graph.py`) — Kuzu deferred until Python 3.14 wheels ship
- ✅ Citation-quality audit (`audit-semantic-edges.py`) — flagged sibling-pair dedup misses
- ✅ **Deeper citations** — `fetch-abstracts.py` (arXiv + OpenAlex, 437/491 abstracts) + `extract-citations-deep.py` (LLM over real abstracts). +109 new citation edges, 95 corroborated. Citation-style edges grew 496 → 605 (+22%); FNO in-degree 29 → 40, PINN 24 → 27.

### Open work, priority order

1. **Fuzzy dedup** — 9 sibling-pair records flagged by `audit-semantic-edges.py` (e.g. `creo-generative-design` vs `-topology`, typo'd `forn-transformers`). Needs manual review or normalized-name dedup pass in `consolidate.py`.
2. **Audit deep-citations.csv** — `audit-semantic-edges.py` currently only reads `semantic-edges.csv`. Extend it to merge both files, or write a parallel audit for the abstract-derived edges.
3. **Recover the missing 54 abstracts** — `fetch-abstracts.py` failed on 54 records (mostly DOIs OpenAlex doesn't index, plus some 429s). Try Semantic Scholar API or PDF text extraction as a third fallback.
4. **Underrepresented categories** — `eda-chip-design` (4), `ai-plm` (3), `implicit-modeling` (2), `ai-simulation-prep` (2). Worth a Wave-N targeted at these.
5. **Industry coverage gaps** — defense (2), semiconductor (subsumed under electronics?), construction (better post-Wave 3 but still thin outside Forma/Hypar).
6. **Port the graph to Kuzu** for real Cypher queries when Python 3.14 wheels arrive (NetworkX `query-graph.py` is the today-bridge).
7. **Schema docs** — `SCHEMA.md` lists the 40 categories; KNOWLEDGE-GRAPH.md predates the People/Venue node types and should be refreshed.

---

## 11. House rules (recap from `~/.claude/CLAUDE.md`)

- Verify before asserting (URLs, model names, prices — search, don't guess).
- Append-only on `raw/*.jsonl`.
- Write `BACKGROUND-TASKS.md` the same turn you dispatch a background agent.
- For non-trivial new code, do the two-question delegation test before opening an editor.
- Never commit secrets or read API keys.
