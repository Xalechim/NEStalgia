#!/bin/bash
# Double-click this file to make a transcript for one episode.
cd "$HOME/Developer/nestalgia" || exit 1
export PATH="$HOME/.venvs/nestalgia/bin:$HOME/bin:$PATH"
clear
echo "NEStalgia transcript maker"
echo "--------------------------"
python scripts/run_episode.py
echo
read -p "All finished. Press Enter to close this window."
