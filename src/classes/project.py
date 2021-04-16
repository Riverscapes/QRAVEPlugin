
import os

import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
from .borg import Borg

from qgis.PyQt.QtGui import QStandardItemModel, QStandardItem, QIcon
from qgis.PyQt.QtCore import Qt

from .settings import Settings, CONSTANTS

BL_XML_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'resources', CONSTANTS['businessLogicDir'])


class Project(Borg):

    def __init__(self, project_xml_path: str):
        Borg.__init__(self)
        self.settings = Settings()
        self.project_path = self.settings.getValue('projectPath')

        if project_xml_path is not None:
            self.project_xml_path = project_xml_path
            self.project = None
            self.project_type = None
            self.business_logic = None
            self.qproject = None
            self.load_project()
            self.load_businesslogic()
            self.build_tree()

    def load_project(self):
        if os.path.isfile(self.project_xml_path):
            self.project = ET.parse(self.project_xml_path).getroot()
            self.projectType = self.project.find('ProjectType').text

    def load_businesslogic(self):
        if self.project is None or self.projectType is None:
            return

        self.business_logic = None
        bl_filename = '{}.xml'.format(self.projectType)
        local_bl_path = os.path.join(os.path.dirname(self.project_xml_path), bl_filename)
        builtin_bl_path = os.path.join(BL_XML_DIR, bl_filename)
        # 1. first check for a businesslogic file next to the project file
        if os.path.isfile(local_bl_path):
            self.business_logic = ET.parse(local_bl_path).getroot()

        # 2. Second, check the businesslogic we've got from the web
        elif os.path.isfile(builtin_bl_path):
            self.business_logic = ET.parse(builtin_bl_path).getroot()

        # 3. Fall back to the default xml file
        elif os.path.isfile(os.path.join(BL_XML_DIR, 'default.xml')):
            self.business_logic = ET.parse(local_bl_path).getroot()

        # Or do nothing
        return

    def build_tree(self, force=False):
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
        self.qproject = Project._recurse_tree(self.business_logic.find('Node'), self.project)

    @staticmethod
    #####################################
    # TODO: Reference input lookups
    #####################################
    def _recurse_tree(blEl, projEl, parent: QStandardItem = None):
        curr_item = QStandardItem()

        # The label is either explicit or it's an xpath lookup
        if 'label' in blEl.attrib:
            curr_item.setText(blEl.attrib['label'])
        elif 'xpathlabel' in blEl.attrib:
            found = projEl.find(blEl.attrib['xpathlabel'])
            qlabel = found.text if found is not None else '<unknown>'
            curr_item.setText(qlabel)

        new_projEl = projEl
        if 'xpath' in blEl.attrib:
            new_projEl = projEl.find(blEl.attrib['xpath'])

        children_container = blEl.find('Children')
        # If there are children then this is a branch
        if children_container:
            for child_node in children_container.findall('*'):
                if child_node.tag == 'Node':
                    Project._recurse_tree(child_node, new_projEl, curr_item)
                elif child_node.tag == 'Repeater':
                    qrepeater = QStandardItem(child_node.attrib['label'])
                    curr_item.appendRow(qrepeater)
                    repeat_xpath = child_node.attrib['xpath']
                    repeat_node = child_node.find('Node')
                    for repeater_el in projEl.findall(repeat_xpath):
                        Project._recurse_tree(repeat_node, repeater_el, qrepeater)
        # Otherwise this is a leaf
        else:
            meta = {meta.attrib['name']: meta.text for meta in new_projEl.findall('Metadata/Meta')}
            curr_item.setData({
                # We get this from the BL
                **blEl.attrib,
                # We get this from the project
                'meta': meta
            }, Qt.UserRole)

        if parent:
            parent.appendRow(curr_item)

        return curr_item
