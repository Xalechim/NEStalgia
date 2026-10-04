#!/usr/bin/env python3
"""Make an Audition project folder for each upcoming episode: a copy of the Template folder, its session file renamed to match,
and the game's NES box art (from box_art.py) saved inside as '<Game>_cover.jpg'.

Episodes come from the episode spreadsheet (data/game-info.json). Folders that already exist are never touched.
  python3 scripts/make_project_folders.py --dry-run               show what would be made
  python3 scripts/make_project_folders.py --season 7              make every missing folder for that season
  python3 scripts/make_project_folders.py --first 455 --last 464  only this range
"""
import argparse
import difflib
import json
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import box_art  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
ROOT = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/10_NEStalgia/Audition Projects"
TEMPLATE = ROOT / "Template"


def folder_title(title):
    """A title that is safe in a folder name: 'Faria: A World of Mystery' -> 'Faria A World of Mystery'."""
    t = title.replace("—", " - ").replace("–", " - ").replace("&", "and")
    t = re.sub(r'[:/\\?!*"<>|]', "", t)
    return re.sub(r"\s+", " ", t).strip(" .")


def file_title(title):
    """For the cover's file name: 'Harlem Globetrotters' -> 'Harlem_Globetrotters'."""
    return re.sub(r"\s+", "_", folder_title(title))


def find_box(title, names):
    """Exact match first, then a close match among clean North American boxes (only if it is very close)."""
    exact = box_art.auto_match(title, names)
    if exact and re.search(r"\((?:USA|World)\)|\(US\)", exact):
        return exact, "exact"
    clean = [n for n in names if not re.search(r"\[[^\]]*\]|e-Reader|GameCube|Virtual Console|Switch|Proto|Beta|Sample|\(Pirate\)|Translation", n) and re.search(r"\((?:USA|World|[^)]*US)\)", n)]
    keys = {}
    for n in clean:
        base = re.sub(r",\s*(The|A)$", "", re.sub(r"\s*\((?:[^)]*)\)", "", n[:-4]))
        keys.setdefault(box_art.norm(base), n)
    want = box_art.norm(re.sub(r"^(the|a)\s+", "", title, flags=re.I))
    for key, n in keys.items():  # one is a shorter form of the other ("Bard's Tale" / "Bard's Tale: Tales of the Unknown")
        if min(len(key), len(want)) >= 6 and (key.startswith(want) or want.startswith(key)):
            return n, "close match"
    close = [] if exact else difflib.get_close_matches(box_art.norm(re.sub(r"^(the|a)\s+", "", title, flags=re.I)), list(keys), n=1, cutoff=0.88)
    if exact:
        return exact, "exact"
    return (keys[close[0]], "close match") if close else (None, "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, default=7)
    ap.add_argument("--first", type=int)
    ap.add_argument("--last", type=int)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if not TEMPLATE.exists():
        print(f"Can't find the Template folder: {TEMPLATE}")
        return 1
    info = json.loads((REPO / "data/game-info.json").read_text())
    existing = {int(m.group(1)) for p in ROOT.iterdir() if (m := re.match(r"NES (\d+) - ", p.name))}
    if a.first is None and existing:
        a.first = max(existing) + 1  # "remaining" = after the last folder you already have
    todo = sorted((int(n), v) for n, v in info.items() if v["season"] == a.season and int(n) not in existing
                  and (a.first is None or int(n) >= a.first) and (a.last is None or int(n) <= a.last))
    if not todo:
        print("Every episode already has a folder.")
        return 0
    names = box_art.box_names()
    made, no_art = 0, []
    for n, v in todo:
        name = f"NES {n} - {folder_title(v['title'])}"
        dest = ROOT / name
        fname, how = find_box(v["title"], names)
        print(f"   {name}   art: {fname + (' (' + how + ')' if how == 'close match' else '') if fname else 'none found'}")
        if not fname:
            no_art.append(f"{n} {v['title']}")
        if a.dry_run:
            continue
        if subprocess.run(["cp", "-cR", str(TEMPLATE), str(dest)]).returncode != 0:  # -c: instant copy on the same disk where possible
            shutil.copytree(TEMPLATE, dest)
        sesx = dest / "_Edit.sesx"
        if sesx.exists():
            sesx.rename(dest / f"{name}.sesx")
        if fname:
            data = urllib.request.urlopen(urllib.request.Request(box_art.RAW + urllib.parse.quote(fname), headers=box_art.UA), timeout=60).read()
            box_art.compose(data).save(dest / f"{file_title(v['title'])}_cover.jpg", "JPEG", quality=88, optimize=True)
        made += 1
    print(f"\n{'Would make' if a.dry_run else 'Made'} {len(todo) if a.dry_run else made} folder(s)." + (f" No box art found for: {', '.join(no_art)}" if no_art else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
