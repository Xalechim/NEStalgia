#!/usr/bin/env python3
"""Transcribe a NEStalgia episode.

Pipeline: ffmpeg -> 16 kHz mono wav -> mlx-whisper (Apple Silicon) for text and timestamps -> sentences -> paragraphs at
natural thought breaks (see paragraphs.py) -> .md (a timestamp on every paragraph) and .vtt (sentence-level subtitles).
There are no speaker labels: they were tried and weren't reliable enough to publish.

Usage:
  transcribe.py AUDIO --out transcripts/446-touchdown-fever [--title "446 - Touchdown Fever"] [--prompt-file FILE]
                [--cache-dir DIR]

Setup is described in scripts/README.md.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import paragraphs  # noqa: E402

WHISPER_MODEL = "mlx-community/whisper-large-v3-turbo"
DEFAULT_PROMPT = (
    "Glossary: NEStalgia, Famicom, Konami, Capcom, Hudson Soft, Tecmo, Zapper, Power Pad, "
    "Mike, Sean, Joe, Sam."
)
MIN_SENTENCE = 0.8  # seconds; shorter sentences are merged into the next one


def to_wav(src: str, dst: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-ac", "1", "-ar", "16000", dst], check=True)


def runaway(text: str) -> bool:
    """Whisper sometimes loops on music/laughter ("Ha! Ha! Ha! ...")."""
    toks = [t.strip(".,!?").lower() for t in text.split()]
    run = 1
    for x, y in zip(toks, toks[1:]):
        run = run + 1 if x == y else 1
        if run >= 5:
            return True
    return False


def clean_segments(segments):
    """Drop empty, looping, and immediately repeated segments."""
    out, prev = [], None
    for s in segments:
        txt = s["text"].strip()
        if not txt or runaway(txt) or (txt == prev and s["end"] - s["start"] < 2.0):
            continue
        out.append(s)
        prev = txt
    return out


def sentences(segs, min_dur=MIN_SENTENCE):
    """Split Whisper segments into sentences using word timestamps. Returns [{'start','end','text'}]."""
    sents = []
    for s in segs:
        words = s.get("words") or [{"word": " " + s["text"].strip(), "start": s["start"], "end": s["end"]}]
        cur = []
        for w in words:
            cur.append(w)
            if w["word"].strip()[-1:] in ".?!":
                sents.append(cur)
                cur = []
        if cur:
            sents.append(cur)
    merged, carry = [], []
    for sent in sents:  # merge sentences shorter than min_dur into the next one
        sent = carry + sent
        if sent[-1]["end"] - sent[0]["start"] < min_dur:
            carry = sent
        else:
            merged.append(sent)
            carry = []
    if carry:
        if merged:
            merged[-1] += carry
        else:
            merged.append(carry)
    return [{"start": m[0]["start"], "end": m[-1]["end"], "text": "".join(w["word"] for w in m).strip()} for m in merged]


def fix_names(text: str) -> str:
    """Whisper hears the show's name as Nostalgia/Nastalgia."""
    return re.sub(r"welcome to (?:Nostalgia|Nastalgia|Nestalgia)", "welcome to NEStalgia", text)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--out", required=True, help="output path without extension")
    ap.add_argument("--title", default="")
    ap.add_argument("--prompt-file")
    ap.add_argument("--cache-dir", help="reuse/save the raw Whisper result here")
    a = ap.parse_args()

    prompt = Path(a.prompt_file).read_text().strip() if a.prompt_file else DEFAULT_PROMPT
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    cache = Path(a.cache_dir) / (out.name + ".whisper.json") if a.cache_dir else None

    if cache and cache.exists():
        res = json.loads(cache.read_text())
    else:
        import mlx_whisper

        with tempfile.TemporaryDirectory() as td:
            wav = os.path.join(td, "a.wav")
            to_wav(a.audio, wav)
            res = mlx_whisper.transcribe(
                wav,
                path_or_hf_repo=WHISPER_MODEL,
                initial_prompt=prompt,
                word_timestamps=True,
                condition_on_previous_text=True,  # keeps punctuation and capitalization consistent
                verbose=None,
            )
        if cache:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(res, default=float))

    cues = sentences(clean_segments(res["segments"]))
    for c in cues:
        c["text"] = fix_names(c["text"])
    paras = paragraphs.group(cues)
    out.with_suffix(".md").write_text(paragraphs.to_markdown(a.title, paras))
    out.with_suffix(".vtt").write_text(paragraphs.to_vtt(cues))
    minutes = (cues[-1]["end"] / 60) if cues else 0
    print(f"{out.name}: {len(cues)} sentences, {len(paras)} paragraphs, {minutes:.1f} min")


if __name__ == "__main__":
    sys.exit(main())
