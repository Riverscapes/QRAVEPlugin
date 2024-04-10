from typing import List, Callable, Dict
import os
from collections import namedtuple
from qgis.PyQt.QtCore import QObject, pyqtSignal, pyqtSlot
from qgis.core import QgsMessageLog, Qgis

from ..GraphQLAPI import GraphQLAPI, GraphQLAPIConfig, RunGQLQueryTask, RefreshTokenTask
from ..settings import CONSTANTS

MyOrg = namedtuple('MyOrg', ['id', 'name', 'myRole'])


class DEProfile:
    def __init__(self, id, name, organizations):
        self.id = id
        self.name = name
        self.organizations: List[MyOrg] = organizations


class DEProject:
    def __init__(self, id, name, ownedBy, visibility, permissions, tags):
        self.id = id
        self.name = name
        self.tags = tags
        self.ownedBy = ownedBy
        self.visibility = visibility
        self.permissions = permissions


class DEValidation:
    def __init__(self, valid, errors):
        self.valid = valid
        self.errors = []
        for error in errors:
            del error['__typename']
            self.errors.append(ValidationErrorTuple(**error))


class ValidationErrorTuple(namedtuple('ValidationErrorTuple', ['code', 'message', 'severity'])):
    pass


class OwnerInputTuple(namedtuple('OwnerInputTuple', ['id', 'type'])):
    pass


# BASE is the name we want to use inside the settings keys
MESSAGE_CATEGORY = CONSTANTS['logCategory']


