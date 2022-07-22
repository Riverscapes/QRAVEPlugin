from __future__ import annotations
import os
from typing import Dict
import lxml.etree
import traceback

from qgis.core import Qgis
from qgis.PyQt.QtGui import QStandardItem, QIcon, QBrush
from qgis.PyQt.QtCore import Qt

from .qrave_map_layer import QRaveMapLayer, QRaveTreeTypes, ProjectTreeData
from .rspaths import parse_rel_path
from .settings import CONSTANTS, Settings

MESSAGE_CATEGORY = CONSTANTS['logCategory']

BL_XML_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'resources', CONSTANTS['businessLogicDir'])


class Project:

    def __init__(self, project_xml_path: str):
        self.exists = False
        self.meta = None
        self.warehouse_meta = None
        self.default_view = None
        self.views = {}
        self.settings = Settings()

        self.project_xml_path = os.path.abspath(project_xml_path)
        self.project = None
        self.loadable = False
        self.load_errs = False
        self.project_type = None
        self.business_logic_path = None
        self.business_logic = None
        self.qproject = None
        self.project_dir = None
        self.exists = os.path.isfile(self.project_xml_path)
        if self.exists:
            self.project_dir = os.path.dirname(self.project_xml_path)

    def load(self):
        self.load_errs = False
        if self.exists is True:
            try:
                self._load_project()
                self._load_businesslogic()
                self._build_tree()
                self.loadable = True
                if self.load_errs is False:
                    self.settings.msg_bar('Project Loaded', self.project_xml_path, Qgis.Success)
                else:
                    self.settings.msg_bar('Project Loaded with errors', "(See QRAVE logs for details)", Qgis.Critical)
            except Exception as e:
                self.settings.msg_bar("Error loading project", "Project: {}\n (See QRAVE logs for specifics)".format(self.project_xml_path),
                                      Qgis.Critical)
                self.settings.log("Exception {}\n\nTrace: {}".format(e, traceback.format_exc()), Qgis.Critical)
        else:
            self.settings.msg_bar("Project Not Found", self.project_xml_path,
                                  Qgis.Critical)

    def _load_project(self):
        if os.path.isfile(self.project_xml_path):
            self.project = lxml.etree.parse(self.project_xml_path).getroot()

            self.meta = self.extract_meta(self.project.findall('MetaData/Meta'))
            self.warehouse_meta = self.extract_meta(self.project.findall('Warehouse/Meta'))
            self.project_type = self.project.find('ProjectType').text

            realizations = self.project.find('Realizations')
            if realizations is None:
                raise Exception('Could not find the <Realizations> node. Are you sure the xml file you opened is Riverscapes Project? File: {}'.format(self.project_xml_path))

    def extract_meta(self, nodelist):
        meta = {}
        for meta_node in nodelist:
            key = meta_node.attrib['name']
            value = meta_node.text
            type = meta_node.attrib['type'] if 'type' in meta_node.attrib else None
            meta[key] = (value, type)
        return meta

    def _load_businesslogic(self):
        if self.project is None or self.project_type is None:
            return
        # TODO Determine if V2 needed

        self.business_logic = None

        # Case-sensitive filename we expect
        bl_filename = '{}.xml'.format(self.project_type)
        bl_file_dir = bl_filename
        if self.project.attrib['{http://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation'] == 'https://xml.riverscapes.xyz/Projects/XSD/V2/RiverscapesProject.xsd':
            bl_file_dir = os.path.join('V2', bl_filename)

        hierarchy = [
            # 1. first check for a businesslogic file next to the project file
            parse_rel_path(os.path.join(os.path.dirname(self.project_xml_path), bl_filename)),
            # 2. Second, check the businesslogic we've got from the web
            parse_rel_path(os.path.join(BL_XML_DIR, bl_file_dir)),
            # 3. Fall back to the default xml file
            parse_rel_path(os.path.join(BL_XML_DIR, 'default.xml'))
        ]

        # Find the first match
        chosen_qml = next(iter([candidate for candidate in hierarchy if os.path.isfile(candidate)]))

        if chosen_qml is not None:
            self.business_logic_path = chosen_qml
            try:
                self.business_logic = lxml.etree.parse(self.business_logic_path).getroot()
                # Let the user know what business logic we're using
                self.settings.log("Using business logic file: {}".format(self.business_logic_path), Qgis.Info)
            except TypeError as e:
                raise Exception('Error parsing business logic file: {}, {}'.format(self.business_logic_path, e))
            except lxml.etree.XMLSyntaxError as e:
                raise Exception('XML Syntax error while parsing file: {}, {}'.format(self.business_logic_path, e))
            except Exception as e:
                raise Exception('Unknown XML File error: {}, {}'.format(self.business_logic_path, e))
        else:
            raise Exception('Could not find a valid business logic file. Valid paths are: [ {} ]'.format(','.join(hierarchy)))

        # Check for a different kind of file
        root_node = self.business_logic.find('Node')
        if root_node is None:
            raise Exception('Could not find the root <Node> element. Are you sure the xml file you opened is Riverscapes Business logic XML? File: {}'.format(self.business_logic_path))

    def _build_tree(self, force=False):
        """
        Parse the XML and return any basemaps you find
        """

        # Maybe the basemaps file isn't synced yet
        if self.project_xml_path is None or not os.path.isfile(self.project_xml_path):
            self.qproject = None
            return

        # Parse the XML
        if self.business_logic is None:
            self.settings.log("No business logic file for this project could be found.")
        else:
            self.qproject = self._recurse_tree()
            self._build_views()

    def _build_views(self):
        if self.business_logic is None or self.qproject is None:
            return

        views = self.business_logic.find('Views')
        if views is None or 'default' not in views.attrib:
            self.settings.log('Default view could not be located', Qgis.Warning)
            return

        self.default_view = views.attrib['default']
        self.views = {}

        curr_item = QStandardItem(QIcon(':/plugins/qrave_toolbar/BrowseFolder.png'), "Project Views")
        curr_item.setData(ProjectTreeData(QRaveTreeTypes.PROJECT_VIEW_FOLDER, project=self), Qt.UserRole)

        for view in self.business_logic.findall('Views/View'):
            name = view.attrib['name']
            view_id = view.attrib['id'] if 'id' in view.attrib else None

            if name is None or view_id is None:
                continue

            view_item = QStandardItem(QIcon(':/plugins/qrave_toolbar/project_view.png'), name)
            view_layer_ids = [layer.attrib['id'] for layer in view.findall('Layers/Layer')]
            self.views[view_id] = view_layer_ids
            view_item.setData(
                ProjectTreeData(QRaveTreeTypes.PROJECT_VIEW, project=self, data=view_layer_ids),
                Qt.UserRole
            )
            curr_item.appendRow(view_item)

        self.qproject.appendRow(curr_item)

    def _recurse_tree(self, bl_el=None, proj_el=None, parent: QStandardItem = None):
        settings = Settings()

        if bl_el is None:
            bl_el = self.business_logic.find('Node')

        if bl_el is None:
            self.settings.log('No default businesslogic root node could be located in file: {}'.format(self.business_logic_path), Qgis.Critical)
            return

        is_root = proj_el is None
        bl_attr = bl_el.attrib

        if proj_el is None:
            proj_el = self.project

        new_proj_el = proj_el
        if 'xpath' in bl_el.attrib:
            if len(bl_el.attrib['xpath']) == 0:
                self.load_errs = True
                self.settings.log("Empty Xpath detected on line {} of file: {}".format(bl_el.sourceline, self.business_logic_path), Qgis.Critical)
                return
            new_proj_el = xpathone_withref(self.project, proj_el, bl_el.attrib['xpath'])
            if new_proj_el is None:
                # We just ignore layers we can't find. Log them though
                return

        # The label is either explicit or it's an xpath lookup
        curr_label = '<unknown>'
        if 'label' in bl_el.attrib:
            curr_label = bl_el.attrib['label']
        elif 'xpathlabel' in bl_el.attrib:
            if len(bl_el.attrib['xpathlabel']) == 0:
                self.load_errs = True
                self.settings.log("Empty xpathlabel detected on line {} of file: {}".format(bl_el.sourceline, self.business_logic_path), Qgis.Critical)
                return
            found = new_proj_el.xpath(bl_el.attrib['xpathlabel'])
            curr_label = found[0].text if found is not None and len(found) > 0 else '<unknown>'

        curr_item = QStandardItem()
        curr_item.setText(curr_label)

        children_container = bl_el.find('Children')

        # If there are children then this is a branch
        if children_container is not None:
            curr_item.setIcon(QIcon(':/plugins/qrave_toolbar/BrowseFolder.png'))
            if is_root is True:
                curr_item.setData(ProjectTreeData(QRaveTreeTypes.PROJECT_ROOT, project=self, data=dict(children_container.attrib)), Qt.UserRole),
            else:
                curr_item.setData(ProjectTreeData(QRaveTreeTypes.PROJECT_FOLDER, project=self, data=dict(children_container.attrib)), Qt.UserRole),

            for child_node in children_container.xpath('*'):
                # Handle any explicit <Node> children
                if child_node.tag == 'Node':
                    self._recurse_tree(child_node, new_proj_el, curr_item)

                # Repeaters are a separate case
                elif child_node.tag == 'Repeater':
                    qrepeater = QStandardItem(QIcon(':/plugins/qrave_toolbar/BrowseFolder.png'), child_node.attrib['label'])
                    qrepeater.setData(ProjectTreeData(QRaveTreeTypes.PROJECT_REPEATER_FOLDER, project=self, data=dict(children_container.attrib)), Qt.UserRole),
                    curr_item.appendRow(qrepeater)

                    if len(child_node.attrib['xpath']) == 0:
                        self.load_errs = True
                        self.settings.log("Empty repeater xpath detected on line {} of file: {}".format(child_node.sourceline, self.business_logic_path), Qgis.Critical)
                        return

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
            else:
                curr_item.setIcon(QIcon(':/plugins/qrave_toolbar/RaveAddIn_16px.png'))

            # Couldn't find this node. Ignore it.
            meta = self.extract_meta(new_proj_el.findall('MetaData/Meta'))
            new_proj_el.find('Path')

            layer_name = None

            # If this is a geopackage it's special
            if new_proj_el.getparent().tag == 'Layers':
                if self.project.attrib['{http://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation'] == 'https://xml.riverscapes.xyz/Projects/XSD/V2/RiverscapesProject.xsd':
                    layer_name = new_proj_el.attrib['lyrName']
                else:
                    layer_name = new_proj_el.find('Path').text
                layer_uri = os.path.join(self.project_dir, new_proj_el.getparent().getparent().find('Path').text)

            else:
                layer_uri = os.path.join(self.project_dir, new_proj_el.find('Path').text)
                layer_path = new_proj_el.find('Path')
                if layer_path is None:
                    self.settings.log("Could not find <Path> element on line {} of file: {}".format(new_proj_el.sourceline, self.business_logic_path), Qgis.Critical)
                    return

            layer_type = bl_attr['type'] if 'type' in bl_attr else 'unknown'

            map_layer = QRaveMapLayer(curr_label, layer_type, layer_uri, bl_attr, meta, layer_name)
            curr_item.setData(ProjectTreeData(QRaveTreeTypes.LEAF, project=self, data=map_layer), Qt.UserRole)

            if not map_layer.exists:
                settings.msg_bar(
                    'Missing File',
                    'Error finding file with path={}'.format(map_layer.layer_uri),
                    Qgis.Warning)
                curr_item.setData(QBrush(Qt.red), Qt.ForegroundRole)
                curr_item_font = curr_item.font()
                curr_item_font.setItalic(True)
                curr_item.setFont(curr_item_font)

                curr_item.setToolTip('File not found: {}'.format(map_layer.layer_uri))
            elif map_layer.layer_uri:
                curr_item.setToolTip(map_layer.layer_uri)

        if parent:
            parent.appendRow(curr_item)

        return curr_item


