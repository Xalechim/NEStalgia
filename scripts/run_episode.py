#!/usr/bin/env python3
"""Make a transcript for one episode, start to finish.

Asks for episode number(s), finds the audio, picks the best speaker-labeling
method, writes the transcript, links it in the episode index, and (if you say
yes) publishes it to GitHub.

Several at once work too (401 402 405-410). Run it by double-clicking "Transcribe Episode.command" in the scripts folder.
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


def parse_numbers(raw: str):
    """'401 402, 405-408' -> [401, 402, 405, 406, 407, 408]"""
    nums = []
    for tok in raw.replace(",", " ").split():
        m = re.fullmatch(r"(\d+)-(\d+)", tok)
        if m and int(m.group(1)) <= int(m.group(2)):
            nums += range(int(m.group(1)), int(m.group(2)) + 1)
        elif tok.isdigit():
            nums.append(int(tok))
        else:
            return None
    return list(dict.fromkeys(nums))  # drop repeats, keep order


def maybe_links(n: int) -> None:
    """If an Anthropic key is set up, offer to find the web links for this episode now."""
    key_file = Path.home() / ".config/nestalgia/anthropic_key"
    if not (key_file.exists() or os.environ.get("ANTHROPIC_API_KEY")) or not sys.stdin.isatty():
        return
    if input(f"   Also find the web links for episode {n} now? (costs a few cents) (y/n): ").strip().lower().startswith("y"):
        subprocess.run([sys.executable, str(REPO / "scripts/make_links.py"), str(n)])


def transcribe_one(n: int, dry_run: bool) -> bool:
    audio = find_audio(n)
    if not audio:
        print(f"Episode {n}: I couldn't find an MP3 in:\n  {MIXES}")
        print("   Put the finished episode there, named like 'NES 401 - Game Name.mp3'.")
        return False

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

    print(f"\nEpisode: {title}\nAudio:   {audio.name}\nSpeaker names by: {method}")
    if dry_run:
        return True

    print("Transcribing. This takes a few minutes.\n")
    if subprocess.run(cmd).returncode != 0:
        print(f"Episode {n}: something went wrong while transcribing. Moving on.")
        return False

    # Link the transcript from the episode index (works for rows with one or several links).
    index = REPO / "episodes/README.md"
    link = f"[transcript](../transcripts/{out.name}.md)"
    if index.exists():
        text = index.read_text()
        row = re.compile(rf"^(\| {n:03d} \|.*) \|$", re.M)
        if link not in text and row.search(text):
            index.write_text(row.sub(rf"\1, {link} |", text, count=1))
        elif link not in text:
            print("Note: this episode isn't in the episode index yet, so I didn't add a link.")
    print(f"Episode {n}: done -> transcripts/{out.name}.md")
    maybe_links(n)
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("numbers", nargs="*")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true", help="publish without asking")
    a = ap.parse_args()

    raw = " ".join(a.numbers) or input(
        "Which episode(s)? One number (401), several (401 402 405), or a range (401-410): "
    )
    nums = parse_numbers(raw)
    if not nums:
        print("I couldn't read that. Use numbers like: 401   or   401 402 405   or   401-410. Nothing was done.")
        return 1
    print(f"\nEpisodes to do ({len(nums)}): {', '.join(map(str, nums))}")

    done, failed = [], []
    for n in nums:
        (done if transcribe_one(n, a.dry_run) else failed).append(n)

    print("\n==============================")
    print(f"Finished: {len(done)} done" + (f", {len(failed)} skipped ({', '.join(map(str, failed))})" if failed else ""))
    if a.dry_run or not done:
        return 0 if done or a.dry_run else 1
    if a.yes or input("\nPublish them to GitHub now? (y/n): ").strip().lower().startswith("y"):
        label = f"{done[0]:03d}" if len(done) == 1 else f"{len(done)} episodes ({done[0]:03d} to {done[-1]:03d})"
        for script in ("build_episode_data.py", "build_index.py"):  # keep the data file and the index current (needs internet)
            subprocess.run([sys.executable, str(REPO / "scripts" / script)], cwd=REPO)
        subprocess.run(["git", "-C", str(REPO), "add", "transcripts", "episodes", "data"], check=True)
        subprocess.run(["git", "-C", str(REPO), "commit", "-m", f"Add transcripts for {label}"], check=True)
        r = subprocess.run(["git", "-C", str(REPO), "push"])
        print("Published." if r.returncode == 0 else "The upload failed; the transcripts are saved locally.")
    else:
        print("Okay, not published. They're saved on your Mac.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
