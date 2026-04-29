# Knowledge Graph Proposal — AI for Engineering Design

How to turn the flat JSONL database + embeddings into a queryable knowledge graph. Goal: a graph you can ask things like *"show me all neural-operator surrogates that NVIDIA's PhysicsNeMo enables, and which startups have built products on top of them"* or *"find every model that consumes B-rep input and outputs a parametric CAD program"*.

---

## 1. Node types

Each `consolidated.jsonl` record becomes one **Project / Model / Tool node**, but we explode several denormalized fields out into their own node types. This is what makes a graph useful (the connections) versus a tagged list.

| Node type | Source | Examples |
| --- | --- | --- |
| **Project** | one per record in `consolidated.jsonl` | `deepcad`, `mattergen`, `monolith-ai`, `simscale-foundation-pump-model` |
| **Organization** | unique `organization` strings | `MIT`, `NVIDIA`, `Microsoft Research`, `UC Berkeley Co-Design Lab` |
| **Person** | extracted from descriptions / paper authors (later pass) | `Karniadakis`, `Anandkumar`, `Goucher-Lambert` |
| **Technique** | items in `techniques[]` array | `transformer`, `diffusion-model`, `fourier-neural-operator`, `equivariant-gnn` |
| **Modality** | unique `input_modality` and `output_modality` values | `text`, `b-rep`, `mesh`, `sdf`, `point-cloud` |
| **Physics domain** | `physics_domain` field | `fluid`, `structural`, `thermal`, `electromagnetic`, `multi-physics` |
| **Industry** | `industry_application[]` | `automotive`, `aerospace`, `medical` |
| **Category / School** | `category` field + the 34 schools in the AI-in-Design-Map site | `text-to-cad`, `neural-operator`; `discourse-mining`, `physics-first-generative` |
| **Venue** | extracted from `url_paper` host (later pass) | `arXiv`, `ICCV`, `NeurIPS`, `ASME-IDETC`, `Nature` |
| **Year** | `year` integer | `2019`, `2020`, ... `2026` |
| **Funding round** | (optional, future pass for commercial rows) | `seed`, `series-a`, `series-b` |

Each node carries:
- `id` (uuid or composite slug)
- `label` (display name)
- `type` (one of the above)
- `props` (free dict — copies of source fields)

---

## 2. Edge types

Edges are where the value lives. Build these in two passes — **structural** edges from the JSON record, **inferred** edges from text + embeddings.

### Pass A — structural edges (cheap, deterministic)

| Edge | From → To | Source field |
| --- | --- | --- |
| `BUILT_BY` | Project → Organization | `organization` |
| `IN_CATEGORY` | Project → Category | `category` |
| `USES_TECHNIQUE` | Project → Technique | `techniques[]` |
| `CONSUMES` | Project → Modality | `input_modality` |
| `PRODUCES` | Project → Modality | `output_modality` |
| `OPERATES_ON` | Project → Physics domain | `physics_domain` |
| `APPLIED_TO` | Project → Industry | `industry_application[]` |
| `PUBLISHED_AT` | Project → Venue | derived from `url_paper` host |
| `RELEASED_IN` | Project → Year | `year` |
| `IN_SCHOOL` | Project → School-of-thought | `tags[]` containing `school:<slug>` |

### Pass B — inferred / semantic edges (LLM + embeddings)

| Edge | How to extract |
| --- | --- |
| `CITES` | Parse description text (and the actual paper PDFs in a deeper pass) for "...follows DeepCAD..." / "...builds on FNO..." — match cited names to project IDs. |
| `BUILT_ON` | Detect "built on PhysicsNeMo / Modulus / DeepXDE / Genesis" patterns. Strong signal in the description text. |
| `BENCHMARKED_AGAINST` | "outperforms X by Y%" patterns. |
| `COMPETES_WITH` | Same `category` + same `output_modality` + same year-window → candidate; LLM confirms in a small batch verification step. |
| `EVOLVES_FROM` | Project name shares stem with another (`SkexGen` → `SkexGen-2`); confirm by description overlap. |
| `SEMANTICALLY_NEAR` | Cosine similarity in `embeddings.jsonl` ≥ τ (start τ=0.75 for `all-MiniLM-L6-v2`, tune). Edge weight = similarity score. This is the catch-all edge that surfaces unexpected adjacencies. |
| `MENTIONED_BY_PERSON` | from a later pass over your LinkedIn inbox, X follow list, and newsletter scrape. |

Pass B is iterative — start with the cheap regex-style ones (`BUILT_ON`, `BENCHMARKED_AGAINST`) since most descriptions explicitly name predecessors.

