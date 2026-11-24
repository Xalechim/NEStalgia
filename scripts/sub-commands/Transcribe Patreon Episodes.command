#!/bin/bash
# Makes transcripts for the Patreon-only shows, NEStalgia Bytes and SNEStalgia, from the final mixes in iCloud Mixes.
# Skips any episode that already has one. These are for Patreon members, so they are NOT put in the GitHub repo (or the website):
# they are saved to iCloud, in 10_NEStalgia/Patreon Transcripts/ (Bytes and SNEStalgia folders), ready to attach to the Patreon posts.
# Nothing here is ever uploaded, so it has no publish step. To do just some: python scripts/python/patreon_transcripts.py --bytes 22 40-45
source "$(dirname "$0")/_common.sh"
nes_header "Patreon transcripts (Bytes and SNEStalgia)" "Saved to iCloud 10_NEStalgia/Patreon Transcripts, never to GitHub."
python scripts/python/patreon_transcripts.py
open "$HOME/Library/Mobile Documents/com~apple~CloudDocs/10_NEStalgia/Patreon Transcripts" 2>/dev/null
nes_pause
