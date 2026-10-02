#!/usr/bin/env python3
"""Check the podcast feed for new episodes and take care of everything, start to finish.

For each new episode this
  1. adds its information to the repo (data/episodes.json and .csv, cover art, the episode index),
  2. makes the transcript from your final mix (the MP3 in iCloud 10_NEStalgia/Mixes),
  3. measures the audio shift so clickable timestamps land correctly,
  4. (optional) finds the web links for the Links tab,
  5. commits only its own files, pushes to GitHub, and
  6. waits for the website to rebuild and checks that the new page is live.

What counts as "new": the first time it runs it records every episode already in the feed as handled, so it never tries to redo
your back catalog. After that, any episode that shows up in the feed is new. An episode whose final mix isn't in Mixes yet is kept on
a waiting list and picked up on a later run.

  python3 scripts/new_episodes.py                    check the feed and do everything
  python3 scripts/new_episodes.py --dry-run          show what it would do; change nothing
  python3 scripts/new_episodes.py --no-publish       do the work on this Mac but don't commit, push or wait
  python3 scripts/new_episodes.py --episodes 450     treat these as new even if already handled (also 450-452)
  python3 scripts/new_episodes.py --links            also find web links (needs an Anthropic key)
  python3 scripts/new_episodes.py --use-hosted-audio if there's no final mix, transcribe the host's audio (may include ads)
  python3 scripts/new_episodes.py --install-schedule run by itself every Friday morning (--uninstall-schedule to stop)

Log: ~/Library/Logs/nestalgia-new-episodes.log
"""
import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import build_episode_data as B  # noqa: E402
import run_episode as R  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
STATE = REPO / "data/pipeline-state.json"
LOG = Path.home() / "Library/Logs/nestalgia-new-episodes.log"
LOCK = Path.home() / ".nestalgia-new-episodes.lock"
SITE = "https://xalechim.github.io/NEStalgia"
KEY_FILE = Path.home() / ".config/nestalgia/anthropic_key"
PLIST = Path.home() / "Library/LaunchAgents/com.nestalgia.newepisodes.plist"
NS = {"i": "http://www.itunes.com/dtds/podcast-1.0.dtd"}


# ----------------------------------------------------------------------------- small helpers


def log(msg=""):
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(msg, flush=True)
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG, "a") as f:
            f.write(line + "\n")
    except OSError:
        pass


def tool_env():
    """PATH that works when launched by macOS on a schedule (no shell profile): the venv's ffmpeg, plus gh in ~/bin."""
    env = dict(os.environ)
    env["PATH"] = os.pathsep.join([str(Path(sys.executable).parent), str(Path.home() / "bin"), "/opt/homebrew/bin", "/usr/local/bin", env.get("PATH", "")])
    if KEY_FILE.exists() and not env.get("ANTHROPIC_API_KEY"):
        env["ANTHROPIC_API_KEY"] = KEY_FILE.read_text().strip()
    return env


def run(cmd, check=True, quiet=False, **kw):
    r = subprocess.run(cmd, cwd=REPO, env=tool_env(), text=True, capture_output=quiet, **kw)
    if check and r.returncode != 0:
        tail = ((r.stderr or "") + (r.stdout or ""))[-600:] if quiet else ""
        raise RuntimeError(f"command failed ({r.returncode}): {' '.join(map(str, cmd))}\n{tail}")
    return r


def git(*args, check=True):
    return run(["git", *args], check=check, quiet=True)


def notify(title, message):
    if sys.stdin.isatty():
        return
    try:
        subprocess.run(["osascript", "-e", f'display notification "{message}" with title "{title}"'], timeout=10)
    except Exception:
        pass


# ----------------------------------------------------------------------------- feed and state


