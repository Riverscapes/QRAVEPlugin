from __future__ import annotations
import os
import requests
from typing import Dict

import lxml.etree
from .borg import Borg

from qgis.PyQt.QtGui import QStandardItem, QIcon
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsTask, QgsApplication, Qgis

from .qrave_map_layer import QRaveMapLayer, QRaveTreeTypes, ProjectTreeData
from .settings import CONSTANTS, Settings
from .util import md5, requestFetch

BASEMAPS_XML_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'resources', 'BaseMaps.xml')

MESSAGE_CATEGORY = CONSTANTS['logCategory']
REQUEST_ARGS = '?service=wms&request=GetCapabilities&version=1.0.0'


class QRaveBaseMap():

    def __init__(self, parent: QStandardItem, layer_url: str, tile_type: str, meta: Dict[str, str]):
        self.parent = parent
        self.meta = meta
        self.loaded = False
        self.tile_type = tile_type
        self.settings = Settings()
        self.layer_url = layer_url.replace('?', '')

        self.tm = QgsApplication.taskManager()
        self.reset()

    def reset(self):
        if self.tile_type == 'wms':
            self.parent.removeRows(0, self.parent.rowCount())
            loading_layer = QStandardItem('loading...')
            f = loading_layer.font()
            f.setItalic(True)
            loading_layer.setFont(f)
            loading_layer.setEnabled(False)
            self.parent.appendRow(loading_layer)

    def _parse_wms_layer(self, root_el, parent: QStandardItem):

        try:
            title = root_el.find('Title').text
            name_fnd = root_el.find('Name')
            name = name_fnd.text if name_fnd is not None else title

            srs = root_el.find('SRS').text.split(' ')[0]
            lyr_format = root_el.find('Style/LegendURL/Format').text

            abstract_fnd = root_el.find('Abstract')
            abstract = abstract_fnd.text if abstract_fnd is not None else "No abstract provided"

            urlWithParams = "crs={}&format={}&layers={}&styles&url={}".format(srs, lyr_format, name, self.layer_url)

            lyr_item = QStandardItem(QIcon(':/plugins/qrave_toolbar/layers/Raster.png'), title)

            extra_meta = {
                "srs": srs,
                "name": name,
                "lyr_format": lyr_format
            }
            lyr_item.setData(
                ProjectTreeData(
                    QRaveTreeTypes.LEAF,
                    None,
                    QRaveMapLayer(title, QRaveMapLayer.LayerTypes.WEBTILE, tile_type=self.tile_type, layer_uri=urlWithParams, meta=extra_meta)
                ),
                Qt.UserRole)
            lyr_item.setToolTip(wrap_by_word(abstract, 20))

        except AttributeError as e:
            sourceline = root_el.sourceline if root_el is not None else None
            # Something went wrong. This layer is not renderable.
            self.settings.log(
                'Error parsing basemap layer Exception: {}, Line: {}, Url: {}'.format(e, sourceline, self.layer_url + REQUEST_ARGS),
                Qgis.Warning
            )
            lyr_item = QStandardItem(QIcon(':/plugins/qrave_toolbar/BrowseFolder.png'), root_el.find('Title').text)
            lyr_item.setData(ProjectTreeData(QRaveTreeTypes.BASEMAP_SUB_FOLDER), Qt.UserRole)

        parent.appendRow(lyr_item)

        for sublyr in root_el.findall('Layer'):
            self._parse_wms_layer(sublyr, lyr_item)

    def _wms_fetch_done(self, exception, result=None):
        """This is called when doSomething is finished.
        Exception is not None if doSomething raises an exception.
        result is the return value of doSomething."""
        if exception is None:
            if result is None:
                self.settings.log('Completed with no exception and no result ', Qgis.Warning)
            else:
                try:
                    self.parent.removeRows(0, self.parent.rowCount())
                    for lyr in result.findall('Capability/Layer'):
                        self._parse_wms_layer(lyr, self.parent)

                except Exception as e:
                    self.settings.log(str(e), Qgis.Critical)

        else:
            self.settings.log("Exception: {}".format(exception),
                              Qgis.Critical)
            raise exception

    def load_layers(self, force=False):
        if self.loaded is True and force is False:
            return

        def _wms_fetch(task):
            result = requestFetch(self.layer_url + REQUEST_ARGS)
            return lxml.etree.fromstring(result)

        if self.tile_type == 'wms':
            self.settings.log('Fetching WMS Capabilities: {}'.format(self.layer_url), Qgis.Info)
            ns_task = QgsTask.fromFunction('Loading WMS Data', _wms_fetch, on_finished=self._wms_fetch_done)
            self.tm.addTask(ns_task)


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
        try:
            for region in lxml.etree.parse(BASEMAPS_XML_PATH).getroot().findall('Region'):
                q_region = QStandardItem(QIcon(':/plugins/qrave_toolbar/BrowseFolder.png'), 'Basemaps')
                q_region.setData(ProjectTreeData(QRaveTreeTypes.BASEMAP_ROOT), Qt.UserRole),
                self.regions[region.attrib['name']] = q_region

                for group_layer in region.findall('GroupLayer'):
                    q_group_layer = QStandardItem(QIcon(':/plugins/qrave_toolbar/BrowseFolder.png'), group_layer.attrib['name'])
                    q_group_layer.setData(ProjectTreeData(QRaveTreeTypes.BASEMAP_SUPER_FOLDER), Qt.UserRole),
                    q_region.appendRow(q_group_layer)

                    for layer in group_layer.findall('Layer'):
                        layer_label = layer.attrib['name']
                        # TODO: Need to go a little backward compatible. We can remove this logic after July 1, 2021
                        tile_type = layer.attrib['type'] if 'type' in layer.attrib else 'wms'
                        layer_url = layer.attrib['url']
                        q_layer = QStandardItem(QIcon(':/plugins/qrave_toolbar/RaveAddIn_16px.png'), layer_label)

                        meta = {meta.attrib['name']: meta.text for meta in layer.findall('Metadata/Meta')}

                        basemap_obj = QRaveBaseMap(q_layer, layer_url, tile_type, meta)

                        if tile_type == 'wms':
                            pt_data = basemap_obj
                        else:
                            url_with_params = 'type=xyz&url={}'.format(layer_url)
                            pt_data = QRaveMapLayer(
                                layer_label,
                                QRaveMapLayer.LayerTypes.WEBTILE,
                                tile_type=tile_type,
                                layer_uri=url_with_params,
                                meta=meta
                            )

                        # WMS is complicated because it needs a lookup
                        q_layer.setData(
                            ProjectTreeData(QRaveTreeTypes.LEAF, None, pt_data),
                            Qt.UserRole
                        )

                        # We set the data to be Basemaps to help us load this stuff later
                        q_group_layer.appendRow(q_layer)
        except Exception as e:
            settings = Settings()
            settings.msg_bar("Error loading basemaps", "Exception: {}".format(e),
                             Qgis.Critical)


def wrap_by_word(s, n):
    '''returns a string where \\n is inserted between every n words'''
    a = s.split()
    ret = ''
    for i in range(0, len(a), n):
        ret += ' '.join(a[i:i + n]) + '\n'

    return ret
