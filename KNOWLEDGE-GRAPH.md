# Knowledge Graph — AI for Engineering Design

Live explorer: **https://ai-engineering-design-db.vercel.app**

A queryable knowledge graph of AI/ML tools, papers, and products for engineering design. 842 projects, 2,449 graph nodes, 8,884 edges. Push to `main` → auto-deploys.

---

## Current state (as of 2026-05)

| Metric | Value |
|--------|-------|
| Project records | 842 |
| Total graph nodes | 2,449 |
| Total edges | 8,884 |
| Domain categories | 42 |
| Organizations | 514 unique |
| Techniques | 537 unique |
| Venues | 242 unique |

### Node breakdown

| Node type | Count | Source |
|-----------|-------|--------|
| Project | 842 | one per `consolidated.jsonl` record |
| Technique | 537 | exploded from `techniques[]` array |
| Organization | 514 | unique `organization` strings |
| Venue | 242 | derived from paper URL host |
| Modality | 124 | unique `input_modality` + `output_modality` values |
| Person | 75 | extracted from descriptions |
| Category | 42 | `category` field |
| Industry | 38 | `industry_application[]` items |
| Year | 25 | `year` integer (2000–2026) |
| PhysicsDomain | 10 | `physics_domain` field |

### Edge breakdown

| Edge type | Count | How it's built |
|-----------|-------|----------------|
| USES_TECHNIQUE | 1,432 | `techniques[]` array → Technique node |
| APPLIED_TO | 857 | `industry_application[]` → Industry node |
| BUILT_BY | 842 | `organization` field → Organization node |
| IN_CATEGORY | 842 | `category` field → Category node |
| CONSUMES | 842 | `input_modality` → Modality node |
| PRODUCES | 842 | `output_modality` → Modality node |
| RELEASED_IN | 842 | `year` → Year node |
| PUBLISHED_AT | 831 | paper URL host → Venue node |
| OPERATES_ON | 786 | `physics_domain` → PhysicsDomain node |
| CITES | 287 | LLM-extracted from description text |
| BUILT_ON | 168 | LLM-extracted ("builds on X…") patterns |
| BENCHMARKED_AGAINST | 150 | LLM-extracted ("outperforms X…") patterns |
| SEMANTICALLY_NEAR | 87 | cosine similarity ≥ τ on embeddings |
| AUTHORED | 76 | LLM-extracted author mentions |

---

## How the data was collected

The database was built by AI research agents running in three phases:

### Phase 1 — Seed (file `00-seed-from-training.jsonl`)
68 records drawn from Claude's training knowledge — well-known papers and tools the model had high confidence in: DeepCAD, SkexGen, BRepNet, FNO, DreamFusion, etc. These form the backbone and the citation targets for Phase 2 edges.

### Phase 2 — Domain sweeps (files `01–25`)
25 parallel domain research agents, each assigned a sub-field of engineering-design AI:

| Domain file | Topic | Records |
|-------------|-------|---------|
| 01-text-to-cad-commercial | Commercial text-to-CAD products | 31 |
| 02-text-to-cad-academic | Academic text/program CAD generation | 40 |
| 03-topology-optimization | Neural topology & generative TO | 38 |
| 04-neural-operators-surrogates | FNO, DeepONet, PINNs, physics surrogates | 42 |
| 05-generative-3d-shape | Shape generation, 3D diffusion | 35 |
| 06-generative-materials | Generative materials, crystal gen | 37 |
| 07-dfm-dfam-ai | DFM/DFAM, printability AI | 31 |
| 08-cad-copilots-agents | CAD copilots, LLM agents for CAD | 25 |
| 09-generative-platforms | Genesis, Modulus, PhysicsNeMo, etc. | 25 |
| 10-pinn-differentiable | Physics-informed NNs, differentiable physics | 34 |
| 11-b-rep-learning | B-rep neural nets, UV-Net, BRepNet | 35 |
| 12-benchmark-datasets | Benchmark datasets and evaluation frameworks | 26 |
| 13-architected-materials | Lattice/metamaterial AI design | 32 |
| 14-scientific-ml-tools | SciML, JAX-MD, DeepXDE, Triton | 30 |
| 15-inverse-design-mdo | Inverse design, MDO, topology opt. | 31 |
| 16-eda-chip-design | EDA AI, chip placement, routing | 31 |
| 17-pcb-electronics-design | PCB layout AI, electronics design | 25 |
| 18-aec-construction-ai | Architecture, engineering, construction | 30 |
| 19-robotics-manufacturing | Robotics path planning, grasping | 30 |
| 20-vision-inspection-qa-ml | Visual QA, defect detection, inspection | 30 |
| 21-process-monitoring-am-boost | AM process monitoring, parameter pred. | 25 |
| 22-dfm-machining-molding | Machining/molding design rules | 25 |
| 23-medical-engineering-ai | Medical device design AI | 25 |
| 24-engineering-rag-chat | Engineering RAG and chat tools | 25 |
| 25-scan-to-cad-reverse-eng | Scan-to-CAD, reverse engineering | 25 |

