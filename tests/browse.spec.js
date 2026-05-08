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

  // ── Table column sort ─────────────────────────────────────────────
  test("table name column sorts ascending on first click", async ({ page }) => {
    await page.click("#btn-table");
    await page.click("th[onclick*=\"'name'\"]");
    await page.waitForTimeout(100);
    const names = await page.locator("#table-body tr td:first-child").allInnerTexts();
    const sorted = [...names].sort((a, b) => a.localeCompare(b));
    expect(names).toEqual(sorted);
  });

  test("table name column sort toggles to descending on second click", async ({ page }) => {
    await page.click("#btn-table");
    await page.click("th[onclick*=\"'name'\"]"); // asc
    await page.click("th[onclick*=\"'name'\"]"); // desc
    await page.waitForTimeout(100);
    const names = await page.locator("#table-body tr td:first-child").allInnerTexts();
    const sorted = [...names].sort((a, b) => b.localeCompare(a));
    expect(names).toEqual(sorted);
  });

  test("table year column sorts descending after switching from another sort", async ({ page }) => {
    await page.click("#btn-table");
    // First sort by name to clear year sort state
    await page.click("th[onclick*=\"'name'\"]");
    await page.waitForTimeout(100);
    // Now click year — first click on a fresh field defaults to "desc"
    await page.click("th[onclick*=\"'year'\"]");
    await page.waitForTimeout(100);
    const years = (await page.locator("#table-body tr td:nth-child(3)").allInnerTexts()).map(Number).filter(Boolean);
    for (let i = 0; i < years.length - 1; i++) {
      expect(years[i]).toBeGreaterThanOrEqual(years[i + 1]);
    }
  });

  test("table year column sort toggles to ascending on second consecutive click", async ({ page }) => {
    await page.click("#btn-table");
    // Sort by name first to reset year sort state
    await page.click("th[onclick*=\"'name'\"]");
    await page.waitForTimeout(100);
    // Click year once → desc, twice → asc
    await page.click("th[onclick*=\"'year'\"]");
    await page.click("th[onclick*=\"'year'\"]");
    await page.waitForTimeout(100);
    const years = (await page.locator("#table-body tr td:nth-child(3)").allInnerTexts()).map(Number).filter(Boolean);
    for (let i = 0; i < years.length - 1; i++) {
      expect(years[i]).toBeLessThanOrEqual(years[i + 1]);
    }
  });

  // ── Year range filter ─────────────────────────────────────────────
  test("year-min filter hides projects below threshold", async ({ page }) => {
    await page.fill("#year-min", "2023");
    await page.waitForTimeout(150);
    const count = await page.locator(".project-card").count();
    expect(count).toBe(1); // only Alpha (2023); Beta (2021) hidden
  });

  test("year-max filter hides projects above threshold", async ({ page }) => {
    await page.fill("#year-max", "2022");
    await page.waitForTimeout(150);
    const count = await page.locator(".project-card").count();
    expect(count).toBe(1); // only Beta (2021); Alpha (2023) hidden
  });

  test("year range cleared on clear-all", async ({ page }) => {
    await page.fill("#year-min", "2022");
    await page.waitForTimeout(100);
    await page.click(".clear-all-btn");
    await page.waitForTimeout(100);
    const val = await page.locator("#year-min").inputValue();
    expect(val).toBe("");
    const count = await page.locator(".project-card").count();
    expect(count).toBe(2);
  });

  // ── Collections ───────────────────────────────────────────────────
  test("create collection via JS and render it in list", async ({ page }) => {
    // Bypass prompt() by writing directly to localStorage and calling renderCollections()
    await page.evaluate(() => {
      localStorage.setItem("aied-collections", JSON.stringify({ "Favorites": [] }));
      if (typeof renderCollections === "function") renderCollections();
    });
    await expect(page.locator("#collections-list .collection-item-name")).toContainText("Favorites");
  });

  test("save project to existing collection updates count", async ({ page }) => {
    await page.evaluate(() => {
      localStorage.setItem("aied-collections", JSON.stringify({ "Favorites": [] }));
      if (typeof renderCollections === "function") renderCollections();
    });
    // Open detail panel then save
    await page.click(".project-card:first-child");
    await page.waitForTimeout(200);
    // saveToCollection with exactly 1 collection goes directly (no prompt)
    await page.evaluate(() => {
      if (typeof saveToCollection === "function") saveToCollection("project:alpha");
    });
    const count = await page.evaluate(() => {
      const cols = JSON.parse(localStorage.getItem("aied-collections") || "{}");
      return (cols["Favorites"] || []).length;
    });
    expect(count).toBe(1);
  });

  test("collection filter shows only collection members", async ({ page }) => {
    await page.evaluate(() => {
      localStorage.setItem("aied-collections", JSON.stringify({ "My List": ["project:alpha"] }));
      if (typeof renderCollections === "function") renderCollections();
    });
    // Click the collection to filter
    await page.evaluate(() => {
      if (typeof toggleCollectionFilter === "function") toggleCollectionFilter("My List");
    });
    await page.waitForTimeout(150);
    const count = await page.locator(".project-card").count();
    expect(count).toBe(1);
  });

  test("delete collection removes it from list", async ({ page }) => {
    await page.evaluate(() => {
      localStorage.setItem("aied-collections", JSON.stringify({ "ToDelete": ["project:alpha"] }));
      if (typeof renderCollections === "function") renderCollections();
    });
    await expect(page.locator("#collections-list .collection-item-name")).toContainText("ToDelete");
    await page.evaluate(() => {
      if (typeof deleteCollection === "function") deleteCollection("ToDelete");
    });
    const items = await page.locator("#collections-list .collection-item").count();
    expect(items).toBe(0);
  });

  // ── Submit modal ──────────────────────────────────────────────────
  test("FAB opens submit modal and sets body.modal-open", async ({ page }) => {
    await page.click("#submit-fab");
    await expect(page.locator("#submit-modal")).not.toHaveClass(/is-hidden/);
    const hasClass = await page.evaluate(() => document.body.classList.contains("modal-open"));
    expect(hasClass).toBe(true);
  });

  test("FAB is hidden when modal is open", async ({ page }) => {
    await page.click("#submit-fab");
    const fabVisible = await page.locator("#submit-fab").isVisible();
    expect(fabVisible).toBe(false); // hidden via body.modal-open CSS
  });

  test("close button dismisses modal and removes modal-open", async ({ page }) => {
    await page.click("#submit-fab");
    await page.click(".modal-close, #submit-close");
    await expect(page.locator("#submit-modal")).toHaveClass(/is-hidden/);
    const hasClass = await page.evaluate(() => document.body.classList.contains("modal-open"));
    expect(hasClass).toBe(false);
  });

  test("backdrop click closes modal", async ({ page }) => {
    await page.click("#submit-fab");
    // Click the backdrop (the modal-backdrop element itself, not its contents)
    await page.locator("#submit-modal").click({ position: { x: 5, y: 5 } });
    await expect(page.locator("#submit-modal")).toHaveClass(/is-hidden/);
  });

  test("submit modal note text is not stale GPT-4o copy", async ({ page }) => {
    await page.click("#submit-fab");
    const noteText = await page.locator(".modal-note").first().innerText();
    expect(noteText).not.toContain("GPT-4o");
    expect(noteText).toContain("AI will");
  });

  // ── GitHub API submission ─────────────────────────────────────────
  test("submit sends GET then PUT to GitHub API and shows success", async ({ page }) => {
    // Use in-page fetch mock (page.route CORS is blocked from file:// origin)
    await page.evaluate(() => {
      window._ghCalls = [];
      const orig = window.fetch.bind(window);
      window.fetch = async (input, init) => {
        const url = typeof input === "string" ? input : (input?.url || "");
        if (url.includes("api.github.com")) {
          window._ghCalls.push({ method: (init?.method || "GET").toUpperCase(), url });
          const method = (init?.method || "GET").toUpperCase();
          if (method === "GET") {
            return new Response(JSON.stringify({ message: "Not Found" }), {
              status: 404, headers: { "Content-Type": "application/json" }
            });
          }
          return new Response(JSON.stringify({ content: { sha: "abc123" } }), {
            status: 200, headers: { "Content-Type": "application/json" }
          });
        }
        return orig(input, init);
      };
    });

    // Inject a fake token — bypasses admin gating, getToken() reads localStorage directly
    // browse.html uses TOKEN_KEY = "inbox-gh-token"
    await page.evaluate(() => localStorage.setItem("inbox-gh-token", "fake_pat_token_test123"));

    // Open modal, fill text, submit
    await page.click("#submit-fab");
    await page.fill("#submit-text", "Test project submission from Playwright");
    await page.click("#submit-send");

    // Wait for result message (success or error)
    await page.waitForFunction(
      () => {
        const el = document.getElementById("submit-result-msg");
        return el && (el.textContent.includes("✓") || el.textContent.includes("✗"));
      },
      { timeout: 10000 }
    );

    // Verify both API calls were made
    const calls = await page.evaluate(() => window._ghCalls || []);
    expect(calls.some(c => c.method === "GET")).toBe(true);
    expect(calls.some(c => c.method === "PUT")).toBe(true);

    const msg = await page.locator("#submit-result-msg").innerText();
    expect(msg).toContain("✓");
  });
});
