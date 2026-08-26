"""deckforge — build fully-editable PowerPoint decks from a content spec.

Public API is deliberately small: load a :class:`~deckforge.tokens.Theme`, load a
:class:`~deckforge.spec.DeckSpec`, hand both to :func:`~deckforge.build.build_deck`,
then check the result with :func:`~deckforge.verify.verify`.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0"
