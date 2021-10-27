from __future__ import annotations
import os
from typing import Dict
from qgis.core import Qgis, QgsProject, QgsRasterLayer, QgsVectorLayer
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QStandardItem
from .rspaths import parse_rel_path
from .settings import CONSTANTS, Settings

SYMBOLOGY_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'resources', 'symbology')
# BASE is the name we want to use inside the settings keys
MESSAGE_CATEGORY = CONSTANTS['logCategory']


class QRaveTreeTypes():
    PROJECT_ROOT = 'PROJECT_ROOT'
    PROJECT_FOLDER = 'PROJECT_FOLDER'
    PROJECT_REPEATER_FOLDER = 'PROJECT_REPEATER_FOLDER'
    PROJECT_VIEW_FOLDER = 'PROJECT_VIEW_FOLDER'
    PROJECT_VIEW = 'PROJECT_VIEW'
    LEAF = 'LEAF'  # any kind of end node: maplayers and other open-able files
    # Basemaps have a surprising number of itmes
    BASEMAP_ROOT = 'BASEMAP_ROOT'
    BASEMAP_SUPER_FOLDER = 'BASEMAP_SUPER_FOLDER'
    BASEMAP_SUB_FOLDER = 'BASEMAP_SUB_FOLDER'
    # Note: Add-able layers are all covered by QRaveMapLayer and QRaveBaseMap


class ProjectTreeData:
    """This is just a helper class to make sure we have everyhting we need
    for context menus when we right click
    """

    def __init__(self, node_type, project=None, data=None):
        self.type = node_type
        self.project = project
        self.data = data


