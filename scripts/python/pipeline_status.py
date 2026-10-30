#!/usr/bin/env python3
"""Where every episode stands, and what is left to do. Needs nothing but Python (no packages), so any machine can run it.

  python3 scripts/python/pipeline_status.py                    a short summary
  python3 scripts/python/pipeline_status.py --board            the episodes being prepared or just published, one row each
  python3 scripts/python/pipeline_status.py --prep-queue       episodes with a transcript that still need a review and/or links, in the order to do them
  python3 scripts/python/pipeline_status.py --publish-check    is the newest episode in the feed on the website's data?  (prints ON_SITE / PENDING / WAITING)
  python3 scripts/python/pipeline_status.py --live-check N     is episode N on the live website?  (exit code 0 yes, 1 no)
  python3 scripts/python/pipeline_status.py --missing-links    episode numbers with a transcript but no Links tab
  python3 scripts/python/pipeline_status.py --links-ranges     the same, as ranges like 2-56, 94-167
  python3 scripts/python/pipeline_status.py --missing-offsets  episode numbers with a transcript but no measured audio shift
  python3 scripts/python/pipeline_status.py --has-key          exit code 0 if an Anthropic key is set up (needed to find links without Claude Code)

An episode goes through: transcript (you make it, any time before it comes out) -> review and links (Claude, ahead of time too)
-> published (automatic, the minute it is in the podcast feed). Review and links files for an episode that is not in the feed
yet are simply ignored by the website until it is.
"""
import glob
import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def transcript_numbers():
    nums = set()
    for p in glob.glob(str(REPO / "transcripts/[0-9]*.md")):
        m = re.match(r"(\d+)-", os.path.basename(p))
        if m:
            nums.add(int(m.group(1)))
    return sorted(nums)


def missing_links():
    have = {int(m.group(1)) for p in glob.glob(str(REPO / "data/links/*.json")) if (m := re.match(r"(\d+)-", os.path.basename(p)))}
    return [n for n in transcript_numbers() if n not in have]


def missing_offsets():
    f = REPO / "data/audio-offsets.json"
    have = set(json.loads(f.read_text())) if f.exists() else set()
    return [n for n in transcript_numbers() if str(n) not in have]


def has_key():
    return bool(os.environ.get("ANTHROPIC_API_KEY") or (Path.home() / ".config/nestalgia/anthropic_key").exists())


def ranges(nums):
    """[1,2,3,7] -> '1-3, 7'"""
    out, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        out.append(str(nums[i]) if i == j else f"{nums[i]}-{nums[j]}")
        i = j + 1
    return ", ".join(out)


SITE = "https://nestalgiacast.com"


def have(pattern):
    return bool(glob.glob(str(REPO / pattern)))


def episodes_data():
    f = REPO / "data/episodes.json"
    return json.loads(f.read_text()) if f.exists() else []


def published_numbers():
    return {r["number"] for r in episodes_data() if r.get("type") == "episode" and r.get("number")}


def readiness(n):
    """What exists for episode n: {'transcript','review','links','notes','offset'} as booleans."""
    offsets = json.loads((REPO / "data/audio-offsets.json").read_text()) if (REPO / "data/audio-offsets.json").exists() else {}
    return {
        "transcript": have(f"transcripts/{n:03d}-*.md") and have(f"transcripts/{n:03d}-*.vtt"),
        "review": have(f"reviews/{n:03d}-*.md"),
        "links": have(f"data/links/{n:03d}-*.json"),
        "notes": have(f"episodes/{n:03d}-*.md"),
        "offset": str(n) in offsets,
        "fingerprint": have(f"data/mix-fingerprints/{n:03d}.json"),
    }


def board_numbers(published, back=2):
    """The newest few published episodes, plus everything being prepared that isn't published yet."""
    nums = set()
    newest = sorted(published)[-back:]
    nums.update(newest)
    for pattern in ("transcripts/[0-9]*.md", "reviews/[0-9]*.md", "episodes/[0-9]*.md", "data/links/[0-9]*.json", "data/mix-fingerprints/[0-9]*.json"):
        for f in glob.glob(str(REPO / pattern)):
            m = re.match(r"(\d+)", os.path.basename(f))
            if m and published and int(m.group(1)) > max(published):
                nums.add(int(m.group(1)))
    return sorted(nums)


def board():
    """Markdown table of where each recent or upcoming episode stands (also used as the GitHub job summary)."""
    pub = published_numbers()
    rows = ["| Episode | On the site | Transcript | Review | Links | Click-to-play timing |", "|---|---|---|---|---|---|"]
    for n in board_numbers(pub):
        r = readiness(n)
        mark = lambda ok: "yes" if ok else "-"
        if r["offset"]:
            timing = "yes"
        elif n in pub:
            timing = "-"
        elif r["fingerprint"]:
            timing = "ready (measured when it comes out)"
        else:
            timing = "waiting for the transcript" if not r["transcript"] else "needs the mix fingerprint"
        rows.append(f"| {n} | {'**published**' if n in pub else 'not yet'} | {mark(r['transcript'])} | {mark(r['review'])} | {mark(r['links'])} | {timing} |")
    return "\n".join(rows)


