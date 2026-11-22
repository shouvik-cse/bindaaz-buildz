"""FR-14 / NFR-05: the static site generator (scraper/build_site.py) and SEO output."""
import json
import re
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from conftest import build_copy
import build_site

BASE = "https://bindaaz-buildz.smart-builder.workers.dev"


@pytest.mark.parametrize("raw,expect", [
    ("https://https://bindaaz-buildz.smart-builder.workers.dev/", BASE),     # regression DEF-10
    (" bindaaz-buildz.smart-builder.workers.dev", BASE),
    ("https://bindaaz-buildz.smart-builder.workers.dev/", BASE),
    ("http://x.dev", "https://x.dev"),
    ("localhost:8000", "http://localhost:8000"),
])
def test_clean_base(raw, expect):
    """TC-S01 [EP + error guessing] typos in base_url are corrected."""
    assert build_site.clean_base(raw) == expect


def html_files(dist):
    return [p for p in dist.rglob("*.html")]


def test_no_placeholders_or_double_scheme(built_site):
    """TC-S02 [regression DEF-07, DEF-10] no __BASE__/__ROOT__ placeholders or https://https:// anywhere."""
    for f in html_files(built_site):
        t = f.read_text(encoding="utf-8")
        assert "__BASE__" not in t and "__ROOT__" not in t, f
        assert "https://https://" not in t, f


def sitemap_urls(dist):
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    return [e.text for e in ET.parse(dist / "sitemap.xml").getroot().findall("s:url/s:loc", ns)]


def test_sitemap_valid_and_trailing_slash(built_site):
    """TC-S03 [regression DEF-11] sitemap is valid XML, every address ends with / and exists in the build."""
    urls = sitemap_urls(built_site)
    assert len(urls) >= 90
    assert len(urls) == len(set(urls)), "duplicate sitemap entries"
    for u in urls:
        assert u.startswith(BASE + "/") and u.endswith("/"), u
        rel = u[len(BASE) + 1:]
        assert (built_site / rel / "index.html").exists() or rel == "", f"sitemap points to a missing page: {u}"


def test_canonical_matches_sitemap(built_site):
    """TC-S04 [SEO] each page's canonical address equals its own sitemap address."""
    for u in sitemap_urls(built_site):
        rel = u[len(BASE) + 1:]
        t = (built_site / rel / "index.html").read_text(encoding="utf-8")
        m = re.search(r'<link rel="canonical" href="([^"]+)"', t)
        assert m and m.group(1) == u, f"{u}: canonical {m and m.group(1)}"


def test_titles_and_descriptions_unique(built_site):
    """TC-S05 [SEO] every page has a unique title and a description."""
    titles = {}
    for f in html_files(built_site):
        if f.name == "404.html":
            continue
        t = f.read_text(encoding="utf-8")
        title = re.search(r"<title>(.*?)</title>", t, re.S).group(1)
        assert re.search(r'<meta name="description" content="[^"]{30,}"', t), f
        assert title not in titles, f"same title on {f} and {titles.get(title)}"
        titles[title] = f


def test_structured_data_parses(built_site):
    """TC-S06 [SEO] all JSON-LD blocks are valid JSON; price pages carry BDT AggregateOffer."""
    offers = 0
    for f in html_files(built_site):
        for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', f.read_text(encoding="utf-8"), re.S):
            data = json.loads(block)
            for node in data.get("@graph", []):
                if node.get("@type") == "Product":
                    assert node["offers"]["priceCurrency"] == "BDT"
                    assert node["offers"]["lowPrice"] <= node["offers"]["highPrice"]
                    offers += 1
    assert offers >= 20


def test_internal_links_resolve(built_site):
    """TC-S07 [link check] every internal link on every page points to a page that exists."""
    broken = set()
    for f in html_files(built_site):
        for href in re.findall(r'href="(' + re.escape(BASE) + r'[^"#?]*)', f.read_text(encoding="utf-8")):
            rel = href[len(BASE):].lstrip("/")
            target = built_site / rel
            if not (target.is_file() or (target / "index.html").exists() or rel == ""):
                broken.add(href)
    assert not broken, sorted(broken)[:10]


def test_ready_builds_precomputed(built_site):
    """TC-S08 [FR-14] 19 ready-build pages, each with a static 8-part preview and its budget preset."""
    pages = sorted((built_site / "builds").glob("*/index.html"))
    assert len(pages) == 19
    for p in pages:
        t = p.read_text(encoding="utf-8")
        assert "window.PRESET" in t
        page_html = t.split('<script src="')[0]          # the static preview, not the page's script code
        assert page_html.count('<li class="row">') == 8, p


def test_404_page(built_site):
    """TC-S13 [regression DEF-17] the error page is not indexed and links nowhere broken."""
    t = (built_site / "404.html").read_text(encoding="utf-8")
    assert "404-tmp" not in t and 'rel="canonical"' not in t and 'content="noindex"' in t


def test_robots_and_parts_file(built_site):
    """TC-S09 robots.txt points to the sitemap; parts.json only holds parts the builder can use."""
    assert f"Sitemap: {BASE}/sitemap.xml" in (built_site / "robots.txt").read_text()
    parts = json.loads((built_site / "parts.json").read_text(encoding="utf-8"))
    assert parts["items"] and all(i.get("m") or i.get("a") for i in parts["items"])
    assert parts["total"] >= len(parts["items"])


def test_build_without_photos(tmp_path, sample_catalog):
    """TC-S10 [regression DEF-08] products without photos don't crash the build."""
    dist, log = build_copy(tmp_path, sample_catalog, drop_images=True)
    assert "Built" in log and (dist / "builds" / "gaming-pc-under-1-lakh-taka" / "index.html").exists()


def test_build_without_catalog(tmp_path):
    """TC-S11 [EP] first deploy before any crawl: site still builds (estimate prices)."""
    dist, log = build_copy(tmp_path, None)
    assert (dist / "index.html").exists() and (dist / "sitemap.xml").exists()


def test_source_page_works_unbuilt():
    """TC-S12 [regression DEF-07] site/index.html loads its logo and engine by plain relative paths."""
    t = (Path(build_site.SITE) / "index.html").read_text(encoding="utf-8")
    assert 'src="engine.js"' in t and 'src="logo.webp"' in t and "__ROOT__" not in t
