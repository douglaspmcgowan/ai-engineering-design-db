# Knowledge Graph Explorer — Feature Audit

> **Scope:** Compare `explorer.html` (vis-network single-file SPA, ~5500 lines) against (A) the user's own "ways-of-thinking-through-things" site and (B) the leading citation/network exploration tools. Recommend what to port.

---

## 1. Features the user's site has that this DB lacks

**Status: blocked.** All three URL variants returned HTTP 404 on 2026-05-07:

- `https://ways-of-thinking-through-things.vercel.app/` → 404
- `https://waysofthinkingthroughthings.vercel.app/` → DNS failed
- `https://ways-of-thinking.vercel.app/` → 404

The site was not findable via web search either (no public index entry). Possible causes: project renamed, taken offline, on a custom domain, or behind preview-deploy auth. Cannot perform the gap analysis until a working URL is provided. **Action: paste the live URL or push the latest deploy, then re-run Task A.** A separate `ai-in-design-map.vercel.app` deploy was reachable but is a static taxonomy site with no graph view, so it does not substitute.

---

## 2. Top 10 features from other KG tools (ranked, value-for-effort)

Existing baseline (do not re-port): vis-network rendering, search, category/year/modality/org filters, click detail, double-click 1-hop focus, Find Similar, embed mode (UMAP), localStorage collections, GitHub-API submission, palette switching, physics sliders, timeline view, shareable filter URLs.

| # | Feature | Source | What it does | Why it matters here | Cost |
|---|---|---|---|---|---|
| 1 | **Edge click → relationship panel** | (own MISSING-FEATURES.md, also Bloom, Kumu) | Selecting an edge shows source/target labels, relationship type (USES_TECHNIQUE, BUILT_BY, CITES), and any edge properties. | The graph encodes 2+ edge types but they are currently dead targets. With ~2400 nodes, edges carry most of the semantic load — making them inspectable converts a pretty picture into an actual exploration tool. | **S** |
| 2 | **Shortest-path / "how is A connected to B"** | Inciteful, Neo4j Bloom, Kumu | Pick two nodes; tool draws and highlights the shortest path (or all paths up to N hops) between them, dimming the rest. | The killer question for an AI-for-design corpus is "what connects MIT's lab to Autodesk's product line?" or "what techniques bridge generative design and topology optimization?" That is path-finding, not 1-hop neighborhood. | **M** |
| 3 | **PageRank / centrality ranking + size-by-metric** | Inciteful (PageRank), Gephi Lite, Kumu (degree/betweenness/eigenvector) | Compute a centrality metric on the visible subgraph and (a) list the top-N nodes in a side panel, (b) optionally size or color nodes by score. | Right now there is no "what are the most influential projects/labs/techniques?" surface. PageRank on the citation/USES_TECHNIQUE graph would auto-surface the canonical works. Graphology already runs in-browser. | **M** |
| 4 | **Cluster auto-labels / modularity overlay** | Open Knowledge Maps (bubble clusters), Gephi modularity | Run community detection on the graph; overlay a translucent label ("LLM planners," "topology optimization," "CAD kernels") on each detected region. | The user's own MISSING-FEATURES.md flags this. With 2400 nodes the eye sees clusters but cannot name them. Auto-labels turn the graph into an at-a-glance field map without manual curation. | **M** |
| 5 | **Earlier work / Later work / Similar work toggles** | Research Rabbit (signature feature), Connected Papers (Prior/Derivative) | From a selected node, three buttons reveal (a) ancestors it cites or builds on, (b) descendants citing it, (c) techniquely similar peers. Replaces the current single "Find Similar." | The corpus has CITES edges and technique overlap. Splitting "similar" into temporal axes matches how researchers actually navigate ("what came before this?" "what built on it?") and is cheap given existing data. | **S** |
| 6 | **Search results panel (ranked) + in-graph hit highlighting** | Litmaps, Bloom, OK Maps in-map text search | Live ranked list of matches by label, type, degree; arrow-key through; current focus stays in sync with graph highlight. Replaces the current "first match wins." | Already on user's own missing list. With 2400 nodes the current search misses obvious hits behind same-prefix labels. | **S** |
| 7 | **Saved views / perspectives** | Kumu (views), Neo4j Bloom (perspectives) | Persist {filter set + node positions + zoom + selected node + palette} as a named view; share via URL or list. Builds on existing shareable-filter URL. | Lets the user pin "the LLM-planner subgraph" or "everything from CMU 2023+" and jump back instantly. Also useful for paper figures and talks. | **M** |
| 8 | **Decoration rules (size/color by attribute)** | Kumu decorations, Gephi appearance, Bloom rule-based styling | UI to say "size nodes by year-recency" or "color by modality" or "size edges by citation count." User-defined, not hardcoded. | Current palette switching is whole-graph; decoration rules let users encode 2 dimensions at once (e.g. color = category, size = PageRank). High expressivity at modest UI cost. | **M** |
| 9 | **Step-by-step presentation mode** | Kumu presentations, Connected Papers walkthroughs | Author a sequence of view states with caption text; viewers click "next" to walk the graph. Each step = saved view + markdown caption. | The user is heading to ASME IDETC and writing fellowship apps. A presentation mode lets the same graph become talk slides — huge leverage for research dissemination. Builds directly on #7. | **M** |
| 10 | **Citation-monitoring / "alert me on new"** | Litmaps Monitor, Research Rabbit alerts | When new entries are added to the corpus that touch a saved view (e.g. new project tagged with "topology optimization"), surface them in a "what's new" panel. | The DB grows via GitHub-API submission. Without a "new since I last looked" feed, returning users see no signal of growth. Implement as: localStorage timestamp per view + diff against `consolidated.jsonl`. | **M** |

