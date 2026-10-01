#!/usr/bin/env python3
"""Build the NEStalgia website into site/ from the data in this repo.

  python3 scripts/build_site.py            # for GitHub Pages (URLs start with /NEStalgia)
  SITE_BASE= python3 scripts/build_site.py # for a local preview served from site/

Needs: pip install pillow markdown. Search is added afterwards by Pagefind (see the workflow).
"""
import html
import json
import os
import re
import shutil
from pathlib import Path

import markdown
from PIL import Image

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "site"
SRC = REPO / "site-src"
_cname = SRC / "CNAME"
if _cname.exists():  # custom domain: the site lives at the root of that domain
    DOMAIN = _cname.read_text().strip()
    BASE = os.environ.get("SITE_BASE", "").rstrip("/")
    SITE_URL = f"https://{DOMAIN}"
else:
    DOMAIN = None
    BASE = os.environ.get("SITE_BASE", "/NEStalgia").rstrip("/")
    SITE_URL = "https://xalechim.github.io/NEStalgia"
LINKS = [
    ("Apple Podcasts", "https://itunes.apple.com/us/podcast/nestalgia/id1342922798"),
    ("Spotify", "https://open.spotify.com/show/1SoG0RFa4nPk0YqaXW6vRi"),
    ("Patreon", "https://www.patreon.com/nestalgia"),
    ("Twitch", "https://www.twitch.tv/nestalgia"),
    ("RSS", "https://anchor.fm/s/5808ab8/podcast/rss"),
]
SHEET_URL = "https://docs.google.com/spreadsheets/d/1r5WpTbM0EYLbr1ylXthvf57HWgjo1iScI_c5HKgfSKc/edit?usp=sharing"
E = html.escape


def slug(s):
    s = s.lower().replace("'", "").replace("’", "")
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s)).strip("-")


