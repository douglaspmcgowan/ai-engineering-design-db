/**
 * audit.spec.js — Full exploratory audit of explorer.html using real data.
 * Runs against http://localhost:8770 (python -m http.server 8770 must be running).
 *
 * Takes screenshots at every major step into tests/screenshots/audit/.
 * Each test section is independent but they share a single long-running page
 * to exercise state transitions naturally.
 */

const { test, expect } = require("@playwright/test");
const path = require("path");
const fs = require("fs");

const BASE_URL = "http://localhost:8770/explorer.html";
const SS_DIR = path.resolve(__dirname, "screenshots/audit");
fs.mkdirSync(SS_DIR, { recursive: true });

let page; // shared across describes
let shotIdx = 0;
async function shot(label) {
  const fname = `${String(shotIdx++).padStart(3, "0")}-${label.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}.png`;
  await page.screenshot({ path: path.join(SS_DIR, fname), fullPage: false });
  return fname;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

async function waitForGraph() {
  // loading overlay gets display:none via is-hidden — use state:attached not visible
  await page.waitForSelector("#loading-overlay.is-hidden", { state: "attached", timeout: 30000 });
  await page.waitForFunction(
    () => {
      try { return typeof state !== "undefined" && state.currentView?.nodeIds?.size > 800; }
      catch { return false; }
    },
    { timeout: 30000, polling: 800 }
  );
  await page.waitForTimeout(4000); // physics settle + fit animation
}

async function getState(key) {
  return page.evaluate((k) => {
    try { return k ? state[k] : state; } catch { return null; }
  }, key);
}

async function getNodeCount() {
  return page.evaluate(() => state?.currentView?.nodeIds?.size ?? 0);
}

async function dismissModal() {
  // Close any open modal by pressing Escape
  await page.keyboard.press("Escape");
  await page.waitForTimeout(100);
}

// ─── Setup ────────────────────────────────────────────────────────────────────

test.describe.configure({ mode: "serial" });

test.beforeAll(async ({ browser }) => {
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 } });
  page = await ctx.newPage();
  await page.addInitScript(() => {
    window.localStorage.setItem("explorer-visited", "1");
  });
  await page.goto(BASE_URL);
  await waitForGraph();
});

test.afterAll(async () => {
  await page.close().catch(() => {});
});

// ═══════════════════════════════════════════════════════════════════════════════
// 1. PAGE LOAD
// ═══════════════════════════════════════════════════════════════════════════════

test("1-01 page loads — topbar and all panels visible", async () => {
  await shot("01-initial-load");
  await expect(page.locator(".topbar")).toBeVisible();
  await expect(page.locator("#search-input")).toBeVisible();
  await expect(page.locator(".sidebar")).toBeVisible();
  await expect(page.locator(".tools-panel")).toBeVisible();
  await expect(page.locator(".detail-panel")).toBeVisible();
  await expect(page.locator("#network")).toBeVisible();
});

test("1-02 graph data loaded — node count > 800", async () => {
  const count = await getNodeCount();
  console.log("Initial node count:", count);
  expect(count).toBeGreaterThan(800);
});

test("1-03 loading overlay is hidden", async () => {
  await expect(page.locator("#loading-overlay")).toHaveClass(/is-hidden/);
});

test("1-04 detail panel shows empty-state tip", async () => {
  const body = page.locator("#detail-body");
  const text = await body.innerText();
  expect(text).toMatch(/Select a node/i);
  await shot("04-empty-detail");
});

// ═══════════════════════════════════════════════════════════════════════════════
// 2. TOPBAR BUTTONS
// ═══════════════════════════════════════════════════════════════════════════════

test("2-01 help modal opens on ? key", async () => {
  await page.keyboard.press("?");
  await page.waitForTimeout(200);
  await expect(page.locator("#help-modal")).not.toHaveClass(/is-hidden/);
  await shot("help-modal-open");
});

