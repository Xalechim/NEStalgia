#!/usr/bin/env python3
"""Transcribe a NEStalgia episode with speaker labels.

Pipeline: ffmpeg -> 16 kHz mono wav -> mlx-whisper (Apple Silicon) for text and
timestamps -> sherpa-onnx for speaker diarization -> merge -> .md and .vtt.

Usage:
  transcribe.py AUDIO --out transcripts/446-touchdown-fever [--title "Touchdown Fever"]
                [--speakers 4] [--prompt-file scripts/prompt.txt]

Setup is described in scripts/README.md.
"""
import argparse
import re
import json
import os
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

MODELS = Path.home() / ".nestalgia-models"
WHISPER_MODEL = "mlx-community/whisper-large-v3-turbo"
DEFAULT_PROMPT = (
    "Glossary: NEStalgia, Famicom, Konami, Capcom, Hudson Soft, Tecmo, Zapper, Power Pad, "
    "Mike, Sean, Joe, Sam."
)


def to_wav(src: str, dst: str) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-ac", "1", "-ar", "16000", dst],
        check=True,
    )


def read_wav(path: str) -> np.ndarray:
    with wave.open(path, "rb") as w:
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return data.astype(np.float32) / 32768.0


def diarize(samples: np.ndarray, num_speakers: int):
    import sherpa_onnx

    cfg = sherpa_onnx.OfflineSpeakerDiarizationConfig(
        segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
            pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(
                model=str(MODELS / "sherpa-onnx-pyannote-segmentation-3-0" / "model.onnx")
            ),
            num_threads=8,
        ),
        embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(
            model=str(MODELS / os.environ.get("DIAR_EMB", "emb_en.onnx")), num_threads=8
        ),
        clustering=sherpa_onnx.FastClusteringConfig(
            num_clusters=num_speakers if num_speakers > 0 else -1, threshold=float(os.environ.get('DIAR_THRESHOLD', 0.5))
        ),
        min_duration_on=0.3,
        min_duration_off=0.5,
    )
    sd = sherpa_onnx.OfflineSpeakerDiarization(cfg)
    result = sd.process(samples).sort_by_start_time()
    return [(r.start, r.end, r.speaker) for r in result]


def speaker_at(turns, start: float, end: float) -> int:
    """Speaker with the most overlap with [start, end], else nearest turn."""
    best, best_ov = None, 0.0
    for s, e, spk in turns:
        ov = min(end, e) - max(start, s)
        if ov > best_ov:
            best, best_ov = spk, ov
    if best is not None:
        return best
    mid = (start + end) / 2
    return min(turns, key=lambda t: min(abs(mid - t[0]), abs(mid - t[1])))[2]


def ts(sec: float, vtt: bool = False) -> str:
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    sep = "." if vtt else ","
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace(".", sep)


def runaway(text: str) -> bool:
    """Whisper sometimes loops on music/laughter ("Ha! Ha! Ha! ...")."""
    toks = [t.strip(".,!?").lower() for t in text.split()]
    run = 1
    for x, y in zip(toks, toks[1:]):
        run = run + 1 if x == y else 1
        if run >= 5:
            return True
    return False


INTRO_NAMES = re.compile(r"\bI'?m (Mike|Sean|Joe|Sam)\b", re.I)


def intro_names(start: float, text: str) -> bool:
    """The hosts saying their names at the top is too quick to attribute."""
    return start < 150 and bool(INTRO_NAMES.search(text))


