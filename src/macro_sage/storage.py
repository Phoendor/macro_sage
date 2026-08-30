from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import date, datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from zoneinfo import ZoneInfo

from macro_sage.feeds import canonicalize_url
from macro_sage.models import (
    AcquisitionMode,
    Document,
    FeedItem,
    SourceDefinition,
    SourceHealthSnapshot,
    SourceHealthStatus,
    SourceOutcome,
    SourceState,
)
from macro_sage.versions import DATABASE_SCHEMA_VERSION, EXTRACTOR_VERSION


class DocumentStore:
    def __init__(self, path: str | Path):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._migrate()

    def _table_columns(self, table: str) -> set[str]:
        return {
            str(row["name"])
            for row in self.connection.execute(f"PRAGMA table_info({table})")
        }

    def _migrate(self) -> None:
        legacy_rows: list[sqlite3.Row] = []
        columns = self._table_columns("documents")
        if columns and "body" in columns:
            legacy_rows = list(self.connection.execute("SELECT * FROM documents"))
            self.connection.execute("ALTER TABLE documents RENAME TO documents_v1")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                canonical_url TEXT NOT NULL UNIQUE,
                current_revision_id TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS document_revisions (
                revision_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL REFERENCES documents(id),
                source_id TEXT NOT NULL,
                source_name TEXT NOT NULL,
                publisher TEXT NOT NULL,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                original_url TEXT,
                resolved_content_url TEXT,
                published_at TEXT,
                updated_at TEXT,
                raw_published TEXT,
                raw_updated TEXT,
                body TEXT NOT NULL,
                author TEXT,
                media_type TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                language TEXT NOT NULL,
                content_sha256 TEXT NOT NULL,
                extractor_version TEXT NOT NULL,
                acquisition_method TEXT NOT NULL,
                quality_flags TEXT NOT NULL,
                etag TEXT,
                last_modified TEXT,
                page_count INTEGER,
                UNIQUE(document_id, content_sha256, extractor_version)
            );
            CREATE INDEX IF NOT EXISTS idx_revisions_document
                ON document_revisions(document_id, fetched_at DESC);
            CREATE INDEX IF NOT EXISTS idx_revisions_content
                ON document_revisions(content_sha256);
            CREATE TABLE IF NOT EXISTS discovery_origins (
                document_id TEXT NOT NULL REFERENCES documents(id),
                source_id TEXT NOT NULL,
                original_url TEXT NOT NULL,
                feed_url TEXT NOT NULL,
                guid TEXT NOT NULL DEFAULT '',
                publisher_id TEXT NOT NULL DEFAULT '',
                discovered_at TEXT NOT NULL,
                published_at TEXT,
                updated_at TEXT,
                PRIMARY KEY(document_id, source_id, original_url, guid)
            );
            CREATE INDEX IF NOT EXISTS idx_origins_url
                ON discovery_origins(original_url);
            CREATE TABLE IF NOT EXISTS source_health_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                checked_at TEXT NOT NULL,
                state TEXT NOT NULL,
                stage TEXT,
                detail TEXT,
                document_count INTEGER NOT NULL,
                latest_publication_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_source_health_source_checked
                ON source_health_events(source_id, checked_at DESC);
            CREATE TABLE IF NOT EXISTS duplicate_candidates (
                left_document_id TEXT NOT NULL REFERENCES documents(id),
                right_document_id TEXT NOT NULL REFERENCES documents(id),
                title_similarity REAL NOT NULL,
                proposed_at TEXT NOT NULL,
                PRIMARY KEY(left_document_id, right_document_id)
            );
            """
        )
        for row in legacy_rows:
            self._migrate_legacy(row)
        if legacy_rows:
            self.connection.execute("DROP TABLE documents_v1")
        self.connection.execute(
            "INSERT OR REPLACE INTO schema_metadata(key, value) VALUES('version', ?)",
            (str(DATABASE_SCHEMA_VERSION),),
        )
        if "latest_publication_at" not in self._table_columns("source_health_events"):
            self.connection.execute(
                "ALTER TABLE source_health_events ADD COLUMN latest_publication_at TEXT"
            )
        self.connection.commit()

    def _migrate_legacy(self, row: sqlite3.Row) -> None:
        canonical_url = canonicalize_url(str(row["url"]))
        content_sha256 = hashlib.sha256(str(row["body"]).encode()).hexdigest()
        document_id = str(row["id"])
        revision_id = hashlib.sha256(
            f"{canonical_url}\0{content_sha256}\0legacy-v1".encode()
        ).hexdigest()[:24]
        fetched_at = str(row["fetched_at"])
        self.connection.execute(
            "INSERT OR IGNORE INTO documents VALUES (?, ?, ?, ?)",
            (document_id, canonical_url, revision_id, fetched_at),
        )
        self.connection.execute(
            """
            INSERT OR IGNORE INTO document_revisions (
                revision_id, document_id, source_id, source_name, publisher,
                category, title, url, original_url, resolved_content_url,
                published_at, updated_at, raw_published, raw_updated, body,
                author, media_type, fetched_at, language, content_sha256,
                extractor_version, acquisition_method, quality_flags, etag,
                last_modified, page_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?, ?, ?,
                      ?, 'en', ?, 'legacy-v1', ?, '["legacy_migration"]', NULL,
                      NULL, NULL)
            """,
            (
                revision_id,
                document_id,
                row["source_id"],
                row["source_name"],
                row["publisher"],
                row["category"],
                row["title"],
                canonical_url,
                row["url"],
                row["url"],
                row["published_at"],
                row["body"],
                row["author"],
                row["media_type"],
                fetched_at,
                content_sha256,
                AcquisitionMode.FEED_BODY.value
                if row["media_type"] == "application/rss+xml"
                else AcquisitionMode.FULL_PDF.value
                if row["media_type"] == "application/pdf"
                else AcquisitionMode.FULL_HTML.value,
            ),
        )

    @property
    def schema_version(self) -> int:
        row = self.connection.execute(
            "SELECT value FROM schema_metadata WHERE key = 'version'"
        ).fetchone()
        return int(row["value"])

    def _document_from_row(self, row: sqlite3.Row) -> Document:
        origin_rows = self.connection.execute(
            "SELECT DISTINCT source_id FROM discovery_origins WHERE document_id = ?",
            (row["document_id"],),
        )
        origins = tuple(value["source_id"] for value in origin_rows)
        return Document(
            id=row["document_id"],
            source_id=row["source_id"],
            source_name=row["source_name"],
            publisher=row["publisher"],
            category=row["category"],
            title=row["title"],
            url=row["url"],
            published_at=(
                datetime.fromisoformat(row["published_at"])
                if row["published_at"]
                else None
            ),
            body=row["body"],
            author=row["author"],
            media_type=row["media_type"],
            original_url=row["original_url"],
            canonical_url=row["url"],
            resolved_content_url=row["resolved_content_url"],
            updated_at=(
                datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None
            ),
            raw_published=row["raw_published"],
            raw_updated=row["raw_updated"],
            fetched_at=datetime.fromisoformat(row["fetched_at"]),
            language=row["language"],
            content_sha256=row["content_sha256"],
            extractor_version=row["extractor_version"],
            acquisition_method=AcquisitionMode(row["acquisition_method"]),
            quality_flags=tuple(json.loads(row["quality_flags"])),
            revision_id=row["revision_id"],
            etag=row["etag"],
            last_modified=row["last_modified"],
            page_count=row["page_count"],
            discovery_source_ids=origins or (row["source_id"],),
        )

    def get(self, document_id: str) -> Document | None:
        row = self.connection.execute(
            """
            SELECT r.* FROM documents d
            JOIN document_revisions r ON r.revision_id = d.current_revision_id
            WHERE d.id = ?
            """,
            (document_id,),
        ).fetchone()
        return self._document_from_row(row) if row else None

    def get_for_item(self, item: FeedItem) -> Document | None:
        direct = self.get(item.document_id)
        if direct:
            return direct
        normalized = canonicalize_url(item.original_url or item.url)
        row = self.connection.execute(
            """
            SELECT document_id FROM discovery_origins
            WHERE original_url IN (?, ?)
            ORDER BY discovered_at DESC LIMIT 1
            """,
            (item.original_url or item.url, normalized),
        ).fetchone()
        return self.get(row["document_id"]) if row else None

    def _record_origin(self, document_id: str, item: FeedItem) -> None:
        self.connection.execute(
            """
            INSERT OR REPLACE INTO discovery_origins (
                document_id, source_id, original_url, feed_url, guid,
                publisher_id, discovered_at, published_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document_id,
                item.source.id,
                item.original_url or item.url,
                item.source.feed_url,
                item.guid or "",
                item.publisher_id or "",
                datetime.now(timezone.utc).isoformat(),
                item.published_at.isoformat() if item.published_at else None,
                item.updated_at.isoformat() if item.updated_at else None,
            ),
        )

    def save(self, document: Document, *, item: FeedItem | None = None) -> Document:
        content_sha256 = document.content_sha256 or hashlib.sha256(
            document.body.encode()
        ).hexdigest()
        canonical_url = canonicalize_url(document.canonical_url or document.url)
        existing_content = self.connection.execute(
            """
            SELECT document_id, revision_id FROM document_revisions
            WHERE content_sha256 = ? LIMIT 1
            """,
            (content_sha256,),
        ).fetchone()
        existing_url = self.connection.execute(
            "SELECT id FROM documents WHERE canonical_url = ?",
            (canonical_url,),
        ).fetchone()
        document_id = (
            existing_url["id"]
            if existing_url
            else existing_content["document_id"]
            if existing_content
            else document.id
        )
        fetched_at = document.fetched_at or datetime.now(timezone.utc)
        matching_revision = self.connection.execute(
            """
            SELECT revision_id FROM document_revisions
            WHERE document_id = ? AND content_sha256 = ? AND extractor_version = ?
            LIMIT 1
            """,
            (
                document_id,
                content_sha256,
                document.extractor_version or EXTRACTOR_VERSION,
            ),
        ).fetchone()
        revision_id = (
            matching_revision["revision_id"]
            if matching_revision
            else document.revision_id
            or hashlib.sha256(
                f"{canonical_url}\0{content_sha256}\0{document.extractor_version or EXTRACTOR_VERSION}".encode()
            ).hexdigest()[:24]
        )
        self.connection.execute(
            "INSERT OR IGNORE INTO documents VALUES (?, ?, ?, ?)",
            (document_id, canonical_url, revision_id, fetched_at.isoformat()),
        )
        self.connection.execute(
            """
            INSERT OR IGNORE INTO document_revisions (
                revision_id, document_id, source_id, source_name, publisher,
                category, title, url, original_url, resolved_content_url,
                published_at, updated_at, raw_published, raw_updated, body,
                author, media_type, fetched_at, language, content_sha256,
                extractor_version, acquisition_method, quality_flags, etag,
                last_modified, page_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                      ?, ?, ?, ?, ?, ?)
            """,
            (
                revision_id,
                document_id,
                document.source_id,
                document.source_name,
                document.publisher,
                document.category,
                document.title,
                canonical_url,
                document.original_url,
                document.resolved_content_url,
                document.published_at.isoformat() if document.published_at else None,
                document.updated_at.isoformat() if document.updated_at else None,
                document.raw_published,
                document.raw_updated,
                document.body,
                document.author,
                document.media_type,
                fetched_at.isoformat(),
                document.language,
                content_sha256,
                document.extractor_version or EXTRACTOR_VERSION,
                document.acquisition_method.value,
                json.dumps(document.quality_flags),
                document.etag,
                document.last_modified,
                document.page_count,
            ),
        )
        self.connection.execute(
            "UPDATE documents SET current_revision_id = ? WHERE id = ?",
            (revision_id, document_id),
        )
        self._propose_title_duplicates(document_id, document.title, content_sha256)
        if item:
            self._record_origin(document_id, item)
        self.connection.commit()
        saved = self.get(document_id)
        if saved is None:
            raise RuntimeError(f"failed to save document {document_id}")
        return saved

    def _propose_title_duplicates(
        self,
        document_id: str,
        title: str,
        content_sha256: str,
    ) -> None:
        normalized = " ".join(re.findall(r"[a-z0-9]+", title.lower()))
        if len(normalized) < 12:
            return
        rows = self.connection.execute(
            """
            SELECT d.id, r.title, r.content_sha256
            FROM documents d
            JOIN document_revisions r ON r.revision_id = d.current_revision_id
            WHERE d.id <> ?
            """,
            (document_id,),
        )
        for row in rows:
            if row["content_sha256"] == content_sha256:
                continue
            other = " ".join(re.findall(r"[a-z0-9]+", row["title"].lower()))
            similarity = SequenceMatcher(None, normalized, other).ratio()
            if similarity < 0.9:
                continue
            left, right = sorted((document_id, row["id"]))
            self.connection.execute(
                """
                INSERT OR IGNORE INTO duplicate_candidates
                    (left_document_id, right_document_id, title_similarity, proposed_at)
                VALUES (?, ?, ?, ?)
                """,
                (left, right, similarity, datetime.now(timezone.utc).isoformat()),
            )

    def record_source_health(self, outcome: SourceOutcome) -> None:
        self.connection.execute(
            """
            INSERT INTO source_health_events (
                source_id, checked_at, state, stage, detail, document_count
                , latest_publication_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                outcome.source_id,
                (outcome.checked_at or datetime.now(timezone.utc)).isoformat(),
                outcome.state.value,
                outcome.stage,
                outcome.detail,
                outcome.document_count,
                (
                    outcome.latest_publication_at.isoformat()
                    if outcome.latest_publication_at
                    else None
                ),
            ),
        )
        self.connection.commit()

    def source_health_snapshots(
        self,
        sources: list[SourceDefinition],
        *,
        target: date,
        timezone_name: str,
    ) -> list[SourceHealthSnapshot]:
        failure_states = {
            SourceState.FAILED,
            SourceState.PARTIAL,
            SourceState.EXPECTED_ABSENT,
            SourceState.STALE,
            SourceState.INVALID_DATES,
            SourceState.DEGRADED,
        }
        snapshots: list[SourceHealthSnapshot] = []
        local_zone = ZoneInfo(timezone_name)
        for source in sources:
            rows = list(
                self.connection.execute(
                    """
                    SELECT checked_at, state, latest_publication_at
                    FROM source_health_events
                    WHERE source_id = ?
                    ORDER BY checked_at DESC, id DESC
                    """,
                    (source.id,),
                )
            )
            if not rows:
                snapshots.append(
                    SourceHealthSnapshot(
                        source.id,
                        source.name,
                        SourceHealthStatus.UNKNOWN,
                        None,
                        None,
                        None,
                        None,
                        None,
                        0,
                        source.failure_threshold,
                        "No source-health observation has been recorded.",
                    )
                )
                continue
            states = [SourceState(str(row["state"])) for row in rows]
            checks = [datetime.fromisoformat(str(row["checked_at"])) for row in rows]
            consecutive_failures = 0
            for state in states:
                if state not in failure_states:
                    break
                consecutive_failures += 1
            success_at = next(
                (checked for checked, state in zip(checks, states) if state not in failure_states),
                None,
            )
            failure_at = next(
                (checked for checked, state in zip(checks, states) if state in failure_states),
                None,
            )
            publications = [
                datetime.fromisoformat(str(row["latest_publication_at"]))
                for row in rows
                if row["latest_publication_at"]
            ]
            latest_publication = max(publications) if publications else None
            expected_next = None
            if not source.event_driven and latest_publication is not None:
                latest_day = latest_publication.astimezone(local_zone).date()
                expected_next = latest_day + timedelta(days=source.max_gap_days)
            current = states[0]
            if current in {SourceState.QUIET_EXPECTED, SourceState.NO_ITEMS}:
                status = SourceHealthStatus.QUIET
                detail = "No publication was expected; discovery remained healthy."
            elif current in failure_states:
                status = (
                    SourceHealthStatus.FAILING
                    if consecutive_failures >= source.failure_threshold
                    else SourceHealthStatus.WARNING
                )
                detail = (
                    f"{consecutive_failures} consecutive adverse observation(s); "
                    f"attention threshold is {source.failure_threshold}."
                )
            else:
                status = SourceHealthStatus.HEALTHY
                detail = "Latest source-health observation passed."
            if expected_next and target > expected_next:
                detail += f" Expected publication boundary was {expected_next.isoformat()}."
            snapshots.append(
                SourceHealthSnapshot(
                    source.id,
                    source.name,
                    status,
                    checks[0],
                    success_at,
                    failure_at,
                    latest_publication,
                    expected_next,
                    consecutive_failures,
                    source.failure_threshold,
                    detail,
                )
            )
        return snapshots

    def revision_count(self, document_id: str) -> int:
        row = self.connection.execute(
            "SELECT COUNT(*) AS count FROM document_revisions WHERE document_id = ?",
            (document_id,),
        ).fetchone()
        return int(row["count"])

    def duplicate_candidates(self) -> list[tuple[str, str, float]]:
        return [
            (row["left_document_id"], row["right_document_id"], row["title_similarity"])
            for row in self.connection.execute(
                """
                SELECT left_document_id, right_document_id, title_similarity
                FROM duplicate_candidates ORDER BY left_document_id, right_document_id
                """
            )
        ]

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> DocumentStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
