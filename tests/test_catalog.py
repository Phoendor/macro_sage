from pathlib import Path

from macro_sage.catalog import render_catalog, render_coverage_matrix
from macro_sage.config import load_inventory


def test_generated_catalog_and_coverage_match_authoritative_inventory():
    inventory = load_inventory("config/sources.toml")

    assert Path("docs/SOURCE_CATALOG.md").read_text(
        encoding="utf-8"
    ) == render_catalog(inventory)
    assert Path("docs/SOURCE_COVERAGE.md").read_text(
        encoding="utf-8"
    ) == render_coverage_matrix(inventory)


def test_catalog_exposes_required_human_fields_and_candidate_registry():
    catalog = Path("docs/SOURCE_CATALOG.md").read_text(encoding="utf-8")

    assert "Publication frequency" in catalog
    assert "Why I need it" in catalog
    assert "## Would be good to have, but these don't work" in catalog
    assert "Exact failure / constraint" in catalog
