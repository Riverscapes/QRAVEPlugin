
import os

import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
from .borg import Borg

from qgis.PyQt.QtGui import QStandardItemModel, QStandardItem, QIcon
from qgis.PyQt.QtCore import Qt

BASEMAPS_XML_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'resources', 'BaseMaps.xml')


class BaseMaps(Borg):

    def __init__(self):
        Borg.__init__(self)
        if 'regions' not in self.__dict__:
            self.regions = {}

    def load(self):
        """
        Parse the XML and return any basemaps you find
        """
        self.regions = {}

        # Maybe the basemaps file isn't synced yet
        if not os.path.isfile(BASEMAPS_XML_PATH):
            return

        # Parse the XML
        for region in ET.parse(BASEMAPS_XML_PATH).getroot().findall('Region'):
            q_region = QStandardItem(QIcon(':/plugins/qrave_toolbar/BrowseFolder.png'), 'Basemaps')
            q_region.setData({'type': 'BASEMAP_ROOT'}, Qt.UserRole),
            self.regions[region.attrib['name']] = q_region

            for group_layer in region.findall('GroupLayer'):
                q_group_layer = QStandardItem(QIcon(':/plugins/qrave_toolbar/BrowseFolder.png'), group_layer.attrib['name'])
                q_group_layer.setData({'type': 'BASEMAP_FOLDER'}, Qt.UserRole),
                q_region.appendRow(q_group_layer)

                for layer in group_layer.findall('Layer'):
                    q_layer = QStandardItem(QIcon(':/plugins/qrave_toolbar/RaveAddIn_16px.png'), layer.attrib['name'])

                    meta = {meta.attrib['name']: meta.text for meta in layer.findall('Metadata/Meta')}

                    q_layer.setData({
                        'type': 'BASEMAP',
                        'url': layer.attrib['url'],
                        'meta': meta
                    }, Qt.UserRole)
                    q_group_layer.appendRow(q_layer)
