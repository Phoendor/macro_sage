from __future__ import annotations

import hashlib
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from openai import OpenAI

from macro_sage.feeds import discover
from macro_sage.http import HttpClient
from macro_sage.models import (
    AcquisitionMode,
    CollectionReport,
    Document,
    ItemOutcome,
    ItemState,
    SourceDefinition,
    SourceOutcome,
    SourceState,
)
from macro_sage.pipeline import is_on_date
from macro_sage.run_state import redact_text
from macro_sage.scheduling import AcquisitionWindow
from macro_sage.storage import DocumentStore
from macro_sage.versions import EXTRACTOR_VERSION

MAX_UPLOAD_BYTES = 24 * 1024 * 1024
SEGMENT_SECONDS = 15 * 60
MEDIA_PROCESS_TIMEOUT_SECONDS = 10 * 60


class PodcastBudgetExceeded(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PodcastTranscript:
    text: str
    duration_seconds: int


class PodcastTranscriber:
    def __init__(self, client: OpenAI, http: HttpClient, model: str):
        self.client = client
        self.http = http
        self.model = model

    def _download(self, url: str, destination: Path) -> None:
        response = self.http.get(url, stream=True)
        with destination.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)

    def _segments(
        self,
        audio_path: Path,
        workdir: Path,
        duration_seconds: int,
    ) -> list[Path]:
        if (
            audio_path.stat().st_size <= MAX_UPLOAD_BYTES
            and duration_seconds <= SEGMENT_SECONDS
        ):
            return [audio_path]
        if shutil.which("ffmpeg") is None:
            raise RuntimeError(
                "ffmpeg is required for podcast files larger than 24 MiB "
                "or longer than 15 minutes"
            )
        pattern = workdir / "segment-%03d.mp3"
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(audio_path),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-b:a",
                "48k",
                "-f",
                "segment",
                "-segment_time",
                str(SEGMENT_SECONDS),
                str(pattern),
            ],
            check=True,
            timeout=MEDIA_PROCESS_TIMEOUT_SECONDS,
        )
        segments = sorted(workdir.glob("segment-*.mp3"))
        if not segments:
            raise RuntimeError("ffmpeg did not produce any podcast segments")
        return segments

    def _duration(self, audio_path: Path) -> int:
        if shutil.which("ffprobe") is None:
            raise RuntimeError(
                "ffprobe is required for podcast transcription and duration limits"
            )
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(audio_path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=MEDIA_PROCESS_TIMEOUT_SECONDS,
        )
        return max(1, round(float(result.stdout.strip())))

    def transcribe(self, url: str, *, max_seconds: int) -> PodcastTranscript:
        suffix = Path(urlsplit(url).path).suffix or ".audio"
        with tempfile.TemporaryDirectory(prefix="macro-sage-") as directory:
            workdir = Path(directory)
            audio_path = workdir / f"episode{suffix}"
            self._download(url, audio_path)
            duration_seconds = self._duration(audio_path)
            if duration_seconds > max_seconds:
                raise PodcastBudgetExceeded(
                    f"episode is {duration_seconds / 60:.0f} minutes; "
                    f"{max_seconds / 60:.0f} minutes remain in the run budget"
                )
            transcripts = []
            for segment in self._segments(audio_path, workdir, duration_seconds):
                with segment.open("rb") as handle:
                    result = self.client.audio.transcriptions.create(
                        model=self.model,
                        file=handle,
                    )
                transcripts.append(result if isinstance(result, str) else result.text)
            return PodcastTranscript(
                text="\n\n".join(transcripts),
                duration_seconds=duration_seconds,
            )


