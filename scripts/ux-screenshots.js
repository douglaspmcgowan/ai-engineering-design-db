/**
 * UX/UI Research Screenshots
 * Run: node scripts/ux-screenshots.js
 * Captures key app states to test/screenshots/ux/
 */
const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");

const BASE_URL = "http://localhost:8770/explorer.html";
const OUT_DIR = path.join(__dirname, "../tests/screenshots/ux");
fs.mkdirSync(OUT_DIR, { recursive: true });

async function shot(page, name) {
  await page.screenshot({ path: path.join(OUT_DIR, name + ".png"), fullPage: false });
  console.log(`  ✓ ${name}.png`);
}

async function waitForGraph(page) {
  // Wait for state to be populated (loading overlay may hide differently in headed vs headless)
  await page.waitForFunction(
    () => { try { return typeof state !== "undefined" && state.currentView?.nodeIds?.size > 800; } catch { return false; } },
    { timeout: 45000, polling: 800 }
  );
  await page.waitForTimeout(4500); // let physics settle
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();

  // suppress errors
  page.on("pageerror", () => {});

  // Set localStorage before page load to skip intro
  await page.addInitScript(() => {
    window.localStorage.setItem("explorer-visited", "1");
  });

  console.log("Loading app...");
  await page.goto(BASE_URL);
  await waitForGraph(page);

  // 1. Default view — full graph
  await shot(page, "01-default-view");

  // 2. Left sidebar open (filters)
  await shot(page, "02-sidebar-visible");

  // 3. Search — type a query
  await page.click("#search-input");
  await page.fill("#search-input", "cad");
  await page.waitForTimeout(300);
  await shot(page, "03-search-suggestions");

  // 4. Click a search result to enter focus mode
  const firstSugg = page.locator(".search-suggestion-item").first();
  if (await firstSugg.count() > 0) {
    await firstSugg.click();
    await page.waitForTimeout(800);
    await shot(page, "04-focus-mode-from-search");
  }

  // 5. Clear search, click canvas to deselect
  await page.keyboard.press("Escape");
  await page.click("#canvas-surface", { position: { x: 720, y: 450 }, force: true });
  await page.waitForTimeout(400);

  // 6. Help modal
  await page.keyboard.press("?");
  await page.waitForTimeout(200);
  await shot(page, "05-help-modal");
  await page.keyboard.press("Escape");
  await page.waitForTimeout(200);

  // 7. Palette picker
  await page.click("#palette-button");
  await page.waitForTimeout(200);
  await shot(page, "06-palette-picker");
  await page.keyboard.press("Escape");
  await page.waitForTimeout(200);

  // 8. Node type filters sidebar (click Summary section if collapsed)
  const typesSection = page.locator("details[data-accordion]").first();
  if (!(await typesSection.evaluate(el => el.hasAttribute("open")))) {
    await typesSection.locator("summary").click();
  }
  await page.waitForTimeout(200);
  await shot(page, "07-node-type-filters");

  // 9. Embed mode (UMAP layout)
  await page.click("#embed-button");
  await page.waitForTimeout(3000);
  await shot(page, "08-embed-mode");

  // 10. Embed all-nodes mode
  const allNodesBtn = page.locator("#embed-all-nodes-button, #embed-scope-button, button:has-text('All nodes'), button:has-text('Projects only')").first();
  if (await allNodesBtn.count() > 0) {
    await allNodesBtn.click();
    await page.waitForTimeout(3000);
    await shot(page, "09-embed-all-nodes");
    await allNodesBtn.click(); // toggle back
    await page.waitForTimeout(1000);
  }

  // 11. Back to force mode
  await page.click("#embed-button"); // toggle off embed
  await page.waitForTimeout(1000);
  await shot(page, "10-force-mode-restored");

  // 12. Right-click a node for context menu — simulate
  await page.evaluate(() => {
    const firstNodeId = Array.from(state?.caches?.nodeById?.keys() || [])[0];
    if (firstNodeId && state?.network) {
      const pos = state.network.canvasToDOM(state.network.getPositions([firstNodeId])[firstNodeId] || { x: 0, y: 0 });
      state.network.selectNodes([firstNodeId]);
    }
  });
  await page.waitForTimeout(200);

  // 13. Double-click to enter focus mode (via JS)
  const firstProjectId = await page.evaluate(() => {
    for (const [id, node] of (state?.caches?.nodeById || [])) {
      if (node?.type === "Project") return id;
    }
    return null;
  });
  if (firstProjectId) {
    await page.evaluate((nodeId) => {
      if (typeof handleNetworkDoubleClick === "function") {
        handleNetworkDoubleClick({ nodes: [nodeId], edges: [], event: { srcEvent: {} } });
      }
    }, firstProjectId);
    await page.waitForTimeout(600);
    await shot(page, "11-focus-mode-project");

    // 14. Detail panel with neighbor count
    await shot(page, "12-detail-panel-neighbor-count");

    // 15. Discover nav with neighbor count
    const discoverNav = page.locator("#detail-discover-nav");
    if (await discoverNav.isVisible()) {
      await shot(page, "13-discover-nav-with-count");
    }
  }

  // 16. Tools panel — physics lab
  const physicsSection = page.locator("#tools-physics-section");
  if (await physicsSection.count() > 0) {
    const physicsSummary = physicsSection.locator("summary").first();
    if (physicsSummary && !(await physicsSection.evaluate(el => el.hasAttribute("open")))) {
      await physicsSummary.click();
      await page.waitForTimeout(200);
    }
    await shot(page, "14-physics-lab");
  }

  // 17. Stats panel
  const statsSection = page.locator("#tools-stats-section, details:has-text('Stats')").first();
  if (await statsSection.count() > 0) {
    await shot(page, "15-stats-panel");
  }

  // 18. Year range filter — open the date filter section first
  try {
    // open a details section that contains year inputs if collapsed
    const yearInput = page.locator("input#year-min").first();
    const yearVisible = await yearInput.isVisible().catch(() => false);
    if (!yearVisible) {
      // find the section containing year and open it
      const yearSection = page.locator("details:has(input#year-min)");
      if (await yearSection.count() > 0 && !(await yearSection.evaluate(el => el.hasAttribute("open")))) {
        await yearSection.locator("summary").click();
        await page.waitForTimeout(200);
      }
    }
    if (await yearInput.isVisible().catch(() => false)) {
      await yearInput.fill("2022");
      await page.waitForTimeout(800);
      await shot(page, "16-year-filter-applied");
      await yearInput.fill("2020");
      await page.waitForTimeout(400);
    } else {
      console.log("  ⚠ year input not visible, skipping");
    }
  } catch (e) {
    console.log("  ⚠ year filter skip:", e.message.split("\n")[0]);
  }

  // 19. Feedback modal
  await page.click("#feedback-button");
  await page.waitForTimeout(200);
  await shot(page, "17-feedback-modal");
  await page.keyboard.press("Escape");

  await browser.close();
  console.log(`\nDone — ${fs.readdirSync(OUT_DIR).length} screenshots in tests/screenshots/ux/`);
})();