def label_words(segs, who, min_dur=0.8):
    """Split Whisper segments into sentences, label each by the loudest mic.

    Per-word labels were too noisy (timing is only good to a fraction of a second);
    whole Whisper segments sometimes hold two speakers ("I'm Mike. I'm Sean.").
    """
    sents = []
    for s in segs:
        words = s.get("words") or [{"word": " " + s["text"].strip(), "start": s["start"], "end": s["end"]}]
        cur = []
        for w in words:
            cur.append(w)
            if w["word"].strip()[-1:] in ".?!":
                sents.append(cur)
                cur = []
        if cur:
            sents.append(cur)
    # merge sentences shorter than min_dur into the next one
    merged, carry = [], []
    for sent in sents:
        sent = carry + sent
        if sent[-1]["end"] - sent[0]["start"] < min_dur:
            carry = sent
        else:
            merged.append(sent)
            carry = []
    if carry:
        if merged:
            merged[-1] += carry
        else:
            merged.append(carry)
    return [
        (m[0]["start"], m[-1]["end"], who(m[0]["start"], m[-1]["end"]), "".join(w["word"] for w in m).strip())
        for m in merged
    ]


HOP = 0.05  # seconds per envelope frame


def envelope(samples: np.ndarray) -> np.ndarray:
    n = int(16000 * HOP)
    k = len(samples) // n
    return np.sqrt((samples[: k * n].reshape(k, n) ** 2).mean(axis=1) + 1e-10)


