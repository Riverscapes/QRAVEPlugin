from PyQt5 import QtCore, QtGui, QtWidgets
from qgis.gui import QgsFileWidget

class Ui_ProjectDownloadDialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("ProjectDownloadDialog")
        Dialog.resize(600, 500)
        self.verticalLayout = QtWidgets.QVBoxLayout(Dialog)
        
        self.stackedWidget = QtWidgets.QStackedWidget(Dialog)
        
        # --- Step 1: Project Selection ---
        self.step1 = QtWidgets.QWidget()
        self.layout1 = QtWidgets.QVBoxLayout(self.step1)
        self.lblStep1 = QtWidgets.QLabel("Step 1: Select a project to download")
        font = QtGui.QFont()
        font.setBold(True)
        self.lblStep1.setFont(font)
        self.layout1.addWidget(self.lblStep1)
        
        self.lblInstructions = QtWidgets.QLabel("Find a project on the <a href='https://data.riverscapes.net'>Riverscapes Data Exchange</a>. You can copy and paste the Project ID (UUID) or the URL of the project page into the box below.")
        self.lblInstructions.setOpenExternalLinks(True)
        self.lblInstructions.setWordWrap(True)
        self.layout1.addWidget(self.lblInstructions)
        
        self.lblProjectInput = QtWidgets.QLabel("Enter Project ID or URL:")
        self.layout1.addWidget(self.lblProjectInput)
        
        self.txtProjectInput = QtWidgets.QLineEdit()
        self.txtProjectInput.setPlaceholderText("e.g. ac104f27-93b7-4e47-b279-7a7dad8ccf1d")
        self.layout1.addWidget(self.txtProjectInput)
        
        self.btnVerifyProject = QtWidgets.QPushButton("Verify Project")
        self.layout1.addWidget(self.btnVerifyProject)
        
        # Styled Project Details area
        self.frameProjectDetails = QtWidgets.QFrame()
        self.frameProjectDetails.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frameProjectDetails.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
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
        self.lblProjectDetails.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        self.lblProjectDetails.setOpenExternalLinks(True)
        self.layoutProjectDetails.addWidget(self.lblProjectDetails)
        
        self.layout1.addWidget(self.frameProjectDetails)
        self.frameProjectDetails.hide()
        
        self.layout1.addStretch()
        self.stackedWidget.addWidget(self.step1)
        
        # --- Step 2: Location ---
        self.step2 = QtWidgets.QWidget()
        self.layout2 = QtWidgets.QVBoxLayout(self.step2)
        self.lblStep2 = QtWidgets.QLabel("Step 2: Select where to download")
        self.lblStep2.setFont(font)
        self.layout2.addWidget(self.lblStep2)
        
        self.lblParentFolder = QtWidgets.QLabel("Parent Folder:")
        self.layout2.addWidget(self.lblParentFolder)
        
        self.fileWidget = QgsFileWidget()
        self.fileWidget.setStorageMode(QgsFileWidget.GetDirectory)
        self.layout2.addWidget(self.fileWidget)
        
        self.lblFolderName = QtWidgets.QLabel("Folder Name:")
        self.layout2.addWidget(self.lblFolderName)
        
        self.txtFolderName = QtWidgets.QLineEdit()
        self.layout2.addWidget(self.txtFolderName)
        
        self.lblFolderStatus = QtWidgets.QLabel("")
        self.lblFolderStatus.setStyleSheet("color: red;")
        self.layout2.addWidget(self.lblFolderStatus)
        
        self.layout2.addStretch()
        self.stackedWidget.addWidget(self.step2)
        
        # --- Step 3: File Selection ---
        self.step3 = QtWidgets.QWidget()
        self.layout3 = QtWidgets.QVBoxLayout(self.step3)
        self.lblStep3 = QtWidgets.QLabel("Step 3: Choose files to download")
        self.lblStep3.setFont(font)
        self.layout3.addWidget(self.lblStep3)

        self.lblStep3Instructions = QtWidgets.QLabel("You don't need to download every file in a project. Only select the files you need.")
        self.lblStep3Instructions.setOpenExternalLinks(True)
        self.lblStep3Instructions.setWordWrap(True)
        self.layout3.addWidget(self.lblStep3Instructions)        
        
        self.selectionLayout = QtWidgets.QHBoxLayout()
        self.btnSelectAll = QtWidgets.QPushButton("Select All")
        self.btnDeselectAll = QtWidgets.QPushButton("Deselect All")
        self.selectionLayout.addWidget(self.btnSelectAll)
        self.selectionLayout.addWidget(self.btnDeselectAll)
        self.selectionLayout.addStretch()
        self.layout3.addLayout(self.selectionLayout)
        
        self.treeFiles = QtWidgets.QTreeWidget()
        self.treeFiles.setHeaderLabels(["File Path", "Size"])
        self.layout3.addWidget(self.treeFiles)
        
        self.stackedWidget.addWidget(self.step3)
        
        # --- Step 4: Download ---
        self.step4 = QtWidgets.QWidget()
        self.layout4 = QtWidgets.QVBoxLayout(self.step4)
        self.lblStep4 = QtWidgets.QLabel("Step 4: Downloading...")
        self.lblStep4.setFont(font)
        self.layout4.addWidget(self.lblStep4)
        
        self.progressBar = QtWidgets.QProgressBar()
        self.layout4.addWidget(self.progressBar)
        
        self.lblStatus = QtWidgets.QLabel("Initializing...")
        self.layout4.addWidget(self.lblStatus)
        
        self.lblProgressDetails = QtWidgets.QLabel("")
        self.layout4.addWidget(self.lblProgressDetails)
        
        self.layout4.addStretch()
        self.stackedWidget.addWidget(self.step4)
        
        self.verticalLayout.addWidget(self.stackedWidget)
        
        # --- Navigation Buttons ---
        self.navLayout = QtWidgets.QHBoxLayout()
        self.btnBack = QtWidgets.QPushButton("Back")
        self.btnNext = QtWidgets.QPushButton("Next")
        self.btnHelp = QtWidgets.QPushButton("Help")
        self.btnCancel = QtWidgets.QPushButton("Cancel")
        self.navLayout.addWidget(self.btnHelp)
        self.navLayout.addWidget(self.btnBack)
        self.navLayout.addStretch()
        self.navLayout.addWidget(self.btnNext)
        self.navLayout.addWidget(self.btnCancel)
        self.verticalLayout.addLayout(self.navLayout)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Download Riverscapes Project"))
