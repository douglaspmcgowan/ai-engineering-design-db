# Tech Debt Audit — ai-engineering-design-db
Generated: 2026-05-04

---

## Executive Summary

- 0 Critical findings. 2 High, 7 Medium, 6 Low.
- This is a healthy solo research project. The debt is real but manageable.
- **Largest single debt item:** `explorer.html` at 6,854 lines — a functional but unmaintainable god file that concentrates all risk.
- **Highest-impact quick fix:** Fix `package.json` test script — `npm test` currently errors, hiding that 3 Playwright test suites exist.
- **Documentation drift is the most pervasive pattern:** CLAUDE.md, PLAYBOOK.md, and SCHEMA.md all describe outdated state.
- **Repo hygiene:** Several temp/scratch artifacts committed to root and `raw/` that shouldn't be there.
- No CVEs (`npm audit` clean). No secrets in diff. XSS-safe (`escapeHtml` used consistently on all innerHTML writes).

---

## Architectural Mental Model

The system has two distinct layers that share only the `graph-data.json` artifact:

**Layer 1 — Data pipeline (Python scripts):** Raw domain-specific JSONL files in `raw/` (27 files, 842 records) are merged by `consolidate.py`, embedded by `embed.py` + `project-embeddings.py` + `embed-all-entities.py`, then assembled into `graph/graph-data.json` by `build-graph.py`. A separate large script (`generate_raw_sweep.py`, 1,423 lines) queries OpenAlex/DOI pages to build the raw files.

**Layer 2 — Graph explorer (single-file SPA):** `explorer.html` (6,854 lines of HTML + CSS + JS) loads `graph-data.json` at runtime, renders it with vis-network, and provides UMAP embedding view, physics simulation, clustering, search, and filtering. No build step — it serves directly from Vercel.

The pipeline is one-way and rebuild-from-scratch. There is no incremental update path: adding records means re-running consolidate → embed → build-graph in sequence. This sequence is documented in PLAYBOOK.md but not in README or as npm scripts.

The explorer is deployed on Vercel via GitHub push. The data files (`graph-data.json`, `embed-coords*.json`) are committed to the repo and served as static assets.

**One contradiction:** CLAUDE.md says the explorer is "~4900 lines" — it is 6,854. The file has grown ~40% beyond what the documentation describes. This is the clearest signal that docs are not being maintained as the app grows.

---

## Findings

