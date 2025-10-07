"""Tkinter powered graphical interface for StreamSaavy."""
from __future__ import annotations

import queue
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
    StringVar,
    Text,
    Tk,
    filedialog,
    messagebox,
)
from tkinter import ttk
from typing import Dict, Optional

from .downloader import (
    BackgroundDownloader,
    DownloadMode,
    DownloadRequest,
    StreamSaavyDownloader,
)


class StreamSaavyApp(Tk):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.title("StreamSaavy - yt-dlp Power UI")
        self.geometry("960x640")
        self.minsize(800, 600)

        self._log_queue: "queue.Queue[str]" = queue.Queue()
        self._downloader = BackgroundDownloader(StreamSaavyDownloader(self.queue_log))

        self.save_path = Path.home()
        self.mode_var = StringVar(value=DownloadMode.SINGLE_SONG.value)
        self.url_var = StringVar()
        self.audio_bitrate_var = StringVar(value="256k")
        self.video_resolution_var = StringVar(value="1080")
        self.embed_thumbnail_var = BooleanVar(value=True)
        self.embed_metadata_var = BooleanVar(value=True)

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
            text="High-touch yt-dlp front-end with MP3 compatibility fallback",
            font=("Segoe UI", 12),
        )
        subtitle.grid(row=1, column=0, columnspan=4, sticky=W, pady=(0, 20))

        # URL entry
        ttk.Label(container, text="Source URL:").grid(row=2, column=0, sticky=W)
        self.url_entry = ttk.Entry(container, textvariable=self.url_var, width=70)
        self.url_entry.grid(row=2, column=1, columnspan=3, sticky=W + E, pady=5)
        self.url_entry.focus_set()

        # Save location
        ttk.Label(container, text="Save to:").grid(row=3, column=0, sticky=W)
        self.save_label = ttk.Label(container, text=str(self.save_path), relief="groove", padding=(6, 3))
        self.save_label.grid(row=3, column=1, columnspan=2, sticky=W + E, pady=5)
        choose_button = ttk.Button(container, text="Choose...", command=self.choose_save_location)
        choose_button.grid(row=3, column=3, sticky=E)

        # Mode selection
        mode_frame = ttk.LabelFrame(container, text="What are we grabbing?", padding=10)
        mode_frame.grid(row=4, column=0, columnspan=4, sticky=W + E, pady=10)

        for index, (mode, label) in enumerate(
            [
                (DownloadMode.SINGLE_SONG, "Single Song (Audio)"),
                (DownloadMode.SINGLE_VIDEO, "Single Video"),
                (DownloadMode.PLAYLIST_SONGS, "Playlist (Audio)"),
                (DownloadMode.PLAYLIST_VIDEOS, "Playlist (Video)"),
                (DownloadMode.COMPATIBILITY, "Compatibility (MP3)"),
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
        audio_frame.grid(row=5, column=0, columnspan=2, sticky=W + E)
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
        video_frame.grid(row=5, column=2, columnspan=2, sticky=W + E)
        ttk.Label(video_frame, text="Max resolution (p):").grid(row=0, column=0, sticky=W)
        video_entry = ttk.Entry(video_frame, textvariable=self.video_resolution_var, width=12)
        video_entry.grid(row=0, column=1, sticky=W)
        self._video_widgets.append(video_entry)

        ttk.Checkbutton(
            container,
            text="Embed metadata tags",
            variable=self.embed_metadata_var,
        ).grid(row=6, column=0, columnspan=4, sticky=W, pady=(8, 0))

        # Buttons
        self.download_button = ttk.Button(container, text="Start download", command=self.start_download)
        self.download_button.grid(row=7, column=0, pady=12, sticky=W)

        self.cancel_button = ttk.Button(container, text="Cancel", command=self.cancel_download, state=DISABLED)
        self.cancel_button.grid(row=7, column=1, pady=12, sticky=W)

        # Log area
        log_frame = ttk.LabelFrame(container, text="Activity", padding=10)
        log_frame.grid(row=8, column=0, columnspan=4, sticky=N + S + W + E, pady=(10, 0))
        container.rowconfigure(8, weight=1)
        container.columnconfigure(1, weight=1)
        container.columnconfigure(2, weight=1)
        container.columnconfigure(3, weight=1)

        self.log_text = Text(log_frame, height=14, wrap="word")
        self.log_text.pack(fill=BOTH, expand=True)
        self.log_text.configure(state=DISABLED)

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

        request = DownloadRequest(
            url=url,
            save_path=self.save_path,
            mode=DownloadMode(self.mode_var.get()),
            audio_bitrate=self.audio_bitrate_var.get() or "256k",
            video_resolution=self.video_resolution_var.get() or "1080",
            embed_thumbnail=self.embed_thumbnail_var.get(),
            embed_metadata=self.embed_metadata_var.get(),
        )

        self.download_button.configure(state=DISABLED)
        self.cancel_button.configure(state=NORMAL)
        self.queue_log("Launching download job...")

        def done_callback(error: Optional[Exception]) -> None:
            def finalize() -> None:
                if error:
                    messagebox.showerror("Download failed", str(error))
                    self.queue_log(f"ERROR: {error}")
                else:
                    messagebox.showinfo("Download complete", "All tasks finished successfully")
                    self.queue_log("Download pipeline completed")
                self.download_button.configure(state=NORMAL)
                self.cancel_button.configure(state=DISABLED)

            self.after(0, finalize)

        try:
            self._downloader.start(
                request,
                progress_callback=lambda status: self.after(0, self._handle_progress, status),
                done_callback=done_callback,
            )
        except RuntimeError as exc:
            messagebox.showwarning("Busy", str(exc))
            self.download_button.configure(state=NORMAL)
            self.cancel_button.configure(state=DISABLED)

    def cancel_download(self) -> None:
        messagebox.showinfo(
            "Cancel",
            "Graceful cancellation isn't supported yet, but you can close the app to abort the download.",
        )

    def _handle_progress(self, status: Dict[str, object]) -> None:
        if status.get("status") == "downloading":
            percent = status.get("_percent_str", "0%")
            eta = status.get("_eta_str", "?")
            self.queue_log(f"Progress: {percent} remaining ETA {eta}")
        elif status.get("status") == "finished":
            filename = status.get("filename", "")
            self.queue_log(f"Finished: {filename}")
        elif status.get("status") == "error":
            self.queue_log("A download error was reported by yt-dlp")

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

def run() -> None:
    app = StreamSaavyApp()
    app.mainloop()
