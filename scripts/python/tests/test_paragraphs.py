#!/usr/bin/env python3
"""Offline tests for paragraphs.py and strip_speakers.py. Run:  python3 scripts/python/tests/test_paragraphs.py"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paragraphs as P
import strip_speakers as S


def cue(start, text, dur=2.0):
    return {"start": start, "end": start + dur, "text": text}


def main():
    # a long pause is a hard break; no pause -> one paragraph
    cues = [cue(0, "One."), cue(2.1, "Two."), cue(10, "Three after a pause.")]
    cues[0]["text"] = cues[1]["text"] = "A sentence long enough to count on its own as part of a paragraph " * 3
    cues[2]["text"] = cues[2]["text"] + " " + "padding " * 30
    ps = P.group(cues)
    assert len(ps) == 2 and ps[1]["start"] == 10, ps
    # words are never lost or reordered, however it splits
    many = [cue(i * 3.0, f"Sentence number {i} talks about thing {i % 7} and then some more words here.") for i in range(60)]
    out = P.group(many)
    assert " ".join(p["text"] for p in out) == " ".join(c["text"] for c in many)
    assert all(len(p["text"]) <= P.MAX_CHARS * 1.4 for p in out), [len(p["text"]) for p in out]
    # file formats round trip
    md = P.to_markdown("446 - T", [{"start": 22.4, "end": 30, "text": "Hello there."}, {"start": 3725, "end": 3800, "text": "Later."}])
    assert "[00:22] Hello there." in md and "[1:02:05] Later." in md and "**" not in md
    vtt = P.to_vtt([cue(1.5, "Hi.")])
    assert "00:00:01.500 --> 00:00:03.500" in vtt
    assert P.read_vtt("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n<v Mike>Hello</v>\n")[0]["text"] == "Hello"

    # converting an old speaker transcript: with a .vtt, without one, twice
    old = "# 400 - Test\n\n_old note_\n\n**Mike** [00:00]: Hello there. How are you?\n\n**Sean** [00:05]: Fine thanks. And you?\n"
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "400-test.md").write_text(old)
        (d / "400-test.vtt").write_text("WEBVTT\n\n00:00:00.000 --> 00:00:02.000\n<v Mike>Hello there. How are you?\n\n00:00:05.000 --> 00:00:07.000\n<v Sean>Fine thanks. And you?\n")
        status, _ = S.convert(d / "400-test.md", dry_run=True)
        assert status == "converted" and "**" in (d / "400-test.md").read_text(), "dry run must not write"
        status, _ = S.convert(d / "400-test.md", dry_run=False)
        new = (d / "400-test.md").read_text()
        assert status == "converted" and "**" not in new and "Hello there." in new and "Fine thanks." in new and "[00:00]" in new, new
        assert "<v " not in (d / "400-test.vtt").read_text()
        assert S.convert(d / "400-test.md", dry_run=False)[0] == "skipped"  # idempotent
        # no .vtt: timing is estimated from the turns
        (d / "401-x.md").write_text(old.replace("400", "401"))
        status, detail = S.convert(d / "401-x.md", dry_run=False)
        assert status == "converted" and "estimated" in detail and "**" not in (d / "401-x.md").read_text()
    print("all tests passed")


if __name__ == "__main__":
    main()
