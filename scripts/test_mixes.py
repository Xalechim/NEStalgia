#!/usr/bin/env python3
"""Offline checks for mixes.py: odd file names are found by episode number. Run: python3 scripts/test_mixes.py"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import mixes

files = ["NES 401 - WWF WrestleMania Challenge.mp3", "NES 221 POW.mp3", "NES285_PerfectFitmixdown.mp3", "NES 111 AdventureIsland.mp3",
         "NES 341 - Final Fantasy.mp3", "NES 341 - Final Fantasy_mixdownV2.mp3", "NES 341 - Final Fantasy_mixdownV2.wav",
         "NES 262 - Miracle Piano.mp3", "NES 262 - Rescue.mp3", "NES 147 - Paperboy.mp3", "NES 147 - PaperboyV2.mp3",
         "NES 040 - VOLLEYBALL.mp3", "SNES 001 - Super Mario World.mp3", "001 - 10-Yard Fight (Remastered).mp3",
         "NES 4012 - Not This.mp3", "NES 39 - Notes.pkf", ".DS_Store"]
with tempfile.TemporaryDirectory() as d:
    for f in files:
        (Path(d) / f).write_text("x")
    find = lambda n, t=None: (mixes.find_audio(n, t, d) or Path("none")).name
    assert find(401) == "NES 401 - WWF WrestleMania Challenge.mp3"
    assert find(221) == "NES 221 POW.mp3"
    assert find(285) == "NES285_PerfectFitmixdown.mp3"
    assert find(111) == "NES 111 AdventureIsland.mp3"
    assert find(40) == "NES 040 - VOLLEYBALL.mp3"                                  # leading zero in the file, none in the number
    assert find(1) == "001 - 10-Yard Fight (Remastered).mp3"                       # not SNES 001
    assert find(341) == "NES 341 - Final Fantasy_mixdownV2.mp3"                    # mixdown, newest version, mp3 over wav
    assert find(147) == "NES 147 - PaperboyV2.mp3"
    assert find(262, "The Miracle Piano Teaching System") == "NES 262 - Miracle Piano.mp3"   # two games under one number: title decides
    assert find(262, "Rescue: The Embassy Mission") == "NES 262 - Rescue.mp3"
    assert find(4012) == "NES 4012 - Not This.mp3" and find(401) != "NES 4012 - Not This.mp3"
    assert find(39) == "none"                                                      # .pkf is not audio
    assert find(999) == "none"
print("all tests passed")
