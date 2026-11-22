"""Deterministic sample shop listing pages for testing the crawler without the internet.

Three page layouts imitate the real shops:
  * "Star Tech" style  - .p-item cards, "39,900৳ 43,850৳" new/old price, "Save: …" badge, lazy data-src photos
  * "Ryans" style      - generic cards, "Tk 48,300", photo in a sibling link outside the price box
  * "Tech Land" style  - <li> cards, "৳ 41,999" with a struck-through old price and an EMI line
  * "OpenCart" style   - PCB Store / Sumash Tech: "66,800৳ 70,500৳" new/old + "Ex Tax:66,800৳"
                         Sumash Tech cuts long names on cards ("MSI PRO B760M-E DDR5 Micro-ATX M...") and keeps
                         the full name in the photo's alt text, followed by " Price In Bangladesh"
  * "WooCommerce" style - a WordPress shop: "৳ 74,000", "Sold out" badge, /page/2/ paging (unit tests only)

Sumash Tech's sample site only answers its first category path for the processor; every other
category is found through the links in its menu page (tests the crawler's discovery).

Products are generated from the site's own parts table (site/engine.js), with a few
accessories mixed in (which the classifier must reject) and ~15% out of stock.
"""
import random
import re
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "site" / "engine.js"
TABLES = {"cpu": "C", "gpu": "G", "board": "B", "ram": "R", "ssd": "S", "psu": "P", "case": "K", "cooler": "Q"}
SHOPS = {"www.startech.com.bd": "startech", "www.ryans.com": "ryans", "www.techlandbd.com": "techland",
         "pcbstore.com.bd": "opencart", "www.sumashtech.com": "opencart"}
PRICE_FACTOR = {"startech": 1.0, "ryans": 1.03, "techland": 0.98, "opencart": 0.97, "woo": 1.01}
# per-host tweak so shops don't all quote the same price
HOST_FACTOR = {"pcbstore.com.bd": 1.0, "www.sumashtech.com": 1.02}
SUMASH_MENU = {"cooler": "/cat/cpu-cooler", "board": "/cat/motherboard", "ram": "/cat/ram", "ssd": "/cat/ssd",
               "gpu": "/cat/graphics-card", "psu": "/cat/power-supply", "case": "/cat/casing"}
MENU_WORDS = {"cooler": "CPU Cooler", "board": "Motherboard", "ram": "RAM", "ssd": "SSD", "gpu": "Graphics Card",
              "psu": "Power Supply", "case": "Casing"}
PER_PAGE = 20


def _rows(block):
    src = ENGINE.read_text(encoding="utf-8")
    a = src.index(f"const {block}=[")
    return re.findall(r"\{id:'([^']+)',(?:ent:1,)?n:'([^']+)'.*?[,{]p:(\d+)", src[a:src.index("];", a)])


def products(seed=4):
    """{category: [(name, price, in_stock), ...]} shared by all three shops."""
    rnd = random.Random(seed)
    out = {}
    for cat, block in TABLES.items():
        rows = []
        for mid, name, p in _rows(block):
            if mid in ("none", "stock"):
                continue
            n = re.sub(r"\s*\(e\.g\. ([^)]+)\)", r" \1", name)
            if cat == "gpu":
                n = rnd.choice(["ZOTAC GAMING", "MSI", "ASUS Dual", "Gigabyte WINDFORCE", "Sapphire Pulse"]) + " " + \
                    n.replace("NVIDIA ", "GeForce ").replace("AMD ", "") + " Graphics Card"
            if cat == "ram":
                n = (n.replace("(1×16, ", "").replace("(2×8 GB)", "(2x8GB)").replace("(2×16 GB)", "(2x16GB)")
                     .replace("(2×32 GB)", "(2x32GB)").replace("(1×8 GB)", "") + " Desktop RAM")
            if cat == "ssd":
                n = n.replace(" GB", "GB").replace(" TB", "TB")
            if cat == "psu":
                n = n.replace(" W ", "W ")
            if cat == "case" and "mATX" not in n:
                n += " Mid Tower Casing"
            rows.append((n, int(int(p) * rnd.uniform(0.9, 1.1)), rnd.random() > 0.15))
        rows.append((f"Generic Accessory Bracket For {cat}", 1500, True))   # must be rejected by the classifier
        out[cat] = rows
    return out


def _slug(n):
    return re.sub(r"[^a-z0-9]+", "-", n.lower()).strip("-")


def _img(n, host):
    return f"https://{host}/image/{_slug(n)}.jpg"


def startech_page(items):
    cards = "".join(
        f'<div class="p-item"><div class="p-item-img"><a href="/{_slug(n)}"><img alt="{n}" '
        f'src="/catalog/view/theme/starship/images/placeholder.png" data-src="{_img(n, "www.startech.com.bd")}"></a></div>'
        f'<div class="p-item-details"><h4 class="p-item-name"><a href="/{_slug(n)}">{n}</a></h4><div class="p-item-price">'
        + (f'<span class="price-new">{p:,}৳</span> <span class="price-old">{int(p * 1.1):,}৳</span>' if s else '<span>Out Of Stock</span>')
        + f'</div><span class="mark">Save: {int(p * .1):,}৳</span></div></div>' for n, p, s in items)
    return f'<html><body><nav><a href="/component/ram">RAM Memory Modules</a></nav><div class="main-content">{cards}</div></body></html>'


