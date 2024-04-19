import os
import json
import lxml.etree
import datetime
from typing import Tuple, Dict

from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox, QButtonGroup, QMessageBox
from qgis.PyQt.QtGui import QStandardItemModel, QStandardItem, QDesktopServices
from qgis.PyQt.QtCore import pyqtSignal, pyqtSlot, Qt, QUrl, QTimer
from qgis.PyQt.QtWidgets import QErrorMessage
from qgis.core import Qgis, QgsMessageLog

from .classes.data_exchange.DataExchangeAPI import DataExchangeAPI, DEProfile, DEProject, DEValidation, OwnerInputTuple, UploadFileList, UploadFile
from .classes.GraphQLAPI import RunGQLQueryTask, RefreshTokenTask
from .classes.settings import CONSTANTS, Settings
from .classes.project import Project
from .classes.util import error_level_to_str
from .classes.data_exchange.uploader import UploadQueue, UploadMultiPartFileTask
# DIALOG_CLASS, _ = uic.loadUiType(os.path.join(
#     os.path.dirname(__file__), 'ui', 'options_dialog.ui'))
from .ui.project_upload_dialog import Ui_Dialog


# BASE is the name we want to use inside the settings keys
MESSAGE_CATEGORY = CONSTANTS['logCategory']
LOG_FILE = 'RiverscapesViewer-Upload.log'

# Here are the states we're going to pass through


class ProjectUploadDialogStateFlow:
    INITIALIZING = 'INITIALIZING'
    LOGGING_IN = 'LOGGING_IN'
    FETCHING_CONTEXT = 'FETCHING_CONTEXT'
    USER_ACTION = 'USER_ACTION'
    VALIDATING = 'VALIDATING'
    REQUESTING_UPLOAD = 'REQUESTING_UPLOAD'
    UPLOADING = 'UPLOADING'
    WAITING_FOR_COMPLETION = 'WAITING_FOR_COMPLETION'
    COMPLETED = 'COMPLETED'
    ERROR = 'ERROR'
    NO_ACTION = 'NO_ACTION'

# Once we click the start upload button there is going to be a chain of callbacks:

# When the form launches:
# =================================
#           handle_login -->
#           handle_profile_change -->
#           handle_existing_project

# Workflow When he user clicks start:
# =================================
#           handle_start_click --> self.dataExchangeAPI.validate_project
#           handle_project_validation --> self.dataExchangeAPI.request_upload_project
#           handle_request_upload_project --> self.dataExchangeAPI.request_upload_project_files_url
#           handle_request_upload_project_files_url -->
#           handle_upload_start --> upload_progress -->
#           handle_uploads_complete --> self.dataExchangeAPI.finalize_project_upload -->
#           handle_wait_for_upload_completion --> self.dataExchangeAPI.check_upload --> self.dataExchangeAPI.download_file) -->
#           handle_all_done


class ProjectUploadDialogError():
    def __init__(self, summary: str, detail: str) -> None:
        self.summary = summary
        self.detail = detail


