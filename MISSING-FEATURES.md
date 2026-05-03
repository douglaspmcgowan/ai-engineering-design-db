# Missing Features — AI Engineering Design DB Explorer

Catalogued from Codex review + session observations. Not prioritized — add to these as we go.

---

## High-value / Likely to build

### Edge inspection
Clicking an edge shows nothing. A popup or detail panel entry should show:
- Relationship type (e.g. USES_TECHNIQUE)
- Source node + target node labels
- Any edge properties (e.g. weight, year added)

### Shareable deep links
No way to share a specific node or view state. URL should encode:
- Selected node ID
- Active node/edge type filters
- View preset name (if applicable)
- Maybe: canvas pan/zoom position

### Relationship tracing (path finding)
"How is node A connected to node B?" — shortest-path or all-paths query with visual highlight. Useful for: "which organizations share a technique?" "what connects Project X to Project Y?"

### Search with results panel
Current search highlights the first matched node but gives no ranked list. A results panel (like VS Code's quick-open) with ranked matches by label, type, degree would be much faster to navigate.

### Node pinning
Hold a node in place while physics runs around it. Useful for anchoring known hubs before using Gephi phases or Remove Overlap.

---

## Medium value

### Edge weight visualization
Some edge types could have weights (e.g. citation count for CITES edges). Thicker edges for stronger connections would add a visual hierarchy layer.

### Undo / redo for layout moves
After drag-repositioning several nodes, "undo" to restore prior positions. State stack would need to track `nodePositionCache` snapshots.

### Saved layouts
Persist the current node positions to localStorage so refreshing the page restores your manual arrangement. (Related to shareable deep links if positions are encoded in URL.)

### Multi-node selection details
When multiple nodes are box-selected (shift+drag), the detail panel could show aggregate stats: shared neighbors, shared edge types, combined degree.

### Export graph view
Export the currently-visible subgraph as:
- PNG/SVG screenshot (with node labels)
- JSON (filtered adjacency list for the visible nodes/edges)

### Neighborhood expansion ("load more")
In focus mode (double-click a node), currently shows N-hop neighbors. A "load 2nd ring" button would let users progressively expand without switching to full graph.

---

## Lower priority / Nice to have

### Keyboard shortcuts cheat sheet
The `?` modal lists some shortcuts but misses several (e.g. `/` to search, double-click focus). A complete reference would help new users.

### Node history / breadcrumb
After navigating through several double-click focus expansions, a back-button or breadcrumb trail to return to previously focused nodes.

### Embed mode for all node types
Currently embed mode shows only 831 Project nodes (those with UMAP coords). Once `scripts/embed-all-entities.py` is run and `build-graph.py` is updated, embed mode could show all 2405 nodes in joint semantic space.

### Physics preset import/export
Copy-paste a JSON blob of physics params — useful for sharing interesting configurations or saving custom presets beyond the 4 built-in ones.

### Cluster labels / annotation overlay
Auto-label dense regions of the graph based on the dominant Category or Technique among nodes in that region. Like Gephi's "Modularity Labels."

### Timeline slider
Filter by Year using a range slider — show only projects released between 2018–2022, animate forward year by year.

---

## Technical debt noted by Codex review

- `computeViewModel()` does full-graph rescans on every filter change — could diff against previous state
- Whole-file architecture (5300+ lines) makes it hard to work on isolated subsections; consider splitting into JS modules loaded as `<script type="module">`
- No error boundary around vis-network init — a bad graph-data.json silently breaks the whole page
