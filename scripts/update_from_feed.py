#!/usr/bin/env python3
"""Refresh everything that comes from the podcast feed.

Downloads cover art for new episodes, rebuilds data/episodes.json and .csv, and
rebuilds the episode index. Run by the GitHub Action after you publish, or by hand:
  python3 scripts/update_from_feed.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import build_episode_data  # noqa: E402
import build_index  # noqa: E402

build_episode_data.main(fetch_art=True)
build_index.main()
