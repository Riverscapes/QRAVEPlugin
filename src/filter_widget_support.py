"""Shared chrome for the dock's filter widgets.

Both :class:`~.float_filter_widget.FloatFilterWidget` and
:class:`~.list_filter_widget.ListFilterWidget` pair their field name with two
tiny icon-only buttons.  Keeping the sizes, the quiet label styling and the
icon-button factory in one place means the two controls cannot drift apart.
"""

from __future__ import annotations

from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtWidgets import QLabel, QPushButton

from .icon_utils import qrave_icon

#: Size of the little header buttons, and of their icons (which sit inside a
#: flat button, so they can be nearly the full size).
SMALL_BUTTON_SIZE = 16
SMALL_ICON_SIZE = 14

#: The field-name label is deliberately quiet: one step smaller than the group
#: title and dark grey, so it reads as supporting information rather than a
#: heading.
FIELD_LABEL_COLOUR = "#555555"
FIELD_LABEL_POINT_STEP = 1.0


def make_icon_button(parent, icon_alias: str, tooltip: str) -> QPushButton:
    """A 16x16 flat button whose only content is a 14x14 icon."""
    button = QPushButton(parent)
    button.setIcon(qrave_icon(icon_alias))
    button.setIconSize(QSize(SMALL_ICON_SIZE, SMALL_ICON_SIZE))
    button.setFixedSize(SMALL_BUTTON_SIZE, SMALL_BUTTON_SIZE)
    button.setFlat(True)
    button.setToolTip(tooltip)
    return button


def deemphasise_label(label: QLabel) -> None:
    """Make a supporting label one point smaller and dark grey.

    Font metrics are taken from the label's own font so it still follows the
    user's QGIS font size.
    """
    label_font = label.font()
    if label_font.pointSizeF() > 0:
        label_font.setPointSizeF(max(7.0, label_font.pointSizeF() - FIELD_LABEL_POINT_STEP))
    elif label_font.pixelSize() > 0:
        label_font.setPixelSize(max(9, label_font.pixelSize() - 2))
    label.setFont(label_font)

    # A stylesheet rather than a palette: the same call works on Qt 5 and
    # Qt 6 without the scoped-enum dance.
    label.setStyleSheet(f"color: {FIELD_LABEL_COLOUR};")