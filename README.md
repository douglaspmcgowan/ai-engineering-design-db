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
- `scripts/consolidate.py` — merge + dedupe
- `scripts/embed.py` — generate embeddings
- `KNOWLEDGE-GRAPH.md` — proposed graph structure with node/edge types
