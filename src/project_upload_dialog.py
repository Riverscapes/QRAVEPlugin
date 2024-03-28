from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox
from qgis.PyQt.QtCore import pyqtSignal, pyqtSlot
from qgis.PyQt.QtWidgets import QErrorMessage
from qgis.core import Qgis, QgsMessageLog

from .classes.data_exchange.DataExchangeAPI import DataExchangeAPI, DEProfile, DEProject
from .classes.GraphQLAPI import RunGQLQueryTask, RefreshTokenTask
from .classes.settings import CONSTANTS
from .classes.project import Project

# DIALOG_CLASS, _ = uic.loadUiType(os.path.join(
#     os.path.dirname(__file__), 'ui', 'options_dialog.ui'))
from .ui.project_upload_dialog import Ui_Dialog

# Here are the states we're going to pass through

# BASE is the name we want to use inside the settings keys
MESSAGE_CATEGORY = CONSTANTS['logCategory']


class ProjectUploadDialogStateFlow:
    INITIALIZING = 0
    LOGGING_IN = 1
    FETCHING_PROFILE = 2
    FETCHING_EXISTING_PROJECT = 3
    USER_ACTION = 4
    VALIDATING = 5
    UPLOADING = 6
    WAITING_FOR_COMPLETION = 7
    COMPLETED = 8


class ProjectUploadDialogError():
    def __init__(self, summary: str, detail: str) -> None:
        self.summary = summary
        self.detail = detail


