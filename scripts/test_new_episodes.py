#!/usr/bin/env python3
"""Offline tests for new_episodes.py (no network, no git). Run:  python3 scripts/test_new_episodes.py"""
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import new_episodes as N


def item(num, guid=None, kind="episode", name="Game"):
    return {"guid": guid or f"g{num}", "title": f"{num} - {name}", "kind": kind, "number": num, "name": name, "key": f"{num:03d}-game", "published": "2026-10-02", "audio_url": "u"}


def main():
    items = [item(447), item(448), item(449)]
    # nothing new when everything has been seen
    assert N.find_new(items, {"seen": ["g447", "g448", "g449"], "pending": {}}) == []
    # a new feed item is found
    assert [r["number"] for r in N.find_new(items, {"seen": ["g447", "g448"], "pending": {}})] == [449]
    # an episode on the waiting list is retried even though it was seen
    assert [r["number"] for r in N.find_new(items, {"seen": ["g447", "g448", "g449"], "pending": {"448": {"reason": "no mix"}}})] == [448]
    # --episodes forces an older one; it only applies to numbered episodes
    assert [r["number"] for r in N.find_new(items, {"seen": ["g447", "g448", "g449"], "pending": {}}, forced={447})] == [447]
    # first run: old episodes are baseline, a recent one without a transcript is not
    from datetime import date
    old, new_ = item(300), item(448)
    old["published"], new_["published"] = "2025-01-01", "2026-10-02"
    base = N.initial_baseline([old, new_], lambda n: False, today=date(2026, 10, 2))
    assert base == ["g300"], base
    assert N.initial_baseline([old, new_], lambda n: n == 448, today=date(2026, 10, 2)) == ["g300", "g448"]  # already transcribed: baseline
    assert N.initial_baseline([old, new_], lambda n: False, forced={300}, today=date(2026, 10, 2)) == []
    # commit messages
    assert N.commit_message([item(450, name="Foo")]) == "Add episode 450: Foo (transcript, data, cover art)"
    assert N.commit_message([item(450), item(451)]) == "Add episodes 450-451 (transcripts, data, cover art)"
    assert N.commit_message([item(1, kind="special")]) == "Update from the podcast feed"
    assert N.commit_message([], [item(100)]) == "Add data for episode 100 (waiting for the final mix)"
    assert N.parse_numbers(["450-452", "455,457"]) == [450, 451, 452, 455, 457]
    # the schedule file is valid
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "x.plist"
        p.write_text(N.plist_xml("/usr/bin/python3", "/tmp/new_episodes.py"))
        r = subprocess.run(["plutil", "-lint", str(p)], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
    print("all tests passed")


if __name__ == "__main__":
    main()
