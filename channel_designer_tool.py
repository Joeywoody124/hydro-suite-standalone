"""
Channel Designer Tool for Hydro Suite
Trapezoidal channel cross-section generator with SWMM integration
Version 2.0 - January 2025

STANDALONE SCRIPT VERSION
Repository: https://github.com/Joeywoody124/hydro-suite-standalone

Changelog v2.0:
- Added GIS Layer Import tab for loading channels from vector layers
- Supports import from sample_channels.gpkg and similar layers
- Added Manning's n and slope fields for capacity calculations
- Added capacity (Q) calculation using Manning's equation
"""

import os
import csv
import json
import traceback
from pathlib import Path
from typing import Optional, Tuple, Callable, Dict, Any, List

from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QMessageBox, QScrollArea, QFrame, QGroupBox, QDoubleSpinBox,
    QSpinBox, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QTextEdit, QTabWidget, QFileDialog, QCheckBox, QComboBox
)
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QFont, QPixmap, QPainter, QPen, QBrush

from qgis.core import QgsProject, QgsVectorLayer, QgsWkbTypes

# Import our shared components
from hydro_suite_interface import HydroToolInterface, LayerSelectionMixin
from shared_widgets import (
    LayerFieldSelector, DirectorySelector, ProgressLogger, ValidationPanel
)


class ChannelGeometry:
    """Class to handle trapezoidal channel geometry calculations"""
    
    def __init__(self, depth: float, bottom_width: float, left_slope: float, 
                 right_slope: float, ref_elevation: float = 0.0,
                 mannings_n: float = 0.035, channel_slope: float = 0.005):
        """
        Initialize channel geometry
        
        Args:
            depth: Channel depth (ft)
            bottom_width: Bottom width (ft)
            left_slope: Left side slope (horizontal:1 vertical)
            right_slope: Right side slope (horizontal:1 vertical)
            ref_elevation: Reference bottom elevation (ft)
            mannings_n: Manning's roughness coefficient
            channel_slope: Channel bed slope (ft/ft)
        """
        self.depth = depth
        self.bottom_width = bottom_width
        self.left_slope = left_slope
        self.right_slope = right_slope
        self.ref_elevation = ref_elevation
        self.mannings_n = mannings_n
        self.channel_slope = channel_slope
        
    def calculate_points(self) -> List[Dict[str, float]]:
        """Calculate the four corner points of the trapezoidal channel"""
        points = []
        
        # Left bottom point
        left_bottom_offset = -self.bottom_width / 2
        points.append({
            'offset': left_bottom_offset,
            'elevation': self.ref_elevation,
            'description': 'Left Bottom'
        })
        
        # Right bottom point
        right_bottom_offset = self.bottom_width / 2
        points.append({
            'offset': right_bottom_offset,
            'elevation': self.ref_elevation,
            'description': 'Right Bottom'
        })
        
        # Left top point
        left_top_offset = -self.bottom_width / 2 - self.left_slope * self.depth
        left_top_elevation = self.ref_elevation + self.depth
        points.append({
            'offset': left_top_offset,
            'elevation': left_top_elevation,
            'description': 'Left Top'
        })
        
        # Right top point
        right_top_offset = self.bottom_width / 2 + self.right_slope * self.depth
        right_top_elevation = self.ref_elevation + self.depth
        points.append({
            'offset': right_top_offset,
            'elevation': right_top_elevation,
            'description': 'Right Top'
        })
        
        # Sort by offset for SWMM compatibility
        return sorted(points, key=lambda p: p['offset'])
        
    def get_swmm_format(self) -> str:
        """Get points in SWMM cross-section format"""
        points = self.calculate_points()
        lines = []
        for point in points:
            lines.append(f"{point['offset']:.4f} {point['elevation']:.4f}")
        return "\n".join(lines)
        
    def calculate_properties(self) -> Dict[str, float]:
        """Calculate hydraulic properties"""
        # Top width at full depth
        top_width = self.bottom_width + (self.left_slope + self.right_slope) * self.depth
        
        # Cross-sectional area at full depth
        area = (self.bottom_width + top_width) / 2 * self.depth
        
        # Wetted perimeter at full depth
        left_side_length = self.depth * (1 + self.left_slope**2)**0.5
        right_side_length = self.depth * (1 + self.right_slope**2)**0.5
        wetted_perimeter = self.bottom_width + left_side_length + right_side_length
        
        # Hydraulic radius
        hydraulic_radius = area / wetted_perimeter if wetted_perimeter > 0 else 0
        
        # Calculate velocity and capacity using Manning's equation
        if self.mannings_n > 0 and self.channel_slope > 0 and hydraulic_radius > 0:
            velocity = (1.49 / self.mannings_n) * (hydraulic_radius ** (2.0/3.0)) * (self.channel_slope ** 0.5)
            capacity = velocity * area
        else:
            velocity = 0.0
            capacity = 0.0
        
        return {
            'top_width': top_width,
            'area': area,
            'wetted_perimeter': wetted_perimeter,
            'hydraulic_radius': hydraulic_radius,
            'side_slopes': f"{self.left_slope}:1 / {self.right_slope}:1",
            'velocity': velocity,
            'capacity': capacity,
            'mannings_n': self.mannings_n,
            'channel_slope': self.channel_slope
        }