class DataExchangeAPI(QObject):
    # This will mean that all instances of this class will share the same state
    _shared_state = {}
    stateChange = pyqtSignal()

    """ Class to handle data exchange between the different components of the system
    """

    def __init__(self, on_login=Callable[[bool], None]):
        super().__init__()
        # Make sure the Borg pattern is initialized
        self.__dict__ = self._shared_state
        if not hasattr(self, 'initialized'):
            self.myId = None
            self.myName = None
            self.myOrgs = []
            self.initialized = False
            self.on_login = on_login
            self.api = GraphQLAPI(
                apiUrl=os.environ.get('DE_API_URL', CONSTANTS['DE_API_URL']),
                config=GraphQLAPIConfig(**CONSTANTS['DE_API_AUTH'])
            )
            # Tie the state change signal to the state change handler inside self.api
            self.api.stateChange.connect(self.stateChange.emit)

            self.initialized = self.api.access_token is not None
        # Regardless of outcome we should check the token status
        self.api.refresh_token(self._handle_refresh_token)

    def login(self):
        self.myId = None
        self.myName = None
        self.myOrgs = []
        self.initialized = False
        self.api.refresh_token(self._handle_refresh_token)
        self.stateChange.emit()

    def _handle_refresh_token(self, task: RefreshTokenTask):
        if task.error:
            QgsMessageLog.logMessage(
                'Error refreshing token', MESSAGE_CATEGORY, Qgis.Critical)
            QgsMessageLog.logMessage(task.error, MESSAGE_CATEGORY, Qgis.Error)
            self.initialized = False
            self.on_login(task)
        else:
            self.initialized = True
            self.on_login(task)

    def _load_query(self, query_name: str) -> str:
        """ Load a query from the queries directory

        Args:
            query_name (str): the name of the query to load
        """
        with open(os.path.join(os.path.dirname(__file__), 'graphql', f'{query_name}.graphql'), 'r') as f:
            return f.read()

    def get_user_info(self, callback: Callable[[RunGQLQueryTask, DEProfile], None]):
        """ Get the organizations that the user is a part of

        """
        def _parse_orgs(task: RunGQLQueryTask):
            profile = None
            if task.response and not task.error:
                myId = task.response['data']['profile']['id']
                myName = task.response['data']['profile']['name']
                myOrgs = [
                    MyOrg(**org) for org in task.response['data']['profile']['organizations']['items']
                ]
                profile = DEProfile(myId, myName, myOrgs)

            return callback(task, profile)

        # Returns a RunGQLQueryTask(QgsTask) object in case you want to handle or manage it
        return self.api.run_query(self._load_query('getProfile'), {}, _parse_orgs)

    def get_project(self, project_id: str, callback: Callable[[RunGQLQueryTask, DEProject], None]):
        """ Get the metadata for a project

        Args:
            project_id (str): the id of the project to get
        """
        def _parse_project(task: RunGQLQueryTask):
            project = None
            if task.response and not task.error:
                project = DEProject(**task.response['data']['project'])

            return callback(task, project)

        return self.api.run_query(self._load_query('getProject'), {'id': project_id}, _parse_project)

    def validate_project(self, xml_str: str, owner_obj: OwnerInputTuple, files: List[str], callback: Callable[[RunGQLQueryTask, Dict], None]):
        """ Validate a project

        Args:
            xml_str (str): the xml string of the project
            owner_obj (OwnerInputTuple): the owner of the project
            files (List[str]): the list of files in the project (relative paths only)
            callback (Callable[[RunGQLQueryTask, Dict], None]): the callback function to call
        """
        def _validate_project(task: RunGQLQueryTask):
            validation = None
            if task.response and not task.error:
                validation = DEValidation(**task.response['data']['validateProject'])

            return callback(task, validation)

        return self.api.run_query(self._load_query('validateProject'), {'xml': xml_str, 'owner': owner_obj, 'files': files}, _validate_project)

    def request_upload_project(self,
                               files: List[str], file_etags: List[str], file_sizes: List[int],
                               tags: List[str],
                               owner_obj: OwnerInputTuple,
                               project_id: str = None, project_token: str = None,
                               no_delete=False,
                               visibility: str = 'PUBLIC',
                               callback: Callable[[RunGQLQueryTask, Dict], None] = None):
        """ Request to upload a project

        Args:
            files (List[str]): _description_
            file_etags (List[str]): _description_
            file_sizes (List[int]): _description_
            tags (List[str]): _description_
            owner_obj (OwnerInputTuple): _description_
            project_id (str, optional): _description_. Defaults to None.
            project_token (str, optional): _description_. Defaults to None.
            no_delete (bool, optional): _description_. Defaults to False.
            visibility (str, optional): _description_. Defaults to 'PUBLIC'.
            callback (Callable[[RunGQLQueryTask, Dict], None], optional): _description_. Defaults to None.
        """
        def _request_upload_project(task: RunGQLQueryTask):
            ret_obj = None
            if task.response and not task.error:
                ret_obj = task.response['data']['requestUploadProject']

            return callback(task, ret_obj)

        return self.api.run_query(self._load_query('requestUploadProject'), {'xml': xml_str, 'owner': owner_obj, 'files': files}, _request_upload_project)

    def request_upload_project_files_url(self, files: List[str], project_upload_token: str, callback: Callable[[RunGQLQueryTask, Dict], None]):
        """ Request a URL to upload project files to

        Args:
            files (List[str]): _description_
            project_upload_token (str): _description_
            callback (Callable[[RunGQLQueryTask, Dict], None]): _description_
        """
        def _request_upload_project_files_url(task: RunGQLQueryTask):
            ret_obj = None
            if task.response and not task.error:
                ret_obj = task.response['data']['requestUploadProjectFilesUrl']

            return callback(task, ret_obj)

        return self.api.run_query(self._load_query('requestUploadProjectFilesUrl'), {'files': files, 'token': project_upload_token}, _request_upload_project_files_url)

    def finalize_project_upload(self, project_upload_token: str, callback: Callable[[RunGQLQueryTask, Dict], None]):
        """ Finalize the project upload

        Args:
            project_id (str): the id of the project to upload
        """
        def _finalize_project_upload(task: RunGQLQueryTask):
            ret_obj = None
            if task.response and not task.error:
                ret_obj = task.response['data']['finalizeProjectUpload']

            return callback(task, ret_obj)

        return self.api.run_query(self._load_query('finalizeProjectUpload'), {'token': project_upload_token}, _finalize_project_upload)

    def check_upload(self, project_upload_token: str, callback: Callable[[RunGQLQueryTask, Dict], None]):
        """ Check the status of the upload

        Args:
            project_id (str): the id of the project to upload
        """
        def _check_upload(task: RunGQLQueryTask):
            ret_obj = None
            if task.response and not task.error:
                ret_obj = task.response['data']['checkUpload']

            return callback(task, ret_obj)

        return self.api.run_query(self._load_query('checkUpload'), {'token': project_upload_token}, _check_upload)

    def download_file(self, project_id: str, remote_path: str, local_path: str, callback: Callable[[RunGQLQueryTask, Dict], None]):
        """ Download the project file

        Args:
            project_id (str): the id of the project to download
        """
        def _download_file(task: RunGQLQueryTask):
            ret_obj = None
            if task.response and not task.error:
                ret_obj = task.response['data']['downloadFile']

            return callback(task, ret_obj)

        return self.api.run_query(self._load_query('downloadFile'), {'id': project_id, 'filePath': remote_path}, _download_file)


#     def upload_project(self, project_id: str, callback=None):
#         """ Upload a project

#         Args:
#             project_id (str): the id of the project to upload
#         """
#         self.validate_project(project_id, callback)

#         self.request_upload_project(project_id, callback)
#         upload_url = self.request_upload_project_files_url(project_id, callback)
#         # Upload the files to the S3 bucket
#         # ...
#         # Finalize the upload
#         self.finalize_project_upload(project_id, callback)
#         # Check the status of the upload
#         self.check_upload(project_id, callback)
#         # Download the project file
#         self.download_file(project_id, callback)


# """
# # Validate the project file to see if there are any errors
# validateProject
#         requestUploadProject

# # Request a URL to upload the files to the S3 bucket
#         requestUploadProjectFilesUrl

# # Finalize meaning that all files are uploaded and the upload copy is good to start
# finalizeProjectUpload

# # Check to see if the upload is complete on a while loop
# checkUpload

# Then download the new project file here:
# downloadFile
#         """
