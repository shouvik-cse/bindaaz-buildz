"""FR-11: product names from the shops → builder parts (scraper/classify.py).
Technique: equivalence partitioning with a decision table of real-style product names,
plus boundary values for price thresholds."""
import pytest
from classify import classify, norm_gb

# (category, product name, price, expected model id or attribute subset, or None = rejected)
CASES = [
    # --- processors: exact model, suffix variants must not be confused (EP)
    ("cpu", "AMD Ryzen 7 7800X3D Processor", 47000, "r7-7800x3d"),
    ("cpu", "AMD Ryzen 5 5600 Processor", 13500, "r5-5600"),
    ("cpu", "AMD Ryzen 5 5600G Processor with Radeon Graphics", 15000, "r5-5600g"),
    ("cpu", "AMD Ryzen 5 5600GT Processor", 14000, "r5-5600gt"),
    ("cpu", "Intel Core i5 14th Gen Raptor Lake 14400F Up to 4.70GHz Processor - (Without GPU)", 22500, "i5-14400f"),
    ("cpu", "Intel Core i5-12400 12th Gen Processor", 16000, "i5-12400"),
    ("cpu", "Intel Core Ultra 5 245K Processor", 33000, "u5-245k"),
    ("cpu", "Intel Core Ultra 5-245KF Core 14 Threads", 31000, "u5-245kf"),
    ("cpu", "AMD Ryzen 7 9800X3D 8 Cores", 60000, "r7-9800x3d"),
    ("cpu", "Intel Core i7-14700KF Processor", 43000, "i7-14700kf"),
    ("cpu", "AMD Ryzen Threadripper 7960X", 150000, None),
    # --- graphics cards: Ti/XT/SUPER suffixes and VRAM variants (EP + decision table)
    ("gpu", "ZOTAC GAMING GeForce RTX 5060 SOLO 8GB GDDR7 Graphics Card", 44000, "rtx5060"),
    ("gpu", "ASUS PRIME GeForce RTX 5060 Ti 16GB OC", 72000, "rtx5060ti16"),
    ("gpu", "ASUS Dual GeForce RTX 5060 Ti 8GB GDDR7 OC Edition", 58000, "rtx5060ti8"),
    ("gpu", "Sapphire PULSE AMD Radeon RX 9070 XT 16GB", 105000, "rx9070xt"),
    ("gpu", "PowerColor Reaper Radeon RX 9070 16GB", 92000, "rx9070"),
    ("gpu", "XFX Radeon RX 9060 XT 16GB", 58000, "rx9060xt16"),
    ("gpu", "MSI GeForce RTX 5070 Ti 16G VENTUS 3X", 135000, "rtx5070ti"),
    ("gpu", "Intel Arc B580 Limited Edition 12GB", 40000, "arcb580"),
    ("gpu", "ASRock Intel Arc A750 Challenger 8GB", 28000, "arca750"),          # regression DEF-15
    ("gpu", "Gigabyte GTX 1650 D6 OC 4G", 18000, "gtx1650"),
    ("gpu", "Sapphire Pulse RX 7600 XT 16GB", 42000, "rx7600xt"),
    ("gpu", "NVIDIA RTX PRO 6000 Blackwell", 900000, None),
    ("gpu", "PNY NVIDIA RTX A4000 16GB", 150000, None),
    ("gpu", "Lian Li GPU Support Bracket", 1200, None),
    # --- motherboards: socket, class, memory type, size
    ("board", "MSI B650M Gaming Plus WiFi DDR5 AM5 Micro-ATX Motherboard", 21000, {"sock": "AM5", "ch": "B650M", "t": 2, "mem": "DDR5", "ff": "mATX", "wifi": 1}),
    ("board", "ASUS TUF Gaming B760M-Plus WiFi D4 Motherboard", 20000, {"sock": "LGA1700", "mem": "DDR4", "ff": "mATX"}),
    ("board", "Gigabyte B760M DS3H AX DDR5", 18000, {"sock": "LGA1700", "mem": "DDR5"}),
    ("board", "MSI MAG B550 Tomahawk Max WiFi", 21000, {"sock": "AM4", "t": 3, "ff": "ATX", "mem": "DDR4"}),
    ("board", "ASRock A620M-HDV/M.2+ AM5", 13000, {"ch": "A620M", "t": 1}),
    ("board", "ASUS ROG STRIX X870E-E GAMING WIFI", 70000, {"sock": "AM5", "t": 4, "ff": "ATX"}),
    ("board", "Gigabyte B650I AORUS Ultra", 32000, {"ff": "ITX"}),
    ("board", "Some Motherboard Without Chipset", 9000, None),
    # --- RAM: desktop only, kits, sizes
    ("ram", "KingBank Soarblade 16GB DDR5 6000Hz CL36 Desktop RAM", 25500, {"mem": "DDR5", "gb": 16, "k": 1, "mhz": 6000}),
    ("ram", "Corsair Vengeance 32GB (2x16GB) DDR5 6000MHz", 54000, {"mem": "DDR5", "gb": 32, "k": 2}),
    ("ram", "Team T-Force Delta RGB 8GB DDR5 5600MHz", 15000, {"gb": 8, "k": 1}),
    ("ram", "Crucial 16GB DDR4 3200MHz Laptop RAM", 9000, None),
    ("ram", "Kingston 4GB DDR3 1600MHz Desktop RAM", 2500, None),
    # --- SSD: internal NVMe vs SATA; size normalisation
    ("ssd", "Lexar NM620 512GB M.2 2280 NVMe SSD", 7000, {"gb": 512, "nv": 1, "gen": 3}),
    ("ssd", "Samsung 990 PRO 2TB PCIe 4.0 NVMe", 24000, {"gb": 2000, "nv": 1, "gen": 4}),
    ("ssd", "Kingston NV3 1TB Gen4", 13000, {"gb": 1000, "nv": 1, "gen": 4}),
    ("ssd", "Kingston A400 480GB SATA SSD", 5000, {"gb": 512, "nv": 0}),
    ("ssd", "Samsung T7 1TB Portable SSD", 12000, None),
    # --- PSU
    ("psu", "Deepcool PK650D 650W 80 Plus Bronze Power Supply", 7200, {"w": 650, "r": "Bronze"}),
    ("psu", "Corsair RM850e 850 Watt 80 PLUS Gold", 15500, {"w": 850, "r": "Gold"}),
    ("psu", "Antec Atom V450 450W", 4500, {"w": 450, "r": ""}),
    ("psu", "PSU Extension Cable Kit", 2500, None),
    # --- cases
    ("case", "Montech X3 Mesh Mid Tower Case", 5500, {"atx": 1, "t": 2}),
    ("case", "Xigmatek Gaming X mATX Case", 3800, {"atx": 0, "t": 1}),
    ("case", "Lian Li O11 Dynamic EVO", 16000, {"atx": 1, "t": 4}),
    ("case", "Generic Accessory Bracket For case", 2500, None),                  # regression DEF-03
    # --- coolers
    ("cooler", "Deepcool AK400 CPU Air Cooler", 2800, {"cap": 150, "aio": 0}),
    ("cooler", "Thermalright Peerless Assassin 120 SE", 5500, {"cap": 220}),
    ("cooler", "Deepcool LE520 240mm Liquid Cooler", 8500, {"cap": 230, "aio": 240}),
    ("cooler", "Arctic Liquid Freezer III 360 A-RGB", 14000, {"cap": 300, "aio": 360}),
    ("cooler", "Deepcool AG200 Low Profile", 1800, {"cap": 95}),
    ("cooler", "Arctic MX-4 Thermal Paste", 900, None),
]


