// Unit tests for site/engine.js (Smart Build logic). Run: node --test tests/js
// Each test name starts with its test-case ID; the technique is in brackets.
import { test, describe } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const SRC = fs.readFileSync(path.join(ROOT, "site/engine.js"), "utf8");

/** Fresh engine (own data + state) for every test, so tests never affect each other. */
const BB_total = x => Object.values(x).reduce((t, p) => t + (p.live ? p.p : p.p), 0);
function engine(opt = {}) {
  const ctx = {};
  vm.createContext(ctx);
  vm.runInContext(SRC, ctx, { filename: path.join(ROOT, "site/engine.js") });
  Object.assign(ctx.BB.opt, opt);
  return ctx.BB;
}
const USES = ["gaming", "creator", "office"];
const allChecksPass = (BB, x) => BB.checks(x).every(([ok]) => ok);

/** A small catalogue in the crawler's format, for stock/price tests. */
function miniCatalog(items) {
  return { updated: "2026-11-22T00:00:00+00:00", shops: ["Star Tech", "Ryans"], items };
}

describe("FR-01 build stays within budget", () => {
  test("TC-E01 [property-based] every budget 50k–600k and every use: total ≤ budget, all checks pass", () => {
    const BB = engine();
    let built = 0;
    for (const use of USES) {
      for (let b = 50000; b <= 600000; b += 10000) {
        const r = BB.build(b, use);
        if (!r.x) continue;
        built++;
        assert.ok(BB.total(r.x) <= b, `${use} ${b}: total ${BB.total(r.x)} over budget`);
        assert.ok(allChecksPass(BB, r.x), `${use} ${b}: ${JSON.stringify(BB.checks(r.x).filter(c => !c[0]))}`);
      }
    }
    assert.ok(built > 150, `only ${built} budgets produced a build`);
  });

  test("TC-E02 [BVA] budget at minimum−1 → no build; minimum → build; minimum+1 → build", () => {
    for (const use of USES) {
      const BB = engine();
      const min = BB.build(1000, use).min;
      assert.ok(Number.isFinite(min) && min > 0, `${use}: min ${min}`);
      assert.equal(BB.build(min - 1, use).x, undefined, `${use}: built below minimum`);
      assert.ok(BB.build(min, use).x, `${use}: no build at exactly the minimum ${min}`);
      assert.ok(BB.build(min + 1, use).x, `${use}: no build at minimum+1`);
    }
  });

  test("TC-E03 [EP] too-small budget returns the cheapest possible total instead of a build (FR-09)", () => {
    const r = engine().build(20000, "gaming");
    assert.equal(r.x, undefined);
    assert.ok(r.min > 20000);
  });
});

describe("FR-02 use case changes the build", () => {
  test("TC-E04 [EP] gaming favours the graphics card, office can skip it", () => {
    const BB = engine();
    const g = BB.build(150000, "gaming").x, o = BB.build(60000, "office").x;
    assert.notEqual(g.gpu.id, "none");
    assert.ok(g.gpu.p >= g.cpu.p, "gaming build should spend more on GPU than CPU");
    assert.ok(o.cpu.ig, "office build CPU must have built-in graphics when no card is chosen");
  });
  test("TC-E05 [EP] editing build picks a CPU at least as strong for productivity as the gaming build", () => {
    const BB = engine();
    const g = BB.build(200000, "gaming").x, c = BB.build(200000, "creator").x;
    assert.ok(c.cpu.c >= g.cpu.c);
  });
});

describe("FR-03 processor / graphics preferences", () => {
  test("TC-E06 [EP] a named GPU is always used", () => {
    const x = engine({ gpu: "rtx5070" }).build(200000, "gaming").x;
    assert.equal(x.gpu.id, "rtx5070");
  });
  test("TC-E07 [EP] brand filters: 'intel' CPU and 'amd' GPU", () => {
    const x = engine({ cpu: "intel", gpu: "amd" }).build(150000, "gaming").x;
    assert.equal(x.cpu.b, "intel");
    assert.equal(x.gpu.b, "amd");
  });
  test("TC-E08 [decision table] 'no graphics card' + CPU without graphics → impossible (no display)", () => {
    const r = engine({ cpu: "i5-12400f", gpu: "none" }).build(300000, "office");
    assert.equal(r.x, undefined);
    assert.ok(!Number.isFinite(r.min));
  });
  test("TC-E09 [decision table] 'no graphics card' + CPU with graphics → valid build", () => {
    const x = engine({ cpu: "i5-12400", gpu: "none" }).build(80000, "office").x;
    assert.equal(x.gpu.id, "none");
    assert.ok(x.cpu.ig);
  });
});

