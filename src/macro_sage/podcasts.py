from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from openai import OpenAI

from macro_sage.feeds import discover
from macro_sage.http import HttpClient
from macro_sage.models import (
    CollectionReport,
    Document,
    SourceDefinition,
    SourceOutcome,
    SourceState,
)
from macro_sage.pipeline import is_on_date
from macro_sage.storage import DocumentStore

MAX_UPLOAD_BYTES = 24 * 1024 * 1024


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

    def _segments(self, audio_path: Path, workdir: Path) -> list[Path]:
        if audio_path.stat().st_size <= MAX_UPLOAD_BYTES:
            return [audio_path]
        if shutil.which("ffmpeg") is None:
            raise RuntimeError("ffmpeg is required for podcast files larger than 24 MiB")
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
                "1800",
                str(pattern),
            ],
            check=True,
        )
        return sorted(workdir.glob("segment-*.mp3"))

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
            for segment in self._segments(audio_path, workdir):
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
) -> CollectionReport:
    report = CollectionReport()
    remaining_seconds = max_minutes * 60
    remaining_episodes = max_episodes
    for source in sources:
        try:
            items = discover(source, http)
        except Exception as exc:
            report.outcomes.append(
                SourceOutcome(
                    source.id,
                    source.name,
                    source.kind,
                    SourceState.FAILED,
                    stage="feed discovery",
                    detail=str(exc),
                )
            )
            continue
        matching = [
            entry
            for entry in items
            if is_on_date(entry.published_at, target, timezone_name)
        ]
        if not matching:
            report.outcomes.append(
                SourceOutcome(
                    source.id,
                    source.name,
                    source.kind,
                    SourceState.NO_ITEMS,
                    detail=f"no items on {target.isoformat()}",
                )
            )
            continue

        collected = 0
        failures: list[str] = []
        policy_skips: list[str] = []
        for item in matching:
            cached = store.get(item.document_id)
            if cached:
                report.documents.append(cached)
                collected += 1
                continue
            if remaining_episodes <= 0:
                policy_skips.append(f"{item.title}: daily episode limit reached")
                continue
            if item.duration_seconds and item.duration_seconds > remaining_seconds:
                policy_skips.append(
                    f"{item.title}: declared duration exceeds the remaining "
                    f"{remaining_seconds / 60:.0f}-minute budget"
                )
                continue
            try:
                transcript = transcriber.transcribe(
                    item.media_url or "",
                    max_seconds=remaining_seconds,
                )
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
                )
                store.save(document)
                report.documents.append(document)
                collected += 1
                remaining_episodes -= 1
                remaining_seconds -= transcript.duration_seconds
            except PodcastBudgetExceeded as exc:
                policy_skips.append(f"{item.title}: {exc}")
            except Exception as exc:
                failures.append(f"{item.title}: {exc}")
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
        report.outcomes.append(
            SourceOutcome(
                source.id,
                source.name,
                source.kind,
                state,
                document_count=collected,
                stage=stage,
                detail="; ".join(details) if details else None,
            )
        )
    return report
