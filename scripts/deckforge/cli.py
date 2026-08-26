"""Command line interface. One entry point, identical on every OS.

Run it through the launcher so no ``PYTHONPATH`` juggling is needed::

    python scripts/deck.py --help
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .artifacts import ArtifactError, Library, extract
from .build import BuildError, build_deck, init_template, resolve_template
from .harvest import HarvestError, inspect_package, make_template, report_markdown
from .render import available_tiers, render
from .spec import SpecError, load_spec
from .tokens import ThemeError, available_themes, load_theme
from .verify import verify

__all__ = ["main"]

DEFAULT_OUTPUT_DIR = "PRESENTATION"
"""Where finished decks land when the caller names no directory."""

_EXIT_OK = 0
_EXIT_ERROR = 1
_EXIT_VERIFY_FAILED = 2


def _workspace(args: argparse.Namespace) -> Path:
    return Path(args.workspace).resolve() if args.workspace else Path.cwd()


def _out_root(args: argparse.Namespace) -> Path:
    """Resolve the output directory, defaulting to ``<workspace>/PRESENTATION``."""
    if args.out:
        return Path(args.out).resolve()
    return _workspace(args) / DEFAULT_OUTPUT_DIR


def _search_dirs(args: argparse.Namespace, kind: str) -> list[Path]:
    """Where to look for themes, templates and artifact libraries, in priority order.

    The output root comes first: it is where ``harvest`` and ``init-template`` put what
    they produce, so a deck built with ``--out`` finds its own template.
    """
    root = _workspace(args)
    candidates = [
        _out_root(args) / kind,
        root / DEFAULT_OUTPUT_DIR / kind,
        root / kind,
        root,
    ]
    return list(dict.fromkeys(candidates))


def _theme_for(args: argparse.Namespace):
    return load_theme(args.theme, search=_search_dirs(args, "themes"))


def _library_for(args: argparse.Namespace, spec_value: str = "") -> Library | None:
    value = getattr(args, "artifacts", "") or spec_value
    if not value:
        return None
    for candidate in [Path(value), *(folder / value for folder in _search_dirs(args, "artifacts"))]:
        if candidate.is_dir():
            return Library(candidate)
    raise ArtifactError(f"artifact library {value!r} not found")


def cmd_doctor(args: argparse.Namespace) -> int:
    """Report the toolchain this machine can offer."""
    root = _workspace(args)
    print(f"workspace     : {root}")
    print(f"output default: {_out_root(args)}")
    print(f"python        : {sys.version.split()[0]}")
    print(f"render tiers  : {', '.join(available_tiers())}")
    themes = available_themes(_search_dirs(args, "themes"))
    print(f"themes        : {', '.join(sorted(themes)) or 'none'}")
    for name, path in sorted(themes.items()):
        print(f"                {name:<12} {path}")
    return _EXIT_OK


def cmd_themes(args: argparse.Namespace) -> int:
    """List discoverable themes."""
    for name, path in sorted(available_themes(_search_dirs(args, "themes")).items()):
        print(f"{name:<14} {path}")
    return _EXIT_OK


def cmd_init_template(args: argparse.Namespace) -> int:
    """Generate the neutral base template from theme tokens."""
    theme = _theme_for(args)
    destination = (
        Path(args.output) if args.output else _out_root(args) / "templates" / theme.template
    )
    written = init_template(theme, destination)
    print(f"template written: {written}")
    return _EXIT_OK


def cmd_harvest(args: argparse.Namespace) -> int:
    """Strip a branded deck to a reusable template and report its design system."""
    source = Path(args.source)
    out_dir = Path(args.output) if args.output else _out_root(args) / "templates"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = args.name or f"{source.stem.replace(' ', '_')}-template"
    destination = out_dir / f"{stem}.pptx"
    report = make_template(source, destination)
    markdown = out_dir / f"{stem}-report.md"
    markdown.write_text(report_markdown(report, template_path=destination), encoding="utf-8")
    (out_dir / f"{stem}-report.json").write_text(report.to_json(), encoding="utf-8")
    print(f"template : {destination}")
    print(f"report   : {markdown}")
    print(
        f"found    : {report.layout_count} layouts, {len(report.colors)} theme colours, "
        f"fonts {report.fonts.get('major', '?')}/{report.fonts.get('minor', '?')}, "
        f"{len(report.images)} master/layout images, stripped {report.slide_count} slides"
    )
    print("next     : copy the palette and layout indices into a theme token file")
    return _EXIT_OK


def cmd_inspect(args: argparse.Namespace) -> int:
    """Print a design report for a deck without modifying it."""
    print(report_markdown(inspect_package(Path(args.source))))
    return _EXIT_OK


def cmd_extract(args: argparse.Namespace) -> int:
    """Mine a deck into a versioned artifact library."""
    source = Path(args.source)
    library_dir = (
        Path(args.library)
        if args.library
        else _out_root(args) / "artifacts" / source.stem.replace(" ", "_")
    )
    stats = extract(source, library_dir, include_clusters=not args.no_clusters)
    print(f"library  : {library_dir}")
    print(
        f"artifacts: {stats.artifacts} ({', '.join(f'{k}={v}' for k, v in sorted(stats.by_kind.items()))})"
    )
    print(
        f"mined    : {stats.slides} slides, {stats.tables} tables, {stats.notes_chars} chars of notes"
    )
    print(f"design   : {stats.colors} distinct colours, {stats.fonts} fonts")
    print(f"reuse    : deckforge artifacts --library {library_dir}")
    return _EXIT_OK


def cmd_artifacts(args: argparse.Namespace) -> int:
    """List or search an artifact library."""
    library = Library(Path(args.library))
    entries = library.search(args.search) if args.search else list(library.artifacts.values())
    for artifact in sorted(entries, key=lambda a: (a.kind, a.id)):
        print(artifact.summary())
    print(f"\n{len(entries)} artifact(s) in {library.root}")
    return _EXIT_OK


def cmd_build(args: argparse.Namespace) -> int:
    """Render a spec into a deck, then verify it unless told not to."""
    theme = _theme_for(args)
    spec_path = Path(args.spec)
    spec = load_spec(spec_path, theme, theme_override=args.theme if args.theme_given else "")
    if spec.theme != theme.name:
        theme = load_theme(spec.theme, search=_search_dirs(args, "themes"))
        spec = load_spec(spec_path, theme, theme_override=spec.theme)
    template = (
        Path(args.template)
        if args.template
        else resolve_template(theme, spec, _search_dirs(args, "templates"))
    )
    library = _library_for(args, spec.artifacts)
    out_dir = _out_root(args)
    output = out_dir / f"{args.name or spec_path.stem.replace('.deck', '')}.pptx"
    result = build_deck(spec, theme, output, template=template, library=library)
    print(f"deck     : {result.path}")
    print(f"slides   : {result.slide_count}")
    print(f"theme    : {theme.name} ({theme.source})")
    print(f"template : {template}")
    print(f"manifest : {result.manifest_path()}")
    for warning in result.warnings:
        print(f"warning  : {warning}")
    if args.no_verify:
        return _EXIT_OK
    return _report_verification(
        verify(
            output,
            theme,
            do_render=not args.no_render,
            tier=args.tier,
            image_dir=out_dir / f"{output.stem}_render",
        ),
        as_json=args.json,
    )


def cmd_verify(args: argparse.Namespace) -> int:
    """Check an existing deck."""
    theme = _theme_for(args)
    deck = Path(args.deck)
    report = verify(
        deck,
        theme,
        do_render=not args.no_render,
        tier=args.tier,
        image_dir=Path(args.images) if args.images else None,
    )
    return _report_verification(report, as_json=args.json)


def _report_verification(report, *, as_json: bool) -> int:
    print()
    print(report.to_json() if as_json else report.to_text())
    return _EXIT_OK if report.ok else _EXIT_VERIFY_FAILED


def cmd_render(args: argparse.Namespace) -> int:
    """Rasterise a deck with the best renderer available."""
    deck = Path(args.deck)
    out_dir = Path(args.output) if args.output else deck.with_name(f"{deck.stem}_render")
    result = render(deck, out_dir, tier=args.tier, dpi=args.dpi)
    print(f"tier   : {result.tier}")
    print(f"images : {len(result.images)} in {out_dir}")
    if result.message:
        print(f"note   : {result.message}")
    return _EXIT_OK if result.ok else _EXIT_ERROR


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--workspace", default="", help="workspace root (default: cwd)")
    parser.add_argument(
        "--out",
        default="",
        help=f"output directory (default: <workspace>/{DEFAULT_OUTPUT_DIR})",
    )


def _add_theme(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--theme", default="neutral", help="theme name or token file path")


def build_parser() -> argparse.ArgumentParser:
    """Assemble the argument parser."""
    parser = argparse.ArgumentParser(
        prog="deckforge",
        description="Build fully-editable PowerPoint decks from a content spec.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="report the available toolchain")
    _add_common(doctor)
    doctor.set_defaults(func=cmd_doctor)

    themes = subparsers.add_parser("themes", help="list discoverable themes")
    _add_common(themes)
    themes.set_defaults(func=cmd_themes)

    init = subparsers.add_parser("init-template", help="generate the neutral base template")
    _add_common(init)
    _add_theme(init)
    init.add_argument("--output", default="", help="destination .pptx")
    init.set_defaults(func=cmd_init_template)

    harvest = subparsers.add_parser("harvest", help="strip a branded deck into a template")
    _add_common(harvest)
    harvest.add_argument("source", help="source .pptx")
    harvest.add_argument("--output", default="", help="destination directory")
    harvest.add_argument("--name", default="", help="template file stem")
    harvest.set_defaults(func=cmd_harvest)

    inspect = subparsers.add_parser("inspect", help="print a design report for a deck")
    _add_common(inspect)
    inspect.add_argument("source", help="source .pptx")
    inspect.set_defaults(func=cmd_inspect)

    extract_cmd = subparsers.add_parser("extract", help="mine a deck into an artifact library")
    _add_common(extract_cmd)
    extract_cmd.add_argument("source", help="source .pptx")
    extract_cmd.add_argument("--library", default="", help="library directory")
    extract_cmd.add_argument(
        "--no-clusters",
        action="store_true",
        help="capture only explicit groups, tables and SmartArt",
    )
    extract_cmd.set_defaults(func=cmd_extract)

    artifacts = subparsers.add_parser("artifacts", help="list or search an artifact library")
    _add_common(artifacts)
    artifacts.add_argument("--library", required=True, help="library directory")
    artifacts.add_argument("--search", default="", help="filter by id, title or text")
    artifacts.set_defaults(func=cmd_artifacts)

    build = subparsers.add_parser("build", help="render a spec into a deck and verify it")
    _add_common(build)
    _add_theme(build)
    build.add_argument("spec", help="deck spec .yaml")
    build.add_argument("--template", default="", help="base .pptx to build on")
    build.add_argument("--artifacts", default="", help="artifact library directory")
    build.add_argument("--name", default="", help="output file stem")
    build.add_argument(
        "--tier", default="auto", choices=("auto", "powerpoint", "libreoffice", "none")
    )
    build.add_argument("--no-render", action="store_true", help="skip the visual pass")
    build.add_argument("--no-verify", action="store_true", help="skip verification entirely")
    build.add_argument("--json", action="store_true", help="emit the verification report as JSON")
    build.set_defaults(func=cmd_build)

    verify_cmd = subparsers.add_parser("verify", help="check an existing deck")
    _add_common(verify_cmd)
    _add_theme(verify_cmd)
    verify_cmd.add_argument("deck", help="deck .pptx")
    verify_cmd.add_argument("--images", default="", help="directory for rendered slides")
    verify_cmd.add_argument(
        "--tier", default="auto", choices=("auto", "powerpoint", "libreoffice", "none")
    )
    verify_cmd.add_argument("--no-render", action="store_true", help="skip the visual pass")
    verify_cmd.add_argument("--json", action="store_true", help="emit JSON")
    verify_cmd.set_defaults(func=cmd_verify)

    render_cmd = subparsers.add_parser("render", help="rasterise a deck to PNG")
    _add_common(render_cmd)
    render_cmd.add_argument("deck", help="deck .pptx")
    render_cmd.add_argument("--output", default="", help="directory for the PNGs")
    render_cmd.add_argument(
        "--tier", default="auto", choices=("auto", "powerpoint", "libreoffice", "none")
    )
    render_cmd.add_argument("--dpi", type=int, default=110)
    render_cmd.set_defaults(func=cmd_render)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI. Returns the process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    args.theme_given = any(
        a == "--theme" or a.startswith("--theme=") for a in (argv or sys.argv[1:])
    )
    try:
        return int(args.func(args))
    except (ArtifactError, BuildError, HarvestError, SpecError, ThemeError) as err:
        print(f"error: {err}", file=sys.stderr)
        return _EXIT_ERROR
    except FileNotFoundError as err:
        print(f"error: file not found: {err.filename}", file=sys.stderr)
        return _EXIT_ERROR
