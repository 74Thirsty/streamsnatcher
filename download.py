"""Command-line download helpers shared between CLI and GUI."""

import os
import subprocess
from pathlib import Path
import sys
import time
from typing import Callable, Optional

LineHandler = Callable[[str], None]
ProgressHandler = Callable[[float], None]


class ProgressBar:
    def __init__(self, width=50):
        self.width = width
        
    def update(self, percentage):
        filled = int(self.width * percentage / 100)
        bar = f"[{'#' * filled}{'-' * (self.width - filled)}]"
        print(f"\rProgress: {bar} {percentage:.1f}% ", end='')
        sys.stdout.flush()

def get_user_input():
    print("\n=== YouTube Downloader ===")
    print("1. Single Video [1080p HD MP4]")
    print("2. Single Song [256k VBR MP3]")
    print("3. Playlist Video [1080p HD MP4]")
    print("4. Playlist Song [256k VBR MP3]")
    
    while True:
        choice = input("\nEnter number (1-4): ").strip()
        if choice in ['1', '2', '3', '4']:
            break
        print("Invalid choice. Please enter 1-4.")
    
    url = input("\nEnter URL: ").strip()
    
    destination = input("Enter destination folder (leave blank for ~/Music): ").strip()
    if not destination:
        destination = str(Path.home() / "Music")
    
    return choice, url, destination

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
)


def create_command(choice, url, destination, cookies_path: Optional[str] = None):
    base_command = [
        "yt-dlp",
        "--newline",
        "--extractor-args",
        "youtube:player_client=web",
        "--user-agent",
        USER_AGENT,
    ]

    if cookies_path:
        base_command.extend(["--cookies", cookies_path])
    else:
        cookies_file = Path.home() / ".yt-dlp-cookies.txt"
        if cookies_file.exists():
            base_command.extend(["--cookies-from-browser", "Chrome"])
    
    base_command.extend([
        "-P",
        destination,
        "--write-thumbnail",
        "--write-description",
        "--write-info-json",
        "--compat-options",
        "no-youtube-channel-redirect,no-youtube-live-check,prefer-free-formats,manifestless",
    ])

    format_selector = "bestaudio[ext=m4a]/bestaudio[ext=webm]/best[protocol*=https]"

    if choice == '1':  # Single video
        base_command.extend(["--remux-video", "mp4"])
        return base_command + ["-f", format_selector, "--no-playlist", url]

    elif choice == '2':  # Single song
        base_command.extend([
            "-f",
            format_selector,
            "--extract-audio",
            "--audio-format",
            "mp3",
            "--audio-quality",
            "0.256",
            "--no-playlist",
        ])
        return base_command + [url]

    elif choice == '3':  # Playlist videos
        base_command.extend(["--remux-video", "mp4", "--yes-playlist"])
        return base_command + ["-f", format_selector, url]

    elif choice == '4':  # Playlist songs
        base_command.extend([
            "-f",
            format_selector,
            "--extract-audio",
            "--audio-format",
            "mp3",
            "--audio-quality",
            "0.256",
            "--yes-playlist",
        ])
        return base_command + [url]
    
def monitor_progress(
    process: subprocess.Popen[str],
    *,
    log_handler: Optional[LineHandler] = None,
    progress_handler: Optional[ProgressHandler] = None,
) -> None:
    bar = ProgressBar() if progress_handler is None else None
    processing_complete = False

    for line in process.stdout:
        line = line.strip()
        if not line:
            continue

        if log_handler is not None:
            log_handler(line)
        else:
            print(f"STATUS: {line}")

        if "%" in line:
            parts = line.split()
            for part in parts:
                if "%" in part:
                    try:
                        percentage = float(part.strip('%'))
                        if progress_handler is not None:
                            progress_handler(percentage)
                        elif bar is not None:
                            bar.update(percentage)
                        break
                    except ValueError:
                        pass

        if "Merging formats into" in line or "Transcoding" in line or "Extracting audio" in line:
            if not processing_complete:
                if log_handler is not None:
                    log_handler("Transcoding, please wait...")
                else:
                    print("\nTranscoding, please wait...")
                processing_complete = True

        time.sleep(0.1)

    if progress_handler is not None:
        progress_handler(100.0)

    completion_message = "\nDownload completed successfully!"
    if log_handler is not None:
        log_handler(completion_message.strip())
    else:
        print(completion_message)


def run_download(
    choice: str,
    url: str,
    destination: str,
    *,
    log_handler: Optional[LineHandler] = None,
    progress_handler: Optional[ProgressHandler] = None,
    cookies_path: Optional[str] = None,
) -> None:
    """Execute a yt-dlp download using the CLI options.

    Parameters
    ----------
    choice:
        The menu option number representing the download type.
    url:
        Target video or playlist URL.
    destination:
        Output directory path.
    log_handler:
        Optional callback for textual log lines. Falls back to printing.
    progress_handler:
        Optional callback receiving progress percentage updates.
    """

    command = create_command(choice, url, destination, cookies_path=cookies_path)

    if log_handler is not None:
        log_handler("Starting download...")
    else:
        print("\nStarting download...")

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

def main():
    try:
        choice, url, destination = get_user_input()
        bar = ProgressBar()
        run_download(choice, url, destination, progress_handler=bar.update)
        print("\nIts' Finally Done.")

    except subprocess.SubprocessError as e:
        print(f"\nError: {str(e)}")
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nUnexpected error occurred: {str(e)}")
    
    input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()
