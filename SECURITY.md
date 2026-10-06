# Security Policy

NEStalgia is a podcast, and this repository is the show's website and archive: show notes, transcripts, reviews, and the scripts and GitHub Actions workflows that build and publish [nestalgiacast.com](https://nestalgiacast.com). It is run by volunteers, so there is no 24/7 security team, but we take reports seriously and will fix real problems quickly.

## Reporting a vulnerability

**Please do not open a public issue, pull request or discussion for a security problem.** Use one of these instead:

1. **Private vulnerability reporting on GitHub (preferred).** Go to the [Security tab](https://github.com/Xalechim/NEStalgia/security) of this repository and choose **Report a vulnerability**. Only the maintainers can see what you send.
2. **The website's contact form.** If you can't use GitHub, send a short note at [nestalgiacast.com/contact](https://nestalgiacast.com/contact/) saying you have a security report and how to reach you. Don't put the details in that message. We will reply and arrange a private channel.

Helpful things to include:

- What the problem is and where it is (a URL, file path or workflow name).
- Steps to reproduce it, and what you expected to happen versus what did.
- What you think someone could do with it.
- Whether you plan to publish your findings, and when.

If you find a leaked secret (a webhook URL, token or password), tell us where it is, but don't repeat the value in your report and please don't use it.

## What to expect

- We aim to acknowledge your report within **7 days**.
- We aim to confirm whether it is a real issue, and tell you our plan, within **14 days**.
- We will keep you posted until it is fixed, credit you in the fix if you want that, and let you know when it is safe to talk about it publicly.
- Anything involving an exposed secret gets handled first: we rotate the secret, then clean up.

These are goals, not guarantees, since this is a volunteer project. If you haven't heard back after a week, please nudge us through the other channel above.

## Supported versions

There are no versioned releases. The only supported version is the code on the `main` branch and the site published from it at [nestalgiacast.com](https://nestalgiacast.com). Fixes go to `main` and are deployed automatically.

## Scope

In scope:

- The website at nestalgiacast.com and its generated pages, including the JavaScript in `site-src/` (search, filters, audio player, theme toggle, contact form wiring) and anything that could be used for cross-site scripting, injection or unwanted redirects.
- The build and automation code: `scripts/`, and the workflows in `.github/workflows/` (deploy, feed updates and the Discord new-episode announcement).
- Secrets, tokens or credentials committed to the repository or exposed in its history, workflow logs or published pages.
- Workflow permissions, or dependencies and third-party actions we use, that could let someone tamper with the published site or the repository.

Out of scope:

- Mistakes in episode details, transcripts, reviews or show notes. Please use the contact form or open a normal issue for those.
- Problems in services we don't run: GitHub Pages, GitHub itself, Patreon, Anchor and the podcast apps, Discord, FormSubmit (the contact form's mail service), GoatCounter (our analytics) and similar. Report those to the service.
- Denial-of-service or load testing, spam, or flooding the contact form.
- Social engineering of the maintainers or the show's guests, and physical attacks.
- Automated scanner output with no demonstrated impact, or missing hardening headers on a static site with no accounts and no sensitive data.

## Please be a good neighbor

- Test only against your own copy where you can. The live site is static, so there is rarely a reason to touch it hard.
- Don't access, change or delete data that isn't yours, and stop as soon as you've shown the issue exists.
- Give us a reasonable chance to fix a problem before you publish it.

If you follow these guidelines when you look for and report a problem, we will treat it as good-faith research and won't take action against you. We don't offer a paid bug bounty, but we are happy to say thank you and credit you.

## What's here, and what isn't

The repository is public by design: episode show notes, transcripts, reviews, cover art and the build scripts are all meant to be read. There are no user accounts or payment details on the site. The few secrets the automation needs, such as the Discord webhook for new-episode posts, are kept in GitHub Actions secrets and are never committed to the repository.
