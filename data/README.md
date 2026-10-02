# Episode data

One record for every item in the podcast feed (459 as of the last build), newest first.

- `episodes.json`: full records
- `episodes.csv`: the same data for spreadsheets (the `notes` column joins several files with `;`)

Rebuild both from the live feed any time (it also re-checks which notes, transcripts and art exist in the repo):

```bash
python3 scripts/build_episode_data.py
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
`scripts/make_links.py`; safe to edit by hand.
