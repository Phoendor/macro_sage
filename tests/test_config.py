from pathlib import Path

import pytest

from macro_sage.config import ConfigurationError, load_sources
from macro_sage.models import SourceKind


def test_repository_source_config_is_valid():
    sources = load_sources(Path("config/sources.toml"))

    assert len(sources) >= 15
    assert all(source.enabled for source in sources)
    assert all(source.kind is SourceKind.ARTICLE for source in sources)


def test_disabled_podcasts_are_only_loaded_explicitly():
    all_sources = load_sources(Path("config/sources.toml"), include_disabled=True)

    podcasts = [source for source in all_sources if source.kind is SourceKind.PODCAST]
    assert podcasts
    assert all(not source.enabled for source in podcasts)


def test_duplicate_source_ids_are_rejected(tmp_path):
    config = tmp_path / "sources.toml"
    config.write_text(
        """
[[sources]]
id = "same"
name = "One"
publisher = "Publisher"
feed_url = "https://example.com/one.xml"
category = "research"

[[sources]]
id = "same"
name = "Two"
publisher = "Publisher"
feed_url = "https://example.com/two.xml"
category = "research"
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="Duplicate"):
        load_sources(config)
