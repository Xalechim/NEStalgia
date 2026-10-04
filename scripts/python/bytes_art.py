#!/usr/bin/env python3
"""Cover art for the NEStalgia Bytes episodes: the Famicom/NES box scan from the libretro thumbnail library when the game is
in it, otherwise a generated 'BYTES' cover with the game's name. Saved as assets/episode-art/nb-NNN-<title>.jpg; existing files are
never replaced (put your own picture there to override).

  python3 scripts/python/bytes_art.py            make any missing covers
  python3 scripts/python/bytes_art.py --dry-run  show what it would use
"""
import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import box_art  # noqa: E402
from bytes_info import cover_name  # noqa: E402
import share_cards  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
ART = REPO / "assets/episode-art"
SOURCES = REPO / "data/bytes-art-sources.json"
# Games the library files under their Japanese names (the show uses the English ones). Episode number -> file.
ALIASES = {
    12: "Akumajou Special - Boku Dracula-kun (Japan).png",
    21: "Heracles no Eikou II - Titan no Metsubou (Japan).png",
    29: "Dragon Ball Z II - Gekishin Freeza!! (Japan).png",
}


def candidates(title):
    """Names to look for, most specific first: the title, without notes in brackets, before a colon, before 'and' / '/'."""
    t = re.sub(r"\s*\((?:fan translation|[^)]*translat[^)]*)\)", "", title, flags=re.I).strip()
    out = [t, re.sub(r"\s*\([^)]*\)", "", t).strip(), re.split(r"\s*:\s*", t)[0], re.split(r"\s+and\s+|\s*/\s*", t)[0], re.sub(r"!$", "", t),
           re.sub(r"\s+and\s+", " ", t)]  # "Nuts and Milk" is filed as "Nuts & Milk"
    seen, res = set(), []
    for c in out:
        n = box_art.norm(c)
        if len(n) >= 4 and n not in seen:
            seen.add(n)
            res.append(n)
    return res


def index(names):
    """normalized game name -> clean box files (no hacks or translations), best region first (Japan, USA, then others)."""
    idx = {}
    for n in names:
        if re.search(r"\[[^\]]*\]|Beta|Proto|Sample|Translation|\(Pirate\)|Unl|Hack|Aftermarket|Virtual Console|e-Reader|Collection|Switch Online", n):
            continue
        base = re.sub(r",\s*(The|A)$", "", re.sub(r"\s*\([^)]*\)", "", n[:-4]))
        idx.setdefault(box_art.norm(base), []).append(n)
    rank = lambda n: (0 if "(Japan)" in n else 1 if "(USA)" in n else 2 if "(World)" in n else 3, len(n))
    return {k: sorted(v, key=rank) for k, v in idx.items()}


def find(title, idx):
    cands = candidates(title)
    for c in cands:
        if c in idx:
            return idx[c][0]
    for c in cands[:3]:  # a title that is the start of exactly one longer file name ("Downtown Special" / "Downtown Special - Kunio-kun ...")
        longer = [k for k in idx if k.startswith(c) and len(c) >= 10]
        if len(longer) == 1:
            return idx[longer[0]][0]
    return None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    f = REPO / "data/bytes-info.json"
    info = json.loads(f.read_text()) if f.exists() else {}
    todo = {n: v for n, v in info.items() if not (ART / f"{cover_name(n, v['title'])}.jpg").exists()}
    if not todo:
        print("Every Bytes episode already has a cover.")
        return 0
    idx = index(box_art.box_names()) if not a.dry_run or True else {}
    sources = json.loads(SOURCES.read_text()) if SOURCES.exists() else {}
    boxed = 0
    for n, v in todo.items():
        fname = ALIASES.get(int(n)) or find(v["title"], idx)
        print(f"   Bytes {int(n):03d} {v['title'][:50]}: " + (fname if fname else "no box art found, making a 'BYTES' cover"))
        if a.dry_run:
            continue
        out = ART / f"{cover_name(n, v['title'])}.jpg"
        if fname:
            data = urllib.request.urlopen(urllib.request.Request(box_art.RAW + urllib.parse.quote(fname), headers=box_art.UA), timeout=60).read()
            box_art.compose(data).save(out, "JPEG", quality=82, optimize=True)
            sources[n] = {"file": fname}
            boxed += 1
        else:
            share_cards.make_bytes_cover(v["title"], int(n), out)
            sources[n] = {"file": None}
    if not a.dry_run:
        SOURCES.write_text(json.dumps(dict(sorted(sources.items(), key=lambda kv: int(kv[0]))), indent=1) + "\n")
    print(f"{boxed} box scans, {len(todo) - boxed} generated covers." if not a.dry_run else "Dry run: nothing changed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
