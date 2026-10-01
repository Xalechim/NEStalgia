# Putting the NES Zapper article on Squarespace

## What's in this folder

- **nes-zapper-article.html** — the whole article: tabbed layout, styling, all five sections. Double-click it to preview in your browser right now (keep it next to the `images` folder).
- **images/** — all 44 images, already resized and compressed for web (4.7 MB total, down from 18 MB).
- This file.

## What you need

A Squarespace plan that includes **Code Blocks** — that's Business or higher on the old plan names, **Core** or higher on the current ones. The tabs are pure CSS (no JavaScript required), so nothing breaks if Squarespace strips scripts. There is one small optional script at the bottom that snaps you back to the top of the article when you switch tabs from deep in a long section; if your plan won't run it, the tabs still work, you just stay scrolled down.

## Step 1 — Upload the images

Squarespace can't read files off your computer, so the images have to live on their CDN first.

1. In Squarespace, go to **Website → Pages**, open (or create) the blog post or page for the article.
2. Easiest route: add a temporary **Gallery block** (or Image blocks) and upload everything in the `images` folder to it. You'll delete the block later — uploading is just how you get the files onto Squarespace's CDN.
3. For each image: click it → right-click the displayed image → **Copy Image Address**. You'll get a URL like
   `https://images.squarespace-cdn.com/content/v1/…/hw-nes-zapper-gray.jpg`
4. Keep a scratch list of filename → URL as you go. The filenames in the HTML match the files exactly, so there's no guessing about which is which.

(Alternative if you have it: **Settings → Files** / the asset manager lets you upload files and copy their links directly, which skips the temporary gallery.)

## Step 2 — Paste the article

1. Open `nes-zapper-article.html` in a text editor (TextEdit works — File → Open, and in the Open dialog check "Display HTML files as HTML code", or just use VS Code).
2. Copy everything between `<!-- COPY-START -->` and `<!-- COPY-END -->`.
3. In your Squarespace page, add a **Code** block, set it to **HTML**, and paste.

## Step 3 — Point the images at Squarespace

In the pasted code, every image reference looks like `images/hw-nes-zapper-gray.jpg`. Replace each one with its Squarespace CDN URL from Step 1. Find-and-replace makes this quick: search for `images/` and work through the 40-odd hits. (Do this in your text editor before pasting if that's more comfortable — same result.)

Save, and delete the temporary gallery block if you used one (the uploaded files stay on the CDN).

## Step 4 — Check it

- Click all five tabs.
- Look at it on your phone — the layout stacks to a single column under 600px wide.
- The article carries its own dark background and fonts, so it should look the same regardless of your site theme. If your theme's CSS bleeds in anywhere, tell me what looks off and I'll tighten the styles.

## Notes

- The retro heading font is Google's "Press Start 2P," loaded by the `<link>` tag on the first line of the paste. If you'd rather self-host or skip it, delete that line — everything falls back to a monospace font.
- Tab labels and colors are all in the `<style>` block up top: the orange is `--orange:#f47b20` (Zapper orange), the red is `--red:#e60012` (NES red). Change them in one place.
- Photo credits are in the footer of the Totals & Sources tab. The Evan-Amos and Wikimedia photos are free to publish. The beforemario and famicomblog photos are credited as their owners ask. Box art and screenshots are fair use for commentary — normal practice for a games-history article, but they're the assets to reconsider if you ever get a takedown request.
