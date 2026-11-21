"""Read the Riverscapes business logic and its QML symbology files.

This module mirrors how the workspace tree finds layers and symbology, but it
does so without QGIS so the parsing can be unit-tested on its own:

* Business logic XML lives in ``resources/blXML/<version>/<ProjectType>.xml``.
  Every ``<Node>`` that maps a map layer carries ``symbology="<name>"`` and a
  ``type`` of ``point``/``polygon``/``line``/``raster``.
* The matching QML file is looked up as
  ``resources/symbology/<ProjectType>/<name>.qml`` and then
  ``resources/symbology/Shared/<name>.qml`` — the same precedence
  :meth:`QRaveMapLayer.find_layer_symbology` uses (minus the project folder,
  which is not relevant here).
* IGOs are points and DGOs are polygons, so the point and polygon variants of
  the same metric (``ownership_rme3`` / ``ownership_rme3_dgo``) are grouped into
  one :class:`SymbologyEntry` that can serve either dataset.

The QML itself is just XML, so :func:`parse_qml` turns its renderer into a
geometry-neutral :class:`SymbologyStyle` — a list of labelled classes with a
QGIS filter expression and colours — which
:mod:`~.dgos_layer` then turns into vector-tile renderer styles.
"""

from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

#: Repository root, relative to ``src/classes``.
RESOURCES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "resources"))

#: Where the business-logic XML files are kept.
BUSINESS_LOGIC_DIR = os.path.join(RESOURCES_DIR, "blXML")

#: Where the QML symbology files are kept.
SYMBOLOGY_DIR = os.path.join(RESOURCES_DIR, "symbology")

#: Project type used by the Riverscapes Metric Engine.
RME_PROJECT_TYPE = "rs_metric_engine"

#: Fallback colours (the dock's single-colour preset).  Lower-case so they
#: match the colours parsed out of QML.
FALLBACK_FILL = "#5b9bd5"
FALLBACK_OUTLINE = "#1f4e79"

#: Only these node types can symbolize an IGO (point) or DGO (polygon) layer.
SUPPORTED_GEOMETRIES = ("point", "polygon")

#: Filter fields whose symbology attribute is spelled differently in the QML.
#: Keys are the fields the dock filters on (see ``dgos_filters``); values are
#: the extra ``attr`` names that paint the same thing.
FIELD_ATTRIBUTE_ALIASES = {
    "primary_channel_gradient": ("prim_channel_gradient",),
    "road_den": ("road_dens",),
    "floodplain_area": ("active_floodplain_area",),
}

# Matches a trailing "(IGO)"/"(DGO)" marker on a business-logic label.
_GEOMETRY_SUFFIX = re.compile(r"\s*\((?:igo|dgo)\)\s*$", re.IGNORECASE)

# Matches the "_dgo" suffix that distinguishes the polygon QML from its point
# sibling (``ownership_rme3`` vs ``ownership_rme3_dgo``).
_DGO_SUFFIX = re.compile(r"[_-]dgo$", re.IGNORECASE)

