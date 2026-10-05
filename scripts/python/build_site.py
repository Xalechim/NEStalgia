#!/usr/bin/env python3
"""Build the NEStalgia website into site/ from the data in this repo.

  python3 scripts/python/build_site.py            # for GitHub Pages (URLs start with /NEStalgia)
  SITE_BASE= python3 scripts/python/build_site.py # for a local preview served from site/

Needs: pip install pillow markdown. Search is added afterwards by Pagefind (see the workflow).
"""
import html
import json
import os
import re
import datetime
import shutil
import subprocess
import sys
import urllib.parse
from pathlib import Path

import markdown
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from textutil import nice_case  # noqa: E402
from build_episode_data import local_files  # noqa: E402
from wikipedia_intros import boilerplate_only  # noqa: E402
import share_cards  # noqa: E402
import bytes_info  # noqa: E402
import show_stats  # noqa: E402
import site_extras  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
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
PATREON_PAGE = "https://www.patreon.com/nestalgia"
CONTACT_EMAIL = "michaelespositofilm@gmail.com"
CONTACT_ALIAS = "eadd631cab7eee30e436788843647564"  # the private address FormSubmit issued after activation (hides the email from spam scrapers)
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
    text = (REPO / path).read_text().replace("\t", "    ").replace("\u00a0", " ")
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
            item = re.sub(r"^([-*+]) (?:[-*+\u2022\u25e6\u25aa\u2023] )+", r"\1 ", m.group(2))  # "- - text" / "- • text": one bullet is enough
            item = re.sub(r"^([-*+]) #(?=[^\s#])", r"\1 \\#", item)  # "#1: ..." is a number, not a heading
            item = re.sub(r"^[-*+] (\d+)\. ", r"- NUM\1:: ", item)  # "- 1. Heading": numbered already, flag it
            ln = " " * (4 * level) + item
        elif in_list and ln.strip() and ln.startswith(" "):
            # Heading-then-description pairs keep their line break; text that was hard-wrapped mid-sentence ("... ter-" / "ritory")
            # is joined back together.
            cont = ln.strip()
            soft = out and (out[-1].rstrip().endswith(("-", ",", ";")) or cont[:1].islower())
            if out and out[-1].strip() and not soft and not out[-1].endswith("  "):
                out[-1] += "  "
            ln = ln.lstrip()  # continuation line of the item above, not a code block
        elif not ln.strip():
            pass
        else:
            in_list, prev = False, -1
            ln = re.sub(r"^(\s*)#(?=[^\s#])", r"\1\\#", ln)
        out.append(re.sub(r"(?<![(<\"])(https?://[^\s)>]+)", r"<\1>", ln))
    html_out = markdown.markdown("\n".join(out), extensions=["tables"])
    # "- 1. Heading": the notes already number these, so show the number and drop the bullet; bold the heading line.
    def numbered(m):
        body = m.group(2)
        head, br, rest = body.partition("<br />")
        return f'<li class="num"><b class="n">{m.group(1)}.</b> ' + (f"<strong>{head.strip()}</strong>{br}{rest}" if br else body)
    return re.sub(r"<li>NUM(\d+):: (.*?)(?=</li>|<ul>)", numbered, html_out, flags=re.S)


def ts_seconds(ts):
    secs = 0
    for part in ts.split(":"):
        secs = secs * 60 + int(part)
    return secs


def ts_button(ts):
    return f'<button type="button" class="ts" data-t="{ts_seconds(ts)}" data-pagefind-ignore aria-label="Play from {ts}">{ts}</button>'


def load_offsets():
    f = REPO / "data/audio-offsets.json"
    return json.loads(f.read_text()) if f.exists() else {}


KIND_LABELS = [
    ("game", "Games"), ("hardware", "Hardware"), ("company", "Companies"), ("person", "People"),
    ("team_or_league", "Teams and leagues"), ("film_tv_music", "Film, TV and music"),
    ("event_or_term", "Terms and events"), ("website_or_article", "Articles, videos and sites"), ("other", "Other"),
]
SOURCE_LABELS = {"wikipedia": "Wikipedia", "reference": "Reference", "site": "On this site", "other": "Link"}


def nice(t):
    """Feed titles are often ALL CAPS; make them readable."""
    if not t.isupper():
        return t
    small = {"of", "the", "and", "a", "an", "in", "on", "to", "vs", "for"}
    words = []
    for i, w in enumerate(t.split()):
        if i and w.lower() in small:
            words.append(w.lower())
        elif w.rstrip(":").upper() in ("II", "III", "IV", "VI"):
            words.append(w)
        else:
            words.append(re.sub(r"[A-Za-z]+", lambda m: m.group().capitalize(), w).replace("'S", "'s"))
    return " ".join(words)


def review_path(number):
    """The written review for an episode (reviews/NNN-game-name.md), if there is one."""
    hits = sorted((REPO / "reviews").glob(f"{number:03d}-*.md"))
    return hits[0] if hits else None


def render_review(path, number):
    """Review markdown -> HTML for the Review tab, with the verdict from the spreadsheet shown at the top."""
    text = path.read_text()
    lines = text.split("\n")
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    html_ = markdown.markdown("\n".join(lines), extensions=["tables"])
    info = GAME_INFO.get(str(number)) or {}
    verdict = info.get("verdict")
    badge = ""
    if verdict:
        badge = (f'<p class="rverdict"><a class="gtag v-{verdict.lower().replace(" ", "")}" href="{BASE}/episodes/?{urllib.parse.urlencode({"verdict": verdict.lower()})}"'
                 f' title="See every episode with this verdict">Our verdict: {E(verdict)}</a></p>')
    return f'<div class="review">{badge}{html_}<p class="src">Written from our conversation in this episode.</p></div>'


