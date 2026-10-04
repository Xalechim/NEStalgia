#!/usr/bin/env python3
"""One-time migration of the Squarespace site (articles and pages) into the repo.

Reads the live site through Squarespace's ?format=json view, cleans the markup,
downloads every image, and writes:
  site-src/migrated/articles.json   cleaned articles (title, date, tags, body HTML)
  site-src/migrated/pages.json      cleaned pages (essential, zapper, nrd1)
  site-src/migrated/redirects.json  old address -> kind/target hints
  site-src/migrated/media/          every image used, hosted locally

Needs: pip install beautifulsoup4 pillow. Safe to re-run; downloads are cached.
"""
import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString
from PIL import Image

HOST = "https://www.nestalgiacast.com"
REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "site-src/migrated"
MEDIA = OUT / "media"
UA = {"User-Agent": "Mozilla/5.0 (NEStalgia migration)"}
CDN = re.compile(r"https?://(?:images|static1|assets)\.squarespace(?:-cdn)?\.com/[^\s\"'()<>\\]+", re.I)
PAGES = {"essential": "/essential", "zapper": "/zapper", "nrd1": "/nrd1"}

ALLOWED = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "a", "strong", "b", "em", "i", "u", "br",
           "blockquote", "table", "thead", "tbody", "tr", "td", "th", "hr", "sup", "sub", "code", "pre", "figure", "figcaption"}


def get(url, tries=3):
    for i in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(2)


def get_json(path):
    return json.loads(get(f"{HOST}{path}?format=json"))


def localize_url(url):
    """Download an image once; return the site-relative path used in the fragments."""
    url = url.replace("&amp;", "&")
    p = urllib.parse.urlparse(url)
    name = Path(urllib.parse.unquote(p.path)).name or "image"
    stem, ext = (name.rsplit(".", 1) + ["jpg"])[:2] if "." in name else (name, "jpg")
    ext = ext.lower()[:4]
    fn = f"{hashlib.sha1(url.encode()).hexdigest()[:8]}-{re.sub(r'[^a-zA-Z0-9]+', '-', stem)[:40].strip('-')}.{ext}"
    dest = MEDIA / fn
    if not dest.exists():
        MEDIA.mkdir(parents=True, exist_ok=True)
        try:
            data = get(url)
        except Exception as e:
            print(f"   could not download {url[:80]}: {e}")
            return url
        dest.write_bytes(data)
        if ext in ("jpg", "jpeg", "png"):  # keep sharp pixel art, but cap huge images
            try:
                im = Image.open(dest)
                if im.width > 1600:
                    im.thumbnail((1600, 1600))
                    im.save(dest, optimize=True)
            except Exception:
                pass
    return f"{{BASE}}/media/{fn}"


def localize_all(html):
    return CDN.sub(lambda m: localize_url(m.group(0)), html)


