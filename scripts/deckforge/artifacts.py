"""Artifact library: mine an existing deck for reusable material, then re-place it.

This is what makes consecutive decks look like one family. A harvested template gives
you the *chrome* — master, layouts, fonts, logo. It gives you nothing of the *design
work*: the diagram someone spent an afternoon aligning, the comparison table, the
SmartArt process chain. Those live on slides, and slides are exactly what the template
harvester throws away.

So they are extracted first, into a versioned library on disk, and re-placed later:
text retargeted to the new deck's content, colours retargeted to the active theme, and
geometry retargeted to the grid. Nothing is rasterised at any point — an artifact is
stored as the original DrawingML and comes back as native, editable shapes.
"""

from __future__ import annotations

import colorsys
import json
import re
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lxml import etree
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.opc.package import Part
from pptx.opc.packuri import PackURI
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches

from .harvest import hydrated
from .primitives import Box, name_shape
from .tokens import Theme, hex_to_rgb, mix

__all__ = [
    "Artifact",
    "ArtifactError",
    "Library",
    "LibraryStats",
    "extract",
]

LIBRARY_VERSION = 1
_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
_DGM_URI = "http://schemas.openxmlformats.org/drawingml/2006/diagram"
_DGM = f"{{{_DGM_URI}}}"
_CHART_URI = "http://schemas.openxmlformats.org/drawingml/2006/chart"
_TABLE_URI = "http://schemas.openxmlformats.org/drawingml/2006/table"
_R_ATTRS = ("embed", "link", "id", "dm", "lo", "qs", "cs")
_CLUSTER_GAP_IN = 0.18
_CLUSTER_MIN_SHAPES = 3
_CLUSTER_MAX_COVERAGE = 0.80
_NEUTRAL_SATURATION = 0.20
_INK_LIGHTNESS = 0.25
# Chrome this package draws on every slide. Re-mining a deck it generated should yield
# the design work, not the accent bar and the page number.
_CHROME_NAMES = frozenset(
    {
        "df:accent",
        "df:kicker",
        "df:pagenum",
        "df:takeaway",
        "df:unknowns",
        "df:band:takeaway",
        "df:label:takeaway",
    }
)


class ArtifactError(Exception):
    """Raised when an artifact cannot be extracted or placed."""


@dataclass
class TextSlot:
    """One retargetable piece of text inside an artifact."""

    index: int
    text: str
    chars: int


@dataclass
class Artifact:
    """One reusable design element, addressable by id."""

    id: str
    kind: str  # group | cluster | table | smartart | chart
    source: str
    slide: int
    title: str
    left_in: float
    top_in: float
    width_in: float
    height_in: float
    shape_count: int
    slots: list[TextSlot] = field(default_factory=list)
    colors: list[str] = field(default_factory=list)
    fonts: list[str] = field(default_factory=list)
    parts: int = 0

    @property
    def aspect(self) -> float:
        """Width divided by height, used to fit the artifact into a target box."""
        return self.width_in / self.height_in if self.height_in else 1.0

    def summary(self) -> str:
        """One-line description for a library listing."""
        preview = " / ".join(slot.text for slot in self.slots[:3])[:60]
        return (
            f"{self.id:<38} {self.kind:<9} {self.width_in:5.2f}x{self.height_in:<5.2f}in "
            f"{len(self.slots):>3} slots  {preview}"
        )


@dataclass
class LibraryStats:
    """What an extraction run found."""

    artifacts: int
    by_kind: dict[str, int]
    slides: int
    tables: int
    notes_chars: int
    colors: int
    fonts: int


def _slug(text: str, limit: int = 28) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (cleaned[:limit].rstrip("-")) or "untitled"


def _shape_text(shape) -> str:
    if shape.has_text_frame:
        return shape.text_frame.text
    return ""


def _slide_title(slide) -> str:
    if slide.shapes.title is not None and slide.shapes.title.has_text_frame:
        text = slide.shapes.title.text_frame.text.strip()
        if text:
            return text
    for shape in slide.shapes:
        text = _shape_text(shape).strip()
        if text:
            return text.splitlines()[0]
    return ""


