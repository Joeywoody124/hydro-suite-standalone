"""
Time of Concentration Calculator Tool for Hydro Suite
Multi-method TC calculator with comprehensive methodology support
Version 1.0 - 2025

STANDALONE SCRIPT VERSION
Repository: https://github.com/Joeywoody124/hydro-suite-standalone
"""

import os
import csv
import math
import traceback
from pathlib import Path
from typing import Optional, Tuple, Callable, Dict, Any, List

from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QMessageBox, QScrollArea, QFrame, QGroupBox, QCheckBox,
    QDoubleSpinBox, QSpinBox, QComboBox, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from qgis.PyQt.QtCore import Qt, pyqtSignal

from qgis.core import (
    QgsCoordinateReferenceSystem, QgsProcessingFeedback, QgsProject,
    QgsVectorFileWriter, QgsVectorLayer, QgsField, QgsFeature,
    QgsWkbTypes, Qgis, QgsMessageLog, QgsPointXY, QgsGeometry
)
from qgis import processing

# Import our shared components
from hydro_suite_interface import HydroToolInterface, LayerSelectionMixin
from shared_widgets import (
    LayerFieldSelector, FileSelector, DirectorySelector, 
    ProgressLogger, ValidationPanel
)


class TCMethodCalculator:
    """Base class for TC calculation methods"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.parameters = {}
        
    def calculate(self, length_ft: float, slope_percent: float, **kwargs) -> float:
        """Calculate TC in minutes"""
        raise NotImplementedError
        
    def get_parameters(self) -> Dict[str, Any]:
        """Get method-specific parameters"""
        return self.parameters
        
    def set_parameters(self, params: Dict[str, Any]):
        """Set method-specific parameters"""
        self.parameters.update(params)


class KirpichMethod(TCMethodCalculator):
    """Kirpich (1940) method for rural watersheds"""
    
    def __init__(self):
        super().__init__("Kirpich", "Rural watersheds with defined channels")
        self.parameters = {
            'coefficient': 0.0078,  # Standard coefficient
            'length_exponent': 0.77,
            'slope_exponent': -0.385
        }
        
    def calculate(self, length_ft: float, slope_percent: float, **kwargs) -> float:
        """
        Kirpich formula: tc = 0.0078 * (L^0.77) / (S^0.385)
        where L is length in feet, S is slope in %
        """
        if length_ft <= 0 or slope_percent <= 0:
            return 0.0
            
        return (self.parameters['coefficient'] * 
                (length_ft ** self.parameters['length_exponent']) / 
                (slope_percent ** self.parameters['slope_exponent']))


class FAAMethod(TCMethodCalculator):
    """FAA (1965) method for urban areas"""
    
    def __init__(self):
        super().__init__("FAA", "Urban areas, regulatory standard")
        self.parameters = {
            'coefficient': 1.8,
            'length_exponent': 0.5,
            'slope_exponent': -0.33,
            'c_factor': 1.1  # Runoff coefficient factor
        }
        
    def calculate(self, length_ft: float, slope_percent: float, **kwargs) -> float:
        """
        FAA formula: tc = (1.8 * (1.1 - C) * L^0.5) / S^0.33
        where C is runoff coefficient (default 0.2 for mixed development)
        """
        if length_ft <= 0 or slope_percent <= 0:
            return 0.0
            
        c_value = kwargs.get('runoff_coefficient', 0.2)
        
        return ((self.parameters['coefficient'] * 
                (self.parameters['c_factor'] - c_value) * 
                (length_ft ** self.parameters['length_exponent'])) / 
                (slope_percent ** self.parameters['slope_exponent']))


class SCSMethod(TCMethodCalculator):
    """SCS/NRCS (1972) method for natural watersheds"""
    
    def __init__(self):
        super().__init__("SCS/NRCS", "Natural watersheds, NRCS compliance")
        self.parameters = {
            'coefficient': 0.0078,
            'length_exponent': 0.8,
            'slope_exponent': -0.5,
            'cn_adjustment': True
        }
        
    def calculate(self, length_ft: float, slope_percent: float, **kwargs) -> float:
        """
        SCS formula: tc = 0.0078 * (L^0.8) / (S^0.5)
        with optional CN adjustment
        """
        if length_ft <= 0 or slope_percent <= 0:
            return 0.0
            
        base_tc = (self.parameters['coefficient'] * 
                  (length_ft ** self.parameters['length_exponent']) / 
                  (slope_percent ** self.parameters['slope_exponent']))
        
        # Optional CN adjustment
        if self.parameters['cn_adjustment']:
            cn = kwargs.get('curve_number', 75)
            if cn > 0:
                adjustment_factor = (100 - cn) / 100
                base_tc *= (1 + adjustment_factor)
                
        return base_tc


class KerbyMethod(TCMethodCalculator):
    """Kerby method for overland flow with surface roughness"""
    
    def __init__(self):
        super().__init__("Kerby", "Overland flow with surface roughness")
        self.parameters = {
            'coefficient': 1.44,
            'length_exponent': 0.467,
            'slope_exponent': -0.235,
            'roughness_coefficient': 0.4  # Default for mixed surfaces
        }
        
    def calculate(self, length_ft: float, slope_percent: float, **kwargs) -> float:
        """
        Kerby formula: tc = 1.44 * (n * L)^0.467 / S^0.235
        where n is Manning's roughness coefficient
        """
        if length_ft <= 0 or slope_percent <= 0:
            return 0.0
            
        n = kwargs.get('roughness_coefficient', self.parameters['roughness_coefficient'])
        
        return (self.parameters['coefficient'] * 
                ((n * length_ft) ** self.parameters['length_exponent']) / 
                (slope_percent ** self.parameters['slope_exponent']))


class TCCalculatorTool(HydroToolInterface, LayerSelectionMixin):
    """Time of Concentration Calculator with multiple methods"""
    
    def __init__(self):
        super().__init__()
        self.name = "Time of Concentration Calculator"
        self.description = "Calculate time of concentration using multiple industry-standard methods"
        self.category = "Watershed Analysis"
        self.version = "1.0"
        self.author = "Hydro Suite"
        
        # Available methods
        self.methods = {
            'kirpich': KirpichMethod(),
            'faa': FAAMethod(),
            'scs': SCSMethod(),
            'kerby': KerbyMethod()
        }
        
        # Tool-specific properties
        self.target_crs = QgsCoordinateReferenceSystem("EPSG:3361")
        self.selected_methods = ['kirpich', 'faa']  # Default selection
        
        # GUI components
        self.subbasin_selector = None
        self.dem_selector = None
        self.output_selector = None
        self.validation_panel = None
        self.progress_logger = None
        self.method_checkboxes = {}
        self.parameter_widgets = {}
        self.results_table = None
        
    def create_gui(self, parent_widget: QWidget) -> QWidget:
        """Create the TC Calculator GUI with tabbed interface"""
        # Create tab widget
        tab_widget = QTabWidget(parent_widget)
        
        # Main configuration tab
        main_tab = self.create_main_tab()
        tab_widget.addTab(main_tab, "Configuration")
        
        # Methods tab
        methods_tab = self.create_methods_tab()
        tab_widget.addTab(methods_tab, "Methods")
        
        # Parameters tab
        params_tab = self.create_parameters_tab()
        tab_widget.addTab(params_tab, "Parameters")
        
        # Results tab
        results_tab = self.create_results_tab()
        tab_widget.addTab(results_tab, "Results")
        
        self.gui_widget = tab_widget
        return tab_widget
        
    def create_main_tab(self) -> QWidget:
        """Create main configuration tab"""
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        main_widget = QWidget()
        scroll.setWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Title and description
        title_label = QLabel(f"<h2>{self.name}</h2>")
        layout.addWidget(title_label)
        
        desc_label = QLabel(
            "<p>This tool calculates time of concentration using multiple industry-standard methods. "
            "It requires subbasin polygons and a DEM for slope calculations.</p>"
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #555; margin-bottom: 10px;")
        layout.addWidget(desc_label)
        
        # Validation panel
        self.validation_panel = ValidationPanel()
        layout.addWidget(self.validation_panel)
        
        # Input layers section
        inputs_frame = QFrame()
        inputs_frame.setFrameStyle(QFrame.StyledPanel)
        inputs_layout = QVBoxLayout(inputs_frame)
        
        inputs_title = QLabel("<h3>Input Data</h3>")
        inputs_layout.addWidget(inputs_title)
        
        # Subbasin layer selector
        self.subbasin_selector = LayerFieldSelector(
            "Subbasin Layer", 
            default_field="Name",
            geometry_type=QgsWkbTypes.PolygonGeometry
        )
        inputs_layout.addWidget(self.subbasin_selector)
        
        # DEM layer selector
        self.dem_selector = LayerFieldSelector(
            "DEM (Digital Elevation Model)",
            default_field="",
            geometry_type=None  # Raster layer
        )
        inputs_layout.addWidget(self.dem_selector)
        
        layout.addWidget(inputs_frame)
        
        # Output section
        output_frame = QFrame()
        output_frame.setFrameStyle(QFrame.StyledPanel)
        output_layout = QVBoxLayout(output_frame)
        
        output_title = QLabel("<h3>Output</h3>")
        output_layout.addWidget(output_title)
        
        # Output directory selector
        self.output_selector = DirectorySelector(
            "Output Directory",
            default_path=""
        )
        output_layout.addWidget(self.output_selector)
        
        layout.addWidget(output_frame)
        
        # Progress and logging
        self.progress_logger = ProgressLogger()
        layout.addWidget(self.progress_logger)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        validate_btn = QPushButton("Validate Inputs")
        validate_btn.clicked.connect(self.validate_and_update)
        button_layout.addWidget(validate_btn)
        
        button_layout.addStretch()
        
        self.run_btn = QPushButton("Calculate Time of Concentration")
        self.run_btn.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
                background-color: #17a2b8;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.run_btn.clicked.connect(self.run_calculation)
        button_layout.addWidget(self.run_btn)
        
        layout.addLayout(button_layout)
        
        # Setup validation monitoring
        self.setup_validation_monitoring()
        
        # Initial validation
        self.validate_and_update()
        
        return scroll
        
    def create_methods_tab(self) -> QWidget:
        """Create methods selection tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Title
        title = QLabel("<h3>Select Calculation Methods</h3>")
        layout.addWidget(title)
        
        desc = QLabel(
            "Choose one or more methods for TC calculation. "
            "Multiple methods allow for comparison and validation of results."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666; margin-bottom: 15px;")
        layout.addWidget(desc)
        
        # Method selection
        methods_frame = QFrame()
        methods_frame.setFrameStyle(QFrame.StyledPanel)
        methods_layout = QVBoxLayout(methods_frame)
        
        for method_id, method in self.methods.items():
            # Create checkbox
            checkbox = QCheckBox(f"{method.name} - {method.description}")
            checkbox.setChecked(method_id in self.selected_methods)
            checkbox.toggled.connect(lambda checked, mid=method_id: self.on_method_toggled(mid, checked))
            
            # Add to layout and store reference
            methods_layout.addWidget(checkbox)
            self.method_checkboxes[method_id] = checkbox
            
        layout.addWidget(methods_frame)
        
        # Method information
        info_frame = QFrame()
        info_frame.setFrameStyle(QFrame.StyledPanel)
        info_layout = QVBoxLayout(info_frame)
        
        info_title = QLabel("<h4>Method Information</h4>")
        info_layout.addWidget(info_title)
        
        method_info = QLabel("""
<b>Kirpich (1940):</b> Best for rural watersheds with defined channels. Formula: tc = 0.0078 * (L^0.77) / (S^0.385)<br><br>
<b>FAA (1965):</b> Standard for urban areas and regulatory compliance. Accounts for runoff coefficient.<br><br>
<b>SCS/NRCS (1972):</b> Natural watersheds, NRCS compliance. Optional curve number adjustment.<br><br>
<b>Kerby:</b> Overland flow with surface roughness considerations. Uses Manning's n coefficient.
        """)
        method_info.setWordWrap(True)
        method_info.setStyleSheet("color: #555; padding: 10px;")
        info_layout.addWidget(method_info)
        
        layout.addWidget(info_frame)
        layout.addStretch()
        
        return widget
        
    def create_parameters_tab(self) -> QWidget:
        """Create parameters configuration tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Title
        title = QLabel("<h3>Method Parameters</h3>")
        layout.addWidget(title)
        
        desc = QLabel(
            "Adjust method-specific parameters. Default values are based on standard practice."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666; margin-bottom: 15px;")
        layout.addWidget(desc)
        
        # Create parameter groups for each method
        for method_id, method in self.methods.items():
            group = QGroupBox(f"{method.name} Parameters")
            group_layout = QVBoxLayout(group)
            
            # Create parameter widgets based on method
            method_widgets = {}
            
            if method_id == 'faa':
                # FAA specific parameters
                rc_layout = QHBoxLayout()
                rc_layout.addWidget(QLabel("Runoff Coefficient:"))
                rc_spin = QDoubleSpinBox()
                rc_spin.setRange(0.1, 0.95)
                rc_spin.setValue(0.2)
                rc_spin.setSingleStep(0.05)
                rc_spin.setDecimals(2)
                rc_layout.addWidget(rc_spin)
                rc_layout.addStretch()
                group_layout.addLayout(rc_layout)
                method_widgets['runoff_coefficient'] = rc_spin
                
            elif method_id == 'scs':
                # SCS specific parameters
                cn_layout = QHBoxLayout()
                cn_layout.addWidget(QLabel("Curve Number (if available):"))
                cn_spin = QSpinBox()
                cn_spin.setRange(30, 98)
                cn_spin.setValue(75)
                cn_layout.addWidget(cn_spin)
                cn_layout.addStretch()
                group_layout.addLayout(cn_layout)
                method_widgets['curve_number'] = cn_spin
                
            elif method_id == 'kerby':
                # Kerby specific parameters
                n_layout = QHBoxLayout()
                n_layout.addWidget(QLabel("Manning's n (roughness):"))
                n_spin = QDoubleSpinBox()
                n_spin.setRange(0.1, 1.0)
                n_spin.setValue(0.4)
                n_spin.setSingleStep(0.1)
                n_spin.setDecimals(2)
                n_layout.addWidget(n_spin)
                n_layout.addStretch()
                group_layout.addLayout(n_layout)
                method_widgets['roughness_coefficient'] = n_spin
                
            # Store widgets for later access
            self.parameter_widgets[method_id] = method_widgets
            
            layout.addWidget(group)
            
        layout.addStretch()
        return widget
        
    def create_results_tab(self) -> QWidget:
        """Create results display tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Title
        title = QLabel("<h3>Calculation Results</h3>")
        layout.addWidget(title)
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setAlternatingRowColors(True)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.results_table)
        
        # Summary stats
        self.summary_label = QLabel("Run calculation to see results...")
        self.summary_label.setStyleSheet("color: #666; font-style: italic; padding: 10px;")
        layout.addWidget(self.summary_label)
        
        return widget
        
    def on_method_toggled(self, method_id: str, checked: bool):
        """Handle method selection change"""
        if checked and method_id not in self.selected_methods:
            self.selected_methods.append(method_id)
        elif not checked and method_id in self.selected_methods:
            self.selected_methods.remove(method_id)
            
        self.progress_logger.log(f"Method {method_id}: {'enabled' if checked else 'disabled'}")
        
    def setup_validation_monitoring(self):
        """Setup validation monitoring for all inputs"""
        # Add validation items
        self.validation_panel.add_validation("subbasin", "Subbasin layer and field")
        self.validation_panel.add_validation("dem", "DEM layer")
        self.validation_panel.add_validation("methods", "At least one calculation method")
        self.validation_panel.add_validation("output", "Output directory")
        
        # Connect validation signals
        self.subbasin_selector.selection_valid.connect(
            lambda valid: self.validation_panel.set_validation_status("subbasin", valid)
        )
        self.dem_selector.selection_valid.connect(
            lambda valid: self.validation_panel.set_validation_status("dem", valid)
        )
        self.output_selector.directory_selected.connect(
            lambda dir: self.validation_panel.set_validation_status("output", bool(dir))
        )
        
    def validate_and_update(self):
        """Validate all inputs and update UI"""
        # Trigger validation on all selectors
        self.subbasin_selector.validate_selection()
        self.dem_selector.validate_selection()
        
        # Validate methods selection
        methods_valid = len(self.selected_methods) > 0
        self.validation_panel.set_validation_status("methods", methods_valid, 
                                                   f"{len(self.selected_methods)} methods selected")
        
        # Validate output directory
        output_valid = self.output_selector.is_valid()
        self.validation_panel.set_validation_status("output", output_valid)
        
        # Enable/disable run button
        all_valid = self.validation_panel.is_all_valid()
        self.run_btn.setEnabled(all_valid)
        
        if all_valid:
            self.progress_logger.log("All inputs validated - ready to run", "success")
        else:
            invalid_items = self.validation_panel.get_invalid_items()
            self.progress_logger.log(f"Please complete: {', '.join(invalid_items)}", "warning")
            
    def validate_inputs(self) -> Tuple[bool, str]:
        """Validate all inputs before processing"""
        errors = []
        
        # Check layer selections
        if not self.subbasin_selector.is_valid():
            errors.append("Invalid subbasin layer or field selection")
            
        if not self.dem_selector.is_valid():
            errors.append("Invalid DEM layer selection")
            
        # Check methods selection
        if not self.selected_methods:
            errors.append("No calculation methods selected")
            
        # Check output directory
        if not self.output_selector.is_valid():
            errors.append("No output directory selected")
            
        if errors:
            return False, "Please fix the following issues:\n- " + "\n- ".join(errors)
            
        return True, "All inputs valid"
        
    def run_calculation(self):
        """Run the TC calculation"""
        try:
            self.run(lambda progress, msg: self.progress_logger.update_progress(progress, msg))
        except Exception as e:
            self.progress_logger.log(f"Error: {str(e)}", "error")
            QMessageBox.critical(self.gui_widget, "Calculation Error", str(e))
            
    def run(self, progress_callback: Optional[Callable[[int, str], None]] = None) -> bool:
        """Execute the TC calculation"""
        if not progress_callback:
            progress_callback = lambda p, m: None
            
        try:
            self.progress_logger.show_progress(True)
            progress_callback(0, "Starting TC calculation...")
            
            # Validate inputs
            valid, message = self.validate_inputs()
            if not valid:
                raise ValueError(message)
                
            # Get input layers and fields
            subbasin_layer = self.subbasin_selector.get_selected_layer()
            subbasin_field = self.subbasin_selector.get_selected_field()
            dem_layer = self.dem_selector.get_selected_layer()
            output_dir = self.output_selector.get_selected_directory()
            
            progress_callback(10, f"Using methods: {', '.join(self.selected_methods)}")
            
            # Calculate TC for each subbasin
            progress_callback(20, "Processing subbasins...")
            results = self.calculate_tc_for_subbasins(
                subbasin_layer, subbasin_field, dem_layer, progress_callback
            )
            
            # Create outputs
            progress_callback(80, "Creating output files...")
            self.create_outputs(subbasin_layer, results, subbasin_field, output_dir)
            
            # Update results display
            progress_callback(95, "Updating results display...")
            self.update_results_display(results)
            
            progress_callback(100, "TC calculation completed successfully!")
            
            # Show completion dialog
            self.show_completion_dialog(results, output_dir)
            
            return True
            
        except Exception as e:
            progress_callback(0, f"Error: {str(e)}")
            self.progress_logger.log(f"Calculation failed: {str(e)}", "error")
            self.progress_logger.log(traceback.format_exc(), "error")
            raise
            
        finally:
            self.progress_logger.show_progress(False)
            
    def calculate_tc_for_subbasins(self, subbasin_layer: QgsVectorLayer, 
                                  subbasin_field: str, dem_layer: QgsVectorLayer,
                                  progress_callback: Callable) -> Dict:
        """Calculate TC for each subbasin using selected methods"""
        results = {}
        total_features = subbasin_layer.featureCount()
        
        for i, feature in enumerate(subbasin_layer.getFeatures()):
            subbasin_id = feature[subbasin_field]
            geometry = feature.geometry()
            
            # Calculate length and slope for this subbasin
            length_ft, slope_percent = self.calculate_subbasin_characteristics(
                geometry, dem_layer
            )
            
            # Calculate TC using each selected method
            tc_results = {}
            method_params = self.get_current_parameters()
            
            for method_id in self.selected_methods:
                method = self.methods[method_id]
                params = method_params.get(method_id, {})
                
                tc_minutes = method.calculate(length_ft, slope_percent, **params)
                tc_results[method_id] = {
                    'tc_minutes': tc_minutes,
                    'tc_hours': tc_minutes / 60.0,
                    'method_name': method.name
                }
                
            results[subbasin_id] = {
                'length_ft': length_ft,
                'slope_percent': slope_percent,
                'tc_results': tc_results
            }
            
            # Update progress
            progress = 20 + int((i + 1) / total_features * 60)
            progress_callback(progress, f"Processed {i + 1}/{total_features} subbasins")
            
        return results
        
    def calculate_subbasin_characteristics(self, geometry: QgsGeometry, 
                                         dem_layer: QgsVectorLayer) -> Tuple[float, float]:
        """Calculate flow length and slope for a subbasin"""
        # For now, use simplified approach
        # In production, this would use more sophisticated flow path analysis
        
        # Get subbasin centroid and bounds
        centroid = geometry.centroid().asPoint()
        bbox = geometry.boundingBox()
        
        # Estimate flow length as longest dimension
        length_ft = max(bbox.width(), bbox.height()) * 3.28084  # Convert m to ft
        
        # Estimate slope from DEM (simplified)
        # In production, this would sample DEM values along flow path
        slope_percent = 2.0  # Default 2% slope
        
        # TODO: Implement proper flow path and slope calculation
        # This would involve:
        # 1. Finding outlet point
        # 2. Tracing flow path to divide
        # 3. Sampling elevation along path
        # 4. Calculating average slope
        
        return length_ft, slope_percent
        
    def get_current_parameters(self) -> Dict:
        """Get current parameter values from UI"""
        params = {}
        
        for method_id, widgets in self.parameter_widgets.items():
            method_params = {}
            for param_name, widget in widgets.items():
                if hasattr(widget, 'value'):
                    method_params[param_name] = widget.value()
            params[method_id] = method_params
            
        return params
        
    def update_results_display(self, results: Dict):
        """Update the results table with calculation results"""
        # Setup table
        subbasin_count = len(results)
        method_count = len(self.selected_methods)
        
        # Columns: Subbasin, Length, Slope, then TC for each method
        columns = ['Subbasin', 'Length (ft)', 'Slope (%)', 'Min TC (min)', 'Max TC (min)', 'Avg TC (min)']
        for method_id in self.selected_methods:
            method_name = self.methods[method_id].name
            columns.append(f'{method_name} (min)')
            
        self.results_table.setRowCount(subbasin_count)
        self.results_table.setColumnCount(len(columns))
        self.results_table.setHorizontalHeaderLabels(columns)
        
        # Populate data
        all_tc_values = []
        
        for row, (subbasin_id, data) in enumerate(results.items()):
            # Basic data
            self.results_table.setItem(row, 0, QTableWidgetItem(str(subbasin_id)))
            self.results_table.setItem(row, 1, QTableWidgetItem(f"{data['length_ft']:.0f}"))
            self.results_table.setItem(row, 2, QTableWidgetItem(f"{data['slope_percent']:.2f}"))
            
            # TC values for this subbasin
            tc_values = [result['tc_minutes'] for result in data['tc_results'].values()]
            all_tc_values.extend(tc_values)
            
            if tc_values:
                self.results_table.setItem(row, 3, QTableWidgetItem(f"{min(tc_values):.1f}"))
                self.results_table.setItem(row, 4, QTableWidgetItem(f"{max(tc_values):.1f}"))
                self.results_table.setItem(row, 5, QTableWidgetItem(f"{sum(tc_values)/len(tc_values):.1f}"))
            
            # Individual method results
            col = 6
            for method_id in self.selected_methods:
                if method_id in data['tc_results']:
                    tc_min = data['tc_results'][method_id]['tc_minutes']
                    self.results_table.setItem(row, col, QTableWidgetItem(f"{tc_min:.1f}"))
                col += 1
                
        # Resize columns
        self.results_table.resizeColumnsToContents()
        
        # Update summary
        if all_tc_values:
            min_tc = min(all_tc_values)
            max_tc = max(all_tc_values)
            avg_tc = sum(all_tc_values) / len(all_tc_values)
            
            summary = f"""
<b>Calculation Summary:</b><br>
- Subbasins processed: {subbasin_count}<br>
- Methods used: {', '.join([self.methods[m].name for m in self.selected_methods])}<br>
- TC range: {min_tc:.1f} - {max_tc:.1f} minutes<br>
- Average TC: {avg_tc:.1f} minutes
            """
            self.summary_label.setText(summary)
            self.summary_label.setStyleSheet("color: #333; padding: 10px;")
            
    def create_outputs(self, subbasin_layer: QgsVectorLayer, results: Dict, 
                      subbasin_field: str, output_dir: str):
        """Create output files"""
        from qgis.PyQt.QtCore import QVariant
        
        # Create output layer with TC fields
        output_layer = QgsVectorLayer(f"Polygon?crs={self.target_crs.authid()}", "subbasins_tc", "memory")
        output_provider = output_layer.dataProvider()
        
        # Copy original fields and add TC fields
        original_fields = subbasin_layer.fields()
        new_fields = [field for field in original_fields]
        
        # Add general TC fields
        new_fields.append(QgsField("Length_ft", QVariant.Double, "double", 12, 2))
        new_fields.append(QgsField("Slope_pct", QVariant.Double, "double", 8, 3))
        new_fields.append(QgsField("TC_min_min", QVariant.Double, "double", 10, 2))
        new_fields.append(QgsField("TC_max_min", QVariant.Double, "double", 10, 2))
        new_fields.append(QgsField("TC_avg_min", QVariant.Double, "double", 10, 2))
        
        # Add method-specific fields
        for method_id in self.selected_methods:
            method_name = self.methods[method_id].name.replace('/', '_')
            new_fields.append(QgsField(f"TC_{method_name}", QVariant.Double, "double", 10, 2))
            
        output_provider.addAttributes(new_fields)
        output_layer.updateFields()
        
        # Add features with TC values
        output_features = []
        
        for orig_feature in subbasin_layer.getFeatures():
            subbasin_id = orig_feature[subbasin_field]
            
            new_feature = QgsFeature()
            new_feature.setGeometry(orig_feature.geometry())
            
            # Copy original attributes
            attributes = list(orig_feature.attributes())
            
            # Add TC data if available
            if subbasin_id in results:
                data = results[subbasin_id]
                tc_values = [result['tc_minutes'] for result in data['tc_results'].values()]
                
                # General TC data
                attributes.extend([
                    data['length_ft'],
                    data['slope_percent'],
                    min(tc_values) if tc_values else None,
                    max(tc_values) if tc_values else None,
                    sum(tc_values)/len(tc_values) if tc_values else None
                ])
                
                # Method-specific data
                for method_id in self.selected_methods:
                    if method_id in data['tc_results']:
                        attributes.append(data['tc_results'][method_id]['tc_minutes'])
                    else:
                        attributes.append(None)
            else:
                # No data for this subbasin
                attributes.extend([None] * (5 + len(self.selected_methods)))
                
            new_feature.setAttributes(attributes)
            output_features.append(new_feature)
            
        output_provider.addFeatures(output_features)
        
        # Save shapefile
        shp_path = os.path.join(output_dir, "subbasins_tc.shp")
        write_options = QgsVectorFileWriter.SaveVectorOptions()
        write_options.driverName = "ESRI Shapefile"
        write_options.fileEncoding = "UTF-8"
        
        error = QgsVectorFileWriter.writeAsVectorFormatV3(
            output_layer, shp_path, QgsProject.instance().transformContext(), write_options
        )
        
        if error[0] != QgsVectorFileWriter.NoError:
            raise ValueError(f"Error saving shapefile: {error[1]}")
            
        # Save detailed CSV
        self.save_detailed_csv(results, output_dir)
        
        self.progress_logger.log(f"Outputs saved to {output_dir}")
        
    def save_detailed_csv(self, results: Dict, output_dir: str):
        """Save detailed TC calculation results to CSV"""
        csv_path = os.path.join(output_dir, "tc_calculations_detailed.csv")
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header
            header = ['Subbasin_ID', 'Length_ft', 'Slope_percent']
            for method_id in self.selected_methods:
                method_name = self.methods[method_id].name
                header.extend([f'{method_name}_minutes', f'{method_name}_hours'])
            header.extend(['Min_TC_minutes', 'Max_TC_minutes', 'Avg_TC_minutes'])
            
            writer.writerow(header)
            
            # Data rows
            for subbasin_id, data in results.items():
                row = [subbasin_id, round(data['length_ft'], 2), round(data['slope_percent'], 3)]
                
                tc_values = []
                for method_id in self.selected_methods:
                    if method_id in data['tc_results']:
                        tc_min = data['tc_results'][method_id]['tc_minutes']
                        tc_hr = data['tc_results'][method_id]['tc_hours']
                        row.extend([round(tc_min, 2), round(tc_hr, 3)])
                        tc_values.append(tc_min)
                    else:
                        row.extend([None, None])
                        
                # Summary stats
                if tc_values:
                    row.extend([
                        round(min(tc_values), 2),
                        round(max(tc_values), 2), 
                        round(sum(tc_values)/len(tc_values), 2)
                    ])
                else:
                    row.extend([None, None, None])
                    
                writer.writerow(row)
                
    def show_completion_dialog(self, results: dict, output_dir: str):
        """Show completion dialog with results summary"""
        processed_count = len(results)
        method_names = [self.methods[m].name for m in self.selected_methods]
        
        message = f"""
Time of Concentration Calculation Completed!

Results Summary:
- Processed {processed_count} subbasins
- Methods used: {', '.join(method_names)}
- Outputs saved to: {output_dir}

Output Files:
- subbasins_tc.shp - Shapefile with TC fields
- tc_calculations_detailed.csv - Detailed results

Would you like to load the results into QGIS?
"""
        
        reply = QMessageBox.question(
            self.gui_widget,
            "Calculation Complete",
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            # Load result layer into QGIS
            shp_path = os.path.join(output_dir, "subbasins_tc.shp")
            result_layer = QgsVectorLayer(shp_path, "Subbasins with TC", "ogr")
            QgsProject.instance().addMapLayer(result_layer)
            self.progress_logger.log("Results loaded into QGIS project", "success")
