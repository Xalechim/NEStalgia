#!/usr/bin/env python3
"""Work out which episode comes next and save what the homepage's "Up next" box shows.

The next episode is read from the public episode spreadsheet: the first numbered episode after the newest one in the
podcast feed. Its cover art comes from the episode's folder in iCloud Audition Projects (else Wikipedia); the opening paragraph
comes from Wikipedia (left blank if there is no article).
Saved to data/next-episode.json and data/next-episode.jpg.

Only does anything when it has to: if the saved "next" episode is still ahead of the newest published episode,
nothing is fetched. Once the feed catches up to it (it just came out), the next one is looked up.
  python3 scripts/python/next_episode.py          # update if needed
  python3 scripts/python/next_episode.py --force  # look it up again
"""
import csv
import io
import json
import re
import sys
import urllib.parse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import make_links as W  # noqa: E402  (Wikipedia helpers)

REPO = Path(__file__).resolve().parents[2]
SHEET_ID = "1r5WpTbM0EYLbr1ylXthvf57HWgjo1iScI_c5HKgfSKc"
SHEET_CSV = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
OUT_JSON = REPO / "data/next-episode.json"
OUT_ART = REPO / "data/next-episode.jpg"
# Each episode's working folder in iCloud ("NES 450 - MetalMachine") holds its cover art, under any file name.
AUDITION = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/10_NEStalgia/Audition Projects"


def latest_published():
    rows = json.loads((REPO / "data/episodes.json").read_text())
    return max((r["number"] for r in rows if r["type"] == "episode" and r["number"]), default=0)


def parse_date(s):
    try:
        return datetime.strptime(s.strip(), "%m/%d/%Y").date().isoformat()
    except ValueError:
        return ""


def read_sheet_rows(text):
    """Numbered episodes from the spreadsheet CSV: [{'number','title','publish_date','developer','publisher'}], by number."""
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return []
    head = [h.strip().lower() for h in rows[0]]
    col = {name: head.index(name) for name in ("season", "ep #", "episode", "publisher") if name in head}
    pub_col = next((i for i, h in enumerate(head) if "publish date" in h), None)
    dev_col = head.index("developer 1") if "developer 1" in head else None
    out = []
    for r in rows[1:]:
        try:
            if r[col["season"]].strip().lower() == "byte" or not r[col["ep #"]].strip().isdigit():
                continue
            out.append({
                "number": int(r[col["ep #"]]),
                "title": r[col["episode"]].strip(),
                "publish_date": parse_date(r[pub_col]) if pub_col is not None and pub_col < len(r) else "",
                "developer": r[dev_col].replace("\n", ", ").strip() if dev_col is not None and dev_col < len(r) else "",
                "publisher": r[col["publisher"]].strip() if col["publisher"] < len(r) else "",
            })
        except (KeyError, IndexError):
            continue
    return sorted(out, key=lambda x: x["number"])


def pick_next(rows, latest):
    return next((r for r in rows if r["number"] > latest), None)


def summary(title):
    """Wikipedia summary for an article that is a video game, or None."""
    api = "https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(title.replace(" ", "_"), safe="")
    try:
        d = json.loads(W.http(api).read())
    except Exception:
        return None
    if d.get("type") != "standard" or "game" not in (d.get("description") or "").lower():
        return None
    return d


def find_wikipedia(name):
    """Best article for this game, or None. Careful: a wrong article is worse than a blank one."""
    want = re.sub(r"[^a-z0-9]", "", name.lower())
    # Wikipedia often drops the subtitle: "Metal Mech: Man & Machine" is the article "Metal Mech".
    names = [name] + [p.strip() for p in re.split(r"\s*(?::|\s-\s)\s*", name, maxsplit=1)[:1] if p.strip() and p.strip() != name]
    for n in names:
        for t in (f"{n} (NES video game)", f"{n} (video game)", n):
            d = summary(t)
            if d:
                return d
    q = urllib.parse.urlencode({"action": "query", "list": "search", "srsearch": f"{name} NES video game", "srlimit": 8, "format": "json"})
    try:
        hits = json.loads(W.http("https://en.wikipedia.org/w/api.php?" + q).read())["query"]["search"]
    except Exception:
        return None
    for h in hits:
        got = re.sub(r"[^a-z0-9]", "", re.sub(r"\(.*?\)", "", h["title"]).lower())
        if got.startswith(want):  # "Indiana Jones and the Last Crusade: The Action Game" for "Indiana Jones and the Last Crusade"
            d = summary(h["title"])
            if d:
                return d
    return None


