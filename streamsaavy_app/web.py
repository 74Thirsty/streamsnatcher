"""Flask powered web interface for StreamSaavy."""
from __future__ import annotations

import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from werkzeug.utils import secure_filename

from .downloader import BackgroundDownloader, DownloadMode, DownloadRequest, StreamSaavyDownloader


TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


@dataclass
class DownloadState:
    """Shared download state for the web interface."""

    active: bool = False
    progress: float = 0.0
    status: str = "idle"
    logs: List[str] = field(default_factory=list)
    last_error: Optional[str] = None
    last_cookies_dir: Optional[Path] = None
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def reset(self) -> None:
        with self._lock:
            self.active = False
            self.progress = 0.0
            self.status = "idle"
            self.logs.clear()
            self.last_error = None
            self._cleanup_cookies_dir()

    def start(self) -> None:
        with self._lock:
            self.active = True
            self.progress = 0.0
            self.status = "running"
            self.last_error = None
            self.logs.clear()

    def finish(self, error: Optional[Exception]) -> None:
        with self._lock:
            self.active = False
            self.progress = 100.0 if error is None else self.progress
            self.status = "completed" if error is None else "error"
            if error is not None:
                self.last_error = str(error)
            self._cleanup_cookies_dir()

    def add_log(self, message: str) -> None:
        with self._lock:
            self.logs.append(message)
            # Keep history manageable for the UI.
            if len(self.logs) > 400:
                self.logs[:] = self.logs[-400:]

    def set_progress(self, value: float) -> None:
        with self._lock:
            self.progress = max(0.0, min(value, 100.0))

    def snapshot(self) -> Dict[str, object]:
        with self._lock:
            return {
                "active": self.active,
                "progress": self.progress,
                "status": self.status,
                "logs": list(self.logs),
                "error": self.last_error,
            }

    def store_cookies_dir(self, directory: Path) -> None:
        with self._lock:
            self._cleanup_cookies_dir()
            self.last_cookies_dir = directory

    def _cleanup_cookies_dir(self) -> None:
        if self.last_cookies_dir and self.last_cookies_dir.exists():
            for child in self.last_cookies_dir.iterdir():
                try:
                    child.unlink()
                except OSError:
                    pass
            try:
                self.last_cookies_dir.rmdir()
            except OSError:
                pass
        self.last_cookies_dir = None


state = DownloadState()
downloader = StreamSaavyDownloader(logger=state.add_log)
background = BackgroundDownloader(downloader)
app = Flask(__name__, template_folder=str(TEMPLATE_DIR))


def _build_request(form: Dict[str, str], cookies_path: Optional[Path]) -> DownloadRequest:
    url = (form.get("url") or "").strip()
    if not url:
        raise ValueError("A video or playlist URL is required.")

    save_directory = Path(form.get("save_path") or (Path.home() / "Downloads"))
    mode = DownloadMode(form.get("mode", DownloadMode.SINGLE_SONG.value))

    audio_bitrate = form.get("audio_bitrate", "256k")
    video_resolution = form.get("video_resolution", "1080")
    embed_thumbnail = form.get("embed_thumbnail") == "on"
    embed_metadata = form.get("embed_metadata") == "on"

    return DownloadRequest(
        url=url,
        save_path=save_directory.expanduser(),
        mode=mode,
        audio_bitrate=audio_bitrate,
        video_resolution=video_resolution,
        embed_thumbnail=embed_thumbnail,
        embed_metadata=embed_metadata,
        cookies_path=cookies_path,
    )


@app.route("/")
def index() -> str:
    snapshot = state.snapshot()
    default_save_path = str(Path.home() / "Downloads")
    return render_template(
        "index.html",
        modes=[(mode.value, mode.display_label) for mode in DownloadMode],
        state=snapshot,
        default_save_path=default_save_path,
    )


@app.post("/start")
def start_download() -> Response:
    if background.is_running():
        state.add_log("⚠️ A download is already running. Please wait for it to finish.")
        return redirect(url_for("index"))

    form = request.form
    cookies_file = request.files.get("cookies")
    cookies_path: Optional[Path] = None

    if cookies_file and cookies_file.filename:
        temp_dir = Path(tempfile.mkdtemp(prefix="streamsaavy_cookies_"))
        filename = secure_filename(cookies_file.filename) or "cookies.txt"
        destination = temp_dir / filename
        cookies_file.save(destination)
        cookies_path = destination
        state.store_cookies_dir(temp_dir)

    try:
        download_request = _build_request(form, cookies_path)
    except ValueError as exc:
        state.add_log(f"❌ {exc}")
        state.finish(error=exc)
        return redirect(url_for("index"))

    state.start()
    state.add_log("🚀 Launching download job...")

    def progress_hook(status: Dict[str, object]) -> None:
        if status.get("status") == "downloading":
            percent = status.get("_percent_str", "0%")
            try:
                value = float(str(percent).strip().rstrip("%"))
            except ValueError:
                value = 0.0
            state.set_progress(value)
        elif status.get("status") == "finished":
            filename = status.get("filename")
            if filename:
                state.add_log(f"✅ Finished: {filename}")
            state.set_progress(100.0)

    def on_complete(error: Optional[Exception]) -> None:
        if error is None:
            state.add_log("🎉 All tasks finished successfully.")
        else:
            state.add_log(f"❌ Download failed: {error}")
        state.finish(error)

    background.start(download_request, progress_callback=progress_hook, done_callback=on_complete)

    return redirect(url_for("index"))


@app.get("/status")
def status() -> Response:
    return jsonify(state.snapshot())


def run_server(host: str = "127.0.0.1", port: int = 5000, debug: bool = False) -> None:
    """Launch the Flask development server."""

    app.run(host=host, port=port, debug=debug)


__all__ = ["app", "run_server"]

