from typing import Dict, Any, Callable
import os
import time
import traceback
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

    def __str__(self):
        return f"GraphQLAPIException: {self.message}"


class RunGQLQueryTask(QgsTask):
    def __init__(self, api, query, variables):
        super().__init__('RunGQLQueryTask', QgsTask.CanCancel)
        self.api = api
        self.query = query
        self.variables = variables
        self.error = None
        self.response = None
        self.success = False

    def debug_log(self) -> str:
        debug_obj = {
            'url': self.api.uri,
            'query': self.query,
            'error': str(self.error),
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
                            self.api.log("Authentication timed out. Fetching new token...")
                            try:
                                self.api._refresh_token(force=True)
                            except Exception as e:
                                self.api.log(f"Failed to refresh token: {e}")
                                return  # or handle the error in some other way

                            self.api.log("   done. Re-trying query...")
                            return self.run(retries=retries+1)
                        else:
                            self.api.log("Failed to authenticate after multiple attempts.")
                            return  # or handle the error in some other way
                    
                    # Log the error to the console
                    for err in resp_json['errors']:
                        self.api.log(f"GraphQL Error: {err['message']}", Qgis.Critical)
                        
                    raise GraphQLAPIException(
                        f"Query failed to run by returning code of {request.status_code}. ERRORS: {json.dumps(resp_json, indent=4, sort_keys=True)}")
                else:
                    self.response = request.json()
                    self.success = True
                    return True
            else:
                self.api.log(f"Query failed with code {request.status_code}: {self.query}", Qgis.Critical)
                raise GraphQLAPIException(
                    f"Query failed to run by returning code of {request.status_code}. {self.query} {json.dumps(self.variables)}")
        except GraphQLAPIException as e:
            self.api.log(f"GraphQLAPIException: {e}", Qgis.Critical)
            self.error = e
            return False
        except Exception as e:
            self.api.log(f"GraphQL Unknown Error: {e}", Qgis.Critical)
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
    def __init__(self, api, force=False):
        super().__init__('RefreshTokenTask', QgsTask.CanCancel)
        self.api = api
        self.force = force
        self.success = False
        self.error = None

    def debug_log(self) -> str:
        debug_obj = {
            'url': self.api.uri,
            'error': str(self.error)
        }
        json_str = json.dumps(debug_obj, indent=4, sort_keys=True)
        # Replace all \n line breaks with a newline character
        json_str = json_str.replace('\\n', '\n                ')
        return json_str

    def run(self):
        try:
            self.api._refresh_token(self.force)
            self.success = True
            return True
        except Exception as e:
            self.error = e
            return False


class GraphQLAPI(QObject):

    stateChange = pyqtSignal()
    # Shared access token and expiration time
    _shared_access_token = None
    _shared_token_expires = None
    _shared_auth_lock = threading.Lock()

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
        # We use a class-level lock to prevent multiple instances from authenticating at once
        self._auth_lock = GraphQLAPI._shared_auth_lock
        
        if GraphQLAPI._shared_access_token and GraphQLAPI._shared_token_expires:
            if float(GraphQLAPI._shared_token_expires) > time.time() + 300:
                self.access_token = GraphQLAPI._shared_access_token
                expires_in = float(GraphQLAPI._shared_token_expires) - time.time()
                self.log(f"   Using shared in-memory token (expires in {int(expires_in)}s)")
                return


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

    def refresh_token(self, callback: Callable[[RefreshTokenTask], None] = None, force=False):
        """ Refresh the authentication token

        Raises:
            error: _description_

        Returns:
            _type_: _description_
        """
        task = RefreshTokenTask(self, force=force)
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
        if self._auth_lock.locked():
            self.log("   Authentication already in progress. Waiting for lock...")
        
        with self._auth_lock:
            if self.token_timeout:
                self.token_timeout.cancel()

            # On development there's no reason to actually go get a token
            if self.dev_headers and len(self.dev_headers) > 0:
                return self

            # Check again inside the lock if someone else already fetched a token
            if GraphQLAPI._shared_access_token and GraphQLAPI._shared_token_expires:
                if float(GraphQLAPI._shared_token_expires) > time.time() + 300:
                    self.access_token = GraphQLAPI._shared_access_token
                    self.log("   Token was fetched by another process. Using it.")
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
            auth_url = QUrl(urlunparse(login_url))
            # self.log(f"Opening browser for authentication: {auth_url}", Qgis.Info)
            QDesktopServices.openUrl(auth_url)

            auth_code = self._wait_for_auth_code()
            authentication_url = f"https://{self.config.domain}/oauth/token"

            data = {
                "grant_type": "authorization_code",
                "client_id": self.config.clientId,
                "code_verifier": code_verifier,
                "code": auth_code,
                "redirect_uri": redirect_url,
            }

            response = requests.post(authentication_url, headers={"content-type": "application/x-www-form-urlencoded"}, data=data, timeout=60)
            response.raise_for_status()
            res = response.json()
            
            self.access_token = res["access_token"]
            expires_at = time.time() + res["expires_in"]
            
            # Update shared state
            GraphQLAPI._shared_access_token = self.access_token
            GraphQLAPI._shared_token_expires = expires_at
            # Set up a timer to refresh the token 60 seconds before it expires
            self.token_timeout = threading.Timer(res["expires_in"] - 60, self._refresh_token)
            self.token_timeout.daemon = True
            self.token_timeout.start()
            
            self.log("SUCCESSFUL Browser Authentication", Qgis.Success)
            self.loading = False
            self.stateChange.emit()
            return self

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

            def __init__(self, config, logger, *args, **kwargs):
                self.config = config
                self.logger = logger
                super().__init__(*args, **kwargs)

            def log_message(self, format, *args):
                """Log an arbitrary message.

                This is used by all other logging functions.  Override
                it if you have specific logging wishes.

                The first argument, FORMAT, is a format string for the
                message to be logged.  If the format string contains
                any % escapes requiring parameters, they should be
                specified as subsequent arguments (it's just like
                printf!).

                The client ip and current date/time are prefixed to
                every message.

                Unicode control characters are replaced with escaped hex
                before writing the output to stderr.

                """
                message = format % args
                self.logger(f"{self.address_string()} - - [{self.log_date_time_string()}] {message}", Qgis.Info)

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

                # Make sure the connection is still open
                if not self.wfile.closed:
                    try:
                        self.send_response(200)
                        self.send_header("Content-type", "text/html")
                        self.end_headers()
                        if success:
                            # self.logger(f"AUTH     SUCCESS: {self.path}", Qgis.Info)
                            self.wfile.write(success_html_body.encode())
                        else:
                            # self.logger(f"AUTH     FAILED: {self.path}", Qgis.Warning)
                            self.wfile.write(failed_html_body.encode())

                    except Exception as e:
                        self.logger(f"LOGIN ERROR: {e}", Qgis.Warning)
                        # Drop a stacktrace too
                        self.logger(f"LOGIN ERROR STACKTRACE: {traceback.format_exc()}", Qgis.Warning)
                else:
                    self.logger(f"Connection Closed. Killing the server", Qgis.Warning)
                # Now regardless of the result shut down the server and return
                try:
                    self.server.shutdown()
                    self.server.server_close()
                except Exception as e:
                    self.logger(f"Failed to shut down server: {e}", Qgis.Warning)

        server = ThreadingHTTPServer(("localhost", self.config.port), lambda *args, **kwargs: AuthHandler(self.config, self.log, *args, **kwargs))
        # Keep the server running until it is manually stopped
        try:
            self.log("Starting server to wait for auth code...")
            server_thread = threading.Thread(target=server.serve_forever)
            server_thread.start()

            start_time = time.time()

            # Loop for up to 120 seconds
            counter = 0
            while time.time() - start_time < 120:
                # If the server thread is still running, shut it down
                # self.log(f"Waiting for auth code...")
                if not server_thread.is_alive():
                    break
                counter += 1
                self.log(f"Waiting for auth code... {counter}", Qgis.Info)
                time.sleep(2)

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
