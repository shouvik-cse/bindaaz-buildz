// বিন্দাজ Buildz worker. Website files come from dist/ (see wrangler.jsonc). This adds:
//   /img?u=<shop photo URL>  re-serves product photos from the allowed shops with CORS headers,
//                            so the build pictures can include them
//   /render?case=&gpu=&cool=&ram=&color=
//                            a realistic AI picture of the assembled PC (Cloudflare Workers AI, free
//                            daily allowance). Only fixed option values are accepted (240 combinations)
//                            and every picture is cached for 30 days, so each one is generated once.
const ALLOWED = ["startech.com.bd", "ryans.com", "techlandbd.com", "pcbstore.com.bd", "sumashtech.com", "creatus.com.bd", "computermania.com.bd"];

async function photo(url) {
  let target;
  try { target = new URL(url.searchParams.get("u")); } catch { return new Response("bad url", { status: 400 }); }
  const host = target.hostname.toLowerCase();
  if (!/^https?:$/.test(target.protocol)) return new Response("bad url", { status: 400 });
  if (!ALLOWED.some(h => host === h || host.endsWith("." + h))) return new Response("host not allowed", { status: 403 });
  const r = await fetch(target.toString(), {
    headers: { "User-Agent": "BindaazBuildzImageProxy/1.0" },
    cf: { cacheTtl: 604800, cacheEverything: true },
  });
  const type = r.headers.get("content-type") || "";
  if (!r.ok || !type.startsWith("image/")) return new Response("not found", { status: 404 });
  return new Response(r.body, { headers: { "Content-Type": type, "Access-Control-Allow-Origin": "*", "Cache-Control": "public, max-age=604800" } });
}


const OPT = {
  case: {
    matx: "a compact micro-ATX mini tower case with a tempered glass side panel and a mesh front",
    mid: "a mid-tower ATX case with a tempered glass side panel and a mesh front with three RGB intake fans",
    show: "a premium dual-chamber panoramic case with glass on the front and side corner, RGB fans on the side and bottom",
  },
  gpu: {
    none: "no graphics card installed, the PCIe slot is empty, clean motherboard",
    small: "a compact dual-fan graphics card installed horizontally",
    mid: "a dual-fan graphics card installed horizontally",
    big: "a large triple-fan graphics card with a metal backplate installed horizontally",
  },
  cool: {
    stock: "a small stock box CPU cooler",
    air: "a single-tower air CPU cooler with one fan",
    dual: "a large dual-tower air CPU cooler with two fans",
    aio240: "a 240mm AIO liquid cooler with the radiator mounted at the top and an illuminated pump head",
    aio360: "a 360mm AIO liquid cooler with the radiator mounted at the top and an illuminated pump head",
  },
  ram: { 1: "one RAM stick", 2: "two RGB RAM sticks" },
  color: { black: "black", white: "white" },
};

async function render(request, url, env, ctx) {
  const p = {};
  for (const k of Object.keys(OPT)) {
    const v = url.searchParams.get(k);
    if (!(v in OPT[k])) return new Response(`bad ${k}`, { status: 400 });
    p[k] = v;
  }
  const key = new Request(`${url.origin}/render?${Object.keys(OPT).map(k => `${k}=${p[k]}`).join("&")}`);
  const cache = caches.default;
  const hit = await cache.match(key);
  if (hit) return hit;
  if (!env.AI) return new Response("AI not configured", { status: 503 });

  const prompt = `Professional product photograph of a fully assembled custom desktop gaming PC, three-quarter view from the glass side. ` +
    `${OPT.color[p.color]} ${OPT.case[p.case]}. Inside: ${OPT.gpu[p.gpu]}, ${OPT.cool[p.cool]}, ${OPT.ram[p.ram]}, ` +
    `a modern motherboard, tidy braided cable management, power supply in a shroud at the bottom. ` +
    `Purple and violet RGB lighting, dark studio background with soft purple rim light, sitting on a desk, photorealistic, sharp focus, 50mm lens. ` +
    `No text, no logos, no watermark, no people.`;
  let seed = 0;
  for (const ch of key.url) seed = (seed * 31 + ch.charCodeAt(0)) >>> 0;  // same build look → same picture
  let out;
  try {
    out = await env.AI.run("@cf/black-forest-labs/flux-1-schnell", { prompt, steps: 6, seed: seed % 2147483647 });
  } catch (e) {
    return new Response("render failed: " + (e && e.message || e), { status: 502 });
  }
  const b64 = out && out.image;
  if (!b64) return new Response("render failed", { status: 502 });
  const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
  const res = new Response(bytes, { headers: { "Content-Type": "image/jpeg", "Cache-Control": "public, max-age=2592000", "Access-Control-Allow-Origin": "*" } });
  ctx.waitUntil(cache.put(key, res.clone()));
  return res;
}


export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname === "/img") return photo(url);
    if (url.pathname === "/render") return render(request, url, env, ctx);
    return env.ASSETS.fetch(request);
  },
};
