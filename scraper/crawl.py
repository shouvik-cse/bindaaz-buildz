#!/usr/bin/env python3
"""বিন্দাজ Buildz product crawler.

Walks every category page listed in scraper/shops.json (all pages of processors,
graphics cards, motherboards, RAM, SSDs, power supplies, cases, coolers), reads
each product card (name, price, stock, link), sorts products into builder parts
with classify.py, and writes site/catalog.json:

  {"updated": "...", "shops": [...],
   "items": [{"id": "a1b2c3d4", "s": "Star Tech", "c": "gpu", "n": "ZOTAC ... RTX 5060 ...",
              "p": 39900, "st": 1, "u": "https://...", "m": "rtx5060"},              # CPU/GPU model
             {"id": "...", "c": "board", ..., "a": {"sock": "AM5", "ch": "B650M", ...}}]}  # part attributes

Usage:
  python scraper/crawl.py                      # crawl everything -> site/catalog.json
  python scraper/crawl.py --check              # page 1 of every category: how many products found
  python scraper/crawl.py --shop "Star Tech" --cat gpu --pages 2
  python scraper/crawl.py --test URL           # print the products found on one listing page
"""
import argparse
import datetime as dt
import hashlib
import json
import random
import re
import sys
import time
import urllib.robotparser
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlencode, parse_qsl, urlunparse

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
from classify import classify  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SHOPS = ROOT / "scraper" / "shops.json"
OUT = ROOT / "site" / "catalog.json"

UA = "BindaazBuildzPriceBot/2.0 (PC-builder price comparison)"
DELAY = (2.0, 4.0)
MAX_PAGES = 80
PRICE_MIN, PRICE_MAX = 300, 2_000_000

session = requests.Session()
session.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.8"})
_robots, _last = {}, {}

BAD_HREF = re.compile(r"(/category/|[?&](page|sort|limit|order|filter)=|cart|compare|wishlist|login|register|account|checkout|"
                      r"javascript:|tel:|mailto:|/blog|/brand|/offer|/tag/|/search|whatsapp|facebook|youtube|#)", re.I)
PRICE_RX = re.compile(r"(?:৳|Tk\.?|BDT)\s*([\d,]{3,})|([\d,]{3,})\s*৳")
NOISE_RX = re.compile(r"(Save|Regular\s*Price|Was|EMI[^৳]{0,30}|Discount)\s*:?\s*(?:৳|Tk\.?|BDT)?\s*[\d,]+\s*৳?", re.I)
OOS_RX = re.compile(r"out\s*of\s*stock|stock\s*out|up\s*coming|pre[\s-]*order|to be announced|call for price|sold out", re.I)


def now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def clean(t):
    return re.sub(r"\s+", " ", t or "").strip()


def to_int(s):
    try:
        v = int(re.sub(r"[^\d]", "", s))
    except ValueError:
        return None
    return v if PRICE_MIN <= v <= PRICE_MAX else None


def allowed(url):
    p = urlparse(url)
    base = f"{p.scheme}://{p.netloc}"
    if base not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            r = session.get(base + "/robots.txt", timeout=15)
            rp.parse(r.text.splitlines() if r.ok else [])
        except requests.RequestException:
            rp.parse([])
        _robots[base] = rp
    return _robots[base].can_fetch(UA, url)


def get(url):
    """Polite GET. Returns (status, html)."""
    if not allowed(url):
        return "robots", ""
    host = urlparse(url).netloc
    wait = random.uniform(*DELAY) - (time.time() - _last.get(host, 0))
    if wait > 0:
        time.sleep(wait)
    for attempt in range(3):
        _last[host] = time.time()
        try:
            r = session.get(url, timeout=30)
            if r.status_code == 200:
                return 200, r.text
            if r.status_code in (403, 404, 410, 429):
                return r.status_code, ""
        except requests.RequestException:
            pass
        time.sleep(5 * (attempt + 1))
    return "failed", ""


OLD_RX = re.compile(r"old|regular|save|emi|was|strike|before|off|mrp|discount-amount", re.I)
LEAF_RX = re.compile(r"^(?:(?:৳|Tk\.?|BDT)\s*[\d,]{3,}(?:\.\d+)?|[\d,]{3,}(?:\.\d+)?\s*(?:৳|Tk\.?))$")


