# -*- coding: utf-8 -*-
"""
/***************************************************************************
 RiverscapesToolbarViewer
                                 A QGIS plugin
 this is the RiverscapesToolbarViewer plugin
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2021-04-07
        copyright            : (C) 2021 by NAR
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


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load RiverscapesToolbarViewer class from file RiverscapesToolbarViewer.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from src.lib.RiverscapesToolbarViewer import RiverscapesToolbarViewer
    return RiverscapesToolbarViewer(iface)
