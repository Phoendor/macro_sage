# Macro Sage evaluation baseline

This directory freezes the acceptance contract that existed immediately before
DailyBriefV2. It is intentionally body-free. Publisher text and podcast
transcripts remain in the private local corpus or the evictable hosted cache;
they are not copied into Git.

`cases.json` records 15 representative historical or contract cases and states
exactly which replay material is available. Two complete local corpora can be
replayed by the owner from the ignored `output/` directory. The durable hosted
case contains only its body-free history record. Older GitHub cases retain run
metadata and failure classification but not source bodies. A case without a
corpus may test orchestration or contract behavior, but must never be presented
as a same-corpus model comparison.

`RUBRIC.md` is the human and deterministic scoring contract. `DEFECT_LOG.md`
freezes the observed V1 defects that justified the redesign. The command below
runs the deterministic portion against any saved output:

```bash
macro-sage evaluate --brief path/to/brief.json --manifest path/to/manifest.json
```

Human review remains authoritative for factual support, prioritization,
transmission quality and trading usefulness. Model-assisted grading may be
added to an evaluation run, but it may not override a critical deterministic or
human grounding defect.
