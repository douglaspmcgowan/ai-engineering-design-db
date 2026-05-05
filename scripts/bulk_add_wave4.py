"""
bulk_add_wave4.py  — wave-4 deep-search additions + data quality fixes
1. Add ~59 new records found by targeted deep searches
2. Split `program` output_modality → cad-program / toolpath / workflow-script
3. Deduplicate technique slugs (physics-informed-neural-networks → physics-informed-nn, etc.)
4. Normalize organisation names (Autodesk AI Lab → Autodesk Research, etc.)
Run from repo root:
  python scripts/bulk_add_wave4.py
"""

import json, re
from pathlib import Path

ROOT  = Path(__file__).resolve().parent.parent
JSONL = ROOT / "consolidated.jsonl"

# ── helpers ───────────────────────────────────────────────────────────────────
def slug(s):
    s = re.sub(r"[^\w\s-]", "", s.lower().strip())
    s = re.sub(r"[\s_]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")[:80]

# ── new records ───────────────────────────────────────────────────────────────
NEW_RECORDS = [

    # ── TOPOLOGY OPTIMIZATION ─────────────────────────────────────────────────
    {
        "id": "oat-optimize-any-topology",
        "name": "OAT — Optimize Any Topology",
        "category": "topology-optimization",
        "type": "academic-paper", "entry_type": "research-paper",
        "organization": "MIT (anonymous, NeurIPS 2025)",
        "country": "US", "year": 2025,
        "url_primary": "https://arxiv.org/abs/2510.23667",
        "url_paper":   "https://arxiv.org/abs/2510.23667", "url_github": "",
        "description": "The first foundation model for structural topology optimization — a resolution- and shape-agnostic autoencoder with implicit neural-field decoder that predicts minimum-compliance layouts for arbitrary aspect ratios, volume fractions, loads, and fixtures in one shot without retraining.",
        "techniques": ["implicit-function", "foundation-model-physics", "topology-optimization"],
        "input_modality": "mesh", "output_modality": "topology",
        "physics_domain": "structural", "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"], "source_files": ["topology-opt-deep-search.jsonl"],
    },
    {
        "id": "topodiff-guided-diffusion-topology-optimization",
        "name": "TopoDiff",
        "category": "topology-optimization",
        "type": "academic-paper", "entry_type": "research-paper",
        "organization": "MIT DeCoDe Lab",
        "country": "US", "year": 2023,
        "url_primary": "https://arxiv.org/abs/2208.09591",
        "url_paper":   "https://arxiv.org/abs/2208.09591",
        "url_github":  "https://github.com/francoismaze/topodiff",
        "description": "A conditional diffusion model with surrogate-based guidance for topology optimization; reduces compliance error 8x and infeasible samples 11x vs prior GAN/VAE baselines; introduced the first large public 2D topology-optimization dataset with physics fields (33 k structures).",
        "techniques": ["diffusion-model", "topology-optimization", "surrogate-modeling"],
        "input_modality": "mesh", "output_modality": "topology",
        "physics_domain": "structural", "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"], "source_files": ["topology-opt-deep-search.jsonl"],
    },
    {
        "id": "trajectory-alignment-diffusion-topology-optimization",
        "name": "Trajectory Alignment Diffusion for TO",
        "category": "topology-optimization",
        "type": "academic-paper", "entry_type": "research-paper",
        "organization": "IBM Research / DTU / MIT",
        "country": "US", "year": 2023,
        "url_primary": "https://arxiv.org/abs/2305.18470",
        "url_paper":   "https://arxiv.org/abs/2305.18470", "url_github": "",
        "description": "Aligns diffusion model sampling trajectories with physics-based SIMP optimization trajectories at NeurIPS 2023, eliminating external surrogates while halving inference cost; bridges iterative physics solvers and generative modeling.",
        "techniques": ["diffusion-model", "topology-optimization"],
        "input_modality": "mesh", "output_modality": "topology",
        "physics_domain": "structural", "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"], "source_files": ["topology-opt-deep-search.jsonl"],
    },
    {
        "id": "nito-neural-implicit-topology-optimization",
        "name": "NITO",
        "category": "topology-optimization",
        "type": "academic-paper", "entry_type": "research-paper",
        "organization": "MIT DeCoDe Lab",
        "country": "US", "year": 2024,
        "url_primary": "https://arxiv.org/abs/2402.05073",
        "url_paper":   "https://arxiv.org/abs/2402.05073", "url_github": "",
        "description": "Resolution-free and domain-agnostic topology optimization via neural implicit fields with Boundary-Point Order-Invariant MLP, outperforming diffusion baselines in structural efficiency by 7x; handles arbitrary domain shapes at test time without retraining.",
        "techniques": ["implicit-function", "topology-optimization"],
        "input_modality": "mesh", "output_modality": "topology",
        "physics_domain": "structural", "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"], "source_files": ["topology-opt-deep-search.jsonl"],
    },
    {
        "id": "to-node-topology-optimization-neural-ode",
        "name": "TO-NODE",
        "category": "topology-optimization",
        "type": "academic-paper", "entry_type": "research-paper",
        "organization": "Penn State",
        "country": "US", "year": 2024,
        "url_primary": "https://onlinelibrary.wiley.com/doi/full/10.1002/nme.7428",
        "url_paper":   "https://onlinelibrary.wiley.com/doi/full/10.1002/nme.7428", "url_github": "",
        "description": "Reframes SIMP design-variable updates as integration of a neural ordinary differential equation, treating topology optimization as a continuous-time dynamical system; enables full-resolution TO paths in seconds with better cross-domain generalization.",
        "techniques": ["topology-optimization", "physics-informed-nn"],
        "input_modality": "mesh", "output_modality": "topology",
        "physics_domain": "structural", "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"], "source_files": ["topology-opt-deep-search.jsonl"],
    },
    {
        "id": "gento-diverse-topology-optimization-neural-fields",
        "name": "GenTO — Diverse TO via Modulated Neural Fields",
        "category": "topology-optimization",
        "type": "academic-paper", "entry_type": "research-paper",
        "organization": "multiple institutions",
        "country": "US", "year": 2025,
        "url_primary": "https://arxiv.org/abs/2502.13174",
        "url_paper":   "https://arxiv.org/abs/2502.13174", "url_github": "",
        "description": "Data-free method using modulated neural fields with a solver-in-the-loop and an explicit diversity constraint, generating a population of structurally near-optimal but geometrically varied designs in parallel — faster than any prior multi-solution TO method.",
        "techniques": ["implicit-function", "topology-optimization"],
        "input_modality": "mesh", "output_modality": "topology",
        "physics_domain": "structural", "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"], "source_files": ["topology-opt-deep-search.jsonl"],
    },
    {
        "id": "meta-neural-topology-optimization",
        "name": "Meta-Neural Topology Optimization",
        "category": "topology-optimization",
        "type": "academic-paper", "entry_type": "research-paper",
        "organization": "multiple institutions",
        "country": "US", "year": 2025,
        "url_primary": "https://arxiv.org/abs/2502.01830",
        "url_paper":   "https://arxiv.org/abs/2502.01830", "url_github": "",
        "description": "Applies MAML/Reptile meta-learning to neural reparameterization-based topology optimization, learning cross-task initializations that reduce average iterations by 33.6% and succeed in 74.1% of cross-resolution transfer tasks.",
        "techniques": ["topology-optimization", "transfer-learning"],
        "input_modality": "mesh", "output_modality": "topology",
        "physics_domain": "structural", "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"], "source_files": ["topology-opt-deep-search.jsonl"],
    },
    {
        "id": "dl4to-selto-dataset",
        "name": "DL4TO + SELTO Dataset",
        "category": "topology-optimization",
        "type": "open-source", "entry_type": "open-source",
        "organization": "University of Bremen",
        "country": "DE", "year": 2023,
        "url_primary": "https://github.com/dl4to/dl4to",
        "url_paper":   "https://link.springer.com/chapter/10.1007/978-3-031-38271-0_54",
        "url_github":  "https://github.com/dl4to/dl4to",
        "description": "PyTorch library for 3D topology optimization with differentiable SIMP physics and plug-in neural network architectures; includes SELTO, the first standardized 3D TO benchmark dataset (four subsets: disc/sphere x simple/complex) for reproducible evaluation.",
        "techniques": ["topology-optimization", "surrogate-modeling"],
        "input_modality": "mesh", "output_modality": "topology",
        "physics_domain": "structural", "industry_application": ["manufacturing"],
        "status": "open-source-tool",
        "tags": ["codex-generated", "wave-4"], "source_files": ["topology-opt-deep-search.jsonl"],
    },
    {
        "id": "gigala-rl-topology-optimization",
        "name": "Gigala",
        "category": "topology-optimization",
        "type": "open-source", "entry_type": "open-source",
        "organization": "Giorgi Tskhondia (independent)",
        "country": "GE", "year": 2024,
        "url_primary": "https://gigala.io",
        "url_paper":   "", "url_github": "https://github.com/gigatskhondia/gigala",
        "description": "Open-source Python tool for 2D/3D structural topology optimization using reinforcement learning and genetic algorithms without requiring labeled training data; one of very few RL-only TO tools with explicit stochastic-loading support.",
        "techniques": ["reinforcement-learning", "topology-optimization"],
        "input_modality": "mesh", "output_modality": "topology",
        "physics_domain": "structural", "industry_application": ["manufacturing"],
        "status": "open-source-tool",
        "tags": ["codex-generated", "wave-4"], "source_files": ["topology-opt-deep-search.jsonl"],
    },
    {
        "id": "physicsx-airplane-large-physics-model",
        "name": "PhysicsX Ai.rplane",
        "category": "physics-surrogate",
        "type": "commercial-product", "entry_type": "commercial-product",
        "organization": "PhysicsX",
        "country": "UK", "year": 2024,
        "url_primary": "https://www.physicsx.ai",
        "url_paper":   "", "url_github": "",
        "description": "A free-access Large Physics Model trained on 25 million Siemens Simcenter shapes that infers aero performance, flight stability, and structural stress for any flying geometry in under a second; enables generative shape exploration for aerospace structural design.",
        "techniques": ["neural-operator", "surrogate-modeling"],
        "input_modality": "mesh", "output_modality": "scalar-field",
        "physics_domain": "structural", "industry_application": ["aerospace"],
        "status": "public-preview",
        "tags": ["codex-generated", "wave-4"], "source_files": ["topology-opt-deep-search.jsonl"],
    },

    # ── IMPLICIT MODELING ─────────────────────────────────────────────────────
    {
        "id": "neurcadrecon-neural-sdf-cad",
        "name": "NeurCADRecon",
        "category": "implicit-modeling",
        "type": "academic-paper", "entry_type": "research-paper",
        "organization": "Shandong University / University of Hong Kong / Texas A&M",
        "country": "CN", "year": 2024,
        "url_primary": "https://arxiv.org/abs/2404.13420",
        "url_paper":   "https://arxiv.org/abs/2404.13420", "url_github": "",
        "description": "Self-supervised neural SDF that reconstructs piecewise-flat CAD surfaces from point clouds by enforcing zero Gaussian curvature as a developability constraint, recovering sharp edges and flat faces characteristic of engineering geometry.",
        "techniques": ["implicit-function", "scan-to-cad"],
        "input_modality": "point-cloud", "output_modality": "brep",
        "physics_domain": "none", "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"], "source_files": ["implicit-modeling-deep-search.jsonl"],
    },
    {
        "id": "brepgen-diffusion-brep-generation",
        "name": "BRepGen",
        "category": "b-rep-learning",
        "type": "academic-paper", "entry_type": "research-paper",
        "organization": "Autodesk Research / Simon Fraser University",
        "country": "US", "year": 2024,
        "url_primary": "https://www.research.autodesk.com/publications/brepgen/",
        "url_paper":   "https://www.research.autodesk.com/publications/brepgen/", "url_github": "",
        "description": "Transformer-based diffusion model that generates CAD B-rep solids by denoising a hierarchical geometry tree (solid → face → edge → vertex); the first generative model to produce complete, structured B-rep topology from a latent diffusion process.",
        "techniques": ["diffusion-model", "transformer"],
        "input_modality": "text", "output_modality": "brep",
        "physics_domain": "none", "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"], "source_files": ["implicit-modeling-deep-search.jsonl"],
    },
    {
        "id": "hnc-cad-hierarchical-neural-coding",
        "name": "HNC-CAD",
        "category": "b-rep-learning",
        "type": "academic-paper", "entry_type": "research-paper",
        "organization": "Autodesk Research / Simon Fraser University",
        "country": "US", "year": 2023,
        "url_primary": "https://arxiv.org/abs/2307.00149",
        "url_paper":   "https://arxiv.org/abs/2307.00149", "url_github": "",
        "description": "Three-level hierarchical neural coding system using a masked-skip VQ-VAE and cascaded auto-regressive transformers to generate and complete CAD models from partial design specifications.",
        "techniques": ["transformer", "implicit-function"],
        "input_modality": "program", "output_modality": "brep",
        "physics_domain": "none", "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"], "source_files": ["implicit-modeling-deep-search.jsonl"],
    },
    {
        "id": "partsdf-part-based-implicit-representation",
        "name": "PartSDF",
        "category": "implicit-modeling",
        "type": "academic-paper", "entry_type": "research-paper",
        "organization": "EPFL",
        "country": "CH", "year": 2025,
        "url_primary": "https://arxiv.org/abs/2502.12985",
        "url_paper":   "https://arxiv.org/abs/2502.12985", "url_github": "",
        "description": "Part-based implicit neural representation that models composite 3D shapes as independently controllable SDF parts trained from global shape supervision alone, enabling structured shape optimization and part-level editing.",
        "techniques": ["implicit-function"],
        "input_modality": "mesh", "output_modality": "implicit-field",
        "physics_domain": "none", "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"], "source_files": ["implicit-modeling-deep-search.jsonl"],
    },
    {
        "id": "neuronurbs-neural-nurbs-encoding",
        "name": "NeuroNURBS",
        "category": "b-rep-learning",
        "type": "academic-paper", "entry_type": "research-paper",
        "organization": "Leiden University",
        "country": "NL", "year": 2024,
        "url_primary": "https://arxiv.org/abs/2411.10848",
        "url_paper":   "https://arxiv.org/abs/2411.10848", "url_github": "",
        "description": "Encodes NURBS surface parameters for CAD B-rep solids directly with a neural network, reducing GPU memory consumption by 86.7% relative to UV-grid baselines while matching geometric fidelity for learning on large-scale CAD datasets.",
        "techniques": ["implicit-function", "neural-operator"],
        "input_modality": "brep", "output_modality": "brep",
        "physics_domain": "none", "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"], "source_files": ["implicit-modeling-deep-search.jsonl"],
    },
    {
        "id": "csg-neural-sdfs-boolean-operations",
        "name": "Constructive Solid Geometry on Neural SDFs",
        "category": "implicit-modeling",
        "type": "academic-paper", "entry_type": "research-paper",
        "organization": "Cornell University / University of Toronto",
        "country": "US", "year": 2023,
        "url_primary": "https://dl.acm.org/doi/10.1145/3610548.3618170",
        "url_paper":   "https://dl.acm.org/doi/10.1145/3610548.3618170", "url_github": "",
        "description": "Derives a closest-point loss regularizer that preserves exact SDF properties after Boolean CSG operations on neural signed distance fields, enabling CAD-like geometry composition with neural implicit representations at SIGGRAPH Asia 2023.",
        "techniques": ["implicit-function"],
        "input_modality": "mesh", "output_modality": "implicit-field",
        "physics_domain": "none", "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"], "source_files": ["implicit-modeling-deep-search.jsonl"],
    },
    {
        "id": "toinr-topology-optimization-implicit-neural",
        "name": "TOINR",
        "category": "topology-optimization",
        "type": "academic-paper", "entry_type": "research-paper",
        "organization": "National University of Defense Technology, China",
        "country": "CN", "year": 2023,
        "url_primary": "https://www.sciencedirect.com/science/article/abs/pii/S0045782523001767",
        "url_paper":   "https://www.sciencedirect.com/science/article/abs/pii/S0045782523001767", "url_github": "",
        "description": "Introduces neural implicit representations into topology optimization by parameterizing the topology description function with a SIREN-based MLP, enabling continuous boundary representation without mesh resolution constraints.",
        "techniques": ["implicit-function", "topology-optimization", "physics-informed-nn"],
        "input_modality": "mesh", "output_modality": "topology",
        "physics_domain": "structural", "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"], "source_files": ["implicit-modeling-deep-search.jsonl"],
    },
    {
        "id": "touchsdf-tactile-sdf-reconstruction",
        "name": "TouchSDF",
        "category": "implicit-modeling",
        "type": "academic-paper", "entry_type": "research-paper",
        "organization": "University of Bristol / Google DeepMind",
        "country": "UK", "year": 2023,
        "url_primary": "https://arxiv.org/abs/2311.12602",
        "url_paper":   "https://arxiv.org/abs/2311.12602", "url_github": "",
        "description": "Combines a CNN with DeepSDF's implicit neural representation to reconstruct 3D object surface geometry from vision-based tactile sensor readings; the first implicit-field method for tactile-driven shape reconstruction validated on real robotics hardware.",
        "techniques": ["implicit-function", "robotics"],
        "input_modality": "image", "output_modality": "implicit-field",
        "physics_domain": "none", "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"], "source_files": ["implicit-modeling-deep-search.jsonl"],
    },

    # ── SKETCH-TO-CAD ─────────────────────────────────────────────────────────
    {
        "id": "sketch2cad-sequential-cad-modeling-by-sketching",
        "name": "Sketch2CAD (UCL 2020)",
        "category": "sketch-to-cad",
        "type": "academic-paper", "entry_type": "research-paper",
        "organization": "UCL / Inria / Microsoft Research Asia",
        "country": "UK", "year": 2020,
        "url_primary": "https://arxiv.org/abs/2009.04927",
        "url_paper":   "https://arxiv.org/abs/2009.04927", "url_github": "",
        "description": "Users sketch incremental edits onto a partial CAD model; a deep neural network interprets each sketch in context, identifies the intended CAD operation (extrude, cut, fillet), and estimates its parameters to produce an editable CAD operation sequence.",
        "techniques": ["transformer", "scan-to-cad"],
        "input_modality": "image", "output_modality": "parametric-cad",
        "physics_domain": "none", "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"], "source_files": ["sketch-to-cad-deep-search.jsonl"],
    },
    {
        "id": "free2cad-parsing-freehand-drawings",
        "name": "Free2CAD",
        "category": "sketch-to-cad",
        "type": "academic-paper", "entry_type": "research-paper",
        "organization": "UCL / Inria / Microsoft Research Asia / Adobe Research",
        "country": "UK", "year": 2022,
        "url_primary": "https://dl.acm.org/doi/10.1145/3528223.3530133",
        "url_paper":   "https://dl.acm.org/doi/10.1145/3528223.3530133", "url_github": "",
        "description": "Takes an ordered sequence of freehand strokes and translates them into a parametric CAD command sequence using a Transformer; groups strokes into per-operation clusters, then geometrically fits parameters for each operation; published at SIGGRAPH 2022.",
        "techniques": ["transformer"],
        "input_modality": "image", "output_modality": "parametric-cad",
        "physics_domain": "none", "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"], "source_files": ["sketch-to-cad-deep-search.jsonl"],
    },
    {
        "id": "sfmcad-unsupervised-sketch-feature-modeling",
        "name": "SfmCAD",
        "category": "sketch-to-cad",
        "type": "academic-paper", "entry_type": "research-paper",
        "organization": "CVPR 2024",
        "country": "US", "year": 2024,
        "url_primary": "https://openaccess.thecvf.com/content/CVPR2024/papers/Li_SfmCAD_Unsupervised_CAD_Reconstruction_by_Learning_Sketch-based_Feature_Modeling_Operations_CVPR_2024_paper.pdf",
        "url_paper":   "https://openaccess.thecvf.com/content/CVPR2024/papers/Li_SfmCAD_Unsupervised_CAD_Reconstruction_by_Learning_Sketch-based_Feature_Modeling_Operations_CVPR_2024_paper.pdf",
        "url_github": "",
        "description": "Unsupervised method that learns sketch-based feature modeling operations (extrude/cut primitives used in real CAD software) directly from raw 3D shapes without labeled operation sequences, producing editable parametric CAD representations; CVPR 2024.",
        "techniques": ["implicit-function", "scan-to-cad"],
        "input_modality": "mesh", "output_modality": "parametric-cad",
        "physics_domain": "none", "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"], "source_files": ["sketch-to-cad-deep-search.jsonl"],
    },
    {
        "id": "drawing2cad-engineering-drawings-to-parametric",
        "name": "Drawing2CAD",
        "category": "sketch-to-cad",
        "type": "academic-paper", "entry_type": "research-paper",
        "organization": "Hangzhou Dianzi University / Zhejiang University / USTC",
        "country": "CN", "year": 2025,
        "url_primary": "https://arxiv.org/abs/2508.18733",
        "url_paper":   "https://arxiv.org/abs/2508.18733", "url_github": "",
        "description": "Converts 2D vector engineering drawings (SVG, isometric/orthographic) into parametric CAD operation sequences via a dual-decoder Transformer with soft-target loss; introduces CAD-VGDrawing dataset of 150K+ paired drawings and parametric models.",
        "techniques": ["transformer", "code-generation"],
        "input_modality": "image", "output_modality": "parametric-cad",
        "physics_domain": "none", "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"], "source_files": ["sketch-to-cad-deep-search.jsonl"],
    },

    # ── IMAGE-TO-CAD ──────────────────────────────────────────────────────────
    {
        "id": "img2cad-vlm-conditional-factorization",
        "name": "Img2CAD (VLM, Stanford)",
        "category": "image-to-cad",
        "type": "academic-paper", "entry_type": "research-paper",
        "organization": "Stanford University / USC",
        "country": "US", "year": 2024,
        "url_primary": "https://arxiv.org/abs/2408.01437",
        "url_paper":   "https://arxiv.org/abs/2408.01437", "url_github": "",
        "description": "Decomposes image-to-CAD into two stages: a VLM predicts the discrete command structure, then a semantic-conditioned Transformer predicts continuous attribute values; outputs editable sketch-extrude CAD programs; accepted SIGGRAPH Asia 2025.",
        "techniques": ["vision-language-model", "transformer"],
        "input_modality": "image", "output_modality": "parametric-cad",
        "physics_domain": "none", "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"], "source_files": ["image-to-cad-deep-search.jsonl"],
    },
    {
        "id": "img2cad-structured-visual-geometry-2024",
        "name": "Img2CAD (Structured Visual Geometry)",
        "category": "image-to-cad",
        "type": "academic-paper", "entry_type": "research-paper",
        "organization": "multiple institutions",
        "country": "US", "year": 2024,
        "url_primary": "https://arxiv.org/abs/2410.03417",
        "url_paper":   "https://arxiv.org/abs/2410.03417", "url_github": "",
        "description": "Single-image-conditioned CAD generation that uses Structured Visual Geometry (vectorized wireframes) as intermediate representation; outputs sketch-and-extrude command sequences parseable to B-rep; introduces ABC-mono (200K+ models) and KOCAD datasets.",
        "techniques": ["transformer", "computer-vision"],
        "input_modality": "image", "output_modality": "parametric-cad",
        "physics_domain": "none", "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"], "source_files": ["image-to-cad-deep-search.jsonl"],
    },
    {
        "id": "point2cad-cvpr2024",
        "name": "Point2CAD",
        "category": "image-to-cad",
        "type": "academic-paper", "entry_type": "research-paper",
        "organization": "ETH Zurich",
        "country": "CH", "year": 2024,
        "url_primary": "https://arxiv.org/abs/2312.04962",
        "url_paper":   "https://arxiv.org/abs/2312.04962",
        "url_github":  "https://github.com/prs-eth/point2cad",
        "description": "Takes a 3D point cloud and reverse-engineers it into a full structured CAD model with faces, edges, and corners; segments cloud into face clusters, fits analytic primitives or neural implicit freeform surfaces, then builds topology; state-of-the-art on ABC benchmark at CVPR 2024.",
        "techniques": ["implicit-function", "scan-to-cad"],
        "input_modality": "point-cloud", "output_modality": "brep",
        "physics_domain": "none", "industry_application": ["manufacturing", "reverse-engineering"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"], "source_files": ["image-to-cad-deep-search.jsonl"],
    },
    {
        "id": "cad2program-2d-drawings-to-3d-parametric",
        "name": "CAD2Program",
        "category": "image-to-cad",
        "type": "academic-paper", "entry_type": "research-paper",
        "organization": "Manycore Research",
        "country": "CN", "year": 2025,
        "url_primary": "https://github.com/manycore-research/CAD2Program",
        "url_paper":   "https://github.com/manycore-research/CAD2Program",
        "url_github":  "https://github.com/manycore-research/CAD2Program",
        "description": "Vision-language model that converts 2D engineering CAD drawings into editable 3D parametric models with adjustable parameters; bridges flat technical drawings and fully parametric 3D geometry; accepted at AAAI 2025.",
        "techniques": ["vision-language-model", "code-generation"],
        "input_modality": "image", "output_modality": "parametric-cad",
        "physics_domain": "none", "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"], "source_files": ["image-to-cad-deep-search.jsonl"],
    },
    {
        "id": "image2cadseq-product-images-to-cad-sequence",
        "name": "Image2CADSeq",
        "category": "image-to-cad",
        "type": "academic-paper", "entry_type": "research-paper",
        "organization": "multiple institutions",
        "country": "CN", "year": 2025,
        "url_primary": "https://arxiv.org/abs/2501.04928",
        "url_paper":   "https://arxiv.org/abs/2501.04928", "url_github": "",
        "description": "Neural network that takes a 2D product photo and infers the ordered CAD construction sequence — the modeling operations used to build the object — which can be fed to a solid modeling kernel to produce an editable model.",
        "techniques": ["transformer", "computer-vision"],
        "input_modality": "image", "output_modality": "parametric-cad",
        "physics_domain": "none", "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"], "source_files": ["image-to-cad-deep-search.jsonl"],
    },
    {
        "id": "caddreamer-single-image-brep-cvpr2025",
        "name": "CADDreamer",
        "category": "image-to-cad",
        "type": "academic-paper", "entry_type": "research-paper",
        "organization": "University of Hong Kong / Texas A&M",
        "country": "HK", "year": 2025,
        "url_primary": "https://arxiv.org/abs/2502.20732",
        "url_paper":   "https://arxiv.org/abs/2502.20732", "url_github": "",
        "description": "Diffusion-based pipeline that infers normal and semantic primitive maps from a single image via multi-view diffusion, then reconstructs a complete, watertight B-rep CAD model with sharp edges; outputs structured editable geometry; CVPR 2025.",
        "techniques": ["diffusion-model", "computer-vision"],
        "input_modality": "image", "output_modality": "brep",
        "physics_domain": "none", "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"], "source_files": ["image-to-cad-deep-search.jsonl"],
    },

    # ── DFM-AI ────────────────────────────────────────────────────────────────
    {
        "id": "brepgat-machining-feature-recognition",
        "name": "BRepGAT",
        "category": "dfm-ai",
        "type": "academic-paper", "entry_type": "research-paper",
        "organization": "multiple institutions",
        "country": "KR", "year": 2023,
        "url_primary": "https://academic.oup.com/jcde/article/10/6/2384/7453688",
        "url_paper":   "https://academic.oup.com/jcde/article/10/6/2384/7453688", "url_github": "",
        "description": "Graph attention network operating directly on B-rep CAD topology to identify machining features (pockets, holes, slots) at 99.1% accuracy without converting to mesh or point cloud; published in Journal of Computational Design and Engineering 2023.",
        "techniques": ["graph-neural-network"],
        "input_modality": "brep", "output_modality": "defect-label",
        "physics_domain": "none", "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"], "source_files": ["dfm-ai-deep-search.jsonl"],
    },
    {
        "id": "brepmfr-machining-feature-recognition-transformer",
        "name": "BrepMFR",
        "category": "dfm-ai",
        "type": "academic-paper", "entry_type": "research-paper",
        "organization": "multiple institutions",
        "country": "CN", "year": 2024,
        "url_primary": "https://doi.org/10.1016/j.cagd.2024.102318",
        "url_paper":   "https://doi.org/10.1016/j.cagd.2024.102318", "url_github": "",
        "description": "Transformer-based GNN with two-stage domain-adaptation transfer learning recognizes machining features on real-world B-rep CAD models with high generalization beyond synthetic training data; published in Computer Aided Geometric Design 2024.",
        "techniques": ["graph-neural-network", "transfer-learning", "transformer"],
        "input_modality": "brep", "output_modality": "defect-label",
        "physics_domain": "none", "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"], "source_files": ["dfm-ai-deep-search.jsonl"],
    },
    {
        "id": "sparse-voxel-cnn-manufacturing-feature-recognition",
        "name": "Sparse Voxel CNN for Feature Recognition",
        "category": "dfm-ai",
        "type": "academic-paper", "entry_type": "research-paper",
        "organization": "Georgia Tech",
        "country": "US", "year": 2025,
        "url_primary": "https://doi.org/10.1115/1.4067334",
        "url_paper":   "https://doi.org/10.1115/1.4067334", "url_github": "",
        "description": "Octree-based sparse voxel CNN achieves 99.5% manufacturing feature recognition accuracy with 44% lower GPU memory than dense voxel models, making DFM feature recognition scalable to high-resolution parts; ASME JCISE 2025.",
        "techniques": ["computer-vision"],
        "input_modality": "mesh", "output_modality": "defect-label",
        "physics_domain": "none", "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"], "source_files": ["dfm-ai-deep-search.jsonl"],
    },
    {
        "id": "xai-injection-molding-lstm",
        "name": "Explainable AI for Injection Molding Quality",
        "category": "dfm-ai",
        "type": "academic-paper", "entry_type": "research-paper",
        "organization": "multiple institutions",
        "country": "DE", "year": 2025,
        "url_primary": "https://arxiv.org/abs/2511.08108",
        "url_paper":   "https://arxiv.org/abs/2511.08108", "url_github": "",
        "description": "LSTM model with SHAP/Grad-CAM/LIME explainability reduces sensor feature set from 19 to 6-9 while maintaining ≥99% quality-classification accuracy on injection molding process data; demonstrates interpretable AI for DFM feedback.",
        "techniques": ["machine-learning"],
        "input_modality": "scalar-field", "output_modality": "defect-label",
        "physics_domain": "none", "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"], "source_files": ["dfm-ai-deep-search.jsonl"],
    },
    {
        "id": "springback-prediction-lstm-incremental-forming",
        "name": "Springback Prediction LSTM",
        "category": "dfm-ai",
        "type": "academic-paper", "entry_type": "research-paper",
        "organization": "multiple institutions",
        "country": "CN", "year": 2024,
        "url_primary": "https://doi.org/10.1007/s00170-024-13632-6",
        "url_paper":   "https://doi.org/10.1007/s00170-024-13632-6", "url_github": "",
        "description": "LSTM + MLP model operating on point-series geometry representations predicts springback in single-point incremental forming with R²=0.918, enabling sheet-metal DFM feedback before tooling is cut; IJAMT 2024.",
        "techniques": ["machine-learning", "physics-informed-nn"],
        "input_modality": "scalar-field", "output_modality": "scalar-field",
        "physics_domain": "structural", "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"], "source_files": ["dfm-ai-deep-search.jsonl"],
    },
    {
        "id": "fictiv-automated-dfm-injection-molding",
        "name": "Fictiv Automated DFM",
        "category": "dfm-ai",
        "type": "commercial-product", "entry_type": "commercial-product",
        "organization": "Fictiv",
        "country": "US", "year": 2024,
        "url_primary": "https://www.fictiv.com/articles/announcing-fictivs-automated-injection-molding-dfm",
        "url_paper":   "", "url_github": "",
        "description": "Industry-first fully automated real-time DFM analysis for injection molding covering draft angles, wall thickness, undercuts, and parting-line projection; launched October 2024 as a cloud manufacturing platform feature.",
        "techniques": ["dfm-analysis", "computer-vision"],
        "input_modality": "mesh", "output_modality": "defect-label",
        "physics_domain": "none", "industry_application": ["manufacturing"],
        "status": "deployed-production",
        "tags": ["codex-generated", "wave-4"], "source_files": ["dfm-ai-deep-search.jsonl"],
    },

    # ── DFAM-AI ───────────────────────────────────────────────────────────────
    {
        "id": "wu-lattice-topology-optimization-derivative-aware-ml",
        "name": "Derivative-Aware ML for Functionally Graded Lattice TO",
        "category": "dfam-ai",
        "type": "academic-paper", "entry_type": "research-paper",
        "organization": "multiple institutions",
        "country": "CN", "year": 2023,
        "url_primary": "https://doi.org/10.1016/j.addma.2023.103833",
        "url_paper":   "https://doi.org/10.1016/j.addma.2023.103833", "url_github": "",
        "description": "Derivative-aware ML algorithm enables multiscale topology optimization of AM lattice unit cells to achieve uniform strain distributions, directly targeting AM-specific lattice manufacturability constraints; Additive Manufacturing journal 2023.",
        "techniques": ["topology-optimization", "surrogate-modeling"],
        "input_modality": "mesh", "output_modality": "topology",
        "physics_domain": "structural", "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"], "source_files": ["dfam-ai-deep-search.jsonl"],
    },
    {
        "id": "crispo-build-orientation-topology-optimization-am",
        "name": "Build Orientation + Topology Joint Optimization",
        "category": "dfam-ai",
        "type": "academic-paper", "entry_type": "research-paper",
        "organization": "multiple institutions",
        "country": "US", "year": 2024,
        "url_primary": "https://doi.org/10.1007/s00158-024-03808-9",
        "url_paper":   "https://doi.org/10.1007/s00158-024-03808-9", "url_github": "",
        "description": "Gradient-based simultaneous topology and build-orientation optimization with explicit overhang density constraints achieves up to 27% print time reduction for FDM parts; Structural and Multidisciplinary Optimization 2024.",
        "techniques": ["topology-optimization", "gradient-based-optimization"],
        "input_modality": "mesh", "output_modality": "topology",
        "physics_domain": "structural", "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"], "source_files": ["dfam-ai-deep-search.jsonl"],
    },
    {
        "id": "layer-wise-porosity-prediction-dl-metal-am",
        "name": "Layer-wise Porosity Prediction DL",
        "category": "dfam-ai",
        "type": "academic-paper", "entry_type": "research-paper",
        "organization": "multiple institutions",
        "country": "US", "year": 2023,
        "url_primary": "https://doi.org/10.1007/s10845-022-02039-3",
        "url_paper":   "https://doi.org/10.1007/s10845-022-02039-3", "url_github": "",
        "description": "Deep learning model predicts next-layer porosity probability from in-situ thermal signatures of prior layers in metal powder bed fusion, enabling AM-specific DFM feedback during process planning; Journal of Intelligent Manufacturing 2023.",
        "techniques": ["machine-learning", "physics-informed-nn"],
        "input_modality": "scalar-field", "output_modality": "scalar-field",
        "physics_domain": "thermal", "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"], "source_files": ["dfam-ai-deep-search.jsonl"],
    },
    {
        "id": "porosity-process-map-ml-lpbf",
        "name": "ML Porosity Process Map for LPBF",
        "category": "dfam-ai",
        "type": "academic-paper", "entry_type": "research-paper",
        "organization": "multiple institutions",
        "country": "US", "year": 2024,
        "url_primary": "https://doi.org/10.1007/s40964-023-00544-2",
        "url_paper":   "https://doi.org/10.1007/s40964-023-00544-2", "url_github": "",
        "description": "ML classifiers map LPBF process parameters to porosity regimes (keyhole, lack-of-fusion, optimal), producing actionable process maps that guide DFAM parameter selection; Progress in Additive Manufacturing 2024.",
        "techniques": ["machine-learning", "bayesian-optimization"],
        "input_modality": "scalar-field", "output_modality": "scalar-field",
        "physics_domain": "thermal", "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"], "source_files": ["dfam-ai-deep-search.jsonl"],
    },
    {
        "id": "rl-topology-optimization-lightweight-am",
        "name": "RL Topology Optimization for AM Lightweight Structures",
        "category": "dfam-ai",
        "type": "academic-paper", "entry_type": "research-paper",
        "organization": "multiple institutions",
        "country": "IN", "year": 2025,
        "url_primary": "https://doi.org/10.1016/j.mex.2025.103539",
        "url_paper":   "https://doi.org/10.1016/j.mex.2025.103539", "url_github": "",
        "description": "PPO deep reinforcement learning agent performs topology optimization under mechanical constraints and generates STL files for direct 3D printing, achieving up to 40% weight reduction vs SIMP; MethodsX 2025.",
        "techniques": ["reinforcement-learning", "topology-optimization"],
        "input_modality": "mesh", "output_modality": "topology",
        "physics_domain": "structural", "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"], "source_files": ["dfam-ai-deep-search.jsonl"],
    },
    {
        "id": "ml-support-structure-design-am",
        "name": "ML-Driven Support Structure Design for AM",
        "category": "dfam-ai",
        "type": "academic-paper", "entry_type": "research-paper",
        "organization": "multiple institutions",
        "country": "US", "year": 2025,
        "url_primary": "https://doi.org/10.1080/17452759.2025.2525988",
        "url_paper":   "https://doi.org/10.1080/17452759.2025.2525988", "url_github": "",
        "description": "Integrated ML framework for jointly optimizing support structure geometry and LPBF process parameters for overhanging features, reducing material waste and part defects; Virtual and Physical Prototyping 2025.",
        "techniques": ["machine-learning", "support-generation"],
        "input_modality": "mesh", "output_modality": "topology",
        "physics_domain": "thermal", "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["codex-generated", "wave-4"], "source_files": ["dfam-ai-deep-search.jsonl"],
    },
]

