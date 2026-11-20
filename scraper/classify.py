"""Turn a shop product name into something the PC builder understands.

classify(cat, name, price) -> (model_id or None, attrs dict or None)

cpu / gpu   -> model id from the builder's own CPU/GPU table (read from site/index.html)
board       -> socket, chipset, tier, DDR type, form factor, Wi-Fi
ram         -> DDR type, total GB, sticks, MHz
ssd         -> GB, NVMe, PCIe gen
psu         -> watts, 80+ rating
case        -> ATX support, tier (from price)
cooler      -> heat capacity in watts, AIO or air
Products that don't fit (laptop RAM, external SSDs, case fans...) return (None, None):
they still appear in the product list, the builder just doesn't use them.
"""
import re
from pathlib import Path

INDEX = Path(__file__).resolve().parent.parent / "site" / "engine.js"


def _table(block):
    src = INDEX.read_text(encoding="utf-8")
    start = src.index(f"const {block}=[")
    end = src.index("];", start)
    return re.findall(r"\{id:'([^']+)',n:'([^']+)'", src[start:end])


def _cpu_patterns():
    pats = []
    for mid, name in _table("C"):
        tok = re.split(r"[\s-]", name)[-1].upper()          # 5600, 12400F, 245K, 9800X3D
        need = "RYZEN" if "Ryzen" in name else ("ULTRA" if "Ultra" in name else "CORE|INTEL")
        rx = re.compile(rf"(?<![A-Z0-9]){re.escape(tok)}(?![A-Z0-9])")
        pats.append((mid, rx, re.compile(need)))
    return pats


SUFFIX = r"(?:TI|XT|XTX|SUPER|GRE|X)"


def _gpu_patterns():
    pats = []
    for mid, name in _table("G"):
        if mid == "none":
            continue
        core = re.sub(r"^(NVIDIA|AMD Radeon|AMD|Intel)\s+", "", name)
        vram = re.search(r"(\d+)GB$", core)
        core = re.sub(r"\s*\d+GB$", "", core).upper()          # RTX 5060 TI, RX 9070 XT, ARC B580
        words = core.split()
        body = r"\s*-?\s*".join(map(re.escape, words))
        tail = "" if re.fullmatch(SUFFIX, words[-1]) else rf"(?!\s*-?\s*{SUFFIX}\b)"
        rx = re.compile(rf"(?<![A-Z0-9]){body}(?![0-9]){tail}")
        pats.append((mid, rx, int(vram.group(1)) if vram else None))
    return pats


CPU_P = _cpu_patterns()
GPU_P = _gpu_patterns()

CHIPSETS = {  # chipset: (socket, base tier, price at which a board counts as one tier higher)
    "A520": ("AM4", 1, 99999), "B450": ("AM4", 1, 99999), "B550": ("AM4", 2, 20000), "X570": ("AM4", 3, 99999),
    "A620": ("AM5", 1, 99999), "B650": ("AM5", 2, 25000), "B650E": ("AM5", 3, 99999), "B850": ("AM5", 3, 99999),
    "X670": ("AM5", 4, 99999), "X670E": ("AM5", 4, 99999), "X870": ("AM5", 4, 99999), "X870E": ("AM5", 4, 99999),
    "H610": ("LGA1700", 1, 99999), "B660": ("LGA1700", 2, 21000), "B760": ("LGA1700", 2, 21000),
    "H770": ("LGA1700", 3, 99999), "Z690": ("LGA1700", 4, 99999), "Z790": ("LGA1700", 4, 99999),
    "H810": ("LGA1851", 1, 99999), "B860": ("LGA1851", 2, 26000), "Z890": ("LGA1851", 4, 99999),
}
CHIP_RX = re.compile(r"(?<![A-Z0-9])(" + "|".join(sorted(CHIPSETS, key=len, reverse=True)) + r")(M|I)?(?![0-9])")


def norm_gb(n, unit):
    gb = float(n) * (1000 if unit == "TB" else 1)
    for size, lo, hi in [(256, 230, 270), (512, 470, 530), (1000, 900, 1100), (2000, 1800, 2200), (4000, 3600, 4400), (8000, 7000, 9000)]:
        if lo <= gb <= hi:
            return size
    return int(gb)


MIN_PRICE = {"cpu": 3000, "gpu": 5000, "board": 5000, "ram": 1500, "ssd": 1500, "psu": 2000, "case": 2000, "cooler": 800}
ACCESSORY = re.compile(r"BRACKET|HOLDER|MOUNT(?:ING)? KIT|ACCESSOR|SCREW|\bCABLE\b|EXTENSION|RISER|ADAPTER|CONVERTER|LED STRIP|DUST FILTER|"
                       r"SPARE|REPLACEMENT|THERMAL PASTE|\bPASTE\b|FAN HUB|CONTROLLER|BACKPLATE|SUPPORT STAND|ANTI[- ]?SAG")


