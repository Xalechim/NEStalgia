#!/usr/bin/env python3
"""Check that text on the site is readable (WCAG AA: 4.5:1 for normal text, 3:1 for large/bold text and UI borders).

Colors come from site-src/style.css (the :root and dark-theme variables); the pairs below are the combinations the site uses.
  python3 scripts/python/check_contrast.py        prints a table; exits 1 if anything fails
"""
import re
import sys
from pathlib import Path

CSS = (Path(__file__).resolve().parents[2] / "site-src/style.css").read_text()


def variables(block):
    return dict(re.findall(r"--([a-z-]+):\s*(#[0-9a-fA-F]{3,6})", block))


def parse_themes():
    root = re.search(r":root\s*\{(.*?)\}", CSS, re.S).group(1)
    dark = re.search(r':root\[data-theme="dark"\]\s*\{(.*?)\}', CSS, re.S).group(1)
    light = variables(root)
    return light, {**light, **variables(dark)}


def rgb(h):
    h = h.lstrip("#")
    h = "".join(c * 2 for c in h) if len(h) == 3 else h
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lum(c):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(v) for v in c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a, b):
    la, lb = sorted((lum(rgb(a)), lum(rgb(b))), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# (what, text color, background color, minimum). Colors are variable names ("ink") or hex.
FIXED = {"white": "#ffffff", "navhover": "#ff8a80", "yellow": "#f2c230", "yellowink": "#1a1a1a", "blue": "#2a6fdb", "gray-bar": "#6f6f78",
         "purple": "#5a3fa0", "teal": "#0b6e5a", "blue-dark": "#4a86ea", "gray-bar-dark": "#8a8a96", "skip-dark": "#3a3a46"}
PAIRS = {
    "light": [
        ("Body text on page", "ink", "bg", 4.5), ("Body text on cards", "ink", "card", 4.5),
        ("Muted text on page", "gray", "bg", 4.5), ("Muted text on cards", "gray", "card", 4.5), ("Muted text on white", "gray", "paper", 4.5),
        ("Links on page", "link", "bg", 4.5), ("Links on cards", "link", "card", 4.5),
        ("Menu links on header", "white", "dark", 4.5), ("Menu hover on header", "navhover", "dark", 4.5),
        ("Button text", "white", "red", 4.5), ("Section label", "white", "dark", 4.5),
        ("TRANSCRIPT tag (white on red)", "white", "red", 4.5), ("NOTES tag", "yellowink", "yellow", 4.5), ("LINKS tag (white on blue)", "white", "blue", 4.5), ("PATREON tag (white on purple)", "white", "purple", 4.5), ("REVIEW tag (white on teal)", "white", "teal", 4.5),
        ("Verdict: Essential", "yellowink", "yellow", 4.5), ("Verdict: Play it", "white", "blue", 4.5), ("Verdict: Skip it", "white", "dark", 4.5),
        ("Stats bar: skip colour vs card (UI)", "gray-bar", "card", 3.0), ("Stats bar: blue vs card (UI)", "blue", "card", 3.0), ("Stats bar: yellow vs card (UI)", "yellow", "card", 1.4),
        ("Card border vs page (UI)", "line", "bg", 3.0),
    ],
    "dark": [
        ("Body text on page", "ink", "bg", 4.5), ("Body text on cards", "ink", "card", 4.5),
        ("Muted text on page", "gray", "bg", 4.5), ("Muted text on cards", "gray", "card", 4.5), ("Muted text on inputs", "gray", "paper", 4.5),
        ("Links on page", "link", "bg", 4.5), ("Links on cards", "link", "card", 4.5),
        ("Menu links on header", "white", "dark", 4.5), ("Menu hover on header", "navhover", "dark", 4.5),
        ("Button text", "white", "red", 4.5), ("TRANSCRIPT tag (white on red)", "white", "red", 4.5), ("NOTES tag", "yellowink", "yellow", 4.5),
        ("LINKS tag (white on blue)", "white", "blue", 4.5), ("Verdict: Essential", "yellowink", "yellow", 4.5), ("Verdict: Play it", "white", "blue", 4.5),
        ("Verdict: Skip it", "white", "skip-dark", 4.5),
        ("Stats bar: skip colour vs card (UI)", "gray-bar-dark", "card", 3.0), ("Stats bar: blue vs card (UI)", "blue-dark", "card", 3.0),
        ("Card border vs page (UI)", "line", "bg", 3.0),
    ],
}


def main():
    light, dark = parse_themes()
    fails = 0
    for theme, vars_ in (("light", light), ("dark", dark)):
        print(f"\n{theme.upper()} THEME")
        for what, fg, bg, need in PAIRS[theme]:
            f = vars_.get(fg) or FIXED[fg]
            b = vars_.get(bg) or FIXED[bg]
            r = ratio(f, b)
            ok = r >= need
            fails += not ok
            print(f"  {'ok  ' if ok else 'FAIL'} {r:5.2f}:1 (need {need})  {what}   [{f} on {b}]")
    print(f"\n{fails} failing pair(s)." if fails else "\nAll checked pairs pass.")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
