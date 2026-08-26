"""Allow ``python -m deckforge`` when ``scripts/`` is on the path."""

from __future__ import annotations

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
