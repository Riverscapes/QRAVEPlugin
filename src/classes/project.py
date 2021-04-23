from __future__ import annotations
import os
from typing import Dict
import lxml.etree
from .borg import Borg

from qgis.core import QgsMessageLog, Qgis
from qgis.PyQt.QtGui import QStandardItem, QIcon, QBrush
from qgis.PyQt.QtCore import Qt

from .qrave_map_layer import QRaveMapLayer, QRaveTreeTypes
from .settings import CONSTANTS

MESSAGE_CATEGORY = CONSTANTS['logCategory']

BL_XML_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'resources', CONSTANTS['businessLogicDir'])


class Project(Borg):

    def __init__(self, project_xml_path: str):
        Borg.__init__(self)
        self.exists = False
        self.meta = None
        self.warehouse_meta = None

        if project_xml_path is not None:
            self.project_xml_path = os.path.abspath(project_xml_path)
            self.project = None
            self.project_type = None
            self.business_logic = None
            self.qproject = None
            self.project_dir = None
            self.exists = os.path.isfile(self.project_xml_path)
            if self.exists:
                self.project_dir = os.path.dirname(self.project_xml_path)

    def load(self):
        if self.exists is True:
            self._load_project()
            self._load_businesslogic()
            self._build_tree()

    def _load_project(self):
        if os.path.isfile(self.project_xml_path):
            self.project = lxml.etree.parse(self.project_xml_path).getroot()

            self.meta = {meta.attrib['name']: meta.text for meta in self.project.findall('MetaData/Meta')}
            self.warehouse_meta = {meta.attrib['name']: meta.text for meta in self.project.findall('Warehouse/Meta')}
            self.project_type = self.project.find('ProjectType').text

    def _load_businesslogic(self):
        if self.project is None or self.project_type is None:
            return

        self.business_logic = None
        bl_filename = '{}.xml'.format(self.project_type)
        local_bl_path = os.path.join(os.path.dirname(self.project_xml_path), bl_filename)
        builtin_bl_path = os.path.join(BL_XML_DIR, bl_filename)
        # 1. first check for a businesslogic file next to the project file
        if os.path.isfile(local_bl_path):
            self.business_logic = lxml.etree.parse(local_bl_path).getroot()

        # 2. Second, check the businesslogic we've got from the web
        elif os.path.isfile(builtin_bl_path):
            self.business_logic = lxml.etree.parse(builtin_bl_path).getroot()

        # 3. Fall back to the default xml file
        elif os.path.isfile(os.path.join(BL_XML_DIR, 'default.xml')):
            self.business_logic = lxml.etree.parse(local_bl_path).getroot()

        # Or do nothing
        return

    def _build_tree(self, force=False):
        """
        Parse the XML and return any basemaps you find
        """

        if self.business_logic is None or force is True:
            self.load_businesslogic()

        if self.project is None or force is True:
            self.load_project()

        # Maybe the basemaps file isn't synced yet
        if self.project_xml_path is None or not os.path.isfile(self.project_xml_path):
            self.qproject = None
            return

        # Parse the XML
        self.qproject = self._recurse_tree()
        self._build_views()

    def _build_views(self):
        views = self.business_logic.find('Views')

        if views is None or 'default' not in views.attrib:
            return

        curr_item = QStandardItem(QIcon(':/plugins/qrave_toolbar/BrowseFolder.png'), "Project Views")
        curr_item.setData({'type': QRaveTreeTypes.PROJECT_VIEW_FOLDER}, Qt.UserRole)

        for view in self.business_logic.findall('Views/View'):
            name = view.attrib['name']
            view_id = view.attrib['id']

            if name is None or view_id is None:
                continue

            view_item = QStandardItem(QIcon(':/plugins/qrave_toolbar/project_view.png'), name)
            view_item.setData({
                'type': QRaveTreeTypes.PROJECT_VIEW,
                'ids': [layer.attrib['id'] for layer in view.findall('Layers/Layer')]
            }, Qt.UserRole)
            curr_item.appendRow(view_item)

        self.qproject.appendRow(curr_item)

    def _recurse_tree(self, bl_el=None, proj_el=None, parent: QStandardItem = None):
        if bl_el is None:
            bl_el = self.business_logic.find('Node')

        is_root = proj_el is None
        bl_attr = bl_el.attrib

        if proj_el is None:
            proj_el = self.project

        new_proj_el = proj_el
        if 'xpath' in bl_el.attrib:
            new_proj_el = xpathone_withref(self.project, proj_el, bl_el.attrib['xpath'])
            if new_proj_el is None:
                # We just ignore layers we can't find. Log them though
                return

        # The label is either explicit or it's an xpath lookup
        curr_label = '<unknown>'
        if 'label' in bl_el.attrib:
            curr_label = bl_el.attrib['label']
        elif 'xpathlabel' in bl_el.attrib:
            found = new_proj_el.xpath(bl_el.attrib['xpathlabel'])
            curr_label = found[0].text if found is not None and len(found) > 0 else '<unknown>'

        curr_item = QStandardItem()
        curr_item.setText(curr_label)

        children_container = bl_el.find('Children')

        # If there are children then this is a branch
        if children_container:
            curr_item.setIcon(QIcon(':/plugins/qrave_toolbar/BrowseFolder.png'))
            if is_root is True:
                curr_item.setData({'type': QRaveTreeTypes.PROJECT_ROOT}, Qt.UserRole),
            else:
                curr_item.setData({'type': QRaveTreeTypes.PROJECT_FOLDER}, Qt.UserRole),

            for child_node in children_container.xpath('*'):
                # Handle any explicit <Node> children
                if child_node.tag == 'Node':
                    self._recurse_tree(child_node, new_proj_el, curr_item)

                # Repeaters are a separate case
                elif child_node.tag == 'Repeater':
                    qrepeater = QStandardItem(QIcon(':/plugins/qrave_toolbar/BrowseFolder.png'), child_node.attrib['label'])
                    qrepeater.setData({'type': QRaveTreeTypes.PROJECT_REPEATER_FOLDER}, Qt.UserRole),
                    curr_item.appendRow(qrepeater)
                    repeat_xpath = child_node.attrib['xpath']
                    repeat_node = child_node.find('Node')
                    if repeat_node is not None:
                        for repeater_el in new_proj_el.xpath(repeat_xpath):
                            self._recurse_tree(repeat_node, repeater_el, qrepeater)

        # Otherwise this is a leaf
        else:
            bl_type = bl_el.attrib['type']
            if bl_type == 'polygon':
                curr_item.setIcon(QIcon(':/plugins/qrave_toolbar/layers/Polygon.png'))
            elif bl_type == 'line':
                curr_item.setIcon(QIcon(':/plugins/qrave_toolbar/layers/Polyline.png'))
            elif bl_type == 'point':
                curr_item.setIcon(QIcon(':/plugins/qrave_toolbar/layers/MultiDot.png'))
            elif bl_type == 'raster':
                curr_item.setIcon(QIcon(':/plugins/qrave_toolbar/layers/Raster.png'))

            # Couldn't find this node. Ignore it.
            meta = {meta.attrib['name']: meta.text for meta in new_proj_el.findall('MetaData/Meta')}
            new_proj_el.find('Path')

            layer_name = None
            layer_uri = os.path.join(self.project_dir, new_proj_el.find('Path').text)
            # If this is a geopackage it's special
            if new_proj_el.getparent().tag == 'Layers':
                layer_name = new_proj_el.find('Path').text
                layer_uri = os.path.join(self.project_dir, new_proj_el.getparent().getparent().find('Path').text)

            layer_type = bl_attr['type'] if 'type' in bl_attr else 'unknown'

            map_layer = QRaveMapLayer(curr_label, layer_type, layer_uri, bl_attr, meta, layer_name)
            curr_item.setData(map_layer, Qt.UserRole)

            if not map_layer.exists:
                curr_item.setData(QBrush(Qt.red), Qt.ForegroundRole)
                curr_item_font = curr_item.font()
                curr_item_font.setItalic(True)
                curr_item.setFont(curr_item_font)

                curr_item.setToolTip('File not found: {}'.format(map_layer.layer_uri))

        if parent:
            parent.appendRow(curr_item)

        return curr_item


def xpathone_withref(root_el, el, xpath_str):
    found = el.xpath(xpath_str)

    # If the node is not found we need to check if it's a reference
    if found is None or len(found) < 1:
        if '@id=' in xpath_str:
            ref_found = el.xpath(xpath_str.replace('@id=', '@ref='))
            # If not even the ref is found then this is not valid
            if ref_found is not None and len(ref_found) > 1:
                ref_str = ref_found[0].attrib['ref']
                # Now we go hunting for the origin of the reference
                origin = root_el.get_element_by_id(ref_str)
                # we found the origin but the reference could not be found
                if origin is None or len(origin) < 1:
                    QgsMessageLog.logMessage(
                        'Error finding input node with xpath={} and ref="{}"'.format(xpath_str, ref_str),
                        MESSAGE_CATEGORY, Qgis.Critical)
                    return
                else:
                    return origin[0]

        QgsMessageLog.logMessage(
            'Error finding node with path="{}"'.format(xpath_str),
            MESSAGE_CATEGORY, Qgis.Critical)
    else:
        # If the node is found and is not a reference this is the easy case
        return found[0]
