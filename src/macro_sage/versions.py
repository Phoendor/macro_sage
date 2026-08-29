from __future__ import annotations

import os
import subprocess
from pathlib import Path

from macro_sage import __version__

SOURCE_CONFIG_VERSION = 2
EXTRACTOR_VERSION = "3"
CORPUS_VERSION = "2"
SYNTHESIS_PROMPT_VERSION = "2"
BRIEF_SCHEMA_VERSION = "1"
TRANSCRIPTION_PROMPT_VERSION = "1"
RENDERER_VERSION = "2"
DATABASE_SCHEMA_VERSION = 2
HISTORY_STORE_VERSION = 1
HISTORY_RECORD_VERSION = 1
DATE_RESOLUTION_VERSION = 2
ACQUISITION_WINDOW_VERSION = 1
COMPARISON_KEY_VERSION = 1


def git_revision(root: Path | None = None) -> str | None:
    configured = os.getenv("GITHUB_SHA", "").strip()
    if configured:
        return configured
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def transformation_versions(root: Path | None = None) -> dict[str, object]:
    return {
        "application": __version__,
        "git_commit": git_revision(root),
        "source_config": SOURCE_CONFIG_VERSION,
        "extractor": EXTRACTOR_VERSION,
        "corpus": CORPUS_VERSION,
        "synthesis_prompt": SYNTHESIS_PROMPT_VERSION,
        "brief_schema": BRIEF_SCHEMA_VERSION,
        "transcription_prompt": TRANSCRIPTION_PROMPT_VERSION,
        "renderer": RENDERER_VERSION,
        "database_schema": DATABASE_SCHEMA_VERSION,
        "history_store": HISTORY_STORE_VERSION,
        "history_record": HISTORY_RECORD_VERSION,
        "date_resolution": DATE_RESOLUTION_VERSION,
        "acquisition_window": ACQUISITION_WINDOW_VERSION,
        "comparison_keys": COMPARISON_KEY_VERSION,
    }
