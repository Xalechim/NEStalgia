#!/usr/bin/env python3
"""Voice enrollment and speaker identification for NEStalgia hosts.

Enroll: build voice profiles from episodes that have separate mic tracks, using
stretches where only one host is talking.
  voiceid.py enroll --out ~/.nestalgia-models/profiles.npz \
      --episode "Mike=Espo_A.wav,Sean=Sean_A.wav,Joe=Joe_A.wav" [--episode ...]

transcribe.py then uses the profiles (--profiles) to name speakers on episodes
that only have a mixdown.
"""
import argparse
import os
import random
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from transcribe import HOP, MODELS, envelope, read_wav, to_wav  # noqa: E402

EMB_MODEL = MODELS / "wespeaker_resnet34.onnx"
SR = 16000


def extractor():
    import sherpa_onnx

    cfg = sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(EMB_MODEL), num_threads=8)
    return sherpa_onnx.SpeakerEmbeddingExtractor(cfg)


def embed(ex, samples: np.ndarray) -> np.ndarray:
    st = ex.create_stream()
    st.accept_waveform(sample_rate=SR, waveform=samples.astype(np.float32))
    st.input_finished()
    v = np.array(ex.compute(st), dtype=np.float32)
    return v / (np.linalg.norm(v) + 1e-9)


def solo_chunks(tracks: dict, chunk_s=3.0, per_host=30, seed=0):
    """Yield (host, samples) for stretches where only that host is loud."""
    env = {k: envelope(v) for k, v in tracks.items()}
    m = min(len(e) for e in env.values())
    env = {k: e[:m] for k, e in env.items()}
    for k in env:
        env[k] = env[k] / (np.percentile(env[k], 95) + 1e-9)
    rng = random.Random(seed)
    need = int(chunk_s / HOP)
    for host, e in env.items():
        others = np.max([o for k, o in env.items() if k != host], axis=0) if len(env) > 1 else np.zeros(m)
        solo = (e > 0.25) & (e > 4 * others)
        # frames where the mic is "talking" with brief gaps tolerated
        cands, i = [], 0
        while i + need < m:
            if solo[i : i + need].mean() > 0.6 and others[i : i + need].max() < 0.5:
                cands.append(i)
                i += need
            else:
                i += int(0.5 / HOP)
        rng.shuffle(cands)
        for i in cands[:per_host]:
            a = int(i * HOP * SR)
            yield host, tracks[host][a : a + int(chunk_s * SR)]


def load_tracks(spec: str) -> dict:
    tracks = {}
    with tempfile.TemporaryDirectory() as td:
        for item in spec.split(","):
            name, path = item.split("=", 1)
            w = os.path.join(td, name + ".wav")
            to_wav(path, w)
            tracks[name] = read_wav(w)
    return tracks


CACHE = MODELS / "cache"


def mix_segments(mix_path: str, spec: str):
    """All sentences of the mixdown (>= 1 s) with the host named by the mic tracks.

    Yields (start, end, host, clear, samples); `clear` means one mic was at least
    3x louder than the next, i.e. no crosstalk, so the label is trustworthy.
    """
    import json

    import mlx_whisper
    from transcribe import WHISPER_MODEL, label_words, track_label_fn

    with tempfile.TemporaryDirectory() as td:
        wav = os.path.join(td, "mix.wav")
        to_wav(mix_path, wav)
        mix = read_wav(wav)
        cache = CACHE / (Path(mix_path).stem + ".json")
        if cache.exists():
            res = json.loads(cache.read_text())
        else:
            res = mlx_whisper.transcribe(
                wav, path_or_hf_repo=WHISPER_MODEL, word_timestamps=True,
                condition_on_previous_text=True, verbose=None,
            )
            CACHE.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(res, default=float))
    who = track_label_fn(mix, load_tracks(spec))
    segs = [s for s in res["segments"] if s["text"].strip()]
    for a, b, host, _ in label_words(segs, who):
        if b - a < 1.0:
            continue
        en = sorted(who.energies(a, b).items(), key=lambda kv: -kv[1])
        clear = len(en) < 2 or en[0][1] >= 3.0 * en[1][1]
        yield a, b, host, clear, mix[int(a * SR) : int(b * SR)]


def mix_chunks(mix_path: str, spec: str, min_dur=2.0):
    """Clear, solo-speaker sentences of the mixdown, for training."""
    for a, b, host, clear, chunk in mix_segments(mix_path, spec):
        if clear and b - a >= min_dur:
            yield host, chunk


def enroll_mix(args):
    ex = extractor()
    embs, hosts, eps = [], [], []
    for n, item in enumerate(args.episode):
        mix_path, spec = item.split(";", 1)
        for host, chunk in mix_chunks(mix_path, spec):
            embs.append(embed(ex, chunk))
            hosts.append(host)
            eps.append(n)
        print(f"episode {n}: {sum(1 for e in eps if e == n)} segments")
    np.savez(args.out, embs=np.array(embs), hosts=np.array(hosts), eps=np.array(eps))
    print({h: hosts.count(h) for h in set(hosts)})


def enroll(args):
    ex = extractor()
    embs, hosts, eps = [], [], []
    for n, spec in enumerate(args.episode):
        for host, chunk in solo_chunks(load_tracks(spec), per_host=args.per_host, seed=n):
            embs.append(embed(ex, chunk))
            hosts.append(host)
            eps.append(n)
        print(f"episode {n}: {sum(1 for e in eps if e == n)} chunks")
    np.savez(args.out, embs=np.array(embs), hosts=np.array(hosts), eps=np.array(eps))
    print({h: hosts.count(h) for h in set(hosts)})


class Identifier:
    def __init__(self, profiles: str, top_k=5):
        z = np.load(profiles)
        self.embs, self.hosts, self.top_k = z["embs"], z["hosts"], top_k
        self.names = sorted(set(self.hosts.tolist()))
        self.ex = extractor()

    def scores(self, samples: np.ndarray) -> dict:
        v = embed(self.ex, samples)
        sims = self.embs @ v
        out = {}
        for h in self.names:
            s = np.sort(sims[self.hosts == h])[::-1][: self.top_k]
            out[h] = float(s.mean())
        return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("enroll")
    e.add_argument("--out", required=True)
    e.add_argument("--episode", action="append", required=True)
    e.add_argument("--per-host", type=int, default=30)
    e.set_defaults(fn=enroll)
    m = sub.add_parser("enroll-mix")
    m.add_argument("--out", required=True)
    m.add_argument("--episode", action="append", required=True, help="MIXDOWN.mp3;Name=track.wav,...")
    m.set_defaults(fn=enroll_mix)
    a = ap.parse_args()
    a.fn(a)
