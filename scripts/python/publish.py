#!/usr/bin/env python3
"""Publish this Mac's changes to GitHub (and so to the website), then wait for the site to rebuild.

  python3 scripts/python/publish.py "Commit message" PATH [PATH ...] [--yes] [--no-wait]

Only the given paths are committed, so unrelated work in progress is never swept up. Shows what changed and asks first
(unless --yes). Needs the GitHub CLI (gh) to wait for the rebuild; without it, it just says the site updates in a few minutes.
"""
import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TRAILER = "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"


def git(*args, check=True):
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True, check=check)


def find_gh():
    return shutil.which("gh") or (str(Path.home() / "bin/gh") if (Path.home() / "bin/gh").exists() else None)


def wait_for_deploy(sha, timeout=420):
    gh = find_gh()
    if not gh:
        print("The website rebuilds in about 2 minutes.")
        return True
    print("Waiting for the website to rebuild ...", flush=True)
    end = time.time() + timeout
    while time.time() < end:
        r = subprocess.run([gh, "run", "list", "--workflow", "deploy-site.yml", "--limit", "8", "--json", "headSha,status,conclusion"],
                           capture_output=True, text=True, cwd=REPO)
        try:
            runs = [x for x in json.loads(r.stdout or "[]") if x["headSha"] == sha]
        except ValueError:
            runs = []
        if runs and runs[0]["status"] == "completed":
            if runs[0]["conclusion"] == "success":
                print("The website is updated.")
                return True
            print(f"The website rebuild finished with: {runs[0]['conclusion']}. Check the Actions tab on GitHub.")
            return False
        time.sleep(8)
    print("Still rebuilding; it should finish in a minute or two.")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("message")
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--no-wait", action="store_true")
    a = ap.parse_args()

    status = git("status", "--short", "--", *a.paths).stdout.rstrip()
    if not status:
        print("Nothing new to publish.")
        return 0
    lines = status.splitlines()
    print(f"What changed ({len(lines)} file(s)):")
    print("\n".join(lines[:25]) + (f"\n   ... and {len(lines) - 25} more" if len(lines) > 25 else ""))
    if not a.yes:
        if not sys.stdin.isatty() or not input("\nPublish these changes to the website now? (y/n): ").strip().lower().startswith("y"):
            print("Okay, nothing was published. The changes are saved on your Mac.")
            return 0
    git("add", "--", *a.paths)
    if git("diff", "--cached", "--quiet", check=False).returncode == 0:
        print("Nothing new to publish.")
        return 0
    git("commit", "-q", "-m", f"{a.message}\n\n{TRAILER}")
    pulled = git("pull", "--rebase", "--autostash", "-q", "origin", "main", check=False)
    if pulled.returncode != 0:
        print("Couldn't merge with GitHub's latest changes; nothing was uploaded. Details:\n" + pulled.stderr.strip())
        return 1
    pushed = git("push", "-q", "origin", "main", check=False)
    if pushed.returncode != 0:
        print("The upload failed (internet?). Your changes are committed on this Mac; run this again to retry.\n" + pushed.stderr.strip())
        return 1
    sha = git("rev-parse", "HEAD").stdout.strip()
    print("Uploaded to GitHub.")
    return 0 if a.no_wait else (0 if wait_for_deploy(sha) else 1)


if __name__ == "__main__":
    sys.exit(main())
