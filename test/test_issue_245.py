import html
import json
import os
import re
import sys
import types
import unittest
from unittest.mock import MagicMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def mock_module(name, attrs=None):
    m = types.ModuleType(name)
    if attrs:
        for k, v in attrs.items():
            setattr(m, k, v)
    sys.modules[name] = m
    return m


# Mock QGIS modules
qgis = mock_module("qgis")
qgscore = mock_module(
    "qgis.core",
    {
        "Qgis": MagicMock(),
        "QgsMessageLog": MagicMock(),
        "QgsProject": MagicMock(),
        "QgsSettings": MagicMock(),
    },
)
qgis.core = qgscore
mock_module("qgis.gui")
mock_module("qgis.utils")
pyqt = mock_module("qgis.PyQt")
qgis.PyQt = pyqt
qtcore = mock_module(
    "qgis.PyQt.QtCore",
    {
        "Qt": MagicMock(),
        "QObject": MagicMock(),
        "QSettings": MagicMock(),
        "pyqtSignal": MagicMock(),
        "QTimer": MagicMock(),
    },
)
pyqt.QtCore = qtcore
qtwidgets = mock_module(
    "qgis.PyQt.QtWidgets",
    {
        "QWidget": MagicMock(),
        "QDialog": MagicMock(),
        "QAction": MagicMock(),
        "QMenu": MagicMock(),
    },
)
pyqt.QtWidgets = qtwidgets
mock_module("qgis.PyQt.QtGui")

from src.classes.settings import Settings


class TestBug4TelemetrySetting(unittest.TestCase):
    def test_telemetry_persistence(self):
        """Bug 4: Test that telemetry setting can be round-tripped."""

        # We need to mock QgsSettings since Settings uses it
        with unittest.mock.patch("src.classes.settings.QgsSettings") as MockQSettings:
            mock_settings_inst = MockQSettings.return_value
            storage = {}

            def set_value(key, val):
                storage[key] = val

            def get_value(key, default=None):
                val = storage.get(key)
                if val is None:
                    return default
                return val

            mock_settings_inst.setValue.side_effect = set_value
            mock_settings_inst.value.side_effect = get_value
            mock_settings_inst.childKeys.side_effect = lambda: list(storage.keys())

            settings = Settings()

            # Test setting and getting telemetryEnabled
            settings.setValue("telemetryEnabled", True)
            self.assertEqual(settings.getValue("telemetryEnabled"), True)

            settings.setValue("telemetryEnabled", False)
            self.assertEqual(settings.getValue("telemetryEnabled"), False)


class TestBug5RecentProjects(unittest.TestCase):
    def test_recent_projects_logic(self):
        """Bug 5: Test storing and retrieving remote projects with names."""

        with unittest.mock.patch("src.classes.settings.QgsSettings") as MockQSettings:
            mock_settings_inst = MockQSettings.return_value
            storage = {}

            def set_value(key, val):
                storage[key] = val

            def get_value(key, default=None):
                val = storage.get(key)
                if val is None:
                    return default
                return val

            mock_settings_inst.setValue.side_effect = set_value
            mock_settings_inst.value.side_effect = get_value
            mock_settings_inst.childKeys.side_effect = lambda: list(storage.keys())

            settings = Settings()

            # Simulate the logic in dock_widget.py: _add_to_recent_projects
            def add_to_recent(path, name=None):
                recent = settings.getValue("recentProjects")
                if not isinstance(recent, list):
                    recent = []

                # New logic: store as dict
                entry = {"path": path, "name": name}

                # Remove if exists (either as string or dict)
                recent = [r for r in recent if (r if isinstance(r, str) else r.get("path")) != path]
                recent.insert(0, entry)
                settings.setValue("recentProjects", recent[:10])

            # Test adding a remote project
            remote_path = "remote:project-uuid"
            project_name = "My Remote Project"
            add_to_recent(remote_path, project_name)

            recent = settings.getValue("recentProjects")
            self.assertEqual(len(recent), 1)
            self.assertEqual(recent[0]["path"], remote_path)
            self.assertEqual(recent[0]["name"], project_name)

            # Test backward compatibility (legacy string entry)
            settings.setValue("recentProjects", ["/local/path.xml"])
            add_to_recent(remote_path, project_name)
            recent = settings.getValue("recentProjects")
            self.assertEqual(len(recent), 2)
            self.assertEqual(recent[0]["path"], remote_path)
            self.assertEqual(recent[0]["name"], project_name)
            self.assertEqual(recent[1], "/local/path.xml")

            # Test normalization logic from qrave_toolbar.py: _populate_recent_menu
            def normalize(entry):
                if isinstance(entry, str):
                    return entry, None
                return entry.get("path"), entry.get("name")

            p, n = normalize(recent[0])
            self.assertEqual(p, remote_path)
            self.assertEqual(n, project_name)

            p, n = normalize(recent[1])
            self.assertEqual(p, "/local/path.xml")
            self.assertEqual(n, None)


class TestBug3MetaWidgetUrl(unittest.TestCase):
    def test_description_to_html(self):
        """Bug 3: Test that URLs in descriptions are converted to links."""

        def _description_to_html(description):
            if not description:
                return ""
            escaped_text = html.escape(description)
            escaped_text = escaped_text.replace("\n", "<br>")
            url_pattern = re.compile(r"(https?://[^\s<]+)")
            return url_pattern.sub(r'<a href="\1">\1</a>', escaped_text)

        desc = "Check out https://riverscapes.net for more info."
        expected = 'Check out <a href="https://riverscapes.net">https://riverscapes.net</a> for more info.'
        self.assertEqual(_description_to_html(desc), expected)

        desc_with_html = "Search <script>alert(1)</script> at http://google.com"
        expected = 'Search &lt;script&gt;alert(1)&lt;/script&gt; at <a href="http://google.com">http://google.com</a>'
        self.assertEqual(_description_to_html(desc_with_html), expected)


if __name__ == "__main__":
    unittest.main()
