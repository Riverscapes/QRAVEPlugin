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
import json

from qgis.PyQt.QtCore import pyqtSignal, pyqtSlot, Qt, QModelIndex, QUrl
from qgis.PyQt.QtWidgets import QDockWidget, QWidget, QTreeView, QVBoxLayout, QMenu, QAction
from qgis.PyQt.QtGui import QStandardItemModel, QStandardItem, QIcon, QDesktopServices
from qgis.core import Qgis, QgsRasterLayer, QgsVectorLayer, QgsProject
from qgis.PyQt import uic
from .ui.dock_widget import Ui_QRAVEDockWidgetBase
from .meta_widget import MetaType
from .classes.qrave_map_layer import QRaveMapLayer, QRaveTreeTypes
from .classes.context_menu import ContextMenu
from .classes.project import Project, ProjectTreeData
from .classes.basemaps import BaseMaps, QRaveBaseMap
from .classes.settings import Settings, CONSTANTS


# FORM_CLASS, _ = uic.loadUiType(os.path.join(
#     os.path.dirname(__file__), 'ui', 'dock_widget.ui'))

ADD_TO_MAP_TYPES = ['polygon', 'raster', 'point', 'line']


class QRAVEDockWidget(QDockWidget, Ui_QRAVEDockWidgetBase):

    closingPlugin = pyqtSignal()
    dataChange = pyqtSignal()
    showMeta = pyqtSignal()
    metaChange = pyqtSignal(str, str, dict, bool)

    def __init__(self, parent=None):
        """Constructor."""
        super(QRAVEDockWidget, self).__init__(parent)

        self.setupUi(self)
        self.menu = ContextMenu()
        self.qproject = QgsProject.instance()
        self.qproject.cleared.connect(self.close_all)

        self.treeView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.treeView.customContextMenuRequested.connect(self.open_menu)
        self.treeView.doubleClicked.connect(self.default_tree_action)
        self.treeView.clicked.connect(self.item_change)

        self.treeView.expanded.connect(self.expand_tree_item)

        self.settings = Settings()

        # If a project fails to load we track it and don't autorefresh it.
        self.failed_loads = []

        self.model = QStandardItemModel()

        self.loaded_projects: List(Project) = []

        # Initialize our classes
        self.basemaps = BaseMaps()
        self.treeView.setModel(self.model)

        self.dataChange.connect(self.reload_tree)
        self.reload_tree()

    def expand_tree_item(self, idx: QModelIndex):
        item = self.model.itemFromIndex(idx)
        item_data = item.data(Qt.UserRole)
        if item_data and item_data.data and isinstance(item_data.data, QRaveBaseMap):
            item_data.data.load_layers()

    def _get_project(self, xml_path):
        try:
            return next(iter(self.loaded_projects))
        except Exception:
            return None

    def _get_project_by_name(self, name):
        try:
            for project in self.loaded_projects:
                if project.qproject.text() == name:
                    return project
            return None
        except Exception:
            return None

    @pyqtSlot()
    def reload_tree(self):
        # re-initialize our model and reload the projects from file
        # Try not to do this too often if you can
        expanded_states = {}

        def get_checked_state(idx, output=[]):

            for idy in range(self.model.rowCount(idx)):
                child = self.model.index(idy, 0, idx)
                output = get_checked_state(child, output)

            item = self.model.itemFromIndex(idx)
            expanded = self.treeView.isExpanded(idx)
            output.append((item.text(), expanded))

            return output

        for project in self.loaded_projects:
            if not isinstance(project, str):
                project_name = project.qproject.text()
                project_states = []
                project_states = get_checked_state(self.model.indexFromItem(project.qproject), project_states)
                expanded_states[project_name] = project_states

        basemap_states = None
        region = self.settings.getValue('basemapRegion')
        if self.basemaps.regions is not None and len(self.basemaps.regions) > 0:
            basemap_states = []
            basemap_states = get_checked_state(self.model.indexFromItem(self.basemaps.regions[region]), basemap_states)

        self.model.clear()
        self.loaded_projects = []
        qrave_projects = self.get_project_settings()

        for project_name, _basename, project_path in qrave_projects:
            project = Project(project_path)
            project.load()

            if project is not None \
                    and project.exists is True \
                    and project.qproject is not None \
                    and project.loadable is True:
                project.qproject.setText(project_name)
                self.model.appendRow(project.qproject)
                if project_name in expanded_states.keys():
                    self.restore_expaned_state(self.model.indexFromItem(project.qproject), expanded_states[project_name])
                else:
                    self.expand_children_recursive(self.model.indexFromItem(project.qproject))
                self.loaded_projects.append(project)
            else:
                # If this project is unloadable then make sure it never tries to load again
                self.set_project_settings([x for x in qrave_projects if x != project_path])

        # Load the tree objects
        self.basemaps.load()

        # Now load the basemaps
        region = self.settings.getValue('basemapRegion')
        if self.settings.getValue('basemapsInclude') is True \
                and region is not None and len(region) > 0 \
                and region in self.basemaps.regions.keys():
            self.model.appendRow(self.basemaps.regions[region])
            if basemap_states is not None:
                self.restore_expaned_state(self.model.indexFromItem(self.basemaps.regions[region]), basemap_states)
            else:
                self.expand_children_recursive(self.model.indexFromItem(self.basemaps.regions[region]))

    def get_project_settings(self):
        qrave_projects = []
        try:
            qrave_projects_raw, type_conversion_ok = self.qproject.readEntry(
                CONSTANTS['settingsCategory'],
                'qrave_projects'
            )

            if type_conversion_ok is False:
                qrave_projects = []
            else:
                qrave_projects = json.loads(qrave_projects_raw)

                if qrave_projects is None or not isinstance(qrave_projects, list):
                    qrave_projects = []

        except Exception as e:
            self.settings.log('Error loading project settings: {}'.format(e), Qgis.Warning)

        return qrave_projects

    def set_project_settings(self, projects: List[str]):
        self.qproject.writeEntry(CONSTANTS['settingsCategory'], 'qrave_projects', json.dumps(projects))

    @pyqtSlot()
    def add_project(self, xml_path: str):
        qrave_projects = self.get_project_settings()

        test_project = Project(xml_path)
        test_project.load()
        basename = test_project.qproject.text()
        count = [project[1] for project in qrave_projects].count(basename)
        name = f'{basename} Copy {count:02d}' if count > 0 else basename
        qrave_projects.insert(0, (name, basename, xml_path))
        self.set_project_settings(qrave_projects)
        self.reload_tree()

        new_project = self._get_project_by_name(name)

        # If this is a fresh load and the setting is set we load the default view
        load_default_setting = self.settings.getValue('loadDefaultView')

        if new_project is not None and load_default_setting is True \
                and new_project.default_view is not None \
                and new_project.default_view in new_project.views:
            self.add_children_to_map(new_project.qproject, new_project.views[new_project.default_view])

    def closeEvent(self, event):
        """ When the user clicks the "X" in the dockwidget titlebar
        """
        self.hide()
        self.qproject.removeEntry(CONSTANTS['settingsCategory'], 'enabled')
        self.closingPlugin.emit()
        event.accept()

    def expand_children_recursive(self, idx: QModelIndex = None, force=False):
        """Expand all the children of a QTreeView node. Do it recursively
        TODO: Recursion might not be the best for large trees here.

        Args:
            idx (QModelIndex, optional): [description]. Defaults to None.
            force: ignore the "collapsed" business logic attribute
        """
        if idx is None:
            idx = self.treeView.rootIndex()

        for idy in range(self.model.rowCount(idx)):
            child = self.model.index(idy, 0, idx)
            self.expand_children_recursive(child, force)

        item = self.model.itemFromIndex(idx)
        item_data = item.data(Qt.UserRole) if item is not None else None

        # NOTE: This is pretty verbose on purpose

        # This thing needs to have data or it defaults to being expanded
        if item_data is None or item_data.data is None:
            collapsed = False

        # Collapsed is an attribute set in the business logic
        # Never expand the QRaveBaseMap object becsause there's a network call involved
        elif isinstance(item_data.data, QRaveBaseMap) \
                or (isinstance(item_data.data, dict) and 'collapsed' in item_data.data and item_data.data['collapsed'] == 'true'):
            collapsed = True

        else:
            collapsed = False

        if not self.treeView.isExpanded(idx) and not collapsed:
            self.treeView.setExpanded(idx, True)

    def restore_expaned_state(self, idx: QModelIndex = None, states: List(dict) = None):
        """Expand all the children of a QTreeView node. Do it recursively
        TODO: Recursion might not be the best for large trees here.

        Args:
            idx (QModelIndex, optional): [description]. Defaults to None.
            force: ignore the "collapsed" business logic attribute
        """
        if idx is None:
            idx = self.treeView.rootIndex()

        for idy in range(self.model.rowCount(idx)):
            child = self.model.index(idy, 0, idx)
            self.restore_expaned_state(child, states)

        item = self.model.itemFromIndex(idx)
        item_data = item.data(Qt.UserRole) if item is not None else None

        # NOTE: This is pretty verbose on purpose

        # This thing needs to have data or it defaults to being expanded
        if item_data is None or item_data.data is None:
            collapsed = False

        # Collapsed is an attribute set in the business logic
        # Never expand the QRaveBaseMap object becsause there's a network call involved
        elif isinstance(item_data.data, QRaveBaseMap):  # \
            # or (isinstance(item_data.data, dict) and 'collapsed' in item_data.data and item_data.data['collapsed'] == 'true'):
            collapsed = True

        else:
            collapsed = False

        name = item.text()
        state = next((item_state[1] for item_state in states if item_state[0] == name), None)

        if not self.treeView.isExpanded(idx) and not collapsed and state is True:
            self.treeView.setExpanded(idx, True)

    def default_tree_action(self, idx: QModelIndex):
        if not idx.isValid():
            return

        item = self.model.itemFromIndex(idx)
        item_data: ProjectTreeData = item.data(Qt.UserRole)

        # This is the default action for all add-able layers including basemaps
        if isinstance(item_data.data, QRaveMapLayer):
            if item_data.data.layer_type in [QRaveMapLayer.LayerTypes.FILE, QRaveMapLayer.LayerTypes.REPORT]:
                self.file_system_open(item_data.data.layer_uri)
            else:
                QRaveMapLayer.add_layer_to_map(item)

        # Expand is the default option for wms because we might need to load the layers
        elif isinstance(item_data.data, QRaveBaseMap):
            if item_data.data.tile_type == 'wms':
                pass
            # All the XYZ layers can be added normally.
            else:
                QRaveMapLayer.add_layer_to_map(item)

        elif item_data.type in [QRaveTreeTypes.PROJECT_ROOT]:
            self.change_meta(item, item_data, True)

        # For folder-y types we want Expand and contract is already implemented as a default
        elif item_data.type in [
            QRaveTreeTypes.PROJECT_FOLDER,
            QRaveTreeTypes.PROJECT_REPEATER_FOLDER,
            QRaveTreeTypes.PROJECT_VIEW_FOLDER,
            QRaveTreeTypes.BASEMAP_ROOT,
            QRaveTreeTypes.BASEMAP_SUPER_FOLDER,
            QRaveTreeTypes.BASEMAP_SUB_FOLDER
        ]:
            # print("Default Folder Action")
            pass

        elif item_data.type == QRaveTreeTypes.PROJECT_VIEW:
            print("Default View Action")
            self.add_view_to_map(item_data)

    def item_change(self, pos):
        """Triggered when the user selects a new item in the tree

        Args:pos
            pos ([type]): [description]
        """
        indexes = self.treeView.selectedIndexes()

        # No multiselect so there is only ever one item
        item = self.model.itemFromIndex(indexes[0])
        data_item: ProjectTreeData = item.data(Qt.UserRole)

        if len(indexes) < 1 or data_item.project is None or not data_item.project.exists:
            return

        # Update the metadata if we need to
        self.change_meta(item, data_item)

    def change_meta(self, item: QStandardItem, item_data: ProjectTreeData, show=False):
        """Update the MetaData dock widget with new information

        Args:
            item (QStandardItem): [description]
            data ([type]): [description]
            show (bool, optional): [description]. Defaults to False.
        """
        data = item_data.data
        if isinstance(data, QRaveMapLayer):
            meta = data.meta if data.meta is not None else {}
            self.metaChange.emit(item.text(), MetaType.LAYER, meta, show)

        elif isinstance(data, QRaveBaseMap):
            self.metaChange.emit(item.text(), MetaType.NONE, {}, show)

        elif item_data.type == QRaveTreeTypes.PROJECT_ROOT:
            self.metaChange.emit(item.text(), MetaType.PROJECT, {
                'project': item_data.project.meta,
                'warehouse': item_data.project.warehouse_meta
            }, show)
        elif item_data.type in [
            QRaveTreeTypes.PROJECT_FOLDER,
            QRaveTreeTypes.PROJECT_REPEATER_FOLDER,
            QRaveTreeTypes.PROJECT_VIEW_FOLDER,
            QRaveTreeTypes.BASEMAP_ROOT,
            QRaveTreeTypes.BASEMAP_SUPER_FOLDER,
            QRaveTreeTypes.BASEMAP_SUB_FOLDER
        ]:
            self.metaChange.emit(item.text(), MetaType.FOLDER, data or {}, show)
        elif isinstance(data, dict):
            # this is just the generic case for any kind of metadata
            self.metaChange.emit(item.text(), MetaType.NONE, data or {}, show)
        else:
            # Do not  update the metadata if we have nothing to show
            self.metaChange.emit(item.text(), MetaType.NONE, {}, show)

    def get_warehouse_url(self, wh_meta: Dict[str, str]):

        if wh_meta is not None:

            if 'program' in wh_meta and 'id' in wh_meta:
                return '/'.join([CONSTANTS['warehouseUrl'], wh_meta['program'][0], wh_meta['id'][0]])

            elif '_rs_wh_id' in wh_meta and '_rs_wh_program' in wh_meta:
                return '/'.join([CONSTANTS['warehouseUrl'], wh_meta['_rs_wh_program'][0], wh_meta['_rs_wh_id'][0]])

        return None

    def project_warehouse_view(self, project: Project):
        """Open this project in the warehouse if the warehouse meta entries exist
        """
        url = self.get_warehouse_url(project.warehouse_meta)
        if url is not None:
            QDesktopServices.openUrl(QUrl(url))

    def layer_warehouse_view(self, data: ProjectTreeData):
        """Open this project in the warehouse if the warehouse meta entries exist
        """
        url = self.get_warehouse_url(data.data.meta)
        if url is not None:
            QDesktopServices.openUrl(QUrl(url))

    def close_all(self):
        if len(self.loaded_projects) > 0:
            for p in range(len(self.loaded_projects)):
                self.close_project(self.loaded_projects[0])

    def close_project(self, project: Project):
        """ Close the project
        """
        try:
            qrave_projects_raw, type_conversion_ok = self.qproject.readEntry(
                CONSTANTS['settingsCategory'],
                'qrave_projects'
            )
            qrave_projects = json.loads(qrave_projects_raw)
            if not type_conversion_ok or qrave_projects is None:
                qrave_projects = []
        except Exception as e:
            self.settings.log('Error closing project: {}'.format(e), Qgis.Warning)
            qrave_projects = []

        # Filter out the project we want to close and reload the tree
        project_name = project.qproject.text()
        qrave_projects = [(name, basename, xml) for name, basename, xml in qrave_projects if name != project_name]

        QRaveMapLayer.remove_project_from_map(project_name)

        # Write the settings back to the project
        self.qproject.writeEntry(CONSTANTS['settingsCategory'], 'qrave_projects', json.dumps(qrave_projects))
        self.loaded_projects = [loaded_project for loaded_project in self.loaded_projects if loaded_project.qproject.text() != project_name]
        self.reload_tree()

    def file_system_open(self, fpath: str):
        """Open a file on the operating system using the default action

        Args:
            fpath (str): [description]
        """
        qurl = QUrl.fromLocalFile(fpath)
        QDesktopServices.openUrl(QUrl(qurl))

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

    def add_view_to_map(self, item_data: ProjectTreeData):
        """Add a view and all its layers to the map

        Args:
            item (QStandardItem): [description]
        """
        self.add_children_to_map(item_data.project.qproject, item_data.data)

    def add_children_to_map(self, item: QStandardItem, bl_ids: List[str] = None):
        """Iteratively add all children to the map

        Args:
            item (QStandardItem): [description]
            bl_ids (List[str], optional): List of ids to filter by so we don't load everything. this is used for loading views
        """

        for child in self._get_children(item):
            # Is this something we can add to the map?
            project_tree_data = child.data(Qt.UserRole)
            if project_tree_data is not None and isinstance(project_tree_data.data, QRaveMapLayer):
                data = project_tree_data.data
                loadme = False
                # If this layer matches the businesslogic id filter
                if bl_ids is not None and len(bl_ids) > 0:
                    if 'id' in data.bl_attr and data.bl_attr['id'] in bl_ids:
                        loadme = True
                else:
                    loadme = True

                if loadme is True:
                    data.add_layer_to_map(child)

    def _get_children(self, root_item: QStandardItem):
        """Recursion is going to kill us here so do an iterative solution instead
           https://stackoverflow.com/questions/41949370/collect-all-items-in-qtreeview-recursively

        Yields:
            [type]: [description]
        """
        stack = [root_item]
        while stack:
            parent = stack.pop(0)
            for row in range(parent.rowCount()):
                for column in range(parent.columnCount()):
                    child = parent.child(row, column)
                    yield child
                    if child.hasChildren():
                        stack.append(child)

    def _get_parents(self, start_item: QStandardItem):
        stack = []
        placeholder = start_item.parent()
        while placeholder is not None and placeholder != self.model.invisibleRootItem():
            stack.append(placeholder)
            placeholder = start_item.parent()

        return stack.reverse()

    def open_menu(self, position):

        indexes = self.treeView.selectedIndexes()
        if len(indexes) < 1:
            return

        # No multiselect so there is only ever one item
        idx = indexes[0]

        if not idx.isValid():
            return

        item = self.model.itemFromIndex(indexes[0])
        project_tree_data = item.data(Qt.UserRole)  # ProjectTreeData object
        data = project_tree_data.data  # Could be a QRaveBaseMap, a QRaveMapLayer or just some random data

        # This is the layer context menu
        if isinstance(data, QRaveMapLayer):
            if data.layer_type == QRaveMapLayer.LayerTypes.WEBTILE:
                self.basemap_context_menu(idx, item, project_tree_data)
            elif data.layer_type in [QRaveMapLayer.LayerTypes.FILE, QRaveMapLayer.LayerTypes.REPORT]:
                self.file_layer_context_menu(idx, item, project_tree_data)
            else:
                self.map_layer_context_menu(idx, item, project_tree_data)

        elif isinstance(data, QRaveBaseMap):
            # A WMS QARaveBaseMap is just a container for layers
            if data.tile_type == 'wms':
                self.folder_dumb_context_menu(idx, item, project_tree_data)
            # Every other kind of basemap is an add-able layer
            else:
                self.basemap_context_menu(idx, item, project_tree_data)

        elif project_tree_data.type == QRaveTreeTypes.PROJECT_ROOT:
            self.project_context_menu(idx, item, project_tree_data)

        elif project_tree_data.type in [
            QRaveTreeTypes.PROJECT_VIEW_FOLDER,
            QRaveTreeTypes.BASEMAP_ROOT,
            QRaveTreeTypes.BASEMAP_SUPER_FOLDER
        ]:
            self.folder_dumb_context_menu(idx, item, project_tree_data)

        elif project_tree_data.type in [
            QRaveTreeTypes.PROJECT_FOLDER,
            QRaveTreeTypes.PROJECT_REPEATER_FOLDER,
            QRaveTreeTypes.BASEMAP_SUB_FOLDER
        ]:
            self.folder_context_menu(idx, item, project_tree_data)

        elif project_tree_data.type == QRaveTreeTypes.PROJECT_VIEW:
            self.view_context_menu(idx, item, project_tree_data)

        self.menu.exec_(self.treeView.viewport().mapToGlobal(position))

    def map_layer_context_menu(self, idx: QModelIndex, item: QStandardItem, item_data: ProjectTreeData):
        self.menu.clear()
        self.menu.addAction('ADD_TO_MAP', lambda: QRaveMapLayer.add_layer_to_map(item), enabled=item_data.data.exists)
        self.menu.addAction('VIEW_LAYER_META', lambda: self.change_meta(item, item_data, True))

        if bool(self.get_warehouse_url(item_data.data.meta)):
            self.menu.addAction('VIEW_WEB_SOURCE', lambda: self.layer_warehouse_view(item_data))

        self.menu.addAction('BROWSE_FOLDER', lambda: self.file_system_locate(item_data.data.layer_uri))

    def file_layer_context_menu(self, idx: QModelIndex, item: QStandardItem, item_data: ProjectTreeData):
        self.menu.clear()
        self.menu.addAction('OPEN_FILE', lambda: self.file_system_open(item_data.data.layer_uri))
        self.menu.addAction('BROWSE_FOLDER', lambda: self.file_system_locate(item_data.data.layer_uri))

    # Basemap context items
    def basemap_context_menu(self, idx: QModelIndex, item: QStandardItem, data: ProjectTreeData):
        self.menu.clear()
        self.menu.addAction('ADD_TO_MAP', lambda: QRaveMapLayer.add_layer_to_map(item))

    # Folder-level context menu
    def folder_context_menu(self, idx: QModelIndex, item: QStandardItem, data: ProjectTreeData):
        self.menu.clear()
        self.menu.addAction('ADD_ALL_TO_MAP', lambda: self.add_children_to_map(item))
        self.menu.addSeparator()
        self.menu.addAction('COLLAPSE_ALL', lambda: self.toggleSubtree(item, False))
        self.menu.addAction('EXPAND_ALL', lambda: self.toggleSubtree(item, True))

    # Some folders don't have the 'ADD_ALL_TO_MAP' functionality enabled
    def folder_dumb_context_menu(self, idx: QModelIndex, item: QStandardItem, data: ProjectTreeData):
        self.menu.clear()
        self.menu.addAction('COLLAPSE_ALL', lambda: self.toggleSubtree(item, False))
        self.menu.addAction('EXPAND_ALL', lambda: self.toggleSubtree(item, True))

    # View context items
    def view_context_menu(self, idx: QModelIndex, item: QStandardItem, item_data: ProjectTreeData):
        self.menu.clear()
        self.menu.addAction('ADD_ALL_TO_MAP', lambda: self.add_view_to_map(item_data))

    # Project-level context menu
    def project_context_menu(self, idx: QModelIndex, item: QStandardItem, data: ProjectTreeData):
        self.menu.clear()
        self.menu.addAction('COLLAPSE_ALL', lambda: self.toggleSubtree(None, False))
        self.menu.addAction('EXPAND_ALL', lambda: self.toggleSubtree(None, True))

        self.menu.addSeparator()
        self.menu.addAction('BROWSE_PROJECT_FOLDER', lambda: self.file_system_locate(data.project.project_xml_path))
        self.menu.addAction('VIEW_PROJECT_META', lambda: self.change_meta(item, data, True))
        self.menu.addAction('WAREHOUSE_VIEW', lambda: self.project_warehouse_view(data.project), enabled=bool(self.get_warehouse_url(data.project.warehouse_meta)))
        self.menu.addAction('ADD_ALL_TO_MAP', lambda: self.add_children_to_map(item))
        self.menu.addSeparator()
        self.menu.addAction('REFRESH_PROJECT_HIERARCHY', self.reload_tree)
        self.menu.addAction('CUSTOMIZE_PROJECT_HIERARCHY', enabled=False)
        self.menu.addSeparator()
        self.menu.addAction('CLOSE_PROJECT', lambda: self.close_project(data.project), enabled=bool(data.project))
