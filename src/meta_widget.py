# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List, Dict
import os
import json


from qgis.PyQt import uic
from qgis.core import Qgis
from qgis.PyQt.QtGui import QStandardItemModel, QStandardItem, QDesktopServices, QGuiApplication, QBrush
from qgis.PyQt.QtWidgets import QDockWidget, QMenu, QMessageBox, QWidget, QTextEdit, QVBoxLayout, QTreeView, QAbstractItemView
from qgis.PyQt.QtCore import pyqtSignal, pyqtSlot, Qt, QModelIndex, QUrl

from .classes.settings import Settings, CONSTANTS


class MetaType:
    PROJECT = 'project'
    LAYER = 'layer'
    FOLDER = 'folder'
    NONE = 'none'


class QRAVEMetaWidget(QDockWidget):

    def __init__(self, parent=None):
        """Constructor."""
        super(QRAVEMetaWidget, self).__init__(parent)
        self.setupUi()

        self.treeView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.treeView.customContextMenuRequested.connect(self.open_menu)
        self.treeView.doubleClicked.connect(self.default_tree_action)

        self.settings = Settings()
        self.model = QStandardItemModel()
        self.treeView.setModel(self.model)
        self.meta = None
        self.description = None
        self.menu = QMenu()

        # Initialize our classes
        self.hide()

    @pyqtSlot(str, str, dict, str, bool)
    def load(self, label: str, meta_type: str, meta: dict, description: str, show: bool = False):
        # re-initialize our model
        self.model.clear()
        self.meta = meta
        self.description = description
        root_item = self.model.invisibleRootItem()
        self.model.setColumnCount(2)
        self.model.setHorizontalHeaderLabels(['Meta Name', 'Meta Value'])

        if description is not None and len(description) > 0:
            self.descriptionBox.setPlainText(description)
            self.descriptionBox.show()
        else:
            self.descriptionBox.setPlainText('No description available.')
            self.descriptionBox.show()
        if meta_type == MetaType.PROJECT:
            self.treeView.setHeaderHidden(False)
            self.setWindowTitle('Project Metadata: {}'.format(label))
            self.treeView.setEnabled(True)
            if meta is not None and len(meta.keys()) > 0:
                if 'project' in meta and len(meta['project'].keys()) > 0:
                    proj_meta = QStandardItem('Project Meta')
                    proj_meta_font = proj_meta.font()
                    proj_meta_font.setBold(True)
                    proj_meta.setFont(proj_meta_font)
                    for k, v in meta['project'].items():
                        self.appendMetaItem(proj_meta, k, v[0], v[1])
                    root_item.appendRow(proj_meta)
                if 'warehouse' in meta and meta['warehouse'] is not None and len(meta['warehouse'].keys()) > 0:
                    wh_meta = QStandardItem('Warehouse Meta')
                    wh_meta_font = proj_meta.font()
                    wh_meta_font.setBold(True)
                    wh_meta.setFont(wh_meta_font)
                    for k, v in meta['warehouse'].items():
                        self.appendMetaItem(wh_meta, k, v[0], v[1])
                    root_item.appendRow(wh_meta)

        elif meta_type == MetaType.FOLDER:
            self.setWindowTitle('Folder: {}'.format(label))
            self.descriptionBox.hide()
            self.treeView.setHeaderHidden(True)
            self.treeView.setEnabled(False)
            self.model.setColumnCount(1)
            self.model.setHorizontalHeaderLabels(['Meta Name'])
            no_item = QStandardItem('Folders have no Metadata')
            no_item.setTextAlignment(Qt.AlignCenter)
            no_f = no_item.font()
            no_f.setItalic(True)
            no_item.setFont(no_f)
            root_item.appendRow(no_item)

        elif meta_type == MetaType.LAYER:
            self.setWindowTitle('Layer Metadata: {}'.format(label))
            self.treeView.setEnabled(True)
            self.treeView.setHeaderHidden(False)
            if meta is not None and len(meta.keys()) > 0:
                for k, v in meta.items():
                    self.appendMetaItem(root_item, k, v[0], v[1])
            else:
                self.treeView.setHeaderHidden(True)
                self.treeView.setEnabled(False)
                self.model.setColumnCount(1)
                self.model.setHorizontalHeaderLabels(['Meta Name'])
                no_item = QStandardItem('This layer has no Metadata')
                no_item.setTextAlignment(Qt.AlignCenter)
                no_f = no_item.font()
                no_f.setItalic(True)
                no_item.setFont(no_f)
                root_item.appendRow(no_item)
        elif meta_type == MetaType.NONE:
            self.descriptionBox.hide()
            self.treeView.setHeaderHidden(True)
            self.treeView.setEnabled(False)
            self.model.setColumnCount(1)
            self.setWindowTitle('Riverscapes Metadata: {}'.format(label))
            no_item = QStandardItem('This item cannot have metadata')
            no_item.setTextAlignment(Qt.AlignCenter)
            no_f = no_item.font()
            no_f.setItalic(True)
            no_item.setFont(no_f)
            root_item.appendRow(no_item)
            return

        # self.tree.header().setDefaultSectionSize(180)

        # self._populateTree(self.tree, )
        # Finally expand all levels
        self.treeView.expandAll()
        if show is True:
            self.show()

    def appendMetaItem(self, root_item: QStandardItem, key: str, value: str, meta_type=None):
        val_item = QStandardItem(value)
        if (value is not None and len(value) > 0):
            val_item.setToolTip(value)
        val_item.setData(meta_type, Qt.UserRole)

        # Getting ready for custom meta types
        if (meta_type == 'url' or meta_type == 'image' or meta_type == 'video') and value is not None and value.startswith('http'):
            val_item.setData(QBrush(Qt.blue), Qt.ForegroundRole)
        # val_item.setUnderlineStyle(QTextCharFormat.SingleUnderline)

        root_item.appendRow([
            QStandardItem(key),
            val_item
        ])

    def closeEvent(self, event):
        self.hide()

    def default_tree_action(self, index):
        item = self.model.itemFromIndex(index)
        meta_type = item.data(Qt.UserRole)
        text = item.text()

        if meta_type is not None and text is not None:
            if (meta_type == 'url' or meta_type == 'image' or meta_type == 'video') and text.startswith('http'):
                qm = QMessageBox
                result = qm.question(self, 'Riverscapes Viewer', "Visit in browser?", qm.Yes | qm.No)
                if result == qm.Yes:
                    QDesktopServices.openUrl(QUrl(text))
        else:
            self.copy(text)

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
            meta_type = item_val.data(Qt.UserRole)
            if meta_type == 'url' or meta_type == 'image' or meta_type == 'video' and item_val.text().startswith('http'):
                self.menu.addAction('Visit URL in Browser', lambda: QDesktopServices.openUrl(QUrl(item_val.text())))
                self.menu.addSeparator()
            self.menu.addAction('Copy name', lambda: self.copy(item_name.text()))
            self.menu.addAction('Copy value', lambda: self.copy(item_val.text()))
            self.menu.addAction('Copy row (json)', lambda: self.copy(
                json.dumps(row_text, indent=4, sort_keys=True)
            ))
        self.menu.addAction('Copy all rows (json)', lambda: self.copy(json.dumps(self.meta, indent=4, sort_keys=True)))

        self.menu.exec_(self.treeView.viewport().mapToGlobal(position))

    def copy(self, data: str):
        self.settings.msg_bar('Item Copied to clipboard:', data, Qgis.Success)
        cb = QGuiApplication.clipboard()
        cb.clear(mode=cb.Clipboard)
        cb.setText(data, mode=cb.Clipboard)

    def clear_and_hide(self):
        """Clear the metadata panel and hide it."""
        self.model.clear()
        self.setWindowTitle("Riverscapes Metadata")
        self.hide()

    def setupUi(self):
        
        self.resize(555, 559)
        self.dockWidgetContents = QWidget()
        self.verticalLayout = QVBoxLayout(self.dockWidgetContents)
        self.verticalLayout.setContentsMargins(0, 4, 0, 4)
        self.verticalLayout.setSpacing(0)

        # Add a read-only QTextEdit for the description above the tree view
        self.descriptionBox = QTextEdit(self.dockWidgetContents)
        self.descriptionBox.setReadOnly(True)
        self.descriptionBox.setMinimumHeight(60)  # About 2 lines of text
        self.descriptionBox.setMaximumHeight(60)  # Prevents it from growing too tall
        self.verticalLayout.addWidget(self.descriptionBox)

        self.treeView = QTreeView(self.dockWidgetContents)
        self.treeView.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.treeView.setProperty("showDropIndicator", False)
        self.treeView.setAlternatingRowColors(True)
        self.treeView.setIndentation(0)
        self.treeView.setSortingEnabled(False)
        self.treeView.setHeaderHidden(False)
        self.verticalLayout.addWidget(self.treeView)
        self.setWidget(self.dockWidgetContents)
