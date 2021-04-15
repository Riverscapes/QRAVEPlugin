import os
import json
from time import time
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox
from qgis.core import QgsMessageLog, Qgis
from qgis.PyQt.QtCore import pyqtSignal
from .classes.settings import Settings
from .classes.net_sync import NetSync

DIALOG_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui', 'progress_dialog.ui'))


class ProgressDialog(QDialog, DIALOG_CLASS):

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.settings = Settings()
        self.buttonBox.rejected.connect(self.cancel)
        self.netsync = NetSync()
        # progressLabel
        # progressBar

    def cancel(self, btn):
        self.netsync.q.stopWorker()
        # currTime = int(time())  # timestamp in seconds
        # # Finally set the sync value
        # self.settings.setValue('lastSync', currTime)
