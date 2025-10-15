"""Command line interface for StreamSaavy.

This module offers a lightweight alternative to the Tkinter GUI so the
application can run comfortably inside terminal environments such as
Termux on Android.  The CLI mirrors the major options from the desktop
app while keeping sensible defaults.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, Optional, Sequence

from .downloader import DownloadMode, DownloadRequest, StreamSaavyDownloader


def _iter_modes() -> Iterable[str]:
    for mode in DownloadMode:
        yield mode.value


def _build_request(args: argparse.Namespace) -> DownloadRequest:
    url = (args.url or "").strip()
    if not url:
        raise ValueError("A YouTube or supported URL is required to start the download.")

    output_dir = Path(args.output).expanduser()

    cookies_path: Optional[Path] = None
    if args.cookies is not None:
        cookies_path = Path(args.cookies).expanduser()
        if not cookies_path.exists() or not cookies_path.is_file():
            raise ValueError(f"Cookies file not found: {cookies_path}")

    mode = DownloadMode(args.mode)
    return DownloadRequest(
        url=url,
        save_path=output_dir,
        mode=mode,
        audio_bitrate=args.audio_bitrate,
        video_resolution=args.video_resolution,
        embed_thumbnail=args.embed_thumbnail,
        embed_metadata=args.embed_metadata,
        cookies_path=cookies_path,
    )


def run_cli(argv: Optional[Sequence[str]] = None) -> int:
    """Execute the CLI workflow. Returns an exit status code."""

    parser = argparse.ArgumentParser(
        prog="streamsaavy_app --ui cli",
        description="Terminal interface for StreamSaavy (yt-dlp front-end).",
    )
    parser.add_argument("url", nargs="?", help="Video or playlist URL to download")
    parser.add_argument(
        "--mode",
        choices=list(_iter_modes()),
        default=DownloadMode.VIDEO.value,
        help="Choose between mp4 video or mp3 audio exports.",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=str(Path.home() / "Downloads"),
        help="Destination directory for downloaded files (default: ~/Downloads)",
    )
    parser.add_argument(
        "--audio-bitrate",
        default="256k",
        help="Audio bitrate when using audio/compatibility modes (default: 256k)",
    )
    parser.add_argument(
        "--video-resolution",
        default="1080",
        help="Maximum video resolution when using video modes (default: 1080)",
    )
    parser.add_argument(
        "--no-embed-thumbnail",
        dest="embed_thumbnail",
        action="store_false",
        help="Disable thumbnail embedding for audio downloads.",
    )
    parser.add_argument(
        "--no-embed-metadata",
        dest="embed_metadata",
        action="store_false",
        help="Disable metadata tagging after downloads.",
    )
    parser.add_argument(
        "--cookies",
        help="Path to a cookies.txt file exported from a browser session.",
    )

    args = parser.parse_args(argv)

    url = args.url
    if not url:
        try:
            url = input("Enter the video or playlist URL: ").strip()
        except EOFError:  # pragma: no cover - interactive only
            url = ""
        args.url = url

    try:
        request = _build_request(args)
    except ValueError as exc:
        parser.error(str(exc))

    downloader = StreamSaavyDownloader(logger=print)

    def progress_hook(status: dict) -> None:
        state = status.get("status")
        if state == "downloading":
            percent = status.get("_percent_str", "0%")
            speed = status.get("_speed_str", "?")
            eta = status.get("_eta_str", "?")
            print(f"⬇️  {percent} at {speed} (ETA {eta})", end="\r", flush=True)
        elif state == "finished":
            filename = status.get("filename")
            if filename:
                print(f"\n✅ Finished: {filename}")

    try:
        downloader.download(request, progress_callback=progress_hook)
    except Exception as exc:  # pragma: no cover - runtime integration path
        print(f"\n❌ Download failed: {exc}", file=sys.stderr)
        return 1

    print("\nAll tasks completed successfully.")
    return 0


__all__ = ["run_cli"]


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(run_cli())

