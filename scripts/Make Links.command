#!/bin/bash
# Double-click this file to find the web links for episodes that have transcripts.
cd "$HOME/Developer/nestalgia" || exit 1
export PATH="$HOME/.venvs/nestalgia/bin:$HOME/bin:$PATH"
clear
echo "NEStalgia link finder"
echo "---------------------"
echo "Reads a transcript, finds everything mentioned on the show,"
echo "and looks up a web page for each. Costs a few cents per episode."
echo
read -p "Which episode(s)? (for example 446, or 401-410, or type ALL for every transcript without links): " WHICH
if [ "$(echo "$WHICH" | tr a-z A-Z)" = "ALL" ]; then
  python scripts/make_links.py --all
else
  python scripts/make_links.py $WHICH
fi
echo
read -p "Publish the new links to GitHub now? (y/n): " PUB
if [ "$PUB" = "y" ] || [ "$PUB" = "Y" ]; then
  git add data/links && git commit -m "Add episode links" && git push && echo "Published. The website updates in a few minutes."
fi
echo
read -p "All finished. Press Enter to close this window."
