#!/usr/bin/env python3
"""Offline tests for the pieces of the automatic publishing pipeline that don't need the network (status board, prep queue, offsets
from fingerprints, the Up next art). Run:  python3 scripts/python/tests/test_pipeline.py"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pipeline_status as P


def touch(root, rel, text="x"):
    f = root / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text)


def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        P.REPO = root
        eps = [{"type": "episode", "number": n, "title": f"Game {n}", "published": f"2026-10-{n - 430:02d}"} for n in (450, 451, 452)]
        touch(root, "data/episodes.json", json.dumps(eps))
        touch(root, "data/audio-offsets.json", json.dumps({"451": [[0, 60.2]], "452": [[0, 60.2]]}))
        # 452 is out and complete; 451 is out but has no links; 453 and 454 have transcripts (453 also a fingerprint); 455 only has notes
        for n in (451, 452, 453, 454):
            touch(root, f"transcripts/{n}-game.md")
            touch(root, f"transcripts/{n}-game.vtt")
        for n in (451, 452):
            touch(root, f"reviews/{n}-game.md")
        touch(root, "data/links/452-game.json")
        touch(root, "data/mix-fingerprints/453.json", "{}")
        touch(root, "episodes/455-game.md")

        assert P.published_numbers() == {450, 451, 452}
        r = P.readiness(453)
        assert r["transcript"] and not r["review"] and not r["links"] and r["fingerprint"] and not r["offset"]
        assert P.readiness(452)["offset"] and P.readiness(452)["links"] and P.readiness(452)["review"]
        # the prep queue: published episodes first (newest first), then upcoming ones in the order they come out; none without a transcript
        assert P.prep_queue() == [(451, ["links"]), (453, ["review", "links"]), (454, ["review", "links"])], P.prep_queue()
        board = P.board()
        assert "| 452 | **published** | yes | yes | yes | yes |" in board
        assert "| 453 | not yet | yes | - | - | ready (measured when it comes out) |" in board
        assert "| 455 | not yet | - | - | - | waiting for the transcript |" in board
        # a review or links file for an episode that is not out never makes it "published"
        assert 453 not in P.published_numbers()

    # offsets from fingerprints: tries are counted and capped, a changed shift is flagged for the Mac
    try:
        import audio_offsets as A
    except ImportError:  # numpy isn't installed here (the Mac's venv and GitHub have it)
        print("all tests passed (skipped the offsets part: numpy isn't installed)")
        return
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        A.FP_DIR, A.OUT, A.TODO = root / "fp", root / "offsets.json", root / "todo.json"
        A.TRIED = A.FP_DIR / "_tried.json"
        A.REPO = root
        touch(root, "data/episodes.json", json.dumps([
            {"type": "episode", "number": n, "title": "g", "feed_title": "g", "published": "2026-10-30", "audio_url": f"http://x/{n}.mp3"} for n in (452, 453, 454)]))
        for n in (452, 453, 454, 455):
            touch(root, f"fp/{n:03d}.json", json.dumps({"head": [0.1, 0.2], "tail": [0.3, 0.4], "tail_start": 1.0, "mix_total": 3.0}))
        results = {452: ([[0, 60.2]], False), 453: ([[0, 59.9]], True), 454: (None, False)}
        A.measure_from_fingerprint = lambda n, fp, url, log=print: results[n]
        got = A.measure_from_fingerprints(log=lambda m: None)
        assert got == [452, 453], got                                     # 455 is not published, so it is left alone
        assert json.loads(A.OUT.read_text()) == {"452": [[0, 60.2]], "453": [[0, 59.9]]}
        assert A.load_todo() == {453}                                     # only the start shift is known for 453: the Mac should finish it
        assert json.loads(A.TRIED.read_text()) == {"454": 1}
        for _ in range(8):
            A.measure_from_fingerprints(log=lambda m: None)
        assert json.loads(A.TRIED.read_text()) == {"454": A.MAX_TRIES}, "gives up after MAX_TRIES instead of downloading audio forever"
    print("all tests passed")


if __name__ == "__main__":
    main()