def render_links(number):
    hits = sorted((REPO / "data/links").glob(f"{number:03d}-*.json"))
    if not hits:
        return ""
    f = hits[0]
    d = json.loads(f.read_text())
    by_kind = {}
    for it in d["items"]:
        by_kind.setdefault(it["kind"], []).append(it)
    out = ['<p class="note">Found automatically from the transcript and checked, but it can miss things or pick the wrong page. '
           'Spot a mistake? <a href="https://github.com/Xalechim/NEStalgia/issues/new">Tell us</a>.</p>']
    for kind, label in KIND_LABELS:
        items = by_kind.get(kind)
        if not items:
            continue
        out.append(f"<h3>{label}</h3><ul class=\"lk\">")
        for it in items:
            chips = []
            if it.get("episode_key"):
                chips.append(f'<a class="chip src-site" href="{BASE}/episodes/{it["episode_key"]}/">Our episode: {E(nice(it.get("episode_title", it["name"])))}</a>')
            for l in it["links"]:
                url = l["url"].replace("{BASE}", BASE)
                host = urllib.parse.urlparse(url).netloc.replace("www.", "") if url.startswith("http") else ""
                text = SOURCE_LABELS.get(l["source"], "Link") if l["source"] in ("wikipedia", "site") else l.get("label", host)
                ext = ' rel="noopener" target="_blank"' if url.startswith("http") else ""
                chips.append(f'<a class="chip src-{E(l["source"])}" href="{E(url)}"{ext}>{E(text)}<small>{E(host)}</small></a>')
            out.append(f'<li><div class="lk-h"><b>{E(it["name"])}</b> <span class="mention">mentioned at {ts_button(it["timestamp"])}</span></div>'
                       f'<p>{E(it["description"])}</p><div class="chips">{"".join(chips)}</div></li>')
        out.append("</ul>")
    return "".join(out)


TURN = re.compile(r"^\*\*([^*]+)\*\* \[([\d:]+)\]: (.*)$")


PARA = re.compile(r"^\[(\d+:\d\d(?::\d\d)?)\] (.*)$")


def render_transcript(path):
    """Paragraph format: [mm:ss] text. (Old speaker-turn format is still understood until converted.)"""
    parts, note = [], ""
    for ln in (REPO / path).read_text().split("\n"):
        m = PARA.match(ln)
        t = TURN.match(ln)
        if m:
            parts.append(f'<p class="para" data-t="{ts_seconds(m.group(1))}">{ts_button(m.group(1))} {E(m.group(2))}</p>')
        elif t:
            who, ts, txt = t.groups()
            parts.append(f'<p class="turn spk-{slug(who)}" data-t="{ts_seconds(ts)}"><b>{E(who)}</b> {ts_button(ts)} {E(txt)}</p>')
        elif ln.startswith("_") and ln.endswith("_"):
            note = ln.strip("_")
    return (f'<p class="note">{E(note)}</p>' if note else "") + "\n".join(parts)


WIKI_INTROS = {}
GAME_INFO = {}


def load_seo():
    """Per-page search-engine text, related-episode blocks and extra redirects, from site-src/seo.json."""
    f = SRC / "seo.json"
    return json.loads(f.read_text()) if f.exists() else {}


SEO = {}


def guide_link(r):
    """On an episode page, a link to the article that goes with it (SHMUP episodes -> the SHMUP guide). Helps readers and search engines."""
    info = GAME_INFO.get(str(r["number"])) if r["type"] == "episode" and r["number"] is not None else None
    if not info:
        return ""
    for g in SEO.get("episode_guides", []):
        if ((g.get("genre") and info["genre"] == g["genre"]) or (g.get("title_contains") and g["title_contains"].lower() in r["title"].lower())
                or (g.get("title_equals") and g["title_equals"].lower() == r["title"].strip().lower())):
            return f'<p class="guide-link" data-pagefind-ignore><a href="{BASE}{g["href"]}">{E(g["label"])} &rarr;</a></p>'
    return ""


def related_block(cfg, data, card_html):
    """'Every X we've covered': episode cards for a genre, newest game last, with a link to the filtered Episodes page."""
    rows = [r for r in data if r["type"] == "episode" and r["number"] is not None and (GAME_INFO.get(str(r["number"])) or {}).get("genre") == cfg["genre"]]
    rows.sort(key=lambda r: r["number"])
    if not rows:
        return ""
    more = f'{BASE}/episodes/?{urllib.parse.urlencode(cfg["see_all"])}'
    return (f'<section class="related" data-pagefind-ignore><h2>{E(cfg["heading"])} ({len(rows)})</h2>'
            f'<div class="grid">{"".join(card_html(r) for r in rows)}</div>'
            f'<p style="margin-top:16px"><a class="btn" href="{more}">{E(cfg.get("see_all_label", "See them all"))}</a></p></section>')


def load_game_info():
    f = REPO / "data/game-info.json"
    return json.loads(f.read_text()) if f.exists() else {}


def game_tags(r):
    """A 'GAME INFO' status screen under an episode's title. Every value is a link to the Episodes list filtered by it."""
    info = GAME_INFO.get(str(r["number"])) if r["type"] == "episode" and r["number"] is not None else None
    if not info:
        return ""

    def chip(label, value, query, cls=""):
        href = f'{BASE}/episodes/?{urllib.parse.urlencode(query)}'
        return f'<a class="gtag {cls}" href="{href}" title="See every episode with this {label.lower()}">{E(value)}</a>'

    cells = []  # (label, [chips], css class)
    if info["verdict"]:
        v = info["verdict"]
        cells.append(("Verdict", [chip("Verdict", v, {"verdict": v.lower()}, "v-" + v.lower().replace(" ", ""))], "c-verdict"))
    if info["genre"]:
        cells.append(("Genre", [chip("Genre", info["genre"], {"genre": info["genre"].lower()})], ""))
    if info["year"]:
        q = {"year": info["year"]}
        if info["month"]:
            q["month"] = info["month"].lower()
        cells.append(("Released", [chip("Release date", f'{info["month"] + " " if info["month"] else ""}{info["year"]}', q)], ""))
    cells.append(("Season", [chip("Season", f'Season {info["season"]}', {"season": info["season"]})], ""))
    if info["developers"]:
        cells.append(("Developer" + ("s" if len(info["developers"]) > 1 else ""), [chip("Developer", d, {"dev": d.lower()}) for d in info["developers"]], ""))
    if info["publishers"]:
        cells.append(("Publisher" + ("s" if len(info["publishers"]) > 1 else ""), [chip("Publisher", p, {"pub": p.lower()}) for p in info["publishers"]], ""))
    body = "".join(f'<div class="gcell {cls}"><span class="gk">{lab}</span><span class="gv">{"".join(chips)}</span></div>' for lab, chips, cls in cells)
    return f'<section class="ginfo" data-pagefind-ignore aria-label="Game info"><div class="ginfo-h">&#9654; Game info</div><div class="ginfo-b">{body}</div></section>'


