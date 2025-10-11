"""Entry point for launching StreamSaavy interfaces."""
from __future__ import annotations

import argparse
from typing import Optional, Sequence


def main(argv: Optional[Sequence[str]] = None) -> None:
    """Launch the chosen StreamSaavy interface."""

    parser = argparse.ArgumentParser(description="Launcher for StreamSaavy interfaces.")
    parser.add_argument(
        "--ui",
        choices={"tk", "cli", "web"},
        default="tk",
        help="Choose the interface to launch: Tkinter GUI (tk), terminal CLI (cli), or Flask web (web).",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host for the web interface.")
    parser.add_argument("--port", type=int, default=5000, help="Port for the web interface.")
    parser.add_argument("--debug", action="store_true", help="Enable Flask debug mode for the web UI.")

    args, remaining = parser.parse_known_args(argv)

    ui_choice = args.ui

    if ui_choice == "tk":
        if remaining:
            parser.error(f"Unrecognized arguments for tk interface: {' '.join(remaining)}")
        from .ui import run as run_tk

        run_tk()
    elif ui_choice == "cli":
        from .cli import run_cli

        exit_code = run_cli(remaining)
        if exit_code != 0:
            raise SystemExit(exit_code)
    else:  # web
        if remaining:
            parser.error(f"Unrecognized arguments for web interface: {' '.join(remaining)}")
        from .web import run_server

        run_server(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":  # pragma: no cover - script entry
    main()
