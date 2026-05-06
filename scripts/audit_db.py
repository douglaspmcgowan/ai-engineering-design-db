"""DB quality audit script — run from repo root"""
import json, sys, re
from collections import defaultdict, Counter
sys.stdout.reconfigure(encoding='utf-8')

with open('consolidated.jsonl', encoding='utf-8') as f:
    recs = [json.loads(l) for l in f if l.strip()]
with open('graph/graph-data.json', encoding='utf-8') as f:
    g = json.load(f)

# ── Duplicate / near-duplicate: same URL ─────────────────────────
url_to_recs = defaultdict(list)
for r in recs:
    for key in ['url_primary', 'url_paper', 'url_github']:
        u = (r.get(key) or '').strip()
        if u and len(u) > 10:
            url_to_recs[u].append((r['id'], r['name']))

print('=== RECORDS SHARING THE SAME URL ===')
found = 0
for url, items in url_to_recs.items():
    if len(items) > 1:
        print(f'  {url}')
        for rid, rname in items:
            print(f'    -> {rid}  |  {rname}')
        found += 1
print(f'  Total URL dupes: {found}')

# ── Duplicate: same name (case-insensitive) ───────────────────────
name_map = defaultdict(list)
for r in recs:
    name_map[r['name'].lower().strip()].append(r['id'])
print('\n=== RECORDS WITH DUPLICATE NAMES ===')
found2 = 0
for name, ids in name_map.items():
    if len(ids) > 1:
        print(f'  "{name}": {ids}')
        found2 += 1
if not found2:
    print('  (none)')

# ── Edge type counts ──────────────────────────────────────────────
print('\n=== EDGE TYPE COUNTS ===')
etype = Counter(e['type'] for e in g['edges'])
for t, cnt in sorted(etype.items(), key=lambda x: -x[1]):
    print(f'  {cnt:5d}  {t}')

# ── Hub nodes: high degree non-project/technique ──────────────────
node_deg = defaultdict(int)
for e in g['edges']:
    node_deg[e['source']] += 1
    node_deg[e['target']] += 1

non_proj = {n['id']: n for n in g['nodes'] if n.get('type') not in ('Project', 'Technique')}
print('\n=== TOP 20 NON-PROJECT/TECHNIQUE HUBS ===')
hubs = sorted([(nid, cnt) for nid, cnt in node_deg.items() if nid in non_proj], key=lambda x: -x[1])[:20]
for nid, cnt in hubs:
    n = non_proj[nid]
    print(f'  {cnt:4d}  [{n["type"]:16s}]  {n["label"]}')

# ── Under-populated categories ────────────────────────────────────
print('\n=== UNDER-POPULATED CATEGORIES (< 5 entries) ===')
cat_counts = Counter(r.get('category', '?') for r in recs)
for cat, cnt in sorted(cat_counts.items(), key=lambda x: x[1]):
    if cnt < 5:
        examples = [r['name'] for r in recs if r.get('category') == cat][:3]
        print(f'  {cnt}  {cat}:  {examples}')

# ── Overlapping category pairs ────────────────────────────────────
print('\n=== POTENTIALLY OVERLAPPING CATEGORY PAIRS ===')
overlap_pairs = [
    ('optimization', 'topology-optimization'),
    ('physics-informed-nn', 'differentiable-physics'),
    ('physics-surrogate', 'neural-operator'),
    ('text-to-3d', 'text-to-cad'),
    ('image-to-3d', 'image-to-cad'),
    ('dfm-ai', 'dfam-ai'),
    ('generative-3d-shape', 'image-to-3d'),
    ('cad-copilot', 'cad-agent'),
    ('program-cad', 'text-to-cad'),
]
for a, b in overlap_pairs:
    ca = cat_counts.get(a, 0)
    cb = cat_counts.get(b, 0)
    # find records that use techniques/keywords bridging both
    bridge = [r['name'] for r in recs if r.get('category') in (a, b)]
    print(f'  {a} ({ca}) vs {b} ({cb})')

# ── Technique synonyms (known pairs to check) ─────────────────────
print('\n=== KNOWN TECHNIQUE SYNONYM PAIRS IN DATA ===')
all_techs = []
for r in recs:
    all_techs.extend(r.get('techniques', []))
tech_freq = Counter(all_techs)

synonym_candidates = [
    ('machine-learning', 'deep-learning'),
    ('gan', 'generative-adversarial-network'),
    ('cnn', 'convolutional-neural-network'),
    ('llm', 'large-language-model'),
    ('rl', 'reinforcement-learning'),
    ('transformer', 'attention-mechanism'),
    ('gnn', 'graph-neural-network'),
    ('vae', 'variational-autoencoder'),
    ('diffusion', 'diffusion-model'),
    ('pinn', 'physics-informed-nn'),
    ('neural-radiance-field', 'nerf'),
    ('point-cloud', 'point-clouds'),
    ('cad-generation', 'cad-gen'),
    ('data-driven', 'machine-learning'),
    ('deep-learning', 'neural-network'),
    ('multimodal', 'multi-modal'),
    ('generative-ai', 'generative-model'),
    ('vision-language-model', 'vlm'),
]
for a, b in synonym_candidates:
    fa = tech_freq.get(a, 0)
    fb = tech_freq.get(b, 0)
    if fa > 0 and fb > 0:
        print(f'  BOTH EXIST: "{a}" ({fa}) vs "{b}" ({fb}) -> merge to single slug')
    elif fa > 0 and fb == 0:
        pass  # only one exists, fine
    elif fb > 0 and fa == 0:
        pass  # only one exists, fine

# ── Single-use techniques count ────────────────────────────────────
singles = [(t, c) for t, c in tech_freq.items() if c == 1]
print(f'\n=== SINGLE-USE TECHNIQUE SLUGS: {len(singles)} total ===')
for t, _ in sorted(singles)[:40]:
    print(f'    {t}')
if len(singles) > 40:
    print(f'    ... and {len(singles)-40} more')