def filter_panel(data):
    """The 'Filter by' controls for the Episodes page: choices and counts come from the episodes actually on the site."""
    import collections
    eps = [r for r in data if r["type"] == "episode" and str(r["number"]) in GAME_INFO]
    infos = [(r, GAME_INFO[str(r["number"])]) for r in eps]
    if not infos:
        return ""

    def options(counter, label=lambda k: k, order=None):
        keys = order or sorted(counter, key=lambda k: str(k).lower())
        return "".join(f'<option value="{E(str(k).lower())}">{E(str(label(k)))} ({counter[k]})</option>' for k in keys if counter.get(k))

    genres = collections.Counter(i["genre"] for _, i in infos if i["genre"])
    years = collections.Counter(i["year"] for _, i in infos if i["year"])
    months = collections.Counter(i["month"] for _, i in infos if i["month"])
    seasons = collections.Counter(i["season"] for _, i in infos)
    verdicts = collections.Counter(i["verdict"] for _, i in infos)
    devs = collections.Counter(d for _, i in infos for d in i["developers"])
    pubs = collections.Counter(p for _, i in infos for p in i["publishers"])
    months_order = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    has = collections.Counter()
    for r, _ in infos:
        has.update(w for w, on in (("review", r.get("review")), ("notes", r["notes"]), ("links", r.get("has_links")), ("transcript", r["transcript"])) if on)
    chips = "".join(f'<button type="button" class="chip v-{v.lower().replace(" ", "")}" data-verdict="{v.lower()}" aria-pressed="false">{v} <span>{verdicts[v]}</span></button>'
                    for v in ("Essential", "Play it", "Skip it") if verdicts.get(v))
    return f"""<details class="filters" open data-pagefind-ignore><summary>Filter by game details</summary>
<div class="fgrid">
<div class="fverdict"><span class="flabel">Verdict</span>{chips}</div>
<label>Genre<select data-f="genre"><option value="">Any genre</option>{options(genres)}</select></label>
<label>Release year<select data-f="year"><option value="">Any year</option>{options(years, order=sorted(years))}</select></label>
<label>Release month<select data-f="month"><option value="">Any month</option>{options(months, order=[m for m in months_order if m in months])}</select></label>
<label>Season<select data-f="season"><option value="">Any season</option>{options(seasons, label=lambda k: f"Season {k}", order=sorted(seasons))}</select></label>
<label>Episode has<select data-f="has"><option value="">Anything</option>{"".join(f'<option value="{k}">{lab} ({has[k]})</option>' for k, lab in (("review", "A review"), ("transcript", "A transcript"), ("links", "A Links tab"), ("notes", "Show notes")) if has.get(k))}</select></label>
<label>Developer<input type="text" data-f="dev" list="dev-list" placeholder="Type or pick, e.g. Capcom" autocomplete="off"></label>
<label>Publisher<input type="text" data-f="pub" list="pub-list" placeholder="Type or pick, e.g. Konami" autocomplete="off"></label>
</div>
<datalist id="dev-list">{"".join(f'<option value="{E(d)}">' for d in sorted(devs, key=str.lower))}</datalist>
<datalist id="pub-list">{"".join(f'<option value="{E(p)}">' for p in sorted(pubs, key=str.lower))}</datalist>
<button type="button" id="clear-filters" class="btn alt" hidden>Clear filters</button></details>"""


def load_wiki_intros():
    f = REPO / "data/wikipedia-intros.json"
    return json.loads(f.read_text()) if f.exists() else {}


def last_modified():
    """{repo file path: date (YYYY-MM-DD) of the last commit that touched it}, from git history. Empty if git isn't available."""
    try:
        out = subprocess.run(["git", "-C", str(REPO), "log", "--format=@%cs", "--name-only", "--", "episodes", "transcripts", "data/links", "reviews"],
                             capture_output=True, text=True, check=True).stdout
    except Exception:
        return {}
    mod, day = {}, None
    for line in out.splitlines():
        if line.startswith("@"):
            day = line[1:]
        elif line.strip() and line not in mod:  # newest commit comes first
            mod[line.strip()] = day
    return mod


ASSET_FILES = ("style.css", "app.js", "tabs.js", "player.js", "nav.js")


def asset(name):
    """Address of a stylesheet/script with a version that changes whenever the file does, so a browser never pairs an old
    cached file with a new page (that once made the menu links run together)."""
    import hashlib
    h = hashlib.sha1(b"".join((SRC / f).read_bytes() for f in ASSET_FILES if (SRC / f).exists())).hexdigest()[:8]
    return f"{BASE}/{name}?v={h}"


def bytes_records():
    """NEStalgia Bytes episodes (Patreon-only) as site records: no audio, notes, transcript or links, just a page pointing to Patreon."""
    f = REPO / "data/bytes-info.json"
    info = json.loads(f.read_text()) if f.exists() else {}
    out = []
    for n, v in info.items():
        name = bytes_info.cover_name(n, v["title"])
        if not (REPO / "assets/episode-art" / f"{name}.jpg").exists():
            continue  # bytes_art.py makes the cover; a Bytes episode without one waits for it
        out.append({"type": "bytes", "number": int(n), "title": v["title"], "feed_title": f"NEStalgia Bytes {int(n):03d} - {v['title']}",
                    "published": v["published"], "duration_seconds": None, "description": "", "audio_url": None, "episode_page": None,
                    "art": f"assets/episode-art/{name}.jpg", "guid": None, "patreon_url": v.get("patreon_url", "")})
    return out


def bytes_page_body(r, prev, nxt):
    url = r.get("patreon_url") or ""
    cta = (f'<a class="btn" href="{E(url)}" rel="noopener">Listen on Patreon</a>' if url else
           f'<a class="btn" href="{PATREON_PAGE}" rel="noopener">Find it on Patreon</a>')
    pn = "".join(f'<a href="{BASE}/episodes/{x["key"]}/">{lab}</a>' if x else "<span></span>"
                 for x, lab in ((prev, f'← {E(prev["title"])}' if prev else ""), (nxt, f'{E(nxt["title"])} →' if nxt else "")))
    when = fmt_date(r["published"]) + " · " if r["published"] else ""
    return f"""<p class="crumbs"><a href="{BASE}/episodes/">← All episodes</a></p>
<div class="ep"><div class="art"><img src="{BASE}/art/{r['key']}.jpg" alt="{E(cover_alt(r))}" width="1000" height="1000"></div>
<div data-pagefind-body><h1 data-pagefind-meta="title">Bytes {r['number']:03d} · {E(r['title'])}</h1>
<div class="meta">{when}NEStalgia Bytes · Patreon members only</div>
<aside class="patreon-box"><b>Members-only episode</b>
<p>NEStalgia Bytes is our Patreon-exclusive show about Famicom games you can play without any Japanese knowledge.
Members at the $5 level and above can listen to this episode on Patreon.</p>
<div class="btns" style="justify-content:flex-start">{cta}</div></aside></div></div>
<div class="pn">{pn}</div>"""


