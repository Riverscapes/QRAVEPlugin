from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from .compat import DLGBTN_CANCEL, DLGBTN_OK, DLGBTN_ROLE_HELP


class RemoteProjectDialog(QDialog):
    """
    Dialog for opening a remote Riverscapes project.
    """

    # def __init__(self, parent=None, default_id="https://data.riverscapes.net/p/ac104f27-93b7-4e47-b279-7a7dad8ccf1d/"):
    def __init__(self, parent=None, default_id=""):
        """Constructor."""
        super().__init__(parent)
        self.setWindowTitle("Open Remote Project")
        self.setMinimumWidth(600)

        self.layout = QVBoxLayout(self)

        # Description Label
        self.description = QLabel(
            "Open a riverscapes project from the <a href='https://data.riverscapes.net'>Riverscapes Data Exchange</a> without downloading it first!\n\n"
            "Enter a Riverscapes Project ID or paste a URL from the Riverscapes Data Exchange. "
            "Click OK to open the project and add it to the list. "
            "Viewing the project layers will use web mapping services instead of local data files.\n"
        )
        self.description.setWordWrap(True)
        self.description.setOpenExternalLinks(True)
        self.layout.addWidget(self.description)

        form_layout = QFormLayout()
        self.layout.addLayout(form_layout)

        # Text Input
        self.line_edit = QLineEdit(self)
        self.line_edit.setText(default_id)
        self.line_edit.setMinimumWidth(500)
        # https://data.riverscapes.net/p/ac104f27-93b7-4e47-b279-7a7dad8ccf1d/
        self.line_edit.setPlaceholderText("e.g. ac104f27-93b7-4e47-b279-7a7dad8ccf1d or https://data.riverscapes.net/p/ac104f27-93b7-4e47-b279-7a7dad8ccf1d")
        form_layout.addRow("Project ID or URL", self.line_edit)

        # Button Box
        self.button_box = QDialogButtonBox(DLGBTN_OK | DLGBTN_CANCEL)

        self.btn_help = QPushButton("Help")
        self.button_box.addButton(self.btn_help, DLGBTN_ROLE_HELP)

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def get_text(self):
        """Returns the text entered in the QLineEdit."""
        return self.line_edit.text()
