from typing import Dict, Any, Callable
import os
import time
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtCore import QUrl, QUrlQuery
from qgis.PyQt.QtCore import QObject, pyqtSignal, pyqtSlot
from qgis.core import QgsMessageLog, Qgis, QgsTask, QgsApplication
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlencode, urlparse, urlunparse
import json
import threading
import hashlib
import base64
import logging
import requests
from .settings import CONSTANTS
# Disable all the weird terminal noise from urllib3
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("urllib3").propagate = False

CHARSET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~'
MAX_RETRIES = 5

# BASE is the name we want to use inside the settings keys
MESSAGE_CATEGORY = CONSTANTS['logCategory']


class GraphQLAPIException(Exception):
    """Exception raised for errors in the GraphQLAPI.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message="GraphQLAPI encountered an error"):
        self.message = message
        super().__init__(self.message)


class RunGQLQueryTask(QgsTask):
    def __init__(self, api, query, variables):
        super().__init__('RunGQLQueryTask', QgsTask.CanCancel)
        self.api = api
        self.query = query
        self.variables = variables
        self.error = None
        self.response = None

    def debug_log(self) -> str:
        debug_obj = {
            'url': self.api.uri,
            'query': self.query,
            'variables': self.variables,
            'response': self.response
        }
        json_str = json.dumps(debug_obj, indent=4, sort_keys=True)
        # Replace all \n line breaks with a newline character
        json_str = json_str.replace('\\n', '\n                ')
        return json_str

    def run(self, retries=0):
        try:
            headers = {"authorization": "Bearer " +
                       self.api.access_token} if self.api.access_token else {}

            request = requests.post(self.api.uri, json={
                'query': self.query,
                'variables': self.variables
            }, headers=headers, timeout=30)

            if request.status_code == 200:
                resp_json = request.json()
                if 'errors' in resp_json and len(resp_json['errors']) > 0:
                    # Authentication timeout: re-login and retry the query
                    if len(list(filter(lambda err: 'You must be authenticated' in err['message'], resp_json['errors']))) > 0:
                        if retries < MAX_RETRIES:
                            self.log("Authentication timed out. Fetching new token...")
                            try:
                                self.api._refresh_token()
                            except Exception as e:
                                self.log(f"Failed to refresh token: {e}")
                                return  # or handle the error in some other way

                            self.log("   done. Re-trying query...")
                            return self.run(retries=retries+1)
                        else:
                            self.log("Failed to authenticate after multiple attempts.")
                            return  # or handle the error in some other way
                    raise GraphQLAPIException(
                        f"Query failed to run by returning code of {request.status_code}. ERRORS: {json.dumps(resp_json, indent=4, sort_keys=True)}")
                else:
                    self.response = request.json()
                    return True
            else:
                raise GraphQLAPIException(
                    f"Query failed to run by returning code of {request.status_code}. {self.query} {json.dumps(self.variables)}")
        except GraphQLAPIException as e:
            self.error = e
            return False
        except Exception as e:
            self.error = e
            return False


class GraphQLAPIConfig():

    def __init__(self, domain: str, audience: str, clientId: str, scope: str, port: int, success_url: int) -> None:
        # Now do some checking
        if not domain:
            raise GraphQLAPIException("Domain is required")
        if not clientId:
            raise GraphQLAPIException("clientId is required")
        if not scope:
            raise GraphQLAPIException("scope is required")
        if not audience:
            raise GraphQLAPIException("audience is required")
        if not port or port < 1:
            raise GraphQLAPIException("port is required")
        if not success_url:
            raise GraphQLAPIException("success_url is required")

        self.domain = domain
        self.clientId = clientId
        self.scope = scope
        self.port = port
        self.audience = audience
        self.success_url = success_url


class RefreshTokenTask(QgsTask):
    def __init__(self, api):
        super().__init__('RefreshTokenTask', QgsTask.CanCancel)
        self.api = api
        self.success = False
        self.error = None

    def run(self):
        try:
            self.api._refresh_token(True)
            self.success = True
            return True
        except Exception as e:
            self.error = e
            return False


class GraphQLAPI(QObject):

    stateChange = pyqtSignal()

    """This class is a wrapper around the GraphQL API. It handles authentication and provides a 
    simple interface for making queries.

    this is meant to be wrapped for specific APIs. for example, the DE API and Phlux can both use this
    class but they will have different configurations.
    """

    def __init__(self, apiUrl: str, config: GraphQLAPIConfig, dev_headers: Dict[str, str] = None):
        super().__init__()

        self.config = config
        self.dev_headers = dev_headers
        self.access_token = None
        self.token_timeout = None
        self.loading = False

        self.uri = apiUrl

    # Add a destructor to make sure any timeout threads are cleaned up
    def __del__(self):
        self.shutdown()

    def log(self, msg: str, level: Qgis.MessageLevel = Qgis.Info):
        QgsMessageLog.logMessage(msg, MESSAGE_CATEGORY, level=level)

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
        self.log(f"Shutting down GraphQL API: {self.uri}")
        if self.token_timeout:
            self.token_timeout.cancel()

    def refresh_token(self, callback: Callable[[RefreshTokenTask], None] = None):
        """ Refresh the authentication token

        Raises:
            error: _description_

        Returns:
            _type_: _description_
        """
        task = RefreshTokenTask(self)
        task.taskCompleted.connect(lambda: callback(task))
        task.taskTerminated.connect(lambda: callback(task))
        QgsApplication.taskManager().addTask(task)
        return task

    def _refresh_token(self, force: bool = False):
        """ This is the actual code for refreshing the token. It is called by the RefreshTokenTask
        so that it can be run asynchronously

        Raises:
            error: _description_

        Returns:
            _type_: _description_
        """
        self.log(f"Authenticating on GraphQL API: {self.uri}")
        if self.token_timeout:
            self.token_timeout.cancel()

        # On development there's no reason to actually go get a token
        if self.dev_headers and len(self.dev_headers) > 0:
            return self

        if self.access_token and not force:
            self.log("   Token already exists. Not refreshing.")
            return self

        # If this is a user workflow then we need to pop open a web browser
        code_verifier = self._generate_random(128)
        code_challenge = self._generate_challenge(code_verifier)
        state = self._generate_random(32)

        redirect_url = f"http://localhost:{self.config.port}/rscli/"
        login_url = urlparse(f"https://{self.config.domain}/authorize")
        query_params = {
            "client_id": self.config.clientId,
            "response_type": "code",
            "scope": self.config.scope,
            "state": state,
            "audience": self.config.audience,
            "redirect_uri": redirect_url,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        login_url = login_url._replace(query=urlencode(query_params))

        self.loading = True
        self.stateChange.emit()

        # Now open the browser so we can authenticate
        QDesktopServices.openUrl(QUrl(urlunparse(login_url)))

        auth_code = self._wait_for_auth_code()
        authentication_url = f"https://{self.config.domain}/oauth/token"

        data = {
            "grant_type": "authorization_code",
            "client_id": self.config.clientId,
            "code_verifier": code_verifier,
            "code": auth_code,
            "redirect_uri": redirect_url,
        }

        response = requests.post(authentication_url, headers={
            "content-type": "application/x-www-form-urlencoded"}, data=data, timeout=30)
        response.raise_for_status()
        res = response.json()
        self.token_timeout = threading.Timer(
            res["expires_in"] - 20, self._refresh_token)
        self.token_timeout.start()
        self.access_token = res["access_token"]
        self.log("SUCCESSFUL Browser Authentication", Qgis.Success)
        self.loading = False
        self.stateChange.emit()

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

            def __init__(self, config, *args, **kwargs):
                self.config = config
                super().__init__(*args, **kwargs)

            def do_GET(self):
                """ Do all the server stuff here
                """
                url = QUrl(self.path)
                query = QUrlQuery(url.query())
                # Now get the items as a key-value dictionary
                self.server.query_resp = {k: v for k, v in query.queryItems()}
                success = 'code' in self.server.query_resp and 'error' not in self.server.query_resp

                success_html_body = f"""
                    <html>
                        <head>
                            <title>GraphQL API: Authentication successful</title>
                            <script>
                                window.onload = function() {{
                                    window.location.replace('{self.config.success_url}?code=ASDASD778587587JHKLJKHKJH88689');
                                }}
                            </script>
                        </head>
                        <body>
                            <p>GraphQL API: Authentication successful. Redirecting....</p>
                        </body>
                    </html>
                """
                failed_html_body = f"""
                    <html>
                        <head>
                            <title>GraphQL API: Authentication failed</title>
                        </head>
                        <body>
                            <p>GraphQL API: Authentication failed. Please try again.</p>
                            <code>{json.dumps(self.server.query_resp, indent=4, sort_keys=True)}</code>
                        </body>
                    </html>
                """

                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(success_html_body.encode()
                                 if success else failed_html_body.encode())

                # Now shut down the server and return
                self.server.shutdown()

        server = ThreadingHTTPServer(("localhost", self.config.port),
                                     lambda *args, **kwargs: AuthHandler(self.config, *args, **kwargs))
        # Keep the server running until it is manually stopped
        try:
            self.log("Starting server to wait for auth code...")
            server_thread = threading.Thread(target=server.serve_forever)
            server_thread.start()

            start_time = time.time()

            # Loop for up to 10 seconds
            while time.time() - start_time < 10:
                # If the server thread is still running, shut it down
                # self.log(f"Waiting for auth code...")
                if not server_thread.is_alive():
                    server.server_close()
                    break
                time.sleep(1)

            # If the server thread is still running after 10 seconds, shut it down
            if server_thread.is_alive():
                server.shutdown()
                server_thread.join()
            # Regardless of how the server thread ended, close the server
            server.server_close()

        except KeyboardInterrupt:
            pass

        auth_code = None
        if not hasattr(server, "query_resp"):
            raise GraphQLAPIException(
                "Authentication failed with unknown return")
        else:
            query_resp = server.query_resp
            if 'error' in query_resp or 'code' not in query_resp:
                raise GraphQLAPIException(
                    f"Authentication failed: {json.dumps(query_resp, indent=4, sort_keys=True)}")

            auth_code = query_resp['code']

        return auth_code

    def run_query(self, query: str, variables: Dict[str, Any], callback: Callable[[RunGQLQueryTask], None]):
        """ Run a query asynchronously against the GraphQL API

        Args:
            query (_type_): _description_
            variables (_type_): _description_
            callback (function): _description_

        Returns:
            _type_: _description_
        """
        self.loading = True
        self.stateChange.emit()
        task = RunGQLQueryTask(self, query, variables)

        def completion_callback(task):
            self.loading = False
            callback(task)
            self.stateChange.emit()

        # For Async usage
        task.taskCompleted.connect(lambda: completion_callback(task))
        task.taskTerminated.connect(lambda: completion_callback(task))

        QgsApplication.taskManager().addTask(task)
        return task

    def run_query_sync(self, query: str, variables: Dict[str, any]):
        """ Run a query against the GraphQL API synchronously. 

        this WILL block the main thread so use with caution

        Args:
            query (_type_): _description_
            variables (_type_): _description_

        Raises:
            Exception: _description_

        Returns:
            _type_: _description_
        """
        self.loading = True
        self.stateChange.emit()
        task = RunGQLQueryTask(self, query, variables)

        # For Async usage
        response = task.run()
        self.loading = False
        self.stateChange.emit()
        return response
