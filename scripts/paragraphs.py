#!/usr/bin/env python3
"""Turn a transcript's sentence cues into readable paragraphs, and read/write the transcript file formats.

No speaker labels anywhere. A paragraph break falls at a "thought break":
  1. a clear pause (>= HARD_PAUSE seconds), or
  2. inside a stretch that has run too long (> MAX_CHARS), at the best spot: a longer pause and a change of vocabulary
     (the conversation moving to a different subject) score highest;
and pieces that came out too short get folded into a neighbour.

Used by transcribe.py (new transcripts) and strip_speakers.py (converting old ones). Pure Python, works offline.
"""
import re

HARD_PAUSE = 1.6   # seconds of silence that always starts a new paragraph
MAX_CHARS = 760    # a paragraph longer than this is split at its best internal break
MIN_CHARS = 170    # a piece shorter than this is merged into a neighbour (unless a long pause separates them)
LONG_PAUSE = 3.0   # a pause this long is never merged away
WINDOW = 3         # cues on each side when comparing vocabulary

STOP = set("""a an the and or but so if then than that this these those it its it's i i'm i've i'll you you're we we're they they're he she
to of in on at for with as by from is are was were be been being do does did have has had not no yes yeah okay oh um uh like just
really very kind sort mean know think guess right well what who which when where why how there here can could would should will
about into over out up down all some any more most my your our their me him her them us one two get got going go gonna""".split())

TS = r"\d+:\d\d(?::\d\d)?"


def fmt_ts(seconds):
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"


def parse_ts(text):
    parts = [int(p) for p in text.split(":")]
    secs = 0
    for p in parts:
        secs = secs * 60 + p
    return secs


def words(text):
    return {w for w in re.findall(r"[a-z0-9']+", text.lower()) if w not in STOP and len(w) > 2}


def similarity(a, b):
    """Overlap of the meaningful words in two stretches of text (0 = nothing in common, 1 = same)."""
    wa, wb = words(a), words(b)
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / (len(wa | wb) or 1)


def split_long(cues, lo, hi):
    """Recursively split cues[lo:hi] while the text is too long; returns a list of (lo, hi) ranges."""
    text_len = sum(len(c["text"]) + 1 for c in cues[lo:hi])
    if text_len <= MAX_CHARS or hi - lo < 2:
        return [(lo, hi)]
    best, best_score = None, -1.0
    run = 0
    for i in range(lo + 1, hi):
        run += len(cues[i - 1]["text"]) + 1
        left, right = run, text_len - run
        if left < MIN_CHARS or right < MIN_CHARS:
            continue
        gap = max(0.0, cues[i]["start"] - cues[i - 1]["end"])
        before = " ".join(c["text"] for c in cues[max(lo, i - WINDOW) : i])
        after = " ".join(c["text"] for c in cues[i : min(hi, i + WINDOW)])
        shift = 1.0 - similarity(before, after)          # more different = more likely a new subject
        balance = 1.0 - abs(left - right) / text_len     # prefer splitting nearer the middle
        score = min(gap, 2.5) * 1.0 + shift * 1.2 + balance * 0.6
        if score > best_score:
            best, best_score = i, score
    if best is None:
        return [(lo, hi)]
    return split_long(cues, lo, best) + split_long(cues, best, hi)


def group(cues):
    """cues: list of {'start','end','text'} in order. Returns list of {'start','end','text'} paragraphs."""
    cues = [c for c in cues if c["text"].strip()]
    if not cues:
        return []
    ranges, lo = [], 0
    for i in range(1, len(cues)):
        if cues[i]["start"] - cues[i - 1]["end"] >= HARD_PAUSE:
            ranges.append((lo, i))
            lo = i
    ranges.append((lo, len(cues)))
    split = []
    for a, b in ranges:
        split += split_long(cues, a, b)

    def size(r):
        return sum(len(c["text"]) + 1 for c in cues[r[0] : r[1]])

    # fold tiny pieces into the previous one (or the next, for the first piece), unless a long pause separates them
    merged = []
    for r in split:
        if merged and size(r) < MIN_CHARS and cues[r[0]]["start"] - cues[merged[-1][1] - 1]["end"] < LONG_PAUSE \
                and size(merged[-1]) + size(r) <= MAX_CHARS * 1.4:
            merged[-1] = (merged[-1][0], r[1])
        else:
            merged.append(r)
    if len(merged) > 1 and size(merged[0]) < MIN_CHARS and cues[merged[1][0]]["start"] - cues[merged[0][1] - 1]["end"] < LONG_PAUSE:
        merged[1] = (merged[0][0], merged[1][1])
        merged.pop(0)
    return [{"start": cues[a]["start"], "end": cues[b - 1]["end"], "text": " ".join(c["text"].strip() for c in cues[a:b])} for a, b in merged]


# ----------------------------------------------------------------------------- file formats

NOTE = "_Auto-generated transcript. Each paragraph starts with its timestamp. Speakers are not identified._"


def to_markdown(title, paras):
    head = f"# {title}\n\n" if title else ""
    return head + NOTE + "\n\n" + "\n\n".join(f"[{fmt_ts(p['start'])}] {p['text']}" for p in paras) + "\n"


def vtt_time(t):
    ms = int(round(t * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def to_vtt(cues):
    out = ["WEBVTT", ""]
    for c in cues:
        out += [f"{vtt_time(c['start'])} --> {vtt_time(c['end'])}", c["text"].strip(), ""]
    return "\n".join(out)


def read_vtt(text):
    """Cues from a .vtt (speaker tags like <v Mike> are dropped)."""
    cues, cur = [], None
    for ln in text.splitlines():
        m = re.match(r"(\d+):(\d+):(\d+)\.(\d+) --> (\d+):(\d+):(\d+)\.(\d+)", ln)
        if m:
            g = list(map(int, m.groups()))
            cur = {"start": g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000, "end": g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000, "text": ""}
            cues.append(cur)
        elif cur is not None and ln.strip() and not ln.startswith("WEBVTT"):
            cur["text"] = (cur["text"] + " " + re.sub(r"<v [^>]*>", "", ln).replace("</v>", "")).strip()
    return cues


OLD_TURN = re.compile(rf"^\*\*([^*]+)\*\* \[({TS})\]: (.*)$")
NEW_PARA = re.compile(rf"^\[({TS})\] (.*)$")


def is_old_format(md_text):
    return any(OLD_TURN.match(l) for l in md_text.splitlines())


def read_old_markdown(md_text):
    """Old speaker-turn markdown -> (title, [(start_seconds, text)]). Used only when there is no .vtt to take timing from."""
    title, turns = "", []
    for ln in md_text.splitlines():
        if ln.startswith("# ") and not title:
            title = ln[2:].strip()
        m = OLD_TURN.match(ln)
        if m:
            turns.append((parse_ts(m.group(2)), m.group(3)))
    return title, turns
