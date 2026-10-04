#!/usr/bin/env python3
"""Offline checks for next_episode.py (no network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import next_episode as N

CSV = '''Season,Episode (Season),Ep #,Episode,Release Date,Developer 1,Developer 2,Publisher,Genre,Espisode Publish Date,Verdict
7,27,447,Bill Elliott's NASCAR Challenge,March 1991,Distinctive Software,,Konami,,9/25/2026,Skip it
Byte,,45,Cocona World,,,,,,9/30/2026,
7,28,448,Harlem Globetrotters,March 1991,Softie,,GameTek,,10/2/2026,
7,29,449,Indiana Jones and the Last Crusade,March 1991,Software Creations,,Taito,,10/9/2026,
7,30,450,Metal Mech: Man & Machine,March 1991,Sculptured Software,,Jaleco,,10/16/2026,
'''
rows = N.read_sheet_rows(CSV)
assert [r["number"] for r in rows] == [447, 448, 449, 450], rows          # the Byte row is ignored
assert N.pick_next(rows, 448)["title"] == "Indiana Jones and the Last Crusade"
assert N.pick_next(rows, 449)["number"] == 450                            # feed caught up: move on
assert N.pick_next(rows, 450) is None
assert rows[2]["publish_date"] == "2026-10-09" and rows[2]["publisher"] == "Taito"
print("all tests passed")
