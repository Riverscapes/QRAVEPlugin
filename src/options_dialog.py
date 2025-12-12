from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QComboBox, QPushButton, QSizePolicy, QSpacerItem, QGridLayout, QRadioButton
from qgis.PyQt.QtCore import pyqtSignal, Qt
from qgis.PyQt.QtGui import QIcon

from .classes.settings import Settings
from .classes.basemaps import BaseMaps


class OptionsDialog(QDialog):

    closingPlugin = pyqtSignal()
    dataChange = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        QDialog.__init__(self, parent)
        self.setupUi()
        self.setWindowTitle("Riverscapes Viewer Settings")

        self.basemaps = BaseMaps()
        self.settings = Settings()
        self.buttonBox.clicked.connect(self.commit_settings)
        self.basemaps.load()
        self.setValues()

        self.regionHelp.setText(None)
        self.regionHelp.setIcon(QIcon(':/plugins/qrave_toolbar/Help.png'))
        self.regionHelp.setToolTip("Help choosing a basemap region")
        # self.regionHelp.clicked.connect(la
        self.regionHelp.setEnabled(False)

    def setValues(self):
        self.basemapsInclude.setChecked(self.settings.getValue('basemapsInclude'))
        self.loadDefaultView.setChecked(self.settings.getValue('loadDefaultView'))
        self.autoUpdate.setChecked(self.settings.getValue('autoUpdate'))

        # Set the combo box
        self.basemapRegion.clear()
        region = self.settings.getValue('basemapRegion')
        self.basemapRegion.addItems(self.basemaps.regions.keys())
        if region and len(region) > 0:
            self.basemapRegion.setCurrentText(region)

        # Set the dock location radio buttons
        dock_location = self.settings.getValue('dockLocation')
        if dock_location == "left":
            self.left_radio.setChecked(True)
        elif dock_location == "right":
            self.right_radio.setChecked(True)
        else:
            self.left_radio.setChecked(True)  # Default

    def commit_settings(self, btn):
        role = self.buttonBox.buttonRole(btn)

        if role == QDialogButtonBox.ApplyRole:
            self.settings.setValue('basemapsInclude', self.basemapsInclude.isChecked())
            self.settings.setValue('loadDefaultView', self.loadDefaultView.isChecked())
            self.settings.setValue('basemapRegion', self.basemapRegion.currentText())
            self.settings.setValue('autoUpdate', self.autoUpdate.isChecked())
            if self.left_radio.isChecked():
                self.settings.setValue('dockLocation', 'left')
            elif self.right_radio.isChecked():
                self.settings.setValue('dockLocation', 'right')

        elif role == QDialogButtonBox.ResetRole:
            self.settings.resetAllSettings()
            self.setValues()

        # Emit a datachange so we can trigger other parts of this plugin
        self.dataChange.emit()

    def setupUi(self):
        self.resize(365, 251)
        self.verticalLayout = QVBoxLayout(self)
        self.verticalLayout.setObjectName("verticalLayout")
        # Basemaps and region
        self.basemapsInclude = QCheckBox(self)
        self.basemapsInclude.setObjectName("basemapsInclude")
        self.verticalLayout.addWidget(self.basemapsInclude)
        self.basemapsInclude.setText("Include basemaps in explorer tree")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QLabel(self)
        self.label.setObjectName("label")
        self.label.setText("Region")
        self.horizontalLayout.addWidget(self.label)
        self.basemapRegion = QComboBox(self)
        sizePolicy = QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.basemapRegion.sizePolicy().hasHeightForWidth())
        self.basemapRegion.setSizePolicy(sizePolicy)
        self.basemapRegion.setObjectName("basemapRegion")
        self.horizontalLayout.addWidget(self.basemapRegion)
        self.regionHelp = QPushButton(self)
        self.regionHelp.setObjectName("regionHelp")
        self.horizontalLayout.addWidget(self.regionHelp)
        self.verticalLayout.addLayout(self.horizontalLayout)
        # Auto Update Checkbox
        self.autoUpdate = QCheckBox(self)
        self.autoUpdate.setObjectName("autoUpdate")
        self.autoUpdate.setText("Automatically update resource files (symbology, business logic etc.)")
        self.verticalLayout.addWidget(self.autoUpdate)
        # Load Default View Checkbox
        self.loadDefaultView = QCheckBox(self)
        self.loadDefaultView.setObjectName("loadDefaultView")
        self.loadDefaultView.setText("Load default project views when opening projects")
        self.verticalLayout.addWidget(self.loadDefaultView)
        # Dock location radio buttons
        self.grid = QGridLayout()
        self.labelDock = QLabel("Default Dock widget location")
        self.grid.addWidget(self.labelDock, 0, 0, 1, 2)
        self.left_radio = QRadioButton("Dock to left")
        self.right_radio = QRadioButton("Dock to right")
        self.grid.addWidget(self.left_radio, 1, 0)
        self.grid.addWidget(self.right_radio, 1, 1)
        self.verticalLayout.addLayout(self.grid)
        # Button Box
        spacerItem = QSpacerItem(20, 154, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.buttonBox = QDialogButtonBox(self)
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Apply|QDialogButtonBox.Cancel|QDialogButtonBox.Reset)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)
        # Standard buttons
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
