from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import re
import secrets
import threading
import time
from typing import Any, Callable
from urllib.parse import urlencode, urlparse, urlunparse

from qgis.core import Qgis, QgsApplication, QgsMessageLog, QgsTask
from qgis.PyQt.QtCore import QObject, QUrl, pyqtSignal
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

# Nonce format enforced by the server-side OAuth callback (see rs-web-monorepo
# docs/oauth-callback-flow.md): base64url charset, 16-128 chars.
NONCE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{16,128}$")


def generate_nonce() -> str:
    """Generate an unguessable nonce keying the server-side OAuth callback.

    The nonce is embedded in the ``redirect_uri`` handed to Auth0 so the parked
    authorization code can be matched back to this client. It must match the
    server-side validation ``^[A-Za-z0-9_-]{16,128}$`` (base64url charset, no
    padding) -- ``secrets.token_urlsafe`` already produces that shape; the check
    below enforces the contract defensively. (``self._generate_random`` is NOT
    suitable here: its charset includes ``.`` and ``~``, which the server rejects.)

    Returns:
        str: a fresh nonce (32 random bytes, base64url-encoded).

    Raises:
        GraphQLAPIError: if the generated nonce fails the server-side regex.
    """
    nonce = secrets.token_urlsafe(32)
    if not NONCE_PATTERN.match(nonce):
        raise GraphQLAPIError(f"Generated nonce does not match the server-side format: {nonce!r}")
    return nonce


def _never_cancelled() -> bool:
    """Default ``cancel_check``: never treats the caller as cancelled."""
    return False


