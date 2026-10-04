#!/bin/bash
# THE one command to run after anything happens (a new episode, a verdict added in the spreadsheet, a fresh batch of mixes).
# Double-click it. It does, in order:
#   1. Refresh the feed and your spreadsheet   new episodes and covers, verdicts and genres, the Up next box, Wikipedia intros
#   2. Check for new episodes                  transcript + audio shift for anything new (needs the final mix in iCloud Mixes)
#   3. Measure audio offsets                   click-to-play timing for any transcript that still lacks it
#   4. Link finder                             tells you which episodes still need a Links tab (does them if an API key is set up)
#   5. Publish everything once                 shows what changed, asks, uploads to GitHub and waits for the website to rebuild
# Each step is its own command in the sub-commands folder, so any of them can also be run by itself.
DIR="$(cd "$(dirname "$0")" && pwd)/sub-commands"
export NES_LAUNCHER=1
source "$DIR/_common.sh"
clear
echo "NEStalgia: update everything"
echo "============================="
echo

step() {  # step "n" "title" "command file"
  echo
  echo "--- Step $1 of 4: $2 ---"
  bash "$DIR/$3"
  [ $? -ne 0 ] && echo "   (that step reported a problem; carrying on with the rest)"
}

step 1 "Refresh the feed and spreadsheet" "Refresh Feed and Spreadsheet.command"
step 2 "Check for new episodes" "Check for New Episodes.command"
step 3 "Measure audio offsets" "Measure Audio Offsets.command"
step 4 "Link finder" "Make Links.command"

echo
echo "--- Publish ---"
python scripts/python/publish.py "Update everything: feed, spreadsheet, transcripts and offsets" $PUBLISH_PATHS
echo
echo "Still to do on your side (if anything):"
python scripts/python/pipeline_status.py | sed 's/^/   /'
echo
read -p "All finished. Press Enter to close this window."
