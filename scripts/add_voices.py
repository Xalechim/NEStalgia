#!/usr/bin/env python3
"""Teach the voice matcher with more episodes.

Pick episodes that have each host's own mic recording (in Audition Projects).
For each one this listens to the finished episode, uses the mic recordings to
know who is talking, and saves those voice samples. Afterwards it re-tests
itself: for every new episode it checks how well the OTHER samples would have
named its speakers, and compares that with the old samples.

Run it by double-clicking "Add Voices.command" in the scripts folder.
`--no-save` tries it out without changing your saved voice samples.
"""
import argparse
import shutil
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import run_episode as r  # noqa: E402
import voiceid as v  # noqa: E402

PROFILES = r.PROFILES
# The first profiles were built from these episodes, in this order.
LEGACY_EPS = [438, 439, 442, 443, 444, 445, 446, 450]
TOP_K = 5


def load_profiles():
    if not PROFILES.exists():
        return np.zeros((0, 1), np.float32), np.array([]), np.array([], dtype=int)
    z = np.load(PROFILES)
    embs, hosts = z["embs"], z["hosts"]
    if "epnums" in z.files:
        return embs, hosts, z["epnums"]
    idx = z["eps"]  # older file: episode index only
    epnums = np.array([LEGACY_EPS[i] if i < len(LEGACY_EPS) else -1 for i in idx])
    return embs, hosts, epnums


def predict(embs, hosts, vec):
    sims = embs @ vec
    best, best_s = None, -9.0
    for h in sorted(set(hosts.tolist())):
        s = float(np.sort(sims[hosts == h])[::-1][:TOP_K].mean())
        if s > best_s:
            best, best_s = h, s
    return best


def accuracy(rows, embs, hosts):
    """rows: (dur, truth, vec). Returns (% of sentences right, % of airtime right)."""
    if not rows or len(embs) == 0:
        return float("nan"), float("nan")
    ok = sum(1 for d, t, vec in rows if predict(embs, hosts, vec) == t)
    air = sum(d for d, t, vec in rows if predict(embs, hosts, vec) == t)
    return 100 * ok / len(rows), 100 * air / sum(d for d, _, _ in rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("numbers", nargs="*")
    ap.add_argument("--no-save", action="store_true")
    a = ap.parse_args()

    raw = " ".join(a.numbers) or input("Which episode numbers? (for example: 447 448 449): ")
    nums = [int(x) for x in raw.replace(",", " ").split() if x.isdigit()]
    if not nums:
        print("I didn't see any episode numbers. Nothing was done.")
        return 1

    embs0, hosts0, ep0 = load_profiles()
    have = set(ep0.tolist())
    ex = v.extractor()

    new_embs, new_hosts, new_eps = [], [], []
    held = {}  # episode -> list of (dur, truth, vec) used for the re-test
    for n in nums:
        if n in have:
            print(f"Episode {n}: already in the voice samples, skipping.")
            continue
        audio, tracks = r.find_audio(n), r.find_tracks(n)
        if not audio:
            print(f"Episode {n}: no MP3 in the Mixes folder, skipping.")
            continue
        if len(tracks) < 2:
            print(f"Episode {n}: needs at least two hosts' own mic recordings, skipping.")
            continue
        print(f"Episode {n}: listening ({', '.join(sorted(tracks))}) ... this takes a few minutes")
        spec = ",".join(f"{k}={p}" for k, p in tracks.items())
        rows, added = [], 0
        for start, end, host, clear, chunk in v.mix_segments(str(audio), spec):
            vec = v.embed(ex, chunk)
            rows.append((end - start, host, vec))
            if clear and end - start >= 2.0:
                new_embs.append(vec)
                new_hosts.append(host)
                new_eps.append(n)
                added += 1
        held[n] = rows
        print(f"   {added} clean voice samples, {len(rows)} sentences for the re-test")

    if not held:
        print("\nNothing new to add.")
        return 0

    all_embs = np.vstack([embs0, np.array(new_embs)]) if len(embs0) else np.array(new_embs)
    all_hosts = np.concatenate([hosts0, np.array(new_hosts)])
    all_eps = np.concatenate([ep0, np.array(new_eps)])

    print("\nRe-test (how often the right person is named, on episodes the samples did NOT learn from):")
    print(f"{'episode':>8} | {'old samples':>20} | {'new samples':>20}")
    tot = defaultdict(float)
    for n, rows in held.items():
        b = accuracy(rows, embs0, hosts0)
        keep = all_eps != n
        af = accuracy(rows, all_embs[keep], all_hosts[keep])
        print(f"{n:>8} | {b[0]:5.1f}% / {b[1]:5.1f}% air | {af[0]:5.1f}% / {af[1]:5.1f}% air")
        tot["b"] += b[1] * len(rows)
        tot["a"] += af[1] * len(rows)
        tot["n"] += len(rows)
    before, after = tot["b"] / tot["n"], tot["a"] / tot["n"]
    print(f"\nAverage airtime correct: {before:.1f}% before, {after:.1f}% after.")
    if after + 0.5 < before:
        print("The new samples did not help here.")

    if a.no_save:
        print("(--no-save: nothing was changed.)")
        return 0
    if input("\nKeep the new voice samples? (y/n): ").strip().lower().startswith("y"):
        if PROFILES.exists():
            shutil.copy(PROFILES, PROFILES.with_suffix(".backup.npz"))
        np.savez(PROFILES, embs=all_embs, hosts=all_hosts, eps=np.zeros(len(all_embs), int), epnums=all_eps)
        counts = {h: int((all_hosts == h).sum()) for h in sorted(set(all_hosts.tolist()))}
        print(f"Saved. Voice samples now: {counts}. (Old ones are backed up as profiles.backup.npz.)")
    else:
        print("Okay, kept the old voice samples.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
