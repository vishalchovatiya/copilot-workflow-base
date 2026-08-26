#!/usr/bin/env python3
"""Cross-platform launcher for the deckforge CLI.

Keeps the invocation identical on Windows, macOS and Linux::

    python scripts/deck.py build PRESENTATION/specs/my.deck.yaml

without asking anyone to set ``PYTHONPATH`` or install the package.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from deckforge.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
