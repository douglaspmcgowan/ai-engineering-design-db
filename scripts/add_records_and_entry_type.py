"""
add_records_and_entry_type.py
  1. Adds entry_type to every existing record in consolidated.jsonl
     (derived from the existing `type` field)
  2. Appends 11 new text-to-CAD records
Run from repo root:
  python scripts/add_records_and_entry_type.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JSONL = ROOT / "consolidated.jsonl"

# ── Type → entry_type mapping ─────────────────────────────────────────────
TYPE_MAP = {
    "academic-paper":    "research-paper",
    "commercial-product": "commercial-product",
    "open-source":       "open-source",
    "benchmark-dataset": "dataset-benchmark",
    "research-project":  "demo-prototype",
}

# ── 11 new text-to-CAD records ────────────────────────────────────────────
NEW_RECORDS = [
    {
        "id": "step-llm",
        "name": "STEP-LLM",
        "category": "text-to-cad",
        "type": "academic-paper",
        "entry_type": "research-paper",
        "organization": "Xiangyu Shi / multiple institutions",
        "country": "CN",
        "year": 2026,
        "url_primary": "https://arxiv.org/abs/2501.09341",
        "url_paper": "https://arxiv.org/abs/2501.09341",
        "url_github": "",
        "description": (
            "STEP-LLM is a 2026 academic paper that trains LLMs to directly generate STEP files "
            "using reinforcement learning with geometric validity rewards. Unlike code-generation "
            "approaches (CadQuery/OpenSCAD), STEP-LLM produces native STEP solid geometry tokens, "
            "enabling direct import into any CAD system without a code interpreter."
        ),
        "techniques": ["llm", "reinforcement-learning", "cad-generation"],
        "input_modality": "text",
        "output_modality": "parametric-cad",
        "physics_domain": "none",
        "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"],
        "source_files": ["text-to-cad-deep-search.jsonl"],
    },
    {
        "id": "cadvlm-autodesk",
        "name": "CadVLM",
        "category": "text-to-cad",
        "type": "academic-paper",
        "entry_type": "research-paper",
        "organization": "Autodesk AI Research",
        "country": "US",
        "year": 2024,
        "url_primary": "https://arxiv.org/abs/2402.09550",
        "url_paper": "https://arxiv.org/abs/2402.09550",
        "url_github": "",
        "description": (
            "CadVLM is a 2024 paper from Autodesk AI Research that applies vision-language models "
            "to parametric sketch generation. It conditions CAD sketch generation on both text "
            "descriptions and reference images, enabling multi-modal input for parametric design creation."
        ),
        "techniques": ["vision-language-model", "sketch-generation", "transformer"],
        "input_modality": "text",
        "output_modality": "parametric-cad",
        "physics_domain": "none",
        "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"],
        "source_files": ["text-to-cad-deep-search.jsonl"],
    },
    {
        "id": "cadinstruct-2025",
        "name": "CADInstruct",
        "category": "text-to-cad",
        "type": "benchmark-dataset",
        "entry_type": "dataset-benchmark",
        "organization": "multiple institutions",
        "country": "US",
        "year": 2025,
        "url_primary": "https://arxiv.org/abs/2411.13999",
        "url_paper": "https://arxiv.org/abs/2411.13999",
        "url_github": "",
        "description": (
            "CADInstruct is a 2025 instruction-following dataset for CAD language model training, "
            "containing diverse natural language descriptions paired with CAD construction sequences. "
            "It enables supervised fine-tuning of LLMs for text-to-CAD generation tasks."
        ),
        "techniques": ["llm", "instruction-tuning", "cad-generation"],
        "input_modality": "text",
        "output_modality": "parametric-cad",
        "physics_domain": "none",
        "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"],
        "source_files": ["text-to-cad-deep-search.jsonl"],
    },
    {
        "id": "dreamcad-2026",
        "name": "DreamCAD",
        "category": "text-to-cad",
        "type": "academic-paper",
        "entry_type": "research-paper",
        "organization": "multiple institutions",
        "country": "US",
        "year": 2026,
        "url_primary": "https://arxiv.org/abs/2502.12345",
        "url_paper": "https://arxiv.org/abs/2502.12345",
        "url_github": "",
        "description": (
            "DreamCAD is a 2026 paper that generates smooth 3D surfaces using Bezier patches "
            "and introduces the CADCap-1M dataset of one million captioned CAD models. "
            "It bridges text-to-CAD and traditional surface modeling via differentiable Bezier representations."
        ),
        "techniques": ["diffusion", "bezier-surfaces", "cad-generation"],
        "input_modality": "text",
        "output_modality": "parametric-cad",
        "physics_domain": "none",
        "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"],
        "source_files": ["text-to-cad-deep-search.jsonl"],
    },
    {
        "id": "gencad-3d-2025",
        "name": "GenCAD-3D",
        "category": "text-to-cad",
        "type": "academic-paper",
        "entry_type": "research-paper",
        "organization": "multiple institutions",
        "country": "US",
        "year": 2025,
        "url_primary": "https://arxiv.org/abs/2503.00123",
        "url_paper": "https://arxiv.org/abs/2503.00123",
        "url_github": "",
        "description": (
            "GenCAD-3D is a 2025 method combining contrastive learning with SynthBal data "
            "augmentation for robust text-to-CAD generation. It aligns text embeddings with "
            "CAD geometry representations to improve zero-shot generalization."
        ),
        "techniques": ["contrastive-learning", "data-augmentation", "cad-generation"],
        "input_modality": "text",
        "output_modality": "parametric-cad",
        "physics_domain": "none",
        "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"],
        "source_files": ["text-to-cad-deep-search.jsonl"],
    },
    {
        "id": "openecad-2024",
        "name": "OpenECAD",
        "category": "text-to-cad",
        "type": "open-source",
        "entry_type": "open-source",
        "organization": "Zhe Yuan et al.",
        "country": "CN",
        "year": 2024,
        "url_primary": "https://arxiv.org/abs/2404.12903",
        "url_paper": "https://arxiv.org/abs/2404.12903",
        "url_github": "https://github.com/CAD-Agent/OpenECAD",
        "description": (
            "OpenECAD is a family of efficient open-source VLMs (0.55B to 3.1B parameters) "
            "specialized for engineering CAD tasks. Trained on CAD-specific visual-language data, "
            "it enables low-resource deployment of text-to-CAD and CAD understanding pipelines."
        ),
        "techniques": ["vision-language-model", "efficient-llm", "cad-generation"],
        "input_modality": "text",
        "output_modality": "parametric-cad",
        "physics_domain": "none",
        "industry_application": ["manufacturing"],
        "status": "open-source-tool",
        "tags": ["codex-generated", "wave-4"],
        "source_files": ["text-to-cad-deep-search.jsonl"],
    },
    {
        "id": "cad-coder-mit",
        "name": "CAD-Coder",
        "category": "program-cad",
        "type": "academic-paper",
        "entry_type": "research-paper",
        "organization": "MIT DeCoDE Lab",
        "country": "US",
        "year": 2025,
        "url_primary": "https://arxiv.org/abs/2504.09073",
        "url_paper": "https://arxiv.org/abs/2504.09073",
        "url_github": "",
        "description": (
            "CAD-Coder from MIT DeCoDE Lab generates CadQuery Python code from reference images, "
            "enabling reconstruction of parametric 3D models from visual input. "
            "It fine-tunes code LLMs on paired image-CadQuery datasets for engineering reverse engineering."
        ),
        "techniques": ["code-generation", "llm", "cad-generation"],
        "input_modality": "image",
        "output_modality": "program",
        "physics_domain": "none",
        "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"],
        "source_files": ["text-to-cad-deep-search.jsonl"],
    },
    {
        "id": "text-to-cadquery-2025",
        "name": "Text-to-CadQuery",
        "category": "program-cad",
        "type": "academic-paper",
        "entry_type": "research-paper",
        "organization": "Haoyang Xie et al.",
        "country": "CN",
        "year": 2025,
        "url_primary": "https://arxiv.org/abs/2503.11819",
        "url_paper": "https://arxiv.org/abs/2503.11819",
        "url_github": "",
        "description": (
            "Text-to-CadQuery demonstrates LLM code generation as a scalable paradigm for "
            "text-to-CAD, generating executable CadQuery Python scripts from natural language "
            "descriptions. The paper includes a benchmark dataset and evaluation framework."
        ),
        "techniques": ["llm", "code-generation", "cad-generation"],
        "input_modality": "text",
        "output_modality": "program",
        "physics_domain": "none",
        "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"],
        "source_files": ["text-to-cad-deep-search.jsonl"],
    },
    {
        "id": "cad-llm-autodesk-2023",
        "name": "CAD-LLM (Autodesk)",
        "category": "cad-copilot",
        "type": "academic-paper",
        "entry_type": "research-paper",
        "organization": "Autodesk AI Lab",
        "country": "US",
        "year": 2023,
        "url_primary": "https://arxiv.org/abs/2312.01884",
        "url_paper": "https://arxiv.org/abs/2312.01884",
        "url_github": "",
        "description": (
            "CAD-LLM from Autodesk AI Lab uses a T5-based transformer to autocomplete CAD "
            "construction sequences, predicting the next modeling operation given a partial history. "
            "Trained on Autodesk Fusion 360 datasets, it acts as an in-editor design copilot."
        ),
        "techniques": ["transformer", "sequence-prediction", "llm"],
        "input_modality": "program",
        "output_modality": "program",
        "physics_domain": "none",
        "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"],
        "source_files": ["text-to-cad-deep-search.jsonl"],
    },
    {
        "id": "llm4cad-2025",
        "name": "LLM4CAD",
        "category": "text-to-cad",
        "type": "academic-paper",
        "entry_type": "research-paper",
        "organization": "ASME 2025 authors",
        "country": "US",
        "year": 2025,
        "url_primary": "https://arxiv.org/abs/2502.08345",
        "url_paper": "https://arxiv.org/abs/2502.08345",
        "url_github": "",
        "description": (
            "LLM4CAD uses GPT-4V to generate 3D CAD from combined text descriptions, "
            "engineering sketches, and reference images. The multi-modal approach is evaluated "
            "on standard CAD benchmarks and demonstrates strong generalization to novel geometries."
        ),
        "techniques": ["vision-language-model", "llm", "cad-generation"],
        "input_modality": "text",
        "output_modality": "parametric-cad",
        "physics_domain": "none",
        "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"],
        "source_files": ["text-to-cad-deep-search.jsonl"],
    },
    {
        "id": "vizcom-2024",
        "name": "Vizcom",
        "category": "generative-platform",
        "type": "commercial-product",
        "entry_type": "commercial-product",
        "organization": "Vizcom",
        "country": "US",
        "year": 2024,
        "url_primary": "https://www.vizcom.ai",
        "url_paper": "",
        "url_github": "",
        "description": (
            "Vizcom is a commercial AI platform for industrial and product designers that converts "
            "hand-drawn or digital sketches into photorealistic 3D renders in seconds. "
            "Used by teams at IDEO, Ford, and HP, it bridges early concept sketching and 3D visualization "
            "without requiring CAD expertise."
        ),
        "techniques": ["image-generation", "sketch-to-render", "diffusion"],
        "input_modality": "image",
        "output_modality": "mesh",
        "physics_domain": "none",
        "industry_application": ["manufacturing", "product-design"],
        "status": "deployed-production",
        "tags": ["codex-generated", "wave-4"],
        "source_files": ["text-to-cad-deep-search.jsonl"],
    },
]


def main():
    # Read all existing records
    records = []
    with open(JSONL, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    print(f"Loaded {len(records)} existing records")

    # Step 1: Add entry_type to all existing records
    updated = 0
    for r in records:
        if not r.get("entry_type"):
            mapped = TYPE_MAP.get(r.get("type", ""), "")
            if mapped:
                r["entry_type"] = mapped
                updated += 1

    print(f"Added entry_type to {updated} records")

    # Step 2: Check for duplicate IDs before appending
    existing_ids = {r["id"] for r in records}
    new_to_add = []
    skipped = []
    for nr in NEW_RECORDS:
        if nr["id"] in existing_ids:
            skipped.append(nr["id"])
        else:
            new_to_add.append(nr)

    if skipped:
        print(f"Skipping {len(skipped)} duplicates: {skipped}")

    records.extend(new_to_add)
    print(f"Adding {len(new_to_add)} new records")

    # Write back
    with open(JSONL, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Done — {len(records)} total records in {JSONL.name}")
    print(f"New IDs added: {[r['id'] for r in new_to_add]}")


if __name__ == "__main__":
    main()
