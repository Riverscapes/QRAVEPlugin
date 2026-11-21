"""Dockable window for exploring and filtering the IGO/DGO vector tile layers.

A dataset picker at the top of the dock switches between **IGOs** (points) and
**DGOs** (polygons).  The two services differ only in the ``igos``/``dgos``
path segment of the tile URL and in their geometry type; attributes and
authentication are shared, so the rest of the panel serves both.

Below the picker is a tab control: **Filters** holds a :class:`QToolBox` whose
pages group the filter controls by theme, **Symbology** holds the symbology
picker and its legend, **Metrics** holds an empty :class:`QToolBox` with the
same theme panels (ready for future metric widgets), and **About** shows the
where clause currently applied to the layer.

The symbology picker offers the built-in presets and then every point/polygon
map layer the ``rs_metric_engine`` business logic defines.  Pick one and the
dock resolves its QML file (see :mod:`~.classes.symbology_library`), applies the
geometry-appropriate symbol class — markers for IGOs, fills for DGOs — and
shows the QML's classes as a legend below the picker.

===============  =============================================================
Filters panel    Controls
===============  =============================================================
Anthropogenic     Ownership, Land Use Intensity, US state
Hydrology         Stream order, Stream Permanence, Level Path, HUC 10, High
                  and Low Stream Power
Geomorphology     Gradient, Valley Bottom Area, Floodplain Area
Beaver            Existing and historic beaver capacity (opt-in checkbox,
                  off by default), Risk, Restoration or Conservation
                  Opportunities, Limitations
Transportation    Road Density, Rail Density
===============  =============================================================

Every change immediately rebuilds the current layer's renderer with a fresh
filter expression.

The two capacity controls are :class:`FloatFilterWidget` instances, so each
one carries its own field name and an on/off checkbox that decides whether that
field narrows the layer at all.  The categorical lists are
:class:`ListFilterWidget` instances, which pair the label the user sees with the
value the layer stores, and free-text fields use
:class:`TextFilterWidget`.

Above the toolbox sit **Clear filters** (whose label counts the filter inputs
currently switched on) and **Copy filters**, plus **Previous** and **Next**,
which walk a running history of the filter combinations the user has built up.
Every distinct change appends to the history; navigating sets the relevant
controls back to that combination and refreshes the map.
"""

from __future__ import annotations

from typing import NamedTuple

from qgis.core import Qgis
from qgis.PyQt.QtGui import QColor, QIcon, QPainter, QPixmap
from qgis.PyQt.QtWidgets import (
    QApplication,
    QComboBox,
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QToolBox,
    QVBoxLayout,
    QWidget,
)

from .classes.dgos_filters import (
    CAPACITY_FIELD,
    CAPACITY_MAX,
    CAPACITY_MIN,
    GEOMORPHOLOGY_RANGES,
    HIST_CAPACITY_FIELD,
    HUC10_FIELD,
    HYDROLOGY_RANGES,
    LAND_USE_INTENSITY_CLASSES,
    LAND_USE_INTENSITY_FIELD,
    LEVEL_PATH_FIELD,
    LEVEL_PATH_MAX_LENGTH,
    LIMITATION_CLASSES,
    LIMITATION_FIELD,
    TRANSPORTATION_RANGES,
    OPPORTUNITY_FIELD,
    OPPORTUNITY_VALUES,
    OWNERSHIP_FIELD,
    OWNERSHIP_VALUES,
    PERMANENCE_FIELD,
    RISK_FIELD,
    RISK_VALUES,
    STATE_FIELD,
    STREAM_ORDER_FIELD,
    STREAM_ORDER_VALUES,
    STREAM_PERMANENCE_VALUES,
    US_STATES,
    build_filter_expression,
)
from .classes.dgos_layer import (
    AUTH_CONFIG_NAME,
    DATASETS,
    DEFAULT_DATASET,
    DEFAULT_SYMBOLOGY,
    SYMBOLOGY_FIELD_PRESETS,
    SYMBOLOGY_MODES,
    apply_style,
    apply_symbology_style,
    dataset_for,
    find_auth_config_id,
    legend_entries,
    remove_layer,
)
from .classes.settings import Settings
from .classes.symbology_library import (
    RME_PROJECT_TYPE,
    categorized_items,
    field_matches_attribute,
    load_symbology_entries,
    parse_qml,
)
from .compat import (
    FOCUS_POLICY_NONE,
    MSGBOX_ICON_WARNING,
    QABSTRACTITEMVIEW_NO_SELECTION,
    TEXT_SELECTABLE_BY_MOUSE,
)
from .float_filter_widget import FloatFilterWidget
from .list_filter_widget import ListFilterWidget
from .text_filter_widget import TextFilterWidget