# ── output_modality reclassification map ─────────────────────────────────────
# IDs that need output_modality changed from "program"
MOD_REMAP = {
    # toolpath (NC/CAM code)
    "cloudnc-cam-assist":     "toolpath",
    "mastercam-copilot":      "toolpath",
    "nx-cam-ai-copilot":      "toolpath",
    "gibbscam":               "toolpath",
    # workflow scripts (engineering copilots, not CAD programs)
    "factorytalk-design-studio-copilot":  "workflow-script",
    "matlab-ai-chat-playground":          "workflow-script",
    "matlab-copilot":                     "workflow-script",
    "polyspace-copilot":                  "workflow-script",
    "schneider-industrial-copilot":       "workflow-script",
    "siemens-industrial-copilot-engineering": "workflow-script",
}
# Everything else with output_modality == "program" → cad-program
CAD_PROGRAM_CATS = {
    "program-cad", "text-to-cad", "b-rep-learning", "cad-agent",
    "benchmark-dataset", "cad-reconstruction", "cad-copilot",
}

# ── technique deduplication ──────────────────────────────────────────────────
TECH_MERGE = {
    "physics-informed-neural-networks": "physics-informed-nn",
    "large-language-models":            "llm",
}

# ── organization normalization ───────────────────────────────────────────────
ORG_MERGE = {
    "Autodesk AI Lab":                  "Autodesk Research",
    "Autodesk AI Research":             "Autodesk Research",
    "DeepMind":                         "Google DeepMind",
    "Siemens":                          "Siemens Digital Industries Software",
    "Microsoft":                        "Microsoft Research",
}


