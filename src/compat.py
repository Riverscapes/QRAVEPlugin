# -*- coding: utf-8 -*-
"""Qt 5 / Qt 6 (QGIS 3 / QGIS 4) enum compatibility constants.

In Qt 6 / PyQt6, enums are scoped (e.g. ``Qt.AlignmentFlag.AlignCenter``).
In Qt 5 / PyQt5, they were flat (``Qt.AlignCenter``).  Import the constants
you need from this module rather than accessing ``Qt`` directly.
"""
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QDialogButtonBox, QSizePolicy, QMessageBox, QHeaderView

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


# ── QSizePolicy ───────────────────────────────────────────────────────────────
try:
    SPSZ_FIXED = QSizePolicy.Policy.Fixed
    SPSZ_MINIMUM = QSizePolicy.Policy.Minimum
    SPSZ_PREFERRED = QSizePolicy.Policy.Preferred
    SPSZ_EXPANDING = QSizePolicy.Policy.Expanding
    SPSZ_MINIMUM_EXPANDING = QSizePolicy.Policy.MinimumExpanding
    SPSZ_IGNORED = QSizePolicy.Policy.Ignored
except AttributeError:
    SPSZ_FIXED = QSizePolicy.Fixed  # type: ignore[attr-defined]
    SPSZ_MINIMUM = QSizePolicy.Minimum  # type: ignore[attr-defined]
    SPSZ_PREFERRED = QSizePolicy.Preferred  # type: ignore[attr-defined]
    SPSZ_EXPANDING = QSizePolicy.Expanding  # type: ignore[attr-defined]
    SPSZ_MINIMUM_EXPANDING = QSizePolicy.MinimumExpanding  # type: ignore[attr-defined]
    SPSZ_IGNORED = QSizePolicy.Ignored  # type: ignore[attr-defined]


# ── QDialogButtonBox standard buttons and roles ───────────────────────────────
try:
    DLGBTN_OK = QDialogButtonBox.StandardButton.Ok
    DLGBTN_CANCEL = QDialogButtonBox.StandardButton.Cancel
    DLGBTN_APPLY = QDialogButtonBox.StandardButton.Apply
    DLGBTN_RESET = QDialogButtonBox.StandardButton.Reset
    DLGBTN_ROLE_APPLY = QDialogButtonBox.ButtonRole.ApplyRole
    DLGBTN_ROLE_RESET = QDialogButtonBox.ButtonRole.ResetRole
    DLGBTN_ROLE_HELP = QDialogButtonBox.ButtonRole.HelpRole
except AttributeError:
    DLGBTN_OK = QDialogButtonBox.Ok  # type: ignore[attr-defined]
    DLGBTN_CANCEL = QDialogButtonBox.Cancel  # type: ignore[attr-defined]
    DLGBTN_APPLY = QDialogButtonBox.Apply  # type: ignore[attr-defined]
    DLGBTN_RESET = QDialogButtonBox.Reset  # type: ignore[attr-defined]
    DLGBTN_ROLE_APPLY = QDialogButtonBox.ApplyRole  # type: ignore[attr-defined]
    DLGBTN_ROLE_RESET = QDialogButtonBox.ResetRole  # type: ignore[attr-defined]
    DLGBTN_ROLE_HELP = QDialogButtonBox.HelpRole  # type: ignore[attr-defined]


# ── QMessageBox standard buttons and icons ────────────────────────────────────
try:
    MSGBOX_BTN_YES = QMessageBox.StandardButton.Yes
    MSGBOX_BTN_NO = QMessageBox.StandardButton.No
    MSGBOX_ICON_QUESTION = QMessageBox.Icon.Question
    MSGBOX_ICON_WARNING = QMessageBox.Icon.Warning
    MSGBOX_ICON_CRITICAL = QMessageBox.Icon.Critical
    MSGBOX_ICON_INFORMATION = QMessageBox.Icon.Information
except AttributeError:
    MSGBOX_BTN_YES = QMessageBox.Yes  # type: ignore[attr-defined]
    MSGBOX_BTN_NO = QMessageBox.No  # type: ignore[attr-defined]
    MSGBOX_ICON_QUESTION = QMessageBox.Question  # type: ignore[attr-defined]
    MSGBOX_ICON_WARNING = QMessageBox.Warning  # type: ignore[attr-defined]
    MSGBOX_ICON_CRITICAL = QMessageBox.Critical  # type: ignore[attr-defined]
    MSGBOX_ICON_INFORMATION = QMessageBox.Information  # type: ignore[attr-defined]


# ── QHeaderView resize modes ──────────────────────────────────────────────────
try:
    HEADER_STRETCH = QHeaderView.ResizeMode.Stretch
    HEADER_RESIZE_TO_CONTENTS = QHeaderView.ResizeMode.ResizeToContents
    HEADER_INTERACTIVE = QHeaderView.ResizeMode.Interactive
    HEADER_FIXED = QHeaderView.ResizeMode.Fixed
except AttributeError:
    HEADER_STRETCH = QHeaderView.Stretch  # type: ignore[attr-defined]
    HEADER_RESIZE_TO_CONTENTS = QHeaderView.ResizeToContents  # type: ignore[attr-defined]
    HEADER_INTERACTIVE = QHeaderView.Interactive  # type: ignore[attr-defined]
    HEADER_FIXED = QHeaderView.Fixed  # type: ignore[attr-defined]


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


# ── QGIS API compatibility ────────────────────────────────────────────────────
from qgis.core import QgsTask, QgsVectorFileWriter, QgsMapLayer  # noqa: E402

try:
    # QGIS 4 / PyQt6 — scoped flag form
    QGSTASK_CAN_CANCEL = QgsTask.Flag.CanCancel
except AttributeError:
    # QGIS 3 / PyQt5 — flat flag form
    QGSTASK_CAN_CANCEL = QgsTask.CanCancel  # type: ignore[attr-defined]

try:
    # QGIS 4 / PyQt6
    QGSTASK_COMPLETE = QgsTask.TaskStatus.Complete
except AttributeError:
    # QGIS 3 / PyQt5
    QGSTASK_COMPLETE = QgsTask.Complete  # type: ignore[attr-defined]

try:
    # QGIS 4 / PyQt6
    VFW_NO_ERROR = QgsVectorFileWriter.WriterError.NoError
except AttributeError:
    # QGIS 3 / PyQt5
    VFW_NO_ERROR = QgsVectorFileWriter.NoError  # type: ignore[attr-defined]

try:
    # QGIS 4 / PyQt6
    MAPLAYER_VECTOR = QgsMapLayer.LayerType.VectorLayer
    MAPLAYER_RASTER = QgsMapLayer.LayerType.RasterLayer
except AttributeError:
    # QGIS 3 / PyQt5
    MAPLAYER_VECTOR = QgsMapLayer.VectorLayer  # type: ignore[attr-defined]
    MAPLAYER_RASTER = QgsMapLayer.RasterLayer  # type: ignore[attr-defined]
