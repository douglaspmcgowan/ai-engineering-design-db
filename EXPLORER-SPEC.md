# Explorer — Specs & Benchmarks

> What "good" means for `explorer.html`, as testable criteria. Paired with `KG-EXPLORERS.md` (the research) and the Playwright suites in `tests/`. Check items off as they land. This is the definition-of-done for the navigation/simplicity overhaul.

---

## A. Visual quality (force-graph mode)

| # | Spec | How to verify | Status |
|---|---|---|---|
| A1 | Default load auto-zooms so the whole graph fits (`getScale()` < 0.35) | `tests/visual.spec.js` | existing |
| A2 | Nodes sized so hubs are visibly larger than leaves (degree/PageRank encoded) | visual + DOM size check | partial |
| A3 | Node base size ~50% larger than the old baseline | screenshot diff | ☐ |
| A4 | Edge opacity falls off for high-degree hubs (no hairball) | screenshot of a hub | ☐ |
| A5 | Edge color = source-node color (type still legible via dash pattern) | screenshot | ☐ |
| A6 | Graph spread is organic (xRange & yRange > 500; aspect 0.4–2.5) | `tests/visual.spec.js` | existing |
| A7 | Physics settles within its timer then `network.fit()` is called | `handleNetworkStabilized` | existing |

## B. Typography & chrome

| # | Spec | Verify | Status |
|---|---|---|---|
| B1 | No monospace/"code" font in the UI — clean neutral sans throughout | grep `--font-mono` usages; visual | ☐ |
| B2 | No decorative emojis in buttons (🔍, ⚡, ▶, ◈, ⏵, raw ← →) | grep emoji codepoints | ☐ |
| B3 | Right-side tools (View presets / Analysis / Physics Lab / Stats) is a **floating window in the top-right**, not a full-height column | DOM + screenshot | ☐ |
| B4 | Left sidebar sections have **adjustable heights** (resize/collapse) | manual + DOM | ☐ |
| B5 | "Related work" buttons (Earlier / Similar / Later) look like real buttons, no emoji | screenshot | ☐ |

## C. Hover / tooltip

| # | Spec | Verify | Status |
|---|---|---|---|
| C1 | Tooltip appears **adjacent to the hovered node**, not pinned top-left | Playwright: hover node, assert tooltip left/top near node | ☐ |
| C2 | No stray black square rendered near the cursor on hover | screenshot at hover | ☐ |
| C3 | Tooltip hides on blur | existing handler | existing |

## D. Auto-zoom & physics

| # | Spec | Verify | Status |
|---|---|---|---|
| D1 | After any mode switch (force/embed/chrono), the view fits all visible nodes | Playwright: switch modes, assert scale | ☐ |
| D2 | Physics runs long enough to settle but ≤ a sane cap; UMAP geometry preserved in embed mode | timer check | ☐ |

## E. Embedding (UMAP) mode — the hard one

| # | Spec | Verify | Status |
|---|---|---|---|
| E1 | Embed mode renders **raw UMAP coords with physics OFF** (no barnesHut) | assert physics disabled in embed | ☐ |
| E2 | Clusters are **visually separated**, not a central blob | screenshot; cluster bbox spread | ☐ |
| E3 | Per-point alpha + density so dense regions read as density | screenshot | ☐ |
| E4 | Switching embed → force → embed is stable (positions restore) | Playwright round-trip | ☐ |
| E5 | Run the load 5+ times headed; no blank canvas, no all-overlapping nodes | repeated `visual.spec.js` runs | ☐ |

## F. Clusters & labels

| # | Spec | Verify | Status |
|---|---|---|---|
| F1 | Cluster labels render at cluster centroids/medoids, readable, non-overlapping | screenshot | ☐ |
| F2 | Cluster labels work in **both** force and embed modes | screenshot each | ☐ |
| F3 | Label density gated by zoom (fewer when zoomed out) | manual | ☐ |

## G. Chronological / Litmaps mode

| # | Spec | Verify | Status |
|---|---|---|---|
| G1 | X = publication year (locked); axis labels visible | screenshot | ☐ |
| G2 | Y = collision-avoidance spread of log(citations / in-degree), not weighted-embed | code review | ☐ |
| G3 | Thin, low-opacity citation lines, no arrowheads | screenshot | ☐ |
| G4 | Switching **back to force graph** from chrono works (physics restored, re-fit) | Playwright round-trip | ☐ BUG |
| G5 | Scrolling/pan works in chrono mode | Playwright | ☐ BUG |
| G6 | Reads recognizably like Litmaps (time flows left→right, recent+impactful top-right) | screenshot vs reference | ☐ |

## H. Discover & search

| # | Spec | Verify | Status |
|---|---|---|---|
| H1 | Discover opens to a **search bar** as the primary entry point | screenshot | ☐ |
| H2 | A **semantic search** toggle exists; results can build a focused sub-graph | Playwright | ☐ |
| H3 | Selecting a node from search results does **not** break detail-panel scroll | Playwright: search→select→scroll | ☐ BUG |
| H4 | Search shows a ranked results list, not just first-match | Playwright | partial |

## I. Detail panel & data hygiene

| # | Spec | Verify | Status |
|---|---|---|---|
| I1 | Duplicate links suppressed: if `url_primary == url_paper`, show one link | code + DOM (≈394 affected records) | ☐ |
| I2 | "Primary" link relabeled/explained (it's the canonical/home URL for the record) | copy review | ☐ |
| I3 | `codex-generated` provenance tag not shown as a user-facing chip (it's pipeline metadata) | DOM check | ☐ |
| I4 | Detail-body scrolls correctly for long records | Playwright | ☐ |

---

## Benchmarks (numeric targets)

- **Default-load scale:** `state.network.getScale()` < 0.35
- **Spread:** node xRange > 500 AND yRange > 500; aspect ratio 0.4–2.5
- **Embed mode:** physics disabled; cluster bounding-box centroids span > 60% of canvas (not collapsed)
- **Tooltip:** on hover, tooltip rect within ~120px of the hovered node's screen position (not at 0,0 / top-left)
- **Frame:** initial render + fit completes < 4 s on the 2,449-node dataset
- **Tests:** `tests/explorer.spec.js` (unit, 27) stays green; `tests/visual.spec.js` (real data) green

## Test commands

```bash
python -m http.server 8770 &                          # serve for visual tests
npx playwright test tests/explorer.spec.js            # fast unit (mock vis-network)
PW_SERVER=1 npx playwright test tests/visual.spec.js  # real-data visual
```

## Known bugs to close (from session 2026-05)

1. Chrono → force switch broken (G4).
2. Scrolling broken in chrono / on search-select (G5, H3).
3. Embedding mode "doesn't work" — blob, physics on top of UMAP (E1, E2).
4. Tooltip pinned top-left instead of by node (C1); stray black square on hover (C2).
5. Duplicate Primary/Paper links (I1); confusing `codex-generated` chips (I3).
