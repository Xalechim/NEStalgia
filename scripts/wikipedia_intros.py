#!/usr/bin/env python3
"""Give episodes that only have the Patreon boilerplate a real description, taken from the game's Wikipedia article.

Finds every episode whose feed description is nothing but the "Support NEStalgia directly..." boilerplate, looks up the
game on Wikipedia, and saves the article's opening paragraph in data/wikipedia-intros.json. The website then shows that
paragraph above the boilerplate (and uses it for search results and link previews). Your podcast feed is not changed.

  python3 scripts/wikipedia_intros.py              look up the episodes that are missing one
  python3 scripts/wikipedia_intros.py --dry-run    show which episodes it would look up
  python3 scripts/wikipedia_intros.py --episodes 446 447   only these
  python3 scripts/wikipedia_intros.py --retry      look again at games that had no article last time
  python3 scripts/wikipedia_intros.py --force      look everything up again
Wikipedia's text is free to reuse with credit (CC BY-SA); the site credits Wikipedia under each excerpt.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

REPO = Path(__file__).resolve().parent.parent
STORE = REPO / "data/wikipedia-intros.json"


def real_paragraphs(desc):
    """The description's paragraphs without the Patreon boilerplate."""
    return [p for p in (desc or "").split("\n\n") if p.strip() and not p.strip().lower().startswith("support nestalgia directly")]


def boilerplate_only(desc):
    return not real_paragraphs(desc)


def load():
    return json.loads(STORE.read_text()) if STORE.exists() else {}


def pick(episodes, store, only=None, retry=False, force=False):
    """Episodes (boilerplate-only descriptions) that still need a lookup."""
    out = []
    for r in episodes:
        if r["type"] != "episode" or r["number"] is None or "remaster" in r["feed_title"].lower():
            continue
        if only and r["number"] not in only:
            continue
        if not boilerplate_only(r["description"]):
            continue
        have = store.get(str(r["number"]))
        if have is not None and not force and (have.get("text") or not retry):
            continue
        out.append(r)
    return out


NES_WORDS = r"\bNES\b|Nintendo Entertainment System|Famicom"


def mentions_nes(page_title, lead):
    """True if the opening paragraph, or failing that anywhere in the article, says the game came out on the NES."""
    import re
    import urllib.parse

    import make_links as W
    if re.search(NES_WORDS, lead):
        return True
    q = urllib.parse.urlencode({"action": "query", "prop": "extracts", "explaintext": 1, "titles": page_title, "format": "json", "redirects": 1})
    try:
        pages = json.loads(W.http("https://en.wikipedia.org/w/api.php?" + q).read())["query"]["pages"]
        return any(re.search(NES_WORDS, p.get("extract", "")) for p in pages.values())
    except Exception:
        return True  # can't tell (network trouble): keep it, it is still about the right game


def lookup(title):
    """(intro dict or None). Titles naming two games ('A / B') are skipped: one article can't describe both."""
    import next_episode as N
    if "/" in title:
        return None
    game = title.title() if title.isupper() else title
    d = N.find_wikipedia(game)
    if not d or not d.get("extract"):
        return None
    if not mentions_nes(d.get("title", game), d["extract"]):
        return None  # an arcade/computer game of the same name, not the NES one: better blank than wrong
    return {"text": d["extract"].strip(), "title": d.get("title", game),
            "url": ((d.get("content_urls") or {}).get("desktop") or {}).get("page", ""), "about": d.get("description", "")}


def main(argv=None, log=print):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--retry", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--episodes", nargs="*", type=int)
    a = ap.parse_args(argv)
    episodes = json.loads((REPO / "data/episodes.json").read_text())
    store = load()
    todo = pick(episodes, store, set(a.episodes or []), a.retry, a.force)
    if not todo:
        log("Every episode that needs a Wikipedia intro already has one (or was checked).")
        return 0
    log(f"{len(todo)} episode(s) with only the Patreon boilerplate: " + ", ".join(str(r["number"]) for r in todo))
    if a.dry_run:
        return 0
    found = 0
    for r in todo:
        info = lookup(r["title"])
        store[str(r["number"])] = info or {"text": ""}
        found += bool(info)
        log(f"   {r['number']:03d} {r['title']}: " + (f"{info['title']} ({info['about']})" if info else "no Wikipedia article found, left blank"))
        STORE.write_text(json.dumps(dict(sorted(store.items(), key=lambda kv: int(kv[0]))), indent=1, ensure_ascii=False) + "\n")
    log(f"Done: {found} found, {len(todo) - found} blank.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
