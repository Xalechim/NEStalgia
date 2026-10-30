# NEStalgia team handbook

How the repo and the website fit together, and what to do when something happens. This is a map, not a manual: the detailed docs live next to the code, and this page links to them.

- Transcription tools, the launcher commands and the Links tab: [`scripts/README.md`](../scripts/README.md)
- Making one transcript by hand: [`scripts/HOW-TO-MAKE-A-TRANSCRIPT.md`](../scripts/HOW-TO-MAKE-A-TRANSCRIPT.md)
- The data files: [`data/README.md`](../data/README.md)
- Writing reviews: [`reviews/README.md`](../reviews/README.md)
- Show notes: [`docs/SHOW-NOTES-STYLE.md`](SHOW-NOTES-STYLE.md)
- Writing and editing articles: [`articles/README.md`](../articles/README.md)
- Article look and rules: [`docs/ARTICLE-STYLE.md`](ARTICLE-STYLE.md)
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
- **Content we write.** `episodes/` (show notes), `transcripts/`, `reviews/`, `articles/` and `site-src/` are edited by hand.
- **The build.** `scripts/python/build_site.py` turns all of it into the static site in `site/` (not stored in git), and Pagefind builds the search index.
- **Deploy.** GitHub Actions builds and publishes on every push to `main`.

## How a new episode reaches the site

New episodes go live on Friday mornings, at some point between about 2am and 6:30am Eastern (the last eight were 1:55, 2:22, 3:00, 3:11, 3:23, 3:25, 3:54 and 6:26). Nobody has to be awake: the website is updated by itself within a few minutes of the episode appearing in the podcast feed. The one thing it needs from you is the **transcript**, made any time beforehand.

```
 you (Mac)              Claude (cloud routine)           GitHub (Update site)                   the website
 ─────────              ──────────────────────           ────────────────────                   ───────────
 finish the mix
 make the transcript ─► (push) ─► writes the review
 + mix fingerprint                 and links, hidden
                                   until the episode      Friday: watches the feed ─► episode appears
                                   is out                 adds it to Episodes, moves "Up next" on,
                                                          measures click-to-play, builds, deploys ─► live in ~3 minutes
                                                          announces it on Discord
```

- **Transcript and fingerprint (you).** `scripts/Transcribe Episode.command` (or Update Everything) makes the transcript from the final mix in iCloud `Mixes`, and also saves a small fingerprint of the mix (`data/mix-fingerprints/NNN.json`). Push it; the command offers to. A transcript for an episode that isn't out yet is fine: the site ignores everything about an episode until it is in the feed (a review, links, transcript and fingerprint sit in the repo, unseen). Update Everything also copies the upcoming episodes' covers out of iCloud into `data/up-next-art/` so the Up next box has your art.
- **Review and links (Claude).** The "NEStalgia review and links" routine looks for episodes that have a transcript but no review or links, whether or not they are out yet, writes them and pushes. Run `python3 scripts/python/pipeline_status.py --board` to see where every upcoming episode stands.
- **Publishing (GitHub, automatic).** The new episode joins the Episodes list, the Up next box moves on to the following episode in the spreadsheet, the click-to-play timing is measured from the fingerprint, the site is rebuilt, and the episode is announced on Discord.

If a transcript is late, the episode still goes live on time, just without its Transcript, Review and Links tabs. They appear after the next push and rebuild.

## What runs automatically

| What | Where | When | What it does |
| --- | --- | --- | --- |
| **Update site** (`update-site.yml`) | GitHub | Every 4 hours; on Fridays before 9am Eastern it is started many times (see below) so that one run becomes the watcher; any push that changes `kick/`; or on demand | Reads the feed and the spreadsheet, fetches cover art and Wikipedia intros, measures click-to-play timing for a new episode, moves the Up next box on, commits what changed and calls the deploy. **On a Friday morning it first does that once, then checks the feed every minute or two and does it again the moment a new numbered episode shows up** (`watch_feed.py`). |
| **Deploy website** (`deploy-site.yml`) | GitHub | Every push to `main`, or called by Update site | Builds the site and search index, publishes to GitHub Pages, then runs the announcement |
| **Announce new episode** (`announce-episode.yml`) | GitHub | Last step of every deploy | Posts any new episode to Discord, once. Needs the repository secret `DISCORD_WEBHOOK_URL`, and does nothing without it |
| **NEStalgia Friday clock** | Claude cloud routine | Fridays at 05:10, 07:10, 09:10 and 11:10 UTC (about 1am to 7am Eastern) | A second, independent clock. Checks whether the newest episode in the feed is on the site; if not (or on the first check of the morning), it pushes a change in `kick/`, which starts Update site. Costs almost nothing when everything is fine. |
| **NEStalgia review and links** | Claude cloud routine | Twice a day, and whenever a transcript is pushed | Writes the review and the Links tab for up to two episodes that have a transcript and are missing them (published ones first, then upcoming ones in release order), and pushes. Never touches show notes, transcripts or other data. |

