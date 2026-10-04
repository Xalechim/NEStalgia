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
# The thumbnail library has one folder per console. Games it files under their Japanese names (or on the Disk System / Game Boy)
# are pointed at by hand: episode number -> (console, file) or, for a collage, a list of such pairs.
REPOS = {"NES": "Nintendo_-_Nintendo_Entertainment_System", "FDS": "Nintendo_-_Family_Computer_Disk_System", "GB": "Nintendo_-_Game_Boy"}
RAW_BASE = "https://raw.githubusercontent.com/libretro-thumbnails/{}/master/Named_Boxarts/"
ALIASES = {
    4: ("NES", "Kekkyoku Nankyoku Daibouken (Japan).png"),                                   # Antarctic Adventure
    12: ("NES", "Akumajou Special - Boku Dracula-kun (Japan).png"),                          # Kid Dracula
    13: ("FDS", "All Night Nippon Super Mario Bros. (Japan) (Promo).png"),
    21: ("NES", "Heracles no Eikou II - Titan no Metsubou (Japan).png"),
    29: ("NES", "Dragon Ball Z II - Gekishin Freeza!! (Japan).png"),
    32: ("FDS", "Ai Senshi Nicol (Japan).png"),                                               # Love Warrior Nicol
    33: ("FDS", "Armana no Kiseki (Japan).png"),                                              # Miracle of Almana
    40: ("FDS", "Otocky (Japan).png"),
    44: ("FDS", "Cleopatra no Mahou (Japan).png"),                                            # The Magic Treasure of Cleopatra
    45: ("FDS", "Cocona World (Japan).png"),
    48: ("FDS", "Smash Ping Pong (Japan).png"),
    49: ("FDS", "Idol Hotline - Nakayama Miho no Tokimeki High School (Japan).png"),
    50: ("NES", "Wily _ Right no Rockboard - That's Paradise (Japan).png"),
    53: ("NES", "Getsu Fuuma Den (Japan).png"),
    52: [("GB", "Castlevania - The Adventure (USA).png"), ("GB", "Castlevania II - Belmont's Revenge (USA, Europe).png"),
         ("GB", "Castlevania Legends (USA, Europe) (SGB Enhanced).png")],                  # Castlevania Game Boy Games: all three
}


def fetch(console, fname):
    url = RAW_BASE.format(REPOS[console]) + urllib.parse.quote(fname)
    return urllib.request.urlopen(urllib.request.Request(url, headers=box_art.UA), timeout=60).read()


def trio_cover(boxes, big, small, number, size=1000):
    """Three box scans fanned out over a dark red 'castle' backdrop, with the title underneath."""
    from PIL import Image, ImageDraw, ImageFilter
    bg = Image.new("RGB", (size, size), (18, 10, 16))
    glow = Image.new("RGB", (size, size), (0, 0, 0))
    ImageDraw.Draw(glow).ellipse([size * 0.1, size * 0.02, size * 0.9, size * 0.7], fill=(140, 22, 28))
    bg = Image.blend(bg, glow.filter(ImageFilter.GaussianBlur(120)), 0.55)
    d = ImageDraw.Draw(bg)
    for i in range(0, size, 46):  # faint brick lines, like a castle wall
        d.line([(0, i), (size, i)], fill=(30, 16, 22), width=2)
    d.rectangle([0, 0, size, 22], fill=share_cards.RED)
    d.rectangle([0, size - 22, size, size], fill=share_cards.RED)

    def card(img, height, angle):
        img = img.convert("RGB")
        img = img.resize((round(img.width * height / img.height), height), Image.LANCZOS)
        framed = Image.new("RGB", (img.width + 14, img.height + 14), (236, 236, 241))
        framed.paste(img, (7, 7))
        layer = Image.new("RGBA", (framed.width + 60, framed.height + 60), (0, 0, 0, 0))
        shadow = Image.new("RGBA", framed.size, (0, 0, 0, 190))
        layer.paste(shadow, (38, 38))
        layer = layer.filter(ImageFilter.GaussianBlur(12))
        layer.paste(framed, (22, 22))
        return layer.rotate(angle, resample=Image.BICUBIC, expand=True)

    left, mid, right = (Image.open(__import__("io").BytesIO(b)) for b in boxes)
    for img, h, ang, cx, cy in ((left, 440, 10, 262, 400), (right, 440, -10, 738, 400), (mid, 540, 0, 500, 372)):
        c = card(img, h, ang)
        bg.paste(c, (cx - c.width // 2, cy - c.height // 2), c)
    d = ImageDraw.Draw(bg)
    d.text((size / 2, 748), f"NEStalgia BYTES {number:03d}", font=share_cards.font(share_cards.MONO, 34), fill=share_cards.PINK, anchor="mm")
    f, lines = share_cards.fit_title(d, big, size - 120, max_lines=2, sizes=(92, 80, 70), max_height=210)
    y = 790
    for line in lines:
        d.text((size / 2, y), line, font=f, fill=share_cards.INK, anchor="mt")
        y += int(f.size * 1.1)
    d.text((size / 2, size - 62), small.upper(), font=share_cards.font(share_cards.MONO, 30), fill=share_cards.MUTED, anchor="mm")
    return bg


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
        pick = ALIASES.get(int(n))
        if pick is None:
            found = find(v["title"], idx)
            pick = ("NES", found) if found else None
        shown = (", ".join(f for _, f in pick) if isinstance(pick, list) else pick[1]) if pick else None
        print(f"   Bytes {int(n):03d} {v['title'][:50]}: " + (shown if shown else "no box art found, making a 'BYTES' cover"))
        if a.dry_run:
            continue
        out = ART / f"{cover_name(n, v['title'])}.jpg"
        try:
            if isinstance(pick, list):
                pass
            elif pick:
                data_ = fetch(*pick)
        except Exception as e:  # a missing or unreachable scan must not stop the others
            print(f"      couldn't fetch {shown}: {e}; making a 'BYTES' cover instead")
            pick = None
        if isinstance(pick, list):  # several covers on one picture
            trio_cover([fetch(c, f) for c, f in pick], "CASTLEVANIA", "Game Boy games", int(n)).save(out, "JPEG", quality=86, optimize=True)
            sources[n] = {"files": [f for _, f in pick]}
            boxed += 1
        elif pick:
            box_art.compose(data_).save(out, "JPEG", quality=82, optimize=True)
            sources[n] = {"file": pick[1], "console": pick[0]}
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
