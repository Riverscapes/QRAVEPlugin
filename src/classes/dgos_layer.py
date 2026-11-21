"""Create and symbolize the IGOs / DGOs vector tile layers.

Two vector tile services sit behind the same panel:

* **IGOs** — point features, served from ``.../tiles/igos/{z}/{x}/{y}.pbf``
* **DGOs** — polygon features, served from ``.../tiles/dgos/{z}/{x}/{y}.pbf``

The two services differ *only* in the ``igos``/``dgos`` path segment.  They use
the same authentication configuration and expose the same attributes, so
everything here is shared apart from the layer name and the geometry type:
IGOs are symbolized with markers, DGOs with polygon fills (never the other way
round).

Filtering and symbolization are both applied through the QGIS *vector tile basic
renderer*: each renderer style carries a filter expression, so a style only
draws the features it matches.  That is the supported way to filter vector
tiles — there is no per-layer ``subsetString`` on
:class:`QgsVectorTileLayer`.  The renderer is rebuilt whenever the filters, the
symbology preset or the selected dataset change.

The tile services require authentication.  The layer URI carries
``authcfg=<id>`` for the QGIS authentication configuration named
:data:`AUTH_CONFIG_NAME`, which the user sets up once in their QGIS session.
See :func:`find_auth_config_id`.
"""

from __future__ import annotations

from dataclasses import dataclass
import urllib.parse

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsAuthMethodConfig,
    QgsFillSymbol,
    QgsMarkerSymbol,
    QgsProject,
    QgsVectorTileBasicRenderer,
    QgsVectorTileBasicRendererStyle,
    QgsVectorTileLayer,
)

from ..compat import GEOM_POINT, GEOM_POLYGON
from .dgos_filters import (
    CAPACITY_FIELD,
    CAPACITY_MAX,
    CAPACITY_MIN,
    HIST_CAPACITY_FIELD,
    OWNERSHIP_VALUES,
    STREAM_ORDER_FIELD,
    STREAM_ORDER_VALUES,
    quote_string,
)
from .settings import Settings

#: XYZ vector tile URL template.  ``{dataset}`` is the ``igos``/``dgos``
#: path segment; see :class:`TileDataset`.
TILE_URL_TEMPLATE = "https://reach.riverscapes.net/tiles/{dataset}/{z}/{x}/{y}.pbf"

#: Provider key for vector tile layers (used when re-pointing a data source).
PROVIDER_KEY = "vectortile"

#: Name of the QGIS authentication configuration the tile services need.
#: The config itself is set up by the user under
#: Settings ▸ Options ▸ Authentication; we only look up its id by name.
AUTH_CONFIG_NAME = "Reach Production API Key"

#: Source layer inside the vector tiles.  An empty string on a renderer style
#: means "all source layers", which we use so the styles keep working if the
#: services rename their internal layer.
SOURCE_LAYER = ""

# Set once we have logged a missing-auth warning, so repeated style refreshes
# do not flood the message log.
_missing_auth_warned = False


# ── Datasets ──────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class TileDataset:
    """One of the two nearly-identical vector tile services.

    Attributes:
        key: The URL path segment (``"igos"`` or ``"dgos"``).
        label: Human-readable name, also used as the QGIS layer name.
        is_point: ``True`` for point features (IGOs), ``False`` for polygons
            (DGOs).  This is the only symbology difference between the two.
    """

    key: str
    label: str
    is_point: bool

    @property
    def tile_url(self) -> str:
        """The XYZ tile URL template for this dataset."""
        # ``str.replace`` rather than ``str.format``: the template also contains
        # the ``{z}``/``{x}``/``{y}`` placeholders QGIS fills in later.
        return TILE_URL_TEMPLATE.replace("{dataset}", self.key)

    @property
    def geometry_type(self):
        """The only geometry type this dataset is ever symbolized with."""
        return GEOM_POINT if self.is_point else GEOM_POLYGON


DATASET_IGOS = "igos"
DATASET_DGOS = "dgos"

#: The datasets in the order they appear in the dock's dropdown: IGOs, DGOs.
DATASETS = (
    TileDataset(key=DATASET_IGOS, label="IGOs", is_point=True),
    TileDataset(key=DATASET_DGOS, label="DGOs", is_point=False),
)

