"""Unit tests for ``src/classes/util.requestDownload`` atomic-write behaviour.

The downloader writes to a temp file in the same directory and then moves it
into place with ``os.replace``, so a failed/interrupted download can never
leave the destination file truncated or empty. This matters most for
``resources/index.json``: NetSync reads it back at every startup, and a
non-atomic ``"wb"`` write plus an interruption produced a JSONDecodeError
crash (previously reported as "Expecting value: line 1 column 1 (char 0)").

These tests run WITHOUT QGIS: the ``qgis`` import chain is stubbed in
``sys.modules`` before ``src.classes.util`` is imported (same pattern as
``test_graphql_api.py``).

Run standalone: ``python3 test/test_request_download.py``
"""

import os
import sys
import types
import unittest
from unittest import mock

import requests

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_TEST_DIR)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


# ---------------------------------------------------------------------------
# QGIS stubs
# ---------------------------------------------------------------------------


class _Dummy:
    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return _Dummy()

    def __getattr__(self, name):
        return _Dummy()

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        return False


class _DummyMeta(type):
    def __getattr__(cls, name):
        return _Dummy()


class _DummyModule(types.ModuleType):
    def __getattr__(self, name):
        return _Dummy()


def _install_qgis_stubs():
    qgis = _DummyModule("qgis")
    qgis.core = _DummyModule("qgis.core")
    qgis.PyQt = _DummyModule("qgis.PyQt")
    qgis.PyQt.QtCore = _DummyModule("qgis.PyQt.QtCore")
    sys.modules["qgis"] = qgis
    sys.modules["qgis.core"] = qgis.core
    sys.modules["qgis.PyQt"] = qgis.PyQt
    sys.modules["qgis.PyQt.QtCore"] = qgis.PyQt.QtCore


_saved = {name: sys.modules.get(name) for name in ["qgis", "qgis.core", "qgis.PyQt", "qgis.PyQt.QtCore"]}
_install_qgis_stubs()


def _restore():
    for name, mod in _saved.items():
        if mod is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = mod


unittest.addModuleCleanup(_restore)

# pytest caveat: an earlier-collected test module (test_remote_project.py)
# permanently installs a stub of ``src.classes.settings`` in ``sys.modules``
# whose CONSTANTS dict lacks ``logCategory``. Drop it (and any cached
# ``util``) so the real modules load here; their imports only need the
# qgis stubs above. Standalone runs are unaffected (nothing polluted yet).
for _name in ("src.classes.settings", "src.classes.util"):
    sys.modules.pop(_name, None)

from src.classes.util import requestDownload


class _FakeResponse:
    """Minimal stand-in for ``requests.Response``."""

    def __init__(self, status_code, content: bytes):
        self.status_code = status_code
        self.content = content

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def _md5(content: bytes) -> str:
    import hashlib

    return hashlib.md5(content, usedforsecurity=False).hexdigest() if hasattr(hashlib, "md5") else hashlib.md5(content).hexdigest()


def _md5_of_file(path: str) -> str:
    """MD5 of a file on disk, closing the handle (used in mock side effects)."""
    with open(path, "rb") as fh:
        return _md5(fh.read())


class TestRequestDownload(unittest.TestCase):
    def _make_local_path(self):
        self._tmp_dir = os.path.join(self._tmp_base, str(len(os.listdir(self._tmp_base))))
        os.makedirs(self._tmp_dir, exist_ok=True)
        return os.path.join(self._tmp_dir, "index.json")

    def setUp(self):
        import tempfile

        self._tmp_base = tempfile.mkdtemp(prefix="reqdl-test-")

    def tearDown(self):
        import shutil

        shutil.rmtree(self._tmp_base, ignore_errors=True)

    def test_success_atomically_replaces(self):
        """A successful download replaces the destination and leaves no .tmp."""
        local = self._make_local_path()
        pre = b'{"ok": "old"}'
        with open(local, "wb") as fh:
            fh.write(pre)
        with mock.patch("src.classes.util.requests.get", return_value=_FakeResponse(200, b'{"ok": "new"}')) as mock_get:
            ok = requestDownload("https://example.com/index.json", local)
        self.assertTrue(ok)
        with open(local, "rb") as fh:
            self.assertEqual(fh.read(), b'{"ok": "new"}')
        self.assertFalse(os.path.exists(local + ".tmp"))
        mock_get.assert_called_once()

    def test_failure_leaves_destination_untouched(self):
        """A network failure must never modify the existing destination."""
        local = self._make_local_path()
        pre = b'{"ok": "old"}'
        with open(local, "wb") as fh:
            fh.write(pre)
        with mock.patch("src.classes.util.requests.get", side_effect=requests.RequestException("boom")):
            ok = requestDownload("https://example.com/index.json", local)
        self.assertFalse(ok)
        with open(local, "rb") as fh:
            self.assertEqual(fh.read(), pre)
        self.assertFalse(os.path.exists(local + ".tmp"))

    def test_http_error_leaves_destination_untouched(self):
        """A 4xx/5xx response must leave the existing destination intact."""
        local = self._make_local_path()
        pre = b'{"ok": "old"}'
        with open(local, "wb") as fh:
            fh.write(pre)
        with mock.patch("src.classes.util.requests.get", return_value=_FakeResponse(500, b"oops")):
            ok = requestDownload("https://example.com/index.json", local)
        self.assertFalse(ok)
        with open(local, "rb") as fh:
            self.assertEqual(fh.read(), pre)
        self.assertFalse(os.path.exists(local + ".tmp"))

    def test_md5_mismatch_keeps_previous_file(self):
        """An MD5 mismatch discards the new download but keeps the old file."""
        local = self._make_local_path()
        pre = b'{"ok": "old"}'
        with open(local, "wb") as fh:
            fh.write(pre)
        wrong_md5 = "00000000000000000000000000000000"  # expected hash that won't match
        with mock.patch("src.classes.util.requests.get", return_value=_FakeResponse(200, b'{"ok": "corrupt"}')), mock.patch("src.classes.util.md5", side_effect=_md5_of_file):
            ok = requestDownload("https://example.com/index.json", local, expected_md5=wrong_md5)
        self.assertFalse(ok)
        with open(local, "rb") as fh:
            self.assertEqual(fh.read(), pre)
        self.assertFalse(os.path.exists(local + ".tmp"))

    def test_fresh_download_failure_leaves_nothing(self):
        """Fresh download (no previous file) that fails leaves no artifacts."""
        local = self._make_local_path()
        with mock.patch("src.classes.util.requests.get", side_effect=requests.RequestException("boom")):
            ok = requestDownload("https://example.com/index.json", local)
        self.assertFalse(ok)
        self.assertFalse(os.path.exists(local))
        self.assertFalse(os.path.exists(local + ".tmp"))


if __name__ == "__main__":
    unittest.main()
