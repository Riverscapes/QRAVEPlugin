
import os

import lxml.etree
from .borg import Borg

from qgis.core import QgsMessageLog, Qgis
from qgis.PyQt.QtGui import QStandardItemModel, QStandardItem, QIcon
from qgis.PyQt.QtCore import Qt


from .settings import CONSTANTS

MESSAGE_CATEGORY = CONSTANTS['logCategory']

BL_XML_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'resources', CONSTANTS['businessLogicDir'])


class Project(Borg):

    def __init__(self, project_xml_path: str):
        Borg.__init__(self)

        if project_xml_path is not None:
            self.project_xml_path = project_xml_path
            self.project = None
            self.project_type = None
            self.business_logic = None
            self.qproject = None

    def load(self):
        self._load_project()
        self._load_businesslogic()
        self._build_tree()

    def _load_project(self):
        if os.path.isfile(self.project_xml_path):
            self.project = lxml.etree.parse(self.project_xml_path).getroot()
            self.projectType = self.project.find('ProjectType').text

    def _load_businesslogic(self):
        if self.project is None or self.projectType is None:
            return

        self.business_logic = None
        bl_filename = '{}.xml'.format(self.projectType)
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
        self.qproject = Project._recurse_tree(self.project, self.business_logic.find('Node'))

    @staticmethod
    #####################################
    # TODO: Reference input lookups
    #####################################
    def _recurse_tree(proj_root, bl_el, proj_el=None, parent: QStandardItem = None):
        curr_item = QStandardItem()
        is_root = proj_el is None
        bl_attr = bl_el.attrib
        if proj_el is None:
            proj_el = proj_root

        new_proj_el = proj_el
        if 'xpath' in bl_el.attrib:
            new_projs = proj_el.xpath(bl_el.attrib['xpath'])
            if new_projs is None or len(new_projs) < 1:

                # We just ignore layers we can't find. Log them though
                return
            new_proj_el = new_projs[0]

        # The label is either explicit or it's an xpath lookup
        if 'label' in bl_el.attrib:
            curr_item.setText(bl_el.attrib['label'])
        elif 'xpathlabel' in bl_el.attrib:
            found = new_proj_el.xpath(bl_el.attrib['xpathlabel'])
            qlabel = found[0].text if found is not None and len(found) > 0 else '<unknown>'
            curr_item.setText(qlabel)

        children_container = bl_el.find('Children')

        # If there are children then this is a branch
        if children_container:
            curr_item.setIcon(QIcon(':/plugins/qrave_toolbar/BrowseFolder.png'))
            if is_root is True:
                curr_item.setData({'type': 'ROOT'}, Qt.UserRole),
            else:
                curr_item.setData({'type': 'FOLDER'}, Qt.UserRole),

            for child_node in children_container.xpath('*'):
                # Handle any explicit <Node> children
                if child_node.tag == 'Node':
                    Project._recurse_tree(proj_root, child_node, new_proj_el, curr_item)

                # Repeaters are a separate case
                elif child_node.tag == 'Repeater':
                    qrepeater = QStandardItem(QIcon(':/plugins/qrave_toolbar/BrowseFolder.png'), child_node.attrib['label'])
                    qrepeater.setData({'type': 'REPEATER_FOLDER'}, Qt.UserRole),
                    curr_item.appendRow(qrepeater)
                    repeat_xpath = child_node.attrib['xpath']
                    repeat_node = child_node.find('Node')
                    if repeat_node is not None:
                        for repeater_el in new_proj_el.xpath(repeat_xpath):
                            Project._recurse_tree(proj_root, repeat_node, repeater_el, qrepeater)

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
            meta = {meta.attrib['name']: meta.text for meta in new_proj_el.xpath('Metadata/Meta')}
            curr_item.setData({
                # We get this from the BL
                **bl_el.attrib,
                # We get this from the project
                'meta': meta
            }, Qt.UserRole)

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
