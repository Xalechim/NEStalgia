#!/usr/bin/env python3
"""Find the web links for everything mentioned in an episode's transcript.

For each transcript in transcripts/ this:
  1. asks Claude to list everything the hosts referenced (games, people, companies,
     movies, events, ...), with the timestamp of the mention;
  2. asks Claude (with web search) for reference-site and other pages for the
     important ones, and fills in English Wikipedia pages automatically;
  3. VERIFIES every link before keeping it: Wikipedia pages must exist and not be
     disambiguation pages; every other URL must have come back from a web search
     and still load;
  4. writes data/links/NNN.json, which the website shows on the episode's Links tab.

  python3 scripts/make_links.py 446              one episode
  python3 scripts/make_links.py 401-410 446      a range and a single one
  python3 scripts/make_links.py --all            every transcript without links yet
  python3 scripts/make_links.py 446 --force      redo it (overwrites hand edits)
  python3 scripts/make_links.py 446 --dry-run    show what would be sent, spend nothing
  python3 scripts/make_links.py 446 --from-proposals file.json
                                                 skip the API: verify links from a file
  python3 scripts/make_links.py --check-proposals file.json
                                                 preview what each proposed Wikipedia title resolves to

API key: set ANTHROPIC_API_KEY, or put the key in ~/.config/nestalgia/anthropic_key.
"""
import argparse
import glob
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "data/links"
KEY_FILE = Path.home() / ".config/nestalgia/anthropic_key"
MODEL = "claude-opus-5-5"
UA = "Mozilla/5.0 (compatible; NEStalgiaLinks/1.0; +https://github.com/Xalechim/NEStalgia)"
WEB_SEARCH = {"type": "web_search_20260209", "name": "web_search", "max_uses": 25}
KINDS = ["game", "hardware", "company", "person", "team_or_league", "film_tv_music", "event_or_term", "website_or_article", "other"]
# Rough cost per million tokens for the progress report (claude-opus-5-5).
PRICE_IN, PRICE_OUT, PRICE_SEARCH = 4.0, 20.0, 0.01

EXTRACT_SYSTEM = """You are building the "Links" tab for one episode of NEStalgia, a podcast that covers every NES game \
released in North America, one game per episode, with three hosts (Mike, Sean and Joe).

You get an automatically generated transcript. List every specific thing the hosts referenced that a curious listener \
might want to look up, so that anything they mention has a link:
- the episode's main game first, then other games, consoles, accessories and franchises
- companies (developers, publishers, leagues, networks), people (designers, musicians, athletes, actors, hosts of shows)
- sports teams, movies, TV shows, music, books, real-world events, places, products
- articles, videos, websites or documents they explicitly mention (manuals, ads, interviews)
- named concepts or terms a listener may not know (for example a slang word or rule)

Rules:
- Use the correct canonical spelling. The transcript is machine-made and misspells names; fix them from your knowledge \
(for example "Travis Kelsey" is Travis Kelce).
- Merge duplicates. Ignore generic words, the hosts themselves, and the podcast.
- For each item give a one-sentence context that says why it came up, written for a listener, under 25 words.
- timestamp is the first mention as mm:ss (or h:mm:ss), copied from the transcript.
- wikipedia_title is your best guess of the exact English Wikipedia article title, including any disambiguation \
suffix such as "(video game)". Use "" when you doubt a Wikipedia article exists.
- search_query is a short web search that would find the best page for it.
- At most 45 items, most important first. Quality over padding."""

