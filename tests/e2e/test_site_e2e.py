"""End-to-end tests: the built website in a real browser (Playwright + Chromium).

The site is built from the sample shop pages, served locally, and used like a visitor would.
External things are replaced: product photos and the AI picture return a test image, web fonts are skipped.
Run:  pip install pytest playwright && playwright install chromium && pytest tests/e2e
"""
import re
import functools
import http.server
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tests" / "py"), str(ROOT / "scraper"), str(ROOT / "tests" / "fixtures")]
from conftest import build_copy, sample_catalog, shops_cfg  # noqa: E402,F401  (fixtures re-used)

playwright = pytest.importorskip("playwright.sync_api")
TEST_JPG = (ROOT / "site" / "og-image.jpg").read_bytes()


@pytest.fixture(scope="session")
def site_url(tmp_path_factory, sample_catalog):
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), None)
    port = srv.server_address[1]
    dist, _ = build_copy(tmp_path_factory.mktemp("e2e"), sample_catalog, base=f"http://127.0.0.1:{port}")
    srv.RequestHandlerClass = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(dist))
    srv.RequestHandlerClass.log_message = lambda *a: None
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{port}"
    srv.shutdown()


@pytest.fixture(scope="session")
def browser():
    with playwright.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def new_page(browser, width=1280, height=900, mobile=False):
    ctx = browser.new_context(viewport={"width": width, "height": height}, is_mobile=mobile, has_touch=mobile)
    page = ctx.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    page.route("**/fonts.gstatic.com/**", lambda r: r.abort())
    for pat in ("**/image/*.jpg", "**/img?u=*", "**/render?*"):
        page.route(pat, lambda r: r.fulfill(body=TEST_JPG, content_type="image/jpeg", headers={"Access-Control-Allow-Origin": "*"}))
    page.requests = []
    page.on("request", lambda r: page.requests.append(r.url))
    return page


def ready(page, url):
    page.goto(url)
    page.wait_for_function("document.querySelectorAll('#sheet .row').length===8 && /Live prices/.test(document.querySelector('.foot .note')?.textContent||'')", timeout=15000)


def money(text):
    return int("".join(ch for ch in text if ch.isdigit()))


# ---------------------------------------------------------------- functional

def test_U01_home_builds_with_live_prices(browser, site_url):
    """TC-U01 [FR-01, FR-07] home page: logo, 8 parts, live prices, total within budget, all checks pass."""
    p = new_page(browser)
    ready(p, site_url + "/")
    assert p.eval_on_selector("header img", "i => i.naturalWidth") > 0
    assert money(p.inner_text(".big")) <= int(p.input_value("#bud"))
    assert p.locator(".chk.w").count() == 0
    assert not p.errors


def test_U02_budget_preset_changes_build(browser, site_url):
    """TC-U02 [FR-01] choosing a preset rebuilds within the new budget."""
    p = new_page(browser)
    ready(p, site_url + "/")
    p.click("#presets button[data-v='250000']")
    p.wait_for_function("document.getElementById('bud').value==='250000'")
    assert money(p.inner_text(".big")) <= 250000


def test_U03_url_preset(browser, site_url):
    """TC-U03 [FR-15, FR-03] ?budget=&gpu= link opens the builder pre-set."""
    p = new_page(browser)
    ready(p, site_url + "/?budget=200000&gpu=rtx5070")
    assert p.input_value("#bud") == "200000"
    assert "RTX 5070" in p.locator("#sheet .row").nth(1).inner_text()


def test_U04_swap_keeps_compatibility(browser, site_url):
    """TC-U04 [FR-08] swapping the motherboard keeps every compatibility check green."""
    p = new_page(browser)
    ready(p, site_url + "/")
    sel = p.locator("select[data-slot='board']")
    values = sel.locator("option").evaluate_all("os => os.map(o => o.value)")
    assert len(values) > 1
    sel.select_option(values[-1])
    p.wait_for_timeout(200)
    assert p.locator(".chk.w").count() == 0


