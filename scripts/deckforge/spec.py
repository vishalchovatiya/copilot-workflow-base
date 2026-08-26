"""The deck specification: narrative content, and nothing else.

The format is YAML rather than Markdown for two reasons. First, this repository's own
`scripts/check_markdown.py` rewrites headings, regenerates a table of contents and
re-aligns tables in every ``.md`` file it is pointed at — a Markdown deck spec would be
silently restructured by the repo's own tooling. Second, archetype payloads are nested
data (panel pairs, chevron steps, table rows); expressing them in Markdown means
inventing a mini-syntax, whereas in YAML they are validated against a schema, which is
what turns "no styling in the spec" from a convention into an enforced rule.

Prose still reads as prose: every long field is a block scalar.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .tokens import Budget, Theme

__all__ = [
    "ARCHETYPES",
    "DeckSpec",
    "SectionSpec",
    "SlideSpec",
    "SpecError",
    "Unknown",
    "load_spec",
]

# Styling belongs to the theme. Any of these keys in a spec is a hard error, because a
# spec that carries styling cannot be re-rendered on-brand against a second theme.
_STYLE_KEYS = frozenset(
    {
        "color",
        "colour",
        "fill",
        "font",
        "fontsize",
        "font_size",
        "size",
        "bold",
        "italic",
        "rgb",
        "hex",
        "left",
        "top",
        "width",
        "height",
        "x",
        "y",
        "margin",
        "padding",
        "align",
        "style",
        "css",
    }
)
_UNKNOWN_TOKENS = ("TBC", "TBD", "???")


@dataclass(frozen=True)
class ArchetypeSpec:
    """What one slide archetype accepts, and how much of it."""

    name: str
    required: tuple[str, ...] = ()
    optional: tuple[str, ...] = ()
    list_key: str = ""
    min_items: int = 0
    max_items: int = 0
    needs_takeaway: bool = True
    purpose: str = ""


ARCHETYPES: dict[str, ArchetypeSpec] = {
    a.name: a
    for a in (
        ArchetypeSpec(
            "title",
            optional=("subtitle", "presenter", "date"),
            needs_takeaway=False,
            purpose="Slide 1 only.",
        ),
        ArchetypeSpec(
            "agenda",
            optional=("items",),
            needs_takeaway=False,
            purpose="Generated from the section list; shows the whole arc.",
        ),
        ArchetypeSpec(
            "section",
            optional=("question",),
            needs_takeaway=False,
            purpose="Divider showing progress through the agenda.",
        ),
        ArchetypeSpec(
            "bullets",
            ("bullets",),
            ("lead",),
            "bullets",
            1,
            6,
            purpose="An argument or a list. The default content slide.",
        ),
        ArchetypeSpec(
            "cards", ("cards",), (), "cards", 2, 5, purpose="Principles, the ask, parallel options."
        ),
        ArchetypeSpec(
            "process",
            ("steps",),
            ("bullets",),
            "steps",
            2,
            5,
            purpose="Any left-to-right flow. Rebuilt from autoshapes.",
        ),
        ArchetypeSpec(
            "panels",
            ("panels",),
            (),
            "panels",
            2,
            2,
            purpose="A versus B; blockers versus enablers.",
        ),
        ArchetypeSpec("checklist", ("do", "dont"), (), purpose="Do and do-not, review gates."),
        ArchetypeSpec(
            "table",
            ("columns", "rows"),
            ("legend",),
            "rows",
            1,
            10,
            purpose="Comparison, rubric, owners and actions.",
        ),
        ArchetypeSpec(
            "artifact",
            ("artifact",),
            ("text", "caption", "bullets"),
            purpose="Re-place a harvested diagram, table or SmartArt.",
        ),
        ArchetypeSpec(
            "statement",
            ("statement",),
            (),
            needs_takeaway=False,
            purpose="One full-bleed line. Closing only.",
        ),
        ArchetypeSpec(
            "summary",
            ("nodes",),
            ("flow",),
            "nodes",
            3,
            6,
            purpose="The mandatory closing picture of the whole argument.",
        ),
    )
}


class SpecError(Exception):
    """Raised when a deck spec is malformed, over budget or carries styling."""


@dataclass(frozen=True)
class Unknown:
    """A fact the deck does not know, with the person who will supply it."""

    item: str
    owner: str
    deliverable: str

    def label(self) -> str:
        """One-line rendering for the slide."""
        return f"{self.item}: TBC — Owner: {self.owner} — Deliverable: {self.deliverable}"


@dataclass
class SlideSpec:
    """One slide's content."""

    archetype: str
    title: str
    notes: str
    takeaway: str = ""
    entity: str = ""
    content: dict[str, Any] = field(default_factory=dict)
    unknowns: list[Unknown] = field(default_factory=list)
    section: str = ""
    section_index: int = 0

    def items(self) -> list[Any]:
        """The archetype's variable-length payload, whatever it is called."""
        key = ARCHETYPES[self.archetype].list_key
        return list(self.content.get(key, [])) if key else []