def clean_node(node):
    """Return sanitized HTML for a block of text content."""
    out = []
    for ch in node.children:
        if isinstance(ch, NavigableString):
            out.append(str(ch).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
            continue
        inner = clean_node(ch)
        if ch.name in ALLOWED:
            attrs = ""
            if ch.name == "a" and ch.get("href"):
                attrs = f' href="{ch["href"]}"'
            if ch.name == "br" or ch.name == "hr":
                out.append(f"<{ch.name}>")
            elif ch.name == "p" and not re.sub(r"(&nbsp;|\s|​|\xa0)+", "", re.sub(r"<[^>]+>", "", inner)):
                continue  # empty paragraph
            else:
                out.append(f"<{ch.name}{attrs}>{inner}</{ch.name}>")
        else:
            out.append(inner)
    return "".join(out)


def img_src(tag):
    return tag.get("data-image") or tag.get("data-src") or tag.get("src")


def live_code_blocks(path):
    """Code blocks exactly as served in the page HTML. (The ?format=json view strips the {..}
    from template strings like ${r.ep}, which breaks embedded scripts.)"""
    soup = BeautifulSoup(get(f"{HOST}{path}").decode("utf-8", "replace"), "html.parser")
    return [b.select_one(".sqs-block-content").decode_contents() for b in soup.select(".sqs-block-code")
            if b.select_one(".sqs-block-content")]


def clean_blocks(html, code_blocks=None):
    soup = BeautifulSoup(html, "html.parser")
    out = []
    code_iter = iter(code_blocks or [])
    for b in soup.select(".sqs-block"):
        if b.find_parent(class_="sqs-block"):
            continue
        cls = " ".join(b.get("class", []))
        if "sqs-block-html" in cls:
            c = b.select_one(".sqs-html-content") or b
            out.append(clean_node(c))
        elif "sqs-block-markdown" in cls:
            out.append(clean_node(b.select_one(".sqs-block-content") or b))
        elif "sqs-block-code" in cls:
            c = b.select_one(".sqs-block-content") or b
            out.append(next(code_iter, None) or c.decode_contents())  # raw HTML/CSS/JS, kept as written
        elif "sqs-block-horizontalrule" in cls:
            out.append("<hr>")
        elif "sqs-block-button" in cls:
            for a in b.select("a"):
                out.append(f'<p><a class="btn" href="{a.get("href", "#")}">{a.get_text(strip=True)}</a></p>')
        elif "sqs-block-summary" in cls:
            continue  # an automatic list of other posts; the new site makes its own
        elif "sqs-block-gallery" in cls:
            imgs = []
            for im in b.select("img"):
                src = img_src(im)
                if src:
                    dims = re.match(r"(\d+)x(\d+)", im.get("data-image-dimensions", "") or "")
                    px = ' class="px"' if dims and int(dims.group(1)) <= 600 else ""
                    imgs.append(f'<img{px} src="{src}" alt="{(im.get("alt") or "").replace(chr(34), "&quot;")}" loading="lazy">')
            if imgs:
                out.append('<div class="gallery">' + "".join(imgs) + "</div>")
        elif b.select("img") or b.select("figcaption"):
            fig = b.select_one("img")
            src = img_src(fig) if fig else None
            dims = re.match(r"(\d+)x(\d+)", (fig.get("data-image-dimensions", "") if fig else "") or "")
            cap = b.select_one("figcaption") or b.select_one(".image-caption")
            capt = ""
            if cap and cap.get_text(strip=True):
                capt = clean_node(cap)
            px = ' class="px"' if dims and int(dims.group(1)) <= 600 else ""
            w = f' width="{dims.group(1)}" height="{dims.group(2)}"' if dims else ""
            alt = ((fig.get("alt") or "") if fig else "").replace('"', "&quot;")
            img = f'<img{px} src="{src}" alt="{alt}"{w} loading="lazy">' if src else ""
            out.append(f"<figure>{img}" + (f"<figcaption>{capt}</figcaption>" if capt else "") + "</figure>")
    return "\n".join(x for x in out if x.strip())


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sm = get(f"{HOST}/sitemap.xml").decode()
    paths = [re.sub(r"https://(www\.)?nestalgiacast\.com", "", u) for u in re.findall(r"<loc>([^<]+)</loc>", sm)]

    # 1. Old episode page addresses -> episode numbers
    redirects = {}
    eps = [p for p in paths if p.startswith("/nestalgia/podcast/") and "/category/" not in p and "/tag/" not in p]
    print(f"{len(eps)} old episode pages")
    for p in eps:
        try:
            title = get_json(p)["item"]["title"]
        except Exception as e:
            print("  skip", p, e)
            continue
        m = re.search(r"(\d{1,3})\s*-", title)
        redirects[p] = {"kind": "episode", "title": title, "number": int(m.group(1)) if m else None}
        time.sleep(0.15)

    # 2. Articles
    art_paths = [p for p in paths if p.startswith("/articles/") and not re.search(r"/(category|tag)/", p)]
    articles = []
    for p in art_paths:
        print("article", p)
        d = get_json(p)
        it = d["item"]
        body = localize_all(clean_blocks(it["body"], live_code_blocks(p)))
        asset = localize_url(it["assetUrl"]) if it.get("assetUrl") else None
        excerpt = re.sub(r"\s+", " ", BeautifulSoup(it.get("excerpt", ""), "html.parser").get_text(" ", strip=True))
        from datetime import datetime, timezone

        date = datetime.fromtimestamp(it["publishOn"] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        articles.append({"path": p, "slug": it["urlId"], "title": it["title"], "date": date,
                         "author": (it.get("author") or {}).get("displayName", "Michael Esposito"),
                         "tags": it.get("tags", []), "categories": it.get("categories", []),
                         "image": asset, "excerpt": excerpt, "body": body})
        time.sleep(0.2)
    (OUT / "articles.json").write_text(json.dumps(articles, indent=2, ensure_ascii=False))

    # 3. Pages
    pages = {}
    for name, p in PAGES.items():
        print("page", p)
        d = get_json(p)
        pages[name] = {"path": p, "title": d["collection"]["title"], "body": localize_all(clean_blocks(d["mainContent"], live_code_blocks(p)))}
        time.sleep(0.2)
    (OUT / "pages.json").write_text(json.dumps(pages, indent=2, ensure_ascii=False))

    # 4. Everything else gets a redirect hint
    for p in paths:
        if p in redirects or p in art_paths or p in PAGES.values():
            continue
        redirects[p] = {"kind": "other"}
    (OUT / "redirects.json").write_text(json.dumps(redirects, indent=2, ensure_ascii=False))
    size = sum(f.stat().st_size for f in MEDIA.glob("*")) / 1048576 if MEDIA.exists() else 0
    print(f"done: {len(articles)} articles, {len(pages)} pages, {len(redirects)} redirects, {len(list(MEDIA.glob('*')))} images, {size:.0f} MB")


if __name__ == "__main__":
    main()
