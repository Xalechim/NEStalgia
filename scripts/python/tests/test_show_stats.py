#!/usr/bin/env python3
"""Offline checks for show_stats.py and site_extras.py. Run: python3 scripts/python/tests/test_show_stats.py"""
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import show_stats as S
import site_extras as X


def g(verdict, dev=("A",), pub=("P",), genre="Action", year=1990, month="May", season=6, comment=""):
    return {"verdict": verdict, "developers": list(dev), "publishers": list(pub), "genre": genre, "year": year, "month": month, "season": season, "comment": comment, "title": "t"}


assert S.tally(["Essential", "Play it", "Skip it", "Skip it"])["worth"] == 0.5
assert S.tally([])["n"] == 0

votes = S.parse_votes("Mike and Joe voted Essential. Removed in Best of 1989")
assert votes["who"] == ["Mike", "Joe"] and not votes["all"] and votes["removed"] == "Best of 1989"
assert S.parse_votes("ALL voted Essential")["all"]
assert S.parse_votes("Sean voted Essential. Added in Best of 1989")["added"] == "Best of 1989"
assert S.parse_votes("")["who"] == []

info = {str(i): g("Skip it") for i in range(1, 6)}
info.update({"6": g("Essential", comment="All voted Essential"), "7": g("Play it", comment="Joe voted Essential"), "8": g("Skip it"), "9": g("Essential", comment="Mike and Sean voted Essential")})
info["10"] = g("")  # no verdict yet: ignored
st = S.streaks(info)
assert st["skip"] == {"length": 5, "from": 1, "to": 5}, st
assert st["drought"]["episodes"] == 2 and st["drought"]["after"] == 6 and st["drought"]["before"] == 9
hv = S.host_votes(info)
assert hv["unanimous"] == 1 and hv["solo"] == {"Joe": 1} and hv["per_host"]["Joe"] == 1 and hv["split"] == 2, hv

groups = S.group({"1": g("Essential", dev=("X",)), "2": g("Skip it", dev=("X",)), "3": g("Essential", dev=("Y",))}, lambda v: v["developers"])
assert [n for n, _ in S.ranked(groups, min_games=2)] == ["X"]                       # Y has only one game: not ranked

# related episodes: never the game itself, never the same game twice
data = [{"type": "episode", "number": n, "title": f"Game {n}", "key": f"k{n}", "published": "2026-01-01"} for n in range(1, 9)]
inf = {str(n): g("Skip it", dev=("Dev",), genre="Action", year=1990) for n in range(1, 9)}
idx = X.build_related_index(data, inf)
out = X.related_html(data[3], idx, inf, lambda r: f"<c{r['number']}>", html.escape, "")
assert "<c4>" not in out and out.count("<c") == len(set(__import__("re").findall(r"<c\d+>", out))), out
assert out.count("rgroup") >= 1
print("all tests passed")