#: Lookup by :attr:`TileDataset.key`.
DATASETS_BY_KEY = {dataset.key: dataset for dataset in DATASETS}

#: Dataset shown when the panel first opens (the original DGO behaviour).
DEFAULT_DATASET = DATASET_DGOS


def dataset_for(dataset_key: str = DEFAULT_DATASET) -> TileDataset:
    """Return the :class:`TileDataset` for *dataset_key*, defaulting to DGOs."""
    return DATASETS_BY_KEY.get(dataset_key, DATASETS_BY_KEY[DEFAULT_DATASET])


# ── Symbology presets ─────────────────────────────────────────────────────────
SYMBOLOGY_SINGLE = "Single color"
SYMBOLOGY_OWNERSHIP = "Ownership"
SYMBOLOGY_STREAM_ORDER = "Stream order"
SYMBOLOGY_EXISTING_CAPACITY = "Existing beaver capacity"
SYMBOLOGY_HISTORIC_CAPACITY = "Historic beaver capacity"

#: Order in which the presets appear in the dock's combo box.
SYMBOLOGY_MODES = (
    SYMBOLOGY_SINGLE,
    SYMBOLOGY_OWNERSHIP,
    SYMBOLOGY_STREAM_ORDER,
    SYMBOLOGY_EXISTING_CAPACITY,
    SYMBOLOGY_HISTORIC_CAPACITY,
)
DEFAULT_SYMBOLOGY = SYMBOLOGY_SINGLE

#: Built-in presets that paint one specific field, keyed by field name.  Used
#: when a filter control asks to be symbolized and no business-logic QML covers
#: the field.
SYMBOLOGY_FIELD_PRESETS = {
    CAPACITY_FIELD: SYMBOLOGY_EXISTING_CAPACITY,
    HIST_CAPACITY_FIELD: SYMBOLOGY_HISTORIC_CAPACITY,
    # The stream-order QML is rule-based (no renderer ``attr``), so the preset is
    # what paints that field.
    STREAM_ORDER_FIELD: SYMBOLOGY_STREAM_ORDER,
}

# Colours: (fill, line).  Polygon fills use ``fill`` + an outline in ``line``;
# lines and points use ``line`` for their stroke/marker colour.
DEFAULT_COLOURS = ("#5B9BD5", "#1F4E79")

# Ownership categories → (label, category filter, fill, line).
_OWNERSHIP_PALETTE = {"PVT": ("#2171B5", "#0B3C5D"), "BLM": ("#238B45", "#0B4A1F"), "UND": ("#756BB1", "#3F007D"), "STATE": ("#FFEDA0", "#7F7F7F")}
_OTHER_COLOURS = ("#BDBDBD", "#757575")

# Stream order categories → a light→dark blue ramp.
_STREAM_ORDER_RAMP = ("#DEEBF7", "#9ECAE1", "#6BAED6", "#3182BD", "#08519C")

# Capacity category breaks.  Capacity is a float in 0-40, so the ramp is split
# into 5-unit bins; the last bin includes the upper bound (<= 40).
CAPACITY_BREAKS = (0, 5, 10, 15, 20, 25, 30, 35, 40)

# Capacity categories → a light→dark blue ramp, one colour per bin.
_CAPACITY_RAMP = ("#F7FBFF", "#DEEBF7", "#C6DBEF", "#9ECAE1", "#6BAED6", "#4292C6", "#2171B5", "#084594")


def _make_fill_symbol(colour: str, outline: str) -> QgsFillSymbol:
    """Build the polygon fill symbol used for every DGO style."""
    return QgsFillSymbol.createSimple(
        {
            "color": colour,
            "outline_color": outline,
            "outline_width": "0.3",
        }
    )


def _make_marker_symbol(colour: str, outline: str) -> QgsMarkerSymbol:
    """Build the point marker symbol used for every IGO style."""
    return QgsMarkerSymbol.createSimple(
        {
            "name": "circle",
            "color": colour,
            "outline_color": outline,
            "outline_width": "0.2",
            "size": "2.0",
        }
    )


