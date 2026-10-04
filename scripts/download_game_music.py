#!/usr/bin/env python3
"""Download each upcoming game's theme (the first KHInsider track longer than 30 seconds) into its Audition project folder.

The track list comes from a JSON file of [episode number, album, track number, track name, length, mp3 address] rows, produced
by scripts/khinsider_lookup.js run in the browser pane (KHInsider blocks scripts but works fine in a browser).
Each file is saved as 'NN Track name.mp3' next to the session file, checked to be a real MP3 over 30 seconds, and logged in
data/game-music-sources.json. Existing files are never overwritten.
  python3 scripts/download_game_music.py tracks.json [--dry-run]
"""
import argparse
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ROOT = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/10_NEStalgia/Audition Projects"
LOG = REPO / "data/game-music-sources.json"
UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://downloads.khinsider.com/"}


def duration(path):
    import imageio_ffmpeg
    err = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-i", str(path)], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else 0.0


def file_name(track, url):
    name = urllib.parse.unquote(url.rsplit("/", 1)[-1])
    name = re.sub(r'[/:\\]', "-", name)
    return name if re.match(r"\d", name) else f"{track:02d} {name}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tracks")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    rows = json.loads(Path(a.tracks).read_text())
    log = json.loads(LOG.read_text()) if LOG.exists() else {}
    folders = {int(m.group(1)): p for p in ROOT.iterdir() if p.is_dir() and (m := re.match(r"NES (\d+) - ", p.name))}
    ok = skipped = failed = 0
    for num, album, track, tname, length, url in rows:
        folder = folders.get(num)
        if not folder:
            print(f"{num}: no project folder, skipped")
            failed += 1
            continue
        dest = folder / file_name(track, url)
        if dest.exists():
            print(f"{num}: already has {dest.name}")
            skipped += 1
            continue
        print(f"{num} {folder.name}: {dest.name}  ({length})")
        if a.dry_run:
            continue
        try:
            data = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90).read()
            dest.write_bytes(data)
            secs = duration(dest)
            if secs <= 30:
                dest.unlink()
                raise ValueError(f"only {secs:.0f}s long")
        except Exception as e:
            print(f"   FAILED: {e}")
            failed += 1
            continue
        log[str(num)] = {"album": album, "track": track, "name": tname, "length": length, "file": dest.name}
        ok += 1
        time.sleep(1.0)  # be polite to their file server
    if ok:
        LOG.write_text(json.dumps(dict(sorted(log.items(), key=lambda kv: int(kv[0]))), indent=1, ensure_ascii=False) + "\n")
    print(f"Downloaded {ok}, already there {skipped}, failed {failed}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
