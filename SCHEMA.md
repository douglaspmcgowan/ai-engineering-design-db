# AI for Engineering Design — Database Schema

A flat JSONL file of projects/models. One JSON object per line. Optional fields can be omitted, but `id`, `name`, `category`, `type`, and `description` are required.

```json
{
  "id": "kebab-case-slug",
  "name": "Project / model display name",
  "category": "text-to-cad | sketch-to-cad | image-to-cad | b-rep-learning | program-cad | cad-copilot | cad-agent | cad-reconstruction | topology-optimization | generative-3d-shape | text-to-3d | image-to-3d | neural-operator | physics-surrogate | physics-informed-nn | foundation-model-physics | differentiable-physics | scientific-ml | dfm-ai | dfam-ai | mesh-generation | process-monitoring-ml | ml-quoting | generative-materials | inverse-design-materials | ml-interatomic-potential | architected-materials | generative-platform | implicit-modeling | multi-disciplinary-optimization | optimization | ai-drawing | ai-simulation-prep | ai-plm | benchmark-dataset | eda-chip-design | pcb-design-ai | aec-construction-ai | robotics-mfg-ai | vision-inspection-ml | engineering-rag-chat | medical-engineering-ai | design-cognition-ai | human-ai-design-collab | other",
  "subcategory": "freeform secondary tag (e.g. 'transformer', 'diffusion', 'GNN')",
  "type": "commercial-product | academic-paper | open-source | research-project | benchmark-dataset",
  "organization": "Lab name, university, or company",
  "country": "ISO-2 country code or 'multi'",
  "year": 2024,
  "url_primary": "main project URL or product URL",
  "url_paper": "arXiv / journal / DOI URL if applicable",
  "url_github": "code repo URL if applicable",
  "description": "DENSE 80-250 word paragraph: what it does, the technique used, scale/results, status, and what makes it distinct. Should let a future reader understand the contribution without clicking out.",
  "techniques": ["transformer", "diffusion-model", "graph-neural-network"],
  "input_modality": "text | image | sketch | point-cloud | voxel | mesh | brep | parametric | program | physics-spec | none",
  "output_modality": "brep | mesh | sdf | voxel | program | parametric-cad | topology | material | scalar-field | vector-field | etc.",
  "physics_domain": "fluid | structural | thermal | electromagnetic | acoustic | multi-physics | atmospheric | ocean | molecular | none",
  "industry_application": ["automotive", "aerospace", "electronics", "medical", "consumer", "construction", "energy"],
  "status": "deployed-production | research-prototype | open-source-tool | discontinued | unknown",
  "license": "MIT | Apache-2 | proprietary | research-only | etc.",
  "tags": ["any other tags"]
}
```

## Required minimum
- `id` (lowercase kebab-case, unique across the database)
- `name`
- `category`
- `type`
- `description` (substantive — short stubs are not acceptable)

## Files
- `raw/*.jsonl` — per-domain agent outputs
- `consolidated.jsonl` — merged, deduped database (built by `scripts/consolidate.py`)
- `embeddings.jsonl` — `{id, vector}` per record (built by `scripts/embed.py`)
- `KNOWLEDGE-GRAPH.md` — proposed graph structure
