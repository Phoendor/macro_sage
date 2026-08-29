from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from macro_sage.settings import Settings


class HttpClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.session = requests.Session()
        retry = Retry(
            total=3,
            connect=3,
            read=2,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self.session.headers.update({"User-Agent": settings.user_agent})

    def get(
        self,
        url: str,
        *,
        stream: bool = False,
        headers: dict[str, str] | None = None,
    ) -> requests.Response:
        response = self.session.get(
            url,
            timeout=(10, self.settings.request_timeout_seconds),
            stream=stream,
            headers=headers,
        )
        response.raise_for_status()
        return response

    def probe(self, url: str) -> requests.Response:
        response = self.session.head(
            url,
            timeout=(10, self.settings.request_timeout_seconds),
            allow_redirects=True,
        )
        if response.status_code in {403, 405}:
            response.close()
            response = self.session.get(
                url,
                timeout=(10, self.settings.request_timeout_seconds),
                headers={"Range": "bytes=0-0"},
                stream=True,
            )
        response.raise_for_status()
        return response

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> HttpClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