def fmt_dur(sec):
    if not sec:
        return ""
    h, m = divmod(sec // 60, 60)
    return f"{h} hr {m} min" if h else f"{m} min"


def fmt_date(d):
    from datetime import date

    y, m, dd = map(int, d.split("-"))
    return date(y, m, dd).strftime("%B %-d, %Y")


def linkify(text):
    return re.sub(r"(https?://[^\s<]+)", r'<a href="\1" rel="noopener">\1</a>', E(text), flags=re.I)


def render_notes(path):
    """Markdown notes -> HTML. Files nest bullets with 2 or 4 spaces (or tabs); Python-Markdown
    wants 4, and anything indented further is turned into an unwrappable code block."""
    text = (REPO / path).read_text().replace("\t", "    ")
    lines = text.split("\n")
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    indents = sorted({len(m.group(1)) for ln in lines if (m := re.match(r"^( *)(?:[-*+]|\d+\.) ", ln)) and m.group(1)})
    unit = indents[0] if indents else 4
    out, prev, in_list = [], -1, False  # prev = nesting level of the previous bullet (-1: not in a list)
    for ln in lines:
        m = re.match(r"^( *)((?:[-*+]|\d+\.) .*)$", ln)
        if m:
            level = min(round(len(m.group(1)) / unit), prev + 1)  # can't nest deeper than one below the last bullet
            prev, in_list = level, True
            ln = " " * (4 * level) + m.group(2)
        elif in_list and ln.strip() and ln.startswith(" "):
            ln = ln.lstrip()  # wrapped continuation line of the item above, not a code block
        elif not ln.strip():
            pass
        else:
            in_list, prev = False, -1
        out.append(re.sub(r"(?<![(<\"])(https?://[^\s)>]+)", r"<\1>", ln))
    return markdown.markdown("\n".join(out), extensions=["tables"])


TURN = re.compile(r"^\*\*([^*]+)\*\* \[([\d:]+)\]: (.*)$")


def render_transcript(path):
    parts, note = [], ""
    for ln in (REPO / path).read_text().split("\n"):
        m = TURN.match(ln)
        if m:
            who, ts, txt = m.groups()
            parts.append(f'<p class="turn spk-{slug(who)}"><b>{E(who)}</b> <span class="ts">{ts}</span> {E(txt)}</p>')
        elif ln.startswith("_") and ln.endswith("_"):
            note = ln.strip("_")
    return (f'<p class="note">{E(note)}</p>' if note else "") + "\n".join(parts)


def page(title, body, path, desc="", image=None, search=False, current=""):
    desc = desc or "A chronological exploration of every NES game released in North America."
    img = f'<meta property="og:image" content="{SITE_URL}{image}">' if image else f'<meta property="og:image" content="{SITE_URL}/icon.png">'
    pf = (f'<link href="{BASE}/pagefind/pagefind-ui.css" rel="stylesheet">'
          f'<script src="{BASE}/pagefind/pagefind-ui.js"></script>') if search else ""
    nav = "".join(
        f'<a href="{BASE}{href}"{" aria-current=page" if current == key else ""}>{label}</a>'
        for key, href, label in (("home", "/", "Home"), ("eps", "/episodes/", "Episodes"), ("articles", "/articles/", "Articles"), ("search", "/search/", "Search"), ("about", "/about/", "About"))
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(desc[:200])}">
<meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc[:200])}">{img}
<meta property="og:type" content="website"><meta name="twitter:card" content="summary">
<link rel="icon" href="{BASE}/icon.png"><link rel="apple-touch-icon" href="{BASE}/icon.png">
<link rel="stylesheet" href="{BASE}/style.css">{pf}</head>
<body><a class="skip" href="#main">Skip to content</a>
<header class="site"><div class="bar"><a class="brand" href="{BASE}/"><img src="{BASE}/logo.png" alt="NEStalgia"></a><nav>{nav}</nav></div></header>
<main id="main">{body}</main>
<footer class="site">NEStalgia is a podcast by Michael Esposito and friends. Text is
<a href="https://creativecommons.org/licenses/by-nc/4.0/">CC BY-NC 4.0</a>; game art belongs to its owners.
<a href="https://github.com/Xalechim/NEStalgia">Source on GitHub</a>.</footer>
</body></html>"""


def write(rel, content):
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def card(r):
    label = f"{r['number']:03d}" if r["number"] is not None and r["type"] == "episode" else ("Special" if r["type"] == "special" else "")
    badge = '<span class="badge">TRANSCRIPT</span>' if r["transcript"] else ""
    return (f'<a class="card" href="{BASE}/episodes/{r["key"]}/" data-type="{r["type"]}" data-date="{r["published"]}" '
            f'data-num="{r["number"] if r["number"] is not None else ""}" data-title="{E(r["title"].lower())}">'
            f'<img src="{BASE}/art/thumb/{r["key"]}.jpg" alt="" loading="lazy" width="300" height="300">'
            f'<div class="t"><span class="n">{label}</span>{E(r["title"])}{badge}</div></a>')


MIG = SRC / "migrated"


def load_migrated():
    def j(name):
        f = MIG / name
        return json.loads(f.read_text()) if f.exists() else None
    return j("articles.json") or [], j("pages.json") or {}, j("redirects.json") or {}


def episode_targets(data, redirects):
    """Old /nestalgia/podcast/<slug> address -> new /episodes/<key>/ path."""
    by_num = {}
    for r in data:
        if r["type"] == "episode" and r["number"] is not None and "remaster" not in r["feed_title"].lower():
            by_num.setdefault(r["number"], r)
    specials = [(slug(r["feed_title"]), r) for r in data if r["type"] != "episode"]
    out = {}
    for old, info in redirects.items():
        if info.get("kind") != "episode":
            continue
        tgt = by_num.get(info.get("number"))
        if not tgt:
            t = slug(re.sub(r"^(podcast\s*-\s*)", "", info.get("title", ""), flags=re.I))
            tgt = next((r for k, r in specials if t and (t in k or k in t)), None)
        out[old] = f"/episodes/{tgt['key']}/" if tgt else "/episodes/"
    return out


def prose(fragment, ep_map):
    """Fill in {BASE} and point old Squarespace links at their new homes."""
    def fix(m):
        path = m.group(2)
        clean = path.rstrip("/")
        if clean in ep_map:
            return f'href="{BASE}{ep_map[clean]}"'
        if clean in ("/episodes", "/show-notes", "/nestalgia/podcast", "/home"):
            return f'href="{BASE}{"/" if clean == "/home" else "/episodes/"}"'
        if clean.startswith(("/articles", "/essential", "/zapper", "/nrd1", "/contact")):
            return f'href="{BASE}{clean}/"'
        return m.group(0)
    fragment = re.sub(r'href="(https?://(?:www\.)?nestalgiacast\.com)?(/[^"#?]*)"', fix, fragment)
    return fragment.replace("{BASE}", BASE)


def redirect_stub(target):
    url = f"{BASE}{target}"
    return (f'<!doctype html><html lang="en"><meta charset="utf-8"><title>Moved</title>'
            f'<link rel="canonical" href="{SITE_URL}{target}"><meta http-equiv="refresh" content="0; url={url}">'
            f'<script>location.replace({json.dumps(url)})</script><p>This page moved to <a href="{url}">{url}</a>.</p></html>')


def build_migrated(data, write, card_html):
    articles, pages, redirects = load_migrated()
    ep_map = episode_targets(data, redirects)
    if (MIG / "media").exists():
        shutil.copytree(MIG / "media", OUT / "media")

    # Articles keep their original addresses
    articles.sort(key=lambda a: a["date"], reverse=True)
    for a in articles:  # Squarespace sometimes stores a tiny blank placeholder as the thumbnail
        f = MIG / "media" / Path((a.get("image") or "").replace("{BASE}/media/", "")).name
        if not a.get("image") or not f.exists() or f.stat().st_size < 5000:
            m = re.search(r'<img[^>]*src="([^"]+)"', a["body"])
            a["image"] = m.group(1) if m else None
    real = {a["path"].rstrip("/") for a in articles}
    for a in articles:
        tags = "".join(f'<span class="atag">{E(t)}</span>' for t in a["tags"])
        body = f"""<p class="crumbs"><a href="{BASE}/articles/">← All articles</a></p>
