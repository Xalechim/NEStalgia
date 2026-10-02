# How to make a transcript (no coding)

You only need to do this one thing: **double-click a file**, type an episode number, and wait.

## Before you start (one time)

Make sure the finished episode MP3 is in your iCloud NEStalgia folder, in `Mixes`, named like this:

    NES 401 - WWF Wrestlemania Challenge.mp3

(That's how you already name them.)

## The easy way: do everything for a new episode in one go

When a new episode comes out, **double-click `Check for New Episodes.command`** (in the same `scripts` folder). It:

1. checks your podcast feed for new episodes,
2. adds the episode's information and cover art to the repo,
3. makes the transcript from your final mix in `Mixes` (the file must be named like `NES 449 - Game Name.mp3`),
4. measures the audio shift so the clickable timestamps land correctly,
5. uploads everything to GitHub, and
6. waits for the website to rebuild and tells you whether the new page is live.

Things to know:
- **The first time you run it**, it marks the episodes already in the feed as handled so it never redoes your back catalog. Any recent
  episode that still has no transcript (like one that came out this week) is treated as new.
- **If the final mix isn't in `Mixes` yet**, the episode goes on a waiting list and is picked up automatically the next time you run it.
- **It only commits its own files**, so anything else you have in progress is left alone. Safe to run again: if nothing is new it says so.
- **To preview without changing anything**, run `python3 scripts/new_episodes.py --dry-run` in Terminal.
- **To make it run by itself every Friday** (Fridays 9:00 and 14:00, Saturdays 10:00, whenever your Mac is awake), run
  `python3 scripts/new_episodes.py --install-schedule` once. A notification appears when it finishes. Turn it off with `--uninstall-schedule`.
  The log is `~/Library/Logs/nestalgia-new-episodes.log`.
- It does **not** write show notes, and it only finds web links if you ask (`--links`, needs an Anthropic key; otherwise use `/make-links`).

## Making a transcript for one specific episode

1. Open **Finder**.
2. Go to your home folder, then **Developer**, then **nestalgia**, then **scripts**.
   - Shortcut: in Finder press **Shift + Command + G**, paste `~/Developer/nestalgia/scripts`, press Enter.
3. Double-click **Transcribe Episode.command**.
   - A black window (Terminal) opens. This is normal.
   - The first time, macOS may say it can't verify the file. Right-click the file, choose **Open**, then **Open** again. You only do this once.
4. It asks which episode(s). Type the number, like `401`, and press **Enter**. To do several at once, type:
   - a list: `401 402 405`
   - a range: `401-410`
   - or a mix: `401-403 408`
   They run one after another, and it asks about publishing **once** at the end, for all of them.
5. It tells you which episode it found. Then it works for a minute or two (about 1.5 minutes for a 30-minute episode, per episode). Leave the window open.
6. When everything is done, it asks: **Publish them to GitHub now? (y/n)**
   - Type `y` and press Enter to put it on the website.
   - Type `n` if you want to read it first. It's saved on your Mac either way.
7. Press **Enter** to close the window.

Your transcript is saved in the `transcripts` folder as a normal text file you can open and read.

## How the transcript is laid out

- The text is broken into paragraphs at natural pauses and changes of subject, and **every paragraph starts with its timestamp**, like `[04:20]`.
- **There are no speaker names.** Automatic speaker labels weren't accurate enough to publish, so they were removed.
- A matching `.vtt` file (subtitles, one sentence at a time) is saved next to it.

## If something goes wrong

- **"I couldn't find an MP3 for episode …"** (in a batch it just skips that one and keeps going): the file isn't in `Mixes`, or the name doesn't start with `NES 401 - `.
- **Nothing happens when you double-click**: right-click it, choose **Open With**, then **Terminal**.
- **Anything else**: copy what the black window says and send it to Claude.

## What it does NOT do

- It doesn't work for episodes whose MP3 isn't on your Mac yet.
- It doesn't edit the transcript. If a name or word is wrong, open the `.md` file in `transcripts` and fix it by hand, then publish again.
- Bytes episodes (`NB …`) and SNEStalgia aren't supported yet. Ask Claude to add them.

## Clickable timestamps on the website

On the website, every timestamp in the transcript (and in the Links tab) is clickable: it starts the episode player at that point.
A small player floats at the bottom of the screen when you scroll away from the main one, and the paragraph being played is highlighted.

The podcast host sometimes adds an ad at the start of the audio it serves, which shifts everything later by about a minute. The transcript
tool measures that shift for each new episode automatically (it needs internet, and the episode must already be in the public feed)
and saves it in `data/audio-offsets.json`. To measure episodes yourself: `python3 scripts/audio_offsets.py 450` or `--all`.
If a click ever lands a bit off (the host changed its ad), use the **−5s / +5s** buttons above the transcript. Your adjustment is
remembered in your browser for that episode.

## Removing the speaker names from older transcripts (one time)

Transcripts made before this change still show `**Mike** [00:22]:` speaker lines. To convert all of them at once:

1. In Finder, open the `scripts` folder (Shift + Command + G, paste `~/Developer/nestalgia/scripts`).
2. Double-click **Strip Speakers.command**. It first shows a preview and changes nothing.
3. Type `y` to convert. It keeps every word and every timestamp, regroups the text into paragraphs, and skips any transcript that is
   already done, so it is safe to run again. It works offline.
4. Type `y` to publish when it asks (that step needs internet). The website updates in a few minutes.

Your old versions are kept in git history if you ever want them back.

## Updating the patron list on the homepage

The names under "Special thanks to our patrons!" come from one text file: `site-src/patrons.txt` (one name per line).
Open it, add or remove names, save, then publish:

    cd ~/Developer/nestalgia
    git add site-src/patrons.txt && git commit -m "Update patron list" && git push

The website rebuilds itself in a few minutes.

## Finding the web links for an episode (the Links tab)

Each episode that has a transcript can get a **Links** tab on its web page: a list of everything mentioned on the show (games, people,
companies, teams, movies, terms) with a link for each. Claude reads the transcript, searches the web, and the tool double-checks every
link before keeping it. Cost: a few cents to a few tens of cents per episode.

### One-time setup: your Anthropic API key

1. Go to **console.anthropic.com**, sign in, add a payment method under Billing, then open **API Keys** and click **Create Key**.
   Copy the key (it starts with `sk-ant-`). You only see it once.
2. Open **Terminal** and paste this whole line, then press Enter. It saves the key from your clipboard to a private file on your Mac
   (never into the GitHub repo):

       mkdir -p ~/.config/nestalgia && pbpaste > ~/.config/nestalgia/anthropic_key && chmod 600 ~/.config/nestalgia/anthropic_key

   Never paste the key into a chat, an email, or a file inside the `nestalgia` folder.

### Each time

1. Make the transcript first (above). If the key is set up, the transcript tool will offer to find the links right after.
2. Or double-click **Make Links.command** in the `scripts` folder, type an episode number like `446` (or `401-410`, or `ALL` for every
   transcript that has no links yet), and answer `y` when it offers to publish.
3. Wait a few minutes. The website updates itself shortly after you publish.

### No API key? Use Claude Code instead (nothing to set up)

You can have Claude Code do the same job, using your normal Claude plan:

1. Open the **nestalgia** folder in Claude Code (the folder is `~/Developer/nestalgia`).
2. Type `/make-links 450` (or `/make-links 401-410`).
3. Claude reads the transcript, searches the web, and runs every link through the same checker. It shows you what it found and asks
   before publishing.

It takes a few minutes per episode and isn't a double-click, but the quality is the same as the API version.

### Good to know

- It skips episodes that already have links (so it never overwrites your edits). To redo one, run it from Terminal with `--force`.
- Each episode's links are saved in `data/links/NNN.json`, a plain text file. You can open it and delete or fix an entry by hand,
  then publish.
- A link that can't be verified is dropped rather than shown, so some things may be missing on purpose.
- Episode 446's links are a hand-made sample so you can see how the tab looks. Run it with `--force` once your key is set up to
  replace them with Claude's own.
