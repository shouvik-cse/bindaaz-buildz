#!/usr/bin/env python3
"""Build the public website into dist/ with search-engine pages.

  site/            hand-written page, images, catalog.json (from crawl.py)
  site_config.json your domain, verification codes, analytics id
  -> dist/
       index.html                    the builder (SEO tags filled in)
       price/                        price guide hub
       price/graphics-card/ ...      one page per category, with every listing
       price/rtx-5060-8gb/ ...       one page per CPU/GPU model listed by a shop
       builds/                       ready-build hub
       builds/gaming-pc-under-1-lakh-taka/ ...   builder pre-set to that budget
       about/  404.html  sitemap.xml  robots.txt  site.webmanifest

Run:  python scraper/build_site.py      then open dist/index.html via a local server:
      SITE_BASE_URL=http://localhost:8000 python scraper/build_site.py && python -m http.server -d dist 8000
"""
import datetime as dt
import html
import json
import os
import re
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE, DIST = ROOT / "site", ROOT / "dist"
CFG = json.loads((ROOT / "site_config.json").read_text(encoding="utf-8"))
BASE = (os.environ.get("SITE_BASE_URL") or CFG["base_url"]).rstrip("/")  # SITE_BASE_URL=http://localhost:8000 for a local preview
E = html.escape

CATS = {  # builder key: (url slug, English name, Bengali name)
    "cpu": ("processor", "Processor", "প্রসেসর"),
    "gpu": ("graphics-card", "Graphics card", "গ্রাফিক্স কার্ড"),
    "board": ("motherboard", "Motherboard", "মাদারবোর্ড"),
    "ram": ("ram", "Desktop RAM", "র‍্যাম"),
    "ssd": ("ssd", "SSD", "এসএসডি"),
    "psu": ("power-supply", "Power supply", "পাওয়ার সাপ্লাই"),
    "case": ("casing", "PC casing", "কেসিং"),
    "cooler": ("cpu-cooler", "CPU cooler", "সিপিইউ কুলার"),
}
BUILDS = [  # (use, budget)
    *[("gaming", b) for b in (60000, 70000, 80000, 90000, 100000, 120000, 150000, 180000, 200000, 250000, 300000, 400000)],
    *[("creator", b) for b in (100000, 150000, 200000, 300000)],
    *[("office", b) for b in (50000, 60000, 75000)],
]
USE = {"gaming": ("Gaming PC", "গেমিং পিসি"), "creator": ("Video Editing PC", "এডিটিং পিসি"), "office": ("Office & Study PC", "অফিস ও পড়াশোনার পিসি")}


# ---------------------------------------------------------------- helpers
def tk(n):
    s = str(int(n))
    if len(s) <= 3:
        return "৳" + s
    head, tail = s[:-3], s[-3:]
    head = re.sub(r"(\d)(?=(\d{2})+$)", r"\1,", head)
    return f"৳{head},{tail}"


def budget_words(b):
    if b >= 100000:
        lakh = b / 100000
        return (f"{lakh:g} Lakh", f"{lakh:g}-lakh".replace(".", "-"))
    return (f"{b:,}", f"{b}")


def slugify(t):
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def short_name(name):
    return re.sub(r"^(NVIDIA|AMD Radeon|AMD|Intel)\s+", "", name)


def model_slug(name):
    return slugify(short_name(name))


def models(block):
    src = (SITE / "engine.js").read_text(encoding="utf-8")
    a = src.index(f"const {block}=[")
    b = src.index("];", a)
    out = []
    for line in src[a:b].splitlines():
        m = re.search(r"\{id:'([^']+)',n:'([^']+)'", line)
        if not m or m.group(1) == "none":
            continue
        f = lambda k: (re.search(rf"[,{{]{k}:'([^']*)'", line) or [None, ""])[1]
        n = lambda k: int((re.search(rf"[,{{]{k}:(\d+)", line) or [0, 0])[1])
        out.append({"id": m.group(1), "n": m.group(2), "b": f("b"), "s": f("s"), "sp": f("sp"), "p": n("p"), "g": n("g"), "c": n("c"), "w": n("w")})
    return out


AFF = {k: v for k, v in (CFG.get("affiliate_templates") or {}).items() if v}


def buy(url, shop):
    t = AFF.get(shop)
    if not t:
        return url
    from urllib.parse import quote
    return t.replace("{url_encoded}", quote(url, safe="")).replace("{url}", url)