def classify(cat, name, price=None):
    u = " " + name.upper().replace("–", "-") + " "
    if re.search(r"LAPTOP|NOTEBOOK|SO-?DIMM|MACBOOK", u) or ACCESSORY.search(u):
        return None, None
    if price and price < MIN_PRICE.get(cat, 0):
        return None, None

    if cat == "cpu":
        if re.search(r"THREADRIPPER|XEON|EPYC|COOLER ONLY", u):
            return None, None
        for mid, rx, need in CPU_P:
            if rx.search(u) and need.search(u):
                return mid, None
        return None, None

    if cat == "gpu":
        if re.search(r"RTX\s*PRO|QUADRO|RTX\s*A\d{4}|RIGHT ANGLE|RISER|BRACKET|HOLDER|SUPPORT|CABLE", u):
            return None, None
        hits = [(mid, v) for mid, rx, v in GPU_P if rx.search(u)]
        if not hits:
            return None, None
        if len(hits) > 1:  # same chip, different VRAM: pick by the GB in the name
            m = re.search(r"(\d{1,2})\s*G(?:B|\b)", u)
            gb = int(m.group(1)) if m else None
            pick = [h for h in hits if h[1] == gb] or sorted(hits, key=lambda h: h[1] or 0)
            return pick[0][0], None
        return hits[0][0], None

    if cat == "board":
        m = CHIP_RX.search(u)
        if not m:
            return None, None
        chip = m.group(1)
        sock, tier, bump = CHIPSETS[chip]
        if price and price >= bump:
            tier += 1
        if sock in ("AM5", "LGA1851"):
            mem = "DDR5"
        elif sock == "AM4":
            mem = "DDR4"
        else:
            mem = "DDR4" if re.search(r"DDR4|\bD4\b|-D4\b", u) else "DDR5"
        if m.group(2) == "I" or "ITX" in u:
            ff = "ITX"
        elif m.group(2) == "M" or re.search(r"M-?ATX|MICRO", u):
            ff = "mATX"
        else:
            ff = "ATX"
        wifi = bool(re.search(r"WI-?FI|\bAX\b|WIFI", u))
        return None, {"sock": sock, "ch": chip + (m.group(2) or ""), "t": min(tier, 4), "mem": mem, "ff": ff, "wifi": int(wifi)}

    if cat == "ram":
        mt = re.search(r"DDR\s*([45])", u)
        if not mt:
            return None, None
        kit = re.search(r"(\d)\s*[X×*]\s*(\d{1,2})\s*GB", u)
        if kit:
            sticks, gb = int(kit.group(1)), int(kit.group(1)) * int(kit.group(2))
        else:
            c = re.search(r"(\d{1,3})\s*GB", u)
            if not c:
                return None, None
            gb, sticks = int(c.group(1)), (2 if re.search(r"\bKIT\b|DUAL", u) else 1)
        if gb not in (8, 16, 24, 32, 48, 64, 96, 128):
            return None, None
        mhz = re.search(r"(\d{4})\s*(?:MHZ|MT/S|HZ)", u) or re.search(r"DDR[45]-(\d{4})", u)
        return None, {"mem": "DDR" + mt.group(1), "gb": gb, "k": sticks, "mhz": int(mhz.group(1)) if mhz else None}

    if cat == "ssd":
        if re.search(r"PORTABLE|EXTERNAL|USB|ENCLOSURE|HEATSINK|ADAPTER|CADDY|\bHDD\b|HARD DISK|MSATA", u):
            return None, None
        c = re.search(r"(\d+(?:\.\d+)?)\s*(TB|GB)", u)
        if not c:
            return None, None
        nv = bool(re.search(r"NVME|M\.?2|PCIE|GEN\s*[345]", u)) and "SATA" not in u
        gen = 5 if re.search(r"GEN\s*5|PCIE\s*5", u) else 4 if re.search(r"GEN\s*4|PCIE\s*4", u) else 3
        return None, {"gb": norm_gb(c.group(1), c.group(2)), "nv": int(nv), "gen": gen if nv else 0}

    if cat == "psu":
        if re.search(r"ADAPTER|\bUPS\b|CABLE|EXTENSION|SLEEVED", u):
            return None, None
        w = re.search(r"(\d{3,4})\s*W(?:ATT)?\b", u) or re.search(r"\b(\d{3,4})\b", u)
        if not w or not 250 <= int(w.group(1)) <= 2000:
            return None, None
        rating = next((r for r in ("TITANIUM", "PLATINUM", "GOLD", "SILVER", "BRONZE", "WHITE") if r in u), "")
        return None, {"w": int(w.group(1)), "r": rating.title()}

    if cat == "case":
        if re.search(r"\bFANS?\b|PANEL ONLY|GLASS PANEL|\bSTAND\b", u) and not re.search(r"CASE|CASING|TOWER|CHASSIS", u):
            return None, None
        if re.search(r"(?:CASE|CASING) FAN|FAN FOR", u):
            return None, None
        small = bool(re.search(r"M-?ATX|MICRO|ITX|MINI TOWER", u)) and not re.search(r"MID[- ]?TOWER|FULL[- ]?TOWER|E-?ATX", u)
        p = price or 0
        t = 1 if p < 4500 else 2 if p < 8500 else 3 if p < 13500 else 4
        return None, {"atx": int(not small), "t": t if not small else min(t, 1)}

    if cat == "cooler":
        if re.search(r"PASTE|COMPOUND|FAN HUB|CONTROLLER|CASE FAN|COOLING PAD|THERMAL PAD|\b(?:3|4|5) ?IN ?1\b|FAN PACK|FAN KIT", u):
            return None, None
        if re.search(r"LIQUID|\bAIO\b|WATER|ARCTIC LIQUID", u):
            r = re.search(r"\b(120|240|280|360|420)\b", u)
            size = int(r.group(1)) if r else 240
            return None, {"cap": {120: 150, 240: 230, 280: 250, 360: 300, 420: 320}[size], "aio": size}
        if re.search(r"LOW[- ]?PROFILE|AG200|AN600|\bL9|\bL12", u):
            cap = 95
        elif re.search(r"DUAL[- ]?TOWER|PEERLESS|PHANTOM SPIRIT|AK620|AG620|NH-D15|DARK ROCK PRO|ASSASSIN|FROZEN EDGE|AK500", u) or (price or 0) >= 5000:
            cap = 220
        else:
            cap = 150
        return None, {"cap": cap, "aio": 0}

    return None, None
