"""
_spring_length_shots.py
Re-shoot spring length screenshots for the Obsidian doc.
Fixes help-modal-over-graph bug by pre-seeding localStorage before graph loads.

Usage (from project root, with http.server running on port 8770):
    python _spring_length_shots.py
"""
import sys
import asyncio
import os
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("Install playwright: pip install playwright && playwright install chromium")
    sys.exit(1)

URL = "http://localhost:8770/explorer.html"
OUT_DIR = Path(
    r"C:\Users\dougl\My Drive (douglaspmcgowan@gmail.com)"
    r"\Obsidian\Metropolis Pt. 1--The Maverick And The Test"
    r"\Research\attachments\spring-lengths"
)

# springLength values to capture
SPRING_LENGTHS = [80, 120, 150, 200, 240, 280]

# Base physics params (from CLAUDE.md defaults)
BASE_PHYSICS = {
    "gravitationalConstant": -15000,
    "centralGravity": 0.006,
    "springConstant": 0.10,
    "avoidOverlap": 0.20,
    "damping": 0.15,
}

# How long to let physics run before screenshot (ms)
SETTLE_MS = 5500
VIEWPORT = {"width": 1440, "height": 900}


async def shoot(page, spring_length: int, out_path: Path):
    """Navigate to the explorer, override spring length, wait, screenshot."""
    print(f"  springLength={spring_length} → {out_path.name}")

    await page.goto(URL, wait_until="networkidle")

    # Pre-seed localStorage so the help modal doesn't open
    await page.evaluate("""() => {
        localStorage.setItem('explorer-visited', 'true');
    }""")

    # Reload so the seeded localStorage takes effect before init runs
    await page.goto(URL, wait_until="networkidle")

    # Wait for vis-network canvas to be present
    await page.wait_for_selector("#network canvas", timeout=30000)

    # Inject the custom spring length and restart physics
    await page.evaluate(f"""(springLength) => {{
        // Set the Physics Lab slider so settlePhysics() picks it up
        const sl = document.getElementById('phys-sl');
        const slVal = document.getElementById('phys-sl-val');
        if (sl) {{
            sl.value = springLength;
            if (slVal) slVal.textContent = springLength;
        }}

        // Programmatically call settlePhysics to apply the new spring length
        if (typeof settlePhysics === 'function') {{
            settlePhysics();
        }} else if (window.settlePhysics) {{
            window.settlePhysics();
        }}
    }}""", spring_length)

    # Wait for physics to settle
    await page.wait_for_timeout(SETTLE_MS)

    # Capture only the canvas area (exclude sidebars)
    canvas = page.locator("#canvas-surface")
    await canvas.screenshot(path=str(out_path))
    print(f"    ✓ saved ({out_path.stat().st_size // 1024} KB)")


async def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output: {OUT_DIR}")
    print(f"Target: {URL}\n")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        context = await browser.new_context(viewport=VIEWPORT)
        page = await context.new_page()

        for sl in SPRING_LENGTHS:
            slug = f"sl-{sl:03d}"
            out = OUT_DIR / f"{slug}.png"
            try:
                await shoot(page, sl, out)
            except Exception as exc:
                print(f"    ✗ FAILED: {exc}")

        await browser.close()

    print("\nDone. Check the Obsidian vault for updated screenshots.")


if __name__ == "__main__":
    asyncio.run(main())