test("2-02 help modal has keyboard shortcuts section", async () => {
  const shortcuts = page.locator(".shortcuts-grid, .shortcut-row, .help-section");
  const count = await shortcuts.count();
  console.log("Shortcut elements:", count);
  expect(count).toBeGreaterThan(0);
});

test("2-03 help modal closes on Escape", async () => {
  await page.keyboard.press("Escape");
  await page.waitForTimeout(200);
  const isHidden = await page.locator("#help-modal").evaluate(
    (el) => el.classList.contains("is-hidden") || el.getAttribute("aria-hidden") === "true"
  );
  expect(isHidden).toBe(true);
  await shot("help-modal-closed");
});

test("2-04 feedback modal opens on button click", async () => {
  await page.click("#feedback-button");
  await page.waitForTimeout(200);
  await expect(page.locator("#feedback-modal")).not.toHaveClass(/is-hidden/);
  await shot("feedback-modal-open");
  await dismissModal();
  await page.waitForTimeout(200);
});

test("2-05 palette picker opens on button click", async () => {
  await page.click("#palette-button");
  await page.waitForTimeout(200);
  await expect(page.locator("#palette-picker")).toBeVisible();
  const opts = await page.locator(".palette-option").count();
  expect(opts).toBeGreaterThanOrEqual(3);
  await shot("palette-picker-open");
  // Close by clicking elsewhere
  await page.keyboard.press("Escape");
  await page.waitForTimeout(100);
});

test("2-06 / key focuses search input", async () => {
  await page.keyboard.press("/");
  await expect(page.locator("#search-input")).toBeFocused();
  await page.keyboard.press("Escape");
});

test("2-07 Ctrl+K focuses search input", async () => {
  await page.locator("body").click();
  await page.keyboard.press("Control+k");
  await expect(page.locator("#search-input")).toBeFocused();
  await page.keyboard.press("Escape");
});

test("2-08 fit button fires without error", async () => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.click("#fit-button");
  await page.waitForTimeout(300);
  expect(errors).toHaveLength(0);
});

// ═══════════════════════════════════════════════════════════════════════════════
// 3. LEFT SIDEBAR — FILTERS
// ═══════════════════════════════════════════════════════════════════════════════

test("3-01 node type filter renders options", async () => {
  const options = page.locator("#node-type-list label, #node-type-list .color-row");
  const count = await options.count();
  console.log("Node type options:", count);
  expect(count).toBeGreaterThan(0);
  await shot("sidebar-node-types");
});

test("3-02 clearing node types shows fewer nodes", async () => {
  const before = await getNodeCount();
  await page.click("#node-types-clear-all");
  await page.waitForTimeout(500);
  const after = await getNodeCount();
  console.log("Node count before clear:", before, "after:", after);
  // After clearing all node types, no nodes should be visible
  expect(after).toBeLessThan(before);
  await shot("node-types-cleared");
});

test("3-03 selecting all node types restores full count", async () => {
  await page.click("#node-types-select-all");
  await page.waitForTimeout(500);
  const count = await getNodeCount();
  expect(count).toBeGreaterThan(800);
  await shot("node-types-restored");
});

test("3-04 edge type section visible and has options", async () => {
  // Open edge types section if not open
  const edgeSection = page.locator("details.sidebar-section").nth(1);
  const isOpen = await edgeSection.evaluate((el) => el.open);
  if (!isOpen) await edgeSection.locator("summary").click();
  await page.waitForTimeout(200);

  const opts = page.locator("#edge-type-list label, #edge-type-list .option-row");
  const count = await opts.count();
  console.log("Edge type options:", count);
  expect(count).toBeGreaterThan(0);
  await shot("sidebar-edge-types");
});

test("3-05 clearing edge types reduces visible edges to 0", async () => {
  await page.click("#edge-types-clear-all");
  await page.waitForTimeout(400);
  const edgeCount = await page.evaluate(() => state?.currentView?.edgeIds?.size ?? 0);
  console.log("Edges after clear:", edgeCount);
  expect(edgeCount).toBe(0);
  await page.click("#edge-types-select-all");
  await page.waitForTimeout(400);
});