FIND_SYSTEM = """You find authoritative web pages for the things mentioned in a podcast episode about an NES game.

For each numbered item, search the web and return the best page(s). Order of preference:
1. gaming reference sites: hardcoregaming101.net, mobygames.com, gamefaqs.gamespot.com, nesdev.org, strategywiki.org, \
giantbomb.com, archive.org (game manuals and scans), the NES database sites, Nintendo/publisher pages
2. anything else reputable: official sites, news or magazine articles, interviews, a YouTube video of the exact thing referenced

English Wikipedia is handled separately, so do NOT search for or return Wikipedia pages.

Rules:
- Only return URLs that appeared in your web search results. Never write a URL from memory.
- Give the main game (item 0) up to 3 links; other items one link, or two if both are valuable.
- Skip an item rather than return a weak or off-topic page. You have a limited number of searches: spend them on the main \
game, other games, and anything not likely to have a Wikipedia page (articles, videos, local events, products).
- label is a short human-readable page title.

When done, reply with ONLY this JSON and nothing else:
{"results": [{"index": 0, "links": [{"url": "https://...", "label": "...", "source": "reference"}]}]}
Use source "reference" for gaming reference sites and "other" for everything else."""


# ----------------------------------------------------------------------------- helpers


def slug(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower().replace("'", "").replace("’", ""))).strip("-")


