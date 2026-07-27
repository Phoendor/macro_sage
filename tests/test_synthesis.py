from datetime import date, datetime, timezone

import pytest

from macro_sage.models import Bias, DailyBrief, Document
from macro_sage.settings import Settings
from macro_sage.synthesis import _assert_known_sources, prepare_corpus, synthesize


def document(
    identifier: str,
    body: str = "body",
    *,
    publisher: str = "Publisher",
) -> Document:
    return Document(
        id=identifier,
        source_id="source",
        source_name="Source",
        publisher=publisher,
        category="research",
        title=identifier,
        url=f"https://example.com/{identifier}",
        published_at=datetime(2026, 7, 27, tzinfo=timezone.utc),
        body=body,
    )


def test_prepare_corpus_uses_one_bounded_payload():
    settings = Settings(max_articles=1, max_article_chars=20, max_corpus_chars=500)

    prepared = prepare_corpus([document("one", "x" * 50), document("two")], settings)

    assert [item.id for item in prepared.included] == ["one"]
    assert prepared.omitted_ids == ["two"]
    assert "x" * 20 in prepared.text
    assert "x" * 21 not in prepared.text


def test_prepare_corpus_balances_publishers_before_taking_second_item():
    settings = Settings(max_articles=2, max_article_chars=20, max_corpus_chars=500)
    documents = [
        document("a-new", publisher="A"),
        document("a-old", publisher="A"),
        document("b-new", publisher="B"),
    ]

    prepared = prepare_corpus(documents, settings)

    assert [item.id for item in prepared.included] == ["a-new", "b-new"]
    assert prepared.omitted_ids == ["a-old"]


def test_unknown_model_citation_is_rejected():
    brief = DailyBrief(
        as_of_date="2026-07-27",
        executive_summary=["Summary"],
        macro_themes=[
            {
                "theme": "Inflation",
                "market_implication": "Rates stay volatile.",
                "source_ids": ["invented"],
            }
        ],
        asset_views=[
            {
                "asset": "EUR/USD",
                "bias": Bias.NEUTRAL,
                "horizon": "one week",
                "confidence": 3,
                "drivers": ["Policy"],
                "risks": ["Data"],
                "source_ids": ["known"],
            }
        ],
        top_risks=["Inflation"],
        source_ids_used=["known"],
    )

    with pytest.raises(ValueError, match="unknown source"):
        _assert_known_sources(brief, {"known"})


def test_synthesize_uses_structured_responses_api():
    brief = DailyBrief(
        as_of_date="2026-07-27",
        executive_summary=["Summary"],
        macro_themes=[],
        asset_views=[],
        top_risks=[],
        source_ids_used=["known"],
    )

    class Usage:
        input_tokens = 100
        output_tokens = 20

    class Response:
        output_parsed = brief
        usage = Usage()

    class Responses:
        def __init__(self):
            self.arguments = None

        def parse(self, **kwargs):
            self.arguments = kwargs
            return Response()

    class Client:
        def __init__(self):
            self.responses = Responses()

    client = Client()
    result = synthesize(
        [document("known")],
        date(2026, 7, 27),
        Settings(),
        client=client,
    )

    assert client.responses.arguments["model"] == "gpt-5.4-mini"
    assert client.responses.arguments["text_format"] is DailyBrief
    assert client.responses.arguments["store"] is False
    assert result.input_tokens == 100
