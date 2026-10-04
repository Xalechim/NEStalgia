---
description: Find web links for everything mentioned in an episode's transcript (fills the episode's Links tab)
argument-hint: <episode number(s), e.g. 450 or 401-410>
allowed-tools: Read, Write, WebSearch, Bash(python3 scripts/python/make_links.py:*), Bash(ls:*), Bash(git status:*), Bash(git add data/links:*), Bash(git commit:*), Bash(git push:*)
---

Make the Links tab data for NEStalgia episode(s): $ARGUMENTS

This does by hand, in this Claude Code session, what `scripts/python/make_links.py` does with the Claude API: no API key. The script's
checker is still the gatekeeper: nothing reaches the site unless it passes verification.

Do the episodes one at a time. For each episode number N (expand ranges like 401-410):

1. **Find the transcript**: `transcripts/NNN-*.md` (NNN = N zero-padded to 3). If there is none, tell the user to make it first
   with "Transcribe Episode.command", and move on. If `data/links/NNN-game-name.json` already exists, say so and skip the episode unless the
   user asked to redo it.

2. **Read the whole transcript.** Then read `EXTRACT_SYSTEM` near the top of `scripts/python/make_links.py`. Those are the rules for what
   counts as a reference and how to write it: follow them exactly (correct canonical spellings, merged duplicates, one-sentence
   listener-friendly context under 25 words, first-mention timestamp copied from the transcript as mm:ss, a best-guess English
   Wikipedia title or "" when unsure, at most 45 items, main game first). Kinds: game, hardware, company, person, team_or_league,
   film_tv_music, event_or_term, website_or_article, other. The user wants a link for **anything referenced on the show**, so be
   thorough, but skip generic words, the hosts, and the podcast itself.

3. **Find reference pages with WebSearch.** Read `FIND_SYSTEM` in `scripts/python/make_links.py` for the rules. Do not search for Wikipedia
   (the script resolves Wikipedia titles itself). Spend searches (about 10 to 15 per episode) on the main game, other games, and
   anything that won't have a Wikipedia page: articles, videos, local events, products. Prefer hardcoregaming101.net,
   mobygames.com, gamefaqs.gamespot.com, nesdev.org, strategywiki.org, giantbomb.com, tcrf.net, archive.org, then other reputable
   pages. The main game gets up to 3 links; others 1 (2 if both are valuable). **Only use URLs that actually appeared in your search
   results. Never write a URL from memory.** Keep a list of every URL your searches returned.

4. **Write the proposals file** (a temporary file outside the repo, for example in the session scratchpad):

   ```json
   {
     "method": "claude-code: written from the transcript, links verified by script",
     "items": [
       {"name": "...", "kind": "game", "context": "...", "timestamp": "04:20", "wikipedia_title": "...", "search_query": "..."}
     ],
     "found": {"0": [{"url": "https://...", "label": "short page title", "source": "reference"}]},
     "searched_urls": ["every URL your web searches returned"]
   }
   ```

   `found` is keyed by the item's position in `items` (0 is the first item). `source` is `reference` for gaming reference sites and
   `other` for everything else. To link the NEStalgia Essential Games List, use the url `{BASE}/essential/` with source `other`.

5. **Preview the Wikipedia matches**: `python3 scripts/python/make_links.py --check-proposals FILE`. Read every line. Fix any `NO` (find
   the right title, or set it to ""), and any `OK` that resolves to the wrong thing (a redirect to a movie instead of a game, the
   wrong person, a different year). The script rejects a game whose page isn't about a game, but you are the second check.

6. **Build it**: `python3 scripts/python/make_links.py NNN --from-proposals FILE --force`. It verifies every link (Wikipedia pages must
   exist, other URLs must be in `searched_urls` and load), adds "Our episode" links to matching NEStalgia episodes, and writes
   `data/links/NNN-game-name.json`. If it drops something, decide whether to fix it and rerun.

7. **Report**: items made, links kept, anything dropped or that you couldn't find, and anything worth a second look. Be plain about
   what you are unsure of.

When all the episodes are done, **ask before publishing**; this is a public repository. If the user says yes:
`git add data/links && git commit -m "Add episode links" && git push`. The website rebuilds itself a few minutes later.
Do not run `git push` without that yes.
