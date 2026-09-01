import json

import pytest
import requests

from macro_sage import cli
from macro_sage.telegram import (
    TELEGRAM_MAX_DOCUMENT_BYTES,
    TelegramConfig,
    TelegramDelivery,
    TelegramDeliveryError,
    private_technical_caption,
    public_delayed_message,
    public_no_data_message,
    public_report_caption,
    report_document_name,
    send_pdf,
    send_status,
)


class Response:
    def __init__(self, status_code=200, value=None):
        self.status_code = status_code
        self.value = value or {"ok": True, "result": {"message_id": 42}}

    def json(self):
        return self.value


class Client:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def pdf(path):
    path.write_bytes(b"%PDF-1.4\nfixture\n%%EOF\n")
    return path


def test_telegram_configuration_is_disabled_only_when_both_values_absent(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    assert TelegramConfig.from_env() is None

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret")
    with pytest.raises(TelegramDeliveryError, match="TELEGRAM_CHAT_ID"):
        TelegramConfig.from_env()

    monkeypatch.setenv("TELEGRAM_CHAT_ID", "@channel")
    monkeypatch.setenv("TELEGRAM_ADMIN_CHAT_ID", "123456")
    assert TelegramConfig.from_env() == TelegramConfig(
        "secret", "@channel", "123456"
    )

    monkeypatch.setenv("TELEGRAM_ADMIN_CHAT_ID", "@artembaulin")
    with pytest.raises(TelegramDeliveryError, match="must be a numeric"):
        TelegramConfig.from_env()


def test_send_pdf_records_success_without_formatting_mode(tmp_path):
    client = Client([Response()])
    state = tmp_path / "telegram.json"

    result = send_pdf(
        TelegramConfig("secret-token", "@channel"),
        pdf_path=pdf(tmp_path / "brief.pdf"),
        target_date="2026-08-30",
        run_id="run-one",
        caption="Macro Sage *plain* caption",
        state_path=state,
        client=client,
    )

    assert result.status == "sent"
    assert result.message_id == 42
    assert "secret-token" in client.calls[0][0]
    assert "parse_mode" not in client.calls[0][1]["data"]
    assert client.calls[0][1]["files"]["document"][0] == "Macro-Sage-2026-08-30.pdf"
    text = state.read_text(encoding="utf-8")
    assert "secret-token" not in text
    assert json.loads(text)["deliveries"][0]["message_id"] == 42


def test_public_delivery_copy_contains_no_operational_details():
    caption = public_report_caption("2026-08-30")
    no_data = public_no_data_message("2026-08-30")
    delayed = public_delayed_message("2026-08-30")

    assert caption == "Macro Sage — 30 August 2026"
    assert no_data == "Macro Sage — 30 August 2026: no new edition today."
    assert delayed == "Macro Sage — 30 August 2026: today's edition is delayed."
    assert report_document_name("2026-08-30") == "Macro-Sage-2026-08-30.pdf"
    assert private_technical_caption("2026-08-30") == (
        "Macro Sage technical report — 30 August 2026"
    )
    assert report_document_name("2026-08-30", technical=True) == (
        "Macro-Sage-Technical-2026-08-30.pdf"
    )
    combined = " ".join((caption, no_data, delayed)).casefold()
    for internal_term in ("github", "http", "degraded", "health", "source", "failed"):
        assert internal_term not in combined


def test_public_and_admin_destinations_have_independent_idempotency(tmp_path):
    client = Client([Response(), Response(value={"ok": True, "result": {"message_id": 43}})])
    state = tmp_path / "telegram.json"
    report = pdf(tmp_path / "brief.pdf")
    config = TelegramConfig("secret", "@channel")

    public = send_pdf(
        config,
        pdf_path=report,
        target_date="2026-08-30",
        run_id="run-one",
        caption="Public",
        state_path=state,
        destination="public",
        client=client,
    )
    admin = send_pdf(
        TelegramConfig("secret", "123456"),
        pdf_path=report,
        target_date="2026-08-30",
        run_id="run-one",
        caption="Admin",
        state_path=state,
        destination="admin",
        document_name="Macro-Sage-Technical-2026-08-30.pdf",
        client=client,
    )

    assert public == TelegramDelivery("sent", public.idempotency_key, public.pdf_sha256, 42)
    assert admin.message_id == 43
    assert len(client.calls) == 2
    saved = json.loads(state.read_text(encoding="utf-8"))["deliveries"]
    assert {item["destination"] for item in saved} == {"public", "admin"}


def test_run_delivery_routes_content_publicly_and_technical_report_privately(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "@channel")
    monkeypatch.setenv("TELEGRAM_ADMIN_CHAT_ID", "123456")
    public_pdf = tmp_path / "report.pdf"
    technical_pdf = tmp_path / "technical-report.pdf"
    run_record = tmp_path / "run.json"
    run_record.write_text(
        json.dumps(
            {
                "run_id": "run-one",
                "target_date": "2026-08-30",
                "content_result": "report",
                "report_pdf": str(public_pdf),
                "technical_report_pdf": str(technical_pdf),
            }
        ),
        encoding="utf-8",
    )
    calls = []

    def fake_send(config, **kwargs):
        calls.append((config, kwargs))
        message_id = 42 if kwargs.get("destination", "public") == "public" else 43
        return TelegramDelivery(
            "sent",
            f"key-{message_id}",
            "digest",
            message_id,
        )

    monkeypatch.setattr(cli, "send_pdf", fake_send)

    result = cli._deliver_run_record(
        run_record,
        state_path=tmp_path / "delivery.json",
        force=False,
        notify_failure=False,
    )

    assert result == 0
    assert calls[0][0].chat_id == "@channel"
    assert calls[0][1]["pdf_path"] == public_pdf
    assert calls[1][0].chat_id == "123456"
    assert calls[1][1]["pdf_path"] == technical_pdf
    assert calls[1][1]["document_name"] == "Macro-Sage-Technical-2026-08-30.pdf"
    delivery = json.loads(run_record.read_text(encoding="utf-8"))["telegram_delivery"]
    assert delivery["public"]["message_id"] == 42
    assert delivery["admin"]["message_id"] == 43


def test_same_date_and_pdf_is_suppressed_across_different_run_ids(tmp_path):
    client = Client([Response()])
    state = tmp_path / "telegram.json"
    report = pdf(tmp_path / "brief.pdf")
    config = TelegramConfig("secret", "chat")

    send_pdf(
        config,
        pdf_path=report,
        target_date="2026-08-30",
        run_id="run-one",
        caption="First",
        state_path=state,
        client=client,
    )
    duplicate = send_pdf(
        config,
        pdf_path=report,
        target_date="2026-08-30",
        run_id="run-two",
        caption="Retry",
        state_path=state,
        client=client,
    )

    assert duplicate.status == "duplicate_suppressed"
    assert len(client.calls) == 1


def test_same_date_and_status_is_suppressed_across_different_run_ids(tmp_path):
    client = Client([Response()])
    state = tmp_path / "telegram.json"
    config = TelegramConfig("secret", "chat")

    send_status(
        config,
        target_date="2026-08-30",
        run_id="run-one",
        text="No publications today.",
        state_path=state,
        status_kind="no_data",
        client=client,
    )
    duplicate = send_status(
        config,
        target_date="2026-08-30",
        run_id="run-two",
        text="No publications today. A different rerun link follows.",
        state_path=state,
        status_kind="no_data",
        client=client,
    )

    assert duplicate.status == "duplicate_suppressed"
    assert len(client.calls) == 1


def test_force_resend_bypasses_duplicate_suppression(tmp_path):
    client = Client([Response(), Response(value={"ok": True, "result": {"message_id": 43}})])
    state = tmp_path / "telegram.json"
    report = pdf(tmp_path / "brief.pdf")
    config = TelegramConfig("secret", "chat")

    send_pdf(
        config,
        pdf_path=report,
        target_date="2026-08-30",
        run_id="run-one",
        caption="First",
        state_path=state,
        client=client,
    )
    resent = send_pdf(
        config,
        pdf_path=report,
        target_date="2026-08-30",
        run_id="run-one",
        caption="Intentional resend",
        state_path=state,
        client=client,
        force=True,
    )

    assert resent.status == "sent"
    assert resent.message_id == 43
    assert len(client.calls) == 2


def test_permission_error_is_sanitized(tmp_path):
    client = Client(
        [
            Response(
                403,
                {
                    "ok": False,
                    "description": "bot secret-token is not an administrator",
                },
            )
        ]
    )

    with pytest.raises(TelegramDeliveryError, match=r"\[REDACTED\]") as error:
        send_pdf(
            TelegramConfig("secret-token", "chat"),
            pdf_path=pdf(tmp_path / "brief.pdf"),
            target_date="2026-08-30",
            run_id="run-one",
            caption="Caption",
            state_path=tmp_path / "state.json",
            client=client,
        )

    assert "secret-token" not in str(error.value)


def test_explicit_rate_limit_is_retried_once(tmp_path):
    client = Client(
        [
            Response(
                429,
                {"ok": False, "parameters": {"retry_after": 3}, "description": "wait"},
            ),
            Response(),
        ]
    )
    waits = []

    result = send_pdf(
        TelegramConfig("secret", "chat"),
        pdf_path=pdf(tmp_path / "brief.pdf"),
        target_date="2026-08-30",
        run_id="run-one",
        caption="Caption",
        state_path=tmp_path / "state.json",
        client=client,
        sleep=waits.append,
    )

    assert result.status == "sent"
    assert waits == [3]
    assert len(client.calls) == 2


def test_ambiguous_transport_error_is_not_retried_or_leaked(tmp_path):
    client = Client([requests.Timeout("https://api.telegram.org/botsecret/sendDocument")])

    with pytest.raises(TelegramDeliveryError, match="automatic retry disabled") as error:
        send_pdf(
            TelegramConfig("secret", "chat"),
            pdf_path=pdf(tmp_path / "brief.pdf"),
            target_date="2026-08-30",
            run_id="run-one",
            caption="Caption",
            state_path=tmp_path / "state.json",
            client=client,
        )

    assert "secret" not in str(error.value)
    assert len(client.calls) == 1


def test_oversized_pdf_is_rejected_before_network(tmp_path):
    report = tmp_path / "large.pdf"
    with report.open("wb") as stream:
        stream.write(b"%PDF-")
        stream.seek(TELEGRAM_MAX_DOCUMENT_BYTES)
        stream.write(b"x")
    client = Client([])

    with pytest.raises(TelegramDeliveryError, match="limit"):
        send_pdf(
            TelegramConfig("secret", "chat"),
            pdf_path=report,
            target_date="2026-08-30",
            run_id="run-one",
            caption="Caption",
            state_path=tmp_path / "state.json",
            client=client,
        )

    assert client.calls == []
