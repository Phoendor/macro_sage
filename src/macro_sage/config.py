from __future__ import annotations

import tomllib
from pathlib import Path

from macro_sage.models import SourceDefinition, SourceKind


class ConfigurationError(ValueError):
    pass


def load_sources(
    path: str | Path,
    *,
    include_disabled: bool = False,
) -> list[SourceDefinition]:
    config_path = Path(path)
    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)

    rows = raw.get("sources")
    if not isinstance(rows, list) or not rows:
        raise ConfigurationError("sources.toml must contain at least one [[sources]] table")

    sources: list[SourceDefinition] = []
    seen: set[str] = set()
    for row in rows:
        try:
            source = SourceDefinition(
                id=row["id"],
                name=row["name"],
                publisher=row["publisher"],
                feed_url=row["feed_url"],
                category=row["category"],
                kind=SourceKind(row.get("kind", "article")),
                enabled=bool(row.get("enabled", True)),
                max_items=int(row.get("max_items", 3)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ConfigurationError(f"Invalid source row: {row!r}") from exc

        if source.id in seen:
            raise ConfigurationError(f"Duplicate source id: {source.id}")
        if not source.feed_url.startswith("https://"):
            raise ConfigurationError(f"{source.id}: feed_url must use HTTPS")
        if source.max_items < 1:
            raise ConfigurationError(f"{source.id}: max_items must be positive")
        seen.add(source.id)
        if source.enabled or include_disabled:
            sources.append(source)

    return sources
