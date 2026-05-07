/**
 * Professionalism/UI audit screenshot capture
 * Run: node scripts/professionalism-screenshots.js
 * Requires: local HTTP server on port 8770 (python -m http.server 8770)
 * Outputs to: tests/screenshots/professionalism/
 */
const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");

const BASE = "http://localhost:8770";
const OUT = path.join(__dirname, "../tests/screenshots/professionalism");
fs.mkdirSync(OUT, { recursive: true });

const DESKTOP = { width: 1440, height: 900 };
const MOBILE  = { width: 390,  height: 844 };

async function shot(page, name) {
  const p = path.join(OUT, name + ".png");
  await page.screenshot({ path: p, fullPage: false });
  console.log(`  ✓ ${name}.png`);
  return p;
}

async function waitForGraph(page) {
  await page.waitForFunction(
    () => { try { return typeof state !== "undefined" && state.currentView?.nodeIds?.size > 800; } catch { return false; } },
    { timeout: 45000, polling: 800 }
  );
  await page.waitForTimeout(4000);
}

async function waitForBrowse(page) {
  await page.waitForFunction(
    () => document.querySelectorAll(".project-card,.project-row").length > 5,
    { timeout: 30000 }
  );
  await page.waitForTimeout(400);
}

(async () => {
  const browser = await chromium.launch({ headless: true });

  // ═══════════════════════════════════════════
  // EXPLORER — DESKTOP
  // ═══════════════════════════════════════════
  console.log("\n── Explorer desktop ──");
  {
    const ctx = await browser.newContext({ viewport: DESKTOP });
    const page = await ctx.newPage();
    page.on("pageerror", () => {});
    await page.addInitScript(() => window.localStorage.setItem("explorer-visited", "1"));
    await page.goto(`${BASE}/explorer.html`);
    await waitForGraph(page);

    await shot(page, "exp-01-default");

    // Open detail panel via single click on a project node
    await page.evaluate(() => {
      const id = [...(state?.caches?.nodeById?.keys() || [])].find(k => state.caches.nodeById.get(k)?.type === "Project");
      if (id && state.network) state.network.selectNodes([id]);
      if (id && typeof handleNetworkClick === "function") handleNetworkClick({ nodes: [id], edges: [] });
    });
    await page.waitForTimeout(600);
    await shot(page, "exp-02-detail-panel");

    // Submit modal
    const fab = page.locator("#submit-fab");
    if (await fab.count() > 0) {
      await fab.click();
      await page.waitForTimeout(300);
      await shot(page, "exp-03-submit-modal");
      await page.keyboard.press("Escape");
      await page.waitForTimeout(200);
    }

    // Search with suggestions
    await page.fill("#search-input", "cad");
    await page.waitForTimeout(400);
    await shot(page, "exp-04-search-suggestions");
    await page.keyboard.press("Escape");
    await page.waitForTimeout(200);

    // Focus mode via double-click
    await page.evaluate(() => {
      const id = [...(state?.caches?.nodeById?.keys() || [])].find(k => state.caches.nodeById.get(k)?.type === "Project");
      if (id && typeof handleNetworkDoubleClick === "function") handleNetworkDoubleClick({ nodes: [id], edges: [], event: { srcEvent: {} } });
    });
    await page.waitForTimeout(800);
    await shot(page, "exp-05-focus-mode");

    // Embed mode — open mode menu then click Embeddings
    await page.keyboard.press("Escape");
    await page.waitForTimeout(400);
    const modeMenuBtn = page.locator("#mode-menu-button, button[aria-label*='mode'], button:has-text('Mode')").first();
    if (await modeMenuBtn.count() > 0) {
      await modeMenuBtn.click();
      await page.waitForTimeout(200);
    }
    const embedModeItem = page.locator("[data-mode='embed']").first();
    if (await embedModeItem.count() > 0) {
      await embedModeItem.click();
      await page.waitForTimeout(3000);
      await shot(page, "exp-06-embed-mode");
    } else {
      await shot(page, "exp-06-embed-mode"); // fallback — still capture current state
    }

    await ctx.close();
  }

  // ═══════════════════════════════════════════
  // EXPLORER — MOBILE
  // ═══════════════════════════════════════════
  console.log("\n── Explorer mobile ──");
  {
    const ctx = await browser.newContext({ viewport: MOBILE });
    const page = await ctx.newPage();
    page.on("pageerror", () => {});
    await page.addInitScript(() => window.localStorage.setItem("explorer-visited", "1"));
    await page.goto(`${BASE}/explorer.html`);
    await waitForGraph(page);

    await shot(page, "exp-07-mobile-default");

    const fab = page.locator("#submit-fab");
    if (await fab.count() > 0) {
      await fab.click();
      await page.waitForTimeout(300);
      await shot(page, "exp-08-mobile-submit-modal");
      await page.keyboard.press("Escape");
      await page.waitForTimeout(200);
    }

    await ctx.close();
  }

  // ═══════════════════════════════════════════
  // BROWSE — DESKTOP
  // ═══════════════════════════════════════════
  console.log("\n── Browse desktop ──");
  {
    const ctx = await browser.newContext({ viewport: DESKTOP });
    const page = await ctx.newPage();
    page.on("pageerror", () => {});
    await page.goto(`${BASE}/browse.html`);
    await waitForBrowse(page);

    await shot(page, "brw-01-default");

    // Table view
    const tableBtn = page.locator("#btn-table");
    if (await tableBtn.count() > 0) {
      await tableBtn.click();
      await page.waitForTimeout(300);
      await shot(page, "brw-02-table-view");
      // Back to card view
      const cardBtn = page.locator("#btn-cards, button[onclick*=\"setView('cards')\"]").first();
      if (await cardBtn.count() > 0) {
        await cardBtn.click();
        await page.waitForTimeout(300);
      }
    }

    // Click a card to open detail panel
    const card = page.locator(".project-card").first();
    if (await card.count() > 0) {
      await card.click();
      await page.waitForTimeout(400);
      await shot(page, "brw-03-detail-panel-open");

      // FAB position with detail open
      await shot(page, "brw-04-fab-with-detail");
    }

    // Submit modal
    const fab = page.locator("#submit-fab");
    if (await fab.count() > 0) {
      await fab.click();
      await page.waitForTimeout(300);
      await shot(page, "brw-05-submit-modal");

      // Scroll down inside modal to see drop zone
      const modal = page.locator("#submit-modal .modal-body");
      if (await modal.count() > 0) {
        await modal.evaluate(el => el.scrollTop = el.scrollHeight);
        await page.waitForTimeout(200);
        await shot(page, "brw-06-submit-modal-dropzone");
      }
      await page.keyboard.press("Escape");
      await page.waitForTimeout(200);
    }

    // Filter sidebar: search
    const searchEl = page.locator("#search-input, input[placeholder*='Search']").first();
    if (await searchEl.count() > 0) {
      await searchEl.fill("diffusion");
      await page.waitForTimeout(600);
      await shot(page, "brw-07-search-filter");
      await searchEl.fill("");
      await page.waitForTimeout(400);
    }

    // Collections sidebar (if visible)
    const collBtn = page.locator("#collections-toggle, button:has-text('Collections')").first();
    if (await collBtn.count() > 0 && await collBtn.isVisible()) {
      await collBtn.click();
      await page.waitForTimeout(300);
      await shot(page, "brw-08-collections-sidebar");
    }

    await ctx.close();
  }

  // ═══════════════════════════════════════════
  // BROWSE — MOBILE
  // ═══════════════════════════════════════════
  console.log("\n── Browse mobile ──");
  {
    const ctx = await browser.newContext({ viewport: MOBILE });
    const page = await ctx.newPage();
    page.on("pageerror", () => {});
    await page.goto(`${BASE}/browse.html`);
    await waitForBrowse(page);

    await shot(page, "brw-09-mobile-default");

    // Click a card
    const card = page.locator(".project-card").first();
    if (await card.count() > 0) {
      await card.click();
      await page.waitForTimeout(400);
      await shot(page, "brw-10-mobile-detail-panel");
    }

    // Close detail panel first (if open) so FAB is in viewport
    const closeBtn = page.locator(".detail-close, button:has-text('Close')").first();
    if (await closeBtn.isVisible().catch(() => false)) {
      await closeBtn.click();
      await page.waitForTimeout(300);
    }
    // Submit modal on mobile
    const fab = page.locator("#submit-fab");
    if (await fab.count() > 0) {
      await fab.click({ force: true });
      await page.waitForTimeout(300);
      await shot(page, "brw-11-mobile-submit-modal");
      await page.keyboard.press("Escape");
      await page.waitForTimeout(200);
    }

    await ctx.close();
  }

  await browser.close();
  const files = fs.readdirSync(OUT);
  console.log(`\nDone — ${files.length} screenshots in tests/screenshots/professionalism/`);
  console.log(files.map(f => "  " + f).join("\n"));
})();
