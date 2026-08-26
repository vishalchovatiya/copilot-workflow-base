"""Tiered rasteriser: turn a ``.pptx`` into one PNG per slide, wherever you are.

Visual verification needs pixels, but the fastest renderer — PowerPoint automation —
exists only on Windows with Office installed. So rendering degrades in tiers and always
reports which one ran:

1. ``powerpoint`` — COM automation via ``comtypes``. Windows + Office only.
2. ``libreoffice`` — ``soffice --headless`` to PDF, then ``pdftoppm`` to PNG. Portable.
3. ``none`` — nothing available. The structural checks in :mod:`deckforge.verify` still
   run, and the caller is told the visual pass was skipped.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

__all__ = ["RenderError", "RenderResult", "available_tiers", "render"]

_SOFFICE_CANDIDATES = (
    "soffice",
    "libreoffice",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
)
_CONVERT_TIMEOUT_S = 300


class RenderError(Exception):
    """Raised when a renderer was available but failed."""


@dataclass
class RenderResult:
    """Outcome of a rasterisation attempt."""

    tier: str
    images: list[Path] = field(default_factory=list)
    pdf: Path | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        """True when at least one slide image was produced."""
        return bool(self.images)


def _find_soffice() -> str | None:
    for candidate in _SOFFICE_CANDIDATES:
        found = shutil.which(candidate) or (candidate if Path(candidate).is_file() else None)
        if found:
            return found
    return None


def _powerpoint_available() -> bool:
    if platform.system() != "Windows":
        return False
    try:
        import comtypes.client  # noqa: F401
    except ImportError:
        return False
    return True


def available_tiers() -> list[str]:
    """Renderer tiers usable on this machine, best first."""
    tiers: list[str] = []
    if _powerpoint_available():
        tiers.append("powerpoint")
    if _find_soffice():
        tiers.append("libreoffice")
    tiers.append("none")
    return tiers


def _run(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=_CONVERT_TIMEOUT_S,
        check=False,
    )


def _render_libreoffice(pptx_path: Path, out_dir: Path, dpi: int) -> RenderResult:
    soffice = _find_soffice()
    if soffice is None:
        raise RenderError("soffice not found")
    with tempfile.TemporaryDirectory(prefix="deckforge-lo-") as profile:
        result = _run(
            [
                soffice,
                f"-env:UserInstallation=file://{Path(profile).as_posix()}",
                "--headless",
                "--norestore",
                "--convert-to",
                "pdf",
                "--outdir",
                str(out_dir),
                str(pptx_path),
            ]
        )
    pdf = out_dir / f"{pptx_path.stem}.pdf"
    if not pdf.is_file():
        raise RenderError(
            f"LibreOffice produced no PDF: {result.stderr.strip() or result.stdout.strip()}"
        )
    if shutil.which("pdftoppm") is None:
        return RenderResult(
            tier="libreoffice",
            pdf=pdf,
            message="pdftoppm not installed — PDF written, no per-slide PNGs",
        )
    _run(["pdftoppm", "-r", str(dpi), "-png", str(pdf), str(out_dir / "slide")])
    images = sorted(out_dir.glob("slide-*.png"))
    return RenderResult(tier="libreoffice", images=images, pdf=pdf, message="")


def _render_powerpoint(pptx_path: Path, out_dir: Path) -> RenderResult:
    import comtypes.client  # local import: Windows-only dependency

    app = comtypes.client.CreateObject("PowerPoint.Application")
    try:
        presentation = app.Presentations.Open(str(pptx_path), True, False, False)
        try:
            presentation.SaveCopyAs(str(out_dir), 18)  # 18 = ppSaveAsPNG
        finally:
            presentation.Close()
    finally:
        app.Quit()
    images = sorted(p for p in out_dir.rglob("*.PNG")) + sorted(out_dir.rglob("*.png"))
    return RenderResult(tier="powerpoint", images=images)


def render(pptx_path: Path, out_dir: Path, *, tier: str = "auto", dpi: int = 110) -> RenderResult:
    """Rasterise every slide of ``pptx_path`` into ``out_dir``.

    Args:
        pptx_path: Deck to render.
        out_dir: Directory for the PNGs; created if absent.
        tier: ``auto`` picks the best available, or force ``powerpoint`` /
            ``libreoffice`` / ``none``.
        dpi: Raster resolution for the LibreOffice path.

    Returns:
        A :class:`RenderResult` naming the tier that actually ran.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    order = [tier] if tier != "auto" else available_tiers()
    problems: list[str] = []
    for candidate in order:
        try:
            if candidate == "powerpoint" and _powerpoint_available():
                return _render_powerpoint(pptx_path, out_dir)
            if candidate == "libreoffice":
                return _render_libreoffice(pptx_path, out_dir, dpi)
        except (RenderError, OSError, subprocess.SubprocessError) as err:
            problems.append(f"{candidate}: {err}")
    return RenderResult(
        tier="none",
        message="; ".join(problems)
        or "no renderer available (install LibreOffice for the portable path)",
    )


if __name__ == "__main__":  # pragma: no cover - manual probe
    print(f"python {sys.version.split()[0]} on {platform.system()}")
    print("tiers:", ", ".join(available_tiers()))
