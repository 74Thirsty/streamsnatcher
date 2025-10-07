# StreamSaavy 🎧⚡

StreamSaavy is a modern, desktop-friendly front end for `yt-dlp` that focuses on the
most common YouTube workflows:

* Grab a **single song** and transparently encode it to 256 kbps MP3.
* Pull down a **single video** and transcode it to an H.264 MP4 capped at 1080p HD.
* Rip **playlist audio** to MP3 at 256 kbps.
* Download **playlist video** in MP4 format, limited to 1080p.
* Fall back to a **Compatibility (MP3)** mode that accepts whatever audio is available
  and re-encodes it to MP3.

All options are configurable from a clean Tkinter interface that walks you through
choosing a destination folder, selecting download mode, and overriding defaults when
needed.

> **Note:** ffmpeg must be available on your system `PATH` for transcoding.

---

## 🚀 Feature highlights

* 🎛️ Five dedicated workflows (single/playlist × audio/video + compatibility)
* 🎚️ Sensible defaults with overrides for bitrate and resolution
* 💾 Directory picker and persistent logging console
* 🧰 Runs downloads in the background so the UI stays responsive

---

## 📦 Getting started

Clone the repository and install the minimal dependency list:

```bash
git clone https://github.com/youruser/streamsnatcher.git
cd streamsnatcher
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
pip install -r requirements.txt
```

Make sure `ffmpeg` is installed and accessible from your terminal.

---

## 🖥 Running the app

Launch the Tkinter interface via the module entry point:

```bash
python -m streamsaavy_app
```

From here you can paste a YouTube URL, choose where to save the output, and press
**Start download**. Progress is streamed in the activity panel and the UI stays responsive
while yt-dlp works in the background.

---

## 🧪 Development

The project is intentionally dependency-light. If you plan to contribute, install
development tools as needed and run linting or tests that you add.

---

## 📜 License

StreamSaavy is released under the **MIT License**.

---

## 🤝 Contributing

Issues and pull requests are welcome. Feel free to open a discussion for new workflows or
UI refinements.
