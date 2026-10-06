# NEStalgia team handbook

How the repo and the website fit together, and what to do when something happens. This is a map, not a manual: the detailed docs live next to the code, and this page links to them.

- Transcription tools, the launcher commands and the Links tab: [`scripts/README.md`](../scripts/README.md)
- Making one transcript by hand: [`scripts/HOW-TO-MAKE-A-TRANSCRIPT.md`](../scripts/HOW-TO-MAKE-A-TRANSCRIPT.md)
- The data files: [`data/README.md`](../data/README.md)
- Writing reviews: [`reviews/README.md`](../reviews/README.md)
- Reporting problems: [`CONTRIBUTING.md`](../CONTRIBUTING.md) and [`SECURITY.md`](../SECURITY.md)

## The big picture

```
 podcast feed ─┐
 Google Sheet ─┤                                      GitHub Pages
 Wikipedia ────┼─►  data/*.json  ─┐                   nestalgiacast.com
 box art ──────┘                  ├─►  build_site.py ─►  site/  ─►  deploy
 episodes/  transcripts/  reviews/ ┤
 site-src/ (pages, articles, CSS, JS) ┘
```

- **Sources of truth.** The podcast feed (episodes, dates, audio links, cover art) and the show's Google Sheet (verdicts, genres, developers, years, the "Up next" box, Bytes rows) live outside the repo. Everything in `data/` is generated from them. Don't edit `data/game-info.json` by hand, because the next refresh overwrites it. Fix it in the sheet.
- **Content we write.** `episodes/` (show notes), `transcripts/`, `reviews/` and `site-src/` are edited by hand.
- **The build.** `scripts/python/build_site.py` turns all of it into the static site in `site/` (not stored in git), and Pagefind builds the search index.
- **Deploy.** GitHub Actions builds and publishes on every push to `main`.

## What runs automatically

| Workflow | When | What it does |
| --- | --- | --- |
| `update-from-feed.yml` | Every 4 hours, plus Fridays 11:30 and 15:30 UTC and Saturday 15:30 UTC, or on demand | Reads the feed and the spreadsheet, fetches new cover art and Wikipedia intros, swaps generic covers for NES box art, commits what changed, and starts a deploy only if it committed |
| `deploy-site.yml` | Every push to `main`, or on demand | Builds the site, builds the search index, publishes to GitHub Pages |
| `announce-episode.yml` | After each deploy | Posts any new episode to Discord, once. Needs the repository secret `DISCORD_WEBHOOK_URL`, and does nothing without it |

Notes:

- If two pushes land close together, the older deploy shows as **cancelled**. That's expected: the newer run covers both.
- To refresh right now (a verdict you just changed in the sheet, say), open the Actions tab and run **Update from podcast feed**.
- The only secret is the Discord webhook. The Anthropic key used for the Links tab is local only (`~/.config/nestalgia/anthropic_key`) and is never in the repo. GoatCounter's site code and the contact form's FormSubmit alias are public by design.

## When a new episode comes out

1. Put the finished mix in the iCloud `Mixes` folder, named like `NES 449 - Game Name.mp3`.
2. Double-click **`scripts/Update Everything.command`**. It refreshes the feed and the spreadsheet, makes the transcript, measures the audio offset, lists episodes that still need a Links tab, then shows what changed and **asks before it publishes**. Only `data/`, cover art, the episode index and `transcripts/` are ever committed by it.
3. Ask Claude Code to run `/make-links 449` for the Links tab (no API key needed), and write the review if you want one.
4. The deploy posts the new episode to Discord.

Other launcher commands, when you need just one step, are in `scripts/sub-commands/` and `scripts/Transcribe Episode.command`.

## Everyday tasks

**A verdict, genre or date is wrong.** Fix the spreadsheet. The site picks it up within about four hours, or run the workflow by hand.

**A transcript has a mistake.** Edit `transcripts/NNN-name.md`. Keep exactly one transcript file per episode number (see Gotchas).

**Write or change a review.** `reviews/NNN-game-name.md`, shown as the first tab on the episode page. Read [`reviews/README.md`](../reviews/README.md) for the voice: write as "we", say a unanimous vote once without naming voters, never write "one of us".

**Write an article.**
1. Add the article to `site-src/migrated/articles.json` (`path`, `slug`, `title`, `date`, `body` as HTML; use `{BASE}` for internal links and media).
2. Put images in `site-src/migrated/media/`.
3. Set its search title and description in `site-src/seo.json` under `articles`.
4. For a ranking article (Top 5, Top 10, a themed list), use the `countdown` layout in `seo.json`: `ranks` maps each rank to an episode number, `screenshots` lists images per rank, and options like `heading`, `numbered`, `intro_label` and `listen_label` change the labels. `stats` and `special` add the year-in-numbers tiles and the link to the special episode.
5. Add entries to `episode_guides` in `seo.json` to put a link back to the article on each episode page.

Screenshots come from the libretro thumbnail library (`Named_Titles` and `Named_Snaps` in its NES repository), the same place the box art comes from. MobyGames blocks automated downloads.

**Preview the site on your Mac.**
```bash
pip install pillow markdown
python3 scripts/python/build_site.py
python3 -m http.server 8000 --directory site      # then open http://localhost:8000
```

## Gotchas we've already hit

- **One transcript per episode number.** The site uses the first matching file alphabetically, so a stray second file for the same number shows the wrong transcript. (It happened once, with a Magic Kingdom transcript filed under Remote Control.)
- **Pull before you push, and stage explicit paths.** Scripts and people both commit here. Use `git pull --rebase -X theirs --autostash`, and `git add` the files you mean, not everything.
- **Never `git checkout data`.** It once threw away the measured audio offsets for a run of episodes. They can be re-measured with the launcher, but it takes a while.
- **Python versions.** GitHub builds with Python 3.12, but macOS ships 3.9. In an f-string, don't nest the same kind of quote or use a backslash inside the braces: 3.9 rejects it, and a push with that mistake once failed to build.
- **Feed hiccups.** A stale or partial feed once dropped an episode. The updater now keeps episodes that go missing from the feed, so a bad fetch won't delete anything.
- **Bytes episodes are Patreon-only.** They get a page and a cover but no player, notes or transcript, and show notes for them should not be published.
- **Check the deploy.** After pushing, watch the **Deploy website** run on the Actions tab (or `gh run list`), and open the page that changed.

## Loose ends (as of October 2026)

Worth checking before you rely on them:

- The old Bytes show notes are still in the git history. Removing them means rewriting history, so it needs a decision first.
- Episode 1 (10-Yard Fight) has no transcript, so it has no review yet.
- Written reviews cover episodes 2 to 50, 300 to the latest, and a handful in between. Most of episodes 51 to 299 don't have one yet.
