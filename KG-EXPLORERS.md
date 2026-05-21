# Knowledge-Graph & Embedding Explorers — Landscape + Playbook

> Research notes for improving `explorer.html`. Covers the best graph / knowledge-graph / embedding-space explorers, what makes them look and feel good, the open-source rendering engines we could adopt, and concrete "how to replicate" recipes (Litmaps chronological view, Nomic-style embedding maps, Cosmograph clustering).
>
> Compiled 2026-05. Sources are linked inline.

---

## 0. TL;DR recommendations for this project

1. **Biggest visual wins (no engine change):** size nodes by degree, fade edge opacity on high-degree hubs, color edges by their source node, dark canvas, clean sans-serif font. These alone close most of the gap to Cosmograph/Sigma.
2. **Embedding mode:** render **raw UMAP coordinates with physics OFF**. Running barnesHut on top of UMAP destroys the cluster geometry — that is the #1 cause of the "blob." Re-bake UMAP with `min_dist≈0.0`, `n_neighbors≈30`, add per-point alpha + density-scaled size.
3. **Cluster labels:** cluster the **2D points** (HDBSCAN or 2D-density peaks), name with **c-TF-IDF** (fallback: modal Category), one label at each cluster's medoid/density peak, gated by zoom.
4. **Chronological mode:** Litmaps = X is publication year, Y is a **collision-avoidance spread** of log(citations), short low-opacity citation lines, labels drop on overlap. Our current "weighted-embed Y" is not Litmaps.
5. **Engine question:** at 2,400 nodes vis-network is functionally fine but Canvas-based and near its ceiling. If we want WebGL polish + 50k headroom + one engine for *both* graph and embedding modes, **cosmos.gl** (MIT, CDN-droppable) is the migration target. Otherwise stay on vis-network and apply the cheap wins above.

---

## 1. The tools, by category

### 1A. Embedding / vector-space map explorers (closest to our "embed mode")

