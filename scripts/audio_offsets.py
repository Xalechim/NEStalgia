#!/usr/bin/env python3
"""Measure how far the podcast host's audio is shifted from the final mix, per episode.

Transcript timestamps are measured on the final mix (the MP3 in your Mixes folder). The audio the website plays is served by the
podcast host, which can insert ads (usually a pre-roll) and so shifts everything later. This finds that shift by lining the two
recordings up (loudness patterns), using only small partial downloads (the first and last few MB of the hosted file).

  python3 scripts/audio_offsets.py 446            one episode
  python3 scripts/audio_offsets.py --all          every transcript that has no measurement yet
  python3 scripts/audio_offsets.py --all --force  measure everything again

Writes data/audio-offsets.json:  {"446": [[0, 60.2]]}  meaning "from mix time 0 s on, hosted audio is 60.2 s later".
Needs internet and the mix MP3 on this Mac. Run it automatically by the transcript tool; safe to rerun any time.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
import wave
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
MIXES = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/10_NEStalgia/Mixes"
OUT = REPO / "data/audio-offsets.json"
UA = {"User-Agent": "Mozilla/5.0 (compatible; NEStalgiaOffsets/1.0)"}
SR, HOP = 8000, 0.05
HEAD_BYTES = 6_000_000
FFMPEG = "ffmpeg"


def decode(src, start=0.0, dur=None):
    """Audio -> mono 8 kHz float array (optionally just a slice)."""
    with tempfile.TemporaryDirectory() as td:
        wav = os.path.join(td, "a.wav")
        cmd = [FFMPEG, "-y", "-loglevel", "error"] + (["-ss", str(start)] if start else []) + ["-i", str(src)] + (["-t", str(dur)] if dur else []) + ["-ac", "1", "-ar", str(SR), wav]
        subprocess.run(cmd, check=True)
        with wave.open(wav) as w:
            return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768


def envelope(x):
    n = int(SR * HOP)
    k = len(x) // n
    return np.sqrt((x[: k * n].reshape(k, n) ** 2).mean(axis=1) + 1e-10)


def zscore(a):
    return (a - a.mean()) / (a.std() + 1e-9)


def best_match(needle, haystack):
    """Position (in envelope frames) in `haystack` where `needle` fits best, with its correlation and the runner-up correlation."""
    w = len(needle)
    if len(haystack) < w:
        return None
    a = zscore(needle)
    # normalized cross-correlation via cumulative sums
    csum = np.concatenate([[0], np.cumsum(haystack)])
    csq = np.concatenate([[0], np.cumsum(haystack ** 2)])
    n = len(haystack) - w + 1
    mean = (csum[w:w + n] - csum[:n]) / w
    var = (csq[w:w + n] - csq[:n]) / w - mean ** 2
    cross = np.correlate(haystack, a, mode="valid")[:n]
    corr = cross / (w * np.sqrt(np.maximum(var, 1e-12)))
    best = int(np.argmax(corr))
    mask = np.ones(n, bool)
    mask[max(0, best - int(2 / HOP)) : best + int(2 / HOP)] = False
    second = float(corr[mask].max()) if mask.any() else 0.0
    return best, float(corr[best]), second


def http(url, headers=None):
    return urllib.request.urlopen(urllib.request.Request(url, headers={**UA, **(headers or {})}), timeout=120)


def total_bytes(url):
    r = urllib.request.urlopen(urllib.request.Request(url, headers=UA, method="HEAD"), timeout=60)
    return int(r.headers["Content-Length"])


def download(url, rng, dest):
    with http(url, {"Range": rng}) as r, open(dest, "wb") as f:
        f.write(r.read())


def bitrate_bps(path):
    out = subprocess.run([FFMPEG, "-i", str(path)], capture_output=True, text=True).stderr
    m = re.search(r"bitrate: (\d+) kb/s", out)
    return int(m.group(1)) * 1000 if m else 128000


def measure(n, mix_path, url, log=print):
    """Returns a list of [mix_time, offset] anchors, or None if no confident answer."""
    out = subprocess.run([FFMPEG, "-i", str(mix_path)], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out).groups()
    mix_total = int(h) * 3600 + int(m) * 60 + float(s)
    size = total_bytes(url)

    with tempfile.TemporaryDirectory() as td:
        head = os.path.join(td, "head.mp3")
        download(url, f"bytes=0-{HEAD_BYTES - 1}", head)
        bps = bitrate_bps(head)
        hosted_est = size * 8 / bps  # CBR estimate of the hosted length
        head_env = envelope(decode(head))
        # start of the mix (first 150 s) against the first minutes of the hosted file
        mix_env = envelope(decode(mix_path, 0, 150))
        r = best_match(mix_env, head_env)
        if not r or r[1] < 0.5 or r[2] > r[1] * 0.85:
            log(f"   episode {n}: no confident match at the start (corr {r[1]:.2f}, runner-up {r[2]:.2f})" if r else f"   episode {n}: no match at the start")
            return None
        off_start = round(r[0] * HOP, 1)

        anchors = [[0, off_start]]
        # does the shift change later (a mid-roll)? Compare with the tail of the file.
        tail = os.path.join(td, "tail.mp3")
        tail_bytes = 4_000_000
        download(url, f"bytes={size - tail_bytes}-{size - 1}", tail)
        tail_start_abs = (size - tail_bytes) * 8 / bps
        tail_env = envelope(decode(tail))
        win_start = max(0.0, mix_total - 150)
        mix_tail = envelope(decode(mix_path, win_start, 90))
        r2 = best_match(mix_tail, tail_env)
        if r2 and r2[1] >= 0.45 and r2[2] <= r2[1] * 0.9:
            off_end = round(tail_start_abs + r2[0] * HOP - win_start, 1)
            if 1.5 < abs(off_end - off_start) <= 150:  # bigger than that can't be an ad insert; the length estimate is off, so ignore it
                log(f"   episode {n}: the shift changes later ({off_start:+.1f}s at the start, {off_end:+.1f}s at the end); aligning the whole file")
                return measure_full(n, mix_path, url, off_start, log)
        log(f"   episode {n}: hosted audio is {off_start:+.1f}s from the mix (match {r[1]:.2f}); hosted length ~{hosted_est:.0f}s vs mix {mix_total:.0f}s")
        return anchors


def measure_full(n, mix_path, url, off_start, log=print):
    """Slow path for episodes whose shift changes mid-episode: download the whole hosted file and align a window every 40 s."""
    out = subprocess.run([FFMPEG, "-i", str(mix_path)], capture_output=True, text=True).stderr
    h, m, s_ = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out).groups()
    mix_total = int(h) * 3600 + int(m) * 60 + float(s_)
    with tempfile.TemporaryDirectory() as td:
        hosted = os.path.join(td, "full.mp3")
        with http(url) as r, open(hosted, "wb") as f:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
        he, me = envelope(decode(hosted)), envelope(decode(mix_path))
    WIN, SEARCH = int(40 / HOP), 130
    found = []  # (mix_time, offset)
    for t in range(0, int(mix_total) - 40, 40):
        needle = me[int(t / HOP) : int(t / HOP) + WIN]
        lo = max(0, int((t + off_start - SEARCH) / HOP))
        hay = he[lo : int((t + off_start + SEARCH) / HOP) + WIN]
        r = best_match(needle, hay)
        if r and r[1] >= 0.5 and r[2] <= r[1] * 0.9:
            found.append((t, round(lo * HOP + r[0] * HOP - t, 1)))
    anchors = []
    for t, off in found:
        if not anchors or abs(off - anchors[-1][1]) > 1.5:
            # require the new offset to hold for the next window too, so one bad window can't create a step
            nxt = [o for tt, o in found if t < tt <= t + 80]
            if anchors and nxt and not any(abs(o - off) <= 1.5 for o in nxt):
                continue
            anchors.append([t if anchors else 0, off])
    log(f"   episode {n}: full alignment found {len(anchors)} step(s): {anchors}")
    return anchors or None


def load():
    return json.loads(OUT.read_text()) if OUT.exists() else {}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("numbers", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    nums = []
    for tok in " ".join(a.numbers).replace(",", " ").split():
        mm = re.fullmatch(r"(\d+)-(\d+)", tok)
        nums += list(range(int(mm.group(1)), int(mm.group(2)) + 1)) if mm else ([int(tok)] if tok.isdigit() else [])
    done = load()
    if a.all:
        nums = [int(Path(p).name[:3]) for p in sorted(glob.glob(str(REPO / "transcripts/[0-9]*.md")))]
    nums = [n for n in dict.fromkeys(nums) if a.force or str(n) not in done]
    if not nums:
        print("Nothing to measure.")
        return 0

    episodes = {r["number"]: r for r in json.loads((REPO / "data/episodes.json").read_text()) if r["type"] == "episode" and r["number"] and "remaster" not in r["feed_title"].lower()}
    ok = 0
    for n in nums:
        mix = sorted(glob.glob(str(MIXES / f"NES {n} - *.mp3")))
        rec = episodes.get(n)
        if not mix or not rec:
            print(f"   episode {n}: skipped (" + ("no MP3 in Mixes" if not mix else "not in the public feed yet") + ")")
            continue
        try:
            anchors = measure(n, mix[0], rec["audio_url"])
        except Exception as e:
            print(f"   episode {n}: failed: {type(e).__name__}: {e}")
            continue
        if anchors:
            done[str(n)] = anchors
            OUT.parent.mkdir(exist_ok=True)
            OUT.write_text(json.dumps(dict(sorted(done.items(), key=lambda kv: int(kv[0]))), indent=1) + "\n")
            ok += 1
    print(f"\nMeasured {ok} of {len(nums)} episodes -> data/audio-offsets.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
