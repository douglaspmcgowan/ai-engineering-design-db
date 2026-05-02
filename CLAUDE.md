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
The layout looks "natural" (organic blob, dense center, sparse periphery) when:
- Use **`barnesHut` solver** — ForceAtlas2Based creates square packing with 2400+ nodes
- `avoidOverlap: 0` — non-zero avoidOverlap pushes ALL nodes to boundary → square
- `centralGravity: 0.25` — pulls hubs to center, creates organic shape
- `springLength: 200`, `springConstant: 0.05` — connected nodes stay near hubs
- Physics timer **≤ 3500ms** — nodes start from UMAP positions (already organic); long physics destroys that
- ALWAYS call `network.fit()` after physics stops (`handleNetworkStabilized` + `settlePhysics` timer)

**Current working physics (barnesHut, organic blob):**
```js
solver: "barnesHut",
barnesHut: {
  gravitationalConstant: -8000,
  centralGravity: 0.25,
  springLength: 200,
  springConstant: 0.05,
  damping: 0.12,
  avoidOverlap: 0,
},
stabilization: { iterations: 100 },
// settlePhysics timer: 3500ms
```

**Why NOT ForceAtlas2Based with avoidOverlap > 0:**
With 2400+ nodes, avoidOverlap forces ALL nodes to repel each other, creating uniform pressure that pushes them to the canvas boundary → square packing. BarnesHut's gravitational model creates organic hub clustering instead.

## Key architecture
- `explorer.html` — single-file SPA, ~4800 lines
- `graph/` — `graph-data.json` loaded at runtime
- `graph/embed-coords.json` — UMAP 2D positions (embed_x, embed_y) for 831 project nodes
- Node initial positions: projects start at UMAP × 120, other nodes at centroid of neighbor projects

## Vercel deploy
Push to `main` on GitHub → auto-deploys. Check `vercel.json` for rewrites.

## Common pitfalls
- High `avoidOverlap` (> 0.4) creates square packing
- High `centralGravity` (> 0.01) compresses graph into a tight square
- Missing `network.fit()` after physics → viewport stays zoomed in
- `Venue` shape must NOT be `"database"` — that shape disappears on hover in vis-network
- `multiselect: false` in vis-network options — otherwise drag creates a selection rectangle
