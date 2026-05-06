from __future__ import annotations

import math

from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsPointXY, QgsProject


def get_zoom_level(canvas) -> int:
    # Get current extent and CRS
    extent = canvas.extent()
    src_crs = canvas.mapSettings().destinationCrs()
    dest_crs = QgsCoordinateReferenceSystem("EPSG:3857")

    # Transform extent to EPSG:3857 if needed
    if src_crs != dest_crs:
        transform = QgsCoordinateTransform(src_crs, dest_crs, QgsProject.instance())
        extent = transform.transformBoundingBox(extent)

    width = extent.width()
    # 40075016.68557849 is the width of the world in meters in EPSG:3857
    zoom = round(math.log(40075016.68557849 / width) / math.log(2))
    return zoom


def get_map_center(canvas) -> QgsPointXY:
    # Get the center of the map in the current CRS
    extent = canvas.extent()
    src_crs = canvas.mapSettings().destinationCrs()
    dest_crs = QgsCoordinateReferenceSystem("EPSG:4326")

    # Transform extent to EPSG:4326 if needed
    if src_crs != dest_crs:
        transform = QgsCoordinateTransform(src_crs, dest_crs, QgsProject.instance())
        extent = transform.transformBoundingBox(extent)

    center = extent.center()
    return center
