"""
query-graph.py — NetworkX-based query interface for the graph.

Runs the same kinds of queries as load-kuzu.py without needing Kuzu
(useful while Kuzu has no Python 3.14 wheels). Loads graph-data.json
into a directed multigraph, runs a saved set of "queries", and supports
ad-hoc queries via Python expressions on the `G` graph object.

Usage:
    python scripts/query-graph.py                      # run all saved queries
    python scripts/query-graph.py --query "category:neural-operator"
    python scripts/query-graph.py --shell              # drop into REPL with G loaded
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
GRAPH_JSON = ROOT / "graph" / "graph-data.json"


def load_graph():
    import networkx as nx  # type: ignore
    data = json.loads(GRAPH_JSON.read_text(encoding="utf-8"))
    G = nx.MultiDiGraph()
    for n in data["nodes"]:
        # Avoid clobbering networkx attribute names (`type`); namespace into props
        props = n.get("props") or {}
        # Drop keys that collide with networkx internals
        props_clean = {k: v for k, v in props.items() if k not in ("type",)}
        G.add_node(n["id"], type=n["type"], label=n["label"], **props_clean)
    for e in data["edges"]:
        G.add_edge(
            e["source"], e["target"],
            type=e["type"], weight=e.get("weight", 1.0),
            evidence=e.get("evidence", ""),
        )
    return G, data["meta"]


# ── Query helpers ─────────────────────────────────────────────────────────────

def by_type(G, t: str):
    return [n for n, d in G.nodes(data=True) if d.get("type") == t]


def edges_of_type(G, t: str):
    return [(u, v, d) for u, v, d in G.edges(data=True) if d.get("type") == t]


def neighbors(G, n: str, edge_type: str | None = None, direction: str = "out"):
    if direction == "out":
        edges = G.out_edges(n, data=True)
        return [(v, d) for u, v, d in edges if not edge_type or d.get("type") == edge_type]
    else:
        edges = G.in_edges(n, data=True)
        return [(u, d) for u, v, d in edges if not edge_type or d.get("type") == edge_type]


# ── Saved queries ─────────────────────────────────────────────────────────────

def q_top_techniques(G, k: int = 15):
    print(f"\n--- Top {k} techniques (by USES_TECHNIQUE in-degree) ---")
    counts = Counter()
    for u, v, d in G.edges(data=True):
        if d.get("type") == "USES_TECHNIQUE":
            counts[v] += 1
    for tid, n in counts.most_common(k):
        print(f"  {n:3d}  {G.nodes[tid]['label']}")


def q_top_orgs(G, k: int = 15):
    print(f"\n--- Top {k} organizations ---")
    counts = Counter()
    for u, v, d in G.edges(data=True):
        if d.get("type") == "BUILT_BY":
            counts[v] += 1
    for oid, n in counts.most_common(k):
        print(f"  {n:3d}  {G.nodes[oid]['label']}")


def q_top_venues(G, k: int = 10):
    print(f"\n--- Top {k} venues (PUBLISHED_AT in-degree) ---")
    counts = Counter()
    for u, v, d in G.edges(data=True):
        if d.get("type") == "PUBLISHED_AT":
            counts[v] += 1
    for vid, n in counts.most_common(k):
        print(f"  {n:3d}  {G.nodes[vid]['label']}")


def q_built_on_lineage(G, target_substring: str = "FNO", k: int = 20):
    print(f"\n--- Projects BUILT_ON something containing '{target_substring}' ---")
    rows = []
    for u, v, d in G.edges(data=True):
        if d.get("type") != "BUILT_ON":
            continue
        tgt_label = G.nodes[v].get("label", "")
        if target_substring.lower() in tgt_label.lower():
            rows.append((G.nodes[u]["label"], tgt_label))
    for src, tgt in rows[:k]:
        print(f"  {src}  ->  {tgt}")


def q_category_counts(G, k: int = 15):
    print(f"\n--- Top {k} categories ---")
    counts = Counter()
    for u, v, d in G.edges(data=True):
        if d.get("type") == "IN_CATEGORY":
            counts[v] += 1
    for cid, n in counts.most_common(k):
        print(f"  {n:3d}  {G.nodes[cid]['label']}")


def q_projects_in_category(G, cat: str, k: int = 20):
    print(f"\n--- First {k} projects in category '{cat}' ---")
    cat_id = f"category:{cat}"
    for u, v, d in G.in_edges(cat_id, data=True):
        if d.get("type") == "IN_CATEGORY":
            print(f"  {G.nodes[u]['label']}")
            k -= 1
            if k == 0:
                break


def q_citation_density(G, k: int = 10):
    print(f"\n--- Most-cited projects (CITES + BUILT_ON in-degree) ---")
    counts = Counter()
    for u, v, d in G.edges(data=True):
        if d.get("type") in ("CITES", "BUILT_ON"):
            counts[v] += 1
    for pid, n in counts.most_common(k):
        if G.nodes[pid].get("type") == "Project":
            print(f"  {n:3d}  {G.nodes[pid]['label']}")


def q_org_x_industry(G):
    print("\n--- Top (org, industry) co-occurrences ---")
    counts = Counter()
    for proj in by_type(G, "Project"):
        orgs = [v for v, d in neighbors(G, proj, "BUILT_BY", "out")]
        inds = [v for v, d in neighbors(G, proj, "APPLIED_TO", "out")]
        for o in orgs:
            for ind in inds:
                counts[(G.nodes[o]["label"], G.nodes[ind]["label"])] += 1
    for (o, i), n in counts.most_common(15):
        print(f"  {n:3d}  {o:25s}  -> {i}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--shell", action="store_true",
                   help="Drop into a Python REPL with G + helpers loaded")
    p.add_argument("--query", help="Run a single named query: top-techniques, top-orgs, "
                   "top-venues, built-on:FNO, categories, in-cat:neural-operator, citations, org-industry")
    args = p.parse_args()

    try:
        import networkx as nx  # type: ignore  # noqa: F401
    except ImportError:
        print("networkx not installed. Run: pip install networkx", file=sys.stderr)
        return 1

    G, meta = load_graph()
    print(f"Loaded {meta['name']}: {G.number_of_nodes()} nodes, "
          f"{G.number_of_edges()} edges")

    if args.shell:
        import code
        banner = "G = the graph. Helpers: by_type(G, 'Project'), neighbors(G, n, 'CITES'), edges_of_type(G, 'BUILT_ON')"
        code.interact(banner=banner, local={
            "G": G, "by_type": by_type, "neighbors": neighbors,
            "edges_of_type": edges_of_type, "Counter": Counter,
        })
        return 0

    if args.query:
        q = args.query
        if q == "top-techniques":      q_top_techniques(G)
        elif q == "top-orgs":          q_top_orgs(G)
        elif q == "top-venues":        q_top_venues(G)
        elif q == "categories":        q_category_counts(G)
        elif q == "citations":         q_citation_density(G)
        elif q == "org-industry":      q_org_x_industry(G)
        elif q.startswith("built-on:"):    q_built_on_lineage(G, q.split(":", 1)[1])
        elif q.startswith("in-cat:"):      q_projects_in_category(G, q.split(":", 1)[1])
        else:
            print(f"Unknown query: {q}", file=sys.stderr)
            return 1
        return 0

    # Default: run them all
    q_category_counts(G)
    q_top_techniques(G)
    q_top_orgs(G)
    q_top_venues(G)
    q_citation_density(G)
    q_built_on_lineage(G, "FNO")
    q_org_x_industry(G)
    return 0


if __name__ == "__main__":
    sys.exit(main())
