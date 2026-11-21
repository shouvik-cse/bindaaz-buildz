"""FR-10: crawler (scraper/crawl.py) – price/stock/photo extraction, pagination, robustness.
Unit tests on single cards, then an integration test of the whole crawl against sample pages."""
import json
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

import crawl
import shops as fixture_shops

ROOT = Path(__file__).resolve().parents[2]


def card(html):
    return BeautifulSoup(html, "html.parser").div


@pytest.mark.parametrize("html,price,stock", [
    ('<div><span class="price-new">39,900৳</span> <span class="price-old">43,850৳</span></div>', 39900, 1),   # Star Tech new + old
    ('<div><span>৳ 41,999</span><del>৳ 45,500</del><div>EMI Start From* ৳ 1,234</div></div>', 41999, 1),  # Tech Land
    ('<div><p>Tk 48,300</p></div>', 48300, 1),                                                            # Ryans
    ('<div><span class="mark">Save: 3,950৳</span><span>36,000৳</span></div>', 36000, 1),                  # save badge first
    ('<div><h3>AMD Ryzen 5 7600</h3><span>৳ 23,500</span></div>', 23500, 1),                              # regression DEF-02
    ('<div><span>Out Of Stock</span></div>', None, 0),
    ('<div><span>39,900৳</span><b>Out of stock</b></div>', 39900, 0),
    ('<div>Price To be announced</div>', None, 0),
    ('<div><span>৳ 120</span></div>', None, 0),                                                           # below sane minimum
])
def test_card_price(html, price, stock):
    """TC-K01 [EP + error guessing] current price wins over old / save / EMI / name digits."""
    assert crawl.card_price(card(html)) == (price, stock)


@pytest.mark.parametrize("html,expect", [
    ('<div><img src="/x/placeholder.png" data-src="/img/real.webp"></div>', "https://s.com/img/real.webp"),
    ('<div><img src="data:image/gif;base64,AAA" data-lazy-src="https://cdn.s.com/a.jpg"></div>', "https://cdn.s.com/a.jpg"),
    ('<div><img srcset="/a-300.jpg 300w, /a-600.jpg 600w"></div>', "https://s.com/a-300.jpg"),
    ('<div><img src="/loading.gif"></div>', None),
    ('<div>no image</div>', None),
])
def test_card_img(html, expect):
    """TC-K02 [EP] product photo: lazy-load attributes first, placeholders skipped."""
    assert crawl.card_img(card(html), "https://s.com/cat") == expect


@pytest.mark.parametrize("base,n,expect", [
    ("https://s.com/c", 1, "https://s.com/c"),
    ("https://s.com/c", 3, "https://s.com/c?page=3"),
    ("https://s.com/c?sort=p", 2, "https://s.com/c?sort=p&page=2"),
])
def test_page_url(base, n, expect):
    """TC-K03 [BVA] first page has no ?page, later pages keep other query values."""
    assert crawl.page_url(base, n) == expect


def test_generic_parser_ryans_photo_outside_price_box():
    """TC-K04 [regression DEF-06] photo in a sibling link outside the price box is still found."""
    html = fixture_shops.ryans_page([("MSI GeForce RTX 5060 8GB", 44000, True)])
    shop = {"name": "Ryans", "base": "https://www.ryans.com", "categories": {"gpu": "/category/x"}}
    [c] = crawl.parse_listing(html, "https://www.ryans.com/category/x", shop)
    assert c["p"] == 44000 and c["st"] == 1 and c["i"].endswith(".jpg")


def test_selector_parser_falls_back_to_generic():
    """TC-K05 [error guessing] wrong CSS selectors in shops.json → generic finder still works."""
    html = fixture_shops.techland_page([("Deepcool AK400 CPU Air Cooler", 2800, True)])
    shop = {"name": "T", "base": "https://www.techlandbd.com", "card": {"item": ".does-not-exist"}, "categories": {}}
    [c] = crawl.parse_listing(html, "https://www.techlandbd.com/pc-components/cpu-cooler", shop)
    assert c["p"] == 2800


def test_crawl_stops_on_repeated_last_page(monkeypatch):
    """TC-K06 [boundary] a shop that repeats its last page for ?page=99 doesn't loop forever."""
    pages = {1: [("A product one name", 5000, True)], 2: [("B product two name", 6000, True)]}
    def fake_get(url):
        n = int(url.split("page=")[1]) if "page=" in url else 1
        return 200, fixture_shops.ryans_page(pages.get(n, pages[2]))
    monkeypatch.setattr(crawl, "get", fake_get)
    shop = {"name": "Ryans", "base": "https://www.ryans.com", "categories": {"gpu": "/category/x"}}
    items, err = crawl.crawl_category(shop, "gpu", "/category/x", 80)
    assert len(items) == 2 and err is None


def test_crawl_reports_missing_category(monkeypatch):
    """TC-K07 [EP] a category page that doesn't exist is reported (404), not silently empty."""
    monkeypatch.setattr(crawl, "get", lambda url: (404, ""))
    shop = {"name": "T", "base": "https://www.techlandbd.com", "categories": {"ssd": "/wrong"}}
    items, err = crawl.crawl_category(shop, "ssd", "/wrong", 80)
    assert items == [] and err == 404


