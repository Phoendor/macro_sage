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

## Private admin report

The public channel receives only the content PDF. To receive the separate
technical acquisition and filtering report privately:

1. Open a direct chat with the bot from the intended Telegram account and send
   `/start`. A bot cannot initiate a private conversation before this.
2. Obtain that private chat's **numeric** ID. `@artembaulin` is a username and
   cannot be used as the Bot API destination. The numeric ID can be read from a
   `getUpdates` response after `/start` or from a trusted Telegram ID utility.
3. Add the numeric value as the GitHub repository variable
   `TELEGRAM_ADMIN_CHAT_ID`. It is optional; the public delivery continues when
   it is absent.

One successful report run then sends `Macro-Sage-YYYY-MM-DD.pdf` to the channel
and `Macro-Sage-Technical-YYYY-MM-DD.pdf` to the private admin chat. The two
destinations have independent duplicate protection.

The scheduled workflow sends automatically only when the public token and chat
values both exist. If both are absent, delivery is disabled. If only one is
present, a direct local delivery command fails clearly rather than guessing
configuration. The admin ID never substitutes for the public channel ID.
Scheduled runs always publish. A manually dispatched GitHub run exposes a
`deliver_telegram` switch, which can be turned off for hosted validation without
creating a second public post; report artifacts and private run diagnostics are
still generated normally.

## Public channel presentation

The channel message is intentionally editorial rather than operational. A PDF
is posted with a caption such as `Macro Sage — 31 August 2026` and the document
name `Macro-Sage-2026-08-31.pdf`. It does not expose GitHub links, internal run
states, source-health counts or failure stages. Those diagnostics are excluded
from the public content PDF and remain available in the private technical PDF,
the run record and GitHub's operator-facing summary. Normal no-data and
explicitly enabled delayed-edition notices use the same public wording policy.

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

Automatic duplicate suppression is destination-aware and covers both PDFs and
no-data status messages, including workflow reruns with a different run ID.
Intentional redelivery is explicit:

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
