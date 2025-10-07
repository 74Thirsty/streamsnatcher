import subprocess
from pathlib import Path
import sys
import time
from typing import Callable, Optional

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

def create_command(choice, url, destination):
    base_command = ["yt-dlp", "--progress", "--newline"]

    cookies_file = Path.home() / ".yt-dlp-cookies.txt"
    if cookies_file.exists():
        base_command.extend(["--cookies-from-browser", "Chrome"])
    
    base_command.extend([
        "-P", destination,
        "--write-thumbnail",
        "--write-description",
        "--write-info-json"
    ])

    if choice == '1':  # Single video
        base_command.extend(["--remux-video", "mp4"])
        return base_command + ["-f", "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[ext=mp4]", "--no-playlist", url]

    elif choice == '2':  # Single song
        base_command.extend(["-f", "bestaudio", "--extract-audio", "--audio-format", "mp3", "--audio-quality", "0.256", "--no-playlist"])
        return base_command + [url]

    elif choice == '3':  # Playlist videos
        base_command.extend(["--remux-video", "mp4", "--yes-playlist"])
        return base_command + ["-f", "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[ext=mp4]", url]

    elif choice == '4':  # Playlist songs
        base_command.extend(["-f", "bestaudio", "--extract-audio", "--audio-format", "mp3", "--audio-quality", "0.256", "--yes-playlist"])
        return base_command + [url]
    
def monitor_progress(
    process,
    *,
    log_callback: Optional[Callable[[str], None]] = None,
    progress_handler: Optional[Callable[[float], None]] = None,
):
    bar = ProgressBar()
    processing_complete = False

    for line in process.stdout:
        line = line.strip()
        if not line:
            continue

        if log_callback is not None:
            log_callback(line)
        else:
            print(f"STATUS: {line}")  # Debugging to see exact yt-dlp output

        if "%" in line:
            parts = line.split()
            for part in parts:
                if "%" in part:
                    try:
                        percentage = float(part.strip('%'))
                        if progress_handler is not None:
                            progress_handler(percentage)
                        else:
                            bar.update(percentage)
                        break
                    except ValueError:
                        pass

        if "Merging formats into" in line or "Transcoding" in line or "Extracting audio" in line:
            if not processing_complete:
                message = "\nTranscoding, please wait..."
                if log_callback is not None:
                    log_callback(message.strip())
                else:
                    print(message)
                processing_complete = True

        time.sleep(0.1)

    completion_message = "Download completed successfully!"
    if log_callback is not None:
        log_callback(completion_message)
    else:
        print(f"\n{completion_message}")  # Force final message when yt-dlp is done


def run_download(
    choice,
    url,
    destination,
    *,
    cookies_path: Optional[str] = None,
    log_callback: Optional[Callable[[str], None]] = None,
    progress_handler: Optional[Callable[[float], None]] = None,
):
    command = create_command(choice, url, destination)

    if cookies_path:
        command.extend(["--cookies", cookies_path])

    if log_callback is not None:
        log_callback("Starting download...")
    else:
        print("\nStarting download...")

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # Redirect stderr to stdout
        text=True,
        bufsize=1,
        universal_newlines=True
    )

    try:
        monitor_progress(
            process,
            log_callback=log_callback,
            progress_handler=progress_handler,
        )
        process.wait()  # Ensure full completion
    finally:
        if process.stdout is not None:
            process.stdout.close()

    if log_callback is None:
        print("\nIts' Finally Done.")

def main():
    try:
        choice, url, destination = get_user_input()
        run_download(choice, url, destination)

    except subprocess.SubprocessError as e:
        print(f"\nError: {str(e)}")
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nUnexpected error occurred: {str(e)}")
    
    input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()
