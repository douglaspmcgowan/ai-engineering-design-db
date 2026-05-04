"""
build-graph.py — Pass A: construct knowledge graph from consolidated.jsonl.

Builds structural edges only (deterministic, from JSON fields):
  BUILT_BY      Project → Organization
  IN_CATEGORY   Project → Category
  USES_TECHNIQUE Project → Technique
  CONSUMES      Project → Modality (input)
  PRODUCES      Project → Modality (output)
  OPERATES_ON   Project → PhysicsDomain
  APPLIED_TO    Project → Industry
  RELEASED_IN   Project → Year

Outputs (in graph/):
  nodes.csv       id, type, label, props_json
  edges.csv       source, target, type, weight, evidence
  graph.gexf      Gephi-importable
  graph.html      pyvis interactive (opens in browser)

Usage:
  python scripts/build-graph.py [--no-html]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import uuid
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IN_FILE = ROOT / "consolidated.jsonl"
GRAPH_DIR = ROOT / "graph"
EMBED_COORDS = GRAPH_DIR / "embed-coords.json"
EMBED_COORDS_ALL = GRAPH_DIR / "embed-coords-all.json"  # all-entity UMAP coords
CLUSTER_LABELS = GRAPH_DIR / "cluster-labels.json"

# ── Node type constants ──────────────────────────────────────────────────────
T_PROJECT = "Project"
T_ORG = "Organization"
T_CATEGORY = "Category"
T_TECHNIQUE = "Technique"
T_MODALITY = "Modality"
T_PHYSICS = "PhysicsDomain"
T_INDUSTRY = "Industry"
T_YEAR = "Year"


def slugify(text: str) -> str:
    s = str(text).lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")[:80]


def node_id(node_type: str, label: str) -> str:
    return f"{node_type.lower()}:{slugify(label)}"


class GraphBuilder:
    def __init__(self) -> None:
        self.nodes: dict[str, dict] = {}   # node_id → {id, type, label, props}
        self.edges: list[dict] = []        # {source, target, type, weight, evidence}
        self._edge_seen: set[tuple] = set()

    # ── Node helpers ─────────────────────────────────────────────────────────

    def add_node(self, ntype: str, label: str, props: dict | None = None) -> str:
        nid = node_id(ntype, label)
        if nid not in self.nodes:
            self.nodes[nid] = {
                "id": nid,
                "type": ntype,
                "label": label,
                "props": json.dumps(props or {}),
            }
        return nid

    # ── Edge helpers ─────────────────────────────────────────────────────────

    def add_edge(
        self,
        src: str,
        tgt: str,
        etype: str,
        weight: float = 1.0,
        evidence: str = "structural",
    ) -> None:
        key = (src, tgt, etype)
        if key in self._edge_seen:
            return
        self._edge_seen.add(key)
        self.edges.append(
            {
                "source": src,
                "target": tgt,
                "type": etype,
                "weight": weight,
                "evidence": evidence,
            }
        )

    # ── Main build ───────────────────────────────────────────────────────────

    def ingest(self, records: list[dict]) -> None:
        for rec in records:
            # Project node IDs MUST use rec['id'] (the canonical, deduplicated id),
            # not slugify(rec['name']). Otherwise semantic-edges.csv (which
            # references project:<rec['id']>) won't resolve when name-slug differs.
            pid = f"project:{rec['id']}"
            label = rec.get("name", rec["id"])
            if pid not in self.nodes:
                self.nodes[pid] = {
                    "id":    pid,
                    "type":  T_PROJECT,
                    "label": label,
                    "props": json.dumps({
                        k: rec.get(k)
                        for k in (
                            "id", "category", "type", "organization", "year",
                            "url_primary", "url_paper", "url_github",
                            "status", "input_modality", "output_modality",
                            "physics_domain", "country",
                        )
                    }),
                }

            # BUILT_BY → Organization
            org = (rec.get("organization") or "").strip()
            if org:
                oid = self.add_node(T_ORG, org)
                self.add_edge(pid, oid, "BUILT_BY")

            # IN_CATEGORY → Category
            cat = (rec.get("category") or "").strip()
            if cat:
                cid = self.add_node(T_CATEGORY, cat)
                self.add_edge(pid, cid, "IN_CATEGORY")

            # USES_TECHNIQUE → Technique
            for tech in rec.get("techniques") or []:
                tech = tech.strip()
                if tech:
                    tid = self.add_node(T_TECHNIQUE, tech)
                    self.add_edge(pid, tid, "USES_TECHNIQUE")

            # CONSUMES → Modality (input)
            inp = (rec.get("input_modality") or "").strip()
            if inp:
                mid = self.add_node(T_MODALITY, inp)
                self.add_edge(pid, mid, "CONSUMES")

            # PRODUCES → Modality (output)
            out = (rec.get("output_modality") or "").strip()
            if out:
                mid = self.add_node(T_MODALITY, out)
                self.add_edge(pid, mid, "PRODUCES")

            # OPERATES_ON → PhysicsDomain
            phys = (rec.get("physics_domain") or "").strip()
            if phys:
                phid = self.add_node(T_PHYSICS, phys)
                self.add_edge(pid, phid, "OPERATES_ON")

            # APPLIED_TO → Industry
            for ind in rec.get("industry_application") or []:
                ind = ind.strip()
                if ind:
                    iid = self.add_node(T_INDUSTRY, ind)
                    self.add_edge(pid, iid, "APPLIED_TO")

            # RELEASED_IN → Year
            yr = rec.get("year")
            if yr:
                yid = self.add_node(T_YEAR, str(yr))
                self.add_edge(pid, yid, "RELEASED_IN")

    # ── Export helpers ───────────────────────────────────────────────────────

    def write_csv(self, out_dir: Path) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        with open(out_dir / "nodes.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["id", "type", "label", "props"])
            w.writeheader()
            w.writerows(self.nodes.values())
        with open(out_dir / "edges.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(
                f, fieldnames=["source", "target", "type", "weight", "evidence"]
            )
            w.writeheader()
            w.writerows(self.edges)
        print(f"Wrote {len(self.nodes)} nodes, {len(self.edges)} edges to {out_dir}/")

    def write_gexf(self, path: Path) -> None:
        """Write a minimal GEXF 1.3 file (Gephi-importable)."""
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<gexf xmlns="http://gexf.net/1.3" version="1.3">',
            '  <graph defaultedgetype="directed">',
            "    <nodes>",
        ]
        for n in self.nodes.values():
            label = n["label"].replace('"', "&quot;").replace("&", "&amp;")
            lines.append(
                f'      <node id="{n["id"]}" label="{label}">'
                f'<attvalues><attvalue for="type" value="{n["type"]}"/>'
                f"</attvalues></node>"
            )
        lines.append("    </nodes>")
        lines.append("    <edges>")
        for i, e in enumerate(self.edges):
            lines.append(
                f'      <edge id="e{i}" source="{e["source"]}" target="{e["target"]}"'
                f' label="{e["type"]}" weight="{e["weight"]}"/>'
            )
        lines.append("    </edges>")
        lines.append("  </graph>")
        lines.append("</gexf>")
        path.write_text("\n".join(lines), encoding="utf-8")
        print(f"Wrote GEXF to {path}")

    def write_json(self, path: Path, records: list[dict]) -> None:
        """Write graph-data.json for the graph explorer app."""
        # Gather metadata
        categories = sorted({r.get("category", "") for r in records if r.get("category")})
        years = [r.get("year") for r in records if r.get("year")]
        year_range = [min(years), max(years)] if years else [2019, 2026]

        # Build id → record lookup for description enrichment
        by_id: dict[str, dict] = {r["id"]: r for r in records}

        # Load UMAP embed coordinates (optional — skip gracefully if missing)
        embed_coords: dict[str, dict] = {}
        if EMBED_COORDS.exists():
            try:
                embed_coords = json.loads(EMBED_COORDS.read_text(encoding="utf-8"))
                print(f"Loaded embed coords for {len(embed_coords)} project nodes")
            except Exception:
                pass

        # Load all-entity UMAP coords (keyed by full node ID e.g. "project:foo")
        embed_coords_all: dict[str, dict] = {}
        if EMBED_COORDS_ALL.exists():
            try:
                embed_coords_all = json.loads(EMBED_COORDS_ALL.read_text(encoding="utf-8"))
                print(f"Loaded all-entity embed coords for {len(embed_coords_all)} nodes")
            except Exception:
                pass

        # Load cluster labels (set_B_kmeans) for embed view
        cluster_label_map: dict[int, str] = {}
        if CLUSTER_LABELS.exists():
            try:
                cl = json.loads(CLUSTER_LABELS.read_text(encoding="utf-8"))
                for c, v in cl.get("set_B_kmeans", {}).items():
                    cluster_label_map[int(c)] = v["label"]
            except Exception:
                pass

        # Nodes: parse props JSON so the explorer gets structured objects
        out_nodes = []
        for n in self.nodes.values():
            try:
                props = json.loads(n["props"])
            except Exception:
                props = {}
            # Enrich Project nodes with full description + embed coords
            rec_id = props.get("id", "")
            if n["type"] == T_PROJECT and rec_id in by_id:
                rec = by_id[rec_id]
                props["description"] = rec.get("description", "")
                props["techniques"] = rec.get("techniques", [])
                props["industry_application"] = rec.get("industry_application", [])
                props["tags"] = rec.get("tags", [])
                props["name"] = rec.get("name", n["label"])
                # Inject UMAP 2D coords for embed view (project-only embedding)
                ec = embed_coords.get(rec_id)
                if ec:
                    props["embed_x"] = ec["x"]
                    props["embed_y"] = ec["y"]
                    props["cluster_k"] = ec["cluster_k"]
                    props["cluster_label"] = cluster_label_map.get(ec["cluster_k"], f"Cluster {ec['cluster_k']}")

            # Inject all-entity UMAP coords + cluster assignment (keyed by full node ID)
            ec_all = embed_coords_all.get(n["id"])
            if ec_all:
                props["embed_all_x"] = ec_all["x"]
                props["embed_all_y"] = ec_all["y"]
                if "cluster_k_all" in ec_all:
                    props["cluster_k_all"] = ec_all["cluster_k_all"]
                    props["cluster_label_all"] = ec_all.get("cluster_label_all", f"Cluster {ec_all['cluster_k_all']}")

            out_nodes.append({"id": n["id"], "type": n["type"], "label": n["label"], "props": props})

        out_edges = [dict(e) for e in self.edges]

        # Load all-entity cluster labels if available
        cluster_labels_all: dict[str, str] = {}
        labels_all_path = GRAPH_DIR / "cluster-labels-all.json"
        if labels_all_path.exists():
            try:
                cluster_labels_all = json.loads(labels_all_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        data = {
            "meta": {
                "name": "AI Engineering Design DB",
                "version": "2026-04-29",
                "nodeCount": len(out_nodes),
                "edgeCount": len(out_edges),
            },
            "categories": categories,
            "yearRange": year_range,
            "clusterLabels": cluster_label_map,      # project-only Set-B clusters
            "clusterLabelsAll": cluster_labels_all,  # all-entity k-means clusters
            "nodes": out_nodes,
            "edges": out_edges,
        }
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        print(f"Wrote graph-data.json ({len(out_nodes)} nodes, {len(out_edges)} edges) to {path}")

    def write_html(self, path: Path) -> None:
        try:
            from pyvis.network import Network  # type: ignore
        except ImportError:
            print("pyvis not installed — skipping HTML export. Run: pip install pyvis")
            return

        TYPE_COLOR = {
            T_PROJECT: "#4e79a7",
            T_ORG: "#f28e2b",
            T_CATEGORY: "#e15759",
            T_TECHNIQUE: "#76b7b2",
            T_MODALITY: "#59a14f",
            T_PHYSICS: "#edc948",
            T_INDUSTRY: "#b07aa1",
            T_YEAR: "#ff9da7",
        }
        TYPE_SIZE = {
            T_PROJECT: 8,
            T_ORG: 18,
            T_CATEGORY: 22,
            T_TECHNIQUE: 14,
            T_MODALITY: 14,
            T_PHYSICS: 16,
            T_INDUSTRY: 14,
            T_YEAR: 12,
        }

        net = Network(
            height="900px",
            width="100%",
            directed=True,
            bgcolor="#1a1a2e",
            font_color="white",
        )
        net.set_options("""
        {
          "physics": {"stabilization": {"iterations": 150}},
          "edges": {"arrows": {"to": {"enabled": true, "scaleFactor": 0.5}},
                    "color": {"opacity": 0.4}},
          "interaction": {"hover": true, "navigationButtons": true}
        }
        """)

        for n in self.nodes.values():
            color = TYPE_COLOR.get(n["type"], "#aaa")
            size = TYPE_SIZE.get(n["type"], 10)
            net.add_node(
                n["id"],
                label=n["label"][:40],
                title=f"{n['type']}: {n['label']}",
                color=color,
                size=size,
            )
        for e in self.edges:
            net.add_edge(e["source"], e["target"], title=e["type"], width=0.8)

        net.save_graph(str(path))
        print(f"Wrote interactive HTML to {path}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--no-html", action="store_true", help="Skip pyvis HTML export")
    p.add_argument(
        "--input", default=str(IN_FILE), help="Path to consolidated.jsonl"
    )
    args = p.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"Missing {in_path} — run consolidate.py first", file=sys.stderr)
        return 1

    records = [json.loads(l) for l in open(in_path, encoding="utf-8") if l.strip()]
    print(f"Loaded {len(records)} records")

    g = GraphBuilder()
    g.ingest(records)

    # Auto-include external nodes (Venues, People) if their CSVs exist
    import csv as _csv
    for nodes_csv in (GRAPH_DIR / "venue-nodes.csv", GRAPH_DIR / "people-nodes.csv"):
        if not nodes_csv.exists():
            continue
        added = 0
        with open(nodes_csv, newline="", encoding="utf-8") as nf:
            for row in _csv.DictReader(nf):
                if row["id"] in g.nodes:
                    continue
                g.nodes[row["id"]] = {
                    "id":    row["id"],
                    "type":  row["type"],
                    "label": row["label"],
                    "props": row.get("props", "{}"),
                }
                added += 1
        print(f"Loaded {added} nodes from {nodes_csv.name}")

    # Auto-include all auxiliary edge CSVs (semantic, deep citations, venue, people)
    for edges_csv in (
        GRAPH_DIR / "semantic-edges.csv",
        GRAPH_DIR / "deep-citations.csv",
        GRAPH_DIR / "venue-edges.csv",
        GRAPH_DIR / "people-edges.csv",
    ):
        if not edges_csv.exists():
            continue
        n = 0
        with open(edges_csv, newline="", encoding="utf-8") as sf:
            for row in _csv.DictReader(sf):
                if row["source"] not in g.nodes or row["target"] not in g.nodes:
                    continue  # skip dangling refs
                key = (row["source"], row["target"], row["type"])
                if key not in g._edge_seen:
                    g._edge_seen.add(key)
                    g.edges.append({
                        "source": row["source"],
                        "target": row["target"],
                        "type": row["type"],
                        "weight": float(row.get("weight", 1.0)),
                        "evidence": row.get("evidence", ""),
                    })
                    n += 1
        print(f"Loaded {n} edges from {edges_csv.name}")

    out = GRAPH_DIR
    g.write_csv(out)
    g.write_gexf(out / "graph.gexf")
    g.write_json(out / "graph-data.json", records)
    if not args.no_html:
        g.write_html(out / "graph.html")

    # Summary stats
    by_type: dict[str, int] = defaultdict(int)
    for n in g.nodes.values():
        by_type[n["type"]] += 1
    print("\nNode counts by type:")
    for t, c in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  {t}: {c}")
    edge_types: dict[str, int] = defaultdict(int)
    for e in g.edges:
        edge_types[e["type"]] += 1
    print("\nEdge counts by type:")
    for t, c in sorted(edge_types.items(), key=lambda x: -x[1]):
        print(f"  {t}: {c}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
