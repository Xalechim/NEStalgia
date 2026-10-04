# Transcription tooling

Local, free transcripts (paragraphs with timestamps, no speaker labels). Nothing here uploads audio.

## Setup (already done on Mike's Mac)

- Python venv at `~/.venvs/nestalgia` with `mlx-whisper`, `imageio-ffmpeg`, `markdown`, `pillow`, `beautifulsoup4`, `anthropic`.
- `ffmpeg` symlinked into the venv's `bin/` (from `imageio-ffmpeg`), so run with `export PATH=$HOME/.venvs/nestalgia/bin:$PATH`.
- Whisper `mlx-community/whisper-large-v3-turbo` downloads itself into the Hugging Face cache.
  (`~/.nestalgia-models/` held the speaker-recognition models and voice profiles from the retired speaker experiment; it can be deleted.)

## How this folder is organized

```
scripts/
  Update Everything.command      MAIN: the one to double-click after anything happens (new episode, new verdict, new mixes)
  Transcribe Episode.command     MAIN: make the transcript for specific episodes you name
  sub-commands/                  the commands the main ones run (each also works by itself when double-clicked)
    Refresh Feed and Spreadsheet.command    feed, cover art, spreadsheet verdicts/genres, Up next box, Wikipedia intros, box art
    Check for New Episodes.command          transcript + audio shift for new episodes
    Measure Audio Offsets.command           click-to-play timing for any transcript without it
    Make Links.command                      links for the Links tab (lists what's missing; does them if an API key is set up)
    Add Wikipedia Intros.command            just the Wikipedia intros (also part of Refresh)
    Strip Speakers.command                  one-time converter for old speaker-labelled transcripts
    _common.sh                              shared setup used by all of them
  python/                        the Python scripts those commands run (plus tests/, and khinsider_lookup.js used by download_game_music.py)
```

**Update Everything** runs, in order: Refresh Feed and Spreadsheet, Check for New Episodes, Measure Audio Offsets, Make Links, then publishes
everything once (it shows what changed and asks first; only `data`, cover art, the episode index and `transcripts` are ever committed).
When a main command runs a sub-command it sets `NES_LAUNCHER=1`, which makes the sub-command skip its own pauses and publishing.
The same refresh as step 1 also runs by itself on GitHub every 4 hours, so a verdict added to the spreadsheet shows up on the site within a few hours.
Not part of the launcher because they need a person at the keyboard: making a Links tab without an API key (ask Claude Code: `/make-links 449`),
getting KHInsider music and Audition project folders (`python/make_project_folders.py`, `python/download_game_music.py`).

## Scripts (in `python/`)

- `transcribe.py AUDIO --out transcripts/NNN-name --title "NNN - Name"` writes `NNN-name.md` (paragraphs, each starting with a `[mm:ss]` timestamp)
  and `NNN-name.vtt` (sentence-level subtitles). About 70 seconds for a 25-minute episode.
- `paragraphs.py` turns sentences into paragraphs: a pause of 1.6 s or more always breaks; text longer than ~760 characters is split at its
  best internal break (longer pause + change of vocabulary = new subject); pieces under ~170 characters are folded into a neighbour.
- `strip_speakers.py` (double-click `Strip Speakers.command`) converts old speaker-labelled transcripts in bulk: timing from the `.vtt`,
  speaker names dropped, regrouped into paragraphs, word count verified unchanged, idempotent, offline. `--dry-run` previews.
