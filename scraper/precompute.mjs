// Runs the website's own build engine (site/engine.js) in Node to precompute the
// ready builds, so their pages can show real parts and photos before any JavaScript runs.
// usage: node scraper/precompute.mjs site/engine.js site/catalog.json '[{"use":"gaming","budget":100000}]'
import fs from "node:fs";
import vm from "node:vm";

const [, , enginePath, catalogPath, spec] = process.argv;
const ctx = {};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(enginePath, "utf8"), ctx);
const BB = ctx.BB;
if (catalogPath && fs.existsSync(catalogPath)) BB.applyCatalog(JSON.parse(fs.readFileSync(catalogPath, "utf8")));
const out = [];
for (const { use, budget } of JSON.parse(spec)) {
  const r = BB.build(budget, use);
  if (!r.x) { out.push({ use, budget, ok: false }); continue; }
  out.push({
    use, budget, ok: true, total: BB.total(r.x), tier: BB.tier(r.x),
    parts: BB.SLOTS.map(k => {
      const o = r.x[k], L = BB.listing(o);
      return { k, lab: BB.LAB[k], n: o.n, sp: o.sp || "", p: BB.pr(o) || 0, url: (L && L.url) || null, shop: (L && L.shop) || null, img: (L && L.img) || null, stock: L ? L.stock !== false : true };
    }),
  });
}
process.stdout.write(JSON.stringify(out));
