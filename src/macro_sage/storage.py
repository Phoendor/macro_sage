from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from macro_sage.models import Document


class DocumentStore:
    def __init__(self, path: str | Path):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                source_name TEXT NOT NULL,
                publisher TEXT NOT NULL,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                published_at TEXT,
                body TEXT NOT NULL,
                author TEXT,
                media_type TEXT NOT NULL,
                fetched_at TEXT NOT NULL
            )
            """
        )
        self.connection.commit()

    def get(self, document_id: str) -> Document | None:
        row = self.connection.execute(
            "SELECT * FROM documents WHERE id = ?", (document_id,)
        ).fetchone()
        if row is None:
            return None
        return Document(
            id=row["id"],
            source_id=row["source_id"],
            source_name=row["source_name"],
            publisher=row["publisher"],
            category=row["category"],
            title=row["title"],
            url=row["url"],
            published_at=datetime.fromisoformat(row["published_at"])
            if row["published_at"]
            else None,
            body=row["body"],
            author=row["author"],
            media_type=row["media_type"],
        )

    def save(self, document: Document) -> None:
        self.connection.execute(
            """
            INSERT OR REPLACE INTO documents (
                id, source_id, source_name, publisher, category, title, url,
                published_at, body, author, media_type, fetched_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document.id,
                document.source_id,
                document.source_name,
                document.publisher,
                document.category,
                document.title,
                document.url,
                document.published_at.isoformat() if document.published_at else None,
                document.body,
                document.author,
                document.media_type,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> DocumentStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
