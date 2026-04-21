# Privacy

Bodhisattva is local-first. On the free tier, **no data ever leaves your machine**
except to the LLM provider you configured (Anthropic or OpenAI) for the framing
pass itself.

## What is stored locally

- Every email draft you attempt to send via `bodhisattva.send_email`.
- The wisdom frame returned for that draft.
- The decision (proceed, revise, hold).
- The final sent text (if sent) and the Gmail message id.

Stored at: `~/.bodhisattva/journal.sqlite` — readable only by you.

## What is sent to your LLM provider

- The current email draft body, subject, recipient, and recipient-context fields
  you supply — because those are what the framing model reads.

## What is sent to `bodhisattva.dev`

On the free tier: **nothing**. No telemetry, no phone-home.

On the paid tier (Plan 2, not yet shipped): the current draft payload plus a
short digest of recent pauses (summary lines, not full past drafts). See the
paid-tier privacy page when that tier ships.

## Deleting your data

```bash
rm -rf ~/.bodhisattva
```

That removes your journal, Gmail credentials, and all local state.

## Gmail scope

The OAuth scope requested is `gmail.send` only. Bodhisattva cannot read, list,
or modify any of your existing email.
