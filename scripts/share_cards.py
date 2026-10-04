"""Make the 1200x630 preview image shown when an episode page is shared (Discord, Twitter, iMessage, Slack).

Cover art on the left; episode number, title, publisher/year and a colored verdict stamp on the right.
"""
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
BG, BAR, RED = (27, 27, 33), (44, 44, 55), (214, 45, 32)
INK, MUTED, PINK = (236, 236, 241), (169, 169, 182), (255, 143, 132)
STAMPS = {  # verdict -> (fill, text color)
    "Essential": ((242, 194, 48), (26, 26, 26)),
    "Play it": ((42, 111, 219), (255, 255, 255)),
    "Skip it": ((111, 111, 120), (255, 255, 255)),
}
SANS = ["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", ("/System/Library/Fonts/Helvetica.ttc", 1), "Arial Bold.ttf"]
MONO = ["DejaVuSansMono-Bold.ttf", "LiberationMono-Bold.ttf", ("/System/Library/Fonts/Menlo.ttc", 1), "Courier New Bold.ttf"]


def font(candidates, size):
    for c in candidates:
        try:
            return ImageFont.truetype(c[0], size, index=c[1]) if isinstance(c, tuple) else ImageFont.truetype(c, size)
        except OSError:
            continue
    return ImageFont.load_default(size)  # scalable built-in font (Pillow 10.1+)


def wrap(draw, text, fnt, width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=fnt) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    return lines + ([line] if line else [])


def fit_title(draw, text, width, max_lines=3, sizes=(78, 68, 60, 52, 46, 40, 36), max_height=232):
    """Largest bold size at which the title fits in `width`, `max_lines` and `max_height` (so it never runs into the stamp)."""
    for size in sizes:
        f = font(SANS, size)
        lines = wrap(draw, text, f, width)
        if len(lines) <= max_lines and all(draw.textlength(l, font=f) <= width for l in lines) and len(lines) * size * 1.12 <= max_height:
            return f, lines
    f = font(SANS, sizes[-1])
    lines = wrap(draw, text, f, width)[:max_lines]
    lines[-1] = lines[-1].rstrip(" .,:;") + "…"
    return f, lines


def trimmed(logo_path):
    """The logo without its transparent margin."""
    logo = Image.open(logo_path).convert("RGBA")
    box = logo.getchannel("A").getbbox()
    return logo.crop(box) if box else logo


def top_bar(img, logo_path, right_text="nestalgiacast.com"):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 90], fill=BAR)
    d.rectangle([0, 90, W, 96], fill=RED)
    tile = Image.new("RGBA", (210, 66), (255, 255, 255, 255))
    mask = Image.new("L", tile.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, tile.width - 1, tile.height - 1], radius=10, fill=255)
    logo = trimmed(logo_path)
    logo.thumbnail((190, 50))
    tile.alpha_composite(logo, ((tile.width - logo.width) // 2, (tile.height - logo.height) // 2))
    img.paste(tile.convert("RGB"), (40, 12), mask)
    f = font(MONO, 28)
    d.text((W - 40, 46), right_text, font=f, fill=MUTED, anchor="rm")


def stamp(verdict, size=60):
    """A tilted rubber-stamp style label."""
    fill, ink = STAMPS[verdict]
    f = font(MONO, size)
    text = verdict.upper()
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    tw = int(probe.textlength(text, font=f))
    pad_x, pad_y = 30, 16
    w, h = tw + 2 * pad_x, size + 2 * pad_y
    layer = Image.new("RGBA", (w + 24, h + 24), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle([12 + 8, 12 + 8, 12 + w + 8, 12 + h + 8], radius=8, fill=(0, 0, 0, 255))  # hard shadow
    d.rounded_rectangle([12, 12, 12 + w, 12 + h], radius=8, fill=fill, outline=INK, width=5)
    d.text((12 + w / 2, 12 + h / 2 + 2), text, font=f, fill=ink, anchor="mm")
    return layer.rotate(5, resample=Image.BICUBIC, expand=True)


def make_episode_card(art_path, label, title, verdict, meta, logo_path, out_path):
    img = Image.new("RGB", (W, H), BG)
    top_bar(img, logo_path)
    d = ImageDraw.Draw(img)
    # cover art with a light frame and a hard shadow
    size, x0, y0 = 440, 56, 138
    art = Image.open(art_path).convert("RGB")
    art = art.resize((size, size), Image.LANCZOS)
    d.rectangle([x0 + 12, y0 + 12, x0 + size + 12 + 8, y0 + size + 12 + 8], fill=(0, 0, 0))
    d.rectangle([x0 - 8, y0 - 8, x0 + size + 8, y0 + size + 8], fill=INK)
    img.paste(art, (x0, y0))
    # text column
    tx, tw = 556, W - 556 - 56
    d.text((tx, y0 - 4), label.upper(), font=font(MONO, 34), fill=PINK)
    f, lines = fit_title(d, title, tw)
    y = y0 + 48
    for line in lines:
        d.text((tx, y), line, font=f, fill=INK)
        y += int(f.size * 1.12)
    if meta:
        d.text((tx, y + 10), meta, font=font(MONO, 28), fill=MUTED)
    if verdict in STAMPS:
        s = stamp(verdict)
        img.paste(s, (tx - 8, H - s.height - 28), s)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "JPEG", quality=84, optimize=True)


def make_default_card(logo_path, tagline, out_path):
    """The card used for the home page and every page without its own picture."""
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 14], fill=RED)
    d.rectangle([0, H - 14, W, H], fill=RED)
    logo = trimmed(logo_path)
    logo.thumbnail((760, 260))
    plate = Image.new("RGB", (logo.width + 70, logo.height + 56), (255, 255, 255))
    plate.paste(logo, (35, 28), logo)
    d.rectangle([(W - plate.width) // 2 + 10, 90 + 10, (W + plate.width) // 2 + 10, 90 + plate.height + 10], fill=(0, 0, 0))
    img.paste(plate, ((W - plate.width) // 2, 90))
    f, lines = fit_title(d, tagline, W - 220, max_lines=2, sizes=(54, 48, 42, 36))
    y = 90 + plate.height + 50
    for line in lines:
        d.text((W / 2, y), line, font=f, fill=INK, anchor="mt")
        y += int(f.size * 1.2)
    d.text((W / 2, H - 52), "nestalgiacast.com", font=font(MONO, 28), fill=MUTED, anchor="mm")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "JPEG", quality=86, optimize=True)


def clean_label(number, kind):
    if kind == "episode" and number is not None:
        return f"Episode {number}"
    return {"special": "Special episode", "bytes": "NEStalgia Bytes"}.get(kind, "NEStalgia")
