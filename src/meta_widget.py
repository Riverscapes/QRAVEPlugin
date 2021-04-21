# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List, Dict
import os


from qgis.PyQt import uic
from qgis.core import Qgis
from qgis.PyQt.QtGui import QStandardItemModel, QStandardItem, QIcon, QDesktopServices
from qgis.PyQt.QtWidgets import QDockWidget, QWidget, QTreeView, QVBoxLayout, QMenu, QAction
from qgis.PyQt.QtCore import pyqtSignal, pyqtSlot, Qt, QModelIndex, QUrl

from .classes.settings import Settings, CONSTANTS

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui', 'meta_widget.ui'))


class MetaType:
    PROJECT = 'project'
    LAYER = 'layer'
    NONE = 'none'


class QRAVEMetaWidget(QDockWidget, FORM_CLASS):

    def __init__(self, parent=None):
        """Constructor."""
        super(QRAVEMetaWidget, self).__init__(parent)
        self.setupUi(self)

        self.treeView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.treeView.customContextMenuRequested.connect(self.open_menu)
        self.treeView.doubleClicked.connect(self.default_tree_action)

        self.settings = Settings()
        self.model = QStandardItemModel()
        self.treeView.setModel(self.model)

        # Initialize our classes
        self.hide()

    @pyqtSlot(str, dict, bool)
    def load(self, meta_type: str, meta: dict, show: bool = False):
        # re-initialize our model
        self.model.clear()
        root_item = self.model.invisibleRootItem()
        self.model.setHorizontalHeaderLabels(['Meta Name', 'Meta Value'])

        if meta_type == MetaType.PROJECT:
            self.treeView.setHeaderHidden(False)
            self.setWindowTitle('Project MetaData')
            self.treeView.setEnabled(True)
            if meta is not None and len(meta.keys()) > 0:
                if 'project' in meta and len(meta['project'].keys()) > 0:
                    proj_meta = QStandardItem('Project Meta')
                    for k, v in meta['project'].items():
                        proj_meta.appendRow([
                            QStandardItem(k),
                            QStandardItem(v)
                        ])
                    root_item.appendRow(proj_meta)
                if 'warehouse' in meta and len(meta['warehouse'].keys()) > 0:
                    wh_meta = QStandardItem('Warehouse Meta')
                    for k, v in meta['warehouse'].items():
                        proj_meta.appendRow([
                            QStandardItem(k),
                            QStandardItem(v)
                        ])
                    root_item.appendRow(wh_meta)

        elif meta_type == MetaType.LAYER:
            self.setWindowTitle('Layer MetaData')
            self.treeView.setEnabled(True)
            self.treeView.setHeaderHidden(False)
            if meta is not None and len(meta.keys()) > 0:
                for k, v in meta.items():
                    root_item.appendRow([
                        QStandardItem(k),
                        QStandardItem(v)
                    ])
            else:
                self.treeView.setHeaderHidden(True)
                self.model.setHorizontalHeaderLabels(['Meta Name'])
                root_item.appendRow(QStandardItem('Layer has no MetaData'))
        elif meta_type == MetaType.NONE:
            self.treeView.setHeaderHidden(True)
            self.treeView.setEnabled(False)
            self.setWindowTitle('Riverscapes MetaData')
            return

        # self.tree.header().setDefaultSectionSize(180)

        # self._populateTree(self.tree, )
        # Finally expand all levels
        self.treeView.expandAll()
        if show is True:
            self.show()

    def closeEvent(self, event):
        self.hide()

    def default_tree_action(self, index):
        item = self.model.itemFromIndex(index)
        data = item.data(Qt.UserRole)

    def open_menu(self, position):

        indexes = self.treeView.selectedIndexes()
        if len(indexes) < 1:
            return

        # No multiselect so there is only ever one item
        idx = indexes[0]
        item = self.model.itemFromIndex(indexes[0])
        data = item.data(Qt.UserRole)
