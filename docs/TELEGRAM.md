# Telegram report delivery

Telegram delivery is optional and separate from report generation. A valid PDF
remains available locally and as a GitHub artifact if Telegram is unavailable.
No credential is written to a run record, delivery-state file, artifact, test
fixture or log.

## Channel setup

1. In Telegram, create a bot with `@BotFather` and copy its token into a secure
   password manager.
2. Add the bot to the destination channel as an administrator. Grant only the
   permission to post messages; it does not need permission to edit channel
   information, add users or manage other administrators.
3. Choose the destination identifier:
   - a public channel can use its `@channel_username`;
   - a private channel uses its numeric chat ID, normally beginning with
     `-100`. Obtain it through an authorized Telegram client or Bot API update;
     do not commit it merely to discover it.
4. In GitHub, open **Settings → Secrets and variables → Actions**. Add
   `TELEGRAM_BOT_TOKEN` as a repository secret and `TELEGRAM_CHAT_ID` as a
   repository variable.

The scheduled workflow sends automatically only when both values exist. If
both are absent, delivery is disabled. If only one is present, a direct local
delivery command fails clearly rather than guessing configuration.

## Public channel presentation

The channel message is intentionally editorial rather than operational. A PDF
is posted with a caption such as `Macro Sage — 31 August 2026` and the document
name `Macro-Sage-2026-08-31.pdf`. It does not expose GitHub links, internal run
states, source-health counts or failure stages. Those diagnostics remain
available inside the PDF, the private run record and GitHub's operator-facing
summary. Normal no-data and explicitly enabled delayed-edition notices use the
same public wording policy.

## Local use

Load both variables into the shell, then opt in on a new run:

```bash
macro-sage run --deliver
```

To deliver an already completed run:

```bash
macro-sage deliver \
  --run-record output/runs/RUN_ID/run.json
```

Automatic duplicate suppression covers both PDFs and no-data status messages,
including workflow reruns with a different run ID. Intentional redelivery is
explicit:

```bash
macro-sage deliver \
  --run-record output/runs/RUN_ID/run.json \
  --force
```

Failure notifications are not sent by default. They can be requested for a
specific existing run with `--notify-failure`; normal no-data runs send one
plain status message rather than an invented report.

## Safety and failure behavior

- PDFs must have a `.pdf` suffix, a PDF signature and fit the Bot API's current
  50 MB document limit before a network request is made.
- Captions are plain text and capped at the Bot API limit, so article text
  cannot inject formatting or commands.
- The delivery state contains only run/date identifiers, a content hash and the
  returned message ID. GitHub persists it on the body-free history branch.
- Only an explicit HTTP 429 rate limit is retried, once, after the requested
  delay. Ambiguous transport failures are not retried automatically because
  Telegram may already have accepted the first request.
- A delivery error is recorded as a separate `telegram_failed` stage. It does
  not delete the PDF or its audit artifact.

Telegram's current method and limit details are documented in the official
[Bot API](https://core.telegram.org/bots/api#senddocument).