def cover_alt(r):
    """Alt text for an episode's cover art: what it is, for which game, which episode (helps screen readers and image search)."""
    game = nice_case(r["title"])
    if r["type"] == "bytes":
        return f"Cover art for NEStalgia Bytes {r['number']}: {game}"
    if r["type"] == "episode" and r["number"] is not None:
        return f"NES box art for {game}, the cover of NEStalgia episode {r['number']}"
    return f"Cover art for the NEStalgia episode {game}"


def analytics_tag():
    """GoatCounter's privacy-friendly counter (no cookies, no personal data), only when a code is set in site-src/analytics.json."""
    f = SRC / "analytics.json"
    code = (json.loads(f.read_text()).get("goatcounter") or "").strip() if f.exists() else ""
    if not re.fullmatch(r"[a-z0-9-]+", code):
        return ""
    return f'<script data-goatcounter="https://{code}.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>'


def jsonld_tag(items):
    """<script type=application/ld+json> for one or more schema.org objects (what Google reads to understand the page)."""
    if not items:
        return ""
    data = {"@context": "https://schema.org", "@graph": items} if len(items) > 1 else {"@context": "https://schema.org", **items[0]}
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False).replace("</", "<\\/") + "</script>"


def iso_duration(seconds):
    if not seconds:
        return None
    h, rem = divmod(int(seconds), 3600)
    m, sec = divmod(rem, 60)
    return "PT" + (f"{h}H" if h else "") + (f"{m}M" if m else "") + (f"{sec}S" if sec or not (h or m) else "")


SERIES = {"@type": "PodcastSeries", "name": "NEStalgia", "url": f"{SITE_URL}/"}


def series_jsonld():
    return {**SERIES, "description": "A chronological exploration of every NES game released in North America, one game per episode.",
            "image": f"{SITE_URL}/logo.png", "webFeed": "https://anchor.fm/s/5808ab8/podcast/rss",
            "sameAs": [u for _, u in LINKS if u != "https://anchor.fm/s/5808ab8/podcast/rss"],
            "inLanguage": "en"}


def episode_jsonld(r, url, desc):
    ep = {"@type": "PodcastEpisode", "name": r["title"], "url": f"{SITE_URL}{url}", "datePublished": r["published"],
          "description": desc, "partOfSeries": SERIES, "image": f"{SITE_URL}/art/{r['key']}.jpg"}
    if r["type"] == "episode" and r["number"] is not None:
        ep["episodeNumber"] = r["number"]
        ep["about"] = {"@type": "VideoGame", "name": nice_case(r["title"]),
                       "gamePlatform": "Nintendo Entertainment System"}
    if r["type"] == "bytes":
        ep["isAccessibleForFree"] = False
    if iso_duration(r.get("duration_seconds")):
        ep["timeRequired"] = iso_duration(r["duration_seconds"])
    if r.get("audio_url"):
        ep["associatedMedia"] = {"@type": "AudioObject", "contentUrl": r["audio_url"], "encodingFormat": "audio/mpeg"}
    return ep


def article_jsonld(a, desc, img):
    """Structured data for an article page: headline, author, date and picture, so search engines and AI answers can cite it properly."""
    out = {"@type": "BlogPosting", "headline": a["title"], "datePublished": str(a["date"])[:10], "author": {"@type": "Person", "name": a.get("author") or "Michael Esposito"},
           "publisher": {"@type": "Organization", "name": "NEStalgia", "url": f"{SITE_URL}/", "logo": {"@type": "ImageObject", "url": f"{SITE_URL}/logo.png"}},
           "mainEntityOfPage": f"{SITE_URL}/{a['path'].strip('/')}/", "inLanguage": "en"}
    if desc:
        out["description"] = desc
    if img:
        out["image"] = img if img.startswith("http") else f"{SITE_URL}{img}"
    return out


def breadcrumbs(*trail):
    """trail = (name, path) pairs from the home page down; the last is the current page."""
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i, "name": n, "item": f"{SITE_URL}{u}"} for i, (n, u) in enumerate(trail, 1)]}