def prep_queue():
    """[(episode, [missing items])] for episodes that have a transcript but lack a review and/or links. Published ones first (newest
    first, since a listener may be looking at them), then upcoming ones in the order they will come out."""
    pub = published_numbers()
    todo = []
    for n in transcript_numbers():
        r = readiness(n)
        if not r["transcript"]:
            continue
        missing = [k for k in ("review", "links") if not r[k]]
        if missing and (n in pub and n >= max(pub) - 8 or n not in pub):  # old back-catalogue episodes are handled separately
            todo.append((n, missing))
    now = [t for t in todo if t[0] in pub]
    later = [t for t in todo if t[0] not in pub]
    return sorted(now, reverse=True) + sorted(later)


def feed_newest():
    """(number, title, published datetime in UTC) of the newest numbered episode in the podcast feed, read through never-used addresses."""
    sys.path.insert(0, str(Path(__file__).parent))
    import build_episode_data as B
    from email.utils import parsedate_to_datetime
    best = None
    for it in B.fetch_feed().findall("item"):
        if B.is_scheduled_for_later(it):
            continue
        kind, num, name, _ = B.classify(it.findtext("title") or "")
        if kind == "episode" and num and (best is None or num > best[0]):
            when = parsedate_to_datetime(it.findtext("pubDate")) if it.findtext("pubDate") else None
            best = (num, name, when)
    return best


def origin_published():
    """Episode numbers on origin/main (what the website is built from), else this checkout."""
    import subprocess
    try:
        subprocess.run(["git", "-C", str(REPO), "fetch", "-q", "origin", "main"], check=True, timeout=60, capture_output=True)
        shown = subprocess.run(["git", "-C", str(REPO), "show", "origin/main:data/episodes.json"], check=True, capture_output=True, text=True, timeout=30).stdout
        return {r["number"] for r in json.loads(shown) if r.get("type") == "episode" and r.get("number")}
    except Exception:
        return published_numbers()


def publish_state(newest=None, on_site=None, now=None):
    """('PENDING' | 'ON_SITE' | 'WAITING', number, title, minutes since it came out) for the newest numbered episode in the feed.
    PENDING: in the feed but not yet on the website's data. ON_SITE: the site has it. WAITING: the feed lists no numbered episode."""
    from datetime import datetime, timezone
    newest = newest or feed_newest()
    if not newest:
        return "WAITING", None, "", None
    n, name, when = newest
    minutes = None
    if when is not None:
        minutes = (((now or datetime.now(timezone.utc)) - when).total_seconds()) / 60
    return ("ON_SITE" if n in (on_site if on_site is not None else origin_published()) else "PENDING"), n, name, minutes


def publish_check():
    """Prints one line: PENDING n title (N min ago) | ON_SITE n title (published today|earlier) | WAITING. Exit code 10 means PENDING."""
    from datetime import datetime, timezone
    from zoneinfo import ZoneInfo
    state, n, name, minutes = publish_state()
    if state == "WAITING":
        print("WAITING (the feed lists no numbered episode)")
        return 0
    if state == "PENDING":
        print(f"PENDING {n} {name} (out {minutes:.0f} min ago)" if minutes is not None else f"PENDING {n} {name}")
        return 10
    et = ZoneInfo("America/New_York")
    today = minutes is not None and (datetime.now(timezone.utc) - __import__("datetime").timedelta(minutes=minutes)).astimezone(et).date() == datetime.now(et).date()
    print(f"ON_SITE {n} {name} (published {'today' if today else 'earlier'})")
    return 0


def live_check(n):
    import urllib.request
    try:
        html_ = urllib.request.urlopen(urllib.request.Request(f"{SITE}/episodes/", headers={"User-Agent": "Mozilla/5.0", "Cache-Control": "no-cache"}), timeout=60).read().decode("utf-8", "replace")
    except Exception as e:
        print(f"couldn't load the website: {e}")
        return 2
    found = bool(re.search(rf"/episodes/{n:03d}-", html_))
    print(f"episode {n} is {'on' if found else 'NOT on'} the live website")
    return 0 if found else 1


def main(argv):
    if "--board" in argv:
        print(board())
    elif "--prep-queue" in argv:
        for n, missing in prep_queue():
            print(f"{n} {' '.join(missing)}")
    elif "--publish-check" in argv:
        return publish_check()
    elif "--live-check" in argv:
        return live_check(int(argv[argv.index("--live-check") + 1]))
    elif "--missing-links" in argv:
        print(" ".join(map(str, missing_links())))
    elif "--links-ranges" in argv:
        print(ranges(missing_links()))
    elif "--missing-offsets" in argv:
        print(" ".join(map(str, missing_offsets())))
    elif "--has-key" in argv:
        return 0 if has_key() else 1
    else:
        t, ml, mo = transcript_numbers(), missing_links(), missing_offsets()
        print(f"{len(t)} episodes have transcripts.")
        print(f"   {len(ml)} are missing a Links tab" + (f": {ranges(ml)}" if ml else "") + ".")
        print(f"   {len(mo)} are missing a measured audio shift (click-to-play)" + (f": {ranges(mo)}" if mo else "") + ".")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
