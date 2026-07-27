import re
from pathlib import Path

from macro_sage.config import load_sources


def test_source_catalog_matches_configuration():
    catalog = Path("docs/SOURCE_CATALOG.md").read_text(encoding="utf-8")
    catalog_ids = re.findall(r"^\| `([^`]+)` \|", catalog, flags=re.MULTILINE)
    configured_ids = [
        source.id
        for source in load_sources("config/sources.toml", include_disabled=True)
    ]

    assert len(catalog_ids) == len(set(catalog_ids))
    assert set(catalog_ids) == set(configured_ids)
    assert "Why I need it" in catalog
    assert "**O (observed):**" in catalog
    assert "**I (implicit):**" in catalog
    assert "**E (expected):**" in catalog
    assert "## Would be good to have, but these don't work" in catalog
