from __future__ import annotations
import os
from typing import Dict, Union
from qgis.core import Qgis, QgsProject, QgsRasterLayer, QgsVectorLayer
from qgis.PyQt.QtCore import Qt, QModelIndex, QUrl
from qgis.PyQt.QtGui import QStandardItem


class QRaveTreeTypes():
    ROOT = 'ROOT'
    FOLDER = 'FOLDER'
    VIEW = 'VIEW'


class QRaveMapLayer():

    class LayerTypes():
        POLYGON = 'polygon'
        LINE = 'line'
        POINT = 'point'
        RASTER = 'raster'
        WMS = 'WMS'

    def __init__(self,
                 label: str,
                 layer_type: str,
                 layer_uri: str,
                 bl_attr: Dict[str, str] = None,
                 meta: Dict[str, str] = None,
                 layer_name: str = None
                 ):
        self.label = label
        self.layer_uri = layer_uri
        self.bl_attr = bl_attr
        self.meta = meta
        self.layer_name = layer_name

        if layer_type not in QRaveMapLayer.LayerTypes.__dict__.values():
            raise Exception('Layer type "{}" is not valid'.format(layer_type))
        self.layer_type = layer_type

        self.exists = self.layer_type == QRaveMapLayer.LayerTypes.WMS or os.path.isfile(layer_uri)

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
        map_layer = item.data(Qt.UserRole)

        # Loop over all the parent group layers for this raster
        # ensuring they are in the tree in correct, nested order
        ancestry = []
        if map_layer.exists is True:
            parent = item.parent()
            while parent is not None and len(ancestry) < 50:
                ancestry.append((parent.text(), parent.row()))
                parent = parent.parent()
        else:
            # Layer does not exist. do not try to put it on the map
            return

        ancestry.reverse()
        parentGroup = None
        for agroup in ancestry:
            parentGroup = QRaveMapLayer._addgrouptomap(agroup[0], agroup[1], parentGroup)

        assert parentGroup, "All rasters should be nested and so parentGroup should be instantiated by now"

        # Loop over all the parent group layers for this raster
        # ensuring they are in the tree in correct, nested order

        # Only add the layer if it's not already in the registry
        if not QgsProject.instance().mapLayersByName(map_layer.label):
            # This might be a basemap
            if map_layer.layer_type == QRaveMapLayer.LayerTypes.WMS:
                rOutput = QgsRasterLayer(map_layer.layer_uri, map_layer.label, 'wms')

            elif map_layer.layer_type in [QRaveMapLayer.LayerTypes.LINE, QRaveMapLayer.LayerTypes.POLYGON, QRaveMapLayer.LayerTypes.POINT]:
                symbology = map_layer.bl_attr['symbology'] if map_layer.bl_attr is not None and 'symbology' in map_layer.bl_attr else 'unknown'
                filepath = map_layer.layer_uri
                uri = filepath
                if map_layer.layer_name is not None:
                    uri += "|layername={}".format(map_layer.layer_name)
                rOutput = QgsVectorLayer(uri, map_layer.label, "ogr")

            elif map_layer.layer_type == QRaveMapLayer.LayerTypes.RASTER:
                # Raster
                rOutput = QgsRasterLayer(filepath, map_layer.label)

            # if not rOutput.isValid():
            #     print("Layer failed to load!")
            # else:
            QgsProject.instance().addMapLayer(rOutput, False)
            parentGroup.insertLayer(item.row(), rOutput)

            # Symbolize this layer
            #     Symbology().symbolize(rOutput, symbology)

        # if the layer already exists trigger a refresh
        else:
            print("REFRESH")
            QgsProject.instance().mapLayersByName(map_layer.label)[0].triggerRepaint()
