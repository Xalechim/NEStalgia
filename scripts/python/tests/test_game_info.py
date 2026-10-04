#!/usr/bin/env python3
"""Offline checks for game_info.py. Run: python3 scripts/python/tests/test_game_info.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import game_info as G

CSV = '''Season,Episode (Season),Ep #,Episode,Release Date,Developer 1,Developer 2,Publisher,Genre,Espisode Publish Date,Verdict
7,1,421,Heroes of the Lance,January 1991,Natsume,"FCINA
Pony CanyonJP","FCINA
Pony CanyonJP",RPG,3/27/2026,Skip it
7,27,447,Bill Elliott's NASCAR Challenge,March 1991,Distinctive Software,Konami,Konami,,9/25/2026,Skip it
6,5,400,Werewolf,"November 1990","Data East, Sakata SAS",,Data East,Action,10/24/2025,Play it
1,1,1,10-Yard Fight,"October 18, 1985",Irem,,NintendoNA/JP,Sports,2/9/2018,Essential
Byte,,45,Cocona World,,,,,,9/30/2025,
S,,1,Best of 1985,,,,,,5/18/2018,
SNEStalgia,,1,Super Mario World,,,,,,12/31/2025,
7,28,448,Harlem Globetrotters,March 1991,Softie,GameTek,GameTek,,10/2/2026,
'''
d = G.parse(CSV)
assert sorted(d, key=int) == ["1", "400", "421", "447", "448"], sorted(d)          # Byte, special and SNES rows ignored
assert d["421"]["publishers"] == ["FCI", "Pony Canyon"] and d["421"]["developers"] == ["Natsume"]   # region tags removed
assert d["447"]["developers"] == ["Distinctive Software"]                           # 'Developer 2' repeating the publisher is not a developer
assert d["400"]["developers"] == ["Data East", "Sakata SAS"]                        # several developers in one cell
assert d["1"]["publishers"] == ["Nintendo"] and d["1"]["year"] == 1985 and d["1"]["month"] == "October" and d["1"]["verdict"] == "Essential"
assert d["421"]["genre"] == "RPG" and d["421"]["season"] == 7 and d["447"]["genre"] == "" and d["448"]["verdict"] == ""
print("all tests passed")
