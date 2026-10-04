#!/usr/bin/env python3
"""Offline checks for wikipedia_intros.py. Run: python3 scripts/python/tests/test_wikipedia_intros.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import wikipedia_intros as W

BP = "Support NEStalgia directly by becoming a member of our Patreon at https://www.patreon.com/Nestalgia \xa0Members at the $5 and above level..."
assert W.boilerplate_only(BP)
assert W.boilerplate_only("")
assert not W.boilerplate_only("Willow is an action RPG.\n\n" + BP)               # real text above it: leave alone
assert not W.boilerplate_only(BP + "\n\nSHOW NOTES\n\nLongplay")                  # real links below it: leave alone

def ep(n, desc, feed="x", t="episode"):
    return {"type": t, "number": n, "title": f"Game {n}", "feed_title": feed, "description": desc}

eps = [ep(1, BP), ep(2, "Real text"), ep(3, BP), ep(4, BP, feed="004 - Game (Remastered)"), ep(5, BP, t="special"), ep(6, BP)]
store = {"3": {"text": "Already found"}, "6": {"text": ""}}
assert [r["number"] for r in W.pick(eps, store)] == [1]                           # 3 done, 6 checked before, 2 has text
assert [r["number"] for r in W.pick(eps, store, retry=True)] == [1, 6]            # --retry revisits the blanks
assert [r["number"] for r in W.pick(eps, store, force=True)] == [1, 3, 6]
assert [r["number"] for r in W.pick(eps, store, only={6})] == []
assert W.lookup("Super Spike V'Ball / Nintendo World Cup") is None                # two games in one title: skipped
print("all tests passed")