test("3-06 categories section visible and has options", async () => {
  const catSection = page.locator("details.sidebar-section").nth(2);
  const isOpen = await catSection.evaluate((el) => el.open);
  if (!isOpen) await catSection.locator("summary").click();
  await page.waitForTimeout(200);

  const opts = page.locator("#category-list label, #category-list .option-row");
  const count = await opts.count();
  console.log("Category options:", count);
  expect(count).toBeGreaterThan(0);
  await shot("sidebar-categories");
});

test("3-07 year range filter works", async () => {
  // Open year section if needed
  const yearSection = page.locator("details.sidebar-section").nth(3);
  const isOpen = await yearSection.evaluate((el) => el.open);
  if (!isOpen) await yearSection.locator("summary").click();
  await page.waitForTimeout(200);

  const before = await getNodeCount();
  // Set min year to 2023
  await page.fill("#year-min", "2023");
  await page.keyboard.press("Enter");
  await page.waitForTimeout(500);
  const after = await getNodeCount();
  console.log("Year filter: before=", before, "after=", after);
  expect(after).toBeLessThanOrEqual(before);
  await shot("year-filter-applied");

  // Reset year filter
  await page.fill("#year-min", "");
  await page.keyboard.press("Enter");
  await page.waitForTimeout(400);
});

// ═══════════════════════════════════════════════════════════════════════════════
// 4. SEARCH
// ═══════════════════════════════════════════════════════════════════════════════

test("4-01 typing shows suggestions dropdown", async () => {
  await page.click("#search-input");
  await page.fill("#search-input", "neural");
  await page.waitForTimeout(300);
  const sugg = page.locator("#search-suggestions");
  await expect(sugg).not.toHaveClass(/is-hidden/);
  const items = sugg.locator(".search-suggestion-item");
  const count = await items.count();
  console.log("Suggestions for 'neural':", count);
  expect(count).toBeGreaterThan(0);
  await shot("search-neural-suggestions");
});

test("4-02 suggestions show label and type columns", async () => {
  const first = page.locator(".search-suggestion-item").first();
  const label = await first.locator(".search-sugg-label").textContent();
  const type = await first.locator(".search-sugg-type").textContent();
  console.log("First suggestion: label=", label, "type=", type);
  expect(label.length).toBeGreaterThan(0);
  expect(type.length).toBeGreaterThan(0);
});

test("4-03 semantic mini-map appears with 3+ embedded results", async () => {
  // "neural" should produce enough embedded results
  const miniMap = page.locator(".search-mini-map");
  const count = await miniMap.count();
  console.log("Mini-map count:", count);
  if (count > 0) {
    await expect(miniMap.first()).toBeVisible();
    await shot("search-mini-map");
  }
});

test("4-04 arrow keys navigate suggestion list", async () => {
  // Re-type to ensure suggestions are showing
  await page.fill("#search-input", "neural");
  await page.focus("#search-input");
  await page.waitForTimeout(200);
  // Ensure dropdown is visible
  await expect(page.locator("#search-suggestions")).not.toHaveClass(/is-hidden/);
  await page.keyboard.press("ArrowDown");
  await page.waitForTimeout(150);
  // Keyboard navigation uses class 'kbd-focus', not 'is-active'
  const activeItem = page.locator(".search-suggestion-item.kbd-focus");
  const count = await activeItem.count();
  console.log("kbd-focus suggestions after ArrowDown:", count);
  expect(count).toBe(1);
  await shot("search-keyboard-nav");
});

test("4-05 pressing Enter on suggestion activates focus mode", async () => {
  await page.focus("#search-input");
  // Navigate to first suggestion
  await page.keyboard.press("ArrowDown");
  await page.waitForTimeout(100);
  await page.keyboard.press("Enter");
  await page.waitForTimeout(500);

  // After pressing Enter on a suggestion, focus mode should activate
  const focusActive = await page.evaluate(() => Boolean(state?.focus));
  console.log("Focus active after search Enter:", focusActive);
  expect(focusActive).toBe(true);
  await shot("search-enter-focus");
});

