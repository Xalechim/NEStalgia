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
BASE = os.environ.get("SITE_BASE", "/NEStalgia").rstrip("/")
SITE_URL = "https://xalechim.github.io/NEStalgia"
LINKS = [
    ("Apple Podcasts", "https://itunes.apple.com/us/podcast/nestalgia/id1342922798"),
    ("Spotify", "https://open.spotify.com/show/1SoG0RFa4nPk0YqaXW6vRi"),
    ("Patreon", "https://www.patreon.com/nestalgia"),
    ("Twitch", "https://www.twitch.tv/nestalgia"),
    ("RSS", "https://anchor.fm/s/5808ab8/podcast/rss"),
]
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
    text = (REPO / path).read_text()
    lines = text.split("\n")
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    out = []
    for ln in lines:
        m = re.match(r"^( *)- ", ln)
        if m:  # Python-Markdown nests on 4 spaces; our notes use 2
            ln = " " * (len(m.group(1)) * 2) + ln[len(m.group(1)):]
        out.append(re.sub(r"(?<![(<\"])(https?://[^\s)>]+)", r"<\1>", ln))
    return markdown.markdown("\n".join(out), extensions=["tables"])


TURN = re.compile(r"^\*\*([^*]+)\*\* \[([\d:]+)\]: (.*)$")


def render_transcript(path):
    parts, note = [], ""
    for ln in (REPO / path).read_text().split("\n"):
        m = TURN.match(ln)
        if m:
            who, ts, txt = m.groups()
            parts.append(f'<p class="turn spk-{slug(who)}"><b>{E(who)}</b><span class="ts">{ts}</span>{E(txt)}</p>')
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
        for key, href, label in (("home", "/", "Home"), ("eps", "/episodes/", "Episodes"), ("search", "/search/", "Search"), ("about", "/about/", "About"))
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
<p style="margin-top:20px"><a class="btn" href="{BASE}/episodes/">Browse all episodes</a></p>"""
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
    write("404.html", page("Not found · NEStalgia", f'<h1>Page not found</h1><p><a class="btn" href="{BASE}/">Back to the home page</a></p>', ""))
    print(f"site built: {len(data)} episode pages, base='{BASE}'")


if __name__ == "__main__":
    main()
