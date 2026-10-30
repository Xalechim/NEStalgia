#!/usr/bin/env python3
"""Build data/episodes.json and data/episodes.csv from the podcast RSS feed.

Run any time (it only reads the feed and the repo, and rewrites the two files):
  python3 scripts/python/build_episode_data.py
"""
import csv
import glob
import html
import json
import random
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

FEED = "https://anchor.fm/s/5808ab8/podcast/rss"
FEED_ID = "5808ab8"
# The feed's host caches every address it is asked for, for up to 7 days (s-maxage=605396), and only clears the cache for the one
# plain address above when an episode is published. Any other address stays frozen at whatever it showed the first time someone
# asked: on 2026-10-30 a GitHub run at 6:54am Eastern was still handed a feed without the episode that went out at 3:00am, from the
# addresses we used to rely on (a trailing slash, a capital "RSS": they worked once, then our own regular updates froze them).
# The host's origin ignores letter case in the id, in "podcast" and in "rss", but its cache does not, so a random mix of capitals
# is an address nobody has asked for before (about 8,000 of them), and always comes straight from the source.
REPO = Path(__file__).resolve().parents[2]
NS = {"i": "http://www.itunes.com/dtds/podcast-1.0.dtd"}


def slug(s: str) -> str:
    s = s.lower().replace("'", "").replace("’", "")
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s)).strip("-")


def classify(title: str):
    """Return (kind, number, name, file_key) for a feed title."""
    t = html.unescape(title).strip()
    m = re.match(r"^(?:NES\s+)?(\d+)\s*-\s*(.*)", t, re.I)
    if m:
        n = int(m.group(1))
        return "episode", n, m.group(2).strip(), f"{n:03d}-{slug(m.group(2))}"
    m = re.match(r"^Nestalgia Bytes\s+(\d+)\s*-\s*(.*)", t, re.I)
    if m:
        n = int(m.group(1))
        return "bytes", n, m.group(2).strip(), f"nb-{n:03d}-{slug(m.group(2))}"
    m = re.match(r"^(?:S|SPECIAL\s*)0*(\d+)\s*-\s*(.*)", t, re.I)
    if m:
        n = int(m.group(1))
        return "special", n, m.group(2).strip(), f"s{n:03d}-{slug(m.group(2))}"
    return ("special" if t.lower().startswith("special") else "other"), None, t, slug(t)


def plain(text: str) -> str:
    text = re.sub(r"<br\s*/?>|</p>|</li>", "\n", text or "", flags=re.I)
    text = html.unescape(re.sub(r"<[^>]+>", "", text))
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def duration_seconds(d: str):
    if not d:
        return None
    if ":" in d:
        secs = 0
        for p in d.split(":"):
            secs = secs * 60 + int(float(p))
        return secs
    return int(float(d))


def repo_files(*patterns):
    out = []
    for p in patterns:
        out += [str(Path(f).relative_to(REPO)) for f in sorted(glob.glob(str(REPO / p)))]
    return out


def local_files(kind, num, name, title):
    """The show notes and transcript in this repo for a feed item: (list of notes paths, transcript path or None)."""
    if kind == "episode" and num is not None:
        notes = repo_files(f"episodes/{num:03d}-*.md")
        tx = repo_files(f"transcripts/{num:03d}-*.md")
    elif kind == "bytes":
        notes, tx = [], []  # NEStalgia Bytes are Patreon-only: no notes or transcripts are published
    elif kind == "special" and num is not None:
        notes = repo_files(f"episodes/specials/s{num:03d}-*.md")
        tx = repo_files(f"transcripts/s{num:03d}-*.md")
    elif kind == "special":
        notes, tx = repo_files(f"episodes/specials/{slug(name)}*.md"), []
    else:
        notes, tx = [], []
    # Episode 1 exists twice in the feed (original and remastered); the notes are for the remaster.
    notes = [f for f in notes if ("remastered" in f) == ("remastered" in title.lower())]
    return notes, (tx[0] if tx else None)


def ensure_art(path: Path, url: str) -> None:
    """Download a cover and save it as a 1000 px JPEG (quality 80), if we don't have it yet."""
    if path.exists():
        return
    import io

    from PIL import Image

    data = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read()
    img = Image.open(io.BytesIO(data)).convert("RGB")
    img.thumbnail((1000, 1000))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "JPEG", quality=80, optimize=True)