def rel_attr(shop):
    return "sponsored nofollow noopener" if AFF.get(shop) else "nofollow noopener"


def img_tag(src, cls="ti", alt=""):
    if not src:
        return f'<span class="{cls} ph"></span>'
    return f'<img class="{cls}" src="{E(src)}" alt="{E(alt)}" loading="lazy" referrerpolicy="no-referrer" onerror="this.style.visibility=\'hidden\'">'


def head_extra():
    x = []
    if AFF:
        x.append(f"<script>window.AFF={json.dumps(AFF, ensure_ascii=False)}</script>")
    if CFG.get("google_site_verification"):
        x.append(f'<meta name="google-site-verification" content="{E(CFG["google_site_verification"])}">')
    if CFG.get("bing_site_verification"):
        x.append(f'<meta name="msvalidate.01" content="{E(CFG["bing_site_verification"])}">')
    if CFG.get("ga4_measurement_id"):
        gid = E(CFG["ga4_measurement_id"])
        x.append(f'<script async src="https://www.googletagmanager.com/gtag/js?id={gid}"></script>'
                 f"<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag('js',new Date());gtag('config','{gid}');</script>")
    return "\n".join(x)


CSS = """:root{color-scheme:dark;--bg:#0b0814;--panel:#140f22;--line:#2b2244;--ink:#eeebf6;--mute:#a69fbd;--vio:#9d5cff;--vio2:#c9a2ff;--warn:#fbbf24}
*{box-sizing:border-box;min-width:0}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 Barlow,system-ui,sans-serif;overflow-x:clip}
h1,h2,h3{font-family:"Chakra Petch",system-ui,sans-serif;line-height:1.1;text-wrap:balance}h1{font-size:clamp(30px,4.2vw,46px);margin:.2em 0}h2{font-size:clamp(24px,3vw,32px);margin:1.6em 0 .5em}
a{color:var(--vio2)}.wrap{max-width:1180px;margin:0 auto;padding:0 max(5vw,16px)}.bn{font-family:"Hind Siliguri",sans-serif}
nav{border-bottom:1px solid var(--line);position:sticky;top:0;background:rgba(11,8,20,.92);backdrop-filter:blur(8px);z-index:3}
nav .wrap{display:flex;gap:18px;align-items:center;flex-wrap:wrap;padding-block:10px}.brand{font:700 21px "Chakra Petch",system-ui,sans-serif;color:var(--ink);text-decoration:none}.brand i{color:var(--vio)}
nav .l{display:flex;gap:16px;margin-left:auto;flex-wrap:wrap}nav .l a{color:var(--mute);text-decoration:none;font-weight:600}nav .l a:hover{color:var(--ink)}
main{padding:28px 0 60px}.crumbs{font-size:14px;color:var(--mute)}.crumbs a{color:var(--mute)}.lead{font-size:18px;color:var(--mute);max-width:70ch}
.stat{display:flex;flex-wrap:wrap;gap:12px;margin:22px 0}.stat div{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 18px}.stat b{display:block;font:700 26px "Chakra Petch",system-ui,sans-serif;color:var(--vio2);white-space:nowrap}.stat span{font-size:14px;color:var(--mute)}
.btn{display:inline-flex;align-items:center;min-height:46px;padding:0 20px;border-radius:10px;background:var(--vio);color:#fff;font-weight:600;text-decoration:none}
.scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:15px}th,td{padding:9px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{font:600 13px "Chakra Petch",system-ui,sans-serif;color:var(--vio2)}
td.n,th.n{text-align:right;white-space:nowrap}td a{color:var(--ink)}.oos{color:var(--warn)}.note{color:var(--mute);font-size:14px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:8px 24px}.grid a{color:var(--mute);text-decoration:none;padding:4px 0}.grid a:hover{color:var(--vio2)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:14px}.cards a{display:block;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px;text-decoration:none;color:var(--ink)}.cards a:hover{border-color:var(--vio)}.cards b{display:block;font:700 20px "Chakra Petch",system-ui,sans-serif}.cards span{color:var(--mute);font-size:14px}
.ti{width:56px;height:56px;object-fit:contain;background:#fff;border-radius:8px;display:block}.ph{background:var(--panel)!important;border:1px solid var(--line)}
.hero-img{width:180px;height:180px;object-fit:contain;background:#fff;border-radius:14px;float:right;margin:0 0 16px 20px}
.bcard{display:grid!important;gap:8px}.collage{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}.collage img,.collage span{width:100%;aspect-ratio:1;object-fit:contain;background:#fff;border-radius:8px;display:block}.collage span{background:var(--panel2,#1a1430)}
.bcard .tot{font:700 26px "Chakra Petch",system-ui,sans-serif;color:var(--ink)}.bcard small{color:var(--mute);font-size:14px;line-height:1.4}
footer{border-top:1px solid var(--line);padding:26px 0;color:var(--mute);font-size:14px}
nav .l a{display:inline-flex;align-items:center;min-height:44px}
@media(max-width:600px){.hero-img{width:110px;height:110px}
 nav .wrap{flex-wrap:nowrap;gap:12px;padding-block:4px}nav .l{margin-left:0;flex-wrap:nowrap;overflow-x:auto;scrollbar-width:none;-webkit-mask-image:linear-gradient(90deg,#000 85%,transparent)}
 nav .l::-webkit-scrollbar{display:none}nav .l{flex:1 1 auto}nav .l a{flex:none;white-space:nowrap;font-size:15px}.brand{flex:none;font-size:19px}
 main{padding:18px 0 40px}.lead{font-size:16px}.stat div{padding:10px 14px;flex:1 1 40%}.stat b{font-size:22px}
 .btn{width:100%;justify-content:center}.cards{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.cards a{padding:12px}.cards b{font-size:17px}}
@media(max-width:600px){table{font-size:13px}.stack thead{display:none}.stack tr{display:grid;padding-block:8px}.stack td{border:0;padding:2px 0}.stack td.n{text-align:left}}"""