| ID | Category | File:Line | Severity | Effort | Description | Recommendation |
|----|----------|-----------|----------|--------|-------------|----------------|
| F001 | Architectural decay | explorer.html:1–6854 | High | L | God file: 6,854 lines of HTML + CSS + JS with no module separation. All state, rendering, physics, UI, data loading, and event handling in one file. Every edit risks breaking something unrelated. | No rewrite needed. Extract CSS to `explorer.css` and the `state` object + pure utility functions to `explorer-core.js`, keeping the HTML as the shell. Requires adding a build step or using `<link>` + `<script src>`. Alternatively, split into clearly labeled `<!-- SECTION -->` comment blocks to aid navigation without a build step. |
| F002 | Configuration debt | package.json:7 | High | S | `"test": "echo \"Error: no test specified\" && exit 1"` — running `npm test` actively reports no tests exist. Three Playwright test suites exist (`explorer.spec.js`, `audit.spec.js`, `visual.spec.js`) with substantial coverage. | Change to `"test": "npx playwright test tests/explorer.spec.js"` and add `"test:visual": "python -m http.server 8770 & npx playwright test tests/visual.spec.js"`. |
| F003 | Documentation drift | CLAUDE.md | Medium | S | CLAUDE.md says "~4900 lines" (actual: 6,854), "831 project nodes" (actual: 842), and embed-coords path has wrong count. PLAYBOOK.md says 831 records / 2,405 nodes / 8,795 edges (actual: 842 / 2,449 / 8,884). | Update counts in CLAUDE.md and PLAYBOOK.md after each pipeline rebuild. Consider generating them from `consolidated-stats.json` rather than hand-editing. |
| F004 | Documentation drift | SCHEMA.md | Medium | S | SCHEMA.md category enum is missing Wave 4 categories: `design-cognition-ai` and `human-ai-design-collab`. Anyone adding records using SCHEMA.md as reference will get an invalid category. | Add Wave 4 categories to SCHEMA.md. Consider auto-generating the category list from `VALID_CATEGORY` in `consolidate.py` to keep them in sync. |
| F005 | Performance / resource hygiene | explorer.html:3058,3080,4337,5046,5081,6047,6606,6645,6665 | Medium | M | 9 bare `window.setTimeout()` calls with no stored ID. These timers cannot be cancelled if they fire after state has changed (e.g. user navigates away mid-timeout). Most are short (100–300ms) so the window is small, but one at line 4337 defers a `renderDetailPanel()` call after state could have been mutated by a parallel interaction. | Store IDs for any timeout that triggers a state-changing callback: `state.timers.detailDefer = window.setTimeout(...)` and clear before re-setting. The truly fire-and-forget ones (focus/scroll tweaks) are fine as-is. |
| F006 | Error handling | explorer.html:6833 | Medium | S | `fetch("./graph/graph-data.json")` has no timeout or AbortController. On a slow connection the loading overlay persists indefinitely with no retry or error recovery beyond the single catch block. | Wrap in an AbortController with a 15s timeout: `const ctrl = new AbortController(); setTimeout(() => ctrl.abort(), 15000); fetch(url, { signal: ctrl.signal })`. Show a "Retry" button in the catch handler. |
| F007 | Documentation drift | scripts/ | Medium | M | 19 Python scripts with no documented dependency order or run sequence. The pipeline order (consolidate → embed → project-embeddings → embed-all-entities → build-graph) is implicit. `generate_raw_sweep.py` at 1,423 lines is not mentioned in README at all. | Add a `## Pipeline` section to README with the ordered command sequence and what each script produces. Add npm scripts: `"pipeline": "python scripts/consolidate.py && python scripts/embed.py && ..."` |
| F008 | Repo hygiene | root | Low | S | `codex-task-input.txt` (7KB) and `gpt55-review.txt` (empty file) are operational artifacts committed to the repo root. These are noise for anyone cloning or browsing the repo. | Delete both files and add `*-task-input.txt`, `*-review.txt` to `.gitignore`. |
| F009 | Repo hygiene | raw/idetc26-temp-raw.json | Low | S | Scratch data file from the IDETC import workflow committed to `raw/`. It doesn't follow the `NN-domain-name.jsonl` naming convention and `consolidate.py` ignores `.json` (only reads `.jsonl`). It's dead weight. | Delete `raw/idetc26-temp-raw.json`. The data was already incorporated into `raw/26-idetc-design-cognition-ai.jsonl`. |
| F010 | Repo hygiene | `_embed_shots.js`, `_spring_length_shots.py` | Low | S | Scratch scripts prefixed with `_` in the repo root indicating they were always meant to be temporary. `knip` flags them as unused. | Delete both. If needed again they can be recreated from git history. |
| F011 | Configuration debt | package.json, playwright.config.js | Low | S | `knip` flags `lib/bindings/utils.js`, `lib/tom-select/*`, and `lib/vis-9.1.2/*` as unused. They're actually loaded via `<script src>` HTML tags — knip can't see HTML imports. This produces noisy false positives when running `npx knip`. | Add a `knip.json` ignoring `lib/`: `{ "ignore": ["lib/**"] }`. |
| F012 | Error handling | explorer.html:2551 | Low | S | `catch (_error) { regionName = ""; }` silently swallows the exception from `Intl.DisplayNames.of()` on invalid region codes. The behavior is correct but looks like a bug without a comment. | Add: `// Intl.DisplayNames.of() throws on invalid codes (e.g. "AA", "ZZ") — silently default` |
| F013 | Repo hygiene | root | Low | S | `BACKGROUND-TASKS.md` and `CURRENT-TASK.md` are session-management artifacts (per CLAUDE.md memory rules) committed to the repo. They're stale operational notes rather than project docs. | Either gitignore `CURRENT-TASK.md` and `BACKGROUND-TASKS.md`, or commit a policy of deleting them when tasks complete. |
| F014 | Test debt | tests/ | Low | S | Visual tests (`visual.spec.js`) require a pre-running HTTP server (`python -m http.server 8770`) that is not started by any npm script, CI config, or documented setup step. Running `npx playwright test` without the server causes visual tests to silently fail or time out. | Add a `globalSetup` script to `playwright.config.js` that starts and stops the HTTP server around the visual test suite. Or add a `pretest:visual` npm script. |

---

## Top 5 — if you fix nothing else, fix these

**1. F002 — Fix the npm test script** *(S effort, immediate payoff)*

```json
"scripts": {
  "test": "npx playwright test tests/explorer.spec.js",
  "test:all": "npx playwright test",
  "test:visual": "python -m http.server 8770 & sleep 1 && npx playwright test tests/visual.spec.js"
}
```
Right now `npm test` actively lies about whether tests exist. This is the first thing any CI system or new contributor would run.

**2. F004 — Add Wave 4 categories to SCHEMA.md** *(S effort, prevents bad data)*

SCHEMA.md is the canonical reference for anyone adding records. It's currently missing `design-cognition-ai` and `human-ai-design-collab`. Every new IDETC-style record added without checking `consolidate.py` directly will get the wrong category and be silently reclassified as `other`.

