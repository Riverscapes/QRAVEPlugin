"""Unit tests for the server-side OAuth callback handling in src/classes/GraphQLAPI.py.

The old flow listened on a localhost HTTP server for the Auth0 callback; the new
flow redirects the browser to the Data Exchange server and POLLS for the parked
authorization code (mirroring the Node.js CLI -- see the rs-web-monorepo
``docs/oauth-callback-flow.md`` spec).

These tests run WITHOUT QGIS: the whole ``qgis`` import chain (``qgis.core``,
``qgis.PyQt.QtCore``/``QtGui``/``QtWidgets``/``QtNetwork``) is stubbed in
``sys.modules`` BEFORE ``src.classes.GraphQLAPI`` is imported. The stubs answer
any attribute access with a generic dummy, and provide real-class stand-ins for
the two base classes the source subclasses (``QObject``, ``QgsTask``).

Notes on running:
- ``python3 test/test_graphql_api.py``            -- standalone (unittest main)
- ``python3 -m unittest discover -s test -t test -p test_graphql_api.py -v``
- Running through the ``test`` *package* (``pytest test/test_graphql_api.py``
  or ``python3 -m unittest test.test_graphql_api``) executes ``test/__init__.py``
  first, which does a hard ``import qgis`` -- so those invocations need a real
  QGIS installation (or a ``qgis`` shim on ``sys.path``) before this module's
  stubs are installed.
"""

import os
import re
import sys
import threading
import types
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlparse

# The requests module under test is the same one patched below, so import it
# before any patch is active. It is also needed to build real RequestExceptions.
import requests

# Make `import src...` resolve when this file is executed directly
# (``python3 test/test_graphql_api.py``):
_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_TEST_DIR)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


# ---------------------------------------------------------------------------
# QGIS stubs -- installed in sys.modules BEFORE any source import.
# ---------------------------------------------------------------------------


class _Dummy:
    """Generic stand-in for any QGIS / PyQt object.

    Attribute access, calls, indexing and iteration all succeed and return
    further dummies, so the source module can use these exactly like the real
    objects in every expression the unit tests exercise.
    """

    def __init__(self, *args, **kwargs):
        pass

    def __or__(self, other):
        """Qt enum flags support ``|`` (e.g. ``QgsTask.Flag.CanCancel | QgsTask.Flag.Silent``)."""
        return self

    def __ror__(self, other):
        return self

    def __call__(self, *args, **kwargs):
        return _Dummy()

    def __getattr__(self, name):
        return _Dummy()

    def __getitem__(self, key):
        return _Dummy()

    def __iter__(self):
        return iter(())

    def __bool__(self):
        return False

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        return False


class _DummyMeta(type):
    """Metaclass so dummy *classes* (e.g. ``QgsTask.Flag.Silent``) also resolve
    attribute access to dummies instead of raising AttributeError."""

    def __getattr__(cls, name):
        return _Dummy()


class QObject(_Dummy, metaclass=_DummyMeta):
    """Stand-in base class: ``GraphQLAPI(QObject)`` must be subclassable."""