def norm_url(u):
    p = urllib.parse.urlparse(u.strip())
    return urllib.parse.urlunparse((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/") or "/", "", p.query, ""))


def http(url, method="GET", timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/json;q=0.9,*/*;q=0.5"}, method=method)
    return urllib.request.urlopen(req, timeout=timeout)


def wikipedia_page(title):
    """Return {'url','title','description'} for a real, non-disambiguation English Wikipedia page, else None."""
    if not title:
        return None
    api = "https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(title.replace(" ", "_"), safe="")
    data = None
    for attempt in range(3):  # retry temporary trouble; a real 404 means the page doesn't exist
        try:
            data = json.loads(http(api).read())
            break
        except urllib.error.HTTPError as e:
            if e.code in (404, 400):
                return None
        except Exception:
            pass
        time.sleep(1.5 * (attempt + 1))
    if data is None:
        return None
    if data.get("type") != "standard":  # disambiguation, missing, etc.
        return None
    url = (data.get("content_urls") or {}).get("desktop", {}).get("page")
    if not url:
        return None
    return {"url": url, "title": data.get("title", title), "description": data.get("description", "")}


def wikipedia_lookup(title, name, kind):
    """Exact title first; otherwise search Wikipedia and accept only a closely matching result."""
    page = wikipedia_page(title)
    if page and kind == "game" and "game" not in page["description"].lower():
        page = None  # e.g. "Days of Thunder (video game)" redirects to the movie; don't link a game to a film
    if page or not name:
        return page
    q = urllib.parse.urlencode({"action": "query", "list": "search", "srsearch": name + (" video game" if kind == "game" else ""), "srlimit": 8, "format": "json"})
    try:
        hits = json.loads(http("https://en.wikipedia.org/w/api.php?" + q).read())["query"]["search"]
    except Exception:
        return None
    want = re.sub(r"[^a-z0-9]", "", name.lower())
    for h in hits:
        got = re.sub(r"[^a-z0-9]", "", re.sub(r"\(.*?\)", "", h["title"]).lower())
        if got != want:
            continue
        page = wikipedia_page(h["title"])
        if page and (kind != "game" or "video game" in page["description"].lower() or "game" in page["description"].lower()):
            return page
    return None


def url_alive(url):
    """True if the page loads (or the site just blocks bots)."""
    for method in ("HEAD", "GET"):
        try:
            http(url, method=method).close()
            return True
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308):
                return True  # a redirect (older Pythons don't follow 308): the page exists
            if e.code in (401, 403, 405, 429, 999) and method == "GET":
                return True  # exists, but won't talk to scripts
            if e.code in (404, 410) or e.code >= 500:
                if method == "GET":
                    return False
        except Exception:
            if method == "GET":
                return False
    return False


def load_key():
    if not os.environ.get("ANTHROPIC_API_KEY") and KEY_FILE.exists():
        os.environ["ANTHROPIC_API_KEY"] = KEY_FILE.read_text().strip()
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def parse_numbers(args):
    nums = []
    for tok in " ".join(args).replace(",", " ").split():
        m = re.fullmatch(r"(\d+)-(\d+)", tok)
        if m:
            nums += range(int(m.group(1)), int(m.group(2)) + 1)
        elif tok.isdigit():
            nums.append(int(tok))
    return list(dict.fromkeys(nums))


def transcript_path(n):
    hits = sorted(glob.glob(str(REPO / f"transcripts/{n:03d}-*.md")))
    return Path(hits[0]) if hits else None


def match_episode(name, ep_titles):
    """Find your episode for a name, forgiving small spelling differences (Elliott / Elliot)."""
    import difflib
    k = re.sub(r"[^a-z0-9]", "", name.lower())
    if k in ep_titles:
        return ep_titles[k]
    close = difflib.get_close_matches(k, list(ep_titles), n=1, cutoff=0.93)
    return ep_titles[close[0]] if close else None


def episode_titles():
    f = REPO / "data/episodes.json"
    if not f.exists():
        return {}
    out = {}
    for r in json.loads(f.read_text()):
        out.setdefault(re.sub(r"[^a-z0-9]", "", r["title"].lower()), r)
    return out


# ----------------------------------------------------------------------------- model calls


def create(client, **kw):
    """messages.create with the server-side refusal fallback; plain call if the API doesn't accept that."""
    try:
        return client.messages.create(
            extra_headers={"anthropic-beta": "server-side-fallback-2026-07-01"}, extra_body={"fallbacks": "default"}, **kw
        )
    except Exception as e:
        if type(e).__name__ == "BadRequestError" and "fallback" in str(e).lower():
            return client.messages.create(**kw)
        raise


def text_of(resp):
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


def check_stop(resp, what):
    if resp.stop_reason == "refusal":
        raise RuntimeError(f"{what}: the model declined this request ({getattr(resp, 'stop_details', None)})")
    if resp.stop_reason == "max_tokens":
        raise RuntimeError(f"{what}: the answer was cut off (max_tokens); try again or shorten the transcript")


EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "kind": {"type": "string", "enum": KINDS},
                    "context": {"type": "string"},
                    "timestamp": {"type": "string"},
                    "wikipedia_title": {"type": "string"},
                    "search_query": {"type": "string"},
                },
                "required": ["name", "kind", "context", "timestamp", "wikipedia_title", "search_query"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["items"],
    "additionalProperties": False,
}


def extract_items(client, title, transcript, usage):
    resp = create(
        client,
        model=MODEL,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": EXTRACT_SCHEMA}},
        system=EXTRACT_SYSTEM,
        messages=[{"role": "user", "content": f"Episode: {title}\n\nTranscript:\n\n{transcript}"}],
    )
    check_stop(resp, "listing references")
    usage.add(resp)
    return json.loads(text_of(resp))["items"]


def find_links(client, title, items, usage, max_continuations=6):
    """Web-search pass. Returns ({index: [link,...]}, set of every URL the searches returned)."""
    listing = json.dumps(
        [{"index": i, "name": it["name"], "kind": it["kind"], "context": it["context"], "search_query": it["search_query"]}
         for i, it in enumerate(items)],
        indent=1,
    )
    messages = [{"role": "user", "content": f"Episode: {title}\n\nItems:\n{listing}"}]
    seen = set()
    resp = None
    for _ in range(max_continuations):
        resp = create(client, model=MODEL, max_tokens=16000, thinking={"type": "adaptive"}, output_config={"effort": "medium"},
                      system=FIND_SYSTEM, tools=[WEB_SEARCH], messages=messages)
        usage.add(resp)
        for b in resp.content:
            if getattr(b, "type", "") == "web_search_tool_result" and isinstance(b.content, list):
                for r in b.content:
                    if getattr(r, "url", None):
                        seen.add(norm_url(r.url))
        if resp.stop_reason != "pause_turn":
            break
        messages = [messages[0], {"role": "assistant", "content": resp.content}]  # server tool paused; resume
    check_stop(resp, "finding links")
    return parse_results(text_of(resp)), seen


def parse_results(text):
    """Pull the {"results": [...]} JSON out of the model's final message (it may be fenced or wrapped in prose)."""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return {}
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}
    out = {}
    for r in data.get("results", []):
        if isinstance(r, dict) and isinstance(r.get("index"), int):
            out[r["index"]] = [l for l in r.get("links", []) if isinstance(l, dict) and l.get("url")]
    return out


class Usage:
    def __init__(self):
        self.inp = self.out = self.searches = 0

    def add(self, resp):
        u = resp.usage
        self.inp += (u.input_tokens or 0) + (getattr(u, "cache_creation_input_tokens", 0) or 0)
        self.out += u.output_tokens or 0
        st = getattr(u, "server_tool_use", None)
        self.searches += (getattr(st, "web_search_requests", 0) or 0) if st else 0

    @property
    def dollars(self):
        return self.inp / 1e6 * PRICE_IN + self.out / 1e6 * PRICE_OUT + self.searches * PRICE_SEARCH


# ----------------------------------------------------------------------------- verification


def finalize(items, found, searched, ep_titles, log=print, allow_internal=False):
    """Turn model proposals into verified items. Nothing unverified gets through."""
    result, dropped = [], 0
    for i, it in enumerate(items):
        links = []
        wp = wikipedia_lookup(it.get("wikipedia_title", ""), it["name"] if it.get("wikipedia_title") else "", it["kind"])
        if wp:
            links.append({"url": wp["url"], "label": f"Wikipedia: {wp['title']}", "source": "wikipedia", "note": wp["description"]})
        for l in found.get(i, []):
            url = l["url"].strip()
            if url.startswith("{BASE}/") and allow_internal:  # an internal page on this site (proposals files only)
                links.append({"url": url, "label": l.get("label", url), "source": "site"})
                continue
            host = urllib.parse.urlparse(url).netloc.lower()
            if host.endswith("wikipedia.org"):
                continue  # Wikipedia only via the verified path above
            if searched is not None and norm_url(url) not in searched:
                dropped += 1
                log(f"   dropped (not in search results): {url}")
                continue
            if not url_alive(url):
                dropped += 1
                log(f"   dropped (dead link): {url}")
                continue
            links.append({"url": url, "label": (l.get("label") or host)[:120], "source": l.get("source", "other")})
        ep = match_episode(it["name"], ep_titles)
        entry = {
            "name": it["name"],
            "kind": it["kind"] if it["kind"] in KINDS else "other",
            "description": it["context"],
            "timestamp": it["timestamp"],
            "links": links,
        }
        if ep and ep.get("art"):
            entry["episode_key"] = Path(ep["art"]).stem
            entry["episode_title"] = ep["title"]
        if links or entry.get("episode_key"):
            result.append(entry)
    return result, dropped


# ----------------------------------------------------------------------------- one episode


def do_episode(n, args, client, ep_titles):
    tp = transcript_path(n)
    if not tp:
        print(f"Episode {n}: no transcript in transcripts/, skipping.")
        return False
    text = tp.read_text()
    title = text.splitlines()[0].lstrip("# ").strip()
    digest = hashlib.sha1(text.encode()).hexdigest()[:12]
    out = OUT / f"{n:03d}.json"
    if out.exists() and not args.force:
        old = json.loads(out.read_text())
        if old.get("transcript_hash") == digest:
            print(f"Episode {n}: links already made for this transcript (use --force to redo).")
            return True
        print(f"Episode {n}: the transcript changed since the links were made; redoing.")

    # The transcript, minus the header lines, is what Claude reads.
    body = "\n".join(l for l in text.splitlines() if l.startswith("**") or re.match(r"^\[\d+:\d\d", l))
    print(f"\nEpisode {title}: {len(body.split())} words")
    if args.dry_run:
        print(f"   dry run: would send about {len(body) // 4:,} tokens to {MODEL}; no API call made.")
        return True

    usage = Usage()
    if args.from_proposals:
        prop = json.loads(Path(args.from_proposals).read_text())
        items, found = prop["items"], {int(k): v for k, v in prop.get("found", {}).items()}
        # A proposals file can list every URL its web searches returned ("searched_urls"); if so, links must be in it, exactly
        # like the API path. Without the list, links are only checked live.
        searched = {norm_url(u) for u in prop["searched_urls"]} if prop.get("searched_urls") else None
        method = prop.get("method", "proposals file")
    else:
        print("   1/3 listing what was mentioned ...")
        items = extract_items(client, title, body, usage)
        print(f"       {len(items)} things found; 2/3 searching the web ...")
        found, searched = find_links(client, title, items, usage)
        method = "claude-api"
    print("   3/3 checking every link ...")
    verified, dropped = finalize(items, found, searched, ep_titles, allow_internal=bool(args.from_proposals))
    for it in verified:  # an episode doesn't need a link to itself
        if it.get("episode_key", "").startswith(f"{n:03d}-"):
            it.pop("episode_key"); it.pop("episode_title", None)
    verified = [it for it in verified if it["links"] or it.get("episode_key")]
    n_links = sum(len(i["links"]) for i in verified)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "episode": n, "title": title, "generated": date.today().isoformat(), "model": MODEL if method == "claude-api" else None,
        "method": method, "transcript_hash": digest, "items": verified,
    }, indent=2, ensure_ascii=False) + "\n")
    cost = f", about ${usage.dollars:.2f}" if usage.inp else ""
    print(f"   done: {len(verified)} items, {n_links} verified links, {dropped} dropped{cost} -> data/links/{n:03d}.json")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("numbers", nargs="*")
    ap.add_argument("--all", action="store_true", help="every transcript that has no links yet")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--from-proposals", metavar="FILE")
    ap.add_argument("--check-proposals", metavar="FILE", help="show what each proposed Wikipedia title resolves to; writes nothing")
    args = ap.parse_args()

    if args.check_proposals:
        for it in json.loads(Path(args.check_proposals).read_text())["items"]:
            if not it.get("wikipedia_title"):
                print(f"  -    {it['name'][:36]:36} (no Wikipedia page proposed)")
                continue
            w = wikipedia_lookup(it["wikipedia_title"], it["name"], it["kind"])
            print(f"  {'OK ' if w else 'NO '}  {it['name'][:36]:36} " + (f"-> {w['title']} :: {w['description'][:60]}" if w else f"'{it['wikipedia_title']}' not found / not a {it['kind']} page"))
        return 0

    nums = parse_numbers(args.numbers)
    if args.all:
        have = {int(p.stem) for p in OUT.glob("*.json")} if OUT.exists() else set()
        nums = [int(Path(p).name[:3]) for p in sorted(glob.glob(str(REPO / "transcripts/[0-9]*.md"))) if int(Path(p).name[:3]) not in have]
    if not nums:
        print("Nothing to do. Give episode numbers (446, 401-410) or --all.")
        return 1

    client = None
    if not args.dry_run and not args.from_proposals:
        if not load_key():
            print("No Anthropic API key found.\n"
                  "  Put your key in the file  ~/.config/nestalgia/anthropic_key  (or set ANTHROPIC_API_KEY).\n"
                  "  See scripts/HOW-TO-MAKE-A-TRANSCRIPT.md, 'Finding links'.")
            return 1
        import anthropic

        client = anthropic.Anthropic()

    ep_titles = episode_titles()
    ok = 0
    for n in nums:
        try:
            ok += bool(do_episode(n, args, client, ep_titles))
        except Exception as e:  # keep a batch going
            print(f"Episode {n}: failed: {type(e).__name__}: {e}")
    print(f"\nFinished: {ok} of {len(nums)} episodes.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
