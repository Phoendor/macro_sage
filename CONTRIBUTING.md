# Contributing

Macro Sage is a small daily research pipeline. Keep changes source-attributed,
testable, and inexpensive to run.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest
```

## Working agreements

1. Create a feature branch; do not develop directly on `main`.
2. Keep credentials and downloaded source material out of Git.
3. Add offline tests for parsing, normalization, and orchestration behavior.
4. Mock network and model calls in the test suite.
5. Run the lint, test, and compile checks from the README before opening a pull request.
6. Document new feed-specific behavior, failure modes, and attribution fields.
7. Never put live feeds or paid API calls in the deterministic test suite.

## Commit and pull request scope

- Prefer one coherent change per pull request.
- Explain the user-visible behavior and the validation performed.
- Call out live-source checks separately from deterministic automated tests.
- Do not include audio files, transcripts, local databases, IDE settings, or
  virtual environments.

## Security incidents

If a secret is committed:

1. Revoke or rotate it immediately.
2. Stop before pushing any affected history.
3. Create a clean branch from a known-safe remote commit.
4. reapply only sanitized changes, then scan the resulting history.

Deleting a secret in a later commit does not remove it from earlier commits.