def _element_texts(element: etree._Element) -> list[str]:
    return [node.text or "" for node in element.iter(f"{_A}t")]


def _element_colors(element: etree._Element) -> list[str]:
    seen: dict[str, int] = {}
    for node in element.iter(f"{_A}srgbClr"):
        value = str(node.get("val", "")).upper()
        if value:
            seen[value] = seen.get(value, 0) + 1
    return [value for value, _ in sorted(seen.items(), key=lambda kv: -kv[1])]


def _element_fonts(element: etree._Element) -> list[str]:
    seen = {
        str(node.get("typeface", ""))
        for tag in ("latin", "ea", "cs")
        for node in element.iter(f"{_A}{tag}")
        if node.get("typeface")
    }
    return sorted(seen)


def _graphic_uri(element: etree._Element) -> str:
    data = element.find(f".//{qn('a:graphicData')}")
    return "" if data is None else str(data.get("uri", ""))


def _classify(shape) -> str | None:
    tag = etree.QName(shape._element).localname
    if tag == "grpSp":
        return "group"
    if tag != "graphicFrame":
        return None
    uri = _graphic_uri(shape._element)
    if uri == _DGM_URI:
        return "smartart"
    if uri == _CHART_URI:
        return "chart"
    if uri == _TABLE_URI:
        return "table"
    return None


def _box_of(shape) -> Box:
    return Box(
        Emu(int(shape.left or 0)).inches,
        Emu(int(shape.top or 0)).inches,
        Emu(int(shape.width or 0)).inches,
        Emu(int(shape.height or 0)).inches,
    )


def _is_chrome(shape) -> bool:
    name = str(shape.name)
    return name in _CHROME_NAMES or name.startswith("df:title")


def _cluster(shapes: list) -> list[list]:
    """Group loose shapes into spatial clusters, so infographics survive as one unit."""
    parents = list(range(len(shapes)))

    def find(i: int) -> int:
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    boxes = [_box_of(shape) for shape in shapes]
    for i, first in enumerate(boxes):
        for j in range(i + 1, len(boxes)):
            second = boxes[j]
            gap_x = max(first.left, second.left) - min(first.right, second.right)
            gap_y = max(first.top, second.top) - min(first.bottom, second.bottom)
            if gap_x <= _CLUSTER_GAP_IN and gap_y <= _CLUSTER_GAP_IN:
                parents[find(i)] = find(j)
    buckets: dict[int, list] = {}
    for index, shape in enumerate(shapes):
        buckets.setdefault(find(index), []).append(shape)
    return [group for group in buckets.values() if len(group) >= _CLUSTER_MIN_SHAPES]


def _wrap_cluster(shapes: list) -> tuple[etree._Element, Box]:
    """Wrap loose shapes in a synthetic group so the cluster moves and scales as one."""
    boxes = [_box_of(shape) for shape in shapes]
    bounds = Box(
        min(b.left for b in boxes),
        min(b.top for b in boxes),
        max(b.right for b in boxes) - min(b.left for b in boxes),
        max(b.bottom for b in boxes) - min(b.top for b in boxes),
    )
    nsmap = 'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
    group = etree.fromstring(
        f'<p:grpSp {nsmap} xmlns:a="{_A[1:-1]}">'
        "<p:nvGrpSpPr><p:cNvPr id='900' name='cluster'/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>"
        "<p:grpSpPr><a:xfrm>"
        f"<a:off x='{Inches(bounds.left)}' y='{Inches(bounds.top)}'/>"
        f"<a:ext cx='{Inches(bounds.width)}' cy='{Inches(bounds.height)}'/>"
        f"<a:chOff x='{Inches(bounds.left)}' y='{Inches(bounds.top)}'/>"
        f"<a:chExt cx='{Inches(bounds.width)}' cy='{Inches(bounds.height)}'/>"
        "</a:xfrm></p:grpSpPr></p:grpSp>".encode()
    )
    for shape in shapes:
        group.append(etree.fromstring(etree.tostring(shape._element)))
    return group, bounds


def _related_rids(element: etree._Element) -> set[str]:
    found: set[str] = set()
    for node in element.iter():
        for attr in _R_ATTRS:
            value = node.get(qn(f"r:{attr}"))
            if value:
                found.add(value)
    return found