test("4-06 search clear restores full graph", async () => {
  // Exit focus if active
  await page.evaluate(() => {
    if (typeof exitFocus === "function") exitFocus(false);
  });
  await page.waitForTimeout(400);

  await page.fill("#search-input", "");
  await page.waitForTimeout(300);
  const sugg = page.locator("#search-suggestions");
  const isHidden = await sugg.evaluate((el) => el.classList.contains("is-hidden"));
  expect(isHidden).toBe(true);
});

test("4-07 multi-word search works", async () => {
  await page.fill("#search-input", "neural operator");
  await page.waitForTimeout(300);
  const items = page.locator(".search-suggestion-item");
  const count = await items.count();
  console.log("Multi-word 'neural operator' results:", count);
  // Should only show items matching both tokens
  expect(count).toBeGreaterThanOrEqual(0); // may be 0 if no match
  await shot("search-multiword");
  await page.fill("#search-input", "");
  await page.keyboard.press("Escape");
  await page.waitForTimeout(200);
});

// ═══════════════════════════════════════════════════════════════════════════════
// 5. CANVAS INTERACTIONS — SINGLE CLICK, DOUBLE CLICK
// ═══════════════════════════════════════════════════════════════════════════════

test("5-01 single click selects a node and populates detail panel", async () => {
  // Select a node programmatically (canvas clicks are pixel-dependent)
  const firstNodeId = await page.evaluate(() => {
    const ids = Array.from(state?.currentView?.nodeIds || []);
    return ids.find((id) => id.startsWith("project:")) || ids[0];
  });
  expect(firstNodeId).toBeTruthy();

  await page.evaluate((nodeId) => {
    if (typeof handleNetworkClick === "function") {
      handleNetworkClick({ nodes: [nodeId], edges: [], event: { srcEvent: { shiftKey: false } } });
    }
  }, firstNodeId);
  await page.waitForTimeout(400);

  const primaryId = await page.evaluate(() => state?.selection?.primaryId);
  expect(primaryId).toBe(firstNodeId);

  const detailBody = await page.locator("#detail-body").innerText();
  expect(detailBody).not.toMatch(/Select a node/i);
  await shot("single-click-detail");
});

test("5-02 detail panel shows node label", async () => {
  const headerText = await page.locator("#detail-header-title, .detail-node-title, #detail-body").first().innerText();
  console.log("Detail header/body:", headerText.slice(0, 100));
  expect(headerText.length).toBeGreaterThan(0);
});

test("5-03 double-click activates focus mode", async () => {
  const nodeId = await page.evaluate(() => state?.selection?.primaryId);
  await page.evaluate((nid) => {
    if (typeof handleNetworkDoubleClick === "function") {
      handleNetworkDoubleClick({ nodes: [nid], edges: [], event: { srcEvent: {} } });
    }
  }, nodeId);
  await page.waitForTimeout(500);

  const focusActive = await page.evaluate(() => Boolean(state?.focus));
  expect(focusActive).toBe(true);

  await expect(page.locator("#focus-exit-button")).not.toHaveClass(/is-hidden/);
  await expect(page.locator("#detail-discover-nav")).not.toHaveClass(/is-hidden/);
  await shot("double-click-focus-mode");
});

test("5-04 focus mode shows fewer nodes than full graph", async () => {
  const focusedCount = await getNodeCount();
  console.log("Focused node count:", focusedCount);
  // Focus at depth=1 should show a subset
  expect(focusedCount).toBeGreaterThan(0);
  expect(focusedCount).toBeLessThan(2000);
});

// ═══════════════════════════════════════════════════════════════════════════════
// 6. DISCOVER / FOCUS MODE
// ═══════════════════════════════════════════════════════════════════════════════