Each agent was given a domain description and instructed to:
- Search arXiv, GitHub, company blogs, and conference proceedings (ICCV, NeurIPS, ASME IDETC, ICML, AAAI)
- Prioritize papers with available code or deployed products over pure theory
- Write 80–250 word descriptions per record
- Fill all schema fields (techniques, modality, physics domain, industry, year, URL)

### Phase 3 — Conference deep-dive (file `26-idetc-design-cognition-ai`)
11 records from ASME IDETC proceedings specifically on design cognition and human-AI design collaboration — a thinner but distinct subfield that general domain sweeps missed.

### Deduplication
`scripts/consolidate.py` merges all 27 raw files, deduplicates on `(name, organization)` exact match, and produces `consolidated.jsonl` (842 unique records from ~879 raw).

---

## Schema

Each record in `consolidated.jsonl`:

```json
{
  "id": "deepcad",
  "name": "DeepCAD",
  "organization": "Tsinghua University",
  "category": "program-cad",
  "year": 2021,
  "description": "RNN-based generative model for CAD command sequences...",
  "url": "https://github.com/ChrisWu1997/DeepCAD",
  "url_paper": "https://arxiv.org/abs/2105.09492",
  "techniques": ["transformer", "rnn", "vae"],
  "input_modality": "latent-vector",
  "output_modality": "cad-sequence",
  "physics_domain": "",
  "industry_application": ["mechanical-design"],
  "tags": []
}
```

Full schema → `SCHEMA.md`.

---

## Pipeline

After adding records to `raw/`, rebuild in order:

```bash
npm run pipeline
# expands to:
python scripts/consolidate.py        # merge + dedupe raw/*.jsonl → consolidated.jsonl
python scripts/embed.py              # embed records → embeddings.jsonl
python scripts/project-embeddings.py # UMAP → graph/embed-coords.json
python scripts/embed-all-entities.py # UMAP all nodes → graph/embed-coords-all.json
python scripts/build-graph.py        # structural + semantic edges → graph/graph-data.json
```

Graph is served from `graph/graph-data.json` by the Vercel-hosted `explorer.html`. No server-side code; everything is pre-built.

---

## Edge construction detail

### Structural edges (deterministic, `build-graph.py` Pass A)
Exploded directly from JSON fields. Every record contributes BUILT_BY, IN_CATEGORY, CONSUMES, PRODUCES, RELEASED_IN, OPERATES_ON, and APPLIED_TO edges. These 7 × 842 = 5,894 edges are complete and exact.

### Semantic edges (LLM-extracted, `build-graph.py` Pass B)
`build-graph.py` runs an LLM over each record's description to extract:
- **CITES** — mentions of other papers/tools by name ("...following DeepCAD...", "...extends FNO...")
- **BUILT_ON** — explicit dependency ("built on NVIDIA PhysicsNeMo", "uses DeepXDE")
- **BENCHMARKED_AGAINST** — comparison ("outperforms PointConv by 12%")
- **AUTHORED** — author names extracted from descriptions

### Cosine edges (`embed.py` → `build-graph.py`)
`embeddings.jsonl` stores 1536-dim text embeddings per record. Pairs with cosine similarity ≥ τ (tuned threshold) become SEMANTICALLY_NEAR edges. Currently 87 such edges — these surface unexpected adjacencies across different sub-fields.

---

## Explorer features

The live explorer (`explorer.html`, deployed to Vercel) is a single-file SPA using vis-network:

- **Left sidebar** — filter by category, organization, year, physics domain, modality, technique
- **Canvas** — vis-network force-directed layout; nodes colored by type; edges drawn
- **Right panel** — View Presets, Physics Lab sliders, graph stats
- **Click** — opens detail panel for the selected node (metadata, neighbors, links)
- **Double-click** — enters focus/explore mode, showing only the node's neighborhood
- **Embed button** — switches to UMAP scatter layout (2D projection of embeddings)
- **Right-click** — context menu (focus, explore, open URL)
- **Search (/)** — fuzzy search over names, descriptions, organizations

Initial positions are UMAP projections (from `graph/embed-coords.json`), so semantically similar projects start near each other and physics stabilizes quickly.

---

## What's not here (open work)

- **Person nodes are sparse** — 75 Person nodes, lightly populated; the `AUTHORED` edge only fires when an author's name appears in the description text
- **Venue nodes** — derived from URL host (`arxiv.org` → arXiv), not from structured paper metadata; conference proceedings hosted on ACM/IEEE often resolve to the same venue node
- **Citation quality** — CITES edges rely on description text, not parsed reference lists; Semantic Scholar API integration would improve recall significantly
- **Organization normalization** — 516 unique org strings with likely duplicates (e.g. "MIT" vs "Massachusetts Institute of Technology"); a canonical-name pass hasn't been run
- **Technique vocabulary** — 537 technique nodes with no controlled vocabulary; synonyms exist ("FNO" vs "fourier-neural-operator")
