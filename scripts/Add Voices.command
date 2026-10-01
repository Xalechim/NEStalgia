#!/bin/bash
# Double-click this file to teach the voice matcher with more episodes.
cd "$HOME/Developer/nestalgia" || exit 1
export PATH="$HOME/.venvs/nestalgia/bin:$HOME/bin:$PATH"
clear
echo "NEStalgia voice trainer"
echo "-----------------------"
echo "Pick episodes where each host has their own mic recording"
echo "(recent ones like 440, 441, 447, 448, 449, 451, 452, 453, 454)."
echo
python scripts/add_voices.py
echo
read -p "All finished. Press Enter to close this window."
