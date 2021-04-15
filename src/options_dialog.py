import os
import json
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox
from qgis.core import QgsMessageLog, Qgis
from qgis.PyQt.QtCore import pyqtSignal
from .classes.settings import Settings

DIALOG_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui', 'options_dialog.ui'))


class OptionsDialog(QDialog, DIALOG_CLASS):

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.settings = Settings()
        self.setValues()
        self.buttonBox.clicked.connect(self.commit_settings)

    def setValues(self):
        self.regionInclude.setChecked(bool(self.settings.getValue('regionInclude')))
        self.loadDefaultView.setChecked(bool(self.settings.getValue('loadDefaultView')))

    def commit_settings(self, btn):
        role = self.buttonBox.buttonRole(btn)
        if role == QDialogButtonBox.ApplyRole:
            self.settings.setValue('regionInclude', self.regionInclude.isChecked())
            self.settings.setValue('loadDefaultView', self.loadDefaultView.isChecked())
        elif role == QDialogButtonBox.ResetRole:
            self.settings.resetAllSettings()
            self.setValues()

    def openUrl(self, url):
        """
        Open the folder in finder or windows explorer
        :param url:
        :return:
        """
        pass
