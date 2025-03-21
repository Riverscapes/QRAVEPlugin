import json
import xml.etree.ElementTree as ET
from xml.dom import minidom

from PyQt5 import QtCore, QtGui, QtWidgets
from qgis.core import QgsProject, QgsVectorLayer, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsRectangle


class FrmProjectBounds(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super(FrmProjectBounds, self).__init__(parent)
        self.setupUi()

        # Add all layers to the combo box, layer name as text, layer id as data
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer):
                self.cmbLayer.addItem(layer.name(), layer.id())

        self.spnPrecision.setValue(7)
        self.rdoXML.setChecked(True)

        self.cmbLayer.currentIndexChanged.connect(self.generate_output)
        self.spnPrecision.valueChanged.connect(self.generate_output)
        self.chkIncludeBoundsFile.toggled.connect(self.generate_output)
        self.rdoXML.toggled.connect(self.generate_output)
        self.rdoJSON.toggled.connect(self.generate_output)
        self.btnCopy.clicked.connect(self.copy_output)
        self.btnClose.clicked.connect(self.close)

        self.generate_output()

    def generate_output(self):

        self.btnCopy.setEnabled(False)
        self.btnCopy.setText("Copy")
        self.txtOutput.setPlainText("")

        layer_id = self.cmbLayer.currentData()
        layer = QgsProject.instance().mapLayer(layer_id)
        precision = self.spnPrecision.value()

        # First check if there are any features in the layer
        if layer.featureCount() == 0:
            self.txtOutput.setPlainText("No features selected in layer")
            self.btnCopy.setEnabled(False)
            return

        bounds = self.get_layer_bounds(layer)

        if self.rdoXML.isChecked():
            output = self.generate_xml(bounds, precision, self.chkIncludeBoundsFile.isChecked())
        else:
            output = self.generate_json(bounds, precision)

        self.txtOutput.setPlainText(output)
        if output is not None:
            self.btnCopy.setEnabled(True)

    def get_layer_bounds(self, layer: QgsVectorLayer) -> QgsRectangle:
        
        # Given we need typically this information in WGS84, transform the data into this project if the source layer is in another projection.
        if layer.crs().authid() != 'EPSG:4326':
            scratch_layer = layer.clone()
            epsg4326 = QgsCoordinateReferenceSystem(4326)
            scratch_layer.setCrs(epsg4326)
            transform = QgsCoordinateTransform(layer.crs(), epsg4326, QgsProject.instance())
            feats = []
            bounds = QgsRectangle()
            for f in layer.getFeatures():
                g = f.geometry()
                g.transform(transform)
                f.setGeometry(g)
                bounds.combineExtentWith(g.boundingBox())
                feats.append(f)
            scratch_layer.dataProvider().addFeatures(feats)
            layer = scratch_layer
        else:
            bounds = layer.extent()

        return bounds

    def generate_xml(self, bounds: QgsRectangle, precision: int, include_bounds_file: bool = True):
        
        centroid = bounds.center()

        project_bounds = ET.Element("ProjectBounds")

        centroid_elem = ET.SubElement(project_bounds, "Centroid")
        lat_elem = ET.SubElement(centroid_elem, "Lat")
        lat_elem.text = f"{centroid.y():.{precision}f}"
        lng_elem = ET.SubElement(centroid_elem, "Lng")
        lng_elem.text = f"{centroid.x():.{precision}f}"

        bounding_box_elem = ET.SubElement(project_bounds, "BoundingBox")
        min_lng_elem = ET.SubElement(bounding_box_elem, "MinLng")
        min_lng_elem.text = f"{bounds.xMinimum():.{precision}f}"
        min_lat_elem = ET.SubElement(bounding_box_elem, "MinLat")
        min_lat_elem.text = f"{bounds.yMinimum():.{precision}f}"
        max_lng_elem = ET.SubElement(bounding_box_elem, "MaxLng")
        max_lng_elem.text = f"{bounds.xMaximum():.{precision}f}"
        max_lat_elem = ET.SubElement(bounding_box_elem, "MaxLat")
        max_lat_elem.text = f"{bounds.yMaximum():.{precision}f}"

        if include_bounds_file:
            path_elem = ET.SubElement(project_bounds, "Path")
            path_elem.text = "project_bounds.geojson"

        xml_str = ET.tostring(project_bounds, encoding='unicode', method='xml')
        pretty_xml_str = minidom.parseString(xml_str).toprettyxml(indent="  ")
        # Remove the XML declaration
        pretty_xml_str = '\n'.join(pretty_xml_str.split('\n')[1:])
        
        return pretty_xml_str
    
    def generate_json(self, bounds: QgsRectangle, precision: int):

        centroid = bounds.center()

        project_bounds = {
            "ProjectBounds": {
                "Centroid": {
                    "Lat": round(centroid.y(), precision), 
                    "Lng": round(centroid.x(), precision)},
                "BoundingBox": {
                    "MinLng": round(bounds.xMinimum(), precision),
                    "MinLat": round(bounds.yMinimum(), precision),
                    "MaxLng": round(bounds.xMaximum(), precision),
                    "MaxLat": round(bounds.yMaximum(), precision)}
            }
        }

        return json.dumps(project_bounds, indent=4)
    
    def copy_output(self):
        
        # Copy to clipboard
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(self.txtOutput.toPlainText())
        self.btnCopy.setText("Copied!")


    def setupUi(self):

        self.setWindowTitle("Project Bounds")
        self.resize(300, 350)

        vertLayout = QtWidgets.QVBoxLayout(self)
        self.setLayout(vertLayout)
        
        gridLayout = QtWidgets.QGridLayout(self)
        vertLayout.addLayout(gridLayout)

        self.lblLayer = QtWidgets.QLabel("Layer")
        gridLayout.addWidget(self.lblLayer, 0, 0)

        self.cmbLayer = QtWidgets.QComboBox()
        gridLayout.addWidget(self.cmbLayer, 0, 1)

        self.lblPrecision = QtWidgets.QLabel("Precision")
        gridLayout.addWidget(self.lblPrecision, 1, 0)

        self.spnPrecision = QtWidgets.QSpinBox()
        gridLayout.addWidget(self.spnPrecision, 1, 1)

        horiz_layout_rdo = QtWidgets.QHBoxLayout()
        gridLayout.addLayout(horiz_layout_rdo, 2, 0, 1, 2)

        self.rdoXML = QtWidgets.QRadioButton("XML")
        horiz_layout_rdo.addWidget(self.rdoXML)

        self.rdoJSON = QtWidgets.QRadioButton("JSON")
        horiz_layout_rdo.addWidget(self.rdoJSON)

        hspacer = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        horiz_layout_rdo.addItem(hspacer)

        self.txtOutput = QtWidgets.QTextEdit()
        self.txtOutput.setReadOnly(True)
        vertLayout.addWidget(self.txtOutput)

        self.chkIncludeBoundsFile = QtWidgets.QCheckBox("Include bounds file reference in xml output")
        self.chkIncludeBoundsFile.setChecked(True)
        vertLayout.addWidget(self.chkIncludeBoundsFile)

        horiz_layout_btn = QtWidgets.QHBoxLayout()
        vertLayout.addLayout(horiz_layout_btn)

        spacer = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        horiz_layout_btn.addItem(spacer)

        self.btnCopy = QtWidgets.QPushButton("Copy")
        self.btnCopy.setEnabled(False)
        horiz_layout_btn.addWidget(self.btnCopy)

        self.btnClose = QtWidgets.QPushButton("Close")
        horiz_layout_btn.addWidget(self.btnClose)




        




