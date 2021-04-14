import os
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog
from qgis.PyQt.QtGui import QPixmap
from qgis.PyQt.QtCore import pyqtSignal
# from settings import Settings

DIALOG_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'about.ui'))


class AboutDialog(QDialog, DIALOG_CLASS):

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        QDialog.__init__(self, parent)
        self.setupUi(self)
        pixmap = QPixmap(':/plugins/qrave_toolbar/RaveAddIn.png').scaled(128, 128)
        self.logo.setPixmap(pixmap)
        self.website.setText('<a href="https://rave.riverscapes.xyz">https://rave.riverscapes.xyz</a>')
        self.issues.setText('<a href="http://rave.riverscapes.xyz/known-bugs.html">http://rave.riverscapes.xyz/known-bugs.html</a>')
