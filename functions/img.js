// Cloudflare Pages Function: /img?u=<shop image URL>
// Re-serves product photos from the allowed shops with CORS headers, so the
// "Build image" button can draw them onto a canvas. Cached for a week at the edge.
const ALLOWED = ["startech.com.bd", "ryans.com", "techlandbd.com"];

export async function onRequest({ request }) {
  const u = new URL(request.url).searchParams.get("u");
  let target;
  try { target = new URL(u); } catch { return new Response("bad url", { status: 400 }); }
  const host = target.hostname.toLowerCase();
  if (target.protocol !== "https:" && target.protocol !== "http:") return new Response("bad url", { status: 400 });
  if (!ALLOWED.some(h => host === h || host.endsWith("." + h))) return new Response("host not allowed", { status: 403 });

  const r = await fetch(target.toString(), {
    headers: { "User-Agent": "BindaazBuildzImageProxy/1.0" },
    cf: { cacheTtl: 604800, cacheEverything: true },
  });
  const type = r.headers.get("content-type") || "";
  if (!r.ok || !type.startsWith("image/")) return new Response("not found", { status: 404 });
  const h = new Headers();
  h.set("Content-Type", type);
  h.set("Access-Control-Allow-Origin", "*");
  h.set("Cache-Control", "public, max-age=604800");
  return new Response(r.body, { headers: h });
}
