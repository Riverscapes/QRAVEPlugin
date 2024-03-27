from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox
from qgis.PyQt.QtCore import pyqtSignal, pyqtSlot
from qgis.core import Qgis, QgsMessageLog

from .classes.DataExchangeAPI import DataExchangeAPI
from .classes.settings import CONSTANTS

# DIALOG_CLASS, _ = uic.loadUiType(os.path.join(
#     os.path.dirname(__file__), 'ui', 'options_dialog.ui'))
from .ui.project_upload_dialog import Ui_Dialog

# Here are the states we're going to pass through

# BASE is the name we want to use inside the settings keys
MESSAGE_CATEGORY = CONSTANTS['logCategory']


class State:
    ERROR = -1
    INITIALIZING = 0
    LOGING_IN = 1
    FETCHING_PROFILE = 2
    FETCHING_EXISTING_PROJECT = 3
    USER_ACTION = 4
    VALIDATING = 5
    UPLOADING = 6
    WAITING_FOR_COMPLETION = 7
    COMPLETED = 8


class ProjectUploadDialog(QDialog, Ui_Dialog):

    closingPlugin = pyqtSignal()
    stateChange = pyqtSignal()
    dataChange = pyqtSignal()

    def __init__(self, parent=None, project=None):
        """Constructor."""
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.project_xml = project
        self.flow_state = State.INITIALIZING
        self.stateChange.connect(self.state_change_handler)

        self.api = DataExchangeAPI()

        #   <Warehouse id="00000000-0000-0000-0000-000000000000" apiUrl="https://api.data.riverscapes.net"/>
        self.warehouse_id = None
        self.apiUrl = None
        warehouse_tag = self.project_xml.project.find('Warehouse')
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

    def set_error(self, message):
        self.flow_state = State.ERROR
        self.stateChange.emit()
        QgsMessageLog.logMessage(message, MESSAGE_CATEGORY, Qgis.Error)

    @pyqtSlot()
    def state_change_handler(self):
        """ Control the state of the controls in the dialog
        """
        allow_user_action = self.flow_state in [State.USER_ACTION]
        # QtWidgets.QDialogButtonBox
        # set the ok button text to "Start"
        self.actionBtnBox.button(QDialogButtonBox.Ok).setText("Start")
        self.actionBtnBox.button(QDialogButtonBox.Cancel).setText(self.flow_state == State.USER_ACTION and "Cancel" or "Stop")
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

        self.progressBar.setEnabled(self.flow_state in [State.UPLOADING])
        self.progressBar.setValue(0)
        self.progressSubLabel.setEnabled(self.flow_state in [State.UPLOADING])
        self.progressSubLabel.setText('...')

        # Set things enabled at the group level to save time
        self.newOrUpdateLayout.setEnabled(allow_user_action)
        self.ownershipGroup.setEnabled(allow_user_action)
        self.tagGroup.setEnabled(allow_user_action)
        self.accessGroup.setEnabled(allow_user_action)

    def check_login(self):
        # 1. Check the secure settings for a valid token
        # 2. Ping the API with the token to see if it's still valid
        if (self.token is None):
            self.login_reset()
        pass

    def login_reset(self):
        self.api = None
        self.api = DataExchangeAPI()
        self.stateChange.emit()

    def init_values_async(self):
        # 0. Verify logged-in status and bail if not (if any of the following fail then also reset the login status)
        # 1. Read the <Warehouse> tag of the current project and decide if we need to fetch metadata
        #     a. If not then disable "view in exchange" btn and "modify existing" option.
        # 2. Make a graphql query to get the user's organizations
        # 3. If this project has a warehouse tag fetch the metadata
        pass

    def new_or_old_change(self):
        """ If the user selects "new" or "old" we need to check some things
        """
        pass

    def project_ownership_change(self):
        """ IF the user selects "new" then reset self.selectedOrg. 
        """
        pass

    def set_values(self):
        # Set the combo box
        pass

    def tag_add(self, tag: str):
        pass

    def tag_remove(self, tag: str):
        pass

    def login(self):
        pass

    def open_project_in_browser(self):
        pass

    def cancel_btn_press(self):
        pass

    def ok_btn_press(self):
        pass

    def help_btn_press(self):
        pass

    def confirm_overwrite(self):
        """ Ask the user if they want to overwrite the destination project (always show if not new)
        """
        pass

    def confirm_dest_newer(self):
        """If the destination project is newer than the source project, ask the user if they want to overwrite the destination project.
        """
        pass

    def commit_settings(self, btn):
        pass
