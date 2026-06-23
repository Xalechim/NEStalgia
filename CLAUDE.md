# Working notes for Claude

## Catch-up briefing routine — standing rules

When generating the catch-up / morning briefing (Outlook schedule + emails, Slack,
action items, Forge Airtable), follow these rules:

### Reconcile against replies before flagging anything as "needs a reply/approval"
Do NOT flag an email or message as needing action without first checking whether the
user has already responded.

- **Email:** before flagging an Inbox thread, search **Sent Items** for a reply on the
  same conversation (match by subject, e.g. `Re: <subject>`). The Inbox alone only shows
  incoming mail, so an item can look "open" when the user already approved/replied.
  If a reply exists in Sent, drop the item.
- **Slack:** treat a DM/mention as needing a reply only if the user's own last message in
  that thread/DM came *before* the other person's latest message. If the user already
  responded after them, drop it.
- **Second rounds still count:** if the other party replied again with a new question
  *after* the user's response, still surface it — but note the user already replied once.

### Known caveats to state when relevant
- Very recently sent replies (last few minutes) may lag before they're searchable, so a
  just-sent reply can occasionally slip through.

### Context
- User: Michael Esposito (michael.esposito@nick.com), Sr. Writer/Producer, Nickelodeon.
  Times should be presented in Eastern.
- Forge Airtable base (`appLgiUu15D0bQPj6`) is interface-only access — use the
  page-based Airtable tools (`list_pages_for_base` / `list_records_for_page`), not the
  table tools.
