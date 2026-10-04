# Shared by every command in this folder (not meant to be double-clicked).
# When a main command runs a sub-command it sets NES_LAUNCHER=1: the sub-command then skips clearing the screen,
# the "press Enter" pauses and its own publish step, because the main command publishes everything once at the end.
REPO="$HOME/Developer/nestalgia"
export PATH="$HOME/.venvs/nestalgia/bin:$HOME/bin:$PATH"
cd "$REPO" || exit 1
# What gets published: generated data, cover art, the episode index and transcripts. Nothing else is ever committed.
PUBLISH_PATHS="data assets/episode-art episodes/README.md transcripts"

nes_header() {  # nes_header "Title" "one-line description"
  [ -z "$NES_LAUNCHER" ] && clear
  echo "$1"
  echo "$(echo "$1" | sed 's/./-/g')"
  [ -n "$2" ] && echo "$2" && echo
}
nes_pause() {
  echo
  [ -z "$NES_LAUNCHER" ] && read -p "All finished. Press Enter to close this window."
  return 0
}
nes_publish() {  # nes_publish "Commit message"  (does nothing when a main command is in charge)
  [ -n "$NES_LAUNCHER" ] && return 0
  echo
  python scripts/python/publish.py "$1" $PUBLISH_PATHS
}
