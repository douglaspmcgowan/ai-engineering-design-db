# Current Task — Data Fixes + UX/UI Improvements

**Goal:** Fix missing data fields in raw JSONL files, add total neighbor count to discover mode, then do UX/UI research and improvements.

**Verifier:**
```bash
python -m http.server 8770 &
npx playwright test tests/explorer.spec.js   # must pass
npx playwright test tests/visual.spec.js     # must pass
npx playwright test tests/audit.spec.js      # must pass
```

---

## Steps

- [ ] 1. Fix 37 records missing `url_primary` → copy from `url_paper` in raw JSONL files
- [ ] 2. Fix 41 records missing `status` → infer from `type` field in raw JSONL files
- [ ] 3. Rebuild `graph/graph-data.json` via `python scripts/build-graph.py`
- [ ] 4. Add "X visible / Y total" neighbor count in discover mode panel (explorer.html)
- [ ] 5. Take screenshots of app, do UX/UI research, implement improvements
- [ ] 6. Run full Playwright test suites to verify

## Data fixes needed (from last audit)

### url_primary missing (37 records)
All 37 have `url_paper` as fallback — copy url_paper → url_primary.
Records: deepcad, skexgen, cad-mllm, brepnet, uv-net, polygen, meshgpt, point-e, shap-e, get3d, dreamfusion, magic3d, triposr, instantmesh, trellis, hunyuan3d-2, fno, deeponet, gino, pino, and ~17 more

### status missing (41 records)
Infer from type:
- academic-paper (24) → "research-prototype"
- open-source (15) → "open-source-tool"  
- benchmark-dataset (2) → "released-benchmark"

## Key files
- Explorer: `explorer.html` (~6300+ lines)
- Raw data: `raw/*.jsonl` (25 files)
- Build script: `scripts/build-graph.py`
- Graph data: `graph/graph-data.json`
- Tests: `tests/explorer.spec.js`, `tests/visual.spec.js`, `tests/audit.spec.js`
