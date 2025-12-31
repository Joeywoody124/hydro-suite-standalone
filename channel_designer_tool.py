"""
Channel Designer Tool for Hydro Suite
Trapezoidal channel cross-section generator with SWMM integration
Version 1.0 - 2025

STANDALONE SCRIPT VERSION
Repository: https://github.com/Joeywoody124/hydro-suite-standalone
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
    QTextEdit, QTabWidget, QFileDialog, QCheckBox
)
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QFont, QPixmap, QPainter, QPen, QBrush

# Import our shared components
from hydro_suite_interface import HydroToolInterface, LayerSelectionMixin
from shared_widgets import (
    DirectorySelector, ProgressLogger, ValidationPanel
)


class ChannelGeometry:
    """Class to handle trapezoidal channel geometry calculations"""
    
    def __init__(self, depth: float, bottom_width: float, left_slope: float, 
                 right_slope: float, ref_elevation: float = 0.0):
        """
        Initialize channel geometry
        
        Args:
            depth: Channel depth
            bottom_width: Bottom width
            left_slope: Left side slope (horizontal:1 vertical)
            right_slope: Right side slope (horizontal:1 vertical)
            ref_elevation: Reference bottom elevation
        """
        self.depth = depth
        self.bottom_width = bottom_width
        self.left_slope = left_slope
        self.right_slope = right_slope
        self.ref_elevation = ref_elevation
        
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
        
        return {
            'top_width': top_width,
            'area': area,
            'wetted_perimeter': wetted_perimeter,
            'hydraulic_radius': hydraulic_radius,
            'side_slopes': f"{self.left_slope}:1 / {self.right_slope}:1"
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
        
        # Add some padding
        offset_range = max_offset - min_offset
        elev_range = max_elev - min_elev
        
        if offset_range == 0 or elev_range == 0:
            return
            
        # Scale to fit widget
        scale_x = width / (offset_range * 1.2)
        scale_y = height / (elev_range * 1.2)
        
        # Use same scale for both axes to maintain proportions
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
            # Order points for drawing: left top -> left bottom -> right bottom -> right top
            left_top = screen_points[0]  # Leftmost point
            left_bottom = None
            right_bottom = None
            right_top = screen_points[-1]  # Rightmost point
            
            # Find bottom points (lowest elevation)
            bottom_points = [p for p in points if abs(p['elevation'] - min_elev) < 0.001]
            if len(bottom_points) >= 2:
                bottom_screen = [(center_x + (p['offset'] - (min_offset + max_offset) / 2) * scale,
                                center_y - (p['elevation'] - (min_elev + max_elev) / 2) * scale)
                               for p in bottom_points]
                bottom_screen.sort(key=lambda p: p[0])  # Sort by x coordinate
                left_bottom = bottom_screen[0]
                right_bottom = bottom_screen[-1]
                
                # Draw filled trapezoid
                from qgis.PyQt.QtGui import QPolygonF
                from qgis.PyQt.QtCore import QPointF
                
                polygon = QPolygonF([
                    QPointF(*left_top),
                    QPointF(*left_bottom),
                    QPointF(*right_bottom),
                    QPointF(*right_top)
                ])
                painter.drawPolygon(polygon)
        
        # Draw grid
        painter.setPen(QPen(Qt.gray, 1))
        # Draw center lines
        painter.drawLine(int(center_x), 20, int(center_x), self.height() - 20)  # Vertical center
        painter.drawLine(20, int(center_y), self.width() - 20, int(center_y))   # Horizontal center
        
        # Draw points and labels
        painter.setPen(QPen(Qt.red, 1))
        painter.setBrush(QBrush(Qt.red))
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)
        
        for i, (point, (x, y)) in enumerate(zip(points, screen_points)):
            # Draw point
            painter.drawEllipse(int(x)-3, int(y)-3, 6, 6)
            
            # Draw label
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
        self.version = "1.0"
        self.author = "Hydro Suite"
        
        # Tool properties
        self.channels = []  # List of designed channels
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
        
    def create_gui(self, parent_widget: QWidget) -> QWidget:
        """Create the Channel Designer GUI with tabbed interface"""
        # Create tab widget
        tab_widget = QTabWidget(parent_widget)
        
        # Design tab
        design_tab = self.create_design_tab()
        tab_widget.addTab(design_tab, "Design")
        
        # Batch tab
        batch_tab = self.create_batch_tab()
        tab_widget.addTab(batch_tab, "Batch Design")
        
        # Results tab
        results_tab = self.create_results_tab()
        tab_widget.addTab(results_tab, "Results")
        
        self.gui_widget = tab_widget
        return tab_widget
        
    def create_design_tab(self) -> QWidget:
        """Create the main design tab"""
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
        
        # Connect parameter changes to update visualization
        self.depth_spin.valueChanged.connect(self.update_visualization)
        self.bottom_width_spin.valueChanged.connect(self.update_visualization)
        self.left_slope_spin.valueChanged.connect(self.update_visualization)
        self.right_slope_spin.valueChanged.connect(self.update_visualization)
        self.ref_elevation_spin.valueChanged.connect(self.update_visualization)
        
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
        
        # Hydraulic properties
        props_frame = QFrame()
        props_frame.setFrameStyle(QFrame.StyledPanel)
        props_layout = QVBoxLayout(props_frame)
        
        props_title = QLabel("<h4>Hydraulic Properties</h4>")
        props_layout.addWidget(props_title)
        
        self.properties_text = QTextEdit()
        self.properties_text.setMaximumHeight(150)
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
        """Create batch design tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Title
        title = QLabel("<h3>Batch Channel Design</h3>")
        layout.addWidget(title)
        
        desc = QLabel(
            "Import multiple channel designs from CSV file. "
            "CSV format: channel_id, depth, bottom_width, left_slope, right_slope, ref_elevation"
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
        
        # Template download
        template_btn = QPushButton("Download CSV Template")
        template_btn.clicked.connect(self.download_csv_template)
        file_layout.addWidget(template_btn)
        
        # Process button
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
        
        # Progress logger
        self.progress_logger = ProgressLogger()
        layout.addWidget(self.progress_logger)
        
        layout.addStretch()
        return widget
        
    def create_results_tab(self) -> QWidget:
        """Create results display tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Title
        title = QLabel("<h3>Channel Design Results</h3>")
        layout.addWidget(title)
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setAlternatingRowColors(True)
        headers = ["Channel ID", "Depth", "Bottom Width", "Left Slope", "Right Slope", 
                  "Ref Elevation", "Top Width", "Area", "Wetted Perimeter", "Hydraulic Radius"]
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
            # Get current parameters
            depth = self.depth_spin.value()
            bottom_width = self.bottom_width_spin.value()
            left_slope = self.left_slope_spin.value()
            right_slope = self.right_slope_spin.value()
            ref_elevation = self.ref_elevation_spin.value()
            
            # Create geometry
            self.current_geometry = ChannelGeometry(
                depth, bottom_width, left_slope, right_slope, ref_elevation
            )
            
            # Update visualization
            self.visualization.set_geometry(self.current_geometry)
            
            # Update properties text
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
- Hydraulic Radius: {props['hydraulic_radius']:.3f} ft<br>
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
            
        # Check for duplicate IDs
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
                # Remove existing
                self.channels = [ch for ch in self.channels if ch['id'] != channel_id]
        
        # Add to list
        channel_data = {
            'id': channel_id,
            'geometry': self.current_geometry,
            'properties': self.current_geometry.calculate_properties()
        }
        self.channels.append(channel_data)
        
        # Update results display
        self.update_results_display()
        
        # Auto-increment channel ID
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
        # Update table
        self.results_table.setRowCount(len(self.channels))
        
        swmm_lines = []
        
        for row, channel in enumerate(self.channels):
            geom = channel['geometry']
            props = channel['properties']
            
            # Populate table row
            items = [
                channel['id'],
                f"{geom.depth:.2f}",
                f"{geom.bottom_width:.2f}",
                f"{geom.left_slope:.1f}",
                f"{geom.right_slope:.1f}",
                f"{geom.ref_elevation:.2f}",
                f"{props['top_width']:.2f}",
                f"{props['area']:.2f}",
                f"{props['wetted_perimeter']:.2f}",
                f"{props['hydraulic_radius']:.3f}"
            ]
            
            for col, item in enumerate(items):
                self.results_table.setItem(row, col, QTableWidgetItem(item))
                
            # Add to SWMM output
            swmm_lines.append(f";{channel['id']}")
            swmm_lines.append(geom.get_swmm_format())
            swmm_lines.append("")  # Blank line
            
        # Update SWMM output
        self.swmm_output.setPlainText("\n".join(swmm_lines))
        
        # Resize columns
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
        template_content = """channel_id,depth,bottom_width,left_slope,right_slope,ref_elevation
Channel_1,2.0,4.0,3.0,3.0,100.0
Channel_2,3.0,5.0,2.0,2.0,95.0
Channel_3,2.5,6.0,4.0,3.0,105.0"""
        
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
                        # Extract parameters
                        channel_id = row['channel_id'].strip()
                        depth = float(row['depth'])
                        bottom_width = float(row['bottom_width'])
                        left_slope = float(row['left_slope'])
                        right_slope = float(row['right_slope'])
                        ref_elevation = float(row['ref_elevation'])
                        
                        # Validate parameters
                        if depth <= 0 or bottom_width <= 0:
                            raise ValueError("Depth and bottom width must be positive")
                        if left_slope < 0 or right_slope < 0:
                            raise ValueError("Slopes must be non-negative")
                            
                        # Create geometry
                        geometry = ChannelGeometry(depth, bottom_width, left_slope, right_slope, ref_elevation)
                        
                        # Add to channels list
                        channel_data = {
                            'id': channel_id,
                            'geometry': geometry,
                            'properties': geometry.calculate_properties()
                        }
                        
                        # Remove existing if duplicate
                        self.channels = [ch for ch in self.channels if ch['id'] != channel_id]
                        self.channels.append(channel_data)
                        
                        processed += 1
                        
                    except Exception as e:
                        errors += 1
                        self.progress_logger.log(f"Error processing {row.get('channel_id', 'unknown')}: {str(e)}", "warning")
                        
            # Update display
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
                    
                    # Headers
                    writer.writerow([
                        'Channel_ID', 'Depth', 'Bottom_Width', 'Left_Slope', 'Right_Slope',
                        'Ref_Elevation', 'Top_Width', 'Area', 'Wetted_Perimeter', 'Hydraulic_Radius',
                        'SWMM_Points'
                    ])
                    
                    # Data
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
                            props['top_width'],
                            props['area'],
                            props['wetted_perimeter'],
                            props['hydraulic_radius'],
                            swmm_points
                        ])
                        
                self.progress_logger.log(f"Exported {len(self.channels)} channels to {file_path}", "success")
                QMessageBox.information(self.gui_widget, "Export Complete", f"Channels exported to:\n{file_path}")
                
            except Exception as e:
                self.progress_logger.log(f"Export error: {str(e)}", "error")
                QMessageBox.critical(self.gui_widget, "Export Error", f"Error exporting file:\n{str(e)}")
                
    def validate_inputs(self) -> Tuple[bool, str]:
        """Validate tool inputs"""
        # Channel designer doesn't require external inputs
        return True, "Channel designer ready"
        
    def run(self, progress_callback: Optional[Callable[[int, str], None]] = None) -> bool:
        """Execute tool - not needed for interactive designer"""
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
                "Please create some channel designs first using the Design tab."
            )
            return False
