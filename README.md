# 🎧⚡ StreamSaavy

**StreamSaavy** is a modern, desktop-friendly front end for `yt-dlp`, built for creators, collectors, and everyday users who just want their music and videos — fast.  

It provides a **clean Tkinter interface** that wraps `yt-dlp`’s power into simple workflows: choose your mode, set a destination, click “Start,” and watch real-time progress roll by.

---

## 🚀 Feature Highlights

- 🎛️ **Five core workflows**
  - Single Song → 256 kbps MP3
  - Single Video → H.264 MP4 (1080 p)
  - Playlist Audio → MP3 (256 kbps)
  - Playlist Video → MP4 (1080 p)
  - Compatibility Mode → re-encodes anything to MP3 when format data is missing
- 🎚️ **Smart defaults** with optional bitrate / resolution overrides
- 📂 **Destination picker** that remembers your last save folder
- 💬 **Persistent console** that mirrors `yt-dlp` output in real time
- 🧩 **Background threading** keeps the UI responsive during downloads
- 🧠 **Cookie import support** for authenticated YouTube sessions
- 📊 **Integrated progress bar** showing live percentage updates
- 🪶 **Lightweight, zero-nonsense footprint** — no Electron, no browser engine

---

## 🧰 Requirements

- **Python 3.9 +**
- [`yt-dlp`](https://github.com/yt-dlp/yt-dlp)
- `ffmpeg` accessible on your system `PATH`
- Standard library modules only (Tkinter, `subprocess`, `threading`, etc.)

---

## 💾 Installation

```bash
git clone https://github.com/youruser/streamsaavy.git
cd streamsaavy
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
````

Make sure `ffmpeg` is installed and works from your terminal:

```bash
ffmpeg -version
```

---

## 🖥 Running the App

### Desktop GUI (Tkinter)

```bash
python -m streamsaavy_app
```

Paste a YouTube URL, select your workflow (audio/video, single/playlist), choose where to save, and click **Start Download**.
A live activity panel displays `yt-dlp` progress, while the main window stays fully interactive.

### 📱 Terminal-friendly CLI (great for Android/Termux)

```bash
python -m streamsaavy_app --ui cli --mode single_song --output /sdcard/Download \
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

If you omit the URL the CLI will prompt for one. Additional flags let you override bitrate, resolution,
cookies, and metadata embedding so the experience mirrors the desktop app without requiring a GUI.
Run `python -m streamsaavy_app.cli --help` to see the full list of flags.

### 🌐 Web dashboard

1. Activate your virtual environment (if you created one during installation).
2. From the project directory run:

   ```bash
   python -m streamsaavy_app --ui web --host 0.0.0.0 --port 5000
   ```

   - Use `--host 127.0.0.1` if you only need to reach the site from the same machine.
   - Swap the port if `5000` is already taken.

3. Open a browser to `http://127.0.0.1:5000` (or the host/port you specified) to reach the dashboard.

The web UI mirrors the desktop workflows: pick a mode, paste a URL, and track live logs/progress. Cookie
uploads are supported as well, making it perfect for Android/Termux – start the server on your device and
visit the URL from mobile Chrome or Firefox.

---

## 🍪 Cookie Authentication

Need to download age-restricted or private videos?
Import your YouTube cookies (`cookies.txt`) from a browser extension like [Get Cookies.txt](https://chrome.google.com/webstore/detail/get-cookiestxt/).

In StreamSaavy:

1. Click **Import Cookies**.
2. Select your `cookies.txt` file.
3. StreamSaavy will use it automatically for authenticated downloads.

The app remembers your last-used cookies file between sessions.

---

## 📊 Progress Display

The console area now includes a live progress bar synced with `yt-dlp`’s percentage output.
You’ll see:

```
[download]   57.4% of 12.5MiB at 1.20MiB/s ETA 00:04
```

reflected visually in a smooth bar that fills as each download advances.

---

## 🧪 Development Notes

* The GUI layer (Tkinter) only handles display, progress, and user input.
* All download logic lives in `download.py` — the same backend used by the CLI.
* The interface calls those functions asynchronously to avoid blocking.
* Logging uses the same stdout stream as the CLI, ensuring consistent output.

### Lint & test (if you add tests)

```bash
flake8 streamsaavy_app
pytest -v
```

---

## 🧭 Roadmap

* [ ] Dark mode toggle
* [ ] Drag-and-drop URL support
* [ ] Inline metadata editor (title, artist, album tags)
* [ ] Download queue with pause/resume
* [ ] Visualized bitrate / file size estimator

---

## 📜 License

**MIT License** — do whatever you like, just give credit.
See [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

Issues and pull requests are welcome!
If you’ve built a new workflow or improved UI logic, open a PR or discussion.
Design and UX feedback are equally valuable — StreamSaavy is for everyone who loves fast, offline media access.

