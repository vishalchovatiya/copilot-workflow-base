#!/usr/bin/env python3
"""Check (and optionally fix) Markdown structure: section numbering, TOC, and tables.

Three conventions from ``.github/instructions/markdown.instructions.md`` are enforced:

1. **Hierarchical section numbering** — every heading below the document title
   (``##`` and deeper, excluding the ``Table of Contents`` heading) carries a
   sequential dotted number mirroring its position in the hierarchy (``## 1.``,
   ``### 1.1.``, ``#### 1.1.1.``): gap-free, in document order, restarting at ``1``
   under each new parent.
2. **Table of Contents** — the bullet list under an existing ``Table of Contents``
   marker lists every numbered heading as nested bullets with anchor links matching
   each heading's slug, and is regenerated when out of date.
3. **Table alignment** — within every GFM table block the ``|`` delimiters sit at
   identical character positions on every row, so the raw Markdown reads as tidy
   columns.

Numbering and the Table of Contents are applied **only** to documents that already
declare a TOC marker — a ``## Table of Contents`` heading or a bold
``**Table of Contents**`` paragraph; every other file is checked for table alignment
alone, so agent-customization docs (instructions, skills, prompts) are left untouched.
Only heading lines, the TOC list, and table blocks are ever rewritten; prose, code
fences, and ``$…$`` math are left alone, so it is safe to run across the whole repo
(including LaTeX docs).

Usage::

    python .github/scripts/check_markdown.py <files...>        # report; exit 1
    python .github/scripts/check_markdown.py --fix <files...>  # rewrite in place
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

_FENCE = re.compile(r"^\s*(```|~~~)")
_SEP_CELL = re.compile(r"^:?-+:?$")
_HEADING = re.compile(r"^(#{1,6})[ \t]+(.*?)(?:[ \t]+#+)?[ \t]*$")
# A leading section number: either dotted-with-trailing-dot (``1.`` / ``1.1.``) or
# dotted-without-trailing-dot (``1.1`` / ``2.1.3``). A bare integer with no dot at
# all (e.g. a title like ``2024 Roadmap``) is deliberately *not* treated as a number.
_LEADING_NUMBER = re.compile(r"^\d+(?:\.\d+)*\.[ \t]+|^\d+(?:\.\d+)+[ \t]+")

TOC_TITLE = "Table of Contents"
# The TOC marker is written either as a heading (``## Table of Contents``) or, as most
# repo docs do, as a bold/italic paragraph (``**Table of Contents**`` /
# ``***Table of Contents***``). The marker line is preserved verbatim; only the bullet
# list beneath it is regenerated.
_BOLD_TOC = re.compile(
    r"^\s*(?:\*{1,3}|_{1,3})\s*" + re.escape(TOC_TITLE) + r"\s*(?:\*{1,3}|_{1,3})\s*$",
    re.IGNORECASE,
)
_TOC_BULLET = re.compile(r"^\s*[-*+]\s")


def _is_row(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and s.endswith("|") and len(s) > 1


def _cells(row: str) -> list[str]:
    return [c.strip() for c in row.strip()[1:-1].split("|")]


def _is_separator(row: str) -> bool:
    cells = _cells(row)
    return bool(cells) and all(_SEP_CELL.match(c) for c in cells)


def _pipe_positions(row: str) -> list[int]:
    return [i for i, ch in enumerate(row) if ch == "|"]


def _find_tables(lines: list[str]) -> list[tuple[int, int]]:
    """Return (start, end) line indices (inclusive) for each GFM table block."""
    tables: list[tuple[int, int]] = []
    in_fence = False
    i = 0
    while i < len(lines):
        if _FENCE.match(lines[i]):
            in_fence = not in_fence
            i += 1
            continue
        if (
            not in_fence
            and _is_row(lines[i])
            and i + 1 < len(lines)
            and _is_row(lines[i + 1])
            and _is_separator(lines[i + 1])
        ):
            start = i
            i += 2
            while i < len(lines) and _is_row(lines[i]) and not _FENCE.match(lines[i]):
                i += 1
            tables.append((start, i - 1))
            continue
        i += 1
    return tables


def _render(block: list[str]) -> list[str]:
    rows = [_cells(r) for r in block]
    ncols = max(len(r) for r in rows)
    rows = [r + [""] * (ncols - len(r)) for r in rows]
    widths = [3] * ncols
    for ri, row in enumerate(rows):
        if ri == 1:
            continue
        for ci, cell in enumerate(row):
            widths[ci] = max(widths[ci], len(cell))
    out: list[str] = []
    for ri, row in enumerate(rows):
        if ri == 1:
            cells = ["-" * widths[ci] for ci in range(ncols)]
        else:
            cells = [row[ci].ljust(widths[ci]) for ci in range(ncols)]
        out.append("| " + " | ".join(cells) + " |")
    return out


def _aligned(block: list[str]) -> bool:
    positions = [_pipe_positions(r) for r in block]
    return all(p == positions[0] for p in positions) and block == _render(block)


@dataclass
class Heading:
    """A parsed ATX heading, with any leading section number stripped from ``title``."""

    index: int  # 0-based line index in the file
    level: int  # number of leading '#' characters (1..6)
    title: str  # heading text with any leading section number removed
    is_toc: bool  # True for the special, unnumbered 'Table of Contents' heading


def _slug(text: str) -> str:
    """Return the GitHub-style anchor slug for a heading's full (numbered) text."""
    slug = re.sub(r"[^\w\s-]", "", text.strip().lower())
    return slug.replace(" ", "-")


