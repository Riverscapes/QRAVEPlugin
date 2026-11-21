"""Reusable min/max filter control for a float (or integer) map-layer field.

The IGO/DGO dock uses one of these per capacity field (existing and historic
BRAT capacity) and per geomorphology metric (gradient, valley bottom area,
floodplain area), but there is nothing field-specific in here: it takes the
display name, the field it filters, the valid range and how many decimals to
show, and reports a ``(lower, upper)`` pair only while the user has switched
it on.

The checkbox to the left of the spin boxes is the on/off switch.  It starts
**unchecked**, because a range filter must be opted into before it narrows the
layer.  While unchecked the spin boxes are disabled and
:meth:`FloatFilterWidget.filter_range` returns ``None``, which callers pass
straight through as "no clause for this field".

The header row pairs the field name with two 16x16 icon buttons floated to the
right: a help button (nothing listens to it yet) and a paint button that asks
the dock to symbolize the layer by this field.
"""

from __future__ import annotations

from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from .compat import TEXT_SELECTABLE_BY_MOUSE
from .filter_widget_support import deemphasise_label, make_icon_button


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
        decimals: Digits shown after the decimal point (``0`` for counts such
            as beaver capacity, ``3`` for a gradient).
        step: Increment used by the spin-box arrows.

    Attributes:
        checkbox: The on/off switch; unchecked means "do not filter".
        min_spin: The lower bound spin box.
        max_spin: The upper bound spin box.

    Signals:
        changed: Emitted whenever the checkbox or either bound changes, so a
            dock can rebuild its filter expression in one place.  It fires once
            per user action, and once per :meth:`reset`.
        paint_requested: Emitted with the field name when the paint button is
            clicked, asking the dock to symbolize the layer by that field.
        help_requested: Emitted with the field name when the help button is
            clicked.  Nothing listens to it yet — it is a hook for later.
    """

    changed = pyqtSignal()
    paint_requested = pyqtSignal(str)
    help_requested = pyqtSignal(str)

    def __init__(self, title: str, field_name: str, minimum: float, maximum: float, parent=None, decimals: int = 0, step: float = 1.0):
        super().__init__(title, parent)

        if minimum > maximum:
            raise ValueError(f"minimum ({minimum}) must not exceed maximum ({maximum})")

        self._field_name = field_name
        self._minimum = minimum
        self._maximum = maximum
        self._decimals = decimals
        self._step = step
        # Guards against feedback loops and duplicate signals while we move the
        # spin boxes ourselves (and while resetting).
        self._updating = False

        self._build_ui()
        self._connect_signals()
        self._apply_active_state()

    # ── UI construction ──────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Field name on the left, tiny action buttons floated to the right.
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        self.field_label = QLabel(self._field_name)
        self.field_label.setToolTip(f'Filters the map layer\'s "{self._field_name}" field')
        self.field_label.setTextInteractionFlags(TEXT_SELECTABLE_BY_MOUSE)
        self._deemphasise_field_label()
        header.addWidget(self.field_label, 1)

        self.help_button = self._make_icon_button("help.svg", "Help for this filter (not available yet)")
        header.addWidget(self.help_button)

        self.paint_button = self._make_icon_button("format-paint.svg", f'Symbolize the layer by "{self._field_name}"')
        header.addWidget(self.paint_button)

        layout.addLayout(header)

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

    def _make_icon_button(self, icon_alias: str, tooltip: str) -> QPushButton:
        """A 16x16 flat button whose only content is an icon."""
        return make_icon_button(self, icon_alias, tooltip)

    def _deemphasise_field_label(self) -> None:
        """Make the field name one point smaller and dark grey (see support)."""
        deemphasise_label(self.field_label)

    def _make_spin(self, value: float) -> QDoubleSpinBox:
        """A spin box bounded by this control's range, set to *value*."""
        spin = QDoubleSpinBox()
        spin.setDecimals(self._decimals)
        spin.setRange(self._minimum, self._maximum)
        spin.setValue(value)
        spin.setSingleStep(self._step)
        return spin

    def _connect_signals(self) -> None:
        self.checkbox.toggled.connect(self._on_active_changed)
        self.min_spin.valueChanged.connect(self._on_min_changed)
        self.max_spin.valueChanged.connect(self._on_max_changed)
        self.paint_button.clicked.connect(lambda: self.paint_requested.emit(self._field_name))
        self.help_button.clicked.connect(lambda: self.help_requested.emit(self._field_name))

    # ── Signal handlers ──────────────────────────────────────────────────────
    def _on_active_changed(self, _active: bool) -> None:
        """Enable/disable the bounds to match the checkbox, then announce it."""
        self._apply_active_state()
        self._emit_changed()

    def _on_min_changed(self, value: float) -> None:
        """Keep the lower bound from passing the upper one, then announce it."""
        if self._updating:
            return
        if value > self.max_spin.value():
            self._set_values(value, value)
        self._emit_changed()

    def _on_max_changed(self, value: float) -> None:
        """Keep the upper bound from passing the lower one, then announce it."""
        if self._updating:
            return
        if value < self.min_spin.value():
            self._set_values(value, value)
        self._emit_changed()

    def _set_values(self, lower: float, upper: float) -> None:
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

    def full_range(self) -> tuple:
        """``(minimum, maximum)`` — the bounds this control was built with."""
        return self._minimum, self._maximum

    def state(self) -> tuple:
        """``(active, lower, upper)`` — everything needed to restore this control."""
        return self.is_active(), self.min_spin.value(), self.max_spin.value()

    def set_state(self, active: bool, lower: float, upper: float) -> None:
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