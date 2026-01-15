import os
import sys
import importlib

from qgis.core import QgsMessageLog, Qgis

RSXML_VERSION = '2.2.1'

# This is how we import the rsxml module. We do this because we want to bundle the rsxml whl with this package
try:
    # NOTE: IF this shows as a pylance warning that's ok.
    import rsxml
    # If the version does not match what we expect, raise an import error so we can force a reload from the wheel
    if getattr(rsxml, '__version__', '') != RSXML_VERSION:
         raise ImportError(f"Version mismatch: {getattr(rsxml, '__version__', 'unknown')} != {RSXML_VERSION}")
    QgsMessageLog.logMessage(f'rsxml {RSXML_VERSION} imported from system', 'Riverscapes Viewer', Qgis.Info)
except ImportError:
    this_dir = os.path.dirname(os.path.realpath(__file__))
    path = os.path.join(this_dir, '..', 'wheels', f'rsxml-{RSXML_VERSION}-py3-none-any.whl')
    
    if not os.path.exists(path):
        QgsMessageLog.logMessage(f'rsxml wheel not found at {path}.', 'Riverscapes Viewer', Qgis.Critical)
        raise Exception(f'rsxml wheel not found at {path}.')

    # Insert at the beginning of the path to prioritize this wheel
    if path not in sys.path:
        sys.path.insert(0, path)

    if 'rsxml' in sys.modules:
        import rsxml
        importlib.reload(rsxml)
    else:
        import rsxml
    QgsMessageLog.logMessage(f'rsxml imported from wheel {path}', 'Riverscapes Viewer', Qgis.Info)
