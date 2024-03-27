from typing import Dict
import os
import time
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtCore import QUrl, QUrlQuery
from qgis.core import QgsMessageLog, Qgis, QgsTask
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlencode, urlparse, urlunparse
import json
import threading
import hashlib
import base64
import logging
import requests

# Disable all the weird terminal noise from urllib3
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("urllib3").propagate = False

CHARSET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~'


class GraphQLAPIException(Exception):
    """Exception raised for errors in the GraphQLAPI.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message="GraphQLAPI encountered an error"):
        self.message = message
        super().__init__(self.message)


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


class GraphQLAPI():
    """This class is a wrapper around the GraphQL API. It handles authentication and provides a 
    simple interface for making queries.

    this is meant to be wrapped for specific APIs. for example, the DE API and Phlux can both use this
    class but they will have different configurations.
    """

    def __init__(self, apiUrl: str, config: GraphQLAPIConfig, dev_headers: Dict[str, str] = None):
        self.config = config
        self.dev_headers = dev_headers
        self.access_token = None
        self.token_timeout = None

        self.uri = apiUrl

    # Add a destructor to make sure any timeout threads are cleaned up
    def __del__(self):
        self.shutdown()

    def log(self, msg: str, level: Qgis.MessageLevel = Qgis.Info):
        QgsMessageLog.logMessage(msg, 'QRAVE', level=level)

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

    def refresh_token(self, force: bool = False):
        """_summary_

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
            res["expires_in"] - 20, self.refresh_token)
        self.token_timeout.start()
        self.access_token = res["access_token"]
        self.log("SUCCESSFUL Browser Authentication")

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
                self.wfile.write(success_html_body.encode() if success else failed_html_body.encode())

                # Now shut down the server and return
                self.server.shutdown()

        server = ThreadingHTTPServer(("localhost", self.config.port), lambda *args, **kwargs: AuthHandler(self.config, *args, **kwargs))
        # Keep the server running until it is manually stopped
        try:
            self.log("Starting server to wait for auth code...")
            server_thread = threading.Thread(target=server.serve_forever)
            server_thread.start()

            start_time = time.time()

            # Loop for up to 10 seconds
            while time.time() - start_time < 10:
                # If the server thread is still running, shut it down
                self.log(f"Waiting for auth code...")
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
            raise GraphQLAPIException("Authentication failed with unknown return")
        else:
            query_resp = server.query_resp
            if 'error' in query_resp or 'code' not in query_resp:
                raise GraphQLAPIException(f"Authentication failed: {json.dumps(query_resp, indent=4, sort_keys=True)}")

            auth_code = query_resp['code']

        self.log("   done." + auth_code)
        return auth_code

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
        

        class NetworkRequestTask(QgsTask):
            def __init__(self, uri, query, variables, headers):
                super().__init__('Network request', QgsTask.CanCancel)
                self.uri = uri
                self.query = query
                self.variables = variables
                self.headers = headers

            def run(self):
                request = requests.post(self.uri, json={
                    'query': self.query,
                    'variables': self.variables
                }, headers=self.headers, timeout=30)
                # Handle the response here
                # ...
                return True

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
                raise GraphQLAPIException(f"Query failed to run by returning code of {request.status_code}. ERRORS: {json.dumps(resp_json, indent=4, sort_keys=True)}")
            else:
                # self.last_pass = True
                # self.retry = 0
                return request.json()
        else:
            raise GraphQLAPIException(f"Query failed to run by returning code of {request.status_code}. {query} {json.dumps(variables)}")
