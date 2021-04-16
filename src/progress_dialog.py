import os
import json
from time import time
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox, QAbstractButton
from qgis.core import QgsMessageLog, Qgis
from qgis.PyQt.QtCore import pyqtSignal

from .classes.settings import Settings

DIALOG_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui', 'progress_dialog.ui'))


class ProgressDialog(QDialog, DIALOG_CLASS):

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.settings = Settings()
        self.buttonBox.accepted.connect(self.handle_accept)
        self.buttonBox.rejected.connect(self.handle_cancel)

    def handle_cancel(self):
        pass

    def handle_accept(self):
        pass

    def handle_done(self, force=False):
        if force is False:
            self.accept()
        else:
            self.buttonBox.setStandardButtons(QDialogButtonBox.Ok)
            pass

        self.settings.setValue('initialized', True)
