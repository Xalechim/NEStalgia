#!/usr/bin/env python3
"""Publish a new episode the minute it appears in the podcast feed.

New episodes go live on Friday mornings, but not at a fixed time (the last eight came out between 1:55 and 6:26am Eastern), and
GitHub's own scheduler is too unreliable to hit a time window. So on Friday mornings this program is started early (by a schedule,
by the Claude "kick" routine pushing to kick/, or by hand), does one normal update, then keeps asking the feed every two minutes
(always through a feed address no cache has seen before) until a new numbered episode shows up. Then it runs the full update straight away:
the episode joins the Episodes list, the Up next box moves on to the following episode, click-to-play timing is measured, and the
workflow around it commits, rebuilds the site and announces the episode.

  python3 scripts/python/watch_feed.py                   automatic: watch on Friday before 9am Eastern, otherwise one update
  python3 scripts/python/watch_feed.py --once            one update, no waiting
  python3 scripts/python/watch_feed.py --watch           wait for a new episode no matter what day it is
  python3 scripts/python/watch_feed.py --every 60 --max-minutes 335

Only a numbered "NNN - Title" episode ends the wait. Anything the feed lists with a future date is ignored until its time comes.
When run by GitHub it reports how it ended in $GITHUB_OUTPUT: result=published | continue | gave-up | single.
"continue" means the time limit of one GitHub job ran out before 9am Eastern, so the workflow starts another watcher.
"""
import argparse
import html
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent))
import build_episode_data as B  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
EASTERN = ZoneInfo("America/New_York")
WATCH_UNTIL_HOUR = 9  # Friday, Eastern


def log(msg):
    print(f"{datetime.now(timezone.utc):%H:%M:%SZ}  {msg}", flush=True)


def git(*args, timeout=120):
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True, timeout=timeout)


def main_episodes(rows):
    return [r for r in rows if r.get("type") == "episode" and r.get("number")]


def known_state():
    """(episode numbers the site has, date the newest numbered episode was published) from origin/main plus this checkout."""
    texts = [(REPO / "data/episodes.json").read_text()]
    try:
        if git("fetch", "-q", "origin", "main").returncode == 0:
            shown = git("show", "origin/main:data/episodes.json")
            if shown.returncode == 0:
                texts.append(shown.stdout)
    except Exception:
        pass
    rows = [r for t in texts for r in main_episodes(json.loads(t))]
    return {r["number"] for r in rows}, max((r.get("published") or "" for r in rows), default="")


def new_main_episodes(channel, known_numbers, now=None):
    """[(number, name)] for numbered episodes the feed lists that the site doesn't have yet (ignoring ones dated in the future)."""
    found = []
    for it in channel.findall("item"):
        if B.is_scheduled_for_later(it, now):
            continue
        kind, num, name, _ = B.classify(html.unescape(it.findtext("title") or ""))
        if kind == "episode" and num and num not in known_numbers:
            found.append((num, name))
    return found


def watch_deadline(now):
    """The moment to stop waiting if `now` is on a Friday before 9am Eastern; otherwise None (no watching)."""
    et = now.astimezone(EASTERN)
    if et.weekday() != 4:
        return None
    end = et.replace(hour=WATCH_UNTIL_HOUR, minute=0, second=0, microsecond=0)
    return end.astimezone(timezone.utc) if et < end else None


def watch(fetch, known, update, now, sleep, stop_at, every=120, say=log):
    """Ask the feed every `every` seconds until a new numbered episode shows up (then run update() and return 'published')
    or `stop_at` passes (return 'waiting'). A feed that can't be read this time is simply tried again."""
    polls = 0
    while True:
        numbers, _ = known()
        new = []
        try:
            new = new_main_episodes(fetch(), numbers, now())
        except Exception as e:
            say(f"couldn't read the feed ({type(e).__name__}: {e}); trying again")
        polls += 1
        if new:
            say("new episode in the feed: " + ", ".join(f"{n} {name}" for n, name in new) + f" (after {polls} check{'s' if polls != 1 else ''})")
            update()
            return "published"
        if now() >= stop_at:
            say(f"no new episode after {polls} checks")
            return "waiting"
        sleep(max(1, min(every, (stop_at - now()).total_seconds())))


def update_pass():
    """The normal full update (feed, art, offsets, Up next, spreadsheet ...), starting from the latest main."""
    git("pull", "--rebase", "--autostash", "-q", "origin", "main")
    import update_from_feed
    update_from_feed.main()


def local_numbers():
    return {r["number"] for r in main_episodes(json.loads((REPO / "data/episodes.json").read_text()))}


def report(result):
    log(f"result: {result}")
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"result={result}\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--once", action="store_true", help="one update, no waiting")
    ap.add_argument("--watch", action="store_true", help="wait for a new episode on any day")
    ap.add_argument("--every", type=int, default=120, help="seconds between checks of the feed (default 120)")
    ap.add_argument("--max-minutes", type=int, default=335, help="longest one run may wait (a GitHub job is limited to 6 hours)")
    a = ap.parse_args(argv)

    now = datetime.now(timezone.utc)
    deadline = None if a.once else (now + timedelta(days=1) if a.watch else watch_deadline(now))
    if deadline and not a.watch:
        numbers, newest = known_state()
        if newest == now.astimezone(EASTERN).date().isoformat():
            log(f"today's episode ({max(numbers)}) is already published; one update is enough")
            deadline = None
    if deadline is None:
        update_pass()
        report("single")
        return 0

    stop_at = min(deadline, now + timedelta(minutes=a.max_minutes))
    log(f"watching the feed until {stop_at.astimezone(EASTERN):%a %-I:%M%p %Z} (checking every {a.every}s)")
    before = local_numbers()
    update_pass()  # the regular refresh happens first; the episode may already be there
    if local_numbers() - before:
        log("the new episode was already in the feed; published")
        report("published")
        return 0
    # one never-used feed address plus the plain one on each check (the host's cache freezes any address it has seen; see build_episode_data.py)
    result = watch(lambda: B.fetch_feed(B.feed_addresses(fresh=1)), known_state, update_pass, lambda: datetime.now(timezone.utc), time.sleep, stop_at, a.every)
    if result == "published":
        report("published")
    else:
        report("continue" if datetime.now(timezone.utc) < deadline else "gave-up")
    return 0


if __name__ == "__main__":
    sys.exit(main())