def page(path, title, desc, body, crumbs=(), ld=None, updated=None):
    """Write a generated page to dist/<path>/index.html."""
    url = f"{BASE}/{path}" if path else f"{BASE}/"
    trail = [("Home", f"{BASE}/"), *crumbs]
    bc = {"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": u} for i, (n, u) in enumerate(trail)]}
    graph = [bc] + (ld or [])
    crumb_html = " › ".join(f'<a href="{u}">{E(n)}</a>' for n, u in trail[:-1]) + (f" › {E(trail[-1][0])}" if len(trail) > 1 else "")
    doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(desc)}"><link rel="canonical" href="{url}">
<meta property="og:type" content="website"><meta property="og:site_name" content="বিন্দাজ Buildz"><meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{url}"><meta property="og:image" content="{BASE}/og-image.jpg">
<meta name="twitter:card" content="summary_large_image"><meta name="theme-color" content="#0b0814">
<link rel="icon" href="{BASE}/favicon.ico" sizes="any"><link rel="apple-touch-icon" href="{BASE}/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@600;700&family=Hind+Siliguri:wght@500;700&family=Barlow:wght@400;600&display=swap" rel="stylesheet">
<script type="application/ld+json">{json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)}</script>
{head_extra()}
<style>{CSS}</style></head><body>
<nav><div class="wrap"><a class="brand" href="{BASE}/"><span class="bn">বিন্দাজ</span> <i>Buildz</i></a>
<div class="l"><a href="{BASE}/#builder">Smart Build</a><a href="{BASE}/price/">Price guides</a><a href="{BASE}/builds/">Ready builds</a><a href="{BASE}/about/">About</a></div></div></nav>
<main><div class="wrap"><div class="crumbs">{crumb_html}</div>
{body}
</div></main>
<footer><div class="wrap">বিন্দাজ Buildz: PC builds and price comparison for Bangladesh. Prices are read from shop websites{f", last updated {updated}" if updated else ""}. Confirm price, stock and warranty with the shop before buying. <a href="{BASE}/about/">About &amp; disclaimer</a></div></footer>
</body></html>"""
    out = DIST / path / "index.html" if path else DIST / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    return url


def listing_table(items, show_cat=False):
    rows = []
    for i in sorted(items, key=lambda i: (not (i["st"] and i["p"]), i["p"] or 9e9)):
        stock = "In stock" if i["st"] and i["p"] else '<span class="oos">Out of stock</span>'
        cat = f"<td>{CATS[i['c']][1]}</td>" if show_cat else ""
        rows.append(f'<tr><td>{img_tag(i.get("i"))}</td><td><a href="{E(buy(i["u"], i["s"]))}" rel="{rel_attr(i["s"])}" target="_blank">{E(i["n"])}</a></td>{cat}<td>{E(i["s"])}</td><td>{stock}</td><td class="n">{tk(i["p"]) if i["p"] else "—"}</td></tr>')
    th = "<th>Category</th>" if show_cat else ""
    return f'<div class="scroll"><table class="stack"><thead><tr><th></th><th>Product</th>{th}<th>Shop</th><th>Stock</th><th class="n">Price</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def offers_ld(name, items, url):
    priced = [i for i in items if i["p"]]
    if not priced:
        return []
    instock = [i for i in priced if i["st"]]
    pool = instock or priced
    return [{"@type": "Product", "name": name, "url": url,
             "offers": {"@type": "AggregateOffer", "priceCurrency": "BDT", "lowPrice": min(i["p"] for i in pool),
                        "highPrice": max(i["p"] for i in pool), "offerCount": len(priced),
                        "availability": "https://schema.org/InStock" if instock else "https://schema.org/OutOfStock"}}]


GROUPERS = {
    "board": lambda a: f'{a["ch"].rstrip("MI")} ({a["sock"]})',
    "ram": lambda a: f'{a["gb"]} GB {a["mem"]}',
    "ssd": lambda a: (f'{a["gb"] // 1000} TB' if a["gb"] >= 1000 else f'{a["gb"]} GB') + (f' NVMe Gen{a["gen"]}' if a["nv"] else " SATA"),
    "psu": lambda a: f'{a["w"]} W' + (f' {a["r"]}' if a["r"] else ""),
    "case": lambda a: "ATX mid/full tower" if a["atx"] else "mATX / ITX",
    "cooler": lambda a: f'{a["aio"]} mm liquid' if a["aio"] else ("Dual-tower air" if a["cap"] >= 200 else "Low-profile air" if a["cap"] < 100 else "Tower air"),
}


# ---------------------------------------------------------------- build
def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(SITE, DIST)
    cat_path = SITE / "catalog.json"
    catalog = json.loads(cat_path.read_text(encoding="utf-8")) if cat_path.exists() else {"items": []}
    items = catalog.get("items", [])
    if items:  # small file with only what Smart Build needs; the full catalogue loads later, on demand
        lite = {"updated": catalog.get("updated"), "shops": catalog.get("shops", []), "total": len(items),
                "items": [i for i in items if i.get("m") or i.get("a")]}
        (DIST / "parts.json").write_text(json.dumps(lite, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    updated_iso = catalog.get("updated") or dt.datetime.now(dt.timezone.utc).isoformat()
    upd = dt.datetime.fromisoformat(updated_iso)
    month = upd.strftime("%B %Y")
    upd_h = upd.strftime("%-d %B %Y")
    lastmod = upd.date().isoformat()
    urls = []
    C, G = models("C"), models("G")
    by_model = defaultdict(list)
    by_cat = defaultdict(list)
    for i in items:
        by_cat[i["c"]].append(i)
        if i.get("m"):
            by_model[i["m"]].append(i)

    # ---- model pages
    model_url = {}
    for cat, table in (("cpu", C), ("gpu", G)):
        for m in table:
            L = by_model.get(m["id"])
            if not L:
                continue
            slug = model_slug(m["n"])
            short = short_name(m["n"])
            priced = sorted([i for i in L if i["p"]], key=lambda i: i["p"])
            instock = [i for i in priced if i["st"]]
            best = (instock or priced or [None])[0]
            shops = sorted({i["s"] for i in L})
            url = f"{BASE}/price/{slug}/"
            model_url[m["id"]] = url
            q = "gpu" if cat == "gpu" else "cpu"
            sugg = max(60000, min(600000, round((best["p"] if best else m["p"]) * (2.3 if cat == "gpu" else 4) / 10000) * 10000))
            if best:
                summ = (f"The lowest price for the {E(short)} in Bangladesh today is <b>{tk(best['p'])}</b> at {E(best['s'])}"
                        f"{'' if best['st'] else ' (out of stock)'}. We found {len(L)} listing{'s' if len(L) > 1 else ''} at {', '.join(map(E, shops))}"
                        + (f", priced from {tk(priced[0]['p'])} to {tk(priced[-1]['p'])}" if len(priced) > 1 else "") + ".")
            else:
                summ = f"The {E(short)} is listed at {', '.join(map(E, shops))} but out of stock everywhere right now."
            spec = E(m["sp"]) + (f" · socket {m['s']}" if m["s"] else "") + (f" · about {m['w']} W" if m["w"] else "")
            rel = [x for x in table if x["id"] != m["id"] and x["id"] in by_model and x["b"] == m["b"]]
            rel = sorted(rel, key=lambda x: abs(x["p"] - m["p"]))[:6]
            rel_html = "".join(f'<a href="{BASE}/price/{model_slug(x["n"])}/">{E(short_name(x["n"]))} price</a>' for x in rel)
            pic = next((i.get("i") for i in ([best] if best else []) + L if i and i.get("i")), None)
            body = f"""{img_tag(pic, "hero-img", short) if pic else ""}<h1>{E(short)} price in Bangladesh</h1>
