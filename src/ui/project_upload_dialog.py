from PyQt5 import QtCore, QtGui, QtWidgets
from ..file_selection_widget import ProjectFileSelectionWidget


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(600, 700)
        self.verticalLayoutMain = QtWidgets.QVBoxLayout(Dialog)
        self.verticalLayoutMain.setObjectName("verticalLayoutMain")

        # Create stacked widget
        self.stackedWidget = QtWidgets.QStackedWidget(Dialog)
        self.stackedWidget.setObjectName("stackedWidget")
        
        # =====================================================================
        # Step 1: Form details
        # =====================================================================
        self.step1 = QtWidgets.QWidget()
        self.layoutStep1 = QtWidgets.QVBoxLayout(self.step1)
        
        # Riverscapes Project Group
        self.groupProject = QtWidgets.QGroupBox("Riverscapes Project")
        self.grdGroupProject = QtWidgets.QGridLayout(self.groupProject)
        
        self.projectNameLabel = QtWidgets.QLabel("Project name")
        self.grdGroupProject.addWidget(self.projectNameLabel, 0, 0)
        
        self.projectNameValue = QtWidgets.QLabel("...")
        self.grdGroupProject.addWidget(self.projectNameValue, 0, 1)
        
        self.projectPathLabel = QtWidgets.QLabel("Local path")
        self.grdGroupProject.addWidget(self.projectPathLabel, 1, 0)
        
        self.projectPathValue = QtWidgets.QLineEdit()
        self.projectPathValue.setReadOnly(True)
        self.grdGroupProject.addWidget(self.projectPathValue, 1, 1)
        
        self.loginStatusLabel = QtWidgets.QLabel("Riverscapes login")
        self.grdGroupProject.addWidget(self.loginStatusLabel, 2, 0)
        
        self.loginButtonLayout = QtWidgets.QHBoxLayout()
        self.loginStatusValue = QtWidgets.QLabel("Logging in...")
        self.loginButtonLayout.addWidget(self.loginStatusValue)
        self.loginButtonLayout.addStretch()
        self.loginResetBtn = QtWidgets.QToolButton()
        self.loginResetBtn.setText("Reset")
        self.loginButtonLayout.addWidget(self.loginResetBtn)
        self.grdGroupProject.addLayout(self.loginButtonLayout, 2, 1)

        # Project Details Card
        self.frameProjectDetails = QtWidgets.QFrame()
        self.frameProjectDetails.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frameProjectDetails.setStyleSheet("""
            QFrame {
                background-color: #f9f9f9;
                border: 1px solid #dcdcdc;
                border-radius: 6px;
            }
            QLabel {
                border: none;
                background-color: transparent;
            }
        """)
        self.layoutProjectDetails = QtWidgets.QVBoxLayout(self.frameProjectDetails)
        self.lblProjectDetails = QtWidgets.QLabel("")
        self.lblProjectDetails.setWordWrap(True)
        self.lblProjectDetails.setTextFormat(QtCore.Qt.RichText)
        self.lblProjectDetails.setOpenExternalLinks(True)
        self.layoutProjectDetails.addWidget(self.lblProjectDetails)
        self.grdGroupProject.addWidget(self.frameProjectDetails, 3, 0, 1, 2)
        
        self.layoutStep1.addWidget(self.groupProject)

        # New or Update Choice
        self.newOrUpdateLayout = QtWidgets.QGroupBox("New Or Update")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.newOrUpdateLayout)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.optModifyProject = QtWidgets.QRadioButton("Modify existing project")
        self.optModifyProject.setChecked(True)
        self.horizontalLayout_2.addWidget(self.optModifyProject)
        self.noDeleteChk = QtWidgets.QCheckBox("No remote delete")
        self.noDeleteChk.setToolTip("Do not delete remote files even if they are not present locally")
        self.horizontalLayout_2.addWidget(self.noDeleteChk)
        self.viewExistingBtn = QtWidgets.QToolButton()
        self.viewExistingBtn.setText("Visit")
        self.horizontalLayout_2.addWidget(self.viewExistingBtn)
        self.verticalLayout_2.addLayout(self.horizontalLayout_2)
        self.optNewProject = QtWidgets.QRadioButton("Upload as new project")
        self.verticalLayout_2.addWidget(self.optNewProject)
        self.layoutStep1.addWidget(self.newOrUpdateLayout)

        # Ownership Group
        self.ownershipGroup = QtWidgets.QGroupBox("Project Ownership")
        self.ownershipGroup.setMinimumSize(QtCore.QSize(0, 100))
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.ownershipGroup)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.optOwnerOrg = QtWidgets.QRadioButton("Organization")
        self.optOwnerOrg.setChecked(True)
        self.horizontalLayout.addWidget(self.optOwnerOrg)
        self.orgSelect = QtWidgets.QComboBox()
        self.horizontalLayout.addWidget(self.orgSelect)
        self.verticalLayout_3.addLayout(self.horizontalLayout)
        self.optOwnerMe = QtWidgets.QRadioButton("My personal account")
        self.verticalLayout_3.addWidget(self.optOwnerMe)
        self.layoutStep1.addWidget(self.ownershipGroup)

        # Visibility Group
        self.visibilityGroup = QtWidgets.QGroupBox("Project Visibility")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.visibilityGroup)
        self.visibilitySelect = QtWidgets.QComboBox()
        self.visibilitySelect.addItems(["PUBLIC", "PRIVATE", "SECRET"])
        self.verticalLayout_4.addWidget(self.visibilitySelect)
        self.layoutStep1.addWidget(self.visibilityGroup)

        # Tags Group
        self.tagGroup = QtWidgets.QGroupBox("Tags")
        self.verticalLayout_5 = QtWidgets.QVBoxLayout(self.tagGroup)
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.addTag = QtWidgets.QLineEdit()
        self.addTag.setPlaceholderText("Add Tag")
        self.horizontalLayout_4.addWidget(self.addTag)
        self.addTagButton = QtWidgets.QToolButton()
        self.addTagButton.setText("Add")
        self.horizontalLayout_4.addWidget(self.addTagButton)
        self.removeTagButton = QtWidgets.QToolButton()
        self.removeTagButton.setText("Remove")
        self.horizontalLayout_4.addWidget(self.removeTagButton)
        self.tagList = QtWidgets.QListWidget()
        self.tagList.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.tagList.setFixedHeight(80)
        self.verticalLayout_5.addLayout(self.horizontalLayout_4)
        self.verticalLayout_5.addWidget(self.tagList)
        self.layoutStep1.addWidget(self.tagGroup)
                
        self.layoutStep1.addStretch()
        self.stackedWidget.addWidget(self.step1)

        # =====================================================================
        # Step 2: File Selection
        # =====================================================================
        self.step2 = QtWidgets.QWidget()
        self.layoutStep2 = QtWidgets.QVBoxLayout(self.step2)
        self.lblStep2 = QtWidgets.QLabel("Step 2: Select files to upload")
        font_step = QtGui.QFont()
        font_step.setBold(True)
        font_step.setPointSize(12)
        self.lblStep2.setFont(font_step)
        self.layoutStep2.addWidget(self.lblStep2)
        
        self.fileSelection = ProjectFileSelectionWidget()
        self.layoutStep2.addWidget(self.fileSelection)
        
        self.lblSelectionSummary = QtWidgets.QLabel("")
        font_summary = QtGui.QFont()
        font_summary.setItalic(True)
        font_summary.setPointSize(11)
        self.lblSelectionSummary.setFont(font_summary)
        self.lblSelectionSummary.setAlignment(QtCore.Qt.AlignCenter)
        self.layoutStep2.addWidget(self.lblSelectionSummary)
        
        self.stackedWidget.addWidget(self.step2)

        # =====================================================================
        # Step 3: Upload Status
        # =====================================================================
        self.step3 = QtWidgets.QWidget()
        self.layoutStep3 = QtWidgets.QVBoxLayout(self.step3)
        self.lblStep3 = QtWidgets.QLabel("Step 3: Uploading...")
        self.lblStep3.setFont(font_step)
        self.layoutStep3.addWidget(self.lblStep3)
        
        self.uploadGroup = QtWidgets.QGroupBox("Upload Status")
        self.verticalLayout_6 = QtWidgets.QVBoxLayout(self.uploadGroup)
        self.todoLabel = QtWidgets.QLabel("...")
        font_todo = QtGui.QFont()
        font_todo.setPointSize(11)
        font_todo.setItalic(True)
        self.todoLabel.setFont(font_todo)
        self.todoLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.verticalLayout_6.addWidget(self.todoLabel)
        
        self.progressBar = QtWidgets.QProgressBar()
        self.progressBar.setValue(0)
        self.verticalLayout_6.addWidget(self.progressBar)
        
        self.progressSubLabel = QtWidgets.QLabel("...")
        self.progressSubLabel.setFont(font_todo)
        self.progressSubLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.verticalLayout_6.addWidget(self.progressSubLabel)
        self.layoutStep3.addWidget(self.uploadGroup)
        
        self.openWebProjectBtn = QtWidgets.QPushButton("View In Data Exchange")
        self.layoutStep3.addWidget(self.openWebProjectBtn)
        self.layoutStep3.addStretch()
        self.stackedWidget.addWidget(self.step3)

        self.verticalLayoutMain.addWidget(self.stackedWidget)

        # =====================================================================
        # Error Layout
        # =====================================================================
        self.errorLayout = QtWidgets.QHBoxLayout()
        self.errorSummaryLable = QtWidgets.QLabel("Error")
        self.errorLayout.addWidget(self.errorSummaryLable)
        self.errorMoreBtn = QtWidgets.QToolButton()
        self.errorMoreBtn.setText("More")
        self.errorMoreBtn.setToolTip("Copy error to clipboard")
        self.verticalLayoutMain.addLayout(self.errorLayout)

        # =====================================================================
        # Footer / Navigation
        # =====================================================================
        self.navLayout = QtWidgets.QHBoxLayout()
        self.btnHelp = QtWidgets.QPushButton("Help")
        self.navLayout.addWidget(self.btnHelp)
        
        self.btnBack = QtWidgets.QPushButton("Back")
        self.navLayout.addWidget(self.btnBack)
        
        self.navLayout.addStretch()
        
        self.actionBtnBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Cancel)
        self.navLayout.addWidget(self.actionBtnBox)
        
        self.startBtn = QtWidgets.QPushButton("Next")
        self.navLayout.addWidget(self.startBtn)
        
        self.stopBtn = QtWidgets.QPushButton("Stop")
        self.navLayout.addWidget(self.stopBtn)
        
        self.verticalLayoutMain.addLayout(self.navLayout)

        self.retranslateUi(Dialog)
        self.actionBtnBox.rejected.connect(Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Upload Riverscapes Project"))
