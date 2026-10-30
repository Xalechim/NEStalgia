#!/usr/bin/env python3
"""The Friday-morning second clock: make sure the website's update is running when a new episode is due, whatever GitHub's scheduler does.

GitHub skips and delays scheduled runs, so a Claude routine runs this every hour early on Friday mornings. It needs nothing but Python.
It looks at the feed (through never-used addresses, so no cache can hide an episode) and at GitHub, and decides:

  * the newest episode is in the feed but not on the website's data  ->  kick (push a change in kick/, which starts the update workflow)
  * it is Friday before 9am Eastern, today's episode isn't out yet, and no "Update site" run is going  ->  kick, to start a watcher
  * anything else (the episode is on the site, or a run is already waiting for it)  ->  do nothing

A push is the one trigger GitHub never drops, which is the point. Prints one line saying what it decided.

  python3 scripts/python/clock.py             decide, and kick if needed
  python3 scripts/python/clock.py --dry-run   decide and say so, but change nothing
"""
import json
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent))
import pipeline_status as P  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
EASTERN = ZoneInfo("America/New_York")
RUNS = "https://api.github.com/repos/Xalechim/NEStalgia/actions/workflows/update-site.yml/runs?per_page=5"
PENDING_GRACE_MINUTES = 8  # a run that is already going gets this long to publish an episode that only just came out


def update_running():
    """True / False if GitHub says an 'Update site' run is going or waiting; None if GitHub can't be asked (then we assume not)."""
    try:
        req = urllib.request.Request(RUNS, headers={"User-Agent": "nestalgia-clock", "Accept": "application/vnd.github+json"})
        runs = json.loads(urllib.request.urlopen(req, timeout=30).read())["workflow_runs"]
    except Exception:
        return None
    return any(r.get("status") in ("in_progress", "queued", "waiting", "pending") for r in runs)


def in_watch_window(now):
    et = now.astimezone(EASTERN)
    return et.weekday() == 4 and et.hour < 9


def decide(state, number, minutes, running, now):
    """(kick?, reason). Pure, so it can be tested."""
    if state == "PENDING":
        if running and minutes is not None and minutes < PENDING_GRACE_MINUTES:
            return False, f"episode {number} only just came out ({minutes:.0f} min ago) and an update is already running"
        return True, f"episode {number} is in the feed but not on the website's data"
    if in_watch_window(now) and state in ("ON_SITE", "WAITING"):
        et = now.astimezone(EASTERN)
        out_today = minutes is not None and minutes < (et.hour * 60 + et.minute + 1)  # came out since midnight Eastern
        if not out_today and not running:
            return True, "it is Friday morning, today's episode isn't out yet and no update is running to wait for it"
    return False, "the site is up to date" if state == "ON_SITE" else "an update is already running" if running else "nothing to do"


def kick(reason, now):
    f = REPO / "kick/last-kick.txt"
    f.parent.mkdir(exist_ok=True)
    f.write_text(f"{now:%Y-%m-%dT%H:%M:%SZ} {reason}\n")
    run = lambda *a: subprocess.run(["git", "-C", str(REPO), *a], capture_output=True, text=True)
    if not run("config", "user.name").stdout.strip():  # a fresh sandbox may have no git identity
        run("config", "user.name", "NEStalgia clock")
        run("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    run("add", "kick/last-kick.txt")
    run("commit", "-m", f"Kick the site update: {reason}")
    for _ in range(3):
        run("pull", "--rebase", "-X", "theirs", "--autostash", "-q", "origin", "main")
        pushed = run("push", "origin", "HEAD:main")
        if pushed.returncode == 0:
            return True
    print(pushed.stderr.strip())
    return False


def main(argv):
    now = datetime.now(timezone.utc)
    subprocess.run(["git", "-C", str(REPO), "pull", "--rebase", "--autostash", "-q", "origin", "main"], capture_output=True)
    state, number, title, minutes = P.publish_state()
    running = update_running()
    go, reason = decide(state, number, minutes, bool(running), now)
    where = f"newest episode in the feed: {number} {title}" if number else "no numbered episode in the feed"
    print(f"{now:%H:%MZ} {state}; {where}; update running: {'unknown' if running is None else 'yes' if running else 'no'}")
    if not go:
        print(f"NO KICK: {reason}")
        return 0
    if "--dry-run" in argv:
        print(f"WOULD KICK: {reason}")
        return 0
    print(("KICKED: " if kick(reason, now) else "KICK FAILED (couldn't push): ") + reason)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
