from datetime import datetime, timezone

from macro_sage.models import Document
from macro_sage.storage import DocumentStore


def test_document_round_trip():
    document = Document(
        id="source:abc",
        source_id="source",
        source_name="Source",
        publisher="Publisher",
        category="research",
        title="Title",
        url="https://example.com/title",
        published_at=datetime(2026, 7, 27, tzinfo=timezone.utc),
        body="Body",
    )

    with DocumentStore(":memory:") as store:
        store.save(document)
        loaded = store.get(document.id)

    assert loaded == document