_HEX_COLOUR = re.compile(r"^#([0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


# ── Value objects ─────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class SymbologyClass:
    """One legend class: a label, its QGIS filter and its colours.

    Attributes:
        label: Text shown in the legend, e.g. ``"Bureau of Land Management"``.
        filter_expression: Query for this class (empty means "everything else").
        fill: ``#rrggbb`` colour for the polygon fill / marker fill.
        outline: ``#rrggbb`` colour for the outline.
        value: For categorized renderers, the raw category value the layer
            stores (``"BLM"``).  ``None`` means the category matches NULL or
            blank values (QGIS's "Other" bucket).
        lower: For graduated renderers, the inclusive lower bound.
        upper: For graduated renderers, the upper bound (inclusive for the
            top-most class, exclusive otherwise).
    """

    label: str
    filter_expression: str
    fill: str
    outline: str
    value: str | None = None
    lower: float | None = None
    upper: float | None = None


@dataclass(frozen=True)
class SymbologyStyle:
    """A parsed QML renderer, independent of any geometry type.

    Attributes:
        name: QML file stem, e.g. ``"ownership_rme3_dgo"``.
        attr: The field the renderer classifies on, if any.
        renderer_type: QML renderer type, e.g. ``"categorizedSymbol"``.
        classes: The classes/rules, in QML order.
        qml_path: Absolute path of the source file.
    """

    name: str
    attr: str | None
    renderer_type: str
    classes: tuple
    qml_path: str

    @property
    def legend(self) -> tuple:
        """``((label, fill), …)`` pairs for drawing a legend."""
        return tuple((symbology_class.label, symbology_class.fill) for symbology_class in self.classes)


@dataclass(frozen=True)
class SymbologyEntry:
    """One business-logic metric, with the QML for each geometry it supports.

    ``point_qml`` serves the IGO layer and ``polygon_qml`` the DGO layer.  The
    two are separate files (``ownership_rme3`` / ``ownership_rme3_dgo``), so a
    metric that only exists for one geometry still makes sense to offer.
    """

    label: str
    point_qml: str | None = None
    polygon_qml: str | None = None

    def qml_for(self, is_point: bool) -> str | None:
        """The best QML for the requested geometry.

        The geometry-matched file wins; otherwise the sibling is used, so the
        colours still apply and the caller can draw the right symbol class for
        the active layer.
        """
        preferred, other = (self.point_qml, self.polygon_qml) if is_point else (self.polygon_qml, self.point_qml)
        return preferred or other


# ── Business logic ────────────────────────────────────────────────────────────
def business_logic_path(project_type: str = RME_PROJECT_TYPE) -> str | None:
    """Return the newest business-logic XML for *project_type*, if present.

    Version folders (``V1``, ``V2``, …) are searched in reverse order so the
    highest version wins.
    """
    if not os.path.isdir(BUSINESS_LOGIC_DIR):
        return None

    fname = f"{project_type}.xml"
    for version in sorted(os.listdir(BUSINESS_LOGIC_DIR), reverse=True):
        candidate = os.path.join(BUSINESS_LOGIC_DIR, version, fname)
        if os.path.isfile(candidate):
            return candidate
    return None


def find_qml(symbology: str, project_type: str = RME_PROJECT_TYPE) -> str | None:
    """Resolve a business-logic ``symbology`` name to a QML file.

    Searches ``resources/symbology/<project_type>/`` first, then ``Shared/``,
    matching the precedence the workspace tree uses.
    """
    fname = f"{symbology}.qml"
    for folder in (project_type, "Shared"):
        candidate = os.path.join(SYMBOLOGY_DIR, folder, fname)
        if os.path.isfile(candidate):
            return candidate
    return None


def field_matches_attribute(field: str, attribute: str | None) -> bool:
    """Whether a symbology attribute paints the data *field* filters on.

    Exact matches win; :data:`FIELD_ATTRIBUTE_ALIASES` covers the handful of
    fields whose QML spells the attribute slightly differently.
    """
    if not field or not attribute:
        return False
    if attribute == field:
        return True
    return attribute in FIELD_ATTRIBUTE_ALIASES.get(field, ())


def _clean_label(label: str) -> str:
    """Drop a trailing ``(IGO)``/``(DGO)`` marker and surrounding whitespace."""
    return _GEOMETRY_SUFFIX.sub("", label or "").strip()


def load_symbology_entries(project_type: str = RME_PROJECT_TYPE) -> tuple:
    """Build the symbology menu for a project type's business logic.

    Every point/polygon node with a ``symbology`` attribute becomes part of an
    entry, grouped so the point and polygon variants of one metric share a
    single menu item.  Entries are returned in business-logic order; a label
    that occurs more than once gets its QML stem appended so the menu stays
    unambiguous.
    """
    path = business_logic_path(project_type)
    if path is None:
        return ()

    grouped = {}
    order = []

    for node in ET.parse(path).getroot().iter():
        if node.tag != "Node":
            continue
        symbology = node.get("symbology")
        geometry = node.get("type")
        if not symbology or geometry not in SUPPORTED_GEOMETRIES:
            continue

        # ``ownership_rme3`` and ``ownership_rme3_dgo`` are the point and
        # polygon files for the same metric, so they share a menu entry.
        key = _DGO_SUFFIX.sub("", symbology)
        entry = grouped.get(key)
        if entry is None:
            entry = grouped[key] = {
                "label": _clean_label(node.get("label", "")),
                "stem": symbology,
                "point_qml": None,
                "polygon_qml": None,
            }
            order.append(key)

        qml_path = find_qml(symbology, project_type)
        if geometry == "point" and entry["point_qml"] is None:
            entry["point_qml"] = qml_path
        elif geometry == "polygon" and entry["polygon_qml"] is None:
            entry["polygon_qml"] = qml_path

    # Only offer metrics we can actually symbolize.
    usable = [grouped[key] for key in order if grouped[key]["point_qml"] or grouped[key]["polygon_qml"]]
    if not usable:
        return ()

    label_counts = {}
    for entry in usable:
        label_counts[entry["label"]] = label_counts.get(entry["label"], 0) + 1

    entries = []
    for entry in usable:
        label = entry["label"]
        if label_counts[label] > 1:
            # Several metrics share a display name; disambiguate with the QML.
            label = f"{label} ({entry['stem']})"
        entries.append(SymbologyEntry(label=label, point_qml=entry["point_qml"], polygon_qml=entry["polygon_qml"]))

    return tuple(entries)


# ── QML parsing ───────────────────────────────────────────────────────────────
def _normalise_colour(value: str | None) -> str | None:
    """Turn a QML colour value into ``#rrggbb``, or ``None`` if unparseable.

    QML stores colours either as ``#rrggbb`` or as ``"r,g,b,a,rgb:…"``.  Data
    defined values (``@symbol_color`` etc.) are rejected so callers fall back.
    """
    if not value:
        return None

    value = value.strip()
    if value.startswith("#"):
        return value[:7].lower() if _HEX_COLOUR.match(value) else None

    parts = value.split(",")
    if len(parts) >= 3:
        try:
            red, green, blue = (int(float(part)) for part in parts[:3])
        except ValueError:
            return None
        if all(0 <= channel <= 255 for channel in (red, green, blue)):
            return f"#{red:02x}{green:02x}{blue:02x}"
    return None


def _darken(colour: str, factor: float = 0.65) -> str:
    """Return a darker version of *colour*, used when QML has no outline."""
    try:
        red = int(colour[1:3], 16)
        green = int(colour[3:5], 16)
        blue = int(colour[5:7], 16)
    except (ValueError, IndexError):
        return FALLBACK_OUTLINE
    return f"#{max(0, int(red * factor)):02x}{max(0, int(green * factor)):02x}{max(0, int(blue * factor)):02x}"


def _option_value(element, names) -> str | None:
    """Find the first ``<Option name=… value=…>``/``<prop k=… v=…>`` child.

    QML files use both spellings depending on the QGIS version that wrote them,
    so both are supported here.
    """
    for child in element.iter():
        name = child.get("name") or child.get("k")
        if name in names:
            value = child.get("value") or child.get("v")
            if value:
                return value
    return None


def _symbol_colours(symbol) -> tuple:
    """``(fill, outline)`` for one ``<symbol>`` element."""
    fill = _normalise_colour(_option_value(symbol, {"color", "fill_color"}))
    outline = _normalise_colour(_option_value(symbol, {"outline_color", "line_color", "stroke_color"}))
    if fill is None:
        return FALLBACK_FILL, FALLBACK_OUTLINE
    return fill, outline or _darken(fill)


def _number(value: str | None) -> float | None:
    """Parse a QML numeric attribute, tolerating ``NULL``/blanks."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_number(value: float) -> str:
    """Render a float as a compact QGIS literal (``3`` rather than ``3.0``)."""
    return f"{value:g}"


def _quote(value: str) -> str:
    """Single-quote a string for a QGIS expression."""
    return "'" + str(value).replace("'", "''") + "'"


def _leaf(element, tag: str):
    """First direct child element with *tag*, or ``None``."""
    for child in element:
        if child.tag == tag:
            return child
    return None


def _parse_categories(renderer, symbols) -> list:
    """Classes for a ``categorizedSymbol`` renderer."""
    attr = renderer.get("attr")
    categories = _leaf(renderer, "categories")
    if not attr or categories is None:
        return []

    classes = []
    for category in categories.findall("category"):
        if category.get("render", "true") == "false":
            continue
        value = category.get("value")
        if value is None:
            continue

        kind = category.get("type", "string")
        raw_value = None if kind == "NULL" or value == "" else value
        if kind == "int":
            try:
                clause = f'to_int("{attr}") = {int(value)}'
            except ValueError:
                clause = f'"{attr}" = {_quote(value)}'
        elif kind in ("double", "float"):
            number = _number(value)
            clause = f'"{attr}" = {_format_number(number)}' if number is not None else f'"{attr}" = {_quote(value)}'
        else:
            clause = f'"{attr}" = {_quote(value)}'

        fill, outline = _symbol_colours(symbols[int(category.get("symbol", 0))]) if symbols else (FALLBACK_FILL, FALLBACK_OUTLINE)
        classes.append(SymbologyClass(label=category.get("label") or value, filter_expression=clause, fill=fill, outline=outline, value=raw_value))
    return classes


def _parse_ranges(renderer, symbols) -> list:
    """Classes for a ``graduatedSymbol`` renderer."""
    attr = renderer.get("attr")
    ranges = _leaf(renderer, "ranges")
    if not attr or ranges is None:
        return []

    ranges = [item for item in ranges.findall("range") if item.get("render", "true") != "false"]

    # Zero-width classes (lower == upper) draw nothing in QGIS either, so keep
    # them out of both the renderer and the legend.
    ranges = [item for item in ranges if _number(item.get("lower")) != _number(item.get("upper")) or _number(item.get("lower")) is None]

    bounds = [(index, _number(item.get("lower")), _number(item.get("upper"))) for index, item in enumerate(ranges)]
    uppers = [upper for _index, _lower, upper in bounds if upper is not None]
    top = max(uppers) if uppers else None

    classes = []
    for index, lower, upper in bounds:
        if lower is not None and upper is not None:
            operator = "<=" if upper == top else "<"
            clause = f'"{attr}" >= {_format_number(lower)} AND "{attr}" {operator} {_format_number(upper)}'
        elif lower is not None:
            clause = f'"{attr}" >= {_format_number(lower)}'
        elif upper is not None:
            clause = f'"{attr}" <= {_format_number(upper)}'
        else:
            clause = ""

        item = ranges[index]
        fill, outline = _symbol_colours(symbols[int(item.get("symbol", 0))]) if symbols else (FALLBACK_FILL, FALLBACK_OUTLINE)
        classes.append(SymbologyClass(label=item.get("label") or clause, filter_expression=clause, fill=fill, outline=outline, lower=lower, upper=upper))
    return classes


def _parse_rules(renderer, symbols) -> list:
    """Classes for a ``RuleRenderer`` (rule filters are QGIS expressions)."""
    rules_element = _leaf(renderer, "rules")
    if rules_element is None:
        return []

    classes = []
    for rule in rules_element.iter("rule"):
        if rule.get("render", "true") == "false":
            continue

        clause = (rule.get("filter") or "").strip()
        label = rule.get("label") or (rule.get("description") or "").strip() or "Other"
        fill, outline = _symbol_colours(symbols[int(rule.get("symbol", 0))]) if symbols else (FALLBACK_FILL, FALLBACK_OUTLINE)
        classes.append(SymbologyClass(label=label, filter_expression=clause, fill=fill, outline=outline))
    return classes


def categorized_items(symbology: str, project_type: str = RME_PROJECT_TYPE) -> tuple:
    """``((label, value), …)`` for a symbology's categories, in QML order.

    Labels are the human-readable class names the legend shows; the values are
    what the layer actually stores, which is what a filter needs.  A NULL/blank
    category (QGIS's "Other" bucket) yields ``None``.
    """
    path = find_qml(symbology, project_type)
    if path is None:
        return ()

    style = parse_qml(path)
    if style.renderer_type != "categorizedSymbol":
        return ()

    return tuple((symbology_class.label, symbology_class.value) for symbology_class in style.classes)


def ranged_items(symbology: str, project_type: str = RME_PROJECT_TYPE) -> tuple:
    """``((label, lower, upper), …)`` for a graduated symbology, in QML order.

    This is what lets a filter use the symbology's own class breaks instead of
    re-inventing them.
    """
    path = find_qml(symbology, project_type)
    if path is None:
        return ()

    style = parse_qml(path)
    if style.renderer_type != "graduatedSymbol":
        return ()

    return tuple((symbology_class.label, symbology_class.lower, symbology_class.upper) for symbology_class in style.classes)


def parse_qml(qml_path: str) -> SymbologyStyle:
    """Parse a QML file into a geometry-neutral :class:`SymbologyStyle`.

    Categorized, graduated, rule and single-symbol renderers are supported.
    Anything else degrades to a single class using the file's first symbol, so
    picking a layer can never leave the map unstyled.
    """
    root = ET.parse(qml_path).getroot()
    name = os.path.splitext(os.path.basename(qml_path))[0]

    renderer = None
    for element in root:
        if element.tag == "renderer-v2":
            renderer = element
            break

    symbols = []
    if renderer is not None:
        symbols_element = _leaf(renderer, "symbols")
        if symbols_element is not None:
            symbols = symbols_element.findall("symbol")
    if not symbols:
        # Single-symbol (or exotic) renderers keep their symbol outside the
        # ``symbols`` list only in very old files; take the first one we see.
        symbols = [element for element in root.iter("symbol") if element.get("type") in ("fill", "marker", "line")]

    renderer_type = renderer.get("type", "singleSymbol") if renderer is not None else "singleSymbol"
    attr = renderer.get("attr") if renderer is not None else None
    classes = []

    if renderer is not None and renderer_type == "categorizedSymbol":
        classes = _parse_categories(renderer, symbols)
    elif renderer is not None and renderer_type == "graduatedSymbol":
        classes = _parse_ranges(renderer, symbols)
    elif renderer is not None and renderer_type == "RuleRenderer":
        classes = _parse_rules(renderer, symbols)

    if not classes:
        fill, outline = _symbol_colours(symbols[0]) if symbols else (FALLBACK_FILL, FALLBACK_OUTLINE)
        classes = [SymbologyClass(label=name.replace("_", " "), filter_expression="", fill=fill, outline=outline)]

    return SymbologyStyle(
        name=name,
        attr=attr,
        renderer_type=renderer_type,
        classes=tuple(classes),
        qml_path=os.path.abspath(qml_path),
    )