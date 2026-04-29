from qgis.PyQt import QtGui
from qgis.PyQt.QtWidgets import QDialog, QLabel, QVBoxLayout, QDialogButtonBox, QSizePolicy, QFormLayout, QHBoxLayout
from qgis.PyQt.QtCore import pyqtSignal, Qt, QSize
from .classes.settings import CONSTANTS
from ..__version__ import __version__


class AboutDialog(QDialog):
    """
    About Dialog
    """

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        QDialog.__init__(self, parent)
        self.setupUi()

        pixmap = QtGui.QIcon(':/plugins/qrave_toolbar/viewer-icon.svg').pixmap(128, 128)
        self.logo.setPixmap(pixmap)

        self.setWindowTitle("About Riverscapes Viewer")
        self.version.setText(str(__version__))
        self.website.setText('<a href="{0}">{0}</a>'.format(CONSTANTS['webUrl']))
        self.issues.setText('<a href="{0}">{0}</a>'.format(CONSTANTS['issueUrl']))
        self.changelog.setText('<a href="{0}">{0}</a>'.format(CONSTANTS['changelogUrl']))
        self.acknowledgements.setText('<a href="{0}">{0}</a>'.format(CONSTANTS['acknowledgementsUrl']))

    def setupUi(self):
        self.resize(700, 200)
        self.verticalLayout_3 = QVBoxLayout(self)
        self.horizontalLayout = QHBoxLayout()
        # Logo
        self.logo = QLabel(self)
        self.logo.setText("LOGO")
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.logo.sizePolicy().hasHeightForWidth())
        self.logo.setSizePolicy(sizePolicy)
        self.logo.setMinimumSize(QSize(128, 128))
        self.logo.setMaximumSize(QSize(128, 128))

        # Add a vertical layout for the logo to push it to the top
        self.logoLayout = QVBoxLayout()
        self.logoLayout.addWidget(self.logo)
        self.logoLayout.addStretch()  # Push logo to the top

        self.horizontalLayout.addLayout(self.logoLayout)

        # Title and form layout
        self.verticalLayout_2 = QVBoxLayout()
        self.label_2 = QLabel(self)
        font = QtGui.QFont()
        font.setPointSize(14)
        font.setBold(True)
        font.setWeight(75)
        self.label_2.setFont(font)
        self.label_2.setText("Riverscapes Viewer Plugin for QGIS")
        self.verticalLayout_2.addWidget(self.label_2)

        # Form layout for all info
        self.formLayout = QFormLayout()
        self.version = QLabel(self)
        self.formLayout.addRow("Version", self.version)

        self.website = QLabel(self)
        self.website.setTextFormat(Qt.RichText)
        self.website.setOpenExternalLinks(True)
        self.formLayout.addRow("Website", self.website)

        self.issues = QLabel(self)
        self.issues.setTextFormat(Qt.RichText)
        self.issues.setOpenExternalLinks(True)
        self.formLayout.addRow("Issues", self.issues)

        self.changelog = QLabel(self)
        self.changelog.setTextFormat(Qt.RichText)
        self.changelog.setOpenExternalLinks(True)
        self.formLayout.addRow("Changelog", self.changelog)

        self.acknowledgements = QLabel(self)
        self.acknowledgements.setTextFormat(Qt.RichText)
        self.acknowledgements.setOpenExternalLinks(True)
        self.formLayout.addRow("Acknowledgements", self.acknowledgements)

        self.verticalLayout_2.addLayout(self.formLayout)
        self.verticalLayout_2.addStretch()  # Push form to the top

        self.horizontalLayout.addLayout(self.verticalLayout_2)
        self.verticalLayout_3.addLayout(self.horizontalLayout)

        # Only add the close button
        self.closeButton = QDialogButtonBox(self)
        self.closeButton.setOrientation(Qt.Horizontal)
        self.closeButton.setStandardButtons(QDialogButtonBox.Close)
        self.verticalLayout_3.addWidget(self.closeButton)

        # Connect the rejected signal of the close button to the reject slot of the dialog
        self.closeButton.rejected.connect(self.reject)
