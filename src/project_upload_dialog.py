import os
import json
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox
from qgis.PyQt.QtCore import pyqtSignal, QUrl
from qgis.PyQt.QtGui import QIcon, QDesktopServices
from qgis.core import Qgis

from .classes.settings import SecureSettings
from .classes.basemaps import BaseMaps


# DIALOG_CLASS, _ = uic.loadUiType(os.path.join(
#     os.path.dirname(__file__), 'ui', 'options_dialog.ui'))
from .ui.project_upload_dialog import Ui_Dialog


class ProjectUploadDialog(QDialog, Ui_Dialog):

    closingPlugin = pyqtSignal()
    dataChange = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.secure_settings = SecureSettings()

        self.token = self.secure_settings.retrieve_token()
        self.selectedOrg = None
        self.selectUpdate = False
        self.access = None
        self.tags = []

    def check_login(self):
        # 1. Check the secure settings for a valid token
        # 2. Ping the API with the token to see if it's still valid
        if (self.token is None):
            self.login_reset()
        pass

    def login_reset(self):
        self.secure_settings.delete_token()
        self.token = None
        pass

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