class ProjectUploadDialog(QDialog, Ui_Dialog):

    closingPlugin = pyqtSignal()

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
        self.warehouse_id = None  # This is the existing project ID from the XML file (if there is one)
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
        self.queue = UploadQueue(log_callback=self.upload_log)
        self.local_ops = {
            UploadFile.FileOp.CREATE: 0,
            UploadFile.FileOp.UPDATE: 0,
            UploadFile.FileOp.DELETE: 0
        }
        # This state gets set AFTER The user clicks start
        self.new_project_id: str = None  # this is the returned project id from requestUploadProject. May be the same as warehouse_id
        self.first_upload_check: datetime.datetime = None
        self.last_upload_check: datetime.datetime = None
        self.progress: int = 0
        self.upload_start_time: datetime.datetime = None
        ########################################################

        # The queue processor signals needs to get hooked into the UI slots
        self.queue.progress_signal.connect(self.upload_progress)
        self.queue.complete_signal.connect(self.handle_uploads_complete)
        self.queue.cancelled_signal.connect(self.handle_uploads_cancelled)

        # Read the warehouse tag from the project XML
        if warehouse_tag is not None:
            self.warehouse_id = warehouse_tag.get('id')[0]
            self.apiUrl = warehouse_tag.get('apiUrl')[0]

        # when clicking self.errorMoreBtn pop open a QErrorMessage dialog
        self.errorMoreBtn.clicked.connect(self.show_error_message)

        self.OrgModel = QStandardItemModel(self.orgSelect)

        # Remove the log file if it exists. All the logging in logs will be wiped when the used clicks start
        if self.upload_log_path is not None and os.path.isfile(self.upload_log_path):
            os.remove(self.upload_log_path)
        self.upload_log('--------------------------------------------------------------------------------', Qgis.Info)
        self.upload_log('Project Upload Form Loaded', Qgis.Info)
        self.upload_log('--------------------------------------------------------------------------------', Qgis.Info)

        self.upload_log('Logging in... (waiting for browser)', Qgis.Info)

        self.dataExchangeAPI = DataExchangeAPI(on_login=self.handle_login)
        self.loading = self.dataExchangeAPI.api.loading

        # Set the initial state of the form
        self.optNewProject.setChecked(True)
        self.optModifyProject.setChecked(False)
        self.viewExistingBtn.clicked.connect(lambda: self.open_web_project(self.existing_project.id))
        self.new_or_update_group = QButtonGroup(self)
        self.new_or_update_group.addButton(self.optNewProject, 1)  # NEW === 1
        self.new_or_update_group.addButton(self.optModifyProject, 2)  # MODIFY === 2
        self.new_or_update_group.buttonToggled.connect(self.handle_new_or_update_change)
        self.new_or_update_group.setExclusive(True)

        # Add a "View Log" button to the QtWidgets.QDialogButtonBox
        self.viewLogsButton = self.actionBtnBox.addButton('View Log', QDialogButtonBox.ActionRole)
        self.viewLogsButton.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self.upload_log_path)))

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
        self.openWebProjectBtn.clicked.connect(lambda: self.open_web_project(self.new_project_id))
        self.progressBar.setValue(0)
        self.progressBar.setMaximum(100)

        # Connect
        self.loginResetBtn.clicked.connect(self.dataExchangeAPI.login)

        self.flow_state = ProjectUploadDialogStateFlow.LOGGING_IN
        self.loginStatusValue.setText('Logging in... (check your browser)')

        self.startBtn.clicked.connect(self.handle_start_click)
        self.stopBtn.clicked.connect(self.handle_stop_click)

        self.projectNameValue.setText(self.project_xml.project.find('Name').text)
        # The text should fill the label with ellipses if it's too long
        project_path = self.project_xml.project_xml_path
        self.projectPathValue.setText(project_path)
        self.projectPathValue.setToolTip(project_path)

        # 1. Files - we need relative paths to the files
        self.upload_digest.fetch_local_files(self.project_xml.project_dir, self.project_xml.project_type)

        self.recalc_state()

    def recalc_state(self):
        """ We have one BIG method to deal with all the state on the form. It gets run whenever we affect the state
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
            self.noDeleteChk.setEnabled(False)
        # Only if the warehouse_id exists AND the project retieval is successful AND the acccess is correct can we enable the modify option
        else:
            self.optModifyProject.setEnabled(allow_user_action)
            self.viewExistingBtn.setEnabled(allow_user_action)
            self.noDeleteChk.setEnabled(allow_user_action and self.optModifyProject.isChecked())

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

        if self.flow_state not in [ProjectUploadDialogStateFlow.UPLOADING]:
            self.progressBar.setValue(0)
            self.progressSubLabel.setText('...')
            self.progressBar.setEnabled(False)
            self.progressSubLabel.setEnabled(False)
        else:
            self.progressBar.setEnabled(True)
            self.progressSubLabel.setEnabled(True)

        # We only show the "View in Data Exchange" button if we're sure the upload has succeeded
        self.openWebProjectBtn.setEnabled(self.flow_state in [ProjectUploadDialogStateFlow.COMPLETED])

        todo_text = ''
        if self.flow_state == ProjectUploadDialogStateFlow.LOGGING_IN:
            todo_text = 'Logging in... (check your browser)'
        elif self.flow_state == ProjectUploadDialogStateFlow.FETCHING_CONTEXT:
            todo_text = 'Fetching user context...'
        elif self.flow_state == ProjectUploadDialogStateFlow.USER_ACTION:
            todo_text = f"Ready: {self.local_ops[UploadFile.FileOp.CREATE]:,} New {self.local_ops[UploadFile.FileOp.UPDATE]:,} Update {self.local_ops[UploadFile.FileOp.DELETE]:,} delete"
        elif self.flow_state == ProjectUploadDialogStateFlow.VALIDATING:
            todo_text = 'Validating project...'
        elif self.flow_state == ProjectUploadDialogStateFlow.REQUESTING_UPLOAD:
            todo_text = 'Requesting upload...'
        elif self.flow_state == ProjectUploadDialogStateFlow.UPLOADING:
            todo_text = 'Uploading...'
        elif self.flow_state == ProjectUploadDialogStateFlow.WAITING_FOR_COMPLETION:
            todo_text = 'Waiting for upload completion...'
        elif self.flow_state == ProjectUploadDialogStateFlow.COMPLETED:
            todo_text = 'Upload complete'
        elif self.flow_state == ProjectUploadDialogStateFlow.NO_ACTION:
            todo_text = 'No differences between local and remote. Nothing to upload'
        self.todoLabel.setText(todo_text)

        # Action buttons at the bottom of the screen
        ########################################################################

        # set the ok button text to "Start"
        self.startBtn.setEnabled(allow_user_action)
        # We swap the start button with the stop button when we're uploading
        self.startBtn.setVisible(self.flow_state not in [ProjectUploadDialogStateFlow.UPLOADING])
        self.stopBtn.setEnabled(self.flow_state in [ProjectUploadDialogStateFlow.UPLOADING])
        self.stopBtn.setVisible(self.flow_state in [ProjectUploadDialogStateFlow.UPLOADING])

        # User cannot cancel the dialog if uploading is happening. They must first stop the upload
        self.actionBtnBox.button(QDialogButtonBox.Cancel).setEnabled(self.flow_state not in [
            ProjectUploadDialogStateFlow.UPLOADING
        ])

        self.viewLogsButton.setEnabled(os.path.isfile(self.upload_log_path))

    def reset_upload_state(self):
        # Make sure the state is clear to behin with
        self.new_project_id = None
        self.first_upload_check = None
        self.last_upload_check = None
        self.progress = 0
        self.upload_start_time = None
        # Reset the queue and the upload digest
        self.queue.reset()
        self.upload_digest.reset()

    def calculate_end_time(self):
        """ Calculate the estimated end time of the upload
        """
        if self.upload_start_time is None:
            return None, ''
        if self.progress == 0:
            return None, ''
        elapsed = datetime.datetime.now() - self.upload_start_time
        total_seconds = elapsed.total_seconds()
        remaining_seconds = (total_seconds / self.progress) * (100 - self.progress)

        days, remaining_seconds = divmod(remaining_seconds, 86400)
        hours, remainder_seconds = divmod(remaining_seconds, 3600)
        minutes, seconds = divmod(remainder_seconds, 60)
        if days > 0:
            duration_str = f" ETA: {int(days)}d {int(hours)}h {int(minutes)}m"
        elif hours > 0:
            duration_str = f" ETA: {int(hours)}h {int(minutes)}m"
        elif minutes > 0:
            duration_str = f" ETA: {int(minutes)}m {int(seconds)}s"
        elif seconds > 0:
            duration_str = f" ETA: {int(seconds)}s"
        else:
            duration_str = ""

        return datetime.datetime.now() + datetime.timedelta(seconds=remaining_seconds), duration_str

    def get_owner_obj(self) -> OwnerInputTuple:
        """ Helper function to get the owner object for the project

        Returns:
            OwnerInputTuple: _description_
        """
        if not self.org_id and not self.profile:
            return None
        if self.org_id is not None:
            owner_obj = OwnerInputTuple(id=self.org_id, type='ORGANIZATION')
        else:
            owner_obj = OwnerInputTuple(id=self.profile.id, type='USER')
        return owner_obj

    def handle_login(self, task: RefreshTokenTask):
        """ Handle the response from the API when logging in
        THis kicks off the process of fetching the user profile

        Args:
            task (RefreshTokenTask): _description_
        """
        if not task.success:
            self.upload_log('Could not log in to the data exchange API', Qgis.Critical, task)
            self.error = ProjectUploadDialogError('Could not log in to the data exchange API', task.error)
        else:
            self.upload_log('  - SUCCESS: Logged in to the data exchange API', Qgis.Info)
            self.upload_log('Fetching User profile...', Qgis.Info)
            self.flow_state = ProjectUploadDialogStateFlow.FETCHING_CONTEXT
            self.loginStatusValue.setText('Fetching Profile...')
            self.profile = None
            self.dataExchangeAPI.get_user_info(self.handle_profile_change)

        self.recalc_state()

    def handle_select_tag(self, item):
        """ Handle the user clicking on a tag. This selects it so we can remove it.

        Args:
            item (_type_): _description_
        """
        if item is not None:
            self.selected_tag = item.text()

    def remove_tag(self):
        """ Remove a tag from the list
        """
        if self.selected_tag is None:
            return
        self.tags = [tag for tag in self.tags if tag != self.selected_tag]
        self.selected_tag = None
        self.recalc_state()

    def add_tag(self):
        """ Add a tag to the list
        """

        tag = self.addTag.text().strip()
        if len(tag) > 0 and tag not in self.tags:
            self.tags.append(tag)
            self.recalc_state()

    def handle_profile_change(self, task: RunGQLQueryTask, profile: DEProfile):
        """ When the 

        Args:
            task (RunGQLQueryTask): _description_
            profile (DEProfile): _description_
        """
        if profile is None:
            self.upload_log('Could not fetch user profile', Qgis.Critical, task)
            self.profile = None
            self.error = ProjectUploadDialogError('Could not fetch user profile', task.error)
        else:
            self.upload_log('  - SUCCESS: Fetched user profile', Qgis.Info)
            self.profile = profile
            self.upload_log(f'Logged in as {profile.name} ({profile.id})', Qgis.Info)
            self.loginStatusValue.setText('Logged in as: ' + profile.name + ' (' + profile.id + ')')
            if self.project_xml.warehouse_meta is not None:
                self.upload_log('Found a <Warehouse> tag. Checking project association with the current warehouse', Qgis.Info)
                project_api = self.project_xml.warehouse_meta.get('apiUrl', [None])[0]
                project_id = self.project_xml.warehouse_meta.get('id', [None])[0]

                # Handle Errors. We fail harshly on these because they should be rare (borderline impossible) for
                # non-developers to get into these states
                if project_api is None or len(project_api.strip()) == 0:
                    self.upload_log('ERROR: Missing or invalid "apiUrl" in the <Warehouse> tag', Qgis.Critical)
                    self.error = ProjectUploadDialogError('Warehouse lookup error', 'Missing API URL in the project')
                    self.flow_state = ProjectUploadDialogStateFlow.USER_ACTION
                    self.existingProject = None
                    self.recalc_state()
                    return

                elif project_id is None or len(project_id.strip()) == 0:
                    self.upload_log('ERROR: Missing "id" attribute in the <Warehouse> tag', Qgis.Critical)
                    self.error = ProjectUploadDialogError('Warehouse lookup error', 'Missing ID in the project')
                    self.flow_state = ProjectUploadDialogStateFlow.USER_ACTION
                    self.existingProject = None
                    self.recalc_state()
                    return

                elif project_api != self.dataExchangeAPI.api.uri:
                    err_title = 'The project is not associated with the current warehouse'
                    err_str = f"Project API: {project_api} \nWarehouse API: {self.dataExchangeAPI.api.uri}"
                    self.upload_log(err_title, Qgis.Critical, err_str)
                    self.error = ProjectUploadDialogError(err_title, err_str)
                    self.flow_state = ProjectUploadDialogStateFlow.ERROR
                    self.existingProject = None
                    self.recalc_state()
                    return
            else:
                self.flow_state = ProjectUploadDialogStateFlow.USER_ACTION

        # Repopulate the orgs combo box from the profile object
        self.orgSelect.clear()
        if self.profile is not None and len(self.profile.organizations) > 0:
            first_usable_idx = -1
            count_idx = 0
            self.upload_log('  - Found organizations in the user profile:', Qgis.Info)
            for org in self.profile.organizations:
                item_name = f"{org.name} ({org.myRole.lower().capitalize()})"
                item = QStandardItem(item_name)
                item.setData(org.id)
                self.upload_log(f'    - {item_name}: [{org.myRole}]({org.id})', Qgis.Info)

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
                        self.upload_log(f'  - Setting the previously selected organization: {self.org_id}', Qgis.Info)
                        self.orgSelect.setCurrentIndex(i)
                        org_index_set = True
                        break
            if not org_index_set:
                if first_usable_idx > -1:
                    self.upload_log(f'  - Setting the first usable organization active: {self.orgSelect.itemData(first_usable_idx)}', Qgis.Info)
                    self.orgSelect.setCurrentIndex(first_usable_idx)
        else:
            self.upload_log('  - No organizations found in the user profile.', Qgis.Warning)
            self.orgSelect.addItem('No Organizations', None)

        # If there's no project to look up we can go straight to the user action state
        if self.warehouse_id is None:
            self.upload_log('No existing project found in the warehouse, proceeding to user action', Qgis.Info)
            self.flow_state = ProjectUploadDialogStateFlow.USER_ACTION
        else:
            self.upload_log('Fetching existing project from the warehouse...', Qgis.Info)
            self.existing_project = None
            self.dataExchangeAPI.get_project(self.warehouse_id, self.handle_existing_project)

        self.recalc_state()

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

            self.recalc_state()

    def handle_owner_change(self, button, checked):
        if checked:
            btn_id = self.mine_group.checkedId()
            if btn_id == 1:
                self.org_id = self.orgSelect.currentData()
            else:
                self.org_id = None
        self.recalc_state()

    def handle_existing_project(self, task: RunGQLQueryTask, project: DEProject):
        """ Handle the response from the API when fetching an existing project

        Args:
            task (RunGQLQueryTask): _description_
            project (DEProject): _description_
        """
        if project is None:
            self.upload_log('  - ERROR: Could not fetch existing project', Qgis.Critical, task)
            self.error = ProjectUploadDialogError('Could not fetch existing project', task.error)
            self.existing_project = None
        else:
            self.upload_log('  - SUCCESS: Fetched existing project', Qgis.Info)
            self.existing_project = project
            self.new_project = False

            # Do a little local check to see if the project needs to be uploaded at all
            for file in self.upload_digest.files.values():
                if project.files.get(file.rel_path) is None:
                    self.local_ops[UploadFile.FileOp.CREATE] += 1
                elif project.files[file.rel_path].etag != file.etag:
                    self.local_ops[UploadFile.FileOp.UPDATE] += 1
            # Now find the deletions
            for rel_path, file in project.files.items():
                if self.upload_digest.files.get(rel_path) is None:
                    self.local_ops[UploadFile.FileOp.DELETE] += 1
            total_changes = self.local_ops[UploadFile.FileOp.CREATE] + self.local_ops[UploadFile.FileOp.UPDATE] + self.local_ops[UploadFile.FileOp.DELETE]

            if total_changes == 0:
                self.upload_log('  - No differences between local and remote. Nothing to upload', Qgis.Info)
                self.flow_state = ProjectUploadDialogStateFlow.NO_ACTION
                self.recalc_state()
                return

            self.upload_log(f"Found changes that need: {self.local_ops[UploadFile.FileOp.CREATE]:,} New {self.local_ops[UploadFile.FileOp.UPDATE]:,} Update {self.local_ops[UploadFile.FileOp.DELETE]:,} delete", Qgis.Info)
            self.optModifyProject.setChecked(True)

        self.upload_log('Waiting for user input...' + os.linesep * 3, Qgis.Info)
        self.flow_state = ProjectUploadDialogStateFlow.USER_ACTION
        self.recalc_state()

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

    def upload_log(self, message: str, level: int = Qgis.Info, context_obj=None):
        """ Logging here should go to the QGIS log and to a file we can check later

        Args:
            message (str): _description_
            level (int): _description_
            context_obj (_type_, optional): _description_. Defaults to None.
        """
        self.settings.log(message, level)
        level_name = error_level_to_str(level)
        with open(self.upload_log_path, 'a') as f:
            # Get an iso timestamp to prepend the message
            timestamp = datetime.datetime.now().isoformat()
            f.write(f"[{timestamp}][{level_name}] {message}{os.linesep}")
            if context_obj is not None:
                if isinstance(context_obj, (dict, list)):
                    try:
                        f.write(json.dumps(context_obj, indent=2) + os.linesep)
                    except Exception as e:
                        f.write(f"        Could not serialize context object: {str(e)}{os.linesep}")
                elif isinstance(context_obj, RunGQLQueryTask):
                    context_str = f"Task Context: {context_obj.debug_log()}{os.linesep}"
                    # indent every line in context_str including the first one by 4 spaces
                    context_str = os.linesep.join(['    ' + line for line in context_str.split(os.linesep)])
                    f.write(context_str)
                elif isinstance(context_obj, UploadMultiPartFileTask):
                    context_str = f"UploadFile Context: {context_obj.debug_log()}{os.linesep}"
                    # indent every line in context_str including the first one by 4 spaces
                    context_str = os.linesep.join(['    ' + line for line in context_str.split(os.linesep)])
                    f.write(context_str)
                elif isinstance(context_obj, RefreshTokenTask):
                    context_str = f"Refresh Token Context: {context_obj.debug_log()}{os.linesep}"
                    # indent every line in context_str including the first one by 4 spaces
                    context_str = os.linesep.join(['    ' + line for line in context_str.split(os.linesep)])
                    f.write(context_str)
                else:
                    try:
                        f.write(str(context_obj) + os.linesep)
                    except Exception as e:
                        f.write(f"Could not convert context object to string: {str(e)}{os.linesep}")

    def handle_start_click(self):
        """ The user kicks off the upload process. we give them a dialog to confirm
        and then we start the process
        """

        # Make sure the state is clear to begin with. This is maybe a little overkill but it can't hurt to be safe
        self.reset_upload_state()

        qm = QMessageBox()
        qm.setWindowTitle('Start Upload?')
        qm.setDefaultButton(qm.No)
        text = f"This will upload the project \"{self.project_xml.project.find('Name').text}\" to the Data Exchange API"
        if self.new_project:
            text += ' as a new project.'
        else:
            text += ' as an update to the existing project.'
        qm.setText(text + ' Are you sure?')
        qm.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        # Remove the log file if it exists and create a new one
        self.upload_log('--------------------------------------------------------------------------------', Qgis.Info)
        self.upload_log('User-Initiated project upload starting', Qgis.Info)
        self.upload_log('--------------------------------------------------------------------------------', Qgis.Info)

        response = qm.exec_()
        if response == QMessageBox.Yes:
            # New let's kick off project validation. We need 3 things to do this: 1. The XML, 2. The files, 3. The owner

            with open(self.project_xml.project_xml_path, 'r') as f:
                xml = lxml.etree.parse(self.project_xml.project_xml_path).getroot()
                if self.new_project:
                    # We need to remove the <Warehouse> tag from the XML
                    warehouse_tag = xml.find('Warehouse')
                    if warehouse_tag is not None:
                        xml.remove(warehouse_tag)
                # Now transform back to a string
                xml = lxml.etree.tostring(xml, pretty_print=True).decode('utf-8')
                owner_obj = self.get_owner_obj() if self.new_project else None
                self.upload_log('Validating project using the API validation endpoint...', Qgis.Info)
                self.dataExchangeAPI.validate_project(xml, owner_obj, self.upload_digest, self.handle_project_validation)
        else:
            return

    def handle_stop_click(self):
        self.queue.cancel_all()
        self.flow_state = ProjectUploadDialogStateFlow.USER_ACTION
        self.recalc_state()

    def handle_project_validation(self, task: RunGQLQueryTask, validation_obj: DEValidation):
        """ Before we can upload a project we need to validate it. This saves a lot of time and effort
        When validation succeeds we can request permission to upload the project

        Args:
            task (RunGQLQueryTask): _description_
            validation_obj (DEValidation): _description_
        """
        if validation_obj is None:
            self.error = ProjectUploadDialogError('Could not validate project for an unknown reason', task.error)
            self.upload_log('  - ERROR: Project validation failed to run', Qgis.Critical, task)
            self.flow_state = ProjectUploadDialogStateFlow.ERROR
        else:
            if validation_obj.valid is True:
                # Validation done. Now request upload
                owner_obj = self.get_owner_obj()
                self.upload_log('  - SUCCESS: Validation: Project is valid.', Qgis.Info)
                self.upload_log('Requesting new upload from the API...', Qgis.Info)
                self.dataExchangeAPI.request_upload_project(
                    files=self.upload_digest,
                    tags=self.tags,
                    no_delete=self.noDeleteChk.isEnabled() and self.noDeleteChk.isChecked(),
                    owner_obj=owner_obj if self.new_project else None,
                    project_id=self.warehouse_id if not self.new_project else None,
                    visibility=self.visibilitySelect.currentText(),
                    callback=self.handle_request_upload_project
                )
                self.flow_state = ProjectUploadDialogStateFlow.REQUESTING_UPLOAD
            else:
                self.upload_log('  - ERROR: Project is not valid', Qgis.Critical, task)
                detail_text = [f"[{err.severity}][{err.code}] {err.message}" for err in validation_obj.errors]
                self.error = ProjectUploadDialogError('Project is not valid', detail_text)
                self.flow_state = ProjectUploadDialogStateFlow.ERROR

        self.recalc_state()

    def handle_request_upload_project(self, task: RunGQLQueryTask, upload_obj: Dict[str, any]):
        """ We formally request permission from the API to upload a project.
        When we get the response we can then request URLs for all the files in the project

        Args:
            task (RunGQLQueryTask): _description_
            upload_obj (DEProject): _description_
        """
        if upload_obj is None:
            self.upload_log('  - FAILED: Could not upload project', Qgis.Critical, task)
            self.error = ProjectUploadDialogError('Could not upload project', task.error)
            self.flow_state = ProjectUploadDialogStateFlow.ERROR
        else:
            self.upload_log('  - SUCCESS: Got project upload token', Qgis.Info)
            self.new_project_id = upload_obj['newId']
            self.upload_log(f"  - New Project ID: {self.new_project_id}", Qgis.Info)
            self.upload_log(f'  - NOTE: When completed this project will be available at: {CONSTANTS["warehouseUrl"]}/p/{self.new_project_id}', Qgis.Info)

            changes = 0
            self.upload_log('Summary of files and operations:', Qgis.Info)
            for file in self.upload_digest.files.values():
                if file.op in [UploadFile.FileOp.CREATE, UploadFile.FileOp.UPDATE]:
                    changes += 1
                self.upload_log(f"  - [{file.op}] {file.rel_path} size: {file.size:,} etag: {file.etag}", Qgis.Info)

            if changes == 0:
                self.upload_log('No files to upload. Skipping upload step', Qgis.Info)
                self.flow_state = ProjectUploadDialogStateFlow.NO_ACTION
            else:
                self.upload_log('Requesting upload URLs...', Qgis.Info)
                self.dataExchangeAPI.request_upload_project_files_url(self.upload_digest, self.handle_request_upload_project_files_url)

        self.recalc_state()

    def handle_request_upload_project_files_url(self, task: RunGQLQueryTask, project: DEProject):
        """ After requesting permission to upload a project we can ask for URLS for all project files

        Args:
            task (RunGQLQueryTask): _description_
            project (DEProject): _description_
        """
        if project is None:
            self.upload_log('  - ERROR: Could not get the file upload URLs', Qgis.Critical, task)
            self.error = ProjectUploadDialogError('Could not upload project', task.error)
            self.flow_state = ProjectUploadDialogStateFlow.ERROR
        else:
            self.upload_log('  - SUCCESS: Got the file upload URLs', Qgis.Info)
            self.handle_upload_start()
        self.recalc_state()

    @pyqtSlot(str, int, int, int)
    def upload_progress(self, biggest_file_relpath: str, progress: int, uploaded_bytes: int, total_bytes: int):
        """ Reporting on file uploads

        Args:
            biggest_file (UploadMultiPartFileTask): _description_
            progress (int): _description_
        """
        if progress > 100:
            progress = 100
        elif progress < 0:
            progress = 0

        if self.upload_start_time is None:
            self.upload_start_time = datetime.datetime.now()

        self.progressBar.setValue(progress)
        self.progress = progress

        _end_time, end_time_str = self.calculate_end_time()

        file_str = '...'
        if biggest_file_relpath is not None:
            file_str = "Current File: "
            if len(biggest_file_relpath) > 50:
                # Truncate the file path if it's too long, keeping only the last 50 characters
                file_str += f"...{biggest_file_relpath[:50]}"
            else:
                file_str += biggest_file_relpath

        # This would be too busy for the log files. Just dump it to the console for debug purposes
        print(f"Uploading: {biggest_file_relpath} {progress}%")

        # Print "uploaded_bytes of total_bytes" in a human-friendly way showing megabytes or gigabytes with at most one decimal place
        uploaded_mb = uploaded_bytes / 1024 / 1024
        total_mb = total_bytes / 1024 / 1024
        uploaded_gb = uploaded_mb / 1024
        total_gb = total_mb / 1024

        if uploaded_gb >= 1:
            uploaded_str = f"{uploaded_gb:.1f} GB"
        elif uploaded_mb >= 1:
            uploaded_str = f"{uploaded_mb:.1f} MB"
        else:
            uploaded_str = f"{uploaded_bytes:,} bytes"

        if total_gb >= 1:
            total_str = f"{total_gb:.1f} GB"
        elif total_mb >= 1:
            total_str = f"{total_mb:.1f} MB"
        else:
            total_str = f"{total_bytes:,} bytes"

        self.todoLabel.setText(f"Uploading: {uploaded_str} of {total_str} {end_time_str}")
        self.progressSubLabel.setText(f"Uploading: {biggest_file_relpath}")

    def handle_upload_start(self):
        """ Start the upload process
        This kicks off our asynchronous upload queue process
        After all files are uploaded we will call the finalize endpoint
        """
        self.upload_log('Starting the ACTUAL file upload process...', Qgis.Info)

        for upFile in self.upload_digest.files.values():
            if upFile.op in [UploadFile.FileOp.CREATE, UploadFile.FileOp.UPDATE]:
                abs_path = os.path.join(self.project_xml.project_dir, upFile.rel_path)
                self.queue.enqueue(upFile.rel_path, abs_path, upload_urls=upFile.urls)

        self.flow_state = ProjectUploadDialogStateFlow.UPLOADING
        self.recalc_state()

    @pyqtSlot()
    def handle_uploads_complete(self):
        self.upload_log('Upload Queue Completed. Calling the finalize endpoint...', Qgis.Info)
        self.progressBar.setValue(100)
        self.progressSubLabel.setText('...')

        # If this succeeds we should call the finalize endpoint
        self.dataExchangeAPI.finalize_project_upload(self.upload_digest.token, self.handle_wait_for_upload_completion)
        self.recalc_state()

    @pyqtSlot()
    def handle_uploads_cancelled(self):
        self.upload_log('Upload Queue Cancelled', Qgis.Warning)
        # Reset all state back to the beginning so we can click "start" again if we want
        self.reset_upload_state()

        self.flow_state = ProjectUploadDialogStateFlow.USER_ACTION
        self.recalc_state()

    def handle_finalize(self, task: RunGQLQueryTask, job_status_obj: Dict[str, any]):
        """ This is kind of a non-operation that serves just to print a single log file and kick off the recursive check_upload

        Args:
            task (RunGQLQueryTask): _description_
            job_status_obj (Dict[str, any]): _description_
        """
        if task.error is not None:
            self.upload_log('  - ERROR: Finalize failed', Qgis.Critical, task)
            self.error = ProjectUploadDialogError('Finalize failed', 'The finalize call failed. Check the logs to see the reason')
            self.flow_state = ProjectUploadDialogStateFlow.ERROR
        else:
            self.upload_log('  - SUCCESS: API Finalize complete.', Qgis.Info)
            self.upload_log('Starting process to wait for upload completion...', Qgis.Info)
            self.dataExchangeAPI.check_upload(self.upload_digest.token, self.handle_wait_for_upload_completion)

    def handle_wait_for_upload_completion(self, task: RunGQLQueryTask, job_status_obj: Dict[str, any]):
        """ Handle the response from the API when waiting for the upload to complete
        NOTE: This is a looping callback that will loop for 5 minutes waiting for the upload copier to finalize

        Note that both finalize and check_upload return {'__typename': 'JobStatusObj'} so this should work in both cases.

        Possible Statuses:
            SUCCESS
            FAILED

            UNKNOWN
            READY
            PROCESSING

        Args:
            response (Dict[str, any]): _description_
            start_time (datetime.datetime): _description_
        """
        self.flow_state = ProjectUploadDialogStateFlow.WAITING_FOR_COMPLETION

        if self.first_upload_check is None:
            self.first_upload_check = datetime.datetime.now()

        self.last_upload_check = datetime.datetime.now()
        total_duration_s = (self.last_upload_check - self.first_upload_check).total_seconds()
        status = job_status_obj.get('status', 'UNKNOWN')

        # Uploader Fail case
        if status == 'FAILED':
            self.upload_log('Upload failed: ' + json.dumps(job_status_obj, indent=2) + os.linesep * 3, Qgis.Critical, task)
            self.error = ProjectUploadDialogError('Upload failed', 'The upload failed. Check the logs to see the reason')
            self.flow_state = ProjectUploadDialogStateFlow.ERROR

        # Success case
        elif status == 'SUCCESS':
            self.upload_log(f'Upload succeeded and is now present on the Warehouse at {CONSTANTS["warehouseUrl"]}/p/{self.new_project_id}', Qgis.Info)
            # Downlod the project.rs.xml file back to the local folder
            self.upload_log('Downloading the project.rs.xml file back to the local project folder...', Qgis.Info)
            self.dataExchangeAPI.download_file(self.new_project_id,
                                               'project.rs.xml',
                                               os.path.join(self.project_xml.project_dir, 'project.rs.xml'),
                                               self.handle_all_done
                                               )
        # Timeout case
        elif total_duration_s >= 300:
            # If it failed we need to handle that
            self.upload_log('Upload Timed-Out after 300 seconnds (5min)' + os.linesep * 3, Qgis.Critical, task)
            self.error = ProjectUploadDialogError('Upload failed', 'The upload took too long to complete. It\'s possible the upload failed. Check the logs to see the reason.')
            self.flow_state = ProjectUploadDialogStateFlow.ERROR

        else:
            # Wait 10 seconds and then check again
            self.upload_log(f"Waiting 10 seconds then trying again... Waited so far: {int(total_duration_s):,} seconds", Qgis.Info)
            # Wait 10 seconds and then check again
            QTimer.singleShot(10000, lambda: self.dataExchangeAPI.check_upload(self.upload_digest.token, self.handle_wait_for_upload_completion))

        self.recalc_state()

    def handle_all_done(self, task: RunGQLQueryTask, download_file_obj: Dict[str, any]):
        """After the last callback is complete we report success
        """
        if task.error is not None:
            self.upload_log('  - ERROR: Could not download the project.rs.xml file back to the local project folder' + os.linesep * 3, Qgis.Critical, task)
            self.error = ProjectUploadDialogError('Download failed', 'The download of the project.rs.xml file failed. Check the logs to see the reason')
            self.flow_state = ProjectUploadDialogStateFlow.ERROR
        else:
            self.upload_log('  - SUCCESS: Downloaded the project.rs.xml file back to the local project folder', Qgis.Info)
            self.upload_log('Upload process complete. Shutting down.' + os.linesep * 3, Qgis.Info)
            self.flow_state = ProjectUploadDialogStateFlow.COMPLETED
            self.recalc_state()
