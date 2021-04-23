# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QRAVEDockWidget
                                 A QGIS plugin
 QRAVE Dock Widget
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2021-04-12
        git sha              : $Format:%H$
        copyright            : (C) 2021 by NAR
        email                : info@northarrowresearch.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from __future__ import annotations
from typing import List, Dict
import os


from qgis.PyQt import uic
from qgis.core import Qgis, QgsRasterLayer, QgsVectorLayer, QgsProject
from qgis.PyQt.QtGui import QStandardItemModel, QStandardItem, QIcon, QDesktopServices
from qgis.PyQt.QtWidgets import QDockWidget, QWidget, QTreeView, QVBoxLayout, QMenu, QAction
from qgis.PyQt.QtCore import pyqtSignal, pyqtSlot, Qt, QModelIndex, QUrl

from .classes.settings import Settings, CONSTANTS
from .classes.basemaps import BaseMaps, QRaveBaseMap
from .classes.project import Project
from .classes.context_menu import ContextMenu
from .classes.qrave_map_layer import QRaveMapLayer, QRaveTreeTypes
from .meta_widget import MetaType

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui', 'dock_widget.ui'))


ADD_TO_MAP_TYPES = ['polygon', 'raster', 'point', 'line']


class QRAVEDockWidget(QDockWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()
    dataChange = pyqtSignal()
    showMeta = pyqtSignal()
    metaChange = pyqtSignal(str, str, dict, bool)

    def __init__(self, parent=None):
        """Constructor."""
        super(QRAVEDockWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://doc.qt.io/qt-5/designer-using-a-ui-file.html
        # widgets-and-dialogs-with-auto-connect

        # self.treeView
        self.setupUi(self)
        self.menu = ContextMenu()
        self.qproject = QgsProject.instance()
        self.qproject.cleared.connect(self.close_project)
        self.qproject.readProject.connect(self.load)

        self.treeView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.treeView.customContextMenuRequested.connect(self.open_menu)
        self.treeView.doubleClicked.connect(self.default_tree_action)
        self.treeView.clicked.connect(self.item_change)

        self.treeView.expanded.connect(self.expand_tree_item)

        self.settings = Settings()
        self.project = None
        self.model = QStandardItemModel()

        # Initialize our classes
        self.basemaps = BaseMaps()
        self.treeView.setModel(self.model)

        self.dataChange.connect(self.load)
        self.load()

    def expand_tree_item(self, idx: QModelIndex):
        item = self.model.itemFromIndex(idx)
        data = item.data(Qt.UserRole)
        if isinstance(data, QRaveBaseMap):
            data.load_layers()

    @pyqtSlot()
    def load(self):
        # re-initialize our model
        self.model.clear()

        qrave_project_path, type_conversion_ok = self.qproject.readEntry(CONSTANTS['settingsCategory'],
                                                                         CONSTANTS['project_filepath'])

        if type_conversion_ok is True and os.path.isfile(qrave_project_path):
            self.project = Project(qrave_project_path)
            self.project.load()
        # Load the tree objects
        self.basemaps.load()

        if self.project is not None and self.project.exists is True and self.project.qproject is not None:
            self.model.appendRow(self.project.qproject)

        # Now load the basemaps
        region = self.settings.getValue('basemapRegion')
        if self.settings.getValue('basemapsInclude') is True \
                and region is not None and len(region) > 0 \
                and region in self.basemaps.regions.keys():
            self.model.appendRow(self.basemaps.regions[region])

        # Finally expand all levels
        self.expandChildren()

    def closeEvent(self, event):
        """ When the user clicks the "X" in the dockwidget titlebar
        """
        self.closingPlugin.emit()
        event.accept()

    def expandChildren(self, idx: QModelIndex = None):
        if idx is None:
            idx = self.treeView.rootIndex()

        for idy in range(self.model.rowCount(idx)):
            child = self.model.index(idy, 0, idx)
            self.expandChildren(child)

        item = self.model.itemFromIndex(idx)
        data = item.data(Qt.UserRole) if item is not None else None
        if not self.treeView.isExpanded(idx) and not isinstance(data, QRaveBaseMap):
            self.treeView.setExpanded(idx, True)

    def default_tree_action(self, idx: QModelIndex):
        if not idx.isValid():
            return
        item = self.model.itemFromIndex(idx)
        data = item.data(Qt.UserRole)

        # This is the default action for all add-able layers including basemaps
        if isinstance(data, QRaveMapLayer):
            QRaveMapLayer.add_layer_to_map(item, self.project)

        if isinstance(data, QRaveBaseMap):
            # Expand is the default option because we might need to load the layers
            return

        if data is not None and 'type' in data:

            if data['type'] in [QRaveTreeTypes.PROJECT_ROOT]:
                self.change_meta(item, data, True)

            # For folder-y types we want Expand and contract is already implemented as a default
            elif data['type'] in [
                QRaveTreeTypes.PROJECT_FOLDER,
                QRaveTreeTypes.PROJECT_REPEATER_FOLDER,
                QRaveTreeTypes.PROJECT_VIEW_FOLDER,
                QRaveTreeTypes.BASEMAP_ROOT,
                QRaveTreeTypes.BASEMAP_SUPER_FOLDER,
                QRaveTreeTypes.BASEMAP_SUB_FOLDER
            ]:
                print("Default Folder Action")

            elif data['type'] == QRaveTreeTypes.PROJECT_VIEW:
                print("Default View Action")
                self.add_view_to_map(item)

    def item_change(self, postion):
        """Triggered when the user selects a new item in the tree

        Args:
            postion ([type]): [description]
        """
        indexes = self.treeView.selectedIndexes()
        if len(indexes) < 1 or self.project is None or self.project.exists is False:
            return

        # No multiselect so there is only ever one item
        item = self.model.itemFromIndex(indexes[0])
        data = item.data(Qt.UserRole)

        # Update the metadata if we need to
        self.change_meta(item, data)

    def change_meta(self, item: QStandardItem, data, show=False):
        """Update the MetaData dock widget with new information

        Args:
            item (QStandardItem): [description]
            data ([type]): [description]
            show (bool, optional): [description]. Defaults to False.
        """
        if isinstance(data, QRaveMapLayer):
            self.metaChange.emit(item.text(), MetaType.LAYER, data.meta, show)

        elif isinstance(data, QRaveBaseMap):
            self.metaChange.emit(item.text(), MetaType.NONE, {}, show)

        elif data is not None and 'type' in data:
            if data['type'] == QRaveTreeTypes.PROJECT_ROOT:
                self.metaChange.emit(item.text(), MetaType.PROJECT, {
                    'project': self.project.meta,
                    'warehouse': self.project.warehouse_meta
                }, show)
            elif data['type'] in [
                QRaveTreeTypes.PROJECT_FOLDER,
                QRaveTreeTypes.PROJECT_REPEATER_FOLDER,
                QRaveTreeTypes.PROJECT_VIEW_FOLDER,
                QRaveTreeTypes.BASEMAP_ROOT,
                QRaveTreeTypes.BASEMAP_SUPER_FOLDER,
                QRaveTreeTypes.BASEMAP_SUB_FOLDER
            ]:
                self.metaChange.emit(item.text(), MetaType.FOLDER, data, show)
        else:
            self.metaChange.emit(item.text(), MetaType.NONE, data, show)

    def open_menu(self, position):

        indexes = self.treeView.selectedIndexes()
        if len(indexes) < 1:
            return

        # No multiselect so there is only ever one item
        idx = indexes[0]

        if not idx.isValid():
            return

        item = self.model.itemFromIndex(indexes[0])
        data = item.data(Qt.UserRole)

        # This is the layer context menu
        if isinstance(data, QRaveMapLayer):
            if data.layer_type == QRaveMapLayer.LayerTypes.WMS:
                self.basemap_context_menu(idx, item, data)
            else:
                self.layer_context_menu(idx, item, data)

        # A QARaveBaseMap is just a container for layers
        elif isinstance(data, QRaveBaseMap):
            self.basemap_service_context_menu(idx, item, data)

        elif data is not None and 'type' in data:

            if data['type'] == QRaveTreeTypes.PROJECT_ROOT:
                self.project_context_menu(idx, item, data)

            elif data['type'] in [
                QRaveTreeTypes.PROJECT_VIEW_FOLDER,
                QRaveTreeTypes.BASEMAP_ROOT,
                QRaveTreeTypes.BASEMAP_SUPER_FOLDER
            ]:
                self.folder_dumb_context_menu(idx, item, data)

            elif data['type'] in [
                QRaveTreeTypes.PROJECT_FOLDER,
                QRaveTreeTypes.PROJECT_REPEATER_FOLDER,
                QRaveTreeTypes.BASEMAP_SUB_FOLDER
            ]:
                self.folder_context_menu(idx, item, data)

            elif data['type'] == QRaveTreeTypes.PROJECT_VIEW:
                self.view_context_menu(idx, item, data)

        self.menu.exec_(self.treeView.viewport().mapToGlobal(position))

    # Layer context view
    def layer_context_menu(self, idx: QModelIndex, item: QStandardItem, data: QRaveMapLayer):
        self.menu.clear()
        self.menu.addAction('ADD_TO_MAP', lambda: QRaveMapLayer.add_layer_to_map(item, self.project), enabled=data.exists)
        self.menu.addAction('VIEW_LAYER_META', lambda: self.change_meta(item, data, True))

        if bool(self.get_warehouse_url(data.meta)):
            self.menu.addAction('VIEW_WEB_SOURCE', lambda: self.layer_warehouse_view(data))

        self.menu.addAction('BROWSE_FOLDER', lambda: self.file_system_locate(data.layer_uri))

    # Basemap context items
    def basemap_context_menu(self, idx: QModelIndex, item: QStandardItem, data: Dict[str, str]):
        self.menu.clear()
        self.menu.addAction('ADD_TO_MAP', lambda: QRaveMapLayer.add_layer_to_map(item, self.project))

    # Folder-level context menu
    def folder_context_menu(self, idx: QModelIndex, item: QStandardItem, data):
        self.menu.clear()
        self.menu.addAction('ADD_ALL_TO_MAP', lambda: self.add_children_to_map(item))
        self.menu.addSeparator()
        self.menu.addAction('COLLAPSE_ALL', lambda: self.toggleSubtree(item, False))
        self.menu.addAction('EXPAND_ALL', lambda: self.toggleSubtree(item, True))

    # Some folders don't have the 'ADD_ALL_TO_MAP' functionality enabled
    def folder_dumb_context_menu(self, idx: QModelIndex, item: QStandardItem, data):
        self.menu.clear()
        self.menu.addAction('COLLAPSE_ALL', lambda: self.toggleSubtree(item, False))
        self.menu.addAction('EXPAND_ALL', lambda: self.toggleSubtree(item, True))

    # View context items
    def view_context_menu(self, idx: QModelIndex, item: QStandardItem, data):
        self.menu.clear()
        self.menu.addAction('ADD_ALL_TO_MAP', lambda: self.add_view_to_map(item))

    # Project-level context menu
    def project_context_menu(self, idx: QModelIndex, item: QStandardItem, data):
        self.menu.clear()
        self.menu.addAction('COLLAPSE_ALL', lambda: self.toggleSubtree(None, False))
        self.menu.addAction('EXPAND_ALL', lambda: self.toggleSubtree(None, True))

        self.menu.addSeparator()
        self.menu.addAction('BROWSE_PROJECT_FOLDER', lambda: self.file_system_locate(self.project.project_xml_path))
        self.menu.addAction('VIEW_PROJECT_META', lambda: self.change_meta(item, data, True))
        self.menu.addAction('WAREHOUSE_VIEW', self.project_warehouse_view, enabled=bool(self.get_warehouse_url(self.project.warehouse_meta)))
        self.menu.addAction('ADD_ALL_TO_MAP', self.add_children_to_map(item))
        self.menu.addSeparator()
        self.menu.addAction('REFRESH_PROJECT_HIERARCHY', self.load)
        self.menu.addAction('CUSTOMIZE_PROJECT_HIERARCHY', enabled=False)
        self.menu.addSeparator()
        self.menu.addAction('CLOSE_PROJECT', self.close_project, enabled=bool(self.project))

    def get_warehouse_url(self, wh_meta: Dict[str, str]):

        if wh_meta is not None:

            if 'program' in wh_meta and 'id' in wh_meta:
                return '/'.join([CONSTANTS['warehouseUrl'], wh_meta['program'], wh_meta['id']])

            elif '_rs_wh_id' in wh_meta and '_rs_wh_program' in wh_meta:
                return '/'.join([CONSTANTS['warehouseUrl'], wh_meta['_rs_wh_program'], wh_meta['_rs_wh_id']])

        return None

    def project_warehouse_view(self):
        """Open this project in the warehouse if the warehouse meta entries exist
        """
        url = self.get_warehouse_url(self.project.warehouse_meta)
        if url is not None:
            QDesktopServices.openUrl(QUrl(url))

    def layer_warehouse_view(self, data: QRaveMapLayer):
        """Open this project in the warehouse if the warehouse meta entries exist
        """
        url = self.get_warehouse_url(data.meta)
        if url is not None:
            QDesktopServices.openUrl(QUrl(url))

    def file_system_open(self, fpath: str):
        """Open a file on the operating system using the default action

        Args:
            fpath (str): [description]
        """
        qurl = QUrl.fromLocalFile(fpath)
        QDesktopServices.openUrl(QUrl(qurl))

    def close_project(self):
        """ Close the project
        """

        self.qproject.removeEntry(CONSTANTS['settingsCategory'], CONSTANTS['project_filepath'])
        self.project = None
        self.load()

    def file_system_locate(self, fpath: str):
        """This the OS-agnostic "show in Finder" or "show in explorer" equivalent
        It should open the folder of the item in question

        Args:
            fpath (str): [description]
        """
        final_path = os.path.dirname(fpath)
        while not os.path.isdir(final_path):
            final_path = os.path.dirname(final_path)

        qurl = QUrl.fromLocalFile(final_path)
        QDesktopServices.openUrl(qurl)

    def toggleSubtree(self, item: QStandardItem = None, expand=True):

        def _recurse(curritem):
            idx = self.model.indexFromItem(item)
            if expand is not self.treeView.isExpanded(idx):
                self.treeView.setExpanded(idx, expand)

            for row in range(curritem.rowCount()):
                _recurse(curritem.child(row))

        if item is None:
            if expand is True:
                self.treeView.expandAll()
            else:
                self.treeView.collapseAll()
        else:
            _recurse(item)

    def add_view_to_map(self, item: QStandardItem):
        """Add a view and all its layers to the map

        Args:
            item (QStandardItem): [description]
        """
        print('Add view to map')

    def add_children_to_map(self, item: QStandardItem):
        """Recursively add all children to the map

        Args:
            item (QStandardItem): [description]
        """
        print('Add children to map')
