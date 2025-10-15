"""Core download logic built around yt-dlp."""
from __future__ import annotations

import threading
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
)

from yt_dlp.utils import DownloadError

AUDIO_FORMAT_SELECTOR = "bestaudio[ext=m4a]/bestaudio[ext=webm]/best[protocol*=https]"

try:
    from yt_dlp import YoutubeDL
except ImportError as exc:  # pragma: no cover - yt_dlp is required at runtime
    raise SystemExit(
        "yt-dlp is required to run StreamSaavy. Install it with 'pip install yt-dlp'."
    ) from exc


class DownloadMode(str, Enum):
    """Supported download modes."""

    SINGLE_SONG = "single_song"
    SINGLE_VIDEO = "single_video"
    PLAYLIST_SONGS = "playlist_songs"
    PLAYLIST_VIDEOS = "playlist_videos"
    COMPATIBILITY = "compatibility"

    @property
    def is_audio(self) -> bool:
        return self in {self.SINGLE_SONG, self.PLAYLIST_SONGS, self.COMPATIBILITY}

    @property
    def is_playlist(self) -> bool:
        return self in {self.PLAYLIST_SONGS, self.PLAYLIST_VIDEOS}

    @property
    def display_label(self) -> str:
        """Return a human friendly label for UI elements."""

        base = self.name.replace("_", " ").title()
        if self is self.COMPATIBILITY:
            return f"{base} (Audio Fallback)"
        media_type = "Audio" if self.is_audio else "Video"
        return f"{base} ({media_type})"


@dataclass
class DownloadRequest:
    """Container for download configuration."""

    url: str
    save_path: Path
    mode: DownloadMode
    audio_bitrate: str = "256K"
    video_resolution: str = "1080"
    embed_thumbnail: bool = True
    embed_metadata: bool = True
    cookies_path: Optional[Path] = None

    def normalized_audio_bitrate(self) -> str:
        bitrate = self.audio_bitrate.strip().lower()
        return bitrate if bitrate.endswith("k") else f"{bitrate}k"

    def normalized_video_resolution(self) -> str:
        return "".join(ch for ch in self.video_resolution if ch.isdigit()) or "1080"


VIDEO_FORMAT_SELECTOR_TEMPLATE = (
    "bestvideo[ext=mp4][height<={height}][fps<=60]+bestaudio[ext=m4a]/"
    "bestvideo[height<={height}][fps<=60]+bestaudio/best[ext=mp4]/best"
)


