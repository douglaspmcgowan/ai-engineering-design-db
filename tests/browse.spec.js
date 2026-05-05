const { test, expect } = require("@playwright/test");
const path = require("path");

const FILE_URL =
  "file:///" + path.resolve(__dirname, "../browse.html").replace(/\\/g, "/");

const GRAPH_DATA = {
  nodes: [
    {
      id: "project:alpha",
      type: "Project",
      label: "Alpha",
      props: {
        name: "Alpha",
        organization: "MIT",
        category: "cad-generation",
        year: 2023,
        description: "A neural network tool for CAD generation using transformers and diffusion models.",
        url: "https://github.com/example/alpha",
        url_paper: "https://arxiv.org/abs/1234",
        techniques: ["transformer", "diffusion", "vae"],
        input_modality: "text",
        output_modality: "cad-sequence",
        physics_domain: "",
        industry_application: ["mechanical-design"],
        tags: [],
      },
    },
    {
      id: "project:beta",
      type: "Project",
      label: "Beta",
      props: {
        name: "Beta",
        organization: "Stanford",
        category: "neural-operator",
        year: 2021,
        description: "A physics-informed neural operator for fluid dynamics simulation and surrogate modeling.",
        url: "",
        url_paper: "https://arxiv.org/abs/5678",
        techniques: ["fno", "pinn", "neural-operator"],
        input_modality: "geometry",
        output_modality: "simulation",
        physics_domain: "fluid-dynamics",
        industry_application: ["aerospace"],
        tags: [],
      },
    },
    {
      id: "org:mit",
      type: "Organization",
      label: "MIT",
      props: { name: "MIT", organization: "MIT" },
    },
  ],
  edges: [
    { source: "project:alpha", target: "org:mit", type: "BUILT_BY", weight: 1 },
  ],
};

test.describe("browse", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(
      ({ graphData }) => {
        const originalFetch = window.fetch.bind(window);
        window.fetch = (input, init) => {
          const url = typeof input === "string" ? input : input?.url || "";
          if (url.includes("graph-data.json")) {
            return Promise.resolve(
              new Response(JSON.stringify(graphData), {
                status: 200,
                headers: { "Content-Type": "application/json" },
              })
            );
          }
          return originalFetch(input, init);
        };
      },
      { graphData: GRAPH_DATA }
    );

    await page.goto(FILE_URL);

    // Wait until results-count contains "project" (init() completed)
    await page.waitForFunction(
      () => {
        const el = document.getElementById("results-count");
        return el && el.textContent.includes("project");
      },
      { timeout: 8000 }
    );
  });

  // ── Basic load ────────────────────────────────────────────────────
  test("page loads and topbar renders", async ({ page }) => {
    await expect(page.locator(".topbar")).toBeVisible();
    await expect(page.locator("#search-input")).toBeVisible();
    await expect(page.locator(".view-toggle")).toBeVisible();
  });

  test("project cards are rendered", async ({ page }) => {
    const count = await page.locator(".project-card").count();
    expect(count).toBe(2);
  });

  test("results count shows correct total", async ({ page }) => {
    const text = await page.locator("#results-count").innerText();
    expect(text).toContain("2");
    expect(text).toContain("project");
  });

  // ── Sidebar ───────────────────────────────────────────────────────
  test("category sidebar is populated", async ({ page }) => {
    const items = await page.locator(".cat-item").count();
    expect(items).toBeGreaterThanOrEqual(1);
  });

  test("output modality chips are rendered", async ({ page }) => {
    const chips = await page.locator("#mod-chips .chip").count();
    expect(chips).toBeGreaterThanOrEqual(1);
  });

  // ── Search ────────────────────────────────────────────────────────
  test("search filters cards by name", async ({ page }) => {
    await page.fill("#search-input", "Alpha");
    await page.waitForTimeout(100);
    const count = await page.locator(".project-card").count();
    expect(count).toBe(1);
  });

  test("search shows no-results message when no match", async ({ page }) => {
    await page.fill("#search-input", "xyznotfound999");
    await page.waitForTimeout(100);
    await expect(page.locator(".no-results")).toBeVisible();
  });

  test("search clear button resets results", async ({ page }) => {
    await page.fill("#search-input", "Alpha");
    await page.waitForTimeout(100);
    // Wait for clear button to appear
    await page.waitForFunction(
      () => document.getElementById("search-clear")?.classList.contains("visible"),
      { timeout: 2000 }
    );
    await page.click("#search-clear");
    await page.waitForTimeout(100);
    const count = await page.locator(".project-card").count();
    expect(count).toBe(2);
  });

  // ── View toggle ───────────────────────────────────────────────────
  test("table view toggle shows table and hides cards", async ({ page }) => {
    await page.click("#btn-table");
    await expect(page.locator("#table-wrap")).toBeVisible();
    await expect(page.locator("#card-grid")).not.toBeVisible();
  });

  test("table view shows correct row count", async ({ page }) => {
    await page.click("#btn-table");
    const rows = await page.locator("#table-body tr").count();
    expect(rows).toBe(2);
  });

  test("cards view toggle restores cards", async ({ page }) => {
    await page.click("#btn-table");
    await page.click("#btn-cards");
    await expect(page.locator("#card-grid")).toBeVisible();
    await expect(page.locator("#table-wrap")).not.toBeVisible();
  });

  // ── Detail panel ──────────────────────────────────────────────────
  test("clicking card opens detail panel", async ({ page }) => {
    await page.click(".project-card:first-child");
    await expect(page.locator("#detail-panel")).toHaveClass(/open/);
    await expect(page.locator(".detail-name")).toBeVisible();
  });

  test("close button hides detail panel", async ({ page }) => {
    await page.click(".project-card:first-child");
    await expect(page.locator("#detail-panel")).toHaveClass(/open/);
    await page.click(".detail-close");
    await expect(page.locator("#detail-panel")).not.toHaveClass(/open/);
  });

  test("clicking same card twice closes detail panel", async ({ page }) => {
    await page.click(".project-card:first-child");
    await expect(page.locator("#detail-panel")).toHaveClass(/open/);
    await page.click(".project-card:first-child");
    await expect(page.locator("#detail-panel")).not.toHaveClass(/open/);
  });

  // ── Keyboard ──────────────────────────────────────────────────────
  test("slash key focuses search input", async ({ page }) => {
    await page.evaluate(() => document.activeElement?.blur());
    await page.keyboard.press("/");
    await expect(page.locator("#search-input")).toBeFocused();
  });

  test("Escape key closes detail panel", async ({ page }) => {
    await page.click(".project-card:first-child");
    await expect(page.locator("#detail-panel")).toHaveClass(/open/);
    await page.keyboard.press("Escape");
    await expect(page.locator("#detail-panel")).not.toHaveClass(/open/);
  });

  // ── Filters ───────────────────────────────────────────────────────
  test("clear all button resets search and shows all cards", async ({ page }) => {
    await page.fill("#search-input", "Alpha");
    await page.waitForTimeout(100);
    await page.click(".clear-all-btn");
    await page.waitForTimeout(100);
    const count = await page.locator(".project-card").count();
    expect(count).toBe(2);
    const searchVal = await page.locator("#search-input").inputValue();
    expect(searchVal).toBe("");
  });

  // ── Sort ─────────────────────────────────────────────────────────
  test("default sort is newest first", async ({ page }) => {
    const yearTags = await page.locator(".project-card .year-tag").allInnerTexts();
    const years = yearTags.map(Number).filter(Boolean);
    for (let i = 0; i < years.length - 1; i++) {
      expect(years[i]).toBeGreaterThanOrEqual(years[i + 1]);
    }
  });
});
