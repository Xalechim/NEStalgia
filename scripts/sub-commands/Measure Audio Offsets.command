#!/bin/bash
# Measures how far the podcast host's audio (which has ads inserted) is shifted from your final mix, for every transcript
# that hasn't been measured yet, so the clickable timestamps on the website start playing in the right place. (An episode that
# isn't out yet gets a fingerprint of its mix instead; GitHub measures it by itself when the episode appears in the feed.)
# Needs internet and the mixes in iCloud Mixes. Safe to run any time; it skips episodes already done.
source "$(dirname "$0")/_common.sh"
nes_header "Measure audio offsets" "Makes click-to-play timestamps land in the right spot."
MISSING=$(python scripts/python/pipeline_status.py --missing-offsets)
if [ -z "$MISSING" ]; then
  echo "Every transcript already has its audio shift measured."
else
  echo "Measuring: $MISSING"
  python scripts/python/audio_offsets.py --all 2>&1 | grep -v "^\[" | grep -E "episode|Measured" | tail -n 25
fi
# Episodes that aren't out yet get a small fingerprint of their mix instead, so GitHub can measure them the moment they come out.
python scripts/python/audio_offsets.py --fingerprint-upcoming 2>&1 | grep -E "episode|Saved"
nes_publish "Audio offsets for newly measured episodes"
nes_pause