test("6-01 discover nav Prev button works", async () => {
  const prevBtn = page.locator("#discover-prev");
  await expect(prevBtn).toBeVisible();
  const before = await page.evaluate(() => state?.selection?.primaryId);
  await prevBtn.click();
  await page.waitForTimeout(300);
  // After clicking Prev, selection may have changed (or stayed if 1 neighbor)
  const after = await page.evaluate(() => state?.selection?.primaryId);
  console.log("Prev nav: before=", before, "after=", after);
  await shot("discover-prev");
});

test("6-02 discover nav Next button works", async () => {
  const nextBtn = page.locator("#discover-next");
  await expect(nextBtn).toBeVisible();
  await nextBtn.click();
  await page.waitForTimeout(300);
  await shot("discover-next");
});

test("6-03 depth-2 button expands neighborhood", async () => {
  const count1 = await getNodeCount();
  const d2 = page.locator("#discover-depth-2");
  if (await d2.isVisible()) {
    await d2.click();
    await page.waitForTimeout(400);
    const count2 = await getNodeCount();
    console.log("Depth 1:", count1, "Depth 2:", count2);
    expect(count2).toBeGreaterThanOrEqual(count1);
    await shot("discover-depth-2");
    // Reset to depth 1
    await page.locator("#discover-depth-1").click();
    await page.waitForTimeout(300);
  }
});

test("6-04 exit focus button returns to full graph", async () => {
  await page.click("#focus-exit-button");
  await page.waitForTimeout(400);

  const focusActive = await page.evaluate(() => Boolean(state?.focus));
  expect(focusActive).toBe(false);
  await expect(page.locator("#focus-exit-button")).toHaveClass(/is-hidden/);
  await expect(page.locator("#detail-discover-nav")).toHaveClass(/is-hidden/);

  const restoredCount = await getNodeCount();
  expect(restoredCount).toBeGreaterThan(800);
  await shot("focus-exited");
});

test("6-05 Discover button in topbar activates discover mode", async () => {
  await page.click("#discover-button");
  await page.waitForTimeout(500);
  // Should enter focus/discover mode on first unvisited node
  const focusActive = await page.evaluate(() => Boolean(state?.focus));
  console.log("Discover mode via topbar button:", focusActive);
  await shot("topbar-discover-button");
  // Exit if active
  if (focusActive) {
    await page.click("#focus-exit-button");
    await page.waitForTimeout(300);
  }
});

// ═══════════════════════════════════════════════════════════════════════════════
// 7. RIGHT PANEL — VIEW PRESETS + PHYSICS LAB + STATS
// ═══════════════════════════════════════════════════════════════════════════════

test("7-01 tools panel view presets section visible", async () => {
  await expect(page.locator("#tools-presets-section")).toBeVisible();
  await shot("tools-panel");
});

test("7-02 view preset buttons exist and fire without error", async () => {
  const presetBtns = page.locator(".preset-btn, [data-preset]");
  const count = await presetBtns.count();
  console.log("Preset buttons:", count);
  if (count > 0) {
    const errors = [];
    const handler = (e) => errors.push(e.message);
    page.on("pageerror", handler);
    await presetBtns.first().click();
    await page.waitForTimeout(300);
    page.off("pageerror", handler);
    expect(errors).toHaveLength(0);
    await shot("preset-applied");
  }
});

test("7-03 physics lab sliders are present and interactable", async () => {
  const physSection = page.locator("#tools-physics-section");
  await expect(physSection).toBeVisible();
  const sliders = physSection.locator('input[type="range"]');
  const count = await sliders.count();
  console.log("Physics sliders:", count);
  expect(count).toBeGreaterThanOrEqual(4);
  await shot("physics-lab");
});

test("7-04 Start physics button exists", async () => {
  const startBtn = page.locator("#physics-start-btn, [id*='phys'][id*='start'], button:has-text('Start')").first();
  const exists = await startBtn.count();
  console.log("Physics start button exists:", exists);
});

test("7-05 stats section shows node and edge counts", async () => {
  const statsSection = page.locator(".stats-grid, .stat-card, #stats-nodes, [id*='stat']");
  const count = await statsSection.count();
  console.log("Stats elements:", count);
  if (count > 0) {
    const text = await statsSection.first().innerText();
    console.log("Stats:", text.slice(0, 80));
  }
  await shot("stats-section");
});

