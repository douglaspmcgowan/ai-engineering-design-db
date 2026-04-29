"""
load-kuzu.py — load the knowledge graph into Kuzu (embedded Cypher DB).

Creates graph/kuzu-db/ with the schema from KNOWLEDGE-GRAPH.md and loads
nodes.csv + edges.csv. Then runs a handful of saved Cypher queries.

Usage:
    pip install kuzu
    python scripts/load-kuzu.py             # build + run sample queries
    python scripts/load-kuzu.py --rebuild   # blow away DB and reload
    python scripts/load-kuzu.py --query "MATCH (p:Project)-[:USES_TECHNIQUE]->(t {label:'transformer'}) RETURN p.label LIMIT 20"
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GRAPH = ROOT / "graph"
DB_DIR = GRAPH / "kuzu-db"


def load(rebuild: bool = False) -> "kuzu.Connection":  # type: ignore
    import kuzu  # type: ignore

    if rebuild and DB_DIR.exists():
        shutil.rmtree(DB_DIR)
        print(f"Removed {DB_DIR}")

    db = kuzu.Database(str(DB_DIR))
    conn = kuzu.Connection(db)

    # ── Schema (one node table per type, one rel table per edge type) ─────
    if rebuild or not DB_DIR.exists() or not (DB_DIR / "data.kz").exists():
        print("Creating schema...")
        node_types = [
            "Project", "Organization", "Category", "Technique",
            "Modality", "PhysicsDomain", "Industry", "Year",
            "Venue", "Person",
        ]
        for t in node_types:
            conn.execute(
                f"CREATE NODE TABLE IF NOT EXISTS {t}"
                "(id STRING, label STRING, props STRING, PRIMARY KEY(id))"
            )

        edge_types = [
            "BUILT_BY", "IN_CATEGORY", "USES_TECHNIQUE",
            "CONSUMES", "PRODUCES", "OPERATES_ON", "APPLIED_TO",
            "RELEASED_IN", "PUBLISHED_AT", "AUTHORED",
            "CITES", "BUILT_ON", "BENCHMARKED_AGAINST",
            "SEMANTICALLY_NEAR",
        ]
        # Use a generic FROM/TO so any node type can connect (Kuzu allows multi-pair rel tables)
        # We declare each rel as connecting any pair of node types we expect.
        rel_pairs = {
            "BUILT_BY":            "FROM Project TO Organization",
            "IN_CATEGORY":         "FROM Project TO Category",
            "USES_TECHNIQUE":      "FROM Project TO Technique",
            "CONSUMES":            "FROM Project TO Modality",
            "PRODUCES":            "FROM Project TO Modality",
            "OPERATES_ON":         "FROM Project TO PhysicsDomain",
            "APPLIED_TO":          "FROM Project TO Industry",
            "RELEASED_IN":         "FROM Project TO Year",
            "PUBLISHED_AT":        "FROM Project TO Venue",
            "AUTHORED":            "FROM Project TO Person",
            "CITES":               "FROM Project TO Project",
            "BUILT_ON":            "FROM Project TO Project",
            "BENCHMARKED_AGAINST": "FROM Project TO Project",
            "SEMANTICALLY_NEAR":   "FROM Project TO Project",
        }
        for rel, pair in rel_pairs.items():
            conn.execute(
                f"CREATE REL TABLE IF NOT EXISTS {rel}"
                f"({pair}, weight DOUBLE DEFAULT 1.0, evidence STRING DEFAULT '')"
            )
        print(f"  {len(node_types)} node tables, {len(rel_pairs)} rel tables")

    return conn


def insert_nodes(conn, csv_path: Path) -> int:
    if not csv_path.exists():
        return 0
    n = 0
    with open(csv_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ntype = row["type"]
            try:
                conn.execute(
                    f"MERGE (n:{ntype} {{id: $id}}) "
                    "SET n.label = $label, n.props = $props",
                    {"id": row["id"], "label": row["label"], "props": row.get("props", "")},
                )
                n += 1
            except Exception as e:
                print(f"  ! node error {row.get('id')}: {e}", file=sys.stderr)
    return n


def insert_edges(conn, csv_path: Path, default_type: str | None = None) -> int:
    if not csv_path.exists():
        return 0
    n = 0
    with open(csv_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            etype = (row.get("type") or default_type or "").strip()
            if not etype:
                continue
            src = row["source"]
            tgt = row["target"]
            # Identify the node-type for FROM/TO via the id prefix
            from_type = src.split(":", 1)[0].title().replace("Physicsdomain", "PhysicsDomain")
            to_type   = tgt.split(":", 1)[0].title().replace("Physicsdomain", "PhysicsDomain")
            try:
                conn.execute(
                    f"MATCH (a:{from_type} {{id: $src}}), (b:{to_type} {{id: $tgt}}) "
                    f"CREATE (a)-[:{etype} {{weight: $w, evidence: $ev}}]->(b)",
                    {
                        "src": src, "tgt": tgt,
                        "w":   float(row.get("weight", 1.0) or 1.0),
                        "ev":  row.get("evidence", ""),
                    },
                )
                n += 1
            except Exception as e:
                # Many will fail because we don't match every (FROM, TO) declared above
                # — silently skip rather than spam logs.
                pass
    return n


def run_sample_queries(conn) -> None:
    QUERIES: list[tuple[str, str]] = [
        ("Most-used techniques",
         "MATCH (p:Project)-[:USES_TECHNIQUE]->(t:Technique) "
         "RETURN t.label, count(*) AS uses ORDER BY uses DESC LIMIT 15"),
        ("Most-prolific organizations",
         "MATCH (p:Project)-[:BUILT_BY]->(o:Organization) "
         "RETURN o.label, count(*) AS projects ORDER BY projects DESC LIMIT 15"),
        ("Projects in 'neural-operator' category",
         "MATCH (p:Project)-[:IN_CATEGORY]->(c:Category {label:'neural-operator'}) "
         "RETURN p.label LIMIT 10"),
        ("Projects built on FNO (any project with 'fno' in label)",
         "MATCH (p:Project)-[:BUILT_ON]->(t:Project) "
         "WHERE t.label CONTAINS 'FNO' OR t.label CONTAINS 'Fourier Neural Operator' "
         "RETURN p.label, t.label LIMIT 20"),
        ("Categories with most projects",
         "MATCH (p:Project)-[:IN_CATEGORY]->(c:Category) "
         "RETURN c.label, count(*) AS n ORDER BY n DESC LIMIT 10"),
    ]
    for name, q in QUERIES:
        print(f"\n--- {name} ---")
        try:
            r = conn.execute(q)
            while r.has_next():
                print("  " + " | ".join(str(x) for x in r.get_next()))
        except Exception as e:
            print(f"  query failed: {e}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--rebuild", action="store_true", help="Drop and re-create the DB")
    p.add_argument("--query", help="Run a single Cypher query and exit")
    args = p.parse_args()

    try:
        import kuzu  # type: ignore
    except ImportError:
        print("kuzu not installed. Run: pip install kuzu", file=sys.stderr)
        return 1

    conn = load(rebuild=args.rebuild)

    if args.query:
        r = conn.execute(args.query)
        while r.has_next():
            print(" | ".join(str(x) for x in r.get_next()))
        return 0

    # Load nodes
    print("\nLoading nodes...")
    n1 = insert_nodes(conn, GRAPH / "nodes.csv")
    n2 = insert_nodes(conn, GRAPH / "venue-nodes.csv")
    n3 = insert_nodes(conn, GRAPH / "people-nodes.csv")
    print(f"  Loaded ~{n1 + n2 + n3} nodes (incl. duplicates merged via MERGE)")

    # Load edges (all CSVs)
    print("\nLoading edges...")
    e1 = insert_edges(conn, GRAPH / "edges.csv")
    e2 = insert_edges(conn, GRAPH / "semantic-edges.csv")
    e3 = insert_edges(conn, GRAPH / "venue-edges.csv")
    e4 = insert_edges(conn, GRAPH / "people-edges.csv")
    print(f"  Loaded {e1 + e2 + e3 + e4} edges (some may have failed silently if node-types don't match)")

    print("\n========== Sample queries ==========")
    run_sample_queries(conn)
    print(f"\nKuzu DB ready at: {DB_DIR}")
    print("Run custom queries:")
    print('  py -3 scripts/load-kuzu.py --query "MATCH (p:Project) RETURN count(p)"')
    return 0


if __name__ == "__main__":
    sys.exit(main())