def _strip_number(title: str) -> str:
    """Strip any leading dotted section number from a heading title."""
    return _LEADING_NUMBER.sub("", title, count=1)


def _find_headings(lines: list[str]) -> list[Heading]:
    """Return every ATX heading outside fenced code blocks, in document order."""
    headings: list[Heading] = []
    in_fence = False
    for i, line in enumerate(lines):
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = _HEADING.match(line)
        if not match:
            continue
        level = len(match.group(1))
        title = _strip_number(match.group(2).strip())
        is_toc = level == 2 and title.lower() == TOC_TITLE.lower()
        headings.append(Heading(index=i, level=level, title=title, is_toc=is_toc))
    return headings


def _numbered(headings: list[Heading]) -> list[tuple[Heading, str]]:
    """Pair each numberable heading (``##``+, minus the TOC) with its dotted number."""
    counters = [0, 0, 0, 0, 0]  # one slot per heading level 2..6
    numbered: list[tuple[Heading, str]] = []
    for heading in headings:
        if heading.level < 2 or heading.is_toc:
            continue
        depth = heading.level - 2
        counters[depth] += 1
        for deeper in range(depth + 1, len(counters)):
            counters[deeper] = 0
        number = ".".join(str(counters[d]) for d in range(depth + 1)) + "."
        numbered.append((heading, number))
    return numbered


def _toc_bullets(numbered: list[tuple[Heading, str]]) -> list[str]:
    """Render the nested Table-of-Contents bullet list for the numbered headings."""
    bullets: list[str] = []
    for heading, number in numbered:
        indent = "  " * (heading.level - 2)
        full = f"{number} {heading.title}"
        bullets.append(f"{indent}- [{full}](#{_slug(full)})")
    return bullets


def _find_toc_marker(lines: list[str], headings: list[Heading]) -> int | None:
    """Return the line index of the TOC marker (heading or bold paragraph), if any."""
    toc = next((h for h in headings if h.is_toc), None)
    if toc is not None:
        return toc.index
    in_fence = False
    for i, line in enumerate(lines):
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence and _BOLD_TOC.match(line):
            return i
    return None