def keep_missing(rows, old_file):
    """Never let an episode vanish because the feed answered with an old or partial copy: episodes we already had that
    are missing from this fetch are kept (a stale feed once removed episode 448 from the website this way)."""
    if not old_file.exists():
        return rows
    try:
        old = json.loads(old_file.read_text())
    except ValueError:
        return rows
    ident = lambda r: r.get("guid") or r["feed_title"]
    have = {ident(r) for r in rows}
    for r in old:
        if ident(r) in have:
            continue
        r = dict(r)
        r["notes"], tx = local_files(r["type"], r["number"], r["title"], r["feed_title"])
        r["transcript"] = tx[0] if tx else None
        i = next((k for k, x in enumerate(rows) if (x["published"] or "") <= (r["published"] or "")), len(rows))
        rows.insert(i, r)
        print(f"   kept '{r['feed_title']}': the feed didn't list it this time (stale or partial feed?)")
    return rows


def fresh_feed_address(rng=random):
    """A feed address no cache has seen before: the same feed, with random capitals in the id, "podcast" and "rss" and maybe a slash."""
    def mixed(word):
        return "".join(c.upper() if rng.random() < 0.5 else c for c in word)
    return f"https://anchor.fm/s/{mixed(FEED_ID)}/{mixed('podcast')}/{mixed('rss')}" + ("/" if rng.random() < 0.5 else "")


def feed_addresses(fresh=2):
    """Addresses to read the feed from: `fresh` never-used ones, then the plain one (which the host clears on publishing)."""
    return [fresh_feed_address() for _ in range(fresh)] + [FEED]


def fetch_feed(addresses=None):
    """The <channel> element of the freshest copy of the feed (the one that lists the most episodes; see the note at the top)."""
    best, best_n = None, -1
    for url in addresses or feed_addresses():
        try:
            raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Cache-Control": "no-cache"}), timeout=60).read()
            channel = ET.fromstring(raw).find("channel")
            n = len(channel.findall("item"))
        except Exception as e:  # one address being down is fine as long as another works
            print(f"   feed address {url} failed: {e}")
            continue
        if n > best_n:
            best, best_n = channel, n
    if best is None:
        raise RuntimeError("could not read the podcast feed from any address")
    return best


def is_scheduled_for_later(item, now=None):
    """True for a feed item whose publish date is still in the future: a scheduled episode must not reach the website early."""
    pub = item.findtext("pubDate")
    if not pub:
        return False
    when = parsedate_to_datetime(pub)
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return when > (now or datetime.now(timezone.utc)) + timedelta(minutes=1)


def main(fetch_art=False):
    channel = fetch_feed()
    seen, rows = set(), []
    for it in channel.findall("item"):
        if is_scheduled_for_later(it):
            print(f"   not publishing yet: '{(it.findtext('title') or '').strip()}' is scheduled for {it.findtext('pubDate')}")
            continue
        title = html.unescape(it.findtext("title") or "").strip()
        kind, num, name, key = classify(title)
        k, n = key, 2
        while k in seen:  # e.g. two items numbered 001
            k, n = f"{key}-{n}", n + 1
        seen.add(k)
        art = f"assets/episode-art/{k}.jpg"
        image = it.find("i:image", NS)
        if fetch_art and image is not None:
            try:
                ensure_art(REPO / art, image.get("href"))
            except Exception as e:  # a bad image must not stop the update
                print(f"could not fetch art for {title}: {e}")
        enc = it.find("enclosure")
        notes, transcript = local_files(kind, num, name, title)
        published = parsedate_to_datetime(it.findtext("pubDate")).date().isoformat() if it.findtext("pubDate") else None
        rows.append(
            {
                "type": kind,
                "number": num,
                "title": name,
                "feed_title": title,
                "published": published,
                "duration_seconds": duration_seconds(it.findtext("i:duration", namespaces=NS)),
                "description": plain(it.findtext("description")),
                "audio_url": enc.get("url") if enc is not None else None,
                "episode_page": it.findtext("link"),
                "art": art if (REPO / art).exists() else None,
                "notes": notes,
                "transcript": transcript[0] if transcript else None,
                "guid": it.findtext("guid"),
            }
        )

    out = REPO / "data"
    out.mkdir(exist_ok=True)
    rows = keep_missing(rows, out / "episodes.json")

    # Newest first, as in the feed. Keep a stable, readable order for the CSV too.
    (out / "episodes.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")
    cols = ["type", "number", "title", "published", "duration_seconds", "audio_url", "episode_page", "art", "notes", "transcript", "description"]
    with open(out / "episodes.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            r = dict(r)
            r["notes"] = "; ".join(r["notes"])
            r["description"] = r["description"].replace("\n", " ")
            w.writerow({c: r[c] for c in cols})
    kinds = {}
    for r in rows:
        kinds[r["type"]] = kinds.get(r["type"], 0) + 1
    print(f"{len(rows)} items {kinds}; {sum(1 for r in rows if r['notes'])} with notes, "
          f"{sum(1 for r in rows if r['transcript'])} with transcripts, {sum(1 for r in rows if r['art'])} with art")


if __name__ == "__main__":
    import sys

    main(fetch_art="--fetch-art" in sys.argv)