def test_U05_budget_too_low(browser, site_url):
    """TC-U05 [FR-09] impossible budget shows the cheapest total and a one-click fix."""
    p = new_page(browser)
    ready(p, site_url + "/")
    p.select_option("#gpuP", "rtx5090")
    p.fill("#bud", "40000")
    p.dispatch_event("#bud", "change")
    btn = p.locator("#sheet button[data-set]")
    btn.wait_for()
    btn.click()
    p.wait_for_function("document.querySelectorAll('#sheet .row').length===8")
    assert "RTX 5090" in p.locator("#sheet .row").nth(1).inner_text()


def test_U06_buy_links(browser, site_url):
    """TC-U06 [FR-12] every listed part has a 'Buy at …' link to that shop, opened safely."""
    p = new_page(browser)
    ready(p, site_url + "/")
    links = p.eval_on_selector_all("#sheet a.buy", "as => as.map(a => [a.textContent, a.href, a.rel, a.target])")
    assert len(links) >= 7
    for text, href, rel, target in links:
        shop = text.replace("Buy at ", "")
        domain = {"Star Tech": "startech.com.bd", "Ryans": "ryans.com", "Tech Land": "techlandbd.com", "PCB Store": "pcbstore.com.bd",
                  "Sumash Tech": "sumashtech.com"}[shop]
        assert domain in href and "noopener" in rel and "nofollow" in rel and target == "_blank"


def test_U07_build_pictures(browser, site_url):
    """TC-U07 [FR-12] 'Build Image' draws the parts card and offers download; the AI photo is no longer requested."""
    p = new_page(browser)
    ready(p, site_url + "/")
    p.click("#mkimg")
    p.wait_for_function("document.getElementById('imgprev').src.startsWith('blob:')", timeout=20000)
    assert not any("/render?" in u for u in p.requests)
    assert p.is_visible("#imgsave")


def test_U08_product_list_lazy_and_search(browser, site_url):
    """TC-U08 [FR-10, NFR-02] full catalogue loads only near 'All products'; search filters it."""
    p = new_page(browser)
    ready(p, site_url + "/")
    assert not any(u.endswith("/catalog.json") for u in p.requests), "catalogue loaded before it was needed"
    p.evaluate("document.getElementById('products').scrollIntoView()")
    p.wait_for_function("document.querySelectorAll('#cgrid .pcard').length>=24", timeout=10000)
    p.fill("#q", "rtx 5060")
    p.wait_for_timeout(400)
    names = p.eval_on_selector_all("#cgrid .pn", "ns => ns.map(n => n.textContent.toLowerCase())")
    assert names and all("rtx 5060" in n for n in names)


def test_U09_ready_build_page(browser, site_url):
    """TC-U09 [FR-14] a ready-build page opens with its budget and use pre-set."""
    p = new_page(browser)
    ready(p, site_url + "/builds/gaming-pc-under-1-lakh-taka/")
    assert p.input_value("#bud") == "100000"
    assert p.get_attribute("#use button[data-v='gaming']", "aria-pressed") == "true"
    assert money(p.inner_text(".big")) <= 100000


def test_U10_price_pages_open(browser, site_url):
    """TC-U10 [FR-14] links from the home page to price guides open real pages."""
    p = new_page(browser)
    ready(p, site_url + "/")
    hrefs = p.eval_on_selector_all(".linkgrid a", "as => as.map(a => a.href)")[:6]
    for h in hrefs:
        r = p.goto(h)
        assert r.status == 200, h
        assert p.locator("h1").count() == 1


# ---------------------------------------------------------------- responsive / usability

@pytest.mark.parametrize("w,h,mobile", [(360, 740, True), (390, 844, True), (768, 1024, True), (1280, 900, False), (1440, 900, False)])
def test_U11_no_sideways_scroll(browser, site_url, w, h, mobile):
    """TC-U11 [NFR-01] no horizontal scrolling at phone, tablet and desktop widths."""
    p = new_page(browser, w, h, mobile)
    ready(p, site_url + "/")
    for path in ("/", "/builds/", "/price/graphics-card/"):
        p.goto(site_url + path)
        p.wait_for_timeout(300)
        assert p.evaluate("document.documentElement.scrollWidth") <= w, f"{path} at {w}px"


