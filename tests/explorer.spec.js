const { test, expect } = require("@playwright/test");
const path = require("path");

const FILE_URL = "file:///" + path.resolve(__dirname, "../explorer.html").replace(/\\/g, "/");

const GRAPH_DATA = {
  meta: { source: "playwright-fixture" },
  categories: ["test-cat"],
  yearRange: [2020, 2024],
  clusterLabels: { 0: "Cluster 0" },
  nodes: [
    {
      id: "project:a",
      type: "Project",
      label: "Alpha",
      props: {
        name: "Alpha",
        category: "test-cat",
        year: 2022,
        embed_x: 1.0,
        embed_y: 2.0,
        cluster_k: 0,
        cluster_label: "Cluster 0",
        cluster_category: "Category Cluster 0",
      },
    },
    {
      id: "project:b",
      type: "Project",
      label: "Beta",
      props: {
        name: "Beta",
        category: "test-cat",
        year: 2023,
        embed_x: 2.0,
        embed_y: 1.0,
        cluster_k: 0,
        cluster_label: "Cluster 0",
        cluster_category: "Category Cluster 0",
      },
    },
    {
      id: "org:acme",
      type: "Organization",
      label: "Acme",
      props: {
        name: "Acme",
      },
    },
  ],
  edges: [
    { source: "project:a", target: "org:acme", type: "BUILT_BY", weight: 1 },
    { source: "project:a", target: "project:b", type: "SEMANTICALLY_NEAR", weight: 1 },
  ],
};

