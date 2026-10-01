# How to make a transcript (no coding)

You only need to do this one thing: **double-click a file**, type an episode number, and wait.

## Before you start (one time)

Make sure the finished episode MP3 is in your iCloud NEStalgia folder, in `Mixes`, named like this:

    NES 401 - WWF Wrestlemania Challenge.mp3

(That's how you already name them.)

## Steps

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
5. It tells you which episode it found and how it will label speakers. Then it works for a few minutes (about 3 minutes for a 30-minute episode, about 5 for a long one, per episode). Leave the window open.
6. When everything is done, it asks: **Publish them to GitHub now? (y/n)**
   - Type `y` and press Enter to put it on the website.
   - Type `n` if you want to read it first. It's saved on your Mac either way.
7. Press **Enter** to close the window.

Your transcript is saved in the `transcripts` folder as a normal text file you can open and read.

## How it labels who's talking

- If the Audition project for that episode has each host's own microphone recording, it uses those. This is the most accurate.
- If not, it recognizes Mike, Sean and Joe by their voices. This is good but not perfect, and quick replies like "Yeah." can land on the wrong person.
- The "I'm Mike, I'm Sean, and I'm Joe" part is labeled **Hosts**, and Mike gets the first line of the show.

## If something goes wrong

- **"I couldn't find an MP3 for episode …"** (in a batch it just skips that one and keeps going): the file isn't in `Mixes`, or the name doesn't start with `NES 401 - `.
- **Nothing happens when you double-click**: right-click it, choose **Open With**, then **Terminal**.
- **Anything else**: copy what the black window says and send it to Claude.

## What it does NOT do

- It doesn't work for episodes whose MP3 isn't on your Mac yet.
- It doesn't edit the transcript. If a name or word is wrong, open the `.md` file in `transcripts` and fix it by hand, then publish again.
- Bytes episodes (`NB …`) and SNEStalgia aren't supported yet. Ask Claude to add them.

## Teaching it more voices (optional)

1. Open the same `scripts` folder and double-click **Add Voices.command**.
2. Type episode numbers that have each host's own mic recording in Audition Projects, separated by spaces, like `447 448 449`. Then press Enter.
3. Wait a few minutes per episode. It prints a re-test table comparing how well the old voice samples and the new ones name speakers.
4. It asks **Keep the new voice samples? (y/n)**. Type `y` to keep them. Your old samples are backed up as `profiles.backup.npz` in the `.nestalgia-models` folder.

Episodes already added are skipped. It only helps with Mike, Sean and Joe; it can't learn Sam or guests, who have no mic recordings.

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
