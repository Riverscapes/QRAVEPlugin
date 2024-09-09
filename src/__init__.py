import os

from qgis.core import QgsMessageLog, Qgis

RSXML_VERSION = '2.0.6'

# This is how we import the rsxml module. We do this because we want to bundle the rsxml whl with this package
try:
    import rsxml
    QgsMessageLog.logMessage('rsxml imported from system', 'Riverscapes Viewer', Qgis.Info)
except ImportError:
    import sys
    import os
    this_dir = os.path.dirname(os.path.realpath(__file__))
    path = os.path.join(this_dir, '..', 'wheels', f'rsxml-{RSXML_VERSION}-py3-none-any.whl')
    sys.path.append(path)
    if not os.path.exists(path):
        QgsMessageLog.logMessage(f'rsxml wheel not found at {path}.', 'Riverscapes Viewer', Qgis.Critical)
        raise Exception(f'rsxml wheel not found at {path}.')
    import rsxml
    QgsMessageLog.logMessage(f'rsxml imported from wheel {path}', 'Riverscapes Viewer', Qgis.Info)
