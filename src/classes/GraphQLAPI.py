from __future__ import annotations

import base64
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import os
import threading
import time
import traceback
from typing import Any, Callable
from urllib.parse import urlencode, urlparse, urlunparse

from qgis.core import Qgis, QgsApplication, QgsMessageLog, QgsTask
from qgis.PyQt.QtCore import QObject, QUrl, QUrlQuery, pyqtSignal
from qgis.PyQt.QtGui import QDesktopServices
import requests

from ..compat import QGSTASK_CAN_CANCEL, QGSTASK_SILENT
from .settings import CONSTANTS

# Disable all the weird terminal noise from urllib3
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("urllib3").propagate = False

CHARSET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
MAX_RETRIES = 5

# BASE is the name we want to use inside the settings keys
MESSAGE_CATEGORY = CONSTANTS["logCategory"]


class GraphQLAPIError(Exception):
    """Exception raised for errors in the GraphQLAPI.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message: str = "GraphQLAPI encountered an error") -> None:
        self.message = message
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"GraphQLAPIError: {self.message}"


class RunGQLQueryTask(QgsTask):
    def __init__(self, api: GraphQLAPI, query: str, variables: dict) -> None:
        super().__init__("RunGQLQueryTask", QGSTASK_CAN_CANCEL | QGSTASK_SILENT)
        self.api = api
        self.query = query
        self.variables = variables
        self.error = None
        self.response = None
        self.success = False

    def debug_log(self) -> str:
        debug_obj = {"url": self.api.uri, "query": self.query, "error": str(self.error), "variables": self.variables, "response": self.response}
        json_str = json.dumps(debug_obj, indent=4, sort_keys=True)
        # Replace all \n line breaks with a newline character
        json_str = json_str.replace("\\n", "\n                ")
        return json_str

    def run(self, retries: int = 0) -> bool | None:
        try:
            headers = {"authorization": "Bearer " + self.api.access_token} if self.api.access_token else {}

            request = requests.post(self.api.uri, json={"query": self.query, "variables": self.variables}, headers=headers, timeout=30)

            if request.status_code == 200:
                resp_json = request.json()
                if "errors" in resp_json and len(resp_json["errors"]) > 0:
                    # Authentication timeout: re-login and retry the query
                    if len(list(filter(lambda err: "You must be authenticated" in err["message"], resp_json["errors"]))) > 0:
                        if retries < MAX_RETRIES:
                            self.api.log("Authentication timed out. Fetching new token...")
                            try:
                                self.api._refresh_token(force=True)
                            except Exception as e:
                                self.api.log(f"Failed to refresh token: {e}")
                                return  # or handle the error in some other way

                            self.api.log("   done. Re-trying query...")
                            return self.run(retries=retries + 1)
                        else:
                            self.api.log("Failed to authenticate after multiple attempts.")
                            return  # or handle the error in some other way

                    # Log the error to the console
                    for err in resp_json["errors"]:
                        self.api.log(f"GraphQL Error: {err['message']}", Qgis.Critical)

                    raise GraphQLAPIError(f"Query failed to run by returning code of {request.status_code}. ERRORS: {json.dumps(resp_json, indent=4, sort_keys=True)}")
                else:
                    self.response = request.json()
                    self.success = True
                    return True
            else:
                self.api.log(f"Query failed with code {request.status_code}: {self.query}", Qgis.Critical)
                raise GraphQLAPIError(f"Query failed to run by returning code of {request.status_code}. {self.query} {json.dumps(self.variables)}")
        except GraphQLAPIError as e:
            self.api.log(f"GraphQLAPIError: {e}", Qgis.Critical)
            self.error = e
            return False
        except Exception as e:
            self.api.log(f"GraphQL Unknown Error: {e}", Qgis.Critical)
            self.error = e
            return False


class FetchJsonTask(QgsTask):
    """Background task that GETs a URL and parses the response as JSON.

    The *callback* is invoked on the **main thread** inside ``finished()``
    with the task itself as the sole argument, so callers can inspect
    ``task.success``, ``task.result``, and ``task.error``.
    """

    def __init__(self, url: str, callback: Callable[[FetchJsonTask], None]) -> None:
        super().__init__("FetchJsonTask", QGSTASK_CAN_CANCEL | QGSTASK_SILENT)
        self.url = url
        self._callback = callback
        self.result: dict | None = None
        self.error: Exception | None = None
        self.success = False

    def run(self) -> bool:
        try:
            response = requests.get(self.url, timeout=10)
            if response.status_code == 200:
                self.result = response.json()
                self.success = True
                return True
            self.error = ValueError(f"HTTP {response.status_code} from {self.url}")
            return False
        except Exception as exc:
            self.error = exc
            return False

    def finished(self, result: bool) -> None:
        self._callback(self)


class GraphQLAPIConfig:
    def __init__(self, domain: str, audience: str, clientId: str, scope: str, port: int, success_url: str) -> None:
        # Now do some checking
        if not domain:
            raise GraphQLAPIError("Domain is required")
        if not clientId:
            raise GraphQLAPIError("clientId is required")
        if not scope:
            raise GraphQLAPIError("scope is required")
        if not audience:
            raise GraphQLAPIError("audience is required")
        if not port or port < 1:
            raise GraphQLAPIError("port is required")
        if not success_url:
            raise GraphQLAPIError("success_url is required")

        self.domain = domain
        self.clientId = clientId
        self.scope = scope
        self.port = port
        self.audience = audience
        self.success_url = success_url


class RefreshTokenTask(QgsTask):
    def __init__(self, api: GraphQLAPI, force: bool = False) -> None:
        super().__init__("RefreshTokenTask", QGSTASK_CAN_CANCEL | QGSTASK_SILENT)
        self.api = api
        self.force = force
        self.success = False
        self.error = None

    def debug_log(self) -> str:
        debug_obj = {"url": self.api.uri, "error": str(self.error)}
        json_str = json.dumps(debug_obj, indent=4, sort_keys=True)
        # Replace all \n line breaks with a newline character
        json_str = json_str.replace("\\n", "\n                ")
        return json_str

    def run(self) -> bool:
        try:
            self.api._refresh_token(self.force)
            self.success = True
            return True
        except Exception as e:
            self.error = e
            return False


class GraphQLAPI(QObject):
    stateChange = pyqtSignal()
    # Signal emitted (always on the main thread) to open a browser URL.
    # Connecting to QDesktopServices.openUrl in __init__ keeps all GUI calls
    # off the background auth thread.
    open_browser_signal = pyqtSignal(QUrl)
    # Shared access token and expiration time
    _shared_access_token = None
    _shared_token_expires = None
    _shared_auth_lock = threading.Lock()

    """This class is a wrapper around the GraphQL API. It handles authentication and provides a
    simple interface for making queries.

    this is meant to be wrapped for specific APIs. for example, the DE API and Phlux can both use this
    class but they will have different configurations.
    """

    def __init__(self, apiUrl: str, config: GraphQLAPIConfig, dev_headers: dict[str, str] | None = None):
        super().__init__()

        self.config = config
        self.dev_headers = dev_headers
        self.access_token = None
        self.token_timeout = None
        self.loading = False

        self.uri = apiUrl
        # Cross-thread browser open: emit a queued signal so the GUI call
        # always executes on the main thread, never from RefreshTokenTask.
        self.open_browser_signal.connect(lambda url: QDesktopServices.openUrl(url))
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
        return self._base64_url(hashlib.sha256(code.encode("utf-8")).digest())

    def _base64_url(self, string: bytes) -> str:
        """Convert a string to a base64url string

        Args:
            string (bytes): this is the string to convert

        Returns:
            str: the base64url string
        """
        return base64.urlsafe_b64encode(string).decode("utf-8").replace("=", "").replace("+", "-").replace("/", "_")

    def _generate_random(self, size: int) -> str:
        """Generate a random string of a given size

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
        return "".join(state)

    def shutdown(self) -> None:
        """_summary_"""
        self.log(f"Shutting down GraphQL API: {self.uri}")
        if self.token_timeout:
            self.token_timeout.cancel()

    def refresh_token(self, callback: Callable[[RefreshTokenTask], None] | None = None, force=False):
        """Refresh the authentication token

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

    def _refresh_token(self, force: bool = False) -> GraphQLAPI:
        """This is the actual code for refreshing the token. It is called by the RefreshTokenTask
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

            # Open the browser from the main thread via a queued signal.
            auth_url = QUrl(urlunparse(login_url))
            self.open_browser_signal.emit(auth_url)

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

    def _wait_for_auth_code(self) -> str:
        """Wait for the auth code to come back from the server using a simple HTTP server

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
                """Do all the server stuff here"""
                url = QUrl(self.path)
                query = QUrlQuery(url.query())
                # Now get the items as a key-value dictionary
                self.server.query_resp = {k: v for k, v in query.queryItems()}
                success = "code" in self.server.query_resp and "error" not in self.server.query_resp

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
                    self.logger("Connection Closed. Killing the server", Qgis.Warning)
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
            raise GraphQLAPIError("Authentication failed with unknown return")
        else:
            query_resp = server.query_resp
            if "error" in query_resp or "code" not in query_resp:
                raise GraphQLAPIError(f"Authentication failed: {json.dumps(query_resp, indent=4, sort_keys=True)}")

            auth_code = query_resp["code"]

        return auth_code

    def run_query(self, query: str, variables: dict[str, Any], callback: Callable[[RunGQLQueryTask], None]) -> RunGQLQueryTask:
        """Run a query asynchronously against the GraphQL API

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
