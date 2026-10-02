#!/bin/bash
# Double-click this to check the podcast feed for new episodes and do everything for them:
# add the info and cover art, make the transcript, upload to GitHub, and update the website.
cd "$HOME/Developer/nestalgia" || exit 1
export PATH="$HOME/.venvs/nestalgia/bin:$HOME/bin:$PATH"
clear
echo "NEStalgia: check for new episodes"
echo "----------------------------------"
echo
python scripts/new_episodes.py
echo
read -p "All finished. Press Enter to close this window."
