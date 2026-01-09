# -*- coding: utf-8 -*-
import os
from qgis.PyQt import uic, QtGui
from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QLabel, QDialogButtonBox, QSizePolicy
from qgis.PyQt.QtCore import Qt

class RemoteProjectDialog(QDialog):
    """
    Dialog for opening a remote Riverscapes project.
    """

    # def __init__(self, parent=None, default_id="https://data.riverscapes.net/p/ac104f27-93b7-4e47-b279-7a7dad8ccf1d/"):
    def __init__(self, parent=None, default_id="https://data.riverscapes.net/p/ac104f27-93b7-4e47-b279-7a7dad8ccf1d/"):
        """Constructor."""
        super(RemoteProjectDialog, self).__init__(parent)
        self.setWindowTitle("Open Remote Project")
        self.setMinimumWidth(600)
        
        self.layout = QVBoxLayout(self)

        # Description Label
        self.description = QLabel(
            "Enter a Riverscapes Project ID or paste a URL from the Riverscapes Data Exchange.\n"
            "This will fetch the project metadata and add it to your project list."
        )
        self.description.setWordWrap(True)
        self.description.setStyleSheet("margin-bottom: 10px; color: #555;")
        self.layout.addWidget(self.description)

        # Input Label
        self.input_label = QLabel("Project ID or URL:")
        self.layout.addWidget(self.input_label)

        # Text Input
        self.line_edit = QLineEdit(self)
        self.line_edit.setText(default_id)
        self.line_edit.setMinimumWidth(500)
        # https://data.riverscapes.net/p/ac104f27-93b7-4e47-b279-7a7dad8ccf1d/
        self.line_edit.setPlaceholderText("e.g. ac104f27-93b7-4e47-b279-7a7dad8ccf1d or https://data.riverscapes.net/p/ac104f27-93b7-4e47-b279-7a7dad8ccf1d/...")
        self.layout.addWidget(self.line_edit)

        # Button Box
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def get_text(self):
        """Returns the text entered in the QLineEdit."""
        return self.line_edit.text()
