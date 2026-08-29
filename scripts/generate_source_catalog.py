from __future__ import annotations

import argparse
from pathlib import Path

from macro_sage.catalog import generate_catalog


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    generate_catalog(
        Path("config/sources.toml"),
        Path("docs/SOURCE_CATALOG.md"),
        Path("docs/SOURCE_COVERAGE.md"),
        check=args.check,
    )


if __name__ == "__main__":
    main()
