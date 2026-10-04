#!/usr/bin/env python3
"""Read each game's developer, publisher, genre, release date and verdict from the episode spreadsheet.

Saved to data/game-info.json, which the website uses for the filters on the Episodes page.
  python3 scripts/game_info.py        refresh from the spreadsheet (needs internet; keeps the old file if it can't reach it)
"""
import csv
import io
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "data/game-info.json"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
VERDICTS = {"essential": "Essential", "play it": "Play it", "skip it": "Skip it"}
R = "(?:JP|NA|PAL|EU|AU|UK|KR|BR)"
REGION = re.compile(rf"({R}(?:/{R})*/?)$")


def names(cell):
    """'Taito\\nNatsume' or 'Pony CanyonJP\\nHAL LaboratoryNA' -> ['Taito', 'Natsume'] / ['Pony Canyon', 'HAL Laboratory']."""
    out, seen = [], set()
    for line in re.split(r"[\n;|,]", cell or ""):
        n = line.strip()
        m = REGION.search(n)
        if m and len(n) - len(m.group(1)) >= 2:  # the sheet tags regions on the end of a name: "NintendoPAL"
            n = n[: m.start()].strip()
        if n and n.lower() not in seen:
            seen.add(n.lower())
            out.append(n)
    return out


def release(cell):
    """'March 1991' or 'October 18, 1985' -> (1991, 'March'); (None, None) if unknown."""
    y = re.search(r"\b(19|20)\d\d\b", cell or "")
    m = next((mo for mo in MONTHS if (cell or "").lower().startswith(mo.lower())), None)
    return (int(y.group(0)) if y else None), m


def parse(text):
    """{episode number (str): info} for the numbered NES episodes in the spreadsheet CSV."""
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return {}
    head = [h.strip().lower() for h in rows[0]]
    c = {k: head.index(k) for k in ("season", "ep #", "episode", "release date", "developer 1", "developer 2", "publisher", "genre", "verdict", "comment") if k in head}
    out = {}
    for r in rows[1:]:
        try:
            if not r[c["season"]].strip().isdigit() or not r[c["ep #"]].strip().isdigit():
                continue  # Byte rows, specials, SNES episodes
            get = lambda k: r[c[k]].strip() if k in c and c[k] < len(r) else ""
            pubs = names(get("publisher"))
            devs = names(get("developer 1"))
            if get("developer 2") and get("developer 2") != get("publisher"):  # that column often just repeats the publisher
                devs += [d for d in names(get("developer 2")) if d.lower() not in {x.lower() for x in devs}]
            year, month = release(get("release date"))
            out[str(int(r[c["ep #"]]))] = {
                "title": get("episode"), "developers": devs, "publishers": pubs, "genre": get("genre"),
                "year": year, "month": month, "season": int(get("season")),
                "verdict": VERDICTS.get(get("verdict").lower(), ""),
                "comment": get("comment"),
            }
        except (KeyError, IndexError, ValueError):
            continue
    canon = {}  # one spelling per name across the whole sheet ("Tose" / "TOSE")
    for info in out.values():
        for k in ("developers", "publishers"):
            info[k] = [canon.setdefault(n.lower(), n) for n in info[k]]
    return out


def refresh(log=print):
    import next_episode as N  # same sheet, same address
    import make_links as W
    try:
        info = parse(W.http(N.SHEET_CSV, timeout=30).read().decode("utf-8"))
    except Exception as e:
        log(f"Couldn't read the episode spreadsheet ({e}); keeping the saved game info.")
        return False
    if len(info) < 100:  # an error page or a rearranged sheet: don't wipe good data
        log("The spreadsheet looked wrong (too few episodes); keeping the saved game info.")
        return False
    text = json.dumps(dict(sorted(info.items(), key=lambda kv: int(kv[0]))), indent=1, ensure_ascii=False) + "\n"
    changed = not OUT.exists() or OUT.read_text() != text
    if changed:
        OUT.write_text(text)
    log(f"Game info for {len(info)} episodes" + (" (updated)." if changed else " (no changes)."))
    return changed


if __name__ == "__main__":
    refresh()
