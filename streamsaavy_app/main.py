"""Entry point for launching the StreamSaavy UI."""
from __future__ import annotations

from .ui import run


def main() -> None:
    """Launch the Tkinter interface."""
    run()


if __name__ == "__main__":  # pragma: no cover - script entry
    main()
