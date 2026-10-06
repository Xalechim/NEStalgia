# Contributing to NEStalgia

Thanks for reading along. This repository is the home of the NEStalgia podcast's website and archive, and the easiest way to help is to tell us when something is wrong.

## Suggest a correction

**Open an issue.** A plain, normal issue is all it takes: [open one here](https://github.com/Xalechim/NEStalgia/issues/new). Please include:

- the page or file (a link like `nestalgiacast.com/episodes/...`, or a path like `transcripts/076-mike-tysons-punch-out.md`),
- what is wrong, and what it should say instead,
- a source, if it is a fact (a manual, an interview, a Wikipedia page).

Good things to report: a wrong developer, date or fact in the show notes or a review, a broken link, a typo, or a word in a transcript that was misheard. Transcripts are generated automatically, so mishearings and misspelled names (game titles especially) are expected, and fixes are welcome.

## If you'd like to fix it yourself

Pull requests are welcome for small fixes: typos, transcript wording, links and facts. A few tips:

- Edit the source files, never the `site/` folder. The website is built from this repo and `site/` is not stored in it.
- For a transcript, edit the `.md` file in `transcripts/` and mention the episode number in your pull request. We'll sync the matching `.vtt` subtitle file.
- Keep each pull request small and about one thing. For anything bigger (a new feature, a restructure), open an issue first so we can talk it through.
- If you edit a review, read [`reviews/README.md`](reviews/README.md) first. It's short, and it explains the voice and format.

## Where things live

| Folder | What's in it | Edit by hand? |
| --- | --- | --- |
| `episodes/` | Show notes, one file per episode | Yes |
| `transcripts/` | Auto-generated transcripts (`.md` and `.vtt`) | Yes, for corrections |
| `reviews/` | The written Review shown on episode pages | Yes |
| `data/` | The episode list, verdicts and other generated data | No, it's refreshed automatically |
| `site-src/` | The website's pages, styles, scripts and articles | Yes, with care |
| `scripts/` | The tools that build and update the site | Yes, with care |
| `assets/` | Episode art and branding | Yes |

A few things you can't change from here:

- **Verdicts, genres, developers and release dates** come from the show's own spreadsheet and refresh into `data/` every few hours, so a hand edit to those files gets overwritten. The Essential, Play it and Skip it verdicts are the hosts' calls. If you disagree with one, we'd love to hear why, but use the [contact page](https://nestalgiacast.com/contact/). See [How the show works](https://nestalgiacast.com/articles/how-the-show-works/) for how the votes work.
- **Audio** isn't stored in this repo.

For a map of how the pieces fit together, see [`docs/HANDBOOK.md`](docs/HANDBOOK.md).

## Security problems

Please don't open a public issue for a security problem. Follow [`SECURITY.md`](SECURITY.md) instead.

## License

The content here is licensed under [Creative Commons Attribution-NonCommercial 4.0](LICENSE). By contributing, you agree that your contribution is released under the same license.

## Be kind

This is a fan project run by volunteers, and the people who read it love old games. Be respectful, keep disagreements about the games friendly, and assume good intentions.
