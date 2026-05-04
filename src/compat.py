# -*- coding: utf-8 -*-
"""Qt 5 / Qt 6 (QGIS 3 / QGIS 4) enum compatibility constants.

In Qt 6 / PyQt6, enums are scoped (e.g. ``Qt.AlignmentFlag.AlignCenter``).
In Qt 5 / PyQt5, they were flat (``Qt.AlignCenter``).  Import the constants
you need from this module rather than accessing ``Qt`` directly.
"""
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QDialogButtonBox

try:
    # ── Qt 6 / PyQt6 ──────────────────────────────────────────────────────
    ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter
    ALIGN_LEFT = Qt.AlignmentFlag.AlignLeft
    ALIGN_RIGHT = Qt.AlignmentFlag.AlignRight
    ALIGN_VCENTER = Qt.AlignmentFlag.AlignVCenter
    RICH_TEXT = Qt.TextFormat.RichText
    CHECKED = Qt.CheckState.Checked
    UNCHECKED = Qt.CheckState.Unchecked
    ITEM_FLAG_CHECKABLE = Qt.ItemFlag.ItemIsUserCheckable
    ITEM_FLAG_ENABLED = Qt.ItemFlag.ItemIsEnabled
    HORIZONTAL = Qt.Orientation.Horizontal
    VERTICAL = Qt.Orientation.Vertical
    ASCENDING_ORDER = Qt.SortOrder.AscendingOrder
    LEFT_DOCK = Qt.DockWidgetArea.LeftDockWidgetArea
    RIGHT_DOCK = Qt.DockWidgetArea.RightDockWidgetArea
    TOOL_BTN_TEXT_BESIDE = Qt.ToolButtonStyle.ToolButtonTextBesideIcon
    SCROLL_BAR_ALWAYS_OFF = Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    TEXT_BROWSER_INTERACTION = Qt.TextInteractionFlag.TextBrowserInteraction
    FOREGROUND_ROLE = Qt.ItemDataRole.ForegroundRole
    COLOR_BLUE = Qt.GlobalColor.blue
    COLOR_GRAY = Qt.GlobalColor.gray
    DIALOG_BTN_CLOSE = QDialogButtonBox.StandardButton.Close
    CUSTOM_CONTEXT_MENU = Qt.ContextMenuPolicy.CustomContextMenu
except AttributeError:
    # ── Qt 5 / PyQt5 ──────────────────────────────────────────────────────
    ALIGN_CENTER = Qt.AlignCenter  # type: ignore[attr-defined]
    ALIGN_LEFT = Qt.AlignLeft  # type: ignore[attr-defined]
    ALIGN_RIGHT = Qt.AlignRight  # type: ignore[attr-defined]
    ALIGN_VCENTER = Qt.AlignVCenter  # type: ignore[attr-defined]
    RICH_TEXT = Qt.RichText  # type: ignore[attr-defined]
    CHECKED = Qt.Checked  # type: ignore[attr-defined]
    UNCHECKED = Qt.Unchecked  # type: ignore[attr-defined]
    ITEM_FLAG_CHECKABLE = Qt.ItemIsUserCheckable  # type: ignore[attr-defined]
    ITEM_FLAG_ENABLED = Qt.ItemIsEnabled  # type: ignore[attr-defined]
    HORIZONTAL = Qt.Horizontal  # type: ignore[attr-defined]
    VERTICAL = Qt.Vertical  # type: ignore[attr-defined]
    ASCENDING_ORDER = Qt.AscendingOrder  # type: ignore[attr-defined]
    LEFT_DOCK = Qt.LeftDockWidgetArea  # type: ignore[attr-defined]
    RIGHT_DOCK = Qt.RightDockWidgetArea  # type: ignore[attr-defined]
    TOOL_BTN_TEXT_BESIDE = Qt.ToolButtonTextBesideIcon  # type: ignore[attr-defined]
    SCROLL_BAR_ALWAYS_OFF = Qt.ScrollBarAlwaysOff  # type: ignore[attr-defined]
    TEXT_BROWSER_INTERACTION = Qt.TextBrowserInteraction  # type: ignore[attr-defined]
    FOREGROUND_ROLE = Qt.ForegroundRole  # type: ignore[attr-defined]
    COLOR_BLUE = Qt.blue  # type: ignore[attr-defined]
    COLOR_GRAY = Qt.gray  # type: ignore[attr-defined]
    DIALOG_BTN_CLOSE = QDialogButtonBox.Close  # type: ignore[attr-defined]
    CUSTOM_CONTEXT_MENU = Qt.CustomContextMenu  # type: ignore[attr-defined]


from qgis.PyQt.QtNetwork import QNetworkRequest, QNetworkReply

try:
    # Qt 6 / PyQt6
    NET_CONTENT_LENGTH_HEADER = QNetworkRequest.KnownHeaders.ContentLengthHeader
    NET_OP_CANCELED_ERROR = QNetworkReply.NetworkError.OperationCanceledError
    NET_NO_ERROR = QNetworkReply.NetworkError.NoError
except AttributeError:
    # Qt 5 / PyQt5
    NET_CONTENT_LENGTH_HEADER = QNetworkRequest.ContentLengthHeader  # type: ignore[attr-defined]
    NET_OP_CANCELED_ERROR = QNetworkReply.OperationCanceledError  # type: ignore[attr-defined]
    NET_NO_ERROR = QNetworkReply.NoError  # type: ignore[attr-defined]
