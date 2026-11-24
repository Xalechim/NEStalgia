#!/usr/bin/env python3
"""Transcripts for the Patreon-only shows: NEStalgia Bytes and SNEStalgia.

These episodes are for Patreon members, and this repo is public, so their transcripts are never written into the repo and
never committed. They go to iCloud instead, in 10_NEStalgia/Patreon Transcripts/, ready to attach to the Patreon posts:

  Patreon Transcripts/Bytes/nb-022-sweet-home.md  (+ .vtt)
  Patreon Transcripts/SNEStalgia/snes-003-f-zero.md  (+ .vtt)

It looks in iCloud Mixes for the final mixes ('NB 022 - Sweet Home.mp3', 'SNES 003 - FZero.mp3'), skips any that already have a
transcript, and runs the same transcriber as the main show (paragraphs with [mm:ss] timestamps, no speaker labels). Timestamps are
measured on your mix. A '_FREE' cut of a Bytes episode is never used when the full mix exists.

  python3 scripts/python/patreon_transcripts.py                 do every Bytes and SNEStalgia mix that has no transcript yet
  python3 scripts/python/patreon_transcripts.py --dry-run       list what it would do
  python3 scripts/python/patreon_transcripts.py --bytes 22 40-45   only these Bytes episodes (redoes them if they exist)
  python3 scripts/python/patreon_transcripts.py --snes 3           only these SNEStalgia episodes
  python3 scripts/python/patreon_transcripts.py --redo             remake transcripts that already exist
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import mixes  # noqa: E402
from textutil import nice_case  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
ICLOUD = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/10_NEStalgia"
OUT_ROOT = ICLOUD / "Patreon Transcripts"

# show -> (file-name prefix in Mixes, output folder, output file prefix, title prefix)
SHOWS = {
    "bytes": {"mix": "NB", "folder": "Bytes", "file": "nb", "title": "NEStalgia Bytes"},
    "snes": {"mix": "SNES", "folder": "SNEStalgia", "file": "snes", "title": "SNEStalgia"},
}


def slug(s):
    s = s.lower().replace("'", "").replace("’", "")
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s)).strip("-")


def mix_pattern(show):
    """'NB 022 - ...', 'NB_053 - ...', 'NB022_...' (not 'NBA ...', not 'NB 0225'); same for SNES."""
    return re.compile(rf"^{SHOWS[show]['mix']}[\s_]*0*(\d+)(?!\d)", re.I)


def is_free_cut(path):
    return bool(re.search(r"(?i)[\s_-]free\b", path.stem))


def file_name_title(path, show):
    """The game name as written in the mix's file name: 'NB 022 - Sweet Home_FREE' -> 'Sweet Home'. '' if there isn't one."""
    s = mix_pattern(show).sub("", path.stem, count=1)
    s = re.sub(r"(?i)[_ ]?(mixdown|free)\w*", "", s)
    s = re.sub(r"(?i)[_ ]?v\d+$", "", s)
    s = s.replace("_", " ").strip(" -")
    return re.sub(r"\s+", " ", s)


def find_mixes(show, folder=None):
    """{number: best mix path} for one show. Never picks a _FREE cut when a full mix exists; mp3 beats wav; a later version wins."""
    folder = Path(folder or mixes.MIXES)
    if not folder.exists():
        return {}
    pat = mix_pattern(show)
    by_n = {}
    for p in sorted(folder.iterdir()):
        m = pat.match(p.name)
        if m and p.suffix.lower() in mixes.AUDIO:
            by_n.setdefault(int(m.group(1)), []).append(p)

    def rank(p):
        versions = [int(v) for v in re.findall(r"(?i)v(\d+)", p.stem)]
        return (is_free_cut(p), p.suffix.lower() != ".mp3", -(max(versions) if versions else 0), p.name)

    return {n: min(ps, key=rank) for n, ps in sorted(by_n.items())}


def known_titles(show, repo=REPO):
    """{number: title} from files the repo already has: the Bytes list from the spreadsheet, SNES show notes."""
    out = {}
    if show == "bytes":
        f = repo / "data/bytes-info.json"
        if f.exists():
            out = {int(n): v["title"] for n, v in json.loads(f.read_text()).items() if v.get("title")}
    else:
        for p in sorted((repo / "episodes/snes").glob("*.md")) if (repo / "episodes/snes").exists() else []:
            m = re.match(r"(\d+)-", p.name)
            if not m:
                continue
            first = p.read_text().split("\n", 1)[0]
            t = re.sub(r"^#\s*S?N?E?S?\s*\d+\s*-\s*", "", first).strip() if first.startswith("#") else ""
            out[int(m.group(1))] = t or p.stem.split("-", 1)[1].replace("-", " ").title()
    return out


def episode_title(show, n, path, titles):
    return titles.get(n) or nice_case(file_name_title(path, show)) or f"Episode {n}"


def out_stem(show, n, title):
    return f"{SHOWS[show]['file']}-{n:03d}-{slug(title)[:60].strip('-')}"


def existing(show, n, root=OUT_ROOT):
    """The transcript already made for this episode, whatever its title was then."""
    return sorted((root / SHOWS[show]["folder"]).glob(f"{SHOWS[show]['file']}-{n:03d}-*.md"))


def parse_numbers(tokens):
    nums = []
    for tok in " ".join(tokens).replace(",", " ").split():
        m = re.fullmatch(r"(\d+)-(\d+)", tok)
        nums += list(range(int(m.group(1)), int(m.group(2)) + 1)) if m else ([int(tok)] if tok.isdigit() else [])
    return list(dict.fromkeys(nums))


def plan(show, wanted=None, redo=False, folder=None, root=OUT_ROOT, repo=REPO):
    """[(number, mix path, title, transcript stem)] still to do for one show."""
    found = find_mixes(show, folder)
    titles = known_titles(show, repo)
    todo = []
    for n, path in found.items():
        if wanted and n not in wanted:
            continue
        if not wanted and not redo and existing(show, n, root):
            continue  # already done (naming an episode, or --redo, remakes it)
        title = episode_title(show, n, path, titles)
        todo.append((n, path, title, out_stem(show, n, title)))
    return todo


def transcribe(show, n, path, title, stem, root=OUT_ROOT):
    out_dir = root / SHOWS[show]["folder"]
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in existing(show, n, root):  # a redo under a new title replaces the old files
        for ext in (".md", ".vtt"):
            old.with_suffix(ext).unlink(missing_ok=True)
    # Whisper hears 'F-Zero' as 'F0' unless it is told the name: give it the usual glossary plus this episode's title.
    with tempfile.TemporaryDirectory() as td:
        prompt = Path(td) / "prompt.txt"
        prompt.write_text(f"Glossary: NEStalgia, SNEStalgia, NEStalgia Bytes, Famicom, Super Famicom, Super Nintendo, SNES, Mode 7, "
                          f"Nintendo, Konami, Capcom, Hudson Soft, {title}, Mike, Sean, Joe, Sam.")
        cmd = [sys.executable, str(REPO / "scripts/python/transcribe.py"), str(path), "--out", str(out_dir / stem),
               "--title", f"{SHOWS[show]['title']} {n:03d} - {title}", "--prompt-file", str(prompt)]
        return subprocess.run(cmd).returncode == 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--redo", action="store_true", help="remake transcripts that already exist")
    ap.add_argument("--bytes", nargs="*", metavar="N", help="only these Bytes episodes (none named = all that need one)")
    ap.add_argument("--snes", nargs="*", metavar="N", help="only these SNEStalgia episodes (none named = all that need one)")
    a = ap.parse_args()

    # naming a show with numbers limits the run to those; naming one without numbers (or neither) means everything that's missing
    shows = [s for s, v in (("bytes", a.bytes), ("snes", a.snes)) if v is not None] or ["bytes", "snes"]
    if not str(OUT_ROOT).startswith(str(ICLOUD)) or str(OUT_ROOT).startswith(str(REPO)):
        print("Refusing to run: the Patreon transcripts must stay out of the repo.")
        return 1

    failed = done = 0
    for show in shows:
        names = {"bytes": a.bytes, "snes": a.snes}[show]
        wanted = parse_numbers(names) if names else None
        todo = plan(show, wanted, a.redo)
        print(f"\n{SHOWS[show]['title']}: {len(todo)} to do" + (f" ({', '.join(str(t[0]) for t in todo)})" if todo else " (every mix already has a transcript)"))
        if wanted:
            missing = [n for n in wanted if n not in {t[0] for t in todo}]
            if missing:
                print(f"   no mix found in Mixes for: {', '.join(map(str, missing))}")
                failed += len(missing)
        for n, path, title, stem in todo:
            print(f"   {n:03d} {title}  <-  {path.name}")
            if a.dry_run:
                continue
            if transcribe(show, n, path, title, stem):
                done += 1
                print(f"   done -> {OUT_ROOT.name}/{SHOWS[show]['folder']}/{stem}.md")
            else:
                failed += 1
                print(f"   FAILED: {n:03d} {title}")
    if not a.dry_run:
        print(f"\nFinished: {done} transcribed" + (f", {failed} problem(s)" if failed else "") + f".\nThey are in: {OUT_ROOT}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