def _save_part_tree(part, out_dir: Path, seen: dict[str, str]) -> str:
    """Persist a part and everything it references; return the stored file name."""
    key = str(part.partname)
    if key in seen:
        return seen[key]
    filename = key.strip("/").replace("/", "__")
    seen[key] = filename
    (out_dir / filename).write_bytes(part.blob)
    children: dict[str, dict[str, str]] = {}
    for rid, rel in getattr(part, "rels", {}).items():
        if rel.is_external:
            continue
        children[rid] = {
            "file": _save_part_tree(rel.target_part, out_dir, seen),
            "reltype": rel.reltype,
            "content_type": rel.target_part.content_type,
            "partname": str(rel.target_part.partname),
        }
    if children:
        (out_dir / f"{filename}.rels.json").write_text(
            json.dumps(children, indent=2), encoding="utf-8"
        )
    return filename


class Library:
    """A versioned, on-disk collection of reusable design artifacts."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.manifest_path = self.root / "manifest.json"
        self.artifacts: dict[str, Artifact] = {}
        self.meta: dict[str, Any] = {"library_version": LIBRARY_VERSION, "sources": []}
        if self.manifest_path.is_file():
            self._load()

    def _load(self) -> None:
        data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        version = int(data.get("library_version", 0))
        if version != LIBRARY_VERSION:
            raise ArtifactError(
                f"{self.manifest_path}: library version {version}, this build expects "
                f"{LIBRARY_VERSION}; re-run `deckforge extract`"
            )
        self.meta = {k: v for k, v in data.items() if k != "artifacts"}
        for raw in data.get("artifacts", []):
            slots = [TextSlot(**slot) for slot in raw.pop("slots", [])]
            self.artifacts[raw["id"]] = Artifact(**raw, slots=slots)

    def save(self) -> None:
        """Write the manifest back to disk."""
        self.root.mkdir(parents=True, exist_ok=True)
        payload = dict(self.meta)
        payload["library_version"] = LIBRARY_VERSION
        payload["updated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        payload["artifacts"] = [asdict(a) for a in self.artifacts.values()]
        self.manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def get(self, artifact_id: str) -> Artifact:
        """Look up an artifact by exact id, then by unique prefix."""
        if artifact_id in self.artifacts:
            return self.artifacts[artifact_id]
        matches = [a for key, a in self.artifacts.items() if key.startswith(artifact_id)]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise ArtifactError(f"no artifact {artifact_id!r} in {self.root}")
        raise ArtifactError(
            f"{artifact_id!r} is ambiguous: {', '.join(sorted(a.id for a in matches))}"
        )

    def search(self, query: str) -> list[Artifact]:
        """Find artifacts whose id, title or text mentions ``query``."""
        needle = query.lower()
        return [
            artifact
            for artifact in self.artifacts.values()
            if needle in artifact.id.lower()
            or needle in artifact.title.lower()
            or any(needle in slot.text.lower() for slot in artifact.slots)
        ]

    def dir_for(self, artifact: Artifact) -> Path:
        """Directory holding one artifact's XML and related parts."""
        return self.root / "artifacts" / artifact.id

    def place(
        self,
        slide,
        artifact: Artifact,
        theme: Theme,
        box: Box,
        *,
        text: Iterable[str] | None = None,
        recolor: bool = True,
    ):
        """Clone an artifact onto a slide, retargeted to this deck.

        Args:
            slide: Destination slide.
            artifact: Artifact to place.
            theme: Active theme; supplies the colours the artifact is retargeted to.
            box: Target rectangle; the artifact is scaled to fit inside it, preserving
                its aspect ratio, and centred horizontally.
            text: Replacement strings, applied to the artifact's text slots in order.
                Shorter sequences leave the remaining slots untouched.
            recolor: Retarget explicit ``srgbClr`` values to theme colours. Theme
                (``schemeClr``) references are always left alone — they resolve against
                the destination theme by themselves, which is the behaviour we want.

        Returns:
            The rectangle the artifact actually occupies, which is at most ``box`` and
            usually smaller, since the aspect ratio is preserved.
        """
        source_dir = self.dir_for(artifact)
        element = etree.fromstring((source_dir / "shape.xml").read_bytes())
        rel_map = _clone_parts(slide, source_dir, element)
        if text:
            _retarget_text(element, list(text), rel_map, artifact.kind)
        if recolor:
            _retarget_colors(element, theme, artifact.kind, rel_map)
        placed = _resize(element, box, artifact)
        _reassign_ids(element, slide)
        _rename(element, name_shape("artifact", artifact.id))
        slide.shapes._spTree.append(element)
        return placed


