from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

import requests

from macro_sage.files import write_json_atomic
from macro_sage.run_state import redact_text

TELEGRAM_MAX_DOCUMENT_BYTES = 50 * 1024 * 1024
TELEGRAM_MAX_CAPTION_CHARS = 1024


class HttpPoster(Protocol):
    def post(self, url: str, **kwargs: object) -> Any: ...


class TelegramDeliveryError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class TelegramConfig:
    bot_token: str
    chat_id: str

    @classmethod
    def from_env(cls) -> TelegramConfig | None:
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        if not token and not chat_id:
            return None
        if not token or not chat_id:
            missing = "TELEGRAM_BOT_TOKEN" if not token else "TELEGRAM_CHAT_ID"
            raise TelegramDeliveryError(f"Incomplete Telegram configuration: missing {missing}")
        return cls(token, chat_id)


@dataclass(frozen=True, slots=True)
class TelegramDelivery:
    status: str
    idempotency_key: str
    pdf_sha256: str | None = None
    message_id: int | None = None
    detail: str | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": 1, "deliveries": []}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise TelegramDeliveryError(f"Unsupported Telegram delivery state: {path}")
    if not isinstance(value.get("deliveries"), list):
        raise TelegramDeliveryError(f"Invalid Telegram delivery state: {path}")
    return value


def _save_delivery(path: Path, delivery: dict[str, object]) -> None:
    state = _load_state(path)
    deliveries = [
        item
        for item in state["deliveries"]
        if isinstance(item, dict)
        and item.get("idempotency_key") != delivery.get("idempotency_key")
    ]
    deliveries.append(delivery)
    write_json_atomic(
        path,
        {"schema_version": 1, "deliveries": deliveries[-500:]},
    )


def _response_value(response: Any, token: str) -> dict[str, Any]:
    try:
        value = response.json()
    except (ValueError, TypeError) as exc:
        raise TelegramDeliveryError(
            f"Telegram returned HTTP {getattr(response, 'status_code', 'unknown')} "
            "with a non-JSON response"
        ) from exc
    if not isinstance(value, dict):
        raise TelegramDeliveryError("Telegram returned an invalid response object")
    if not value.get("ok"):
        description = redact_text(str(value.get("description", "request rejected"))).replace(
            token, "[REDACTED]"
        )
        raise TelegramDeliveryError(
            f"Telegram returned HTTP {getattr(response, 'status_code', 'unknown')}: "
            f"{description}"
        )
    return value


def _is_duplicate(
    state: dict[str, Any],
    *,
    key: str,
    target_date: str,
    content_sha256: str | None,
    delivery_kind: str,
) -> dict[str, Any] | None:
    for item in state.get("deliveries", []):
        if not isinstance(item, dict) or item.get("status") != "sent":
            continue
        if item.get("idempotency_key") == key:
            return item
        if (
            delivery_kind != "pdf"
            and item.get("target_date") == target_date
            and item.get("delivery_kind") == delivery_kind
        ):
            return item
        if (
            content_sha256
            and item.get("target_date") == target_date
            and (item.get("content_sha256") or item.get("pdf_sha256"))
            == content_sha256
        ):
            return item
    return None


def _post(
    config: TelegramConfig,
    method: str,
    *,
    data: dict[str, object],
    files: dict[str, object] | None,
    client: HttpPoster,
    sleep: Any,
) -> dict[str, Any]:
    url = f"https://api.telegram.org/bot{config.bot_token}/{method}"
    for attempt in range(2):
        try:
            response = client.post(
                url,
                data=data,
                files=files,
                timeout=(10, 60),
            )
        except requests.RequestException as exc:
            # A transport error is ambiguous: Telegram may have accepted the post.
            # Retrying could duplicate a report, so fail visibly and require force-resend.
            raise TelegramDeliveryError(
                f"Telegram transport failed with {type(exc).__name__}; automatic retry disabled"
            ) from exc
        if getattr(response, "status_code", 0) != 429 or attempt == 1:
            return _response_value(response, config.bot_token)
        try:
            retry_after = int(response.json().get("parameters", {}).get("retry_after", 1))
        except (AttributeError, TypeError, ValueError):
            retry_after = 1
        sleep(max(0, min(retry_after, 10)))
    raise AssertionError("unreachable")


