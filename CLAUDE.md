# AI Engineering Design DB Explorer

Single-file graph explorer (`explorer.html`) served via Vercel. All code lives in that one file.

## Testing with Playwright (required)

**Always test layout/visual changes with Playwright before committing.**

### Real-data visual tests (for physics, layout, visual regressions)
```bash
# Start the local server first (port 8770)
python -m http.server 8770 &

# Run visual tests (real vis-network, real 2405-node data)
npx playwright test tests/visual.spec.js --headed

# View screenshot after run
tests/screenshots/default-load.png
```

### Unit tests (mock vis-network, fast)
```bash
npx playwright test tests/explorer.spec.js
```

### Key metrics the visual tests check
- `state.network.getScale()` < 0.35 → viewport is zoomed out enough to see everything
- Node position xRange > 500 AND yRange > 500 → graph is spread, not collapsed
- Aspect ratio 0.4–2.5 → organic shape, not extreme rectangle or square packing
- `embedActive: false`, `forceEnabled: true` on default load

## Physics rules (DO NOT break these)
The layout shows natural hub-and-spoke clusters (dense center, sparse periphery) when:
- Use **`barnesHut` solver** — ForceAtlas2Based creates square packing with 2000+ nodes
- `avoidOverlap: 0.15–0.25` — creates whitespace between nodes so clusters are readable (avoidOverlap > 0.4 → square boundary)
- `centralGravity: 0.005–0.01` — very weak central pull, lets spring forces dominate → cluster islands form
- `springLength: 180–220`, `springConstant: 0.08–0.12` — long springs mean connected nodes form islands separated by gaps
- `gravitationalConstant: -12000 to -20000` — strong node repulsion separates unconnected clusters
- Physics timer **≤ 3500ms** — nodes start from UMAP positions (already organic); long physics destroys that
- ALWAYS call `network.fit()` after physics stops (`handleNetworkStabilized` + `settlePhysics` timer)

**Key insight on cluster formation:** Long springs + avoidOverlap = cluster islands. Short springs + no avoidOverlap = uniform blob. High centralGravity compresses everything to one mass regardless of other settings.

**Current working physics (barnesHut, clustered hub-and-spoke):**
```js
solver: "barnesHut",
barnesHut: {
  gravitationalConstant: -15000,
  centralGravity: 0.006,
  springLength: 200,
  springConstant: 0.10,
  damping: 0.15,
  avoidOverlap: 0.20,
},
stabilization: { iterations: 100 },
// settlePhysics timer: 3500ms
```

**Why NOT ForceAtlas2Based with avoidOverlap > 0.4:**
With 2000+ nodes, very high avoidOverlap forces ALL nodes to repel equally → square packing at canvas boundary. Keep avoidOverlap ≤ 0.25 with barnesHut.

**Why NOT high centralGravity (> 0.05):**
High centralGravity pulls everything toward one center regardless of connections → featureless blob with no visible clusters.

## Key architecture
- `explorer.html` — single-file SPA, ~4900 lines
- `graph/` — `graph-data.json` loaded at runtime
- `graph/embed-coords.json` — UMAP 2D positions (embed_x, embed_y) for 831 project nodes
- Node initial positions: projects start at UMAP × 120, other nodes at centroid of neighbor projects
- Default types: Project, Organization, Category (3 types) + BUILT_BY, IN_CATEGORY edges (2 types)

## Vercel deploy
Push to `main` on GitHub → auto-deploys. Check `vercel.json` for rewrites.

## Common pitfalls
- `avoidOverlap > 0.4` creates square packing at boundary
- `centralGravity > 0.05` compresses graph into featureless blob (all cluster signal lost)
- Short `springLength` (< 100) collapses clusters into each other instead of separating them
- Missing `network.fit()` after physics → viewport stays zoomed in
- `Venue` shape must NOT be `"database"` — that shape disappears on hover in vis-network
- `multiselect: false` in vis-network options — otherwise drag creates a selection rectangle
