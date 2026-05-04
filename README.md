# AI for Engineering Design — Database

A systematic catalog of AI/ML models, tools, and academic projects for engineering design — text-to-CAD, generative topology, simulation surrogates, neural operators, generative materials, manufacturability AI, CAD copilots, and adjacent areas.

## Goal

Hundreds of entries across the field, each with:
- A solid 80–250 word description
- Categorical tags (modality, technique, physics domain)
- Source URL (paper, product, or repo)

Then: embeddings + a proposed knowledge graph.

## Layout

- `SCHEMA.md` — record schema
- `raw/` — per-domain JSONL files from research agents
- `consolidated.jsonl` — merged + deduped database
- `embeddings.jsonl` — vector embeddings per record
- `graph/graph-data.json` — vis-network graph loaded by explorer.html
- `scripts/` — data pipeline and utility scripts
- `explorer.html` — single-file SPA graph explorer (deployed on Vercel)

## Pipeline

After adding records to `raw/`, rebuild the graph in order:

```bash
npm run pipeline
# expands to:
python scripts/consolidate.py        # merge + dedupe raw/*.jsonl → consolidated.jsonl
python scripts/embed.py              # embed records → embeddings.jsonl
python scripts/project-embeddings.py # UMAP projection → graph/embed-coords.json
python scripts/embed-all-entities.py # UMAP all nodes → graph/embed-coords-all.json
python scripts/build-graph.py        # assemble → graph/graph-data.json
```

## Testing

```bash
npm test              # fast unit tests (mocked vis-network)
npm run test:all      # all test suites
npm run test:visual   # visual/physics tests (starts HTTP server automatically)
```