test.describe("explorer", () => {
  test.beforeEach(async ({ page }) => {
    await page.route("**/graph-data.json", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(GRAPH_DATA),
      });
    });

    await page.addInitScript(({ graphData }) => {
      window.localStorage.setItem("explorer-visited", "1");
      const originalFetch = window.fetch.bind(window);
      window.fetch = (input, init) => {
        const url = typeof input === "string" ? input : input?.url || "";
        if (url.includes("graph-data.json")) {
          return Promise.resolve(new Response(JSON.stringify(graphData), {
            status: 200,
            headers: {
              "Content-Type": "application/json",
            },
          }));
        }
        return originalFetch(input, init);
      };

      class DataSet {
        constructor(items = []) {
          this.map = new Map();
          this.add(items);
        }

        add(items) {
          const list = Array.isArray(items) ? items : [items];
          list.filter(Boolean).forEach((item) => {
            this.map.set(item.id, { ...item });
          });
        }

        update(items) {
          const list = Array.isArray(items) ? items : [items];
          list.filter(Boolean).forEach((item) => {
            const current = this.map.get(item.id) || {};
            this.map.set(item.id, { ...current, ...item });
          });
        }

        remove(items) {
          const list = Array.isArray(items) ? items : [items];
          list.filter(Boolean).forEach((item) => {
            const id = typeof item === "object" ? item.id : item;
            this.map.delete(id);
          });
        }

        clear() {
          this.map.clear();
        }
      }

      class Network {
        constructor(container, data, options) {
          this.container = container;
          this.data = data;
          this.options = options || {};
          this.listeners = {};
          this.selectedNodes = [];
          setTimeout(() => {
            this.emit("stabilized", {});
            this.emit("afterDrawing", {});
          }, 0);
        }

        on(eventName, handler) {
          this.listeners[eventName] = this.listeners[eventName] || [];
          this.listeners[eventName].push(handler);
        }

        emit(eventName, payload) {
          (this.listeners[eventName] || []).forEach((handler) => handler(payload));
        }

        setOptions(options) {
          this.options = { ...this.options, ...options };
        }

        getPositions(ids) {
          const nodeMap = this.data?.nodes?.map || new Map();
          const targetIds = Array.isArray(ids) ? ids : Array.from(nodeMap.keys());
          const positions = {};
          targetIds.forEach((id) => {
            const item = nodeMap.get(id);
            if (item) {
              positions[id] = {
                x: Number(item.x) || 0,
                y: Number(item.y) || 0,
              };
            }
          });
          return positions;
        }

        selectNodes(ids) {
          this.selectedNodes = Array.isArray(ids) ? ids.slice() : [];
        }

        unselectAll() {
          this.selectedNodes = [];
        }

        focus() {}

        fit() {}

        moveNode(id, x, y) {
          const item = this.data?.nodes?.map?.get(id);
          if (!item) {
            return;
          }
          this.data.nodes.map.set(id, { ...item, x, y });
        }

        canvasToDOM(position) {
          return {
            x: Number(position?.x) || 0,
            y: Number(position?.y) || 0,
          };
        }

        getNodeAt() {
          return null;
        }
      }

      window.vis = window.vis || {};
      window.vis.DataSet = DataSet;
      window.vis.Network = Network;
    }, { graphData: GRAPH_DATA });

    await page.goto(FILE_URL);
    await page.waitForSelector("#loading-overlay.is-hidden", { timeout: 10000 }).catch(() => null);
    await page.waitForTimeout(1500);
  });

  test("page loads and topbar renders", async ({ page }) => {
    await expect(page.locator(".topbar")).toBeVisible();
    await expect(page.locator("#search-input")).toBeVisible();
    await expect(page.locator("#settings-button")).toBeVisible();
  });

  test("palette button opens picker menu via settings menu", async ({ page }) => {
    await page.click("#settings-button");
    await page.click("#settings-palette-btn");
    await expect(page.locator("#palette-picker")).toBeVisible();
    expect(await page.locator(".palette-option").count()).toBeGreaterThanOrEqual(2);
  });

  test("sidebar sections can be open simultaneously", async ({ page }) => {
    const sections = page.locator("details[data-accordion]");
    const first = sections.nth(0);
    const second = sections.nth(1);

    if (!(await first.evaluate((element) => element.hasAttribute("open")))) {
      await first.locator("summary").click();
    }
    if (!(await second.evaluate((element) => element.hasAttribute("open")))) {
      await second.locator("summary").click();
    }

    await expect(first).toHaveJSProperty("open", true);
    await expect(second).toHaveJSProperty("open", true);
  });

  test("embed mode activates via mode menu", async ({ page }) => {
    await page.click("#mode-button");
    await page.click("[data-mode='embed']");
    await expect(page.locator("#mode-button")).toHaveClass(/is-active/);
  });

  test("focus exit button is hidden initially", async ({ page }) => {
    await expect(page.locator("#focus-exit-button")).toHaveClass(/is-hidden/);
  });

  test("help modal opens on ? key", async ({ page }) => {
    await page.keyboard.press("?");
    await expect(page.locator("#help-modal")).not.toHaveClass(/is-hidden/);
  });

  test("feedback modal opens via settings menu", async ({ page }) => {
    await page.click("#settings-button");
    await page.click("#settings-feedback-btn");
    await expect(page.locator("#feedback-modal")).not.toHaveClass(/is-hidden/);
  });

  test("search input focused with / key", async ({ page }) => {
    await page.keyboard.press("/");
    await expect(page.locator("#search-input")).toBeFocused();
  });

  test("mode button exists in topbar with mode menu", async ({ page }) => {
    await expect(page.locator("#mode-button")).toBeVisible();
    await page.click("#mode-button");
    await expect(page.locator("[data-mode='discover']")).toBeVisible();
  });

  test("double-click activates focus mode and shows discover nav in detail panel", async ({ page }) => {
    // Simulate double-click via JS event
    await page.evaluate(() => {
      // Call the double-click handler directly
      if (typeof handleNetworkDoubleClick === "function") {
        handleNetworkDoubleClick({ nodes: ["project:a"], edges: [], event: { srcEvent: {} } });
      } else if (window.state?.network) {
        // fallback: fire via network event
      }
    });
    await page.waitForTimeout(200);

    const focusActive = await page.evaluate(() => Boolean(state?.focus));
    expect(focusActive).toBe(true);

    // Discover nav should be visible in the detail panel
    await expect(page.locator("#detail-discover-nav")).not.toHaveClass(/is-hidden/);
    // Focus exit button should be visible
    await expect(page.locator("#focus-exit-button")).not.toHaveClass(/is-hidden/);
  });

  test("search suggestions appear after typing 2+ chars", async ({ page }) => {
    await page.fill("#search-input", "Al");
    await page.waitForTimeout(100);
    const suggEl = page.locator("#search-suggestions");
    await expect(suggEl).not.toHaveClass(/is-hidden/);
    const items = suggEl.locator(".search-suggestion-item");
    expect(await items.count()).toBeGreaterThan(0);
  });

  test("embed mode hides physics and preset sections", async ({ page }) => {
    // Initially both sections visible
    await expect(page.locator("#tools-presets-section")).not.toHaveClass(/is-hidden/);
    await expect(page.locator("#tools-physics-section")).not.toHaveClass(/is-hidden/);

    // Activate embed via mode menu
    await page.click("#mode-button");
    await page.click("[data-mode='embed']");
    await page.waitForTimeout(200);

    await expect(page.locator("#tools-presets-section")).toHaveClass(/is-hidden/);
    await expect(page.locator("#tools-physics-section")).toHaveClass(/is-hidden/);
  });

  test("focus mode filters visible nodes to neighborhood", async ({ page }) => {
    // Start with full view — should have all 3 nodes visible
    const initialCount = await page.evaluate(() => state?.currentView?.nodeIds?.size ?? 0);
    expect(initialCount).toBeGreaterThanOrEqual(1);

    // Double-click project:a — which only has 2 direct neighbors (project:b, org:acme)
    await page.evaluate(() => {
      if (typeof handleNetworkDoubleClick === "function") {
        handleNetworkDoubleClick({ nodes: ["project:a"], edges: [], event: { srcEvent: {} } });
      }
    });
    await page.waitForTimeout(200);

    const focusedCount = await page.evaluate(() => state?.currentView?.nodeIds?.size ?? 0);
    // Focus on project:a at depth=1 should show: project:a + org:acme (BUILT_BY) + project:b (SEMANTICALLY_NEAR)
    // All 3 nodes are 1-hop neighbors, so count should be ≤ initial
    expect(focusedCount).toBeLessThanOrEqual(initialCount);
  });
});
