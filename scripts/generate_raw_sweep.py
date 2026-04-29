"""
generate_raw_sweep.py

Build ten raw/*.jsonl files for the AI engineering design database by combining:
- exact-title lookups against OpenAlex / DOI landing pages for papers and datasets
- targeted search sweeps against OpenAlex for broad literature buckets
- official product / feature pages for commercial tools

The script is intentionally opinionated and reproducible:
- seed IDs from raw/00-seed-from-training.jsonl are never reused
- each output file is rebuilt from scratch
- every record is written with the exact field order requested by the user
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher
from html import unescape
from pathlib import Path
from typing import Any

import requests

try:
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover - best-effort fallback
    BeautifulSoup = None


ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"
SEED_FILE = RAW_DIR / "00-seed-from-training.jsonl"

OPENALEX = "https://api.openalex.org/works"
CROSSREF = "https://api.crossref.org/works/"
ARXIV = "https://export.arxiv.org/api/query"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)

session = requests.Session()
session.headers.update({"User-Agent": UA})

JSON_CACHE: dict[tuple[str, tuple[tuple[str, Any], ...]], Any] = {}
TEXT_CACHE: dict[str, str] = {}
MATCH_STOPWORDS = {
    "a",
    "an",
    "and",
    "approach",
    "based",
    "cad",
    "computer",
    "data",
    "design",
    "for",
    "from",
    "generation",
    "generative",
    "in",
    "learning",
    "model",
    "models",
    "of",
    "on",
    "paper",
    "physics",
    "system",
    "the",
    "through",
    "to",
    "using",
    "via",
    "with",
}


def slugify(text: str) -> str:
    s = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii")
    s = s.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:80]


def normalize_space(text: str) -> str:
    text = unescape(text or "")
    text = text.replace("\\n", " ").replace("\\t", " ")
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", normalize_space(text).lower()).strip()


def compact_key(text: str) -> str:
    return normalize_key(text).replace(" ", "")


def key_tokens(text: str) -> list[str]:
    return [tok for tok in normalize_key(text).split() if len(tok) >= 4 and tok not in MATCH_STOPWORDS]


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w[\w-]*\b", text or ""))


def trim_words(text: str, max_words: int) -> str:
    words = re.findall(r"\S+", text or "")
    if len(words) <= max_words:
        return text.strip()
    return " ".join(words[:max_words]).rstrip(" ,.;:") + "."


def abstract_from_inverted_index(inv: dict[str, list[int]] | None) -> str:
    if not inv:
        return ""
    words: list[str] = []
    for token, positions in inv.items():
        for pos in positions:
            if pos >= len(words):
                words.extend([""] * (pos - len(words) + 1))
            words[pos] = token
    return normalize_space(" ".join(words))


def get_json(url: str, *, params: dict[str, Any] | None = None, timeout: int = 20) -> Any:
    cache_key = (url, tuple(sorted((params or {}).items())))
    if cache_key in JSON_CACHE:
        return JSON_CACHE[cache_key]
    r = session.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    JSON_CACHE[cache_key] = data
    return data


def get_text(url: str, *, timeout: int = 15) -> str:
    if url in TEXT_CACHE:
        return TEXT_CACHE[url]
    r = session.get(url, timeout=timeout)
    r.raise_for_status()
    TEXT_CACHE[url] = r.text
    return TEXT_CACHE[url]


def parse_html(html: str) -> Any:
    if BeautifulSoup is None:
        return None
    try:
        return BeautifulSoup(html, "html.parser")
    except Exception:
        return None


def visible_paragraphs(html: str, *, max_items: int = 6) -> list[str]:
    soup = parse_html(html)
    if soup is None:
        return []
    for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav", "form"]):
        tag.decompose()
    out: list[str] = []
    selectors = ["main p", "article p", ".content p", ".post p", ".entry-content p", "p"]
    seen: set[str] = set()
    for selector in selectors:
        for el in soup.select(selector):
            txt = normalize_space(el.get_text(" ", strip=True))
            low = txt.lower()
            if len(txt) < 45 or txt in seen:
                continue
            if any(
                low.startswith(prefix)
                for prefix in (
                    "cookie",
                    "privacy",
                    "accept ",
                    "sign up",
                    "subscribe",
                    "download now",
                )
            ):
                continue
            seen.add(txt)
            out.append(txt)
            if len(out) >= max_items:
                return out
    return out


def meta_descriptions(html: str) -> list[str]:
    soup = parse_html(html)
    if soup is None:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for meta in soup.find_all("meta"):
        key = meta.get("name") or meta.get("property") or ""
        if key.lower() not in {"description", "og:description", "twitter:description", "dc.description"}:
            continue
        txt = normalize_space(meta.get("content") or "")
        if txt and txt not in seen:
            seen.add(txt)
            out.append(txt)
    return out


def github_links(html: str) -> list[str]:
    links = sorted(
        set(re.findall(r"https?://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", html or ""))
    )
    return links


def generic_abstract_from_html(html: str) -> str:
    soup = parse_html(html)
    if soup is None:
        return ""

    selectors = [
        "section.Abstract",
        "section#Abs1",
        "div#Abs1-content",
        "div.abstract",
        "div.abstract-content",
        "div.c-article-section__content",
        "[data-test='article-section__content']",
        "section[aria-labelledby*='abstract']",
    ]
    for selector in selectors:
        el = soup.select_one(selector)
        if el:
            txt = normalize_space(el.get_text(" ", strip=True))
            if word_count(txt) >= 40:
                return txt

    for header in soup.find_all(re.compile("^h[1-6]$")):
        if normalize_space(header.get_text(" ", strip=True)).lower() == "abstract":
            bits: list[str] = []
            for sib in header.find_next_siblings():
                if sib.name and re.match("^h[1-6]$", sib.name):
                    break
                txt = normalize_space(sib.get_text(" ", strip=True))
                if txt:
                    bits.append(txt)
                if word_count(" ".join(bits)) >= 80:
                    break
            joined = normalize_space(" ".join(bits))
            if word_count(joined) >= 40:
                return joined

    for txt in meta_descriptions(html):
        if word_count(txt) >= 20:
            return txt
    return ""


def clean_crossref_abstract(text: str) -> str:
    text = re.sub(r"</?jats:[^>]+>", " ", text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return normalize_space(text)


def openalex_search(query: str, *, per_page: int = 8, filter_expr: str | None = None) -> list[dict[str, Any]]:
    params = {"search": query, "per-page": per_page}
    if filter_expr:
        params["filter"] = filter_expr
    try:
        data = get_json(OPENALEX, params=params)
        return data.get("results", [])
    except Exception:
        return []


def title_matches_query(query: str, title: str) -> bool:
    q_key = normalize_key(query)
    t_key = normalize_key(title)
    if not q_key or not t_key:
        return False
    if q_key == t_key:
        return True
    if q_key in t_key:
        return True
    if len(q_key) >= 20 and t_key in q_key:
        return True

    q_compact = compact_key(query)
    t_compact = compact_key(title)
    if len(q_compact) >= 4 and q_compact in t_compact:
        return True

    q_tokens = key_tokens(query)
    if q_tokens:
        present = sum(1 for tok in q_tokens if tok in t_key)
        if present / len(q_tokens) >= 0.6:
            return True

    return SequenceMatcher(None, q_key, t_key).ratio() >= 0.72


def best_openalex_match(query: str, preferred_name: str | None = None) -> dict[str, Any] | None:
    results = openalex_search(query, per_page=10)
    if not results:
        return None
    target = normalize_space(preferred_name or query).lower()

    def score(it: dict[str, Any]) -> tuple[float, float]:
        title = normalize_space(it.get("title") or "").lower()
        exact = SequenceMatcher(None, target, title).ratio()
        starts = 1.0 if title.startswith(target[:20]) else 0.0
        return (exact, starts)

    best = max(results, key=score)
    title = normalize_space(best.get("title") or "")
    if not title_matches_query(preferred_name or query, title):
        return None
    return best


def crossref_abstract_from_doi(doi_url: str | None) -> str:
    if not doi_url:
        return ""
    doi = doi_url.replace("https://doi.org/", "").replace("http://doi.org/", "").strip()
    if not doi:
        return ""
    try:
        data = get_json(CROSSREF + doi)
    except Exception:
        return ""
    return clean_crossref_abstract(data.get("message", {}).get("abstract") or "")


def arxiv_summary(query: str) -> str:
    try:
        xml = get_text(ARXIV, timeout=30)
    except Exception:
        return ""
    return normalize_space(xml)


def choose_org_country(work: dict[str, Any], fallback_org: str = "", fallback_country: str = "US") -> tuple[str, str]:
    authorships = work.get("authorships") or []
    for auth in authorships:
        for inst in auth.get("institutions") or []:
            org = normalize_space(inst.get("display_name") or "")
            country = normalize_space(inst.get("country_code") or "")
            if org and re.fullmatch(r"[A-Z]{2}", country or ""):
                return org, country
            if org:
                return org, fallback_country
    return fallback_org or "unknown", fallback_country


def maybe_extract_paper_url(work: dict[str, Any]) -> str:
    doi = work.get("doi") or ""
    if doi:
        return doi
    loc = work.get("primary_location") or {}
    url = loc.get("landing_page_url") or ""
    if url:
        return url
    oa = (work.get("open_access") or {}).get("oa_url") or ""
    return oa


def maybe_extract_primary_url(work: dict[str, Any]) -> str:
    loc = work.get("primary_location") or {}
    return loc.get("landing_page_url") or work.get("doi") or (work.get("open_access") or {}).get("oa_url") or ""


def detect_physics_domain(text: str, default: str = "none") -> str:
    low = text.lower()
    mapping = [
        ("fluid", ["fluid", "cfd", "navier-stokes", "flow", "aero", "aerodynamic", "airfoil", "wing"]),
        ("structural", ["structural", "stress", "strain", "elastic", "stiffness", "compliance", "truss", "beam"]),
        ("thermal", ["thermal", "heat", "temperature", "cooling", "thermo"]),
        ("electromagnetic", ["electromagnetic", "photonic", "optics", "wave", "antenna"]),
        ("molecular", ["molecular", "atom", "interatomic", "crystal", "chemistry", "materials"]),
        ("multi-physics", ["multiphysics", "multi-physics", "thermo-mechanical", "coupled"]),
        ("atmospheric", ["weather", "atmosphere", "climate"]),
        ("ocean", ["ocean", "wave"]),
    ]
    for domain, keys in mapping:
        if any(k in low for k in keys):
            return domain
    return default


def detect_techniques(text: str) -> list[str]:
    low = text.lower()
    pairs = [
        ("transformer", ["transformer", "attention"]),
        ("diffusion-model", ["diffusion"]),
        ("llm", ["large language model", "llm", "gpt", "chatbot"]),
        ("multimodal", ["multimodal", "vision-language", "vlm"]),
        ("graph-neural-network", ["graph neural", "gnn", "message passing"]),
        ("fourier-neural-operator", ["fourier neural operator", "fno"]),
        ("neural-operator", ["neural operator", "operator learning", "deeponet"]),
        ("physics-informed-nn", ["physics-informed", "pinn"]),
        ("reinforcement-learning", ["reinforcement learning"]),
        ("gan", ["gan", "generative adversarial"]),
        ("gaussian-splatting", ["gaussian splatting", "gaussian object"]),
        ("implicit-function", ["implicit", "sdf", "radiance field", "nerf"]),
        ("procedural-modeling", ["procedural", "cadquery", "kcl", "script"]),
        ("topology-optimization", ["topology optimization", "generative design"]),
        ("mlip", ["interatomic potential", "neural potential"]),
        ("equivariant-gnn", ["equivariant", "e(3)", "se(3)"]),
        ("support-generation", ["support structure", "support generation"]),
        ("tool-calling", ["tool-using", "tool-augmented", "function calling", "agent"]),
    ]
    out: list[str] = []
    for label, keys in pairs:
        if any(k in low for k in keys):
            out.append(label)
    return out[:6]


def ensure_min_words(base: str, fallback_sentences: list[str], *, min_words: int = 80, max_words: int = 250) -> str:
    text = normalize_space(base)
    idx = 0
    while word_count(text) < min_words and idx < len(fallback_sentences):
        text = normalize_space(text + " " + fallback_sentences[idx])
        idx += 1
    return trim_words(text, max_words)


def make_id(name: str, *, year: int | None = None, seed_ids: set[str], used_ids: set[str]) -> str:
    base = slugify(name)
    if base in seed_ids or base in used_ids or not base:
        if year:
            base = slugify(f"{name}-{year}")
        else:
            base = slugify(f"{name}-item")
    counter = 2
    original = base
    while base in seed_ids or base in used_ids:
        base = slugify(f"{original}-{counter}")
        counter += 1
    used_ids.add(base)
    return base


def ordered_record(
    *,
    rid: str,
    name: str,
    category: str,
    rtype: str,
    organization: str,
    country: str,
    year: int,
    url_primary: str,
    url_paper: str,
    url_github: str,
    description: str,
    techniques: list[str],
    input_modality: str,
    output_modality: str,
    physics_domain: str,
    industry_application: list[str],
    status: str,
) -> dict[str, Any]:
    return {
        "id": rid,
        "name": name,
        "category": category,
        "type": rtype,
        "organization": organization,
        "country": country,
        "year": year,
        "url_primary": url_primary,
        "url_paper": url_paper,
        "url_github": url_github,
        "description": description,
        "techniques": techniques,
        "input_modality": input_modality,
        "output_modality": output_modality,
        "physics_domain": physics_domain,
        "industry_application": industry_application,
        "status": status,
        "tags": ["codex-generated"],
    }


def paper_defaults_for_file(filename: str, title: str, rtype: str) -> tuple[str, str, str, str]:
    low = title.lower()
    if filename == "02-text-to-cad-academic.jsonl":
        if any(k in low for k in ["dataset", "benchmark", "sketchgraphs", "histcad"]):
            return "benchmark-dataset", "program", "program", "none"
        if any(k in low for k in ["sketch", "drawing", "orthographic"]):
            return "sketch-to-cad" if "sketch" in low else "image-to-cad", "sketch" if "sketch" in low else "image", "parametric-cad", "none"
        if any(k in low for k in ["image", "unconstrained images", "visual language"]):
            return "image-to-cad", "image", "parametric-cad", "none"
        if any(k in low for k in ["cadquery", "program", "translator", "recode"]):
            return "program-cad", "text" if "text" in low else "point-cloud", "program", "none"
        if "b-rep" in low or "brep" in low:
            return "b-rep-learning", "none", "brep", "none"
        return "text-to-cad", "text", "parametric-cad", "none"

    if filename == "03-topology-optimization.jsonl":
        return "topology-optimization", "physics-spec", "topology", detect_physics_domain(title, "structural")

    if filename == "04-neural-operators-surrogates.jsonl":
        category = "neural-operator"
        if rtype == "commercial-product":
            category = "physics-surrogate"
        return category, "physics-spec", "scalar-field", detect_physics_domain(title, "multi-physics")

    if filename == "05-generative-3d-shape.jsonl":
        if any(k in low for k in ["dataset", "objaverse", "shapenet"]):
            return "benchmark-dataset", "none", "mesh", "none"
        if "image" in low or "single image" in low or "view" in low or "wonder3d" in low:
            out = "mesh"
            if any(k in low for k in ["gaussian", "splat"]):
                out = "gaussian-splat"
            elif any(k in low for k in ["nerf", "radiance"]):
                out = "nerf"
            elif "sdf" in low:
                out = "sdf"
            return "image-to-3d", "image", out, "none"
        if "text" in low or "prompt" in low:
            out = "mesh"
            if any(k in low for k in ["gaussian", "splat"]):
                out = "gaussian-splat"
            elif any(k in low for k in ["nerf", "radiance"]):
                out = "nerf"
            elif "sdf" in low:
                out = "sdf"
            return "text-to-3d", "text", out, "none"
        return "generative-3d-shape", "none", "mesh", "none"

    if filename == "06-generative-materials.jsonl":
        if any(k in low for k in ["dataset", "materials project", "alexandria", "oc20"]):
            return "benchmark-dataset", "none", "material", "molecular"
        if any(k in low for k in ["interatomic", "potential", "schnet", "painn", "gemnet", "equiformer", "matgl", "cgcnn", "alignn"]):
            return "ml-interatomic-potential", "crystal-structure", "scalar-field", "molecular"
        return "generative-materials", "chemistry", "material", "molecular"

    if filename == "07-dfm-dfam-ai.jsonl":
        low = title.lower()
        if any(k in low for k in ["quote", "quoting", "cost"]):
            return "ml-quoting", "brep", "scalar-field", "none"
        if any(k in low for k in ["defect", "melt pool", "thermal", "roughness", "surface", "monitor"]):
            return "process-monitoring-ml", "physics-spec", "scalar-field", detect_physics_domain(title, "thermal")
        return "dfam-ai", "mesh", "process-plan", detect_physics_domain(title, "thermal")

    if filename == "08-cad-copilots-agents.jsonl":
        low = title.lower()
        if any(k in low for k in ["windchill", "teamcenter", "plm", "document vault"]):
            return "ai-plm", "text", "text", "none"
        if any(k in low for k in ["cam", "simulation"]):
            return "ai-simulation-prep", "text", "program", "none"
        if any(k in low for k in ["agent", "tool-using", "tool-augmented", "autonomous"]):
            return "cad-agent", "text", "program", "none"
        return "cad-copilot", "text", "text", "none"

    if filename == "09-generative-platforms.jsonl":
        low = title.lower()
        if any(k in low for k in ["implicit", "lattice", "metamaterial"]):
            return "implicit-modeling", "parametric", "implicit-field", "structural"
        if any(k in low for k in ["digital twin", "simulation", "physics"]):
            return "multi-disciplinary-optimization", "physics-spec", "scalar-field", "multi-physics"
        if any(k in low for k in ["topology", "generative design"]):
            return "generative-platform", "physics-spec", "topology", "structural"
        return "generative-platform", "physics-spec", "parametric-cad", "multi-physics"

    if filename == "10-pinn-differentiable.jsonl":
        if any(k in low for k in ["differentiable", "taichi", "brax", "mujoco", "sapien", "theseus", "cvxpylayers", "jax-cfd", "isaaclab", "genesis"]):
            return "differentiable-physics", "physics-spec", "scalar-field", detect_physics_domain(title, "multi-physics")
        return "physics-informed-nn", "physics-spec", "scalar-field", detect_physics_domain(title, "multi-physics")

    return "other", "none", "other", "none"


@dataclass
class ProductCandidate:
    name: str
    url: str
    organization: str
    country: str
    year: int
    category: str
    input_modality: str
    output_modality: str
    techniques: list[str]
    rtype: str = "commercial-product"
    status: str = "deployed-production"
    physics_domain: str = "none"
    industry_application: list[str] | None = None
    url_paper: str = ""
    url_github: str = ""


@dataclass
class TermCandidate:
    term: str
    category_hint: str | None = None
    type_hint: str = "academic-paper"
    search_query: str = ""
    preferred_title: str = ""
    input_hint: str | None = None
    output_hint: str | None = None
    physics_hint: str | None = None
    manual_url_primary: str = ""
    manual_url_paper: str = ""
    manual_url_github: str = ""
    manual_org: str = ""
    manual_country: str = "US"
    manual_year: int | None = None
    industry_application: list[str] | None = None


def p(
    name: str,
    url: str,
    org: str,
    country: str,
    year: int,
    category: str,
    input_modality: str,
    output_modality: str,
    techniques: list[str],
    *,
    rtype: str = "commercial-product",
    status: str = "deployed-production",
    physics_domain: str = "none",
    industry_application: list[str] | None = None,
    url_paper: str = "",
    url_github: str = "",
) -> ProductCandidate:
    return ProductCandidate(
        name=name,
        url=url,
        organization=org,
        country=country,
        year=year,
        category=category,
        input_modality=input_modality,
        output_modality=output_modality,
        techniques=techniques,
        rtype=rtype,
        status=status,
        physics_domain=physics_domain,
        industry_application=industry_application,
        url_paper=url_paper,
        url_github=url_github,
    )


def q(term: str, **kwargs: Any) -> TermCandidate:
    return TermCandidate(term=term, **kwargs)


PRODUCT_FILES: dict[str, list[ProductCandidate]] = {
    "01-text-to-cad-commercial.jsonl": [
        p("Zoo Text-to-CAD", "https://zoo.dev/text-to-cad", "Zoo", "US", 2023, "text-to-cad", "text", "brep", ["llm", "cad-agent"], status="public-preview"),
        p("Zoo Design Studio", "https://docs.zoo.dev/docs/zoo-design-studio", "Zoo", "US", 2024, "text-to-cad", "text", "parametric-cad", ["llm", "procedural-modeling"], status="deployed-production"),
        p("Text-to-CAD Blender Add-on", "https://zoo.dev/blog/text-to-cad-blender-addon", "Zoo", "US", 2024, "text-to-cad", "text", "brep", ["llm", "procedural-modeling"], status="public-preview"),
        p("AdamCAD", "https://adam.new/engineers", "Adam", "US", 2025, "text-to-cad", "text", "parametric-cad", ["llm", "cad-agent"], status="public-preview"),
        p("BuildCAD AI", "https://buildcad.ai/", "BuildCAD", "US", 2025, "text-to-cad", "text", "parametric-cad", ["llm", "cad-agent"]),
        p("Ragnar", "https://ragnar.build/", "Ragnar", "US", 2025, "text-to-cad", "text", "brep", ["llm", "brep-modeling"]),
        p("LuminiCAD", "https://www.luminicad.com/", "LuminiCAD", "US", 2025, "text-to-cad", "text", "parametric-cad", ["llm"]),
        p("Dzine Text to CAD AI", "https://www.dzine.ai/tools/text-to-cad-ai/", "Dzine", "US", 2025, "text-to-cad", "text", "parametric-cad", ["llm", "multimodal"]),
        p("Vizcom", "https://www.vizcom.ai/", "Vizcom", "US", 2022, "sketch-to-cad", "sketch", "mesh", ["multimodal", "design-assist"]),
        p("Sloyd", "https://www.sloyd.ai/", "Sloyd", "SE", 2021, "generative-3d-shape", "text", "mesh", ["procedural-modeling", "llm"]),
        p("Hyper3D Rodin", "https://hyper3d.ai/rodin", "Deemos Tech", "SG", 2025, "image-to-3d", "image", "mesh", ["multimodal", "gaussian-splatting"]),
        p("Kaedim", "https://www.kaedim3d.com/", "Kaedim", "GB", 2022, "image-to-3d", "image", "mesh", ["neural-reconstruction"]),
        p("Alpha3D", "https://www.alpha3d.io/kb/generate-3d/3d-generation/", "Alpha3D", "LT", 2023, "image-to-3d", "image", "mesh", ["3d-generation"]),
        p("Alpha3D 2D Drawing to 3D", "https://www.alpha3d.io/kb/generate-3d/2d-drawing-to-3d-model/", "Alpha3D", "LT", 2025, "image-to-3d", "image", "mesh", ["3d-generation", "multimodal"]),
        p("Alpha3D Game Asset Generation", "https://www.alpha3d.io/kb/generate-3d/3d-generation/", "Alpha3D", "LT", 2025, "text-to-3d", "text", "mesh", ["3d-generation", "multimodal"]),
        p("Neural4D", "https://www.neural4d.com/features/text-to-3d-model", "DreamTech AI", "CN", 2025, "text-to-3d", "text", "mesh", ["3d-generation", "multimodal"]),
        p("Triverse AI", "https://triverse.ai/", "Triverse AI", "US", 2026, "text-to-3d", "text", "mesh", ["3d-generation", "multimodal"]),
        p("Lychee Gen", "https://lychee.co/whats-new/introducing-lychee-gen", "Lychee", "FR", 2025, "text-to-3d", "text", "mesh", ["3d-generation"]),
        p("Hitem3D", "https://www.hitem3d.ai/3dmodeling/home", "Math Magic", "CN", 2025, "image-to-3d", "image", "mesh", ["3d-generation", "multimodal"]),
        p("Tridi", "https://tridi.ai/", "Tridi", "US", 2025, "image-to-3d", "image", "mesh", ["3d-generation"]),
        p("To3D AI", "https://to3d.ai/", "To3D", "US", 2026, "text-to-3d", "text", "mesh", ["3d-generation"]),
        p("Z3D", "https://www.z3d.ai/en", "Z3D", "US", 2025, "text-to-3d", "text", "mesh", ["3d-generation"]),
        p("Luma Genie", "https://www.luma-ai.com/text-to-3d/", "Luma AI", "US", 2023, "text-to-3d", "text", "mesh", ["diffusion-model", "neural-rendering"]),
        p("Shapr3D AI", "https://www.shapr3d.com/ai-approach", "Shapr3D", "GB", 2025, "cad-copilot", "text", "text", ["llm", "multimodal"]),
        p("Backflip AI", "https://www.backflip.ai/", "Backflip", "US", 2025, "image-to-cad", "point-cloud", "parametric-cad", ["neural-reconstruction"]),
        p("Backflip Onshape Plugin", "https://www.backflip.ai/", "Backflip", "US", 2025, "image-to-cad", "point-cloud", "parametric-cad", ["neural-reconstruction", "cad-copilot"]),
        p("Polycam AI 3D Model Generator", "https://poly.cam/", "Polycam", "US", 2024, "image-to-3d", "image", "mesh", ["photogrammetry", "3d-generation"]),
        p("Spline AI 3D Generation", "https://spline.design/ai?via=aitoolzs", "Spline", "US", 2024, "text-to-3d", "text", "mesh", ["multimodal", "3d-generation"]),
        p("Masterpiece X Generate", "https://masterpiecex.com/blog/introducing-masterpiece-x-generate", "Masterpiece Studio", "CA", 2025, "text-to-3d", "text", "mesh", ["3d-generation"]),
        p("Womp Primfusion", "https://womp.com/primfusion", "Womp", "US", 2025, "image-to-3d", "image", "mesh", ["procedural-modeling", "multimodal"]),
        p("Promethean AI World Building", "https://www.prometheanai.com/ai-world-building", "Promethean AI", "US", 2019, "generative-3d-shape", "text", "mesh", ["llm", "asset-reasoning"]),
        p("Layer 3D AI Models", "https://www.layer.ai/models/3d", "Layer", "US", 2025, "generative-3d-shape", "text", "mesh", ["model-routing", "multimodal"]),
        p("3DFY Prompt", "https://www.prnewswire.com/news-releases/generative-ai-creates-3d-models-that-professionals-can-actually-use-3dfyai-launches-3dfy-prompt-a-text-to-3d-model-generator-301838611.html", "3DFY.ai", "IL", 2023, "text-to-3d", "text", "mesh", ["3d-generation"]),
        p("NeuroCAD", "https://neurocad.eu/", "NeuroCAD", "NL", 2026, "text-to-cad", "text", "parametric-cad", ["implicit-function", "llm"]),
    ],
    "03-topology-optimization.jsonl": [
        p("Solid Edge Generative Design Topology", "https://solidedge.siemens.com/en/solutions/products/3d-design/next-generation-design/generative-design/", "Siemens Digital Industries Software", "DE", 2017, "topology-optimization", "physics-spec", "topology", ["topology-optimization", "generative-design"], physics_domain="structural"),
        p("NX Generative Design Topology", "https://www.siemens.com/en-us/technology/generative-design/", "Siemens Digital Industries Software", "DE", 2017, "topology-optimization", "physics-spec", "topology", ["topology-optimization", "generative-design"], physics_domain="structural"),
        p("Creo Generative Design Topology", "https://www.ptc.com/en/about/facts/creo", "PTC", "US", 2023, "topology-optimization", "physics-spec", "topology", ["topology-optimization", "generative-design"], physics_domain="structural"),
        p("CATIA Performance-Driven Generative Design", "https://www.3ds.com/products/catia/ai-driven-generative-experiences", "Dassault Systemes", "FR", 2023, "topology-optimization", "physics-spec", "topology", ["topology-optimization", "generative-design"], physics_domain="structural"),
        p("Frustum TrueSOLID Generative Design", "https://www.siemens.com/en-us/technology/generative-design/", "Frustum", "US", 2017, "topology-optimization", "physics-spec", "topology", ["topology-optimization"], physics_domain="structural"),
        p("Rafinex Möbius Robust Design", "https://rafinex.com/tag/generative-design/", "Rafinex", "PL", 2025, "topology-optimization", "physics-spec", "topology", ["topology-optimization", "stochastic-optimization"], physics_domain="structural"),
        p("Generate Timber Optioneering", "https://generate.design/", "Generate", "US", 2025, "topology-optimization", "physics-spec", "parametric-cad", ["generative-design", "design-space-exploration"], physics_domain="structural"),
    ],
    "06-generative-materials.jsonl": [
        p("SevenNet", "https://github.com/MDIL-SNU/SevenNet", "Seoul National University", "KR", 2024, "ml-interatomic-potential", "atomic-structure", "scalar-field", ["mlip", "equivariant-gnn"], rtype="open-source", status="open-source-tool", physics_domain="molecular"),
        p("Citrine Informatics", "https://citrine.io/", "Citrine Informatics", "US", 2013, "generative-materials", "materials-spec", "scalar-field", ["materials-ai", "optimization"], physics_domain="molecular"),
        p("Schrödinger Materials Science", "https://www.schrodinger.com/materials-science/use-cases/materials-engineering/", "Schrödinger", "US", 2024, "generative-materials", "materials-spec", "scalar-field", ["simulation-driven-design", "materials-ai"], physics_domain="molecular"),
        p("A-Lab", "https://www.nature.com/articles/s41586-023-06734-w", "Lawrence Berkeley National Laboratory", "US", 2023, "generative-materials", "materials-spec", "crystal-structure", ["robotics", "inverse-design"], rtype="research-project", status="research-prototype", physics_domain="molecular"),
        p("Polybot", "https://www.nature.com/articles/s41467-024-55655-3", "Argonne National Laboratory", "US", 2024, "generative-materials", "materials-spec", "process-plan", ["bayesian-optimization", "robotics"], rtype="research-project", status="research-prototype", physics_domain="molecular"),
        p("Alexandria Materials Database", "https://alexandria.icams.rub.de/", "Ruhr University Bochum", "DE", 2024, "benchmark-dataset", "materials-spec", "crystal-dataset", ["materials-database"], rtype="benchmark-dataset", status="open-source-tool", physics_domain="molecular"),
    ],
    "07-dfm-dfam-ai.jsonl": [
        p("Materialise Magics", "https://www.materialise.com/en/software/magics", "Materialise", "BE", 1994, "dfam-ai", "mesh", "process-plan", ["support-generation", "build-preparation"], physics_domain="thermal"),
        p("Aibuild", "https://ai-build.com/applications/", "Aibuild", "GB", 2018, "dfam-ai", "mesh", "toolpath", ["toolpath-optimization", "robotics"]),
        p("Authentise FlowsAM", "https://www.authentise.com/additive", "Authentise", "US", 2018, "dfam-ai", "brep", "process-plan", ["workflow-automation", "manufacturing-execution"]),
        p("Senvol", "https://senvol.com/", "Senvol", "US", 2014, "process-monitoring-ml", "physics-spec", "scalar-field", ["machine-learning", "materials-database"], physics_domain="thermal"),
        p("Inkbit Vista", "https://inkbit3d.com/press-release-inkbit-launches-inkbit-vista-a-new-additive-manufacturing-system-that-revolutionizes-3d-printing/", "Inkbit", "US", 2021, "process-monitoring-ml", "mesh", "scalar-field", ["machine-vision", "feedback-control"], physics_domain="thermal"),
        p("Physna", "https://physna.com/", "Physna", "US", 2019, "dfm-ai", "mesh", "scalar-field", ["shape-search", "geometric-features"]),
        p("Protolabs", "https://www.protolabs.com/", "Protolabs", "US", 1999, "ml-quoting", "brep", "scalar-field", ["ml-cost-prediction", "dfm-analysis"]),
        p("Fictiv Materials.AI", "https://www.fictiv.com/our-platform", "Fictiv", "US", 2023, "ml-quoting", "brep", "scalar-field", ["materials-ai", "quote-automation"]),
        p("Hubs Instant Quote", "https://www.hubs.com/", "Hubs", "NL", 2013, "ml-quoting", "brep", "scalar-field", ["instant-quoting", "dfm-analysis"]),
        p("RapidDirect DFM Analysis", "https://www.rapiddirect.com/", "RapidDirect", "CN", 2019, "ml-quoting", "brep", "scalar-field", ["dfm-analysis", "quote-automation"]),
        p("Velo3D Flow", "https://velo3d.com/", "Velo3D", "US", 2023, "dfam-ai", "mesh", "process-plan", ["build-preparation", "process-optimization"], physics_domain="thermal"),
        p("AON3D Basis", "https://www.aon3d.com/software/basis/", "AON3D", "CA", 2024, "process-monitoring-ml", "mesh", "scalar-field", ["process-simulation", "machine-learning"], physics_domain="thermal"),
        p("Oqton 3DXpert", "https://www.oqton.com/", "Oqton", "US", 2021, "dfam-ai", "mesh", "process-plan", ["build-preparation", "additive-workflow"]),
        p("GE AddWorks", "https://go.additive.ge.com/rs/706-JIU-273/images/GE_Addworks_Brochure_US_Digital.pdf", "GE Additive", "US", 2016, "dfam-ai", "mesh", "process-plan", ["design-services", "dfam"]),
        p("CloudNC CAM Assist", "https://www.cloudnc.com/cam-assist", "CloudNC", "GB", 2023, "dfm-ai", "brep", "program", ["feature-recognition", "cam-automation"]),
        p("CloudNC Soft Jaw Designer", "https://www.cloudnc.com/softjaw-designer", "CloudNC", "GB", 2024, "dfm-ai", "brep", "parametric-cad", ["fixture-generation", "cad-automation"]),
    ],
    "08-cad-copilots-agents.jsonl": [
        p("Zookeeper", "https://docs.zoo.dev/docs/zoo-design-studio/text-to-cad", "Zoo", "US", 2026, "cad-agent", "text", "program", ["llm", "tool-calling"]),
        p("Raven", "https://www.raven.build", "Raven", "US", 2025, "cad-agent", "text", "parametric-cad", ["llm", "agent"]),
        p("gNucleus", "https://gnucleus.ai/", "gNucleus", "US", 2026, "cad-agent", "text", "parametric-cad", ["llm", "multimodal"]),
        p("CADABRA", "https://cadabrai.com/", "CADABRA", "US", 2026, "cad-copilot", "text", "parametric-cad", ["llm", "workflow-automation"]),
        p("Adam Copilot", "https://adam.new/", "Adam", "US", 2025, "cad-copilot", "text", "mesh", ["llm", "cad-agent"], status="public-preview"),
        p("Autodesk Assistant", "https://www.autodesk.com/solutions/autodesk-ai/autodesk-assistant", "Autodesk", "US", 2025, "cad-copilot", "text", "text", ["llm", "retrieval"]),
        p("Autodesk Assistant in Forma", "https://www.autodesk.com/blogs/construction/meet-autodesk-assistant-ai-native-intelligence-in-forma/", "Autodesk", "US", 2026, "cad-copilot", "text", "text", ["llm", "retrieval"], status="deployed-production"),
        p("Autodesk Fusion AI Automation", "https://www.autodesk.com/products/fusion-360/ai-automation", "Autodesk", "US", 2026, "cad-copilot", "text", "program", ["llm", "tool-calling"]),
        p("Designcenter NX CAD AI", "https://plm.sw.siemens.com/en-US/nx/cad-online/ai/", "Siemens Digital Industries Software", "DE", 2025, "cad-copilot", "text", "text", ["llm", "design-assist"]),
        p("NX CAM AI Copilot", "https://blogs.sw.siemens.com/nx-manufacturing/engineering-com-spotlights-siemens-ai-copilot-a-new-era-of-cam-programming/", "Siemens Digital Industries Software", "DE", 2025, "ai-simulation-prep", "text", "program", ["llm", "cam-automation"]),
        p("Teamcenter Assistant", "https://blogs.sw.siemens.com/teamcenter/teamcenter-assistant-an-artificial-intelligence-application/", "Siemens Digital Industries Software", "DE", 2020, "ai-plm", "text", "text", ["machine-learning", "command-prediction"]),
        p("Windchill AI", "https://www.ptc.com/en/products/windchill/windchill-ai", "PTC", "US", 2025, "ai-plm", "text", "text", ["llm", "agent"]),
        p("Onshape AI Advisor", "https://www.onshape.com/en/features/ai-advisor", "PTC", "US", 2025, "cad-copilot", "text", "text", ["llm", "retrieval"]),
        p("IronCAD AI Chatbot", "https://www.ironcad.com/blog/ironcads-ai-chatbot/", "IronCAD", "US", 2025, "cad-copilot", "text", "text", ["llm", "retrieval"]),
        p("ARES AI Assist", "https://www.graebert.com/us/blog/general-news/introducing-ares-ai-assist-a3-your-personal-cad-assistant/", "Graebert", "DE", 2024, "cad-copilot", "text", "text", ["llm", "retrieval"]),
        p("BricsCAD AI", "https://www.bricsys.com/en-eu/cad-software/cad-ai-software", "Bricsys", "BE", 2023, "cad-copilot", "text", "text", ["machine-learning", "design-assist"]),
        p("ZWCAD AI Tools", "https://www.zwsoft.com/product/zwcad?hsa_acc=505552588&hsa_ad=283943143&hsa_cam=620150924&hsa_grp=276663103&hsa_net=linkedin&hsa_ver=3&trk=test", "ZWSOFT", "CN", 2025, "cad-copilot", "text", "text", ["machine-learning", "parametric-design"]),
        p("Vectorworks AI Assistant", "https://www.vectorworks.net/en-US/ai-assistant", "Vectorworks", "US", 2025, "cad-copilot", "text", "text", ["llm", "retrieval"]),
        p("ELECTRIX AI", "https://www.wscad.com/us/electrix/", "WSCAD", "DE", 2026, "cad-copilot", "text", "text", ["llm", "electrical-cad"]),
        p("SOLIDWORKS AI CAD Tools", "https://www.solidworks.com/solution/solidworks-ai-cad-tools-workflow-optimization", "Dassault Systemes", "FR", 2025, "cad-copilot", "text", "parametric-cad", ["machine-learning", "design-assist"]),
        p("CoLab AutoReview", "https://www.colabsoftware.com/", "CoLab Software", "CA", 2024, "cad-copilot", "text", "text", ["review-automation", "llm"]),
        p("Duro", "https://durolabs.co/", "Duro Labs", "US", 2025, "ai-plm", "text", "text", ["llm", "retrieval"], status="deployed-production"),
    ],
    "09-generative-platforms.jsonl": [
        p("Generate", "https://generate.design/", "Generate", "US", 2025, "generative-platform", "physics-spec", "parametric-cad", ["design-space-exploration", "cost-optimization"], physics_domain="structural"),
        p("InfinitForm", "https://infinitform.com/platform/", "InfinitForm", "US", 2025, "generative-platform", "physics-spec", "parametric-cad", ["multi-disciplinary-optimization", "llm"], physics_domain="multi-physics"),
        p("Cognitive Design 2.0", "https://www.cognitive-design-systems.com/news/cognitive-design-2-0-a-new-software-release-to-accelerate-design-exploration-for-high-performance-part-engineering", "Cognitive Design Systems", "FR", 2025, "generative-platform", "physics-spec", "parametric-cad", ["generative-design", "simulation-driven-design"], physics_domain="structural"),
        p("Akselos RB-FEA Technology", "https://support.akselos.com/support/solutions/articles/1000330724-overview-of-akselos-rb-fea-technology", "Akselos", "CH", 2025, "multi-disciplinary-optimization", "physics-spec", "scalar-field", ["reduced-order-modeling", "digital-twin"], physics_domain="structural"),
        p("Neural Concept Platform", "https://www.neuralconcept.com/platform", "Neural Concept", "CH", 2025, "generative-platform", "physics-spec", "scalar-field", ["surrogate-modeling", "design-copilot"], physics_domain="multi-physics"),
        p("Neural Concept AI Design Copilot", "https://www.neuralconcept.com/post/neural-concept-introduces-a-physics--and-geometry-aware-ai-design-copilot-extending-its-established-engineering-ai-platform", "Neural Concept", "CH", 2026, "generative-platform", "physics-spec", "parametric-cad", ["llm", "surrogate-modeling"], physics_domain="multi-physics"),
        p("Monolith Core Platform", "https://www.monolithai.com/products/core-platform", "Monolith", "GB", 2024, "multi-disciplinary-optimization", "physics-spec", "scalar-field", ["surrogate-modeling", "test-data-learning"], physics_domain="multi-physics"),
        p("PhysicsX Platform", "https://www.physicsx.ai/platform", "PhysicsX", "GB", 2025, "multi-disciplinary-optimization", "physics-spec", "scalar-field", ["physics-ai", "foundation-model-physics"], physics_domain="multi-physics"),
        p("PhysicsX Engineering Platform", "https://www.physicsx.ai/newsroom/engineering-in-the-age-of-physics-ai-the-platform-driving-the-shift", "PhysicsX", "GB", 2026, "multi-disciplinary-optimization", "physics-spec", "scalar-field", ["physics-ai", "foundation-model-physics"], physics_domain="multi-physics"),
        p("Akselos Digital Twins Guide", "https://akselos.com/digital-twins-a-comprehensive-guide/", "Akselos", "CH", 2022, "multi-disciplinary-optimization", "physics-spec", "scalar-field", ["digital-twin", "physics-ai"], physics_domain="structural"),
        p("Rescale Platform Experience", "https://rescale.com/blog/new-platform-experience/", "Rescale", "US", 2026, "multi-disciplinary-optimization", "physics-spec", "scalar-field", ["agentic-workflows", "engineering-ai"], physics_domain="multi-physics"),
        p("Rescale AI Physics", "https://rescale.com/platform/ai-physics/", "Rescale", "US", 2025, "multi-disciplinary-optimization", "physics-spec", "scalar-field", ["cloud-hpc", "engineering-ai"], physics_domain="multi-physics"),
        p("Luminary Cloud Platform", "https://luminary.ai/platform", "Luminary Cloud", "US", 2025, "multi-disciplinary-optimization", "physics-spec", "scalar-field", ["physics-ai", "surrogate-modeling"], physics_domain="multi-physics"),
        p("Lumi AI", "https://luminary.ai/resources/luminary-cloud-emerges-from-stealth-empowering-rd-with-realtime-engineering/", "Luminary Cloud", "US", 2024, "generative-platform", "physics-spec", "text", ["llm", "physics-ai"], physics_domain="multi-physics"),
        p("BeyondMath", "https://beyondmath.com/technology", "BeyondMath", "GB", 2025, "generative-platform", "physics-spec", "scalar-field", ["foundation-model-physics", "surrogate-modeling"], physics_domain="multi-physics"),
        p("Rescale AI Physics Powered by NVIDIA", "https://rescale.com/platform/ai-physics-powered-by-nvidia/", "Rescale", "US", 2025, "multi-disciplinary-optimization", "physics-spec", "scalar-field", ["foundation-model-physics", "surrogate-modeling"], physics_domain="multi-physics"),
        p("Hyperganic HyDesign", "https://www.hyperganic.com/solutions/metamaterials/", "Hyperganic", "DE", 2020, "implicit-modeling", "parametric", "implicit-field", ["implicit-modeling", "lattice-generation"], physics_domain="structural"),
        p("Solid Edge Generative Design", "https://solidedge.siemens.com/en/solutions/products/3d-design/next-generation-design/generative-design/", "Siemens Digital Industries Software", "DE", 2017, "generative-platform", "physics-spec", "topology", ["topology-optimization", "generative-design"], physics_domain="structural"),
        p("NX Generative Design", "https://www.siemens.com/en-us/technology/generative-design/", "Siemens Digital Industries Software", "DE", 2017, "generative-platform", "physics-spec", "topology", ["topology-optimization", "generative-design"], physics_domain="structural"),
        p("Simcenter Studio", "https://www.siemens.com/en-us/products/simcenter/integration-solutions/studio/", "Siemens Digital Industries Software", "DE", 2025, "generative-platform", "physics-spec", "scalar-field", ["reinforcement-learning", "system-optimization"], physics_domain="multi-physics"),
        p("Creo Generative Design", "https://www.ptc.com/en/about/facts/creo", "PTC", "US", 2023, "generative-platform", "physics-spec", "topology", ["generative-design", "simulation-driven-design"], physics_domain="structural"),
        p("CATIA AI-Driven Generative Experiences", "https://www.3ds.com/products/catia/ai-driven-generative-experiences", "Dassault Systemes", "FR", 2023, "generative-platform", "physics-spec", "topology", ["generative-design", "topology-optimization"], physics_domain="structural"),
        p("3DEXPERIENCE Generative Design", "https://www.3ds.com/products/catia/generative-experience", "Dassault Systemes", "FR", 2021, "generative-platform", "physics-spec", "topology", ["generative-design", "topology-optimization"], physics_domain="structural"),
        p("Frustum TrueSOLID", "https://www.siemens.com/en-us/technology/generative-design/", "Frustum", "US", 2017, "generative-platform", "physics-spec", "topology", ["topology-optimization"]),
        p("Rafinex Möbius", "https://rafinex.com/tag/generative-design/", "Rafinex", "PL", 2025, "generative-platform", "physics-spec", "topology", ["stochastic-optimization", "robust-design"], physics_domain="structural"),
        p("Ansys SimAI", "https://www.ansys.com/en-gb/news-center/press-releases/1-9-24-ansys-launches-simai", "Ansys", "US", 2024, "multi-disciplinary-optimization", "mesh", "scalar-field", ["surrogate-modeling", "cloud-simulation"], physics_domain="multi-physics"),
        p("SimScale AI Infrastructure", "https://www.simscale.com/product/ai-infrastructure/", "SimScale", "DE", 2024, "multi-disciplinary-optimization", "physics-spec", "scalar-field", ["agentic-workflows", "engineering-ai"], physics_domain="multi-physics"),
        p("SimScale Platform", "https://www.simscale.com/", "SimScale", "DE", 2012, "multi-disciplinary-optimization", "physics-spec", "scalar-field", ["cloud-simulation", "engineering-ai"], physics_domain="multi-physics"),
    ],
    "10-pinn-differentiable.jsonl": [
        p("JAX-CFD", "https://github.com/google/jax-cfd", "Google", "US", 2021, "differentiable-physics", "physics-spec", "scalar-field", ["differentiable-programming", "cfd"], rtype="open-source", status="open-source-tool", physics_domain="fluid"),
        p("Tiny Differentiable Simulator", "https://github.com/erwincoumans/tiny-differentiable-simulator", "Google Research", "US", 2021, "differentiable-physics", "physics-spec", "scalar-field", ["differentiable-programming", "rigid-body-dynamics"], rtype="open-source", status="open-source-tool", physics_domain="multi-physics"),
        p("Genesis", "https://genesis-embodied-ai.github.io/", "Genesis Embodied AI", "US", 2024, "differentiable-physics", "physics-spec", "scalar-field", ["simulation", "robotics"], rtype="open-source", status="open-source-tool", physics_domain="multi-physics"),
        p("SAPIEN", "https://sapien.ucsd.edu/", "UC San Diego", "US", 2020, "differentiable-physics", "physics-spec", "scalar-field", ["robotics", "simulation"], rtype="open-source", status="open-source-tool", physics_domain="multi-physics"),
        p("Isaac Lab", "https://developer.nvidia.com/isaac/lab", "NVIDIA", "US", 2024, "differentiable-physics", "physics-spec", "scalar-field", ["robotics", "simulation"], rtype="open-source", status="open-source-tool", physics_domain="multi-physics"),
        p("MuJoCo MPC", "https://github.com/google-deepmind/mujoco_mpc", "Google DeepMind", "GB", 2024, "differentiable-physics", "physics-spec", "scalar-field", ["model-predictive-control", "simulation"], rtype="open-source", status="open-source-tool", physics_domain="multi-physics"),
        p("CVXPYLayers", "https://github.com/cvxgrp/cvxpylayers", "Stanford University", "US", 2021, "differentiable-physics", "physics-spec", "scalar-field", ["differentiable-optimization"], rtype="open-source", status="open-source-tool", physics_domain="multi-physics"),
    ],
}


TERM_FILES: dict[str, list[TermCandidate]] = {
    "02-text-to-cad-academic.jsonl": [
        q("Free2CAD"),
        q("Hierarchical Neural Coding for Controllable CAD Model Generation"),
        q("BrepGen: A B-rep Generative Diffusion Model with Structured Latent Geometry"),
        q("ComplexGen: CAD Reconstruction by B-Rep Chain Complex Generation"),
        q("SolidGen: An Autoregressive Model for Direct B-rep Synthesis"),
        q("CAD-GPT: Synthesising CAD Construction Sequence with Spatial Reasoning-Enhanced Multimodal LLMs"),
        q("OpenECAD: An efficient visual language model for editable 3D-CAD design"),
        q("CAD-Llama: Leveraging Large Language Models for Computer-Aided Design Parametric 3D Model Generation"),
        q("SketchGraphs: A Large-Scale Dataset for Modeling Relational Geometry in Computer-Aided Design"),
        q("CAPRI-Net: Learning Compact CAD Shapes with Adaptive Primitive Assembly"),
        q("Text2CAD: Generating Sequential CAD Models from Beginner-to-Expert Level Text Prompts"),
        q("Text2CAD: Text to 3D CAD Generation via Technical Drawings"),
        q("SketchGen: Generating Constrained CAD Sketches"),
        q("CADFusion: Text-to-CAD Generation Through Infusing Visual Feedback in LLMs"),
        q("Text-to-CadQuery: A New Paradigm for CAD Generation with Scalable Large Model Capabilities"),
        q("Drawing2CAD: Sequence-to-Sequence Learning for CAD Generation from Vector Drawings"),
        q("NURBGen: High-Fidelity Text-to-CAD Generation through LLM-Driven NURBS Modeling"),
        q("CadVLM: Bridging Language and Vision in the Generation of Parametric CAD Sketches"),
        q("AutoBrep: Autoregressive B-Rep Generation with Unified Topology and Geometry"),
        q("CAD Translator: An Effective Drive for Text to 3D Parametric Computer-Aided Design Generative Modeling"),
        q("CADTrans: A code tree-guided CAD generative transformer model with regularized discrete codebooks"),
        q("Brep2Seq: a dataset and hierarchical deep learning network for reconstruction and generation of computer-aided design models"),
        q("Revisiting CAD Model Generation by Learning Raster Sketch"),
        q("Automatic 3D CAD models reconstruction from 2D orthographic drawings"),
        q("CADCrafter: Generating Computer-Aided Design Models from Unconstrained Images"),
        q("TOOLCAD: Exploring Tool-Using Large Language Models in Text-to-CAD Generation with Reinforcement Learning"),
        q("CAD-Assistant: Tool-Augmented VLLMs as Generic CAD Task Solvers"),
        q("CADDesigner: Conceptual Design of CAD Models Based on General-Purpose Agent"),
        q("From Text to Design: A Framework to Leverage LLM Agents for Automated CAD Generation"),
        q("CADTalk: An Algorithm and Benchmark for Semantic Commenting of CAD Programs"),
        q("JoinABLe: Learning Bottom-up Assembly of Parametric CAD Joints"),
        q("Point2CAD"),
        q("Img2CAD: Conditioned 3D CAD Model Generation From Single Image With Structured Visual Geometry"),
        q("CADParser"),
        q("CAD-Recode: Reverse Engineering CAD Code from Point Clouds"),
        q("CSG-Stump: A Learning Friendly CSG-Like Representation for Interpretable Shape Parsing"),
        q("ExtrudeNet: Unsupervised Inverse Sketch-and-Extrude for Shape Parsing"),
        q("SECAD-Net"),
        q("Sketch2CAD"),
        q("GenCAD: Image-Conditioned Computer-Aided Design Generation with Transformer-Based Contrastive Representation and Diffusion Priors"),
        q("GenCAD-3D: CAD Program Generation using Multimodal Latent Space Alignment and Synthetic Dataset Balancing"),
        q("A parametric and feature-based CAD dataset to support human-computer interaction for advanced 3D shape learning"),
        q("HistCAD: Geometrically Constrained Parametric History-based CAD Dataset", type_hint="benchmark-dataset"),
    ],
    "03-topology-optimization.jsonl": [
        q("Neural Network Topology Optimization"),
        q("Topology Optimization Using Convolutional Neural Network"),
        q("A topology description function-enhanced neural network for topology optimization"),
        q("Robust topology optimization using efficient neural network surrogates"),
        q("Multiscale topology optimization using neural network surrogate models"),
        q("Multi-stage deep neural network accelerated topology optimization"),
        q("Density Topology Optimization Method Based on Neural Network"),
        q("Topology Optimization using Deep Learning"),
        q("Topology Optimization Accelerated by Deep Learning"),
        q("Deep learning frameworks for structural topology optimization"),
        q("Structural topology optimization based on deep learning"),
        q("Enhancing topology optimization with adaptive deep learning"),
        q("Isogeometric Topology Optimization Based on Deep Learning"),
        q("Stress-based topology optimization method using deep learning"),
        q("Accelerated topology optimization by means of deep learning"),
        q("Universal Machine Learning for Topology Optimization"),
        q("Sketch driven machine-learning based topology optimization"),
        q("Machine Learning-Based Topology Optimization in 3D Printing"),
        q("Self-directed online machine learning for topology optimization"),
        q("Deep Generative Design: Integration of Topology Optimization and Generative Models"),
        q("Generative Design by Embedding Topology Optimization into Conditional Generative Adversarial Network"),
        q("Topology Optimization Integrated Deep Learning for Multiphysics Problems"),
        q("Multiphysics Deep Learning for Topology Optimization of Permanent Magnet Motor"),
        q("Novel Artificial Neural Network Aided Structural Topology Optimization"),
        q("Data-driven topology optimization using a multitask conditional variational autoencoder with persistent homology"),
        q("Topology Optimization Via Implicit Neural Representations"),
        q("TOuNN: Topology Optimization using Neural Networks"),
        q("Topology optimization approach using a training-dataset-free neural network reparameterization framework"),
        q("Reinforcement learning-based topology optimization for generative designed lightweight structures"),
        q("Generalized topology optimization through hierarchical reinforcement learning"),
        q("Deep learning for topology optimization of 2D metamaterials"),
        q("Transfer Learning Through Deep Learning: Application to Topology Optimization of Electric Motor"),
        q("Deep learning aided topology optimization of phononic crystals"),
        q("NTopo: Mesh-free Topology Optimization using Implicit Neural Representations"),
        q("NITO: Neural Implicit Fields for Resolution-free Topology Optimization"),
        q("Generative Design by Using Exploration Approaches of Reinforcement Learning in Density-Based Structural Topology Optimization"),
        q("Reinforcement Learning for Topology Optimization of a Synchronous Reluctance Motor"),
    ],
    "05-generative-3d-shape.jsonl": [
        q("Wonder3D"),
        q("Zero-1-to-3"),
        q("Zero123++"),
        q("MVDiffusion: Enabling Holistic Multi-view Image Generation with Correspondence-Aware Diffusion"),
        q("SyncDreamer: Generating Multiview-consistent Images from a Single-view Image"),
        q("One-2-3-45"),
        q("One-2-3-45++"),
        q("SplatSDF"),
        q("GaussianObject: High-Quality 3D Object Reconstruction from Four Views with Gaussian Splatting"),
        q("LGM: Large Multi-View Gaussian Model for High-Resolution 3D Content Creation", search_query="Large Multiview Gaussian Model for High-Resolution 3D Content Creation"),
        q("Splatter Image: Ultra-Fast Single-View 3D Reconstruction"),
        q("CRM: Single Image to 3D Textured Mesh with Convolutional Reconstruction Model"),
        q("LRM: Large Reconstruction Model for Single Image to 3D", manual_url_github="https://github.com/3DTopia/OpenLRM"),
        q("Objaverse", type_hint="benchmark-dataset"),
        q("ShapeNet: An Information-Rich 3D Model Repository", type_hint="benchmark-dataset"),
        q("3D Gaussian Splatting for Real-Time Radiance Field Rendering"),
        q("Text-to-3D using Gaussian Splatting"),
        q("LucidDreamer"),
        q("SceneWiz3D"),
        q("MeshAnything"),
        q("EdgeRunner: Auto-regressive Auto-encoder for Artistic Mesh Generation"),
        q("Hi3D: Pursuing High-Resolution Image-to-3D Generation with Video Diffusion Models"),
        q("Direct3D: Scalable Image-to-3D Generation via 3D Latent Diffusion Transformer"),
        q("ProlificDreamer: High-Fidelity and Diverse Text-to-3D Generation with Variational Score Distillation"),
        q("Latent-NeRF for Shape-Guided Generation of 3D Shapes and Textures"),
        q("LION: Latent Point Diffusion Models for 3D Shape Generation"),
        q("TextMesh: Generation of Realistic 3D Meshes From Text Prompts"),
        q("Text2Tex: Text-driven Texture Synthesis via Diffusion Models"),
        q("HumanGaussian: Text-Driven 3D Human Generation with Gaussian Splatting"),
        q("DreamScene360: Unconstrained Text-to-3D Scene Generation with Panoramic Gaussian Splatting"),
        q("DreamGaussian"),
        q("Michelangelo: Conditional 3D Shape Generation based on Shape-Image-Text Aligned Latent Representation"),
        q("CraftsMan3D"),
        q("Hunyuan3D 1.0"),
        q("CLAY: A Controllable Large-scale Generative Model for Creating High-quality 3D Assets"),
        q("AssetFormer: Modular 3D Assets Generation with Autoregressive Transformer"),
        q("MVDream"),
    ],
    "06-generative-materials.jsonl": [
        q("Crystal Diffusion Variational Autoencoder for Periodic Material Generation"),
        q("Scalable Diffusion for Materials Generation"),
        q("FlowMM: Generating Materials with Riemannian Flow Matching"),
        q("Equivariant Diffusion for Crystal Structure Prediction"),
        q("MatterSim: A Deep Learning Atomistic Model Across Elements, Temperatures and Pressures"),
        q("A foundation model for atomistic materials chemistry"),
        q("OrbNet: Deep Learning for Quantum Chemistry using Symmetry-Adapted Atomic-Orbital Features"),
        q("GemNet: Universal Directional Graph Neural Networks for Molecules"),
        q("GemNet-OC: Developing Graph Neural Networks for Large and Diverse Molecular Simulation Datasets"),
        q("SchNet – A deep learning architecture for molecules and materials"),
        q("Equivariant message passing for the prediction of tensorial properties and molecular spectra"),
        q("Equiformer: Equivariant Graph Attention Transformer for 3D Atomistic Graphs"),
        q("EquiformerV2: Improved Equivariant Transformer for Scaling to Higher-Degree Representations"),
        q("Directional Message Passing for Molecular Graphs"),
        q("Fast and Uncertainty-Aware Directional Message Passing for Non-Equilibrium Molecules"),
        q("Materials Graph Library (MatGL), an open-source graph deep learning library for materials science and chemistry", type_hint="open-source"),
        q("Periodic Graph Transformers for Crystal Material Property Prediction"),
        q("Atomistic Line Graph Neural Network for improved materials property predictions"),
        q("Graph convolutional neural networks with global attention for improved materials property prediction"),
        q("Graph Networks as a Universal Machine Learning Framework for Molecules and Crystals"),
        q("Crystal Graph Convolutional Neural Networks for an Accurate and Interpretable Prediction of Material Properties"),
        q("CrabNet for Explainable Deep Learning in Materials Science: Bridging the Gap Between Academia and Industry"),
        q("Rapid Discovery of Stable Materials by Coordinate-free Coarse Graining"),
        q("A multi-modal pre-training transformer for universal transfer learning in metal–organic frameworks"),
        q("PhysNet: A Neural Network for Predicting Energies, Forces, Dipole Moments, and Partial Charges"),
        q("TorchMD-NET: Equivariant Transformers for Neural Network based Molecular Potentials"),
        q("Accelerated data-driven materials science with the Materials Project", type_hint="benchmark-dataset"),
        q("Open Catalyst 2020 (OC20) Dataset and Community Challenges", type_hint="benchmark-dataset"),
        q("An invertible, invariant crystal representation for inverse design of solid-state materials using generative deep learning"),
        q("MatterGen: a generative model for inorganic materials design"),
        q("Schrödinger Materials Science", type_hint="commercial-product"),
        q("SLICES"),
        q("Foundation Model for Material Science"),
        q("Foundational Large Language Models for Materials Research"),
        q("Matterverse"),
    ],
    "08-cad-copilots-agents.jsonl": [
        q("Generative AI Meets CAD: Enhancing Engineering Design to Manufacturing Processes with LLMs"),
        q("Large Language Models for Computer-Aided Design: A Survey"),
        q("CAD-Prompted Generative Models: A Pathway to Feasible and Novel Engineering Designs"),
        q("Generative AI for CAD Automation: Leveraging LLMs for 3D Modelling"),
        q("Large language model-empowered next-generation computer-aided engineering"),
        q("CADDesigner: Conceptual Design of CAD Models Based on General-Purpose Agent"),
        q("CADInstruct: A Multimodal Dataset for Natural Language-Guided CAD Program Synthesis"),
        q("CAD-CODER: An Open-Source Vision-Language Model for Computer-Aided Design Code"),
        q("Agent-Aided Design for Dynamic CAD Models"),
    ],
    "10-pinn-differentiable.jsonl": [
        q("NSFnets (Navier-Stokes flow nets): Physics-informed neural networks for the incompressible Navier-Stokes equations"),
        q("B-PINNs: Bayesian physics-informed neural networks for forward and inverse PDE problems with noisy data"),
        q("hp-VPINNs: Variational physics-informed neural networks with domain decomposition"),
        q("Conservative physics-informed neural networks on discrete domains for conservation laws: Applications to forward and inverse problems"),
        q("PPINN: Parareal physics-informed neural network for time-dependent PDEs"),
        q("Gradient-enhanced physics-informed neural networks for forward and inverse PDE problems"),
        q("Self-adaptive physics-informed neural networks"),
        q("Variational Physics-Informed Neural Networks For Solving Partial Differential Equations"),
        q("Robust Variational Physics-Informed Neural Networks"),
        q("Extended Physics-Informed Neural Networks (XPINNs): A Generalized Space-Time Domain Decomposition Based Deep Learning Framework for Nonlinear Partial Differential Equations"),
        q("Augmented Physics-Informed Neural Networks (APINNs): A gating network-based soft domain decomposition methodology"),
        q("Interface PINNs (I-PINNs): A physics-informed neural networks framework for interface problems"),
        q("Parallel physics-informed neural networks via domain decomposition"),
        q("DiffTaichi: Differentiable Programming for Physical Simulation"),
        q("Learning to Control PDEs with Differentiable Physics"),
        q("Theseus: A Library for Differentiable Nonlinear Optimization"),
        q("Brax - A Differentiable Physics Engine for Large Scale Rigid Body Simulation"),
        q("Differentiable Convex Optimization Layers"),
        q("Separable physics-informed DeepONet: Breaking the curse of dimensionality in physics-informed machine learning"),
        q("Finite basis physics-informed neural networks (FBPINNs): a scalable domain decomposition approach for solving differential equations"),
        q("HFM: Hidden Fluid Mechanics"),
        q("Physics-informed neural networks for inverse problems in nano-optics and metamaterials"),
        q("Physics-informed neural networks for inverse problems in supersonic flows"),
        q("When Do Extended Physics-Informed Neural Networks (XPINNs) Improve Generalization?"),
        q("FastVPINNs: Tensor-Driven Acceleration of VPINNs for Complex Geometries"),
        q("BC-PINN: an adaptive physics informed neural network based on biased multiobjective coevolutionary algorithm"),
        q("fPINNs: Fractional Physics-Informed Neural Networks"),
        q("PINTO: Physics-informed transformer neural operator for learning generalized solutions of partial differential equations for any initial and boundary condition"),
        q("Physics-Informed Geometry-Aware Neural Operator"),
        q("Accelerated Gradient-based Design Optimization via Differentiable Physics-Informed Neural Operator"),
    ],
}


SEARCH_SWEEPS: dict[str, dict[str, Any]] = {
    "04-neural-operators-surrogates.jsonl": {
        "queries": [
            "Fourier neural operator",
            "neural operator PDE",
            "operator learning transformer PDE",
            "geometry-informed neural operator",
            "operator learning with neural fields",
            "convolutional neural operator",
        ],
        "include_any": [
            "neural operator",
            "operator learning",
            "deeponet",
            "fourier neural operator",
            "transformer for partial differential equations",
            "geometry-informed neural operator",
            "continuous vision transformer",
            "convolutional neural operators",
            "latent neural operator",
        ],
        "exclude_any": [
            "weather model",
            "graphcast",
            "fourcastnet",
            "aurora",
            "mesh-based simulation",
            "bypassing gain",
            "backstepping",
            "remote sensing",
            "medical image",
            "action recognition",
            "optical fiber",
            "image classification",
            "transport pde",
        ],
        "target": 42,
    },
    "07-dfm-dfam-ai.jsonl": {
        "queries": [
            "additive manufacturing machine learning build orientation",
            "support structure additive manufacturing machine learning",
            "thermal history additive manufacturing neural network",
            "surface roughness additive manufacturing machine learning",
            "melt pool additive manufacturing deep learning",
            "laser powder bed fusion graph neural network",
        ],
        "include_any": [
            "additive manufacturing",
            "laser powder bed fusion",
            "3d printing",
            "powder bed fusion",
            "surface roughness",
            "melt pool",
            "build orientation",
            "support structure",
            "thermal history",
        ],
        "exclude_any": ["review", "systematic review", "survey", "preliminary study to predict surface roughness"],
        "target": 18,
    },
    "10-pinn-differentiable.jsonl": {
        "queries": [
            "physics-informed neural networks",
            "variational physics-informed neural networks",
            "domain decomposition physics-informed neural networks",
            "differentiable physics simulation",
            "physics-informed DeepONet",
        ],
        "include_any": [
            "physics-informed neural network",
            "variational physics-informed neural networks",
            "vpinn",
            "xpinn",
            "fbpinn",
            "differentiable physics",
            "differentiable simulator",
            "differentiable convex optimization",
            "physics-informed deeponet",
        ],
        "exclude_any": ["review", "survey", "bibliometric", "editorial"],
        "target": 10,
    },
}


def build_product_record(
    filename: str,
    cand: ProductCandidate,
    *,
    seed_ids: set[str],
    used_ids: set[str],
) -> dict[str, Any] | None:
    try:
        html = get_text(cand.url, timeout=15)
    except Exception:
        return None
    meta = meta_descriptions(html)
    paras = visible_paragraphs(html, max_items=5)
    snippets = meta[:2] + paras[:4]
    if not snippets:
        return None

    intro = f"{cand.name} is a {cand.year} {cand.rtype.replace('-', ' ')} from {cand.organization}."
    body = " ".join(snippets[:4])
    tail = (
        f"It is grouped here as a {cand.category.replace('-', ' ')} system because it takes "
        f"{cand.input_modality.replace('-', ' ')} input and produces {cand.output_modality.replace('-', ' ')} output. "
        f"The current status is best described as {cand.status.replace('-', ' ')}."
    )
    description = ensure_min_words(intro + " " + body, [tail], min_words=80, max_words=250)
    if word_count(description) < 80:
        return None

    rid = make_id(cand.name, year=cand.year, seed_ids=seed_ids, used_ids=used_ids)
    return ordered_record(
        rid=rid,
        name=cand.name,
        category=cand.category,
        rtype=cand.rtype,
        organization=cand.organization,
        country=cand.country,
        year=cand.year,
        url_primary=cand.url,
        url_paper=cand.url_paper,
        url_github=cand.url_github,
        description=description,
        techniques=cand.techniques,
        input_modality=cand.input_modality,
        output_modality=cand.output_modality,
        physics_domain=cand.physics_domain,
        industry_application=cand.industry_application or [],
        status=cand.status,
    )


def abstract_for_work(work: dict[str, Any], fallback_url: str = "") -> tuple[str, str, list[str]]:
    abs_text = abstract_from_inverted_index(work.get("abstract_inverted_index"))
    url_primary = maybe_extract_primary_url(work)
    paper_url = maybe_extract_paper_url(work)
    open_access_url = (work.get("open_access") or {}).get("oa_url") or ""
    candidate_urls = [fallback_url, open_access_url, url_primary]
    seen_urls: set[str] = set()
    html_cache = ""
    if not abs_text:
        abs_text = crossref_abstract_from_doi(work.get("doi"))
    if not abs_text:
        for url in candidate_urls:
            if not url:
                continue
            if url in seen_urls:
                continue
            seen_urls.add(url)
            try:
                html_cache = get_text(url, timeout=12)
            except Exception:
                continue
            abs_text = generic_abstract_from_html(html_cache)
            if abs_text:
                break
    gh_links = github_links(html_cache)
    return abs_text, (url_primary or fallback_url), gh_links


def build_paper_record(
    filename: str,
    cand: TermCandidate,
    *,
    seed_ids: set[str],
    used_ids: set[str],
) -> dict[str, Any] | None:
    work = best_openalex_match(cand.search_query or cand.term, preferred_name=cand.preferred_title or cand.term)
    title = normalize_space((work or {}).get("title") or cand.term)
    if not title:
        return None
    if not title_matches_query(cand.preferred_title or cand.term, title):
        return None
    rtype = cand.type_hint or "academic-paper"
    if rtype == "commercial-product":
        # Treat "term candidates" that are really products through product handling.
        org = cand.manual_org or title
        year = cand.manual_year or 2025
        product = ProductCandidate(
            name=title,
            url=cand.manual_url_primary or cand.manual_url_paper,
            organization=org,
            country=cand.manual_country,
            year=year,
            category=cand.category_hint or paper_defaults_for_file(filename, title, rtype)[0],
            input_modality=cand.input_hint or paper_defaults_for_file(filename, title, rtype)[1],
            output_modality=cand.output_hint or paper_defaults_for_file(filename, title, rtype)[2],
            techniques=detect_techniques(title),
            status="deployed-production",
            physics_domain=cand.physics_hint or paper_defaults_for_file(filename, title, rtype)[3],
            industry_application=cand.industry_application or [],
        )
        return build_product_record(filename, product, seed_ids=seed_ids, used_ids=used_ids)

    category, input_modality, output_modality, physics_domain = paper_defaults_for_file(filename, title, rtype)
    if cand.category_hint:
        category = cand.category_hint
    if cand.input_hint:
        input_modality = cand.input_hint
    if cand.output_hint:
        output_modality = cand.output_hint
    if cand.physics_hint:
        physics_domain = cand.physics_hint

    if work is None:
        return None

    abs_text, url_primary, gh_links = abstract_for_work(work, fallback_url=cand.manual_url_primary or cand.manual_url_paper)
    if not abs_text or word_count(abs_text) < 30:
        return None

    paper_url = cand.manual_url_paper or maybe_extract_paper_url(work) or url_primary
    year = cand.manual_year or int(work.get("publication_year") or 0)
    if not year:
        return None

    organization, country = choose_org_country(work, fallback_org=cand.manual_org, fallback_country=cand.manual_country)
    if rtype == "benchmark-dataset":
        status = "open-source-tool"
    elif rtype == "open-source":
        status = "open-source-tool"
    else:
        status = "research-prototype"

    github = cand.manual_url_github or (gh_links[0] if gh_links else "")
    techniques = detect_techniques(title + " " + abs_text)
    intro = f"{title} is a {year} {rtype.replace('-', ' ')} from {organization}."
    body = abs_text
    tail = (
        f"It is included here under {category.replace('-', ' ')} because it focuses on "
        f"{input_modality.replace('-', ' ')} to {output_modality.replace('-', ' ')} workflows. "
        f"The work is best understood as a {status.replace('-', ' ')}."
    )
    description = ensure_min_words(intro + " " + body, [tail], min_words=80, max_words=250)
    if word_count(description) < 80:
        return None

    rid = make_id(title, year=year, seed_ids=seed_ids, used_ids=used_ids)
    return ordered_record(
        rid=rid,
        name=title,
        category=category,
        rtype=rtype,
        organization=organization,
        country=country,
        year=year,
        url_primary=url_primary or paper_url,
        url_paper=paper_url or url_primary,
        url_github=github,
        description=description,
        techniques=techniques,
        input_modality=input_modality,
        output_modality=output_modality,
        physics_domain=physics_domain,
        industry_application=cand.industry_application or [],
        status=status,
    )


def build_search_records(
    filename: str,
    sweep: dict[str, Any],
    *,
    seed_ids: set[str],
    used_ids: set[str],
    already_titles: set[str],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    include_any = [s.lower() for s in sweep["include_any"]]
    exclude_any = [s.lower() for s in sweep.get("exclude_any", [])]
    for query in sweep["queries"]:
        results = openalex_search(query, per_page=30, filter_expr="from_publication_date:2020-01-01")
        for work in results:
            title = normalize_space(work.get("title") or "")
            if not title:
                continue
            low = title.lower()
            if low in already_titles:
                continue
            if not any(key in low for key in include_any):
                continue
            if any(key in low for key in exclude_any):
                continue
            temp = TermCandidate(term=title)
            rec = build_paper_record(filename, temp, seed_ids=seed_ids, used_ids=used_ids)
            if rec is None:
                continue
            already_titles.add(title.lower())
            out.append(rec)
            if len(out) >= sweep["target"]:
                return out
    return out


def load_seed_ids() -> tuple[set[str], set[str]]:
    ids: set[str] = set()
    names: set[str] = set()
    with open(SEED_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            ids.add(rec["id"])
            names.add(normalize_space(rec["name"]).lower())
    return ids, names


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--only",
        nargs="*",
        default=[],
        help="Restrict output to specific files or numeric prefixes such as 05 or 05-generative-3d-shape.jsonl",
    )
    return parser.parse_args(argv)


def keep_file(filename: str, selectors: list[str]) -> bool:
    if not selectors:
        return True
    for raw in selectors:
        sel = normalize_space(raw)
        if not sel:
            continue
        if filename == sel:
            return True
        if filename.startswith(sel):
            return True
        if sel.isdigit() and filename.startswith(f"{int(sel):02d}-"):
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    seed_ids, seed_names = load_seed_ids()
    used_ids: set[str] = set()
    summary: dict[str, int] = {}

    file_order = [
        "01-text-to-cad-commercial.jsonl",
        "02-text-to-cad-academic.jsonl",
        "03-topology-optimization.jsonl",
        "04-neural-operators-surrogates.jsonl",
        "05-generative-3d-shape.jsonl",
        "06-generative-materials.jsonl",
        "07-dfm-dfam-ai.jsonl",
        "08-cad-copilots-agents.jsonl",
        "09-generative-platforms.jsonl",
        "10-pinn-differentiable.jsonl",
    ]

    for filename in file_order:
        if not keep_file(filename, args.only):
            continue
        records: list[dict[str, Any]] = []
        seen_titles: set[str] = set(seed_names)

        for cand in PRODUCT_FILES.get(filename, []):
            if normalize_space(cand.name).lower() in seen_titles:
                continue
            rec = build_product_record(filename, cand, seed_ids=seed_ids, used_ids=used_ids)
            if rec is None:
                continue
            seen_titles.add(rec["name"].lower())
            records.append(rec)

        for cand in TERM_FILES.get(filename, []):
            if normalize_space(cand.term).lower() in seen_titles:
                continue
            rec = build_paper_record(filename, cand, seed_ids=seed_ids, used_ids=used_ids)
            if rec is None:
                continue
            seen_titles.add(rec["name"].lower())
            records.append(rec)

        if filename in SEARCH_SWEEPS:
            records.extend(
                build_search_records(
                    filename,
                    SEARCH_SWEEPS[filename],
                    seed_ids=seed_ids,
                    used_ids=used_ids,
                    already_titles=seen_titles,
                )
            )

        records.sort(key=lambda r: (r["year"], r["name"].lower()))
        write_jsonl(RAW_DIR / filename, records)
        summary[filename] = len(records)
        print(f"{filename}: {len(records)} records")
        time.sleep(0.5)

    total = sum(summary.values())
    print(f"TOTAL NEW RECORDS WRITTEN: {total}")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
