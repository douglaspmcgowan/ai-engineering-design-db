# Current Task — Done (18/18 tests passing)

**Verifier:**
```bash
python -m http.server 8770 &
npx playwright test tests/explorer.spec.js   # 13/13
npx playwright test tests/visual.spec.js     # 5/5
```

---

## All completed this session

- [x] Panel consolidation — discover nav moved into detail panel; tools sidebar always shows
- [x] URL ↗ button in detail panel header (shown for nodes with url_primary)
- [x] build-graph.py + graph-data.json rebuilt with embed_all_x/y for all 2405 nodes
- [x] Multi-word tokenized search (all tokens must match)
- [x] Search suggestions dropdown — typeahead, click enters focus mode
- [x] Search keyboard nav — ↑↓ arrows + Enter consistent with click-on-suggestion
- [x] Double-click focus bug fixed — viewport now fits to neighborhood (fit:true)
- [x] Zoom choppiness fixed — removed competing focusCameraOnNode+fitVisibleGraph animations
- [x] Discover mode node-type filter bug — focus roots are force-included in eligible set
- [x] Embed mode hides Physics Lab + View Presets sections
- [x] Embed all-nodes toggle ("Projects only" button in topbar, switches to 2405-node joint UMAP)
- [x] Cluster click-to-zoom — clicking a hull in embed mode zooms to that cluster
- [x] Cursor pointer on cluster hull hover
- [x] Discover affordance in empty detail panel tip + help modal overview + shortcuts list
- [x] Codex UX review completed
- [x] Node pinning — right-click → "📌 Pin node" / "📌 Unpin node"; orange border indicator; physics runs around pinned nodes; cleared on reset
- [x] Semantic similarity search — "🔍 Find similar" button in detail Actions section (nodes with embed coords); computes top-12 UMAP nearest neighbors; activates similarity focus mode with "Similar to: X . Exit" label
- [x] Search results mini semantic map — SVG dot-map appended below search suggestions when ≥3 results have embed coords; edges drawn between result nodes; click dot to enter focus on that node

## Key files
- Explorer: `explorer.html` (~6250 lines)
- Tests: `tests/explorer.spec.js` (13 tests), `tests/visual.spec.js` (5 tests)
- Graph data: `graph/graph-data.json` (2405 nodes, 8795 edges, embed_all_x/y injected)