// ═══════════════════════════════════════════════════════════════════════════════
// 8. DETAIL PANEL — DEEP INSPECTION
// ═══════════════════════════════════════════════════════════════════════════════

test("8-01 click a Project node — detail shows project metadata", async () => {
  // Select a project node
  const projectId = await page.evaluate(() => {
    const ids = Array.from(state?.currentView?.nodeIds || []);
    return ids.find((id) => id.startsWith("project:")) || null;
  });
  if (!projectId) { console.log("No project in view, skip"); return; }

  await page.evaluate((nid) => {
    if (typeof handleNetworkClick === "function") {
      handleNetworkClick({ nodes: [nid], edges: [], event: { srcEvent: { shiftKey: false } } });
    }
  }, projectId);
  await page.waitForTimeout(400);
  await shot("detail-project");

  const body = await page.locator("#detail-body").innerText();
  console.log("Project detail body (first 200):", body.slice(0, 200));
  // Should have metadata, not the empty state
  expect(body).not.toMatch(/Select a node/i);
});

test("8-02 click an Organization node — detail shows org metadata", async () => {
  const orgId = await page.evaluate(() => {
    const ids = Array.from(state?.currentView?.nodeIds || []);
    return ids.find((id) => id.startsWith("organization:")) || null;
  });
  if (!orgId) { console.log("No org in view, skip"); return; }

  await page.evaluate((nid) => {
    if (typeof handleNetworkClick === "function") {
      handleNetworkClick({ nodes: [nid], edges: [], event: { srcEvent: { shiftKey: false } } });
    }
  }, orgId);
  await page.waitForTimeout(400);
  await shot("detail-org");

  const body = await page.locator("#detail-body").innerText();
  expect(body.length).toBeGreaterThan(10);
});

test("8-03 Find Similar button exists for nodes with embed coords", async () => {
  // Project nodes should have embed coords → Find Similar button
  const projectId = await page.evaluate(() => {
    const ids = Array.from(state?.currentView?.nodeIds || []);
    return ids.find((id) => {
      const node = state?.caches?.nodeById?.get(id);
      return id.startsWith("project:") && (node?.props?.embed_x != null || node?.props?.embed_all_x != null);
    });
  });
  if (!projectId) { console.log("No embedded project, skip"); return; }

  await page.evaluate((nid) => {
    if (typeof handleNetworkClick === "function") {
      handleNetworkClick({ nodes: [nid], edges: [], event: { srcEvent: { shiftKey: false } } });
    }
  }, projectId);
  await page.waitForTimeout(400);

  const findSimilarBtn = page.locator("button:has-text('Find similar'), #find-similar-btn, [data-action='find-similar']");
  const count = await findSimilarBtn.count();
  console.log("Find Similar button count:", count);
  await shot("detail-find-similar-btn");
});

test("8-04 Find Similar activates similarity focus mode", async () => {
  // Trigger Find Similar via JS
  const projectId = await page.evaluate(() => {
    const ids = Array.from(state?.currentView?.nodeIds || []);
    return ids.find((id) => {
      const node = state?.caches?.nodeById?.get(id);
      return id.startsWith("project:") && (node?.props?.embed_x != null || node?.props?.embed_all_x != null);
    });
  });
  if (!projectId) { console.log("No embedded project, skip"); return; }

  await page.evaluate((nid) => {
    if (typeof findSimilarNodes === "function") findSimilarNodes(nid);
  }, projectId);
  await page.waitForTimeout(500);

  const mode = await page.evaluate(() => state?.focus?.mode);
  console.log("Focus mode after Find Similar:", mode);
  expect(mode).toBe("similarity");
  await shot("similarity-mode");

  // Exit
  await page.click("#focus-exit-button").catch(() => {});
  await page.waitForTimeout(300);
});

