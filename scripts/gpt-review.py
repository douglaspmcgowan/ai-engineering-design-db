"""Run GPT-4.1 design review of explorer.html and print results."""
import os, sys
from pathlib import Path
from openai import OpenAI

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
html = (ROOT / "explorer.html").read_text(encoding="utf-8", errors="replace")

PROMPT = """You are a senior UI engineer doing a design-quality audit. Be blunt, specific, evidence-based. Only cite what you actually see in the code.

Review this single-file HTML graph explorer app against these criteria:

VIBE-CODED ANTI-PATTERNS (FAIL if present):
1. Typography — uses Inter at one weight everywhere instead of Geist + JetBrains Mono with weight contrast
2. Corners — uniform rounded-2xl (16px+) everywhere instead of nested radii (buttons 4-6px, cards 10px)
3. Grain — no feTurbulence grain overlay (flat plastic look)
4. Hero — aurora purple-pink gradient blob
5. Layout — centered everything, no asymmetry
6. Copy-emoji — emoji as emotional decoration in headlines/section titles
7. Icons — mixed icon sets (Lucide + Heroicons + Font Awesome together)
8. Copy — generic text ("Explore the graph", "Rich data") vs specific ("831 projects · 2,405 nodes")
9. Color — slate/zinc cool grays (#94a3b8, #64748b type palette) instead of warm neutrals
10. Shadows — single unmodified flat box-shadow everywhere

IMPLEMENTATION CHECKS:
Q1. All 6 toolbar buttons (Fit, Embed, Force, Palette, Shortcuts, Feedback) have a real onclick handler?
Q2. UMAP embed mode: reads embed_x/embed_y from node props, sets network positions, disables physics?
Q3. Cluster convex hulls: drawn inside network.on('afterDrawing', ctx => ...) callback?
Q4. Focus mode: has exit button, expand-to-N-hop, Tab key cycling through neighbors, Esc to exit?
Q5. Feedback form: POSTs to formspree.io URL?

For each of the 15 items above, answer: PASS / FAIL / MIXED
Then give a one-line evidence quote (exact short snippet from the code, or "not found").
End with a prioritized fix list (top 5 only, most impactful first).

FILE BELOW (first 55000 chars):
""" + html[:55000]

client = OpenAI()
resp = client.chat.completions.create(
    model="gpt-5.5",
    messages=[{"role": "user", "content": PROMPT}],
    max_completion_tokens=2000,
)
print(resp.choices[0].message.content)
