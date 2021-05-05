import os
import json
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox
from qgis.PyQt.QtCore import pyqtSignal, QUrl
from qgis.PyQt.QtGui import QIcon, QDesktopServices
from qgis.core import Qgis

from .classes.settings import Settings
from .classes.basemaps import BaseMaps


# DIALOG_CLASS, _ = uic.loadUiType(os.path.join(
#     os.path.dirname(__file__), 'ui', 'options_dialog.ui'))
from .ui.options_dialog import Ui_Dialog

RESOURCES_DIR = os.path.join(os.path.dirname(__file__), '..', 'resources')


class OptionsDialog(QDialog, Ui_Dialog):

    closingPlugin = pyqtSignal()
    dataChange = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.basemaps = BaseMaps()
        self.settings = Settings()
        self.buttonBox.clicked.connect(self.commit_settings)
        self.basemaps.load()
        self.setValues()

        self.regionHelp.setText(None)
        self.regionHelp.setIcon(QIcon(':/plugins/qrave_toolbar/Help.png'))
        self.regionHelp.setEnabled(False)

    def setValues(self):
        self.basemapsInclude.setChecked(self.settings.getValue('basemapsInclude'))
        self.loadDefaultView.setChecked(self.settings.getValue('loadDefaultView'))

        # Set the combo box
        self.basemapRegion.clear()
        region = self.settings.getValue('basemapRegion')
        self.basemapRegion.addItems(self.basemaps.regions.keys())
        if region and len(region) > 0:
            self.basemapRegion.setCurrentText(region)

    def commit_settings(self, btn):
        role = self.buttonBox.buttonRole(btn)

        if role == QDialogButtonBox.ApplyRole:
            self.settings.setValue('basemapsInclude', self.basemapsInclude.isChecked())
            self.settings.setValue('loadDefaultView', self.loadDefaultView.isChecked())
            self.settings.setValue('basemapRegion', self.basemapRegion.currentText())

        elif role == QDialogButtonBox.ResetRole:
            self.settings.resetAllSettings()
            self.setValues()

        # Emit a datachange so we can trigger other parts of this plugin
        self.dataChange.emit()
