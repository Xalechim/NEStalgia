#!/usr/bin/env python3
"""Measure how far the podcast host's audio is shifted from the final mix, per episode.

Transcript timestamps are measured on the final mix (the MP3 in your Mixes folder). The audio the website plays is served by the
podcast host, which can insert ads (usually a pre-roll) and so shifts everything later. This finds that shift by lining the two
recordings up (loudness patterns), using only small partial downloads (the first and last few MB of the hosted file).

  python3 scripts/python/audio_offsets.py 446            one episode
  python3 scripts/python/audio_offsets.py --all          every transcript that has no measurement yet
  python3 scripts/python/audio_offsets.py --all --force  measure everything again

Writes data/audio-offsets.json:  {"446": [[0, 60.2]]}  meaning "from mix time 0 s on, hosted audio is 60.2 s later".
Needs internet and the mix MP3 on this Mac. Run it automatically by the transcript tool; safe to rerun any time.

Measuring does not need the mix once an episode has a "fingerprint": the mix's loudness pattern for its first 150 s and a 90 s
stretch near its end, saved in data/mix-fingerprints/NNN.json (a few KB). The transcript tool saves one when it makes the
transcript, so the website's update on GitHub can measure the shift itself the moment the episode appears in the feed:

  python3 scripts/python/audio_offsets.py --fingerprint 453 454     save fingerprints from the mixes on this Mac
  python3 scripts/python/audio_offsets.py --fingerprint-upcoming    ... for every transcript of an episode that is not published yet and has no fingerprint
  python3 scripts/python/audio_offsets.py --from-fingerprints       measure published episodes from their fingerprints (what GitHub runs)

A fingerprint can only give the shift at the start, so if the shift changes mid-episode (an ad inserted in the middle) the start
shift is saved for now and the episode is listed in data/audio-offsets-todo.json for a full alignment on this Mac.
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

sys.path.insert(0, str(Path(__file__).parent))
import mixes  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
MIXES = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/10_NEStalgia/Mixes"
OUT = REPO / "data/audio-offsets.json"
FP_DIR = REPO / "data/mix-fingerprints"
TRIED = FP_DIR / "_tried.json"  # how many times GitHub tried (and failed) to measure an episode from its fingerprint
MAX_TRIES = 6  # then it waits for the Mac, instead of downloading the hosted audio again on every update
TODO = REPO / "data/audio-offsets-todo.json"  # episodes measured from a fingerprint that still need a full alignment on the Mac
HEAD_SECONDS, TAIL_SECONDS, TAIL_BACK = 150, 90, 150  # the stretch at the start, and the stretch starting TAIL_BACK s before the end
UA = {"User-Agent": "Mozilla/5.0 (compatible; NEStalgiaOffsets/1.0)"}
SR, HOP = 8000, 0.05
HEAD_BYTES = 6_000_000


def find_ffmpeg():
    """ffmpeg on the PATH, else the copy bundled with the imageio-ffmpeg package (which is how GitHub gets one)."""
    import shutil
    found = os.environ.get("FFMPEG") or shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


FFMPEG = find_ffmpeg()


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


def mix_length(mix_path):
    out = subprocess.run([FFMPEG, "-i", str(mix_path)], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def mix_pieces(mix_path):
    """What measuring needs from the mix: (envelope of its start, envelope of a stretch near its end, where that stretch starts, length)."""
    mix_total = mix_length(mix_path)
    win_start = max(0.0, mix_total - TAIL_BACK)
    return (envelope(decode(mix_path, 0, HEAD_SECONDS)), envelope(decode(mix_path, win_start, TAIL_SECONDS)), win_start, mix_total)


def make_fingerprint(n, mix_path):
    head, tail, win_start, mix_total = mix_pieces(mix_path)
    return {"number": n, "mix_total": round(mix_total, 2), "hop": HOP, "tail_start": round(win_start, 2),
            "head": [round(float(x), 5) for x in head], "tail": [round(float(x), 5) for x in tail]}


def save_fingerprint(n, mix_path):
    fp = make_fingerprint(n, mix_path)
    FP_DIR.mkdir(parents=True, exist_ok=True)
    (FP_DIR / f"{n:03d}.json").write_text(json.dumps(fp, separators=(",", ":")) + "\n")
    return fp


def load_fingerprint(n):
    f = FP_DIR / f"{n:03d}.json"
    return json.loads(f.read_text()) if f.exists() else None


def measure_core(n, mix_head, mix_tail, win_start, mix_total, url, log, when_shift_changes):
    """Returns a list of [mix_time, offset] anchors, or None if no confident answer.
    when_shift_changes(off_start) decides what to do when the shift is not the same all the way through (or the file's end can't be sampled)."""
    size = total_bytes(url)
    with tempfile.TemporaryDirectory() as td:
        head = os.path.join(td, "head.mp3")
        download(url, f"bytes=0-{HEAD_BYTES - 1}", head)
        bps = bitrate_bps(head)
        hosted_est = size * 8 / bps  # CBR estimate of the hosted length
        head_env = envelope(decode(head))
        # start of the mix (first 150 s) against the first minutes of the hosted file
        r = best_match(mix_head, head_env)
        if not r or r[1] < 0.5 or r[2] > r[1] * 0.85:
            log(f"   episode {n}: no confident match at the start (corr {r[1]:.2f}, runner-up {r[2]:.2f})" if r else f"   episode {n}: no match at the start")
            return None
        off_start = round(r[0] * HOP, 1)

        anchors = [[0, off_start]]
        # does the shift change later (a mid-roll)? Compare with the tail of the file.
        tail = os.path.join(td, "tail.mp3")
        tail_bytes = 4_000_000
        try:
            download(url, f"bytes={size - tail_bytes}-{size - 1}", tail)
            tail_start_abs = (size - tail_bytes) * 8 / bps
            tail_env = envelope(decode(tail))
        except subprocess.CalledProcessError:
            # the host sent an end-of-file slice that can't be decoded (seen on a few episodes): use the slow whole-file method instead
            log(f"   episode {n}: the end of the hosted file couldn't be sampled; aligning the whole file instead")
            return when_shift_changes(off_start)
        r2 = best_match(mix_tail, tail_env)
        if r2 and r2[1] >= 0.45 and r2[2] <= r2[1] * 0.9:
            off_end = round(tail_start_abs + r2[0] * HOP - win_start, 1)
            if 1.5 < abs(off_end - off_start) <= 150:  # bigger than that can't be an ad insert; the length estimate is off, so ignore it
                log(f"   episode {n}: the shift changes later ({off_start:+.1f}s at the start, {off_end:+.1f}s at the end); aligning the whole file")
                return when_shift_changes(off_start)
        log(f"   episode {n}: hosted audio is {off_start:+.1f}s from the mix (match {r[1]:.2f}); hosted length ~{hosted_est:.0f}s vs mix {mix_total:.0f}s")
        return anchors


def measure(n, mix_path, url, log=print):
    """Measure from the mix MP3 itself (on this Mac). Falls back to a whole-file alignment if the shift changes mid-episode."""
    head, tail, win_start, mix_total = mix_pieces(mix_path)
    return measure_core(n, head, tail, win_start, mix_total, url, log, lambda off: measure_full(n, mix_path, url, off, log))


def measure_from_fingerprint(n, fp, url, log=print):
    """Measure from a saved fingerprint (no mix needed). Returns (anchors, partial): partial means the shift changes mid-episode,
    so only the start shift is known and a full alignment on the Mac is still wanted."""
    partial = []

    def start_only(off):
        partial.append(True)
        return [[0, off]]

    anchors = measure_core(n, np.array(fp["head"]), np.array(fp["tail"]), fp["tail_start"], fp["mix_total"], url, log, start_only)
    return anchors, bool(partial)


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


def save(done):
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(dict(sorted(done.items(), key=lambda kv: int(kv[0]))), indent=1) + "\n")


def load_todo():
    return {int(x) for x in json.loads(TODO.read_text())} if TODO.exists() else set()


def save_todo(todo):
    if todo:
        TODO.write_text(json.dumps(sorted(todo)) + "\n")
    elif TODO.exists():
        TODO.unlink()


def published_episodes():
    return {r["number"]: r for r in json.loads((REPO / "data/episodes.json").read_text())
            if r["type"] == "episode" and r["number"] and "remaster" not in r["feed_title"].lower()}


def measure_from_fingerprints(log=print):
    """Published episodes that have a fingerprint but no measured shift: measure them now. No mix needed, so GitHub can do this
    the moment an episode appears in the feed. Gives up on an episode after MAX_TRIES failed attempts (the Mac can still do it).
    Returns the episode numbers measured."""
    done, todo, eps, got = load(), load_todo(), published_episodes(), []
    tried = json.loads(TRIED.read_text()) if TRIED.exists() else {}
    for f in sorted(FP_DIR.glob("[0-9]*.json")) if FP_DIR.exists() else []:
        n = int(f.stem)
        if str(n) in done or n not in eps or not eps[n].get("audio_url"):
            continue
        if tried.get(str(n), 0) >= MAX_TRIES:
            continue
        try:
            anchors, partial = measure_from_fingerprint(n, json.loads(f.read_text()), eps[n]["audio_url"], log)
        except Exception as e:
            log(f"   episode {n}: couldn't measure from the fingerprint: {type(e).__name__}: {e}")
            anchors, partial = None, False
        if anchors:
            done[str(n)] = anchors
            save(done)
            if partial:
                todo.add(n)
                save_todo(todo)
            tried.pop(str(n), None)
            got.append(n)
        else:
            tried[str(n)] = tried.get(str(n), 0) + 1
        TRIED.write_text(json.dumps(tried) + "\n") if tried else (TRIED.unlink() if TRIED.exists() else None)
    return got


def fingerprint_main(a):
    """--fingerprint N ... / --fingerprint-upcoming: save fingerprints from the mixes on this Mac."""
    done = load()
    if a.fingerprint_upcoming:
        have_t = [int(Path(p).name[:3]) for p in sorted(glob.glob(str(REPO / "transcripts/[0-9]*.md")))]
        out_now = published_episodes()  # published ones are measured from the mix itself; fingerprints are for what's coming
        nums = [n for n in have_t if n not in out_now and not (FP_DIR / f"{n:03d}.json").exists()]
    else:
        nums = [int(t) for t in " ".join(a.numbers).replace(",", " ").split() if t.isdigit()]
    if not nums:
        print("Nothing needs a fingerprint.")
        return 0
    eps, ok = published_episodes(), 0
    for n in nums:
        if (FP_DIR / f"{n:03d}.json").exists() and not a.force:
            print(f"   episode {n}: already has a fingerprint")
            continue
        found = mixes.find_audio(n, eps[n]["title"] if n in eps else None)
        if not found:
            print(f"   episode {n}: skipped (no MP3 in Mixes)")
            continue
        try:
            save_fingerprint(n, found)
            ok += 1
            print(f"   episode {n}: fingerprint saved from {found.name}")
        except Exception as e:
            print(f"   episode {n}: failed: {type(e).__name__}: {e}")
    print(f"\nSaved {ok} fingerprint(s) -> data/mix-fingerprints/")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("numbers", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--fingerprint", action="store_true", help="save a fingerprint of each given episode's mix instead of measuring")
    ap.add_argument("--fingerprint-upcoming", action="store_true", help="save fingerprints for every transcript of an episode that is not published yet")
    ap.add_argument("--from-fingerprints", action="store_true", help="measure published episodes from their fingerprints (no mix needed)")
    a = ap.parse_args()

    if a.from_fingerprints:
        got = measure_from_fingerprints()
        print(f"\nMeasured {len(got)} episode(s) from fingerprints -> data/audio-offsets.json")
        return 0
    if a.fingerprint or a.fingerprint_upcoming:
        return fingerprint_main(a)

    nums = []
    for tok in " ".join(a.numbers).replace(",", " ").split():
        mm = re.fullmatch(r"(\d+)-(\d+)", tok)
        nums += list(range(int(mm.group(1)), int(mm.group(2)) + 1)) if mm else ([int(tok)] if tok.isdigit() else [])
    done, todo = load(), load_todo()
    if a.all:
        nums = [int(Path(p).name[:3]) for p in sorted(glob.glob(str(REPO / "transcripts/[0-9]*.md")))]
    nums = [n for n in dict.fromkeys(nums) if a.force or str(n) not in done or n in todo]  # todo: only the start shift is known so far
    if not nums:
        print("Nothing to measure.")
        return 0

    episodes = published_episodes()
    ok = 0
    for n in nums:
        rec = episodes.get(n)
        found = mixes.find_audio(n, rec["title"] if rec else None)
        mix = [str(found)] if found else []
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
            save(done)
            if n in todo:
                todo.discard(n)
                save_todo(todo)
            ok += 1
    print(f"\nMeasured {ok} of {len(nums)} episodes -> data/audio-offsets.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
