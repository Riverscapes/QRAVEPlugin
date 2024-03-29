# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file './src/ui/about_dialog.ui'
#
# Created by: PyQt5 UI code generator 5.15.4
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(666, 434)
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(Dialog)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.logo = QtWidgets.QLabel(Dialog)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.logo.sizePolicy().hasHeightForWidth())
        self.logo.setSizePolicy(sizePolicy)
        self.logo.setMinimumSize(QtCore.QSize(128, 128))
        self.logo.setMaximumSize(QtCore.QSize(128, 128))
        self.logo.setObjectName("logo")
        self.horizontalLayout.addWidget(self.logo)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.label_2 = QtWidgets.QLabel(Dialog)
        font = QtGui.QFont()
        font.setPointSize(14)
        font.setBold(True)
        font.setWeight(75)
        self.label_2.setFont(font)
        self.label_2.setObjectName("label_2")
        self.verticalLayout_2.addWidget(self.label_2)
        self.version = QtWidgets.QLabel(Dialog)
        self.version.setObjectName("version")
        self.verticalLayout_2.addWidget(self.version)
        self.groupBox_2 = QtWidgets.QGroupBox(Dialog)
        self.groupBox_2.setFlat(False)
        self.groupBox_2.setCheckable(False)
        self.groupBox_2.setObjectName("groupBox_2")
        self.gridLayout = QtWidgets.QGridLayout(self.groupBox_2)
        self.gridLayout.setObjectName("gridLayout")
        self.website = QtWidgets.QLabel(self.groupBox_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.website.sizePolicy().hasHeightForWidth())
        self.website.setSizePolicy(sizePolicy)
        self.website.setTextFormat(QtCore.Qt.RichText)
        self.website.setOpenExternalLinks(True)
        self.website.setObjectName("website")
        self.gridLayout.addWidget(self.website, 0, 1, 1, 1)
        self.issues = QtWidgets.QLabel(self.groupBox_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.issues.sizePolicy().hasHeightForWidth())
        self.issues.setSizePolicy(sizePolicy)
        self.issues.setTextFormat(QtCore.Qt.RichText)
        self.issues.setOpenExternalLinks(True)
        self.issues.setObjectName("issues")
        self.gridLayout.addWidget(self.issues, 1, 1, 1, 1)
        self.websiteLabel = QtWidgets.QLabel(self.groupBox_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.websiteLabel.sizePolicy().hasHeightForWidth())
        self.websiteLabel.setSizePolicy(sizePolicy)
        self.websiteLabel.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.websiteLabel.setObjectName("websiteLabel")
        self.gridLayout.addWidget(self.websiteLabel, 1, 0, 1, 1)
        self.issuesLabel = QtWidgets.QLabel(self.groupBox_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.issuesLabel.sizePolicy().hasHeightForWidth())
        self.issuesLabel.setSizePolicy(sizePolicy)
        self.issuesLabel.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.issuesLabel.setObjectName("issuesLabel")
        self.gridLayout.addWidget(self.issuesLabel, 0, 0, 1, 1)
        self.changelog = QtWidgets.QLabel(self.groupBox_2)
        self.changelog.setOpenExternalLinks(True)
        self.changelog.setObjectName("changelog")
        self.gridLayout.addWidget(self.changelog, 2, 1, 1, 1)
        self.changelogLabel = QtWidgets.QLabel(self.groupBox_2)
        self.changelogLabel.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.changelogLabel.setObjectName("changelogLabel")
        self.gridLayout.addWidget(self.changelogLabel, 2, 0, 1, 1)
        self.gridLayout.setColumnStretch(0, 1)
        self.gridLayout.setColumnStretch(1, 4)
        self.verticalLayout_2.addWidget(self.groupBox_2)
        self.horizontalLayout.addLayout(self.verticalLayout_2)
        self.verticalLayout_3.addLayout(self.horizontalLayout)
        self.groupBox = QtWidgets.QGroupBox(Dialog)
        self.groupBox.setObjectName("groupBox")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.groupBox)
        self.verticalLayout.setObjectName("verticalLayout")
        self.acknowledgements = QtWidgets.QTextBrowser(self.groupBox)
        self.acknowledgements.setEnabled(True)
        self.acknowledgements.setReadOnly(True)
        self.acknowledgements.setCursorWidth(0)
        self.acknowledgements.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByKeyboard|QtCore.Qt.LinksAccessibleByMouse|QtCore.Qt.TextBrowserInteraction|QtCore.Qt.TextSelectableByKeyboard|QtCore.Qt.TextSelectableByMouse)
        self.acknowledgements.setOpenExternalLinks(True)
        self.acknowledgements.setObjectName("acknowledgements")
        self.verticalLayout.addWidget(self.acknowledgements)
        self.verticalLayout_3.addWidget(self.groupBox)
        self.closeButton = QtWidgets.QDialogButtonBox(Dialog)
        self.closeButton.setOrientation(QtCore.Qt.Horizontal)
        self.closeButton.setStandardButtons(QtWidgets.QDialogButtonBox.Close)
        self.closeButton.setObjectName("closeButton")
        self.verticalLayout_3.addWidget(self.closeButton)

        self.retranslateUi(Dialog)
        self.closeButton.rejected.connect(Dialog.reject)
        self.closeButton.accepted.connect(Dialog.accept)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Dialog"))
        self.logo.setText(_translate("Dialog", "LOGO"))
        self.label_2.setText(_translate("Dialog", "Riverscapes Viewer Plugin for QGIS"))
        self.version.setText(_translate("Dialog", "Version:"))
        self.groupBox_2.setTitle(_translate("Dialog", "Support"))
        self.website.setText(_translate("Dialog", "..."))
        self.issues.setText(_translate("Dialog", "..."))
        self.websiteLabel.setText(_translate("Dialog", "Issues"))
        self.issuesLabel.setText(_translate("Dialog", "Web site"))
        self.changelog.setText(_translate("Dialog", "..."))
        self.changelogLabel.setText(_translate("Dialog", "Changelog"))
        self.groupBox.setTitle(_translate("Dialog", "Acknowledgements"))
        self.acknowledgements.setHtml(_translate("Dialog", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'MS Shell Dlg 2\'; font-size:8pt; font-weight:400; font-style:normal;\">\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p></body></html>"))