describe("FR-04 compatibility rules", () => {
  const BB = engine();
  const base = () => BB.build(150000, "gaming").x;

  test("TC-E10 [decision table] each broken rule is reported by checks()", () => {
    const x = base();
    const otherSocket = BB.B.find(b => b.s !== x.cpu.s);
    const wrongMem = BB.R.find(r => r.mem !== x.board.mem);
    const tinyPsu = [...BB.P].sort((a, b) => a.w - b.w)[0];
    const weakCooler = BB.Q.find(q => q.id !== "stock" && q.cap < 100) || { ...BB.Q[1], cap: 10 };
    const smallCase = BB.K.find(k => !k.atx);
    const atxBoard = BB.B.find(b => b.atx && b.s === x.cpu.s) || { ...x.board, atx: 1 };
    const cases = [
      [{ board: otherSocket }, "socket"],
      [{ ram: wrongMem }, "memory"],
      [{ gpu: BB.G.find(g => g.id === "rtx5090"), psu: tinyPsu }, "W PSU"],
      [{ cpu: { ...x.cpu, w: 250, cool: 0 }, cooler: weakCooler }, "Cooler too weak"],
      [{ board: atxBoard, case: smallCase }, "Case too small"],
      [{ gpu: BB.G.find(g => g.id === "none"), cpu: { ...x.cpu, ig: 0 } }, "no built-in graphics"],
    ];
    for (const [change, expect] of cases) {
      const failed = BB.checks({ ...x, ...change }).filter(c => !c[0]).map(c => c[1]).join(" | ");
      assert.match(failed, new RegExp(expect), `changing ${Object.keys(change)} should fail "${expect}"`);
    }
  });
  test("TC-E11 [BVA] PSU must be at least 1.4 × estimated draw", () => {
    const x = base();
    const need = BB.need(x.cpu, x.gpu) * 1.4;
    assert.equal(BB.psuOk(x.cpu, x.gpu, { w: Math.ceil(need) }), true);
    assert.equal(BB.psuOk(x.cpu, x.gpu, { w: Math.ceil(need) - 1 }), false);
  });
  test("TC-E12 [BVA] stock cooler allowed up to 125 W only", () => {
    const stock = BB.Q.find(q => q.id === "stock");
    assert.equal(BB.coolOk({ cool: 1, w: 125 }, stock), true);
    assert.equal(BB.coolOk({ cool: 1, w: 126 }, stock), false);
    assert.equal(BB.coolOk({ cool: 0, w: 65 }, stock), false);
  });
  test("TC-E13 [EP] swap menus only offer compatible parts", () => {
    const x = base();
    for (const o of BB.options("psu", x)) assert.ok(BB.psuOk(x.cpu, x.gpu, o));
    for (const o of BB.options("cooler", x)) assert.ok(BB.coolOk(x.cpu, o));
    for (const o of BB.options("ram", x)) assert.equal(o.mem, x.board.mem);
    for (const o of BB.options("cpu", x)) assert.equal(o.s, x.board.s);
  });
});

describe("FR-05 balanced motherboard class", () => {
  test("TC-E14 [property-based] board class ≥ CPU class for every generated build", () => {
    const BB = engine();
    for (const use of USES) for (let b = 50000; b <= 600000; b += 25000) {
      const x = BB.build(b, use).x;
      if (x) assert.ok(x.board.t >= x.cpu.t, `${use} ${b}: ${x.board.n} under ${x.cpu.n}`);
    }
  });
  test("TC-E15 [regression DEF-01] Ryzen 7 7800X3D never gets an A-series board", () => {
    const x = engine({ cpu: "r7-7800x3d" }).build(150000, "gaming").x;
    assert.ok(!x.board.ent && !/A6?20/.test(x.board.n), `got ${x.board.n}`);
  });
  test("TC-E16 [state transition] A520/A620 only when nothing else fits, then back when budget allows", () => {
    // find the budget band where only an A-series board fits a Ryzen 5 7600 build
    const noA = engine({ cpu: "r5-7600", avoidA: true });
    const withA = engine({ cpu: "r5-7600", avoidA: false });
    let lowA = withA.build(1000, "gaming").min;
    const x1 = noA.build(lowA, "gaming").x;           // nothing else fits → fallback to A-series
    assert.ok(x1 && x1.board.ent, "expected A-series fallback at the lowest possible budget");
    const x2 = noA.build(lowA + 40000, "gaming").x;   // more money → leaves A-series
    assert.ok(x2 && !x2.board.ent, `still A-series at ${lowA + 40000}: ${x2 && x2.board.n}`);
  });
});