class QgsTask(_Dummy, metaclass=_DummyMeta):
    """Stand-in base class for the QgsTask subclasses in the module under test.

    Mirrors the REAL QGIS API surface for cancellation: ``isCanceled()`` (US
    spelling, single 'l' — ``isCancelled`` does NOT exist on QgsTask) and
    ``cancel()``. The flag-backed implementation lets tests assert exact
    ``is True`` / ``is False`` return values, so a regression to the wrong
    method spelling fails loudly instead of being masked by ``_Dummy``.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cancelled = False

    def isCanceled(self) -> bool:
        return self._cancelled

    def cancel(self) -> None:
        self._cancelled = True


class _DummyModule(types.ModuleType):
    """Module stub whose attribute access always yields a dummy."""

    def __getattr__(self, name):
        return _Dummy()


_QGIS_MODULE_NAMES = [
    "qgis",
    "qgis.core",
    "qgis.PyQt",
    "qgis.PyQt.QtCore",
    "qgis.PyQt.QtGui",
    "qgis.PyQt.QtWidgets",
    "qgis.PyQt.QtNetwork",
]


def _install_qgis_stubs():
    """Register dummy ``qgis`` modules in ``sys.modules`` (idempotent)."""
    qgis = _DummyModule("qgis")
    qgis.core = _DummyModule("qgis.core")
    qgis.PyQt = _DummyModule("qgis.PyQt")
    qgis.PyQt.QtCore = _DummyModule("qgis.PyQt.QtCore")
    qgis.PyQt.QtGui = _DummyModule("qgis.PyQt.QtGui")
    qgis.PyQt.QtWidgets = _DummyModule("qgis.PyQt.QtWidgets")
    qgis.PyQt.QtNetwork = _DummyModule("qgis.PyQt.QtNetwork")
    # Real classes the source subclasses; everything else resolves to _Dummy.
    qgis.core.QgsTask = QgsTask
    qgis.PyQt.QtCore.QObject = QObject
    qgis.PyQt.QtCore.QgsTask = QgsTask
    sys.modules["qgis"] = qgis
    sys.modules["qgis.core"] = qgis.core
    sys.modules["qgis.PyQt"] = qgis.PyQt
    sys.modules["qgis.PyQt.QtCore"] = qgis.PyQt.QtCore
    sys.modules["qgis.PyQt.QtGui"] = qgis.PyQt.QtGui
    sys.modules["qgis.PyQt.QtWidgets"] = qgis.PyQt.QtWidgets
    sys.modules["qgis.PyQt.QtNetwork"] = qgis.PyQt.QtNetwork


# Remember what (if anything) was there so a full-suite run stays polite:
_saved_qgis_modules = {name: sys.modules.get(name) for name in _QGIS_MODULE_NAMES}
_install_qgis_stubs()


def _restore_qgis_modules():
    for name, mod in _saved_qgis_modules.items():
        if mod is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = mod


unittest.addModuleCleanup(_restore_qgis_modules)

# The module under test. Its full import chain (src/__init__, src.classes.settings,
# src.compat) touches qgis too -- all resolved through the stubs above.
from src.classes.GraphQLAPI import GraphQLAPI, GraphQLAPIError, RefreshTokenTask, generate_nonce  # noqa: I001


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


class _FakeResponse:
    """Minimal stand-in for ``requests.Response``."""

    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def _make_api(uri):
    """Build a GraphQLAPI instance without touching __init__/signal wiring."""
    api = object.__new__(GraphQLAPI)
    api.uri = uri
    api.log = lambda *args, **kwargs: None
    return api


NONCE = "n0nce_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


# ---------------------------------------------------------------------------
# generate_nonce
# ---------------------------------------------------------------------------


class TestGenerateNonce(unittest.TestCase):
    """The nonce must satisfy the server-side format ^[A-Za-z0-9_-]{16,128}$."""

    NONCE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{16,128}$")

    def test_matches_server_side_format(self):
        for _ in range(10):
            self.assertRegex(generate_nonce(), self.NONCE_PATTERN)

    def test_length_within_bounds(self):
        nonce = generate_nonce()
        self.assertGreaterEqual(len(nonce), 16)
        self.assertLessEqual(len(nonce), 128)

    def test_two_calls_differ(self):
        # Two calls differ (43-44 char base64url output from 32 random bytes).
        self.assertNotEqual(generate_nonce(), generate_nonce())


# ---------------------------------------------------------------------------
# _poll_for_auth_code
# ---------------------------------------------------------------------------


class TestPollForAuthCode(unittest.TestCase):
    """The client polls <base>/auth/poll/<nonce> until the code is parked."""

    POLL_URL = f"https://api.data.riverscapes.net/auth/poll/{NONCE}"

    def test_returns_code_on_success(self):
        api = _make_api("https://api.data.riverscapes.net")
        with mock.patch("src.classes.GraphQLAPI.requests.get", return_value=_FakeResponse(200, {"code": "abc"})) as mock_get, mock.patch("src.classes.GraphQLAPI.time.sleep"):
            code = api._poll_for_auth_code(NONCE)
        self.assertEqual(code, "abc")
        mock_get.assert_called_once_with(self.POLL_URL, timeout=10)

    def test_uses_staging_base_url(self):
        api = _make_api("https://api.data.riverscapes.net/staging")
        with mock.patch("src.classes.GraphQLAPI.requests.get", return_value=_FakeResponse(200, {"code": "abc"})) as mock_get, mock.patch("src.classes.GraphQLAPI.time.sleep"):
            code = api._poll_for_auth_code(NONCE)
        self.assertEqual(code, "abc")
        mock_get.assert_called_once_with(f"https://api.data.riverscapes.net/staging/auth/poll/{NONCE}", timeout=10)

    def test_normalizes_trailing_slash(self):
        api = _make_api("https://api.data.riverscapes.net/")
        with mock.patch("src.classes.GraphQLAPI.requests.get", return_value=_FakeResponse(200, {"code": "abc"})) as mock_get, mock.patch("src.classes.GraphQLAPI.time.sleep"):
            code = api._poll_for_auth_code(NONCE)
        self.assertEqual(code, "abc")
        mock_get.assert_called_once_with(self.POLL_URL, timeout=10)

    def test_raises_on_server_reported_error(self):
        api = _make_api("https://api.data.riverscapes.net")
        with mock.patch("src.classes.GraphQLAPI.requests.get", return_value=_FakeResponse(200, {"error": "access_denied"})):
            with self.assertRaises(GraphQLAPIError) as ctx:
                api._poll_for_auth_code(NONCE)
        self.assertIn("Browser authentication failed: access_denied", str(ctx.exception))

    def test_retries_on_404_then_succeeds(self):
        api = _make_api("https://api.data.riverscapes.net")
        responses = [_FakeResponse(404, {"error": "not_found"}), _FakeResponse(200, {"code": "abc"})]
        with mock.patch("src.classes.GraphQLAPI.requests.get", side_effect=responses) as mock_get, mock.patch("src.classes.GraphQLAPI.time.sleep"):
            code = api._poll_for_auth_code(NONCE)
        self.assertEqual(code, "abc")
        self.assertEqual(mock_get.call_count, 2)

    def test_retries_on_network_error_then_succeeds(self):
        api = _make_api("https://api.data.riverscapes.net")
        responses = [requests.RequestException("connection refused"), _FakeResponse(200, {"code": "abc"})]
        with mock.patch("src.classes.GraphQLAPI.requests.get", side_effect=responses) as mock_get, mock.patch("src.classes.GraphQLAPI.time.sleep"):
            code = api._poll_for_auth_code(NONCE)
        self.assertEqual(code, "abc")
        self.assertEqual(mock_get.call_count, 2)

    def test_retries_on_server_error_status(self):
        api = _make_api("https://api.data.riverscapes.net")
        responses = [_FakeResponse(500, {"error": "failed_to_read_auth_state"}), _FakeResponse(200, {"code": "abc"})]
        with mock.patch("src.classes.GraphQLAPI.requests.get", side_effect=responses) as mock_get, mock.patch("src.classes.GraphQLAPI.time.sleep"):
            code = api._poll_for_auth_code(NONCE)
        self.assertEqual(code, "abc")
        self.assertEqual(mock_get.call_count, 2)

    def test_times_out_when_deadline_passes(self):
        api = _make_api("https://api.data.riverscapes.net")
        # First time.time() computes the deadline (1000 -> 1300); the subsequent
        # calls walk the loop past it. No iteration ever yields a code.
        time_sequence = [1000.0, 1000.5, 1000.6, 1500.0]
        not_found = _FakeResponse(404, {"error": "not_found"})
        with mock.patch("src.classes.GraphQLAPI.requests.get", return_value=not_found), mock.patch("src.classes.GraphQLAPI.time.sleep"), mock.patch("src.classes.GraphQLAPI.time.time", side_effect=time_sequence):
            with self.assertRaises(GraphQLAPIError) as ctx:
                api._poll_for_auth_code(NONCE)
        self.assertIn("Timed out waiting for browser authentication. Please try again.", str(ctx.exception))


# ---------------------------------------------------------------------------
# _refresh_token end-to-end (browser flow -> poll -> token exchange)
# ---------------------------------------------------------------------------


class TestRefreshTokenFlow(unittest.TestCase):
    """The redirect_uri must be the server callback (with nonce) and must be
    byte-for-byte identical between the authorize request and the token exchange."""

    def setUp(self):
        GraphQLAPI._shared_access_token = None
        GraphQLAPI._shared_token_expires = None

    def tearDown(self):
        GraphQLAPI._shared_access_token = None
        GraphQLAPI._shared_token_expires = None

    def test_browser_flow_uses_server_callback_and_matching_redirect_uri(self):
        api = _make_api("https://api.data.riverscapes.net")
        api.config = types.SimpleNamespace(
            domain="auth.riverscapes.net",
            clientId="dummy-client",
            scope="openid",
            audience="https://api.riverscapes.net",
            port=4721,
            success_url="https://data.riverscapes.net/login_success",
        )
        api._auth_lock = threading.Lock()
        api.token_timeout = None
        api.dev_headers = None
        api.access_token = None
        api.loading = False
        api.stateChange = _Dummy()
        emit_mock = mock.MagicMock()
        api.open_browser_signal = emit_mock

        expected_redirect_uri = f"https://api.data.riverscapes.net/auth/callback?nonce={NONCE}"
        get_responses = [_FakeResponse(404, {"error": "not_found"}), _FakeResponse(200, {"code": "auth-code-xyz"})]
        token_body = {"access_token": "t0ken", "expires_in": 3600}

        try:
            with (
                mock.patch("src.classes.GraphQLAPI.generate_nonce", return_value=NONCE),
                mock.patch("src.classes.GraphQLAPI.QUrl", side_effect=lambda s: s),
                mock.patch("src.classes.GraphQLAPI.time.sleep"),
                mock.patch("src.classes.GraphQLAPI.requests.get", side_effect=get_responses) as mock_get,
                mock.patch("src.classes.GraphQLAPI.requests.post", return_value=_FakeResponse(200, token_body)) as mock_post,
            ):
                api._refresh_token()
        finally:
            if api.token_timeout:
                api.token_timeout.cancel()

        # Shared in-memory token state was updated as before.
        self.assertEqual(api.access_token, "t0ken")
        self.assertEqual(GraphQLAPI._shared_access_token, "t0ken")

        # Authorize URL: https://auth.riverscapes.net/authorize with the
        # server-side callback redirect_uri (nonce included), never localhost.
        emitted_url = emit_mock.emit.call_args.args[0]
        self.assertNotIn("localhost", emitted_url)
        parsed = urlparse(emitted_url)
        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(parsed.netloc, "auth.riverscapes.net")
        self.assertEqual(parsed.path, "/authorize")
        query = parse_qs(parsed.query)
        self.assertEqual(query["redirect_uri"], [expected_redirect_uri])
        self.assertEqual(query["response_type"], ["code"])
        self.assertEqual(query["code_challenge_method"], ["S256"])
        self.assertIn("code_challenge", query)
        self.assertIn("state", query)

        # Poll <base>/auth/poll/<nonce> first, then succeed.
        self.assertEqual(mock_get.call_args_list[0].args[0], f"https://api.data.riverscapes.net/auth/poll/{NONCE}")
        self.assertEqual(mock_get.call_args_list[0].kwargs["timeout"], 10)
        self.assertEqual(mock_get.call_count, 2)

        # Token exchange: same redirect_uri (with nonce), PKCE verifier, form-encoded.
        post_call = mock_post.call_args
        self.assertEqual(post_call.args[0], "https://auth.riverscapes.net/oauth/token")
        self.assertEqual(post_call.kwargs["headers"], {"content-type": "application/x-www-form-urlencoded"})
        self.assertEqual(post_call.kwargs["timeout"], 60)
        data = post_call.kwargs["data"]
        self.assertEqual(data["grant_type"], "authorization_code")
        self.assertEqual(data["client_id"], "dummy-client")
        self.assertEqual(data["code"], "auth-code-xyz")
        self.assertEqual(len(data["code_verifier"]), 128)
        self.assertEqual(data["redirect_uri"], expected_redirect_uri)


# ---------------------------------------------------------------------------
# Task cancellation wiring (RefreshTokenTask / RunGQLQueryTask -> _refresh_token)
# ---------------------------------------------------------------------------


class TestTaskCancelWiring(unittest.TestCase):
    """RefreshTokenTask must wire a ``cancel_check`` that calls the REAL QGIS
    QgsTask API method ``isCanceled()`` (US spelling). A regression to the
    non-existent ``isCancelled()`` raises AttributeError at runtime in QGIS —
    exactly what the stub's exact ``is True`` / ``is False`` assertions catch."""

    def _make_task_for(self, api):
        return RefreshTokenTask(api)

    def test_cancel_check_tracks_qgstask_cancel_state(self):
        api = _make_api("https://api.data.riverscapes.net")
        task = RefreshTokenTask(api)

        with mock.patch.object(GraphQLAPI, "_refresh_token", return_value=api) as m:
            result = task.run()

        self.assertTrue(result)
        self.assertEqual(m.call_count, 1)
        cancel_check = m.call_args.kwargs["cancel_check"]

        # Fresh task: not cancelled -> must be exactly False (bool, not a dummy)
        self.assertIs(cancel_check(), False)

        # After QGIS cancels the task -> must be exactly True
        task.cancel()
        self.assertIs(cancel_check(), True)

    def test_poll_loop_aborts_on_cancel_check(self):
        """_poll_for_auth_code exits with a clear error when the caller is cancelled."""
        api = _make_api("https://api.data.riverscapes.net")

        def cancel_check() -> bool:
            return True  # caller already cancelled -> poll must abort immediately

        with mock.patch("src.classes.GraphQLAPI.requests.get") as mock_get, mock.patch("src.classes.GraphQLAPI.time.sleep"), mock.patch("src.classes.GraphQLAPI.time.time", side_effect=[1000.0, 1000.5]):
            with self.assertRaises(GraphQLAPIError) as ctx:
                api._poll_for_auth_code(NONCE, cancel_check)
        self.assertIn("cancelled by user", str(ctx.exception))
        # The cancel check fires before any HTTP request is made
        mock_get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
