from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TIMEOUT_SECONDS = 120


def _timeout_seconds() -> int:
    raw = os.getenv("MACRO_SAGE_CHECK_TIMEOUT_SECONDS", "").strip()
    if not raw:
        return DEFAULT_TIMEOUT_SECONDS
    value = int(raw)
    if value < 1:
        raise ValueError("MACRO_SAGE_CHECK_TIMEOUT_SECONDS must be positive")
    return value


def _verify_import() -> None:
    import macro_sage

    actual = Path(macro_sage.__file__).resolve()
    expected = (ROOT / "src" / "macro_sage").resolve()
    if expected not in actual.parents and actual.parent != expected:
        raise RuntimeError(
            f"macro_sage imports from {actual}, expected this checkout at {expected}"
        )
    print(f"Environment imports {actual}", flush=True)


def _run(label: str, arguments: list[str], timeout: int) -> None:
    print(f"\n[{label}] {' '.join(arguments)}", flush=True)
    started = time.monotonic()
    try:
        subprocess.run(arguments, cwd=ROOT, check=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise SystemExit(f"{label} exceeded the {timeout}s safety timeout") from exc
    elapsed = time.monotonic() - started
    print(f"[{label}] completed in {elapsed:.2f}s", flush=True)


def main() -> None:
    timeout = _timeout_seconds()
    _verify_import()
    commands = [
        (
            "compile",
            [sys.executable, "-m", "compileall", "-q", "src", "tests", "scripts"],
        ),
        ("lint", [sys.executable, "-m", "ruff", "check", "."]),
        ("tests", [sys.executable, "-m", "pytest", "-q"]),
    ]
    for label, arguments in commands:
        _run(label, arguments, timeout)


if __name__ == "__main__":
    main()
