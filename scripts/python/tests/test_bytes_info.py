#!/usr/bin/env python3
"""Offline checks for bytes_info.py and bytes_art.py. Run: python3 scripts/python/tests/test_bytes_info.py"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bytes_info as B

CSV = '''Season,Episode (Season),Ep #,Episode,Release Date,Developer 1,Developer 2,Publisher,Genre,Espisode Publish Date,Verdict,Comment,Patreon Link
Byte,,1,Nuts and Milk,,,,,,1/22/2022,,,https://www.patreon.com/posts/1
Byte,,2,Devil World,,,,,,,,,
Byte,,,Fire Emblem: Shadow Dragon,,,,,,,,,
Byte,,22,Sweet Home,,,,,,10/30/2023,,,
Byte,,300,Pin*Bot,,,,,,11/24/2023,,,
Byte,,23,Honoo no Toukyuuji: Dodge Danpei,,,,,,,,,
Byte,,56,Future One,,,,,,10/31/2026,,,
7,1,421,Not A Byte,January 1991,Natsume,,FCI,RPG,3/27/2026,Skip it,,
'''
notes = {21: "Glory of Heracles II", 23: "Honoo no Toukyuuji: Dodge Danpei"}
d = B.parse(CSV, notes, today=date(2026, 10, 4))
assert d["1"] == {"title": "Nuts and Milk", "published": "2022-01-22", "patreon_url": "https://www.patreon.com/posts/1"}, d["1"]
assert d["2"]["published"] == ""                                       # no date yet: still listed
assert d["3"]["title"].startswith("Fire Emblem")                       # no number: sits right after the one before it
assert "300" not in d and "56" not in d and "421" not in d             # typo number, future episode, a regular episode: all left out
assert d["21"]["title"] == "Glory of Heracles II"                      # in the notes files but not the sheet: filled in
assert d["23"]["title"] == "Honoo no Toukyuuji: Dodge Danpei"
assert B.cover_name(22, "Sweet Home") == "nb-022-sweet-home"
assert B.cover_name(37, "Summer Carnival '92: RECCA") == "nb-037-summer-carnival-92-recca"
assert len(B.cover_name(18, "Downtown Special: It's Kunio-kun's Period Drama, Gather Everyone!")) <= 70
try:
    import bytes_art as A
except ModuleNotFoundError:  # the cover-art part needs numpy (the project's venv has it)
    A = None
if A:
    idx = A.index(["Nuts _ Milk (Japan).png", "Dig Dug (Japan).png", "Dig Dug (USA).png", "Kid Dracula (World) (Castlevania Anniversary Collection).png",
                   "Downtown Special - Kunio-kun no Jidaigeki Da yo Zenin Shuugou! (Japan).png", "Devil World (Japan) [h].png"])
    assert A.find("Nuts and Milk", idx) == "Nuts _ Milk (Japan).png"      # '&' in file names, 'and' in titles
    assert A.find("Dig Dug", idx) == "Dig Dug (Japan).png"                 # Japan preferred
    assert A.find("Downtown Special: It's Kunio-kun's Period Drama, Gather Everyone!", idx).startswith("Downtown Special -")
    assert A.find("Kid Dracula", idx) is None and A.find("Devil World", idx) is None   # collection scans and hacks are skipped
print("all tests passed")
