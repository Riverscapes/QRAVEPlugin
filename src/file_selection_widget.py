import os
import math
import re
from typing import List, Dict, Optional, Any
from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTreeWidget, QTreeWidgetItem, QHeaderView
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QBrush, QColor, QFont


class SortableTreeWidgetItem(QTreeWidgetItem):
    def __lt__(self, other):
        column = self.treeWidget().sortColumn()
        if column == 1:  # Size column
            size_raw_self = self.data(column, Qt.UserRole)
            size_raw_other = other.data(column, Qt.UserRole)
            if isinstance(size_raw_self, (int, float)) and isinstance(size_raw_other, (int, float)):
                return size_raw_self < size_raw_other
        return super().__lt__(other)


class ProjectFileSelectionWidget(QWidget):
    """
    A reusable widget for selecting files within a Riverscapes project.
    """
    selectionChanged = pyqtSignal()

    def __init__(self, parent=None):
        super(ProjectFileSelectionWidget, self).__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Selection buttons
        self.selectionLayout = QHBoxLayout()
        self.btnSelectAll = QPushButton("Select All")
        self.btnDeselectAll = QPushButton("Deselect All")
        self.selectionLayout.addWidget(self.btnSelectAll)
        self.selectionLayout.addWidget(self.btnDeselectAll)
        self.selectionLayout.addStretch()
        self.layout.addLayout(self.selectionLayout)

        # Tree widget
        self.treeFiles = QTreeWidget()
        self.treeFiles.setSortingEnabled(True)
        self.treeFiles.setAlternatingRowColors(True)
        self.treeFiles.header().setSectionsClickable(True)
        self.treeFiles.header().setSortIndicatorShown(True)
        self.treeFiles.header().setStretchLastSection(False)
        self.treeFiles.setHeaderLabels(["File Path", "Size", "Status"])
        self.treeFiles.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.treeFiles.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.treeFiles.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.layout.addWidget(self.treeFiles)

        # Connect signals
        self.btnSelectAll.clicked.connect(self.select_all)
        self.btnDeselectAll.clicked.connect(self.deselect_all)
        self.treeFiles.itemChanged.connect(lambda item, col: self.selectionChanged.emit())

    def clear(self):
        self.treeFiles.clear()

    def set_sorting_enabled(self, enabled: bool):
        self.treeFiles.setSortingEnabled(enabled)

    def sort_by_column(self, column: int, order: Qt.SortOrder):
        self.treeFiles.sortByColumn(column, order)

    def select_all(self):
        self._set_all_check_state(Qt.Checked)

    def deselect_all(self):
        self._set_all_check_state(Qt.Unchecked)

    def _set_all_check_state(self, state: Qt.CheckState):
        root = self.treeFiles.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if item.flags() & Qt.ItemIsUserCheckable:
                item.setCheckState(0, state)

    def add_file_item(self, rel_path: str, size: int, status_text: str, 
                      checked: bool = True, 
                      is_locked: bool = False, 
                      is_mandatory: bool = False,
                      highlight_color: Optional[str] = None,
                      tooltip: Optional[str] = None):
        """
        Adds a file item to the tree.
        """
        item = SortableTreeWidgetItem(self.treeFiles)
        item.setText(0, rel_path)
        item.setText(1, self.human_size(size))
        item.setTextAlignment(1, Qt.AlignRight | Qt.AlignVCenter)
        item.setText(2, status_text)
        
        item.setData(0, Qt.UserRole, rel_path)
        item.setData(1, Qt.UserRole, size)  # Store raw size for sorting

        if is_mandatory:
            item.setFlags(item.flags() & ~Qt.ItemIsUserCheckable)
            font = item.font(0)
            font.setItalic(True)
            item.setFont(0, font)
            item.setFont(1, font)
            item.setCheckState(0, Qt.Checked)
        else:
            item.setCheckState(0, Qt.Checked if checked else Qt.Unchecked)

        if is_locked:
            item.setCheckState(0, Qt.Unchecked)
            item.setFlags(item.flags() & ~Qt.ItemIsUserCheckable)
            # Gray out
            gray = QBrush(Qt.gray)
            item.setForeground(0, gray)
            item.setForeground(1, gray)
            item.setForeground(2, gray)
            # Strikeout
            font = item.font(0)
            font.setStrikeOut(True)
            item.setFont(0, font)
        
        if highlight_color:
            item.setForeground(2, QBrush(QColor(highlight_color)))

        if tooltip:
            item.setToolTip(0, tooltip)
        
        return item

    def get_selected_files(self) -> List[str]:
        selected = []
        root = self.treeFiles.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if item.checkState(0) == Qt.Checked:
                selected.append(item.data(0, Qt.UserRole))
        return selected

    @staticmethod
    def human_size(nbytes):
        if nbytes == 0:
            return '0 B'
        suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
        i = 0
        while nbytes >= 1024 and i < len(suffixes)-1:
            nbytes /= 1024.
            i += 1
            
        precision = 2 - int(math.floor(math.log10(abs(nbytes)))) - 1
        nbytes = round(nbytes, precision)
            
        if nbytes >= 10:
            f = str(int(nbytes))
        else:
            f = ("%.1f" % nbytes).rstrip('0').rstrip('.')
            
        return '%s %s' % (f, suffixes[i])