def _clone_parts(slide, source_dir: Path, element: etree._Element) -> dict[str, Any]:
    """Copy stored related parts into the destination package and remap rIds."""
    rels_file = source_dir / "rels.json"
    if not rels_file.is_file():
        return {}
    stored = json.loads(rels_file.read_text(encoding="utf-8"))
    package = slide.part.package
    mapping: dict[str, Any] = {}
    for rid, info in stored.items():
        new_part = _materialise(package, source_dir, info["file"], info["content_type"])
        new_rid = slide.part.relate_to(new_part, info["reltype"])
        mapping[rid] = {"rid": new_rid, "part": new_part, "reltype": info["reltype"]}
    for node in element.iter():
        for attr in _R_ATTRS:
            key = qn(f"r:{attr}")
            value = node.get(key)
            if value and value in mapping:
                node.set(key, mapping[value]["rid"])
    return mapping


def _unique_partname(package, template: str) -> PackURI:
    existing = {str(part.partname) for part in package.iter_parts()}
    index = 1
    while True:
        candidate = template.format(index)
        if candidate not in existing:
            return PackURI(candidate)
        index += 1


def _materialise(package, source_dir: Path, filename: str, content_type: str) -> Part:
    """Rebuild a stored part (and its own children) inside the destination package."""
    blob = (source_dir / filename).read_bytes()
    stem = filename.split("__")[-1]
    folder = "/".join(filename.split("__")[:-1]) or "ppt/embeddings"
    suffix = Path(stem).suffix or ".bin"
    partname = _unique_partname(package, f"/{folder}/df{{}}{suffix}")
    part = Part(partname, content_type, package, blob)
    child_rels = source_dir / f"{filename}.rels.json"
    if child_rels.is_file():
        remap: dict[str, str] = {}
        for rid, info in json.loads(child_rels.read_text(encoding="utf-8")).items():
            child = _materialise(package, source_dir, info["file"], info["content_type"])
            remap[rid] = part.relate_to(child, info["reltype"])
        if remap and blob.lstrip().startswith(b"<"):
            tree = etree.fromstring(blob)
            for node in tree.iter():
                for attr in _R_ATTRS:
                    key = qn(f"r:{attr}")
                    value = node.get(key)
                    if value and value in remap:
                        node.set(key, remap[value])
            part._blob = etree.tostring(tree, xml_declaration=True, encoding="UTF-8")
    return part


def _text_nodes(element: etree._Element) -> list[etree._Element]:
    """Non-empty text nodes, in document order — the same list the manifest indexes."""
    return [node for node in element.iter(f"{_A}t") if (node.text or "").strip()]


def _retarget_text(
    element: etree._Element, replacements: list[str], rel_map: dict[str, Any], kind: str
) -> None:
    """Replace slot text in place, keeping every run property untouched."""
    if kind == "smartart":
        _retarget_smartart_text(rel_map, replacements)
        return
    for node, new_text in zip(_text_nodes(element), replacements):
        node.text = new_text


def _retarget_smartart_text(rel_map: dict[str, Any], replacements: list[str]) -> None:
    """SmartArt text lives in the diagram data part, not in the graphic frame."""
    data = next(
        (info["part"] for info in rel_map.values() if info["reltype"].endswith("/diagramData")),
        None,
    )
    if data is None:
        return
    tree = etree.fromstring(data.blob)
    points = [point for point in tree.iter(f"{_DGM}pt") if point.get("type") in (None, "node")]
    by_model: dict[str, str] = {}
    index = 0
    for point in points:
        model_id = str(point.get("modelId", ""))
        for node in point.iter(f"{_A}t"):
            if index >= len(replacements):
                break
            node.text = replacements[index]
            by_model[model_id] = replacements[index]
            index += 1
    data._blob = etree.tostring(tree, xml_declaration=True, encoding="UTF-8")
    _mirror_into_drawing(rel_map, by_model)