class ChannelVisualization(QWidget):
    """Widget to visualize channel cross-section"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.geometry = None
        self.setMinimumSize(400, 300)
        
    def set_geometry(self, geometry: ChannelGeometry):
        """Set channel geometry to visualize"""
        self.geometry = geometry
        self.update()
        
    def paintEvent(self, event):
        """Paint the channel cross-section"""
        if not self.geometry:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Get widget dimensions
        width = self.width() - 40
        height = self.height() - 40
        
        # Calculate scale
        points = self.geometry.calculate_points()
        if not points:
            return
            
        min_offset = min(p['offset'] for p in points)
        max_offset = max(p['offset'] for p in points)
        min_elev = min(p['elevation'] for p in points)
        max_elev = max(p['elevation'] for p in points)
        
        offset_range = max_offset - min_offset
        elev_range = max_elev - min_elev
        
        if offset_range == 0 or elev_range == 0:
            return
            
        # Scale to fit widget
        scale_x = width / (offset_range * 1.2)
        scale_y = height / (elev_range * 1.2)
        scale = min(scale_x, scale_y)
        
        # Center the drawing
        center_x = self.width() / 2
        center_y = self.height() / 2
        
        # Convert points to screen coordinates
        screen_points = []
        for point in points:
            x = center_x + (point['offset'] - (min_offset + max_offset) / 2) * scale
            y = center_y - (point['elevation'] - (min_elev + max_elev) / 2) * scale
            screen_points.append((x, y))
        
        # Draw channel outline
        painter.setPen(QPen(Qt.blue, 2))
        painter.setBrush(QBrush(Qt.lightGray))
        
        # Draw the trapezoidal shape
        if len(screen_points) >= 4:
            left_top = screen_points[0]
            right_top = screen_points[-1]
            
            bottom_points = [p for p in points if abs(p['elevation'] - min_elev) < 0.001]
            if len(bottom_points) >= 2:
                bottom_screen = [(center_x + (p['offset'] - (min_offset + max_offset) / 2) * scale,
                                center_y - (p['elevation'] - (min_elev + max_elev) / 2) * scale)
                               for p in bottom_points]
                bottom_screen.sort(key=lambda p: p[0])
                left_bottom = bottom_screen[0]
                right_bottom = bottom_screen[-1]
                
                from qgis.PyQt.QtGui import QPolygonF
                from qgis.PyQt.QtCore import QPointF
                
                polygon = QPolygonF([
                    QPointF(*left_top),
                    QPointF(*left_bottom),
                    QPointF(*right_bottom),
                    QPointF(*right_top)
                ])
                painter.drawPolygon(polygon)
        
        # Draw grid lines
        painter.setPen(QPen(Qt.gray, 1))
        painter.drawLine(int(center_x), 20, int(center_x), self.height() - 20)
        painter.drawLine(20, int(center_y), self.width() - 20, int(center_y))
        
        # Draw points and labels
        painter.setPen(QPen(Qt.red, 1))
        painter.setBrush(QBrush(Qt.red))
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)
        
        for i, (point, (x, y)) in enumerate(zip(points, screen_points)):
            painter.drawEllipse(int(x)-3, int(y)-3, 6, 6)
            label = f"({point['offset']:.1f}, {point['elevation']:.1f})"
            painter.setPen(QPen(Qt.black, 1))
            painter.drawText(int(x) + 5, int(y) - 5, label)
            painter.setPen(QPen(Qt.red, 1))


class ChannelDesignerTool(HydroToolInterface):
    """Channel Designer tool for creating trapezoidal channel cross-sections"""
    
    def __init__(self):
        super().__init__()
        self.name = "Channel Designer"
        self.description = "Design trapezoidal channel cross-sections for hydraulic modeling"
        self.category = "Hydraulic Design"
        self.version = "2.0"
        self.author = "Hydro Suite"
        
        # Tool properties
        self.channels = []
        self.current_geometry = None
        
        # GUI components
        self.validation_panel = None
        self.progress_logger = None
        self.visualization = None
        self.results_table = None
        self.swmm_output = None
        
        # Parameter controls
        self.depth_spin = None
        self.bottom_width_spin = None
        self.left_slope_spin = None
        self.right_slope_spin = None
        self.ref_elevation_spin = None
        self.channel_id_edit = None
        self.mannings_n_spin = None
        self.channel_slope_spin = None
        
        # GIS layer import controls
        self.layer_selector = None
        self.field_channel_id = None
        self.field_depth = None
        self.field_bottom_width = None
        self.field_side_slope = None
        self.field_mannings_n = None
        self.field_channel_slope = None
        
    def create_gui(self, parent_widget: QWidget) -> QWidget:
        """Create the Channel Designer GUI with tabbed interface"""
        tab_widget = QTabWidget(parent_widget)
        
        # Design tab (manual entry)
        design_tab = self.create_design_tab()
        tab_widget.addTab(design_tab, "Manual Design")
        
        # GIS Layer Import tab (NEW)
        gis_tab = self.create_gis_import_tab()
        tab_widget.addTab(gis_tab, "Import from Layer")
        
        # Batch CSV tab
        batch_tab = self.create_batch_tab()
        tab_widget.addTab(batch_tab, "Batch CSV")
        
        # Results tab
        results_tab = self.create_results_tab()
        tab_widget.addTab(results_tab, "Results")
        
        self.gui_widget = tab_widget
        return tab_widget
    
    def create_gis_import_tab(self) -> QWidget:
        """Create GIS layer import tab"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        main_widget = QWidget()
        scroll.setWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Title
        title = QLabel("<h3>Import Channels from GIS Layer</h3>")
        layout.addWidget(title)
        
        desc = QLabel(
            "Import channel geometry from a line layer (e.g., sample_channels.gpkg). "
            "Map the fields containing channel dimensions and hydraulic parameters."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666; margin-bottom: 15px;")
        layout.addWidget(desc)
        
        # Layer selection
        layer_frame = QFrame()
        layer_frame.setFrameStyle(QFrame.StyledPanel)
        layer_layout = QVBoxLayout(layer_frame)
        
        layer_title = QLabel("<b>Select Channel Layer</b>")
        layer_layout.addWidget(layer_title)
        
        self.layer_selector = LayerFieldSelector(
            "Channels Layer",
            default_field="Channel_ID",
            geometry_type=QgsWkbTypes.LineGeometry
        )
        layer_layout.addWidget(self.layer_selector)
        
        layout.addWidget(layer_frame)
        
        # Field mapping
        fields_frame = QFrame()
        fields_frame.setFrameStyle(QFrame.StyledPanel)
        fields_layout = QVBoxLayout(fields_frame)
        
        fields_title = QLabel("<b>Field Mapping</b>")
        fields_layout.addWidget(fields_title)
        
        # Channel ID field
        id_layout = QHBoxLayout()
        id_layout.addWidget(QLabel("Channel ID:"))
        self.field_channel_id = QComboBox()
        self.field_channel_id.setMinimumWidth(150)
        id_layout.addWidget(self.field_channel_id)
        id_layout.addStretch()
        fields_layout.addLayout(id_layout)
        
        # Depth field
        depth_layout = QHBoxLayout()
        depth_layout.addWidget(QLabel("Depth (ft):"))
        self.field_depth = QComboBox()
        self.field_depth.setMinimumWidth(150)
        depth_layout.addWidget(self.field_depth)
        depth_layout.addStretch()
        fields_layout.addLayout(depth_layout)
        
        # Bottom width field
        bw_layout = QHBoxLayout()
        bw_layout.addWidget(QLabel("Bottom Width (ft):"))
        self.field_bottom_width = QComboBox()
        self.field_bottom_width.setMinimumWidth(150)
        bw_layout.addWidget(self.field_bottom_width)
        bw_layout.addStretch()
        fields_layout.addLayout(bw_layout)
        
        # Side slope field
        ss_layout = QHBoxLayout()
        ss_layout.addWidget(QLabel("Side Slope (H:1V):"))
        self.field_side_slope = QComboBox()
        self.field_side_slope.setMinimumWidth(150)
        ss_layout.addWidget(self.field_side_slope)
        ss_layout.addStretch()
        fields_layout.addLayout(ss_layout)
        
        # Manning's n field
        n_layout = QHBoxLayout()
        n_layout.addWidget(QLabel("Manning's n:"))
        self.field_mannings_n = QComboBox()
        self.field_mannings_n.setMinimumWidth(150)
        n_layout.addWidget(self.field_mannings_n)
        n_layout.addStretch()
        fields_layout.addLayout(n_layout)
        
        # Channel slope field
        slope_layout = QHBoxLayout()
        slope_layout.addWidget(QLabel("Channel Slope (ft/ft):"))
        self.field_channel_slope = QComboBox()
        self.field_channel_slope.setMinimumWidth(150)
        slope_layout.addWidget(self.field_channel_slope)
        slope_layout.addStretch()
        fields_layout.addLayout(slope_layout)
        
        layout.addWidget(fields_frame)
        
        # Import button
        import_btn = QPushButton("Import Channels from Layer")
        import_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                padding: 12px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        import_btn.clicked.connect(self.import_from_layer)
        layout.addWidget(import_btn)
        
        # Progress logger
        self.gis_progress_logger = ProgressLogger()
        layout.addWidget(self.gis_progress_logger)
        
        layout.addStretch()
        
        # Connect layer change to field population
        self.layer_selector.layer_changed.connect(self.on_gis_layer_changed)
        
        return scroll
    
    def on_gis_layer_changed(self, layer):
        """Update field combos when GIS layer changes"""
        # Clear existing items
        for combo in [self.field_channel_id, self.field_depth, self.field_bottom_width,
                      self.field_side_slope, self.field_mannings_n, self.field_channel_slope]:
            combo.clear()
            combo.addItem("-- Select Field --", None)
        
        if not layer or not layer.isValid():
            return
        
        # Get field names
        field_names = [field.name() for field in layer.fields()]
        
        # Add fields to combos
        for field_name in field_names:
            for combo in [self.field_channel_id, self.field_depth, self.field_bottom_width,
                          self.field_side_slope, self.field_mannings_n, self.field_channel_slope]:
                combo.addItem(field_name, field_name)
        
        # Try to auto-select common field names
        field_map = {
            self.field_channel_id: ['Channel_ID', 'ChannelID', 'ID', 'NAME', 'Name'],
            self.field_depth: ['Depth_ft', 'Depth', 'DEPTH', 'D'],
            self.field_bottom_width: ['Bottom_W_ft', 'Bottom_Width', 'BOTTOM_W', 'BW', 'B'],
            self.field_side_slope: ['Side_Slope', 'SideSlope', 'SS', 'Z', 'SIDE_SLOPE'],
            self.field_mannings_n: ['Mannings_n', 'Manning_n', 'N', 'MANNINGS_N'],
            self.field_channel_slope: ['Slope_ftft', 'Slope', 'SLOPE', 'S', 'CH_SLOPE'],
        }
        
        for combo, candidates in field_map.items():
            for candidate in candidates:
                for i in range(combo.count()):
                    if combo.itemText(i).upper() == candidate.upper():
                        combo.setCurrentIndex(i)
                        break
                else:
                    continue
                break
        
        self.gis_progress_logger.log(f"Layer loaded: {layer.name()} ({len(field_names)} fields)")
    
    def import_from_layer(self):
        """Import channels from the selected GIS layer"""
        try:
            layer = self.layer_selector.get_selected_layer()
            if not layer or not layer.isValid():
                QMessageBox.warning(self.gui_widget, "No Layer", 
                                   "Please select a valid channel layer.")
                return
            
            # Get field mappings
            id_field = self.field_channel_id.currentData()
            depth_field = self.field_depth.currentData()
            bw_field = self.field_bottom_width.currentData()
            ss_field = self.field_side_slope.currentData()
            n_field = self.field_mannings_n.currentData()
            slope_field = self.field_channel_slope.currentData()
            
            # Validate required fields
            if not all([id_field, depth_field, bw_field, ss_field]):
                QMessageBox.warning(self.gui_widget, "Missing Fields",
                                   "Please map at least Channel ID, Depth, Bottom Width, and Side Slope fields.")
                return
            
            self.gis_progress_logger.log("Importing channels from layer...")
            
            imported = 0
            errors = 0
            
            for feature in layer.getFeatures():
                try:
                    channel_id = str(feature[id_field])
                    depth = float(feature[depth_field] or 0)
                    bottom_width = float(feature[bw_field] or 0)
                    side_slope = float(feature[ss_field] or 2.0)
                    
                    # Optional fields with defaults
                    mannings_n = float(feature[n_field]) if n_field and feature[n_field] else 0.035
                    channel_slope = float(feature[slope_field]) if slope_field and feature[slope_field] else 0.005
                    
                    # Validate
                    if depth <= 0 or bottom_width <= 0:
                        raise ValueError(f"Invalid depth or width for {channel_id}")
                    
                    # Create geometry (symmetric side slopes)
                    geometry = ChannelGeometry(
                        depth=depth,
                        bottom_width=bottom_width,
                        left_slope=side_slope,
                        right_slope=side_slope,
                        ref_elevation=100.0,  # Default reference
                        mannings_n=mannings_n,
                        channel_slope=channel_slope
                    )
                    
                    # Add to channels list (replace if exists)
                    self.channels = [ch for ch in self.channels if ch['id'] != channel_id]
                    self.channels.append({
                        'id': channel_id,
                        'geometry': geometry,
                        'properties': geometry.calculate_properties()
                    })
                    
                    imported += 1
                    
                except Exception as e:
                    errors += 1
                    self.gis_progress_logger.log(f"Error importing feature: {str(e)}", "warning")
            
            # Update results display
            self.update_results_display()
            
            self.gis_progress_logger.log(
                f"Import complete: {imported} channels imported, {errors} errors", 
                "success" if errors == 0 else "warning"
            )
            
            QMessageBox.information(
                self.gui_widget, "Import Complete",
                f"Imported {imported} channels from layer.\n"
                f"Errors: {errors}\n\n"
                "View results in the Results tab."
            )
            
        except Exception as e:
            self.gis_progress_logger.log(f"Import error: {str(e)}", "error")
            QMessageBox.critical(self.gui_widget, "Import Error", str(e))
        
    def create_design_tab(self) -> QWidget:
        """Create the main manual design tab"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        main_widget = QWidget()
        scroll.setWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Title
        title_label = QLabel(f"<h2>{self.name}</h2>")
        layout.addWidget(title_label)
        
        desc_label = QLabel(
            "<p>Design trapezoidal channel cross-sections for hydraulic modeling. "
            "Generate coordinate points for SWMM, HEC-RAS, and other modeling software.</p>"
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #555; margin-bottom: 10px;")
        layout.addWidget(desc_label)
        
        # Create horizontal layout for parameters and visualization
        main_h_layout = QHBoxLayout()
        
        # Left side - Parameters
        params_frame = QFrame()
        params_frame.setFrameStyle(QFrame.StyledPanel)
        params_frame.setMaximumWidth(350)
        params_layout = QVBoxLayout(params_frame)
        
        params_title = QLabel("<h3>Channel Parameters</h3>")
        params_layout.addWidget(params_title)
        
        # Channel ID
        id_layout = QHBoxLayout()
        id_layout.addWidget(QLabel("Channel ID:"))
        self.channel_id_edit = QLineEdit("Channel_1")
        id_layout.addWidget(self.channel_id_edit)
        params_layout.addLayout(id_layout)
        
        # Depth
        depth_layout = QHBoxLayout()
        depth_layout.addWidget(QLabel("Depth (ft):"))
        self.depth_spin = QDoubleSpinBox()
        self.depth_spin.setRange(0.1, 100.0)
        self.depth_spin.setValue(2.0)
        self.depth_spin.setSingleStep(0.1)
        self.depth_spin.setDecimals(2)
        depth_layout.addWidget(self.depth_spin)
        params_layout.addLayout(depth_layout)
        
        # Bottom width
        width_layout = QHBoxLayout()
        width_layout.addWidget(QLabel("Bottom Width (ft):"))
        self.bottom_width_spin = QDoubleSpinBox()
        self.bottom_width_spin.setRange(0.1, 100.0)
        self.bottom_width_spin.setValue(4.0)
        self.bottom_width_spin.setSingleStep(0.1)
        self.bottom_width_spin.setDecimals(2)
        width_layout.addWidget(self.bottom_width_spin)
        params_layout.addLayout(width_layout)
        
        # Left slope
        left_slope_layout = QHBoxLayout()
        left_slope_layout.addWidget(QLabel("Left Slope (H:1V):"))
        self.left_slope_spin = QDoubleSpinBox()
        self.left_slope_spin.setRange(0.0, 10.0)
        self.left_slope_spin.setValue(3.0)
        self.left_slope_spin.setSingleStep(0.1)
        self.left_slope_spin.setDecimals(1)
        left_slope_layout.addWidget(self.left_slope_spin)
        params_layout.addLayout(left_slope_layout)
        
        # Right slope
        right_slope_layout = QHBoxLayout()
        right_slope_layout.addWidget(QLabel("Right Slope (H:1V):"))
        self.right_slope_spin = QDoubleSpinBox()
        self.right_slope_spin.setRange(0.0, 10.0)
        self.right_slope_spin.setValue(3.0)
        self.right_slope_spin.setSingleStep(0.1)
        self.right_slope_spin.setDecimals(1)
        right_slope_layout.addWidget(self.right_slope_spin)
        params_layout.addLayout(right_slope_layout)
        
        # Reference elevation
        elev_layout = QHBoxLayout()
        elev_layout.addWidget(QLabel("Reference Elevation (ft):"))
        self.ref_elevation_spin = QDoubleSpinBox()
        self.ref_elevation_spin.setRange(-1000.0, 1000.0)
        self.ref_elevation_spin.setValue(100.0)
        self.ref_elevation_spin.setSingleStep(1.0)
        self.ref_elevation_spin.setDecimals(2)
        elev_layout.addWidget(self.ref_elevation_spin)
        params_layout.addLayout(elev_layout)
        
        # Hydraulic parameters group
        hydraulic_group = QGroupBox("Hydraulic Parameters")
        hydraulic_layout = QVBoxLayout(hydraulic_group)
        
        # Manning's n
        n_layout = QHBoxLayout()
        n_layout.addWidget(QLabel("Manning's n:"))
        self.mannings_n_spin = QDoubleSpinBox()
        self.mannings_n_spin.setRange(0.01, 0.20)
        self.mannings_n_spin.setValue(0.035)
        self.mannings_n_spin.setSingleStep(0.005)
        self.mannings_n_spin.setDecimals(3)
        n_layout.addWidget(self.mannings_n_spin)
        hydraulic_layout.addLayout(n_layout)
        
        # Channel slope
        slope_layout = QHBoxLayout()
        slope_layout.addWidget(QLabel("Channel Slope (ft/ft):"))
        self.channel_slope_spin = QDoubleSpinBox()
        self.channel_slope_spin.setRange(0.0001, 0.10)
        self.channel_slope_spin.setValue(0.005)
        self.channel_slope_spin.setSingleStep(0.001)
        self.channel_slope_spin.setDecimals(4)
        slope_layout.addWidget(self.channel_slope_spin)
        hydraulic_layout.addLayout(slope_layout)
        
        params_layout.addWidget(hydraulic_group)
        
        # Connect parameter changes to update visualization
        self.depth_spin.valueChanged.connect(self.update_visualization)
        self.bottom_width_spin.valueChanged.connect(self.update_visualization)
        self.left_slope_spin.valueChanged.connect(self.update_visualization)
        self.right_slope_spin.valueChanged.connect(self.update_visualization)
        self.ref_elevation_spin.valueChanged.connect(self.update_visualization)
        self.mannings_n_spin.valueChanged.connect(self.update_visualization)
        self.channel_slope_spin.valueChanged.connect(self.update_visualization)
        
        # Buttons
        button_layout = QVBoxLayout()
        
        update_btn = QPushButton("Update Preview")
        update_btn.clicked.connect(self.update_visualization)
        button_layout.addWidget(update_btn)
        
        add_btn = QPushButton("Add to Design List")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        add_btn.clicked.connect(self.add_channel_to_list)
        button_layout.addWidget(add_btn)
        
        params_layout.addLayout(button_layout)
        
        # Hydraulic properties display
        props_frame = QFrame()
        props_frame.setFrameStyle(QFrame.StyledPanel)
        props_layout = QVBoxLayout(props_frame)
        
        props_title = QLabel("<h4>Hydraulic Properties</h4>")
        props_layout.addWidget(props_title)
        
        self.properties_text = QTextEdit()
        self.properties_text.setMaximumHeight(200)
        self.properties_text.setReadOnly(True)
        props_layout.addWidget(self.properties_text)
        
        params_layout.addWidget(props_frame)
        params_layout.addStretch()
        
        main_h_layout.addWidget(params_frame)
        
        # Right side - Visualization
        viz_frame = QFrame()
        viz_frame.setFrameStyle(QFrame.StyledPanel)
        viz_layout = QVBoxLayout(viz_frame)
        
        viz_title = QLabel("<h3>Cross-Section Preview</h3>")
        viz_layout.addWidget(viz_title)
        
        self.visualization = ChannelVisualization()
        viz_layout.addWidget(self.visualization)
        
        main_h_layout.addWidget(viz_frame)
        
        layout.addLayout(main_h_layout)
        
        # Initial visualization
        self.update_visualization()
        
        return scroll
        
    def create_batch_tab(self) -> QWidget:
        """Create batch CSV design tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        title = QLabel("<h3>Batch Channel Design from CSV</h3>")
        layout.addWidget(title)
        
        desc = QLabel(
            "Import multiple channel designs from CSV file. "
            "CSV columns: channel_id, depth, bottom_width, left_slope, right_slope, "
            "ref_elevation, mannings_n (optional), channel_slope (optional)"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666; margin-bottom: 15px;")
        layout.addWidget(desc)
        
        # File selection
        file_frame = QFrame()
        file_frame.setFrameStyle(QFrame.StyledPanel)
        file_layout = QVBoxLayout(file_frame)
        
        file_button_layout = QHBoxLayout()
        self.batch_file_label = QLabel("No file selected")
        browse_btn = QPushButton("Browse CSV File...")
        browse_btn.clicked.connect(self.browse_batch_file)
        
        file_button_layout.addWidget(self.batch_file_label, 1)
        file_button_layout.addWidget(browse_btn)
        file_layout.addLayout(file_button_layout)
        
        template_btn = QPushButton("Download CSV Template")
        template_btn.clicked.connect(self.download_csv_template)
        file_layout.addWidget(template_btn)
        
        process_btn = QPushButton("Process Batch File")
        process_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        process_btn.clicked.connect(self.process_batch_file)
        file_layout.addWidget(process_btn)
        
        layout.addWidget(file_frame)
        
        self.progress_logger = ProgressLogger()
        layout.addWidget(self.progress_logger)
        
        layout.addStretch()
        return widget
        
    def create_results_tab(self) -> QWidget:
        """Create results display tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        title = QLabel("<h3>Channel Design Results</h3>")
        layout.addWidget(title)
        
        # Results table with capacity
        self.results_table = QTableWidget()
        self.results_table.setAlternatingRowColors(True)
        headers = ["Channel ID", "Depth", "Bottom Width", "Side Slope", 
                   "Manning's n", "Slope", "Top Width", "Area", "Hyd Radius",
                   "Velocity (fps)", "Capacity (cfs)"]
        self.results_table.setColumnCount(len(headers))
        self.results_table.setHorizontalHeaderLabels(headers)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.results_table)
        
        # SWMM output
        swmm_frame = QFrame()
        swmm_frame.setFrameStyle(QFrame.StyledPanel)
        swmm_layout = QVBoxLayout(swmm_frame)
        
        swmm_title = QLabel("<h4>SWMM Cross-Section Format</h4>")
        swmm_layout.addWidget(swmm_title)
        
        swmm_desc = QLabel("Copy and paste into SWMM cross-section editor:")
        swmm_desc.setStyleSheet("color: #666; font-style: italic;")
        swmm_layout.addWidget(swmm_desc)
        
        self.swmm_output = QTextEdit()
        self.swmm_output.setMaximumHeight(200)
        self.swmm_output.setReadOnly(True)
        self.swmm_output.setStyleSheet("""
            QTextEdit {
                font-family: Consolas, Monaco, monospace;
                font-size: 11px;
                background-color: #f8f9fa;
            }
        """)
        swmm_layout.addWidget(self.swmm_output)
        
        layout.addWidget(swmm_frame)
        
        # Export buttons
        export_layout = QHBoxLayout()
        
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self.clear_results)
        export_layout.addWidget(clear_btn)
        
        export_layout.addStretch()
        
        export_csv_btn = QPushButton("Export to CSV")
        export_csv_btn.clicked.connect(self.export_to_csv)
        export_layout.addWidget(export_csv_btn)
        
        layout.addLayout(export_layout)
        
        return widget
        
    def update_visualization(self):
        """Update the channel visualization and properties"""
        try:
            depth = self.depth_spin.value()
            bottom_width = self.bottom_width_spin.value()
            left_slope = self.left_slope_spin.value()
            right_slope = self.right_slope_spin.value()
            ref_elevation = self.ref_elevation_spin.value()
            mannings_n = self.mannings_n_spin.value()
            channel_slope = self.channel_slope_spin.value()
            
            self.current_geometry = ChannelGeometry(
                depth, bottom_width, left_slope, right_slope, ref_elevation,
                mannings_n, channel_slope
            )
            
            self.visualization.set_geometry(self.current_geometry)
            
            props = self.current_geometry.calculate_properties()
            properties_text = f"""
<b>Channel Geometry:</b><br>
- Depth: {depth:.2f} ft<br>
- Bottom Width: {bottom_width:.2f} ft<br>
- Side Slopes: {props['side_slopes']}<br>
- Reference Elevation: {ref_elevation:.2f} ft<br><br>

<b>Hydraulic Properties:</b><br>
- Top Width: {props['top_width']:.2f} ft<br>
- Cross-sectional Area: {props['area']:.2f} sq ft<br>
- Wetted Perimeter: {props['wetted_perimeter']:.2f} ft<br>
- Hydraulic Radius: {props['hydraulic_radius']:.3f} ft<br><br>

<b>Flow Capacity (Manning's):</b><br>
- Manning's n: {mannings_n:.3f}<br>
- Channel Slope: {channel_slope:.4f} ft/ft<br>
- Velocity: {props['velocity']:.2f} fps<br>
- <b>Capacity Q: {props['capacity']:.1f} cfs</b>
            """
            self.properties_text.setHtml(properties_text)
            
        except Exception as e:
            if self.progress_logger:
                self.progress_logger.log(f"Error updating visualization: {str(e)}", "error")
            
    def add_channel_to_list(self):
        """Add current channel design to the results list"""
        if not self.current_geometry:
            QMessageBox.warning(self.gui_widget, "No Design", "Please update the preview first.")
            return
            
        channel_id = self.channel_id_edit.text().strip()
        if not channel_id:
            QMessageBox.warning(self.gui_widget, "Missing ID", "Please enter a Channel ID.")
            return
            
        existing_ids = [ch['id'] for ch in self.channels]
        if channel_id in existing_ids:
            reply = QMessageBox.question(
                self.gui_widget, "Duplicate ID",
                f"Channel ID '{channel_id}' already exists. Replace it?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
            else:
                self.channels = [ch for ch in self.channels if ch['id'] != channel_id]
        
        channel_data = {
            'id': channel_id,
            'geometry': self.current_geometry,
            'properties': self.current_geometry.calculate_properties()
        }
        self.channels.append(channel_data)
        
        self.update_results_display()
        
        if channel_id.startswith("Channel_"):
            try:
                num = int(channel_id.split("_")[1])
                self.channel_id_edit.setText(f"Channel_{num + 1}")
            except:
                pass
                
        if self.progress_logger:
            self.progress_logger.log(f"Added channel: {channel_id}")
        
    def update_results_display(self):
        """Update the results table and SWMM output"""
        self.results_table.setRowCount(len(self.channels))
        
        swmm_lines = []
        
        for row, channel in enumerate(self.channels):
            geom = channel['geometry']
            props = channel['properties']
            
            items = [
                channel['id'],
                f"{geom.depth:.2f}",
                f"{geom.bottom_width:.2f}",
                f"{geom.left_slope:.1f}",
                f"{geom.mannings_n:.3f}",
                f"{geom.channel_slope:.4f}",
                f"{props['top_width']:.2f}",
                f"{props['area']:.2f}",
                f"{props['hydraulic_radius']:.3f}",
                f"{props['velocity']:.2f}",
                f"{props['capacity']:.1f}"
            ]
            
            for col, item in enumerate(items):
                self.results_table.setItem(row, col, QTableWidgetItem(item))
                
            swmm_lines.append(f";{channel['id']}")
            swmm_lines.append(geom.get_swmm_format())
            swmm_lines.append("")
            
        self.swmm_output.setPlainText("\n".join(swmm_lines))
        self.results_table.resizeColumnsToContents()
        
    def browse_batch_file(self):
        """Browse for batch CSV file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self.gui_widget, "Select Batch CSV File", "", "CSV files (*.csv)"
        )
        if file_path:
            self.batch_file_label.setText(Path(file_path).name)
            self.batch_file_path = file_path
            
    def download_csv_template(self):
        """Download CSV template file"""
        template_content = """channel_id,depth,bottom_width,left_slope,right_slope,ref_elevation,mannings_n,channel_slope
Channel_1,2.0,4.0,3.0,3.0,100.0,0.035,0.005
Channel_2,3.0,5.0,2.0,2.0,95.0,0.030,0.008
Channel_3,2.5,6.0,4.0,3.0,105.0,0.040,0.003"""
        
        file_path, _ = QFileDialog.getSaveFileName(
            self.gui_widget, "Save CSV Template", "channel_template.csv", "CSV files (*.csv)"
        )
        
        if file_path:
            with open(file_path, 'w', newline='') as f:
                f.write(template_content)
            QMessageBox.information(self.gui_widget, "Template Saved", f"Template saved to:\n{file_path}")
            
    def process_batch_file(self):
        """Process batch CSV file"""
        if not hasattr(self, 'batch_file_path'):
            QMessageBox.warning(self.gui_widget, "No File", "Please select a CSV file first.")
            return
            
        try:
            self.progress_logger.log("Processing batch file...")
            
            with open(self.batch_file_path, 'r') as f:
                reader = csv.DictReader(f)
                processed = 0
                errors = 0
                
                for row in reader:
                    try:
                        channel_id = row['channel_id'].strip()
                        depth = float(row['depth'])
                        bottom_width = float(row['bottom_width'])
                        left_slope = float(row['left_slope'])
                        right_slope = float(row['right_slope'])
                        ref_elevation = float(row['ref_elevation'])
                        
                        # Optional fields
                        mannings_n = float(row.get('mannings_n', 0.035) or 0.035)
                        channel_slope = float(row.get('channel_slope', 0.005) or 0.005)
                        
                        if depth <= 0 or bottom_width <= 0:
                            raise ValueError("Depth and bottom width must be positive")
                        if left_slope < 0 or right_slope < 0:
                            raise ValueError("Slopes must be non-negative")
                            
                        geometry = ChannelGeometry(depth, bottom_width, left_slope, right_slope, 
                                                  ref_elevation, mannings_n, channel_slope)
                        
                        channel_data = {
                            'id': channel_id,
                            'geometry': geometry,
                            'properties': geometry.calculate_properties()
                        }
                        
                        self.channels = [ch for ch in self.channels if ch['id'] != channel_id]
                        self.channels.append(channel_data)
                        
                        processed += 1
                        
                    except Exception as e:
                        errors += 1
                        self.progress_logger.log(f"Error processing {row.get('channel_id', 'unknown')}: {str(e)}", "warning")
                        
            self.update_results_display()
            
            self.progress_logger.log(f"Batch processing complete: {processed} channels processed, {errors} errors", "success")
            
        except Exception as e:
            self.progress_logger.log(f"Error reading batch file: {str(e)}", "error")
            QMessageBox.critical(self.gui_widget, "Batch Error", f"Error processing batch file:\n{str(e)}")
            
    def clear_results(self):
        """Clear all results"""
        reply = QMessageBox.question(
            self.gui_widget, "Clear Results",
            "Are you sure you want to clear all channel designs?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.channels = []
            self.update_results_display()
            if self.progress_logger:
                self.progress_logger.log("Results cleared")
            
    def export_to_csv(self):
        """Export results to CSV file"""
        if not self.channels:
            QMessageBox.information(self.gui_widget, "No Data", "No channels to export.")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self.gui_widget, "Export Channels", "channel_designs.csv", "CSV files (*.csv)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    
                    writer.writerow([
                        'Channel_ID', 'Depth', 'Bottom_Width', 'Left_Slope', 'Right_Slope',
                        'Ref_Elevation', 'Mannings_n', 'Channel_Slope', 
                        'Top_Width', 'Area', 'Wetted_Perimeter', 'Hydraulic_Radius',
                        'Velocity_fps', 'Capacity_cfs', 'SWMM_Points'
                    ])
                    
                    for channel in self.channels:
                        geom = channel['geometry']
                        props = channel['properties']
                        swmm_points = geom.get_swmm_format().replace('\n', '; ')
                        
                        writer.writerow([
                            channel['id'],
                            geom.depth,
                            geom.bottom_width,
                            geom.left_slope,
                            geom.right_slope,
                            geom.ref_elevation,
                            geom.mannings_n,
                            geom.channel_slope,
                            props['top_width'],
                            props['area'],
                            props['wetted_perimeter'],
                            props['hydraulic_radius'],
                            props['velocity'],
                            props['capacity'],
                            swmm_points
                        ])
                        
                self.progress_logger.log(f"Exported {len(self.channels)} channels to {file_path}", "success")
                QMessageBox.information(self.gui_widget, "Export Complete", f"Channels exported to:\n{file_path}")
                
            except Exception as e:
                self.progress_logger.log(f"Export error: {str(e)}", "error")
                QMessageBox.critical(self.gui_widget, "Export Error", f"Error exporting file:\n{str(e)}")
                
    def validate_inputs(self) -> Tuple[bool, str]:
        """Validate tool inputs"""
        return True, "Channel designer ready"
        
    def run(self, progress_callback: Optional[Callable[[int, str], None]] = None) -> bool:
        """Execute tool"""
        if self.channels:
            QMessageBox.information(
                self.gui_widget, "Design Complete",
                f"Channel designer has {len(self.channels)} designs ready.\n\n"
                "Use the Results tab to view and export your designs."
            )
            return True
        else:
            QMessageBox.information(
                self.gui_widget, "No Designs",
                "Please create some channel designs first using one of the input tabs."
            )
            return False
