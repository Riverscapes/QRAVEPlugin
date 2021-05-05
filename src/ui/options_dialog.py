# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file './src/ui/options_dialog.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(365, 251)
        self.verticalLayout = QtWidgets.QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.basemapsInclude = QtWidgets.QCheckBox(Dialog)
        self.basemapsInclude.setObjectName("basemapsInclude")
        self.verticalLayout.addWidget(self.basemapsInclude)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(Dialog)
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.basemapRegion = QtWidgets.QComboBox(Dialog)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.basemapRegion.sizePolicy().hasHeightForWidth())
        self.basemapRegion.setSizePolicy(sizePolicy)
        self.basemapRegion.setObjectName("basemapRegion")
        self.horizontalLayout.addWidget(self.basemapRegion)
        self.regionHelp = QtWidgets.QPushButton(Dialog)
        self.regionHelp.setObjectName("regionHelp")
        self.horizontalLayout.addWidget(self.regionHelp)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.loadDefaultView = QtWidgets.QCheckBox(Dialog)
        self.loadDefaultView.setObjectName("loadDefaultView")
        self.verticalLayout.addWidget(self.loadDefaultView)
        spacerItem = QtWidgets.QSpacerItem(20, 154, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.buttonBox = QtWidgets.QDialogButtonBox(Dialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Apply|QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Reset)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Options"))
        self.basemapsInclude.setText(_translate("Dialog", "Include basemaps in explorer tree"))
        self.label.setText(_translate("Dialog", "Region"))
        self.regionHelp.setText(_translate("Dialog", "..."))
        self.loadDefaultView.setText(_translate("Dialog", "Load default project views when opening projects"))

