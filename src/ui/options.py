import os
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog
from qgis.PyQt.QtCore import pyqtSignal
# from settings import Settings

DIALOG_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'options.ui'))


class OptionsDialog(QDialog, DIALOG_CLASS):

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        QDialog.__init__(self, parent)
        self.setupUi(self)

    def openUrl(self, url):
        """
        Open the folder in finder or windows explorer
        :param url:
        :return:
        """
