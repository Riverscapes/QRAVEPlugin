from typing import List, Callable, Dict, OrderedDict
import os
import re
from collections import namedtuple, OrderedDict
from qgis.PyQt.QtCore import QObject, pyqtSignal, pyqtSlot
from qgis.core import Qgis
import requests

from rsxml.etag import calculate_etag
from ..GraphQLAPI import GraphQLAPI, GraphQLAPIConfig, RunGQLQueryTask, RefreshTokenTask
from ..settings import CONSTANTS, Settings

FILE_EXCLUDE_RE = [
    r'^\.git',
    r'^\.DS_Store',
    r'^\.gitignore',
    r'^\.gitattributes',
    r'^\.gitmodules',
    # Anything ending with .gpkg-journal
    r'.*\.gpkg-[a-z]+$',
    # Any file called 'RiverscapesViewer*.log'
    r'^RiverscapesViewer.*\.log$',
]


class DEProfile:
    def __init__(self, id, name, organizations):
        self.id = id
        self.name = name
        self.organizations: List[MyOrg] = []
        for org in organizations:
            self.organizations.append(MyOrg(**org))


class DEProject:
    class GetProjectFile(namedtuple('GetProjectFile', ['size', 'etag'])):
        pass

    def __init__(self, id, name, deleted, ownedBy, visibility, permissions, tags, files, createdOn=None, updatedOn=None, projectType=None, summary=None):
        self.id = id
        self.name = name
        self.tags = tags
        self.deleted = deleted
        self.ownedBy = ownedBy
        self.visibility = visibility
        self.permissions = permissions
        self.createdOn = createdOn
        self.updatedOn = updatedOn
        self.projectType = projectType
        self.summary = summary
        self.files = {f['localPath']: DEProject.GetProjectFile(f['size'], f['etag']) for f in files}


class DEValidation:
    def __init__(self, valid, errors):
        self.valid = valid
        self.errors = []
        for error in errors:
            del error['__typename']
            self.errors.append(ValidationErrorTuple(**error))


class UploadFile():
    class FileOp:
        CREATE = 'create'
        UPDATE = 'update'
        DELETE = 'delete'

    rel_path: str
    size: int
    etag: str
    op: FileOp
    urls: List[str] = []

    def __init__(self, rel_path: str, size: int, etag: str = None):
        self.rel_path = rel_path
        self.size = size
        self.etag = etag
        self.op = None
        urls = []


class UploadFileList():
    token: str = None
    # It should be an ordered dictionary
    files: OrderedDict[str, UploadFile] = OrderedDict()

    def __init__(self):
        # Make sure the Borg pattern is initialized
        self.settings = Settings()
        self.log = self.settings.log

    def reset(self):
        self.token = None
        self.files = OrderedDict()

    def add_file(self, rel_path: str, size: int, etag: str):
        self.files[rel_path] = UploadFile(rel_path, size, etag)

    def scan_local_files(self, project_dir: str, project_type: str):
        """Scrape through the project folder and add all files to the upload digest
        except if they are a business logic file or match the exclusion list

        Args:
            project_dir (str): _description_
            project_type (str): _description_

        Raises:
            ValueError: _description_
        """
        if not self.files:
            self.files = OrderedDict()
        # Search for a file called '{project_type}.xml' in the project directory (case insensitive  )
        bl_file_check = re.compile(rf'{project_type}\.xml$', re.IGNORECASE)

        if not os.path.isdir(project_dir):
            raise ValueError(f"Project directory {project_dir} does not exist")

        for root, _dirs, files in os.walk(project_dir):
            for file in files:
                # make sure this isn't a proj_type file or
                # isn't in the exclusion list (case insensitive)
                if bl_file_check.match(file) or any([re.match(exclude_re, file, re.IGNORECASE) for exclude_re in FILE_EXCLUDE_RE]):
                    continue
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, project_dir)
                # replace backslashes with forward slashes
                rel_path = rel_path.replace('\\', '/')

                file_size = os.path.getsize(abs_path)
                # WE add a dummy etag here, it will be calculated later if there is an existing project. If not then the etag does not really matter
                # Since there is nothing to compare against and we can skip that constly step entirely
                self.add_file(rel_path, file_size, etag='XXXXXXXXXXXXXXXXXXXXXX')

    def calculate_etags(self, project_dir: str, existing_files: Dict[str, str] = None):
        """Calculate the etags for all files in the upload digest

        Args:
            project_dir (str): _description_
            existing_files (Dict[str, str], optional): Dictionary of existing files in the data exchange and their etags. Defaults to None.
        """
        for file in self.files.values():
            abs_path = os.path.join(project_dir, file.rel_path)

            is_single_part = False
            if existing_files and file.rel_path in existing_files:
                existing_etag = existing_files[file.rel_path]
                # If the existing etag has a dash, it is multipart, so we should NOT force single part.
                is_single_part = not re.match(r'.*-[0-9]+$', existing_etag)
                # We only compute the local etag if there is a remote file to compare with. This should
                # Save a lot of time when uploading new files.
                self.log('Calculating etag for file: ' + file.rel_path, Qgis.Info)
                etag_obj = calculate_etag(abs_path, force_single_part=is_single_part)
                self.log(f"Calculated etag: {etag_obj} (single part: {is_single_part})", Qgis.Info)
                file.etag = etag_obj

    def get_rel_paths(self, filter_to: List[UploadFile.FileOp] = None):
        if filter_to and len(filter_to) > 0:
            return [file.rel_path for file in self.files.values() if file.op in filter_to]
        return [file.rel_path for file in self.files.values()]

    def get_etags(self):
        return [file.etag for file in self.files.values()]

    def get_sizes(self):
        return [file.size for file in self.files.values()]