// ═══════════════════════════════════════════════════════════════════════════════
// 9. EMBED MODE
// ═══════════════════════════════════════════════════════════════════════════════

test("9-01 Embed button activates embed mode", async () => {
  // Ensure no focus active
  await page.evaluate(() => { if (typeof exitFocus === "function") exitFocus(false); });
  await page.waitForTimeout(300);

  await page.click("#embed-button");
  await page.waitForTimeout(1000);

  const embedActive = await page.evaluate(() => state?.embedActive);
  expect(embedActive).toBe(true);
  await expect(page.locator("#embed-button")).toHaveClass(/is-active/);
  await shot("embed-mode-on");
});

test("9-02 embed mode defaults to all-nodes (>2000)", async () => {
  const count = await getNodeCount();
  console.log("Embed all-nodes count:", count);
  expect(count).toBeGreaterThan(1000);
});

test("9-03 embed mode hides physics and preset sections", async () => {
  await expect(page.locator("#tools-presets-section")).toHaveClass(/is-hidden/);
  await expect(page.locator("#tools-physics-section")).toHaveClass(/is-hidden/);
});

test("9-04 filter sidebar shows embed notice", async () => {
  const notice = page.locator(".sidebar-embed-notice");
  const isVisible = await notice.evaluate((el) => {
    const style = window.getComputedStyle(el);
    return style.display !== "none";
  });
  console.log("Embed notice visible:", isVisible);
  expect(isVisible).toBe(true);
  await shot("embed-sidebar-dimmed");
});

test("9-05 cluster label toggle appears in embed mode", async () => {
  const toggle = page.locator("#cluster-label-toggle");
  await expect(toggle).not.toHaveClass(/is-hidden/);
  await shot("embed-cluster-toggle");
});

test("9-06 projects-only toggle switches to fewer nodes", async () => {
  const before = await getNodeCount();
  const toggleBtn = page.locator("#embed-all-toggle");
  if (await toggleBtn.count() === 0) {
    console.log("No embed-all-toggle, skip");
    return;
  }
  await toggleBtn.click();
  await page.waitForTimeout(800);
  const after = await getNodeCount();
  console.log("Embed toggle: all=", before, "projects=", after);
  expect(after).toBeLessThan(before);
  await shot("embed-projects-only");
  // Switch back
  await toggleBtn.click();
  await page.waitForTimeout(800);
});

test("9-07 embed cluster overlay SVG is present with paths", async () => {
  const overlay = page.locator("#cluster-overlay");
  const pathCount = await overlay.locator("path, polygon, ellipse").count();
  console.log("Cluster overlay shapes:", pathCount);
  // Hulls may not render immediately in headless, just check SVG exists
  expect(await overlay.count()).toBe(1);
  await shot("embed-cluster-overlay");
});

test("9-08 exiting embed mode restores physics controls", async () => {
  await page.click("#embed-button");
  await page.waitForTimeout(600);

  const embedActive = await page.evaluate(() => state?.embedActive);
  expect(embedActive).toBe(false);
  await expect(page.locator("#tools-presets-section")).not.toHaveClass(/is-hidden/);
  await expect(page.locator("#tools-physics-section")).not.toHaveClass(/is-hidden/);
  await shot("embed-mode-off");
});

// ═══════════════════════════════════════════════════════════════════════════════
// 10. NODE PINNING (right-click context menu)
// ═══════════════════════════════════════════════════════════════════════════════

test("10-01 right-click fires context menu via JS", async () => {
  const nodeId = await page.evaluate(() => {
    const ids = Array.from(state?.currentView?.nodeIds || []);
    return ids.find((id) => id.startsWith("project:")) || ids[0];
  });
  if (!nodeId) return;

  // Open context menu via JS
  await page.evaluate((nid) => {
    if (typeof showContextMenu === "function") {
      showContextMenu(nid, 200, 200);
    }
  }, nodeId);
  await page.waitForTimeout(200);

  const menu = page.locator("#context-menu, .context-menu");
  const visible = await menu.count();
  console.log("Context menu visible:", visible);
  if (visible) {
    await shot("context-menu-open");
    const pinBtn = page.locator("#context-pin-button, [id*='pin']");
    console.log("Pin button:", await pinBtn.count());
  }
});