@pytest.mark.parametrize("w", [360, 390])
def test_U12_mobile_menu_links_do_not_overlap(browser, site_url, w):
    """TC-U12 [regression DEF-05] menu links on phones sit side by side without overlapping."""
    p = new_page(browser, w, 800, True)
    ready(p, site_url + "/")
    boxes = p.eval_on_selector_all("nav .links a", "as => as.map(a => {const r=a.getBoundingClientRect();return [r.left,r.right]})")
    for (l1, r1), (l2, r2) in zip(boxes, boxes[1:]):
        assert r1 <= l2 + 0.5, f"links overlap: {boxes}"
    # added after mutation test M15 survived: a squeezed link keeps its box but its text spills out
    spill = p.eval_on_selector_all("nav .links a", "as => as.filter(a => a.scrollWidth > a.clientWidth + 1).map(a => a.textContent)")
    assert not spill, f"link text doesn't fit its box: {spill}"


def test_U13_touch_targets(browser, site_url):
    """TC-U13 [NFR-01] main controls are at least 44 px tall on a phone."""
    p = new_page(browser, 390, 844, True)
    ready(p, site_url + "/")
    small = p.eval_on_selector_all(
        "#presets .chip, #use button, #cpuP, #gpuP, #bud, #budr, #sheet a.buy, #mgo, nav .links a",
        "es => es.filter(e => e.getBoundingClientRect().height > 0 && e.getBoundingClientRect().height < 43.5).map(e => (e.id || e.className || e.tagName) + ':' + e.getBoundingClientRect().height)")
    assert not small, small


def test_U14_mobile_bar(browser, site_url):
    """TC-U14 [NFR-01] phone bar shows the total and jumps to the parts list."""
    p = new_page(browser, 390, 844, True)
    ready(p, site_url + "/")
    assert p.is_visible("#mbar")
    assert money(p.inner_text("#mtot")) == money(p.inner_text(".big"))
    p.tap("#mgo")
    p.wait_for_function("Math.abs(document.getElementById('sheet').getBoundingClientRect().top) < 120", timeout=5000)


# ---------------------------------------------------------------- accessibility basics / robustness

def test_U15_accessibility_basics(browser, site_url):
    """TC-U15 [accessibility] language set, one h1, images have alt text, controls have names."""
    p = new_page(browser)
    ready(p, site_url + "/")
    assert p.get_attribute("html", "lang") == "en"
    assert p.locator("h1").count() == 1
    assert p.eval_on_selector_all("img", "is => is.filter(i => !i.hasAttribute('alt')).length") == 0
    unnamed = p.eval_on_selector_all("select, input:not([type=hidden]), button",
        "es => es.filter(e => !(e.labels && e.labels.length) && !e.getAttribute('aria-label') && !e.textContent.trim()).map(e => e.id || e.outerHTML.slice(0, 60))")
    assert not unnamed, unnamed


@pytest.mark.parametrize("path", ["/", "/builds/", "/builds/office-study-pc-under-60000-taka/", "/price/", "/price/processor/", "/about/", "/no-such-page/"])
def test_U16_no_script_errors(browser, site_url, path):
    """TC-U16 [robustness] key pages (and the 404 page) open without script errors."""
    p = new_page(browser)
    p.goto(site_url + path)
    p.wait_for_timeout(1200)
    assert not p.errors, p.errors