Why so many clocks: GitHub's scheduler is best effort and drops or delays runs. On the last two Fridays every Friday-morning run before 6am Eastern was skipped, so the site sat unchanged until a person pressed the button. The Update site workflow therefore has a long list of early-morning start times (UTC, and the watcher works out Eastern time itself, so daylight saving needs no changes), the Claude clock starts it a different way (a push, which GitHub does not drop), and once any one of them starts a watcher, the exact start time stops mattering.

Notes:

- If two pushes land close together, the older deploy shows as **cancelled**. That's expected: the newer run covers both.
- To refresh right now (a verdict you just changed in the sheet, say), open the Actions tab and run **Update site**. Leave "Also wait for a new episode" off.
- Every Update site run lists where each recent and upcoming episode stands (its job summary), the same table as `pipeline_status.py --board`.
- The only GitHub secret is the Discord webhook. The Anthropic key used for the Links tab is local only (`~/.config/nestalgia/anthropic_key`) and is never in the repo. GoatCounter's site code and the contact form's FormSubmit alias are public by design.

## When a new episode comes out

Nothing, if the transcript was made ahead of time. To prepare an episode:

1. Put the finished mix in the iCloud `Mixes` folder, named like `NES 453 - Game Name.mp3`.
2. Double-click **`scripts/Transcribe Episode.command`**, enter the number, and say yes when it offers to publish. That saves the transcript and the mix fingerprint.
3. Optionally, double-click **`scripts/Update Everything.command`** any time (it does the same refresh GitHub does, so it is safe to run on a Friday too); it also saves the upcoming covers for the Up next box.
4. Later, check `python3 scripts/python/pipeline_status.py --board`: the episode should show a review and links within a day. If they are missing, tell Claude Code to run `/make-links 453` and write the review.

On Friday, open the site after the episode is out and look for it at the top of the Episodes page and the next game in the Up next box. If something looks wrong, the Actions tab shows what Update site did.

## Everyday tasks

**A verdict, genre or date is wrong.** Fix the spreadsheet. The site picks it up within about four hours, or run **Update site** by hand.

**A transcript has a mistake.** Edit `transcripts/NNN-name.md`. Keep exactly one transcript file per episode number (see Gotchas).

**Write or change a review.** `reviews/NNN-game-name.md`, shown as the first tab on the episode page. Read [`reviews/README.md`](../reviews/README.md) for the voice: write as "we", say a unanimous vote once without naming voters, never write "one of us".

**Write an article.**
1. Add a file `articles/your-article.md`: a few lines of details (title, address, date) and then the article in plain Markdown. [`articles/README.md`](../articles/README.md) explains the format. To change an existing article, open its file there and edit it.
2. Put images in `site-src/migrated/media/`.
3. Set its search title and description in `site-src/seo.json` under `articles`.
4. For a ranking article (Top 5, Top 10, a themed list), use the `countdown` layout in `seo.json`: `ranks` maps each rank to an episode number, `screenshots` lists images per rank, and options like `heading`, `numbered`, `intro_label` and `listen_label` change the labels. `stats` and `special` add the year-in-numbers tiles and the link to the special episode.
5. Add entries to `episode_guides` in `seo.json` to put a link back to the article on each episode page.

The hero block, picture frames, carousels, cards and the shared ending are built for you. See [`docs/ARTICLE-STYLE.md`](ARTICLE-STYLE.md) for the rules and the options.

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
- **GitHub's scheduler can't be trusted with a deadline.** Never rely on a `schedule:` run for something that must happen at a certain time. Anything time-critical needs a trigger that doesn't depend on it (a push, a watcher that is already running).
- **Don't hand-edit `kick/last-kick.txt` in a commit with other work.** Any change under `kick/` starts the update workflow, which is harmless but wasteful.

## Loose ends (as of October 2026)

Worth checking before you rely on them:

- The old Bytes show notes are still in the git history. Removing them means rewriting history, so it needs a decision first.
- Episode 1 (10-Yard Fight) has no transcript, so it has no review yet.
- Written reviews cover episodes 2 to 50 and 240 to the latest, plus a handful in between. About 150 episodes from 51 to 239 don't have one yet.
