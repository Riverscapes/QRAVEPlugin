import json
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox, QButtonGroup
from qgis.PyQt.QtGui import QStandardItemModel, QStandardItem
from qgis.PyQt.QtCore import pyqtSignal, pyqtSlot, Qt
from qgis.PyQt.QtWidgets import QErrorMessage
from qgis.core import Qgis, QgsMessageLog

from .classes.data_exchange.DataExchangeAPI import DataExchangeAPI, DEProfile, DEProject, OwnerInputTuple
from .classes.GraphQLAPI import RunGQLQueryTask, RefreshTokenTask
from .classes.settings import CONSTANTS, Settings
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
        self.setupUi(self)
        self.project_xml = project
        self.flow_state = ProjectUploadDialogStateFlow.INITIALIZING
        warehouse_tag = self.project_xml.warehouse_meta
        self.settings = Settings()

        # when clicking self.errorMoreBtn pop open a QErrorMessage dialog
        self.errorMoreBtn.clicked.connect(self.show_error_message)

        self.OrgModel = QStandardItemModel(self.orgSelect)

        self.dataExchangeAPI = DataExchangeAPI(on_login=self.handle_login)
        self.loading = self.dataExchangeAPI.api.loading

        # This will chain the state change signal from the API to the dialog
        self.dataExchangeAPI.stateChange.connect(self.stateChange.emit)

        # Create a button group
        self.new_or_update_group = QButtonGroup(self)
        self.new_or_update_group.addButton(self.optModifyProject, 1)
        self.new_or_update_group.addButton(self.optNewProject, 2)
        self.new_or_update_group.buttonToggled.connect(self.handle_new_or_update_change)

        self.mine_group = QButtonGroup(self)
        self.mine_group.addButton(self.optOwnerMe, 1)
        self.mine_group.addButton(self.optOwnerOrg, 2)
        self.mine_group.buttonToggled.connect(self.handle_owner_change)

        # Connect
        self.loginResetBtn.clicked.connect(self.dataExchangeAPI.login)

        self.flow_state = ProjectUploadDialogStateFlow.LOGGING_IN
        self.loginStatusValue.setText('Logging in...')

        if warehouse_tag is not None:
            self.warehouse_id = warehouse_tag.get('id')
            self.apiUrl = warehouse_tag.get('apiUrl')

        # Here are the state variables we depend on
        ########################################################
        self.profile = None
        self.existingProject = None
        self.new_project = True
        self.org_id = None
        self.tags = []
        ########################################################

        self.projectNameValue.setText(self.project_xml.project.find('Name').text)
        # The text should fill the label with ellipses if it's too long
        project_path = self.project_xml.project_xml_path
        self.projectPathValue.setText(project_path)
        self.projectPathValue.setToolTip(project_path)

        self.stateChange.connect(self.state_change_handler)
        self.stateChange.emit()

    def handle_login(self, task: RefreshTokenTask):
        print('handle_login')
        if not task.success:
            self.error = ProjectUploadDialogError('Could not log in to the data exchange API', task.error)
        else:
            self.flow_state = ProjectUploadDialogStateFlow.FETCHING_PROFILE
            self.loginStatusValue.setText('Logged in. Fetching Profile...')
            self.dataExchangeAPI.get_user_info(self.handle_profile_change)
        self.stateChange.emit()

    def handle_project_validation(self, task: RunGQLQueryTask, validation_obj):
        print('handle_project_validation', json.dumps(validation_obj, indent=2))
        pass
        # if not valid:
        #     self.error = ProjectUploadDialogError(
        #         'The project is not valid', task.error)
        # else:
        #     self.error = None
        # self.stateChange.emit()

    def handle_profile_change(self, task: RunGQLQueryTask, profile: DEProfile):
        if profile is None:
            self.profile = None
            self.error = ProjectUploadDialogError(
                'Could not fetch user profile', task.error)
        else:
            self.profile = profile
            self.loginStatusValue.setText(
                'Logged in as: ' + profile.name + ' (' + profile.id + ')')
            if self.project_xml.warehouse_meta is not None:
                project_api = self.project_xml.warehouse_meta.get('apiUrl', [None])[0]
                project_id = self.project_xml.warehouse_meta.get('id', [None])[0]
                # Handle Errors. these will all still allow you to upload as a new project
                if project_api is None or len(project_api.strip()) == 0:
                    self.error = ProjectUploadDialogError('The project is not associated with the current warehouse', 'Missing API URL in the project')
                    self.flow_state = ProjectUploadDialogStateFlow.USER_ACTION
                    self.existingProject = None

                elif project_id is None or len(project_id.strip()) == 0:
                    self.error = ProjectUploadDialogError('The project is not associated with the current warehouse', 'Missing ID in the project')
                    self.flow_state = ProjectUploadDialogStateFlow.USER_ACTION
                    self.existingProject = None

                elif project_api != self.dataExchangeAPI.api.uri:
                    self.error = ProjectUploadDialogError('The pr oject is not associated with the current warehouse', f"Project API: {project_api} \nWarehouse API: {self.dataExchangeAPI.api.uri}")
                    self.flow_state = ProjectUploadDialogStateFlow.USER_ACTION
                    self.existingProject = None

                else:
                    self.flow_state = ProjectUploadDialogStateFlow.FETCHING_EXISTING_PROJECT
                    self.dataExchangeAPI.get_project(project_id, self.handle_existing_project)
            else:
                self.flow_state = ProjectUploadDialogStateFlow.USER_ACTION

        # Repopulate the orgs combo box from the profile object
        self.orgSelect.clear()
        if self.profile is not None and len(self.profile.organizations) > 0:
            for org in self.profile.organizations:
                item_name = f"{org.name} ({org.myRole.lower().capitalize()})"
                item = QStandardItem(item_name)
                item.setData(org.id)

                # Disable the item if org.myRole meets your condition
                # cannot be invited to an owner.
                # Valid roles are:  OWNER, ADMIN, CONTRIBUTOR,
                # INVALID ROLES ARE: VIEWER,  NONE
                if org.myRole in ['OWNER', 'ADMIN', 'CONTRIBUTOR']:
                    item.setFlags(item.flags() & ~Qt.ItemIsEnabled)

                self.OrgModel.appendRow(item)

            self.orgSelect.setModel(self.OrgModel)
            org_index_set = False
            # Make sure we always reset the index to what the user had selected
            # Even when we reload the data
            if self.org_id is not None:
                for i in range(self.orgSelect.count()):
                    if self.orgSelect.itemData(i) == self.org_id:
                        self.orgSelect.setCurrentIndex(i)
                        org_index_set = True
                        break
            if not org_index_set:
                self.orgSelect.setCurrentIndex(0)
        else:
            self.orgSelect.addItem('No Organizations', None)

        self.stateChange.emit()

    def handle_org_select_change(self, index):
        # Get the current item's data
        item_data = self.orgSelect.itemData(index)
        if item_data is not None:
            print(f"Selected organization ID: {item_d}")
            self.org_id = item_data

    def handle_new_or_update_change(self, button, checked):
        if checked:
            btn_id = self.new_or_update_group.checkedId()
            if btn_id == 1:
                self.new_project = True
            else:
                self.new_project = False
        self.stateChange.emit()

    def handle_owner_change(self, button, checked):
        if checked:
            btn_id = self.new_or_update_group.checkedId()
            if btn_id == 1:
                self.org_id = self.orgSelect.currentData()
            else:
                self.org_id = None
        self.stateChange.emit()

    def handle_existing_project(self, task: RunGQLQueryTask, project: DEProject):
        if project is None:
            self.error = ProjectUploadDialogError(
                'Could not fetch existing project', task.error)
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
        self.loading = self.dataExchangeAPI.api.loading

        allow_user_action = not self.loading and self.flow_state in [
            ProjectUploadDialogStateFlow.USER_ACTION]

        # Top of the form
        ########################################################################
        self.loginResetBtn.setVisible(allow_user_action)

        # New Or Update Choice
        ########################################################################
        self.newOrUpdateLayout.setEnabled(allow_user_action)
        # If the self.warehouse_id is not set then we're going to disable the "new" option
        if self.warehouse_id is None:
            if self.optModifyProject.isChecked():
                self.optNewProject.setChecked(True)
            self.optModifyProject.setEnabled(False)
            self.selectUpdate = False
        else:
            self.optModifyProject.setEnabled(True)

        # Project Ownership
        ########################################################################
        # Set things enabled at the group level to save time
        self.ownershipGroup.setEnabled(allow_user_action)

        # The org select is only enabled if the project has previously been uploaded (and has a warehouse id)
        # AND if the user has selected ""
        self.orgSelect.setEnabled(self.optOwnerOrg.isChecked() and self.profile is not None and len(self.profile.organizations) > 0)

        # Access
        ########################################################################
        self.accessGroup.setEnabled(allow_user_action)

        # Tags
        ########################################################################
        self.tagGroup.setEnabled(allow_user_action)

        # Error Control
        ########################################################################
        self._handle_error_state()

        # Upload Progress and summary
        ########################################################################
        self.progressBar.setEnabled(
            self.flow_state in [ProjectUploadDialogStateFlow.UPLOADING])
        self.progressBar.setValue(0)
        self.progressSubLabel.setEnabled(
            self.flow_state in [ProjectUploadDialogStateFlow.UPLOADING])
        self.progressSubLabel.setText('...')

        self.openWebProjectBtn.setEnabled(
            allow_user_action and self.existingProject is not None)

        # Action buttons at the bottom of the screen
        ########################################################################

        # set the ok button text to "Start"
        self.actionBtnBox.button(QDialogButtonBox.Ok).setText("Start")
        self.actionBtnBox.button(
            QDialogButtonBox.Ok).setEnabled(not self.loading)
        self.actionBtnBox.button(QDialogButtonBox.Cancel).setText(
            self.flow_state == ProjectUploadDialogStateFlow.USER_ACTION and "Cancel" or "Stop")
        # Disabled the ok button
        self.actionBtnBox.button(
            QDialogButtonBox.Ok).setEnabled(allow_user_action)

    def _handle_error_state(self):
        if (self.error):
            self.errorLayout.setEnabled(True)

            # Make self.errorSummaryLable red with a red border
            self.errorMoreBtn.setVisible(True)
            self.errorSummaryLable.setText("ERROR: " + self.error.summary)
            self.errorSummaryLable.setStyleSheet("QLabel { color : red; border: 1px solid red; }")

            self.error = ProjectUploadDialogError(
                self.error.summary, self.error.detail)
            QgsMessageLog.logMessage(self.error.summary + str(self.error.detail), MESSAGE_CATEGORY, Qgis.Critical)
        else:
            # Set the whole group disabled
            self.errorLayout.setEnabled(False)

            self.errorMoreBtn.setVisible(False)
            self.errorSummaryLable.setText('')
            self.errorSummaryLable.setStyleSheet("QLabel { color : black; border: 0px; }")
            self.error = None