class ProjectUploadDialog(QDialog, Ui_Dialog):

    closingPlugin = pyqtSignal()
    stateChange = pyqtSignal()

    def __init__(self, parent=None, project: Project = None):
        """Constructor."""
        QDialog.__init__(self, parent)

        self.error: ProjectUploadDialogError = None
        self.stateChange.connect(self.state_change_handler)
        self.setupUi(self)
        self.project_xml = project
        self.flow_state = ProjectUploadDialogStateFlow.INITIALIZING
        warehouse_tag = self.project_xml.warehouse_meta

        # when clicking self.errorMoreBtn pop open a QErrorMessage dialog
        self.errorMoreBtn.clicked.connect(self.show_error_message)

        self.api = DataExchangeAPI(on_login=self.handle_login)
        self.flow_state = ProjectUploadDialogStateFlow.LOGGING_IN
        self.loginStatusValue.setText('Logging in...')

        if warehouse_tag is not None:
            self.warehouse_id = warehouse_tag.get('id')
            self.apiUrl = warehouse_tag.get('apiUrl')
            # if apiUrl != self.api.api.uri:
            #     self.set_error(f'The project is not associated with the current warehouse ({apiUrl}) vs ({self.api.api.uri})')

        # This is the existing project record from the API
        self.existingProject = None
        self.tags = []

        self.projectNameValue.setText(self.project_xml.project.find('Name').text)
        # The text should fill the label with ellipses if it's too long
        project_path = self.project_xml.project_xml_path
        self.projectPathValue.setText(project_path)
        self.projectPathValue.setToolTip(project_path)

        self.stateChange.emit()

    def handle_login(self, task: RefreshTokenTask):
        if not task.success:
            self.error = ProjectUploadDialogError('Could not log in to the data exchange API', task.error)
        else:
            self.flow_state = ProjectUploadDialogStateFlow.FETCHING_PROFILE
            self.loginStatusValue.setText('Logged in. Fetching Profile...')
            self.api.get_user_info(self.handle_profile_change)
        self.stateChange.emit()

    def handle_profile_change(self, task: RunGQLQueryTask, profile: DEProfile):
        if profile is None:
            self.error = ProjectUploadDialogError('Could not fetch user profile', task.error)
        else:
            self.profile = profile
            self.loginStatusValue.setText('Logged in as: ' + profile.name + ' (' + profile.id + ')')
            if self.project_xml.warehouse_meta is not None:
                project_api = self.project_xml.warehouse_meta.get('apiUrl', [None])[0]
                project_id = self.project_xml.warehouse_meta.get('id', [None])[0]
                if project_api is None or len(project_api.strip()) == 0:
                    self.error = ProjectUploadDialogError('The project is not associated with the current warehouse',
                                                          'Missing API URL in the project')
                    self.flow_state = ProjectUploadDialogStateFlow.USER_ACTION
                    self.existingProject = None
                    
                elif project_id is None or len(project_id.strip()) == 0:
                    self.error = ProjectUploadDialogError('The project is not associated with the current warehouse',
                                                          'Missing ID in the project')
                    self.flow_state = ProjectUploadDialogStateFlow.USER_ACTION                
                    self.existingProject = None

                elif project_api != self.api.api.uri:
                    self.error = ProjectUploadDialogError('The project is not associated with the current warehouse',
                                                          f"Project API: {project_api} \nWarehouse API: {self.api.api.uri}")
                    self.flow_state = ProjectUploadDialogStateFlow.USER_ACTION
                    self.existingProject = None

                else:
                    self.flow_state = ProjectUploadDialogStateFlow.FETCHING_EXISTING_PROJECT
                    self.api.get_project(project_id, self.handle_existing_project)
            else:
                self.flow_state = ProjectUploadDialogStateFlow.USER_ACTION
        self.stateChange.emit()

    def handle_existing_project(self, task: RunGQLQueryTask, project: DEProject):
        if project is None:
            self.error = ProjectUploadDialogError('Could not fetch existing project', task.error)
            self.existingProject = None
        else:
            self.existingProject = project

        # Regardless if the outcome we're going to allow the user to continue
        # Since they can still create a new project
        self.flow_state = ProjectUploadDialogStateFlow.USER_ACTION
        self.stateChange.emit()

    def show_error_message(self):
        if self.error is None:
            return
        emsg = QErrorMessage(self)
        emsg.setMinimumWidth(600)
        emsg.setMinimumHeight(600)
        emsg.setWindowTitle('Error Details')

        emsg.showMessage(f"""
            <h2>ERROR: {self.error.summary}</h2>
            <pre>
                <code>{self.error.detail}</code>
            </pre>
            """)

    @pyqtSlot()
    def state_change_handler(self):
        """ Control the state of the controls in the dialog
        """
        self._handle_error_state()

        allow_user_action = self.flow_state in [ProjectUploadDialogStateFlow.USER_ACTION]
        # QtWidgets.QDialogButtonBox
        # set the ok button text to "Start"
        self.actionBtnBox.button(QDialogButtonBox.Ok).setText("Start")
        self.actionBtnBox.button(QDialogButtonBox.Cancel).setText(self.flow_state == ProjectUploadDialogStateFlow.USER_ACTION and "Cancel" or "Stop")
        # Disabled the ok button
        self.actionBtnBox.button(QDialogButtonBox.Ok).setEnabled(allow_user_action)

        self.openWebProjectBtn.setEnabled(allow_user_action and self.existingProject is not None)

        # If the self.warehouse_id is not set then we're going to disable the "new" option
        if self.warehouse_id is None:
            if self.optModifyProject.isChecked():
                self.optNewProject.setChecked(True)
            self.optModifyProject.setEnabled(False)
            self.selectUpdate = False
        else:
            self.optModifyProject.setEnabled(True)

        # Hide the reset button if we're not initialized
        self.loginBtn.setVisible(False)
        self.loginResetBtn.setVisible(allow_user_action)

        self.progressBar.setEnabled(self.flow_state in [ProjectUploadDialogStateFlow.UPLOADING])
        self.progressBar.setValue(0)
        self.progressSubLabel.setEnabled(self.flow_state in [ProjectUploadDialogStateFlow.UPLOADING])
        self.progressSubLabel.setText('...')

        # Set things enabled at the group level to save time
        self.newOrUpdateLayout.setEnabled(allow_user_action)
        self.ownershipGroup.setEnabled(allow_user_action)
        self.tagGroup.setEnabled(allow_user_action)
        self.accessGroup.setEnabled(allow_user_action)

    def _handle_error_state(self):
        if (self.error):
            self.errorLayout.setEnabled(True)

            # Make self.errorSummaryLable red with a red border
            self.errorMoreBtn.setVisible(True)
            self.errorSummaryLable.setText("ERROR: " + self.error.summary)
            self.errorSummaryLable.setStyleSheet("QLabel { color : red; border: 1px solid red; }")

            self.error = ProjectUploadDialogError(self.error.summary, self.error.detail)
            QgsMessageLog.logMessage(self.error.summary + self.error.detail, MESSAGE_CATEGORY, Qgis.Error)
        else:
            # Set the whole group disabled
            self.errorLayout.setEnabled(False)

            self.errorMoreBtn.setVisible(False)
            self.errorSummaryLable.setText('')
            self.errorSummaryLable.setStyleSheet("QLabel { color : black; border: 0px; }")
            self.error = None