- `bytes_info.py` / `bytes_art.py`: the NEStalgia Bytes episodes (Patreon-only) on the site. `bytes_info.py` reads the spreadsheet's "Byte" rows
  (a row with no number follows the one before it; a typo'd number or a future date is skipped) into `data/bytes-info.json`; add a
  spreadsheet column whose header contains "Patreon" and paste each post's address in it to link a Bytes page straight to its Patreon post
  (otherwise it points to the Patreon page). `bytes_art.py` makes each cover: the Famicom/NES box scan from the libretro library if the game is
  there, else a generated "BYTES" cover; put your own picture at `assets/episode-art/nb-NNN-name.jpg` to override. Bytes pages have no player,
  notes, transcript or links. Both run inside `update_from_feed.py`.
- `audio_offsets.py` measures the shift between your final mix (what transcript timestamps are measured on) and the audio the podcast host
  serves (Megaphone inserts pre-rolls: 56-60 s on most recent episodes, 0 on others). It aligns loudness envelopes using only the first
  and last few MB of the hosted file (a full alignment is the fallback if the shift changes mid-episode) and writes
  `data/audio-offsets.json` as `{"446": [[0, 60.2]]}`. The site's `player.js` adds it when a timestamp is clicked. Run by `run_episode.py`.
- `new_episodes.py` (double-click `Check for New Episodes.command`) is the whole workflow for new episodes: fetch the feed, find episodes not yet
  handled (state in `data/pipeline-state.json`: guids seen + a waiting list for episodes without a final mix), run `update_from_feed.py`
  (data, art, index), `transcribe.py`, `audio_offsets.py`, optionally `make_links.py`, commit only its own paths, `git pull --rebase -X theirs`,
  push, then watch the `Deploy website` run for that commit (via `gh`) and check the new pages return 200. First run baselines the back catalog
  except recent untranscribed episodes. `--dry-run`, `--no-publish`, `--episodes N`, `--redo`, `--links`, `--use-hosted-audio`,
  `--install-schedule` (a launchd agent, opt-in). Logs to `~/Library/Logs/nestalgia-new-episodes.log`. The Friday GitHub Action
  (`update-from-feed.yml`) still refreshes data/art on its own; the two don't conflict (generated files from this script win a rebase).
- Tests: `python3 scripts/python/tests/test_new_episodes.py`, `python3 scripts/python/tests/test_paragraphs.py`, `python3 scripts/python/tests/test_make_links.py`.

## Auto-update from the feed

`.github/workflows/update-from-feed.yml` runs on GitHub (not on your Mac) every 4 hours, plus extra runs on Fridays at 11:30 and 15:30 UTC and Saturday at 15:30 UTC, and on demand
(repo page, Actions tab, "Update from podcast feed", Run workflow). It runs `scripts/python/update_from_feed.py`, which:

1. downloads cover art for new episodes (resized to 1000 px JPEG),
2. rebuilds `data/episodes.json` and `episodes.csv`,
3. rebuilds `episodes/README.md`,
4. refreshes the spreadsheet data (`data/game-info.json`), the Up next box, Wikipedia intros, and swaps generic covers for NES box art,

and commits the result as "Auto-update (feed spreadsheet ...)", naming what changed. If nothing is new, it does nothing.
It does not make show notes or transcripts; those stay manual (the double-click tool for transcripts).
Run the same thing by hand with `python3 scripts/python/update_from_feed.py` (needs `pip install pillow`).

## Links tab (make_links.py)

`make_links.py` turns a transcript into `data/links/NNN-game-name.json`, which the site shows on the episode's Links tab.
1. Claude (`claude-opus-5-5`, structured output) lists everything referenced, with timestamps.
2. Claude with the web search tool finds reference-site and other pages. Wikipedia is resolved separately through the Wikipedia API
   (exact title, then a strict search fallback; disambiguation pages rejected).
3. Verification: a non-Wikipedia URL is kept only if it appeared in the web search results and still loads. Episode titles that match a
   NEStalgia episode become "Our episode" links.
`/make-links N` (`.claude/commands/make-links.md`) is the no-API-key route: Claude Code does steps 1-2 by hand, writes a proposals file (with `searched_urls`),
and `--check-proposals` / `--from-proposals` run the same verification. Run `python3 scripts/python/tests/test_make_links.py` for the offline tests (fake client, no key needed). Key: `~/.config/nestalgia/anthropic_key`
or `ANTHROPIC_API_KEY`. `--dry-run` shows the size of a request without spending anything; `--from-proposals FILE` verifies links from a
file (used for the episode 446 sample). Untested against the live API as of this commit: there was no key on the dev machine.

## History: why there are no speaker labels

Speaker labeling was built and then retired (the code is in git history, commits before "Remove speaker names").
- Unsupervised diarization (sherpa-onnx pyannote segmentation with 3D-Speaker, WeSpeaker and TitaNet embeddings) failed on this show: it split the three hosts into 1-2 clusters, or 41 when auto-detecting.
- Labeling from each host's own mic recording was accurate but only possible for about the last 20 episodes (Audition projects NES 438-454).
- Voice recognition trained on the final mixes scored 81% of sentences (90% of airtime) on a held-out episode, and only 62% on 1-2 second replies. Not good enough to publish.
- Decision: publish transcripts as timestamped paragraphs with no speaker names.

## Whisper findings

- `condition_on_previous_text=True` is required; with it off, about half of the segments come out lowercase with no punctuation.
- Whisper loops on laughter or outro music ("Ha ha ha." repeated); `transcribe.py` drops runaway repeats.
- `large-v3` is no better than `large-v3-turbo` here and about 12x slower.
