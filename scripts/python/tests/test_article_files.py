#!/usr/bin/env python3
"""Run: python3 scripts/python/tests/test_article_files.py"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import article_files as A

raw = """---
title: A test: with a colon
slug: a-test
path: /articles/a-test
date: 2026-01-02
author: Someone
tags: one, two
---

## Heading

Plain paragraph with *italic*, **bold** and [a link]({BASE}/episodes/x/) & an ampersand.

::: rank 3 | Wizards & Warriors
First.

Second.
:::

<div class="gallery">
<img src="a.png" alt="" loading="lazy">
</div>
"""
with tempfile.TemporaryDirectory() as td:
    f = Path(td) / "a-test.md"
    f.write_text(raw)
    (Path(td) / "README.md").write_text("not an article")
    arts = A.load_articles(td)
assert len(arts) == 1
a = arts[0]
assert a["title"] == "A test: with a colon" and a["slug"] == "a-test" and a["date"] == "2026-01-02"
assert a["tags"] == ["one", "two"] and a["categories"] == []
b = a["body"]
assert "<h2>Heading</h2>" in b and "<em>italic</em>" in b and "<strong>bold</strong>" in b
assert '<a href="{BASE}/episodes/x/">a link</a>' in b and "&amp; an ampersand" in b
assert "<figure><figcaption>" in b and "<p>#3 - Wizards &amp; Warriors</p><p>First.</p><p>Second.</p>" in b
assert '<div class="gallery">' in b
try:
    A.split_front("no details here")
    raise SystemExit("should have failed")
except ValueError:
    pass
print("all tests passed")
