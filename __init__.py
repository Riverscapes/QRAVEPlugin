# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QRAVE
                                 A QGIS plugin
 Explore symbolized Riverscapes projects
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2021-04-13
        copyright            : (C) 2021 by North Arrow Research
        email                : info@northarrowresearch.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""
import os
import json
# noinspection PyPep8Naming
# config is where we keep our constants and configuration strings


def classFactory(iface):  # pylint: disable=invalid-name
    """Load QRAVE class from file QRAVE.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    # Yeah, this is annoying but QGIS needs it so....
    # pylint: disable=import-error
    from .src.qrave_toolbar import QRAVE
    return QRAVE(iface)