def card_price(node_or_text):
    """Current price + stock (1/0) from a product card.

    Given an element, the first small element whose whole text is a price
    ("39,900৳", "৳ 41,999", "Tk 48,300") wins, skipping struck-through, "old",
    "regular", "save" and "EMI" prices. Plain text falls back to a regex scan."""
    if isinstance(node_or_text, str):
        text, node = node_or_text, None
    else:
        node, text = node_or_text, clean(node_or_text.get_text(" "))
    price = None
    if node is not None:
        for el in [node, *node.find_all(True)]:
            t = clean(el.get_text(" "))
            if len(t) > 40 or not LEAF_RX.match(t):
                continue
            bad = False
            for anc in [el, *el.parents]:
                if anc is node.parent:
                    break
                if anc.name in ("del", "s", "strike") or OLD_RX.search(" ".join(anc.get("class", [])) + " " + (anc.get("id") or "")):
                    bad = True
                    break
            if not bad:
                price = to_int(t)
                if price:
                    break
    if price is None:
        t = NOISE_RX.sub(" ", text)
        for m in PRICE_RX.finditer(t):
            price = to_int(m.group(1) or m.group(2))
            if price:
                break
    if OOS_RX.search(text):
        return price, 0
    return price, 1 if price else 0


IMG_SKIP = re.compile(r"placeholder|loader|loading|blank|spinner|no[-_]?image|1x1|pixel|lazy\.(gif|png|svg)|\.svg$", re.I)


def card_img(node, base):
    """Product photo URL from a card: lazy-load attributes first, then src."""
    for img in node.find_all("img"):
        for attr in ("data-src", "data-lazy-src", "data-original", "data-lazy", "data-srcset", "srcset", "src"):
            v = (img.get(attr) or "").strip()
            if not v:
                continue
            v = v.split(",")[0].strip().split(" ")[0]
            if v.startswith("data:") or IMG_SKIP.search(v):
                continue
            return urljoin(base, v)
    return None


def page_url(base, n):
    if n == 1:
        return base
    p = urlparse(base)
    q = dict(parse_qsl(p.query))
    q["page"] = str(n)
    return urlunparse(p._replace(query=urlencode(q)))


def cards_by_selector(soup, url, sel):
    out = []
    for item in soup.select(sel["item"]):
        a = item.select_one(sel.get("name", "a[href]")) or item.find("a", href=True)
        if not a or not a.get("href"):
            continue
        name = clean(a.get_text(" ")) or a.get("title", "")
        pel = item.select_one(sel["price"]) if sel.get("price") else None
        price, st = card_price(pel or item)
        if OOS_RX.search(item.get_text(" ")):
            st = 0
        out.append({"n": name, "p": price, "st": st, "u": urljoin(url, a["href"]).split("#")[0], "i": card_img(item, url)})
    return out


def cards_generic(soup, url, skip_paths):
    """Find product cards without knowing the site's HTML: every same-site link with a
    product-like name, grown outward until its box contains a price or stock text but
    no other product link."""
    host = urlparse(url).netloc
    cand = {}
    for a in soup.find_all("a", href=True):
        href = urljoin(url, a["href"]).split("#")[0]
        p = urlparse(href)
        if p.netloc != host or BAD_HREF.search(a["href"]) or p.path.rstrip("/") in skip_paths or p.path in ("", "/"):
            continue
        name = clean(a.get_text(" ")) or clean(a.get("title")) or (clean(a.img.get("alt")) if a.img else "")
        if len(name) < 12 or len(name) > 250:
            continue
        if href not in cand or len(name) > len(cand[href][0]):
            cand[href] = (name, a)
    out = []
    for href, (name, a) in cand.items():
        node, card = a, None
        for _ in range(8):
            parent = node.parent
            if parent is None or parent.name in ("body", "html"):
                break
            others = {urljoin(url, x["href"]).split("#")[0] for x in parent.find_all("a", href=True)} & cand.keys()
            if len(others) > 1:
                break
            node = parent
            txt = clean(node.get_text(" "))
            if PRICE_RX.search(txt) or OOS_RX.search(txt):
                card = node
                break
        if card is None:
            continue
        price, st = card_price(card)
        img, box = card_img(card, url), card
        for _ in range(3):  # photo may sit just outside the price box, e.g. in a sibling link
            if img or box.parent is None:
                break
            others = {urljoin(url, x["href"]).split("#")[0] for x in box.parent.find_all("a", href=True)} & cand.keys()
            if len(others) > 1:
                break
            box = box.parent
            img = card_img(box, url)
        out.append({"n": name, "p": price, "st": st, "u": href, "i": img})
    return out