**3. F006 — Add a fetch timeout + retry UI** *(S effort, correctness)*

```js
const ctrl = new AbortController();
const timeoutId = window.setTimeout(() => ctrl.abort(), 15000);
const response = await fetch("./graph/graph-data.json", { signal: ctrl.signal });
window.clearTimeout(timeoutId);
```
The catch block already shows a toast. Also add a "Retry" button in `dom.emptyOverlay` that calls `loadDefaultGraph()` again.

**4. F008 + F009 + F010 — Repo hygiene sweep** *(S effort, <5 minutes)*

```bash
rm codex-task-input.txt gpt55-review.txt raw/idetc26-temp-raw.json _embed_shots.js _spring_length_shots.py
```
Five files, zero value, confuse anyone browsing the repo.

**5. F003 — Update CLAUDE.md with accurate counts** *(S effort, prevents wasted debugging)*

After each pipeline rebuild, the file counts in CLAUDE.md are wrong. A stale "4900 lines" causes confusion when someone (or a future Claude session) tries to understand the scope of work. Update once, then note in PLAYBOOK.md to update after rebuilds.

---

## Quick Wins

- [ ] **F002**: Fix `package.json` test script — 1-line change, `npm test` currently reports no tests
- [ ] **F004**: Add `design-cognition-ai`, `human-ai-design-collab` to SCHEMA.md category list
- [ ] **F008**: Delete `codex-task-input.txt` and `gpt55-review.txt`
- [ ] **F009**: Delete `raw/idetc26-temp-raw.json`
- [ ] **F010**: Delete `_embed_shots.js` and `_spring_length_shots.py`
- [ ] **F011**: Add `knip.json` with `{ "ignore": ["lib/**"] }` to silence false positives
- [ ] **F012**: Add a one-line comment to the `catch (_error)` block at `explorer.html:2551`
- [ ] **F013**: Gitignore `CURRENT-TASK.md` and `BACKGROUND-TASKS.md`

---

## Things that look bad but are actually fine

**86 addEventListener vs 2 removeEventListener.** This ratio looks alarming but is not a memory leak. The two removes are correct teardown of `mousemove`/`mouseup` handlers added during sidebar drag. The remaining 84 fall into two safe categories: (a) static listeners in `bindEvents()` attached once to long-lived DOM nodes that persist for the app's lifetime — these should never be removed; (b) listeners attached inside `renderDetailPanel()` to freshly-created `innerHTML` elements — those elements are discarded with the next `innerHTML =` overwrite, taking their listeners with them. No accumulation.

**`catch (_error) {}` at explorer.html:2551.** Looks like a swallowed bug. It's not — `Intl.DisplayNames.of()` throws on invalid ISO codes (like "AA" or "ZZ"), and silently defaulting to empty string is exactly correct behavior for building a country-name lookup table. The fix is just a comment.

**`lib/` flagged unused by knip.** `lib/vis-9.1.2/`, `lib/tom-select/`, and `lib/bindings/` are loaded via `<script src>` and `<link href>` tags in `explorer.html`. Knip can't see HTML imports, so it falsely reports them unused. They're essential.

**Single-file SPA architecture.** A 6,854-line single file looks like a mistake. For this project it's a deliberate tradeoff: no build toolchain, no bundler, deploys by git push. The cost is maintainability; the benefit is operational simplicity. Real debt, real tradeoff, not accidental.

**`generate_raw_sweep.py` at 1,423 lines.** Large but coherent — it's a data acquisition pipeline querying multiple external APIs (OpenAlex, DOI, Crossref, GitHub) with deduplication logic. The size is proportional to the number of data sources it handles. Not a god function situation.

---

## Open Questions for the Maintainer

1. **Is `visual.spec.js` ever actually run?** It requires a pre-running server and that step isn't automated anywhere. If it's been passing, how? If it's been skipped, the visual regression tests are providing no value.

2. **Is `KNOWLEDGE-GRAPH.md` still the plan?** It describes a proposed graph structure, but `build-graph.py` and the current graph seem to have diverged from whatever was originally proposed. Is this doc aspirational, historical, or actively maintained?

3. **What's the intended fate of `graph/graph.html`?** There's a second HTML file in `graph/` that appears to be an older or alternate explorer. Is it served anywhere? Is it meant to be kept in sync with `explorer.html`?

4. **Is `scripts/load-kuzu.py` in use?** It loads data into a KùzuDB graph database. There's no documentation of when this is run or what queries it's meant to support. Dead code or active workflow?

5. **Should `raw/00-seed-from-training.jsonl` be in gitignore?** It came from training data rather than the structured pipeline. Is it intentionally kept as a historical artifact, or should it be regenerated by `generate_raw_sweep.py` on future rebuilds?