#: The theme panels both toolboxes show, in order: the Filters tab fills them
#: with controls, the Metrics tab keeps them empty for now.
PANEL_TITLES = (
    "Anthropogenic",
    "Hydrology",
    "Geomorphology",
    "Beaver",
    "Transportation",
)


class _FilterSnapshot(NamedTuple):
    """The state of every filter control at one point in time.

    Named tuples are hashable and compare by value, which is exactly what the
    dock's filter history needs: duplicates are recognised without any extra
    bookkeeping.
    """

    ownerships: tuple
    land_use: tuple
    stream_orders: tuple
    permanence: tuple
    risks: tuple
    opportunities: tuple
    limitations: tuple
    level_path: str
    huc10: str
    states: tuple
    existing_capacity: tuple
    historic_capacity: tuple
    page_ranges: tuple


class DGOsDockWidget(QDockWidget):
    """Dock that switches between, filters and symbolizes the IGO/DGO layers."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._updating = False

        # Running history of filter combinations (oldest first) plus a cursor.
        # Every distinct user change appends an entry; Previous/Next move the
        # cursor and restore the matching control state.
        self._history = []
        self._history_index = -1
        self._restoring = False

        # Parsed QML files, keyed by path: the dock re-applies symbology on every
        # filter change, so the files themselves are parsed only once.
        self._qml_cache = {}

        self.setObjectName("DGOsDock")
        self.setWindowTitle(dataset_for(DEFAULT_DATASET).label)

        self._build_ui()
        self._connect_signals()
        self.update_filter()

    # ── UI construction ──────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        contents = QWidget()
        layout = QVBoxLayout(contents)

        # Dataset picker: IGOs (points) vs DGOs (polygons).
        dataset_row = QHBoxLayout()
        dataset_row.addWidget(QLabel("Layer:"))
        self.dataset_combo = QComboBox()
        for dataset in DATASETS:
            self.dataset_combo.addItem(dataset.label, dataset.key)
        self.dataset_combo.setCurrentIndex(max(0, self.dataset_combo.findData(DEFAULT_DATASET)))
        dataset_row.addWidget(self.dataset_combo, 1)
        layout.addLayout(dataset_row)

        # ── Tabs: filter groups vs symbology ────────────────────────────────
        self.tabs = QTabWidget()

        # ── Filters tab ──────────────────────────────────────────────────────
        filters_page = QWidget()
        filters_layout = QVBoxLayout(filters_page)

        # Buttons above the toolbox: reset every filter panel, or copy the
        # resulting where clause to the clipboard.
        button_row = QHBoxLayout()
        self.clear_button = QPushButton("Clear filters (0)")
        self.clear_button.setToolTip("Reset every filter in this tab")
        button_row.addWidget(self.clear_button)

        self.copy_button = QPushButton("Copy filters")
        self.copy_button.setToolTip("Copy the current filter expression (QGIS where clause) to the clipboard")
        button_row.addWidget(self.copy_button)

        # Walk the history of filter combinations.
        self.previous_button = QPushButton("Previous")
        self.previous_button.setToolTip("Go back to the previous filter combination")
        button_row.addWidget(self.previous_button)

        self.next_button = QPushButton("Next")
        self.next_button.setToolTip("Go forward to the next filter combination")
        button_row.addWidget(self.next_button)

        button_row.addStretch(1)
        filters_layout.addLayout(button_row)

        # Filter panels, grouped by theme and collapsible one at a time.
        self.toolbox = QToolBox()
        filters_layout.addWidget(self.toolbox, 1)
        panels = {title: self._make_toolbox_page(title) for title in PANEL_TITLES}

        # ── Anthropogenic: ownership + US state ──────────────────────────────
        anthropogenic = panels["Anthropogenic"]
        self.ownership_list = ListFilterWidget("Ownership", self._ownership_items(), field_name=OWNERSHIP_FIELD, min_height=160)
        anthropogenic.addWidget(self.ownership_list)

        # Land use intensity classes come straight from the RME symbology breaks.
        land_use_items = [(label, (lower, upper)) for label, lower, upper in LAND_USE_INTENSITY_CLASSES]
        self.land_use_list = ListFilterWidget("Land Use Intensity", land_use_items, field_name=LAND_USE_INTENSITY_FIELD, min_height=90)
        anthropogenic.addWidget(self.land_use_list)

        state_items = [(f"{abbr}  {name}", abbr) for abbr, name in US_STATES]
        self.state_list = ListFilterWidget("US state", state_items, field_name=STATE_FIELD, min_height=160)
        anthropogenic.addWidget(self.state_list)

        # ── Hydrology: stream order + stream permanence ──────────────────────
        hydrology = panels["Hydrology"]
        order_items = [(str(order), order) for order in STREAM_ORDER_VALUES]
        self.stream_order_list = ListFilterWidget("Stream order", order_items, field_name=STREAM_ORDER_FIELD, min_height=110)
        hydrology.addWidget(self.stream_order_list)

        permanence_items = [(label, code) for label, code in STREAM_PERMANENCE_VALUES]
        self.stream_permanence_list = ListFilterWidget("Stream Permanence", permanence_items, field_name=PERMANENCE_FIELD, min_height=90)
        hydrology.addWidget(self.stream_permanence_list)

        self.level_path_filter = TextFilterWidget("Level Path", LEVEL_PATH_FIELD, max_length=LEVEL_PATH_MAX_LENGTH)
        hydrology.addWidget(self.level_path_filter)

        self.huc10_filter = TextFilterWidget("HUC 10", HUC10_FIELD)
        hydrology.addWidget(self.huc10_filter)

        high_power, low_power = HYDROLOGY_RANGES
        self.high_stream_power_filter = self._make_range_widget(high_power)
        self.low_stream_power_filter = self._make_range_widget(low_power)
        for range_widget in self._hydrology_widgets():
            hydrology.addWidget(range_widget)
        hydrology.addStretch(1)

        # ── Geomorphology: gradient and area ranges ──────────────────────────
        geomorphology = panels["Geomorphology"]
        gradient, valley_bottom, floodplain = GEOMORPHOLOGY_RANGES
        self.gradient_filter = self._make_range_widget(gradient)
        self.valley_bottom_filter = self._make_range_widget(valley_bottom)
        self.floodplain_filter = self._make_range_widget(floodplain)
        for range_widget in self._geomorphology_widgets():
            geomorphology.addWidget(range_widget)
        geomorphology.addStretch(1)

        # ── Beaver: existing + historic capacity over 0-40 ───────────────────
        # Each control is its own widget; the on/off checkbox starts unchecked,
        # so neither field narrows the layer until the user asks for it.
        beaver = panels["Beaver"]
        self.existing_capacity = FloatFilterWidget("Existing Beaver Capacity", CAPACITY_FIELD, CAPACITY_MIN, CAPACITY_MAX)
        self.historic_capacity = FloatFilterWidget("Historic Beaver Capacity", HIST_CAPACITY_FIELD, CAPACITY_MIN, CAPACITY_MAX)
        beaver.addWidget(self.existing_capacity)
        beaver.addWidget(self.historic_capacity)

        risk_items = [(value, value) for value in RISK_VALUES]
        self.risk_list = ListFilterWidget("Risk", risk_items, field_name=RISK_FIELD, min_height=80)
        beaver.addWidget(self.risk_list)

        opportunity_items = [(value, value) for value in OPPORTUNITY_VALUES]
        self.opportunity_list = ListFilterWidget("Restoration or Conservation Opportunities", opportunity_items, field_name=OPPORTUNITY_FIELD, min_height=140)
        beaver.addWidget(self.opportunity_list)

        self.limitation_list = ListFilterWidget("Limitations", self._limitation_items(), field_name=LIMITATION_FIELD, min_height=140)
        beaver.addWidget(self.limitation_list)
        beaver.addStretch(1)

        # ── Transportation: road and rail density ranges ─────────────────────
        transportation = panels["Transportation"]
        road_density, rail_density = TRANSPORTATION_RANGES
        self.road_density_filter = self._make_range_widget(road_density)
        self.rail_density_filter = self._make_range_widget(rail_density)
        for range_widget in self._transportation_widgets():
            transportation.addWidget(range_widget)
        transportation.addStretch(1)

        self.tabs.addTab(filters_page, "Filters")

        # ── Symbology tab ────────────────────────────────────────────────────
        symbology_page = QWidget()
        symbology_layout = QVBoxLayout(symbology_page)

        symbology_row = QHBoxLayout()
        symbology_row.addWidget(QLabel("Symbology:"))
        self.symbology_combo = QComboBox()
        for mode in SYMBOLOGY_MODES:
            self.symbology_combo.addItem(mode, ("preset", mode))
        symbology_row.addWidget(self.symbology_combo, 1)
        symbology_layout.addLayout(symbology_row)

        # Every point/polygon layer in the metric engine's business logic gets a
        # menu item, below the built-in presets.
        self._symbology_entries = load_symbology_entries(RME_PROJECT_TYPE)
        if self._symbology_entries:
            self.symbology_combo.insertSeparator(self.symbology_combo.count())
            for index, entry in enumerate(self._symbology_entries):
                self.symbology_combo.addItem(f"RME \u00b7 {entry.label}", ("business", index))

        self.symbology_combo.setCurrentIndex(0)

        # Legend for whatever symbology is applied, drawn with plain Qt widgets.
        self.legend_label = QLabel("Legend")
        symbology_layout.addWidget(self.legend_label)

        self.legend_list = QListWidget()
        self.legend_list.setSelectionMode(QABSTRACTITEMVIEW_NO_SELECTION)
        self.legend_list.setFocusPolicy(FOCUS_POLICY_NONE)
        symbology_layout.addWidget(self.legend_list, 1)

        self.tabs.addTab(symbology_page, "Symbology")

        # ── Metrics tab: same panels as Filters, still empty ─────────────────
        metrics_page = QWidget()
        metrics_layout = QVBoxLayout(metrics_page)

        self.metrics_toolbox = QToolBox()
        for title in PANEL_TITLES:
            self.metrics_toolbox.addItem(QWidget(), title)
        metrics_layout.addWidget(self.metrics_toolbox, 1)

        self.tabs.addTab(metrics_page, "Metrics")

        # ── About tab: shows the where clause currently applied ─────────────
        about_page = QWidget()
        about_layout = QVBoxLayout(about_page)

        self.filter_label = QLabel()
        self.filter_label.setWordWrap(True)
        self.filter_label.setTextInteractionFlags(TEXT_SELECTABLE_BY_MOUSE)
        about_layout.addWidget(self.filter_label)
        about_layout.addStretch(1)

        self.tabs.addTab(about_page, "About")

        layout.addWidget(self.tabs, 1)

        self.setWidget(contents)

    def _make_toolbox_page(self, title: str) -> QVBoxLayout:
        """Add a named page to the filter toolbox and return its layout."""
        page = QWidget()
        page_layout = QVBoxLayout(page)
        self.toolbox.addItem(page, title)
        return page_layout

    @staticmethod
    def _limitation_items() -> list:
        """Limitation list items: the RME BRAT limitation class strings.

        The labels/values come from the symbology itself (the layer stores the
        long strings), falling back to the constants so the panel is never
        empty if the QML cannot be read.
        """
        items = categorized_items("brat_limitation_rme3")
        return list(items) if items else list(LIMITATION_CLASSES)

    @staticmethod
    def _ownership_items() -> list:
        """Ownership list items: symbology labels mapped to their filter values.

        The labels come from the metric engine's "Dominant Land Ownership"
        symbology, so the filter list reads like its legend, while the value
        stored with each item stays the code the tiles actually carry
        (``BIA``, ``BLM``, …).  Ownership codes that existed before the
        symbology was wired in (and are not in it) are kept at the end so no
        previous filter option is lost.  Falls back to the plain codes when the
        QML cannot be read.
        """
        items = []
        seen = set()

        for label, value in categorized_items("ownership_rme3"):
            items.append((label, value))
            seen.add(value)

        for value in OWNERSHIP_VALUES:
            if value not in seen:
                items.append((value, value))
                seen.add(value)

        return items or [(value, value) for value in OWNERSHIP_VALUES]

    @staticmethod
    def _make_range_widget(config) -> FloatFilterWidget:
        """Build a geomorphology range control from a ``GEOMORPHOLOGY_RANGES`` row."""
        label, field_name, minimum, maximum, decimals, step = config
        return FloatFilterWidget(label, field_name, minimum, maximum, decimals=decimals, step=step)

    def _connect_signals(self) -> None:
        for list_widget in self._filter_lists():
            list_widget.changed.connect(self.update_filter)
            list_widget.paint_requested.connect(self.paint_by_field)
        for text_widget in self._text_widgets():
            text_widget.changed.connect(self.update_filter)
            text_widget.paint_requested.connect(self.paint_by_field)
        for range_widget in self._range_widgets():
            range_widget.changed.connect(self.update_filter)
            range_widget.paint_requested.connect(self.paint_by_field)
        self.symbology_combo.currentTextChanged.connect(self.update_filter)
        self.dataset_combo.currentIndexChanged.connect(self._on_dataset_changed)
        self.clear_button.clicked.connect(self.clear_filters)
        self.copy_button.clicked.connect(self.copy_filters)
        self.previous_button.clicked.connect(self.previous_filters)
        self.next_button.clicked.connect(self.next_filters)

    def _filter_lists(self) -> tuple:
        """The multi-select lists, one per categorical filter."""
        return (
            self.ownership_list,
            self.land_use_list,
            self.stream_order_list,
            self.stream_permanence_list,
            self.risk_list,
            self.opportunity_list,
            self.limitation_list,
            self.state_list,
        )

    def _capacity_widgets(self) -> tuple:
        """The capacity range controls, one per capacity field."""
        return (self.existing_capacity, self.historic_capacity)

    def _geomorphology_widgets(self) -> tuple:
        """The geomorphology range controls, in panel order."""
        return (self.gradient_filter, self.valley_bottom_filter, self.floodplain_filter)

    def _text_widgets(self) -> tuple:
        """The free-text filter controls."""
        return (self.level_path_filter, self.huc10_filter)

    def _hydrology_widgets(self) -> tuple:
        """The stream power range controls, in panel order."""
        return (self.high_stream_power_filter, self.low_stream_power_filter)

    def _transportation_widgets(self) -> tuple:
        """The transportation range controls, in panel order."""
        return (self.road_density_filter, self.rail_density_filter)

    def _page_range_widgets(self) -> tuple:
        """The range controls that live on toolbox pages."""
        return self._geomorphology_widgets() + self._hydrology_widgets() + self._transportation_widgets()

    def _range_widgets(self) -> tuple:
        """Every min/max range control the dock owns."""
        return self._capacity_widgets() + self._page_range_widgets()

    # ── Public API ───────────────────────────────────────────────────────────
    def current_dataset(self):
        """The :class:`TileDataset` currently chosen in the dropdown."""
        return dataset_for(self.dataset_combo.currentData())

    def _on_dataset_changed(self, _index: int) -> None:
        """Swap the on-map layer when the dropdown changes."""
        if self._updating:
            return

        dataset = self.current_dataset()

        # Only one of the two layers should be on the map at a time, otherwise
        # IGO points would be drawn on top of DGO polygons.
        for other in DATASETS:
            if other.key != dataset.key:
                remove_layer(other.key)

        self.setWindowTitle(dataset.label)
        self.update_filter()

    def show_layer(self) -> None:
        """Make sure the current layer exists, then show and focus the dock."""
        self._warn_if_auth_missing()
        self.update_filter()
        self.show()
        self.raise_()

    def _warn_if_auth_missing(self) -> None:
        """Tell the user if the required authentication config is not set up."""
        if find_auth_config_id() is not None:
            return

        box = QMessageBox(self)
        box.setIcon(MSGBOX_ICON_WARNING)
        box.setWindowTitle("IGOs / DGOs authentication")
        box.setText(f'QGIS authentication configuration "{AUTH_CONFIG_NAME}" was not found.')
        box.setInformativeText("The IGO and DGO tile services require it, so the layer will be added but no tiles will load.\n\nAdd the configuration under Settings \u25b8 Options \u25b8 Authentication and try again.")
        box.exec()

    def clear_filters(self) -> None:
        """Deselect everything and refresh once."""
        self._updating = True
        try:
            for list_widget in self._filter_lists():
                list_widget.clear_selection()
            for text_widget in self._text_widgets():
                text_widget.clear()
            for range_widget in self._range_widgets():
                range_widget.reset()
        finally:
            self._updating = False
        self.update_filter()

    # ── Filter history ───────────────────────────────────────────────────────
    def previous_filters(self) -> None:
        """Restore the previous filter combination from the history."""
        self._navigate_history(-1)

    def next_filters(self) -> None:
        """Restore the next filter combination from the history."""
        self._navigate_history(1)

    def _navigate_history(self, step: int) -> None:
        """Move the history cursor by *step* and reapply that combination."""
        index = self._history_index + step
        if not 0 <= index < len(self._history):
            self._update_history_buttons()
            return

        self._history_index = index
        self._apply_snapshot(self._history[index])
        self._update_history_buttons()

    def _current_snapshot(self) -> _FilterSnapshot:
        """Capture every filter control's current setting."""
        return _FilterSnapshot(
            ownerships=tuple(self.ownership_list.values()),
            land_use=tuple(self.land_use_list.values()),
            stream_orders=tuple(self.stream_order_list.values()),
            permanence=tuple(self.stream_permanence_list.values()),
            risks=tuple(self.risk_list.values()),
            opportunities=tuple(self.opportunity_list.values()),
            limitations=tuple(self.limitation_list.values()),
            level_path=self.level_path_filter.value(),
            huc10=self.huc10_filter.value(),
            states=tuple(self.state_list.values()),
            existing_capacity=self.existing_capacity.state(),
            historic_capacity=self.historic_capacity.state(),
            page_ranges=tuple(range_widget.state() for range_widget in self._page_range_widgets()),
        )

    def _apply_snapshot(self, snapshot: _FilterSnapshot) -> None:
        """Put the controls back into *snapshot* and refresh the map once."""
        self._restoring = True
        self._updating = True
        try:
            self.ownership_list.set_values(snapshot.ownerships)
            self.land_use_list.set_values(snapshot.land_use)
            self.stream_order_list.set_values(snapshot.stream_orders)
            self.stream_permanence_list.set_values(snapshot.permanence)
            self.risk_list.set_values(snapshot.risks)
            self.opportunity_list.set_values(snapshot.opportunities)
            self.limitation_list.set_values(snapshot.limitations)
            self.level_path_filter.set_value(snapshot.level_path)
            self.huc10_filter.set_value(snapshot.huc10)
            self.state_list.set_values(snapshot.states)
            self.existing_capacity.set_state(*snapshot.existing_capacity)
            self.historic_capacity.set_state(*snapshot.historic_capacity)
            for range_widget, state in zip(self._page_range_widgets(), snapshot.page_ranges):
                range_widget.set_state(*state)
        finally:
            self._updating = False

        try:
            # ``_restoring`` keeps this refresh out of the history, otherwise
            # navigating would append the state we just restored.
            self.update_filter()
        finally:
            self._restoring = False

    def _record_history(self) -> None:
        """Append the current controls to the history unless they are already there."""
        if self._restoring:
            return

        snapshot = self._current_snapshot()

        if self._history and snapshot == self._history[self._history_index]:
            self._update_history_buttons()
            return

        # Editing from a past state abandons the forward entries, like undo.
        del self._history[self._history_index + 1 :]
        self._history.append(snapshot)
        self._history_index = len(self._history) - 1
        self._update_history_buttons()

    def _update_history_buttons(self) -> None:
        """Enable Previous/Next to match where the cursor sits in the history."""
        self.previous_button.setEnabled(self._history_index > 0)
        self.next_button.setEnabled(0 <= self._history_index < len(self._history) - 1)

    def copy_filters(self) -> None:
        """Copy the current filter expression to the clipboard.

        The clipboard gets exactly what the renderer filters with — the QGIS
        where clause — so it can be pasted into the layer's expression dialog
        or a bug report.  An empty selection copies an empty string, which is
        consistent with "no filtering".
        """
        clipboard = QApplication.clipboard()
        if clipboard is None:
            return
        clipboard.setText(self._current_expression())

    def _current_expression(self) -> str:
        """The QGIS expression implied by the current filter selections."""
        return build_filter_expression(
            ownerships=self.ownership_list.values(),
            land_use=self.land_use_list.values(),
            stream_orders=self.stream_order_list.values(),
            permanence=self.stream_permanence_list.values(),
            risks=self.risk_list.values(),
            opportunities=self.opportunity_list.values(),
            limitations=self.limitation_list.values(),
            level_path=self.level_path_filter.value(),
            huc10=self.huc10_filter.value(),
            states=self.state_list.values(),
            capacity_range=self.existing_capacity.filter_range(),
            hist_capacity_range=self.historic_capacity.filter_range(),
            range_filters=self._active_range_filters(),
        )

    def _active_range_filters(self) -> list:
        """``(field, bounds, minimum, maximum)`` for every switched-on page range."""
        return [
            (range_widget.field_name, range_widget.filter_range(), *range_widget.full_range())
            for range_widget in self._page_range_widgets()
            if range_widget.filter_range() is not None
        ]

    def update_filter(self) -> None:
        """Rebuild the current layer's renderer from the current selections."""
        if self._updating:
            return

        expression = self._current_expression()

        dataset = self.current_dataset()
        self._apply_symbology(dataset, expression)

        self.filter_label.setText(f"{dataset.label} filter: {expression}" if expression else f"{dataset.label} filter: (none — showing all features)")

        self._update_clear_label()
        self._record_history()

    def _filter_count(self) -> int:
        """How many filter inputs are currently switched on.

        Every selected list value counts once, and every capacity field whose
        checkbox is ticked counts once — a min/max range is a single filter
        however wide it is.
        """
        count = sum(len(list_widget.values()) for list_widget in self._filter_lists())
        count += sum(1 for text_widget in self._text_widgets() if text_widget.value())
        count += sum(1 for range_widget in self._range_widgets() if range_widget.is_active())
        return count

    def _update_clear_label(self) -> None:
        """Keep the Clear filters button's count in step with the controls."""
        self.clear_button.setText(f"Clear filters ({self._filter_count()})")

    # ── Symbology ────────────────────────────────────────────────────────────
    def paint_by_field(self, field_name: str) -> None:
        """Switch the symbology picker to whatever paints *field_name*.

        Called by a range control's paint button.  Business-logic QML files win
        (they carry the real class breaks); the built-in presets are the
        fallback for fields no QML covers.  When nothing matches, the dock
        keeps its current symbology and logs why.
        """
        if not field_name:
            return

        target = self._symbology_for_field(field_name)
        if target is None:
            Settings().log(f'No symbology found for the field "{field_name}".', Qgis.Info)
            return

        for index in range(self.symbology_combo.count()):
            if self.symbology_combo.itemData(index) == target:
                self.symbology_combo.setCurrentIndex(index)
                return

    def _symbology_for_field(self, field_name: str):
        """The ``("preset", mode)``/``("business", index)`` that paints a field."""
        dataset = self.current_dataset()

        for index, entry in enumerate(self._symbology_entries):
            style = self._business_style(entry, dataset.is_point)
            if style is not None and field_matches_attribute(field_name, style.attr):
                return "business", index

        preset = SYMBOLOGY_FIELD_PRESETS.get(field_name)
        if preset is not None:
            return "preset", preset

        return None

    def _current_symbology(self) -> tuple:
        """``("preset", mode)`` or ``("business", entry_index)`` for the combo."""
        data = self.symbology_combo.currentData()
        if isinstance(data, tuple) and len(data) == 2:
            return data
        return "preset", self.symbology_combo.currentText() or DEFAULT_SYMBOLOGY

    def _business_style(self, entry, is_point: bool):
        """Parse (and cache) the QML for *entry* that suits the active geometry."""
        qml_path = entry.qml_for(is_point)
        if not qml_path:
            return None

        if qml_path not in self._qml_cache:
            try:
                self._qml_cache[qml_path] = parse_qml(qml_path)
            except Exception as error:  # a broken QML must not break the dock
                self._qml_cache[qml_path] = None
                Settings().log(f"Could not read symbology file {qml_path}: {error}", Qgis.Warning)

        return self._qml_cache[qml_path]

    def _apply_symbology(self, dataset, expression: str) -> None:
        """Apply the chosen symbology (preset or business-logic QML) and its legend."""
        kind, payload = self._current_symbology()

        if kind == "business":
            style = self._business_style(self._symbology_entries[payload], dataset.is_point)
            if style is not None:
                apply_symbology_style(dataset.key, style, expression)
                self._render_legend(style.legend)
                return

            # Missing/unreadable QML: fall back to the single-colour preset.
            payload = DEFAULT_SYMBOLOGY

        apply_style(dataset.key, payload, expression)
        self._render_legend(legend_entries(dataset.key, payload))

    def _render_legend(self, entries) -> None:
        """Fill the legend list with a colour swatch and label per class."""
        self.legend_list.clear()
        for label, colour in entries:
            item = QListWidgetItem(QIcon(self._colour_swatch(colour)), str(label))
            item.setToolTip(f"{label} ({colour})")
            self.legend_list.addItem(item)

        count = len(entries)
        self.legend_label.setText(f"Legend ({count})" if count else "Legend")

    @staticmethod
    def _colour_swatch(colour: str) -> QPixmap:
        """A small outlined colour square for a legend row."""
        swatch = QColor(colour)
        if not swatch.isValid():
            swatch = QColor("#BDBDBD")

        pixmap = QPixmap(14, 14)
        pixmap.fill(swatch)

        painter = QPainter(pixmap)
        try:
            painter.setPen(QColor("#404040"))
            painter.drawRect(0, 0, pixmap.width() - 1, pixmap.height() - 1)
        finally:
            painter.end()
        return pixmap