class MyOrg(namedtuple('MyOrg', ['id', 'name', 'myRole'])):
    pass


class ValidationErrorTuple(namedtuple('ValidationErrorTuple', ['code', 'message', 'severity'])):
    pass


class OwnerInputTuple(namedtuple('OwnerInputTuple', ['id', 'type'])):
    pass


# BASE is the name we want to use inside the settings keys
MESSAGE_CATEGORY = CONSTANTS['logCategory']


class DataExchangeAPI(QObject):
    stateChange = pyqtSignal()

    """ Class to handle data exchange between the different components of the system
    """

    def __init__(self, on_login=Callable[[bool], None]):
        super().__init__()
        # Make sure the Borg pattern is initialized
        self.settings = Settings()
        self.log = self.settings.log
        self.myId = None
        self.myName = None
        self.myOrgs = []
        self.initialized = False
        self.on_login = on_login
        self.api = GraphQLAPI(
            apiUrl=CONSTANTS['DE_API_URL'],
            config=GraphQLAPIConfig(**CONSTANTS['DE_API_AUTH'])
        )
        # Tie the state change signal to the state change handler inside self.api
        self.api.stateChange.connect(self.stateChange.emit)
        self.stateChange.connect(self._handle_state_change)

        self.initialized = self.api.access_token is not None
        # Regardless of outcome we should check the token status
        self.api.refresh_token(self._handle_refresh_token)

    def login(self):
        self.myId = None
        self.myName = None
        self.myOrgs = []
        self.initialized = False
        self.api.refresh_token(self._handle_refresh_token, force=True)
        self.stateChange.emit()

    @pyqtSlot()
    def _handle_state_change(self):
        pass

    def _handle_refresh_token(self, task: RefreshTokenTask):
        if task.error:
            self.log('Error refreshing token', Qgis.Critical)
            self.log(task.debug_log(), Qgis.Critical)
            self.initialized = False
            self.on_login(task)
        else:
            self.log('Token refreshed', Qgis.Info)
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
                myOrgs = task.response['data']['profile']['organizations']['items']

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

    def get_remote_project(self, project_id: str, callback: Callable[[RunGQLQueryTask, Dict], None]):
        """ Get the tree and metadata for a remote project

        Args:
            project_id (str): the id of the project to get
        """
        def _parse_remote_project(task: RunGQLQueryTask):
            # We just return the raw response for now and let the RemoteProject handle it
            return callback(task, task.response)

        return self.api.run_query(self._load_query('webRaveProject'), {
            'id': project_id,
            'dsLimit': 50,
            'dsOffset': 0
        }, _parse_remote_project)

    def validate_project(self, xml_str: str, owner_obj: OwnerInputTuple, files: UploadFileList, callback: Callable[[RunGQLQueryTask, Dict], None]):
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

        return self.api.run_query(self._load_query('validateProject'), {
            'xml': xml_str, 'owner': owner_obj,
            'files': files.get_rel_paths()
        },
            _validate_project
        )

    def request_upload_project(self,
                               files: UploadFileList,
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
                # Add the token to the upload digest in place
                files.token = ret_obj['token']

                # Make sure we update the file operations to make sure that
                for file in files.files.values():
                    if file.rel_path in ret_obj['create']:
                        file.op = UploadFile.FileOp.CREATE
                    elif file.rel_path in ret_obj['update']:
                        file.op = UploadFile.FileOp.UPDATE
                    elif file.rel_path in ret_obj['delete']:
                        file.op = UploadFile.FileOp.DELETE

            return callback(task, ret_obj)

        return self.api.run_query(self._load_query('requestUploadProject'), {
            'projectId': project_id,
            'token': project_token,
            'files': files.get_rel_paths(),
            'etags': files.get_etags(),
            'sizes': files.get_sizes(),
            'noDelete': no_delete,
            'owner': owner_obj,
            'tags': tags,
            'visibility': visibility
        }, _request_upload_project)

    def request_upload_project_files_url(self, files: UploadFileList, callback: Callable[[RunGQLQueryTask, Dict], None]):
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
                for f_resp in ret_obj:
                    files.files[f_resp['relPath']].urls = f_resp['urls']

            return callback(task, ret_obj)

        return self.api.run_query(self._load_query('requestUploadProjectFilesUrl'), {
            'files': files.get_rel_paths([UploadFile.FileOp.CREATE, UploadFile.FileOp.UPDATE]),
            'token': files.token
        },
            _request_upload_project_files_url
        )

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

    def get_download_url(self, project_id: str, remote_path: str, callback: Callable[[RunGQLQueryTask, Dict], None]):
        """ Get a signed download URL for a file
        """
        def _get_download_url(task: RunGQLQueryTask):
            ret_obj = None
            if task.response and not task.error:
                ret_obj = task.response['data']['downloadFile']
            return callback(task, ret_obj)

        return self.api.run_query(self._load_query('downloadFile'), {'projectId': project_id, 'filePath': remote_path}, _get_download_url)

    def get_layer_tiles(self, project_id: str, project_type_id: str, rs_xpath: str, callback: Callable[[RunGQLQueryTask, Dict], None]):
        """ Get the tile service metadata for a layer
        """
        def _get_layer_tiles(task: RunGQLQueryTask):
            ret_obj = None
            if task.response and not task.error:
                ret_obj = task.response['data']['getLayerTiles']
            return callback(task, ret_obj)

        return self.api.run_query(self._load_query('getLayerTiles'), {'projectId': project_id, 'projectTypeId': project_type_id, 'rsXPath': rs_xpath}, _get_layer_tiles)

    def get_web_symbology(self, project_type_id: str, name: str, is_raster: bool, callback: Callable[[RunGQLQueryTask, Dict], None]):
        """ Get the web symbology for a layer
        """
        def _get_web_symbology(task: RunGQLQueryTask):
            ret_obj = None
            if task.response and not task.error:
                ret_obj = task.response['data']['getWebSymbology']
            return callback(task, ret_obj)

        return self.api.run_query(self._load_query('getWebSymbology'), {
            'projectTypeId': project_type_id,
            'name': name,
            'isRaster': is_raster
        }, _get_web_symbology)

    def download_file(self, project_id: str, remote_path: str, local_path: str, callback: Callable[[RunGQLQueryTask, Dict], None]):
        """ Download the project file

        Args:
            project_id (str): the id of the project to download
        """
        def _download_file(task: RunGQLQueryTask, ret_obj: Dict):
            if ret_obj and not task.error:
                download_url = ret_obj['downloadUrl']
                try:
                    with open(local_path, 'wb') as f:
                        f.write(requests.get(download_url).content)
                except Exception as e:
                    self.log(f"Error downloading file: {local_path}", Qgis.Critical)
                    self.log(f"Error: {e}", Qgis.Critical)
                    # We don't null out ret_obj here, but we pass the error along if needed
                    # Actually, the original code nulled it out:
                    # ret_obj = None

            return callback(task, ret_obj)

        return self.get_download_url(project_id, remote_path, _download_file)
