# Articles

One file per article on the website, written as plain text. To change an article, open its file here, click the pencil icon on GitHub, edit the words, and commit. The site rebuilds itself a couple of minutes later.

| File | Page |
| --- | --- |
| `best-of-1989.md` | /articles/best-of-1989/ |
| `how-to-enjoy-shmups.md` | /articles/shmups/ |
| (and so on, one file per article) | |

## What a file looks like

```
---
title: The Top 10 NES Games of 1989
slug: best-of-1989
path: /articles/best-of-1989
date: 2026-10-17
author: Michael Esposito
image: {BASE}/media/best-of-1989-cover.jpg
excerpt: One or two sentences shown on the Articles page and in search results.
---

## A heading

A paragraph. **Bold**, *italic*, and a [link](https://example.com).

Another paragraph.
```

The block between the two lines of `---` is the article's details. `title`, `slug`, `path` and `date` (year-month-day) are required. `slug` and `path` are the article's address and should not change once the article is live. `tags` and `categories` (separated by commas) are optional.

## Writing

- Plain paragraphs with a blank line between them. `##` makes a heading and `###` a smaller one. `**bold**`, `*italic*` and `[words](address)` work. A line starting with `- ` makes a bullet. A line starting with `> ` makes a quote.
- To link inside the site, start the address with `{BASE}`, like `[Zelda]({BASE}/episodes/058-the-legend-of-zelda/)`. Game names that match an episode are linked automatically the first time they appear, so you rarely need to.
- Pictures live in `site-src/migrated/media/`. To show one or more, write a gallery in HTML (copy one from another article):

```
<div class="gallery">
<img src="{BASE}/media/some-picture.png" alt="What the picture shows" loading="lazy">
<img src="{BASE}/media/another-picture.png" alt="Another one" loading="lazy">
</div>
```

  One picture becomes a framed picture with a caption (the `alt` text), and two or more become a carousel. Add `class="px"` to the `img` for pixel art so it stays sharp.
- Tables, note boxes and other fancy pieces are written as HTML in the file; look at `zelda-vs-zelda-ii.md` for a table.

## Ranked countdowns

Ranked entries (a Top 10, the Wall of Shame) use a block like this. The cover, the verdict and genre tags, the screenshots and the link to the episode are added for you from the settings below.

```
::: rank 10 | Gyruss
First paragraph of the write-up.

Second paragraph.
:::
```

## Page settings

How an article is laid out (the ranking, which screenshots go with which entry, the special episode, the year's stats, "related episodes") is set in `site-src/seo.json` under `articles`, keyed by the article's `path`. The rules and options are in [`docs/ARTICLE-STYLE.md`](../docs/ARTICLE-STYLE.md).

## Checking your change

On your Mac: `python3 scripts/python/build_site.py`, then open the page from the `site/` folder (see the handbook). On GitHub, a mistake in the details block makes the build fail with the name of the file; fix it and commit again.
