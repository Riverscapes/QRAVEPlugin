from __future__ import annotations

from typing import ClassVar

from qgis.PyQt.QtCore import pyqtSlot
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QMenu

from ..icon_utils import qrave_icon


class ContextMenu(QMenu):
    MENUS: ClassVar[dict] = {
        "EXPAND_ALL": (
            "Expand All Child Nodes",
            ":/plugins/qrave_toolbar/expand.png",
        ),
        "ZOOM_TO_PROJECT": (
            "Zoom Map to Project",
            ":/plugins/qrave_toolbar/bounds",
        ),
        "ADD_PROJECT_BOUNDS_TO_MAP": (
            "Add Project Bounds to Map",
            ":/plugins/qrave_toolbar/AddToMap.png",
        ),
        "COLLAPSE_ALL": (
            "Collapse All Child Nodes",
            ":/plugins/qrave_toolbar/collapse.png",
        ),
        "UPLOAD_PROJECT": (
            "Upload Project to Data Exchange",
            ":/plugins/qrave_toolbar/upload_project.svg",
        ),
        "ADD_ALL_TO_MAP": (
            "Add All Layers to Map",
            ":/plugins/qrave_toolbar/AddToMap.png",
        ),
        "ADD_TO_MAP": (
            "Add to Map",
            ":/plugins/qrave_toolbar/AddToMap.png",
        ),
        "BROWSE_PROJECT_FOLDER": ("Browse Project Folder", ":/plugins/qrave_toolbar/BrowseFolder.png"),
        "OPEN_FILE": ("Open File", ":/plugins/qrave_toolbar/open.svg"),
        "BROWSE_FOLDER": ("Browse Folder", ":/plugins/qrave_toolbar/BrowseFolder.png"),
        "VIEW_WEB_SOURCE": ("View Source Riverscapes Project", ":/plugins/qrave_toolbar/RaveAddIn_16px.png"),
        "VIEW_LAYER_META": ("View Layer Metadata", ":/plugins/qrave_toolbar/metadata.png"),
        "VIEW_PROJECT_META": ("View Project Metadata", ":/plugins/qrave_toolbar/metadata.png"),
        "REFRESH_PROJECT_HIERARCHY": ("Refresh Project Hierarchy", ":/plugins/qrave_toolbar/refresh.png"),
        "CUSTOMIZE_PROJECT_HIERARCHY": ("Customize Project Hierarchy", ":/plugins/qrave_toolbar/tree.png"),
        "CLOSE_PROJECT": ("Close Project", ":/plugins/qrave_toolbar/close.png"),
        "DOWNLOAD_ADD_PROJECT": ("Download or Update Project", ":/plugins/qrave_toolbar/download.svg"),
        "WAREHOUSE_VIEW": ("View in Data Exchange", ":/plugins/qrave_toolbar/data-exchange-icon.svg"),
        "BROWSE_REMOTE_DATA_EXCHANGE": ("Browse Remote Data Exchange", ":/plugins/qrave_toolbar/data-exchange-icon.svg"),
        "RETRY_LOAD": ("Reload Project", ":/plugins/qrave_toolbar/refresh.png"),
        "OPEN_REPORT": ("Open Report", ":/plugins/qrave_toolbar/description.svg"),
        "ADD_WEB_TILES_TO_MAP": (
            "Add WebTiles to Map",
            ":/plugins/qrave_toolbar/data-exchange-icon.svg",
        ),
    }

    # def __init__(self):
    #     self.menu = ContextMenu()
    #     super().__init__(self)

    def addCustomAction(self, icon: QIcon, text: str, slot: pyqtSlot = None, enabled: bool = True) -> None:
        action = super().addAction(icon, text)
        action.setEnabled(enabled)

        if slot is not None:
            action.triggered.connect(slot)

    def addAction(self, lookup: str, slot: pyqtSlot = None, enabled: bool = True) -> None:
        if lookup not in self.MENUS:
            raise Exception("Menu not found")
        action_text = self.MENUS[lookup]
        _alias = action_text[1].replace(":/plugins/qrave_toolbar/", "")
        action = super().addAction(qrave_icon(_alias), action_text[0])
        action.setEnabled(enabled)

        if slot is not None:
            action.triggered.connect(slot)
