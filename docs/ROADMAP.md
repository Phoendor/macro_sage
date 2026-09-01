# Macro Sage action plan

Status: approved; Milestones 1 through 3 are code-complete. Milestone 4 is
code-complete in version 0.5.0, its report hierarchy and output quality received
a positive owner review on 2026-08-30, and its prospective evidence audit and
first configured Telegram delivery remain open. Milestone 1 is still awaiting
its scheduled-run observation gate. Milestone 2 passed its closure audit.
Milestone 3 passed its hosted fixed-date canary and awaits the first scheduled
cutoff-window observation before closure. Milestone 5's first version-0.6
implementation tranche is code-complete and awaits its hosted observation and
remaining advanced corpus-accounting refinements.

Baseline date: 2026-08-30.

This is the authoritative implementation roadmap for turning Macro Sage from a
working source-attributed research reader into a reliable daily macro
decision-support product. It consolidates the recovery work, the modernization
already completed, the observed GitHub failures, the podcast-model review, and
the proposed improvements to trading usefulness.

Cost-safety features are deliberately excluded at the owner's request. This
roadmap does not add spending caps, billing alerts, cost dashboards, or
cost-based model routing. Existing operational limits remain unchanged unless a
separate decision changes them. Model evaluations may still compare published
price, latency and output quality so the default remains economical for daily
use; that is a selection decision, not a cost-safety feature.

## 1. Product contract

Macro Sage should:

- acquire current material from a curated, reputable and documented source set;
- state explicitly which sources succeeded, had no publication, were skipped,
  or failed;
- preserve a traceable chain from every important conclusion to the documents
  that support it;
- distinguish source facts, disagreement, and model inference;
- explain what changed, why it matters, how it can transmit across assets, what
  could invalidate the view, and what should be monitored next;
- generate equivalent JSON, Markdown and PDF outputs locally and on GitHub;
- handle normal empty days, delayed runners, source outages and model mistakes
  without misleading the reader;
- remain a research and decision-support tool, not an automatic order-execution
  system.

The final brief may express directional views and candidate trade expressions,
but must never invent current prices, forecasts, consensus estimates, event
dates or position sizes. Entry levels and market-relative calculations are only
allowed after a timestamped market-data source has been integrated.

## 2. Current baseline

### Completed foundation

- [x] Replaced the original one-off scripts with an installable src-layout
  Python package and deterministic CLI.
- [x] Removed recursive text chunking and map/reduce summarization in favor of
  one bounded structured Responses API synthesis request.
- [x] Added generic RSS discovery, HTML extraction, PDF extraction, canonical
  URL handling and SQLite document caching.
- [x] Added deterministic evidence-tier, priority, relevance, freshness and
  publisher-diversity ranking; reserved primary-evidence capacity; enforced
  source/publisher caps; and recorded every inclusion, truncation and omission.
- [x] Added Pydantic-validated structured output and strict source-citation
  validation.
- [x] Added JSON, Markdown and visually formatted PDF output.
- [x] Made failed and partial sources visible in the terminal, run artifacts,
  Markdown and PDF.
- [x] Created a human-readable source catalog with links, cadence,
  descriptions, rationale and a non-working candidate section.
- [x] Expanded the configured inventory to 31 enabled text feeds and 16 opt-in
  podcast feeds, with one disabled text candidate.
- [x] Removed local Whisper and made cloud transcription explicit.
- [x] Made the same CLI operate locally and in GitHub Actions.
- [x] Added model preflight selection and recorded the selected models.
- [x] Added bounded offline compilation, generated-catalog validation, lint and
  regression checks; version 0.6.0 is verified from a clean editable
  installation.

### Current operating state

- Safe runner version 0.4.0 was implemented on 2026-08-28; its five-run
  operational observation gate remains open.
- The GitHub workflow runs on weekdays at 19:30 Europe/Amsterdam and currently
  includes podcasts.
