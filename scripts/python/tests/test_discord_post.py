#!/usr/bin/env python3
"""Offline checks for discord_post.py. Run: python3 scripts/python/tests/test_discord_post.py"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import discord_post as D

BP = "Support NEStalgia directly by becoming a member of our Patreon at https://www.patreon.com/Nestalgia ..."


def ep(n, pub, desc=BP, guid=None, kind="episode", feed=None):
    return {"type": kind, "number": n, "title": f"Game {n}", "feed_title": feed or f"{n} - Game {n}", "published": pub, "description": desc,
            "guid": guid or f"g{n}", "art": f"assets/episode-art/{n:03d}-game.jpg"}


today = date(2026, 10, 9)
eps = [ep(449, "2026-10-09"), ep(448, "2026-10-02"), ep(300, "2025-01-01"), ep(450, "2026-10-09", feed="450 - Game (Remastered)")]
assert [r["number"] for r in D.unposted(eps, set(), today)] == [448, 449]                      # old and remastered ones are ignored
assert [r["number"] for r in D.unposted(eps, {"g448"}, today)] == [449]                          # already announced
assert [r["number"] for r in D.unposted(eps, {"g300"}, today, only=300)] == []                   # asked for one that was posted: needs --force
assert [r["number"] for r in D.unposted(eps, {"g300"}, today, only=300, force=True)] == [300]

p = D.payload(ep(449, "2026-10-09"), {"449": {"text": "A 1991 action video game for the NES."}})
e = p["embeds"][0]
assert e["title"] == "Episode 449: Game 449" and e["description"] == "A 1991 action video game for the NES."
assert e["image"]["url"].endswith("/art/share/449-game.jpg") and e["url"].endswith("/episodes/449-game/")
assert p["allowed_mentions"] == {"parse": []}                                                    # never pings anyone
assert D.payload(ep(1, "2026-10-09", desc="Real text here. More."), {})["embeds"][0]["description"] == "Real text here. More."
assert D.payload(ep(1, "2026-10-09"), {})["embeds"][0]["description"] == ""                      # boilerplate only, no intro: blank, not Patreon text
assert len(D.short("word " * 200)) <= 321 and D.short("Short.") == "Short."
print("all tests passed")