def save_art(url):
    from io import BytesIO

    from PIL import Image
    try:
        raw = W.http(url, timeout=30).read()
        im = Image.open(BytesIO(raw)).convert("RGB")
    except Exception:
        return False
    im.thumbnail((600, 600))
    im.save(OUT_ART, "JPEG", quality=82, optimize=True)
    return True


def local_art(number):
    """Cover art for this episode from its iCloud working folder (the biggest picture in it), or None."""
    try:
        folders = sorted(AUDITION.glob(f"NES {number} - *"))
    except OSError:
        return None
    pics = [f for d in folders if d.is_dir() for f in d.iterdir()
            if f.suffix.lower() in (".jpg", ".jpeg", ".png") and not f.name.startswith(".")]
    return max(pics, key=lambda f: f.stat().st_size, default=None)


def save_local_art(number):
    from PIL import Image
    src = local_art(number)
    if not src:
        return False
    try:
        im = Image.open(src).convert("RGB")
    except Exception:
        return False
    im.thumbnail((600, 600))
    im.save(OUT_ART, "JPEG", quality=82, optimize=True)
    return True


def refresh(force=False, log=print):
    """Update the saved 'next episode' if it is missing or has already been published. Returns True if it changed."""
    latest = latest_published()
    have = json.loads(OUT_JSON.read_text()) if OUT_JSON.exists() else None
    if have and not force and have.get("number", 0) > latest:
        if not have.get("extract"):  # an earlier lookup found no Wikipedia article; try again
            wiki = find_wikipedia(have["title"])
            if wiki:
                have["wikipedia_url"] = (wiki.get("content_urls") or {}).get("desktop", {}).get("page", "")
                have["extract"] = wiki.get("extract", "")
                OUT_JSON.write_text(json.dumps(have, indent=2, ensure_ascii=False) + "\n")
                log(f"Found the Wikipedia intro for the next episode ({have['number']}).")
        if not have.get("has_art") and save_local_art(have["number"]):
            have["has_art"] = True
            OUT_JSON.write_text(json.dumps(have, indent=2, ensure_ascii=False) + "\n")
            log(f"Added cover art for the next episode ({have['number']}) from your iCloud folder.")
            return True
        log(f"Next episode ({have['number']}) is still ahead of the newest published ({latest}); nothing to do.")
        return False
    try:
        rows = read_sheet_rows(W.http(SHEET_CSV, timeout=30).read().decode("utf-8"))
    except Exception as e:
        log(f"Couldn't read the episode spreadsheet ({e}); keeping what's saved.")
        return False
    nxt = pick_next(rows, latest)
    if not nxt:
        log("The spreadsheet has no episode after the newest published one.")
        return False
    wiki = find_wikipedia(nxt["title"])
    info = dict(nxt)
    info["wikipedia_url"] = ((wiki or {}).get("content_urls") or {}).get("desktop", {}).get("page", "")
    info["extract"] = (wiki or {}).get("extract", "")
    img = ((wiki or {}).get("originalimage") or (wiki or {}).get("thumbnail") or {}).get("source", "")
    info["has_art"] = save_local_art(nxt["number"]) or bool(img and save_art(img))
    if not info["has_art"] and OUT_ART.exists():
        OUT_ART.unlink()  # don't leave the previous game's cover behind
    OUT_JSON.write_text(json.dumps(info, indent=2, ensure_ascii=False) + "\n")
    log(f"Next episode: {nxt['number']} {nxt['title']}" + ("" if wiki else " (no Wikipedia article found)"))
    return True


if __name__ == "__main__":
    refresh(force="--force" in sys.argv)
