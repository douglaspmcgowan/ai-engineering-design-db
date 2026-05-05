"""
add_datasets_wave5.py — Add 18 new dataset/benchmark records
Run from repo root: python scripts/add_datasets_wave5.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JSONL = ROOT / "consolidated.jsonl"

NEW_RECORDS = [
    {
        "id": "cc3d-dataset-cvi2",
        "name": "CC3D Dataset",
        "category": "benchmark-dataset",
        "type": "benchmark-dataset",
        "entry_type": "dataset-benchmark",
        "organization": "CVI² Lab, University of Luxembourg",
        "country": "LU",
        "year": 2022,
        "url_primary": "https://cvi2.uni.lu/cc3d-dataset/",
        "url_paper": "",
        "url_github": "",
        "description": (
            "CC3D is a large-scale CAD dataset containing 50,000+ complex B-rep models virtually scanned "
            "to ~100K points/faces per model. Unlike DeepCAD (which focuses on simple extrude operations), "
            "CC3D covers advanced operations including revolutions, chamfers, and fillets, making it a "
            "more realistic benchmark for point-cloud-to-CAD reconstruction tasks."
        ),
        "techniques": ["b-rep", "point-cloud", "cad-reconstruction"],
        "input_modality": "point-cloud",
        "output_modality": "parametric-cad",
        "physics_domain": "none",
        "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["wave-5", "dataset"],
        "source_files": ["dataset-benchmark-search.jsonl"],
    },
    {
        "id": "cc3d-ops-dataset-cvi2",
        "name": "CC3D-Ops Dataset",
        "category": "benchmark-dataset",
        "type": "benchmark-dataset",
        "entry_type": "dataset-benchmark",
        "organization": "CVI² Lab, University of Luxembourg",
        "country": "LU",
        "year": 2023,
        "url_primary": "https://cvi2.uni.lu/cc3d/",
        "url_paper": "",
        "url_github": "",
        "description": (
            "CC3D-Ops extends CC3D with 37,000+ CAD models annotated with detailed construction-step histories, "
            "including operation type (extrude, revolve, fillet, chamfer) and ordering. It is used for "
            "CAD history recovery, construction sequence prediction, and reverse engineering benchmarks "
            "where recovering parametric intent from geometry is the goal."
        ),
        "techniques": ["b-rep", "sequence-modeling", "cad-reconstruction"],
        "input_modality": "mesh",
        "output_modality": "parametric-cad",
        "physics_domain": "none",
        "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["wave-5", "dataset"],
        "source_files": ["dataset-benchmark-search.jsonl"],
    },
    {
        "id": "cad-estate-google-2023",
        "name": "CAD-Estate",
        "category": "benchmark-dataset",
        "type": "benchmark-dataset",
        "entry_type": "dataset-benchmark",
        "organization": "Google Research",
        "country": "US",
        "year": 2023,
        "url_primary": "https://arxiv.org/abs/2306.09011",
        "url_paper": "https://arxiv.org/abs/2306.09011",
        "url_github": "",
        "description": (
            "CAD-Estate is a large-scale dataset of 101K instances of 12K unique CAD models placed in "
            "20K real-estate video scenes with 9-DoF pose annotations. Created via semi-automatic annotation "
            "from YouTube videos without depth sensors, it is 7× larger than Scan2CAD. "
            "Used for CAD model retrieval and 6-DoF pose estimation in video. ICCV 2023."
        ),
        "techniques": ["pose-estimation", "cad-retrieval", "computer-vision"],
        "input_modality": "image",
        "output_modality": "parametric-cad",
        "physics_domain": "none",
        "industry_application": ["manufacturing", "aec"],
        "status": "research-prototype",
        "tags": ["wave-5", "dataset"],
        "source_files": ["dataset-benchmark-search.jsonl"],
    },
    {
        "id": "automate-assembly-dataset-2021",
        "name": "AutoMate Assembly Dataset",
        "category": "benchmark-dataset",
        "type": "benchmark-dataset",
        "entry_type": "dataset-benchmark",
        "organization": "University of Washington / Autodesk",
        "country": "US",
        "year": 2021,
        "url_primary": "https://arxiv.org/abs/2105.12238",
        "url_paper": "https://arxiv.org/abs/2105.12238",
        "url_github": "",
        "description": (
            "AutoMate is the first large-scale B-rep assembly dataset, containing multi-component CAD "
            "assemblies with annotated mate types (fastened, revolute, slider, pin slot, etc.) and "
            "contact locations. Benchmark task: predict mate type and location from B-rep part pairs. "
            "Data format: JSON + STEP + Parquet metadata. Published at ACM SIGGRAPH Asia 2021."
        ),
        "techniques": ["b-rep", "assembly-modeling", "graph-neural-network"],
        "input_modality": "parametric-cad",
        "output_modality": "structured-data",
        "physics_domain": "none",
        "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["wave-5", "dataset"],
        "source_files": ["dataset-benchmark-search.jsonl"],
    },
    {
        "id": "mcb-mechanical-components-benchmark-2020",
        "name": "MCB: Mechanical Components Benchmark",
        "category": "benchmark-dataset",
        "type": "benchmark-dataset",
        "entry_type": "dataset-benchmark",
        "organization": "Purdue University / Korea University",
        "country": "US",
        "year": 2020,
        "url_primary": "https://github.com/stnoah1/mcb",
        "url_paper": "",
        "url_github": "https://github.com/stnoah1/mcb",
        "description": (
            "MCB (Mechanical Components Benchmark) is a 3D shape dataset of 58,696 mechanical components "
            "across 68 classes with taxonomy from ICS (ISO/TS) standards. Data is available in point cloud, "
            "voxel, and mesh formats. Sourced from TraceParts, GrabCAD, and 3D Warehouse, it is the "
            "engineering-domain counterpart to ModelNet for classification and retrieval. ECCV 2020."
        ),
        "techniques": ["3d-shape-classification", "point-cloud", "retrieval"],
        "input_modality": "mesh",
        "output_modality": "structured-data",
        "physics_domain": "none",
        "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["wave-5", "dataset"],
        "source_files": ["dataset-benchmark-search.jsonl"],
    },
    {
        "id": "mfcad-machining-feature-dataset-2020",
        "name": "MFCAD",
        "category": "benchmark-dataset",
        "type": "benchmark-dataset",
        "entry_type": "dataset-benchmark",
        "organization": "Huazhong University of Science and Technology",
        "country": "CN",
        "year": 2020,
        "url_primary": "https://github.com/hducg/MFCAD",
        "url_paper": "",
        "url_github": "https://github.com/hducg/MFCAD",
        "description": (
            "MFCAD is a machining feature recognition dataset of ~15,000 voxelized CAD models with "
            "16 standard machining feature classes (pocket, slot, boss, hole, chamfer, step, etc.). "
            "Generated via PythonOCC and primarily used with 3D-CNN approaches. "
            "It established the standard benchmark for automated machining feature recognition."
        ),
        "techniques": ["machining-feature-recognition", "3d-cnn", "voxel"],
        "input_modality": "mesh",
        "output_modality": "structured-data",
        "physics_domain": "none",
        "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["wave-5", "dataset"],
        "source_files": ["dataset-benchmark-search.jsonl"],
    },
    {
        "id": "mfcad-plus-plus-2022",
        "name": "MFCAD++",
        "category": "benchmark-dataset",
        "type": "benchmark-dataset",
        "entry_type": "dataset-benchmark",
        "organization": "Queen's University Belfast",
        "country": "GB",
        "year": 2022,
        "url_primary": "https://gitlab.com/qub_femg/machine-learning/mfcad2-dataset",
        "url_paper": "",
        "url_github": "https://gitlab.com/qub_femg/machine-learning/mfcad2-dataset",
        "description": (
            "MFCAD++ is an expanded machining feature recognition dataset of 59,655 STEP files, "
            "each containing 3–10 machining features including both planar and non-planar faces. "
            "Auto-generated via PythonOCC, it supersedes MFCAD and is the standard benchmark for "
            "graph-based and B-rep-based machining feature recognition methods. CAD 2022."
        ),
        "techniques": ["machining-feature-recognition", "b-rep", "graph-neural-network"],
        "input_modality": "parametric-cad",
        "output_modality": "structured-data",
        "physics_domain": "none",
        "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["wave-5", "dataset"],
        "source_files": ["dataset-benchmark-search.jsonl"],
    },
    {
        "id": "hybridcad-dataset-2024",
        "name": "HybridCAD Dataset",
        "category": "benchmark-dataset",
        "type": "benchmark-dataset",
        "entry_type": "dataset-benchmark",
        "organization": "multiple institutions",
        "country": "US",
        "year": 2024,
        "url_primary": "https://zenodo.org/records/14043179",
        "url_paper": "https://arxiv.org/abs/2408.06891",
        "url_github": "",
        "description": (
            "HybridCAD is a benchmark dataset of 8,938 STEP files combining additive and subtractive "
            "manufacturing features (DED/machining hybrid processes). Generated via PythonOCC, it extends "
            "MFCAD/MFCAD++ with additive features including overhangs and support structures. "
            "The first dataset explicitly designed for hybrid DED/machining feature recognition. ASME IDETC-CIE 2024."
        ),
        "techniques": ["machining-feature-recognition", "b-rep", "additive-manufacturing"],
        "input_modality": "parametric-cad",
        "output_modality": "structured-data",
        "physics_domain": "none",
        "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["wave-5", "dataset"],
        "source_files": ["dataset-benchmark-search.jsonl"],
    },
    {
        "id": "airfrans-cfd-benchmark-2022",
        "name": "AirfRANS",
        "category": "benchmark-dataset",
        "type": "benchmark-dataset",
        "entry_type": "dataset-benchmark",
        "organization": "Extrality / Sorbonne Université MLIA",
        "country": "FR",
        "year": 2022,
        "url_primary": "https://airfrans.readthedocs.io/en/latest/notes/introduction.html",
        "url_paper": "https://arxiv.org/abs/2212.07564",
        "url_github": "",
        "description": (
            "AirfRANS is a CFD surrogate benchmark of RANS simulations over 2D airfoils in subsonic regime, "
            "validated against NASA Langley experiments. Benchmark tasks include full-field prediction "
            "(velocity, pressure, turbulent viscosity), drag/lift coefficient regression, and boundary "
            "layer analysis. Supports graph neural network and physics-informed ML evaluation. NeurIPS 2022 Datasets."
        ),
        "techniques": ["physics-informed-nn", "graph-neural-network", "surrogate-model"],
        "input_modality": "mesh",
        "output_modality": "simulation",
        "physics_domain": "fluid-dynamics",
        "industry_application": ["aerospace"],
        "status": "research-prototype",
        "tags": ["wave-5", "dataset"],
        "source_files": ["dataset-benchmark-search.jsonl"],
    },
    {
        "id": "drivaernet-automotive-cfd-2023",
        "name": "DrivAerNet",
        "category": "benchmark-dataset",
        "type": "benchmark-dataset",
        "entry_type": "dataset-benchmark",
        "organization": "MIT DECODE Lab",
        "country": "US",
        "year": 2023,
        "url_primary": "https://arxiv.org/abs/2406.09624",
        "url_paper": "https://arxiv.org/abs/2406.09624",
        "url_github": "",
        "description": (
            "DrivAerNet is a large-scale automotive aerodynamics dataset of 4,000 parametric DrivAer "
            "car body variants with full RANS CFD simulations. Contains 3D meshes and pressure/velocity/"
            "wall-shear stress fields for generative design, graph-based drag prediction, and surrogate "
            "model training. Published in ASME Journal of Mechanical Design."
        ),
        "techniques": ["surrogate-model", "graph-neural-network", "cfd"],
        "input_modality": "mesh",
        "output_modality": "simulation",
        "physics_domain": "fluid-dynamics",
        "industry_application": ["automotive"],
        "status": "research-prototype",
        "tags": ["wave-5", "dataset"],
        "source_files": ["dataset-benchmark-search.jsonl"],
    },
    {
        "id": "drivaernet-plus-plus-2024",
        "name": "DrivAerNet++",
        "category": "benchmark-dataset",
        "type": "benchmark-dataset",
        "entry_type": "dataset-benchmark",
        "organization": "MIT DECODE Lab",
        "country": "US",
        "year": 2024,
        "url_primary": "https://arxiv.org/abs/2406.09624",
        "url_paper": "https://arxiv.org/abs/2406.09624",
        "url_github": "",
        "description": (
            "DrivAerNet++ is the largest public multimodal automotive CFD dataset, with 8,000 parametric "
            "car geometries (fastback/notchback/estateback variants) and 39+ TB of CFD data including "
            "3D meshes, pressure fields, velocity fields, and wall-shear stress. Supports generative design, "
            "drag prediction, and surrogate training. NeurIPS 2024 Datasets & Benchmarks track."
        ),
        "techniques": ["surrogate-model", "graph-neural-network", "cfd"],
        "input_modality": "mesh",
        "output_modality": "simulation",
        "physics_domain": "fluid-dynamics",
        "industry_application": ["automotive"],
        "status": "research-prototype",
        "tags": ["wave-5", "dataset"],
        "source_files": ["dataset-benchmark-search.jsonl"],
    },
    {
        "id": "driveraerml-scale-resolving-cfd-2024",
        "name": "DrivAerML",
        "category": "benchmark-dataset",
        "type": "benchmark-dataset",
        "entry_type": "dataset-benchmark",
        "organization": "UpstreamCFD",
        "country": "GB",
        "year": 2024,
        "url_primary": "https://arxiv.org/abs/2408.11969",
        "url_paper": "https://arxiv.org/abs/2408.11969",
        "url_github": "",
        "description": (
            "DrivAerML is the first large-scale publicly available automotive aerodynamics dataset using "
            "hybrid RANS-LES (scale-resolving) CFD rather than standard RANS. Contains 500 DrivAer notchback "
            "variants computed with OpenFOAM, validated against wind tunnel measurements. "
            "Released under CC-BY-SA on Hugging Face. Highest-fidelity open-source automotive aero dataset."
        ),
        "techniques": ["surrogate-model", "cfd", "physics-informed-nn"],
        "input_modality": "mesh",
        "output_modality": "simulation",
        "physics_domain": "fluid-dynamics",
        "industry_application": ["automotive"],
        "status": "research-prototype",
        "tags": ["wave-5", "dataset"],
        "source_files": ["dataset-benchmark-search.jsonl"],
    },
    {
        "id": "windsorml-les-vehicle-aero-2024",
        "name": "WindsorML",
        "category": "benchmark-dataset",
        "type": "benchmark-dataset",
        "entry_type": "dataset-benchmark",
        "organization": "Amazon AWS / Siemens Energy / Loughborough University",
        "country": "US",
        "year": 2024,
        "url_primary": "https://arxiv.org/abs/2407.19320",
        "url_paper": "https://arxiv.org/abs/2407.19320",
        "url_github": "",
        "description": (
            "WindsorML is a Wall-Modeled Large-Eddy Simulation (WMLES) dataset of 355 Windsor body variants "
            "at 280M+ cells per simulation, with time-averaged volume, surface data, and force/moment coefficients. "
            "The highest-fidelity open-source automotive aerodynamics dataset (CC-BY-SA). "
            "First large-scale LES dataset for Windsor body geometry. NeurIPS 2024 Datasets & Benchmarks."
        ),
        "techniques": ["surrogate-model", "cfd", "large-eddy-simulation"],
        "input_modality": "mesh",
        "output_modality": "simulation",
        "physics_domain": "fluid-dynamics",
        "industry_application": ["automotive"],
        "status": "research-prototype",
        "tags": ["wave-5", "dataset"],
        "source_files": ["dataset-benchmark-search.jsonl"],
    },
    {
        "id": "spare3d-engineering-drawing-2020",
        "name": "SPARE3D",
        "category": "benchmark-dataset",
        "type": "benchmark-dataset",
        "entry_type": "dataset-benchmark",
        "organization": "multiple institutions",
        "country": "US",
        "year": 2020,
        "url_primary": "https://arxiv.org/abs/2003.14040",
        "url_paper": "https://arxiv.org/abs/2003.14040",
        "url_github": "",
        "description": (
            "SPARE3D (Spatial Reasoning Benchmark for 3D from Engineering Drawings) tests whether models "
            "can infer 3D geometry from standard 2D engineering projections (front/side/top views). "
            "Multi-view line drawings with 3D spatial reasoning QA tasks, point cloud and voxel ground truth. "
            "Directly relevant to CAD drawing understanding and sketch-to-3D. CVPR 2020."
        ),
        "techniques": ["computer-vision", "3d-reconstruction", "spatial-reasoning"],
        "input_modality": "image",
        "output_modality": "mesh",
        "physics_domain": "none",
        "industry_application": ["manufacturing"],
        "status": "research-prototype",
        "tags": ["wave-5", "dataset"],
        "source_files": ["dataset-benchmark-search.jsonl"],
    },
    {
        "id": "structured3d-bim-dataset-2020",
        "name": "Structured3D",
        "category": "benchmark-dataset",
        "type": "benchmark-dataset",
        "entry_type": "dataset-benchmark",
        "organization": "multiple institutions",
        "country": "CN",
        "year": 2020,
        "url_primary": "https://structured3d-dataset.org/",
        "url_paper": "https://arxiv.org/abs/1908.00171",
        "url_github": "https://github.com/bertjiazheng/Structured3D",
        "description": (
            "Structured3D contains 3,500 house designs created by professional interior designers with "
            "196K panoramic images and rich annotations (semantic, albedo, depth, normal, layout). "
            "Uses a 'Primitive + Relationship' structured representation similar to BIM. "
            "Used for room layout estimation, semantic segmentation, and scan-to-BIM research. ECCV 2020."
        ),
        "techniques": ["scene-understanding", "3d-reconstruction", "semantic-segmentation"],
        "input_modality": "image",
        "output_modality": "mesh",
        "physics_domain": "none",
        "industry_application": ["aec"],
        "status": "research-prototype",
        "tags": ["wave-5", "dataset"],
        "source_files": ["dataset-benchmark-search.jsonl"],
    },
    {
        "id": "s3dis-stanford-3d-indoor-spaces",
        "name": "S3DIS",
        "category": "benchmark-dataset",
        "type": "benchmark-dataset",
        "entry_type": "dataset-benchmark",
        "organization": "Stanford University",
        "country": "US",
        "year": 2016,
        "url_primary": "http://buildingparser.stanford.edu/dataset.html",
        "url_paper": "https://arxiv.org/abs/1702.01105",
        "url_github": "",
        "description": (
            "S3DIS (Stanford Large-Scale 3D Indoor Spaces) is a point cloud semantic segmentation dataset "
            "covering 6 large indoor areas (272 rooms) with 12 semantic classes including walls, floors, "
            "columns, beams, doors, and windows. A key benchmark for structural element recognition and "
            "scan-to-BIM workflows in the AEC industry, alongside ScanNet."
        ),
        "techniques": ["point-cloud", "semantic-segmentation", "3d-scene-understanding"],
        "input_modality": "point-cloud",
        "output_modality": "structured-data",
        "physics_domain": "none",
        "industry_application": ["aec"],
        "status": "research-prototype",
        "tags": ["wave-5", "dataset"],
        "source_files": ["dataset-benchmark-search.jsonl"],
    },
    {
        "id": "open-catalyst-oc20-oc22",
        "name": "Open Catalyst OC20/OC22",
        "category": "benchmark-dataset",
        "type": "benchmark-dataset",
        "entry_type": "dataset-benchmark",
        "organization": "Meta AI / Carnegie Mellon University",
        "country": "US",
        "year": 2022,
        "url_primary": "https://opencatalystproject.org/",
        "url_paper": "https://arxiv.org/abs/2206.08917",
        "url_github": "https://github.com/Open-Catalyst-Project/ocp",
        "description": (
            "Open Catalyst OC20/OC22 are premier benchmarks for ML interatomic potentials in heterogeneous "
            "catalysis. OC20 contains 1.28M DFT relaxations (~264M single-point evaluations) across 82 "
            "adsorbates on 11,451 metallic slabs. OC22 extends this to oxide electrocatalysts. "
            "OC25 (solid-liquid interfaces) released 2025. The ImageNet of catalyst ML."
        ),
        "techniques": ["graph-neural-network", "ml-interatomic-potential", "dft"],
        "input_modality": "structured-data",
        "output_modality": "structured-data",
        "physics_domain": "chemistry",
        "industry_application": ["energy", "materials"],
        "status": "research-prototype",
        "tags": ["wave-5", "dataset"],
        "source_files": ["dataset-benchmark-search.jsonl"],
    },
    {
        "id": "jarvis-leaderboard-nist-2024",
        "name": "JARVIS-Leaderboard",
        "category": "benchmark-dataset",
        "type": "benchmark-dataset",
        "entry_type": "dataset-benchmark",
        "organization": "NIST",
        "country": "US",
        "year": 2024,
        "url_primary": "https://pages.nist.gov/jarvis_leaderboard",
        "url_paper": "https://www.nature.com/articles/s41524-024-01259-w",
        "url_github": "https://github.com/usnistgov/jarvis_leaderboard",
        "description": (
            "JARVIS-Leaderboard is a community benchmarking platform for reproducible materials design AI, "
            "covering 20+ properties from JARVIS-DFT (~55K structures), Materials Project, and QM9. "
            "Categories include AI models, electronic structure (ES), force fields (FF), quantum chemistry (QC), "
            "and experimental validation (EXP). Most comprehensive materials ML benchmark platform. npj Computational Materials 2024."
        ),
        "techniques": ["graph-neural-network", "ml-interatomic-potential", "dft"],
        "input_modality": "structured-data",
        "output_modality": "structured-data",
        "physics_domain": "chemistry",
        "industry_application": ["materials"],
        "status": "research-prototype",
        "tags": ["wave-5", "dataset"],
        "source_files": ["dataset-benchmark-search.jsonl"],
    },
]


def main():
    records = []
    with open(JSONL, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    print(f"Loaded {len(records)} existing records")

    existing_ids = {r["id"] for r in records}
    existing_names_lower = {r["name"].lower() for r in records}

    new_to_add = []
    skipped = []
    for nr in NEW_RECORDS:
        if nr["id"] in existing_ids:
            skipped.append(f'{nr["id"]} (id duplicate)')
        elif nr["name"].lower() in existing_names_lower:
            skipped.append(f'{nr["id"]} (name duplicate: {nr["name"]})')
        else:
            new_to_add.append(nr)

    if skipped:
        print(f"Skipping {len(skipped)} duplicates:")
        for s in skipped:
            print(f"  {s}")

    records.extend(new_to_add)
    print(f"Adding {len(new_to_add)} new records")

    with open(JSONL, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Done — {len(records)} total records in {JSONL.name}")
    print(f"New IDs: {[r['id'] for r in new_to_add]}")


if __name__ == "__main__":
    main()
