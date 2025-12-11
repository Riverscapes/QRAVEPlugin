from __future__ import annotations
import os
import requests
import urllib.parse
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
        self.default_wms_format = "image/png"

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

    @staticmethod
    def _local_name(tag: str) -> str:
        """Return the local (namespace-stripped) name for an XML tag."""
        return tag.split('}')[-1] if tag else tag

    def _child_by_localname(self, el, names):
        """Return the first direct child whose local-name matches any in names."""
        if el is None:
            return None
        if isinstance(names, str):
            names = (names,)
        for child in el:
            if self._local_name(child.tag) in names:
                return child
        return None

    def _children_by_localname(self, el, name):
        """Yield direct children with the requested local-name."""
        if el is None:
            return
        for child in el:
            if self._local_name(child.tag) == name:
                yield child

    def _extract_srs(self, el, fallback: str | None) -> str:
        """Return the first SRS/CRS defined on this element or inherit the fallback."""
        srs_el = self._child_by_localname(el, ('SRS', 'CRS'))
        if srs_el is not None and srs_el.text:
            first = srs_el.text.split()
            if first:
                return first[0]
        return fallback or "unknown"

    def _parse_wms_layer(self, root_el, parent: QStandardItem, inherited_srs: str | None = None):
        try:
            title_el = self._child_by_localname(root_el, 'Title')
            title = title_el.text.strip() if title_el is not None and title_el.text else "Untitled Layer"

            name_el = self._child_by_localname(root_el, 'Name')
            name = name_el.text.strip() if name_el is not None and name_el.text else title

            srs = self._extract_srs(root_el, inherited_srs)

            format_el = self._child_by_localname(root_el, 'Style')
            legend_format_el = None
            if format_el is not None:
                legend_url_el = self._child_by_localname(format_el, 'LegendURL')
                if legend_url_el is not None:
                    legend_format_el = self._child_by_localname(legend_url_el, 'Format')
            lyr_format = (legend_format_el.text.strip()
                          if legend_format_el is not None and legend_format_el.text
                          else self.default_wms_format)

            abstract_el = self._child_by_localname(root_el, 'Abstract')
            abstract = abstract_el.text.strip() if abstract_el is not None and abstract_el.text else "No abstract provided"

            url_with_params = f"crs={srs}&format={lyr_format}&layers={name}&styles&url={self.layer_url}"

            has_sublayers = any(True for _ in self._children_by_localname(root_el, 'Layer'))
            icon_path = ':/plugins/qrave_toolbar/BrowseFolder.png' if has_sublayers else ':/plugins/qrave_toolbar/layers/Raster.png'
            lyr_item = QStandardItem(QIcon(icon_path), title)

            extra_meta = {"srs": srs, "name": name, "lyr_format": lyr_format}
            lyr_item.setData(
                ProjectTreeData(
                    QRaveTreeTypes.LEAF,
                    None,
                    QRaveMapLayer(
                        title,
                        QRaveMapLayer.LayerTypes.WEBTILE,
                        tile_type=self.tile_type,
                        layer_uri=url_with_params,
                        meta=extra_meta
                    )
                ),
                Qt.UserRole
            )
            lyr_item.setToolTip(wrap_by_word(abstract, 20))

        except AttributeError as e:
            sourceline = root_el.sourceline if root_el is not None else None
            self.settings.log(
                'Error parsing basemap layer Exception: {}, Line: {}, Url: {}'.format(
                    e, sourceline, self.layer_url + REQUEST_ARGS),
                Qgis.Warning
            )
            title_fallback_el = self._child_by_localname(root_el, 'Title')
            fallback_title = title_fallback_el.text.strip() if title_fallback_el is not None and title_fallback_el.text else "Unnamed Layer"
            lyr_item = QStandardItem(QIcon(':/plugins/qrave_toolbar/BrowseFolder.png'), fallback_title)
            lyr_item.setData(ProjectTreeData(QRaveTreeTypes.BASEMAP_SUB_FOLDER), Qt.UserRole)

        parent.appendRow(lyr_item)

        for sublyr in self._children_by_localname(root_el, 'Layer'):
            self._parse_wms_layer(sublyr, lyr_item, srs)

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
                    capability_el = self._child_by_localname(result, 'Capability')
                    if capability_el is None:
                        raise ValueError("WMS capabilities missing <Capability> section")

                    request_el = self._child_by_localname(capability_el, 'Request')
                    getmap_el = self._child_by_localname(request_el, 'GetMap') if request_el is not None else None
                    candidate_formats = []
                    if getmap_el is not None:
                        for fmt_el in self._children_by_localname(getmap_el, 'Format'):
                            if fmt_el.text:
                                text = fmt_el.text.strip()
                                if text:
                                    candidate_formats.append(text)
                    for fmt in candidate_formats:
                        if '/' in fmt:  # basic MIME check
                            self.default_wms_format = fmt
                            break
                    else:
                        self.default_wms_format = "image/png"

                    for lyr in self._children_by_localname(capability_el, 'Layer'):
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
            if isinstance(result, bytes):
                payload = result
            else:
                payload = result.encode('utf-8', errors='ignore')
            try:
                return lxml.etree.fromstring(payload)
            except lxml.etree.XMLSyntaxError as exc:
                preview = payload.decode('utf-8', errors='ignore')[:400]
                raise ValueError(
                    f"WMS capabilities from {self.layer_url} are not valid XML: "
                    f"{exc.msg} (line {exc.lineno}, column {exc.position[1]}). "
                    f"Preview: {preview}"
                )

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
                q_region = QStandardItem(QIcon(':/plugins/qrave_toolbar/layers/basemap.svg'), 'Basemaps')
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

                        icon = 'BrowseFolder.png' if tile_type == 'wms' else 'layers/satellite.svg'
                        q_layer = QStandardItem(QIcon(f':/plugins/qrave_toolbar/{icon}'), layer_label)

                        meta = {meta.attrib['name']: meta.text for meta in layer.findall('Metadata/Meta')}

                        basemap_obj = QRaveBaseMap(q_layer, layer_url, tile_type, meta)

                        if tile_type == 'wms':
                            pt_data = basemap_obj
                        else:
                            encoded_url = urllib.parse.quote_plus(layer_url)
                            url_with_params = 'type=xyz&url={}'.format(encoded_url)
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
