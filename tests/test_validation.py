import json

import pytest

from macro_sage.models import Participation, SourceDefinition, SourceKind
from macro_sage.validation import (
    _contract_sample,
    apply_manual_reviews,
    validate_source,
)


class Response:
    def __init__(self, content, *, url, content_type, status=200):
        self.content = content
        self.text = content.decode() if isinstance(content, bytes) else content
        self.url = url
        self.status_code = status
        self.headers = {"content-type": content_type, "content-length": str(len(content))}
        self.history = []

    def close(self):
        return None


class ArticleClient:
    def get(self, url, **_kwargs):
        if url.endswith("feed.xml"):
            return Response(
                b"""<rss version="2.0"><channel><title>Feed</title><item>
                <title>Rates and growth</title><link>https://example.com/article</link>
                <pubDate>Mon, 27 Jul 2026 08:00:00 GMT</pubDate>
                </item></channel></rss>""",
                url=url,
                content_type="application/rss+xml",
            )
        body = "Rates and growth. " + "The economy and inflation are changing. " * 30
        return Response(
            f"<html><head><title>Rates and growth</title></head><body><article>{body}</article></body></html>".encode(),
            url=url,
            content_type="text/html",
        )


class PodcastClient(ArticleClient):
    def get(self, url, **_kwargs):
        return Response(
            b"""<rss version="2.0"><channel><title>Feed</title><item>
            <title>Episode</title><link>https://example.com/episode</link>
            <pubDate>Mon, 27 Jul 2026 08:00:00 GMT</pubDate>
            <enclosure url="https://example.com/audio.mp3" type="audio/mpeg"/>
            </item></channel></rss>""",
            url=url,
            content_type="application/rss+xml",
        )

    def probe(self, url):
        return Response(b"0", url=url, content_type="text/plain")


def test_article_validation_record_has_auditable_contract_fields():
    source = SourceDefinition(
        "source", "Source", "Publisher", "https://example.com/feed.xml", "research"
    )

    result = validate_source(source, ArticleClient())

    assert result["status"] == "passed"
    assert result["http_status"] == 200
    assert result["parsed_entry_count"] == 1
    assert result["newest_entry"]["published_at"]
    assert result["extraction_method"] == "full_html"
    assert result["content_sha256"]
    assert "body" not in result


def test_declared_audio_enclosure_survives_generic_probe_content_type():
    source = SourceDefinition(
        "podcast",
        "Podcast",
        "Publisher",
        "https://example.com/feed.xml",
        "podcast",
        kind=SourceKind.PODCAST,
        participation=Participation.OPTIONAL,
    )

    result = validate_source(source, PodcastClient())

    assert result["status"] == "passed"
    assert result["declared_media_type"] == "audio/mpeg"
    assert result["resolved_content_url"] == "https://example.com/audio.mp3"
    assert "feed declares audio/mpeg" in result["warnings"][0]


def test_generated_contract_is_pending_until_a_bound_manual_decision():
    sample = _contract_sample(
        {
            "source_id": "source",
            "newest_entry": {"title": "Newest"},
            "representative_entry": {"title": "Representative"},
            "warnings": [],
        }
    )

    assert sample["review"]["status"] == "pending_review"
    assert sample["review"]["reviewer"] is None
    assert len(sample["contract_fingerprint"]) == 64


def test_failed_contract_replaces_stale_success_and_remains_reviewable():
    sample = _contract_sample(
        {
            "source_id": "source",
            "status": "failed",
            "failure_stage": "feed_discovery",
            "error": "HTTP 404",
            "warnings": [],
        }
    )

    assert sample["automated_status"] == "failed"
    assert sample["failure_stage"] == "feed_discovery"
    assert sample["representative_entry"] is None
    assert sample["review"]["status"] == "pending_review"


def test_manual_review_requires_exact_contract_fingerprint(tmp_path):
    validation = tmp_path / "validation.json"
    samples = tmp_path / "contracts"
    decisions = tmp_path / "decisions.json"
    samples.mkdir()
    sample = _contract_sample(
        {
            "source_id": "source",
            "newest_entry": {"title": "Newest"},
            "representative_entry": {"title": "Representative"},
            "warnings": [],
        }
    )
    (samples / "source.json").write_text(json.dumps(sample), encoding="utf-8")
    validation.write_text(
        json.dumps(
            {
                "completed_at": "2026-08-29T10:00:00+00:00",
                "transformation_versions": {"git_commit": "abc123"},
                "sources": [{"source_id": "source", "status": "passed"}],
            }
        ),
        encoding="utf-8",
    )
    decision = {
        "review_version": 1,
        "baseline_completed_at": "2026-08-29T10:00:00+00:00",
        "baseline_git_commit": "abc123",
        "reviewer": "A human reviewer",
        "reviewed_at": "2026-08-29T11:00:00+00:00",
        "decisions": [
            {
                "source_id": "source",
                "contract_fingerprint": sample["contract_fingerprint"],
                "status": "approved",
                "notes": "Representative title and extracted content were inspected.",
            }
        ],
    }
    decisions.write_text(json.dumps(decision), encoding="utf-8")

    summary = apply_manual_reviews(
        validation_path=validation,
        samples_dir=samples,
        decisions_path=decisions,
    )

    reviewed = json.loads((samples / "source.json").read_text(encoding="utf-8"))
    assert summary["status"] == "complete"
    assert reviewed["review"]["status"] == "approved"
    decision["decisions"][0]["contract_fingerprint"] = "stale"
    decisions.write_text(json.dumps(decision), encoding="utf-8")
    with pytest.raises(ValueError, match="Stale review decision"):
        apply_manual_reviews(
            validation_path=validation,
            samples_dir=samples,
            decisions_path=decisions,
        )
