"""Read the site's articles from plain-text files in articles/.

Each article is one file, articles/<name>.md: a few lines of details between two lines of dashes, then the article written
in Markdown. See articles/README.md for the format. This turns a file into the same dictionary the site builder always used
(path, slug, title, date, author, tags, categories, image, excerpt, body as HTML), so nothing else in the build changes.

Besides ordinary Markdown (paragraphs, ## headings, **bold**, *italic*, [links](address), lists, > quotes), two things are understood:

  * Raw HTML is passed through untouched. Picture galleries, tables and note boxes are written as HTML.
  * A ranked entry in a countdown, written like this (the blank lines between paragraphs are normal Markdown):

        ::: rank 10 | Gyruss
        First paragraph of the write-up.

        Second paragraph.
        :::
"""
import html
import re
from pathlib import Path

import markdown

REPO = Path(__file__).resolve().parents[2]
ARTICLES_DIR = REPO / "articles"

META_KEYS = ("title", "slug", "path", "date", "author", "image", "excerpt")
LIST_KEYS = ("tags", "categories")
RANK = re.compile(r"^:::[ \t]*rank[ \t]+(\d+)[ \t]*\|[ \t]*(.+?)[ \t]*\n(.*?)\n:::[ \t]*$", re.S | re.M)


def md_to_html(text):
    """Markdown to HTML. No typographic changes: quotes, dashes and ampersands stay as typed."""
    return markdown.markdown(text.strip("\n"), extensions=[], output_format="html")


def rank_html(m):
    """A countdown entry: the heading '#10 - Title' then the write-up, in the figure/caption shape the countdown layout reads."""
    number, title, text = m.group(1), m.group(2), m.group(3)
    paras = re.sub(r"</p>\s*<p>", "</p><p>", md_to_html(text))
    return (f"<figure><figcaption>\n\n<p>#{number} - {html.escape(html.unescape(title), quote=False)}</p>"
            f"{paras}\n\n</figcaption></figure>")


def body_to_html(text):
    """Markdown body to HTML: rank blocks become countdown entries, everything else goes through Markdown."""
    out, pos = [], 0
    for m in RANK.finditer(text):
        before = text[pos:m.start()]
        if before.strip():
            out.append(md_to_html(before))
        out.append(rank_html(m))
        pos = m.end()
    rest = text[pos:]
    if rest.strip():
        out.append(md_to_html(rest))
    return "\n".join(out)


def split_front(raw):
    m = re.match(r"---[ \t]*\n(.*?)\n---[ \t]*\n?(.*)\Z", raw, re.S)
    if not m:
        raise ValueError("an article file must start with a block of details between two lines of '---'")
    meta = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError(f"bad line in the details block: {line!r}")
        meta[key.strip().lower()] = value.strip()
    return meta, m.group(2)


def parse_article(path):
    meta, body = split_front(Path(path).read_text(encoding="utf-8"))
    missing = [k for k in ("title", "slug", "path", "date") if not meta.get(k)]
    if missing:
        raise ValueError(f"{path}: missing {', '.join(missing)} in the details block")
    art = {k: meta.get(k, "") for k in META_KEYS}
    for k in LIST_KEYS:
        art[k] = [x.strip() for x in meta.get(k, "").split(",") if x.strip()]
    art["body"] = body_to_html(body)
    return art


def load_articles(directory=ARTICLES_DIR):
    """Every article file in the folder, as the dictionaries the builder uses. A README or any file starting with _ is skipped."""
    directory = Path(directory)
    if not directory.exists():
        return []
    found = []
    for f in sorted(directory.glob("*.md")):
        if f.name.lower() == "readme.md" or f.name.startswith("_"):
            continue
        try:
            found.append(parse_article(f))
        except Exception as e:  # say which file, so a typo is easy to find
            raise SystemExit(f"Could not read the article {f.name}: {e}")
    return found
