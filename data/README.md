# Episode data

One record for every item in the podcast feed (459 as of the last build), newest first.

- `episodes.json`: full records
- `episodes.csv`: the same data for spreadsheets (the `notes` column joins several files with `;`)

Rebuild both from the live feed any time (it also re-checks which notes, transcripts and art exist in the repo):

```bash
python3 scripts/python/build_episode_data.py
```

## Fields

| Field | Meaning |
| --- | --- |
| `type` | `episode`, `bytes` (Nestalgia Bytes), `special` (Best of year, etc.) or `other` |
| `number` | Episode number from the feed title, or empty for items without one |
| `title` | Title without the number |
| `feed_title` | Title exactly as it appears in the feed |
| `published` | Publish date (YYYY-MM-DD) |
| `duration_seconds` | Length in seconds |
| `description` | Feed description as plain text |
| `audio_url` | Link to the episode audio on the host (audio is not stored in this repo) |
| `episode_page` | The episode's page on the host |
| `art` | Path to the cover art in this repo |
| `notes` | Show notes and outlines in this repo (a list, can be empty) |
| `transcript` | Transcript in this repo, if one exists |
| `guid` | The feed's unique ID for the episode |

Episodes that aren't in the public feed yet aren't in this file.

## Episode links

`data/links/NNN-game-name.json` holds the links shown on an episode's Links tab (one file per episode that has a transcript). Made by
`scripts/python/make_links.py`; safe to edit by hand.

`bytes-info.json` lists the NEStalgia Bytes episodes (Patreon-only) shown on the website: `{number: {title, published, patreon_url}}`, read from
the episode spreadsheet by `scripts/python/bytes_info.py`. `bytes-art-sources.json` records where each Bytes cover came from.

## Getting an episode ready before it comes out

Everything about an episode that isn't in the podcast feed yet is ignored by the website until it is, so these files can be prepared days ahead.
Where each recent and upcoming episode stands: `python3 scripts/python/pipeline_status.py --board`.

- `mix-fingerprints/NNN.json` (about 37 KB each): the loudness pattern of the episode's final mix, saved when its transcript is made
  (`audio_offsets.py --fingerprint`). When the episode appears in the feed, GitHub lines it up against the host's audio to measure how far the host's
  audio is shifted (ads are inserted at the start), which is what makes the clickable timestamps in the transcript start in the right place.
  `mix-fingerprints/_tried.json` counts failed measurements so GitHub gives up after six instead of downloading the audio on every update.
- `audio-offsets.json`: the measured shifts, `{"446": [[0, 60.2]]}` meaning "from mix time 0 s on, the host's audio is 60.2 s later".
  `audio-offsets-todo.json` lists episodes where the shift changes mid-episode: only the start shift is known and the Mac should do a full alignment.
- `up-next-art/NNN.jpg`: the cover for an upcoming episode, copied from the iCloud working folder by the Mac (`next_episode.stage_upcoming_art`) so
  GitHub can use your own art for the Up next box when it moves on to that episode.
- `next-episode.json` and `next-episode.jpg`: what the Up next box on the home page shows (the first numbered episode in the spreadsheet after the newest
  published one, with its Wikipedia intro). It moves on by itself when the feed catches up.
