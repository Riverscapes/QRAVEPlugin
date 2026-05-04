# -*- coding: utf-8 -*-
"""Icon loading utility that works in both QGIS 3 (Qt5) and QGIS 4 (Qt6).

In QGIS 3 / PyQt5 the compiled resources.py registers icons via
``qRegisterResourceData`` so ``QIcon(":/plugins/qrave_toolbar/…")`` works
directly.  In QGIS 4 / PyQt6 that function no longer exists, so we fall
back to loading icons from the ``Images/`` directory on disk.
"""
import os

from qgis.PyQt.QtGui import QIcon

# Absolute path to the plugin root (one level above this src/ package).
_PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Map every QRC alias → relative path from _PLUGIN_ROOT.
# Derived from src/resources.qrc.  The viewer-icon lives at the root
# (not inside Images/) and the layers/ sub-directory uses 16px PNGs.
_ALIAS_TO_FILE: dict = {
    "BrowseFolder.png": "Images/folder.svg",
    "Help.png": "Images/help.svg",
    "NewProject.png": "Images/add.svg",
    "open.svg": "Images/open.svg",
    "Options.png": "Images/settings.svg",
    "viewer-icon.svg": "icon.svg",
    # Legacy alias used in some tree-builder code (.png extension typo).
    "viewer-icon.png": "icon.svg",
    "data-exchange-icon.svg": "Images/DataExchange.svg",
    "bounds": "Images/bounds.svg",
    "tools": "Images/tools.svg",
    "refresh.png": "Images/refresh.svg",
    "tree.png": "Images/tree.png",
    "expand.png": "Images/expand.svg",
    "collapse.png": "Images/collapse.svg",
    "AddToMap.png": "Images/add_to_map.svg",
    "metadata.png": "Images/metadata.svg",
    "close.png": "Images/close.svg",
    "upload_project.svg": "Images/upload_project.svg",
    "download.svg": "Images/download.svg",
    "description.svg": "Images/description.svg",
    "draft.svg": "Images/draft.svg",
    "summarize.svg": "Images/summarize.svg",
    "view.svg": "Images/view.svg",
    "layers/Dot.png": "Images/layers/Dot16.png",
    # Note: on-disk file has a lowercase 'd' (Multidot16.png).
    "layers/MultiDot.png": "Images/layers/Multidot16.png",
    "layers/Polygon.png": "Images/layers/Polygon16.png",
    "layers/Polyline.png": "Images/layers/Polyline16.png",
    "layers/Raster.png": "Images/layers/Raster16.png",
    "layers/basemap.svg": "Images/layers/basemap.svg",
    "layers/satellite.svg": "Images/layers/satellite.svg",
    "layers/tin.svg": "Images/layers/tin.svg",
    "mActionEditCopy.svg": "Images/mActionEditCopy.svg",
    # Missing from .qrc — fall back to the main plugin icon.
    "RaveAddIn_16px.png": "icon.svg",
}


def qrave_icon(alias: str) -> QIcon:
    """Return a ``QIcon`` for the given resource *alias*.

    Tries the compiled Qt resource path first (QGIS 3 / PyQt5).  If the
    resource system was not registered (QGIS 4 / PyQt6) the icon will be
    null and we fall back to loading the file directly from disk.

    Args:
        alias: The resource alias as declared in ``src/resources.qrc``,
               e.g. ``"viewer-icon.svg"`` or ``"layers/Raster.png"``.

    Returns:
        A valid :class:`QIcon`, or an empty :class:`QIcon` if the file
        cannot be found by either method.
    """
    icon = QIcon(f":/plugins/qrave_toolbar/{alias}")
    if not icon.isNull():
        return icon

    # Qt resource not registered — load from the file system.
    rel_path = _ALIAS_TO_FILE.get(alias, alias)
    fs_path = os.path.join(_PLUGIN_ROOT, rel_path)
    if os.path.exists(fs_path):
        return QIcon(fs_path)

    return QIcon()
