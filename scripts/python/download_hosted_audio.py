#!/usr/bin/env python3
"""Download the public (hosted) audio for episodes that have no final mix in Mixes, so they can be transcribed.

The hosted file is what the podcast host serves: it can include pre-roll ads at the start, so a transcript made from it has the ads in it
and its timestamps are already on the host's timeline (no audio-shift correction needed). Saved as 'NES NNN - Title (hosted).mp3'.
Nothing that already has a file in Mixes is touched.
  python3 scripts/python/download_hosted_audio.py --dry-run       list what would be downloaded and the size
  python3 scripts/python/download_hosted_audio.py                 download them
  python3 scripts/python/download_hosted_audio.py 57 58 60-65     only these episodes
"""
import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import run_episode as R  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
UA = {"User-Agent": "Mozilla/5.0"}


def file_name(number, title):
    safe = re.sub(r'[/:\\?*"<>|]', "", title).strip()
    return f"NES {number:03d} - {safe} (hosted).mp3"


def size_of(url):
    req = urllib.request.Request(url, method="HEAD", headers=UA)
    return int(urllib.request.urlopen(req, timeout=30).headers.get("Content-Length") or 0)


def download(url, dest, expected):
    part = dest.with_suffix(".part")
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r, open(part, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
    if expected and part.stat().st_size != expected:
        part.unlink()
        raise IOError(f"incomplete download ({part.stat().st_size if part.exists() else 0} of {expected} bytes)")
    part.rename(dest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("numbers", nargs="*")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    only = set(R.parse_numbers(" ".join(a.numbers)) or []) if a.numbers else None
    eps = [r for r in json.loads((REPO / "data/episodes.json").read_text()) if r["type"] == "episode" and r["number"] and "remaster" not in r["feed_title"].lower()
           and r.get("audio_url")]
    todo = sorted((r for r in eps if not R.find_audio(r["number"]) and (only is None or r["number"] in only)), key=lambda r: r["number"])
    if not todo:
        print("Every episode already has a file in Mixes.")
        return 0
    total, got, failed = 0, 0, []
    for r in todo:
        title = R.feed_title(r["number"]) or r["title"]
        dest = R.MIXES / file_name(r["number"], title)
        try:
            n = size_of(r["audio_url"])
        except Exception as e:
            n = 0
        total += n
        print(f"   {r['number']:03d} {title}  ({n / 1e6:.0f} MB)", flush=True)
        if a.dry_run:
            continue
        try:
            download(r["audio_url"], dest, n)
            got += 1
        except Exception as e:
            print(f"      FAILED: {e}", flush=True)
            failed.append(r["number"])
        time.sleep(0.5)
    print(f"\n{'Would download' if a.dry_run else 'Downloaded'} {len(todo) if a.dry_run else got} file(s), {total / 1e9:.2f} GB" + (f". Failed: {failed}" if failed else "."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
