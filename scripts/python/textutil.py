"""Small text helpers shared by the scripts and the site build."""
import re

SMALL = {"a", "an", "and", "as", "at", "but", "by", "for", "in", "of", "on", "or", "the", "to", "vs", "vs."}
ROMAN = re.compile(r"^(?:I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII)$")
WORD = re.compile(r"[A-Za-z0-9]+(?:['’][A-Za-z]+)?")


def nice_case(s):
    """Tidy an ALL-CAPS game title ('MIKE TYSON'S PUNCH-OUT' -> "Mike Tyson's Punch-Out"). Titles that aren't all caps are left exactly as written."""
    if not s or not s.isupper():
        return s
    n = 0

    def fix(m):
        nonlocal n
        w, first = m.group(0), n == 0
        n += 1
        if ROMAN.match(w) and len(w) > 1:
            return w  # Gauntlet II, not Gauntlet Ii
        if not first and w.lower() in SMALL:
            return w.lower()
        return w[0].upper() + w[1:].lower()

    return WORD.sub(fix, s)