def track_label_fn(mix: np.ndarray, tracks: dict):
    """Return f(start, end) -> host name using per-host microphone tracks.

    The tracks are raw recordings, the mixdown is the edit, so timing can drift.
    Estimate the offset in 60 s windows by cross-correlating loudness envelopes
    of the mixdown against the sum of the tracks, then compare per-host energy.
    """
    env = {k: envelope(v) for k, v in tracks.items()}
    m = min(len(e) for e in env.values())
    env = {k: e[:m] for k, e in env.items()}
    for k in env:  # level-match each mic
        env[k] = env[k] / (np.percentile(env[k], 95) + 1e-9)
    ref = sum(env.values())
    me = envelope(mix)
    z = lambda x: (x - x.mean()) / (x.std() + 1e-9)
    win, maxlag = int(60 / HOP), int(30 / HOP)
    centers, offsets = [], []
    for c in range(win // 2, len(me) - win // 2 + 1, win // 2):
        a = z(me[c - win // 2 : c + win // 2])
        best, best_off = -1.0, 0
        for off in range(-maxlag, maxlag + 1, 2):
            lo = c - win // 2 + off
            if lo < 0 or lo + win > len(ref):
                continue
            r = float((a * z(ref[lo : lo + win])).mean())
            if r > best:
                best, best_off = r, off
        if best > 0.2:
            centers.append(c * HOP)
            offsets.append(best_off * HOP)
    if not centers:
        raise RuntimeError("could not align host tracks to the mixdown")
    centers, offsets = np.array(centers), np.array(offsets)

    def energies(start: float, end: float) -> dict:
        mid = (start + end) / 2
        off = float(np.interp(mid, centers, offsets))
        lo = max(0, int((start + off) / HOP))
        hi = max(lo + 1, int((end + off) / HOP))
        return {k: float(np.sqrt((e[lo:hi] ** 2).mean())) if hi <= len(e) else 0.0 for k, e in env.items()}

    def label(start: float, end: float) -> str:
        energy = energies(start, end)
        return max(energy, key=energy.get)

    label.energies = energies
    return label


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--out", required=True, help="output path without extension")
    ap.add_argument("--title", default="")
    ap.add_argument("--speakers", type=int, default=0, help="0 = auto-detect")
    ap.add_argument("--prompt-file")
    ap.add_argument("--no-diarize", action="store_true")
    ap.add_argument("--tracks", help="per-host mic tracks, e.g. Mike=a.wav,Sean=b.wav,Joe=c.wav")
    ap.add_argument("--profiles", help="voice profiles from voiceid.py; names speakers when there are no mic tracks")
    ap.add_argument("--cache-dir", help="reuse/save the raw Whisper result here")
    a = ap.parse_args()

    prompt = Path(a.prompt_file).read_text().strip() if a.prompt_file else DEFAULT_PROMPT
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    cache = Path(a.cache_dir) / (out.name + ".whisper.json") if a.cache_dir else None
    with tempfile.TemporaryDirectory() as td:
        wav = os.path.join(td, "a.wav")
        to_wav(a.audio, wav)
        samples = read_wav(wav)

        if cache and cache.exists():
            res = json.loads(cache.read_text())
        else:
            import mlx_whisper

            res = mlx_whisper.transcribe(
                wav,
                path_or_hf_repo=WHISPER_MODEL,
                initial_prompt=prompt,
                word_timestamps=True,
                condition_on_previous_text=True,
                verbose=None,
            )
            if cache:
                cache.parent.mkdir(parents=True, exist_ok=True)
                cache.write_text(json.dumps(res, default=float))

    segs, prev = [], None
    for s in res["segments"]:
        txt = s["text"].strip()
        if not txt or runaway(txt) or (txt == prev and s["end"] - s["start"] < 2.0):
            continue  # empty, looping, or an immediate repeat of the previous segment
        segs.append(s)
        prev = txt
    names = None
    if a.tracks:
        tracks = {}
        with tempfile.TemporaryDirectory() as td:
            for item in a.tracks.split(","):
                name, path = item.split("=", 1)
                w = os.path.join(td, name + ".wav")
                to_wav(path, w)
                tracks[name] = read_wav(w)
        who = track_label_fn(samples, tracks)
        rows = label_words(segs, who)
        names = True
    elif a.profiles:
        sys.path.insert(0, str(Path(__file__).parent))
        from voiceid import Identifier

        idr = Identifier(a.profiles)

        def who(start: float, end: float) -> str:
            sc = idr.scores(samples[int(start * 16000) : int(end * 16000)])
            return max(sc, key=sc.get)

        rows = label_words(segs, who)
        rows = [(s_, e_, "Hosts" if intro_names(s_, t) else spk, t) for s_, e_, spk, t in rows]
        names = "voice"
    else:
        turns = [] if a.no_diarize else diarize(samples, a.speakers)
        rows = []
        for s in segs:
            spk = speaker_at(turns, s["start"], s["end"]) if turns else 0
            rows.append((s["start"], s["end"], spk, s["text"].strip()))
        order = {}
        for _, _, spk, _ in rows:
            order.setdefault(spk, len(order) + 1)
        rows = [(s, e, f"Speaker {order[spk]}", t) for s, e, spk, t in rows]

    rows = [(s_, e_, spk, t.replace("welcome to Nostalgia", "welcome to NEStalgia")) for s_, e_, spk, t in rows]

    # Merge consecutive segments from the same speaker into turns.
    merged = []
    for s, e, spk, t in rows:
        if merged and merged[-1][2] == spk and s - merged[-1][1] < 2.0:
            merged[-1] = (merged[-1][0], e, spk, merged[-1][3] + " " + t)
        else:
            merged.append((s, e, spk, t))

    heading = f"# {a.title}\n\n" if a.title else ""
    note = {
        True: "_Auto-generated transcript. Speakers identified from the hosts' separate microphone tracks._",
        "voice": "_Auto-generated transcript. Speaker names are matched automatically by voice and are not perfect, "
        "especially on short interjections. The opening name introductions are left as \"Hosts\"._",
        None: "_Auto-generated transcript. Speaker numbers are not yet matched to host names._",
    }[names]
    md = [heading + note + "\n"]
    for s, e, spk, t in merged:
        h, rem = divmod(int(s), 3600)
        m, sec = divmod(rem, 60)
        stamp = f"{h}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"
        md.append(f"**{spk}** [{stamp}]: {t}\n")
    out.with_suffix(".md").write_text("\n".join(md))

    vtt = ["WEBVTT", ""]
    for s, e, spk, t in rows:
        vtt += [f"{ts(s, True)} --> {ts(e, True)}", f"<v {spk}>{t}", ""]
    out.with_suffix(".vtt").write_text("\n".join(vtt))

    n_spk = len({r[2] for r in rows})
    print(f"{out.name}: {len(merged)} turns, {n_spk} speakers, {res['segments'][-1]['end']/60:.1f} min")


if __name__ == "__main__":
    sys.exit(main())