describe("FR-06 RAM and SSD defaults", () => {
  test("TC-E17 [EP/BVA] Auto = 16 GB RAM and 512 GB SSD below ৳1.5 lakh", () => {
    const BB = engine();
    for (const use of USES) for (const b of [70000, 120000, 149999]) {
      const x = BB.build(b, use).x;
      assert.equal(x.ram.gb, 16, `${use} ${b}`);
      assert.equal(x.ssd.gb, 512, `${use} ${b}`);
    }
  });
  test("TC-E29 [property] ৳1.5 lakh+: extra RAM/storage never changes the gaming CPU/GPU pairing", () => {
    for (const use of ["gaming", "office"]) for (let b = 150000; b <= 600000; b += 25000) {
      const auto = engine().build(b, use).x, base = engine({ ram: 16, ssd: 512 }).build(b, use).x;
      assert.ok(auto.ram.gb >= 16 && auto.ssd.gb >= 512);
      assert.equal(auto.cpu.id, base.cpu.id, `${use} ${b}: CPU changed`);
      assert.equal(auto.gpu.id, base.gpu.id, `${use} ${b}: GPU changed`);
      assert.ok(BB_total(auto) <= b);
    }
  });
  test("TC-E30 [EP] big budgets get more memory or storage when it fits", () => {
    const g = engine().build(400000, "gaming"), c = engine().build(400000, "creator");
    assert.ok(g.x.ram.gb >= 32 && g.x.ssd.gb >= 1000 && g.more, "৳4 lakh gaming");
    assert.ok(c.x.ram.gb >= 32 && c.x.ssd.gb >= 1000 && c.more, "৳4 lakh editing");
    assert.ok(engine().build(150000, "gaming").x.ssd.gb >= 1000, "৳1.5 lakh gaming: 1 TB fits");
  });
  test("TC-E31 [decision table] editing builds trade at most 5% CPU/GPU score; a user's own RAM/SSD choice is never changed", () => {
    for (let b = 150000; b <= 600000; b += 50000) {
      const BB = engine(), auto = BB.build(b, "creator").x, base = engine({ ram: 16, ssd: 512 }).build(b, "creator").x;
      const sc = x => .5 * x.cpu.c + .4 * x.gpu.c + .1 * x.gpu.g;
      assert.ok(sc(auto) >= sc(base) * 0.95 - 1e-9, `${b}: ${sc(auto)} vs ${sc(base)}`);
    }
    const fixed = engine({ ram: 16, ssd: 0 }).build(400000, "creator").x;
    assert.equal(fixed.ram.gb, 16);
  });
  test("TC-E18 [EP] user choice 32 GB / 2 TB is respected", () => {
    const x = engine({ ram: 32, ssd: 2000 }).build(250000, "creator").x;
    assert.equal(x.ram.gb, 32);
    assert.equal(x.ssd.gb, 2000);
  });
});

describe("FR-07 live catalogue and stock filter", () => {
  const items = [
    { id: "a", s: "Star Tech", c: "gpu", n: "ZOTAC RTX 5060 SOLO", p: 39900, st: 1, u: "https://www.startech.com.bd/a", m: "rtx5060", i: "https://x/a.jpg" },
    { id: "b", s: "Ryans", c: "gpu", n: "MSI RTX 5060 Ventus", p: 38000, st: 0, u: "https://www.ryans.com/b", m: "rtx5060" },
    { id: "c", s: "Ryans", c: "gpu", n: "ASUS RTX 5070", p: null, st: 0, u: "https://www.ryans.com/c", m: "rtx5070" },
    { id: "e", s: "Star Tech", c: "cpu", n: "AMD Ryzen 7 7700", p: 31000, st: 1, u: "https://x/e", m: "r7-7700" },
  ];
  test("TC-E19 [EP] model price = cheapest IN-STOCK listing, not the cheaper out-of-stock one", () => {
    const BB = engine();
    BB.applyCatalog(miniCatalog(items));
    assert.equal(BB.LIVE.rtx5060.price, 39900);
    assert.equal(BB.LIVE.rtx5060.shop, "Star Tech");
    assert.equal(BB.LIVE.rtx5060.img, "https://x/a.jpg");
  });
  test("TC-E20 [regression DEF-04] model listed but out of stock everywhere keeps the estimate price and is unavailable", () => {
    const BB = engine();
    BB.applyCatalog(miniCatalog(items));
    const g = BB.G.find(x => x.id === "rtx5070");
    assert.equal(BB.pr(g), g.p);
    assert.equal(BB.inStock(g), false);
  });
  test("TC-E28 [regression DEF-16] catalogue with only some categories still produces a build", () => {
    const BB = engine();
    BB.applyCatalog(miniCatalog([...items, { id: "d", s: "Star Tech", c: "cpu", n: "AMD Ryzen 5 7600", p: 23000, st: 1, u: "https://x/d", m: "r5-7600" }]));
    const x = BB.build(150000, "gaming").x;
    assert.ok(x, "no build when boards/RAM/etc. are missing from the catalogue");
    assert.ok(["r5-7600", "r7-7700"].includes(x.cpu.id), `CPU ${x.cpu.id} is not one the shops list`);
  });
  test("TC-E21 [decision table] stock filter on → unlisted/out-of-stock models excluded; off → allowed", () => {
    const on = engine({ stockOnly: true, gpu: "rtx5070" });
    on.applyCatalog(miniCatalog(items));
    const xOn = on.build(250000, "gaming").x;
    assert.equal(xOn.gpu.id, "rtx5070", "a GPU the user names explicitly is still used");
    const auto = engine({ stockOnly: true });
    auto.applyCatalog(miniCatalog(items));
    assert.equal(auto.build(250000, "gaming").x.gpu.id, "rtx5060", "only the in-stock GPU should be picked automatically");
  });
  test("TC-E22 [EP] board from catalogue: A-series chipset is flagged 'entry'", () => {
    const BB = engine();
    const boards = ["A620M", "B650M", "B650", "A620M"].map((ch, i) => ({ id: "b" + i, s: "Star Tech", c: "board", n: ch + " board " + i, p: 15000 + i * 1000, st: 1, u: "https://x/b" + i, a: { sock: "AM5", ch, t: ch.startsWith("A") ? 1 : 2, mem: "DDR5", ff: "mATX", wifi: 0 } }));
    BB.applyCatalog(miniCatalog(boards));
    assert.deepEqual(Array.from(BB.B, b => b.ent), [1, 0, 0, 1]);
  });
});