def _make_symbol(dataset: TileDataset, colour: str, outline: str):
    """Build the symbol for *dataset* — markers for IGOs, fills for DGOs."""
    if dataset.is_point:
        return _make_marker_symbol(colour, outline)
    return _make_fill_symbol(colour, outline)


def _ownership_categories() -> list:
    """Categories for the ownership preset, including an "Other" bucket."""
    categories = []
    for value in OWNERSHIP_VALUES:
        fill, line = _OWNERSHIP_PALETTE.get(value, _OTHER_COLOURS)
        categories.append((value, f'"ownership" = {quote_string(value)}', fill, line))

    other_filter = " AND ".join(f'"ownership" <> {quote_string(value)}' for value in OWNERSHIP_VALUES)
    other_filter = f'("ownership" IS NULL OR ({other_filter}))'
    categories.append(("Other", other_filter, *_OTHER_COLOURS))
    return categories


def _stream_order_categories() -> list:
    """Categories for the stream-order preset, including an "Other" bucket."""
    categories = []
    for index, order in enumerate(STREAM_ORDER_VALUES):
        colour = _STREAM_ORDER_RAMP[index % len(_STREAM_ORDER_RAMP)]
        categories.append((f"Order {order}", f'to_int("stream_order") = {order}', colour, colour))

    other_filter = " AND ".join(f'to_int("stream_order") <> {order}' for order in STREAM_ORDER_VALUES)
    other_filter = f'(to_int("stream_order") IS NULL OR ({other_filter}))'
    categories.append(("Other", other_filter, *_OTHER_COLOURS))
    return categories


def _capacity_categories(field: str) -> list:
    """Categories for a capacity preset: 5-unit bins over 0-40, plus "Other".

    Args:
        field: The capacity field to bin — :data:`CAPACITY_FIELD` for existing
            capacity or :data:`HIST_CAPACITY_FIELD` for historic capacity.
    """
    categories = []

    for index, (lower, upper) in enumerate(zip(CAPACITY_BREAKS, CAPACITY_BREAKS[1:])):
        colour = _CAPACITY_RAMP[index % len(_CAPACITY_RAMP)]
        # Closed on the right for the last bin so a capacity of exactly 40 falls
        # in the top class rather than into "Other".
        upper_operator = "<=" if upper == CAPACITY_MAX else "<"
        category_filter = f'"{field}" >= {lower} AND "{field}" {upper_operator} {upper}'
        categories.append((f"{lower}–{upper}", category_filter, colour, colour))

    other_filter = f'("{field}" IS NULL OR "{field}" < {CAPACITY_MIN} OR "{field}" > {CAPACITY_MAX})'
    categories.append(("Other", other_filter, *_OTHER_COLOURS))
    return categories


def _categories(dataset: TileDataset, mode: str) -> list:
    """Return ``(label, category filter, fill, line)`` tuples for a preset."""
    if mode == SYMBOLOGY_OWNERSHIP:
        return _ownership_categories()
    if mode == SYMBOLOGY_STREAM_ORDER:
        return _stream_order_categories()
    if mode == SYMBOLOGY_EXISTING_CAPACITY:
        return _capacity_categories(CAPACITY_FIELD)
    if mode == SYMBOLOGY_HISTORIC_CAPACITY:
        return _capacity_categories(HIST_CAPACITY_FIELD)
    # Single color: one category with no category filter.
    fill, line = DEFAULT_COLOURS
    return [(dataset.label, "", fill, line)]


def _strip_outer_parens(expression: str) -> str:
    """Drop one pair of parentheses that wraps the whole expression.

    :func:`~.dgos_filters.build_filter_expression` already parenthesises each
    clause, so combining without this step yields ``(a) AND ((b))``.  An
    expression like ``(a) AND (b)`` is left alone because its outer pair does
    not wrap the whole thing.
    """
    if len(expression) < 2 or not (expression.startswith("(") and expression.endswith(")")):
        return expression

    depth = 0
    for index, character in enumerate(expression):
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth == 0 and index != len(expression) - 1:
                return expression
    return expression[1:-1]


