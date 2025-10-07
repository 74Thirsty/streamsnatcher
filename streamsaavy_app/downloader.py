"""Core download logic built around yt-dlp."""
from __future__ import annotations

import threading
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

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

    def normalized_audio_bitrate(self) -> str:
        bitrate = self.audio_bitrate.strip().lower()
        return bitrate if bitrate.endswith("k") else f"{bitrate}k"

    def normalized_video_resolution(self) -> str:
        return "".join(ch for ch in self.video_resolution if ch.isdigit()) or "1080"


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
        }

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
        return {
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": bitrate.replace("k", ""),
                }
            ],
            "postprocessor_args": ["-b:a", bitrate, "-ar", "44100"],
        }

    def _compatibility_opts(self, request: DownloadRequest) -> Dict[str, Any]:
        bitrate = request.normalized_audio_bitrate()
        return {
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": bitrate.replace("k", ""),
                }
            ],
            "postprocessor_args": ["-b:a", bitrate, "-ar", "44100"],
        }

    def _video_opts(self, request: DownloadRequest) -> Dict[str, Any]:
        resolution = request.normalized_video_resolution()
        format_selector = (
            f"bestvideo[height<={resolution}][ext=mp4]+bestaudio[ext=m4a]/"
            f"best[height<={resolution}]"
        )
        return {
            "format": format_selector,
            "merge_output_format": "mp4",
            "postprocessors": [
                {
                    "key": "FFmpegVideoConvertor",
                    "preferedformat": "mp4",
                }
            ],
            "postprocessor_args": [
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
            ],
        }

    def download(self, request: DownloadRequest, progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> None:
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

        with YoutubeDL(opts) as ydl:
            ydl.download([request.url])

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