def ryans_page(items):
    cards = "".join(
        f'<div class="col"><div class="card"><a href="https://www.ryans.com/{_slug(n)}"><img alt="x" src="{_img(n, "www.ryans.com")}"></a>'
        f'<div class="card-body"><p><a href="https://www.ryans.com/{_slug(n)}">{n}</a></p><ul><li>Spec 1</li></ul><p class="pr">'
        + (f"Tk {p:,}" if s else "Out of Stock") + '</p><a href="javascript:void(0)">Add to Cart</a></div></div></div>' for n, p, s in items)
    return f'<html><body><div class="row">{cards}</div><a href="?page=2">2</a></body></html>'


def techland_page(items):
    cards = "".join(
        f'<li><img data-src="{_img(n, "www.techlandbd.com")}" src="data:image/gif;base64,R0lGOD">'
        f'<a href="https://www.techlandbd.com/{_slug(n)}"><h3>{n}</h3></a><div>'
        + (f"<span>৳ {p:,}</span><del>৳ {int(p * 1.08):,}</del>" if s else "<span>Out of Stock</span>")
        + "</div><div>EMI Start From* ৳ 1,234</div></li>" for n, p, s in items)
    return f'<html><body><ul class="grid">{cards}</ul></body></html>'


def _cut(n, host):
    """Sumash Tech shows only the first 32 characters of a name on its cards."""
    return n[:32] + "..." if host == "www.sumashtech.com" and len(n) > 35 else n


def opencart_page(items, host="pcbstore.com.bd"):
    alt = (lambda n: f"{n} Price In Bangladesh") if host == "www.sumashtech.com" else (lambda n: n)
    cards = "".join(
        f'<div class="product-layout"><div class="product-thumb"><div class="image"><a href="https://{host}/{_slug(n)}">'
        f'<img src="{_img(n, host)}" alt="{alt(n)}"></a></div><div class="caption"><div class="name"><a href="https://{host}/{_slug(n)}">{_cut(n, host)}</a></div>'
        + (f'<div class="price"><span class="price-new">{p:,}৳</span> <span class="price-old">{int(p * 1.06):,}৳</span>'
           f'<span class="price-tax">Ex Tax:{p:,}৳</span></div>' if s else '<div class="price"><span class="price-new">call for price ৳</span></div><div class="stock">Out Of Stock</div>')
        + '</div></div></div>' for n, p, s in items)
    return f'<html><body><div class="main-products">{cards}</div><div class="pagination-results">Showing 1 to 20</div></body></html>'


def woo_page(items, host="shop.example.com.bd"):
    cards = "".join(
        f'<li class="product"><a href="https://{host}/product/{_slug(n)}/" class="woocommerce-LoopProduct-link">'
        f'<img src="{_img(n, host)}" alt="{n} in bd"><h2 class="woocommerce-loop-product__title">{n}</h2>'
        + (f'<span class="price"><ins><span class="amount">৳&nbsp;{p:,}</span></ins></span>' if s else '<span class="soldout">Sold out</span>')
        + '</a></li>' for n, p, s in items)
    return f'<html><body><ul class="products">{cards}</ul></body></html>'


def menu_page(host):
    links = "".join(f'<li><a href="https://{host}{path}">{MENU_WORDS[c]}</a></li>' for c, path in SUMASH_MENU.items())
    return f'<html><body><nav><ul>{links}<li><a href="https://{host}/cat/headphones">Headphones</a></li></ul></nav></body></html>'


MAKERS = {"startech": startech_page, "ryans": ryans_page, "techland": techland_page, "opencart": opencart_page, "woo": woo_page}


def fake_get_factory(shops_cfg, seed=4):
    """Return a replacement for crawl.get(url) that serves the sample pages.
    Ryans-style pages repeat the last page when you go past the end (like some real shops)."""
    prods = products(seed)
    calls = []

    def fake_get(url):
        calls.append(url)
        u = urlparse(url)
        page = int(parse_qs(u.query).get("page", ["1"])[0])
        path = u.path
        m = re.search(r"/page/(\d+)/?$", path)
        if m:
            page, path = int(m.group(1)), path[:m.start()] + "/"
        style = SHOPS[u.netloc]
        shop = next(s for s in shops_cfg if s["base"].endswith(u.netloc))
        first = lambda v: v[0] if isinstance(v, list) else v
        if u.netloc == "www.sumashtech.com":
            if path in [urlparse(h).path or "/" for h in shop.get("discover", [])][:1]:
                return 200, menu_page(u.netloc)
            cat = "cpu" if path == first(shop["categories"]["cpu"]) else next((c for c, pth in SUMASH_MENU.items() if pth == path), None)
        else:
            cat = next((c for c, pth in shop["categories"].items() if path == first(pth)), None)
        if cat is None:
            return 404, ""
        f = PRICE_FACTOR[style] * HOST_FACTOR.get(u.netloc, 1)
        rows = [(n, int(p * f), s) for n, p, s in prods[cat]]
        chunk = rows[(page - 1) * PER_PAGE: page * PER_PAGE]
        if not chunk:
            if style != "ryans":
                return 200, (MAKERS[style]([], u.netloc) if style in ("opencart", "woo") else MAKERS[style]([]))
            chunk = rows[-PER_PAGE:]
        return 200, (MAKERS[style](chunk, u.netloc) if style in ("opencart", "woo") else MAKERS[style](chunk))

    fake_get.calls = calls
    return fake_get
