# Research Gaps — AI Engineering Design DB

Generated 2026-05-07. Items flagged by user as potentially missing from the knowledge graph.

---

## 1. Davinci by Celedon Solutions

**Correct spelling:** Celedon Solutions Inc. (not "Celadon" / "Cendyon"). Product is "Davinci."

- **Summary:** AI platform for hardware engineering positioned as a conversational design agent. Manages CAD, code, requirements, and digital models in a SysML v2-based system, exports full Technical Data Packages (CAD + SysML + reports), and integrates external tools/databases via Model Context Protocol (MCP). More of a systems-engineering copilot than a pure text-to-CAD converter.
- **URL:** https://celedon.solutions/davinci/
- **Year:** Company/product appears to be recent (2024–2025 era; specific founding date not surfaced)
- **Category:** text-to-CAD (with overlap into systems-engineering-AI)
- **Tags:** conversational-agent, SysML-v2, MCP-integration, TDP-generation, hardware-copilot

---

## 2. Synera (formerly ELISE)

- **Summary:** Munich-based generative engineering / low-code platform that automates CAD, simulation, costing, and design workflows via configurable multi-agent systems. Originally ELISE (Evolutionary Lightweight Structure Engineering); rebranded to Synera in 2022. Positions itself as the "AI agents platform for engineers." Also distributed by Altair as an OEM partner.
- **URL:** https://www.synera.io/
- **Year founded:** ~2018 as ELISE; rebranded 2022 as Synera. Recently raised $40M Series B (Revaia-led).
- **Category:** generative-design (also dfam-ai, simulation-surrogate)
- **Tags:** low-code, agentic-workflows, parametric-automation, multi-agent, CAD-simulation-integration

---

## 3. Ryan McClelland (NASA Goddard)

NASA Goddard research engineer pioneering "Evolved Structures" — generative design + digital manufacturing for spaceflight hardware. Reports >3x performance improvement and >10x dev-time reduction.

Most-cited talks/papers/projects:

1. **"Generative design and digital manufacturing: using AI and robots to build lightweight instrument structures"** — SPIE Optics & Photonics Proc. Vol. 12217 (2022). https://www.spiedigitallibrary.org/conference-proceedings-of-spie/12217/122170O/
2. **EXCITE Tip/Tilt Bracket** — antenna/telescope mounts for the Exoplanet Climate Infrared Telescope balloon mission. Headline result: AI design in ~1 hour vs. 2 days for two human experts; stiffer, stronger, easier to manufacture.
3. **CDFAM NYC 2024 closing keynote** + CDFAM 2023 talk "Generative Design & Digital Manufacturing at NASA Goddard." YouTube: https://www.youtube.com/watch?v=t_h_WmBhRXA
4. **Goddard Engineering Colloquium** on Generative Design — https://ecolloq.gsfc.nasa.gov/Current/announce.mcclelland.html
5. **"From Text to Spaceship: Advancing AI in Aerospace"** (CDFAM 2025-era talk).
6. NTRS citation: https://ntrs.nasa.gov/citations/20220012523
7. Fast Company profile: https://www.fastcompany.com/90950342/ryan-mcclelland-is-pushing-nasa-into-the-next-space-era-with-generative-ai

**Tools championed:** Autodesk Fusion Generative Design (primary). Process pairs Fusion GD with CNC milling and metal 3D printing. No publicly released open-source tool of his own.

---

## 4. Commercial "Generative Engineering" Tools

Tools that explicitly use generative-engineering / generative-design branding:

- **Autodesk Fusion Generative Design** — https://www.autodesk.com/products/fusion-360/ (cloud-solver, multi-outcome generative)
- **nTop** (formerly nTopology, founded 2015) — https://www.ntop.com/ implicit-modeling + field-driven design, lattice/DfAM focus
- **Synera** (see #2)
- **Siemens NX / Solid Edge Generative Design**
- **PTC Creo Generative Design** (acquired Frustum 2018)
- **Dassault SolidWorks / CATIA xGenerative Design**
- **ParaMatters CogniCAD** (early generative-design entrant)
- **Altair Inspire** + Altair-distributed Synera
- **ToffeeX** — physics-driven generative design with explainability controls
- **Neural Concept** — deep-learning surrogate models for generative iteration
- **Hyperganic** — algorithmic/implicit generative engineering
- **Diabatix** ColdStream (cooling-specific generative)
- **Augmenta** — generative design for electrical building systems

---

## 5. CDFAM (cdfam.com) — AI/ML-Relevant Speakers by Year

### CDFAM NYC 2023 (June 14–15, Brooklyn Newlab — inaugural)
- **Keynotes:** Neil Gershenfeld (MIT CBA); Ronald Rael (UC Berkeley / Emerging Objects)
- 30+ speakers from MIT, NYU, Penn State, NASA, New Balance, Hyperganic, etc. Full list: https://cdfam.com/nyc23-speakers/

### CDFAM NYC 2024
- **Opening keynote:** Jessica Rosenkrantz & Jesse Louis-Rosenberg (Nervous System)
- **Closing keynote:** Ryan McClelland (NASA)
- **AI-focused:** Karl D.D. Willis (Autodesk) on **BrepGen**; Joe Griston & Laurence Cook (Generative Engineering); Alexander Lavin (Pasteur Labs) on Scientific ML; Ziyuan Zhu (IDEO) on generative-AI product experience.

### CDFAM Amsterdam 2025 (July 9–10)
- Keynotes: Tiffany Cheng (Cornell); Mathew Vola (Arup); fireside with Federico Casalegno (Samsung).

### CDFAM NYC 2025 (Oct 29–30) — heaviest AI lineup
- **Markus Buehler (MIT)** — Superintelligence for materials discovery
- **Chris McComb (CMU)** — AI and the Battle for the Soul of Design
- **Ian Pegler (NVIDIA)** — accelerated computing + AI surrogates
- **Mark Huntington (PhysicsX)** — Large Physics + Geometry Models
- **Pratap Ranade (ARENA-AI)** — AI for electromagnetic design
- **Luca Zampieri (Neural Concept)** — multi-physics generative design
- **Sergey Pigach (Thornton Tomasetti CORE)** — agentic workflows for structural engineering
- **Alexander Lavin (Pasteur Labs)** — simulation intelligence
- **Matthew Goldsberry & Junling Zhuang (HDR)** — AI agents for parametric geometry
- **Marco Pietropaoli (ToffeeX)**, **Tuo Zhao (Princeton)**, **Sai Nelaturi (C-Infinity)** — adjacent ML/optimization work

### CDFAM Barcelona 2026
- **Hao (Richard) Zhang** — VP AI/R&D at Augmenta, SFU professor; geometric/generative modeling.

YouTube archive (free): https://www.youtube.com/@CDFAM
Podcast: https://www.designforam.com/podcast

---

## 6. Autodesk AI-CAD Research Projects

The Autodesk AI Lab claims 65+ peer-reviewed papers on AI for CAD geometry. Key projects:

- **Project Bernini** (2024) — generative AI for 3D shapes; trained on 10M shapes / 3B params; accepts text, 2D images, sketches, voxels, point clouds. Generates shape and texture separately. https://www.research.autodesk.com/projects/project-bernini/
- **Project Dreamcatcher** — original generative-design research project (predates Fusion Generative Design). https://www.research.autodesk.com/projects/project-dreamcatcher/
- **CAD-LLM** — LLMs generating CAD. https://www.research.autodesk.com/publications/ai-lab-cad-llm/
- **BrepGen** (Karl Willis et al.) — structured latent geometry for B-rep generation
- **DesignQA** — multimodal benchmark for engineering documentation comprehension
- **HG-CAD** — hierarchical graph learning for CAD material prediction
- **Zero-To-CAD** — synthesizing executable CadQuery programs from LLMs
- **Neural CAD foundation models** — announced at AU 2025 for Forma + Fusion commercial release
- HuggingFace org: https://huggingface.co/ADSKAILab
- AU 2025 roundup: https://www.research.autodesk.com/blog/ai-and-industry-transformation-at-au-2025/

---

## 7. YouTube Channels Worth Scraping

For AI-for-engineering-design specifically:

1. **CDFAM** — https://www.youtube.com/@CDFAM (every conference talk, fully indexed)
2. **NASA Goddard / NASA 360** — for McClelland, Evolved Structures, mission engineering content
3. **Autodesk University (AU)** — annual deep dives on Fusion GD, Bernini, AI features
4. **nTop** — DfAM and implicit-modeling tutorials/case studies
5. **The Cool Parts Show** (Additive Manufacturing Media) — practitioner-focused AM/generative case studies (e.g., NASA evolved structures ep. #61)

Honorable mentions: Synera's channel, Neural Concept, and individual academic channels (MIT CBA, CMU IDEAL Lab/Chris McComb).

---

## 8. Automation Pipeline — Concrete Sources

A practical, low-DIY scrape plan:

1. **arXiv API + RSS** — query categories `cs.CG`, `cs.GR`, `cs.LG`, `cs.AI` with keyword filters (CAD, generative design, topology optimization, neural operator, B-rep, implicit modeling). Daily Atom feeds: https://info.arxiv.org/help/rss.html. Custom filter tool: https://github.com/cschreib/flexible-arxiv-rss
2. **YouTube Data API v3** + **Whisper transcription** — pull latest videos from CDFAM, AU, nTop, NASA Goddard channels (channel IDs); auto-transcribe with whisper.cpp; LLM-summarize and tag.
3. **GitHub Trending API / search** — daily query for repos tagged `text-to-cad`, `generative-design`, `cadquery`, `brep`, `implicit-modeling`. https://docs.github.com/en/rest/search
4. **Conference proceedings** — SIGGRAPH (ACM DL RSS), NeurIPS/ICML/ICLR OpenReview API, CVPR (CVF Open Access), SPIE Digital Library RSS, ASME IDETC. Filter by keyword.
5. **CDFAM YouTube + podcast RSS** — feed ID published on https://www.designforam.com/podcast
6. **NASA NTRS API** — https://ntrs.nasa.gov/api/citations search for "generative design," "evolved structures." Returns JSON with PDF links.
7. **Twitter/X lists** — curated list of accounts (Duann Scott / @CDFAM, @AutodeskRschr, @ntopology, @Synera_io, McClelland, Buehler, McComb). Use Nitter RSS or X API.
8. **Google Scholar Alerts** — keyword + author alerts emailed daily; ingest into a mailbox the pipeline parses.
9. **Substack RSS** — Bits-to-Atoms (Duann Scott / CDFAM organizer) is a primary practitioner source.

Suggested architecture: cron-driven Python collector → JSONL → embedding + dedup → LLM tagger that classifies into your taxonomy `{text-to-cad, generative-design, ...}` → review queue UI before adding nodes/edges to the graph.

---

## Sources

- https://celedon.solutions/davinci/
- https://www.synera.io/about
- https://3dadept.com/additive-manufacturing-software-software-engineering-elise-becomes-synera/
- https://thenextweb.com/news/synera-40m-series-b-agentic-ai-engineering
- https://science.nasa.gov/wp-content/uploads/2024/03/evolved-structures-ryan-mcclelland.pdf
- https://etd.gsfc.nasa.gov/capabilities/capabilities-listing/generative-design/
- https://ntrs.nasa.gov/citations/20220012523
- https://www.fastcompany.com/90950342/ryan-mcclelland-is-pushing-nasa-into-the-next-space-era-with-generative-ai
- https://cdfam.com/nyc23-speakers/
- https://cdfam.com/24-nyc/
- https://cdfam.com/amsterdam-2025/
- https://cdfam.com/nyc-2025/
- https://cdfam.com/barcelona-2026/
- https://www.research.autodesk.com/projects/project-bernini/
- https://www.research.autodesk.com/projects/project-dreamcatcher/
- https://www.research.autodesk.com/research-areas/science/ai-lab/
- https://www.research.autodesk.com/blog/ai-and-industry-transformation-at-au-2025/
- https://huggingface.co/ADSKAILab
- https://www.ntop.com/
- https://www.youtube.com/@CDFAM
- https://info.arxiv.org/help/rss.html