@pytest.mark.parametrize("cat,name,price,expected", CASES, ids=[f"TC-C{i + 1:02d}-{c[0]}" for i, c in enumerate(CASES)])
def test_classify_table(cat, name, price, expected):
    model, attrs = classify(cat, name, price)
    if expected is None:
        assert model is None and attrs is None, f"should be rejected, got {model} {attrs}"
    elif isinstance(expected, str):
        assert model == expected
    else:
        assert attrs is not None, "not recognised"
        for k, v in expected.items():
            assert attrs[k] == v, f"{k}: {attrs[k]!r} != {v!r}"


@pytest.mark.parametrize("cat,low", [("cpu", 3000), ("gpu", 5000), ("case", 2000), ("cooler", 800)])
def test_min_price_boundary(cat, low):
    """TC-C70 [BVA] items priced just under a category's minimum are treated as accessories."""
    name = {"cpu": "AMD Ryzen 5 5600 Processor", "gpu": "MSI GeForce RTX 5060 8GB", "case": "Montech X3 Mesh Mid Tower Case", "cooler": "Deepcool AK400 CPU Air Cooler"}[cat]
    assert classify(cat, name, low - 1) == (None, None)
    assert classify(cat, name, low) != (None, None)


@pytest.mark.parametrize("n,unit,expect", [("500", "GB", 512), ("512", "GB", 512), ("960", "GB", 1000), ("1", "TB", 1000),
                                           ("2048", "GB", 2000), ("4", "TB", 4000), ("256", "GB", 256)])
def test_ssd_size_normalisation(n, unit, expect):
    """TC-C71 [EP] marketing sizes map to the builder's size classes."""
    assert norm_gb(n, unit) == expect


def test_board_tier_bump_boundary():
    """TC-C72 [BVA] a B650 board counts one class higher from ৳25,000."""
    assert classify("board", "Gigabyte B650 Eagle AX", 24999)[1]["t"] == 2
    assert classify("board", "Gigabyte B650 Eagle AX", 25000)[1]["t"] == 3
