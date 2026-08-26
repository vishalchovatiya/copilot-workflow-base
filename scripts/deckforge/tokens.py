"""Design tokens: the single source of every colour, coordinate and type size.

Nothing else in the package may contain a hex literal or an inch literal. A theme is
one human-editable YAML file; adding a corporate look is a matter of dropping a second
file next to the default one and pointing a spec at it by name.

This module deliberately imports no ``pptx`` symbol so tokens stay a pure data layer
that the verifier can consult without opening a presentation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

__all__ = [
    "Budget",
    "Canvas",
    "Grid",
    "Layout",
    "Spacing",
    "Theme",
    "ThemeError",
    "TypeStep",
    "Typography",
    "available_themes",
    "hex_to_rgb",
    "load_theme",
    "mix",
    "rgb_to_hex",
    "theme_search_paths",
]

PACKAGE_THEMES = Path(__file__).resolve().parent / "themes"
"""Themes shipped with the package; always the last place searched."""


class ThemeError(Exception):
    """Raised when a theme token file is missing, malformed or incomplete."""


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    """Convert ``#RRGGBB`` (or ``RRGGBB``) to an ``(r, g, b)`` tuple."""
    raw = value.lstrip("#").strip()
    if len(raw) != 6:
        raise ThemeError(f"colour {value!r} is not a 6-digit hex value")
    try:
        return tuple(int(raw[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    except ValueError as err:
        raise ThemeError(f"colour {value!r} is not valid hex") from err


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    """Convert an ``(r, g, b)`` tuple to an uppercase ``RRGGBB`` string."""
    return "{:02X}{:02X}{:02X}".format(*rgb)


def mix(value: str, *, toward: str = "FFFFFF", amount: float = 0.86) -> str:
    """Blend a colour toward another one.

    Args:
        value: Source colour as hex.
        toward: Colour to blend toward; white produces a tint, the ink colour a shade.
        amount: ``0.0`` keeps the source, ``1.0`` returns ``toward``.

    Returns:
        The blended colour as an uppercase ``RRGGBB`` string.
    """
    src = hex_to_rgb(value)
    dst = hex_to_rgb(toward)
    blended = tuple(round(s + (d - s) * amount) for s, d in zip(src, dst))
    return rgb_to_hex(blended)  # type: ignore[arg-type]


@dataclass(frozen=True)
class Canvas:
    """Slide surface in inches."""

    width_in: float
    height_in: float


@dataclass(frozen=True)
class Grid:
    """The one alignment grid. Every element derives its position from these."""

    margin_left_in: float
    margin_right_in: float
    title_top_in: float
    title_height_in: float
    title_right_guard_in: float
    accent_top_in: float
    accent_width_in: float
    accent_height_in: float
    body_top_in: float
    body_bottom_in: float
    footer_top_in: float
    footer_height_in: float
    logo_guard_in: float

    def content_width(self, canvas: Canvas) -> float:
        """Usable width between the two margins."""
        return canvas.width_in - self.margin_left_in - self.margin_right_in

    def title_width(self, canvas: Canvas) -> float:
        """Title width, stopped short of the master logo."""
        return self.content_width(canvas) - self.title_right_guard_in

    @property
    def body_height(self) -> float:
        """Usable height between the content top and bottom rules."""
        return self.body_bottom_in - self.body_top_in


@dataclass(frozen=True)
class Spacing:
    """Gutters, padding and fixed element heights, all in inches."""

    card_gap_in: float
    panel_gap_in: float
    row_gap_in: float
    card_pad_in: float
    chevron_overlap_in: float
    chevron_text_inset_in: float
    table_margin_h_in: float
    table_margin_v_in: float
    table_row_min_in: float
    bullet_indent_in: float
    sub_indent_in: float
    callout_height_in: float
    accent_edge_in: float
    hairline_pt: float


@dataclass(frozen=True)
class Layout:
    """Archetype geometry: block sizes and where a block sits in the body band."""

    block_bias: float
    block_fill: float
    card_min_height_in: float
    card_max_height_in: float
    card_round_adjust: float
    node_min_height_in: float
    head_gap_in: float
    lead_gap_in: float
    chevron_height_in: float
    chevron_adjust: float
    caption_gap_in: float
    caption_height_in: float
    connector_gap_in: float
    legend_gap_in: float
    legend_height_in: float
    table_max_height_in: float
    hero_top_in: float
    hero_height_in: float
    hero_width_ratio: float
    hero_rule_gap_in: float
    hero_rule_width_in: float
    hero_sub_gap_in: float
    numeral_width_in: float
    numeral_height_in: float
    numeral_gap_in: float
    progress_height_in: float
    progress_label_gap_in: float
    statement_width_ratio: float
    artifact_split_ratio: float
    artifact_wide_ratio: float
    hub_width_in: float
    hub_height_in: float
    spoke_height_in: float


@dataclass(frozen=True)
class TypeStep:
    """One rung of the type scale."""

    size_pt: float
    line: float
    font: str
    bold: bool = False
    caps: bool = False
    space_after_pt: float = 0.0


@dataclass(frozen=True)
class Typography:
    """Font families plus the fixed type scale."""

    fonts: dict[str, str]
    scale: dict[str, TypeStep]
    title_steps: tuple[tuple[int, float], ...]
    char_width_ratio: float

    def step(self, name: str) -> TypeStep:
        """Return one rung of the scale by name."""
        try:
            return self.scale[name]
        except KeyError as err:
            raise ThemeError(f"unknown type step {name!r}") from err

    def title_size(self, text: str) -> float:
        """Pick a title size that keeps ``text`` on one line.

        Titles step down by measured length instead of wrapping, because a wrapped
        title pushes out of the title band and clips against the slide edge.
        """
        length = len(text)
        for limit, size in self.title_steps:
            if length <= limit:
                return size
        return self.title_steps[-1][1]


@dataclass(frozen=True)
class Budget:
    """Hard content limits. The builder enforces these; it never shrinks type."""

    max_bullets: int
    max_words_per_bullet: int
    max_title_chars: int
    max_takeaway_words: int
    min_notes_chars: int
    max_notes_chars: int
    overflow: str  # "notes" routes surplus into speaker notes; "fail" raises

    def __post_init__(self) -> None:
        if self.overflow not in {"notes", "fail"}:
            raise ThemeError("budget.overflow must be 'notes' or 'fail'")


@dataclass(frozen=True)
class Theme:
    """A complete, resolved design system."""

    name: str
    description: str
    source: Path
    palette: dict[str, str]
    roles: dict[str, str]
    entity_roles: tuple[str, ...]
    tints: dict[str, float]
    canvas: Canvas
    grid: Grid
    spacing: Spacing
    layout: Layout
    typography: Typography
    budget: Budget
    template: str
    layouts: dict[str, int]
    chrome: dict[str, Any] = field(default_factory=dict)

    def color(self, name: str) -> str:
        """Resolve a palette key or a semantic role to a hex string.

        Args:
            name: Either a palette key (``primary``) or a role (``body_text``).

        Returns:
            Hex colour without the leading ``#``.
        """
        key = self.roles.get(name, name)
        try:
            return self.palette[key].lstrip("#").upper()
        except KeyError as err:
            raise ThemeError(f"unknown colour or role {name!r}") from err

    def tint(self, name: str, level: str = "panel") -> str:
        """Blend a palette colour toward the surface colour by a named tint level."""
        try:
            amount = self.tints[level]
        except KeyError as err:
            raise ThemeError(f"unknown tint level {level!r}") from err
        return mix(self.color(name), toward=self.color("surface"), amount=amount)

    def layout_index(self, name: str) -> int:
        """Return the slide-layout index registered under a role name."""
        if name in self.layouts:
            return self.layouts[name]
        return self.layouts["content"]

    @property
    def content_width(self) -> float:
        """Usable content width in inches."""
        return self.grid.content_width(self.canvas)

    @property
    def title_width(self) -> float:
        """Title width in inches, clear of the master logo."""
        return self.grid.title_width(self.canvas)


def _require(data: dict[str, Any], key: str, source: Path) -> Any:
    if key not in data:
        raise ThemeError(f"{source}: missing required section '{key}'")
    return data[key]


def _type_step(name: str, raw: dict[str, Any], fonts: dict[str, str]) -> TypeStep:
    font_key = raw.get("font", "body")
    if font_key not in fonts:
        raise ThemeError(f"type step {name!r} references unknown font {font_key!r}")
    return TypeStep(
        size_pt=float(raw["size_pt"]),
        line=float(raw.get("line", 1.0)),
        font=font_key,
        bold=bool(raw.get("bold", False)),
        caps=bool(raw.get("caps", False)),
        space_after_pt=float(raw.get("space_after_pt", 0.0)),
    )


def load_theme(name_or_path: str | Path, *, search: list[Path] | None = None) -> Theme:
    """Load a theme by name or path.

    Args:
        name_or_path: A theme name (``neutral``) resolved against the search path, or
            a direct path to a ``.yaml`` token file.
        search: Extra directories to search before the packaged themes.

    Returns:
        The resolved :class:`Theme`.

    Raises:
        ThemeError: If the file cannot be found or a required section is missing.
    """
    path = _resolve_theme_path(name_or_path, search)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ThemeError(f"{path}: theme file must be a mapping")

    palette = {k: str(v).lstrip("#").upper() for k, v in _require(data, "palette", path).items()}
    for value in palette.values():
        hex_to_rgb(value)  # validate early so a bad hex fails at load, not at draw time

    typography_raw = _require(data, "typography", path)
    fonts = dict(typography_raw["fonts"])
    scale = {name: _type_step(name, raw, fonts) for name, raw in typography_raw["scale"].items()}
    title_steps = tuple((int(limit), float(size)) for limit, size in typography_raw["title_steps"])

    canvas = Canvas(**_require(data, "canvas", path))
    grid = Grid(**_require(data, "grid", path))
    spacing = Spacing(**_require(data, "spacing", path))
    layout = Layout(**_require(data, "layout", path))
    budget = Budget(**_require(data, "budget", path))

    return Theme(
        name=str(data.get("name", path.stem)),
        description=str(data.get("description", "")),
        source=path,
        palette=palette,
        roles=dict(_require(data, "roles", path)),
        entity_roles=tuple(data.get("entity_roles", ())),
        tints={k: float(v) for k, v in _require(data, "tints", path).items()},
        canvas=canvas,
        grid=grid,
        spacing=spacing,
        layout=layout,
        typography=Typography(
            fonts=fonts,
            scale=scale,
            title_steps=title_steps,
            char_width_ratio=float(typography_raw.get("char_width_ratio", 0.0072)),
        ),
        budget=budget,
        template=str(data.get("template", "")),
        layouts={k: int(v) for k, v in data.get("layouts", {"content": 0}).items()},
        chrome=dict(data.get("chrome", {})),
    )


def theme_search_paths(extra: list[Path] | None = None) -> list[Path]:
    """Directories searched for theme files, in priority order."""
    paths = list(extra or [])
    paths.append(Path.cwd() / "PRESENTATION" / "themes")
    paths.append(Path.cwd() / "themes")
    paths.append(PACKAGE_THEMES)
    return paths


def available_themes(extra: list[Path] | None = None) -> dict[str, Path]:
    """Map every discoverable theme name to its token file."""
    found: dict[str, Path] = {}
    for directory in theme_search_paths(extra):
        if not directory.is_dir():
            continue
        for candidate in sorted(directory.glob("*.yaml")):
            found.setdefault(candidate.stem, candidate)
    return found


def _resolve_theme_path(name_or_path: str | Path, search: list[Path] | None) -> Path:
    direct = Path(name_or_path)
    if direct.suffix in {".yaml", ".yml"}:
        if direct.is_file():
            return direct
        raise ThemeError(f"theme file not found: {direct}")
    for directory in theme_search_paths(search):
        candidate = directory / f"{direct}.yaml"
        if candidate.is_file():
            return candidate
    known = ", ".join(sorted(available_themes(search))) or "none"
    raise ThemeError(f"theme {name_or_path!r} not found (available: {known})")