<p class="bn lead">বাংলাদেশে {E(short)} এর দাম · {month}</p>
<p class="lead">{summ}</p>
<div class="stat"><div><b>{tk(best['p']) if best else '—'}</b><span>Lowest price{' (in stock)' if best and best['st'] else ''}</span></div><div><b>{len(L)}</b><span>Listings</span></div><div><b>{len(shops)}</b><span>Shops</span></div></div>
<p class="note">{spec}. Prices checked {upd_h}.</p>
<p><a class="btn" href="{BASE}/?{q}={m['id']}&budget={sugg}#builder">Build a PC with the {E(short)}</a></p>
<h2>All {E(short)} listings</h2>{listing_table(L)}
{f'<h2>Compare similar models</h2><div class="grid">{rel_html}</div>' if rel_html else ''}"""
            urls.append(page(f"price/{slug}", f"{short} Price in Bangladesh ({month}) – Star Tech, Ryans, Tech Land",
                             f"{short} price in BD today: " + (f"from {tk(best['p'])} at {best['s']}. " if best else "") + f"Compare {len(L)} listings from {', '.join(shops)}. {m['sp']}.",
                             body, [("Price guides", f"{BASE}/price/"), (f"{CATS[cat][1]} prices", f"{BASE}/price/{CATS[cat][0]}/"), (short, url)],
                             offers_ld(short, L, url), upd_h))

    # ---- category pages
    cat_cards = []
    for cat, (cslug, cname, bn) in CATS.items():
        L = by_cat.get(cat, [])
        if not L:
            continue
        url = f"{BASE}/price/{cslug}/"
        instock = [i for i in L if i["st"] and i["p"]]
        lo = min((i["p"] for i in instock), default=None)
        hi = max((i["p"] for i in instock), default=None)
        if cat in ("cpu", "gpu"):
            table = C if cat == "cpu" else G
            rows = []
            for m in table:
                ml = by_model.get(m["id"])
                if not ml:
                    continue
                ps = [i for i in ml if i["p"] and i["st"]]
                b = min(ps, key=lambda i: i["p"]) if ps else None
                short = short_name(m["n"])
                rows.append((b["p"] if b else 9e9, f'<tr><td><a href="{model_url[m["id"]]}">{E(short)}</a></td><td>{E(m["sp"])}</td><td>{E(b["s"]) if b else "—"}</td><td class="n">{tk(b["p"]) if b else "Out of stock"}</td></tr>'))
            summary = f'<h2>{cname} models, lowest price</h2><div class="scroll"><table class="stack"><thead><tr><th>Model</th><th>Specs</th><th>Cheapest at</th><th class="n">From</th></tr></thead><tbody>{"".join(r for _, r in sorted(rows))}</tbody></table></div>'
        else:
            groups = defaultdict(list)
            for i in L:
                if i.get("a"):
                    groups[GROUPERS[cat](i["a"])].append(i)
            rows = []
            for g, gl in groups.items():
                ps = [i for i in gl if i["p"] and i["st"]]
                if not ps:
                    continue
                b = min(ps, key=lambda i: i["p"])
                rows.append((b["p"], f'<tr><td>{E(g)}</td><td><a href="{E(buy(b["u"], b["s"]))}" rel="{rel_attr(b["s"])}" target="_blank">{E(b["n"])}</a></td><td>{E(b["s"])}</td><td class="n">{tk(b["p"])}</td></tr>'))
            summary = f'<h2>Cheapest {cname.lower()} by type</h2><div class="scroll"><table class="stack"><thead><tr><th>Type</th><th>Cheapest product</th><th>Shop</th><th class="n">Price</th></tr></thead><tbody>{"".join(r for _, r in sorted(rows))}</tbody></table></div>' if rows else ""
        body = f"""<h1>{cname} price in Bangladesh</h1>
