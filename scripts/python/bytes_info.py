#!/usr/bin/env python3
"""The list of NEStalgia Bytes episodes (the Patreon-only Famicom show), read from the episode spreadsheet.

Saved to data/bytes-info.json as {number: {"title", "published" (YYYY-MM-DD or ""), "patreon_url" ("" if unknown)}}.
Rows come from the spreadsheet's "Byte" season. A row with no number sits right after the one before it, and a typo'd number is
skipped. Episodes dated in the future are left out. (Bytes show notes are Patreon content and are not kept in this repo.)

To link a Bytes episode straight to its Patreon post, add a column whose header contains the word "Patreon" to the spreadsheet
and paste the post's address into the Byte rows.
  python3 scripts/python/bytes_info.py        refresh from the spreadsheet (needs internet)
"""
import csv
import io
import json
import re
import sys
import unicodedata
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "data/bytes-info.json"
MAX_NUMBER = 200  # a row numbered 300 is a typo, not episode 300


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()  # "Getsu Fūma Den" -> "Getsu Fuma Den"
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower().replace("'", "").replace("’", ""))).strip("-")


def cover_name(number, title):
    """File name (no extension) of a Bytes episode's cover in assets/episode-art, which is also its page address."""
    return f"nb-{int(number):03d}-{slug(title)[:60].strip('-')}"


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def clean_title(t):
    return re.sub(r"\s+", " ", (t or "").replace("\n", " ")).strip()


def parse_date(s):
    try:
        return datetime.strptime((s or "").strip(), "%m/%d/%Y").date()
    except ValueError:
        return None


def notes_titles(folder=None):
    """{number: title} from Bytes show-notes files, if a folder of them is given (none are kept in the repo any more)."""
    folder = folder or REPO / "episodes/bytes"
    out = {}
    for p in sorted(folder.glob("nb-*.md")) if folder.exists() else []:
        m = re.match(r"nb-(\d+)-", p.name)
        if not m:
            continue
        first = p.read_text().split("\n", 1)[0]
        t = re.sub(r"^#\s*(?:NB\s*)?\d+\s*[-–:]\s*", "", first).strip() if first.startswith("#") else ""
        out[int(m.group(1))] = t or p.stem.split("-", 2)[2].replace("-", " ").title()
    return out


def parse(text, notes=None, today=None):
    """Bytes episodes from the spreadsheet CSV text -> {str(number): info}."""
    today = today or date.today()
    notes = notes or {}
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return {}
    head = [h.strip().lower() for h in rows[0]]
    col = {k: head.index(k) for k in ("season", "ep #", "episode") if k in head}
    date_col = next((i for i, h in enumerate(head) if "publish date" in h), None)
    pat_col = next((i for i, h in enumerate(head) if "patreon" in h), None)
    by_title = {norm(t): n for n, t in notes.items()}
    out, last = {}, None
    for r in rows[1:]:
        try:
            season = r[col["season"]].strip().lower()
            is_byte = season == "byte" or (
                not season and r[col["ep #"]].strip().isdigit() and not any(c.strip() for c in r[4:9] + r[10:11]))  # Season left blank, no game info
            if not is_byte:
                continue
            title = clean_title(r[col["episode"]])
            raw = r[col["ep #"]].strip()
            if raw.isdigit() and 0 < int(raw) <= MAX_NUMBER:
                n = int(raw)
            elif not raw and last is not None and str(last + 1) not in out:
                n = last + 1  # a row left without a number sits right after the previous one
            else:
                n = by_title.get(norm(title))
            if n is None or not title:
                continue  # no usable number (and no matching notes file): can't place it
            d = parse_date(r[date_col]) if date_col is not None and date_col < len(r) else None
            if d and d > today:
                continue  # not out yet
            last = n
            out[str(n)] = {"title": title, "published": d.isoformat() if d else "",
                           "patreon_url": r[pat_col].strip() if pat_col is not None and pat_col < len(r) else ""}
        except (KeyError, IndexError, ValueError):
            continue
    for n, t in notes.items():  # episodes the sheet doesn't list (or lists under a wrong number)
        out.setdefault(str(n), {"title": t, "published": "", "patreon_url": ""})
    return dict(sorted(out.items(), key=lambda kv: int(kv[0])))


def refresh(log=print):
    import make_links as W
    import next_episode as N
    try:
        info = parse(W.http(N.SHEET_CSV, timeout=30).read().decode("utf-8"), notes_titles())
    except Exception as e:
        log(f"Couldn't read the episode spreadsheet for Bytes ({e}); keeping the saved list.")
        return False
    if len(info) < 20:
        log("The Bytes list looked wrong (too few episodes); keeping the saved list.")
        return False
    text = json.dumps(info, indent=1, ensure_ascii=False) + "\n"
    changed = not OUT.exists() or OUT.read_text() != text
    if changed:
        OUT.write_text(text)
    log(f"Bytes list: {len(info)} episodes" + (" (updated)." if changed else " (no changes)."))
    return changed


if __name__ == "__main__":
    refresh()
