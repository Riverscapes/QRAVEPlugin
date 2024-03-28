from typing import List
import os
from collections import namedtuple
from qgis.core import QgsMessageLog, Qgis

from ..GraphQLAPI import GraphQLAPI, GraphQLAPIConfig
from ..settings import CONSTANTS
from ..borg import Borg

MyOrgs = namedtuple('MyOrgs', ['id', 'name', 'myRole'])

# BASE is the name we want to use inside the settings keys
MESSAGE_CATEGORY = CONSTANTS['logCategory']


class DataExchangeAPI(Borg):
    # This will mean that all instances of this class will share the same state
    _shared_state = {}

    """ Class to handle data exchange between the different components of the system
    """

    def __init__(self):
        self.myId = None
        self.myName = None
        self.myOrgs = []
        self.initialized = False
        self.api = GraphQLAPI(
            apiUrl=CONSTANTS['DE_API_Url'],
            config=GraphQLAPIConfig(**CONSTANTS['DE_API_Auth'])
        )
        self.api.refresh_token()
        self.initialized = self.api.access_token is not None

    def _load_query(self, query_name: str) -> str:
        """ Load a query from the queries directory

        Args:
            query_name (str): the name of the query to load
        """
        with open(os.path.join(os.path.dirname(__file__), 'graphql', 'DataExchange' f'{query_name}.gql'), 'r') as f:
            return f.read()

    def get_project(self, project_id: str):
        """ Get the metadata for a project

        Args:
            project_id (str): the id of the project to get
        """
        project = self.api.run_query(self._load_query('getProject'), {'id': project_id})
        QgsMessageLog.logMessage('get_project success', MESSAGE_CATEGORY)
        return project['data']['project']

    def get_user_info(self) -> List[MyOrgs]:
        """ Get the organizations that the user is a part of

        """
        orgs = self.api.run_query(self._load_query('getProfile'), {})
        QgsMessageLog.logMessage('get_organizations success', MESSAGE_CATEGORY)
        self.myId = orgs['data']['profile']['id']
        self.myName = orgs['data']['profile']['name']
        self.myOrgs = [MyOrgs(**org) for org in orgs['data']['profile']['organizations']['items']]

    def request_upload_project(self, project_id: str):
        """ Request to upload a project

        Args:
            project_id (str): the id of the project to upload
        """
        response = self.api.run_query(self._load_query('requestUploadProject'), {'id': project_id})
        QgsMessageLog.logMessage('request_upload_project success', MESSAGE_CATEGORY)
        return response['data']['requestUploadProject']

    def request_upload_project_files_url(self, project_id: str):
        """ Request a URL to upload project files to

        Args:
            project_id (str): the id of the project to upload
        """
        response = self.api.run_query(self._load_query('requestUploadProjectFilesUrl'), {'id': project_id})
        QgsMessageLog.logMessage('request_upload_project_files_url success', MESSAGE_CATEGORY)
        return response['data']['requestUploadProjectFilesUrl']

    def finalize_project_upload(self, project_id: str):
        """ Finalize the project upload

        Args:
            project_id (str): the id of the project to upload
        """
        response = self.api.run_query(self._load_query('finalizeProjectUpload'), {'id': project_id})
        QgsMessageLog.logMessage('finalize_project_upload success', MESSAGE_CATEGORY)
        return response['data']['finalizeProjectUpload']

    def check_upload(self, project_id: str):
        """ Check the status of the upload

        Args:
            project_id (str): the id of the project to upload
        """
        response = self.api.run_query(self._load_query('checkUpload'), {'id': project_id})
        QgsMessageLog.logMessage('check_upload success', MESSAGE_CATEGORY)
        return response['data']['checkUpload']

    def download_file(self, project_id: str):
        """ Download the project file

        Args:
            project_id (str): the id of the project to download
        """
        response = self.api.run_query(self._load_query('downloadFile'), {'id': project_id})
        QgsMessageLog.logMessage('download_file success', MESSAGE_CATEGORY)
        return response['data']['downloadFile']


"""
# Validate the project file to see if there are any errors
validateProject
        requestUploadProject

# Request a URL to upload the files to the S3 bucket
        requestUploadProjectFilesUrl

# Finalize meaning that all files are uploaded and the upload copy is good to start
finalizeProjectUpload

# Check to see if the upload is complete on a while loop
checkUpload

Then download the new project file here:
downloadFile
        """