def fetch_feed():
    """The feed's items, oldest first: dicts with guid, title, kind, number, name, key, published, audio_url."""
    raw = urllib.request.urlopen(urllib.request.Request(B.FEED, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read()
    items = []
    for it in ET.fromstring(raw).find("channel").findall("item"):
        title = (it.findtext("title") or "").strip()
        kind, num, name, key = B.classify(title)
        enc = it.find("enclosure")
        pub = it.findtext("pubDate")
        items.append({
            "guid": it.findtext("guid") or title,
            "title": B.html.unescape(title),
            "kind": kind, "number": num, "name": name, "key": key,
            "published": parsedate_to_datetime(pub).date().isoformat() if pub else "",
            "audio_url": enc.get("url") if enc is not None else None,
        })
    items.sort(key=lambda r: (r["published"], r["number"] or 0))
    return items


def load_state():
    return json.loads(STATE.read_text()) if STATE.exists() else None


def save_state(state):
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(state, indent=1, sort_keys=True) + "\n")


def parse_numbers(tokens):
    nums = []
    for tok in " ".join(tokens).replace(",", " ").split():
        m = re.fullmatch(r"(\d+)-(\d+)", tok)
        nums += list(range(int(m.group(1)), int(m.group(2)) + 1)) if m else ([int(tok)] if tok.isdigit() else [])
    return list(dict.fromkeys(nums))


def find_new(items, state, forced=()):
    """Items to process: unseen ones, plus anything on the waiting list, plus any episodes named explicitly."""
    seen = set(state["seen"])
    waiting = {int(n) for n in state.get("pending", {})}
    out = []
    for r in items:
        want = r["guid"] not in seen or (r["number"] in waiting) or (r["number"] in forced and r["kind"] == "episode")
        if want:
            out.append(r)
    return out


RECENT_DAYS = 21


def initial_baseline(items, has_transcript, forced=(), today=None):
    """First run: guids to mark as already handled. Recent numbered episodes that still lack a transcript are left out,
    so an episode that came out this week is picked up instead of being skipped along with the back catalog."""
    from datetime import date
    today = today or date.today()
    keep = set()
    for r in items:
        if r["kind"] == "episode" and r["number"] and r["published"] and not has_transcript(r["number"]):
            if (today - date.fromisoformat(r["published"])).days <= RECENT_DAYS:
                keep.add(r["guid"])
        if r["number"] in forced:
            keep.add(r["guid"])
    return [r["guid"] for r in items if r["guid"] not in keep]


def commit_message(done, waiting=()):
    nums = [r["number"] for r in done if r["kind"] == "episode" and r["number"]]
    if len(nums) == 1:
        r = next(x for x in done if x["number"] == nums[0])
        return f"Add episode {nums[0]:03d}: {r['name']} (transcript, data, cover art)"
    if nums:
        return f"Add episodes {nums[0]:03d}-{nums[-1]:03d} (transcripts, data, cover art)"
    wn = [r["number"] for r in waiting if r.get("number")]
    if wn:
        return "Add data for episode" + ("s " if len(wn) > 1 else " ") + ", ".join(f"{n:03d}" for n in wn) + " (waiting for the final mix)"
    return "Update from the podcast feed"


# ----------------------------------------------------------------------------- one episode


def transcript_exists(n):
    return bool(sorted(REPO.glob(f"transcripts/{n:03d}-*.md")))


def download(url, dest):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=120) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)


def handle_episode(r, args):
    """Returns (status, detail). status: done | waiting | failed."""
    n = r["number"]
    if transcript_exists(n) and not args.redo:
        return "done", "transcript already in the repo"
    mix = R.find_audio(n)
    hosted_tmp = None
    if mix:
        name = R.episode_name(n, mix)[0]
        audio, source = mix, "your final mix"
    elif args.use_hosted_audio and r["audio_url"]:
        name, source = r["name"], "the host's audio (may contain ads)"
        hosted_tmp = Path(tempfile.mkdtemp()) / f"hosted-{n}.mp3"
        log(f"   no final mix in Mixes; downloading the host's audio ...")
        download(r["audio_url"], hosted_tmp)
        audio = hosted_tmp
    else:
        return "waiting", f"no final mix named 'NES {n} - ....mp3' in Mixes yet"

    out = REPO / "transcripts" / (R.episode_name(n, mix)[1] if mix else f"{n:03d}-{R.slug(name)}")
    log(f"   transcribing from {source} ({audio.name}) ...")
    run([sys.executable, str(REPO / "scripts/transcribe.py"), str(audio), "--out", str(out), "--title", f"{n:03d} - {name}"])
    if mix:
        log("   measuring the audio shift ...")
        run([sys.executable, str(REPO / "scripts/audio_offsets.py"), str(n)], check=False)
    else:  # timestamps are already on the host's timeline
        f = REPO / "data/audio-offsets.json"
        d = json.loads(f.read_text()) if f.exists() else {}
        d[str(n)] = [[0, 0.0]]
        f.write_text(json.dumps(dict(sorted(d.items(), key=lambda kv: int(kv[0]))), indent=1) + "\n")
    if args.links:
        if tool_env().get("ANTHROPIC_API_KEY"):
            log("   finding web links ...")
            run([sys.executable, str(REPO / "scripts/make_links.py"), str(n)], check=False)
        else:
            log("   (skipping links: no Anthropic key set up; use /make-links in Claude Code instead)")
    if hosted_tmp:
        hosted_tmp.unlink(missing_ok=True)
    return "done", f"transcribed from {source}"


# ----------------------------------------------------------------------------- publish


