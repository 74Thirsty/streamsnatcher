"""Verbatim integration point for yt_dlp downloads."""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable, List, Optional

from yt_dlp import YoutubeDL

ProgressHook = Callable[[dict], None]


def _default_progress_hook(status: dict) -> None:
    """Print progress updates using the canonical yt_dlp hook format."""
    filename = status.get("filename")
    state = status.get("status")
    if filename and state:
        print(f"\u23fa\ufe0f {filename} ({state})")


def _build_progress_hooks(hooks: Optional[Iterable[ProgressHook]]) -> List[ProgressHook]:
    if hooks is None:
        return [_default_progress_hook]
    return [*hooks]


class _LoggerProxy:
    """Thin adapter that forwards yt_dlp log events to a callable."""

    def __init__(self, handler: Callable[[str], None]) -> None:
        self._handler = handler

    def debug(self, message: str) -> None:
        self._handler(message)

    def info(self, message: str) -> None:
        self._handler(message)

    def warning(self, message: str) -> None:
        self._handler(message)


def download_media(
    url: str,
    output_dir: str,
    *,
    log_handler: Optional[Callable[[str], None]] = None,
    progress_hooks: Optional[Iterable[ProgressHook]] = None,
    cookiefile: Optional[str] = None,
) -> None:
    """Download media using yt_dlp exactly as mandated by AES Directive 7."""

    destination = Path(output_dir).expanduser()
    destination.mkdir(parents=True, exist_ok=True)

    params = {
        "outtmpl": f"{destination}/%(title)s.%(ext)s",
        "quiet": False,
        "noprogress": False,
        "progress_hooks": _build_progress_hooks(progress_hooks),
        "logger": _LoggerProxy(log_handler) if log_handler is not None else None,
    }

    if cookiefile is not None:
        params["cookiefile"] = cookiefile

    with YoutubeDL(params) as ydl:
        ydl.download([url])


def prompt_and_download() -> None:
    """Simple CLI helper that mirrors the reference integration script."""

    url = input("Enter media URL: ").strip()
    if not url:
        raise SystemExit("A URL is required to start a download.")

    output_dir = input("Enter destination directory (default: ~/Downloads): ").strip()
    if not output_dir:
        output_dir = str(Path.home() / "Downloads")

    download_media(url, output_dir)


if __name__ == "__main__":  # pragma: no cover - manual invocation entry
    prompt_and_download()