<article data-pagefind-body><h1 data-pagefind-meta="title">{E(a["title"])}</h1>
<div class="meta">{fmt_date(a["date"])} · {E(a["author"])}</div>{('<div class="tags">'+tags+'</div>') if tags else ""}
<div class="prose">{prose(a["body"], ep_map)}</div></article>"""
        img = a["image"].replace("{BASE}", "") if a.get("image") else None
        write(a["path"].strip("/") + "/index.html",
              page(f'{a["title"]} · NEStalgia', body, "", desc=a["excerpt"], image=img, current="articles"))
    cards = "".join(
        f'<a class="card wide" href="{BASE}{a["path"]}/">'
        + (f'<img src="{(a["image"] or "").replace("{BASE}", BASE)}" alt="" loading="lazy">' if a.get("image") else "")
        + f'<div class="t"><span class="n">{fmt_date(a["date"])}</span><b>{E(a["title"])}</b><br>{E(a["excerpt"][:160])}</div></a>'
        for a in articles)
    features = f"""<h2>Features</h2><div class="btns" style="justify-content:flex-start">
<a class="btn" href="{BASE}/essential/">Essential Games List</a><a class="btn" href="{BASE}/zapper/">The NES Zapper</a>
<a class="btn" href="{BASE}/nrd1/">Nintendo R&amp;D1 games</a></div>"""
    write("articles/index.html", page("Articles · NEStalgia", f'<h1>Articles</h1>{features}<h2>Writing</h2><div class="grid articles">{cards}</div>', "", current="articles"))

    # Pages
    for name, pg in pages.items():
        wide = name == "zapper"
        inner = prose(pg["body"], ep_map)
        title = pg["title"]
        body = (f'<div class="rawpage">{inner}</div>' if wide else
                f'<h1 data-pagefind-meta="title">{E(title)}</h1><div class="prose" data-pagefind-body>{inner}</div>')
        write(f"{name}/index.html", page(f"{title} · NEStalgia", body, "", current="articles"))
        real.add(pg["path"].rstrip("/"))

    # Contact (the Squarespace form can't move to a static site)
    write("contact/index.html", page("Contact · NEStalgia", f"""<h1>Contact</h1>
<p class="lede">Questions, corrections, or game suggestions? Join the conversation on Patreon, or tell us about a mistake in the show notes or transcripts by
<a href="https://github.com/Xalechim/NEStalgia/issues/new">opening an issue on GitHub</a>.</p>
<div class="btns" style="justify-content:flex-start"><a class="btn" href="https://www.patreon.com/nestalgia">Patreon</a>
<a class="btn alt" href="https://github.com/Xalechim/NEStalgia/issues/new">Report a correction</a></div>""", ""))
    real.add("/contact")

    # Redirect pages for every old address that no longer has a real page
    n = 0
    for old, info in redirects.items():
        old_c = old.rstrip("/")
        if not old_c or old_c in real:
            continue
        if info["kind"] == "episode":
            tgt = ep_map.get(old_c, "/episodes/")
        elif old_c.startswith("/articles"):
            tgt = "/articles/"
        elif old_c in ("/home",):
            tgt = "/"
        elif old_c in ("/404",):
            continue
        elif old_c.startswith("/nestalgia") or old_c in ("/episodes", "/show-notes"):
            tgt = "/episodes/"
        else:
            tgt = "/"
        if not (OUT / old_c.strip("/") / "index.html").exists():
            write(old_c.strip("/") + "/index.html", redirect_stub(tgt))
            n += 1
    for old in ("/nestalgia/podcast", "/show-notes", "/episodes-old"):
        pass
    print(f"migrated: {len(articles)} articles, {len(pages)} pages, {n} redirect pages")
    return [a["path"] + "/" for a in articles] + [f"/{k}/" for k in pages] + ["/contact/", "/articles/"]


def patrons_html():
    f = SRC / "patrons.txt"
    names = [ln.strip() for ln in f.read_text().splitlines() if ln.strip() and not ln.startswith("#")] if f.exists() else []
    if not names:
        return ""
    cols = 3
    rows = []
    for i in range(0, len(names), cols):
        chunk = names[i : i + cols]
        chunk += [""] * (cols - len(chunk))
        rows.append("<tr>" + "".join(f"<td>{E(n)}</td>" for n in chunk) + "</tr>")
    return f"""<h2>Special thanks to our patrons!</h2>