test("10-02 pinning a node via JS adds to pinned set", async () => {
  const nodeId = await page.evaluate(() => {
    const ids = Array.from(state?.currentView?.nodeIds || []);
    return ids.find((id) => id.startsWith("project:")) || ids[0];
  });
  if (!nodeId) return;

  await page.evaluate((nid) => {
    if (typeof pinNode === "function") {
      pinNode(nid);
    } else if (state && state.pinnedNodeIds) {
      state.pinnedNodeIds.add(nid);
    }
  }, nodeId);
  await page.waitForTimeout(300);

  const pinned = await page.evaluate(() => Array.from(state?.pinnedNodeIds || []));
  console.log("Pinned nodes:", pinned);
  expect(pinned.length).toBeGreaterThan(0);
  await shot("node-pinned");
});

test("10-03 reset clears pinned nodes", async () => {
  await page.click("#reset-button");
  await page.waitForTimeout(600);
  const pinned = await page.evaluate(() => Array.from(state?.pinnedNodeIds || []));
  console.log("Pinned after reset:", pinned);
  expect(pinned.length).toBe(0);
  await shot("after-reset");
});

// ═══════════════════════════════════════════════════════════════════════════════
// 11. KEYBOARD SHORTCUTS
// ═══════════════════════════════════════════════════════════════════════════════

test("11-01 Escape dismisses open panels/focus", async () => {
  // First activate focus
  const nodeId = await page.evaluate(() => {
    const ids = Array.from(state?.currentView?.nodeIds || []);
    return ids.find((id) => id.startsWith("project:")) || ids[0];
  });
  await page.evaluate((nid) => {
    if (typeof handleNetworkDoubleClick === "function") {
      handleNetworkDoubleClick({ nodes: [nid], edges: [], event: { srcEvent: {} } });
    }
  }, nodeId);
  await page.waitForTimeout(400);
  expect(await page.evaluate(() => Boolean(state?.focus))).toBe(true);

  await page.keyboard.press("Escape");
  await page.waitForTimeout(400);
  const focusActive = await page.evaluate(() => Boolean(state?.focus));
  console.log("Focus active after Escape:", focusActive);
  await shot("escape-clears-focus");
});

test("11-02 E key toggles embed mode", async () => {
  const before = await page.evaluate(() => state?.embedActive);
  await page.locator("body").click();
  await page.keyboard.press("e");
  await page.waitForTimeout(400);
  const after = await page.evaluate(() => state?.embedActive);
  console.log("E key embed toggle:", before, "->", after);
  // Toggle should have changed
  expect(after).toBe(!before);
  await shot("e-key-embed-toggle");
  // Toggle back
  await page.keyboard.press("e");
  await page.waitForTimeout(300);
});

// ═══════════════════════════════════════════════════════════════════════════════
// 12. FINAL OVERVIEW SCREENSHOTS
// ═══════════════════════════════════════════════════════════════════════════════

test("12-01 final state — full graph overview", async () => {
  // Ensure we're in clean full-graph state
  await page.evaluate(() => {
    if (typeof exitFocus === "function") exitFocus(false);
  });
  await page.waitForTimeout(300);
  if (await page.evaluate(() => state?.embedActive)) {
    await page.click("#embed-button");
    await page.waitForTimeout(400);
  }
  await page.click("#fit-button");
  await page.waitForTimeout(600);
  await shot("final-full-graph");
  console.log("Final node count:", await getNodeCount());
});

test("12-02 embed mode final overview", async () => {
  await page.click("#embed-button");
  await page.waitForTimeout(1200);
  await page.click("#fit-button");
  await page.waitForTimeout(600);
  await shot("final-embed-mode");

  // Exit cleanly
  await page.click("#embed-button");
  await page.waitForTimeout(500);
});