- This operating snapshot includes scheduled workflow run
  [33133346054](https://github.com/Phoendor/macro_sage/actions/runs/33133346054),
  created at 2026-08-28 01:35:56 UTC.
- Between 2026-07-27 and that run, 24 scheduled runs produced 14 successes and
  10 failures.
- Eight historical scheduled failures came from model-generated source
  identifiers that did not exactly match opaque document hashes; version 0.4.0
  replaces those model-facing hashes with short citation keys.
- One scheduled failure was GitHub runner infrastructure.
- One scheduled failure was a healthy empty collection incorrectly treated as
  an error after a severely delayed start selected the wrong publication date;
  version 0.4.0 adds explicit no-data success and delay-safe date resolution.
- The current synthesis model is gpt-5.6-luna with low reasoning effort.
- The current transcription model is gpt-4o-mini-transcribe with whisper-1 as a
  preflight compatibility fallback; request-time fallback is not implemented.
- The proposed gpt-transcribe migration has not been implemented.
- The current live source baseline is 2026-08-29: all 47 participating sources
  have reviewed contract records; 45 passed, Norges Regional Network is
  degraded because charts lose tabular structure even though its prose extracts
  completely, and BIS Research Hub failed because its official RSS endpoint
  returned HTTP 404 on two bounded checks.
- Hosted closure run
  [33262329610](https://github.com/Phoendor/macro_sage/actions/runs/33262329610)
  completed successfully on commit `91ed76b` for 2026-08-28 with podcasts
  enabled. It collected 26 documents, including six newly transcribed podcast
  episodes, synthesized with `gpt-5.6-luna`, transcribed with
  `gpt-4o-mini-transcribe`, and produced an 11-page PDF. The report health was
  correctly degraded and all nine failed, stale or expected-but-absent sources
  remained explicit.
- The nine closure-run limitations were: stale EcoWeek, EcoInsight, Central
  Bank Speeches, Bank of England Speeches and Bank Insights feeds; failed BIS
  Research Hub discovery; and expected-but-absent Bank of Canada, Norges Bank
  and Riksbank speech publications. Odd Lots and The Macro Trading Floor were
  separately shown as skipped after the six-episode run limit, not failures.
- The 2026-08-25 run collected 13 documents from six sources; ING and Saxo
  supplied nine of them. The configured inventory is broad, but daily input can
  still be concentrated in a few prolific publishers.
- Local saved reports cover 2026-07-27 and 2026-07-28; hosted artifacts now
  retain sanitized reports and audits for 30 days.
- The local virtual environment was rebuilt from the exact dependency
  constraints and imports this checkout correctly.
- The owner reviewed the hosted Decision Brief V2 PDF on 2026-08-30 and gave a
  positive assessment of its usefulness and presentation. The information
  hierarchy is therefore accepted as the production baseline; future prompt or
  layout changes should answer an observed defect rather than restart the
  redesign.

## 3. Priority and dependency map

| Order | Workstream | Priority | Depends on | Exit milestone |
| --- | --- | --- | --- | --- |
| 1 | Safe, reproducible run reliability | P0 | Current baseline | Safe runner v0.4 |
| 2 | Acquisition, identity and provenance foundation | P0 | Safe runner and migrations | Trustworthy corpus |
| 3 | Durable brief history and collection windows | P0 | Stable document identity | Comparable daily history |
| 4 | Evaluation baseline and acceptance harness | P1 | Validated corpus and history | Frozen benchmark |
| 5 | Trading-oriented synthesis v2 | P1 | Provenance, history and baseline rubric | Decision brief v0.5 |
| 6 | Report redesign, delivery and retention | P1 | Approved v2 schema | Usable daily service |
| 7 | Source health, material coverage and corpus balancing | P1 | Stable acquisition contracts | Trustworthy daily corpus |
| 8 | Market-context enrichment | P1 | Approved data-provider boundary | Quantified context layer |
| 9 | Podcast modernization | P1 | Reliable transcript/cache provenance | GPT-Transcribe rollout |
| 10 | Selective source expansion | P2 | Health and balancing controls | Verified expanded catalog |
| 11 | Cross-cutting tests and release closure | Every milestone; P2 final closure | Each changed behavior | Release candidate |

P0 items repair known failures, unsafe artifacts and foundational data identity
and must be implemented first. P1 items create the intended product. P2 items
add selectively admitted coverage and close the final release. Tests, replay
fixtures, documentation and artifact checks are part of every milestone, not a
final cleanup phase.

The Decision Brief V2 canary and owner review changed the order of the remaining
work. Report layout is no longer the binding constraint. Corpus concentration,
material coverage classification and unsafe document-boundary serialization
can still distort the evidence supplied to an otherwise good synthesis, so they
come next. Timestamped market context then has greater marginal value for
trading decisions than improving an already usable cloud transcription path.
Podcast modernization remains important, but source expansion waits until
selection controls can prevent additional volume from reducing evidence
quality.

## 4. Workstream A — run and citation reliability

### A1. Replace model-facing document hashes with short citation keys

- [x] Assign deterministic run-scoped labels such as S001, S002 and S003 after
  corpus selection.
- [x] Keep canonical URL-derived document IDs internal; never ask the model to
  reproduce a 16-character hash.
- [x] Include the short label, publisher, title, date, category and URL in each
  corpus document header.
- [x] Constrain every citation-bearing schema field to labels that were
  actually supplied for that run.
- [x] Convert short labels back to canonical document IDs before writing the
  final brief and renderers.
- [x] Save the label-to-document mapping in the run audit trail.
- [x] Preserve strict validation. Unknown or missing citations must not be
  silently discarded.
- [x] Add focused tests for copied, duplicated, missing, malformed and unknown
  labels.
- [x] Reproduce the historical ING, Saxo, BIS, ECB, BOJ, BofA and Goldman
  failure cases in offline fixtures.

Acceptance criteria:

- Every citation in JSON, Markdown and PDF resolves to exactly one collected
  document.
- The historical unknown-source-ID failure class is eliminated.
- A deliberately invalid label still produces a clear validation failure and a
  complete diagnostic artifact.
- Strict citation enforcement remains stronger than the current implementation,
  not weaker.

### A2. Introduce explicit run outcomes

- [x] Record two independent dimensions:
  - content result: report, no-data or not-produced;
  - run health: healthy, degraded or failed.
- [x] Define strict precedence for the displayed outcome and process exit code
  rather than forcing mixed states into one ambiguous enum.
- [x] Define no-data as no matching documents and therefore no synthesis
  request; use the health dimension to say whether that absence was trustworthy.
- [x] Distinguish a normal no-publication day from a day on which every
  important source failed.
- [x] Define zero documents plus a non-systemic source failure as
  no-data/degraded, and zero documents plus systemic or material coverage
  failure as no-data/failed.
- [x] Determine material coverage from configured source criticality and
  coverage rules, not an ad hoc model judgment, and record the rule used.
- [x] Return a successful process status for a healthy no-data run so GitHub
  does not send a false failure notification.
- [x] Produce a small status artifact, and preferably a one-page status PDF,
  explaining that no brief was generated and listing source outcomes.
- [x] Keep failed and partial sources visible even on a no-data day.
- [x] Add tests for healthy empty, partially failed empty, fully failed,
  degraded-with-documents and normal-success cases.

Acceptance criteria:

- A healthy empty day does not fail GitHub Actions or call a synthesis model.
- A degraded empty day remains visibly degraded without pretending that a
  report exists.
- A systemic source failure cannot masquerade as a healthy empty day.
- Every run leaves a human-readable explanation.

### A3. Make the target date independent of runner delay

Phase 1, implemented in Milestone 1:

- [x] Move scheduled-date resolution into tested Python code shared by local
  and hosted execution.
- [x] Preserve an explicitly supplied date exactly.
- [x] For scheduled execution, resolve the intended Amsterdam publication day
  rather than blindly using the runner's eventual start date.
- [x] Handle a weekday job delayed across midnight, a Friday job delayed into
  Saturday, daylight-saving transitions and month/year boundaries.
- [x] Record requested date, resolved date, resolution rule, local start time
  and UTC start time in run.json.
- [x] Display the resolved date and reason in the GitHub job summary.

Phase 2, implemented only after durable history in Milestone 3:

- [x] After durable run history exists, replace scheduled calendar-day-only
  collection with a half-open acquisition window from the previous successful
  cutoff to the current intended cutoff.
- [x] Keep explicit manual `--date` behavior available for reproducible
  calendar-day replays.
- [x] Include Friday-evening and weekend publications in Monday's scheduled
  window without duplicating previously processed items.
- [x] Persist the intended cutoff independently of the actual runner start so a
  delayed rerun resolves the same window.

Acceptance criteria:

- A replay of the delayed 2026-08-28 start selects the intended 2026-08-27
  publication date.
- Manual dates remain deterministic.
- Unit tests cover Amsterdam daylight-saving changes and weekend rollovers.
- A publication released after the weekday run is picked up by the next run,
  and deleting or retrying a run cannot create a silent coverage gap.

### A4. Improve hosted workflow behavior

- [x] Add a concurrency group so two scheduled or manual full runs cannot
  overlap accidentally.
- [x] Keep cancellation behavior conservative so an older in-flight report is
  not silently destroyed by a new run.
- [x] Give collection, transcription, synthesis, validation and rendering
  distinct visible stages and failure categories.
- [x] Set explicit network, subprocess and overall job timeouts appropriate to
  each stage, with progress messages for long podcast work.
- [x] Always upload the available manifest, source status, model selection and
  diagnostics after an application failure.
- [x] Put the resolved date, outcome, collected count, failed-source count,
  no-item count, model names and artifact link in the GitHub summary.
- [x] Ensure infrastructure failures remain distinguishable from application
  failures.
- [x] Assign every attempt a run ID and write diagnostics before synthesis.
- [x] Store attempts in separate run directories; never overwrite an earlier
  same-date run.
- [x] Write output files atomically and expose a convenient latest-successful
  pointer or copy.
- [x] Preserve item-level outcomes with item title, URL, stage, state and error;
  derive concise source summaries from those records.
- [x] Add workflow tests or static assertions for schedule inputs, artifact
  paths and no-data behavior.

Acceptance criteria:

- A failure email or run page identifies the failed stage without searching a
  thousand-line log.
- Diagnostic artifacts exist whenever collection reached the point of writing
  them.
- Repeated triggers cannot create overlapping work for the same report.
- Offline lint and test commands finish predictably and can never wait on feeds
  or APIs.
- Two attempts for one publication date remain independently auditable, and an
  interrupted write cannot look like a valid finished report.

### A5. Make model-response failures recoverable only when safe

- [ ] Classify transport, API, schema, citation and semantic validation errors.
- [x] Use structured schema constraints to prevent errors rather than repairing
  them after generation wherever possible.
- [x] Do not fuzzy-match, truncate or guess an unknown citation label.
- [ ] If schema constraints cannot prevent a narrow formatting failure, permit
  at most one bounded model regeneration with the original error and allowed
  labels; treat it as a nondeterministic retry, not a deterministic repair.
- [x] Never weaken factual or citation requirements to obtain a green run.
- [x] Record the original validation error and whether regeneration was used.
- [x] Preserve OpenAI request IDs in diagnostics when the SDK exposes them,
  without recording credentials or sensitive headers.

Acceptance criteria:

- Avoidable label-format failures are prevented by the model-facing contract.
- Missing evidence and unknown citations remain fatal; unsupported factual
  claims are fatal when detected, with semantic support quality enforced by the
  evaluation and promotion gates until a production evidence checker exists.
- No retry, fallback or validation result is silent.

### A6. Resolve models once per model-backed run

- [x] Perform model discovery and selection once for each model-backed run and
  only for the purposes that run actually needs.
- [x] Keep text-only collection and source validation usable without an OpenAI
  key or Models API request.
- [x] Pass one immutable selection object through collection, transcription and
  synthesis instead of repeating model-list calls in multiple commands.
- [ ] Record requested, selected, attempted and actually used models.
- [x] Rename “fallback” in user-facing output because it remains preflight
  selection only.
- [x] Keep runtime fallback disabled rather than retrying ambiguous transport
  errors that may duplicate a completed paid request.
- [ ] Test inaccessible requested models, empty overrides, explicit overrides
  and request-time failures.

Acceptance criteria:

- One normal model-backed run performs one model-discovery operation; a plain
  non-podcast collection performs none.
- The same configuration snapshot selects the same models locally and on
  GitHub.
- Model-access failures have documented, deterministic behavior.

## 5. Workstream B — provenance and daily history

### B1. Version every transformation

- [x] Define explicit versions for source configuration, extraction behavior,
  corpus preparation, synthesis prompt, output schema, transcription prompt and
  renderer.
- [x] Save those versions, the application version and Git commit in run.json.
- [x] Save the exact selected model identifiers and reasoning settings.
- [x] Add backward-compatible SQLite migrations rather than recreating the
  database.
- [x] Document which changes invalidate cached documents, transcripts or prior
  briefs.

### B2. Store successful brief history

- [x] Add a versioned brief-history table or equivalent durable local store.
- [x] Save structured briefs, run dates, schema versions and document
  references.
- [x] Load the most recent comparable successful brief when producing a new
  one.
- [x] Treat prior model output as historical context, never as current factual
  evidence.
- [x] Define first-run behavior when no prior brief exists.
- [x] Define one history-storage interface with a durable local implementation
  and a durable hosted implementation.
- [x] Choose a genuinely durable hosted store for brief history; do not claim
  reliable comparison when the only copy is an evictable GitHub Actions cache.
- [x] Detect missing hosted history explicitly and label the report as having
  no comparison baseline rather than silently treating it as a first-ever run.
- [x] Define backup, migration and recovery behavior for the selected store.
- [x] Treat GitHub Actions cache only as an optional performance accelerator,
  never as the authoritative history store.

### B3. Track view evolution

- [x] Define canonical asset families and standard horizons.
- [x] Give comparable regimes, theses, events and asset views deterministic
  keys independent of prose.
- [x] Record first-seen, last-updated, expected-expiry and resolved dates.
- [x] Retain supporting evidence, contradicting evidence and status history.
- [x] Classify each current view as new, strengthened, weakened, unchanged,
  reversed or retired relative to the prior successful brief.
- [x] Retain the previous stance, current stance, change explanation and current
  evidence.
- [x] Prevent a missing source or empty day from being interpreted as a genuine
  reversal.
- [x] Expire short-horizon views after their catalyst or stated horizon instead
  of carrying them indefinitely.
- [x] Provide both one-day and one-week context without presenting carried
  material as newly published.

Implementation note: version 0.4.7 stored the V1 schema's cited drivers and
risks as supporting and contrary context. Version 0.5.0 adds claim-level
counterevidence and sourced catalyst timing in DailyBriefV2; history still does
not invent precision that current evidence does not contain.

Acceptance criteria for Workstream B:

- Every report can state which prior successful brief it compared against.
- Prompt, schema and source provenance are sufficient to reproduce the logic of
  a report.
- Historical prose is never cited as if it were a primary source.
- View changes are stable across cosmetic wording differences.
- Deleting an Actions cache cannot silently erase the comparison history.

## 6. Workstream C — trading-oriented synthesis v2

### C1. Redesign the structured schema

Replace the current summary/themes/asset-views-only structure with a versioned
DailyBriefV2 containing:

1. **Coverage and limitations**
   - data cutoff and comparison date;
   - collected, failed, partial and no-item source counts;
   - important missing coverage;
   - explicit statement when price, positioning or calendar data is absent.

   Code, rather than the model, supplies dates, timestamps, schema version,
   aggregate source lists and run counts.

2. **Claim-level evidence objects**
   - claim text;
   - claim type: observed fact, source forecast, source opinion or synthesis
     inference;
   - one or more short citation labels;
   - freshness or carried-forward status;
   - evidence family so several articles based on one underlying release are
     not treated as independent confirmation.

3. **What changed**
   - the most important changes since the previous successful brief;
   - significance, affected assets and current citations;
   - new, strengthened, weakened, reversed and retired views.

4. **Executive decision summary**
   - ranked developments rather than a generic recap;
   - what happened, why it matters and the likely transmission channel;
   - urgency and time horizon;
   - citations for every item.

5. **Macro regime dashboard**
   - growth, inflation, monetary policy, fiscal policy, liquidity/financial
     conditions and risk sentiment;
   - state, direction of travel, horizon, confidence and confidence rationale;
   - evidence and counterevidence with citations.

6. **Theme analysis**
   - concise thesis;
   - source facts separated from Macro Sage inference;
   - supporting evidence, conflicting evidence and unresolved questions;
   - transmission to rates, FX, equities, credit and commodities;
   - horizon, catalysts, invalidation conditions and citations.

7. **Cross-asset map**
   - standardized asset or market;
   - bullish, bearish, neutral or mixed stance;
   - horizon and market-confirmation state;
   - whether a development appears reflected in prices only when verified,
     timestamped market data supports that statement;
   - drivers, counterarguments, catalyst, invalidation condition;
   - confidence score with a written evidence-based rationale;
   - citations.

8. **Candidate research expressions**
   - underlying macro thesis and preferred expression;
   - directional or relative-value framing;
   - catalyst and expected path;
   - horizon;
   - invalidation or change-of-mind condition;
   - key implementation risks and alternative expression;
   - evidence quality, confidence and citations;
   - explicit marker when current market data is required before action;
   - actionability state: background, monitor, conditional or ready for the
     owner's review;
   - schema invariant: ready is impossible while market-data availability is
     false; without verified market context, conditional is the maximum state;
   - an explicit valid outcome of “no sufficiently supported setup today.”

9. **Scenario map**
   - base, upside and downside scenarios;
   - qualitative likelihood rather than invented precision;
   - observable signposts;
   - expected cross-asset consequences;
   - source-supported assumptions and citations.

10. **Disagreement map**
   - the issue on which sources disagree;
   - each side's position and evidence;
   - what evidence or event could resolve the disagreement;
   - citations attached to the correct side.

11. **Catalyst and monitoring list**
    - only events or signposts present in supplied sources or an integrated
      calendar;
    - date/time only when explicitly sourced;
    - what outcome matters and which views it affects;
    - next questions to answer.

12. **Top risks and blind spots**
    - risks to the aggregate interpretation;
    - data or source gaps;
    - crowded or one-sided evidence;
    - conditions under which the brief should not be acted upon.

### C2. Rewrite synthesis instructions

- [x] State the hierarchy: source fact, attributed source opinion, disagreement,
  and Macro Sage inference.
- [x] Require citations next to every material fact, numerical claim, theme,
  scenario assumption and trade thesis.
- [x] Forbid unsupported numerical precision, invented consensus, fabricated
  calendars and fabricated market prices.
- [x] Require the model to return fewer views rather than fill sections with
  weak material.
- [x] Prevent duplicated themes and trade expressions.
- [x] Require causal transmission language rather than unexplained bullish or
  bearish labels.
- [x] Require a concrete instrument or relative-value expression, standardized
  horizon, why-now, trigger, catalyst, transmission path, invalidation and
  counterevidence for each candidate setup.
- [x] Allow zero setups and “no material change” without forcing the model to
  manufacture novelty.
- [x] Standardize horizons so daily reports can be compared.
- [x] Define a confidence rubric based on source directness, freshness, breadth,
  agreement and missing evidence.
- [x] Treat article and transcript text as untrusted data, not instructions.
- [x] Prohibit “priced in,” “crowded,” “confirmed by markets,” live-price or
  target language unless it is backed by a timestamped market-data input.
- [x] Derive the final source register and aggregate source IDs in code from
  resolved claim citations rather than asking the model to reproduce them.
- [x] Keep the brief compact enough to read daily despite the richer schema.

### C3. Define confidence and evidence rubrics

- [x] Use confidence 1–5 with written definitions and a required rationale.
- [x] Separate confidence in the macro thesis from confidence in the chosen
  market expression.
- [x] Label evidence as primary policy/data, institutional research, market
  commentary or practitioner interpretation.
- [x] Penalize single-source views, stale sources, source disagreement and
  missing market context.
- [x] Calculate the displayed tier in code from source authority, independent
  evidence-family count, freshness, corroboration, contradiction and verified
  market confirmation; do not accept an unconstrained model score.
- [x] Define confidence as evidence strength, not probability of profit.
- [x] Never translate a high confidence score into an automatic position size.

Acceptance criteria for Workstream C:

- Every candidate trade expression contains thesis, transmission mechanism,
  catalyst, horizon, invalidation, countercase, confidence rationale and
  citations.
- Every numerical statement is directly supported or clearly marked as a
  calculation from timestamped data.
- Facts and inference are visibly distinct.
- The report explains changes relative to history rather than repeatedly
  summarizing the same standing narrative.
- A reader can identify what to act on, what to wait for and what would change
  the conclusion without reading every source.
- A quiet or weak-evidence day may contain no candidate setup and is still a
  complete, useful report.

## 7. Workstream D — evaluation and acceptance

### D1. Build a representative evaluation set

- [x] Freeze the present output and defect log as the baseline before changing
  the synthesis schema or prompt.
- [x] Select at least 10–15 historical run dates covering quiet days,
  central-bank days, major data days, geopolitical shocks, disagreement,
  podcasts, source failures, holidays/weekends and no-data.
- [x] Preserve lawful minimal fixtures and document links rather than embedding
  unnecessary copyrighted source text.
- [ ] Include the eight historical citation-failure patterns.
- [ ] Define expected facts, critical numbers, important disagreements and
  reasonable asset implications for each case.

### D2. Score output quality

Use a written rubric covering:

- factual faithfulness;
- citation validity and citation completeness;
- separation of fact and inference;
- coverage of the highest-impact developments;
- handling of contradictory sources;
- causal quality of cross-asset implications;
- usefulness of catalysts and invalidations;
- scenario differentiation;
- absence of unsupported precision;
- concision and daily readability;
- stability under reruns with the same input.

Evaluate four distinct layers:

- deterministic contract checks for schema, citations, dates, required fields,
  duplicate themes, inline aliases and unsupported current-market language;
- evidence audit for claim support, numerical accuracy, citation precision,
  source authority and contradictory evidence;
- temporal audit for new/changed/resolved classification, previous-successful
  selection, stale-item handling and event expiry;
- human usefulness for novelty, clarity, prioritization, actionability,
  invalidation quality, uncertainty and two-minute scan value.

### D3. Validate and tune the production synthesis

- [ ] Produce frozen-baseline and V2 outputs from the two complete lawful
  corpora retained locally; do not weaken artifact privacy or retain publisher
  bodies in GitHub merely to manufacture more historical replays.
- [ ] Audit at least ten prospective V2 reports as scheduled runs create them,
  recording material-claim support and human usefulness without requiring an
  obsolete V1 report for every date.
- [ ] Compare the current economical synthesis model with at least one stronger
  eligible model on the retained same-corpus cases, then keep the least
  expensive model that clears all grounding and usefulness gates.
- [ ] Record model snapshot, reasoning setting, latency and token usage for the
  evaluation; this is model-selection evidence, not a spending-control system.
- [ ] Review them blind where practical.
- [ ] Record section-level scores and concrete defects.
- [ ] Revise prompt or schema only in response to an observed failure class.
- [ ] Keep an evaluation changelog tied to prompt/schema versions.
- [x] Add deterministic structural graders and optional model-assisted semantic
  grading, with human review remaining authoritative.

Acceptance criteria:

- Citation resolution is 100%.
- Ten consecutive scheduled runs produce a valid report or an intentional,
  documented normal no-data outcome.
- Every material claim, number, event, risk and setup resolves to evidence.
- A manual audit of at least 100 material claims finds zero critical
  unsupported facts or numbers and at least 95% substantive citation support.
- No candidate trade lacks an invalidation condition or countercase.
- No stale item is called new in the temporal fixture set.
- High confidence cannot result from one non-primary evidence family without
  independent confirmation.
- The report may return zero actionable setups.
- V2 is preferred on both retained same-corpus cases without a grounding
  regression, and at least eight of ten prospective production reports pass the
  human usefulness rubric.
- The approved prompt/schema version is recorded and regression-tested.

## 8. Workstream E — report and renderer redesign

### E1. Keep all formats semantically equivalent

- [x] Update JSON, Markdown and PDF from the same DailyBriefV2 object.
- [x] Test that every section, citation, warning and source status appears in
  all applicable formats.
- [x] Keep machine-readable fields stable and versioned.

### E2. Redesign the PDF for daily use

- [x] Make the first page readable in roughly two minutes.
- [x] Begin with data and market-data cutoffs, the previous comparison brief,
  source-failure/coverage warnings, three to five ranked changes, a compact
  regime panel, at most three highest-priority setups or an explicit no-setup
  result, and the next event risks.
- [x] Follow with theme detail, cross-asset map, candidate expressions,
  scenarios, disagreements and monitoring list.
- [x] Keep source links adjacent to the claims they support.
- [x] Preserve a complete source register and explicit failed/partial source
  section.
- [x] Display comparison date, data cutoff, model, schema version and run
  outcome.
- [x] Move model names, token usage and the full source register to a technical
  audit appendix rather than consuming first-page attention.
- [x] Handle empty and degraded reports gracefully.
- [x] Add visual regression fixtures and render every changed PDF to images for
  inspection before acceptance.

Acceptance criteria:

- The first page is useful on its own.
- No table, card, citation or warning is clipped or split illegibly.
- The PDF, Markdown and JSON cannot disagree about a stance or source.
- Failed sources remain impossible to overlook.

## 9. Workstream F — podcast modernization

### F0. Prefer publisher transcripts before transcription

- [ ] Detect official transcripts advertised through podcast metadata or the
  publisher's episode page.
- [ ] Validate that the transcript is complete and belongs to the episode.
- [ ] Use cloud audio transcription only when a usable official transcript is
  unavailable.
- [ ] Preserve the official transcript as immutable raw evidence.
- [ ] Store advertisement removal or labelling as a versioned derived view with
  traceable source sections or offsets; never destructively overwrite the
  publisher transcript.
- [ ] Handle host-read advertisements, cross-promotions, legal boilerplate and
  unrelated appended programmes in that derived view.
- [ ] Preserve guests, duration, transcript method and quality warnings.

### F1. Evaluate and adopt the correct transcription model

- [ ] Compare gpt-4o-mini-transcribe, direct gpt-transcribe, and
  gpt-transcribe with context on the same representative audio.
- [ ] Include finance-heavy clips with rates, percentages, dates, acronyms,
  institution names, speaker accents, noise and interruptions.
- [ ] Score exact critical-term and critical-number accuracy, completeness and
  keyword hallucination.
- [ ] Record latency, billed audio duration and the published per-minute price
  at evaluation time so the quality improvement can be judged against its
  incremental daily expense.
- [ ] Make gpt-transcribe the primary recorded-audio model if the evaluation
  confirms the expected improvement.
- [ ] Keep gpt-4o-mini-transcribe as the first compatibility fallback.
- [ ] Treat fallback as preflight compatibility selection unless a narrowly
  defined unsupported-model error proves that a request-time retry is safe.
- [ ] Do not use gpt-live-transcribe; Macro Sage processes completed files, not
  live microphones or calls.

### F2. Use transcription context carefully

- [ ] Pass publisher, programme, episode title, named guest where available and
  a concise description of the recording.
- [ ] Supply a conservative validated finance glossary through keyword hints.
- [ ] Supply expected language hints without forcing incorrect language output.
- [ ] Tell the model to transcribe faithfully rather than summarize.
- [ ] Verify that hinted terms are not inserted when absent.

### F3. Replace arbitrary 15-minute cuts

- [ ] Upload supported recordings whole when they fit the API file-size limit.
- [ ] Normalize or compress an oversized recording before splitting.
- [ ] Split only when the normalized file still exceeds the upload limit.
- [ ] Prefer silence-aware boundaries and avoid cutting mid-sentence.
- [ ] Carry episode context and the prior segment's ending into later segments.
- [ ] Join segments without duplicated or missing boundary text.
- [ ] Keep ffmpeg/ffprobe optional outside podcast execution.

### F4. Version transcript provenance

- [ ] Store transcription model, model snapshot where available, transcription
  prompt version, language hints, audio identity, duration, segment information
  and transcription timestamp.
- [ ] Do not reuse a cached transcript when model or transcription behavior has
  changed incompatibly.
- [ ] Migrate existing cached transcripts explicitly; never label an old
  transcript as if the new model created it.
- [ ] Bump the hosted cache namespace when the storage contract changes.
- [ ] Add fake-client tests for request payloads, object/string responses,
  whole-file handling, segmentation and cache invalidation.

### F5. Make long-form audio useful to synthesis

- [ ] Replace raw character-count approximations with model-aware input
  accounting.
- [ ] Do not blindly keep only the first 40,000 transcript characters; preserve
  the complete transcript when it fits.
- [ ] When it does not fit, apply a documented evidence/relevance selection
  strategy that can retain material from the middle and end of an episode.
- [ ] Keep that selection deterministic, versioned and auditable; do not quietly
  reintroduce a model-based chunk-summary/map-reduce pipeline.
- [ ] Keep every omitted or truncated region explicit in the audit trail.
- [ ] Add a fixture in which the decision-relevant statement appears near the
  end of a long episode.

Acceptance criteria for Workstream F:

- Representative finance terms and numbers meet the agreed evaluation
  threshold.
- Normal podcasts are not cut into arbitrary 15-minute pieces.
- A transcript can always be traced to its model and transcription settings.
- Local execution performs no neural transcription on the Intel Mac.
- Important late-episode material is not systematically excluded from the
  synthesis corpus.

## 10. Workstream G — source acquisition and catalog

This workstream has two delivery phases. G1–G5, including the G2 live baseline,
form the acquisition and identity foundation and must precede durable history,
podcast cache migration and synthesis-v2 evaluation. G6–G9 build ongoing health,
selection quality and portfolio expansion after that foundation is stable.

### G1. Make one structured inventory authoritative

- [x] Replace the overloaded enabled flag with explicit participation states:
  default, optional, unavailable and candidate.
- [x] Keep healthy opt-in podcasts distinct from known-broken text sources.
- [x] Add structured metadata used by the program:
  - evidence tier: primary, institutional analysis, market interpretation or
    informed viewpoint;
  - geography, topic and applicable asset classes;
  - language;
  - expected cadence, maximum normal publication gap and active weekdays or
    event-driven status;
  - acquisition mode: full HTML, full PDF, feed body, publisher transcript or
    machine transcript;
  - priority, critical coverage role, scan depth, daily inclusion limit and
    per-publisher selection cap;
  - validation status, last validation date and source owner/publisher.
- [x] Generate the human-readable catalog deterministically from the structured
  inventory so cadence, links, descriptions, status and “why I need it” cannot
  drift.
- [x] Generate the “Would be good to have, but these don't work” section from a
  structured candidate registry containing the attempted official endpoints,
  precise failure, last attempt, lawful alternative, constraint and next
  review date.
- [x] Test complete field equality between configuration and generated catalog,
  not merely the presence of source IDs.

### G2. Establish a fresh, auditable validation baseline

- [x] Run a complete live check of all 31 active text sources and 16 podcast
  feeds before claiming current coverage.
- [x] Save a machine-readable validation record containing check time, HTTP and
  redirect results, newest entry, parseable-entry count, resolved URL,
  extraction method, content type, content length, warnings and exact failure
  stage.
- [x] Retain one manually reviewed representative contract sample per active
  source.
- [x] Build a coverage matrix by geography, institution type, topic, asset
  class, evidence tier, language, cadence and acquisition method.
- [x] Record the 2026-08-25 concentration—nine of 13 documents from ING and
  Saxo—as the initial corpus-balance benchmark.

Acceptance criteria:

- For every source, the owner can answer when it was checked, what was acquired,
  by which method, and whether the content was complete.

### G3. Correct feed discovery and publication dating

- [x] Retain published time, updated time and raw publisher timestamp as
  separate fields.
- [x] Never reinterpret an update date as a publication date unless an explicit
  source policy authorizes it.
- [x] Normalize and sort all scanned entries before applying target-window and
  daily inclusion limits; do not assume feeds are newest-first.
- [x] Separate scan depth from maximum items selected for the day.
- [x] Report missing and malformed timestamps explicitly rather than folding
  them into “no items.”
- [x] Distinguish no publication expected, no publication in the window,
  expected-but-absent, stale feed, entries filtered by policy, invalid dates,
  duplicate discoveries and discovery failure.
- [x] Normalize after redirects and honor reliable canonical links while
  retaining original feed URLs, GUIDs and publisher identifiers.
- [x] Test RSS, Atom, podcast namespaces, timezones, daylight-saving boundaries,
  out-of-order and high-volume feeds, revisions, missing dates and duplicates.

Acceptance criteria:

- A same-window item cannot be hidden merely because its feed was unsorted or
  busy, and a missing date cannot masquerade as a quiet day.

### G4. Verify acquired content, not just HTTP success

Use one generic extraction path with declarative source overrides only where a
documented live failure proves they are required.

For HTML:

- [x] Verify that the final title resembles the feed item title.
- [x] Reject login, denial, cookie, bot-challenge, error and paywall bodies.
- [x] Validate expected language, text density, boilerplate ratio, repeated
  paragraphs, relevance and plausible completeness.
- [x] Preserve useful tables while removing menus and promotion.
- [x] Mark feed-summary or teaser fallback as visibly degraded; never call it a
  complete article.

For PDF:

- [x] Replace the loose link-text heuristic with tested source patterns or
  selectors when a landing page contains multiple files.
- [x] Verify content type, title, date, language, page count and extracted-text
  density before accepting a PDF.
- [x] Detect scans, broken reading order, table corruption and wrong-language,
  appendix, slide or unrelated-file selection.
- [x] Remove repeated headers and footers without deleting substantive text.
- [x] Retain both the publication landing page and actual PDF URL.

For podcasts:

- [x] Validate enclosure type and download behavior without downloading an
  entire episode during a lightweight health check.
- [ ] Prefer and verify official publisher transcripts, then use the cloud
  transcription path in Workstream F.
- [ ] Detect or label advertisements, unrelated appended shows and
  cross-promotions; Odd Lots is a known test fixture for inline advertising.
- [ ] Keep programme, episode, guests, duration, method and transcript-quality
  warnings.

Acceptance criteria:

- Every document declares full HTML, full PDF, feed summary, official
  transcript or machine transcript, and degraded acquisition is unmistakable
  in JSON, Markdown and PDF.

### G5. Fix identity, cache freshness and revision provenance

- [x] Make canonical document identity independent of the source through which
  it was discovered.
- [x] Add a many-to-many discovery-origin record so one BIS/central-bank speech
  is synthesized once while every feed that exposed it remains auditable.
- [x] Use canonical/final URLs and content hashes for exact deduplication.
- [x] Use normalized-title similarity only to propose reviewable duplicate
  candidates; never merge on title alone because recurring releases often have
  nearly identical names.
- [x] Store original URL, canonical URL, resolved content URL, publication and
  update times, fetch time, language, content hash, extractor version,
  extraction method and quality flags.
- [x] Use ETag and Last-Modified validators where available.
- [x] Refresh when the publisher reports an update, content changes, extraction
  behavior changes, or cached content has a quality warning.
- [x] Preserve prior revisions rather than silently overwriting evidence.
- [x] Store source-health events separately from article bodies.
- [x] Normalize tracking parameters and query ordering consistently.

Acceptance criteria:

- Cache reuse cannot conceal publisher corrections or extractor improvements.
- Every cited claim traces to an exact content revision.
- One publication discovered in several feeds is fetched and synthesized once,
  with all origins retained.

### G6. Add cadence-aware source health and complete outcomes

- [x] Run lightweight discovery checks regularly and full extraction canaries
  on a slower schedule independent of paid synthesis and transcription.
- [x] Track last success, last failure, consecutive failures, last publication,
  expected next publication and extraction quality.
- [x] Interpret daily, weekly, monthly and event-driven silence differently.
- [x] Treat one transient failure as a warning and use a defined consecutive
  failure threshold before quarantine.
- [x] Never silently remove or omit a source.
- [x] Expose collected, degraded/summary-only, partial, failed, stale,
  expected-but-missing, quiet-as-expected, filtered, duplicate, policy-skipped
  and unavailable states in the manifest.
- [x] Keep every failure visible in the daily PDF and GitHub summary, with the
  exact item and stage when applicable.
- [x] Flag material coverage holes—for example, a failed Fed source before an
  FOMC decision—more prominently than an unrelated low-frequency failure.

Acceptance criteria:

- The user can see every failure without reading workflow logs, while a quiet
  event-driven source does not create a false alarm.

### G7. Balance what enters synthesis

Keep everything lawfully acquired in the internal manifest, but select a
deterministic, relevant and diverse synthesis subset.

This was the first implementation work after Decision Brief V2. Version 0.6
replaced the earlier round-robin-only baseline with ranked, reserved and capped
selection while retaining deterministic publisher diversity.

- [x] Rank by evidence tier, macro relevance, freshness and source diversity.
- [x] Reserve room for primary policy/data evidence before commentary.
- [x] Cap publisher and product-line contribution so prolific commercial feeds
  do not dominate merely through volume.
- [ ] Treat several publications derived from one underlying release as one
  evidence family for confidence.
- [x] Filter company-specific and lifestyle pieces from broad Saxo feeds unless
  they have a clear macro transmission channel.
- [x] Filter narrowly sectoral ING material unless macro or cross-asset
  relevance is material.
- [x] Limit NBER's batch feed to relevant macroeconomics, monetary economics,
  international finance, asset pricing, labour and public-finance research.
- [ ] Deduplicate BIS speeches against the originating central bank.
- [x] Label practitioner podcasts as opinion rather than primary evidence.
- [x] Preserve genuine disagreement rather than forcing artificial consensus.
- [ ] Replace character-only budgets with model-aware input accounting and keep
  every omission/truncation visible.
- [x] Keep long-document selection deterministic, versioned and auditable; do
  not conceal a second model summarization stage inside corpus preparation.
- [x] Serialize corpus documents safely so titles or bodies containing closing
  tags, quoted attributes or instructions cannot alter document boundaries.

Acceptance criteria:

- No two publishers dominate a normal brief solely because they publish more.
  An exceptional concentration must be explained by the day's available
  evidence.
- Source text containing delimiter-like strings remains inert data.

### G8. Expand the portfolio through an admission gate

Investigate these first-wave coverage additions:

- official activity, inflation and labour releases: US BLS, US BEA, Eurostat
  and UK ONS;
- fiscal and liquidity context: US Treasury and European Commission economic
  and fiscal material;
- energy and commodity fundamentals: US EIA, then usable official IEA and OPEC
  material;
- uncovered G10 policy: RBA and RBNZ through stable official paths;
- multilateral outlooks: IMF, OECD and World Bank;
- targeted indicators: Atlanta Fed GDPNow, Cleveland Fed inflation research
  and Dallas Fed energy surveys;
- China and Asia primary sources, including PBoC, China NBS/SAFE and other major
  central banks, only where stable English-language retrieval is possible;
- official event calendars and release schedules needed for the catalyst layer;
- reputable incremental strategy or practitioner audio only when it adds
  distinct coverage rather than more volume.

Every new source must pass this gate before enablement:

1. reputable and relevant;
2. stable official HTTPS discovery path;
3. usable publication timestamp and canonical link;
4. at least three recent entries inspected;
5. successful complete extraction across representative items/formats;
6. no access-control, licensing or anti-bot workaround;
7. incremental coverage rather than unnecessary duplication;
8. catalog metadata, health policy and offline fixtures complete.

Specific current-source treatment:

- Keep ING and Saxo, but filter and cap them.
- Keep BIS speeches for broader-country coverage while deduplicating directly
  configured institutions.
- Keep BNP product lines only while live samples remain meaningfully distinct.
- Retain NBER as a filtered weekly research input.
- Keep Odd Lots only if advertising can be excluded or clearly separated.
- Do not add FT Unhedged without an authorized complete-content route.

### G9. Maintain non-working candidates and source history

- [ ] Retest Bruegel, RBA, RBNZ, IMF Blog, CEPR/VoxEU and other candidates on a
  documented slower cadence through official endpoints.
- [ ] Keep each unavailable candidate's rationale, exact failure, last attempt,
  possible alternative and next review date in the generated catalog.
- [ ] Do not hit known-broken endpoints in every daily run.
- [ ] Remove an active source only after repeated failure, persistent
  irrelevance, replacement by a better primary source or inability to acquire
  complete lawful content.
- [ ] Preserve additions, removals and reasons in catalog history.

Acceptance criteria for Workstream G:

- The catalog is generated from structured metadata and explains purpose,
  cadence, acquisition method, status and health for every source.
- Every active source has recent live evidence; every unavailable desirable
  source has an actionable retest record.
- Summaries, partial pages, ads, wrong PDFs, stale feeds and missing timestamps
  cannot pass silently.
- Primary evidence cannot be crowded out by high-volume commentary.
- Every new source passes the admission gate.
- Local and GitHub runs use identical acquisition, classification and selection
  behavior.

## 11. Workstream H — timestamped market context

The current source corpus is mainly qualitative. A trading decision layer also
needs objective market context. This work begins only after the qualitative v2
brief and its evaluation are stable.

Until this layer exists, set `market_data_available` to false, label any value
reported by an article as source-reported with its publication time, and treat
candidate expressions as research hypotheses requiring market confirmation.

### H1. Define the required snapshot

- [ ] Rates: policy rates, benchmark yields, curve slopes and selected real-rate
  or inflation-compensation measures.
- [ ] FX: major crosses relevant to the source coverage.
- [ ] Equities: broad regional indices and relevant sector baskets.
- [ ] Credit: representative investment-grade, high-yield and funding spreads
  where legitimately available.
- [ ] Commodities: energy, industrial metals and precious metals relevant to
  macro transmission.
- [ ] Volatility and financial conditions where a reputable source permits.
- [ ] One-day, five-day and one-month changes with a clearly defined timestamp.

### H2. Select providers

- [ ] Evaluate official or appropriately licensed providers for accuracy,
  timeliness, history, stable access, redistribution terms and failure
  behavior.
- [ ] Prefer primary statistical and central-bank data for macro series.
- [ ] Do not scrape unstable consumer quote pages when a documented data source
  exists.
- [ ] Record provider, symbol/series identifier, units, timezone, observation
  time and transformation for every value.
- [ ] Make provider choice a documented decision before implementation.
- [ ] Decide whether the 19:30 Amsterdam report uses clearly labelled delayed
  US intraday data or whether the run moves later to use completed closes; do
  not mix those conventions silently.
- [ ] Define a provider-neutral interface so a lawful provider can be changed
  without rewriting synthesis or report schemas.

### H3. Integrate data deterministically

- [ ] Calculate changes, slopes and spreads in local code rather than asking the
  language model to infer them from raw tables.
- [ ] Pass a compact timestamped market snapshot to synthesis separately from
  narrative documents.
- [ ] Cite or attribute every market value to its provider.
- [ ] Store canonical instrument identifier, field, units, currency, timestamp,
  timezone, and real-time/delayed/previous-close status.
- [ ] Mark stale or missing data explicitly and continue with the qualitative
  brief when appropriate.
- [ ] Allow entry, invalidation and relative-value levels only when supported by
  this timestamped layer.

Acceptance criteria for Workstream H:

- No displayed market number lacks provider, timestamp, units and transformation
  provenance.
- The same input snapshot produces the same calculated changes.
- Missing market data cannot silently become a model estimate.
- The brief distinguishes a sound macro thesis from an unattractive current
  market expression.
- The as-of convention is prominent and delayed intraday data is never confused
  with a completed close.

## 12. Workstream I — delivery, retention and usability

This follows the stable report format in Workstream E and does not wait for
market-data enrichment in Workstream H.

### I1. Make successful reports discoverable

- [x] Increase hosted artifact retention from the current 14 days to an agreed
  useful period.
- [x] Put a direct artifact link and concise outcome summary on the run page.
- [x] Add a repository workflow-status badge and clear instructions for finding
  the latest report.
- [x] Do not publish personal research outputs permanently in the public source
  repository by accident.

### I2. Deliver reports to a Telegram channel

- [x] Add a small Telegram delivery adapter that sends the completed PDF as a
  document through the official Telegram Bot API.
- [x] Configure the destination with `TELEGRAM_BOT_TOKEN` as a GitHub/local
  secret and `TELEGRAM_CHAT_ID` as an explicit environment or repository
  variable; never place either value in source, artifacts or logs.
- [x] Document how to create the bot, add it to the selected channel and grant
  only the permission needed to publish messages.
- [x] Keep delivery disabled when configuration is absent. A local run sends
  only when explicitly requested, while a scheduled GitHub run sends
  automatically after a successful render when Telegram is configured.
- [x] Send successful and degraded PDFs with a concise caption containing the
  report date, run outcome, coverage warning, failed-source count and GitHub run
  link.
- [x] Send a short status message rather than inventing a PDF for a normal
  no-data outcome; make failure notifications a separately configurable option.
- [x] Validate the PDF against the Bot API's current document-size and file-type
  requirements before attempting delivery.
- [x] Use report run ID plus PDF content hash as an idempotency key, store the
  returned Telegram message ID, and prevent automatic retries or workflow
  reruns from posting duplicate reports.
- [x] Provide an explicit force-resend command for intentional redelivery.
- [x] Use bounded retries only for safe transient failures and respect Telegram
  retry guidance; do not loop indefinitely.
- [x] Preserve the generated artifact when delivery fails. Record delivery as a
  separate failed stage with the sanitized API error and a link for manual
  download.
- [x] Escape or constrain captions so report/source text cannot inject Telegram
  formatting or commands.
- [x] Test the adapter with a fake HTTP client for success, missing
  configuration, permission errors, rate limits, oversized files, duplicate
  suppression, force-resend and sanitized logging. Routine tests must not send
  live Telegram messages.

Acceptance criteria:

- One successful scheduled run posts exactly one matching PDF to the configured
  Telegram channel.
- The message identifies the report date and warns visibly when the report is
  degraded or has failed sources.
- A Telegram outage cannot destroy or hide an otherwise valid report.
- The bot token never appears in logs, exceptions, artifacts or test fixtures.
- Local and GitHub delivery use the same adapter and configuration contract.

### I3. Improve notifications

- [x] Make application failure summaries state the exact failed stage and
  whether a usable partial artifact exists.
- [x] Distinguish source degradation, no-data, application failure and GitHub
  infrastructure failure.
- [x] Provide a useful success notification or delivery link once the delivery
  channel is selected.
- [x] Avoid notification noise from normal no-publication days.

### I4. Preserve local usability

- [x] Rebuild the local virtual environment from the current pyproject.
- [x] Verify documented commands from a clean checkout.
- [x] Keep podcast dependencies optional.
- [x] Add a simple command for locating/opening the latest local PDF.
- [x] Keep remote-only behavior out of application logic.

Acceptance criteria for Workstream I:

- The owner can find the latest successful PDF without opening job logs.
- A configured scheduled run delivers the PDF exactly once to the selected
  Telegram channel.
- A failure notification explains what happened in plain language.
- Local and hosted runs produce the same report for the same saved corpus and
  model response.

## 13. Workstream J — testing, reproducibility, artifact safety and release
hardening

J is not deferred housekeeping. J1 and J2 apply to every milestone; the clean
environment and initial dependency lock from J3 plus all of J4 are P0 parts of
Milestone 1. Only final compatibility closure and release discipline wait until
the release-candidate milestone.

### J1. Expand deterministic tests

- [ ] Unit-test date resolution, citation mapping, run outcomes, schema
  validation, history comparison, transcript provenance and source cadence.
- [ ] Add CLI integration tests for collect, synthesize, run, no-data and
  degraded paths.
- [ ] Add fake OpenAI clients for synthesis and transcription payload contracts.
- [ ] Add storage migration tests from the current database schema.
- [x] Add Markdown/JSON parity tests and PDF content assertions.
- [x] Keep all routine CI tests offline and free of live publisher/API
  dependencies.

### J2. Add replay and visual checks

- [ ] Retain sanitized historical manifests for the known failure classes.
- [ ] Replay pipeline stages without redownloading sources.
- [x] Render representative PDFs and inspect page images after layout changes.
- [x] Verify hyperlinks, pagination, long titles, empty sections, multilingual
  text and large source registers.

### J3. Make dependencies reproducible

- [x] Replace the stale local environment.
- [x] Choose and document one lock/constraints strategy for application and
  development dependencies.
- [x] Make GitHub install the tested dependency set rather than unconstrained
  future versions.
- [ ] Add controlled dependency-update automation with CI verification.
- [x] Test the supported Python versions declared by the project.
- [x] Consolidate committed model and runtime defaults into one authoritative
  configuration layer; `.env`, repository variables and workflow inputs should
  be explicit overrides, not duplicate defaults.
- [x] Treat empty local or GitHub override variables as absent rather than as an
  invalid model name or path.
- [x] Add a quick deterministic environment/bootstrap check that verifies the
  active interpreter imports this checkout rather than a stale editable install.
- [x] Inventory ignored legacy audio, downloads, databases and build metadata
  before any cleanup, and request approval before deleting or archiving user
  data.

Implementation note (2026-08-28): the broken 385 MB virtual environment was
replaced; 283 MB of ignored historical downloads, the local database and prior
outputs were inventoried and retained unchanged.

### J4. Protect source material and hosted artifacts

- [x] Separate the private internal synthesis corpus from the user-facing audit
  manifest.
- [x] Do not upload complete article bodies or podcast transcripts in hosted
  workflow artifacts.
- [ ] Keep artifact manifests useful with metadata, canonical links, content
  hashes, revision IDs, extraction/transcription provenance, omissions and
  failures.
- [x] Define local raw-content retention and access expectations separately
  from hosted artifact retention.
- [x] Verify that exception strings, request diagnostics and rendered outputs do
  not expose API keys, authorization headers or repository secrets.
- [x] Add artifact-content tests using distinctive fixture text to prove raw
  bodies and secrets are absent.

Acceptance criteria:

- Hosted artifacts contain no article/transcript body while citations and
  diagnostics remain useful.
- Local raw material is never deleted implicitly.

### J5. Release discipline

- [x] Update architecture, models, sources, catalog and README in the same
  changes that alter behavior.
- [x] Maintain a concise changelog.
- [ ] Use schema and database migrations for breaking changes.
- [x] Run a fixed-date canary before enabling each major change on the schedule;
  Milestone 3 canary `33274205799` passed before its first scheduled window.
- [ ] Observe at least five consecutive scheduled runs after the reliability
  release before stacking another major operational change.

Acceptance criteria for Workstream J:

- A clean checkout can be installed and tested using documented commands.
- Historical failure fixtures remain fixed.
- Dependency updates cannot silently change production behavior.
- Each release records its prompt, schema, model, source and storage versions.

## 14. Decision register

### Confirmed direction

- The weekday GitHub schedule remains active; this planning pass does not pause
  or modify it.
- Local and GitHub execution remain two entry points to the same application.
- Every source failure remains explicit in human-readable output.
- Strict citations stay; reliability is fixed through a better citation
  interface, not weaker validation.
- Synthesis stays one bounded, structured request over a selected corpus; the
  obsolete recursive chunk-summary pipeline will not return.
- Podcast speech recognition remains cloud-based; the Intel Mac will not run a
  local neural model.
- A report may say “no material change” or provide no actionable setup.
- DailyBriefV2 is the production report baseline after a successful hosted
  canary and positive owner review; future prompt, schema or layout changes must
  answer an observed defect and pass the evaluation contract.
- Telegram is the selected external delivery channel for completed PDFs; the
  same delivery adapter must work from GitHub and from an explicitly enabled
  local run.
- The product supports research decisions but does not place orders, select
  leverage or size a portfolio.
- Cost-safety features are excluded from this roadmap.

### Decisions deliberately left for evidence or owner approval

- Promote gpt-transcribe only after the saved-audio comparison in Workstream F.
- The dedicated `macro-sage-history` Git branch is the durable hosted history
  store; it contains body-free append-only JSON records and Git-native backup.
- Select and license market-data providers, and choose delayed intraday versus
  completed-close timing, before making current-market claims.
- Confirm the Telegram channel identifier and its public/private visibility
  before adding live delivery configuration. No-data messages are enabled;
  failure messages remain separately opt-in; artifact retention is 30 days.
- Enable new sources only after the Workstream G admission gate, even when the
  institution is reputable.

## 15. Implementation milestones

### Milestone 0 — plan approval

- [x] Consolidate current status and prior discussions.
- [x] Exclude cost-safety features.
- [x] Review and approve this roadmap.

Approved for implementation on 2026-08-28.

### Milestone 1 — safe runner v0.4

Includes A1, A2, phase 1 of A3, A4, the safe deterministic subset of A5, the
single-preflight subset of A6, the clean environment/bootstrap/initial
dependency-lock subset of J3, the hosted-artifact-safety subset of J4, and the
relevant J1/J2 checks. Unchecked items in those workstreams remain planned and
are not implied complete by this milestone.

Implementation status: code-complete on 2026-08-28 in version 0.4.0. The
operational observation gate remains open until five consecutive scheduled runs
complete without a known application reliability failure.

Exit gate:

- historical source-ID failures are fixed;
- delayed-date and two-dimensional no-data/health behavior are correct;
- GitHub summaries and per-attempt diagnostics are useful;
- hosted artifacts contain no raw article or transcript bodies;
- a clean local environment imports this checkout and runs the bounded offline
  check command predictably;
- five consecutive scheduled runs contain no known application reliability
  failure.

### Milestone 2 — trustworthy acquisition foundation v0.45

Includes G1–G5, including the G2 live validation baseline, B1 storage and
version migrations, and the relevant J1/J2 fixtures.

Implementation status: code-complete on 2026-08-29 in application version
0.4.6. The dated baseline contains 45 passing, one visibly degraded and one
failed contract. Publisher-transcript,
advertisement and rich podcast-programme metadata items explicitly remain in
Milestone 5; ongoing cadence monitoring, selection balancing and source
expansion remain G6–G9.

Closure audit status: complete on 2026-08-29. Automated validation and manual
approval are separate, fingerprint-bound operations. All 47 contracts were
inspected and explicitly decided against extractor-version-3 evidence from
commit `0848e6f`: 44 approved, Norges Regional Network and HSBC Macro Brief
approved with limitations, and BIS Research Hub rejected after its official RSS
endpoint returned HTTP 404 twice. CI passed on Python 3.11 and 3.12, and hosted
run `33262329610` exercised article collection, six podcast transcriptions,
synthesis, PDF rendering and sanitized artifact upload on commit `91ed76b`.

Exit gate:

- the catalog is generated from the structured inventory;
- every active source has a fresh, machine-readable validation result;
- publication dating, full-content quality, document identity, revisions and
  discovery provenance pass their acceptance criteria;
- durable identifiers and cache contracts are ready for history and podcast
  variants.

### Milestone 3 — durable history and comparison v0.46

Includes B2–B3, phase 2 of A3 and their storage/replay tests.

Implementation status: code-complete in application version 0.4.7 on
2026-08-29. Local and hosted execution share an append-only, versioned JSON
history interface. The hosted backend is the dedicated `macro-sage-history`
branch, not Actions cache. Reports expose baseline health plus deterministic
one-day and one-week regime, thesis, event and asset-view changes. Scheduled
collection uses persisted half-open cutoff windows; manual dates remain
calendar replays and cannot advance the scheduled cutoff chain. Closure still
requires the first live scheduled-window observation.

Hosted canary status: passed on 2026-08-29. Run
[`33274205799`](https://github.com/Phoendor/macro_sage/actions/runs/33274205799)
used commit `532d8ae` and a deterministic 2026-08-28 calendar replay without
podcasts. It collected 20 documents, retained nine explicit source
limitations, synthesized with `gpt-5.6-luna`, rendered a 10-page PDF, uploaded
a body-free artifact and remained `history_sync_pending` until history commit
`8735886` reached the dedicated branch. The record correctly reported
`first_run`, contained 20 document references and 12 cited references, and no
source body. Artifact and per-run PDF hashes matched. The canary also identified
and drove fixture coverage for single-currency, commodity, sovereign-rate and
near-term canonical labels before the first scheduled comparison.

Exit gate:

- successful briefs persist outside the evictable Actions cache;
- the next run can state trustworthy regime/thesis changes relative to the last
  comparable success;
- scheduled collection uses a stable previous-cutoff-to-current-cutoff window
  without weekend gaps or duplicates.

### Milestone 4 — decision brief and delivery v0.5

Freeze D1 first, then implement C1–C3, D2–D3, E1–E2 and I1–I4 with their
contract, evidence, temporal and visual tests.

Implementation status: code-complete in application version 0.5.0 on
2026-08-30. DailyBriefV2, deterministic evidence-confidence calibration,
grounding evaluation, semantically equivalent JSON/Markdown/PDF output, the
decision-first PDF, 30-day hosted artifacts, latest-report discovery and
optional idempotent Telegram delivery are implemented and covered by offline
tests. The 15-case body-free evaluation inventory is frozen, but only the two
retained local dates currently have complete lawful corpora. The milestone exit
gate therefore uses same-corpus V1/V2 comparison only on those two lawful
corpora and accumulates claim and usefulness audits prospectively across ten V2
reports. The owner positively reviewed the canary's information hierarchy and
output quality on 2026-08-30. The first live configured Telegram delivery
completed on 2026-09-01; only the evidence audit remains open and it is not
represented as complete by the code release.

Hosted canary
[33319046110](https://github.com/Phoendor/macro_sage/actions/runs/33319046110)
passed on commit `12ae26b` with podcasts disabled. It collected 20 documents,
kept all nine failed or expected-but-absent sources explicit, synthesized schema
2 with `gpt-5.6-luna`, produced a 10-page PDF, persisted body-free history and
uploaded the 30-day artifact. The deterministic evaluator found 27 material
claims, 12 cited documents and zero contract defects. Visual inspection of the
actual hosted PDF confirmed the three leading changes, regime dashboard,
no-setup decision and nearest event risk all remain on page one. Telegram was
correctly skipped because live channel configuration is absent.

The first live Telegram delivery passed on 2026-09-01 in hosted run
[`33495839234`](https://github.com/Phoendor/macro_sage/actions/runs/33495839234).
The workflow generated the fixed-date 2026-08-31 report with podcasts disabled,
sent the PDF to the configured `@macro_sage` channel, reported `Telegram
delivery: sent`, and persisted the idempotency state to durable history before
completing successfully. This closes the live-delivery observation; the normal
scheduled brief remains unchanged.

Exit gate:

- V2 beats the frozen baseline on both retained same-corpus cases and passes
  the prospective production-report usefulness gate;
- all formats agree and the first page is useful in roughly two minutes;
- source failures and market-data limitations remain prominent;
- the latest successful report is immediately discoverable and, when Telegram
  configuration is present, delivered exactly once to the selected channel;
- the owner has approved the information hierarchy and output quality.

### Milestone 5 — trustworthy daily corpus

Includes the remaining critical-coverage rule from A2, G6–G7, safe corpus
serialization, cadence-aware health, deterministic relevance and authority
ranking, enforceable publisher/product-line caps and the associated J1/J2
fixtures. Source admission does not expand yet.

Implementation status: the first version-0.6 tranche is code-complete on
2026-08-30. It implements critical-role coverage rule v1, SQLite source-health
history, independent weekday discovery and weekly extraction workflows,
explicit participation outcomes, deterministic ranked/capped corpus admission,
auditable omission reasons and safe JSON evidence serialization. The bounded
offline suite passes 142 tests. Both hosted validation gates passed on
2026-08-30. Milestone closure remains open only for the unchecked G7 work on
cross-publisher evidence-family grouping, BIS/originating-bank speech
deduplication and model-aware token accounting.

The corrected discovery-only health run
[`33337257541`](https://github.com/Phoendor/macro_sage/actions/runs/33337257541)
passed on commit `60d3b13` in 37 seconds without an OpenAI request or podcast
download. It reported 23 healthy sources, eight genuine warnings and zero
sources at the failure threshold. Expected timestamp derivation notes remained
healthy, while stale, invalid and failed discovery observations remained
visible. The workflow persisted health history and uploaded a body-free
evidence artifact.

The fixed-date report canary
[`33337311571`](https://github.com/Phoendor/macro_sage/actions/runs/33337311571)
passed on the same commit in 1 minute 41 seconds with podcasts disabled. It
collected 20 documents, admitted nine complete and three deliberately truncated
documents from six publishers, omitted eight with explicit machine-readable
reasons, and synthesized with `gpt-5.6-luna` from 52,263 input tokens. It
rendered a valid 10-page PDF, persisted durable history and uploaded the report
and audit trail. Telegram delivery was correctly skipped because live channel
configuration remains absent.

Exit gate:

- source participation and cadence-aware health are reported separately;
- material coverage failures use configured critical roles and explicit rules;
- primary evidence receives reserved capacity and prolific publishers cannot
  dominate merely through volume;
- relevance filters and every omission remain deterministic and auditable;
- document text cannot alter model-facing document boundaries or instructions.

### Milestone 6 — quantified market context

Includes H1–H3. Provider selection and the report's delayed-intraday versus
completed-close convention must be decided before implementation is enabled.

Exit gate:

- the brief can place narratives against timestamped market context;
- the intraday-versus-completed-close convention is explicit;
- every value has provider and transformation provenance;
- missing market data cannot become an implied model estimate.

### Milestone 7 — modern podcasts

Includes F0–F5 and the podcast-specific portions of G4/G5.

Exit gate:

- the recorded-audio model choice is supported by an A/B evaluation;
- official transcripts are preferred and preserved when available;
- arbitrary 15-minute cuts are gone;
- transcript variants, provenance, long-form selection and cache behavior are
  correct.

### Milestone 8 — selective source expansion

Includes G8–G9 after Milestone 5 selection and health controls are operating.

Exit gate:

- broken candidates are accurately documented and retested on a bounded
  cadence rather than during every daily run;
- approved coverage gaps have working sources and fixtures;
- every enabled addition passes the admission gate and adds distinct coverage.

### Milestone 9 — release candidate

Includes remaining J3/J5 work and cross-workstream documentation.

Exit gate:

- clean local and GitHub reproducibility;
- full deterministic test and replay suite;
- visual PDF verification;
- current architecture, source catalog and operating guide;
- ten consecutive scheduled runs without a known application defect.

## 16. Global definition of done

The roadmap is complete when:

- scheduled execution selects the correct Amsterdam publication date even when
  delayed;
- normal empty days do not generate false failures;
- every important claim and view has a valid, clickable source;
- model-visible citations cannot be corrupted opaque hashes;
- every source failure is explicit;
- source participation, health, publication absence, filtering and item-level
  failures are distinct states;
- the brief states what changed, transmission, scenarios, catalysts,
  invalidations, counterarguments and confidence rationale;
- source facts, source opinion and Macro Sage inference are visibly different;
- prior briefs are used for comparison but never treated as primary evidence;
- every transcript has model and prompt provenance and normal episodes are not
  arbitrarily split;
- every active source has a current successful validation record;
- active primary evidence cannot be crowded out merely by prolific commentary
  publishers;
- market values, when added, always carry timestamp and provider provenance;
- JSON, Markdown and PDF agree;
- the owner can reliably receive or find the latest report;
- a configured scheduled run delivers exactly one PDF to the selected Telegram
  channel without exposing its bot credentials;
- local and GitHub execution remain the same application;
- all tests and documented clean-install checks pass;
- hosted artifacts contain no raw article or transcript bodies, and durable
  brief history does not depend solely on an Actions cache.

## 17. Explicitly deferred or excluded

These are not part of the current roadmap:

- cost-safety features, spending caps, balance alerts or cost dashboards;
- automated brokerage or exchange connectivity;
- automatic order placement;
- portfolio-specific position sizing or leverage;
- high-frequency or intraday signal generation;
- a live transcription service;
- local neural transcription on the 2019 Intel Mac;
- paid market-data subscriptions before a provider decision;
- weakening citation validation to improve the workflow success rate;
- keeping broken sources enabled merely for broader apparent coverage.

## 18. First implementation batch after approval

Status: implemented in version 0.4.0 on 2026-08-28; scheduled-run observation
continues under the Milestone 1 exit gate.

The first implementation batch should contain only:

1. short run-scoped citation keys and strict mapping;
2. explicit content-result and run-health dimensions;
3. delay-safe Amsterdam target-date resolution;
4. clearer GitHub summaries and always-available diagnostics;
5. regression fixtures for the nine observed application failures and clear
   classification of the GitHub infrastructure failure;
6. one immutable model selection per model-backed run, without burdening plain
   collection;
7. a rebuilt local environment, tested dependency lock and quick bootstrap
   check;
8. sanitized hosted artifacts that exclude raw article/transcript bodies;
9. the accompanying documentation and cross-cutting tests.

This batch deliberately does not change the synthesis content, transcription
model, source list or report design. It establishes a reliable base so later
output improvements can be evaluated without confusing infrastructure defects
with research-quality defects.
