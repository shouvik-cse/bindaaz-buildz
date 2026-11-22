# বিন্দাজ Buildz

A PC-builder website for Bangladesh. Pick a budget in taka (plus a CPU or GPU if you like) and it suggests a complete, balanced build from **real products currently listed by Star Tech, Ryans, Tech Land, PCB Store and Sumash Tech**, using the lowest in-stock price for every part. Every 6 hours a crawler reads every product in each shop's component categories, along with its price and stock status.

```
site_config.json         your address, affiliate links, Search Console / Bing codes, Analytics id
site/                    the website source
  index.html             Smart Build page, All products, price list, FAQ
  engine.js              parts table + build logic (used by the page AND by build_site.py)
  logo.webp, og-image.jpg, favicons
  catalog.json           written by the crawler, don't edit by hand
worker.js                Cloudflare Worker: serves shop product photos (/img) and the realistic AI picture of the PC (/render)
wrangler.jsonc           Cloudflare settings: publish dist/, run worker.js, switch on the free Workers AI
scraper/
  crawl.py               crawls all category pages of every shop (name, price, stock, link, photo)
  classify.py            turns product names into builder parts (socket, chipset, DDR type, GB, watts, ...)
  shops.json             shops and their category page paths  (you edit this)
  build_site.py          builds dist/: ready builds, price guides, sitemap, robots.txt
  precompute.mjs         runs engine.js in Node so ready-build pages show real parts and photos
.github/workflows/
  update-prices.yml      every 6 h: crawl → build pages → deploy to Cloudflare Pages
```

## What the website does

- **Smart Build**
  - Pick a budget, what the PC is for, and optionally a CPU or GPU. You get a complete, compatible build of real in-stock products.
  - Every part shows its **photo**, price, shop and a **"Buy at <shop>"** button that goes to that product's page.
  - Processors and graphics cards use the cheapest in-stock listing of that model at any shop.
  - A520/A620 motherboards are avoided; they're only used if nothing else fits the budget.
  - Any part can be swapped.
- **Build image:** draws the whole build as one picture (1080×1350): logo, total, all eight parts with photos, prices and shops. Visitors can **download** it or **share** it to Facebook, Messenger or WhatsApp. Every shared image advertises your site.
- **Copy list with links:** copies the build as text, with the shop link for every part.
- **All products:** a photo grid of every product from every shop, with search, category and shop filters, an in-stock toggle and sorting. Each card links to the shop's product page.
- **Ready builds:** 19 pages for popular budgets. They're precomputed at build time, so each shows real parts, photos and buy buttons straight away, and Google can read them. The hub page shows a photo collage per build.
- **Price guides:** a page per CPU/GPU model and per category, with photos and buy links.

## Set it up on Cloudflare Pages (about 15 minutes)

GitHub collects the prices every 6 hours and saves them in the repository. Cloudflare is connected to the repository, so every update makes Cloudflare rebuild and publish the site. No API tokens are needed.

1. **Put the code on GitHub** in a repository called `bindaaz-buildz`, including the hidden `.github` folder.
2. **Allow the bot to save prices:** in the repository, go to **Settings → Actions → General → Workflow permissions**, choose **Read and write permissions**, and click **Save**.
3. **Connect Cloudflare to the repository:**
   - In Cloudflare, go to **Workers & Pages → Create → Pages → Connect to Git**.
   - Authorise GitHub and pick the `bindaaz-buildz` repository.
4. **Build settings:**
   - Framework preset: **None**
   - Build command: `pip install -r scraper/requirements.txt && python scraper/build_site.py`
   - Build output directory: `dist`
   - Environment variable: `PYTHON_VERSION` = `3.12`
   Click **Save and Deploy**. `wrangler.toml` switches on Workers AI for the realistic PC picture, and the `functions/` folder (photos and AI picture) is picked up automatically. If the realistic picture says it isn't available, add the AI binding by hand: **Settings → Bindings → Add → Workers AI**, variable name `AI`, then redeploy.
5. **Set your address:** put the `https://….pages.dev` address Cloudflare shows in `base_url` in `site_config.json` and commit. Cloudflare rebuilds by itself.
6. **Collect the products:** go to **Actions → Update products → Run workflow**. The first crawl takes about 20–40 minutes. When it saves `catalog.json`, Cloudflare publishes the site with all products a minute or two later.

## Quick try without GitHub (upload by hand)

1. On your PC, with Python installed, run:
   ```bash
   pip install -r scraper/requirements.txt
   python scraper/crawl.py          # collects all products into site/catalog.json (20–40 min)
   python scraper/build_site.py     # makes the finished site in the dist/ folder
   ```
2. In Cloudflare, open **Workers & Pages → bindaaz-buildz → Create deployment** and drag in the **`dist`** folder, not `site`.

`site/` is the source. It works on its own, but it shows built-in estimate prices and an empty product list until `catalog.json` exists. The price guides, ready builds and sitemap only exist in `dist/`.

## Earning from the product links