def test_U17_swap_menu_has_search(browser, site_url):
    """TC-U17 [FR-16] every swap menu opens a search box; typing narrows the list and Enter swaps the part."""
    p = new_page(browser)
    ready(p, site_url + "/")
    row = p.locator("#sheet .row").nth(1)            # graphics card row
    before = row.locator(".nm").inner_text()
    row.locator(".sp-btn").click()
    q = p.locator(".sp-pop input[type=search]")
    assert q.is_visible() and q.evaluate("e => e === document.activeElement")
    n_all = p.locator(".sp-pop .sp-o").count()
    q.fill("rtx")
    n_rtx = p.locator(".sp-pop .sp-o").count()
    assert 0 < n_rtx < n_all
    assert all("rtx" in t.lower() for t in p.locator(".sp-pop .sp-o").all_inner_texts())
    q.press("ArrowDown")
    q.press("Enter")
    p.wait_for_function("!document.querySelector('.sp-pop')")
    after = p.locator("#sheet .row").nth(1).locator(".nm").inner_text()
    assert after != before and "RTX" in after.upper()


def test_U18_processor_picker_search_and_escape(browser, site_url):
    """TC-U18 [FR-06, FR-16] the processor picker is searchable; Escape closes it without changing anything."""
    p = new_page(browser)
    ready(p, site_url + "/")
    btn = p.locator("#f .sp-btn").first
    assert "Auto" in btn.inner_text()
    btn.click()
    p.fill(".sp-pop input[type=search]", "zzzz no such cpu")
    assert "No match" in p.locator(".sp-pop").inner_text()
    p.keyboard.press("Escape")
    assert p.locator(".sp-pop").count() == 0 and "Auto" in btn.inner_text()
    btn.click()
    p.fill(".sp-pop input[type=search]", "7800X3D")
    p.locator(".sp-pop .sp-o").first.click()
    p.wait_for_function("document.querySelector('#sheet .row .nm').textContent.includes('7800X3D')")
    assert "7800X3D" in btn.inner_text()


def test_U19_price_list_search(browser, site_url):
    """TC-U19 [FR-16] the price list has a search box for the open tab; no match shows a message."""
    p = new_page(browser)
    ready(p, site_url + "/")
    p.evaluate("document.getElementById('prices').scrollIntoView()")
    p.click("#tabs button[data-k='gpu']")
    assert "graphics card" in p.get_attribute("#pq", "placeholder").lower()
    p.fill("#pq", "5070")
    p.wait_for_timeout(400)
    rows = p.locator("#ptable tbody tr").all_inner_texts()
    assert rows and all("5070" in r for r in rows)
    p.fill("#pq", "qqqq")
    p.wait_for_timeout(400)
    assert "No part matches" in p.inner_text("#ptable")


def test_U20_search_popup_fits_phone_screen(browser, site_url):
    """TC-U20 [NFR-02] on a phone the search list opens as a bottom sheet inside the screen."""
    p = new_page(browser, 390, 844, True)
    ready(p, site_url + "/")
    p.locator("#sheet .row .sp-btn").first.scroll_into_view_if_needed()
    p.locator("#sheet .row .sp-btn").first.click()
    box = p.locator(".sp-pop").bounding_box()
    assert box["x"] >= 0 and box["x"] + box["width"] <= 390 and box["y"] >= 0 and box["y"] + box["height"] <= 844


def test_U21_shop_menu_lists_all_five_shops(browser, site_url):
    """TC-U21 [FR-08] the Shops menu in All Products lists all 5 shops with their product counts,
    and choosing one shows only that shop's products."""
    p = new_page(browser)
    ready(p, site_url + "/")
    opts = p.eval_on_selector_all("#cshop option", "os => os.map(o => o.textContent)")
    names = [o.split(" (")[0] for o in opts[1:]]
    assert names == ["Star Tech", "Ryans", "Tech Land", "PCB Store", "Sumash Tech"], opts
    assert all(re.search(r"\(\d[\d,]*\)$", o) for o in opts[1:])
    p.evaluate("document.getElementById('products').scrollIntoView()")
    p.wait_for_selector("#cgrid a.pcard")
    p.select_option("#cshop", "Sumash Tech")
    p.wait_for_timeout(400)
    shops = set(p.eval_on_selector_all("#cgrid a.pcard", "cs => cs.map(c => c.querySelector('.sh, .shop')?.textContent || c.textContent)"))
    assert shops and all("Sumash Tech" in t for t in shops)
