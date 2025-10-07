"""Download execution helpers for the StreamSaavy GUI."""
from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Callable, Optional

LineHandler = Callable[[str], None]
ProgressHandler = Callable[[float], None]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
)

BASE_ARGS = [
    "--newline",
    "--extractor-args",
    "youtube:player_client=web",
    "--user-agent",
    USER_AGENT,
    "--compat-options",
    "prefer-free-formats,manifestless",
    "--write-thumbnail",
    "--write-description",
    "--write-info-json",
    "--no-playlist",
]

CHOICE_TO_MODE = {
    "1": "single_song",
    "2": "single_video",
    "3": "playlist_song",
    "4": "playlist_video",
}

MODE_TO_ARGS = {
    "single_song": [
        "-f",
        "bestaudio[ext=m4a]/bestaudio[ext=webm]/best[protocol*=https]",
        "--extract-audio",
        "--audio-format",
        "mp3",
        "--audio-quality",
        "0.256",
    ],
    "single_video": [
        "-f",
        "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format",
        "mp4",
    ],
    "playlist_song": [
        "--yes-playlist",
        "-f",
        "bestaudio[ext=m4a]/bestaudio[ext=webm]/best[protocol*=https]",
        "--extract-audio",
        "--audio-format",
        "mp3",
        "--audio-quality",
        "0.256",
    ],
    "playlist_video": [
        "--yes-playlist",
        "-f",
        "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format",
        "mp4",
    ],
}


def build_command(
    mode: str,
    url: str,
    destination: str,
    *,
    cookies_path: Optional[str] = None,
) -> list[str]:
    """Construct a yt-dlp command for the provided download mode."""

    command = ["yt-dlp", *BASE_ARGS]

    if cookies_path:
        command.extend(["--cookies", cookies_path])
    else:
        cookies_file = Path.home() / ".yt-dlp-cookies.txt"
        if cookies_file.exists():
            command.extend(["--cookies-from-browser", "Chrome"])

    command.extend(["-P", destination])

    try:
        mode_args = MODE_TO_ARGS[mode]
    except KeyError as exc:
        raise ValueError(f"Unsupported download mode: {mode}") from exc

    command.extend(mode_args)
    command.append(url)
    return command


def create_command(
    choice: str,
    url: str,
    destination: str,
    *,
    cookies_path: Optional[str] = None,
) -> list[str]:
    """Translate a legacy menu choice to a download command."""

    mode = CHOICE_TO_MODE.get(str(choice))
    if mode is None:
        raise ValueError(f"Unknown selection: {choice}")
    return build_command(mode, url, destination, cookies_path=cookies_path)


def monitor_progress(
    process: subprocess.Popen[str],
    *,
    log_handler: Optional[LineHandler] = None,
    progress_handler: Optional[ProgressHandler] = None,
) -> None:
    """Stream yt-dlp output to log/progress callbacks."""

    progress_bar_width = 50
    processing_complete = False

    for raw_line in process.stdout or []:
        line = raw_line.strip()
        if not line:
            continue

        if log_handler is not None:
            log_handler(line)
        else:
            print(f"STATUS: {line}")

        if "%" in line:
            for part in line.split():
                if part.endswith("%"):
                    try:
                        percentage = float(part.strip("%"))
                    except ValueError:
                        continue
                    if progress_handler is not None:
                        progress_handler(percentage)
                    else:
                        filled = int(progress_bar_width * percentage / 100)
                        bar = f"[{'#' * filled}{'-' * (progress_bar_width - filled)}]"
                        print(f"\rProgress: {bar} {percentage:.1f}% ", end="", flush=True)
                    break

        if any(trigger in line for trigger in ("Merging formats into", "Transcoding", "Extracting audio")):
            if not processing_complete:
                message = "Transcoding, please wait..."
                if log_handler is not None:
                    log_handler(message)
                else:
                    print(f"\n{message}")
                processing_complete = True

        time.sleep(0.1)

    if progress_handler is not None:
        progress_handler(100.0)

    completion_message = "Download completed successfully!"
    if log_handler is not None:
        log_handler(completion_message)
    else:
        print(f"\n{completion_message}")


def run_download(
    choice: str,
    url: str,
    destination: str,
    *,
    log_handler: Optional[LineHandler] = None,
    progress_handler: Optional[ProgressHandler] = None,
    cookies_path: Optional[str] = None,
) -> None:
    """Execute a yt-dlp download using CLI-compatible options."""

    command = create_command(choice, url, destination, cookies_path=cookies_path)

    if log_handler is not None:
        log_handler("Starting download...")
    else:
        print("Starting download...")

    env = os.environ.copy()
    env.setdefault("LANG", "en_US.UTF-8")
    env.setdefault("LC_ALL", "en_US.UTF-8")

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
        env=env,
    )

    try:
        monitor_progress(
            process,
            log_handler=log_handler,
            progress_handler=progress_handler,
        )
        return_code = process.wait()
    finally:
        if process.stdout is not None:
            process.stdout.close()

    if return_code:
        raise subprocess.CalledProcessError(return_code, command)


def download_video(
    url: str,
    output_dir: str = ".",
    *,
    log_handler: Optional[LineHandler] = None,
    progress_handler: Optional[ProgressHandler] = None,
    cookies_path: Optional[str] = None,
) -> None:
    """Convenience wrapper for single video downloads used by the GUI."""

    run_download(
        "1",
        url,
        output_dir,
        log_handler=log_handler,
        progress_handler=progress_handler,
        cookies_path=cookies_path,
    )
