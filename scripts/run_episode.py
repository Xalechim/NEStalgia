#!/usr/bin/env python3
"""Make a transcript for one episode, start to finish.

Asks for episode number(s), finds the audio, writes the transcript (paragraphs with
timestamps, no speaker labels), links it in the episode index, and (if you say yes)
publishes it to GitHub.

Several at once work too (401 402 405-410). Run it by double-clicking "Transcribe Episode.command" in the scripts folder.
`--dry-run` shows what it would do without transcribing.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import mixes  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
ICLOUD = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/10_NEStalgia"
MIXES = ICLOUD / "Mixes"


def slug(s: str) -> str:
    s = s.lower().replace("'", "").replace("’", "")
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s)).strip("-")


def feed_title(n: int):
    """The episode's title from the podcast feed data (e.g. 'Sky Shark'), or None."""
    try:
        for r in json.loads((REPO / "data/episodes.json").read_text()):
            if r["type"] == "episode" and r["number"] == n and "remaster" not in r["feed_title"].lower():
                t = r["title"].strip()
                return t.title() if t.isupper() else t
    except Exception:
        pass
    return None


def find_audio(n: int):
    return mixes.find_audio(n, feed_title(n))


def episode_name(n: int, audio: Path):
    """(game name, file name without extension) for this episode's transcript, matching its show notes if they exist."""
    name = feed_title(n)
    if not name:
        name = re.sub(r"(?i)^(NES\s*0*%d|0*%d)\s*-?\s*" % (n, n), "", audio.stem)
        name = re.sub(r"(?i)[_ ]?mixdown.*$", "", name).strip(" _-") or audio.stem
    notes = sorted((REPO / "episodes").glob(f"{n:03d}-*.md"))
    return name, (notes[0].stem if notes else f"{n:03d}-{slug(name)}")


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


def measure_offset(n: int) -> None:
    """Measure how far the podcast host's audio is shifted from the final mix, so clickable timestamps on the website land
    in the right place. Needs internet and the episode to be in the public feed; if not, it is skipped (run it later)."""
    r = subprocess.run([sys.executable, str(REPO / "scripts/audio_offsets.py"), str(n)], capture_output=True, text=True)
    lines = [l for l in (r.stdout or "").splitlines() if l.strip().startswith("episode")]
    print("   " + (lines[-1].strip() if lines else "Couldn't measure the audio shift now (offline, or not in the public feed yet)."))


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

    name, stem = episode_name(n, audio)
    out = REPO / "transcripts" / stem
    title = f"{n:03d} - {name}"

    cmd = [sys.executable, str(REPO / "scripts/transcribe.py"), str(audio), "--out", str(out), "--title", title]

    print(f"\nEpisode: {title}\nAudio:   {audio.name}")
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
    measure_offset(n)
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
