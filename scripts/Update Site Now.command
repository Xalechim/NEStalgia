#!/bin/bash
# Double-click this to refresh EVERYTHING that comes from outside the repo, right now, and publish it:
#   the podcast feed (new episodes, cover art), your episode spreadsheet (verdicts, genres, the "Up next" box),
#   Wikipedia intros, and NES box art for any generic cover. Needs internet.
# (The same refresh also runs by itself every 4 hours on GitHub.)
cd "$HOME/Developer/nestalgia" || exit 1
export PATH="$HOME/.venvs/nestalgia/bin:$HOME/bin:$PATH"
clear
echo "NEStalgia: update the site now"
echo "-------------------------------"
echo
git pull --rebase --autostash -q origin main
python scripts/update_from_feed.py 2>&1 | grep -v "^$" | tail -n 12
echo
PATHS="data/episodes.json data/episodes.csv data/game-info.json data/next-episode.json data/next-episode.jpg data/wikipedia-intros.json data/box-art-sources.json assets/episode-art episodes/README.md"
if [ -z "$(git status --porcelain -- $PATHS)" ]; then
  echo "Everything was already up to date. Nothing to publish."
  read -p "Press Enter to close this window."
  exit 0
fi
echo "What changed:"
git status --short -- $PATHS
echo
read -p "Publish these changes to the website now? (y/n): " GO
if [ "$GO" = "y" ] || [ "$GO" = "Y" ]; then
  git add -- $PATHS
  git commit -q -m "Manual update: feed, spreadsheet and covers

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
  git pull --rebase --autostash -q origin main
  git push -q origin main && echo "Published. The website rebuilds in about 2 minutes."
else
  echo "Okay, nothing was published. The changes are saved on your Mac."
fi
echo
read -p "All finished. Press Enter to close this window."
