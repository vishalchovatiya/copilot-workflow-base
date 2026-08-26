"""Text metrics without a font engine.

The builder must decide *before* rendering whether a title fits on one line and
whether a bullet block fits inside its card. Shipping a font rasteriser for that is
disproportionate, so width is estimated from an average advance ratio calibrated per
theme (``typography.char_width_ratio``). Estimates run ~5% wide on purpose: erring
toward "too big" makes the builder step down or reflow rather than clip.
"""

from __future__ import annotations

from .tokens import Typography

__all__ = ["fits_one_line", "line_count", "text_height_in", "text_width_in", "wrap_lines"]

_BOLD_WIDENING = 1.05
_CAPS_WIDENING = 1.12


def text_width_in(
    text: str,
    *,
    size_pt: float,
    typography: Typography,
    bold: bool = False,
    caps: bool = False,
) -> float:
    """Estimated rendered width of a single line, in inches."""
    ratio = typography.char_width_ratio
    if bold:
        ratio *= _BOLD_WIDENING
    if caps:
        ratio *= _CAPS_WIDENING
    return len(text) * size_pt * ratio


def wrap_lines(
    text: str,
    *,
    width_in: float,
    size_pt: float,
    typography: Typography,
    bold: bool = False,
    caps: bool = False,
) -> list[str]:
    """Greedily wrap ``text`` to ``width_in``, mirroring PowerPoint's word wrap."""
    if width_in <= 0:
        return [text]
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        wide = text_width_in(
            candidate, size_pt=size_pt, typography=typography, bold=bold, caps=caps
        )
        if current and wide > width_in:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [""]


def line_count(text: str, **kwargs) -> int:
    """Number of rendered lines ``text`` occupies at the given width."""
    return len(wrap_lines(text, **kwargs))


def text_height_in(lines: int, *, size_pt: float, line: float) -> float:
    """Height of ``lines`` lines of type, in inches."""
    return lines * size_pt * line / 72.0


def fits_one_line(text: str, *, width_in: float, **kwargs) -> bool:
    """True when ``text`` renders on a single line at the given width."""
    return line_count(text, width_in=width_in, **kwargs) <= 1
