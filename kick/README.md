# kick

Changing a file in this folder starts the website's update workflow (`.github/workflows/update-site.yml`) straight away.

GitHub's own scheduler is unreliable (it skips and delays runs), so the Claude "kick" routine runs on Friday mornings, checks
whether the new episode has reached the website, and if not writes the time to `last-kick.txt` and pushes. A push is the one
trigger GitHub never drops. You can do the same by hand: edit `last-kick.txt`, commit, push.
Nothing here is published on the website.
