# Transcription tooling

Local, free transcripts with speaker labels. Nothing here uploads audio.

## Setup (already done on Mike's Mac)

- Python venv at `~/.venvs/nestalgia` with `mlx-whisper`, `sherpa-onnx`, `imageio-ffmpeg`, `numpy`, `soundfile`.
- `ffmpeg` symlinked into the venv's `bin/` (from `imageio-ffmpeg`), so run with `export PATH=$HOME/.venvs/nestalgia/bin:$PATH`.
- Models in `~/.nestalgia-models/`: `sherpa-onnx-pyannote-segmentation-3-0/`, `wespeaker_resnet34.onnx`
  (plus `emb_en.onnx`, `titanet_small.onnx`, `wespeaker_resnet293.onnx` that were tried and rejected).
  Whisper `mlx-community/whisper-large-v3-turbo` downloads itself into the Hugging Face cache.

## Scripts

- `transcribe.py AUDIO --out transcripts/NNN-name --title "NNN - Name" [--tracks "Mike=a.wav,Sean=b.wav,Joe=c.wav"]`
  writes `.md` (speaker turns with timestamps) and `.vtt`.
  - With `--tracks` (the hosts' separate mic recordings from the Audition projects) speakers are named exactly.
  - Without it, falls back to unsupervised diarization, which does not work well here (see below).
- `voiceid.py` builds voice profiles for the hosts (`enroll`, `enroll-mix`) for episodes with only a mixdown.

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

## Findings so far (tested on episode 446, 25 min)

- Whisper turbo transcribes a 25-minute episode in about 75 seconds.
- `condition_on_previous_text=True` is required; with it off, about half of the segments come out lowercase with no punctuation.
- Unsupervised diarization (sherpa-onnx pyannote segmentation + 3D-Speaker, WeSpeaker and TitaNet embeddings) fails: it splits the three hosts into 1-2 clusters, or 41 when auto-detecting.
- Multitrack labeling works well. Align each host's mic track to the mixdown (windowed envelope cross-correlation), then pick the loudest mic per segment. Mike, Sean and Joe came out correctly on 446.
- Multitrack data exists only for roughly the last 20 episodes (Audition Projects: NES 438-454, NB 053-055, SNES 002, S06). Tracks are Espo (Mike), Sean, Joe. There is no Sam track.
- Voice-ID from profiles built from raw mic tracks scored only 62% on held-out episode 446 (Sean over-predicted), probably because the mixdown is processed audio.

- Voice-ID trained on the mixdown segments themselves (labeled via the mic tracks; `voiceid.py enroll-mix`, 4 episodes: 439, 442, 444, 445)
  scored, on held-out episode 446: 81.4% of segments, 90.3% of airtime. By segment length: >4 s 96%, 2-4 s 81%, 1-2 s 62%.
  Better than raw-track profiles (62%) but not reliable for quick back-and-forth. Not used for any published transcript yet.
- Word-level mic labeling was worse than sentence-level (timing is only good to a fraction of a second), so `transcribe.py --tracks` labels per sentence.
- Whisper loops on laughter/outro ("Ha ha ha." repeated); `transcribe.py` drops runaway repeats.

- `transcribe.py --profiles ~/.nestalgia-models/profiles.npz` names speakers by voice when there are no mic tracks (sentence-level; the opening
  "I'm Mike / I'm Sean / I'm Joe" is labeled "Hosts"). Profiles come from 8 episodes (438, 439, 442-446, 450). First run: episode 400 (85 min, about 5 minutes).

- `add_voices.py` (double-click `Add Voices.command`) adds episodes with mic tracks to the voice profiles and re-tests leave-one-episode-out.
  Test with 447 and 448 (two-host episodes): airtime accuracy 88.5% before vs 88.7% after, so adding single episodes shows diminishing returns.
  Accuracy is limited more by short interjections than by sample count. On two-host episodes errors include naming the absent third host.

## Published so far

- `transcripts/446-touchdown-fever.md` / `.vtt`, speakers named from the mic tracks.

## Next steps

1. Decide what to do for the ~420 mixdown-only episodes: plain transcripts (no names), voice-ID labels with a caveat, or more enrollment episodes (more training data, add Sam).
   Ideas to raise accuracy: enroll from more episodes (the tracks exist for ~17 more), smooth labels across neighbouring segments, only label segments longer than ~2 s.
2. Run the multitrack path (`--tracks`) for the other episodes that have mic tracks (NES 438-454, NB 053-055, SNES 002, S06).
3. Bulk run. Finished MP3s for episodes 286-454 are in `iCloud/10_NEStalgia/Mixes`; earlier audio comes from the RSS feed (`https://anchor.fm/s/5808ab8/podcast/rss`). Whisper takes about 75 seconds per 25-minute episode.
4. Link transcripts from `episodes/README.md`.