def _combine(first: str, second: str) -> str:
    """AND-combine two expressions, tolerating either being empty."""
    if first and second:
        return f"({_strip_outer_parens(first)}) AND ({_strip_outer_parens(second)})"
    return first or second


def legend_entries(dataset_key: str = DEFAULT_DATASET, mode: str = DEFAULT_SYMBOLOGY) -> list:
    """``[(label, fill_colour), …]`` for a preset, used to draw the legend."""
    dataset = dataset_for(dataset_key)
    return [(label, fill) for label, _filter, fill, _line in _categories(dataset, mode)]


def build_styles(dataset_key: str = DEFAULT_DATASET, mode: str = DEFAULT_SYMBOLOGY, filter_expression: str = "") -> list:
    """Build the list of renderer styles for a dataset, narrowed by a filter.

    Args:
        dataset_key: Which service to style (``"igos"`` or ``"dgos"``).
        mode: One of :data:`SYMBOLOGY_MODES`.
        filter_expression: The user's filter (see
            :func:`~.dgos_filters.build_filter_expression`).  Empty means no
            filtering.

    Returns:
        A fresh list of :class:`QgsVectorTileBasicRendererStyle` objects.  Every
        style uses the dataset's one and only geometry type — points for IGOs,
        polygons for DGOs.  The list is built from scratch every time, so it
        never carries rules over from a previous filter.
    """
    dataset = dataset_for(dataset_key)
    styles = []

    for label, category_filter, fill, line in _categories(dataset, mode):
        style = QgsVectorTileBasicRendererStyle(label, SOURCE_LAYER, dataset.geometry_type)
        style.setFilterExpression(_combine(category_filter, filter_expression))
        style.setSymbol(_make_symbol(dataset, fill, line))
        styles.append(style)

    return styles


def build_symbology_styles(dataset_key: str = DEFAULT_DATASET, symbology_style=None, filter_expression: str = "") -> list:
    """Build renderer styles from a parsed QML style (see symbology_library).

    Every QML class becomes one vector-tile style, so the QML's categories,
    ranges or rules carry over as per-style filters.  Colours come from the
    QML, while the geometry type always comes from the dataset: IGOs get
    markers, DGOs get fills.  Falls back to the default preset when the style
    has no classes.
    """
    dataset = dataset_for(dataset_key)
    classes = getattr(symbology_style, "classes", ()) if symbology_style is not None else ()

    styles = []
    for symbology_class in classes:
        style = QgsVectorTileBasicRendererStyle(symbology_class.label, SOURCE_LAYER, dataset.geometry_type)
        style.setFilterExpression(_combine(symbology_class.filter_expression, filter_expression))
        style.setSymbol(_make_symbol(dataset, symbology_class.fill, symbology_class.outline))
        styles.append(style)

    if not styles:
        return build_styles(dataset_key, DEFAULT_SYMBOLOGY, filter_expression)
    return styles


def find_auth_config_id(name: str = AUTH_CONFIG_NAME):
    """Return the id of the QGIS auth config called *name*, or ``None``.

    The tile services require authentication.  The user is expected to have
    already created an authentication configuration with this name in the QGIS
    session; we resolve it to the short id that goes in the layer's URI
    (``authcfg=<id>``).
    """
    auth_manager = QgsApplication.authManager()
    if auth_manager is None:
        return None

    configs = auth_manager.availableAuthMethodConfigs()

    # ``availableAuthMethodConfigs`` normally populates the (non-secret) name,
    # but fall back to loading each config if it does not.
    for config_id, config in configs.items():
        if config.name() == name:
            return config_id

    for config_id in configs:
        config = QgsAuthMethodConfig()
        if auth_manager.loadAuthenticationConfig(config_id, config, False) and config.name() == name:
            return config_id

    # Be forgiving about case/whitespace differences.
    wanted = name.strip().casefold()
    for config_id in configs:
        config = QgsAuthMethodConfig()
        auth_manager.loadAuthenticationConfig(config_id, config, False)
        if config.name().strip().casefold() == wanted:
            return config_id

    return None