<p class="bn lead">বাংলাদেশে {bn} এর দাম · {month}</p>
<p class="lead">{len(L):,} {cname.lower()} listings from {', '.join(sorted({i['s'] for i in L}))}, {len(instock):,} in stock{f', from {tk(lo)} to {tk(hi)}' if lo else ''}. Checked {upd_h}.</p>
<p><a class="btn" href="{BASE}/#builder">Build a full PC with these prices</a></p>
{summary}
<h2>Every {cname.lower()} listed</h2>{listing_table(L)}"""
        urls.append(page(f"price/{cslug}", f"{cname} Price in Bangladesh ({month}) – Compare {len(L):,} Listings",
                         f"{cname} price list in BD: {len(L):,} products from Star Tech, Ryans and Tech Land" + (f", in stock from {tk(lo)}" if lo else "") + ". Updated " + upd_h + ".",
                         body, [("Price guides", f"{BASE}/price/"), (f"{cname} prices", url)], None, upd_h))
        cat_cards.append(f'<a href="{url}"><b>{cname}</b><span>{len(L):,} listings{f" · from {tk(lo)}" if lo else ""}</span></a>')

    # ---- price hub
    model_links = "".join(f'<a href="{u}">{E(short_name(m["n"]))} price</a>' for m in C + G if (u := model_url.get(m["id"])))
    if cat_cards:
        urls.append(page("price", f"PC Component Price List in Bangladesh ({month})",
                         "Compare today's prices for processors, graphics cards, motherboards, RAM, SSDs, power supplies, casings and coolers from Star Tech, Ryans and Tech Land.",
                         f"""<h1>PC component prices in Bangladesh</h1><p class="bn lead">কম্পিউটার পার্টসের দাম · {month}</p>
