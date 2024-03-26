from typing import Dict, List, Generator, Tuple
import os
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtCore import QUrl
from qgis.core import QgsMessageLog, Qgis
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlencode, urlparse, urlunparse
import json
import threading
import hashlib
import base64
import logging
from .borg import Borg
from .settings import CONSTANTS
import requests

# Disable all the weird terminal noise from urllib3
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("urllib3").propagate = False

CHARSET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~'


class RiverscapesAPIException(Exception):
    """Exception raised for errors in the RiverscapesAPI.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message="RiverscapesAPI encountered an error"):
        self.message = message
        super().__init__(self.message)


class RiverscapesAPI(Borg):
    """This class is a wrapper around the Riverscapes API. It handles authentication and provides a 
    simple interface for making queries.

    If you specify a secretId and clientId then this class will use machine authentication. This is 
    appropriate for development and administration tasks. Otherwise it will use a browser-based 
    authentication workflow which is appropriate for end-users.
    """

    def __init__(self, machine_auth: Dict[str, str] = None, dev_headers: Dict[str, str] = None):
        self.machine_auth = machine_auth
        self.dev_headers = dev_headers
        self.access_token = None
        self.token_timeout = None

        self.uri = CONSTANTS['apiUrl']

    def log(self, msg: str, level: Qgis.MessageLevel = Qgis.Info):
        QgsMessageLog.logMessage(msg, 'QRAVE', level=level)

    def __enter__(self) -> 'RiverscapesAPI':
        """ Allows us to use this class as a context manager
        """
        self.refresh_token()
        return self

    def __exit__(self, _type, _value, _traceback):
        """Behaviour on close when using the "with RiverscapesAPI():" Syntax
        """
        # Make sure to shut down the token poll event so the process can exit normally
        self.shutdown()

    def _generate_challenge(self, code: str) -> str:
        return self._base64_url(hashlib.sha256(code.encode('utf-8')).digest())

    def _generate_state(self, length: int) -> str:
        result = ''
        i = length
        chars = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        while i > 0:
            result += chars[int(round(os.urandom(1)[0] * (len(chars) - 1)))]
            i -= 1
        return result

    def _base64_url(self, string: bytes) -> str:
        """ Convert a string to a base64url string

        Args:
            string (bytes): this is the string to convert

        Returns:
            str: the base64url string
        """
        return base64.urlsafe_b64encode(string).decode('utf-8').replace('=', '').replace('+', '-').replace('/', '_')

    def _generate_random(self, size: int) -> str:
        """ Generate a random string of a given size

        Args:
            size (int): the size of the string to generate

        Returns:
            str: the random string
        """
        buffer = os.urandom(size)
        state = []
        for b in buffer:
            index = b % len(CHARSET)
            state.append(CHARSET[index])
        return ''.join(state)

    def shutdown(self):
        """_summary_
        """
        self.log("Shutting down Riverscapes API")
        if self.token_timeout:
            self.token_timeout.cancel()

    def refresh_token(self, force: bool = False):
        """_summary_

        Raises:
            error: _description_

        Returns:
            _type_: _description_
        """
        self.log(f"Authenticating on Riverscapes API: {self.uri}")
        if self.token_timeout:
            self.token_timeout.cancel()

        # On development there's no reason to actually go get a token
        if self.dev_headers and len(self.dev_headers) > 0:
            return self

        if self.access_token and not force:
            self.log("   Token already exists. Not refreshing.")
            return self

        # Step 1: Determine if we're machine code or user auth
        # If it's machine then we can fetch tokens much easier:
        if self.machine_auth:
            raise RiverscapesAPIException("Machine authentication not yet implemented")

        # If this is a user workflow then we need to pop open a web browser
        else:
            code_verifier = self._generate_random(128)
            code_challenge = self._generate_challenge(code_verifier)
            state = self._generate_random(32)

            redirect_url = f"http://localhost:{CONSTANTS['apiAuth']['port']}/rscli/"
            login_url = urlparse(f"https://{CONSTANTS['apiAuth']['domain']}/authorize")
            query_params = {
                "client_id": CONSTANTS['apiAuth']["clientId"],
                "response_type": "code",
                "scope": CONSTANTS['apiAuth']['scope'],
                "state": state,
                "audience": "https://api.riverscapes.net",
                "redirect_uri": redirect_url,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            }
            login_url = login_url._replace(query=urlencode(query_params))
            QDesktopServices.openUrl(QUrl(urlunparse(login_url)))

            auth_code = self._wait_for_auth_code()
            authentication_url = f"https://{CONSTANTS['apiAuth']['domain']}/oauth/token"

            data = {
                "grant_type": "authorization_code",
                "client_id": CONSTANTS['apiAuth']["clientId"],
                "code_verifier": code_verifier,
                "code": auth_code,
                "redirect_uri": redirect_url,
            }

            response = requests.post(authentication_url, headers={
                                     "content-type": "application/x-www-form-urlencoded"}, data=data, timeout=30)
            response.raise_for_status()
            res = response.json()
            self.token_timeout = threading.Timer(
                res["expires_in"] - 20, self.refresh_token)
            self.token_timeout.start()
            self.access_token = res["access_token"]
            self.log.info("SUCCESSFUL Browser Authentication")

    def _wait_for_auth_code(self):
        """ Wait for the auth code to come back from the server using a simple HTTP server

        Raises:
            Exception: _description_

        Returns:
            _type_: _description_
        """
        class AuthHandler(BaseHTTPRequestHandler):
            """_summary_

            Args:
                BaseHTTPRequestHandler (_type_): _description_
            """

            def stop(self):
                """Stop the server
                """
                self.server.shutdown()

            def do_GET(self):
                """ Do all the server stuff here
                """
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(
                    b"<html><head><title>Riverscapes API: Authentication successful</title></head>")
                self.wfile.write(
                    b"<body><p>Riverscapes API: Authentication successful. You can now close this window.</p></body></html>")
                query = urlparse(self.path).query
                if "=" in query and "code" in query:
                    self.server.auth_code = dict(x.split("=")
                                                 for x in query.split("&"))["code"]
                    # Now shut down the server and return
                    self.stop()

        server = ThreadingHTTPServer(("localhost", CONSTANTS['apiAuth']['port']), AuthHandler)
        # Keep the server running until it is manually stopped
        try:
            print("Starting server to wait for auth, use <Ctrl-C> to stop")
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        if not hasattr(server, "auth_code"):
            raise RiverscapesAPIException("Authentication failed")
        else:
            auth_code = server.auth_code if hasattr(
                server, "auth_code") else None
        return auth_code

    def load_query(self, query_name: str) -> str:
        """ Load a query file from the file system. 

        Args:
            queryName (str): _description_

        Returns:
            str: _description_
        """
        with open(os.path.join(os.path.dirname(__file__), '..', '..', 'graphql', 'queries', f'{query_name}.graphql'), 'r', encoding='utf-8') as queryFile:
            return queryFile.read()

    def load_mutation(self, mutation_name: str) -> str:
        """ Load a mutation file from the file system.

        Args:
            mutationName (str): _description_

        Returns:
            str: _description_
        """
        with open(os.path.join(os.path.dirname(__file__), '..', '..', 'graphql', 'mutations', f'{mutation_name}.graphql'), 'r', encoding='utf-8') as queryFile:
            return queryFile.read()

    def get_project(self, project_id: str):
        """_summary_

        Args:
            project_id (str): _description_

        Returns:
            _type_: _description_
        """
        qry = self.load_query('getProject')
        results = self.run_query(qry, {"id": project_id})
        return results['data']['getProject']

    def get_project_files(self, project_id: str) -> List[Dict[str, any]]:
        """ This returns the file listing with everything you need to download project files


        Args:
            project_id (str): _description_

        Returns:
            _type_: _description_
        """
        qry = self.load_query('projectFiles')
        results = self.run_query(qry, {"projectId": project_id})
        return results['data']['project']['files']

    def run_query(self, query, variables):
        """ A simple function to use requests.post to make the API call. Note the json= section.

        Args:
            query (_type_): _description_
            variables (_type_): _description_

        Raises:
            Exception: _description_

        Returns:
            _type_: _description_
        """
        headers = {"authorization": "Bearer " +
                   self.access_token} if self.access_token else {}
        request = requests.post(self.uri, json={
            'query': query,
            'variables': variables
        }, headers=headers, timeout=30)

        if request.status_code == 200:
            resp_json = request.json()
            if 'errors' in resp_json and len(resp_json['errors']) > 0:
                # Authentication timeout: re-login and retry the query
                if len(list(filter(lambda err: 'You must be authenticated' in err['message'], resp_json['errors']))) > 0:
                    self.log("Authentication timed out. Fetching new token...")
                    self.refresh_token()
                    self.log("   done. Re-trying query...")
                    return self.run_query(query, variables)
                raise RiverscapesAPIException(f"Query failed to run by returning code of {request.status_code}. ERRORS: {json.dumps(resp_json, indent=4, sort_keys=True)}")
            else:
                # self.last_pass = True
                # self.retry = 0
                return request.json()
        else:
            raise RiverscapesAPIException(f"Query failed to run by returning code of {request.status_code}. {query} {json.dumps(variables)}")

    def download_files(self, project_id: str, download_dir: str, re_filter: List[str] = None, force=False):
        """ From a project id get all relevant files and download them

        Args:
            project_id (_type_): _description_
            local_path (_type_): _description_
            force (bool, optional): _description_. Defaults to False.
        """

        # Fetch the project files from the API
        file_results = self.get_project_files(project_id)

        # Now filter the list of files to anything that remains after the regex filter
        filtered_files = []
        for file in file_results:
            if not 'localPath' in file:
                self.log.warning('File has no localPath. Skipping')
                continue
            # now filter the
            if re_filter is not None and len(re_filter) > 0:
                if not any([re.compile(x).match(file['localPath'], re.IGNORECASE) for x in re_filter]):
                    continue
            filtered_files.append(file)

        if len(filtered_files) == 0:
            self.log.warning(
                f"No files found for project {project_id} with the given filters: {re_filter}")
            return

        for file in filtered_files:
            local_file_path = os.path.join(download_dir, file['localPath'])
            self.download_file(file, local_file_path, force)

    def upload_file(self):
        pass
