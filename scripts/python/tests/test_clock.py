#!/usr/bin/env python3
"""Offline tests for the Friday second clock's decision (no network, no git). Run:  python3 scripts/python/tests/test_clock.py"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import clock as C

U = timezone.utc
fri_3am = datetime(2026, 10, 30, 7, 5, tzinfo=U)       # Friday 3:05am Eastern (daylight time)
fri_7am = datetime(2026, 10, 30, 11, 10, tzinfo=U)     # Friday 7:10am Eastern: still in the window
fri_10am = datetime(2026, 10, 30, 14, 10, tzinfo=U)    # after 9am Eastern
thu = datetime(2026, 10, 29, 20, 0, tzinfo=U)


def main():
    # the episode is in the feed but not on the site: always kick (unless a run only just started on it)
    assert C.decide("PENDING", 452, 20, False, fri_3am)[0] is True
    assert C.decide("PENDING", 452, 20, True, fri_3am)[0] is True                  # a run is going but it has had 20 minutes
    assert C.decide("PENDING", 452, 3, True, fri_3am)[0] is False                  # ... only 3 minutes: let it work
    assert C.decide("PENDING", 452, 3, False, fri_3am)[0] is True
    assert C.decide("PENDING", 452, 600, False, thu)[0] is True                    # any day
    # Friday morning, today's episode not out yet (the newest one is last week's)
    assert C.decide("ON_SITE", 451, 7 * 24 * 60 + 60, False, fri_3am)[0] is True   # nobody is watching: start a watcher
    assert C.decide("ON_SITE", 451, 7 * 24 * 60 + 60, True, fri_3am)[0] is False   # someone is: leave it
    assert C.decide("ON_SITE", 451, 7 * 24 * 60 + 60, None, fri_3am)[0] is True    # GitHub couldn't be asked: start one to be safe? (None counts as not running)
    # today's episode is out and on the site: done
    assert C.decide("ON_SITE", 452, 130, False, fri_7am)[0] is False
    # outside the window: nothing to do
    assert C.decide("ON_SITE", 451, 7 * 24 * 60 + 60, False, fri_10am)[0] is False
    assert C.decide("ON_SITE", 451, 7 * 24 * 60 + 60, False, thu)[0] is False
    print("all tests passed")


if __name__ == "__main__":
    main()
