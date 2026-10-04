#!/usr/bin/env python3
"""What still needs doing for episodes that have a transcript: web links (Links tab) and click-to-play audio offsets.

  python3 scripts/python/pipeline_status.py                 a short summary
  python3 scripts/python/pipeline_status.py --missing-links    episode numbers with a transcript but no Links tab
  python3 scripts/python/pipeline_status.py --links-ranges     the same, as ranges like 2-56, 94-167
  python3 scripts/python/pipeline_status.py --missing-offsets  episode numbers with a transcript but no measured audio shift
  python3 scripts/python/pipeline_status.py --has-key          exit code 0 if an Anthropic key is set up (needed to find links without Claude Code)
"""
import glob
import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def transcript_numbers():
    nums = set()
    for p in glob.glob(str(REPO / "transcripts/[0-9]*.md")):
        m = re.match(r"(\d+)-", os.path.basename(p))
        if m:
            nums.add(int(m.group(1)))
    return sorted(nums)


def missing_links():
    have = {int(m.group(1)) for p in glob.glob(str(REPO / "data/links/*.json")) if (m := re.match(r"(\d+)-", os.path.basename(p)))}
    return [n for n in transcript_numbers() if n not in have]


def missing_offsets():
    f = REPO / "data/audio-offsets.json"
    have = set(json.loads(f.read_text())) if f.exists() else set()
    return [n for n in transcript_numbers() if str(n) not in have]


def has_key():
    return bool(os.environ.get("ANTHROPIC_API_KEY") or (Path.home() / ".config/nestalgia/anthropic_key").exists())


def ranges(nums):
    """[1,2,3,7] -> '1-3, 7'"""
    out, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        out.append(str(nums[i]) if i == j else f"{nums[i]}-{nums[j]}")
        i = j + 1
    return ", ".join(out)


def main(argv):
    if "--missing-links" in argv:
        print(" ".join(map(str, missing_links())))
    elif "--links-ranges" in argv:
        print(ranges(missing_links()))
    elif "--missing-offsets" in argv:
        print(" ".join(map(str, missing_offsets())))
    elif "--has-key" in argv:
        return 0 if has_key() else 1
    else:
        t, ml, mo = transcript_numbers(), missing_links(), missing_offsets()
        print(f"{len(t)} episodes have transcripts.")
        print(f"   {len(ml)} are missing a Links tab" + (f": {ranges(ml)}" if ml else "") + ".")
        print(f"   {len(mo)} are missing a measured audio shift (click-to-play)" + (f": {ranges(mo)}" if mo else "") + ".")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
