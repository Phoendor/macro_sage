# Durable brief history and collection windows

Macro Sage uses one append-only JSON directory format for brief history in both
execution environments:

- local runs default to `data/brief-history/`;
- GitHub Actions checks out the same format from the dedicated
  `macro-sage-history` branch into `.history-store/`.

The Actions cache remains only a document/transcript performance accelerator.
Deleting it cannot delete brief history or silently reset comparison state.

## Stored data

`store.json` identifies the history-store and record schema versions. Each
successful brief adds one immutable file under
`records/<year>/<date>--<run-id>.json` containing:

- run ID, target date, completion time, health, model and transformation
  versions;
- the exact half-open acquisition interval and the rule that selected it;
- the structured `DailyBrief` and referenced/cited document IDs;
- canonical theme, regime, event and asset-view keys;
- one-day and one-week comparison records;
- first-seen, last-updated, expected-expiry and resolved dates;
- current supporting drivers, contrary risks, evidence document IDs and view
  status history.

Article bodies, podcast transcripts, API credentials and private manifests are
never stored on the history branch.

## Comparison rules

Historical model output is context, not factual evidence. Synthesis receives
only normalized prior stance metadata, explicitly labelled as non-evidence.
Every current theme and asset view must still cite a current document. The
comparison itself is calculated deterministically after synthesis.

Asset labels are mapped to canonical families (`rates`, `fx`, `equities`,
`credit`, `commodities`, or `other`) and horizons (`immediate`, `short_term`,
`medium_term`, `long_term`, or `unspecified`). Theme labels are normalized into
regime, event or thesis keys. Cosmetic punctuation, articles and common aliases
therefore do not create false changes. Stored labels are re-normalized when
read, so a later key-contract improvement does not require rewriting immutable
records or create a false change by itself.

Current asset views are classified as new, strengthened, weakened, unchanged
or reversed. A prior view missing from today's model output is carried as
historical context with no current evidence; it is not called a reversal. It
becomes retired only when its deterministic horizon expires. Empty/no-brief
runs do not create comparison records and therefore cannot reverse a view.

## Acquisition windows

Explicit `--date` runs always replay the local calendar day `[00:00, 00:00)` in
the configured timezone. They may be comparison baselines, but they never
advance the scheduled collection chain.

Scheduled runs use `[previous successful scheduled cutoff, current intended
cutoff)`. The intended cutoff is recorded during date resolution, independently
of the runner's actual start time. This includes Friday evening and weekend
publications in Monday's run while excluding items already covered by the
previous interval. Per-source limits are applied separately to each publication
day inside a multi-day window.

An initialized store with no records starts at the prior scheduled weekday
cutoff. If an expected hosted store is missing, unreadable or incompatible, the
report says so explicitly and collection uses a visible seven-day recovery
window. This favors duplicate review over a silent coverage gap.

## Backup, migration and recovery

Local history is backed up by copying `data/brief-history/` while the application
is idle. Hosted history is backed up by the full Git commit history of the
`macro-sage-history` branch; any earlier commit can be inspected or restored
without relying on Actions artifact retention.

Writers use atomic file replacement and never edit an existing record. Readers
validate every record against its versioned Pydantic schema. An unreadable file
is reported as a history warning; an unsupported store version is marked
incompatible. Schema changes require a version bump and an explicit migration
that writes new records alongside the originals. Recovery is complete only
after the hosted branch push succeeds: until then, GitHub `run.json` remains in
`history_sync_pending` rather than `complete`.
