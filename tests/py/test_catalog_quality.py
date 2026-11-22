"""Data quality gate for the REAL crawled catalogue (site/catalog.json).
Runs after every crawl, before the new prices are saved, and again in the Cloudflare build.
If the shops change their pages and the crawl comes back broken, these tests fail and the
last good catalogue stays live. Skipped when no catalogue exists yet."""
import json
from collections import Counter
from pathlib import Path

import pytest

CAT = Path(__file__).resolve().parents[2] / "site" / "catalog.json"
pytestmark = pytest.mark.skipif(not CAT.exists(), reason="no crawled catalogue yet")
PARTS = ["cpu", "gpu", "board", "ram", "ssd", "psu", "case", "cooler"]
RANGE = {"cpu": (3000, 300000), "gpu": (5000, 800000), "board": (5000, 200000), "ram": (1500, 300000),
         "ssd": (1500, 300000), "psu": (2000, 100000), "case": (2000, 150000), "cooler": (800, 80000)}


@pytest.fixture(scope="module")
def cat():
    return json.loads(CAT.read_text(encoding="utf-8"))


def test_Q01_schema(cat):
    """TC-Q01 every product has the fields the site needs, with sane types."""
    for i in cat["items"]:
        assert {"id", "s", "c", "n", "p", "st", "u"} <= i.keys(), i
        assert i["c"] in PARTS and i["u"].startswith("http") and i["st"] in (0, 1)


def test_Q02_unique_ids(cat):
    """TC-Q02 no duplicated products."""
    dup = [k for k, v in Counter(i["id"] for i in cat["items"]).items() if v > 1]
    assert not dup, dup[:5]


def test_Q03_in_stock_items_have_plausible_prices(cat):
    """TC-Q03 [BVA] every in-stock usable part has a price inside its category's plausible range."""
    bad = [(i["c"], i["n"][:50], i["p"]) for i in cat["items"]
           if i["st"] and (i.get("m") or i.get("a")) and not (i["p"] and RANGE[i["c"]][0] <= i["p"] <= RANGE[i["c"]][1])]
    assert not bad, bad[:10]


def test_Q04_enough_products(cat):
    """TC-Q04 the crawl returned a realistic amount of data (not a half-broken crawl)."""
    assert len(cat["items"]) >= 200, len(cat["items"])


def test_Q05_builder_has_parts_in_every_category(cat):
    """TC-Q05 Smart Build has at least 3 usable in-stock products in each of the 8 categories."""
    usable = Counter(i["c"] for i in cat["items"] if i["st"] and i["p"] and (i.get("m") or i.get("a")))
    thin = {c: usable[c] for c in PARTS if usable[c] < 3}
    assert not thin, thin


def test_Q06_every_shop_present(cat):
    """TC-Q06 no shop silently disappeared from the crawl."""
    counts = Counter(i["s"] for i in cat["items"])
    assert all(counts[s] >= 20 for s in cat["shops"]), counts
