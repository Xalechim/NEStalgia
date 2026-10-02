#!/usr/bin/env python3
"""Remove the speaker lines from existing transcripts, in bulk. Works offline: no audio, no internet, no AI.

For every transcripts/NNN-*.md that still has speaker lines (**Mike** [00:22]: ...), this
  - takes the sentence timing from the matching .vtt file (or, if there isn't one, estimates it from the turn timestamps),
  - drops the speaker names,
  - regroups the text into paragraphs at natural thought breaks, each starting with its timestamp,
  - rewrites the .md and the .vtt (the .vtt loses its speaker tags too),
  - and checks that not a single word was lost.
Transcripts that are already converted are skipped, so it is safe to run again.

  python3 scripts/strip_speakers.py --dry-run         show what would change, write nothing
  python3 scripts/strip_speakers.py                   convert every transcript that still has speakers
  python3 scripts/strip_speakers.py 446 400-410       only these episodes
  python3 scripts/strip_speakers.py --folder DIR      work on a different folder of transcripts

The old versions stay in git history (git log, git checkout) if you ever want them back.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import paragraphs as P  # noqa: E402

REPO = Path(__file__).resolve().parent.parent


def word_count(text):
    return len(re.findall(r"\S+", text))


def cues_from_turns(turns):
    """No .vtt available: split each speaker turn into sentences and spread them over the time until the next turn."""
    cues = []
    for i, (start, text) in enumerate(turns):
        end_limit = turns[i + 1][0] if i + 1 < len(turns) else start + max(3, len(text) * 0.07)
        sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        total = sum(len(s) for s in sents) or 1
        t = float(start)
        span = max(1.0, min(end_limit - start, len(text) * 0.09))  # speech is ~11 characters/second
        for s in sents:
            dur = span * len(s) / total
            cues.append({"start": t, "end": t + dur * 0.97, "text": s})
            t += dur
    return cues


def convert(md_path, dry_run):
    """Returns (status, detail). status: converted | skipped | warning | error."""
    md_text = md_path.read_text()
    if not P.is_old_format(md_text):
        return "skipped", "already has no speaker lines"
    title, turns = P.read_old_markdown(md_text)
    old_words = sum(word_count(t) for _, t in turns)

    vtt_path = md_path.with_suffix(".vtt")
    if vtt_path.exists():
        cues = P.read_vtt(vtt_path.read_text())
        source = "timing from the .vtt"
    else:
        cues = cues_from_turns(turns)
        source = "no .vtt: timing estimated from the turn timestamps"
    if not cues:
        return "error", "no text found"

    paras = P.group(cues)
    new_words = sum(word_count(p["text"]) for p in paras)
    cue_words = sum(word_count(c["text"]) for c in cues)
    if new_words != cue_words:
        return "error", f"word count changed inside the paragraphs ({cue_words} -> {new_words}); left untouched"
    note = ""
    if abs(new_words - old_words) > max(3, old_words * 0.002):
        note = f" (note: {old_words} words in the old .md vs {new_words} now; the .vtt is the source for timing and text)"
    if not dry_run:
        md_path.write_text(P.to_markdown(title, paras))
        vtt_path.write_text(P.to_vtt(cues))
    return ("warning" if note else "converted"), f"{len(turns)} speaker turns -> {len(paras)} paragraphs, {new_words} words; {source}{note}"


def pick_files(folder, numbers):
    files = sorted(folder.glob("[0-9]*.md"))
    if not numbers:
        return files
    want = set()
    for tok in " ".join(numbers).replace(",", " ").split():
        m = re.fullmatch(r"(\d+)-(\d+)", tok)
        if m:
            want |= set(range(int(m.group(1)), int(m.group(2)) + 1))
        elif tok.isdigit():
            want.add(int(tok))
    return [f for f in files if int(f.name[:3]) in want]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("numbers", nargs="*", help="episode numbers or ranges (default: all)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--folder", default=str(REPO / "transcripts"))
    a = ap.parse_args()

    folder = Path(a.folder)
    files = pick_files(folder, a.numbers)
    if not files:
        print(f"No transcripts found in {folder}.")
        return 1

    counts = {"converted": 0, "skipped": 0, "warning": 0, "error": 0}
    for f in files:
        status, detail = convert(f, a.dry_run)
        counts[status] += 1
        if status != "skipped" or len(files) <= 3:
            mark = {"converted": "OK  ", "warning": "NOTE", "skipped": "skip", "error": "FAIL"}[status]
            print(f"  {mark} {f.name}: {detail}")
    verb = "would convert" if a.dry_run else "converted"
    print(f"\n{verb} {counts['converted'] + counts['warning']}, already done {counts['skipped']}, failed {counts['error']}"
          + (" (dry run: nothing was changed)" if a.dry_run else ""))
    return 1 if counts["error"] else 0


if __name__ == "__main__":
    sys.exit(main())