<p class="lead">{len(items):,} products from {', '.join(catalog.get('shops', []))}, checked {upd_h}.</p>
<div class="cards">{''.join(cat_cards)}</div><h2>Processor and graphics card models</h2><div class="grid">{model_links}</div>""",
                         [("Price guides", f"{BASE}/price/")], None, upd_h))

    # ---- ready builds: copies of the builder, pre-set
    tpl = (DIST / "index.html").read_text(encoding="utf-8")
    build_cards = defaultdict(list)
    EXPECT = [(70000, "esports games like Valorant, CS2 and PUBG at 1080p"), (100000, "most games at 1080p on high settings"),
              (160000, "1080p ultra and 1440p high"), (250000, "1440p ultra with high frame rates"), (10**9, "1440p ultra and 4K gaming")]
    pre = {}
    try:
        spec = json.dumps([{"use": u, "budget": b} for u, b in BUILDS])
        res = subprocess.run(["node", str(ROOT / "scraper" / "precompute.mjs"), str(SITE / "engine.js"), str(cat_path), spec],
                             capture_output=True, text=True, timeout=300, check=True)
        pre = {(r["use"], r["budget"]): r for r in json.loads(res.stdout)}
    except Exception as e:  # Node missing: ready-build pages still work, just without the static preview
        print("Ready-build preview skipped:", e)
    for use, b in BUILDS:
        words, wslug = budget_words(b)
        en, bn = USE[use]
        slug = f"{slugify(en)}-under-{wslug}-taka"
        url = f"{BASE}/builds/{slug}/"
        title = f"Best {en} Build Under {words} Taka in Bangladesh ({month})"
        if use == "gaming":
            exp = next(t for lim, t in EXPECT if b <= lim)
            intro = f"The best gaming PC you can build for {tk(b)} right now, from parts in stock at Bangladeshi shops. Expect {exp}. Prices update several times a day, and you can swap any part."
        elif use == "creator":
            intro = f"A {tk(b)} PC for video editing, design and 3D work, weighted towards more CPU cores and a graphics card with good editing support. Built from parts in stock today."
        else:
            intro = f"A quiet, reliable {tk(b)} PC for office work, online classes and everyday use, with today's prices. No graphics card needed: the processor's built-in graphics drive the display."
        page_html = tpl
        page_html = re.sub(r"<title>.*?</title>", f"<title>{E(title)}</title>", page_html, count=1)
        page_html = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{E(intro[:155])}">', page_html, count=1)
        page_html = page_html.replace('<link rel="canonical" href="__BASE__/">', f'<link rel="canonical" href="{url}">')
        page_html = page_html.replace('<meta property="og:url" content="__BASE__/">', f'<meta property="og:url" content="{url}">')
        page_html = re.sub(r'<meta property="og:title" content="[^"]*">', f'<meta property="og:title" content="{E(title)}">', page_html, count=1)
        page_html = re.sub(r'<h1 id="h1">.*?</h1>', f'<h1 id="h1">{E(en)} under <em>{tk(b)}</em></h1>', page_html, count=1, flags=re.S)
        page_html = re.sub(r'<p id="intro">.*?</p>', f'<p id="intro">{E(intro)}</p><p class="bn note">{tk(b)} বাজেটে {bn} বিল্ড</p>', page_html, count=1, flags=re.S)
        page_html = page_html.replace("<!--HEAD-EXTRA-->", f'<script>window.PRESET={{"budget":{b},"use":"{use}"}};window.ROOT="{BASE}/"</script><!--HEAD-EXTRA-->')
        # this copy lives two folders down, so its own files (engine.js, logo, icons) must point at the site root
        page_html = re.sub(r'\b(src|href)="(?!https?:|#|/|mailto:|data:|__BASE__)([^"]+\.(?:js|webp|png|ico|jpg|webmanifest|json))"',
                           lambda m: f'{m.group(1)}="{BASE}/{m.group(2)}"', page_html)
        r = pre.get((use, b))
        if r and r["ok"]:  # static preview of the build, replaced by the live builder once the page's script runs
            rows = "".join(f'<li class="row">{img_tag(pt.get("img"), "th")}<div class="info"><span class="cat">{E(pt["lab"])}</span><div class="nm">{E(pt["n"])}</div><div class="sp">{E(pt.get("sp") or "")}</div></div>'
                           f'<div class="side"><span class="pr">{tk(pt["p"]) if pt.get("p") else "Included"}</span>'
                           + (f'<a class="buy" href="{E(buy(pt["url"], pt["shop"]))}" target="_blank" rel="{rel_attr(pt["shop"])}">Buy at {E(pt["shop"])}</a>' if pt.get("url") else "") + "</div></li>" for pt in r["parts"])
            snap = f'<div class="total"><div><div class="sub">Build total</div><div class="big">{tk(r["total"])}</div></div><div class="tags"><span class="tag">{E(r["tier"])}</span></div></div><ul class="rows">{rows}</ul>'
            page_html = page_html.replace('<div class="card sheet" id="sheet" aria-live="polite"></div>', f'<div class="card sheet" id="sheet" aria-live="polite">{snap}</div>', 1)
        (DIST / "builds" / slug).mkdir(parents=True, exist_ok=True)
        (DIST / "builds" / slug / "index.html").write_text(page_html, encoding="utf-8")
        urls.append(url)
        if r and r["ok"]:
            pk = {pt["k"]: pt for pt in r["parts"]}
            col = "".join(img_tag(pk[k].get("img"), "") if pk[k].get("img") else "<span></span>" for k in ("case", "gpu", "cpu", "board"))
            main_parts = " + ".join(E(pk[k]["n"]) for k in ("gpu", "cpu") if pk[k]["n"] != "No graphics card")
            build_cards[use].append(f'<a class="bcard" href="{url}"><div class="collage">{col}</div><span>{en} under {words} taka</span><span class="tot">{tk(r["total"])}</span><small>{main_parts}</small></a>')
        else:
            build_cards[use].append(f'<a class="bcard" href="{url}"><b>{tk(b)}</b><span>{en} under {words} taka</span></a>')

    urls.append(page("builds", f"Ready PC Builds by Budget in Bangladesh ({month})",
                     "Gaming, editing and office PC builds for every budget from ৳45,000 to ৳4 lakh, with today's prices from Star Tech, Ryans and Tech Land.",
                     "<h1>Ready PC builds by budget</h1><p class=\"bn lead\">বাজেট অনুযায়ী পিসি বিল্ড</p>"
                     "<p class=\"lead\">Each build is made fresh from parts in stock today and keeps every part compatible. Open one to see the parts and swap anything you like.</p>"
                     + "".join(f"<h2>{USE[u][0]} builds</h2><div class=\"cards\">{''.join(c)}</div>" for u, c in build_cards.items()),
                     [("Ready builds", f"{BASE}/builds/")], None, upd_h))

    # ---- about
    contact = (f'Email: <a href="mailto:{E(CFG["contact_email"])}">{E(CFG["contact_email"])}</a>' if CFG.get("contact_email") else "")
    fb = (f' · <a href="{E(CFG["facebook_page"])}">Facebook page</a>' if CFG.get("facebook_page") else "")
    urls.append(page("about", "About বিন্দাজ Buildz – How Prices Work & Disclaimer",
                     "বিন্দাজ Buildz is an independent PC-builder and price-comparison site for Bangladesh. How we collect prices, how builds are chosen, and our disclaimer.",
                     f"""<h1>About বিন্দাজ Buildz</h1>
