#!/bin/bash
# Double-click this file. Finds episodes whose description is only the Patreon boilerplate, pulls the game's opening
# paragraph from Wikipedia, and shows it above the boilerplate on the website. Needs internet.
cd "$HOME/Developer/nestalgia" || exit 1
export PATH="$HOME/.venvs/nestalgia/bin:$HOME/bin:$PATH"
clear
echo "NEStalgia: add Wikipedia intros to episodes"
echo "--------------------------------------------"
echo "Your podcast feed is not changed. Only the website shows the new text,"
echo "with credit to Wikipedia under each paragraph."
echo
python scripts/wikipedia_intros.py --dry-run
echo
read -p "Look them up now? (y/n): " GO
if [ "$GO" != "y" ] && [ "$GO" != "Y" ]; then
  echo "Okay, nothing was changed."
  read -p "Press Enter to close this window."
  exit 0
fi
python scripts/wikipedia_intros.py
echo
read -p "Publish to the website now? (y/n): " PUB
if [ "$PUB" = "y" ] || [ "$PUB" = "Y" ]; then
  git add data/wikipedia-intros.json && git commit -m "Add Wikipedia intros for episodes with only the Patreon boilerplate" && git pull --rebase -X theirs --autostash && git push && echo "Published. The website updates in a few minutes."
else
  echo "Okay, not published. The results are saved on your Mac."
fi
echo
read -p "All finished. Press Enter to close this window."