def _mirror_into_drawing(rel_map: dict[str, Any], by_model: dict[str, str]) -> None:
    """Keep the cached diagram drawing in step so non-PowerPoint viewers agree.

    PowerPoint re-runs the layout engine when the deck opens and ignores this cache;
    every other renderer draws it verbatim. Matching on ``modelId`` links a data point
    to the shape that draws it, so the cache cannot end up showing both strings.
    """
    drawing = next(
        (info["part"] for info in rel_map.values() if info["reltype"].endswith("/diagramDrawing")),
        None,
    )
    if drawing is None:
        return
    tree = etree.fromstring(drawing.blob)
    for shape in tree.iter():
        model_id = shape.get("modelId")
        if model_id not in by_model:
            continue
        text_nodes = list(shape.iter(f"{_A}t"))
        for position, node in enumerate(text_nodes):
            node.text = by_model[model_id] if position == 0 else ""
    drawing._blob = etree.tostring(tree, xml_declaration=True, encoding="UTF-8")


def _lightness(value: str) -> float:
    red, green, blue = (channel / 255 for channel in hex_to_rgb(value))
    return colorsys.rgb_to_hls(red, green, blue)[1]


def _saturation(value: str) -> float:
    red, green, blue = (channel / 255 for channel in hex_to_rgb(value))
    return colorsys.rgb_to_hls(red, green, blue)[2]


def _hue(value: str) -> float:
    red, green, blue = (channel / 255 for channel in hex_to_rgb(value))
    return colorsys.rgb_to_hls(red, green, blue)[0]


def _nearest_role(value: str, theme: Theme) -> str:
    hue = _hue(value)
    roles = theme.entity_roles or ("primary",)

    def distance(role: str) -> float:
        delta = abs(_hue(theme.color(role)) - hue)
        return min(delta, 1.0 - delta)

    return min(roles, key=distance)


def _distance(left: str, right: str) -> float:
    return sum((a - b) ** 2 for a, b in zip(hex_to_rgb(left), hex_to_rgb(right)))


def _mapped_color(value: str, theme: Theme) -> str:
    """Map one source colour onto the theme, preserving its light/dark structure.

    Very dark values are treated as type or rules whatever their hue: a near-black with
    a faint blue cast is ink, not a brand colour, and mapping it to the accent would
    turn every label in a harvested diagram blue. Everything else snaps to the nearest
    rung of the theme's own ladder, which keeps a two-tone ramp two-tone and makes the
    mapping idempotent — a colour already on the theme maps to itself, so an artifact
    reused a fourth time has not drifted a shade lighter each round.
    """
    light = _lightness(value)
    if light < _INK_LIGHTNESS:
        return theme.color("body_text")
    if _saturation(value) < _NEUTRAL_SATURATION:
        rungs = [theme.color(name) for name in ("page", "card_fill", "hairline", "secondary_text")]
    else:
        role = _nearest_role(value, theme)
        rungs = [theme.tint(role, level) for level in ("panel", "chip", "mid")]
        rungs.append(theme.color(role))
    return min(rungs, key=lambda rung: _distance(rung, value))


def _recolor_tree(tree: etree._Element, theme: Theme) -> bool:
    changed = False
    for node in tree.iter(f"{_A}srgbClr"):
        value = str(node.get("val", "")).upper()
        if not value:
            continue
        mapped = _mapped_color(value, theme)
        if mapped != value:
            node.set("val", mapped)
            changed = True
    return changed