def page(title, body, path, desc="", image=None, search=False, current="", jsonld=None, og_type="website", card=None, published=None, image_dims=None):
    """`path` is this page's address on the site (like /about/); it becomes the canonical link. Leave it empty for no canonical."""
    desc = desc or "A chronological exploration of every NES game released in North America."
    if not image:  # every page gets the NEStalgia card unless it has its own picture
        image, image_dims = "/art/share/default.jpg", (1200, 630)
        title_alt = "NEStalgia: A chronological exploration of every NES game"
    else:
        title_alt = title
    img = f'<meta property="og:image" content="{SITE_URL}{image}">'
    if image:
        img += f'<meta property="og:image:alt" content="{E(title_alt)}">'
        if image_dims:
            img += f'<meta property="og:image:width" content="{image_dims[0]}"><meta property="og:image:height" content="{image_dims[1]}">'
    img += f'<meta property="og:site_name" content="NEStalgia">'
    if path:
        img += f'<meta property="og:url" content="{SITE_URL}{path}">'
    if published:
        img += f'<meta property="article:published_time" content="{published}">'
    card = card or "summary_large_image"
    pf = (f'<link href="{BASE}/pagefind/pagefind-ui.css" rel="stylesheet">'
          f'<script src="{BASE}/pagefind/pagefind-ui.js"></script>') if search else ""
    nav = "".join(
        f'<a href="{BASE}{href}"{" aria-current=page" if current == key else ""}>{label}</a>'
        for key, href, label in (("home", "/", "Home"), ("eps", "/episodes/", "Episodes"), ("essential", "/essential/", "Essentials"), ("stats", "/stats/", "Stats"), ("articles", "/articles/", "Articles"), ("search", "/search/", "Search"), ("contact", "/contact/", "Contact"))
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<script>(function(){{try{{var t=localStorage.getItem("theme");if(!t)t=matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light";document.documentElement.dataset.theme=t}}catch(e){{}}document.documentElement.classList.add("js-nav")}})()</script>
<title>{E(title)}</title>
{f'<link rel="canonical" href="{SITE_URL}{path}">' if path else ""}
<meta name="description" content="{E(desc[:200])}">
<meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc[:200])}">{img}
<meta property="og:type" content="{og_type}"><meta name="twitter:card" content="{card}">
<link rel="icon" href="{BASE}/icon.png"><link rel="apple-touch-icon" href="{BASE}/icon.png">
<link rel="stylesheet" href="{asset('style.css')}">{pf}{jsonld_tag(jsonld)}</head>
<body><a class="skip" href="#main">Skip to content</a>
<header class="site"><div class="bar"><a class="brand" href="{BASE}/"><img src="{BASE}/logo.png" alt="NEStalgia"></a><nav id="nav" aria-label="Main"><div class="links">{nav}</div><div class="more" hidden><button type="button" class="morebtn" aria-expanded="false" aria-haspopup="true" aria-controls="moremenu">More &#9662;</button><div class="menu" id="moremenu" hidden></div></div><button id="theme" type="button" aria-label="Switch between light and dark mode"></button></nav></div></header>
<main id="main">{body}</main>
<footer class="site">NEStalgia is a podcast by Michael Esposito and friends. Text is
<a href="https://creativecommons.org/licenses/by-nc/4.0/">CC BY-NC 4.0</a>; game art belongs to its owners.
<a href="{BASE}/about/">About</a> · <a href="https://github.com/Xalechim/NEStalgia">Source on GitHub</a>.</footer>
<script src="{asset('nav.js')}"></script>
<script>document.getElementById("theme").addEventListener("click",function(){{var t=document.documentElement.dataset.theme==="dark"?"light":"dark";document.documentElement.dataset.theme=t;try{{localStorage.setItem("theme",t)}}catch(e){{}}}});</script>{analytics_tag()}
</body></html>"""


def write(rel, content):
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def card(r):
    label = (f"{r['number']:03d}" if r["number"] is not None and r["type"] == "episode" else
             f"Bytes {r['number']:03d}" if r["type"] == "bytes" else ("Special" if r["type"] == "special" else ""))
    tags = [t for t, on in (("REVIEW", r.get("review")), ("NOTES", r["notes"]), ("LINKS", r.get("has_links")), ("TRANSCRIPT", r["transcript"]), ("PATREON", r["type"] == "bytes")) if on]
    info = GAME_INFO.get(str(r["number"])) if r["type"] == "episode" and r["number"] is not None else None
    extra = ""
    if info:
        has = [w for w, on in (("review", r.get("review")), ("notes", r["notes"]), ("links", r.get("has_links")), ("transcript", r["transcript"])) if on]
        extra = (f' data-verdict="{E(info["verdict"].lower())}" data-genre="{E(info["genre"].lower())}" data-year="{info["year"] or ""}"'
                 f' data-month="{E((info["month"] or "").lower())}" data-season="{info["season"]}"'
                 f' data-dev="{E("|".join(info["developers"]).lower())}" data-pub="{E("|".join(info["publishers"]).lower())}"'
                 f' data-has="{" ".join(has)}"')
    spans = "".join('<span class="badge b-%s">%s</span>' % (t.lower(), t) for t in tags)
    badge = f'<div class="badges">{spans}</div>' if tags else ""
    return (f'<a class="card" href="{BASE}/episodes/{r["key"]}/" data-type="{r["type"]}" data-date="{r["published"]}" '
            f'data-num="{r["number"] if r["number"] is not None else ""}" data-title="{E(r["title"].lower())}"{extra}>'
            f'<img src="{BASE}/art/thumb/{r["key"]}.jpg" alt="" loading="lazy" width="300" height="300">'
            f'<div class="t"><span class="n">{label}</span>{E(r["title"])}{badge}</div></a>')


MIG = SRC / "migrated"


def up_next_html():
    f = REPO / "data/next-episode.json"
    if not f.exists():
        return ""
    n = json.loads(f.read_text())
    art = ""
    if n.get("has_art") and (REPO / "data/next-episode.jpg").exists():
        (OUT / "art").mkdir(exist_ok=True)
        shutil.copy(REPO / "data/next-episode.jpg", OUT / "art/next.jpg")
        art = f'<img src="{BASE}/art/next.jpg?v={n["number"]}" alt="" width="200">'
    when = ""
    if n.get("publish_date"):
        d = datetime.date.fromisoformat(n["publish_date"])
        when = f'<div class="meta">Out {d.strftime("%A, %B")} {d.day}</div>'
    blurb = f'<p>{E(n["extract"])}</p>' if n.get("extract") else ""
    more = f'<p><a href="{E(n["wikipedia_url"])}" rel="noopener">Read more on Wikipedia</a></p>' if n.get("wikipedia_url") else ""
    return (f'<h2>Up next</h2><div class="upnext{" has-art" if art else ""}">{art}<div><span class="n">Episode {n["number"]}</span>'
            f'<h3>{E(n["title"])}</h3>{when}{blurb}{more}</div></div>')


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
        a["body"] = re.sub(r"(?:Start|End)Fragment", "", a["body"])  # leftovers from pasting into Squarespace
        tags = "".join(f'<span class="atag">{E(t)}</span>' for t in a["tags"])
        ov = (SEO.get("articles") or {}).get(a["path"].rstrip("/"), {})
        extra = related_block(ov["related"], data, card_html) if ov.get("related") else ""
        body = f"""<p class="crumbs"><a href="{BASE}/articles/">← All articles</a></p>
<article data-pagefind-body><h1 data-pagefind-meta="title">{E(a["title"])}</h1>
<div class="meta">{fmt_date(a["date"])} · {E(a["author"])}</div>{('<div class="tags">'+tags+'</div>') if tags else ""}
<div class="prose">{prose(a["body"], ep_map)}</div></article>{extra}"""
        img = a["image"].replace("{BASE}", "") if a.get("image") else None
        write(a["path"].strip("/") + "/index.html",
              page(ov.get("title") or f'{a["title"]} · NEStalgia', body, "/" + a["path"].strip("/") + "/", desc=ov.get("description") or a["excerpt"], image=img, current="articles",
                   og_type="article", published=str(a["date"])[:10] if a.get("date") else None,
                   jsonld=[article_jsonld(a, ov.get("description") or a["excerpt"], img), breadcrumbs(("Home", "/"), ("Articles", "/articles/"), (a["title"], "/" + a["path"].strip("/") + "/"))]))
    cards = "".join(
        f'<a class="card wide" href="{BASE}{a["path"]}/">'
        + (f'<img src="{(a["image"] or "").replace("{BASE}", BASE)}" alt="" loading="lazy">' if a.get("image") else "")
        + f'<div class="t"><span class="n">{fmt_date(a["date"])}</span><b>{E(a["title"])}</b><br>{E(a["excerpt"][:160])}</div></a>'
        for a in articles)
    features = f"""<h2>Features</h2><div class="btns" style="justify-content:flex-start">
<a class="btn" href="{BASE}/essential/">Essential Games List</a><a class="btn" href="{BASE}/zapper/">The NES Zapper</a>
<a class="btn" href="{BASE}/nrd1/">Nintendo R&amp;D1 games</a></div>"""
    write("articles/index.html", page("Articles · NEStalgia", f'<h1>Articles</h1>{features}<h2>Writing</h2><div class="grid articles">{cards}</div>', "/articles/", current="articles"))

    # Pages
    for name, pg in pages.items():
        if name == "essential" and (OUT / "essential/index.html").exists():
            real.add(pg["path"].rstrip("/"))
            continue  # replaced by the generated Essential Games List
        wide = name == "zapper"
        inner = prose(pg["body"], ep_map)
        title = pg["title"]
        body = (f'<div class="rawpage">{inner}</div>' if wide else
                f'<h1 data-pagefind-meta="title">{E(title)}</h1><div class="prose" data-pagefind-body>{inner}</div>')
        write(f"{name}/index.html", page(f"{title} · NEStalgia", body, f"/{name}/", current="articles"))
        real.add(pg["path"].rstrip("/"))

    # With the private alias the real address never appears on the page; without it, it is at least split up for scrapers
    contact_attrs = (f'data-alias="{CONTACT_ALIAS}"' if CONTACT_ALIAS else
                     f'data-user="{CONTACT_EMAIL.split("@")[0]}" data-domain="{CONTACT_EMAIL.split("@")[1]}"')
    # Contact: a form that emails the show, sent through FormSubmit (no account needed; the first message must be confirmed once)
    write("contact/index.html", page("Contact · NEStalgia", f"""<h1>Contact</h1>
<p class="lede">Questions, corrections, or a game we should cover? Send us a message and it goes straight to our inbox.</p>
<p id="sent" class="sent" hidden role="status"><b>Message sent.</b> Thanks for writing. We read everything.</p>
<form class="cform" method="POST" {contact_attrs}>
<input type="hidden" name="_subject" value="New message from nestalgiacast.com">
<input type="hidden" name="_next" value="{SITE_URL}/contact/?sent=1">
<input type="hidden" name="_template" value="table">
<input type="text" name="_honey" tabindex="-1" autocomplete="off" aria-hidden="true" style="position:absolute;left:-9999px">
<label>Your name<input name="name" required autocomplete="name"></label>
<label>Your email<input type="email" name="email" required autocomplete="email"></label>
<label>What is this about?<select name="topic"><option>General question</option><option>Game suggestion</option><option>Correction (show notes, transcript, links)</option><option>Guest or collaboration</option><option>Something else</option></select></label>
<label>Message<textarea name="message" rows="7" required></textarea></label>
<button class="btn" type="submit">Send message</button>
<p class="note">Sent through FormSubmit, which delivers it to our email. We only use your address to reply.</p>
</form>
<noscript><p class="note">The form needs JavaScript. Without it, reach us on Patreon or GitHub below.</p></noscript>
<script>(function(){{var f=document.querySelector(".cform");f.action="https://formsubmit.co/"+(f.dataset.alias||(f.dataset.user+"@"+f.dataset.domain));
if(location.search.indexOf("sent=1")!==-1){{document.getElementById("sent").hidden=false;}}}})();</script>
<h2>Other ways to reach us</h2>
<div class="btns" style="justify-content:flex-start"><a class="btn" href="https://www.patreon.com/nestalgia">Patreon</a>
<a class="btn alt" href="https://github.com/Xalechim/NEStalgia/issues/new">Report a correction on GitHub</a></div>""", "/contact/", current="contact"))
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
    for old, tgt in (SEO.get("redirects") or {}).items():  # old addresses that still get visitors or search impressions
        if not (OUT / old.strip("/") / "index.html").exists():
            write(old.strip("/") + "/index.html", redirect_stub(tgt))
            n += 1
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
    OFFSETS = load_offsets()
    global WIKI_INTROS
    WIKI_INTROS = load_wiki_intros()
    global GAME_INFO, SEO
    GAME_INFO = load_game_info()
    SEO = load_seo()
    # data/episodes.json can be a little stale (it is refreshed on a schedule); what is actually in the repo wins.
    data = [r for r in data if r["type"] != "bytes"] + bytes_records()  # Bytes come from the spreadsheet, not the feed
    for r in data:
        if r["type"] == "bytes":  # paid content: never any notes, transcript or links
            r["notes"], r["transcript"], r["has_links"] = [], None, False
            continue
        r["notes"], r["transcript"] = local_files(r["type"], r["number"], r["title"], r["feed_title"])
        r["has_links"] = bool(r["type"] == "episode" and r["number"] is not None and render_links(r["number"]))
        r["review"] = review_path(r["number"]) if r["type"] == "episode" and r["number"] is not None else None
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    for f in ("style.css", "app.js", "tabs.js", "player.js", "nav.js", "logo.png", "icon.png"):
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

    # Share cards (the picture people see when a link is posted in Discord, Twitter, iMessage ...)
    share_cards.make_default_card(SRC / "logo.png", "A chronological exploration of every NES game.", OUT / "art/share/default.jpg")
    for r in data:
        if not r["art"]:
            continue
        meta = GAME_INFO.get(str(r["number"])) if r["type"] == "episode" and r["number"] is not None else None
        bits = []
        if meta:
            bits = [(meta["publishers"] or meta["developers"] or [""])[0], f'{meta["month"] + " " if meta["month"] else ""}{meta["year"] or ""}'.strip()]
        game = nice_case(r["title"])
        share_cards.make_episode_card(REPO / r["art"], share_cards.clean_label(r["number"], r["type"]), game,
                                      "Patreon" if r["type"] == "bytes" else (meta["verdict"] if meta else ""), " · ".join(b for b in bits if b), SRC / "logo.png",
                                      OUT / "art/share" / f"{r['key']}.jpg")

    regular = sorted((r for r in data if r["published"] and r["type"] != "bytes"), key=lambda r: (r["published"], r["number"] or 0))
    bytes_eps = sorted((r for r in data if r["type"] == "bytes"), key=lambda r: r["number"])
    for group in (regular, bytes_eps):
        for i, r in enumerate(group):
            r["prev"] = group[i - 1] if i > 0 else None
            r["next"] = group[i + 1] if i + 1 < len(group) else None

    related_idx = site_extras.build_related_index(data, GAME_INFO)
    related_html_for = lambda r: site_extras.related_html(r, related_idx, GAME_INFO, card, E, BASE)

    for r in data:
        if r["type"] == "bytes":
            url = f"/episodes/{r['key']}/"
            desc = f"NEStalgia Bytes {r['number']:03d}: {r['title']}. A members-only Patreon episode about a Famicom game."
            write(f"episodes/{r['key']}/index.html",
                  page(f"{r['title']} · NEStalgia Bytes {r['number']} (Patreon) · NEStalgia", bytes_page_body(r, r["prev"], r["next"]), url, desc=desc,
                       image=f"/art/share/{r['key']}.jpg", current="eps", og_type="article", published=r["published"] or None, image_dims=(1200, 630),
                       jsonld=[episode_jsonld(r, url, desc), breadcrumbs(("Home", "/"), ("Episodes", "/episodes/"), (r["title"], url))]))
            continue

        def kind(p):
            return "Outline" if p.endswith("-outline.md") else "Early notes" if p.endswith("-early-notes.md") else "Show notes"

        notes = "".join(
            (f"<h3>{kind(p)}</h3>" if len(r["notes"]) > 1 else "") + render_notes(p) for p in r["notes"]
        )
        label = f"{r['number']:03d} · " if r["type"] == "episode" and r["number"] is not None else ""
        def desc_p(p):  # the Patreon boilerplate becomes a 'CONTINUE?' callout; everything else is plain manual text
            if p.strip().lower().startswith("support nestalgia directly"):
                return f'<aside class="continue"><b>Continue? Join us on Patreon</b><p>{linkify(p)}</p></aside>'
            return f"<p>{linkify(p)}</p>"
        desc_html = "".join(desc_p(p) for p in r["description"].split("\n\n") if p.strip())
        intro = WIKI_INTROS.get(str(r["number"])) if r["type"] == "episode" and boilerplate_only(r["description"]) else None
        if intro and intro.get("text"):  # a real description above the Patreon boilerplate, credited to Wikipedia
            credit = (f'<p class="src">From <a href="{E(intro["url"])}" rel="noopener">Wikipedia: {E(intro["title"])}</a> '
                      f'(<a href="https://creativecommons.org/licenses/by-sa/4.0/" rel="noopener">CC BY-SA 4.0</a>)</p>') if intro.get("url") else ""
            desc_html = f'<div class="manual"><div class="mtab">About the game</div><p>{E(intro["text"])}</p>{credit}</div>{desc_html}'
        else:
            intro = None
        panels = []  # (id, tab label, html)
        if r.get("review"):  # first in the list, so it is the tab that opens
            panels.append(("review", "Review", f'<div class="panel">{render_review(r["review"], r["number"])}</div>'))
        if notes:
            panels.append(("notes", "Show notes", f'<div class="panel">{notes}</div>'))
        links_html = render_links(r["number"]) if r["type"] == "episode" and r["number"] is not None else ""
        sync = ('<div class="sync" data-pagefind-ignore>Click a timestamp to play from there. Landing a little off? '
                '<button type="button" data-nudge="-5">&minus;5s</button> <button type="button" data-nudge="5">+5s</button> '
                '<button type="button" data-nudge="0">reset</button> <output class="sync-val"></output></div>') if (r["transcript"] or links_html) else ""
        if links_html:
            panels.append(("links", "Links", f'<div class="panel">{sync}{links_html}</div>'))
        if r["transcript"]:
            panels.append(("transcript", "Transcript", f'<div class="panel">{sync}{render_transcript(r["transcript"])}</div>'))
        if len(panels) > 1:
            tabbar = "".join(
                f'<button role="tab" id="t-{pid}" aria-controls="p-{pid}" aria-selected="{"true" if i == 0 else "false"}">{lab}</button>'
                for i, (pid, lab, _) in enumerate(panels))
            body_tabs = "".join(
                f'<section role="tabpanel" id="p-{pid}" aria-labelledby="t-{pid}"{"" if i == 0 else " hidden"}>{html_}</section>'
                for i, (pid, _, html_) in enumerate(panels))
            tabs_html = (f'<div class="tabs"><div class="tablist" role="tablist" aria-label="Episode extras">{tabbar}</div>{body_tabs}</div>'
                         f'<noscript><style>.tabs [role=tabpanel][hidden]{{display:block}}.tablist{{display:none}}</style></noscript>'
                         f'<script src="{asset("tabs.js")}" defer></script>')
        elif panels:
            tabs_html = f'<h2>{panels[0][1]}</h2>{panels[0][2]}'
        else:
            tabs_html = ""
        pn = "".join(
            f'<a href="{BASE}/episodes/{x["key"]}/">{lab}</a>' if x else "<span></span>"
            for x, lab in ((r["prev"], f'← {E(r["prev"]["title"])}' if r["prev"] else ""), (r["next"], f'{E(r["next"]["title"])} →' if r["next"] else ""))
        )
        listen = "".join(f'<a class="btn alt" href="{u}" rel="noopener">{n}</a>' for n, u in LINKS[:2])
        off = OFFSETS.get(str(r["number"])) if r["type"] == "episode" and r["number"] is not None else None
        ep_attrs = f' data-ep="{r["key"]}" data-offsets=\'{json.dumps(off)}\'' if off else f' data-ep="{r["key"]}"'
        body = f"""<p class="crumbs"><a href="{BASE}/episodes/">← All episodes</a></p>
<div class="ep"{ep_attrs}><div class="art"><img src="{BASE}/art/{r['key']}.jpg" alt="{E(cover_alt(r))}" width="1000" height="1000"></div>
<div data-pagefind-body><h1 data-pagefind-meta="title">{label}{E(r['title'])}</h1>
{game_tags(r)}{guide_link(r)}<div class="meta">{fmt_date(r['published'])} · {fmt_dur(r['duration_seconds'])}{' · transcript available' if r['transcript'] else ''}</div>
<audio id="player" controls preload="none" src="{r['audio_url']}"></audio>
<div class="btns" style="justify-content:flex-start">{listen}</div>
<div class="desc">{desc_html}</div></div></div>
<div data-pagefind-body>{tabs_html}</div>
{related_html_for(r)}
<div class="pn">{pn}</div>{'<script src="' + asset("player.js") + '" defer></script>' if (r["transcript"] or links_html) else ""}"""
        url = f"/episodes/{r['key']}/"
        desc = intro["text"] if intro else r["description"].split("\n")[0]
        if r["type"] == "episode" and r["number"] is not None:  # the game's name first: that is what people search for
            game = nice_case(r["title"])
            seo_title = f"{game} (NES) · Episode {r['number']} · NEStalgia"
        else:
            seo_title = f"{r['title']} · NEStalgia"
        write(f"episodes/{r['key']}/index.html",
              page(seo_title, body, url, desc=desc, image=f"/art/share/{r['key']}.jpg", current="eps",
                   og_type="article", published=r["published"], image_dims=(1200, 630),
                   jsonld=[episode_jsonld(r, url, desc), breadcrumbs(("Home", "/"), ("Episodes", "/episodes/"), (r["title"], url))]))

    # Episode list
    newest_first = sorted(data, key=lambda r: (r["published"], r["number"] or 0), reverse=True)
    body = f"""<h1>All episodes</h1>
<div class="controls"><input id="q" type="search" placeholder="Filter by title or number" aria-label="Filter episodes">
<button data-filter="all" aria-pressed="true">All</button><button data-filter="episode" aria-pressed="false">Episodes</button>
<button data-filter="special" aria-pressed="false">Specials</button><button data-filter="bytes" aria-pressed="false">Bytes</button><button id="sort" type="button">Newest first</button>
<span id="count"></span></div>
{filter_panel(data)}
<div class="grid" id="grid">{''.join(card(r) for r in newest_first)}</div>
<script src="{asset('app.js')}"></script>"""
    write("episodes/index.html", page("Episodes · NEStalgia", body, "/episodes/", current="eps"))

    # Home
    buttons = "".join(f'<a class="btn{" alt" if i > 1 else ""}" href="{u}" rel="noopener">{n}</a>' for i, (n, u) in enumerate(LINKS))
    latest = "".join(card(r) for r in newest_first[:12])  # Bytes are mixed in by release date
    body = f"""<div class="hero"><h1 class="sr">NEStalgia: A chronological exploration of every NES game</h1><img src="{BASE}/logo.png" alt="">
<p class="tag">A chronological exploration of <b>every</b> NES game released in North America. Join us and play along.</p>
<div class="btns">{buttons}</div></div>
{up_next_html()}
<h2>Search the show</h2>
<div id="search"></div>
<script>window.addEventListener("DOMContentLoaded",function(){{new PagefindUI({{element:"#search",showImages:false,showSubResults:false,resetStyles:false}});}});</script>
<h2>Latest episodes</h2><div class="grid">{latest}</div>
<p style="margin-top:20px"><a class="btn" href="{BASE}/episodes/">Browse all episodes</a>
<a class="btn alt" href="{SHEET_URL}" rel="noopener">Spreadsheet</a></p>
{patrons_html()}"""
    write("index.html", page("NEStalgia: A chronological exploration of every NES game", body, "/", desc="A chronological exploration of every NES game.", search=True, current="home", jsonld=[series_jsonld()]))

    # Search page
    body = f"""<h1>Search</h1><p class="lede">Search every episode's description, show notes and transcript.</p><div id="search"></div>
<script>window.addEventListener("DOMContentLoaded",function(){{new PagefindUI({{element:"#search",showImages:false,resetStyles:false}});}});</script>"""
    write("search/index.html", page("Search · NEStalgia", body, "/search/", search=True, current="search"))

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
    write("about/index.html", page("About · NEStalgia", body, "/about/", current="about"))
    if GAME_INFO:
        write("essential/index.html", page("Essential Games List · NEStalgia", site_extras.essential_body(data, GAME_INFO, card, E, BASE, asset("app.js")), "/essential/",
                                           desc="Every NES game the NEStalgia podcast voted Essential, in the order we covered them.", current="essential"))
        write("stats/index.html", page("The Stats · NEStalgia", site_extras.stats_body(show_stats.compute(GAME_INFO, data), E, BASE), "/stats/",
                                       desc="Which NES publishers, developers and genres score best on NEStalgia, plus streaks, droughts and how the hosts vote.", current="stats"))
    extra = build_migrated(data, write, card)
    mod = last_modified()
    lastmod = {}
    for r in data:  # the newest change to anything shown on the episode's page
        files = list(r["notes"]) + ([r["transcript"]] if r["transcript"] else []) + ([str(r["review"].relative_to(REPO))] if r.get("review") else [])
        if r["type"] == "episode" and r["number"] is not None:
            files += [str(f.relative_to(REPO)) for f in (REPO / "data/links").glob(f"{r['number']:03d}-*.json")]
        days = [mod[f] for f in files if f in mod] + ([r["published"][:10]] if r["published"] else [])
        if days:
            lastmod[f"/episodes/{r['key']}/"] = max(days)
    if lastmod:
        lastmod["/"] = lastmod["/episodes/"] = max(lastmod.values())
    urls = ["/", "/episodes/", "/essential/", "/stats/", "/search/", "/about/"] + [u for u in extra if u.rstrip("/") != "/essential"] + [f"/episodes/{r['key']}/" for r in data]
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
          + "".join(f"<url><loc>{SITE_URL}{u}</loc>" + (f"<lastmod>{lastmod[u]}</lastmod>" if u in lastmod else "") + "</url>" for u in urls) + "</urlset>")
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")
    if DOMAIN:
        write("CNAME", DOMAIN + "\n")
    write("404.html", page("Not found · NEStalgia", f'<h1>Page not found</h1><p><a class="btn" href="{BASE}/">Back to the home page</a></p>', ""))
    print(f"site built: {len(data)} episode pages, base='{BASE}'")


if __name__ == "__main__":
    main()