def build_layer_uri(dataset_key: str = DEFAULT_DATASET, auth_config_id=None) -> str:
    """Build the vector tile data source URI, including the auth config if known."""
    dataset = dataset_for(dataset_key)
    encoded_url = urllib.parse.quote(dataset.tile_url, safe="/:?={}")
    uri = f"type=xyz&url={encoded_url}"
    if auth_config_id:
        uri += f"&authcfg={auth_config_id}"
    return uri


def get_or_create_layer(dataset_key: str = DEFAULT_DATASET) -> QgsVectorTileLayer:
    """Return the dataset's layer from the project, adding it if needed.

    The layer is wired to the "Reach Production API Key" authentication
    configuration when that config exists in the session.
    """
    global _missing_auth_warned

    dataset = dataset_for(dataset_key)
    project = QgsProject.instance()
    auth_config_id = find_auth_config_id()
    uri = build_layer_uri(dataset.key, auth_config_id)

    if auth_config_id is None and not _missing_auth_warned:
        _missing_auth_warned = True
        Settings().log(
            f'{dataset.label} tile layer: QGIS authentication configuration "{AUTH_CONFIG_NAME}" was not found. The layer will be added without credentials and the tiles will not load.',
            Qgis.Warning,
        )

    for layer in project.mapLayersByName(dataset.label):
        if isinstance(layer, QgsVectorTileLayer):
            # Make sure an existing layer carries the auth config (e.g. it was
            # created before the config existed, or with a stale id).
            if auth_config_id and f"authcfg={auth_config_id}" not in layer.source():
                layer.setDataSource(uri, layer.name(), PROVIDER_KEY)
            elif dataset.key not in layer.source():
                # Wrong service behind the right name (e.g. a layer left over
                # from an older build) — re-point it at the right URL.
                layer.setDataSource(uri, layer.name(), PROVIDER_KEY)
            return layer

    layer = QgsVectorTileLayer(uri, dataset.label)
    project.addMapLayer(layer)
    return layer


def remove_layer(dataset_key: str = DEFAULT_DATASET) -> None:
    """Remove the dataset's layer from the project, if it is there.

    The dock calls this when the user switches datasets: only one of the two
    layers should be on the map at a time, otherwise point and polygon symbols
    are drawn on top of each other.
    """
    dataset = dataset_for(dataset_key)
    project = QgsProject.instance()
    for layer in project.mapLayersByName(dataset.label):
        if isinstance(layer, QgsVectorTileLayer):
            project.removeMapLayer(layer.id())


def apply_style(dataset_key: str = DEFAULT_DATASET, mode: str = DEFAULT_SYMBOLOGY, filter_expression: str = "") -> QgsVectorTileLayer:
    """(Re)apply symbology and filtering to a layer, creating it if needed.

    The new filter rules **replace** the previous ones: the layer's existing
    renderer is cleared and then repopulated in place.  Mutating the current
    renderer (instead of swapping in a new object) keeps QGIS's Symbology panel
    bound to the same renderer, so old rules cannot linger in the UI either.
    """
    layer = get_or_create_layer(dataset_key)
    return _install_styles(layer, build_styles(dataset_key, mode, filter_expression))


def apply_symbology_style(dataset_key: str = DEFAULT_DATASET, symbology_style=None, filter_expression: str = "") -> QgsVectorTileLayer:
    """Apply a parsed QML style to a layer, creating it if needed."""
    layer = get_or_create_layer(dataset_key)
    return _install_styles(layer, build_symbology_styles(dataset_key, symbology_style, filter_expression))


def _install_styles(layer: QgsVectorTileLayer, styles: list) -> QgsVectorTileLayer:
    """Replace the layer's renderer rules with *styles*, in place."""
    renderer = layer.renderer()
    if not isinstance(renderer, QgsVectorTileBasicRenderer):
        renderer = QgsVectorTileBasicRenderer()
        layer.setRenderer(renderer)

    # Drop every rule from the previous filter before installing the new set.
    renderer.setStyles([])
    renderer.setStyles(styles)

    # We mutated the renderer in place, so announce the change explicitly.  This
    # is what QGIS's Symbology panel and the canvas listen to, and it guarantees
    # the old rules are dropped everywhere, not just in the layer object.
    layer.rendererChanged.emit()
    layer.triggerRepaint()
    return layer