**Considered but not recommended right now:**
- BibTeX/RIS export (Connected Papers) — corpus is not citation-shaped enough to justify
- Natural-language search (Bloom) — needs an LLM call per query, infrastructure overhead
- Author-network sub-graph (Research Rabbit) — would need person-level resolution the schema doesn't have
- GPU rendering (Bloom) — vis-network handles 2400 nodes fine; premature
- Local-graph depth slider (Obsidian) — already partially covered by double-click focus

---

## 3. Recommendation: build these three first

Pick the smallest set that turns the explorer from "looks cool" into "I learned something." Build in this order:

### (1) Edge click + Earlier/Later/Similar toggles → first
**Why first:** Both are S-cost, both unlock data already in the graph, and together they fix the biggest UX cliff (clicking an edge does nothing; "Find Similar" hides what kind of similarity). One afternoon of work, immediate payoff.

### (2) PageRank ranking with top-N panel and size-by-score → second
**Why second:** Surfaces the corpus's actual structure — which labs, techniques, and projects matter most — in a way no current control does. Graphology runs client-side, no backend. Pairs naturally with the Earlier/Later toggles to answer "what's the canonical chain?" Medium effort, single biggest analytical lift.

### (3) Saved views / perspectives + presentation mode → third
**Why third:** Bridges from "exploration tool" to "communication tool." Once the user can save a view, they can build the IDETC talk inside the explorer instead of in PowerPoint screenshots. Reuses the existing shareable-URL plumbing — half the work is already done.

Cluster auto-labels (#4) is the strongest "wow" feature and worth doing fourth, but only after the analytical primitives in (1)-(3) exist; without them, labels are decoration.

---

**Sources used (Task B):**
- [Litmaps Features](https://www.litmaps.com/features), [Aaron Tay's tools comparison](https://aarontay.medium.com/3-new-tools-to-try-for-literature-mapping-connected-papers-inciteful-and-litmaps-a399f27622a)
- [Open Knowledge Maps eLife paper](https://elifesciences.org/labs/ef274c83/open-knowledge-maps-a-visual-interface-to-the-world-s-scientific-knowledge), [About OK Maps](https://openknowledgemaps.org/about)
- [Connected Papers — HKU guide](https://blog-sc.hku.hk/connected-papers-a-visual-tool-that-helps-speed-up-your-literature-search/), [Ness Labs review](https://nesslabs.com/connected-papers)
- [Research Rabbit Peer Review demo](https://thepeerreview-iwca.org/issues/issue-9-1/tool-demo-researchrabbit-an-ai-driven-tool-for-literature-mapping/), [HKUST Library guide](https://libguides.hkust.edu.hk/citation-chaining/researchrabbit)
- [Inciteful Quick Start](https://help.inciteful.xyz/quick-start.html), [HKUST Inciteful guide](https://libguides.hkust.edu.hk/citation-chaining/inciteful)
- [Kumu Metrics docs](https://docs.kumu.io/guides/metrics), [Kumu Architecture](https://docs.kumu.io/overview/kumus-architecture)
- [Obsidian Graph view help](https://obsidian.md/help/plugins/graph), [Extended Graph plugin](https://www.obsidianstats.com/plugins/extended-graph)
- [Neo4j Bloom Perspectives](https://neo4j.com/docs/bloom-user-guide/current/bloom-perspectives/bloom-perspectives/), [Bloom search bar](https://neo4j.com/docs/bloom-user-guide/current/bloom-visual-tour/search-bar/)
- [Gephi Lite documentation](https://docs.gephi.org/lite/), [Gephi Lite v1.0 release](https://gephi.wordpress.com/2025/10/08/gephi-lite-v1/)
