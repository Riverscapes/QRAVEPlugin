import os
import json
import lxml.etree
import datetime
from typing import Tuple, Dict

from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox, QButtonGroup, QMessageBox
from qgis.PyQt.QtGui import QStandardItemModel, QStandardItem, QDesktopServices, QIcon
from qgis.PyQt.QtCore import pyqtSignal, pyqtSlot, Qt, QUrl, QTimer
from qgis.PyQt.QtWidgets import QErrorMessage
from qgis.core import Qgis, QgsMessageLog

from .classes.data_exchange.DataExchangeAPI import DataExchangeAPI, DEProfile, DEProject, DEValidation, OwnerInputTuple, UploadFileList, UploadFile
from .classes.GraphQLAPI import RunGQLQueryTask, RefreshTokenTask
from .classes.settings import CONSTANTS, Settings
from .classes.project import Project
from .classes.util import error_level_to_str, humane_bytes, get_project_details_html
from .classes.data_exchange.uploader import UploadQueue, UploadMultiPartFileTask
from .ui.project_upload_dialog import Ui_Dialog
from .file_selection_widget import ProjectFileSelectionWidget


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
    COMPLETED = 'COMPLETED'
    ERROR = 'ERROR'
    NO_ACTION = 'NO_ACTION'
    CANCELLED = 'CANCELLED'

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
        self.upload_log('Project Upload Form Loaded', Qgis.Info, is_header=True)

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
        self.loginResetBtn.clicked.connect(self.handle_login_reset)

        self.flow_state = ProjectUploadDialogStateFlow.LOGGING_IN
        self.loginStatusValue.setText('Logging in... (check your browser)')

        # Navigation
        self.startBtn.clicked.connect(self._next_step)
        self.stopBtn.clicked.connect(self.handle_stop_click)
        self.btnBack.clicked.connect(self._prev_step)
        self.btnHelp.clicked.connect(self.showHelp)

        self.projectNameValue.setText(self.project_xml.project.find('Name').text)
        # The text should fill the label with ellipses if it's too long
        project_path = self.project_xml.project_xml_path
        self.projectPathValue.setToolTip(project_path)
        self.projectPathValue.setText(project_path)
        
        self.fileSelection.selectionChanged.connect(self._update_selection_summary)

        # 1. Files - we need relative paths to the files
        self.upload_log('Checking for files to upload...', Qgis.Info)
        self.upload_digest.scan_local_files(self.project_xml.project_dir, self.project_xml.project_type)

        self.recalc_state()

    def showHelp(self):
        help_url = CONSTANTS['webUrl'].rstrip('/') + '/software-help/help-qgis-uploader/'
        QDesktopServices.openUrl(QUrl(help_url))

    def recalc_state(self):
        """ We have one BIG method to deal with all the state on the form. It gets run whenever we affect the state
        """

        self.loading = self.dataExchangeAPI.api.loading
        allow_user_action = not self.loading and self.flow_state in [
            ProjectUploadDialogStateFlow.USER_ACTION,
            ProjectUploadDialogStateFlow.CANCELLED,
            ProjectUploadDialogStateFlow.ERROR,
            ProjectUploadDialogStateFlow.NO_ACTION
        ]

        can_update_project = self.warehouse_id is not None \
            and self.existing_project is not None \
            and self.existing_project.permissions.get('update', False) is True

        # Top of the form
        ########################################################################
        curr = self.stackedWidget.currentIndex()
        is_step1 = (curr == 0)
        
        # Reset button should be visible on Step 1 if we're not currently uploading
        show_reset = is_step1 and self.flow_state != ProjectUploadDialogStateFlow.UPLOADING
        self.loginResetBtn.setVisible(show_reset)
        self.loginResetBtn.setEnabled(allow_user_action or self.flow_state == ProjectUploadDialogStateFlow.LOGGING_IN)

        # New Or Update Choice
        ########################################################################
        self.newOrUpdateLayout.setEnabled(not self.loading and self.flow_state in [
            ProjectUploadDialogStateFlow.USER_ACTION,
            ProjectUploadDialogStateFlow.NO_ACTION
        ])
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
        self.lblUploadComplete.setVisible(self.flow_state == ProjectUploadDialogStateFlow.COMPLETED)

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
        elif self.flow_state == ProjectUploadDialogStateFlow.CANCELLED:
            todo_text = 'Upload Aborted. You can restart the upload.'
        self.todoLabel.setText(todo_text)

        # Navigation
        ########################################################################
        # Navigation
        ########################################################################
        curr = self.stackedWidget.currentIndex()
        self.btnBack.setVisible(curr < 2 or self.flow_state in [ProjectUploadDialogStateFlow.CANCELLED, ProjectUploadDialogStateFlow.ERROR]) # Hide back button during/after upload
        
        # Back button is enabled if we're not on the first page AND either we're in USER_ACTION 
        # or we're in a terminal state like CANCELLED or ERROR
        can_go_back = curr > 0 and (allow_user_action or self.flow_state in [ProjectUploadDialogStateFlow.CANCELLED, ProjectUploadDialogStateFlow.ERROR])
        self.btnBack.setEnabled(can_go_back)
        
        if curr == 0:
            self.startBtn.setText("Next")
            # Only enable "Next" if we're in USER_ACTION state (meaning we're logged in and context fetched)
            self.startBtn.setEnabled(allow_user_action)
        elif curr == 1:
            self.startBtn.setText("Start Upload")
            self.startBtn.setEnabled(allow_user_action)
        elif curr == 2:
            self.startBtn.setVisible(self.flow_state in [ProjectUploadDialogStateFlow.CANCELLED, ProjectUploadDialogStateFlow.ERROR])
            self.startBtn.setEnabled(True)
            self.startBtn.setText("Restart Upload")

        self.viewLogsButton.setEnabled(os.path.isfile(self.upload_log_path))
        self.viewLogsButton.setVisible(curr == 2)
        
        # Disable the "Cancel" button while uploading. The user MUST click STOP first
        cancel_btn = self.actionBtnBox.button(QDialogButtonBox.Cancel)
        if cancel_btn:
            cancel_btn.setEnabled(self.flow_state != ProjectUploadDialogStateFlow.UPLOADING)
            if self.flow_state == ProjectUploadDialogStateFlow.COMPLETED:
                cancel_btn.setText('Ok')
                cancel_btn.setEnabled(True)
            else:
                cancel_btn.setText('Cancel')

        self.stopBtn.setVisible(curr == 2 and self.flow_state == ProjectUploadDialogStateFlow.UPLOADING)
        self.stopBtn.setEnabled(self.flow_state == ProjectUploadDialogStateFlow.UPLOADING)
        
        # Project details card visibility
        show_card = self.existing_project is not None and is_step1
        self.frameProjectDetails.setVisible(show_card)
        if show_card:
            self.lblProjectDetails.setText(get_project_details_html(self.existing_project))

    def reset_upload_state(self):
        # Make sure the state is clear to behin with
        self.new_project_id = None
        self.first_upload_check = None
        self.last_upload_check = None
        self.progress = 0
        self.upload_start_time = None
        # Reset the queue and the upload digest
        self.queue.reset()

    def handle_login_reset(self):
        """ This is the "reset" button at the top fo the form
        """
        self.upload_log('Resetting the upload form...\n\n\n', Qgis.Info)
        # First reset the opload state completely
        self.reset_upload_state()
        # Now log in using the data exchange API
        self.dataExchangeAPI.login()
        # Re-verify the MD5 checksums for all local files
        self.upload_log('Checking for files to upload...', Qgis.Info)
        self.upload_digest.scan_local_files(self.project_xml.project_dir, self.project_xml.project_type)

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
        if self.org_id is not None and self.optOwnerOrg.isChecked():
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
            self.loginStatusValue.setText(profile.name)
            self.loginStatusValue.setToolTip(profile.id)
            if self.project_xml.warehouse_meta is not None:
                self.upload_log('Found a <Warehouse> tag. Checking project association with the current warehouse', Qgis.Info)
                project_api = self.project_xml.warehouse_meta.get('apiUrl', [None])[0]
                project_id = self.project_xml.warehouse_meta.get('id', [None])[0]

                # Handle Errors. We fail harshly on these because they should be rare (borderline impossible) for
                # non-developers to get into these states
                # THis case is: missing apiUrl
                if project_api is None or len(project_api.strip()) == 0:
                    self.upload_log('ERROR: Missing or invalid "apiUrl" in the <Warehouse> tag', Qgis.Critical)
                    self.error = ProjectUploadDialogError('Warehouse lookup error', 'Missing API URL in the project')
                    self.flow_state = ProjectUploadDialogStateFlow.USER_ACTION
                    self.existingProject = None
                    self.recalc_state()
                    return
                # THis case is: missing id which means we cannot look up the project in the warehouse
                elif project_id is None or len(project_id.strip()) == 0:
                    self.upload_log('ERROR: Missing "id" attribute in the <Warehouse> tag', Qgis.Critical)
                    self.error = ProjectUploadDialogError('Warehouse lookup error', 'Missing ID in the project')
                    self.flow_state = ProjectUploadDialogStateFlow.USER_ACTION
                    self.existingProject = None
                    self.recalc_state()
                    return
                # This case is the apiUrl does not match the current warehouse API URL
                elif project_api != self.dataExchangeAPI.api.uri:
                    err_title = 'The project is not associated with the current warehouse'
                    err_str = f"Project API: {project_api} \nWarehouse API: {self.dataExchangeAPI.api.uri}"
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
                item.setData(org.id, Qt.UserRole)
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
                    if self.OrgModel.item(i).data(Qt.UserRole) == self.org_id:
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
        """ Handler for the organization select change

        Args:
            index (_type_): _description_
        """
        # Get the current item's data
        if index > -1:
            item_data = self.OrgModel.item(index).data(Qt.UserRole)
            if item_data is not None:
                print(f"Selected organization ID: {item_data}")
                self.org_id = item_data

    def recalc_local_ops(self) -> int:
        """_summary_
        """
        self.local_ops = {
            UploadFile.FileOp.CREATE: 0,
            UploadFile.FileOp.UPDATE: 0,
            UploadFile.FileOp.DELETE: 0
        }
        total_changes = 0

        self.upload_log('Checking for differences between local and remote...', Qgis.Info, is_header=True)
        # If this project is being modified then we have to do one thing
        if not self.new_project:
            if self.existing_project is not None:
                # First find our creations
                for file in self.upload_digest.files.values():
                    # The project file always gets added to the project
                    if self.existing_project.files.get(file.rel_path) is None:
                        self.upload_log(f"  - [CREATE]: {file.rel_path}", Qgis.Info)
                        self.upload_log(f"        -  LOCAL: {file.size:,} Bytes  {file.etag}", Qgis.Info)
                        self.local_ops[UploadFile.FileOp.CREATE] += 1

                # Now we're looking for updates
                for file in self.upload_digest.files.values():
                    # If the file exists in the project but the etag is different then we need to update it
                    if file.rel_path in self.existing_project.files and self.existing_project.files[file.rel_path].etag != file.etag:
                        self.upload_log(f"  - [UPDATE]: {file.rel_path}", Qgis.Info)
                        self.upload_log(f"        - REMOTE: {self.existing_project.files[file.rel_path].size:,} Bytes  {self.existing_project.files[file.rel_path].etag}", Qgis.Info)
                        self.upload_log(f"        -  LOCAL: {file.size:,} Bytes  {file.etag}", Qgis.Info)
                        self.local_ops[UploadFile.FileOp.UPDATE] += 1

                # Now find the deletions
                for rel_path, file in self.existing_project.files.items():
                    if self.upload_digest.files.get(rel_path) is None:
                        self.upload_log(f"  - [DELETE]: {rel_path}", Qgis.Info)
                        self.local_ops[UploadFile.FileOp.DELETE] += 1

                # Now find the ignored changes (may comment this out for brevity later)
                for file in self.upload_digest.files.values():
                    if file.rel_path in self.existing_project.files and self.existing_project.files[file.rel_path].etag == file.etag:
                        self.upload_log(f"  - [NO CHANGE]: {file.rel_path}", Qgis.Info)
                        self.upload_log(f"        - REMOTE: {self.existing_project.files[file.rel_path].size:,} Bytes  {self.existing_project.files[file.rel_path].etag}", Qgis.Info)
                        self.upload_log(f"        -  LOCAL: {file.size:,} Bytes  {file.etag}", Qgis.Info)

            total_changes = self.local_ops[UploadFile.FileOp.CREATE] + self.local_ops[UploadFile.FileOp.UPDATE] + self.local_ops[UploadFile.FileOp.DELETE]
            if total_changes == 0:
                self.upload_log('  - No differences between local and remote. Nothing to upload', Qgis.Info)
                self.flow_state = ProjectUploadDialogStateFlow.NO_ACTION
            else:
                self.upload_log(f'Found changes that need: {self.local_ops[UploadFile.FileOp.CREATE]:,} New {self.local_ops[UploadFile.FileOp.UPDATE]:,} Update {self.local_ops[UploadFile.FileOp.DELETE]:,} delete', Qgis.Info)
                self.flow_state = ProjectUploadDialogStateFlow.USER_ACTION

        # Otherwise we're creating a new project and everything is a creation
        else:
            self.local_ops[UploadFile.FileOp.CREATE] = len(self.upload_digest.files)
            total_changes = self.local_ops[UploadFile.FileOp.CREATE]
            for file in self.upload_digest.files.values():
                self.upload_log(f"  - [CREATE]: {file.rel_path}", Qgis.Info)
            self.flow_state = ProjectUploadDialogStateFlow.USER_ACTION

    def _next_step(self):
        curr = self.stackedWidget.currentIndex()
        if curr == 0:
            self.stackedWidget.setCurrentIndex(1)
            self.recalc_local_ops() # Ensure latest ops
            self._populate_file_selection()
        elif curr == 1:
            self.handle_start_click() # Start upload
        elif curr == 2:
            if self.flow_state in [ProjectUploadDialogStateFlow.CANCELLED, ProjectUploadDialogStateFlow.ERROR]:
                self.handle_start_click()
        self.recalc_state()
            
    def _prev_step(self):
        curr = self.stackedWidget.currentIndex()
        if curr == 1:
            self.stackedWidget.setCurrentIndex(0)
            if self.flow_state in [ProjectUploadDialogStateFlow.CANCELLED, ProjectUploadDialogStateFlow.ERROR]:
                self.flow_state = ProjectUploadDialogStateFlow.USER_ACTION
        elif curr == 2:
            if self.flow_state in [ProjectUploadDialogStateFlow.CANCELLED, ProjectUploadDialogStateFlow.ERROR]:
                self.stackedWidget.setCurrentIndex(1)
                self.flow_state = ProjectUploadDialogStateFlow.USER_ACTION
        self.recalc_state()

    def _populate_file_selection(self):
        self.fileSelection.set_sorting_enabled(False)
        self.fileSelection.clear()
        
        # Map statuses
        if not self.new_project:
            # Modified project
            for rel_path, file in self.upload_digest.files.items():
                status = "New"
                highlight = None
                checked = True
                is_locked = False
                tooltip = None
                
                # We need to know if it exists in remote
                remote_file = self.existing_project.files.get(rel_path) if self.existing_project else None
                
                if remote_file:
                    if remote_file.etag == file.etag:
                        status = "No change"
                        checked = True
                        is_locked = False 
                        tooltip = "This file is already up to date on the Data Exchange."
                    else:
                        status = "Update"
                        highlight = "#2980b9"
                
                # project.rs.xml is mandatory
                is_mandatory = False
                if rel_path.lower() == 'project.rs.xml':
                    is_mandatory = True
                    checked = True
                    is_locked = False # Allow it to be checked/re-uploaded even if No Change? 
                    # Actually user said "always be selected".
                    tooltip = "This file is required for the project structure."

                self.fileSelection.add_file_item(
                    rel_path=rel_path,
                    size=file.size,
                    status_text=status,
                    checked=checked,
                    is_locked=is_locked,
                    is_mandatory=is_mandatory,
                    highlight_color=highlight,
                    tooltip=tooltip
                )
            
            # Find deletions
            allow_delete = self.fileSelection.chkAllowDelete.isChecked()
            if self.existing_project:
                for rel_path, remote_file in self.existing_project.files.items():
                    if rel_path not in self.upload_digest.files:
                        is_locked = not allow_delete
                        checked = allow_delete # If allowed to delete, we check it by default (meaning "Select for deletion")
                        
                        self.fileSelection.add_file_item(
                            rel_path=rel_path,
                            size=remote_file.size,
                            status_text="Delete",
                            checked=checked,  
                            is_locked=is_locked,
                            highlight_color="#c0392b"
                        )
        else:
            # New project
            for rel_path, file in self.upload_digest.files.items():
                checked = True
                is_mandatory = False
                if rel_path.lower() == 'project.rs.xml':
                    is_mandatory = True
                
                self.fileSelection.add_file_item(
                    rel_path=rel_path,
                    size=file.size,
                    status_text="New",
                    checked=checked,
                    is_mandatory=is_mandatory
                )
        
        self.fileSelection.set_sorting_enabled(True)
        self.fileSelection.sort_by_column(0, Qt.AscendingOrder)
        
        self._update_selection_summary()

    def _update_selection_summary(self):
        """ Update the summary line at the bottom of the file selection step """
        selected = self.fileSelection.get_selected_files()
        all_items = []
        root = self.fileSelection.treeFiles.invisibleRootItem()
        for i in range(root.childCount()):
            all_items.append(root.child(i))

        upload_count = 0
        delete_count = 0
        keep_count = 0
        
        for item in all_items:
            # rel_path = item.data(0, Qt.UserRole)
            status = item.text(2)
            checked = item.checkState(0) == Qt.Checked
            
            if status == "Delete":
                if checked:
                    delete_count += 1
                else:
                    keep_count += 1
            elif status == "No change":
                if checked:
                    keep_count += 1
                else:
                    delete_count += 1
            else:
                # New or Update
                if checked:
                    upload_count += 1
                else:
                    # If it existed remotely it's a delete, if it was only local it's a skip
                    # For simplicity in summary we'll just count it as "skip/unchanged" if it's not being uploaded
                    # Actually, if it's local only and unchecked, it just won't be in the project remote.
                    keep_count += 1
            
        summary_parts = []
        if upload_count > 0:
            summary_parts.append(f"{upload_count} file{'s' if upload_count != 1 else ''} will be uploaded")
        if delete_count > 0:
            summary_parts.append(f"{delete_count} file{'s' if delete_count != 1 else ''} will be deleted")
        if keep_count > 0:
            summary_parts.append(f"{keep_count} file{'s' if keep_count != 1 else ''} will remain unchanged")
            
        self.lblSelectionSummary.setText(", ".join(summary_parts) + ".")

    def _reconcile_selections_with_digest(self):
        """ Reconcile the user's selections in the widget with the upload digest """
        # Copy current local files info
        local_files = {rel_path: (file.size, file.etag) for rel_path, file in self.upload_digest.files.items()}
        
        # Reset the digest
        self.upload_digest.reset()
        
        # Loop through widget items
        root = self.fileSelection.treeFiles.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            rel_path = item.data(0, Qt.UserRole)
            status = item.text(2)
            checked = item.checkState(0) == Qt.Checked
            
            if status == "Delete":
                # Only add if UNchecked (meaning "Keep")
                if not checked and self.existing_project and rel_path in self.existing_project.files:
                    remote_file = self.existing_project.files[rel_path]
                    self.upload_digest.add_file(rel_path, remote_file.size, remote_file.etag)
            else:
                # Add if Checked
                if checked and rel_path in local_files:
                    size, etag = local_files[rel_path]
                    self.upload_digest.add_file(rel_path, size, etag)

    def handle_new_or_update_change(self, button, checked):
        """ Handler for the radio button group that determines if we're creating a new project or updating an existing one

        Args:
            button (_type_): _description_
            checked (_type_): _description_
        """
        total_changes = 0
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

                    self.recalc_state()
                else:
                    # If there's no project set it back to new
                    self.optNewProject.setChecked(True)
                    self.new_project = True

            # Re-verify the uplodability of the project
            self.recalc_local_ops()
            self.recalc_state()

    def handle_owner_change(self, button, checked):
        if checked:
            btn_id = self.mine_group.checkedId()
            if btn_id == 1:
                index = self.orgSelect.currentIndex()
                self.org_id = self.OrgModel.item(index).data(Qt.UserRole)
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
        elif project and project.deleted is True:
            # This is a limited case that only exists between when the user actually deletes the project and when the system
            # finishes cleaning up the files etc.
            self.upload_log(f'  - ERROR: Project has been deleted. Could not find: {self.dataExchangeAPI.api.uri}/p/{project.id}', Qgis.Critical, task)
            self.error = ProjectUploadDialogError('Project has been deleted remotely', 'The project has been deleted from the warehouse. You can still upload it as a new project if you want.')
            self.existing_project = None
        else:
            self.upload_log(f'  - SUCCESS: Fetched existing project from: {self.dataExchangeAPI.api.uri}/p/{project.id}', Qgis.Info)
            self.existing_project = project
            self.new_project = False

            self.optModifyProject.setChecked(True)

            self.upload_log('Rescanning files based on existing project files...', Qgis.Info)
            self.upload_digest.reset()
            self.upload_digest.scan_local_files(self.project_xml.project_dir, self.project_xml.project_type)

            # Recalculate etags with existing files
            existing_etags = {k: v.etag for k, v in self.existing_project.files.items()}
            self.upload_log('Recalculating file etags based on existing project files...', Qgis.Info)
            self.upload_digest.calculate_etags(self.project_xml.project_dir, existing_files=existing_etags)

        self.upload_log('Waiting for user input...' + '\n' * 3, Qgis.Info)
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

            self.error = ProjectUploadDialogError(self.error.summary, self.error.detail)
            self.upload_log(f"{self.error.summary} DETAIL:  {self.error.detail}", Qgis.Critical)
        else:
            # Set the whole group disabled
            self.errorLayout.setEnabled(False)

            self.errorMoreBtn.setVisible(False)
            self.errorSummaryLable.setText('')
            self.errorSummaryLable.setStyleSheet("QLabel { color : black; border: 0px; }")
            self.error = None

    def upload_log(self, message: str, level: int = Qgis.Info, context_obj=None, is_header=False):
        """ Logging here should go to the QGIS log and to a file we can check later

        Args:
            message (str): _description_
            level (int): _description_
            context_obj (_type_, optional): _description_. Defaults to None.
        """
        header_bars = '-' * 80
        self.settings.log(message, level)
        level_name = error_level_to_str(level)
        with open(self.upload_log_path, 'a', encoding='utf-8') as f:
            # Get an iso timestamp to prepend the message
            timestamp = datetime.datetime.now().isoformat()
            # add an opening header bar if we need to
            if is_header:
                f.write(f"[{timestamp}][{level_name}]\n")
                f.write(f"[{timestamp}][{level_name}] {header_bars}\n")
            f.write(f"[{timestamp}][{level_name}] {message}\n")
            if context_obj is not None:
                if isinstance(context_obj, (dict, list)):
                    try:
                        f.write(json.dumps(context_obj, indent=2) + '\n')
                    except Exception as e:
                        f.write(f"        Could not serialize context object: {str(e)}\n")
                elif isinstance(context_obj, RunGQLQueryTask):
                    context_str = f"Task Context: {context_obj.debug_log()}\n"
                    # indent every line in context_str including the first one by 4 spaces
                    context_str = '\n'.join(['    ' + line for line in context_str.split(os.linesep)])
                    f.write(context_str)
                elif isinstance(context_obj, UploadMultiPartFileTask):
                    context_str = f"UploadFile Context: {context_obj.debug_log()}\n"
                    # indent every line in context_str including the first one by 4 spaces
                    context_str = '\n'.join(['    ' + line for line in context_str.split(os.linesep)])
                    f.write(context_str)
                elif isinstance(context_obj, RefreshTokenTask):
                    context_str = f"Refresh Token Context: {context_obj.debug_log()}\n"
                    # indent every line in context_str including the first one by 4 spaces
                    context_str = '\n'.join(['    ' + line for line in context_str.split(os.linesep)])
                    f.write(context_str)
                else:
                    try:
                        f.write(str(context_obj) + '\n')
                    except Exception as e:
                        f.write(f"Could not convert context object to string: {str(e)}\n")
            # Add a closing header bar if we need to
            if is_header:
                f.write(f"[{timestamp}][{level_name}] {header_bars}\n")

    def handle_start_click(self):
        """ The user kicks off the upload process. we give them a dialog to confirm
        and then we start the process
        """
        # Set any errors to zero so we can start fresh
        self.error = None

        # Make sure the state is clear to begin with. This is maybe a little overkill but it can't hurt to be safe
        self.reset_upload_state()

        qm = QMessageBox()
        qm.setWindowTitle('Start Upload?')
        qm.setDefaultButton(qm.No)
        text = f"This will upload the project \"{self.project_xml.project.find('Name').text}\" to the Riverscapes Data Exchange"
        if self.new_project:
            text += ' as a new project.'
        else:
            text += ' as an update to the existing project.'
        qm.setText(text + ' Are you sure?')
        qm.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        # Remove the log file if it exists and create a new one
        self.upload_log('User-Initiated project upload starting', Qgis.Info, is_header=True)

        response = qm.exec_()
        if response == QMessageBox.Yes:
            # Before validation, we need to finalize what we're actually sending
            self._reconcile_selections_with_digest()
            self.flow_state = ProjectUploadDialogStateFlow.VALIDATING
            self.recalc_state()

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
        self.flow_state = ProjectUploadDialogStateFlow.CANCELLED
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
            if len(validation_obj.errors) > 0:
                # Find an error that contains "The project you are verifying has been changed in the warehouse since you downloaded it"
                # If we find it, we need to pop open a confirmation dialog to let the user opt out
                # of the upload
                for err in validation_obj.errors:
                    if 'The project you are verifying has been changed in the warehouse since you downloaded it' in err.message:
                        qm = QMessageBox()
                        qm.setWindowTitle('Project Changed')
                        qm.setDefaultButton(qm.No)
                        qm.setText('The project you are trying to upload has been changed in the warehouse since you downloaded it.')
                        qm.setInformativeText('<strong>Are you sure you want to continue? Saying "yes" will overwrite all changes in the Data Exchange.</strong>')
                        qm.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                        response = qm.exec_()
                        if response == QMessageBox.No:
                            self.upload_log('  - WARNING: User opted out of the upload due to project changes', Qgis.Warning)
                            self.flow_state = ProjectUploadDialogStateFlow.USER_ACTION
                            self.recalc_state()
                            return
                        else:
                            self.upload_log('  - WARNING: User opted to continue the upload despite project changes', Qgis.Warning)
                            break

            if validation_obj.valid is True:
                # Validation done. Now request upload
                owner_obj = self.get_owner_obj()
                self.upload_log('  - SUCCESS: Validation: Project is valid.', Qgis.Info)
                self.upload_log('Requesting new upload from the API...', Qgis.Info)
                self.dataExchangeAPI.request_upload_project(
                    files=self.upload_digest,
                    tags=self.tags,
                    no_delete=not self.fileSelection.chkAllowDelete.isChecked(),
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
            self.upload_log('Summary of files and operations: (deletions are not shown here)', Qgis.Info)
            for file in self.upload_digest.files.values():
                # We set the project XML file explicitly because it's ALWAYS uploaded
                if file.op in [UploadFile.FileOp.CREATE, UploadFile.FileOp.UPDATE]:
                    changes += 1
                self.upload_log(f"  - [{(str(file.op).upper())}] {file.rel_path} size: {file.size:,} etag: {file.etag}", Qgis.Info)

            if changes == 0:
                self.upload_log('No files to upload. Skipping upload step', Qgis.Info)
                # If no files to upload, we might still need to finalize (e.g. metadata only change or deletions)
                # But deletions are handled by request_upload_project's delete logic?
                # Actually, the uploader queue ONLY handles uploads.
                self.upload_log('Finalizing metadata/deletions...', Qgis.Info)
                self.handle_uploads_complete()
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
            self.stackedWidget.setCurrentIndex(2)
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
        uploaded_str = humane_bytes(uploaded_bytes)
        total_str = humane_bytes(total_bytes)

        self.todoLabel.setText(f"Uploading: {uploaded_str} of {total_str} {end_time_str}")
        self.progressSubLabel.setText(f"Uploading: {biggest_file_relpath}")

    def handle_upload_start(self):
        """ Start the upload process
        This kicks off our asynchronous upload queue process
        After all files are uploaded we will call the finalize endpoint
        """
        self.upload_log('Starting the ACTUAL file upload process...', Qgis.Info)

        selected_files = self.fileSelection.get_selected_files()
        for rel_path in selected_files:
            if rel_path in self.upload_digest.files:
                upFile = self.upload_digest.files[rel_path]
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

        self.flow_state = ProjectUploadDialogStateFlow.CANCELLED
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
            self.upload_log('Upload failed: ' + json.dumps(job_status_obj, indent=2) + '\n' * 3, Qgis.Critical, task)
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
            self.upload_log('Upload Timed-Out after 300 seconnds (5min)' + '\n' * 3, Qgis.Critical, task)
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
            self.upload_log('  - ERROR: Could not download the project.rs.xml file back to the local project folder' + '\n' * 3, Qgis.Critical, task)
            self.error = ProjectUploadDialogError('Download failed', 'The download of the project.rs.xml file failed. Check the logs to see the reason')
            self.flow_state = ProjectUploadDialogStateFlow.ERROR
        else:
            self.upload_log('  - SUCCESS: Downloaded the project.rs.xml file back to the local project folder', Qgis.Info)
            self.upload_log('Upload process complete. Shutting down.' + '\n' * 3, Qgis.Info)
            self.flow_state = ProjectUploadDialogStateFlow.COMPLETED
            self.recalc_state()
