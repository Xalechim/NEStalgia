#!/bin/bash
# Finds the web links for the Links tab of episodes that have transcripts.
# On its own: asks which episodes and uses the Anthropic API (a few cents per episode; needs a key set up).
# When the Update Everything command runs it: tells you which episodes still have no Links tab, and finds them only if a key is set up.
source "$(dirname "$0")/_common.sh"
nes_header "Link finder" "Reads a transcript, finds everything mentioned on the show, and looks up a web page for each."
if [ -n "$NES_LAUNCHER" ]; then
  MISSING=$(python scripts/python/pipeline_status.py --missing-links)
  COUNT=$(echo $MISSING | wc -w | tr -d ' ')
  if [ "$COUNT" = "0" ]; then
    echo "Every episode with a transcript already has its Links tab."
  elif python scripts/python/pipeline_status.py --has-key; then
    echo "$COUNT episode(s) have a transcript but no Links tab."
    read -p "Find their links now with the Anthropic API? It costs a few cents per episode. (y/n): " GO
    if [ "$GO" = "y" ] || [ "$GO" = "Y" ]; then python scripts/python/make_links.py --all; else echo "Skipped."; fi
  else
    echo "$COUNT episode(s) have a transcript but no Links tab:"
    echo "   Episodes: $(python scripts/python/pipeline_status.py --links-ranges)"
    echo
    echo "You don't have an Anthropic key set up, so ask Claude Code to make them instead,"
    echo "for example:  /make-links 449   (or a few at a time, like /make-links 449 450 451)."
  fi
  nes_pause
  exit 0
fi
read -p "Which episode(s)? (for example 446, or 401-410, or type ALL for every transcript without links): " WHICH
if [ "$(echo "$WHICH" | tr a-z A-Z)" = "ALL" ]; then
  python scripts/python/make_links.py --all
else
  python scripts/python/make_links.py $WHICH
fi
nes_publish "Add episode links"
nes_pause