<p><a class="btn" href="https://www.patreon.com/nestalgia" rel="noopener">Join Today!</a></p>
<div class="table-wrap"><table class="patrons">
<caption class="sr">Patreon members</caption>
<thead><tr><th colspan="{cols}" scope="colgroup">Our Patreon members ({len(names)})</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>"""


def main():
    data = json.loads((REPO / "data/episodes.json").read_text())
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    for f in ("style.css", "app.js", "logo.png", "icon.png"):
        shutil.copy(SRC / f, OUT / f)
    (OUT / ".nojekyll").write_text("")

    # Each record gets a stable page key = its art file name (set by build_episode_data.py).
    for r in data:
        r["key"] = Path(r["art"]).stem if r["art"] else slug(r["feed_title"])

    # Art: full size for episode pages, small thumbnails for lists.
    for r in data:
        if not r["art"]:
            continue
        src = REPO / r["art"]
        (OUT / "art/thumb").mkdir(parents=True, exist_ok=True)
        shutil.copy(src, OUT / "art" / f"{r['key']}.jpg")
        im = Image.open(src).convert("RGB")
        im.thumbnail((300, 300))
        im.save(OUT / "art/thumb" / f"{r['key']}.jpg", "JPEG", quality=75, optimize=True)

    ordered = sorted((r for r in data if r["published"]), key=lambda r: (r["published"], r["number"] or 0))
    for i, r in enumerate(ordered):
        r["prev"] = ordered[i - 1] if i > 0 else None
        r["next"] = ordered[i + 1] if i + 1 < len(ordered) else None

    for r in data:
        def kind(p):
            return "Outline" if p.endswith("-outline.md") else "Early notes" if p.endswith("-early-notes.md") else "Show notes"

        notes = "".join(
            (f"<h3>{kind(p)}</h3>" if len(r["notes"]) > 1 else "") + render_notes(p) for p in r["notes"]
        )
        label = f"{r['number']:03d} · " if r["type"] == "episode" and r["number"] is not None else ""
        desc_html = "".join(f"<p>{linkify(p)}</p>" for p in r["description"].split("\n\n") if p.strip())
        sections = []
        if notes:
            sections.append(f'<h2>Show notes</h2><div class="panel">{notes}</div>')
        if r["transcript"]:
            sections.append(f'<details class="tx"><summary>Read the transcript</summary><div class="panel">{render_transcript(r["transcript"])}</div></details>')
        pn = "".join(
            f'<a href="{BASE}/episodes/{x["key"]}/">{lab}</a>' if x else "<span></span>"
            for x, lab in ((r["prev"], f'← {E(r["prev"]["title"])}' if r["prev"] else ""), (r["next"], f'{E(r["next"]["title"])} →' if r["next"] else ""))
        )
        listen = "".join(f'<a class="btn alt" href="{u}" rel="noopener">{n}</a>' for n, u in LINKS[:2])
        body = f"""<p class="crumbs"><a href="{BASE}/episodes/">← All episodes</a></p>
<div class="ep"><div class="art"><img src="{BASE}/art/{r['key']}.jpg" alt="Cover art for {E(r['title'])}" width="1000" height="1000"></div>
<div data-pagefind-body><h1 data-pagefind-meta="title">{label}{E(r['title'])}</h1>
<div class="meta">{fmt_date(r['published'])} · {fmt_dur(r['duration_seconds'])}{' · transcript available' if r['transcript'] else ''}</div>
<audio controls preload="none" src="{r['audio_url']}"></audio>
<div class="btns" style="justify-content:flex-start">{listen}</div>
<div class="desc">{desc_html}</div></div></div>
<div data-pagefind-body>{''.join(sections)}</div>
<div class="pn">{pn}</div>"""
        write(f"episodes/{r['key']}/index.html",
              page(f"{label}{r['title']} · NEStalgia", body, "", desc=r["description"].split("\n")[0], image=f"/art/{r['key']}.jpg", current="eps"))

    # Episode list
    newest_first = sorted(data, key=lambda r: (r["published"], r["number"] or 0), reverse=True)
    body = f"""<h1>All episodes</h1>
