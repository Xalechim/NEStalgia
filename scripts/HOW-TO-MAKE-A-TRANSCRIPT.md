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
4. It asks: **Which episode number?** Type the number, like `401`, and press **Enter**.
5. It tells you which episode it found and how it will label speakers. Then it works for a few minutes (about 3 minutes for a 30-minute episode, about 5 for a long one). Leave the window open.
6. When it says **Done!**, it asks: **Publish it to GitHub now? (y/n)**
   - Type `y` and press Enter to put it on the website.
   - Type `n` if you want to read it first. It's saved on your Mac either way.
7. Press **Enter** to close the window.

Your transcript is saved in the `transcripts` folder as a normal text file you can open and read.

## How it labels who's talking

- If the Audition project for that episode has each host's own microphone recording, it uses those. This is the most accurate.
- If not, it recognizes Mike, Sean and Joe by their voices. This is good but not perfect, and quick replies like "Yeah." can land on the wrong person.
- The "I'm Mike, I'm Sean, and I'm Joe" part is labeled **Hosts**, and Mike gets the first line of the show.

## If something goes wrong

- **"I couldn't find an MP3 for episode …"**: the file isn't in `Mixes`, or the name doesn't start with `NES 401 - `.
- **Nothing happens when you double-click**: right-click it, choose **Open With**, then **Terminal**.
- **Anything else**: copy what the black window says and send it to Claude.

## What it does NOT do

- It doesn't work for episodes whose MP3 isn't on your Mac yet.
- It doesn't edit the transcript. If a name or word is wrong, open the `.md` file in `transcripts` and fix it by hand, then publish again.
- Bytes episodes (`NB …`) and SNEStalgia aren't supported yet. Ask Claude to add them.
