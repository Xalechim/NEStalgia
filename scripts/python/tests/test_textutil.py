#!/usr/bin/env python3
"""Run: python3 scripts/python/tests/test_textutil.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from textutil import nice_case as n

assert n("MIKE TYSON'S PUNCH-OUT") == "Mike Tyson's Punch-Out"
assert n("THE 3-D BATTLES OF WORLDRUNNER") == "The 3-D Battles of Worldrunner"
assert n("GAUNTLET II") == "Gauntlet II"
assert n("GOTCHA! THE SPORT!") == "Gotcha! the Sport!" or n("GOTCHA! THE SPORT!") == "Gotcha! The Sport!"
assert n("WIZARDS & WARRIORS") == "Wizards & Warriors"
assert n("Bill Elliot's NASCAR Challenge") == "Bill Elliot's NASCAR Challenge"   # not all caps: untouched
assert n("") == "" and n("SKY SHARK") == "Sky Shark"
print("all tests passed")
