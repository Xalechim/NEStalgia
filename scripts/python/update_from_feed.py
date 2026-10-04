#!/usr/bin/env python3
"""Refresh everything that comes from the podcast feed.

Downloads cover art for new episodes, rebuilds data/episodes.json and .csv, and
rebuilds the episode index. Run by the GitHub Action after you publish, or by hand:
  python3 scripts/python/update_from_feed.py
"""
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

build_episode_data.main(fetch_art=True)
build_index.main()

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
