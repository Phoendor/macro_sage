# Cache, identity and migration contract

Macro Sage's SQLite database is an application cache and local evidence store.
Schema migrations run automatically and transactionally when `DocumentStore`
opens the database; the application never deletes or recreates the database to
upgrade it.

## Schema 2

- `documents` owns source-independent canonical identities.
- `document_revisions` preserves immutable bodies and extraction provenance.
- `discovery_origins` records every source/feed path that exposed a document.
- `source_health_events` records acquisition health separately from content.
- `duplicate_candidates` records similar-title review suggestions without
  merging them.

Legacy schema-1 rows migrate to a preserved `legacy-v1` revision with a quality
flag. Their IDs remain valid so older manifests and caches continue to resolve.

## Reuse and invalidation

Canonical/final URLs and exact content hashes may deduplicate a document. A
similar title never does. A cached revision is conditionally revalidated with
ETag or Last-Modified only when:

- the extractor version is unchanged;
- the cached revision has no quality warning; and
- the feed does not report a newer update time.

Otherwise the content is fetched and extracted again. A changed body or
extractor version produces a new immutable revision. Publisher corrections,
changed canonical URLs, extraction improvements and prior degraded fallbacks
therefore cannot be hidden by an apparently successful cache hit.

Extractor version 3 corrects HTML character decoding from publisher bytes and
therefore invalidates older HTML revisions that may contain mojibake.

Changing `SOURCE_CONFIG_VERSION`, `EXTRACTOR_VERSION`, corpus/prompt/schema,
transcription prompt or renderer versions must be deliberate. The exact version
set, application version, Git commit, selected models and reasoning setting are
written to `run.json`. A future transcription-contract change must also bump the
hosted data-cache namespace before old transcripts can be treated as equivalent.

GitHub Actions cache is only a performance accelerator. It is not the durable
brief-history store. Successful brief history uses an append-only local
directory and the dedicated hosted `macro-sage-history` branch described in
[the history contract](HISTORY.md).
