"""Tkinter powered graphical interface for StreamSaavy."""
from __future__ import annotations

import queue
import threading
from pathlib import Path
from tkinter import (
    BOTH,
    DISABLED,
    END,
    E,
    N,
    NORMAL,
    S,
    W,
    BooleanVar,
    DoubleVar,
    StringVar,
    Text,
    Tk,
    filedialog,
    messagebox,
)
from tkinter import ttk
from typing import Any, Dict, Optional

from .downloader import DownloadMode
from download import download_media


class StreamSaavyApp(Tk):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.title("StreamSaavy - yt-dlp Power UI")
        self.geometry("960x640")
        self.minsize(800, 600)

        self._log_queue: "queue.Queue[str]" = queue.Queue()
        self._download_thread: Optional[threading.Thread] = None
        self._is_downloading = False

        self.save_path = Path.home()
        self.mode_var = StringVar(value=DownloadMode.VIDEO.value)
        self.url_var = StringVar()
        self.audio_bitrate_var = StringVar(value="256k")
        self.video_resolution_var = StringVar(value="1080")
        self.embed_thumbnail_var = BooleanVar(value=True)
        self.embed_metadata_var = BooleanVar(value=True)
        self.progress_var = DoubleVar(value=0.0)
        self.cookies_path: Optional[Path] = None

        self._audio_widgets = []
        self._video_widgets = []

        self._build_widgets()
        self.after(100, self._process_log_queue)

    # ------------------------------------------------------------------
    # UI construction helpers
    # ------------------------------------------------------------------
    def _build_widgets(self) -> None:
        container = ttk.Frame(self, padding=20)
        container.pack(fill=BOTH, expand=True)

        header = ttk.Label(container, text="StreamSaavy", font=("Segoe UI", 24, "bold"))
        header.grid(row=0, column=0, columnspan=4, sticky=W)

        subtitle = ttk.Label(
            container,
            text="High-touch yt-dlp front-end for MP4 video and MP3 audio",
            font=("Segoe UI", 12),
        )
        subtitle.grid(row=1, column=0, columnspan=4, sticky=W, pady=(0, 20))

        # URL entry
        ttk.Label(container, text="Source URL:").grid(row=2, column=0, sticky=W)
        self.url_entry = ttk.Entry(container, textvariable=self.url_var, width=70)
        self.url_entry.grid(row=2, column=1, columnspan=2, sticky=W + E, pady=5)
        cookies_button = ttk.Button(container, text="Import Cookies", command=self.import_cookies)
        cookies_button.grid(row=2, column=3, sticky=E, padx=(8, 0))
        self.url_entry.focus_set()

        self.cookies_status = ttk.Label(container, text="🍪 No cookies loaded", font=("Segoe UI", 9))
        self.cookies_status.grid(row=3, column=1, columnspan=3, sticky=W)

        # Save location
        ttk.Label(container, text="Save to:").grid(row=4, column=0, sticky=W)
        self.save_label = ttk.Label(container, text=str(self.save_path), relief="groove", padding=(6, 3))
        self.save_label.grid(row=4, column=1, columnspan=2, sticky=W + E, pady=5)
        choose_button = ttk.Button(container, text="Choose...", command=self.choose_save_location)
        choose_button.grid(row=4, column=3, sticky=E)

        # Mode selection
        mode_frame = ttk.LabelFrame(container, text="Choose output format", padding=10)
        mode_frame.grid(row=5, column=0, columnspan=4, sticky=W + E, pady=10)

        for index, (mode, label) in enumerate(
            [
                (DownloadMode.VIDEO, "Video (MP4)"),
                (DownloadMode.AUDIO, "Audio Only (MP3)"),
            ]
        ):
            ttk.Radiobutton(
                mode_frame,
                text=label,
                value=mode.value,
                variable=self.mode_var,
                command=self._mode_changed,
            ).grid(row=0, column=index, padx=6, pady=6)

        # Audio options
        audio_frame = ttk.LabelFrame(container, text="Audio settings", padding=10)
        audio_frame.grid(row=6, column=0, columnspan=2, sticky=W + E)
        ttk.Label(audio_frame, text="Bitrate (kbps):").grid(row=0, column=0, sticky=W)
        audio_entry = ttk.Entry(audio_frame, textvariable=self.audio_bitrate_var, width=12)
        audio_entry.grid(row=0, column=1, sticky=W)
        embed_thumb = ttk.Checkbutton(
            audio_frame,
            text="Embed thumbnail",
            variable=self.embed_thumbnail_var,
        )
        embed_thumb.grid(row=1, column=0, columnspan=2, sticky=W, pady=(4, 0))
        self._audio_widgets.extend([audio_entry, embed_thumb])

        # Video options
        video_frame = ttk.LabelFrame(container, text="Video settings", padding=10)
        video_frame.grid(row=6, column=2, columnspan=2, sticky=W + E)
        ttk.Label(video_frame, text="Max resolution (p):").grid(row=0, column=0, sticky=W)
        video_entry = ttk.Entry(video_frame, textvariable=self.video_resolution_var, width=12)
        video_entry.grid(row=0, column=1, sticky=W)
        self._video_widgets.append(video_entry)

        ttk.Checkbutton(
            container,
            text="Embed metadata tags",
            variable=self.embed_metadata_var,
        ).grid(row=7, column=0, columnspan=4, sticky=W, pady=(8, 0))

        # Buttons
        self.download_button = ttk.Button(container, text="Start download", command=self.start_download)
        self.download_button.grid(row=8, column=0, pady=12, sticky=W)

        self.cancel_button = ttk.Button(container, text="Cancel", command=self.cancel_download, state=DISABLED)
        self.cancel_button.grid(row=8, column=1, pady=12, sticky=W)

        # Log area
        log_frame = ttk.LabelFrame(container, text="Activity", padding=10)
        log_frame.grid(row=9, column=0, columnspan=4, sticky=N + S + W + E, pady=(10, 0))
        container.rowconfigure(9, weight=1)
        container.columnconfigure(1, weight=1)
        container.columnconfigure(2, weight=1)
        container.columnconfigure(3, weight=1)

        self.log_text = Text(log_frame, height=14, wrap="word")
        self.log_text.pack(fill=BOTH, expand=True)
        self.log_text.configure(state=DISABLED)

        self.progress_bar = ttk.Progressbar(
            container,
            maximum=100,
            mode="determinate",
            variable=self.progress_var,
        )
        self.progress_bar.grid(row=10, column=0, columnspan=4, sticky=W + E, pady=(10, 0))

        self._mode_changed()

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------
    def _mode_changed(self) -> None:
        mode = DownloadMode(self.mode_var.get())
        audio_state = NORMAL if mode.is_audio else DISABLED
        video_state = NORMAL if not mode.is_audio else DISABLED

        for widget in self._audio_widgets:
            widget.configure(state=audio_state)

        for widget in self._video_widgets:
            widget.configure(state=video_state)

    def choose_save_location(self) -> None:
        directory = filedialog.askdirectory(initialdir=str(self.save_path), title="Select download directory")
        if directory:
            self.save_path = Path(directory)
            self.save_label.configure(text=directory)
            self.queue_log(f"Save location set to {directory}")

    def import_cookies(self) -> None:
        file_path = filedialog.askopenfilename(
            initialdir=str(self.save_path),
            title="Select Cookies File",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        )
        if not file_path:
            return

        candidate = Path(file_path)
        if not candidate.exists() or not candidate.is_file():
            messagebox.showerror("Invalid cookies file", "❌ Invalid cookies file or unreadable format")
            self.queue_log("❌ Invalid cookies file or unreadable format")
            return

        try:
            with candidate.open("r", encoding="utf-8", errors="ignore") as handle:
                handle.read(0)
        except OSError:
            messagebox.showerror("Invalid cookies file", "❌ Invalid cookies file or unreadable format")
            self.queue_log("❌ Invalid cookies file or unreadable format")
            return

        self.cookies_path = candidate
        self.cookies_status.configure(text=f"🍪 Cookies loaded: {candidate}")
        self.queue_log(f"Cookies loaded from {candidate}")

    def start_download(self) -> None:
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Missing URL", "Please provide a video or playlist URL.")
            return

        if not self.save_path.exists():
            try:
                self.save_path.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                messagebox.showerror("Invalid directory", f"Unable to use directory: {exc}")
                return

        if self.cookies_path is not None and not self.cookies_path.exists():
            messagebox.showerror("Cookies missing", "The selected cookies file can no longer be found.")
            self.cookies_status.configure(text="🍪 No cookies loaded")
            self.cookies_path = None
            return

        if self._is_downloading:
            messagebox.showwarning("Busy", "A download is already in progress.")
            return

        self._is_downloading = True
        self.download_button.configure(state=DISABLED)
        self.cancel_button.configure(state=NORMAL)
        self.queue_log("Launching download job...")
        self._update_progress(0.0)

        def worker() -> None:
            def log_handler(message: str) -> None:
                self.queue_log(message)

            def progress_hook(status: Dict[str, Any]) -> None:
                if status.get("status") == "downloading":
                    percent = status.get("_percent_str", "0%")
                    try:
                        value = float(percent.strip().rstrip("%"))
                    except ValueError:
                        value = 0.0
                    self.after(0, lambda value=value: self._update_progress(value))
                elif status.get("status") == "finished":
                    filename = status.get("filename")
                    if filename:
                        self.queue_log(f"Finished: {filename}")
                    self.after(0, lambda: self._update_progress(100.0))

            error: Optional[Exception] = None
            try:
                download_media(
                    url,
                    str(self.save_path),
                    log_handler=log_handler,
                    progress_hooks=[progress_hook],
                    cookiefile=str(self.cookies_path) if self.cookies_path is not None else None,
                )
            except Exception as exc:  # pragma: no cover - runtime integration
                error = exc
                self.queue_log(f"ERROR: {exc}")
            finally:
                self.after(0, lambda err=error: self._finish_download(error=err))

        self._download_thread = threading.Thread(target=worker, daemon=True)
        self._download_thread.start()

    def cancel_download(self) -> None:
        messagebox.showinfo(
            "Cancel",
            "Graceful cancellation isn't supported yet, but you can close the app to abort the download.",
        )

    def _finish_download(self, *, error: Optional[Exception]) -> None:
        self._is_downloading = False
        self._download_thread = None
        self.download_button.configure(state=NORMAL)
        self.cancel_button.configure(state=DISABLED)
        if error is not None:
            messagebox.showerror("Download failed", str(error))
            self._update_progress(0.0)
        else:
            messagebox.showinfo("Download complete", "All tasks finished successfully")
            self.queue_log("✅ Download complete")
            self._update_progress(100.0)
            self.queue_log("Download pipeline completed")

    # ------------------------------------------------------------------
    # Logging helpers
    # ------------------------------------------------------------------
    def queue_log(self, message: str) -> None:
        self._log_queue.put(message)

    def _process_log_queue(self) -> None:
        try:
            while True:
                message = self._log_queue.get_nowait()
                self._append_log(message)
        except queue.Empty:
            pass
        finally:
            self.after(150, self._process_log_queue)

    def _append_log(self, message: str) -> None:
        self.log_text.configure(state=NORMAL)
        self.log_text.insert(END, message + "\n")
        self.log_text.see(END)
        self.log_text.configure(state=DISABLED)

    def _update_progress(self, percentage: float) -> None:
        bounded = max(0.0, min(percentage, 100.0))
        self.progress_var.set(bounded)
        self.progress_bar.update_idletasks()

def run() -> None:
    app = StreamSaavyApp()
    app.mainloop()