@dataclass
class SectionSpec:
    """A named part of the deck's argument."""

    name: str
    question: str = ""
    slides: list[SlideSpec] = field(default_factory=list)


@dataclass
class DeckSpec:
    """A whole deck as narrative content."""

    title: str
    subtitle: str
    theme: str
    source: Path
    template: str = ""
    artifacts: str = ""
    presenter: str = ""
    date: str = ""
    agenda: bool = True
    entities: dict[str, str] = field(default_factory=dict)
    sections: list[SectionSpec] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def slides(self) -> Iterable[SlideSpec]:
        """Every slide in narrative order."""
        for section in self.sections:
            yield from section.slides

    @property
    def slide_count(self) -> int:
        """Number of authored slides, before generated agenda and dividers."""
        return sum(len(section.slides) for section in self.sections)


def _reject_styling(node: Any, path: str) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if str(key).lower() in _STYLE_KEYS:
                raise SpecError(
                    f"{path}.{key}: styling does not belong in a spec — it lives in the "
                    "theme token file, so the same spec can render on-brand twice"
                )
            _reject_styling(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            _reject_styling(value, f"{path}[{index}]")


def _parse_unknowns(raw: Any, where: str) -> list[Unknown]:
    unknowns: list[Unknown] = []
    for entry in raw or []:
        missing = [k for k in ("item", "owner", "deliverable") if not entry.get(k)]
        if missing:
            raise SpecError(
                f"{where}: unknown entry is missing {', '.join(missing)} — an unknown is "
                "only allowed on a slide when it names an owner and a deliverable"
            )
        unknowns.append(Unknown(entry["item"], entry["owner"], entry["deliverable"]))
    return unknowns


def _check_budget(slide: SlideSpec, budget: Budget, warnings: list[str]) -> None:
    """Apply the hard content budget, routing overflow into notes or failing loudly."""
    where = f"slide {slide.title!r}"
    if len(slide.title) > budget.max_title_chars:
        raise SpecError(
            f"{where}: title is {len(slide.title)} characters, budget is "
            f"{budget.max_title_chars} — shorten the title, do not shrink the type"
        )
    if slide.takeaway and len(slide.takeaway.split()) > budget.max_takeaway_words:
        raise SpecError(
            f"{where}: takeaway is {len(slide.takeaway.split())} words, budget is "
            f"{budget.max_takeaway_words}"
        )
    bullets = slide.content.get("bullets")
    if not isinstance(bullets, list):
        return
    overflow = bullets[budget.max_bullets :]
    if overflow:
        if budget.overflow == "fail":
            raise SpecError(f"{where}: {len(bullets)} bullets, budget is {budget.max_bullets}")
        slide.content["bullets"] = bullets[: budget.max_bullets]
        slide.notes = f"{slide.notes.rstrip()}\n\nNot on the slide: " + " ".join(
            f"{item}." for item in overflow
        )
        warnings.append(
            f"{where}: {len(overflow)} bullet(s) over budget routed into the speaker notes"
        )
    for bullet in slide.content["bullets"]:
        words = len(str(bullet).split())
        if words > budget.max_words_per_bullet:
            raise SpecError(
                f"{where}: bullet has {words} words, budget is "
                f"{budget.max_words_per_bullet}: {bullet!r}"
            )


def _check_archetype(slide: SlideSpec) -> None:
    spec = ARCHETYPES.get(slide.archetype)
    if spec is None:
        raise SpecError(
            f"unknown archetype {slide.archetype!r}; choose one of "
            f"{', '.join(sorted(ARCHETYPES))}"
        )
    where = f"slide {slide.title!r} ({slide.archetype})"
    missing = [key for key in spec.required if key not in slide.content]
    if missing:
        raise SpecError(f"{where}: content is missing {', '.join(missing)}")
    allowed = set(spec.required) | set(spec.optional)
    extra = set(slide.content) - allowed
    if extra:
        raise SpecError(
            f"{where}: unsupported content key(s) {', '.join(sorted(extra))}; "
            f"this archetype accepts {', '.join(sorted(allowed)) or 'nothing'}"
        )
    if spec.list_key and spec.max_items:
        count = len(slide.content.get(spec.list_key, []))
        if not spec.min_items <= count <= spec.max_items:
            raise SpecError(
                f"{where}: {spec.list_key} has {count} entries, allowed range is "
                f"{spec.min_items}-{spec.max_items}"
            )
    if slide.archetype == "table":
        width = len(slide.content["columns"])
        for number, row in enumerate(slide.content["rows"], start=1):
            if len(row) != width:
                raise SpecError(
                    f"{where}: row {number} has {len(row)} cells but there are {width} "
                    f"columns — quote any cell containing a comma: {row!r}"
                )


def _check_narrative(slide: SlideSpec, theme: Theme) -> None:
    spec = ARCHETYPES[slide.archetype]
    where = f"slide {slide.title!r}"
    if spec.needs_takeaway and not slide.takeaway:
        raise SpecError(
            f"{where}: every content slide needs one takeaway — the slide-level "
            "equivalent of a Bottom line"
        )
    if len(slide.notes.strip()) < theme.budget.min_notes_chars:
        raise SpecError(
            f"{where}: speaker notes are {len(slide.notes.strip())} characters, minimum "
            f"is {theme.budget.min_notes_chars} — the argument lives in the notes"
        )
    text = " ".join(
        [slide.title, slide.takeaway, yaml.safe_dump(slide.content, allow_unicode=True)]
    )
    if any(token in text for token in _UNKNOWN_TOKENS) and not slide.unknowns:
        raise SpecError(
            f"{where}: an unknown is marked in the content but the slide declares no "
            "`unknowns:` entry with an owner and a deliverable"
        )


def _check_entity(slide: SlideSpec, entities: dict[str, str]) -> None:
    if slide.entity and slide.entity not in entities:
        raise SpecError(
            f"slide {slide.title!r}: entity {slide.entity!r} is not declared in the "
            "deck's `entities:` map, so its colour would not be consistent"
        )


def load_spec(path: Path, theme: Theme, *, theme_override: str = "") -> DeckSpec:
    """Load, validate and budget-check a deck spec.

    Args:
        path: The ``.deck.yaml`` file.
        theme: Theme supplying the budget and the legal entity colour roles.
        theme_override: Theme name that wins over the spec's own ``theme:`` field.

    Returns:
        A validated :class:`DeckSpec`; ``spec.warnings`` records overflow that was
        routed into speaker notes.

    Raises:
        SpecError: On any schema, budget, narrative or styling violation.
    """
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise SpecError(f"{path}: spec must be a mapping")
    _reject_styling(raw, "spec")

    deck_meta = raw.get("deck") or {}
    entities = dict(raw.get("entities") or {})
    for name, role in entities.items():
        if role not in theme.entity_roles:
            raise SpecError(
                f"entity {name!r} asks for role {role!r}; theme {theme.name!r} offers "
                f"{', '.join(theme.entity_roles)}"
            )

    spec = DeckSpec(
        title=str(deck_meta.get("title", path.stem)),
        subtitle=str(deck_meta.get("subtitle", "")),
        theme=theme_override or str(deck_meta.get("theme", theme.name)),
        source=path,
        template=str(deck_meta.get("template", "")),
        artifacts=str(deck_meta.get("artifacts", "")),
        presenter=str(deck_meta.get("presenter", "")),
        date=str(deck_meta.get("date", "")),
        agenda=bool(deck_meta.get("agenda", True)),
        entities=entities,
    )

    for index, raw_section in enumerate(raw.get("sections") or [], start=1):
        section = SectionSpec(
            name=str(raw_section.get("name", f"Section {index}")),
            question=str(raw_section.get("question", "")),
        )
        for raw_slide in raw_section.get("slides") or []:
            slide = SlideSpec(
                archetype=str(raw_slide.get("archetype", "bullets")),
                title=str(raw_slide.get("title", "")),
                notes=str(raw_slide.get("notes", "")),
                takeaway=str(raw_slide.get("takeaway", "")),
                entity=str(raw_slide.get("entity", "")),
                content=dict(raw_slide.get("content") or {}),
                unknowns=_parse_unknowns(
                    raw_slide.get("unknowns"), f"slide {raw_slide.get('title')!r}"
                ),
                section=section.name,
                section_index=index,
            )
            _check_archetype(slide)
            _check_entity(slide, entities)
            _check_budget(slide, theme.budget, spec.warnings)
            _check_narrative(slide, theme)
            section.slides.append(slide)
        spec.sections.append(section)

    if not spec.sections:
        raise SpecError(f"{path}: a deck needs at least one section")
    closing = list(spec.slides())[-1].archetype if spec.slide_count else ""
    if closing not in {"summary", "statement"}:
        spec.warnings.append(
            "the deck does not close with a `summary` or `statement` slide — the arc "
            "should end with one picture of the whole argument"
        )
    return spec
