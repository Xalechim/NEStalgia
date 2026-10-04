#!/bin/bash
# Double-click this file to remove the speaker names from every existing transcript.
# Works offline. The old versions stay in git history.
cd "$HOME/Developer/nestalgia" || exit 1
export PATH="$HOME/.venvs/nestalgia/bin:$HOME/bin:$PATH"
clear
echo "NEStalgia: remove speaker names from transcripts"
echo "-------------------------------------------------"
echo "Keeps every word and the timestamps. Regroups the text into paragraphs"
echo "at natural thought breaks. Skips transcripts that are already done."
echo
echo "First, a preview (nothing is changed yet):"
echo
python scripts/python/strip_speakers.py --dry-run | tail -n 8
echo
read -p "Convert them now? (y/n): " GO
if [ "$GO" != "y" ] && [ "$GO" != "Y" ]; then
  echo "Okay, nothing was changed."
  read -p "Press Enter to close this window."
  exit 0
fi
python scripts/python/strip_speakers.py | tail -n 5
echo
read -p "Publish the converted transcripts to GitHub now? (needs internet) (y/n): " PUB
if [ "$PUB" = "y" ] || [ "$PUB" = "Y" ]; then
  python scripts/python/build_episode_data.py | tail -n 1
  python scripts/python/build_index.py | tail -n 1
  git add transcripts data episodes && git commit -m "Remove speaker names from transcripts" && git push && echo "Published. The website updates in a few minutes."
else
  echo "Okay, not published. The converted files are saved on your Mac."
fi
echo
read -p "All finished. Press Enter to close this window."
