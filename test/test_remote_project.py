import os
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


mock_module("qgis")
mock_module("qgis.core", {"Qgis": MagicMock(), "QgsMessageLog": MagicMock()})
mock_module("qgis.PyQt")
mock_module("qgis.PyQt.QtGui", {"QIcon": MagicMock(), "QStandardItem": MagicMock()})
mock_module("qgis.PyQt.QtCore")
mock_module("qgis.utils")

# Mock our own package structure
mock_module("src.compat", {"USER_ROLE": 1000})
mock_module("src.icon_utils", {"qrave_icon": MagicMock()})
mock_module(
    "src.classes.qrave_map_layer",
    {"ProjectTreeData": MagicMock(), "QRaveMapLayer": MagicMock(), "QRaveTreeTypes": MagicMock()},
)
mock_module(
    "src.classes.settings", {"CONSTANTS": {"DE_API_URL": "http://test"}, "Settings": MagicMock()}
)

from src.classes.remote_project import RemoteProject


class TestRemoteProject(unittest.TestCase):
    def setUp(self):
        self.gql_data = {
            "project": {"id": "test-id", "name": "Test Project", "bounds": {"bbox": [0, 0, 1, 1]}}
        }
        self.project = RemoteProject(self.gql_data)

    def test_has_bounds_layer(self):
        """Test that has_bounds_layer exists and returns False"""
        self.assertTrue(hasattr(self.project, "has_bounds_layer"))
        self.assertFalse(self.project.has_bounds_layer)

    def test_bounds_path(self):
        """Test that bounds_path exists and returns None"""
        self.assertTrue(hasattr(self.project, "bounds_path"))
        self.assertIsNone(self.project.bounds_path)

    def test_has_bounds(self):
        """Verify existing has_bounds still works"""
        self.assertTrue(self.project.has_bounds)

        # Test with no bounds
        no_bounds_proj = RemoteProject({"project": {"id": "no-bounds"}})
        self.assertFalse(no_bounds_proj.has_bounds)


if __name__ == "__main__":
    unittest.main()
