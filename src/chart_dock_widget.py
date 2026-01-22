# -*- coding: utf-8 -*-
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
from qgis.PyQt.QtWidgets import (QDockWidget, QVBoxLayout, QWidget, QLabel, QComboBox, QPushButton, QMessageBox,
                                 QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView)
from qgis.core import (QgsMapLayer, QgsVectorLayer, QgsVectorTileLayer, QgsFeatureRequest, Qgis, QgsGeometry,
                       QgsSelectionContext, QgsCoordinateTransform, QgsProject)
from qgis.utils import iface

import matplotlib
matplotlib.use('Qt5Agg')


class ChartDockWidget(QDockWidget):
    def __init__(self, iface, parent=None):
        super(ChartDockWidget, self).__init__(parent)
        self.iface = iface
        self.setWindowTitle("DGO Analytics")
        self.setObjectName("DGOAnalyticsDock")

        # Main widget container
        self.main_widget = QWidget()
        self.setWidget(self.main_widget)
        self.layout = QVBoxLayout(self.main_widget)

        # Chart selector
        self.chart_selector = QComboBox()
        self.chart_selector.addItem("Stream Length by FCode")
        self.chart_selector.addItem("Existing Beaver Dam Capacity")
        self.chart_selector.currentIndexChanged.connect(self.on_combo_changed)
        self.layout.addWidget(self.chart_selector)

        # Tab Widget
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)

        # Tab 1: Chart
        self.chart_tab = QWidget()
        self.chart_layout = QVBoxLayout(self.chart_tab)
        self.tabs.addTab(self.chart_tab, "Chart")

        # Tab 2: Tabular Results
        self.table_tab = QWidget()
        self.table_layout = QVBoxLayout(self.table_tab)
        self.tabs.addTab(self.table_tab, "Tabular Results")

        # Matplotlib setup (moved to chart tab)
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        self.chart_layout.addWidget(self.canvas)

        self.ax = self.figure.add_subplot(111)
        self.ax.set_title("Select features to see statistics")

        # Table setup
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(2)
        self.table_widget.setHorizontalHeaderLabels(["FCode", "Value"])
        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.table_layout.addWidget(self.table_widget)

        self.current_layer = None

        # Connect to map canvas selection change
        self.iface.mapCanvas().selectionChanged.connect(self.on_selection_changed)

    def on_combo_changed(self, index):
        if self.current_layer:
            self.update_chart(self.current_layer)

    def on_selection_changed(self, layer):
        """
        Slot called when selection changes on a layer.
        """
        # We only care if the layer is the DGO layer or if the user wants us to track selection on any layer
        # The prompt says: "refreshes when the CONUS DGO layer selection changes"
        if layer.name() == "CONUS DGO Layer":
            self.current_layer = layer
            self.update_chart(layer)

    def update_chart(self, layer):
        self.ax.clear()
        self.ax.axis('on')  # Reset axis visibility

        # Determine what to chart based on combobox
        chart_mode = self.chart_selector.currentText()
        if chart_mode == "Existing Beaver Dam Capacity":
            value_field = 'brat_capacity'
            y_label = 'Beaver Dam Capacity'
            title = 'Existing Beaver Dam Capacity by FCode'
        else:
            value_field = 'centerline_length'
            y_label = 'Total Centerline Length'
            title = 'Centerline Length by FCode'

        # Data accumulation
        # Expecting attributes: value_field, 'fcode'
        stats = {}

        # Verify if we can get selected features
        selected_features = []
        try:
            # For QgsVectorLayer
            if isinstance(layer, QgsVectorLayer):
                selected_features = layer.selectedFeatures()
            # For QgsVectorTileLayer (Experimental support or future proofing)
            elif isinstance(layer, QgsVectorTileLayer):
                # NOTE: QGIS API regarding Vector Tile selection is limited/evolving.
                # Assuming standard API if available, otherwise this might need custom handling
                # which is out of scope without specific API availability.
                # Currently QgsVectorTileLayer does not expose selectedFeatures() iterator directly in stable API
                # as of typical QGIS 3.x
                if hasattr(layer, 'selectedFeatures'):
                    selected_features = layer.selectedFeatures()
                else:
                    self.ax.axis('off')
                    self.ax.text(0.5, 0.5, "Selection not supported on Vector Tiles\nwithout specific API support.",
                                 ha='center', va='center')
                    self.canvas.draw()
                    self.table_widget.setRowCount(0)
                    return
            else:
                return
        except Exception as e:
            self.ax.axis('off')
            self.ax.text(0.5, 0.5, f"Error accessing features:\n{str(e)}", ha='center', va='center')
            self.canvas.draw()
            self.table_widget.setRowCount(0)
            return

        if not selected_features:
            self.ax.text(0.5, 0.5, "No features selected", ha='center', va='center')
            self.canvas.draw()
            self.table_widget.setRowCount(0)
            return

        for feature in selected_features:
            try:
                fcode = feature['fcode']
                val = feature[value_field]

                # Handle types
                if val is None:
                    continue

                val = float(val)

                # Ensure fcode is a string for consistent sorting and display
                if fcode is None:
                    fcode = "Unknown"
                else:
                    fcode = str(fcode)

                if fcode in stats:
                    stats[fcode] += val
                else:
                    stats[fcode] = val
            except KeyError:
                # If fields don't exist
                pass
            except Exception:
                pass

        if not stats:
            self.ax.axis('off')
            self.ax.text(0.5, 0.5, f"No data found in selection\n(Missing 'fcode' or '{value_field}')",
                         ha='center', va='center')
            self.table_widget.setRowCount(0)
        else:
            # Sort by fcode (key)
            codes = sorted(stats.keys())
            values = [stats[c] for c in codes]

            # Update Table
            self.table_widget.setRowCount(len(codes))
            self.table_widget.setHorizontalHeaderLabels(['FCode', y_label])
            for row, (code, val) in enumerate(zip(codes, values)):
                self.table_widget.setItem(row, 0, QTableWidgetItem(code))
                # Format value to 2 decimal places if it's a number
                self.table_widget.setItem(row, 1, QTableWidgetItem(f"{val:.2f}"))

            # Create bar chart
            self.ax.bar(codes, values)
            self.ax.set_xlabel('FCode', fontsize=8)
            self.ax.set_ylabel(y_label, fontsize=8)
            self.ax.set_title(title, fontsize=10)
            self.ax.tick_params(axis='both', which='major', labelsize=7)

            # Grid configuration
            self.ax.minorticks_on()
            self.ax.grid(which='major', color='#DDDDDD', linestyle='-', linewidth=0.5)
            self.ax.grid(which='minor', color='#EEEEEE', linestyle=':', linewidth=0.5)
            self.ax.set_axisbelow(True)

            # Rotate labels if needed
            plt.setp(self.ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

            self.figure.tight_layout()

        self.canvas.draw()
