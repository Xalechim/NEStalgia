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

## Published so far

- `transcripts/446-touchdown-fever.md` / `.vtt`, speakers named from the mic tracks.

## Next steps

1. Decide what to do for the ~420 mixdown-only episodes: plain transcripts (no names), voice-ID labels with a caveat, or more enrollment episodes (more training data, add Sam).
   Ideas to raise accuracy: enroll from more episodes (the tracks exist for ~17 more), smooth labels across neighbouring segments, only label segments longer than ~2 s.
2. Run the multitrack path (`--tracks`) for the other episodes that have mic tracks (NES 438-454, NB 053-055, SNES 002, S06).
3. Bulk run. Finished MP3s for episodes 286-454 are in `iCloud/10_NEStalgia/Mixes`; earlier audio comes from the RSS feed (`https://anchor.fm/s/5808ab8/podcast/rss`). Whisper takes about 75 seconds per 25-minute episode.
4. Link transcripts from `episodes/README.md`.
