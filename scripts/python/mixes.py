"""Find an episode's final mix in the Mixes folder, whatever the file happens to be called.

Your files are named many ways: 'NES 401 - Game.mp3', 'NES 221 POW.mp3', 'NES 341 - Final Fantasy_mixdownV2.wav',
'NES285_PerfectFitmixdown.mp3', '001 - 10-Yard Fight (Remastered).mp3' ... All of them are found by episode number.
If several files share a number (a mixdown and a rough cut, V2, or even two different games), the best one wins.
"""
import difflib
import re
from pathlib import Path

MIXES = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/10_NEStalgia/Mixes"
AUDIO = {".mp3", ".wav", ".m4a", ".flac", ".aif", ".aiff"}


def _number_pattern(n):
    # "NES 40 ...", "NES040_...", "NES285_..." (not SNES, not NES 4012) or a bare "001 - ..."
    return re.compile(rf"^(?:NES\s*0*{n}(?!\d)|0*{n}\s*-)", re.I)


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _rank(path, n, title):
    stem = path.stem
    rest = re.sub(_number_pattern(n), "", stem)
    rest = re.sub(r"(?i)[_ ]?mixdown|v\d+$|\bv\d+\b|edit", "", rest)
    game = _norm(rest)
    want = _norm(title or "")
    # how well the file's game name fits the episode title (separates two different games filed under one number)
    fit = 0.0
    if want and game:
        fit = 1.0 if (game in want or want in game) else difflib.SequenceMatcher(None, game, want).ratio()
    versions = [int(v) for v in re.findall(r"(?i)v(\d+)", stem)]
    return (-round(fit, 1), "mixdown" not in stem.lower(), -(max(versions) if versions else 0), path.suffix.lower() != ".mp3", path.name)


def find_audio(n, title=None, folder=None):
    folder = Path(folder or MIXES)
    if not folder.exists():
        return None
    pat = _number_pattern(n)
    hits = [p for p in folder.iterdir() if p.suffix.lower() in AUDIO and pat.match(p.name)]
    return min(hits, key=lambda p: _rank(p, n, title)) if hits else None