def _retarget_colors(
    element: etree._Element, theme: Theme, kind: str, rel_map: dict[str, Any]
) -> None:
    """Retarget explicit colours to the active theme.

    SmartArt is the honest exception: its colours come from a ``dgm`` colour part whose
    mapping rules do not survive being rewritten, so the graphic frame is recoloured but
    the diagram parts are left as harvested. The library report says so, and the
    verifier reports the frame as real SmartArt rather than claiming a themed rebuild.
    """
    _recolor_tree(element, theme)
    if kind == "smartart":
        return
    for info in rel_map.values():
        part = info["part"]
        if not part.content_type.endswith("xml"):
            continue
        tree = etree.fromstring(part.blob)
        if _recolor_tree(tree, theme):
            part._blob = etree.tostring(tree, xml_declaration=True, encoding="UTF-8")


def _xfrm_of(element: etree._Element) -> etree._Element | None:
    """Find the transform that positions this shape, whichever kind it is."""
    tag = etree.QName(element).localname
    if tag == "graphicFrame":
        return element.find(qn("p:xfrm"))
    if tag == "grpSp":
        group_pr = element.find(qn("p:grpSpPr"))
        return None if group_pr is None else group_pr.find(f"{_A}xfrm")
    shape_pr = element.find(qn("p:spPr"))
    return None if shape_pr is None else shape_pr.find(f"{_A}xfrm")


def _scale_typography(element: etree._Element, factor: float) -> None:
    """Scale type and line weights with the shape.

    PowerPoint resizes a group's geometry but leaves its font sizes alone, so a
    harvested diagram dropped into a smaller box collides with itself. Scaling the
    ``sz`` and ``w`` attributes by the same factor keeps the artifact proportional.
    """
    if abs(factor - 1.0) < 0.02:
        return
    for tag, attr, floor in (
        ("rPr", "sz", 700),
        ("defRPr", "sz", 700),
        ("endParaRPr", "sz", 700),
        ("ln", "w", 3175),
    ):
        for node in element.iter(f"{_A}{tag}"):
            raw = node.get(attr)
            if raw and str(raw).isdigit():
                node.set(attr, str(max(floor, int(int(raw) * factor))))


def _resize(element: etree._Element, box: Box, artifact: Artifact) -> Box:
    """Scale the artifact to fit ``box`` without distorting it."""
    xfrm = _xfrm_of(element)
    if xfrm is None:
        raise ArtifactError(f"artifact {artifact.id} has no transform to retarget")
    scale = min(box.width / artifact.width_in, box.height / artifact.height_in)
    width = artifact.width_in * scale
    height = artifact.height_in * scale
    left = box.left + (box.width - width) / 2
    top = box.top + (box.height - height) / 2
    off = xfrm.find(f"{_A}off")
    ext = xfrm.find(f"{_A}ext")
    if off is None or ext is None:
        raise ArtifactError(f"artifact {artifact.id} has an incomplete transform")
    off.set("x", str(int(Inches(left))))
    off.set("y", str(int(Inches(top))))
    ext.set("cx", str(int(Inches(width))))
    ext.set("cy", str(int(Inches(height))))
    _scale_typography(element, scale)
    return Box(left, top, width, height)


def _rename(element: etree._Element, new_name: str) -> None:
    node = element.find(f".//{qn('p:cNvPr')}")
    if node is not None:
        node.set("name", new_name)


def _reassign_ids(element: etree._Element, slide) -> None:
    """Renumber cloned shape ids; duplicates make PowerPoint repair the file."""
    used = {
        int(node.get("id", 0))
        for node in slide.shapes._spTree.iter(qn("p:cNvPr"))
        if str(node.get("id", "")).isdigit()
    }
    next_id = max(used, default=1) + 1
    for node in element.iter(qn("p:cNvPr")):
        node.set("id", str(next_id))
        next_id += 1


def _slide_outline(presentation) -> list[dict[str, Any]]:
    outline: list[dict[str, Any]] = []
    for number, slide in enumerate(presentation.slides, start=1):
        notes = slide.notes_slide.notes_text_frame.text.strip() if slide.has_notes_slide else ""
        bullets = [
            line.strip()
            for shape in slide.shapes
            if shape.has_text_frame
            for line in shape.text_frame.text.splitlines()
            if line.strip()
        ]
        outline.append(
            {
                "slide": number,
                "layout": slide.slide_layout.name,
                "title": _slide_title(slide),
                "lines": bullets[:20],
                "notes": notes,
            }
        )
    return outline


