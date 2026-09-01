from __future__ import annotations

import os
import subprocess
import sys
import time
from importlib.metadata import PackageNotFoundError, version
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
    try:
        import macro_sage
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "macro_sage is not importable from the active environment; reinstall "
            "the editable package"
        ) from exc

    actual = Path(macro_sage.__file__).resolve()
    expected = (ROOT / "src" / "macro_sage").resolve()
    if expected not in actual.parents and actual.parent != expected:
        raise RuntimeError(
            f"macro_sage imports from {actual}, expected this checkout at {expected}"
        )
    try:
        installed_version = version("macro-sage")
    except PackageNotFoundError as exc:
        raise RuntimeError(
            "macro-sage is not installed; run `python -m pip install --no-deps -e .`"
        ) from exc
    if installed_version != macro_sage.__version__:
        raise RuntimeError(
            f"Installed macro-sage metadata is {installed_version}, but this checkout is "
            f"{macro_sage.__version__}; reinstall the editable package"
        )
    print(f"Environment imports {actual}", flush=True)


def _run(label: str, arguments: list[str], timeout: int) -> None:
    print(f"\n[{label}] {' '.join(arguments)}", flush=True)
    started = time.monotonic()
    environment = os.environ.copy()
    source_root = str(ROOT / "src")
    current_pythonpath = environment.get("PYTHONPATH", "").strip()
    environment["PYTHONPATH"] = (
        f"{source_root}{os.pathsep}{current_pythonpath}"
        if current_pythonpath
        else source_root
    )
    try:
        subprocess.run(
            arguments,
            cwd=ROOT,
            check=True,
            timeout=timeout,
            env=environment,
        )
    except subprocess.TimeoutExpired as exc:
        raise SystemExit(f"{label} exceeded the {timeout}s safety timeout") from exc
    elapsed = time.monotonic() - started
    print(f"[{label}] completed in {elapsed:.2f}s", flush=True)


def main() -> None:
    timeout = _timeout_seconds()
    _verify_import()
    commands = [
        (
            "catalog",
            [sys.executable, "scripts/generate_source_catalog.py", "--check"],
        ),
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