def stage_and_commit(done, extra_numbers, waiting=()):
    paths = ["data", "assets/episode-art", "episodes/README.md"]
    for n in extra_numbers:
        paths += [f"transcripts/{n:03d}-*"]
    for p in paths:
        git("add", "--", p, check=False)
    if git("diff", "--cached", "--quiet", check=False).returncode == 0:
        return False
    git("commit", "-m", commit_message(done, waiting) + "\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>")
    return True


def push():
    git("pull", "--rebase", "-X", "theirs", "--autostash", "origin", "main")  # our files are freshly generated: they win a conflict
    git("push", "origin", "main")
    return git("rev-parse", "HEAD").stdout.strip()


def wait_for_deploy(sha, urls, timeout=600):
    """Wait for the 'Deploy website' run for this commit, then check the new pages respond. Needs the gh tool."""
    gh = Path.home() / "bin/gh"
    if not gh.exists():
        log("   (gh isn't installed, so I can't watch the website rebuild; it updates in a few minutes)")
        return
    deadline = time.time() + timeout
    run_id = None
    while time.time() < deadline:
        r = run([str(gh), "run", "list", "--workflow", "deploy-site.yml", "--limit", "5", "--json", "databaseId,status,conclusion,headSha"], check=False, quiet=True)
        try:
            runs = [x for x in json.loads(r.stdout or "[]") if x["headSha"] == sha]
        except json.JSONDecodeError:
            runs = []
        if runs:
            run_id, status, concl = runs[0]["databaseId"], runs[0]["status"], runs[0]["conclusion"]
            if status == "completed":
                log(f"   website rebuild: {concl}")
                break
        time.sleep(10)
    else:
        log("   the website rebuild is still running; check the Actions tab on GitHub in a few minutes")
        return
    for u in urls:
        try:
            code = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).status
        except Exception as e:
            code = getattr(e, "code", "error")
        log(f"   {u}  ->  {code}")


# ----------------------------------------------------------------------------- schedule (opt-in)


def plist_xml(py, script):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
 <key>Label</key><string>com.nestalgia.newepisodes</string>
 <key>ProgramArguments</key><array><string>{py}</string><string>{script}</string></array>
 <key>StartCalendarInterval</key><array>
  <dict><key>Weekday</key><integer>5</integer><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
  <dict><key>Weekday</key><integer>5</integer><key>Hour</key><integer>14</integer><key>Minute</key><integer>0</integer></dict>
  <dict><key>Weekday</key><integer>6</integer><key>Hour</key><integer>10</integer><key>Minute</key><integer>0</integer></dict>
 </array>
 <key>StandardOutPath</key><string>{LOG}</string>
 <key>StandardErrorPath</key><string>{LOG}</string>
 <key>RunAtLoad</key><false/>
