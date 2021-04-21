# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List, Dict
import os
import json


from qgis.PyQt import uic
from qgis.core import Qgis
from qgis.PyQt.QtGui import QStandardItemModel, QStandardItem, QIcon, QDesktopServices, QGuiApplication
from qgis.PyQt.QtWidgets import QDockWidget, QWidget, QTreeView, QVBoxLayout, QMenu, QAction
from qgis.PyQt.QtCore import pyqtSignal, pyqtSlot, Qt, QModelIndex, QUrl

from .classes.settings import Settings, CONSTANTS


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui', 'meta_widget.ui'))


class MetaType:
    PROJECT = 'project'
    LAYER = 'layer'
    FOLDER = 'folder'
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
        self.meta = None
        self.menu = QMenu()

        # Initialize our classes
        self.hide()

    @pyqtSlot(str, str, dict, bool)
    def load(self, label: str, meta_type: str, meta: dict, show: bool = False):
        # re-initialize our model
        self.model.clear()
        self.meta = meta
        root_item = self.model.invisibleRootItem()
        self.model.setColumnCount(2)
        self.model.setHorizontalHeaderLabels(['Meta Name', 'Meta Value'])

        if meta_type == MetaType.PROJECT:
            self.treeView.setHeaderHidden(False)
            self.setWindowTitle('Project MetaData: {}'.format(label))
            self.treeView.setEnabled(True)
            if meta is not None and len(meta.keys()) > 0:
                if 'project' in meta and len(meta['project'].keys()) > 0:
                    proj_meta = QStandardItem('Project Meta')
                    proj_meta_font = proj_meta.font()
                    proj_meta_font.setBold(True)
                    proj_meta.setFont(proj_meta_font)
                    for k, v in meta['project'].items():
                        proj_meta.appendRow([
                            QStandardItem(k),
                            QStandardItem(v)
                        ])
                    root_item.appendRow(proj_meta)
                if 'warehouse' in meta and len(meta['warehouse'].keys()) > 0:
                    wh_meta = QStandardItem('Warehouse Meta')
                    wh_meta_font = proj_meta.font()
                    wh_meta_font.setBold(True)
                    wh_meta.setFont(wh_meta_font)
                    for k, v in meta['warehouse'].items():
                        wh_meta.appendRow([
                            QStandardItem(k),
                            QStandardItem(v)
                        ])
                    root_item.appendRow(wh_meta)

        elif meta_type == MetaType.FOLDER:
            self.setWindowTitle('Folder: {}'.format(label))
            self.treeView.setHeaderHidden(True)
            self.treeView.setEnabled(False)
            self.model.setColumnCount(1)
            self.model.setHorizontalHeaderLabels(['Meta Name'])
            no_item = QStandardItem('Folders have no MetaData')
            no_item.setTextAlignment(Qt.AlignCenter)
            no_f = no_item.font()
            no_f.setItalic(True)
            no_item.setFont(no_f)
            root_item.appendRow(no_item)

        elif meta_type == MetaType.LAYER:
            self.setWindowTitle('Layer MetaData: {}'.format(label))
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
                self.treeView.setEnabled(False)
                self.model.setColumnCount(1)
                self.model.setHorizontalHeaderLabels(['Meta Name'])
                no_item = QStandardItem('This layer has no MetaData')
                no_item.setTextAlignment(Qt.AlignCenter)
                no_f = no_item.font()
                no_f.setItalic(True)
                no_item.setFont(no_f)
                root_item.appendRow(no_item)
        elif meta_type == MetaType.NONE:
            self.treeView.setHeaderHidden(True)
            self.treeView.setEnabled(False)
            self.setWindowTitle('Riverscapes MetaData: {}'.format(label))
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
        if len(indexes) < 1 or self.meta is None or len(self.meta.keys()) == 0:
            return

        # No multiselect so there is only ever one item
        item_name = self.model.itemFromIndex(indexes[0])
        item_val = self.model.itemFromIndex(indexes[1]) if len(indexes) > 0 else None

        self.menu.clear()
        if item_val is not None:
            row_text = {item_name.text(): item_val.text()}
            self.menu.addAction('Copy Name to Clipboard', lambda: self.copy(item_name.text()))
            self.menu.addAction('Copy Value to Clipboard', lambda: self.copy(item_val.text()))
            self.menu.addAction('Copy Row to Clipboard (json)', lambda: self.copy(
                json.dumps(row_text, indent=4, sort_keys=True)
            ))
        self.menu.addAction('Copy All to Clipboard (json)', lambda: self.copy(json.dumps(self.meta, indent=4, sort_keys=True)))

        self.menu.exec_(self.treeView.viewport().mapToGlobal(position))

    def copy(self, data: str):
        cb = QGuiApplication.clipboard()
        cb.clear(mode=cb.Clipboard)
        cb.setText(data, mode=cb.Clipboard)
