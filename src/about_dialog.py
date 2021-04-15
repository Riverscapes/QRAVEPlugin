import os
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog
from qgis.PyQt.QtGui import QPixmap
from qgis.PyQt.QtCore import pyqtSignal

from .classes.settings import CONSTANTS

DIALOG_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui', 'about_dialog.ui'))


class AboutDialog(QDialog, DIALOG_CLASS):
    """
    About Dialog
    """

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        QDialog.__init__(self, parent)
        self.setupUi(self)
        pixmap = QPixmap(':/plugins/qrave_toolbar/RaveAddIn.png').scaled(128, 128)
        self.logo.setPixmap(pixmap)
        self.website.setText('<a href="{0}">{0}</a>'.format(CONSTANTS['webUrl']))
        self.issues.setText('<a href="{0}">{0}</a>'.format(CONSTANTS['issueUrl']))
