#!/usr/bin/env python3
"""Offline tests for watch_feed.py and the "don't publish early" rule (no network, no git). Run:  python3 scripts/python/tests/test_watch_feed.py"""
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_episode_data as B
import watch_feed as W

UTC = timezone.utc


def channel(*items):
    """items: (title, pubDate string)"""
    body = "".join(f"<item><title>{t}</title><pubDate>{d}</pubDate></item>" for t, d in items)
    return ET.fromstring(f"<channel>{body}</channel>")


def main():
    now = datetime(2026, 10, 30, 7, 5, tzinfo=UTC)  # Friday 3:05am Eastern (daylight time)
    out = "Fri, 30 Oct 2026 07:00:00 GMT"

    # --- what counts as a new episode
    ch = channel(("452 - Totally Rad", out), ("451 - Power Blade", "Fri, 23 Oct 2026 05:55:00 GMT"))
    assert W.new_main_episodes(ch, {451}, now) == [(452, "Totally Rad")]
    assert W.new_main_episodes(ch, {451, 452}, now) == []                       # already on the site
    assert W.new_main_episodes(channel(("NEStalgia Bytes 57 - Foo", out)), set(), now) == []      # Bytes don't count
    assert W.new_main_episodes(channel(("Special 7 - Best of 1991", out)), set(), now) == []      # neither do specials
    assert W.new_main_episodes(channel(("NES 452 - Totally Rad", out)), set(), now) == [(452, "Totally Rad")]
    # a scheduled episode is not published before its time (the "don't publish until it is on the feed" rule)
    future = channel(("453 - Whomp Em", "Fri, 06 Nov 2026 07:00:00 GMT"))
    assert W.new_main_episodes(future, {452}, now) == []
    assert W.new_main_episodes(future, {452}, datetime(2026, 11, 6, 7, 5, tzinfo=UTC)) == [(453, "Whomp Em")]
    assert B.is_scheduled_for_later(future.find("item"), now) is True
    assert B.is_scheduled_for_later(future.find("item"), datetime(2026, 11, 6, 7, 5, tzinfo=UTC)) is False

    # --- feed addresses: always the same feed, differing only in letter case (so the host's cache has never seen them), plus the plain one
    import random
    addrs = {B.fresh_feed_address(random.Random(i)) for i in range(200)}
    assert len(addrs) > 100, "random capitals should give many different addresses"
    for u in addrs:
        assert u.rstrip("/").lower() == B.FEED, u
    assert B.feed_addresses(fresh=2)[-1] == B.FEED and len(B.feed_addresses(fresh=2)) == 3

    # --- the Friday watch window (Eastern time, so it follows daylight saving)
    assert W.watch_deadline(datetime(2026, 10, 30, 5, 30, tzinfo=UTC)) == datetime(2026, 10, 30, 13, 0, tzinfo=UTC)   # EDT: 9am = 13:00 UTC
    assert W.watch_deadline(datetime(2026, 10, 30, 13, 30, tzinfo=UTC)) is None                                       # after 9am
    assert W.watch_deadline(datetime(2026, 10, 29, 20, 0, tzinfo=UTC)) is None                                       # Thursday
    assert W.watch_deadline(datetime(2026, 10, 31, 6, 0, tzinfo=UTC)) is None                                        # Saturday
    assert W.watch_deadline(datetime(2026, 11, 6, 8, 0, tzinfo=UTC)) == datetime(2026, 11, 6, 14, 0, tzinfo=UTC)      # EST: 9am = 14:00 UTC

    # --- watching: the episode shows up in the feed on the 4th check (its date has passed by then)
    clock = {"t": datetime(2026, 10, 30, 7, 1, tzinfo=UTC)}
    sleeps, updates, polls = [], [], []

    def sleep(sec):
        sleeps.append(sec)
        clock["t"] += timedelta(seconds=sec)

    def fetch():
        polls.append(clock["t"])
        if len(polls) == 2:
            raise OSError("feed hiccup")  # a failed read is tried again, not fatal
        return channel(("452 - Totally Rad", out)) if len(polls) >= 4 else channel(("451 - Power Blade", "Fri, 23 Oct 2026 05:55:00 GMT"))

    said = []
    res = W.watch(fetch, lambda: ({451}, "2026-10-23"), lambda: updates.append(clock["t"]), lambda: clock["t"], sleep,
                  datetime(2026, 10, 30, 13, 0, tzinfo=UTC), every=90, say=said.append)
    assert res == "published" and len(polls) == 4 and len(updates) == 1 and sleeps == [90, 90, 90], (res, polls, updates, sleeps)
    assert any("hiccup" in m for m in said) and any("new episode" in m for m in said)

    # --- the same episode dated in the future is held back until its time, even though the feed already lists it
    clock["t"] = datetime(2026, 10, 30, 6, 50, tzinfo=UTC)
    updates.clear()
    res = W.watch(lambda: channel(("452 - Totally Rad", out)), lambda: ({451}, ""), lambda: updates.append(clock["t"]),
                  lambda: clock["t"], sleep, datetime(2026, 10, 30, 13, 0, tzinfo=UTC), every=300, say=lambda m: None)
    assert res == "published" and updates and updates[0] >= datetime(2026, 10, 30, 6, 59, tzinfo=UTC), updates

    # --- an update that fails is tried again on the next check, and given up on after three failures
    clock["t"] = datetime(2026, 10, 30, 7, 1, tzinfo=UTC)
    attempts = []

    def flaky():
        attempts.append(1)
        if len(attempts) < 3:
            raise RuntimeError("temporary trouble")

    res = W.watch(lambda: channel(("452 - Totally Rad", out)), lambda: ({451}, ""), flaky, lambda: clock["t"], sleep,
                  datetime(2026, 10, 30, 13, 0, tzinfo=UTC), every=120, say=lambda m: None)
    assert res == "published" and len(attempts) == 3
    try:
        W.watch(lambda: channel(("452 - Totally Rad", out)), lambda: ({451}, ""), lambda: 1 / 0, lambda: clock["t"], sleep,
                datetime(2026, 10, 30, 13, 0, tzinfo=UTC), every=120, say=lambda m: None)
        raise AssertionError("should have raised after three failures")
    except ZeroDivisionError:
        pass

    # --- someone else publishes the episode while we wait: stop, and do not run an update of our own
    clock["t"] = datetime(2026, 10, 30, 8, 0, tzinfo=UTC)
    updates.clear()
    res = W.watch(lambda: channel(("451 - Power Blade", "Fri, 23 Oct 2026 05:55:00 GMT")), lambda: ({451, 452}, "2026-10-30"), lambda: updates.append(1),
                  lambda: clock["t"], sleep, datetime(2026, 10, 30, 13, 0, tzinfo=UTC), every=120, say=lambda m: None)
    assert res == "published" and not updates

    # --- watching: nothing comes before the deadline
    clock["t"] = datetime(2026, 10, 30, 12, 55, tzinfo=UTC)
    updates.clear()
    res = W.watch(lambda: channel(("451 - Power Blade", "Fri, 23 Oct 2026 05:55:00 GMT")), lambda: ({451}, ""), lambda: updates.append(1),
                  lambda: clock["t"], sleep, datetime(2026, 10, 30, 13, 0, tzinfo=UTC), every=120, say=lambda m: None)
    assert res == "waiting" and not updates
    print("all tests passed")


if __name__ == "__main__":
    main()
