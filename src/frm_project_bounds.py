import json
import xml.etree.ElementTree as ET
from xml.dom import minidom

from PyQt5 import QtCore, QtGui, QtWidgets
from qgis.core import Qgis, QgsMessageLog, QgsProject, QgsVectorLayer, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsRectangle, QgsGeometry, QgsFeatureRequest, QgsMapLayer, QgsFeature, QgsVectorFileWriter, QgsCoordinateTransformContext


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
        self.chkUseSelected.toggled.connect(self.generate_output)
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
        layer: QgsVectorLayer = QgsProject.instance().mapLayer(layer_id)
        precision = self.spnPrecision.value()

        # First check if there are any features in the layer
        if self.chkUseSelected.isChecked():
            if len(layer.selectedFeatureIds())== 0:
                self.txtOutput.setPlainText("No features selected in layer")
                self.btnCopy.setEnabled(False)
                return
        
        if layer.featureCount() == 0:
            self.txtOutput.setPlainText("No features selected in layer")
            self.btnCopy.setEnabled(False)
            return

        bounds = self.get_layer_bounds(layer, use_selected=self.chkUseSelected.isChecked())

        if self.rdoXML.isChecked():
            output = self.generate_xml(bounds, precision, self.chkIncludeBoundsFile.isChecked())
        else:
            output = self.generate_json(bounds, precision, self.chkIncludeBoundsFile.isChecked())

        self.txtOutput.setPlainText(output)
        if output is not None:
            self.btnCopy.setEnabled(True)

    def get_layer_bounds(self, layer: QgsVectorLayer, use_selected: bool=False) -> QgsRectangle:
        
        # Given we need typically this information in WGS84, transform the data into this project if the source layer is in another projection.
        if layer.crs().authid() != 'EPSG:4326':
            scratch_layer = layer.clone()
            epsg4326 = QgsCoordinateReferenceSystem(4326)
            scratch_layer.setCrs(epsg4326)
            transform = QgsCoordinateTransform(layer.crs(), epsg4326, QgsProject.instance())
            feats = []
            bounds = QgsRectangle()
            feature_request = QgsFeatureRequest()
            if use_selected:
                feature_request.setFilterFids(layer.selectedFeatureIds())
            for f in layer.getFeatures(feature_request):
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
    
    def generate_json(self, bounds: QgsRectangle, precision: int, include_bounds_file: bool = True):

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

        if include_bounds_file:
            project_bounds["ProjectBounds"]["Path"] = "project_bounds.geojson"

        return json.dumps(project_bounds, indent=4)
    
    def copy_output(self):
        # Copy to clipboard
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(self.txtOutput.toPlainText())
        self.btnCopy.setText("Copied!")

    def btn_generate_bounds_file_clicked(self):
        
        layer: QgsMapLayer = QgsProject.instance().mapLayer(self.cmbLayer.currentData())
        crs = layer.crs()
        feature_request = QgsFeatureRequest()
        if self.chkUseSelected.isChecked():
            feature_request.setFilterFids(layer.selectedFeatureIds())

        transform = None
        reverse_transform = None
        
        # Initialize an empty geometry
        geom = QgsGeometry()
        # Combine all geometries into a single multipart geometry
        
        if crs.isGeographic():
            # Find a suitable UTM zone for the centroid of the layer
            centroid = self.get_layer_bounds(layer, use_selected=self.chkUseSelected.isChecked()).center()
            utm_zone = int((centroid.x() + 180) / 6) + 1
            utm_crs = QgsCoordinateReferenceSystem(f'EPSG:326{utm_zone:02d}')
            # Transform the layer to the UTM CRS
            transform = QgsCoordinateTransform(crs, utm_crs, QgsProject.instance())
            reverse_transform = QgsCoordinateTransform(utm_crs, crs, QgsProject.instance())
            
        for f in layer.getFeatures(feature_request):
            g = f.geometry()
            if transform is not None:
                g.transform(transform)
            if geom.isEmpty():
                geom = g
            else:
                geom = geom.combine(g)

        # OK, now we need to run some simplification to reduce the number of vertices so that the file size is not larger than the specified limit
        
        simplify_factor = 0.0001  # This is a starting point, you may need to adjust it based on the file size limit
        geom: QgsGeometry = geom.simplify(simplify_factor)
        # Check the file size of the geometry
        file_size_limit = self.spnFileSize.value() * 1024  # Convert to bytes
        file_size: str = geom.asJson().encode('utf-8')
        if len(file_size) > file_size_limit:
            # If the file size is larger than the limit, we need to simplify further
            # This is a simple example, you may need to implement a more sophisticated algorithm
            while len(file_size) > file_size_limit:
                simplify_factor *= 2
                geom: QgsGeometry = geom.simplify(simplify_factor)
                file_size: str = geom.asJson().encode('utf-8')
                # Check if the geometry is empty after simplification
                if geom.isEmpty():
                    break

        # Transform the geometry to WGS84 if necessary
        if reverse_transform is not None:
            geom.transform(reverse_transform)

        # Initialize the GeoJSON layer
        geojson_layer = QgsVectorLayer("Polygon?crs=EPSG:4326", "Project Bounds", "memory")
        feature = QgsFeature()
        feature.setGeometry(geom)
        geojson_layer.dataProvider().addFeatures([feature])
        geojson_layer.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))

        # Save the layer to a temporary file to calculate the actual file size
        temp_file = QtCore.QTemporaryFile()
        temp_file.open()
        temp_file_path = temp_file.fileName()

        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "GeoJSON"
        options.fileEncoding = "UTF-8"

        error = QgsVectorFileWriter.writeAsVectorFormatV3(
            geojson_layer,
            temp_file_path,
            QgsCoordinateTransformContext(),
            options
        )

        if error != QgsVectorFileWriter.NoError:
            QgsMessageLog.logMessage(f"Error saving temporary GeoJSON file: {error}", "Project Bounds", Qgis.Critical)
            return

        # Check the file size of the temporary file
        file_size_limit = self.spnFileSize.value() * 1024  # Convert to bytes
        buffer_factor = 1.1  # Add a 10% buffer to account for metadata and formatting
        adjusted_file_size_limit = file_size_limit * buffer_factor
        actual_file_size = temp_file.size()

        # Simplify the geometry further if the file size exceeds the adjusted limit
        while actual_file_size > adjusted_file_size_limit:
            simplify_factor *= 2
            geom = geom.simplify(simplify_factor)
            feature.setGeometry(geom)
            geojson_layer.dataProvider().addFeatures([feature])

            # Save the simplified geometry to the temporary file again
            error = QgsVectorFileWriter.writeAsVectorFormatV3(
                geojson_layer,
                temp_file_path,
                QgsCoordinateTransformContext(),
                options
            )

            if error != QgsVectorFileWriter.NoError:
                QgsMessageLog.logMessage(f"Error saving temporary GeoJSON file: {error}", "Project Bounds", Qgis.Critical)
                return

            actual_file_size = temp_file.size()

        # Save the final GeoJSON file
        out_file = QtWidgets.QFileDialog.getSaveFileName(self, "Save Project Bounds GeoJSON", "project_bounds", "GeoJSON Files (*.geojson)")
        if not out_file[0]:
            return

        error = QgsVectorFileWriter.writeAsVectorFormatV3(
            geojson_layer,
            out_file[0],
            QgsCoordinateTransformContext(),
            options
        )

        if error != QgsVectorFileWriter.NoError:
            QgsMessageLog.logMessage(f"Error saving GeoJSON file: {error}", "Project Bounds", Qgis.Critical)
            return


    def setupUi(self):
        self.setWindowTitle("Project Bounds")
        self.resize(300, 450)

        vertLayout = QtWidgets.QVBoxLayout(self)
        self.setLayout(vertLayout)
        
        gridLayout = QtWidgets.QGridLayout(self)
        vertLayout.addLayout(gridLayout)

        self.lblLayer = QtWidgets.QLabel("Layer")
        gridLayout.addWidget(self.lblLayer, 0, 0)

        self.cmbLayer = QtWidgets.QComboBox()
        gridLayout.addWidget(self.cmbLayer, 0, 1)

        self.chkUseSelected = QtWidgets.QCheckBox("Use selected features only")
        gridLayout.addWidget(self.chkUseSelected, 1, 0)

        self.lblPrecision = QtWidgets.QLabel("Precision")
        gridLayout.addWidget(self.lblPrecision, 2, 0)

        self.spnPrecision = QtWidgets.QSpinBox()
        gridLayout.addWidget(self.spnPrecision, 3, 1)

        # Create a button group for XML/JSON radio buttons
        self.outputFormatGroup = QtWidgets.QButtonGroup(self)

        horiz_layout_rdo = QtWidgets.QHBoxLayout()
        gridLayout.addLayout(horiz_layout_rdo, 4, 0, 1, 2)

        self.rdoXML = QtWidgets.QRadioButton("XML")
        horiz_layout_rdo.addWidget(self.rdoXML)
        self.outputFormatGroup.addButton(self.rdoXML)

        self.rdoJSON = QtWidgets.QRadioButton("JSON")
        horiz_layout_rdo.addWidget(self.rdoJSON)
        self.outputFormatGroup.addButton(self.rdoJSON)

        hspacer = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        horiz_layout_rdo.addItem(hspacer)

        self.txtOutput = QtWidgets.QTextEdit()
        self.txtOutput.setReadOnly(True)
        gridLayout.addWidget(self.txtOutput, 4, 0, 1, 2)

        self.chkIncludeBoundsFile = QtWidgets.QCheckBox("Include Project Bounds geojson file")
        gridLayout.addWidget(self.chkIncludeBoundsFile, 5, 0, 1, 2)

        self.lblFileSize = QtWidgets.QLabel("Maximum File Size")
        gridLayout.addWidget(self.lblFileSize, 6, 0)

        self.spnFileSize = QtWidgets.QSpinBox()
        self.spnFileSize.setMinimum(1)
        self.spnFileSize.setMaximum(10000)
        self.spnFileSize.setSingleStep(10)
        self.spnFileSize.setValue(200)
        self.spnFileSize.setSuffix(" kb")
        self.spnFileSize.setEnabled(False)
        self.chkIncludeBoundsFile.toggled.connect(self.spnFileSize.setEnabled)
        gridLayout.addWidget(self.spnFileSize, 6, 1)

        self.btnGenerateBoundsFile = QtWidgets.QPushButton("Save Bounds File")
        self.btnGenerateBoundsFile.setEnabled(False)
        self.chkIncludeBoundsFile.toggled.connect(self.btnGenerateBoundsFile.setEnabled)
        self.btnGenerateBoundsFile.clicked.connect(self.btn_generate_bounds_file_clicked)
        gridLayout.addWidget(self.btnGenerateBoundsFile, 10, 1, 1, 1)

        horiz_layout_btn = QtWidgets.QHBoxLayout()
        vertLayout.addLayout(horiz_layout_btn)

        spacer = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        horiz_layout_btn.addItem(spacer)

        self.btnCopy = QtWidgets.QPushButton("Copy")
        self.btnCopy.setEnabled(False)
        horiz_layout_btn.addWidget(self.btnCopy)

        self.btnClose = QtWidgets.QPushButton("Close")
        horiz_layout_btn.addWidget(self.btnClose)