| Tool | Link | What to steal |
|---|---|---|
| **Nomic Atlas** | [atlas.nomic.ai](https://atlas.nomic.ai/) · [Discover](https://atlas.nomic.ai/discover) | The gold standard. Topographic look = KDE density underlay + homogeneous color fills per topic region. Lasso select → sidebar of selected points. Topic labels appear/disappear by zoom level. |
| **Apple / HuggingFace "Embedding Atlas"** | [github.com/apple/embedding-atlas](https://github.com/apple/embedding-atlas) · [overview](https://apple.github.io/embedding-atlas/overview.html) | Best-in-class **automatic clustering + auto cluster labels**. WebGPU. Clusters the 2D density grid (not the high-D vectors), labels at density peaks, c-TF-IDF naming. MIT. |
| **TensorFlow Embedding Projector** | [projector.tensorflow.org](https://projector.tensorflow.org/) | 3D PCA/t-SNE/UMAP, label search, "show nearest neighbors in original space." |
| **Grant Custer UMAP Explorer** | [grantcuster.github.io/umap-explorer](https://grantcuster.github.io/umap-explorer/) | Minimal-UI reference: pan/zoom + click-to-inspect, point = the actual image. |
| **PixPlot (Yale DHLab)** | [github.com/YaleDHLab/pix-plot](https://github.com/YaleDHLab/pix-plot) | k-means (default 20) hotspots, **medoid** as the cluster's representative item. |
| **deepscatter / Nomic** | [github.com/nomic-ai/deepscatter](https://github.com/nomic-ai/deepscatter) | GPU size/alpha transforms that animate across zoom; density-aware rendering instead of fixed alpha. |

**Live Nomic maps to study:** [Krea Stable-Diffusion explorer](https://atlas.nomic.ai/data/andriy/krea-ai-stable-diffusion-explorer-dkF/map) · [UltraChat](https://atlas.nomic.ai/map/0ce65783-c3a9-40b5-895d-384933f50081/a7b46301-022f-45d8-bbf4-98107eabdbac) · [Open Orca](https://atlas.nomic.ai/map/c1b88b47-2d9b-47e0-9002-b80766792582/2560fd25-52fe-42f1-a58f-ff5eccc890d2).

### 1B. Large-graph / network explorers (closest to our "force mode")

| Tool | Link | What to steal |
|---|---|---|
| **Cosmograph** | [cosmograph.app](https://cosmograph.app/) | GPU force layout, the "galaxy" look. Minimal floating toolbar, search-highlight, linked timeline histogram, lasso. Built on the open **cosmos.gl** core. |
| **Sigma.js + Graphology** | [sigmajs.org](https://www.sigmajs.org/) · [demo](https://www.sigmajs.org/demo) | WebGL. Louvain community detection → color by community, size by degree, ForceAtlas2 baked offline so it loads pre-settled. Hover → non-neighbor edges fade to ~5%. |
| **Neo4j Bloom** | [neo4j graph-viz tools](https://neo4j.com/blog/graph-visualization/neo4j-graph-visualization-tools/) | "Scenes"/perspectives (saved views), search-bar-driven navigation, expand-on-click. |
| **Gephi / Gephi Lite** | [gephi.org](https://gephi.org/) · [Gephi Lite](https://docs.gephi.org/lite/) | Modularity clustering + appearance ("size by metric, color by attribute"), filter panel, overview/detail split. |
| **Open Semantic Graph Explorer** | [opensemanticsearch.org/graph-explorer](https://opensemanticsearch.org/graph-explorer/) | Faceted search + graph combo. |

### 1C. Personal-KG / note graphs (navigation patterns)

| Tool | Link | What to steal |
|---|---|---|
| **Obsidian Graph View** | [obsidian.md/help/plugins/graph](https://obsidian.md/help/plugins/graph) | **Local graph** = ego network around the active node with a **depth slider (1–N hops)** expanding in real time; toggles for incoming / outgoing / neighbor links. The single most transferable navigation idea for us. |

### 1D. Literature / citation mappers (closest to our "chronological" mode)

| Tool | Link | What to steal |
|---|---|---|
| **Litmaps** | [litmaps.com](https://www.litmaps.com/) | X = publication date, Y = collision-avoidance "Compact" spread, log-citation dot sizes, short citation lines, top-right = recent+impactful. See §3. |
| **Connected Papers** | [connectedpapers.com](https://www.connectedpapers.com/) | Similarity force-graph (not citations); node size = citations, **color shade = year** (time as gradient, no axis). |
| **ResearchRabbit** | — | Timeline view: X = year, Y = citation count; green = in collection, darker blue = more recent. The simple version of Litmaps. |
| **Inciteful** | [inciteful.xyz](https://help.inciteful.xyz/quick-start.html) | PageRank over the citation graph to surface canonical works. |
| **Open Knowledge Maps** | [openknowledgemaps.org](https://openknowledgemaps.org/about) | Bubble-cluster "knowledge map" with named regions. |

---

## 2. What makes a graph/embedding view look *good* (transferable principles)

These are the levers, roughly in order of impact:

1. **Density-aware edges.** Edge opacity should fall off with the degree of the node it touches. Hubs with 100 edges at full opacity = hairball; faded = "galaxy." This is the single biggest difference between Cosmograph and a naive vis-network graph.
2. **Edge color = source-node color** (with low alpha). Gives spatial-color coherence. Trade-off vs. **color-by-edge-type**, which is more informative in a *typed* KG — you can keep type info via dashes/secondary encoding while coloring by source.
3. **Node size encodes a metric** (degree or PageRank). Instant hierarchy: hubs big, leaves small.
4. **Color encodes cluster/category**, on a **neutral (usually dark) background**, so density does the visual work.
5. **Per-point alpha (~0.3–0.6)** in scatter/embedding views so overlap reads as density. Pros go further with **density-aware raster** (datashader) instead of fixed alpha. [Datashader plotting pitfalls](https://datashader.org/user_guide/Plotting_Pitfalls.html)
6. **Label-on-zoom (LOD).** A few big region labels when zoomed out; finer labels as you zoom in. Greedy highest-priority-first placement, suppress colliding lower-priority labels. [Automatic label placement](https://en.wikipedia.org/wiki/Automatic_label_placement)
7. **Less persistent chrome, more contextual panels.** The canvas fills the screen; UI (details, filters, analysis) appears on demand via hover/click/search rather than living in always-on full-height columns.
8. **Clean typography.** A neutral sans (Inter / Geist / system-ui) reads as "product"; a monospace reads as "code dump."

---

## 3. Litmaps chronological view — how to replicate

From [Litmaps visualisation guide](https://medium.com/litmaps/guide-to-litmaps-visualisations-95a9bc2cc9de) and [official docs](https://docs.litmaps.com/en/articles/9181490-use-and-edit-litmaps-visualization):

- **X axis = publication date** (older left, newer right). Default "Compact" evenly spaces by date and places a citing paper *left* of the paper it cites.
- **Y axis = "Compact" optimizer** with three goals: (a) spread vertically to avoid label collisions, (b) keep a paper's Y stable across maps, (c) minimize total citation-line length. Alternative Y axes: Citations, Citations (log), Title-similarity.
- **Net effect:** impactful + recent papers land **top-right**.
- **Nodes** are dots; **size = log(citation count)** (or constant, toggle). Color by sub-topic/tag + optional per-paper halo.
- **Edges** = citation lines, thin and subtle, no arrowheads — direction is implied by left-right position. The Compact algorithm explicitly minimizes total line length, so edges are short connectors, not a hairball.
- **Labels** have 6 modes (Keyword / Author-Year / Title / Compact / Off). On overlap, **only the higher-cited paper's label renders.**

**Replication recipe for our explorer:**
1. X = publication year, mapped linearly; **lock node X**, don't let physics move it.
2. Y = initialize by log(citations) (or in-degree as a proxy), then run a **1-D collision-avoidance pass** on Y only: nudge overlapping labels apart while pulling cited-pairs closer. This reproduces the "Compact" feel and avoids everything stacking on one date column.
3. Node radius `∝ log(citations+1)`, clamped.
4. Edges: thin, low-opacity, no arrowheads.
5. Labels: render only above a zoom threshold; drop the lower-cited label on overlap.
6. Bug to fix: switching **back** to force-graph after chrono must restore physics + free node X/Y and re-fit.

**What's distinctive (so we don't accidentally build Connected Papers instead):** left-to-right *time flow* + gentle non-strict vertical spread + short sparse citation lines. Connected Papers has *no* time axis (time = color). ResearchRabbit uses a rigid X=year/Y=citations scatter with no Compact optimizer.

Sources: [Litmaps docs](https://docs.litmaps.com/en/articles/9181490-use-and-edit-litmaps-visualization) · [How to create a literature map](https://www.litmaps.com/learn/how-to-create-a-literature-map) · [Aaron Tay comparison](https://aarontay.medium.com/3-new-tools-to-try-for-literature-mapping-connected-papers-inciteful-and-litmaps-a399f27622a) · [Connected Papers vs Litmaps](https://www.thomasbertelsen.com/literature-map-tools-face-off-connected-papers-vs-litmaps-for-phd-research-2025/).

---

## 4. How Cosmograph shapes those clusters (force-layout mechanics)

Cosmograph/cosmos.gl runs a standard force simulation **on the GPU**; the cluster shapes emerge from the same physics we already use (barnesHut), tuned so that:

- **Strong node-node repulsion** pushes unconnected groups apart → whitespace between clusters.
- **Long springs** keep connected nodes far enough apart that edges are visible, not a blob.
- **Weak central gravity** (or per-cluster gravity, not global) lets spring islands form instead of collapsing to one mass.
- **Optional explicit cluster forces** (`setPointClusters`, `setClusterPositions`, `setPointClusterStrength`) pull labeled groups toward assigned anchors — so you can *seed* the clustering rather than hope physics finds it.
- **GPU rendering at 60fps** means you watch it settle, which itself reads as "alive/organic."

This matches our `CLAUDE.md` physics notes exactly (long springs + avoidOverlap = cluster islands; high centralGravity = featureless blob). The visual gap is **rendering** (WebGL bloom, degree-faded edges, source-colored edges, dark bg), not the layout math.

Source: [cosmos.gl GitHub](https://github.com/cosmosgl/graph) · [cosmos.gl → OpenJS Foundation](https://openjsf.org/blog/introducing-cosmos-gl).

---

## 5. Nomic-style embedding maps + cluster labels — how to replicate

From Apple's [Scalable Clustering of Embedding Projections (arXiv 2504.07285)](https://arxiv.org/html/2504.07285v2), [Embedding Atlas](https://apple.github.io/embedding-atlas/embedding-view.html), [Nomic docs](https://docs.nomic.ai/atlas/embeddings-and-retrieval/guides/how-to-visualize-embeddings), [BERTopic](https://maartengr.github.io/BERTopic/), [UMAP clustering docs](https://umap-learn.readthedocs.io/en/latest/clustering.html):

1. **Render raw UMAP coords with physics OFF.** Physics on top of UMAP destroys the structure — prime "blob" cause.
2. **Re-bake UMAP for clustering:** `min_dist = 0.0` (packs clusters, opens gaps), `n_neighbors ≈ 30` (clearer global structure).
3. **Cluster the 2D projection, not the high-D vectors.** Apple's trick: KDE to a ~1000×1000 grid → hill-climb to local density maxima (union-find) → merge near-touching peaks → truncate each cluster at `0.1 × peak`. ~50 ms for >1M points. Simpler alternatives: **HDBSCAN** (noise-robust, good for ~840 nodes) or **k-means** (fixed N hotspots).
4. **One label per cluster** at the **medoid** (PixPlot) or **density peak** (Apple) — reads better than centroid for irregular shapes. Assign `priority`+`level`, place greedily, suppress collisions, gate by zoom.
5. **Auto-name clusters with c-TF-IDF** (treat each cluster as one document; top distinctive terms). Cheap fallback: **modal Category** (we already have Category nodes). Best: feed top terms + sample titles to an LLM for a 2–4-word name.
6. **Topographic "Nomic look":** KDE heatmap underlay + low-opacity homogeneous color fills per region, dots on top.
7. **Why a UMAP looks like a blob and isn't:** usually **overplotting**, not bad layout — add alpha + density-scaled point size and the structure appears.

**Prioritized "do these 5":**
1. Embedding view = raw UMAP coords, physics OFF.
2. Re-bake UMAP `min_dist=0.0, n_neighbors≈30`; per-point alpha ~0.4; density-scaled size.
3. Cluster on the 2D points (HDBSCAN for ~840 nodes).
4. Name with c-TF-IDF (fallback modal Category), label at medoid/density peak, zoom-gated.
5. Add a KDE density underlay for the topographic look.

---

## 6. Open-source rendering engines we could adopt

For: vanilla single-file app, ~2,400 nodes now (want 50k+ headroom), need **force-graph + UMAP-scatter + cluster labels**, minimal/no build step.

| Library | License | Renders | Tech | Ceiling | Drop-in (no build)? | Clustering + labels |
|---|---|---|---|---|---|---|
| **cosmos.gl** (`@cosmos.gl/graph`) | MIT | graph **and** scatter (one engine) | WebGL GPU | ~1M | **Yes** — ESM via CDN | clustering force; labels = your overlay |
| @cosmograph/cosmograph | proprietary (free tier) | both + widgets | WebGL (cosmos core) | millions | leans to bundling | built-in clustering + labels |
| sigma.js + graphology | MIT | graph only | WebGL | ~tens of k | bundle/ESM | community detection; cluster labels DIY |
| regl-scatterplot | MIT | scatter only | WebGL (regl) | ~20M | **Yes**, tiny | no edges/labels |
| deck.gl | MIT | both | WebGL2/WebGPU | ~1M+ | UMD exists, wants bundling | TextLayer (manual) |
| Apache ECharts (+echarts-gl) | Apache-2.0 / BSD | both | Canvas / WebGL | medium | **Yes**, script tag | categories native; clustering manual |
| 3d-/force-graph | MIT | graph | Three.js / Canvas | ~tens of k | **Yes**, UMD/ESM | none built-in |
| AntV G6 v5 | MIT | graph | Canvas/SVG/WebGL | ~tens of k | **Yes**, CDN | clustering + community layouts built-in |
| Ogma (Linkurious) | commercial | graph | WebGL | enterprise | licensed | full-featured (paid) |
| Apple embedding-atlas | MIT | scatter (+search) | WebGPU/Wasm | ~millions | React/Svelte (needs build) | **auto-cluster + auto-labels (best here)** |

**Ranked recommendation:**
1. **cosmos.gl** — the open MIT core behind Cosmograph; one WebGL engine for *both* our modes, CDN-importable (fits single-file), scales past 50k. Cluster labels rendered in our own overlay (we already do custom label/canvas work). Cleanest "drop-in that fixes slow/weak-looking."
2. **regl-scatterplot** — pair with cosmos.gl if we want the embedding mode rock-solid at huge scale (20M ceiling). Scatter only.
3. **Apple embedding-atlas** — best if auto cluster labels are the priority and we accept a bundler.

**Honest take:** at 2,400 nodes, staying on vis-network is functionally fine — but it's Canvas, it won't reach 50k, and `CLAUDE.md` is already full of barnesHut tuning workarounds. If WebGL polish + headroom matter, migrate to cosmos.gl. Skip @cosmograph/cosmograph (proprietary), echarts-gl (stagnant), G6 (graph-centric), Ogma (paid).

Sources: [cosmos.gl](https://github.com/cosmosgl/graph) · [@cosmos.gl on jsDelivr](https://www.jsdelivr.com/package/npm/@cosmos.gl/graph) · [sigma.js](https://github.com/jacomyal/sigma.js/) · [regl-scatterplot](https://github.com/flekschas/regl-scatterplot) · [deck.gl perf](https://deck.gl/docs/developer-guide/performance) · [echarts-gl](https://github.com/ecomfe/echarts-gl) · [3d-force-graph](https://github.com/vasturiano/3d-force-graph) · [AntV G6](https://github.com/antvis/G6) · [embedding-atlas](https://github.com/apple/embedding-atlas).

---

## 7. Decision log / open questions

- **Keep vis-network or migrate to cosmos.gl?** Migration is a multi-day rewrite of the render layer. Defer until the cheap visual wins (§2) are exhausted and we actually need >10k nodes.
- **Edge color: by source node or by edge type?** Source-node color looks better; edge-type color is more informative for a typed KG. Current plan: color by source node, preserve type via existing dash patterns.
- **Re-baking UMAP** requires re-running `scripts/project-embeddings.py` with new `min_dist`/`n_neighbors`. Worth doing once embedding mode renders raw coords with physics off.
