#!/usr/bin/env python3
"""Announce new episodes in Discord.

Run by the "Announce new episode" GitHub Action after the website has been rebuilt. It posts one message per episode
that has not been announced yet (a card with the cover art, title, a short description and listen links), then records
it in data/discord-posted.json so nothing is ever posted twice.

Needs a Discord webhook address in the DISCORD_WEBHOOK_URL secret (or in ~/.config/nestalgia/discord_webhook when run by hand).
  python3 scripts/python/discord_post.py --dry-run          show what would be posted
  python3 scripts/python/discord_post.py --seed             mark every current episode as already announced (first-time setup)
  python3 scripts/python/discord_post.py --only 448 --force  post (or re-post) one episode, e.g. as a test
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from wikipedia_intros import boilerplate_only, real_paragraphs  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
STATE = REPO / "data/discord-posted.json"
SITE = "https://nestalgiacast.com"
UA = "NEStalgia-site (https://nestalgiacast.com)"
RECENT_DAYS = 14  # never announce something older than this, even if it was somehow missed
LISTEN = [("Apple Podcasts", "https://itunes.apple.com/us/podcast/nestalgia/id1342922798"),
          ("Spotify", "https://open.spotify.com/show/1SoG0RFa4nPk0YqaXW6vRi")]


def slug_key(r):
    """The page address key: the cover art's file name (set by build_episode_data.py)."""
    return Path(r["art"]).stem if r.get("art") else None


def short(text, limit=320):
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    return (cut[: end + 1] if end > limit * 0.5 else cut.rsplit(" ", 1)[0] + "…").strip()


def describe(r, intros):
    """A short blurb: the Wikipedia intro if the feed text is only the Patreon boilerplate, else the feed's first paragraph."""
    if boilerplate_only(r["description"]):
        intro = (intros.get(str(r["number"])) or {}).get("text", "")
        return short(intro) if intro else ""
    return short(real_paragraphs(r["description"])[0])


def payload(r, intros):
    key = slug_key(r)
    page = f"{SITE}/episodes/{key}/" if key else SITE
    n = r.get("number")
    title = f"Episode {n}: {r['title']}" if r["type"] == "episode" and n else r["title"]
    embed = {
        "title": title[:250], "url": page, "color": 0xD62D20,
        "description": describe(r, intros),
        "fields": [{"name": "Listen", "value": " · ".join(f"[{name}]({url})" for name, url in LISTEN) + f" · [Read on the site]({page})"}],
        "footer": {"text": "NEStalgia: A chronological exploration of every NES game."},
    }
    if key:
        embed["image"] = {"url": f"{SITE}/art/share/{key}.jpg"}
    if r.get("published"):
        embed["timestamp"] = f"{r['published']}T12:00:00.000Z"
    return {"username": "NEStalgia", "content": "🎮 **A new NEStalgia episode is out!**", "embeds": [embed], "allowed_mentions": {"parse": []}}


def unposted(episodes, posted, today=None, only=None, force=False):
    """Episodes still to announce, oldest first. Only recent ones, unless one is asked for by number."""
    today = today or date.today()
    out = []
    for r in episodes:
        if r["type"] not in ("episode", "special") or not r.get("art") or not r.get("published"):
            continue
        if "remaster" in r["feed_title"].lower():
            continue
        if only is not None:
            if r["number"] == only and (force or r["guid"] not in posted):
                out.append(r)
            continue
        if r["guid"] in posted:
            continue
        if date.fromisoformat(r["published"]) < today - timedelta(days=RECENT_DAYS):
            continue
        out.append(r)
    return sorted(out, key=lambda r: (r["published"], r["number"] or 0))


def page_is_live(url, tries=8, wait=20):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        if i < tries - 1:
            time.sleep(wait)
    return False


def post(webhook, body):
    req = urllib.request.Request(webhook, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status


def load_state():
    return json.loads(STATE.read_text()) if STATE.exists() else []


def save_state(guids):
    STATE.write_text(json.dumps(sorted(set(guids)), indent=1) + "\n")


def webhook_url():
    url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    f = Path.home() / ".config/nestalgia/discord_webhook"
    return url or (f.read_text().strip() if f.exists() else "")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--seed", action="store_true")
    ap.add_argument("--only", type=int)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    episodes = json.loads((REPO / "data/episodes.json").read_text())
    intros = json.loads((REPO / "data/wikipedia-intros.json").read_text()) if (REPO / "data/wikipedia-intros.json").exists() else {}
    posted = load_state()

    if a.seed:
        save_state(posted + [r["guid"] for r in episodes if r.get("guid")])
        print(f"Marked {len(episodes)} existing episodes as already announced.")
        return 0

    todo = unposted(episodes, set(posted), only=a.only, force=a.force)
    if not todo:
        print("No new episodes to announce.")
        return 0
    hook = webhook_url()
    if not hook and not a.dry_run:
        print("No Discord webhook set (DISCORD_WEBHOOK_URL), so nothing was posted.")
        return 0
    for r in todo:
        body = payload(r, intros)
        if a.dry_run:
            print(json.dumps(body, indent=1, ensure_ascii=False))
            continue
        url = body["embeds"][0]["url"]
        if not page_is_live(url):
            print(f"{r['feed_title']}: its page isn't live yet ({url}); will try again on the next run.")
            continue
        post(hook, body)
        if a.only is None or r["guid"] not in posted:
            posted.append(r["guid"])
            save_state(posted)
        print(f"Announced: {r['feed_title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
