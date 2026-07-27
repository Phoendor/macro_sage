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


def test_disabled_article_sources_explain_why_they_are_unavailable():
    all_sources = load_sources(Path("config/sources.toml"), include_disabled=True)
    disabled_articles = [
        source
        for source in all_sources
        if source.kind is SourceKind.ARTICLE and not source.enabled
    ]

    assert disabled_articles
    assert all(source.disabled_reason for source in disabled_articles)


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


def test_invalid_source_filter_is_rejected(tmp_path):
    config = tmp_path / "sources.toml"
    config.write_text(
        """
[[sources]]
id = "bad-filter"
name = "Bad Filter"
publisher = "Publisher"
feed_url = "https://example.com/feed.xml"
category = "research"
include_url_pattern = "["
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="invalid include_url_pattern"):
        load_sources(config)