Every "Buy at …" button, product card, price-guide row and copied build list goes through one function. That means you can turn on tracking or affiliate links for a shop in one place: `affiliate_templates` in `site_config.json`.

```json
"affiliate_templates": {
  "Star Tech": "{url}?utm_source=bindaazbuildz&utm_medium=referral",
  "Ryans": "https://partner.example.com/click?ref=YOURID&to={url_encoded}",
  "Tech Land": ""
}
```

- `{url}` is the product link and `{url_encoded}` is the same link URL-encoded. Use whichever form the shop's partner programme gives you.
- An empty template means the plain product link.
- When a template is set, that shop's links are automatically marked `rel="sponsored"`, as Google requires for paid links.
- **Do this before you agree a deal:** add plain `utm_source=bindaazbuildz` tracking to every shop. Shops can then see in their own analytics how many visitors and sales you send them, which gives you something concrete to show when you ask for a commission.

**Product photos** are shown straight from the shops' websites (nothing is copied to your site). They belong to the shops and brands, which is normal for a site that sends them buyers. If a shop asks you to stop showing its photos, remove its domain from `ALLOWED` in `worker.js` and its images will fall back to labelled placeholders.

## Check the shop category pages first (do this once)

I couldn't open the shops' pages while building this. The page addresses in `scraper/shops.json` are:

- **Star Tech, Ryans:** taken from their site menus.
- **Tech Land:** only the processor page is confirmed; the other seven are my best guesses.
- **PCB Store:** all eight category pages confirmed.
- **Sumash Tech:** processor, motherboard and graphics card pages confirmed; for the rest the crawler tries the likely address, then finds the link by name in the shop's menu.

Run **Actions → Check shops** (about 3 minutes) after changing `shops.json`: its Summary page shows, per shop, how many products were found and why any category failed.

Before relying on the crawl, run this on your own computer:

```bash
pip install -r scraper/requirements.txt
python scraper/crawl.py --check
```

It loads page 1 of every category and prints something like `Star Tech / gpu: 20 products (19 usable by the builder)`.

- **`ERROR 404` or `0 products`:** open the shop in your browser, click into that category, and copy its path (the part after the domain) into `shops.json`.
- **A wrong-looking product list for one page:** look at exactly what the crawler reads with
  ```bash
  python scraper/crawl.py --test "https://www.startech.com.bd/component/graphics-card"
  ```
  This prints each product's price, stock and name.

**Adding another shop** (Ultra Tech, Skyland, Potaka IT, …): add a block to `shops.json` with its name, base URL and category paths, then run `--check`. The crawler has a generic product-card finder, so most shops work without any site-specific code.

## How the crawler works

- **Reading pages:** it walks `?page=1, 2, 3 …` for each category until a page has no new products, up to 80 pages. For each product card it reads the name, the current price (skipping struck-through, "regular", "save" and EMI prices), the stock status and the link.
- **Sorting products:** `classify.py` sorts every product.
  - **CPUs and GPUs** are matched to the builder's model table.
  - **Motherboards** get socket, chipset class, DDR4/DDR5, form factor and Wi-Fi from the chipset in the name (A520/B550/A620/B650/B850/X870/H610/B760/Z790/B860/Z890…). Expensive B-series boards (TUF, Tomahawk class) count one class higher.
  - **RAM, SSDs, PSUs, cases and coolers** get capacity, generation, wattage, rating, ATX support and cooling capacity.
  - Laptop RAM, external SSDs, thermal paste, brackets, cables and similar items stay in the product list but aren't used by the builder.
- **Failed crawls:** if a whole category fails, last run's products for it are kept and marked "last known", so the site never empties.
- **Politeness:** it obeys each shop's `robots.txt`, waits 2–4 seconds between requests to the same shop, and identifies itself as `BindaazBuildzPriceBot`. Check each shop's terms of use, and consider asking them for permission or a product feed.

## Adding a new CPU or GPU model

New processors and graphics cards appear in **All products** straight away. The builder only uses models listed in its performance table, the `const C=[…]` and `const G=[…]` blocks in `site/engine.js`.

To add one, copy a similar line and change the id, name, socket and scores. For example, adding the Ryzen 5 9600X3D next to the 9600X:

```js
{id:'r5-9600x3d',n:'AMD Ryzen 5 9600X3D',b:'amd',s:'AM5',p:40000,g:92,c:62,w:120,ig:1,cool:0,t:2,mem:'DDR5',sp:'6C/12T, 3D V-Cache'},
```

- `g` / `c`: gaming / productivity score, out of 100.
- `w`: power draw in watts.
- `t`: recommended motherboard class (1 entry, 2 mainstream, 3 upper, 4 enthusiast).

The crawler matches shop listings by the last word of the name (`9600X3D`), so no other change is needed.

## When something breaks

- **A category suddenly has 0 products:** the shop changed its URL or layout. Run `--check` and `--test` as above.
- **The site didn't update after a crawl:** in Cloudflare, open the project → **Deployments** and check that the latest build succeeded. Open its build log if it failed.
- **Every request from GitHub gets HTTP 403:** some shops block cloud servers. Run the crawler on your own PC with Windows Task Scheduler (or cron) every few hours, then push:
  ```bash
  python scraper/crawl.py && git add site/catalog.json && git commit -m "Update product catalogue [prices]" && git push
  ```
  The push redeploys the site automatically.