def collect_podcasts(
    sources: list[SourceDefinition],
    target: date,
    http: HttpClient,
    store: DocumentStore,
    transcriber: PodcastTranscriber,
    *,
    timezone_name: str,
    max_episodes: int,
    max_minutes: int,
    window: AcquisitionWindow | None = None,
) -> CollectionReport:
    report = CollectionReport()
    remaining_seconds = max_minutes * 60
    remaining_episodes = max_episodes
    for source in sources:
        try:
            items = discover(source, http)
        except Exception as exc:
            outcome = SourceOutcome(
                source.id,
                source.name,
                source.kind,
                SourceState.FAILED,
                stage="feed discovery",
                detail=redact_text(str(exc)),
            )
            report.outcomes.append(outcome)
            store.record_source_health(outcome)
            continue
        matching_all = [
            entry
            for entry in items
            if (
                window.contains(entry.published_at)
                if window
                else is_on_date(entry.published_at, target, timezone_name)
            )
        ]
        matching = []
        counts_by_day: dict[date, int] = {}
        for entry in matching_all:
            publication_day = entry.published_at.astimezone(
                ZoneInfo(timezone_name)
            ).date()
            count = counts_by_day.get(publication_day, 0)
            if count >= source.daily_limit:
                continue
            matching.append(entry)
            counts_by_day[publication_day] = count + 1
        if not matching:
            outcome = SourceOutcome(
                source.id,
                source.name,
                source.kind,
                SourceState.QUIET_EXPECTED,
                detail=f"no publication expected or observed on {target.isoformat()}",
            )
            report.outcomes.append(outcome)
            store.record_source_health(outcome)
            continue

        collected = 0
        failures: list[str] = []
        policy_skips: list[str] = []
        for item in matching:
            cached = store.get_for_item(item)
            if cached:
                report.documents.append(cached)
                report.item_outcomes.append(
                    ItemOutcome(
                        source.id,
                        item.title,
                        item.url,
                        ItemState.CACHED,
                        document_id=cached.id,
                    )
                )
                collected += 1
                continue
            if remaining_episodes <= 0:
                policy_skips.append(f"{item.title}: daily episode limit reached")
                report.item_outcomes.append(
                    ItemOutcome(
                        source.id,
                        item.title,
                        item.url,
                        ItemState.SKIPPED,
                        stage="podcast budget",
                        detail="daily episode limit reached",
                    )
                )
                continue
            if item.duration_seconds and item.duration_seconds > remaining_seconds:
                detail = (
                    "declared duration exceeds the remaining "
                    f"{remaining_seconds / 60:.0f}-minute budget"
                )
                policy_skips.append(f"{item.title}: {detail}")
                report.item_outcomes.append(
                    ItemOutcome(
                        source.id,
                        item.title,
                        item.url,
                        ItemState.SKIPPED,
                        stage="podcast budget",
                        detail=detail,
                    )
                )
                continue
            try:
                remaining_episodes -= 1
                print(
                    f"Transcribing {source.name}: {item.title} "
                    f"({remaining_seconds / 60:.0f} run minutes remain)",
                    flush=True,
                )
                transcript = transcriber.transcribe(
                    item.media_url or "",
                    max_seconds=remaining_seconds,
                )
                content_sha256 = hashlib.sha256(transcript.text.encode()).hexdigest()
                fetched_at = datetime.now(timezone.utc)
                document = Document(
                    id=item.document_id,
                    source_id=source.id,
                    source_name=source.name,
                    publisher=source.publisher,
                    category=source.category,
                    title=item.title,
                    url=item.url,
                    published_at=item.published_at,
                    body=transcript.text,
                    author=item.author,
                    media_type="audio/transcript",
                    original_url=item.original_url or item.url,
                    canonical_url=item.url,
                    resolved_content_url=item.media_url,
                    updated_at=item.updated_at,
                    raw_published=item.raw_published,
                    raw_updated=item.raw_updated,
                    fetched_at=fetched_at,
                    language=source.language,
                    content_sha256=content_sha256,
                    extractor_version=EXTRACTOR_VERSION,
                    acquisition_method=AcquisitionMode.MACHINE_TRANSCRIPT,
                    discovery_source_ids=(source.id,),
                )
                document = store.save(document, item=item)
                report.documents.append(document)
                report.item_outcomes.append(
                    ItemOutcome(
                        source.id,
                        item.title,
                        item.url,
                        ItemState.COLLECTED,
                        document_id=document.id,
                    )
                )
                collected += 1
                remaining_seconds -= transcript.duration_seconds
            except PodcastBudgetExceeded as exc:
                safe_error = redact_text(str(exc))
                policy_skips.append(f"{item.title}: {safe_error}")
                report.item_outcomes.append(
                    ItemOutcome(
                        source.id,
                        item.title,
                        item.url,
                        ItemState.SKIPPED,
                        stage="podcast budget",
                        detail=safe_error,
                    )
                )
            except Exception as exc:
                safe_error = redact_text(str(exc))
                failures.append(f"{item.title}: {safe_error}")
                report.item_outcomes.append(
                    ItemOutcome(
                        source.id,
                        item.title,
                        item.url,
                        ItemState.FAILED,
                        stage="podcast transcription",
                        detail=safe_error,
                    )
                )
        details = [*failures, *policy_skips]
        if failures:
            state = SourceState.PARTIAL if collected else SourceState.FAILED
            stage = "podcast transcription"
        elif policy_skips:
            state = SourceState.PARTIAL if collected else SourceState.SKIPPED
            stage = "podcast budget"
        else:
            state = SourceState.COLLECTED
            stage = None
        outcome = SourceOutcome(
            source.id,
            source.name,
            source.kind,
            state,
            document_count=collected,
            stage=stage,
            detail="; ".join(details) if details else None,
        )
        report.outcomes.append(outcome)
        store.record_source_health(outcome)
    return report