def main():
    records = []
    with open(JSONL, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    existing_ids = {r["id"] for r in records}
    print(f"Loaded {len(records)} existing records")

    # ── Step 1: Reclassify output_modality ────────────────────────────────────
    mod_changed = 0
    for r in records:
        rid = r["id"]
        if r.get("output_modality") == "program":
            if rid in MOD_REMAP:
                r["output_modality"] = MOD_REMAP[rid]
                mod_changed += 1
            elif r.get("category") in CAD_PROGRAM_CATS:
                r["output_modality"] = "cad-program"
                mod_changed += 1
    print(f"Reclassified output_modality for {mod_changed} records")

    # ── Step 2: Deduplicate techniques ────────────────────────────────────────
    tech_fixed = 0
    for r in records:
        old = r.get("techniques", [])
        new = [TECH_MERGE.get(t, t) for t in old]
        # deduplicate while preserving order
        seen = set(); deduped = []
        for t in new:
            if t not in seen: seen.add(t); deduped.append(t)
        if deduped != old:
            r["techniques"] = deduped
            tech_fixed += 1
    print(f"Fixed technique slugs in {tech_fixed} records")

    # ── Step 3: Normalize organizations ──────────────────────────────────────
    org_fixed = 0
    for r in records:
        old = r.get("organization", "")
        new = ORG_MERGE.get(old, old)
        if new != old:
            r["organization"] = new
            org_fixed += 1
    print(f"Normalized organization in {org_fixed} records")

    # ── Step 4: Add new records ───────────────────────────────────────────────
    added, skipped = [], []
    for nr in NEW_RECORDS:
        if nr["id"] in existing_ids:
            skipped.append(nr["id"])
        else:
            added.append(nr)
            existing_ids.add(nr["id"])

    records.extend(added)
    if skipped:
        print(f"Skipped {len(skipped)} duplicates: {skipped}")
    print(f"Adding {len(added)} new records")

    # ── Write back ────────────────────────────────────────────────────────────
    with open(JSONL, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\nDone — {len(records)} total records")
    print(f"New IDs: {[r['id'] for r in added]}")


if __name__ == "__main__":
    main()
