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

## Next steps

1. Enroll voices from the mixdown segments themselves, labeled via the tracks (`voiceid.py enroll-mix`, written but not yet run to completion), then re-test on held-out episode 446. Target: well above 90% before using it on mixdown-only episodes.
2. If that works, wire `--profiles` into `transcribe.py`, label unmatched voices "Unknown", and add Sam from early episodes if wanted.
3. Fall back to plain transcripts for anything that cannot be labeled reliably.
4. Bulk run: episodes 286-454 have finished MP3s in `iCloud/10_NEStalgia/Mixes`; earlier ones need the audio from the RSS feed (`https://anchor.fm/s/5808ab8/podcast/rss`).
   Estimated about 30 minutes of audio per 1 minute of compute, so the full catalog is hours, not days.
5. Output goes in `transcripts/NNN-name.md` and `.vtt`. Link each from `episodes/README.md`.