class QRaveMapLayer():

    class LayerTypes():
        POLYGON = 'polygon'
        LINE = 'line'
        POINT = 'point'
        RASTER = 'raster'
        # Regular file types
        FILE = 'file'
        REPORT = 'report'
        # Tile Types
        WEBTILE = 'WEBTILE'

    def __init__(self,
                 label: str,
                 layer_type: str,
                 layer_uri: str,
                 bl_attr: Dict[str, str] = None,
                 meta: Dict[str, str] = None,
                 layer_name: str = None,
                 tile_type: str = None
                 ):

        self.label = label
        self.layer_uri = layer_uri

        # If this is a real file then sanitize the URI
        if isinstance(self.layer_uri, str) and len(layer_uri) > 0 and layer_type != QRaveMapLayer.LayerTypes.WEBTILE:
            sani_path = parse_rel_path(layer_uri)
            self.layer_uri = os.path.abspath(sani_path)

        self.bl_attr = bl_attr
        self.meta = meta
        self.transparency = 0
        self.layer_name = layer_name
        self.tile_type = tile_type

        if layer_type not in QRaveMapLayer.LayerTypes.__dict__.values():
            settings = Settings()
            settings.log('Layer type "{}" is not valid'.format(layer_type), Qgis.Critical)
        self.layer_type = layer_type

        self.exists = self.layer_type == QRaveMapLayer.LayerTypes.WEBTILE or os.path.isfile(self.layer_uri)

    def _getlayerposition(item):

        name = item.text()
        order = [name]
        absolute_position = 0
        parent = item.parent()
        if parent is not None:
            child_idx = 0
            child = parent.child(child_idx)
            child_data = child.data(Qt.UserRole)
            while child_data is not None:
                if child.text() == name:
                    return absolute_position, order
                if isinstance(child_data.data, QRaveMapLayer):
                    if child_data.data.layer_type in [QRaveMapLayer.LayerTypes.LINE, QRaveMapLayer.LayerTypes.POINT, QRaveMapLayer.LayerTypes.POLYGON, QRaveMapLayer.LayerTypes.RASTER]:
                        absolute_position += 1
                else:
                    if child_data.type == 'PROJECT_FOLDER':
                        absolute_position += 1
                order.append(child.text())
                child_idx += 1
                child = parent.child(child_idx)
                child_data = child.data(Qt.UserRole) if child is not None else None
                
        return absolute_position, order

    @staticmethod
    def _addgrouptomap(sGroupName, sGroupOrder, parentGroup):
        """
        Add a hierarchical group to the layer manager
        :param sGroupName:
        :param parentGroup:
        :return:
        """

        # If no parent group specified then the parent is the ToC tree root
        if not parentGroup:
            parentGroup = QgsProject.instance().layerTreeRoot()

        # Attempt to find the specified group in the parent
        thisGroup = parentGroup.findGroup(sGroupName)
        if not thisGroup:
            thisGroup = parentGroup.insertGroup(sGroupOrder, sGroupName)

        return thisGroup

    @staticmethod
    def add_layer_to_map(item: QStandardItem):
        """
        Add a layer to the map
        :param layer:
        :return:
        """

        # No multiselect so there is only ever one item
        pt_data: ProjectTreeData = item.data(Qt.UserRole)
        project = pt_data.project
        map_layer: QRaveMapLayer = pt_data.data

        settings = Settings()

        # Loop over all the parent group layers for this raster
        # ensuring they are in the tree in correct, nested order
        ancestry = []
        ancestry_order = []
        if map_layer.exists is True:
            parent = item.parent()
            while parent is not None and len(ancestry) < 50:
                pos, order = QRaveMapLayer._getlayerposition(parent)
                ancestry.append((parent.text(), pos))
                ancestry_order.append((parent.text(), order))
                parent = parent.parent()
        else:
            # Layer does not exist. do not try to put it on the map
            return

        ancestry.reverse()
        ancestry_order.reverse()
        parentGroup = None
        for agroup, group_order in ancestry_order:
            if not parentGroup:
                parentGroup = QgsProject.instance().layerTreeRoot()
            pos = 0
            group_order.reverse()
            for group in group_order:
                test_group = parentGroup.findGroup(group)
                if test_group:
                    pos += 1
            parentGroup = QRaveMapLayer._addgrouptomap(agroup, pos, parentGroup)

        assert parentGroup, "All rasters should be nested and so parentGroup should be instantiated by now"

        # Loop over all the parent group layers for this raster
        # ensuring they are in the tree in correct, nested order

        # Only add the layer if it's not already in the registry
        exists = False
        existing_layers = QgsProject.instance().mapLayersByName(map_layer.label)
        layers_ancestry = [QRaveMapLayer.get_layer_ancestry(lyr) for lyr in existing_layers]

        # Now we compare the ancestry group labels to the business logic ancestry branch names
        # to see if this layer is already in the map
        for lyr in layers_ancestry:
            if len(lyr) == len(ancestry) \
                    and all(iter([ancestry[x][0] == lyr[x] for x in range(len(ancestry))])):
                exists = True
                break

        if not exists:
            layer_uri = map_layer.layer_uri
            rOutput = None
            # This might be a basemap
            if map_layer.layer_type == QRaveMapLayer.LayerTypes.WEBTILE:
                rOutput = QgsRasterLayer(layer_uri, map_layer.label, 'wms')

            elif map_layer.layer_type in [QRaveMapLayer.LayerTypes.LINE, QRaveMapLayer.LayerTypes.POLYGON, QRaveMapLayer.LayerTypes.POINT]:
                if map_layer.layer_name is not None:
                    layer_uri += "|layername={}".format(map_layer.layer_name)
                rOutput = QgsVectorLayer(layer_uri, map_layer.label, "ogr")

            elif map_layer.layer_type == QRaveMapLayer.LayerTypes.RASTER:
                # Raster
                rOutput = QgsRasterLayer(layer_uri, map_layer.label)

            if rOutput is not None:
                ##########################################
                # Symbology
                ##########################################

                symbology = map_layer.bl_attr['symbology'] if map_layer.bl_attr is not None and 'symbology' in map_layer.bl_attr else None
                # If the business logic has symbology defined
                if symbology is not None:

                    if len(symbology) == 0:
                        settings.log(
                            "Empty Symbology attribute for node with attributes: {}".format(map_layer.bl_attr),
                            level=Qgis.Warning
                        )
                    else:
                        qml_fname = '{}.qml'.format(symbology)
                        os.path.abspath(os.path.join(project.project_dir, qml_fname))

                        # Here are the search paths for QML files in order of precedence
                        hierarchy = [
                            os.path.abspath(os.path.join(project.project_dir, qml_fname)),
                            # This is the default one
                            os.path.abspath(os.path.join(SYMBOLOGY_DIR, project.project_type, qml_fname)),
                            os.path.abspath(os.path.join(SYMBOLOGY_DIR, 'Shared', qml_fname))
                        ]
                        # Find the first match
                        try:
                            chosen_qml = next(iter([candidate for candidate in hierarchy if os.path.isfile(candidate)]))
                            # Report to the terminal if we couldn't find a qml file to use
                            if chosen_qml is None:
                                settings.log(
                                    "Missing Symbolog: Could not find a valid .qml symbology file for layer {}. Search paths: \n[\n{}]".format(layer_uri, '   ,\n'.join(hierarchy)),
                                    level=Qgis.Warning
                                )
                            # Apply the QML file
                            else:
                                rOutput.loadNamedStyle(chosen_qml)

                        except StopIteration:
                            settings.log('Could not find valid symbology for layer at any of the following search paths: [ {} ]'.format(', '.join(hierarchy)), Qgis.Warning)

                ############################################################
                # Transparency. A few notes:
                # - QML transparency will prevail for rasters before 3.18
                # - We set this here so that QML layer transparency will be
                #   overruled
                ############################################################
                transparency = 0

                try:
                    if 'transparency' in map_layer.bl_attr:
                        transparency = int(map_layer.bl_attr['transparency'])
                except Exception as e:
                    settings.log('Error interpretting error in business logic: {}'.format(e), Qgis.Warning)

                try:
                    if transparency > 0:
                        if rOutput.__class__ is QgsVectorLayer:
                            if hasattr(rOutput, 'setLayerTransparency'):
                                rOutput.setLayerTransparency(transparency)
                            elif hasattr(rOutput, 'setOpacity'):
                                rOutput.setOpacity((100 - transparency) / 100.0)
                            else:
                                settings.log('Setting vector transparency: {}'.format(e), Qgis.Warning)

                            # rOutput.triggerRepaint()
                        elif rOutput.__class__ is QgsRasterLayer:
                            renderer = rOutput.renderer()
                            renderer.setOpacity((100 - transparency) / 100.0)
                            # rOutput.triggerRepaint()
                except Exception as e:
                    settings.log('Error deriving transparency from layer: {}'.format(e), Qgis.Warning)

                QgsProject.instance().addMapLayer(rOutput, False)
                parentGroup.insertLayer(item.row(), rOutput)

        # if the layer already exists trigger a refresh
        else:
            QgsProject.instance().mapLayersByName(map_layer.label)[0].triggerRepaint()

    @staticmethod
    def get_layer_ancestry(layer: list):
        root = QgsProject.instance().layerTreeRoot()
        tree_layer = root.findLayer(layer.id())

        lyr_ancestry = []
        if tree_layer:
            layer_parent = tree_layer.parent()
            while layer_parent is not None and layer_parent.name() != '' and len(lyr_ancestry) < 50:
                lyr_ancestry.append(layer_parent.name())
                layer_parent = layer_parent.parent()

        lyr_ancestry.reverse()
        return lyr_ancestry
