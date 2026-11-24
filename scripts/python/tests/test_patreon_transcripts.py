#!/usr/bin/env python3
"""Offline checks for patreon_transcripts.py. Run: python3 scripts/python/tests/test_patreon_transcripts.py"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import patreon_transcripts as P

with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    mixes_dir, root, repo = td / "Mixes", td / "out", td / "repo"
    mixes_dir.mkdir()
    for name in ["NB 022 - Sweet Home.mp3", "NB 022 - Sweet Home_FREE.mp3", "NB_053 - Getsu Fuma Den.mp3", "NB 039 - Metal Slader Glory.mp3",
                 "NB 039 - Metal Slader Glory_mixdown.wav", "NB 039 - Metal Slader Glory_mixdown.pkf", "NB_Wagyan Land.mp3",
                 "NB 029_mixdown.mp3", "NBA 100 - Not Ours.mp3", "NES 022 - Not A Byte.mp3",
                 "SNES 001 - Super Mario World.mp3", "SNES 003 - FZero.mp3", "S003_Bestof87v2.mp3"]:
        (mixes_dir / name).write_bytes(b"x")

    b = P.find_mixes("bytes", mixes_dir)
    assert sorted(b) == [22, 29, 39, 53], sorted(b)                      # no 'NBA', no 'NES', no nameless 'NB_Wagyan Land'
    assert b[22].name == "NB 022 - Sweet Home.mp3"                         # the full mix, never the _FREE cut
    assert b[39].suffix == ".mp3"                                          # mp3 beats wav; .pkf is not audio
    s = P.find_mixes("snes", mixes_dir)
    assert sorted(s) == [1, 3] and s[3].name == "SNES 003 - FZero.mp3"
    assert P.file_name_title(b[22], "bytes") == "Sweet Home"
    assert P.file_name_title(b[53], "bytes") == "Getsu Fuma Den"
    assert P.file_name_title(b[29], "bytes") == ""                         # no name in the file: falls back to the list or 'Episode 29'
    assert P.file_name_title(s[3], "snes") == "FZero"

    (repo / "episodes/snes").mkdir(parents=True)
    (repo / "episodes/snes/003-f-zero.md").write_text("# SNES 003 - F-Zero\n\n- hook\n")
    (repo / "data").mkdir()
    (repo / "data/bytes-info.json").write_text(json.dumps({"22": {"title": "Sweet Home"}, "29": {"title": "Fuzzical Fighter"}}))
    assert P.known_titles("snes", repo) == {3: "F-Zero"}
    assert P.known_titles("bytes", repo) == {22: "Sweet Home", 29: "Fuzzical Fighter"}

    todo = P.plan("snes", None, False, mixes_dir, root, repo)
    assert [(t[0], t[2], t[3]) for t in todo] == [(1, "Super Mario World", "snes-001-super-mario-world"), (3, "F-Zero", "snes-003-f-zero")], todo
    (root / "SNEStalgia").mkdir(parents=True)
    (root / "SNEStalgia/snes-003-f-zero.md").write_text("done")
    assert [t[0] for t in P.plan("snes", None, False, mixes_dir, root, repo)] == [1]        # 003 already has one
    assert [t[0] for t in P.plan("snes", {3}, False, mixes_dir, root, repo)] == [3]         # naming it remakes it
    assert [t[0] for t in P.plan("snes", None, True, mixes_dir, root, repo)] == [1, 3]      # --redo remakes everything
    assert [t[3] for t in P.plan("bytes", {29}, False, mixes_dir, root, repo)] == ["nb-029-fuzzical-fighter"]
    assert P.parse_numbers(["3", "40-42"]) == [3, 40, 41, 42]
    assert P.out_stem("bytes", 22, "Sweet Home") == "nb-022-sweet-home"
print("all tests passed")
