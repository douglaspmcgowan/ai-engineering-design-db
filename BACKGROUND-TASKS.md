# Background Agent Tasks

## Task: explorer.html 7-fix repair — COMPLETED 2026-04-30
- **Commit**: 567d1e4 on main
- **Agent ID**: task-molvhl65-vwk3eo — was bogus (prompt="test"); fixes made directly by Claude
- **Note**: Codex notification hook updated in ~/.claude/settings.json (agent_complete → Windows popup)
- **Fixes landed**:
  1. ✅ FORCE_OPTIONS restored (gravitationalConstant -30, centralGravity 0.006, springLength 220, springConstant 0.15, avoidOverlap 0.4)
  2. ✅ Embed coord scale 80→120; Project size 10→6 in embed mode
  3. ✅ Zoom-reactive labels (handleViewportChanged → refreshNodeLabels, threshold zoomScale >= 0.65)
  4. ✅ Category cluster mode A groups by props.category (different hulls, not just different labels)
  5. ✅ Select All / Clear buttons added to Node Types + Edge Types sidebar
  6. ✅ Bloom cumulative discovery (accumulatedIds Set, expandFocusToNode, Backspace pops)
  7. ✅ Hull hover via JS mousemove (isPointInPolygon + checkHullHover, no pointer-events breakage)

---
## Task: Spring Length Screenshots — IN PROGRESS 2026-05-02
- **Agent ID:** bofyuidil
- **Script:** `_spring_length_shots.py`
- **Output dir:** `Obsidian/.../Research/attachments/spring-lengths/`
- **Files expected:** `sl-080.png`, `sl-120.png`, `sl-150.png`, `sl-200.png`, `sl-240.png`, `sl-280.png`
- **Output log:** `C:\Users\dougl\AppData\Local\Temp\claude\...\tasks\bofyuidil.output`
- **Re-dispatch:** `python _spring_length_shots.py` from project dir

---
## Task: Online Graph Screenshots — IN PROGRESS 2026-05-02
- **Agent ID:** b5us7pe07
- **Script:** `_online_graph_shots.js`
- **Output dir:** `Obsidian/.../Research/attachments/online-graphs/`
- **Files expected:** `01-connected-papers.png` through `10-semantic-scholar.png`
- **Output log:** `C:\Users\dougl\AppData\Local\Temp\claude\...\tasks\b5us7pe07.output`
- **Re-dispatch:** `node _online_graph_shots.js "<obsidian_dir>/Research/attachments/online-graphs"` from project dir

---
## Task: explorer.html performance + UX fixes
- **Agent ID:** b62i2ghsi
- **Dispatched:** 2026-04-30
- **Output file:** C:\Users\dougl\AppData\Local\Temp\claude\C--Users-dougl-My-Drive--douglaspmcgowan-gmail-com--UC-Berkeley-Research-Claude-Research-Folder\0a42a30d-13e5-48b4-8ed2-73476b8b6a4d\tasks\b62i2ghsi.output
- **Expected changes:** explorer.html only (6 fixes applied, Playwright tests passing, committed)
- **Re-dispatch if needed:** Run codex-rescue with --resume on the same task prompt (explorer.html perf/zoom/one-hop/visual/layout fixes)
- **Fixes:**
  1. Zoom lag — split handleViewportChanged into handleZoom + handleDragEnd
  2. Smooth edges → straight lines in Force mode
  3. Default node/edge types narrowed to Project/Org/Category/Technique + 3 edge types
  4. fit() calls get padding: 60 everywhere
  5. One-hop expand UX — background double-click exits focus, breadcrumb, Exploring label, camera on new node
  6. afterDrawing RAF gated to embed mode only
