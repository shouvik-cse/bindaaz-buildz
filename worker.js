// বিন্দাজ Buildz worker. Website files come from dist/ (see wrangler.jsonc);
// this only adds /img?u=<shop photo URL>, which re-serves product photos from the
// allowed shops with CORS headers so the "Build image" picture can include them.
const ALLOWED = ["startech.com.bd", "ryans.com", "techlandbd.com"];

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

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/img") return photo(url);
    return env.ASSETS.fetch(request);
  },
};
