#!/bin/bash
# Checks the podcast feed for new episodes and takes care of each one: adds its info and cover art, makes the transcript from
# your final mix, measures the audio shift, and (on its own) uploads to GitHub and updates the website.
# When a main command runs it, it leaves the uploading to that command.
source "$(dirname "$0")/_common.sh"
nes_header "Check for new episodes" "Transcript and audio shift for any new episode (the mix must be in iCloud Mixes)."
if [ -n "$NES_LAUNCHER" ]; then
  python scripts/python/new_episodes.py --no-publish
else
  python scripts/python/new_episodes.py
fi
nes_pause
