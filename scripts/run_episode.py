#!/usr/bin/env python3
"""Make a transcript for one episode, start to finish.

Asks for an episode number, finds the audio, picks the best speaker-labeling
method, writes the transcript, links it in the episode index, and (if you say
yes) publishes it to GitHub.

Run it by double-clicking "Transcribe Episode.command" in the scripts folder.
`--dry-run` shows what it would do without transcribing.
"""
import argparse
import glob
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ICLOUD = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/10_NEStalgia"
MIXES = ICLOUD / "Mixes"
AUDITION = ICLOUD / "Audition Projects"
PROFILES = Path.home() / ".nestalgia-models/profiles.npz"
HOSTS = {"espo": "Mike", "sean": "Sean", "joe": "Joe"}


def slug(s: str) -> str:
    s = s.lower().replace("'", "").replace("’", "")
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s)).strip("-")


def find_audio(n: int):
    hits = sorted(glob.glob(str(MIXES / f"NES {n} - *.mp3")))
    # prefer the cleaned-up "mixdown" version if there are several
    hits.sort(key=lambda p: ("mixdown" not in p.lower(), p))
    return Path(hits[0]) if hits else None


def find_tracks(n: int):
    """Each host's own mic recording, if the Audition project has them."""
    folders = glob.glob(str(AUDITION / f"NES {n} - *"))
    if not folders:
        return {}
    tracks = {}
    for wav in glob.glob(folders[0] + "/*.wav"):
        low = os.path.basename(wav).lower()
        if "mixdown" in low:
            continue
        for key, name in HOSTS.items():
            if key in low and name not in tracks:
                tracks[name] = wav
    return tracks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("number", nargs="?")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true", help="publish without asking")
    a = ap.parse_args()

    num = a.number or input("Which episode number? (for example 401): ").strip()
    if not num.isdigit():
        print("That doesn't look like a number. Nothing was done.")
        return 1
    n = int(num)

    audio = find_audio(n)
    if not audio:
        print(f"I couldn't find an MP3 for episode {n} in:\n  {MIXES}")
        print("Put the finished episode there, named like 'NES 401 - Game Name.mp3', and try again.")
        return 1

    name = re.sub(rf"^NES {n} - ", "", audio.stem)
    name = re.sub(r"[_ ]mixdown.*$", "", name, flags=re.I).strip()
    out = REPO / "transcripts" / f"{n:03d}-{slug(name)}"
    title = f"{n:03d} - {name}"

    tracks = find_tracks(n)
    cmd = [sys.executable, str(REPO / "scripts/transcribe.py"), str(audio), "--out", str(out), "--title", title]
    if len(tracks) >= 2:
        method = f"separate microphone tracks ({', '.join(sorted(tracks))}), most accurate"
        cmd += ["--tracks", ",".join(f"{k}={v}" for k, v in tracks.items())]
    elif PROFILES.exists():
        method = "voice matching (good, but not perfect on short replies)"
        cmd += ["--profiles", str(PROFILES)]
    else:
        method = "no speaker names (voice profiles not found)"
        cmd += ["--no-diarize"]

    print(f"\nEpisode: {title}\nAudio:   {audio.name}\nSpeaker names by: {method}\n")
    if a.dry_run:
        print("Dry run, stopping here.")
        return 0

    print("Transcribing. This takes a few minutes. You can leave this window open and wait.\n")
    if subprocess.run(cmd).returncode != 0:
        print("\nSomething went wrong while transcribing. Nothing was published.")
        return 1

    # Link the transcript from the episode index.
    index = REPO / "episodes/README.md"
    link = f"[transcript](../transcripts/{out.name}.md)"
    if index.exists():
        text = index.read_text()
        row = re.compile(rf"^(\| {n:03d} \|.*?\| )(\[(?:notes|outline|early notes)\]\([^)]*\))( \|)$", re.M)
        if link not in text and row.search(text):
            index.write_text(row.sub(rf"\1\2, {link}\3", text, count=1))
            print("Added a transcript link to the episode index.")
        elif link not in text:
            print("Note: this episode isn't in the episode index yet, so I didn't add a link.")

    print(f"\nDone! The transcript is here:\n  {out}.md\n")
    if a.yes or input("Publish it to GitHub now? (y/n): ").strip().lower().startswith("y"):
        subprocess.run(["git", "-C", str(REPO), "add", "transcripts", "episodes"], check=True)
        subprocess.run(["git", "-C", str(REPO), "commit", "-m", f"Add transcript for episode {n:03d}"], check=True)
        r = subprocess.run(["git", "-C", str(REPO), "push"])
        print("Published." if r.returncode == 0 else "The upload failed; the transcript is saved locally.")
    else:
        print("Okay, not published. It's saved on your Mac.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
