# Playbook: Field Mapper

**Goal:** Rapidly map an unfamiliar sub-field — find the key players, core techniques, and how they cluster.

---

## Step 1 — Search the field name

In the Browse sidebar, type the field name into the search box.  
Examples: `topology optimization`, `neural operator`, `sketch-to-cad`

Look at the results count. < 5 results = thin coverage; > 30 = well-represented.

---

## Step 2 — Filter by category

Click the matching category chip in the sidebar (e.g. `topology-opt`).  
Note which organizations appear most in the cards — these are the labs driving the field.

---

## Step 3 — Switch to Timeline view

Click **Timeline** in the view toggle.

- Identify the year the field exploded (sudden jump in project count).
- Look for technique clusters that appear together in a year cohort.

---

## Step 4 — Open the Explorer graph

Click **Explorer** in the nav, then search the field name in the graph search box.

Double-click any project node to enter **Focus mode** and see its 1-hop neighborhood:
- Organization nodes → who built it
- Category nodes → how it's classified
- Other project nodes → direct intellectual neighbors

Use **Find Similar** (appears in the detail panel) to find nearest neighbors by technique overlap.

---

## Step 5 — Map the technique space

In the Explorer sidebar, uncheck all node types except **Technique**.  
This shows only the technique graph. Technique clusters = sub-schools within the field.

---

## Step 6 — Identify key papers

In the Browse detail panel for each project, click the paper URL (arXiv / venue) to read the abstract.  
Projects with `year ≤ field_explosion_year − 2` are likely foundational; later ones are applications.

---

## Output

After this playbook you should be able to answer:
- When did this field start? (Timeline)
- Who are the 3–5 leading labs? (Organization nodes)
- What are the 2–3 dominant technique families? (Technique clusters)
- What is the most-cited/connected project? (highest connection count in Explorer Stats panel)
