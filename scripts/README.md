# Transcription tooling

Local, free transcripts (paragraphs with timestamps, no speaker labels). Nothing here uploads audio.

## Setup (already done on Mike's Mac)

- Python venv at `~/.venvs/nestalgia` with `mlx-whisper`, `imageio-ffmpeg`, `markdown`, `pillow`, `beautifulsoup4`, `anthropic`.
- `ffmpeg` symlinked into the venv's `bin/` (from `imageio-ffmpeg`), so run with `export PATH=$HOME/.venvs/nestalgia/bin:$PATH`.
- Whisper `mlx-community/whisper-large-v3-turbo` downloads itself into the Hugging Face cache.
  (`~/.nestalgia-models/` held the speaker-recognition models and voice profiles from the retired speaker experiment; it can be deleted.)

## Scripts

- `transcribe.py AUDIO --out transcripts/NNN-name --title "NNN - Name"` writes `NNN-name.md` (paragraphs, each starting with a `[mm:ss]` timestamp)
  and `NNN-name.vtt` (sentence-level subtitles). About 70 seconds for a 25-minute episode.
- `paragraphs.py` turns sentences into paragraphs: a pause of 1.6 s or more always breaks; text longer than ~760 characters is split at its
  best internal break (longer pause + change of vocabulary = new subject); pieces under ~170 characters are folded into a neighbour.
- `strip_speakers.py` (double-click `Strip Speakers.command`) converts old speaker-labelled transcripts in bulk: timing from the `.vtt`,
  speaker names dropped, regrouped into paragraphs, word count verified unchanged, idempotent, offline. `--dry-run` previews.
- Tests: `python3 scripts/test_paragraphs.py`, `python3 scripts/test_make_links.py`.

## Auto-update from the feed

`.github/workflows/update-from-feed.yml` runs on GitHub (not on your Mac) on Fridays at 11:30 and 15:30 UTC and Saturday at 15:30 UTC, and on demand
(repo page, Actions tab, "Update from podcast feed", Run workflow). It runs `scripts/update_from_feed.py`, which:

1. downloads cover art for new episodes (resized to 1000 px JPEG),
2. rebuilds `data/episodes.json` and `episodes.csv`,
3. rebuilds `episodes/README.md`,

and commits the result as "Auto-update from feed: <newest episode title>". If nothing is new, it does nothing.
It does not make show notes or transcripts; those stay manual (the double-click tool for transcripts).
Run the same thing by hand with `python3 scripts/update_from_feed.py` (needs `pip install pillow`).

## Links tab (make_links.py)

`make_links.py` turns a transcript into `data/links/NNN.json`, which the site shows on the episode's Links tab.
1. Claude (`claude-opus-5-5`, structured output) lists everything referenced, with timestamps.
2. Claude with the web search tool finds reference-site and other pages. Wikipedia is resolved separately through the Wikipedia API
   (exact title, then a strict search fallback; disambiguation pages rejected).
3. Verification: a non-Wikipedia URL is kept only if it appeared in the web search results and still loads. Episode titles that match a
   NEStalgia episode become "Our episode" links.
`/make-links N` (`.claude/commands/make-links.md`) is the no-API-key route: Claude Code does steps 1-2 by hand, writes a proposals file (with `searched_urls`),
and `--check-proposals` / `--from-proposals` run the same verification. Run `python3 scripts/test_make_links.py` for the offline tests (fake client, no key needed). Key: `~/.config/nestalgia/anthropic_key`
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
