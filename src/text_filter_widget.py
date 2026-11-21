"""Reusable free-text filter control for a map-layer field.

The third member of the filter-widget family, next to
:class:`~.float_filter_widget.FloatFilterWidget` (min/max ranges) and
:class:`~.list_filter_widget.ListFilterWidget` (multi-select lists).  This one
is a single-line text box: the dock uses it for fields such as ``level_path``
where the user types (part of) a value rather than picking from a fixed set.

An empty box means "no filter", so there is no on/off checkbox — typing is the
switch.  The text box is capped at 128 characters by default.

Like the other filter widgets, the header row shows the field name with the
help and paint buttons floated to the right; the paint button asks the dock to
symbolize the layer by this field.
"""

from __future__ import annotations

from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from .compat import TEXT_SELECTABLE_BY_MOUSE
from .filter_widget_support import deemphasise_label, make_icon_button


class TextFilterWidget(QGroupBox):
    """A titled single-line text filter for one field.

    Args:
        title: Plain-English name shown as the group title, e.g.
            ``"Level Path"``.
        field_name: The layer field the text applies to, e.g. ``"level_path"``.
        max_length: Maximum number of characters the box accepts (128 by
            default, matching the ``level_path`` field's length).
        parent: Optional Qt parent.

    Attributes:
        text_edit: The underlying :class:`QLineEdit`.
        field_label: The small grey field-name label in the header row.

    Signals:
        changed: Emitted whenever the typed text changes.
        paint_requested: Emitted with the field name when the paint button is
            clicked, asking the dock to symbolize the layer by that field.
        help_requested: Emitted with the field name when the help button is
            clicked.  Nothing listens to it yet — it is a hook for later.
    """

    changed = pyqtSignal()
    paint_requested = pyqtSignal(str)
    help_requested = pyqtSignal(str)

    def __init__(self, title: str, field_name: str, max_length: int = 128, parent=None):
        super().__init__(title, parent)

        self._field_name = field_name
        self._max_length = max_length

        self._build_ui()

        self.text_edit.textChanged.connect(self.changed)
        self.paint_button.clicked.connect(lambda: self.paint_requested.emit(self._field_name))
        self.help_button.clicked.connect(lambda: self.help_requested.emit(self._field_name))

    # ── UI construction ──────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Field name on the left, tiny action buttons floated to the right.
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

        layout.addLayout(header)

        self.text_edit = QLineEdit()
        self.text_edit.setMaxLength(self._max_length)
        self.text_edit.setClearButtonEnabled(True)
        self.text_edit.setPlaceholderText(f"Filter by {self._field_name}")
        layout.addWidget(self.text_edit)

    # ── Public API ───────────────────────────────────────────────────────────
    @property
    def field_name(self) -> str:
        """The layer field this text filters."""
        return self._field_name

    @property
    def max_length(self) -> int:
        """Maximum number of characters the box accepts."""
        return self._max_length

    def value(self) -> str:
        """The typed text, stripped; ``""`` means "do not filter"."""
        return self.text_edit.text().strip()

    def set_value(self, text: str) -> None:
        """Set the text without emitting :attr:`changed`."""
        self.text_edit.blockSignals(True)
        try:
            self.text_edit.setText(text or "")
        finally:
            self.text_edit.blockSignals(False)

    def clear(self) -> None:
        """Empty the text box without emitting :attr:`changed`."""
        self.set_value("")