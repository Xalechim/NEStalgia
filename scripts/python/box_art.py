#!/usr/bin/env python3
"""Replace generic NEStalgia cover art with the game's NES box art.

Finds episodes whose cover is the plain NEStalgia logo (the feed's default picture), fetches the North American NES box
scan from the libretro thumbnail library, and saves it as a square cover (the box on a soft blurred backdrop).
Where each picture came from is recorded in data/box-art-sources.json.

  python3 scripts/python/box_art.py --dry-run      list the generic covers and the box art it would use
  python3 scripts/python/box_art.py                replace them
  python3 scripts/python/box_art.py --episodes 50 51 --file "Rygar (USA).png"   force a particular file for one episode
Box art belongs to its publishers; it is used here the way the rest of the episode art is.
"""
import argparse
import io
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

REPO = Path(__file__).resolve().parents[2]
SOURCES = REPO / "data/box-art-sources.json"
REPO_API = "https://api.github.com/repos/libretro-thumbnails/Nintendo_-_Nintendo_Entertainment_System/git/trees/master?recursive=1"
RAW = "https://raw.githubusercontent.com/libretro-thumbnails/Nintendo_-_Nintendo_Entertainment_System/master/Named_Boxarts/"
UA = {"User-Agent": "nestalgia-site (https://nestalgiacast.com)"}
GENERIC_REFERENCE = "assets/generic-cover-reference.jpg"  # a copy of the plain NEStalgia logo cover, for comparing against


def fingerprint(img):
    return np.asarray(img.convert("L").resize((24, 24)), dtype=float)


def is_generic(path, ref_fp, threshold=3.0):
    """True if this cover looks like the plain logo picture (mean grey-level difference from the reference is tiny)."""
    return float(np.abs(fingerprint(Image.open(path)) - ref_fp).mean()) < threshold


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def box_names():
    req = urllib.request.Request(REPO_API, headers=UA)
    tree = json.loads(urllib.request.urlopen(req, timeout=60).read())["tree"]
    return [t["path"].split("/", 1)[1] for t in tree if t["path"].startswith("Named_Boxarts/")]


def auto_match(title, names):
    """Best North American box for a title: an exact title, a clean 'Title (USA).png' (no hack/translation tags) preferred."""
    want = norm(re.sub(r"^(the|a)\s+", "", title.strip(), flags=re.I))
    best = None
    for n in names:
        if re.search(r"\[[^\]]*\]|e-Reader|GameCube|Virtual Console|Switch|Proto|Beta|Sample|\(Pirate\)|Translation", n):
            continue
        base = re.sub(r"\s*\((?:[^)]*)\)", "", n[:-4])  # drop (USA), (Rev 1), (1987-07)(Capcom)(US) ...
        base = re.sub(r",\s*(The|A)$", "", base)
        if norm(base) != want:
            continue
        score = (0 if "(USA)" in n else 1 if "(US)" in n or "(World)" in n else 2, len(n))
        if best is None or score < best[0]:
            best = (score, n)
    return best[1] if best else None


def compose(png_bytes, size=1000):
    """The box (whole, not cropped) centred on a blurred, slightly darkened copy of itself."""
    box = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    cover = box.copy()
    scale = size / min(cover.size)
    cover = cover.resize((round(cover.width * scale), round(cover.height * scale)), Image.LANCZOS)
    left, top = (cover.width - size) // 2, (cover.height - size) // 2
    bg = cover.crop((left, top, left + size, top + size)).filter(ImageFilter.GaussianBlur(28))
    bg = Image.blend(bg, Image.new("RGB", bg.size, (28, 28, 34)), 0.35)
    h = round(size * 0.94)
    fg = box.resize((round(box.width * h / box.height), h), Image.LANCZOS)
    bg.paste(fg, ((size - fg.width) // 2, (size - fg.height) // 2))
    return bg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--episodes", nargs="*", type=int)
    ap.add_argument("--file", help="exact file in the libretro Named_Boxarts folder (with --episodes, one episode)")
    a = ap.parse_args()

    ref = REPO / GENERIC_REFERENCE
    if not ref.exists():
        print(f"Missing {GENERIC_REFERENCE} (a copy of the plain logo cover).")
        return 1
    ref_fp = fingerprint(Image.open(ref))
    eps = [r for r in json.loads((REPO / "data/episodes.json").read_text()) if r["type"] == "episode" and r["number"] is not None and r.get("art")]
    sources = json.loads(SOURCES.read_text()) if SOURCES.exists() else {}
    todo = [r for r in eps if (a.episodes and r["number"] in a.episodes) or (not a.episodes and is_generic(REPO / r["art"], ref_fp))]
    if not todo:
        print("No generic covers found.")
        return 0
    names = box_names() if not a.file else []
    done = 0
    for r in todo:
        title = r["title"].title() if r["title"].isupper() else r["title"]
        fname = a.file if a.file else sources.get(str(r["number"]), {}).get("file") or auto_match(title, names)
        if not fname:
            print(f"   {r['number']:03d} {title}: no box art found; left as is")
            continue
        print(f"   {r['number']:03d} {title}  <-  {fname}")
        if a.dry_run:
            continue
        data = urllib.request.urlopen(urllib.request.Request(RAW + urllib.parse.quote(fname), headers=UA), timeout=60).read()
        compose(data).save(REPO / r["art"], "JPEG", quality=82, optimize=True)
        sources[str(r["number"])] = {"file": fname, "title": title}
        done += 1
    if done:
        SOURCES.write_text(json.dumps(dict(sorted(sources.items(), key=lambda kv: int(kv[0]))), indent=1, ensure_ascii=False) + "\n")
    print(f"Replaced {done} cover(s)." if not a.dry_run else "Dry run: nothing changed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