- **A product is in the wrong builder slot:** adjust the matching rule for that category in `classify.py`. Each category is a short block of patterns.

## Your own domain

1. **Buy a domain** like `bindaazbuildz.com`. Cloudflare Registrar sells it at cost, about $10–11 a year, and makes the next step automatic. A `.com.bd` from BTCL or a local reseller also works.
2. **Connect it.** In Cloudflare, open **Workers & Pages → bindaaz-buildz → Custom domains → Set up a domain**, then enter `bindaazbuildz.com` and also `www.bindaazbuildz.com`.
   - **Bought from Cloudflare:** the DNS records are created for you.
   - **Bought elsewhere:** first add the domain to Cloudflare (free plan), then change its nameservers at the seller to the two Cloudflare gives you.
   HTTPS is set up automatically.
3. **Update the config.** Set `"base_url": "https://bindaazbuildz.com"` in `site_config.json` and push. Every page, the sitemap and share cards switch to the new address.

## Getting found on Google (SEO)

### Built into the site already

- **One page per search people actually make**
  - Every CPU and GPU model a shop lists gets a page like `/price/rtx-5060-8gb/` ("RTX 5060 8GB price in Bangladesh"). It shows the lowest price, every listing from every shop, and a "Build a PC with this" button.
  - Every category gets a page like `/price/motherboard/` with the cheapest product of each type and every listing.
  - 19 ready-build pages like `/builds/gaming-pc-under-1-lakh-taka/`, each showing the precomputed build with photos and opening the full Smart Build preset to that budget.
- **Pages that stay current:** pages are rebuilt every 6 hours with new prices, the month in the title and an updated sitemap. Google favours fresh pages for price searches.
- **Technical basics:** unique titles and descriptions, canonical URLs, `sitemap.xml`, `robots.txt`, and structured data (products with price ranges in BDT, breadcrumbs, website and organisation). There are also Open Graph share cards with your logo for Facebook and Messenger, favicons and a 404 page.
- **Bengali text:** pages carry Bengali lines (বাংলাদেশে … এর দাম, বাজেট অনুযায়ী পিসি বিল্ড) and a Bengali FAQ answer, so Bengali searches can match too.
- **Internal links:** the home page links to every price guide and ready build. Every model page links to its category and to similar models.

### Do this on launch day (about 30 minutes)

1. **Google Search Console** (search.google.com/search-console)
   - Add your domain as a property. With your own domain, verify by adding the TXT record it gives you to your DNS. On the pages.dev address, choose "URL prefix", pick the "HTML tag" method, and paste the code into `google_site_verification` in `site_config.json`.
   - Go to **Sitemaps** and submit `sitemap.xml`.
   - Use **URL Inspection → Request indexing** on the home page and a few big pages, such as `/price/graphics-card/` and `/builds/gaming-pc-under-1-lakh-taka/`.
2. **Bing Webmaster Tools** (bing.com/webmasters): sign in and choose **Import from Google Search Console**. This also covers DuckDuckGo and Yahoo.
3. **Analytics (optional):** Cloudflare's free Web Analytics can be switched on in the Pages project with no code. For Google Analytics 4, put its `G-XXXXXXX` id in `ga4_measurement_id`; it's added to every page automatically, and the About page mentions it.

Google usually starts showing new pages within 1–4 weeks. Search Console's **Performance** report then shows which searches bring people in, and that tells you what to write more of.

### How people will actually find it

Search traffic builds slowly. These bring visitors in the first weeks, and the links they create also help Google rank you:

- **Facebook:** the biggest PC community in Bangladesh.
  - Create a বিন্দাজ Buildz page and put its link in `facebook_page`.
  - Be useful in PC-building groups ("PC Builders Bangladesh" and similar). When someone asks "1 lakh budget e gaming PC?", reply with the matching ready-build link; the share card shows the logo and title.
  - Read each group's rules first. Most allow helpful links but ban plain advertising.
- **Weekly price post:** for example, "RTX 5060 lowest price this week: ৳39,900 at Star Tech". Your price pages make these quick to put together.
- **YouTube Shorts / TikTok / Reels:** 30-second clips like "৳1 lakh gaming PC build in 2026", built live on the site with the link in the description.
- **Reddit and forums:** r/bangladesh, r/IndianGaming (many BD members) and techtunes-style forums. Answer build questions with links.
- **Ask the shops:** the site sends them buyers. Some may link to it or share it, and those links count a lot for Google.

### Keep it healthy

- **Check Search Console monthly.** "Pages" shows indexing problems; "Performance" shows what people search.
- **Add models as they launch.** When new CPUs or GPUs come out, add them to the model table (see above) and they get their own price page automatically.
- **Don't change URLs** once pages are indexed. Slugs come from model names, so keep those names stable.
