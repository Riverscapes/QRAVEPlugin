"""Reusable multi-select list filter control for a map-layer field.

This is the list-based sibling of :class:`~.float_filter_widget.FloatFilterWidget`:
the IGO/DGO dock uses one of these per categorical filter (ownership, land use
intensity, stream order, stream permanence, risk, restoration opportunities and
US state), but there is nothing field-specific in here.  It takes the panel
title, the field it filters and the ``(label, value)`` pairs to offer, shows
the labels, and reports the selected values so a dock can build its filter
expression in one place.

Values are kept in each item's ``USER_ROLE`` data, which lets the visible label
differ from the value the layer stores — the ownership list shows full agency
names but filters on codes such as ``BLM``.

Inside the group box, above the list, sit the field name and the same two tiny
icon buttons the range controls carry: a help button (nothing listens to it
yet) and a paint button that asks the dock to symbolize the layer by this
field.  Selections are multi-select; callers decide what that means (they are
OR'd in :func:`~.classes.dgos_filters.build_filter_expression`).
"""

from __future__ import annotations

from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)

from .compat import QABSTRACTITEMVIEW_MULTI_SELECTION, TEXT_SELECTABLE_BY_MOUSE, USER_ROLE
from .filter_widget_support import deemphasise_label, make_icon_button


class ListFilterWidget(QGroupBox):
    """A titled multi-select list whose rows carry a hidden filter value.

    Args:
        title: Plain-English name shown as the group title, e.g.
            ``"Stream order"``.
        items: ``(label, value)`` pairs, in display order.  The label is what
            the user sees; the value is what lands in the filter expression.
        field_name: The layer field this list filters, shown above the list and
            used as the payload of the header buttons' signals.
        parent: Optional Qt parent.
        min_height: Minimum height of the list, in pixels, so short lists stay
            usable while long ones do not force the whole panel to grow.

    Attributes:
        list_widget: The underlying :class:`QListWidget`, for the rare case a
            caller needs item-level access (tooltips, tests).
        field_label: The small grey field-name label in the header row.

    Signals:
        changed: Emitted whenever the selection changes.
        paint_requested: Emitted with the field name when the paint button is
            clicked, asking the dock to symbolize the layer by that field.
        help_requested: Emitted with the field name when the help button is
            clicked.  Nothing listens to it yet — it is a hook for later.
    """

    changed = pyqtSignal()
    paint_requested = pyqtSignal(str)
    help_requested = pyqtSignal(str)

    def __init__(self, title: str, items, field_name: str = "", parent=None, min_height: int = 100):
        super().__init__(title, parent)

        self._field_name = field_name

        self._list_widget = QListWidget()
        self._list_widget.setSelectionMode(QABSTRACTITEMVIEW_MULTI_SELECTION)
        self._list_widget.setMinimumHeight(min_height)

        for label, value in items:
            item = QListWidgetItem(str(label))
            item.setData(USER_ROLE, value)
            self._list_widget.addItem(item)

        layout = QVBoxLayout(self)
        layout.addLayout(self._build_header())
        layout.addWidget(self._list_widget)

        self._list_widget.itemSelectionChanged.connect(self.changed)
        self.paint_button.clicked.connect(lambda: self.paint_requested.emit(self._field_name))
        self.help_button.clicked.connect(lambda: self.help_requested.emit(self._field_name))

    # ── UI construction ──────────────────────────────────────────────────────
    def _build_header(self) -> QHBoxLayout:
        """Field name on the left, tiny action buttons floated to the right."""
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        self.field_label = QLabel(self._field_name)
        self.field_label.setToolTip(f'Filters the map layer\'s "{self._field_name}" field')
        self.field_label.setTextInteractionFlags(TEXT_SELECTABLE_BY_MOUSE)
        deemphasise_label(self.field_label)
        header.addWidget(self.field_label, 1)

        self.help_button = make_icon_button(self, "help.svg", "Help for this filter (not available yet)")
        header.addWidget(self.help_button)

        self.paint_button = make_icon_button(self, "format-paint.svg", f'Symbolize the layer by "{self._field_name}"')
        header.addWidget(self.paint_button)

        return header

    # ── Public API ───────────────────────────────────────────────────────────
    @property
    def list_widget(self) -> QListWidget:
        """The underlying list widget."""
        return self._list_widget

    @property
    def field_name(self) -> str:
        """The layer field this list filters."""
        return self._field_name

    def values(self) -> list:
        """The filter values of the currently selected rows, in list order."""
        return [item.data(USER_ROLE) for item in self._list_widget.selectedItems()]

    def set_values(self, values) -> None:
        """Select exactly the rows whose value is in *values*.

        Signals are blocked while the selection is rebuilt, so restoring a
        saved state notifies listeners once (callers usually refresh after
        restoring several controls).
        """
        wanted = list(values)
        self._list_widget.blockSignals(True)
        try:
            for row in range(self._list_widget.count()):
                item = self._list_widget.item(row)
                item.setSelected(item.data(USER_ROLE) in wanted)
        finally:
            self._list_widget.blockSignals(False)

    def clear_selection(self) -> None:
        """Deselect every row."""
        self._list_widget.clearSelection()