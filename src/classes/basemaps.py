from __future__ import annotations
import os
import requests
from typing import Dict

import lxml.etree
from .borg import Borg

from qgis.PyQt.QtGui import QStandardItemModel, QStandardItem, QIcon
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsTask, QgsApplication, QgsMessageLog, Qgis

from .qrave_map_layer import QRaveMapLayer
from .settings import CONSTANTS
from .util import md5, requestFetch

BASEMAPS_XML_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'resources', 'BaseMaps.xml')

MESSAGE_CATEGORY = CONSTANTS['logCategory']


class BaseMapTreeTypes():
    ROOT = 'ROOT'
    SUPER_FOLDER = 'SUPER_FOLDER'
    SUB_FOLDER = 'SUB_FOLDER'
    LAYER = 'LAYER'


class QRaveBaseMap():

    def __init__(self, parent: QStandardItem, layer_url: str, meta: Dict[str, str]):
        self.parent = parent
        self.meta = meta
        self.loaded = False
        self.layer_url = layer_url.replace('?', '')

        self.tm = QgsApplication.taskManager()
        self.reset()

    def reset(self):
        self.parent.removeRows(0, self.parent.rowCount())
        loading_layer = QStandardItem('loading...')
        f = loading_layer.font()
        f.setItalic(True)
        loading_layer.setFont(f)
        loading_layer.setEnabled(False)
        self.parent.appendRow(loading_layer)

    def _load_layers_done(self, exception, result=None):
        """This is called when doSomething is finished.
        Exception is not None if doSomething raises an exception.
        result is the return value of doSomething."""
        if exception is None:
            if result is None:
                QgsMessageLog.logMessage(
                    'Completed with no exception and no result '
                    '(probably manually canceled by the user)',
                    MESSAGE_CATEGORY, Qgis.Warning)
            else:
                try:
                    self.parent.removeRows(0, self.parent.rowCount())
                    for lyr in result.findall('Capability/Layer'):
                        self.parse_layer(lyr, self.parent)

                except Exception as e:
                    QgsMessageLog.logMessage(str(e), MESSAGE_CATEGORY, Qgis.Warning)

        else:
            QgsMessageLog.logMessage("Exception: {}".format(exception),
                                     MESSAGE_CATEGORY, Qgis.Critical)
            raise exception

    def parse_layer(self, root_el, parent: QStandardItem):
        sublayers = root_el.findall('Layer')
        # This is a branch
        if len(sublayers) > 0:
            q_group_layer = QStandardItem(QIcon(':/plugins/qrave_toolbar/BrowseFolder.png'), root_el.find('Title').text)
            q_group_layer.setData({'type': BaseMapTreeTypes.SUB_FOLDER}, Qt.UserRole),
            parent.appendRow(q_group_layer)
            for sublyr in sublayers:
                self.parse_layer(sublyr, q_group_layer)

        # This is a leaf
        else:
            title = root_el.find('Title').text
            name = root_el.find('Name').text
            srs = root_el.find('SRS').text.split(' ')[0]
            lyr_format = root_el.find('Style/LegendURL/Format').text
            abstract = root_el.find('Abstract').text

            urlWithParams = "crs={}&format={}&layers={}&styles&url={}".format(srs, lyr_format, name, self.layer_url)
            lyr_item = QStandardItem(QIcon(':/plugins/qrave_toolbar/layers/Raster.png'), title)
            extra_meta = {
                "srs": srs,
                "name": name,
                "lyr_format": lyr_format
            }
            lyr_item.setData(
                QRaveMapLayer(title, QRaveMapLayer.LayerTypes.WMS, urlWithParams, extra_meta), Qt.UserRole)
            lyr_item.setToolTip(wrap_by_word(abstract, 20))
            parent.appendRow(lyr_item)

    def load_layers(self, force=False):
        if self.loaded is True and force is False:
            return

        def _layer_fetch(task):
            QgsMessageLog.logMessage('Fetching WMS Capabilities: {}'.format(task.description()),
                                     MESSAGE_CATEGORY, Qgis.Info)
            result = requestFetch(self.layer_url + '?service=wms&request=GetCapabilities&version=1.0.0')
            return lxml.etree.fromstring(result)

        ns_task = QgsTask.fromFunction('Loading WMS Data', _layer_fetch, on_finished=self._load_layers_done)
        self.tm.addTask(ns_task)


class BaseMaps(Borg):

    def __init__(self):
        Borg.__init__(self)
        if 'regions' not in self.__dict__:
            self.regions = {}

    def load_capabilities(self):
        # https://hydro.nationalmap.gov/arcgis/services/wbd/MapServer/WmsServer?service=wms&request=GetCapabilities&version=1.0.0
        print('load_capabilities')

    def load(self):
        """
        Parse the XML and return any basemaps you find
        """
        self.regions = {}

        # Maybe the basemaps file isn't synced yet
        if not os.path.isfile(BASEMAPS_XML_PATH):
            return

        # Parse the XML
        for region in lxml.etree.parse(BASEMAPS_XML_PATH).getroot().findall('Region'):
            q_region = QStandardItem(QIcon(':/plugins/qrave_toolbar/BrowseFolder.png'), 'Basemaps')
            q_region.setData({'type': BaseMapTreeTypes.ROOT}, Qt.UserRole),
            self.regions[region.attrib['name']] = q_region

            for group_layer in region.findall('GroupLayer'):
                q_group_layer = QStandardItem(QIcon(':/plugins/qrave_toolbar/BrowseFolder.png'), group_layer.attrib['name'])
                q_group_layer.setData({'type': BaseMapTreeTypes.SUPER_FOLDER}, Qt.UserRole),
                q_region.appendRow(q_group_layer)

                for layer in group_layer.findall('Layer'):
                    layer_label = layer.attrib['name']
                    layer_url = layer.attrib['url']
                    q_layer = QStandardItem(QIcon(':/plugins/qrave_toolbar/RaveAddIn_16px.png'), layer_label)

                    meta = {meta.attrib['name']: meta.text for meta in layer.findall('Metadata/Meta')}
                    # We set the data to be Basemaps to help us load this stuff later
                    q_layer.setData(QRaveBaseMap(q_layer, layer_url, meta), Qt.UserRole)

                    q_group_layer.appendRow(q_layer)


def wrap_by_word(s, n):
    '''returns a string where \\n is inserted between every n words'''
    a = s.split()
    ret = ''
    for i in range(0, len(a), n):
        ret += ' '.join(a[i:i + n]) + '\n'

    return ret
