#!/usr/bin/env python3
"""Refresh everything that comes from outside the repo: the podcast feed and the spreadsheet.

One pass does, in order: new episodes and cover art (data/episodes.json and .csv, the episode index), click-to-play timing for
a new episode (from the fingerprint of its mix), the Up next box (moves on to the following episode once the feed has
caught up), Wikipedia intros, the spreadsheet's verdicts and genres, box art for generic covers, and the Bytes list.
It is safe to run any time and does nothing when nothing changed. GitHub runs it (see .github/workflows/update-site.yml,
and watch_feed.py for the Friday-morning watch); you can also run it by hand:
  python3 scripts/python/update_from_feed.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import build_episode_data  # noqa: E402
import box_art  # noqa: E402
import bytes_art  # noqa: E402
import bytes_info  # noqa: E402
import build_index  # noqa: E402
import game_info  # noqa: E402
import next_episode  # noqa: E402
import wikipedia_intros  # noqa: E402

REPO = Path(__file__).resolve().parents[2]


def pending_offsets():
    """Published episodes that have a mix fingerprint but no measured click-to-play shift yet (checked without loading numpy)."""
    try:
        fps = {int(p.stem) for p in (REPO / "data/mix-fingerprints").glob("[0-9]*.json")}
        done = {int(k) for k in json.loads((REPO / "data/audio-offsets.json").read_text())}
        out = {r["number"] for r in json.loads((REPO / "data/episodes.json").read_text()) if r["type"] == "episode" and r["number"]}
        return sorted((fps & out) - done)
    except (OSError, ValueError):
        return []


def main():
    build_episode_data.main(fetch_art=True)
    build_index.main()

    try:  # click-to-play timing for an episode that just came out, from the fingerprint saved when its transcript was made
        if pending_offsets():
            import audio_offsets
            got = audio_offsets.measure_from_fingerprints()
            print(f"Measured the click-to-play timing for episode(s) {', '.join(map(str, got))}." if got else "Couldn't measure the click-to-play timing yet.")
    except Exception as e:
        print(f"Couldn't measure the click-to-play timing: {e}")

    try:  # on the Mac: keep a copy of each upcoming episode's iCloud cover in the repo so GitHub can use it (does nothing elsewhere)
        next_episode.stage_upcoming_art()
    except Exception as e:
        print(f"Couldn't save the upcoming covers: {e}")

    try:  # when the feed has caught up to the saved "next" episode, look up the one after it
        next_episode.refresh()
    except Exception as e:  # never let this stop the rest of the update
        print(f"Couldn't update the next-episode box: {e}")

    try:  # new episodes that only have the Patreon boilerplate get the game's Wikipedia intro (no-op when nothing needs it)
        wikipedia_intros.main([])
    except Exception as e:
        print(f"Couldn't add Wikipedia intros: {e}")

    try:  # developer, publisher, genre, release date and verdict for the Episodes page filters
        game_info.refresh()
    except Exception as e:
        print(f"Couldn't update the game info: {e}")

    try:  # a new episode whose cover is the plain NEStalgia logo gets the game's NES box art (does nothing if no cover is generic)
        box_art.main()
    except SystemExit:
        pass
    except Exception as e:
        print(f"Couldn't check for generic covers: {e}")

    try:  # the NEStalgia Bytes list (Patreon-only episodes) from the spreadsheet, and covers for any new ones
        bytes_info.refresh()
        bytes_art.main([])
    except Exception as e:
        print(f"Couldn't update the Bytes episodes: {e}")


if __name__ == "__main__":
    main()