def _renumber(
    lines: list[str],
    numbered: list[tuple[Heading, str]],
    *,
    fix: bool,
    path: Path,
) -> tuple[bool, list[str]]:
    """Check/apply section numbering. Return ``(changed, problems)``."""
    changed = False
    problems: list[str] = []
    for heading, number in numbered:
        desired = f"{'#' * heading.level} {number} {heading.title}"
        if lines[heading.index] == desired:
            continue
        if fix:
            lines[heading.index] = desired
            changed = True
        else:
            want = f"{number} {heading.title}"
            problems.append(f"{path}:{heading.index + 1}: heading should read '{want}'")
    return changed, problems


def _sync_toc(
    lines: list[str],
    marker: int,
    numbered: list[tuple[Heading, str]],
    *,
    fix: bool,
    path: Path,
) -> tuple[list[str], bool, list[str]]:
    """Rewrite the bullet list under an existing TOC marker. Return updated state.

    The marker line itself (a ``## Table of Contents`` heading or a bold
    ``**Table of Contents**`` paragraph) is preserved verbatim; only the bullet list
    beneath it is regenerated from ``numbered``.
    """
    bullets = _toc_bullets(numbered)
    # The TOC body is the run of bullets under the marker; span it (plus any
    # surrounding blank lines) and rewrite it canonically, keeping the marker line.
    cursor = marker + 1
    while cursor < len(lines) and not lines[cursor].strip():
        cursor += 1
    while cursor < len(lines) and _TOC_BULLET.match(lines[cursor]):
        cursor += 1
    trailing_blank = cursor < len(lines) and not lines[cursor].strip()
    end = cursor + 1 if trailing_blank else cursor
    region = [lines[marker], "", *bullets, ""]
    if lines[marker:end] == region:
        return lines, False, []
    if fix:
        return lines[:marker] + region + lines[end:], True, []
    return lines, False, [f"{path}:{marker + 1}: Table of Contents is out of date"]


def process(path: Path, *, fix: bool) -> list[str]:
    """Return a list of problems for ``path``; rewrite the file when ``fix`` is set.

    Section numbering and the Table of Contents are enforced only on documents that
    already declare a TOC marker (a ``## Table of Contents`` heading or a bold
    ``**Table of Contents**`` paragraph); other files receive table checking only.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    problems: list[str] = []
    changed = False

    headings = _find_headings(lines)
    marker = _find_toc_marker(lines, headings)
    numbered = _numbered(headings) if marker is not None else []

    if marker is not None and numbered:
        # 1. Section numbering (in place: heading count and indices are preserved).
        num_changed, num_problems = _renumber(lines, numbered, fix=fix, path=path)
        changed = changed or num_changed
        problems.extend(num_problems)

        # 2. Table of Contents (may change the line count; run before table scanning).
        lines, toc_changed, toc_problems = _sync_toc(
            lines, marker, numbered, fix=fix, path=path
        )
        changed = changed or toc_changed
        problems.extend(toc_problems)

    # 3. Table alignment (re-scanned against the possibly-mutated line list).
    for start, end in _find_tables(lines):
        block = lines[start : end + 1]
        if _aligned(block):
            continue
        if fix:
            lines[start : end + 1] = _render(block)
            changed = True
        else:
            problems.append(f"{path}:{start + 1}: misaligned table column pipes")

    if fix and changed:
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check Markdown section numbering, Table of Contents, and tables."
    )
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument(
        "--fix",
        action="store_true",
        help="rewrite headings, TOC, and tables in place",
    )
    args = parser.parse_args(argv)

    problems: list[str] = []
    for path in args.files:
        if path.exists():
            problems.extend(process(path, fix=args.fix))

    if problems and not args.fix:
        sys.stderr.write("\n".join(problems) + "\n")
        sys.stderr.write(
            f"\n{len(problems)} problem(s). "
            "Fix with: python .github/scripts/check_markdown.py --fix <files>\n"
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