def test_robots_txt_is_respected(monkeypatch):
    """TC-K08 [NFR compliance] pages disallowed by robots.txt are never requested."""
    monkeypatch.setattr(crawl, "allowed", lambda url: False)
    assert crawl.get("https://www.startech.com.bd/component/ram") == ("robots", "")


# ---------------- integration: the whole crawl against the three sample shops ----------------

def test_integration_all_shops_all_categories(sample_catalog, shops_cfg):
    """TC-K09 [integration] every shop × category produces products with correct fields."""
    items = sample_catalog["items"]
    seen = {(i["s"], i["c"]) for i in items}
    for s in shops_cfg:
        for c in s["categories"]:
            assert (s["name"], c) in seen, f"no products for {s['name']} / {c}"
    for i in items:
        assert i["n"] and i["u"].startswith("https://") and len(i["id"]) == 10
        assert i["st"] in (0, 1)
        if i["st"]:
            assert isinstance(i["p"], int) and 300 <= i["p"] <= 2_000_000


def test_integration_prices_match_source(sample_catalog):
    """TC-K10 [integration] parsed price = the price on the page, for each layout."""
    prods = fixture_shops.products()
    from urllib.parse import urlparse
    host_of = {s["name"]: urlparse(s["base"]).netloc for s in json.loads((ROOT / "scraper/shops.json").read_text())["shops"]}
    expected = {}
    for cat, rows in prods.items():
        for n, p, s in rows:
            if s:
                for host, style in fixture_shops.SHOPS.items():
                    expected[(host, n)] = int(p * fixture_shops.PRICE_FACTOR[style] * fixture_shops.HOST_FACTOR.get(host, 1))
    checked = 0
    for i in sample_catalog["items"]:
        key = (host_of[i["s"]], i["n"])
        if i["st"] and key in expected:
            assert i["p"] == expected[key], f"{i['s']} {i['n']}: {i['p']} != {expected[key]}"
            checked += 1
    assert checked > 700


def test_integration_classification_rate(sample_catalog):
    """TC-K11 [integration] ≥95% of real parts are understood; every accessory is rejected."""
    items = sample_catalog["items"]
    acc = [i for i in items if "Accessory" in i["n"]]
    parts = [i for i in items if "Accessory" not in i["n"]]
    understood = sum(1 for i in parts if i.get("m") or i.get("a"))
    assert all(not i.get("m") and not i.get("a") for i in acc)
    assert understood / len(parts) >= 0.95, f"{understood}/{len(parts)}"


def test_integration_photos_found(sample_catalog):
    """TC-K12 [integration] every product card with a photo yields a photo URL."""
    items = sample_catalog["items"]
    assert sum(1 for i in items if i.get("i")) / len(items) >= 0.99


def test_integration_discovers_renamed_category_pages(sample_catalog):
    """TC-K13 [error guessing] when a shop's configured category paths 404, the crawler finds the
    category through the link with that name on the shop's menu page (Sumash Tech sample)."""
    got = {i["c"] for i in sample_catalog["items"] if i["s"] == "Sumash Tech"}
    assert got == {"cpu", "cooler", "board", "ram", "ssd", "gpu", "psu", "case"}
    urls = [i["u"] for i in sample_catalog["items"] if i["s"] == "Sumash Tech"]
    assert all(u.startswith("https://www.sumashtech.com/") for u in urls)


def test_path_paging_and_woocommerce_cards():
    """TC-K14 [EP] WordPress shops page with /page/2/; WooCommerce cards give price, 'Sold out' and photo."""
    assert crawl.page_url("https://computermania.com.bd/product-category/x/", 2, "path") == "https://computermania.com.bd/product-category/x/page/2/"
    assert crawl.page_url("https://computermania.com.bd/product-category/x/", 1, "path") == "https://computermania.com.bd/product-category/x/"
    html = fixture_shops.woo_page([("MSI MAG B650 Tomahawk WiFi Motherboard", 31500, True), ("ASRock B450M Pro4 Motherboard", 9800, False)])
    shop = {"name": "CM", "base": "https://computermania.com.bd", "categories": {}}
    a, b = crawl.parse_listing(html, "https://computermania.com.bd/product-category/desktop-components/motherboard/", shop)
    assert (a["p"], a["st"]) == (31500, 1) and a["i"].endswith(".jpg")
    assert b["st"] == 0


def test_opencart_cards_ignore_old_and_tax_price():
    """TC-K15 [EP] OpenCart cards (Creatus, PCB Store): current price, not old price or 'Ex Tax' line; 'call for price' = out of stock."""
    html = fixture_shops.opencart_page([("Gigabyte GeForce RTX 5060 Eagle OC 8GB Graphics Card", 41800, True), ("PNY RTX 2060 12GB", 0, False)])
    shop = {"name": "C", "base": "https://www.creatus.com.bd", "categories": {}}
    a, b = crawl.parse_listing(html, "https://www.creatus.com.bd/graphics-card", shop)
    assert (a["p"], a["st"]) == (41800, 1)
    assert b["st"] == 0
