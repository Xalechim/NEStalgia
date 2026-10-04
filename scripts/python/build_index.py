#!/usr/bin/env python3
"""Rebuild episodes/README.md from the files in episodes/ and transcripts/.

Needs data/episodes.json (run build_episode_data.py first) to know which
episodes are already in the public feed; the rest are marked (unreleased).
"""
import glob
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EP = REPO / "episodes"


def header(path):
    return Path(path).open().readline()[2:].strip()


def main():
    data = json.loads((REPO / "data/episodes.json").read_text())
    released = {r["number"] for r in data if r["type"] == "episode"}
    transcripts = {Path(f).name.split("-")[0]: Path(f).name for f in glob.glob(str(REPO / "transcripts/[0-9]*.md"))}

    rows = []
    for f in sorted(EP.glob("[0-9]*.md")):
        num, title = header(f).split(" - ", 1)
        kind = "outline" if f.name.endswith("-outline.md") else "early notes" if f.name.endswith("-early-notes.md") else "notes"
        rows.append((num, title, f.name, kind))
    sections = {k: [(header(f), f.relative_to(EP).as_posix()) for f in sorted(EP.glob(g))]
                for k, g in (("sp", "specials/*.md"), ("by", "bytes/*.md"), ("sn", "snes/*.md"))}

    # One table row per episode number; extra files for the same number join the same row.
    table, order = {}, []
    for num, title, name, kind in rows:
        if num not in table:
            table[num] = [title, []]
            order.append(num)
        table[num][1].append(f"[{kind}]({name})")
    # Episodes that have a transcript but no show notes yet still get a row (title from the feed data).
    feed_titles = {f"{r['number']:03d}": r["title"] for r in data if r["type"] == "episode" and r["number"] is not None}
    for num in transcripts:
        if num not in table and num in feed_titles:
            table[num] = [feed_titles[num], []]
            order.append(num)
    order.sort(key=int)
    lines = []
    for num in order:
        title, links = table[num]
        if num in transcripts:
            links.append(f"[transcript](../transcripts/{transcripts[num]})")
        flag = "" if int(num) in released else " *(unreleased)*"
        lines.append(f"| {num} | {title.replace('|', '/')}{flag} | {', '.join(links)} |")

    out = ("# Episode notes\n\nShow notes and outlines written for the podcast. Episode numbers come from the podcast feed; "
           "episodes not yet in the feed are marked *(unreleased)*.\n\n## Main episodes\n\n| # | Game | Notes |\n| --- | --- | --- |\n"
           + "\n".join(lines)
           + "\n\n## Specials\n\n" + "\n".join(f"- [{t}]({f})" for t, f in sections["sp"])
           + "\n\n## Nestalgia Bytes (Famicom / Japan-only)\n\n" + "\n".join(f"- [{t}]({f})" for t, f in sections["by"])
           + "\n\n## SNEStalgia\n\n" + "\n".join(f"- [{t}]({f})" for t, f in sections["sn"]) + "\n")
    (EP / "README.md").write_text(out)
    print(f"index: {len(order)} episodes, {len(transcripts)} transcripts linked")


if __name__ == "__main__":
    main()
