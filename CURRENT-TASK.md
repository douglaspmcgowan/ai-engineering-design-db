# Current Task — Multi-fix pass on explorer.html

**One-sentence goal:** Fix zoom, physics timer, filter-change physics restart, tooltip position, hierarchical freeze, remove-overlap second-run, discover mode UX, stats visibility, and sidebar width.

**Verifier:**
```bash
python -m http.server 8770 &
npx playwright test tests/explorer.spec.js
npx playwright test tests/visual.spec.js
```

---

## Items (check off as done)

- [ ] 1. **Right sidebar wider** — `--tools-w: 220px` → `280px` (CSS line ~375 + layout default)
- [ ] 2. **Zoom out more at start** — fit padding 60→120px everywhere; set initial view scale 0.12 right after network init
- [ ] 3. **Physics timer display** — add `#phys-timer` div (elapsed / total); `setInterval` in `settlePhysics`, clear in `disablePhysics`
- [ ] 4. **Physics duration lever** — add `#phys-duration` slider (2–30s, default 7); `settlePhysics` reads it
- [ ] 5. **Don't restart physics on filter changes** — remove auto-`settlePhysics()` from `applyView`; call it explicitly only on first data load and `applyViewPreset`
- [ ] 6. **Physics stops too quickly** — remove `disablePhysics()` from `handleNetworkStabilized` (let 7s timer control stopping); only call `fit + clamp` there
- [ ] 7. **Tooltip position fix** — use `visibility:hidden` + `offsetWidth/Height` before final positioning (same pattern as context menu fix)
- [ ] 8. **Hierarchical preset freeze** — after applying any view preset, ensure `fixed: {x:false,y:false}` on all nodes via a DataSet update; also call `network.startSimulation()` after `settlePhysics`
- [ ] 9. **Remove Overlap second run fix** — add `state.network.startSimulation()` after `setOptions` in `removeOverlap()`; same for `settlePhysics`
- [ ] 10. **Stats show visible counts** — `statsGrid` cards show `currentView` node/edge counts as primary; note text shows totals + project count
- [ ] 11. **Discover mode UX** — add `#discover-panel` inside tools-panel; shown when `state.focus` is active, hides View Presets + Physics Lab; shows focused node info + prev/next neighbor nav + depth toggle + exit button
- [ ] 12. **Version date** — update version string in `updateStats()` to "2026-05"

---

## Key files
- Explorer: `explorer.html` (~5300 lines) — ALL code in one file
- Tests: `tests/explorer.spec.js` (unit), `tests/visual.spec.js` (visual)
- Rules: `CLAUDE.md` — never break barnesHut physics, always test with Playwright

## Key constraints
- NEVER set `stabilization: { enabled: true }` in any physics options — causes invisible pre-compute
- Always call `network.startSimulation()` explicitly after `setOptions({ physics: { enabled: true } })`
- Physics is barnesHut only — do not switch to ForceAtlas2Based
- CSS Grid columns follow DOM order — tools-panel must come AFTER canvas-column in HTML
