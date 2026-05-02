/**
 * Visual / integration tests using the real server + real data.
 * Server must be running on port 8770 before running these tests:
 *   python -m http.server 8770 (from the project root)
 *
 * Run: npx playwright test tests/visual.spec.js
 */

const { test, expect } = require("@playwright/test");
const fs = require("fs");
const path = require("path");

const BASE_URL = "http://localhost:8770";

// NOTE: `state` in explorer.html is a top-level `const`, not a `var`,
// so it is NOT on window. Access it directly in page.evaluate() as `state`.

async function waitForGraphReady(page) {
  // Wait for loading overlay to get is-hidden (DOM attached, just display:none)
  await page.waitForSelector("#loading-overlay.is-hidden", { state: "attached", timeout: 30000 });
  // Wait for state + currentView to be populated (data loaded)
  await page.waitForFunction(
    () => {
      try {
        // eslint-disable-next-line no-undef
        return typeof state !== "undefined" && state.currentView?.nodeIds?.size > 800;
      } catch (e) {
        return false;
      }
    },
    { timeout: 30000, polling: 1000 }
  );
  // Wait for physics timer (3500ms) + fit animation (600ms) + buffer
  await page.waitForTimeout(6000);
}

test.describe("visual – real graph", () => {
  // Each test gets 60s; beforeAll gets its own 120s slice via test.slow()
  test.setTimeout(60000);

  let page;
  let metrics;

  test.beforeAll(async ({ browser }) => {
    test.setTimeout(120000);
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    page = await ctx.newPage();

    await page.addInitScript(() => {
      // Skip first-visit help modal
      localStorage.setItem("explorer-visited", "1");
    });

    await page.goto(`${BASE_URL}/explorer.html`, { timeout: 30000 });
    await waitForGraphReady(page);

    // Capture layout metrics using direct `state` reference
    metrics = await page.evaluate(() => {
      try {
        const network = state?.network; // eslint-disable-line no-undef
        const ids = Array.from(state?.currentView?.nodeIds ?? []); // eslint-disable-line no-undef
        if (!network || ids.length < 100) {
          return { error: "no network data", idCount: ids.length };
        }
        const positions = network.getPositions(ids);
        const xs = Object.values(positions).map((p) => p.x);
        const ys = Object.values(positions).map((p) => p.y);
        const xRange = Math.max(...xs) - Math.min(...xs);
        const yRange = Math.max(...ys) - Math.min(...ys);
        return {
          visibleNodes: ids.length,
          zoomScale: Math.round(network.getScale() * 1000) / 1000,
          xRange: Math.round(xRange),
          yRange: Math.round(yRange),
          aspectRatio: Math.round((xRange / yRange) * 100) / 100,
          embedActive: state.embedActive, // eslint-disable-line no-undef
          forceEnabled: state.forceEnabled, // eslint-disable-line no-undef
          nodeTypeCount: state.filters?.nodeTypes?.size, // eslint-disable-line no-undef
          venueShape: NODE_METRICS?.Venue?.shape ?? "unknown", // eslint-disable-line no-undef
        };
      } catch (e) {
        return { error: String(e) };
      }
    });

    console.log("Layout metrics:", JSON.stringify(metrics, null, 2));

    // Save screenshot
    await page.evaluate(() =>
      document.querySelectorAll(".modal-backdrop").forEach((m) => m.classList.add("is-hidden"))
    );
    const dir = path.join(__dirname, "screenshots");
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    await page.screenshot({ path: path.join(dir, "default-load.png") });
    console.log("Screenshot: tests/screenshots/default-load.png");
  });

  test.afterAll(async () => {
    await page?.context().close();
  });

  test("state is populated: 10 node types, force mode, not embed", () => {
    expect(metrics?.error).toBeUndefined();
    expect(metrics?.nodeTypeCount).toBe(10);
    expect(metrics?.embedActive).toBe(false);
    expect(metrics?.forceEnabled).toBe(true);
    expect(metrics?.visibleNodes).toBeGreaterThan(2000);
  });

  test("layout is organic: xRange > 500, yRange > 500, aspect ratio 0.4–2.5", () => {
    expect(metrics?.error).toBeUndefined();
    console.log(`  xRange=${metrics?.xRange}, yRange=${metrics?.yRange}, aspect=${metrics?.aspectRatio}`);
    expect(metrics?.xRange).toBeGreaterThan(500);
    expect(metrics?.yRange).toBeGreaterThan(500);
    expect(metrics?.aspectRatio).toBeGreaterThan(0.4);
    expect(metrics?.aspectRatio).toBeLessThan(2.5);
  });

  test("Venue shape is dot (not database – disappears on hover in vis-network)", () => {
    expect(metrics?.venueShape).toBe("dot");
  });

  test("help modal footer has exactly one button (Got it)", async () => {
    await page.click("#help-button");
    await expect(page.locator("#help-modal")).not.toHaveClass(/is-hidden/);
    const btns = page.locator("#help-modal .modal-actions button");
    await expect(btns).toHaveCount(1);
    await expect(btns.first()).toHaveText("Got it");
    await page.keyboard.press("Escape");
  });

  test("Home button exits embed mode", async () => {
    await page.click("#embed-button");
    await expect(page.locator("#embed-button")).toHaveClass(/is-active/);
    await page.click("#home-button");
    await page.waitForTimeout(600);
    const embedActive = await page.evaluate(() => state.embedActive); // eslint-disable-line no-undef
    expect(embedActive).toBe(false);
  });
});