def send_pdf(
    config: TelegramConfig,
    *,
    pdf_path: Path,
    target_date: str,
    run_id: str,
    caption: str,
    state_path: Path,
    force: bool = False,
    client: HttpPoster | None = None,
    sleep: Any = time.sleep,
) -> TelegramDelivery:
    if pdf_path.suffix.casefold() != ".pdf" or not pdf_path.is_file():
        raise TelegramDeliveryError(f"Telegram document is not a PDF file: {pdf_path}")
    size = pdf_path.stat().st_size
    if size > TELEGRAM_MAX_DOCUMENT_BYTES:
        raise TelegramDeliveryError(
            f"PDF is {size} bytes; Telegram Bot API limit is {TELEGRAM_MAX_DOCUMENT_BYTES}"
        )
    with pdf_path.open("rb") as stream:
        if stream.read(5) != b"%PDF-":
            raise TelegramDeliveryError(f"File does not have a PDF signature: {pdf_path}")
        stream.seek(0)
        digest = hashlib.sha256(stream.read()).hexdigest()
    key = f"{run_id}:{digest}"
    state = _load_state(state_path)
    duplicate = _is_duplicate(
        state,
        key=key,
        target_date=target_date,
        content_sha256=digest,
        delivery_kind="pdf",
    )
    if duplicate and not force:
        return TelegramDelivery(
            "duplicate_suppressed",
            key,
            digest,
            int(duplicate["message_id"]) if duplicate.get("message_id") else None,
            "Matching run or same-date PDF was already delivered.",
        )
    safe_caption = " ".join(caption.split())[:TELEGRAM_MAX_CAPTION_CHARS]
    poster = client or requests.Session()
    with pdf_path.open("rb") as stream:
        value = _post(
            config,
            "sendDocument",
            data={"chat_id": config.chat_id, "caption": safe_caption},
            files={"document": (pdf_path.name, stream, "application/pdf")},
            client=poster,
            sleep=sleep,
        )
    result = value.get("result", {})
    message_id = int(result["message_id"])
    record = {
        "status": "sent",
        "idempotency_key": key,
        "target_date": target_date,
        "run_id": run_id,
        "delivery_kind": "pdf",
        "content_sha256": digest,
        "pdf_sha256": digest,
        "message_id": message_id,
    }
    _save_delivery(state_path, record)
    return TelegramDelivery("sent", key, digest, message_id)


def send_status(
    config: TelegramConfig,
    *,
    target_date: str,
    run_id: str,
    text: str,
    state_path: Path,
    status_kind: str = "status",
    force: bool = False,
    client: HttpPoster | None = None,
    sleep: Any = time.sleep,
) -> TelegramDelivery:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    key = f"{run_id}:{status_kind}:{digest}"
    state = _load_state(state_path)
    duplicate = _is_duplicate(
        state,
        key=key,
        target_date=target_date,
        content_sha256=digest,
        delivery_kind=status_kind,
    )
    if duplicate and not force:
        return TelegramDelivery(
            "duplicate_suppressed",
            key,
            message_id=(
                int(duplicate["message_id"]) if duplicate.get("message_id") else None
            ),
            detail="Matching status was already delivered.",
        )
    safe_text = " ".join(text.split())[:4096]
    value = _post(
        config,
        "sendMessage",
        data={"chat_id": config.chat_id, "text": safe_text},
        files=None,
        client=client or requests.Session(),
        sleep=sleep,
    )
    message_id = int(value.get("result", {})["message_id"])
    _save_delivery(
        state_path,
        {
            "status": "sent",
            "idempotency_key": key,
            "target_date": target_date,
            "run_id": run_id,
            "delivery_kind": status_kind,
            "content_sha256": digest,
            "message_id": message_id,
        },
    )
    return TelegramDelivery("sent", key, message_id=message_id)
