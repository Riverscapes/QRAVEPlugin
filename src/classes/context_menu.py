from qgis.PyQt.QtWidgets import QDockWidget, QWidget, QTreeView, QVBoxLayout, QMenu, QAction
from qgis.PyQt.QtCore import pyqtSlot, QModelIndex
from qgis.PyQt.QtGui import QIcon, QStandardItem


class ContextMenu(QMenu):
    MENUS = {
        'EXPAND_ALL': (
            "Expand All Child Nodes",
            ':/plugins/qrave_toolbar/expand.png',
        ),
        'COLLAPSE_ALL': (
            "Collapse All Child Nodes",
            ':/plugins/qrave_toolbar/collapse.png',
        ),
        'UPLOAD_PROJECT': (
            "Upload Project to Data Exchange",
            ':/plugins/qrave_toolbar/upload_project.svg',
        ),
        'ADD_ALL_TO_MAP': (
            "Add All Layers To The Map",
            ':/plugins/qrave_toolbar/AddToMap.png',
        ),
        'ADD_TO_MAP': (
            "Add to Map",
            ':/plugins/qrave_toolbar/AddToMap.png',
        ),
        'BROWSE_PROJECT_FOLDER': (
            'Browse Project Folder',
            ':/plugins/qrave_toolbar/BrowseFolder.png'
        ),
        'OPEN_FILE': (
            'Open File',
            ':/plugins/qrave_toolbar/open.svg'
        ),
        'BROWSE_FOLDER': (
            'Browse Folder',
            ':/plugins/qrave_toolbar/BrowseFolder.png'
        ),
        'VIEW_WEB_SOURCE': (
            'View Source Riverscapes Project',
            ':/plugins/qrave_toolbar/RaveAddIn_16px.png'
        ),
        'VIEW_LAYER_META': (
            'View Layer Metadata',
            ':/plugins/qrave_toolbar/metadata.png'
        ),
        'VIEW_PROJECT_META': (
            'View Project Metadata',
            ':/plugins/qrave_toolbar/metadata.png'
        ),
        'REFRESH_PROJECT_HIERARCHY': (
            'Refresh Project Hierarchy',
            ':/plugins/qrave_toolbar/refresh.png'
        ),
        'CUSTOMIZE_PROJECT_HIERARCHY': (
            'Customize Project Hierarchy',
            ':/plugins/qrave_toolbar/tree.png'
        ),
        'CLOSE_PROJECT': (
            'Close Project',
            ':/plugins/qrave_toolbar/close.png'
        ),
        'WAREHOUSE_VIEW': (
            'View in Data Exchange',
            ':/plugins/qrave_toolbar/data-exchange-icon.svg'
        ),
    }

    # def __init__(self):
    #     self.menu = ContextMenu()
    #     super().__init__(self)

    def addCustomAction(self, icon: QIcon, text: str, slot: pyqtSlot = None, enabled=True):
        action = super().addAction(icon, text)
        action.setEnabled(enabled)

        if slot is not None:
            action.triggered.connect(slot)

    def addAction(self, lookup: str, slot: pyqtSlot = None, enabled=True):
        if lookup not in self.MENUS:
            raise Exception('Menu not found')
        action_text = self.MENUS[lookup]
        action = super().addAction(QIcon(action_text[1]), action_text[0])
        action.setEnabled(enabled)

        if slot is not None:
            action.triggered.connect(slot)