def parse_listing(html, url, shop):
    soup = BeautifulSoup(html, "html.parser")
    skip = {urlparse(urljoin(shop["base"], c)).path.rstrip("/") for c in shop["categories"].values()}
    cards = cards_by_selector(soup, url, shop["card"]) if shop.get("card") else []
    if not cards:
        cards = cards_generic(soup, url, skip)
    seen, out = set(), []
    for c in cards:
        if c["u"] not in seen and c["n"]:
            seen.add(c["u"])
            out.append(c)
    return out


def crawl_category(shop, cat, path, max_pages):
    base = urljoin(shop["base"], path)
    items, seen = [], set()
    for n in range(1, max_pages + 1):
        url = page_url(base, n)
        status, html = get(url)
        if status != 200:
            print(f"    page {n}: {status}", file=sys.stderr)
            return items, (status if n == 1 else None)
        cards = parse_listing(html, url, shop)
        new = [c for c in cards if c["u"] not in seen]
        if not new:
            break
        for c in new:
            seen.add(c["u"])
            items.append(c)
    return items, None


def item_id(url):
    return hashlib.sha1(url.encode()).hexdigest()[:10]


def finish(raw, shop, cat):
    out = []
    for c in raw:
        model, attrs = classify(cat, c["n"], c["p"])
        it = {"id": item_id(c["u"]), "s": shop, "c": cat, "n": c["n"], "p": c["p"], "st": c["st"], "u": c["u"]}
        if c.get("i"):
            it["i"] = c["i"]
        if model:
            it["m"] = model
        if attrs:
            it["a"] = attrs
        out.append(it)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="only page 1 of each category; print counts")
    ap.add_argument("--test", metavar="URL", help="print products found on one listing page")
    ap.add_argument("--shop")
    ap.add_argument("--cat")
    ap.add_argument("--pages", type=int, default=MAX_PAGES)
    args = ap.parse_args()
    cfg = json.loads(SHOPS.read_text(encoding="utf-8"))["shops"]

    if args.test:
        host = urlparse(args.test).netloc
        shop = next((s for s in cfg if urlparse(s["base"]).netloc == host), {"name": host, "base": args.test, "categories": {}})
        status, html = get(args.test)
        if status != 200:
            print("HTTP", status)
            return 1
        cards = parse_listing(html, args.test, shop)
        for c in cards:
            print(f"{c['p'] or '-':>8}  {'in ' if c['st'] else 'OUT'}  {c['n'][:80]}  {'[photo]' if c.get('i') else '[no photo]'}")
        print(f"\n{len(cards)} products")
        return 0

    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"items": []}
    keep = {}
    for it in old.get("items", []):
        keep.setdefault((it["s"], it["c"]), []).append(it)

    items, report = [], []
    for shop in cfg:
        if args.shop and shop["name"] != args.shop:
            continue
        for cat, path in shop["categories"].items():
            if args.cat and cat != args.cat:
                continue
            print(f"{shop['name']} / {cat}: {path}")
            raw, err = crawl_category(shop, cat, path, 1 if args.check else args.pages)
            got = finish(raw, shop["name"], cat)
            used = sum(1 for g in got if "m" in g or "a" in g)
            report.append((shop["name"], cat, len(got), used, err))
            print(f"    {len(got)} products ({used} usable by the builder)" + (f"  ERROR {err}" if err else ""))
            if not got and keep.get((shop["name"], cat)):
                print("    keeping last run's products for this category (marked stale)")
                got = [dict(i, stale=1) for i in keep[(shop["name"], cat)]]
            items.extend(got)

    if args.check:
        print("\nCheck only, nothing written.")
        return 0
    if args.shop or args.cat:  # partial run: merge with the untouched rest
        done = {(r[0], r[1]) for r in report}
        items += [i for i in old.get("items", []) if (i["s"], i["c"]) not in done]

    shops = sorted({i["s"] for i in items})
    OUT.write_text(json.dumps({"updated": now(), "shops": shops, "items": items},
                              ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"\n{len(items)} products from {len(shops)} shops -> {OUT}")
    bad = [r for r in report if r[4] or r[2] == 0]
    if bad:
        print("Categories with problems:", ", ".join(f"{r[0]}/{r[1]} ({r[4] or 'no products'})" for r in bad))
    return 0


if __name__ == "__main__":
    sys.exit(main())