class GraphQLAPIError(Exception):
    """Exception raised for errors in the GraphQLAPI.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message: str = "GraphQLAPI encountered an error") -> None:
        self.message = message
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message


# Kept for backwards compatibility: project_upload_dialog.py previously imported and
# handled this error, but the localhost callback port is no longer used by the OAuth
# flow (the callback now goes to the Data Exchange server and the client polls for
# the parked authorization code). This class is retained so that any external code
# catching it does not break, but it is NEVER raised by the current codebase.
class GraphQLAPIPortError(GraphQLAPIError):
    """Legacy error kept for backwards compatibility — no longer raised.

    The old OAuth flow attempted to bind a localhost port to receive the Auth0
    callback. If that port was blocked, this error was raised. The callback now
    goes to the Data Exchange server (server-side callback with nonce polling),
    so this error is never raised by the current code.

    Attributes:
        port -- the port number that could not be bound (legacy)
    """

    def __init__(self, port: int) -> None:
        self.port = port
        super().__init__(f"Port {port} is unavailable for the authentication callback. [Legacy error — the OAuth flow no longer uses a localhost port.]")

    def __str__(self) -> str:
        return f"GraphQLAPIPortError: {self.message}"


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
                                self.api._refresh_token(force=True, cancel_check=lambda: self.isCanceled())
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
                    self.api.log(
                        f"Full response: {json.dumps(resp_json, indent=4, sort_keys=True)}",
                        Qgis.Critical,
                    )

                    # Use just the user-friendly GraphQL error message(s), not the raw JSON
                    err_msgs = [err["message"] for err in resp_json["errors"]]
                    raise GraphQLAPIError("; ".join(err_msgs))
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
    def __init__(self, domain: str, audience: str, clientId: str, scope: str, port: int | None = None, success_url: str = "") -> None:
        # Now do some checking
        if not domain:
            raise GraphQLAPIError("Domain is required")
        if not clientId:
            raise GraphQLAPIError("clientId is required")
        if not scope:
            raise GraphQLAPIError("scope is required")
        if not audience:
            raise GraphQLAPIError("audience is required")
        if not success_url:
            raise GraphQLAPIError("success_url is required")

        self.domain = domain
        self.clientId = clientId
        self.scope = scope
        self.port = port  # vestigial — no longer used by the OAuth callback flow
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
            self.api._refresh_token(self.force, cancel_check=lambda: self.isCanceled())
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

    def _refresh_token(self, force: bool = False, cancel_check: Callable[[], bool] | None = None) -> GraphQLAPI:
        """Refresh the auth token — opens a browser and polls for the auth code.

        This method blocks the calling thread until the user authenticates in the
        browser or the 5-minute polling deadline passes. When called from a
        QgsTask, the caller should pass ``cancel_check=lambda: self.isCanceled()``
        so the polling loop can exit early if the user cancels the task in QGIS.

        Args:
            force: if True, force a new token even if an existing one is still valid.
            cancel_check: optional callable returning True when the caller has been
                cancelled (e.g. QgsTask.isCanceled()). The polling loop checks this
                on every iteration and raises GraphQLAPIError on cancellation.

        Returns:
            self, with ``self.access_token`` populated.

        Raises:
            GraphQLAPIError: on auth failure, timeout, or cancellation.
        """
        if cancel_check is None:
            cancel_check = _never_cancelled
        self.log(f"Authenticating on GraphQL API: {self.uri}")
        if self._auth_lock.locked():
            self.log("   Authentication already in progress. Waiting for lock...")

        with self._auth_lock:
            if self.token_timeout:
                self.token_timeout.cancel()

            # When forcing a fresh login (e.g. the Reset button), clear the
            # shared in-memory token so the user can sign in as a different
            # Auth0 account.  This must happen before the shared-token check
            # below, otherwise the force flag has no effect.
            if force:
                GraphQLAPI._shared_access_token = None
                GraphQLAPI._shared_token_expires = None
                self.access_token = None

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
            # Unguessable nonce keying the server-side callback. Corporate
            # firewalls/proxies block localhost redirects, so Auth0 now redirects
            # the browser to the Data Exchange server, which parks the
            # authorization code keyed by this nonce; we then poll for it. The
            # code is useless without the PKCE verifier, which never leaves this
            # machine. (Server-side nonce validation: ^[A-Za-z0-9_-]{16,128}$.)
            nonce = generate_nonce()

            # Server-side callback endpoint (replaces the old localhost redirect):
            # <apiUrl>/auth/callback?nonce=<nonce> (self.uri may carry a /staging suffix)
            redirect_url = f"{self.uri.rstrip('/')}/auth/callback?nonce={nonce}"
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

            # Poll the Data Exchange server until the authorization code is
            # parked for our nonce (blocks this background task thread; the Node
            # CLI does exactly the same).
            auth_code = self._poll_for_auth_code(nonce, cancel_check)
            authentication_url = f"https://{self.config.domain}/oauth/token"

            data = {
                "grant_type": "authorization_code",
                "client_id": self.config.clientId,
                "code_verifier": code_verifier,
                "code": auth_code,
                # Must EXACTLY match the redirect_uri used in the authorize
                # request (including the ?nonce=... query parameter) -- Auth0
                # validates this on the token exchange.
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

    def _poll_for_auth_code(self, nonce: str, cancel_check: Callable[[], bool] = lambda: False) -> str:
        """Poll the server-side OAuth callback endpoint for the authorization code.

        The browser is redirected to the Data Exchange server (never localhost, so
        corporate firewalls/proxies cannot break the flow), which parks the code
        in DynamoDB keyed by the nonce. We poll ``<base>/auth/poll/<nonce>`` every
        2 seconds until the code (or an error) shows up, or a 5-minute deadline
        passes. This mirrors the Node CLI's ``GQLApi._pollForAuthCode`` (see
        rs-web-monorepo docs/oauth-callback-flow.md).

        Args:
            nonce: the unguessable nonce embedded in the authorize redirect_uri.
            cancel_check: callable returning True when the caller has been cancelled
                (e.g. QgsTask.isCanceled()). The loop exits early on cancellation.

        Returns:
            the parked authorization code, ready for the token exchange.

        Raises:
            GraphQLAPIError: if the server reports an auth error (e.g. the user
                denied consent), the caller was cancelled, or the 5-minute deadline
                passes before the code appears.
        """
        logger = logging.getLogger(__name__)
        poll_url = f"{self.uri.rstrip('/')}/auth/poll/{nonce}"
        interval = 2  # seconds between polls (matches the Node CLI)
        deadline = time.time() + 5 * 60  # give the user ~5 minutes to log in
        iteration = 0
        self.log(f"Waiting for browser authentication. Polling {poll_url}")

        while time.time() < deadline:
            # Honour QGIS task cancellation so the user can abort a stuck auth
            # attempt instead of waiting the full 5-minute deadline.
            if cancel_check():
                raise GraphQLAPIError("Browser authentication cancelled by user.")

            response = None
            try:
                # 404 means the code is not parked yet; 5xx/network errors are
                # transient -- keep polling in both cases (mirrors the Node CLI).
                response = requests.get(poll_url, timeout=10)
            except requests.RequestException as exc:
                logger.debug("Auth poll request failed; retrying: %s", exc)

            if response is not None:
                status = response.status_code
                if status == 200:
                    try:
                        body = response.json()
                    except ValueError as exc:
                        logger.debug("Auth poll returned a non-JSON body; retrying: %s", exc)
                        body = None
                    if body is not None:
                        if "error" in body:
                            raise GraphQLAPIError(f"Browser authentication failed: {body['error']}")
                        if "code" in body:
                            self.log("Authorization code received. Exchanging for access token...")
                            return body["code"]
                elif status != 404:
                    # 4xx/5xx other than 404 are transient -- keep polling
                    logger.debug("Auth poll returned status %s; retrying", status)

            iteration += 1
            # Don't spam the QGIS message log every 2s -- report progress about once a minute
            if iteration % 30 == 0:
                self.log(f"Still waiting for browser authentication... ({iteration * interval}s elapsed)")
            time.sleep(interval)

        raise GraphQLAPIError("Timed out waiting for browser authentication. Please try again.")

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