<p class="lead">বিন্দাজ Buildz helps people in Bangladesh plan a desktop PC: pick a budget, get a complete and compatible build, and see where each part is cheapest today.</p>
<h2>Where prices come from</h2><p>A program reads the public category pages of Star Tech, Ryans and Tech Land several times a day and records each product's name, price, stock status and link. We are not affiliated with any of these shops and don't sell anything ourselves. Every product links to the shop's own page.</p>
<h2>How builds are chosen</h2><p>The builder tries every processor and graphics card that fits your budget and choices. It scores each pairing for gaming, editing or office use and avoids lopsided pairs. It then adds a motherboard of the right class for the processor, and RAM, storage, power supply, case and cooler that are compatible and in stock. It checks socket, memory type, wattage, cooling and case size.</p>
<h2>Disclaimer</h2><p>Prices and stock change quickly and may differ in the shop, online or with bundle offers. Always confirm the final price, stock and warranty with the shop before you pay. Performance descriptions are general guidance, not guarantees.</p>
<h2>Privacy</h2><p>The site has no accounts. Your budget and choices are remembered only in your own browser.{' We use Google Analytics to count visits.' if CFG.get('ga4_measurement_id') else ''}</p>
<h2>Contact</h2><p>{contact}{fb or ''}{'' if contact or fb else 'Shop owners and visitors can reach us through our social pages.'}</p>""",
                     [("About", f"{BASE}/about/")], None, upd_h))

    # ---- fill the main page: SEO links hub + extra head tags
    links = ("<h2>Price guides and ready builds</h2><div class=\"linkgrid\">"
             + "".join(f'<a href="{BASE}/price/{s}/">{n} price in BD</a>' for k, (s, n, _) in CATS.items() if by_cat.get(k))
             + "".join(f'<a href="{BASE}/builds/{slugify(USE[u][0])}-under-{budget_words(b)[1]}-taka/">{USE[u][0]} under {tk(b)}</a>' for u, b in BUILDS if u == "gaming")
             + "".join(f'<a href="{model_url[m["id"]]}">{E(short_name(m["n"]))} price</a>' for m in G if m["id"] in model_url)
             + "</div>")
    for f in DIST.rglob("*.html"):
        t = f.read_text(encoding="utf-8")
        t = t.replace("<!--LINKS-->", links).replace("<!--HEAD-EXTRA-->", head_extra())
        t = t.replace("__BASE__", BASE)
        f.write_text(t, encoding="utf-8")
    urls.insert(0, f"{BASE}/")

    # ---- 404, robots, sitemap, manifest
    page("404-tmp", "Page not found – বিন্দাজ Buildz", "This page doesn't exist.",
         f'<h1>Page not found</h1><p class="lead">The page may have moved. Try the <a href="{BASE}/">PC builder</a> or the <a href="{BASE}/price/">price guides</a>.</p>')
    (DIST / "404-tmp" / "index.html").rename(DIST / "404.html")
    (DIST / "404-tmp").rmdir()
    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n", encoding="utf-8")
    sm = "".join(f"<url><loc>{E(u)}</loc><lastmod>{lastmod}</lastmod></url>" for u in dict.fromkeys(urls))
    (DIST / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>\n', encoding="utf-8")
    (DIST / "site.webmanifest").write_text(json.dumps({"name": "বিন্দাজ Buildz", "short_name": "Bindaaz Buildz", "start_url": f"{BASE}/",
                                                       "display": "standalone", "background_color": "#0b0814", "theme_color": "#0b0814",
                                                       "icons": [{"src": f"{BASE}/icon-512.png", "sizes": "512x512", "type": "image/png"},
                                                                 {"src": f"{BASE}/apple-touch-icon.png", "sizes": "180x180", "type": "image/png"}]},
                                                      ensure_ascii=False), encoding="utf-8")
    if (ROOT / "CNAME").exists():
        shutil.copy(ROOT / "CNAME", DIST / "CNAME")
    print(f"Built {len(set(urls))} pages into {DIST}  (base URL {BASE})")


if __name__ == "__main__":
    main()
