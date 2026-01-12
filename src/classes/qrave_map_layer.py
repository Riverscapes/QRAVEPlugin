from __future__ import annotations
import os
import json
import urllib.parse

from typing import Dict
from qgis.core import (Qgis, QgsProject, QgsRasterLayer, QgsVectorLayer, QgsVectorTileLayer, 
                       QgsRectangle, QgsCoordinateReferenceSystem, QgsCoordinateTransform, 
                       QgsReferencedRectangle, QgsLayerMetadata)

# Some builds of QGIS do not have the specialized MapboxGL renderer
try:
    from qgis.core import QgsVectorTileMapboxGLRenderer
except ImportError:
    QgsVectorTileMapboxGLRenderer = None

# Most builds have the style converter
try:
    from qgis.core import QgsMapBoxGlStyleConverter
except ImportError:
    QgsMapBoxGlStyleConverter = None
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
        TIN = 'tin'
        # Regular file types
        FILE = 'file'
        REPORT = 'report'
        # Tile Types
        WEBTILE = 'webtile'

    def __init__(self,
                 label: str,
                 layer_type: str,
                 layer_uri: str,
                 bl_attr: Dict[str, str] = None,
                 meta: Dict[str, str] = None,
                 layer_name: str = None,
                 tile_type: str = None,
                 description: str = None):

        self.label = label
        self.layer_uri = layer_uri
        layer_type = layer_type.lower() if layer_type else None

        # If this is a real file then sanitize the URI
        if isinstance(self.layer_uri, str) and len(layer_uri) > 0 and layer_type != QRaveMapLayer.LayerTypes.WEBTILE:
            sani_path = parse_rel_path(layer_uri)
            self.layer_uri = os.path.abspath(sani_path)

        self.bl_attr = bl_attr
        self.meta = meta
        self.transparency = 0
        self.layer_name = layer_name
        self.tile_type = tile_type
        self.description = description

        if layer_type not in QRaveMapLayer.LayerTypes.__dict__.values():
            settings = Settings()
            settings.log('Layer type "{}" is not valid'.format(layer_type), Qgis.Critical)
        self.layer_type = layer_type

        self.exists = False
        if self.layer_type == QRaveMapLayer.LayerTypes.WEBTILE:
            self.exists = True
        elif isinstance(self.layer_uri, str) and len(self.layer_uri) > 0:
            self.exists = os.path.isfile(self.layer_uri)

    @staticmethod
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
                    if child_data.type == QRaveTreeTypes.PROJECT_FOLDER:
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

            # Hack to ensure that basemaps are always added to the bottom of the ToC
            if sGroupName == 'Basemaps' and sGroupOrder == 0 and parentGroup == QgsProject.instance().layerTreeRoot():
                thisGroup = parentGroup.addGroup(sGroupName)
            else:
                thisGroup = parentGroup.insertGroup(sGroupOrder, sGroupName)

        return thisGroup

    @staticmethod
    def find_layer_symbology(item: QStandardItem):

        settings = Settings()
        chosen_qml = None
        # No multiselect so there is only ever one item
        pt_data: ProjectTreeData = item.data(Qt.UserRole)
        project = pt_data.project
        map_layer: QRaveMapLayer = pt_data.data

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
                            "Missing Symbolog: Could not find a valid .qml symbology file for layer {}. Search paths: \n[\n{}]".format(map_layer.layer_uri, '   ,\n'.join(hierarchy)),
                            level=Qgis.Warning
                        )

                except StopIteration:
                    settings.log('Could not find valid symbology for layer at any of the following search paths: [ {} ]'.format(', '.join(hierarchy)), Qgis.Warning)
            return chosen_qml

    @staticmethod
    def _prepare_parent_group(item: QStandardItem):
        """ Prepare the parent group for a layer in the tree
        """
        # Loop over all the parent group layers for this raster
        # ensuring they are in the tree in correct, nested order
        ancestry = []
        ancestry_order = []
        parent = item.parent()
        while parent is not None and len(ancestry) < 50:
            pos, order = QRaveMapLayer._getlayerposition(parent)
            ancestry.append((parent.text(), pos))
            ancestry_order.append((parent.text(), order))
            parent = parent.parent()

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

        if not parentGroup:
            parentGroup = QgsProject.instance().layerTreeRoot()

        return parentGroup, ancestry

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

        if map_layer.exists is False:
            # Layer does not exist. do not try to put it on the map
            return

        parentGroup, ancestry = QRaveMapLayer._prepare_parent_group(item)

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
            elif lyr[0] == ancestry[0][0]:  # bit of a hacky way to test if map layer is in the same named qproject
                exists = True
                break

        if not exists:
            layer_uri = map_layer.layer_uri
            rOutput = None
            # This might be a basemap
            if map_layer.layer_type == QRaveMapLayer.LayerTypes.WEBTILE:
                out_uri = layer_uri.replace('%3F', '?').replace('%3A', ':').replace('%2F', '/').replace('%3D', '=')
                rOutput = QgsRasterLayer(out_uri, map_layer.label, 'wms')

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
                chosen_qml = QRaveMapLayer.find_layer_symbology(item)
                if (chosen_qml):
                    rOutput.loadNamedStyle(chosen_qml)

                ############################################################
                # Transparency. A few notes:
                # - QML transparency will prevail for rasters before 3.18
                # - We set this here so that QML layer transparency will be
                #   overruled
                ############################################################
                transparency = 0

                try:
                    if map_layer.bl_attr is not None:
                        transparency = int(map_layer.bl_attr.get('transparency', 0))
                    else:
                        transparency = map_layer.transparency
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

                ##########################################
                # Feature Filter (Definition Query)
                ##########################################

                filter = map_layer.bl_attr['filter'] if map_layer.bl_attr is not None and 'filter' in map_layer.bl_attr else None

                if filter is not None:
                    rOutput.setSubsetString(filter)

        # if the layer already exists trigger a refresh
        else:
            QgsProject.instance().mapLayersByName(map_layer.label)[0].triggerRepaint()

    @staticmethod
    def add_remote_vector_layer_to_map(item: QStandardItem, tile_service: Dict):
        """ Add a remote vector tile layer to the map
        """
        pt_data: ProjectTreeData = item.data(Qt.UserRole)
        map_layer: QRaveMapLayer = pt_data.data
        settings = Settings()

        parentGroup, ancestry = QRaveMapLayer._prepare_parent_group(item)

        # Check if exists
        existing_layers = QgsProject.instance().mapLayersByName(map_layer.label)
        layers_ancestry = [QRaveMapLayer.get_layer_ancestry(lyr) for lyr in existing_layers]

        exists = False
        for lyr in layers_ancestry:
            if len(lyr) == len(ancestry) and all(iter([ancestry[x][0] == lyr[x] for x in range(len(ancestry))])):
                exists = True
                break
        
        if exists:
            QgsProject.instance().mapLayersByName(map_layer.label)[0].triggerRepaint()
            return

        # Construct Tile URL
        base_url = tile_service.get('url', '').rstrip('/')
        
        # TODO: Fix minZoom and maxZoom on the server-side so we don't need to fetch indexUrl manually
        # For vector layers we use layer_name or nodeId
        layer_name = map_layer.layer_name
        if not layer_name:
            layer_name = map_layer.bl_attr.get('nodeId', '')
        if not layer_name:
            # Strip the id off of the xPath. So for Project/Realizations/Realization#REALIZATION1/Datasets/Vector#Ecoregions I want Ecoregions
            layer_name = map_layer.bl_attr.get('rsXPath', '').split('/')[-1].split('#')[1]
            
        fmt = tile_service.get('format', 'pbf')
        
        # Build the URI
        # Examples: type=xyz&url=https://.../{z}/{x}/{y}.pbf
        tile_url = f"{base_url}/{layer_name}/{{z}}/{{x}}/{{y}}.{fmt}"

        rOutput = None
        if fmt == 'pbf':
            # Vector Tile URI format: type=xyz&url=...&zmin=...&zmax=...
            encoded_url = urllib.parse.quote(tile_url, safe='/:?={}')
            uri = f"type=xyz&url={encoded_url}"
            if tile_service.get('maxZoom') is not None:
                uri += f"&zmax={tile_service['maxZoom']}"
            if tile_service.get('minZoom') is not None:
                uri += f"&zmin={tile_service['minZoom']}"
            
            rOutput = QgsVectorTileLayer(uri, map_layer.label)
        else:
            settings.log(f"Unsupported format: {fmt}", Qgis.Warning)
            return

        
        settings.log(f"Adding remote layer URI: {uri}", Qgis.Info)

        if rOutput and rOutput.isValid():
            QgsProject.instance().addMapLayer(rOutput, False)
            parentGroup.insertLayer(item.row(), rOutput)

            # Set extent and metadata AFTER adding to project to ensure they stick
            bounds = tile_service.get('bounds')
            if bounds and len(bounds) == 4:
                try:
                    rect = QgsRectangle(bounds[0], bounds[1], bounds[2], bounds[3])
                    src_crs = QgsCoordinateReferenceSystem("EPSG:4326")
                    dest_crs = rOutput.crs()
                    if not dest_crs.isValid():
                        dest_crs = QgsCoordinateReferenceSystem("EPSG:3857")
                        rOutput.setCrs(dest_crs)
                    
                    if src_crs != dest_crs:
                        transform = QgsCoordinateTransform(src_crs, dest_crs, QgsProject.instance())
                        rect = transform.transformBoundingBox(rect)
                        
                    rOutput.setExtent(rect)

                    metadata = rOutput.metadata()
                    metadata.setIdentifier(map_layer.label)
                    metadata.setTitle(map_layer.label)
                    
                    spatialExtent = QgsLayerMetadata.SpatialExtent()
                    spatialExtent.extent = QgsReferencedRectangle(rect, dest_crs)
                    
                    extent = QgsLayerMetadata.Extent()
                    extent.setSpatialExtent([spatialExtent])
                    metadata.setExtent(extent)
                    
                    rOutput.setMetadata(metadata)
                    settings.log(f"Finalized layer metadata and extent: {rect.toString()}", Qgis.Info)
                except Exception as e:
                    settings.log(f'Error finalising metadata: {e}', Qgis.Warning)

            rOutput.triggerRepaint()
            
            # Apply Mapbox GL Symbology if present
            mapbox_json = tile_service.get('mapboxJson')
            if mapbox_json:
                try:
                    # The API might return a full Riverscapes Symbology object or just a list of layers
                    layers = []
                    if isinstance(mapbox_json, dict) and 'layerStyles' in mapbox_json:
                        layers = mapbox_json['layerStyles']
                    elif isinstance(mapbox_json, list):
                        layers = mapbox_json
                    else:
                        # Fallback if it's already a full Mapbox GL style
                        layers = mapbox_json.get('layers', [])

                    # Dynamically fix source and source-layer
                    # QGIS expects these to match the source ID and layer name in the tiles
                    source_id = 'vector_tiles'
                    for layer in layers:
                        layer['source'] = source_id
                        layer['source-layer'] = layer_name

                    style = {
                        "version": 8,
                        "sources": {
                            source_id: {
                                "type": "vector",
                                "tiles": [tile_url]
                            }
                        },
                        "layers": layers
                    }
                    style_json = json.dumps(style)

                    # Option 1: Use the specialized native renderer if available
                    if QgsVectorTileMapboxGLRenderer:
                        renderer = QgsVectorTileMapboxGLRenderer()
                        renderer.setStyle(style_json)
                        rOutput.setRenderer(renderer)
                        settings.log("Applied Mapbox GL symbology using native renderer", Qgis.Info)
                    
                    # Option 2: Fallback to the style converter (more compatible)
                    # https://qgis.org/pyqgis/master/core/QgsMapBoxGlStyleConverter.html
                    elif QgsMapBoxGlStyleConverter:
                        converter = QgsMapBoxGlStyleConverter()
                        result = converter.convert(style_json)
                        if result == QgsMapBoxGlStyleConverter.Success:
                            rOutput.setRenderer(converter.renderer())
                            settings.log("Applied Mapbox GL symbology using style converter", Qgis.Info)
                        else:
                            settings.log(f"Mapbox style conversion failed: {converter.errorMessage()}", Qgis.Warning)
                    
                    else:
                        settings.log("No compatible Mapbox GL renderer found in this QGIS build.", Qgis.Warning)

                except Exception as e:
                    settings.log(f"Error applying Mapbox GL symbology: {e}", Qgis.Warning)

            rOutput.triggerRepaint()
            
            # TODO: Transparency and other settings if needed
            transparency = 0
            try:
                transparency = int(map_layer.bl_attr.get('transparency', 0))
                if transparency > 0:
                    if isinstance(rOutput, QgsVectorTileLayer) or isinstance(rOutput, QgsVectorLayer):
                        if hasattr(rOutput, 'setOpacity'):
                            rOutput.setOpacity((100 - transparency) / 100.0)
                    elif isinstance(rOutput, QgsRasterLayer):
                        rOutput.renderer().setOpacity((100 - transparency) / 100.0)
            except Exception as e:
                settings.log(f'Error setting transparency: {e}', Qgis.Warning)
        else:
            settings.log(f'Failed to create valid remote layer for {map_layer.label}', Qgis.Critical)

    @staticmethod
    def add_remote_raster_layer_to_map(item: QStandardItem, tile_service: Dict):
        """ Add a remote raster layer to the map
        """
        pt_data: ProjectTreeData = item.data(Qt.UserRole)
        map_layer: QRaveMapLayer = pt_data.data
        settings = Settings()

        parentGroup, ancestry = QRaveMapLayer._prepare_parent_group(item)

        # Check if exists
        existing_layers = QgsProject.instance().mapLayersByName(map_layer.label)
        layers_ancestry = [QRaveMapLayer.get_layer_ancestry(lyr) for lyr in existing_layers]

        exists = False
        for lyr in layers_ancestry:
            if len(lyr) == len(ancestry) and all(iter([ancestry[x][0] == lyr[x] for x in range(len(ancestry))])):
                exists = True
                break
        
        if exists:
            QgsProject.instance().mapLayersByName(map_layer.label)[0].triggerRepaint()
            return

        # Symbology logic provided by user
        symbology_name = map_layer.bl_attr.get('symbology')
        symbology_key = symbology_name if symbology_name and symbology_name != 'NONE' else 'raster'
        
        fmt = tile_service.get('format', 'png')
        is_cog = fmt == 'COG'
        base_url = tile_service.get('url', '')

        if is_cog:
            # COG logic: User says replace {symbology} and remove trailing slash
            tile_url = base_url.replace('{symbology}', symbology_key).rstrip('/')
        else:
            # Construct XYZ URL: {url}{symbology}/{z}/{x}/{y}.{format}
            # Following user's logic: ${tileService.url}${symbologyKey}/{z}/{x}/{y}.${tileService.format || 'png'}
            # We ensure base_url ends with / if it doesn't already
            xyz_base = base_url
            if not xyz_base.endswith('/'):
                xyz_base += '/'
            tile_url = f"{xyz_base}{symbology_key}/{{z}}/{{x}}/{{y}}.{fmt}"

        # Determine if it's an XYZ tile service or a single file
        # If it has tile placeholders, it's an XYZ service
        if "{z}" in tile_url or "{x}" in tile_url or "{y}" in tile_url:
            # Don't forget to encode the URL so that special characters are handled correctly
            encoded_url = urllib.parse.quote(tile_url, safe='/:?={}')
            uri = f"type=xyz&url={encoded_url}"
            provider = "wms"
        else:
            # Single file COG or other raster
            uri = tile_url
            if uri.startswith('http') and not uri.startswith('/vsicurl/'):
                uri = f"/vsicurl/{uri}"
            provider = "gdal"

        settings.log(f"Attempting to add remote raster: {map_layer.label}", Qgis.Info)
        settings.log(f"  - Format: {fmt} (is_cog: {is_cog})", Qgis.Info)
        settings.log(f"  - Symbology Key: {symbology_key}", Qgis.Info)
        settings.log(f"  - Constructed Tile URL: {tile_url}", Qgis.Info)
        settings.log(f"  - Final URI: {uri}", Qgis.Info)
        settings.log(f"  - Provider: {provider}", Qgis.Info)
        
        rOutput = QgsRasterLayer(uri, map_layer.label, provider)

        if rOutput and rOutput.isValid():
            QgsProject.instance().addMapLayer(rOutput, False)
            parentGroup.insertLayer(item.row(), rOutput)

            # Set extent and metadata
            bounds = tile_service.get('bounds')
            if bounds and len(bounds) == 4:
                try:
                    rect = QgsRectangle(bounds[0], bounds[1], bounds[2], bounds[3])
                    src_crs = QgsCoordinateReferenceSystem("EPSG:4326")
                    dest_crs = rOutput.crs()
                    if not dest_crs.isValid():
                        dest_crs = QgsCoordinateReferenceSystem("EPSG:3857")
                        rOutput.setCrs(dest_crs)
                    
                    if src_crs != dest_crs:
                        transform = QgsCoordinateTransform(src_crs, dest_crs, QgsProject.instance())
                        rect = transform.transformBoundingBox(rect)
                        
                    rOutput.setExtent(rect)

                    metadata = rOutput.metadata()
                    metadata.setIdentifier(map_layer.label)
                    metadata.setTitle(map_layer.label)
                    
                    spatialExtent = QgsLayerMetadata.SpatialExtent()
                    spatialExtent.extent = QgsReferencedRectangle(rect, dest_crs)
                    
                    extent = QgsLayerMetadata.Extent()
                    extent.setSpatialExtent([spatialExtent])
                    metadata.setExtent(extent)
                    
                    rOutput.setMetadata(metadata)
                    settings.log(f"  - Set extent: {rect.toString()}", Qgis.Info)
                except Exception as e:
                    settings.log(f'Error finalising metadata for raster: {e}', Qgis.Warning)

            # Transparency
            try:
                transparency = int(map_layer.bl_attr.get('transparency', 0))
                if transparency > 0:
                    rOutput.renderer().setOpacity((100 - transparency) / 100.0)
                    settings.log(f"  - Set transparency: {transparency}%", Qgis.Info)
            except Exception as e:
                settings.log(f'Error setting transparency for raster: {e}', Qgis.Warning)

            rOutput.triggerRepaint()
            settings.log(f"Successfully added remote raster layer: {map_layer.label}", Qgis.Info)
        else:
            settings.log(f'Failed to create valid remote raster layer for {map_layer.label}. isValid() is False.', Qgis.Critical)
            # Try a fallback without the provider if it failed with it
            if provider == "gdal":
                settings.log(f"Retrying without explicit 'gdal' provider...", Qgis.Info)
                rOutput = QgsRasterLayer(uri, map_layer.label)
                if rOutput and rOutput.isValid():
                    QgsProject.instance().addMapLayer(rOutput, False)
                    parentGroup.insertLayer(item.row(), rOutput)
                    settings.log(f"Success on retry without provider!", Qgis.Info)
                else:
                    settings.log(f"Fallback also failed.", Qgis.Critical)

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

    @staticmethod
    def remove_project_from_map(project_name):

        root = QgsProject.instance().layerTreeRoot()
        for group in [child for child in root.children() if child.nodeType() == 0]:
            if group.name() == project_name:
                root.removeChildNode(group)