class StreamSaavyDownloader:
    """High level helper that prepares yt-dlp options and runs the download."""

    def __init__(self, logger: Optional[Callable[[str], None]] = None) -> None:
        self._logger = logger or (lambda message: None)

    def _log(self, message: str) -> None:
        self._logger(message)

    def _build_ydl_opts(self, request: DownloadRequest, hooks: Iterable[Callable[[Dict[str, Any]], None]]) -> Dict[str, Any]:
        outtmpl = str(request.save_path / "%(title)s.%(ext)s")
        opts: Dict[str, Any] = {
            "outtmpl": outtmpl,
            "progress_hooks": list(hooks),
            "concurrent_fragment_downloads": 4,
            "noplaylist": not request.mode.is_playlist,
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": request.mode == DownloadMode.COMPATIBILITY,
            "extractor_args": {"youtube": {"player_client": ["web"]}},
            "user_agent": USER_AGENT,
            "compat_opts": {"manifestless"},

        }

        if request.cookies_path is not None:
            opts["cookiefile"] = str(request.cookies_path)

        if request.mode == DownloadMode.COMPATIBILITY:
            opts.update(self._compatibility_opts(request))
        elif request.mode.is_audio:
            opts.update(self._audio_opts(request))
        else:
            opts.update(self._video_opts(request))

        postprocessors: List[Dict[str, Any]] = opts.setdefault("postprocessors", [])
        if request.embed_thumbnail and request.mode.is_audio:
            postprocessors.append({"key": "EmbedThumbnail"})
        if request.embed_metadata:
            postprocessors.append({"key": "FFmpegMetadata"})

        return opts

    def _audio_opts(self, request: DownloadRequest) -> Dict[str, Any]:
        bitrate = request.normalized_audio_bitrate()
        quality = "".join(ch for ch in bitrate if ch.isdigit()) or "256"
        return {
            "format": AUDIO_FORMAT_SELECTOR,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": quality,
                }
            ],
            "postprocessor_args": {
                "FFmpegExtractAudio": ["-b:a", bitrate, "-ar", "44100"],
            },
            "final_ext": "mp3",
        }

    def _compatibility_opts(self, request: DownloadRequest) -> Dict[str, Any]:
        return self._audio_opts(request)

    def _video_opts(self, request: DownloadRequest) -> Dict[str, Any]:
        resolution = request.normalized_video_resolution()
        format_selector = VIDEO_FORMAT_SELECTOR_TEMPLATE.format(height=resolution)
        return {
            "format": format_selector,
            "merge_output_format": "mp4",
            "postprocessors": [
                {
                    "key": "FFmpegVideoConvertor",
                    "preferedformat": "mp4",
                }
            ],
            "postprocessor_args": {
                "FFmpegVideoConvertor": [
                    "-map",
                    "0:v:0?",
                    "-map",
                    "0:a:0?",
                    "-vf",
                    f"scale=-2:{resolution}:force_original_aspect_ratio=decrease",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "medium",
                    "-crf",
                    "19",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-movflags",
                    "+faststart",
                ],
            },
            "final_ext": "mp4",
        }

    def download(self, request: DownloadRequest, progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> None:
        request.save_path.mkdir(parents=True, exist_ok=True)
        hooks = []
        if progress_callback is not None:
            hooks.append(progress_callback)
        hooks.append(self._progress_logger)

        opts = self._build_ydl_opts(request, hooks)

        self._log("Starting yt-dlp with the following options:")
        for key, value in opts.items():
            if key == "progress_hooks":
                continue
            self._log(f"  {key}: {value}")

        try:
            with YoutubeDL(opts) as ydl:
                ydl.download([request.url])
        except DownloadError as exc:
            message = str(exc)
            if "Only images are available" in message or "Requested format is not available" in message:
                self._log(
                    "⚠️ YouTube did not provide a playable video stream for the selected format. "
                    "Try switching to Compatibility mode or run 'yt-dlp -F <url>' to list supported formats."
                )
            raise

    def _progress_logger(self, status: Dict[str, Any]) -> None:
        if status.get("status") == "downloading":
            percent = status.get("_percent_str", "0%")
            speed = status.get("_speed_str", "?")
            eta = status.get("_eta_str", "?")
            self._log(f"Downloading... {percent} at {speed}, ETA {eta}")
        elif status.get("status") == "finished":
            filename = status.get("filename")
            self._log(f"Download finished: {filename}")
        elif status.get("status") == "error":
            self._log("An error occurred while downloading.")


class BackgroundDownloader:
    """Utility to run downloads without blocking the UI thread."""

    def __init__(self, downloader: StreamSaavyDownloader) -> None:
        self.downloader = downloader
        self._thread: Optional[threading.Thread] = None

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, request: DownloadRequest, progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None, done_callback: Optional[Callable[[Optional[Exception]], None]] = None) -> None:
        if self.is_running():
            raise RuntimeError("A download is already in progress.")

        def worker() -> None:
            error: Optional[Exception] = None
            try:
                self.downloader.download(request, progress_callback=progress_callback)
            except Exception as exc:  # pragma: no cover - propagated to UI
                error = exc
            finally:
                if done_callback is not None:
                    done_callback(error)

        self._thread = threading.Thread(target=worker, daemon=True)
        self._thread.start()
