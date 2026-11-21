"""Reusable min/max filter control for a float (or integer) map-layer field.

The IGO/DGO dock uses one of these per capacity field (existing and historic
BRAT capacity), but there is nothing field-specific in here: it takes the
display name, the field it filters and the valid range, and reports a
``(lower, upper)`` pair only while the user has switched it on.

The checkbox to the left of the spin boxes is the on/off switch.  It starts
**unchecked**, because a range filter must be opted into before it narrows the
layer.  While unchecked the spin boxes are disabled and
:meth:`FloatFilterWidget.filter_range` returns ``None``, which callers pass
straight through as "no clause for this field".
"""

from __future__ import annotations

from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
)

from .compat import TEXT_SELECTABLE_BY_MOUSE


class FloatFilterWidget(QGroupBox):
    """A titled lower/upper range control for one numeric field.

    Args:
        title: Plain-English name shown as the group title, e.g.
            ``"Existing Beaver Capacity"``.
        field_name: The layer field the range applies to, e.g.
            ``"brat_capacity"``.  Shown under the title so the user can see
            which attribute the control is wired to.
        minimum: Smallest allowed value for both spin boxes.
        maximum: Largest allowed value for both spin boxes (also the initial
            upper bound).
        parent: Optional Qt parent.

    Attributes:
        checkbox: The on/off switch; unchecked means "do not filter".
        min_spin: The lower bound spin box.
        max_spin: The upper bound spin box.

    Signals:
        changed: Emitted whenever the checkbox or either bound changes, so a
            dock can rebuild its filter expression in one place.  It fires once
            per user action, and once per :meth:`reset`.
    """

    changed = pyqtSignal()

    def __init__(self, title: str, field_name: str, minimum: int, maximum: int, parent=None):
        super().__init__(title, parent)

        if minimum > maximum:
            raise ValueError(f"minimum ({minimum}) must not exceed maximum ({maximum})")

        self._field_name = field_name
        self._minimum = minimum
        self._maximum = maximum
        # Guards against feedback loops and duplicate signals while we move the
        # spin boxes ourselves (and while resetting).
        self._updating = False

        self._build_ui()
        self._connect_signals()
        self._apply_active_state()

    # ── UI construction ──────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.field_label = QLabel(self._field_name)
        self.field_label.setToolTip(f'Filters the map layer\'s "{self._field_name}" field')
        self.field_label.setTextInteractionFlags(TEXT_SELECTABLE_BY_MOUSE)
        layout.addWidget(self.field_label)

        row = QHBoxLayout()

        self.checkbox = QCheckBox("Filter")
        self.checkbox.setToolTip(f'Use "{self._field_name}" to filter the map layer')
        self.checkbox.setChecked(False)
        row.addWidget(self.checkbox)

        row.addWidget(QLabel("Min"))
        self.min_spin = self._make_spin(self._minimum)
        row.addWidget(self.min_spin)

        row.addWidget(QLabel("Max"))
        self.max_spin = self._make_spin(self._maximum)
        row.addWidget(self.max_spin)

        row.addStretch(1)
        layout.addLayout(row)

    def _make_spin(self, value: int) -> QSpinBox:
        """A spin box bounded by this control's range, set to *value*."""
        spin = QSpinBox()
        spin.setRange(self._minimum, self._maximum)
        spin.setValue(value)
        spin.setSingleStep(1)
        return spin

    def _connect_signals(self) -> None:
        self.checkbox.toggled.connect(self._on_active_changed)
        self.min_spin.valueChanged.connect(self._on_min_changed)
        self.max_spin.valueChanged.connect(self._on_max_changed)

    # ── Signal handlers ──────────────────────────────────────────────────────
    def _on_active_changed(self, _active: bool) -> None:
        """Enable/disable the bounds to match the checkbox, then announce it."""
        self._apply_active_state()
        self._emit_changed()

    def _on_min_changed(self, value: int) -> None:
        """Keep the lower bound from passing the upper one, then announce it."""
        if self._updating:
            return
        if value > self.max_spin.value():
            self._set_values(value, value)
        self._emit_changed()

    def _on_max_changed(self, value: int) -> None:
        """Keep the upper bound from passing the lower one, then announce it."""
        if self._updating:
            return
        if value < self.min_spin.value():
            self._set_values(value, value)
        self._emit_changed()

    def _set_values(self, lower: int, upper: int) -> None:
        """Set both bounds without triggering a second ``changed`` signal."""
        self._updating = True
        try:
            self.min_spin.setValue(lower)
            self.max_spin.setValue(upper)
        finally:
            self._updating = False

    def _apply_active_state(self) -> None:
        """Only let the user tune bounds for a field that is switched on."""
        active = self.is_active()
        self.min_spin.setEnabled(active)
        self.max_spin.setEnabled(active)

    def _emit_changed(self) -> None:
        """Emit :attr:`changed` unless we are mid-update."""
        if not self._updating:
            self.changed.emit()

    # ── Public API ───────────────────────────────────────────────────────────
    @property
    def field_name(self) -> str:
        """The layer field this control filters."""
        return self._field_name

    def is_active(self) -> bool:
        """Whether this field is currently used to filter the layer."""
        return self.checkbox.isChecked()

    def filter_range(self):
        """``(lower, upper)`` while active, otherwise ``None``.

        ``None`` is the "no clause for this field" value understood by
        :func:`~.dgos_filters.build_filter_expression`.
        """
        if not self.is_active():
            return None
        return self.min_spin.value(), self.max_spin.value()

    def state(self) -> tuple:
        """``(active, lower, upper)`` — everything needed to restore this control."""
        return self.is_active(), self.min_spin.value(), self.max_spin.value()

    def set_state(self, active: bool, lower: int, upper: int) -> None:
        """Restore a state captured by :meth:`state`, emitting ``changed`` once."""
        self._updating = True
        try:
            self.checkbox.setChecked(bool(active))
            self.min_spin.setValue(lower)
            self.max_spin.setValue(upper)
        finally:
            self._updating = False

        self._apply_active_state()
        self.changed.emit()

    def reset(self) -> None:
        """Switch the filter off and restore the full range, emitting once."""
        self._updating = True
        try:
            self.checkbox.setChecked(False)
            self._set_values(self._minimum, self._maximum)
        finally:
            self._updating = False

        self._apply_active_state()
        self.changed.emit()