from __future__ import annotations

import shutil
import subprocess
import tempfile
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from openai import OpenAI

from macro_sage.feeds import discover
from macro_sage.http import HttpClient
from macro_sage.models import CollectionReport, Document, SourceDefinition
from macro_sage.pipeline import is_on_date
from macro_sage.storage import DocumentStore

MAX_UPLOAD_BYTES = 24 * 1024 * 1024


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

    def transcribe(self, url: str) -> str:
        suffix = Path(urlsplit(url).path).suffix or ".audio"
        with tempfile.TemporaryDirectory(prefix="macro-sage-") as directory:
            workdir = Path(directory)
            audio_path = workdir / f"episode{suffix}"
            self._download(url, audio_path)
            transcripts = []
            for segment in self._segments(audio_path, workdir):
                with segment.open("rb") as handle:
                    result = self.client.audio.transcriptions.create(
                        model=self.model,
                        file=handle,
                    )
                transcripts.append(result if isinstance(result, str) else result.text)
            return "\n\n".join(transcripts)


def collect_podcasts(
    sources: list[SourceDefinition],
    target: date,
    http: HttpClient,
    store: DocumentStore,
    transcriber: PodcastTranscriber,
    *,
    timezone_name: str,
) -> CollectionReport:
    report = CollectionReport()
    for source in sources:
        try:
            items = discover(source, http)
        except Exception as exc:
            report.errors.append(f"{source.name}: feed failed: {exc}")
            continue
        for item in [
            entry
            for entry in items
            if is_on_date(entry.published_at, target, timezone_name)
        ]:
            cached = store.get(item.document_id)
            if cached:
                report.documents.append(cached)
                continue
            try:
                body = transcriber.transcribe(item.media_url or "")
                document = Document(
                    id=item.document_id,
                    source_id=source.id,
                    source_name=source.name,
                    publisher=source.publisher,
                    category=source.category,
                    title=item.title,
                    url=item.url,
                    published_at=item.published_at,
                    body=body,
                    author=item.author,
                    media_type="audio/transcript",
                )
                store.save(document)
                report.documents.append(document)
            except Exception as exc:
                report.errors.append(f"{source.name}: {item.title}: {exc}")
    return report