def _table_data(shape) -> list[list[str]]:
    return [[cell.text for cell in row.cells] for row in shape.table.rows]


def extract(
    source: Path,
    library_dir: Path,
    *,
    include_clusters: bool = True,
    min_width_in: float = 1.2,
) -> LibraryStats:
    """Mine a deck for reusable design material and write an artifact library.

    Args:
        source: Deck to mine.
        library_dir: Library root; created if absent, updated in place if it exists.
        include_clusters: Also capture loose infographic shape clusters, not just
            explicit groups.
        min_width_in: Ignore anything narrower than this — labels and stray marks.

    Returns:
        A :class:`LibraryStats` summary of what was captured.
    """
    library = Library(library_dir)
    artifacts_root = library_dir / "artifacts"
    artifacts_root.mkdir(parents=True, exist_ok=True)
    by_kind: dict[str, int] = {}
    tables: list[dict[str, Any]] = []
    colors: dict[str, int] = {}
    fonts: dict[str, int] = {}

    with hydrated(source) as local:
        presentation = Presentation(str(local))
        outline = _slide_outline(presentation)
        for number, slide in enumerate(presentation.slides, start=1):
            title = _slide_title(slide)
            captured: list = []
            for shape in slide.shapes:
                kind = _classify(shape)
                if kind is None:
                    continue
                box = _box_of(shape)
                if box.width < min_width_in or box.height < 0.3:
                    continue
                captured.append(shape)
                artifact = _store(
                    library, artifacts_root, shape._element, box, kind, source, number, title, slide
                )
                by_kind[kind] = by_kind.get(kind, 0) + 1
                if kind == "table":
                    tables.append(
                        {"artifact": artifact.id, "slide": number, "rows": _table_data(shape)}
                    )
            if include_clusters:
                loose = [
                    shape
                    for shape in slide.shapes
                    if shape not in captured
                    and not shape.is_placeholder
                    and not _is_chrome(shape)
                    and shape.shape_type
                    not in (MSO_SHAPE_TYPE.PICTURE, MSO_SHAPE_TYPE.GROUP, MSO_SHAPE_TYPE.MEDIA)
                ]
                slide_area = (
                    Emu(int(presentation.slide_width or 0)).inches,
                    Emu(int(presentation.slide_height or 0)).inches,
                )
                for group in _cluster(loose):
                    element, bounds = _wrap_cluster(group)
                    covers_slide = (
                        bounds.width > slide_area[0] * _CLUSTER_MAX_COVERAGE
                        and bounds.height > slide_area[1] * _CLUSTER_MAX_COVERAGE
                    )
                    if bounds.width < min_width_in or bounds.height < 0.5 or covers_slide:
                        continue
                    _store(
                        library,
                        artifacts_root,
                        element,
                        bounds,
                        "cluster",
                        source,
                        number,
                        title,
                        slide,
                    )
                    by_kind["cluster"] = by_kind.get("cluster", 0) + 1
            for shape in slide.shapes:
                for value in _element_colors(shape._element):
                    colors[value] = colors.get(value, 0) + 1
                for value in _element_fonts(shape._element):
                    fonts[value] = fonts.get(value, 0) + 1

    library.meta.setdefault("sources", [])
    if source.name not in library.meta["sources"]:
        library.meta["sources"].append(source.name)
    library.save()
    _write_reports(library_dir, outline, tables, colors, fonts)
    return LibraryStats(
        artifacts=len(library.artifacts),
        by_kind=by_kind,
        slides=len(outline),
        tables=len(tables),
        notes_chars=sum(len(entry["notes"]) for entry in outline),
        colors=len(colors),
        fonts=len(fonts),
    )