---

## 3. Construction pipeline

```
raw/*.jsonl
   │   (consolidate.py)
   ▼
consolidated.jsonl  ──▶  embed.py  ──▶  embeddings.jsonl
   │                                       │
   │   (build-graph.py — pass A)            │   (build-graph.py — pass B-1: cosine ≥ τ)
   ▼                                       │
graph-passA.gexf   ◀────────────────────────┘
   │
   │   (extract-citations.py — LLM batch over descriptions)
   ▼
graph-passB.gexf  ──▶  Neo4j / NetworkX / Cytoscape
```

Suggested file outputs:
- `graph/nodes.csv` — `id, type, label, ...props`
- `graph/edges.csv` — `source, target, type, weight, evidence`
- `graph/graph.gexf` — Gephi-importable single file
- `graph/graph.cypher` — Neo4j load script
- `graph/graph.html` — pyvis interactive HTML (for quick sharing)

---

## 4. Storage / query layer — pick one

| Option | When | Why |
| --- | --- | --- |
| **NetworkX in memory + pickle** | < 5k nodes, exploratory only | Zero infra, fastest to iterate. Use this first. |
| **Neo4j Aura free tier** | want Cypher queries + visual UI | Built for this. `MATCH (p:Project)-[:USES_TECHNIQUE]->(t {label:'fourier-neural-operator'}) RETURN p.label` reads naturally. Free tier handles ~200k nodes. |
| **DuckDB graph extension** | want SQL + graph in one engine | Lightweight; great if you also keep tabular views of the database. |
| **Memgraph** | Neo4j-compatible, faster, OSS-friendly | If you outgrow Aura free tier. |
| **Kuzu** | embedded, OSS, SQL+Cypher | Nice middle ground; pip-installable. |

**Recommendation:** start with NetworkX → pyvis HTML for instant visualization. If the graph proves useful, port to **Kuzu** (embedded, no server, supports Cypher) — that gives you durable queries without paying for Neo4j Aura.

---

## 5. Visualizations worth building

1. **Category × technique heatmap** — which architectural choices dominate which sub-fields? (e.g. diffusion is now eating text-to-CAD; transformers dominate B-rep learning; FNO dominates surrogates).
2. **Citation timeline** — papers as nodes on a year axis, edges = `CITES` or `BUILT_ON`. Reveals lineage trees (e.g. DeepCAD → SkexGen → CAD-MLLM → Text2CAD).
3. **Commercial ↔ academic bridge graph** — bipartite Project graph, color by `type`. Edges via `BUILT_ON`. Shows which papers got productized and by whom.
4. **Org × industry sankey** — flows from research labs → industries via the projects they spawned.
5. **Embedding scatter (t-SNE / UMAP)** — color by category. Reveals which categories overlap semantically (e.g. `physics-informed-nn` vs `neural-operator` vs `physics-surrogate` should cluster together — confirming the field's natural shape vs our taxonomy).
6. **Whitespace map** — for each pair of `(input_modality, output_modality)` and `(physics_domain, industry)`, count projects. Empty cells = whitespace candidates.

---

## 6. Open questions to resolve before scaling the graph

- **Granularity of "Project."** Is `MatterGen` one node, or `MatterGen-base` + `MatterGen-fine-tuned-Li-batteries` two nodes? Default: one node per record; subvariants live in `tags`.
- **Authority on `Technique`.** Many papers use bespoke names ("HyperFNO"). Need a controlled vocabulary; build it incrementally and store messy-name → canonical-name mapping in `graph/technique-aliases.json`.
- **Citation extraction quality.** First pass is regex on descriptions ("builds on DeepCAD"). Later: parse actual papers via `arxiv` API + Semantic Scholar API. Citations are the most useful edges and the most expensive to extract well.
- **Person nodes.** Worth doing only after you have ~500+ projects; below that, the graph isn't dense enough to matter.

---

## 7. Concrete next steps after the database stabilizes

1. Run `consolidate.py` → confirm count and schema.
2. Run `embed.py` (sentence-transformers) → confirm dim.
3. Write `scripts/build-graph.py` — Pass A only (structural edges from JSON).
4. Run `nearest.py --query "..."` and visually QA — does k-nearest match your intuition?
5. Add Pass B-1 (cosine semantic edges with τ).
6. Add Pass B-2 (LLM batch over descriptions to extract citations / built-on edges) — use a cheap model in batches of 50.
7. Export to pyvis HTML, share, see what queries you actually want.
8. If queries become routine, stand up Kuzu and write 5–10 saved Cypher queries.