describe("FR-08 swapping a part keeps the build compatible", () => {
  test("TC-E23 [state transition] DDR4 build → swap to a DDR5 board → RAM switches to DDR5", () => {
    const BB = engine({ cpu: "i5-12400f" });
    const x = BB.build(90000, "gaming").x;
    assert.equal(x.board.mem, "DDR4");
    const d5 = BB.B.find(b => b.s === "LGA1700" && b.mem === "DDR5");
    const y = { ...x, board: d5 };
    const msgs = BB.fix(y);
    assert.equal(y.ram.mem, "DDR5");
    assert.ok(msgs.some(m => /memory/.test(m)));
    assert.ok(allChecksPass(BB, y));
  });
  test("TC-E24 [state transition] swap to a much bigger GPU → PSU is raised", () => {
    const BB = engine();
    const x = BB.build(120000, "gaming").x;
    const y = { ...x, gpu: BB.G.find(g => g.id === "rtx5090") };
    BB.fix(y);
    assert.ok(BB.psuOk(y.cpu, y.gpu, y.psu));
  });
});

describe("FR-12 buy links", () => {
  test("TC-E25 [EP] affiliate template {url} and {url_encoded}; empty template = plain link", () => {
    const BB = engine();
    BB.AFF = { "Star Tech": "{url}?ref=bb", Ryans: "https://go.example/?to={url_encoded}" };
    assert.equal(BB.buy("https://s/p", "Star Tech"), "https://s/p?ref=bb");
    assert.equal(BB.buy("https://r/p?a=1", "Ryans"), "https://go.example/?to=https%3A%2F%2Fr%2Fp%3Fa%3D1");
    assert.equal(BB.buy("https://t/p", "Tech Land"), "https://t/p");
  });
});

describe("Performance tier text", () => {
  test("TC-E26 [BVA] tier boundaries at GPU score 30/46/60/75/90 (both sides of each)", () => {
    const BB = engine();
    const t = g => BB.tier({ gpu: { id: "x", g } });
    assert.equal(t(29), "1080p esports titles");
    assert.equal(t(30), "1080p high settings");
    assert.equal(t(45), "1080p high settings");
    assert.equal(t(46), "1080p ultra, 1440p medium");
    assert.equal(t(59), "1080p ultra, 1440p medium");     // added after mutation test M05 survived
    assert.equal(t(60), "1440p high to ultra");
    assert.equal(t(74), "1440p high to ultra");
    assert.equal(t(75), "1440p ultra, 4K with upscaling");
    assert.equal(t(89), "1440p ultra, 4K with upscaling");
    assert.equal(t(90), "4K ultra");
    assert.match(BB.tier({ gpu: { id: "none", g: 6 } }), /Office/);
  });
});

describe("NFR-02 performance", () => {
  test("TC-E27 [performance] one build search takes under 300 ms on average", () => {
    const BB = engine();
    const t0 = performance.now();
    const n = 20;
    for (let i = 0; i < n; i++) BB.build(60000 + i * 20000, USES[i % 3]);
    const avg = (performance.now() - t0) / n;
    assert.ok(avg < 300, `average ${avg.toFixed(1)} ms`);
  });
});
