import os
import json
import lxml.etree

from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox, QButtonGroup, QMessageBox
from qgis.PyQt.QtGui import QStandardItemModel, QStandardItem, QDesktopServices
from qgis.PyQt.QtCore import pyqtSignal, pyqtSlot, Qt, QUrl
from qgis.PyQt.QtWidgets import QErrorMessage
from qgis.core import Qgis, QgsMessageLog

from .classes.data_exchange.DataExchangeAPI import DataExchangeAPI, DEProfile, DEProject, DEValidation, OwnerInputTuple, UploadFileList
from .classes.GraphQLAPI import RunGQLQueryTask, RefreshTokenTask
from .classes.settings import CONSTANTS, Settings
from .classes.project import Project
from .classes.util import error_level_to_str

# DIALOG_CLASS, _ = uic.loadUiType(os.path.join(
#     os.path.dirname(__file__), 'ui', 'options_dialog.ui'))
from .ui.project_upload_dialog import Ui_Dialog


# BASE is the name we want to use inside the settings keys
MESSAGE_CATEGORY = CONSTANTS['logCategory']
LOG_FILE = 'RiverscapesViewer-Upload.log'

# Here are the states we're going to pass through


class ProjectUploadDialogStateFlow:
    INITIALIZING = 0
    LOGGING_IN = 1
    FETCHING_CONTEXT = 2
    USER_ACTION = 3
    VALIDATING = 4
    REQUESTING_UPLOAD = 5
    UPLOADING = 6
    WAITING_FOR_COMPLETION = 7
    COMPLETED = 8
    ERROR = 9


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
        self.upload_log_path = os.path.join(project.project_dir, LOG_FILE)
        self.flow_state = ProjectUploadDialogStateFlow.INITIALIZING
        warehouse_tag = self.project_xml.warehouse_meta
        self.settings = Settings()

        # Here are the state variables we depend on
        ########################################################
        self.warehouse_id = None
        self.profile: DEProfile = None
        self.existing_project: DEProject = None
        self.visibility = "PUBLIC"
        self.existingProject = None
        self.new_project = True
        self.org_id = None
        self.tags = []
        self.selected_tag = []
        self.upload_digest = UploadFileList()
        self.api_url = None
        ########################################################

        if warehouse_tag is not None:
            self.warehouse_id = warehouse_tag.get('id')[0]
            self.apiUrl = warehouse_tag.get('apiUrl')[0]

        # when clicking self.errorMoreBtn pop open a QErrorMessage dialog
        self.errorMoreBtn.clicked.connect(self.show_error_message)

        self.OrgModel = QStandardItemModel(self.orgSelect)
        self.dataExchangeAPI = DataExchangeAPI(on_login=self.handle_login)
        self.loading = self.dataExchangeAPI.api.loading

        # This will chain the state change signal from the API to the dialog
        self.dataExchangeAPI.stateChange.connect(self.stateChange.emit)

        # Create a button group
        self.optNewProject.setChecked(True)
        self.optModifyProject.setChecked(False)
        self.viewExistingBtn.clicked.connect(lambda: self.open_web_project(self.existing_project.id))
        self.new_or_update_group = QButtonGroup(self)
        self.new_or_update_group.addButton(self.optNewProject, 1)  # NEW === 1
        self.new_or_update_group.addButton(self.optModifyProject, 2)  # MODIFY === 2
        self.new_or_update_group.buttonToggled.connect(self.handle_new_or_update_change)
        self.new_or_update_group.setExclusive(True)

        self.mine_group = QButtonGroup(self)
        self.mine_group.addButton(self.optOwnerMe, 1)  # ME === 1
        self.mine_group.addButton(self.optOwnerOrg, 2)  # ORG === 2
        self.mine_group.buttonToggled.connect(self.handle_owner_change)

        self.tagList.itemClicked.connect(self.handle_select_tag)
        self.removeTagButton.clicked.connect(self.remove_tag)
        self.addTagButton.clicked.connect(self.add_tag)

        # on changing the org select
        self.orgSelect.currentIndexChanged.connect(self.handle_org_select_change)

        # on clicking the web project upen the existing project in the browser
        self.openWebProjectBtn.clicked.connect(lambda: self.open_web_project(self.existing_project.id))

        # Connect
        self.loginResetBtn.clicked.connect(self.dataExchangeAPI.login)

        self.flow_state = ProjectUploadDialogStateFlow.LOGGING_IN
        self.loginStatusValue.setText('Logging in...')

        self.startBtn.clicked.connect(self.handle_start_click)

        self.projectNameValue.setText(self.project_xml.project.find('Name').text)
        # The text should fill the label with ellipses if it's too long
        project_path = self.project_xml.project_xml_path
        self.projectPathValue.setText(project_path)
        self.projectPathValue.setToolTip(project_path)

        self.stateChange.connect(self.state_change_handler)
        self.stateChange.emit()

    def get_owner_obj(self) -> OwnerInputTuple:
        if not self.org_id and not self.profile:
            return None
        if self.org_id is not None:
            owner_obj = OwnerInputTuple(id=self.org_id, type='ORGANIZATION')
        else:
            owner_obj = OwnerInputTuple(id=self.profile.id, type='USER')
        return owner_obj

    def handle_login(self, task: RefreshTokenTask):
        print('handle_login')
        if not task.success:
            self.error = ProjectUploadDialogError('Could not log in to the data exchange API', task.error)
        else:
            self.flow_state = ProjectUploadDialogStateFlow.FETCHING_CONTEXT
            self.loginStatusValue.setText('Logged in. Fetching Profile...')
            self.dataExchangeAPI.get_user_info(self.handle_profile_change)
        self.stateChange.emit()

    def handle_select_tag(self, item):
        if item is not None:
            self.selected_tag = item.text()

    def remove_tag(self):
        if self.selected_tag is None:
            return
        self.tags = [tag for tag in self.tags if tag != self.selected_tag]
        self.selected_tag = None
        self.stateChange.emit()

    def add_tag(self):
        # addTag is a QLineEdit
        tag = self.addTag.text().strip()
        if len(tag) > 0 and tag not in self.tags:
            self.tags.append(tag)
            self.stateChange.emit()

    def handle_profile_change(self, task: RunGQLQueryTask, profile: DEProfile):
        if profile is None:
            self.profile = None
            self.error = ProjectUploadDialogError('Could not fetch user profile', task.error)
        else:
            self.profile = profile
            self.loginStatusValue.setText('Logged in as: ' + profile.name + ' (' + profile.id + ')')
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
                    self.error = ProjectUploadDialogError('The project is not associated with the current warehouse', f"Project API: {project_api} \nWarehouse API: {self.dataExchangeAPI.api.uri}")
                    self.flow_state = ProjectUploadDialogStateFlow.USER_ACTION
                    self.existingProject = None
            else:
                self.flow_state = ProjectUploadDialogStateFlow.USER_ACTION

        # Repopulate the orgs combo box from the profile object
        self.orgSelect.clear()
        if self.profile is not None and len(self.profile.organizations) > 0:
            first_usable_idx = -1
            count_idx = 0
            for org in self.profile.organizations:
                item_name = f"{org.name} ({org.myRole.lower().capitalize()})"
                item = QStandardItem(item_name)
                item.setData(org.id)

                # Disable the item if org.myRole meets your condition
                # cannot be invited to an owner.
                # Valid roles are:  OWNER, ADMIN, CONTRIBUTOR,
                # INVALID ROLES ARE: VIEWER,  NONE
                if org.myRole not in ['OWNER', 'ADMIN', 'CONTRIBUTOR']:
                    if first_usable_idx == -1:
                        first_usable_idx = count_idx
                    item.setFlags(item.flags() & ~Qt.ItemIsEnabled)

                self.OrgModel.appendRow(item)
                count_idx += 1

            self.orgSelect.setModel(self.OrgModel)
            org_index_set = False

            # Make sure we always reset the index to what the user had selected
            # Even when we reload the data
            if self.org_id is not None:
                for i in range(self.orgSelect.count()):
                    org_id = self.orgSelect.itemData(i)
                    if self.orgSelect.itemData(i) == self.org_id:
                        self.orgSelect.setCurrentIndex(i)
                        org_index_set = True
                        break
            if not org_index_set:
                if first_usable_idx > -1:
                    self.orgSelect.setCurrentIndex(first_usable_idx)
        else:
            self.orgSelect.addItem('No Organizations', None)

        # If there's no project to look up we can go straight to the user action state
        if self.warehouse_id is None:
            self.flow_state = ProjectUploadDialogStateFlow.USER_ACTION
        else:
            self.dataExchangeAPI.get_project(self.warehouse_id, self.handle_existing_project)

        self.stateChange.emit()

    def handle_org_select_change(self, index):
        # Get the current item's data
        item_data = self.orgSelect.itemData(index)
        if item_data is not None:
            print(f"Selected organization ID: {item_data}")
            self.org_id = item_data

    def handle_new_or_update_change(self, button, checked):
        if checked:
            btn_id = self.new_or_update_group.checkedId()
            # NEW
            if btn_id == 1:
                self.new_project = True
            # MODIFY
            elif btn_id == 2:
                if self.existing_project is not None:
                    self.tags = self.existing_project.tags
                    # We need to make sure to lock the Project ownership since that can't be changed
                    # When we're updating a project
                    self.new_project = False
                    if self.existing_project.ownedBy['__typename'].lower() == 'organization':
                        self.optOwnerOrg.setChecked(True)
                        self.org_id = self.existing_project.ownedBy['id']
                        # find the index of the org in the org select and select it
                        for i in range(self.orgSelect.count()):
                            item = self.OrgModel.item(i)
                            item_data = item.data()
                            if item_data == self.org_id:
                                self.orgSelect.setCurrentIndex(i)
                                break
                    else:
                        self.optOwnerMe.setChecked(True)
                        self.org_id = None

                    # Now handle the visibility
                    # find the option that corresponds to the existing project visibility
                    # We find the item that has the same name
                    # as the existing project visibility
                    found_item = self.visibilitySelect.findText(self.existing_project.visibility)
                    if found_item > -1:
                        self.visibilitySelect.setCurrentIndex(found_item)
                    else:
                        # If we can't find the visibility we're going to set it to public
                        self.visibilitySelect.setCurrentIndex(0)

                else:
                    # If there's no project set it back to new
                    self.optNewProject.setChecked(True)
                    self.new_project = True

            self.stateChange.emit()

    def handle_owner_change(self, button, checked):
        if checked:
            btn_id = self.mine_group.checkedId()
            if btn_id == 1:
                self.org_id = self.orgSelect.currentData()
            else:
                self.org_id = None
        self.stateChange.emit()

    def handle_existing_project(self, task: RunGQLQueryTask, project: DEProject):
        """ Handle the response from the API when fetching an existing project

        Args:
            task (RunGQLQueryTask): _description_
            project (DEProject): _description_
        """
        if project is None:
            if self.warehouse_id is not None:
                self.error = ProjectUploadDialogError('Could not fetch existing project', task.error)
            self.existing_project = None
        else:
            self.existing_project = project

        self.flow_state = ProjectUploadDialogStateFlow.USER_ACTION
        self.stateChange.emit()

    def show_error_message(self):
        if self.error is None:
            return
        emsg = QErrorMessage(self)
        emsg.setMinimumWidth(600)
        emsg.setMinimumHeight(600)
        emsg.setWindowTitle('Error Details')

        emsg.showMessage(f"""<h2>ERROR: {self.error.summary}</h2>
                            <pre><code>{self.error.detail}</code></pre>""")

    def open_web_project(self, id: str):
        if id is not None:
            url = CONSTANTS['warehouseUrl'] + '/p/' + id
            QDesktopServices.openUrl(QUrl(url))

    @pyqtSlot()
    def state_change_handler(self):
        """ Control the state of the controls in the dialog
        """
        self.loading = self.dataExchangeAPI.api.loading

        allow_user_action = not self.loading and self.flow_state in [ProjectUploadDialogStateFlow.USER_ACTION]

        can_update_project = self.warehouse_id is not None \
            and self.existing_project is not None \
            and self.existing_project.permissions.get('update', False) is True

        # Top of the form
        ########################################################################
        self.loginResetBtn.setVisible(allow_user_action)

        # New Or Update Choice
        ########################################################################
        self.newOrUpdateLayout.setEnabled(allow_user_action)
        # If the self.warehouse_id is not set then we're going to disable the "new" option
        if not can_update_project:
            if self.optModifyProject.isChecked():
                self.optNewProject.setChecked(True)
            self.optModifyProject.setEnabled(False)
            self.viewExistingBtn.setEnabled(False)
            self.selectUpdate = False
        # Only if the warehouse_id exists AND the project retieval is successful AND the acccess is correct can we enable the modify option
        else:
            self.optModifyProject.setEnabled(allow_user_action)
            self.viewExistingBtn.setEnabled(allow_user_action)

        # Project Ownership
        ########################################################################
        # Set things enabled at the group level to save time
        # If the modify option is set then we lock this whole thing down
        self.ownershipGroup.setEnabled(allow_user_action and self.new_project)

        # The org select is only enabled if the project has previously been uploaded (and has a warehouse id)
        # AND if the user has selected ""
        self.orgSelect.setEnabled(self.optOwnerOrg.isChecked() and self.profile is not None and len(self.profile.organizations) > 0)

        # visibility
        ########################################################################
        self.visibilityGroup.setEnabled(allow_user_action and self.new_project is True)

        # Tags
        ########################################################################
        self.tagGroup.setEnabled(allow_user_action)
        self.tagList.clear()
        for tag in self.tags:
            self.tagList.addItem(tag)

        # Error Control
        ########################################################################
        self._handle_error_state()

        # Upload Progress and summary
        ########################################################################
        self.progressBar.setEnabled(self.flow_state in [ProjectUploadDialogStateFlow.UPLOADING])
        self.progressBar.setValue(0)
        self.progressSubLabel.setEnabled(self.flow_state in [ProjectUploadDialogStateFlow.UPLOADING])
        self.progressSubLabel.setText('...')

        self.openWebProjectBtn.setEnabled(self.flow_state in [ProjectUploadDialogStateFlow.COMPLETED])

        # Action buttons at the bottom of the screen
        ########################################################################

        # set the ok button text to "Start"
        self.startBtn.setEnabled(allow_user_action)

        self.actionBtnBox.button(QDialogButtonBox.Cancel).setText(self.flow_state == ProjectUploadDialogStateFlow.USER_ACTION and "Cancel" or "Stop")

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

    def upload_log(self, message: str, level: int, context_obj=None):
        """ Logging here should go to the QGIS log and to a file we can check later

        Args:
            message (str): _description_
            level (int): _description_
            context_obj (_type_, optional): _description_. Defaults to None.
        """
        self.settings.log(message, level)
        level_name = error_level_to_str(level)
        with open(self.upload_log_path, 'a') as f:
            f.write(f"[{level_name}] {message}{os.linesep}")
            if context_obj is not None:
                if isinstance(context_obj, (dict, list)):
                    try:
                        f.write(json.dumps(context_obj, indent=2) + os.linesep)
                    except Exception as e:
                        f.write(f"Could not serialize context object: {str(e)}{os.linesep}")
                elif isinstance(context_obj, RunGQLQueryTask):
                    f.write(f"Task: {context_obj.debug_log()}{os.linesep}")
                else:
                    try:
                        f.write(str(context_obj) + os.linesep)
                    except Exception as e:
                        f.write(f"Could not convert context object to string: {str(e)}{os.linesep}")

    def handle_start_click(self):
        # First pop open a confirmation dialog to make sure this is something we want to do
        # Then we can start the upload process
        qm = QMessageBox()
        qm.setWindowTitle('Start Upload?')
        qm.setDefaultButton(qm.No)
        text = f"This will upload the project {self.project_xml.project.find('Name').text} to the Data Exchange API"
        if self.new_project:
            text += ' as a new project.'
        else:
            text += ' as an update to the existing project.'
        qm.setText(text + ' Are you sure?')
        qm.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        if self.upload_log_path is not None and os.path.isfile(self.upload_log_path):
            os.remove(self.upload_log_path)

        response = qm.exec_()
        if response == QMessageBox.Yes:
            # New let's kick off project validation. We need 3 things to do this: 1. The XML, 2. The files, 3. The owner

            # 1. Files - we need relative paths to the files
            self.upload_digest = UploadFileList()
            self.upload_digest.fetch_local_files(self.project_xml.project_dir, self.project_xml.project_type)

            with open(self.project_xml.project_xml_path, 'r') as f:
                xml = lxml.etree.parse(self.project_xml.project_xml_path).getroot()
                if self.new_project:
                    # We need to remove the <Warehouse> tag from the XML
                    warehouse_tag = xml.find('Warehouse')
                    if warehouse_tag is not None:
                        xml.remove(warehouse_tag)
                # Now transform back to a string
                xml = lxml.etree.tostring(xml, pretty_print=True).decode('utf-8')
                owner_obj = self.get_owner_obj()
                self.dataExchangeAPI.validate_project(xml, owner_obj, self.upload_digest, self.handle_project_validation)
        else:
            return

    def handle_project_validation(self, task: RunGQLQueryTask, validation_obj: DEValidation):
        if validation_obj is None:
            self.error = ProjectUploadDialogError('Could not validate project for an unknown reason', task.error)
            self.upload_log('Project validation failed to run', Qgis.Critical, task)
            self.flow_state = ProjectUploadDialogStateFlow.ERROR
        else:
            if validation_obj.valid is True:
                # Validation done. Now request upload
                owner_obj = self.get_owner_obj()
                self.upload_log('Project is valid.', Qgis.Info)
                self.upload_log('Requesting upload...', Qgis.Info)
                self.dataExchangeAPI.request_upload_project(
                    files=self.upload_digest,
                    tags=self.tags,
                    owner_obj=owner_obj,
                    visibility=self.visibilitySelect.currentText(),
                    callback=self.handle_request_upload_project
                )
                self.flow_state = ProjectUploadDialogStateFlow.REQUESTING_UPLOAD
            else:
                self.upload_log('Project is not valid', Qgis.Critical, task)
                detail_text = [f"[{err.severity}][{err.code}] {err.message}" for err in validation_obj.errors]
                self.error = ProjectUploadDialogError('Project is not valid', detail_text)
                self.flow_state = ProjectUploadDialogStateFlow.ERROR

        self.stateChange.emit()

    def handle_request_upload_project(self, task: RunGQLQueryTask, upload_obj: DEProject):
        if upload_obj is None:
            self.upload_log('Could not upload project', Qgis.Critical, task)
            self.error = ProjectUploadDialogError('Could not upload project', task.error)
            self.flow_state = ProjectUploadDialogStateFlow.ERROR
        else:
            self.upload_log('Got project upload token', Qgis.Info)
            self.dataExchangeAPI.request_upload_project_files_url(self.upload_digest, self.handle_request_upload_project_files_url)

        self.stateChange.emit()

    def handle_request_upload_project_files_url(self, task: RunGQLQueryTask, project: DEProject):
        if project is None:
            self.upload_log('Could not get the file upload URLs', Qgis.Critical, task)
            self.error = ProjectUploadDialogError('Could not upload project', task.error)
            self.flow_state = ProjectUploadDialogStateFlow.ERROR
        else:
            self.upload_log('Got the file upload URLs', Qgis.Info)
            self.handle_upload_start()
        self.stateChange.emit()

    def handle_upload_start(self):
        self.upload_log('Starting upload...', Qgis.Info)
        self.flow_state = ProjectUploadDialogStateFlow.UPLOADING
        self.stateChange.emit()
