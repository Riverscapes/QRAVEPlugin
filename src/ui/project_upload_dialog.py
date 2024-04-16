# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file './src/ui/project_upload_dialog.ui'
#
# Created by: PyQt5 UI code generator 5.15.10
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(343, 810)
        self.verticalLayout = QtWidgets.QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.projectNameLayout = QtWidgets.QHBoxLayout()
        self.projectNameLayout.setObjectName("projectNameLayout")
        self.projectNameLable = QtWidgets.QLabel(Dialog)
        self.projectNameLable.setMaximumSize(QtCore.QSize(50, 16777215))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.projectNameLable.setFont(font)
        self.projectNameLable.setObjectName("projectNameLable")
        self.projectNameLayout.addWidget(self.projectNameLable)
        self.projectNameValue = QtWidgets.QLabel(Dialog)
        self.projectNameValue.setObjectName("projectNameValue")
        self.projectNameLayout.addWidget(self.projectNameValue)
        self.verticalLayout.addLayout(self.projectNameLayout)
        self.projectPathLayout = QtWidgets.QHBoxLayout()
        self.projectPathLayout.setObjectName("projectPathLayout")
        self.projectPathLable = QtWidgets.QLabel(Dialog)
        self.projectPathLable.setMaximumSize(QtCore.QSize(50, 16777215))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.projectPathLable.setFont(font)
        self.projectPathLable.setObjectName("projectPathLable")
        self.projectPathLayout.addWidget(self.projectPathLable)
        self.projectPathValue = QtWidgets.QLineEdit(Dialog)
        self.projectPathValue.setEnabled(True)
        self.projectPathValue.setReadOnly(True)
        self.projectPathValue.setObjectName("projectPathValue")
        self.projectPathLayout.addWidget(self.projectPathValue)
        self.verticalLayout.addLayout(self.projectPathLayout)
        self.loginButtonLayout = QtWidgets.QHBoxLayout()
        self.loginButtonLayout.setObjectName("loginButtonLayout")
        self.loginStatusLable = QtWidgets.QLabel(Dialog)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.loginStatusLable.setFont(font)
        self.loginStatusLable.setObjectName("loginStatusLable")
        self.loginButtonLayout.addWidget(self.loginStatusLable)
        self.loginStatusValue = QtWidgets.QLabel(Dialog)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.loginStatusValue.setFont(font)
        self.loginStatusValue.setObjectName("loginStatusValue")
        self.loginButtonLayout.addWidget(self.loginStatusValue)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.loginButtonLayout.addItem(spacerItem)
        self.loginResetBtn = QtWidgets.QToolButton(Dialog)
        self.loginResetBtn.setObjectName("loginResetBtn")
        self.loginButtonLayout.addWidget(self.loginResetBtn)
        self.verticalLayout.addLayout(self.loginButtonLayout)
        self.newOrUpdateLayout = QtWidgets.QGroupBox(Dialog)
        self.newOrUpdateLayout.setObjectName("newOrUpdateLayout")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.newOrUpdateLayout)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.optModifyProject = QtWidgets.QRadioButton(self.newOrUpdateLayout)
        self.optModifyProject.setChecked(True)
        self.optModifyProject.setObjectName("optModifyProject")
        self.horizontalLayout_2.addWidget(self.optModifyProject)
        self.viewExistingBtn = QtWidgets.QToolButton(self.newOrUpdateLayout)
        self.viewExistingBtn.setObjectName("viewExistingBtn")
        self.horizontalLayout_2.addWidget(self.viewExistingBtn)
        self.verticalLayout_2.addLayout(self.horizontalLayout_2)
        self.optNewProject = QtWidgets.QRadioButton(self.newOrUpdateLayout)
        self.optNewProject.setObjectName("optNewProject")
        self.verticalLayout_2.addWidget(self.optNewProject)
        self.verticalLayout.addWidget(self.newOrUpdateLayout)
        self.ownershipGroup = QtWidgets.QGroupBox(Dialog)
        self.ownershipGroup.setMinimumSize(QtCore.QSize(0, 100))
        self.ownershipGroup.setObjectName("ownershipGroup")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.ownershipGroup)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.optOwnerOrg = QtWidgets.QRadioButton(self.ownershipGroup)
        self.optOwnerOrg.setChecked(True)
        self.optOwnerOrg.setObjectName("optOwnerOrg")
        self.horizontalLayout.addWidget(self.optOwnerOrg)
        self.orgSelect = QtWidgets.QComboBox(self.ownershipGroup)
        self.orgSelect.setObjectName("orgSelect")
        self.horizontalLayout.addWidget(self.orgSelect)
        self.verticalLayout_3.addLayout(self.horizontalLayout)
        self.optOwnerMe = QtWidgets.QRadioButton(self.ownershipGroup)
        self.optOwnerMe.setChecked(False)
        self.optOwnerMe.setObjectName("optOwnerMe")
        self.verticalLayout_3.addWidget(self.optOwnerMe)
        self.verticalLayout.addWidget(self.ownershipGroup)
        self.visibilityGroup = QtWidgets.QGroupBox(Dialog)
        self.visibilityGroup.setObjectName("visibilityGroup")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.visibilityGroup)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.visibilitySelect = QtWidgets.QComboBox(self.visibilityGroup)
        self.visibilitySelect.setObjectName("visibilitySelect")
        self.visibilitySelect.addItem("")
        self.visibilitySelect.addItem("")
        self.visibilitySelect.addItem("")
        self.verticalLayout_4.addWidget(self.visibilitySelect)
        self.verticalLayout.addWidget(self.visibilityGroup)
        self.tagGroup = QtWidgets.QGroupBox(Dialog)
        self.tagGroup.setObjectName("tagGroup")
        self.verticalLayout_5 = QtWidgets.QVBoxLayout(self.tagGroup)
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.tagList = QtWidgets.QListWidget(self.tagGroup)
        self.tagList.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.tagList.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tagList.setObjectName("tagList")
        self.verticalLayout_5.addWidget(self.tagList)
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.addTag = QtWidgets.QLineEdit(self.tagGroup)
        self.addTag.setObjectName("addTag")
        self.horizontalLayout_4.addWidget(self.addTag)
        self.addTagButton = QtWidgets.QToolButton(self.tagGroup)
        self.addTagButton.setObjectName("addTagButton")
        self.horizontalLayout_4.addWidget(self.addTagButton)
        self.removeTagButton = QtWidgets.QToolButton(self.tagGroup)
        self.removeTagButton.setObjectName("removeTagButton")
        self.horizontalLayout_4.addWidget(self.removeTagButton)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_4.addItem(spacerItem1)
        self.verticalLayout_5.addLayout(self.horizontalLayout_4)
        self.verticalLayout.addWidget(self.tagGroup)
        spacerItem2 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem2)
        spacerItem3 = QtWidgets.QSpacerItem(20, 154, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem3)
        self.uploadGroup = QtWidgets.QGroupBox(Dialog)
        self.uploadGroup.setObjectName("uploadGroup")
        self.verticalLayout_6 = QtWidgets.QVBoxLayout(self.uploadGroup)
        self.verticalLayout_6.setObjectName("verticalLayout_6")
        self.todoLabel = QtWidgets.QLabel(self.uploadGroup)
        font = QtGui.QFont()
        font.setPointSize(11)
        font.setItalic(True)
        font.setUnderline(False)
        self.todoLabel.setFont(font)
        self.todoLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.todoLabel.setObjectName("todoLabel")
        self.verticalLayout_6.addWidget(self.todoLabel)
        self.progressBar = QtWidgets.QProgressBar(self.uploadGroup)
        self.progressBar.setProperty("value", 24)
        self.progressBar.setObjectName("progressBar")
        self.verticalLayout_6.addWidget(self.progressBar)
        self.progressSubLabel = QtWidgets.QLabel(self.uploadGroup)
        font = QtGui.QFont()
        font.setPointSize(11)
        font.setItalic(True)
        self.progressSubLabel.setFont(font)
        self.progressSubLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.progressSubLabel.setObjectName("progressSubLabel")
        self.verticalLayout_6.addWidget(self.progressSubLabel)
        self.verticalLayout.addWidget(self.uploadGroup)
        self.openWebProjectBtn = QtWidgets.QPushButton(Dialog)
        self.openWebProjectBtn.setObjectName("openWebProjectBtn")
        self.verticalLayout.addWidget(self.openWebProjectBtn)
        self.errorLayout = QtWidgets.QHBoxLayout()
        self.errorLayout.setObjectName("errorLayout")
        self.errorSummaryLable = QtWidgets.QLabel(Dialog)
        self.errorSummaryLable.setObjectName("errorSummaryLable")
        self.errorLayout.addWidget(self.errorSummaryLable)
        self.errorMoreBtn = QtWidgets.QToolButton(Dialog)
        self.errorMoreBtn.setObjectName("errorMoreBtn")
        self.errorLayout.addWidget(self.errorMoreBtn)
        self.verticalLayout.addLayout(self.errorLayout)
        self.actionBtnLayout = QtWidgets.QHBoxLayout()
        self.actionBtnLayout.setObjectName("actionBtnLayout")
        self.actionBtnBox = QtWidgets.QDialogButtonBox(Dialog)
        self.actionBtnBox.setOrientation(QtCore.Qt.Horizontal)
        self.actionBtnBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Help)
        self.actionBtnBox.setObjectName("actionBtnBox")
        self.actionBtnLayout.addWidget(self.actionBtnBox)
        self.startBtn = QtWidgets.QPushButton(Dialog)
        self.startBtn.setObjectName("startBtn")
        self.actionBtnLayout.addWidget(self.startBtn)
        self.verticalLayout.addLayout(self.actionBtnLayout)

        self.retranslateUi(Dialog)
        self.actionBtnBox.accepted.connect(Dialog.accept) # type: ignore
        self.actionBtnBox.rejected.connect(Dialog.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Upload Project"))
        self.projectNameLable.setText(_translate("Dialog", "Project:"))
        self.projectNameValue.setText(_translate("Dialog", "Riverscapes Context for HUC 1604020108"))
        self.projectPathLable.setText(_translate("Dialog", "Path:"))
        self.projectPathValue.setText(_translate("Dialog", "..."))
        self.loginStatusLable.setText(_translate("Dialog", "Status:"))
        self.loginStatusValue.setText(_translate("Dialog", "Logged In"))
        self.loginResetBtn.setText(_translate("Dialog", "Reset"))
        self.newOrUpdateLayout.setTitle(_translate("Dialog", "New Or Update"))
        self.optModifyProject.setText(_translate("Dialog", "Modify existing project"))
        self.viewExistingBtn.setText(_translate("Dialog", "View"))
        self.optNewProject.setText(_translate("Dialog", "Upload as new project"))
        self.ownershipGroup.setTitle(_translate("Dialog", "Project Ownership"))
        self.optOwnerOrg.setText(_translate("Dialog", "Organization"))
        self.optOwnerMe.setText(_translate("Dialog", "My Personal Account"))
        self.visibilityGroup.setTitle(_translate("Dialog", "Project Visibility"))
        self.visibilitySelect.setItemText(0, _translate("Dialog", "PUBLIC"))
        self.visibilitySelect.setItemText(1, _translate("Dialog", "PRIVATE"))
        self.visibilitySelect.setItemText(2, _translate("Dialog", "SECRET"))
        self.tagGroup.setTitle(_translate("Dialog", "Tags"))
        self.addTag.setPlaceholderText(_translate("Dialog", "Add Tag"))
        self.addTagButton.setText(_translate("Dialog", "add"))
        self.removeTagButton.setText(_translate("Dialog", "remove"))
        self.uploadGroup.setTitle(_translate("Dialog", "Upload"))
        self.todoLabel.setText(_translate("Dialog", "..."))
        self.progressSubLabel.setText(_translate("Dialog", "Uploading vbet.gpkg"))
        self.openWebProjectBtn.setText(_translate("Dialog", "View In Data Exchange"))
        self.errorSummaryLable.setText(_translate("Dialog", "Error"))
        self.errorMoreBtn.setToolTip(_translate("Dialog", "Copy error to clipboard"))
        self.errorMoreBtn.setText(_translate("Dialog", "More"))
        self.startBtn.setText(_translate("Dialog", "Start"))