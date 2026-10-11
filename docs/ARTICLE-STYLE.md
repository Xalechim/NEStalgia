# Article style guide

Every article on the site is built from the same few parts, so a new article looks like it belongs the moment it is added. These rules are enforced by the build (`scripts/python/build_site.py`, the "article system" section), not by hand, so most of them need no work from the writer.

## Every article has

1. **A hero block** under the title: a cover picture (when the article has a good one), a one-line summary, the reading time, and a "Jump to" list of its sections. The summary comes from `summary` in `site-src/seo.json` (or the article's excerpt). A cover picture is used automatically when it is at least 400 pixels wide; `hero_image` picks one by file name, and `"hero_image": false` turns it off.
2. **The body**, in one of four shapes (below).
3. **Related episodes**: cards for the episodes the article covers (from `ranks` and `episode_guides`), or the genre/year list set in `related`.
4. **More articles**: the next newer and next older article.
5. **A listen row**: Apple Podcasts, Spotify and Patreon.

## The four shapes

| Shape | For | `layout` in seo.json |
| --- | --- | --- |
| Countdown / ranking | Numbered games, each with its episode cover, verdict chips and a write-up | `countdown` |
| Guide / how-to | An intro, numbered tips as cards, then recommended games | `countdown` with `tip_cards: true` |
| Analysis / data | Sections that each make a point (a developer, a game, a hack) | `cards` |
| Roundup / catalog | A series of similar items, one card each | `cards` |

`cards` options: `card_level` (`h2` or `h3`: which heading starts a card; the other headings become section labels), `award_titles` (a heading like "Most Games: Konami" becomes the title "Konami" with a gold award chip), `prefix_titles` (the same, with a plain chip, for "Duck Hunt: Moon Walk"), `developer_links` (adds an "Every X episode" chip), `numbered_cards`.

## Headings

- **Section label**: the dark label bar (an `h2`), such as "The top 10".
- **Card title**: the dark header of a card.
- **Sub-heading**: a small bold run-in inside a card's text. Nothing deeper.

## Pictures

- Every picture is one framed figure with a caption (the picture's description). No bare, unframed images in the text.
- Two or more pictures in one place become a **carousel** (swipe, arrows, dots, a counter). One picture is a single figure.
- Pixel-art screenshots keep their sharp edges (`"px": true` in seo.json, or `class="px"`).
- Screenshots come from the libretro thumbnails, which are free to reuse; MobyGames blocks downloads.

## Callouts

Only two: **stat tiles** for numbers ("the year in numbers") and the **note box** (the red-tab box) for an aside, a formula or a set of rules. No other quote or callout styles.

## Links to episodes

- A game card has a "Hear our episode" button and verdict, genre and developer chips.
- In running text, the first mention of a game that has an episode links to it automatically (names of seven or more characters, capitalized as the episode title).
- Linking old pages: use `{BASE}` in article HTML; old Squarespace addresses are rewritten by the build.

## Adding an article

1. Add it to `site-src/migrated/articles.json` (`path`, `slug`, `title`, `date`, `body` as HTML).
2. Pick its shape and options under `articles` in `site-src/seo.json`, with a `title`, a `description`, a `summary`, and `ranks` or `related` if it covers episodes.
3. Add `episode_guides` entries to link back to it from the episode pages.
4. Build and check the page: `python3 scripts/python/build_site.py`, then `python3 -m http.server --directory site`.