</dict></plist>
"""


def install_schedule():
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    PLIST.write_text(plist_xml(sys.executable, Path(__file__).resolve()))
    uid = os.getuid()
    subprocess.run(["launchctl", "bootout", f"gui/{uid}", str(PLIST)], capture_output=True)
    r = subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", str(PLIST)], capture_output=True, text=True)
    if r.returncode != 0:
        print("Couldn't turn the schedule on:", r.stderr.strip())
        return 1
    print("Scheduled: it will check for new episodes on Fridays at 9:00 and 14:00 and Saturdays at 10:00 (when this Mac is awake or wakes).\n"
          f"Log: {LOG}\nTo stop: python3 scripts/new_episodes.py --uninstall-schedule")
    return 0


def uninstall_schedule():
    subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}", str(PLIST)], capture_output=True)
    PLIST.unlink(missing_ok=True)
    print("Schedule removed.")
    return 0


# ----------------------------------------------------------------------------- main


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-publish", action="store_true")
    ap.add_argument("--no-wait", action="store_true")
    ap.add_argument("--episodes", nargs="+", default=[], metavar="N")
    ap.add_argument("--redo", action="store_true", help="remake the transcript even if one exists")
    ap.add_argument("--links", action="store_true")
    ap.add_argument("--use-hosted-audio", action="store_true")
    ap.add_argument("--install-schedule", action="store_true")
    ap.add_argument("--uninstall-schedule", action="store_true")
    args = ap.parse_args()
    if args.install_schedule:
        return install_schedule()
    if args.uninstall_schedule:
        return uninstall_schedule()

    lock = open(LOCK, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        log("Another run is already in progress; stopping.")
        return 1

    log("=" * 60)
    log(f"Checking the podcast feed ({datetime.now():%A %b %-d, %-I:%M %p})")
    try:
        if not args.dry_run:
            git("pull", "--rebase", "--autostash", "origin", "main")
        items = fetch_feed()
    except Exception as e:
        log(f"Couldn't reach the feed or GitHub: {e}\nCheck your internet connection and try again.")
        notify("NEStalgia", "Couldn't check for new episodes (no internet?)")
        return 1

    state = load_state()
    forced = set(parse_numbers(args.episodes))
    if state is None:
        state = {"seen": [], "pending": {}}
        baseline = initial_baseline(items, transcript_exists, forced)
        log(f"First run: marking the {len(baseline)} episodes already handled (your back catalog) so they are left alone.")
        recent = len(items) - len(baseline)
        if recent:
            log(f"{recent} recent episode(s) without a transcript will be treated as new.")
        log("From now on, any NEW episode in the feed is processed automatically (use --episodes N to do an older one).")
        state["seen"] = baseline

    todo = find_new(items, state, forced)
    if not todo:
        log("No new episodes.")
        if not args.dry_run and STATE.exists() is False:
            save_state(state)
            if not args.no_publish and stage_and_commit([], []):
                push()
                log("Saved the starting point for tracking new episodes.")
        return 0

    log(f"{len(todo)} to process: " + ", ".join(f"{r['number']:03d} {r['name']}" if r['number'] else r['title'] for r in todo))
    if args.dry_run:
        for r in todo:
            if r["kind"] == "episode" and r["number"]:
                mix = R.find_audio(r["number"])
                has_tx = transcript_exists(r["number"])
                log(f"   {r['number']:03d}: " + ("transcript already exists" if has_tx and not args.redo else (f"would transcribe {mix.name}" if mix else "no final mix in Mixes yet: would wait" + (" (or use the host's audio)" if args.use_hosted_audio else ""))))
            else:
                log(f"   {r['title']}: {r['kind']}, would only add its data and cover art")
        log("Dry run: nothing was changed.")
        return 0

    results, failures = [], 0
    # First bring the repo's episode data and cover art up to date, so later steps (the audio-shift measurement) can find these episodes.
    log("\nAdding the new episodes' information and cover art ...")
    try:
        run([sys.executable, str(REPO / "scripts/update_from_feed.py")])
    except Exception as e:
        log(f"   couldn't refresh the data from the feed: {e}")
        failures += 1
    for r in todo:
        if r["kind"] != "episode" or not r["number"]:
            log(f"{r['title']}: not a numbered episode; adding its data and cover art only.")
            results.append((r, "done", "data and art only"))
            continue
        log(f"\nEpisode {r['number']:03d}: {r['name']}")
        try:
            status, detail = handle_episode(r, args)
        except Exception as e:
            status, detail = "failed", str(e).splitlines()[0]
            log(f"   FAILED: {e}")
            failures += 1
        log(f"   {status}: {detail}")
        results.append((r, status, detail))

    # again, now that transcripts exist: the episode flags and the index list them
    log("\nUpdating the episode data and index ...")
    try:
        run([sys.executable, str(REPO / "scripts/update_from_feed.py")])
    except Exception as e:
        log(f"   couldn't refresh the data from the feed: {e}")
        failures += 1

    state["seen"] = sorted(set(state["seen"]) | {r["guid"] for r, _, _ in results})
    state["pending"] = {k: v for k, v in state.get("pending", {}).items() if int(k) not in {r["number"] for r, s, _ in results if s == "done"}}
    for r, status, detail in results:
        if status in ("waiting", "failed"):
            state["pending"][str(r["number"])] = {"reason": detail, "since": state.get("pending", {}).get(str(r["number"]), {}).get("since", datetime.now().date().isoformat())}
    save_state(state)

    done = [r for r, s, _ in results if s == "done"]
    sha = None
    if args.no_publish:
        log("\n--no-publish: everything is saved on this Mac but not committed or uploaded.")
    else:
        try:
            waiting_items = [r for r, st, _ in results if st == "waiting"]
            if stage_and_commit(done, [r["number"] for r in done if r["number"]], waiting_items):
                log("\nUploading to GitHub ...")
                sha = push()
                log("   pushed.")
            else:
                log("\nNothing new to upload.")
        except Exception as e:
            log(f"\nCouldn't upload to GitHub: {e}\nYour work is saved; run this again to retry.")
            failures += 1

    if sha and not args.no_wait:
        pages = [f"{SITE}/episodes/{r['key']}/" for r in done if r["kind"] == "episode"]
        log("\nWaiting for the website to rebuild ...")
        wait_for_deploy(sha, pages)

    waiting = [r for r, s, _ in results if s == "waiting"]
    log("\nSummary:")
    for r, status, detail in results:
        log(f"   {r['number'] or '-'}  {r['name']}: {status} ({detail})")
    if waiting:
        log("   Waiting episodes are retried automatically next time this runs, once their final mix is in the Mixes folder.")
    notify("NEStalgia", f"{len(done)} new episode(s) done" + (f", {len(waiting)} waiting for a mix" if waiting else "") + (f", {failures} problem(s)" if failures else ""))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