def _store(
    library: Library,
    artifacts_root: Path,
    element: etree._Element,
    box: Box,
    kind: str,
    source: Path,
    slide_number: int,
    title: str,
    slide,
) -> Artifact:
    """Write one artifact's XML, related parts and manifest entry."""
    artifact_id = f"{kind}-{slide_number:02d}-{_slug(title)}"
    suffix = 1
    while artifact_id in library.artifacts:
        suffix += 1
        artifact_id = f"{kind}-{slide_number:02d}-{_slug(title)}-{suffix}"
    target = artifacts_root / artifact_id
    target.mkdir(parents=True, exist_ok=True)
    clone = etree.fromstring(etree.tostring(element))
    (target / "shape.xml").write_bytes(etree.tostring(clone, encoding="UTF-8"))

    stored: dict[str, dict[str, str]] = {}
    seen: dict[str, str] = {}
    for rid in _related_rids(clone):
        try:
            related = slide.part.rels[rid]
        except KeyError:
            continue
        if related.is_external:
            continue
        stored[rid] = {
            "file": _save_part_tree(related.target_part, target, seen),
            "reltype": related.reltype,
            "content_type": related.target_part.content_type,
            "partname": str(related.target_part.partname),
        }
    if stored:
        (target / "rels.json").write_text(json.dumps(stored, indent=2), encoding="utf-8")

    texts = _slot_texts(clone, kind, slide, stored)
    (target / "preview.txt").write_text("\n".join(texts), encoding="utf-8")
    artifact = Artifact(
        id=artifact_id,
        kind=kind,
        source=source.name,
        slide=slide_number,
        title=title,
        left_in=round(box.left, 3),
        top_in=round(box.top, 3),
        width_in=round(box.width, 3),
        height_in=round(box.height, 3),
        shape_count=len(list(clone.iter(qn("p:sp")))) or 1,
        slots=[TextSlot(index=i, text=t, chars=len(t)) for i, t in enumerate(texts)],
        colors=_element_colors(clone)[:12],
        fonts=_element_fonts(clone)[:6],
        parts=len(stored),
    )
    library.artifacts[artifact_id] = artifact
    return artifact


def _slot_texts(
    element: etree._Element, kind: str, slide, stored: dict[str, dict[str, str]]
) -> list[str]:
    if kind != "smartart":
        return [text for text in _element_texts(element) if text.strip()]
    for rid, info in stored.items():
        if info["reltype"].endswith("/diagramData"):
            blob = slide.part.rels[rid].target_part.blob
            tree = etree.fromstring(blob)
            return [
                node.text or ""
                for point in tree.iter(f"{_DGM}pt")
                if point.get("type") in (None, "node")
                for node in point.iter(f"{_A}t")
                if (node.text or "").strip()
            ]
    return []


def _write_reports(
    library_dir: Path,
    outline: list[dict[str, Any]],
    tables: list[dict[str, Any]],
    colors: dict[str, int],
    fonts: dict[str, int],
) -> None:
    (library_dir / "outline.json").write_text(json.dumps(outline, indent=2), encoding="utf-8")
    (library_dir / "tables.json").write_text(json.dumps(tables, indent=2), encoding="utf-8")
    (library_dir / "colors.json").write_text(
        json.dumps(
            {
                "by_frequency": dict(sorted(colors.items(), key=lambda kv: -kv[1])),
                "tint_of": {value: mix(value, amount=0.86) for value in list(colors)[:12]},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (library_dir / "fonts.json").write_text(
        json.dumps(dict(sorted(fonts.items(), key=lambda kv: -kv[1])), indent=2), encoding="utf-8"
    )
    lines = ["# Source Deck Outline", "", "## Table of Contents", ""]
    for entry in outline:
        lines += [
            f"## {entry['slide']}. {entry['title'] or 'Untitled'}",
            "",
            f"Layout: `{entry['layout']}`",
            "",
        ]
        lines += [f"- {line}" for line in entry["lines"][:10]] or ["- (no text)"]
        lines += ["", "Notes:", "", f"> {entry['notes'][:600] or '(none)'}", ""]
    (library_dir / "outline.md").write_text("\n".join(lines), encoding="utf-8")
    notes = [
        f"## {entry['slide']}. {entry['title'] or 'Untitled'}\n\n{entry['notes'] or '(none)'}\n"
        for entry in outline
    ]
    (library_dir / "notes.md").write_text(
        "# Speaker Notes\n\n## Table of Contents\n\n" + "\n".join(notes), encoding="utf-8"
    )
