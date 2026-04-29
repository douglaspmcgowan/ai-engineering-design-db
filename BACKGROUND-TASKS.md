# Background Tasks

This file is written immediately when a long-running background agent is dispatched.
Check this file first on any session resume. If expected output files are missing, re-dispatch.

---

## Wave 3 — Codex research sweep (10 domains, ~250 entries)

| Field | Value |
|---|---|
| **First attempt** | task-mojmal15-hls6ta (PID 46584) — ZOMBIE: died ~10m in at 05:41:35Z without writing any raw files |
| **Re-dispatch** | 2026-04-28 (this session) — agent ID a9388bfc28ce61a65 |
| **Status** | running, writing raw/16-25 directly (no helper-script detour) |
| **People extractor** | ✅ done — 72 people, 73 AUTHORED edges (graph/people-{nodes,edges}.csv) |

### Expected output files
| File | Target |
|---|---|
| `raw/16-eda-chip-design.jsonl` | 30+ |
| `raw/17-pcb-electronics-design.jsonl` | 25+ |
| `raw/18-aec-construction-ai.jsonl` | 30+ |
| `raw/19-robotics-manufacturing.jsonl` | 30+ |
| `raw/20-vision-inspection-qa-ml.jsonl` | 30+ |
| `raw/21-process-monitoring-am-boost.jsonl` | 25+ |
| `raw/22-dfm-machining-molding.jsonl` | 25+ |
| `raw/23-medical-engineering-ai.jsonl` | 25+ |
| `raw/24-engineering-rag-chat.jsonl` | 25+ |
| `raw/25-scan-to-cad-reverse-eng.jsonl` | 20+ |

### Next steps after Wave 3 completes
1. `py -3 scripts/consolidate.py`
2. `py -3 scripts/embed.py`
3. `py -3 scripts/extract-people.py` (new)
4. `py -3 scripts/extract-venues.py` (new)
5. `py -3 scripts/extract-semantic-edges.py`
6. `py -3 scripts/build-graph.py --no-html`
7. `py -3 scripts/whitespace-report.py`
8. `py -3 scripts/load-kuzu.py`

---

## Wave 2 — Codex research sweep (5 domains)

| Field | Value |
|---|---|
| **Codex job ID** | task-mojbqtkp-hy60y1 |
| **PID** | 37372 |
| **Dispatched** | 2026-04-29 |
| **Status** | ✅ completed — files written, process exited before marking done |

### Expected output files

| File | Target entries |
|---|---|
| `raw/11-b-rep-learning.jsonl` | 35+ |
| `raw/12-benchmark-datasets.jsonl` | 25+ |
| `raw/13-architected-materials.jsonl` | 30+ |
| `raw/14-scientific-ml-tools.jsonl` | 30+ |
| `raw/15-inverse-design-mdo.jsonl` | 30+ |

### Next steps after Wave 2 completes
1. `python scripts/consolidate.py`
2. `python scripts/embed.py`
3. `python scripts/build-graph.py` → graph/graph.html
4. Report totals

---

## Wave 1 — Codex research sweep (10 domains)

| Field | Value |
|---|---|
| **Codex job ID** | task-moj2yuzz-bhlyou |
| **PID** | 37484 |
| **Dispatched** | 2026-04-28T20:30:29Z |
| **Status** | ✅ completed — 2026-04-29T00:17:26Z |
| **Claude session** | C--Users-dougl-My-Drive--douglaspmcgowan-gmail-com--UC-Berkeley-Research-Claude-Research-Folder |

### Expected output files (check existence to confirm completion)

| File | Target entries |
|---|---|
| `raw/01-text-to-cad-commercial.jsonl` | 30+ |
| `raw/02-text-to-cad-academic.jsonl` | 40+ |
| `raw/03-topology-optimization.jsonl` | 35+ |
| `raw/04-neural-operators-surrogates.jsonl` | 40+ |
| `raw/05-generative-3d-shape.jsonl` | 35+ |
| `raw/06-generative-materials.jsonl` | 35+ |
| `raw/07-dfm-dfam-ai.jsonl` | 30+ |
| `raw/08-cad-copilots-agents.jsonl` | 25+ |
| `raw/09-generative-platforms.jsonl` | 25+ |
| `raw/10-pinn-differentiable.jsonl` | 30+ |

**Seed file already present:** `raw/00-seed-from-training.jsonl` (63 entries)

### Next steps after Codex completes
1. `python scripts/consolidate.py` → `consolidated.jsonl`
2. `python scripts/embed.py` → `embeddings.jsonl`
3. `python scripts/nearest.py "deepcad" -k 5` — spot-check kNN quality
4. Report final entry count + category breakdown to user
5. Consider Wave 2: b-rep learning, benchmark datasets, architected materials, harvest from AI-in-Design-Map site

### Re-dispatch prompt (if output files are missing)
Use `Agent(subagent_type="codex:codex-rescue")` with `--fresh` and the full 10-domain brief from the session transcript.