<div class="controls"><input id="q" type="search" placeholder="Filter by title or number" aria-label="Filter episodes">
<button data-filter="all" aria-pressed="true">All</button><button data-filter="episode" aria-pressed="false">Episodes</button>
<button data-filter="special" aria-pressed="false">Specials</button><button id="sort" type="button">Newest first</button>
<span id="count"></span></div>
<div class="grid" id="grid">{''.join(card(r) for r in newest_first)}</div>
<script src="{BASE}/app.js"></script>"""
    write("episodes/index.html", page("Episodes · NEStalgia", body, "", current="eps"))

    # Home
    n_ep = sum(1 for r in data if r["type"] == "episode")
    n_tx = sum(1 for r in data if r["transcript"])
    n_notes = sum(1 for r in data if r["notes"])
    first_year = min(r["published"] for r in data)[:4]
    buttons = "".join(f'<a class="btn{" alt" if i > 1 else ""}" href="{u}" rel="noopener">{n}</a>' for i, (n, u) in enumerate(LINKS))
    latest = "".join(card(r) for r in newest_first[:12])
    body = f"""<div class="hero"><img src="{BASE}/logo.png" alt="NEStalgia">
<p class="tag">A chronological exploration of <b>every</b> NES game released in North America. Join us and play along.</p>
<div class="btns">{buttons}</div></div>
<div class="stats"><div class="stat"><b>{n_ep}</b>episodes</div><div class="stat"><b>{n_notes}</b>with show notes</div>
<div class="stat"><b>{n_tx}</b>transcripts</div><div class="stat"><b>{first_year}</b>since</div></div>
<h2>Search the show</h2>
<div id="search"></div>
<script>window.addEventListener("DOMContentLoaded",function(){{new PagefindUI({{element:"#search",showImages:false,showSubResults:false,resetStyles:false}});}});</script>
<h2>Latest episodes</h2><div class="grid">{latest}</div>
<p style="margin-top:20px"><a class="btn" href="{BASE}/episodes/">Browse all episodes</a>
<a class="btn alt" href="{SHEET_URL}" rel="noopener">Spreadsheet</a></p>
{patrons_html()}"""
    write("index.html", page("NEStalgia: every NES game, one episode at a time", body, "", search=True, current="home"))

    # Search page
    body = f"""<h1>Search</h1><p class="lede">Search every episode's description, show notes and transcript.</p><div id="search"></div>
<script>window.addEventListener("DOMContentLoaded",function(){{new PagefindUI({{element:"#search",showImages:false,resetStyles:false}});}});</script>"""
    write("search/index.html", page("Search · NEStalgia", body, "", search=True, current="search"))

    # About
    body = f"""<h1>About</h1><p class="lede">NEStalgia is a podcast that works through every NES game released in North America, in release order, one game per episode.
Each episode covers the history, the development story, how the game plays and where it lands, plus a vote on the
<b>Essential Games List</b>.</p>
<h2>Listen and follow</h2><div class="btns" style="justify-content:flex-start">{buttons}</div>
<h2>About this site</h2><p>Everything here is built from the
<a href="https://github.com/Xalechim/NEStalgia">NEStalgia repository on GitHub</a>: show notes, outlines, research and automatically generated transcripts.
The site updates itself when new episodes come out. Transcript speaker names are matched automatically and can be wrong on short interjections.</p>
<p>Episode data is also available as <a href="https://github.com/Xalechim/NEStalgia/blob/main/data/episodes.json">JSON</a> and
<a href="https://github.com/Xalechim/NEStalgia/blob/main/data/episodes.csv">CSV</a>.</p>"""
    write("about/index.html", page("About · NEStalgia", body, "", current="about"))
    extra = build_migrated(data, write, card)
    urls = ["/", "/episodes/", "/search/", "/about/"] + extra + [f"/episodes/{r['key']}/" for r in data]
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
          + "".join(f"<url><loc>{SITE_URL}{u}</loc></url>" for u in urls) + "</urlset>")
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")
    if DOMAIN:
        write("CNAME", DOMAIN + "\n")
    write("404.html", page("Not found · NEStalgia", f'<h1>Page not found</h1><p><a class="btn" href="{BASE}/">Back to the home page</a></p>', ""))
    print(f"site built: {len(data)} episode pages, base='{BASE}'")


if __name__ == "__main__":
    main()