def xpathone_withref(root_el, el, xpath_str):
    """Generic method for looking up an xpath including support for the ref attribute

    Args:
        root_el ([type]): [description]
        el ([type]): [description]
        xpath_str ([type]): [description]

    Returns:
        [type]: [description]
    """
    found = el.xpath(xpath_str)
    settings = Settings()
    # If the node is not found we need to check if it's a reference
    if found is None or len(found) < 1:
        if '@id=' in xpath_str:
            ref_found = el.xpath(xpath_str.replace('@id=', '@ref='))
            # If not even the ref is found then this is not valid
            if ref_found is not None and len(ref_found) > 0:
                ref_str = ref_found[0].attrib['ref']
                return xpath_findref(root_el, ref_str, xpath_str)

        settings.log(
            'Error finding project xml node with path="{}"'.format(xpath_str),
            Qgis.Warning)
    else:
        # If the node is found and is not a reference this is the easy case
        if 'ref' in found[0].attrib:
            ref_str = found[0].attrib['ref']
            return xpath_findref(root_el, ref_str, xpath_str)
        else:
            return found[0]


def xpath_findref(root_el, ref_str, xpath_str):
    """If the ref attribute is set then we need to go looking for an <Inputs> node 
    that corresponds

    Args:
        root_el ([type]): [description]
        ref_str ([type]): [description]
        xpath_str ([type]): [description]

    Returns:
        [type]: [description]
    """
    settings = Settings()
    # Now we go hunting for the origin of the reference
    origin = root_el.xpath('Inputs/*[@id="{}"]'.format(ref_str))
    # we found the origin but the reference could not be found
    if origin is None or len(origin) < 1:
        settings.log(
            'Missing Node',
            'Error finding input node with xpath={} and ref="{}"'.format(xpath_str, ref_str),
            Qgis.Warning)
        return
    else:
        return origin[0]
