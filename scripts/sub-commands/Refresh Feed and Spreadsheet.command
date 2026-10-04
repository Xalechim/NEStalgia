#!/bin/bash
# Refreshes everything that comes from outside the repo: the podcast feed (new episodes, cover art), your episode spreadsheet
# (verdicts, genres, the "Up next" box), Wikipedia intros and NES box art for any generic cover. Needs internet.
# (The same refresh also runs by itself every 4 hours on GitHub.)
source "$(dirname "$0")/_common.sh"
nes_header "Refresh the feed and spreadsheet" "New episodes and covers, verdicts and genres, the Up next box, Wikipedia intros."
git pull --rebase --autostash -q origin main
python scripts/python/update_from_feed.py 2>&1 | grep -v "^$" | tail -n 12
nes_publish "Manual refresh: feed, spreadsheet and covers"
nes_pause
