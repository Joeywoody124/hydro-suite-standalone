"""
Time of Concentration Calculator Tool for Hydro Suite
Multi-method TC calculator with TR-55 style segment-based approach
Version 2.0 - January 2025

STANDALONE SCRIPT VERSION
Repository: https://github.com/Joeywoody124/hydro-suite-standalone

Changelog v2.0:
- Added flowpaths layer input support (TR-55 compliant)
- Implemented segment-based travel time calculation
- Added flow type specific calculations (Sheet, Shallow Concentrated, Channel, Pipe)
- Removed broken DEM-based slope extraction
- Added proper grouping by subbasin
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
    QTableWidgetItem, QHeaderView, QRadioButton, QButtonGroup
)
from qgis.PyQt.QtCore import Qt, pyqtSignal, QVariant

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


# =============================================================================
# TC Calculation Methods
# =============================================================================

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
            'coefficient': 0.0078,
            'length_exponent': 0.77,
            'slope_exponent': -0.385
        }
        
    def calculate(self, length_ft: float, slope_percent: float, **kwargs) -> float:
        """
        Kirpich formula: tc = 0.0078 * (L^0.77) / (S^0.385)
        where L is length in feet, S is slope in ft/ft
        Returns time in minutes
        """
        if length_ft <= 0 or slope_percent <= 0:
            return 0.0
        
        # Convert slope from percent to ft/ft
        slope_ftft = slope_percent / 100.0
            
        return (self.parameters['coefficient'] * 
                (length_ft ** self.parameters['length_exponent']) / 
                (slope_ftft ** self.parameters['slope_exponent']))


class FAAMethod(TCMethodCalculator):
    """FAA (1965) method for urban areas"""
    
    def __init__(self):
        super().__init__("FAA", "Urban areas, regulatory standard")
        self.parameters = {
            'coefficient': 1.8,
            'length_exponent': 0.5,
            'slope_exponent': -0.33,
            'c_factor': 1.1
        }
        
    def calculate(self, length_ft: float, slope_percent: float, **kwargs) -> float:
        """
        FAA formula: tc = (1.8 * (1.1 - C) * L^0.5) / S^0.33
        Returns time in minutes
        """
        if length_ft <= 0 or slope_percent <= 0:
            return 0.0
            
        c_value = kwargs.get('runoff_coefficient', 0.2)
        
        return ((self.parameters['coefficient'] * 
                (self.parameters['c_factor'] - c_value) * 
                (length_ft ** self.parameters['length_exponent'])) / 
                (slope_percent ** self.parameters['slope_exponent']))


class SCSLagMethod(TCMethodCalculator):
    """SCS/NRCS Lag Method for natural watersheds"""
    
    def __init__(self):
        super().__init__("SCS Lag", "NRCS lag equation (Tc = Lag / 0.6)")
        self.parameters = {
            'coefficient': 0.8,  # (L^0.8)
        }
        
    def calculate(self, length_ft: float, slope_percent: float, **kwargs) -> float:
        """
        SCS Lag formula: Lag = (L^0.8 * ((1000/CN) - 9)^0.7) / (1900 * S^0.5)
        Tc = Lag / 0.6
        Returns time in minutes (converted from hours)
        """
        if length_ft <= 0 or slope_percent <= 0:
            return 0.0
            
        cn = kwargs.get('curve_number', 75)
        if cn <= 0 or cn > 100:
            cn = 75
            
        # Convert slope from percent to ft/ft
        slope_ftft = slope_percent / 100.0
        
        # Calculate lag in hours
        storage_term = (1000.0 / cn) - 9.0
        if storage_term <= 0:
            storage_term = 0.1
            
        lag_hours = ((length_ft ** 0.8) * (storage_term ** 0.7)) / (1900.0 * (slope_ftft ** 0.5))
        
        # Convert to Tc in minutes
        tc_minutes = (lag_hours / 0.6) * 60.0
                
        return tc_minutes


class KerbyMethod(TCMethodCalculator):
    """Kerby method for overland/sheet flow with surface roughness"""
    
    def __init__(self):
        super().__init__("Kerby", "Overland flow with surface roughness")
        self.parameters = {
            'coefficient': 1.44,
            'length_exponent': 0.467,
            'slope_exponent': -0.235,
        }
        
    def calculate(self, length_ft: float, slope_percent: float, **kwargs) -> float:
        """
        Kerby formula: tc = 1.44 * (n * L)^0.467 / S^0.235
        where n is Manning's roughness coefficient
        Returns time in minutes
        """
        if length_ft <= 0 or slope_percent <= 0:
            return 0.0
            
        n = kwargs.get('mannings_n', 0.4)
        
        # Convert slope from percent to ft/ft
        slope_ftft = slope_percent / 100.0
        
        return (self.parameters['coefficient'] * 
                ((n * length_ft) ** self.parameters['length_exponent']) / 
                (slope_ftft ** self.parameters['slope_exponent']))


# =============================================================================
# TR-55 Segment Travel Time Calculators
# =============================================================================

class SegmentTravelTimeCalculator:
    """Calculate travel time for individual flow path segments per TR-55"""
    
    # Sheet flow Manning's n values (TR-55 Table 3-1)
    SHEET_FLOW_N = {
        'SMOOTH': 0.011,
        'FALLOW': 0.05,
        'CULTIVATED_RESIDUE': 0.06,
        'CULTIVATED_NO_RESIDUE': 0.17,
        'GRASS_SHORT': 0.15,
        'GRASS_DENSE': 0.24,
        'GRASS_BERMUDA': 0.41,
        'RANGE_NATURAL': 0.13,
        'WOODS_LIGHT': 0.40,
        'WOODS_DENSE': 0.80,
    }
    
    # Shallow concentrated flow velocities (ft/s) per TR-55
    SHALLOW_CONC_VELOCITY = {
        'PAVED': lambda s: 20.328 * (s ** 0.5),      # Paved: V = 20.328 * S^0.5
        'UNPAVED': lambda s: 16.135 * (s ** 0.5),    # Unpaved: V = 16.135 * S^0.5
    }
    
    @staticmethod
    def sheet_flow_time(length_ft: float, slope_pct: float, mannings_n: float, 
                        rainfall_intensity: float = 2.5) -> float:
        """
        TR-55 Sheet Flow travel time
        
        Tt = (0.007 * (n * L)^0.8) / (P2^0.5 * S^0.4)
        
        Args:
            length_ft: Flow length in feet (max 300 ft per TR-55)
            slope_pct: Slope in percent
            mannings_n: Manning's n for sheet flow surface
            rainfall_intensity: 2-year, 24-hour rainfall in inches (default 2.5)
            
        Returns:
            Travel time in minutes
        """
        # Limit sheet flow to 300 ft per TR-55
        length_ft = min(length_ft, 300.0)
        
        if length_ft <= 0 or slope_pct <= 0 or mannings_n <= 0:
            return 0.0
        
        # Convert slope from percent to ft/ft
        slope_ftft = slope_pct / 100.0
        
        # TR-55 Equation 3-3: Tt in hours
        tt_hours = (0.007 * ((mannings_n * length_ft) ** 0.8)) / \
                   ((rainfall_intensity ** 0.5) * (slope_ftft ** 0.4))
        
        return tt_hours * 60.0  # Convert to minutes
    
    @staticmethod
    def shallow_concentrated_time(length_ft: float, slope_pct: float, 
                                  surface_type: str = 'UNPAVED') -> float:
        """
        TR-55 Shallow Concentrated Flow travel time
        
        Args:
            length_ft: Flow length in feet
            slope_pct: Slope in percent
            surface_type: 'PAVED' or 'UNPAVED'
            
        Returns:
            Travel time in minutes
        """
        if length_ft <= 0 or slope_pct <= 0:
            return 0.0
        
        # Convert slope from percent to ft/ft
        slope_ftft = slope_pct / 100.0
        
        # Get velocity function
        if surface_type.upper() in SegmentTravelTimeCalculator.SHALLOW_CONC_VELOCITY:
            velocity_func = SegmentTravelTimeCalculator.SHALLOW_CONC_VELOCITY[surface_type.upper()]
        else:
            velocity_func = SegmentTravelTimeCalculator.SHALLOW_CONC_VELOCITY['UNPAVED']
        
        # Calculate velocity in ft/s
        velocity_fps = velocity_func(slope_ftft)
        
        if velocity_fps <= 0:
            return 0.0
        
        # Time = Length / Velocity, convert to minutes
        tt_seconds = length_ft / velocity_fps
        return tt_seconds / 60.0
    
    @staticmethod
    def channel_flow_time(length_ft: float, slope_pct: float, mannings_n: float,
                          hydraulic_radius: float = 1.0) -> float:
        """
        Open channel flow travel time using Manning's equation
        
        V = (1.49/n) * R^(2/3) * S^(1/2)
        
        Args:
            length_ft: Channel length in feet
            slope_pct: Channel slope in percent
            mannings_n: Manning's n for channel
            hydraulic_radius: Hydraulic radius in feet (default 1.0)
            
        Returns:
            Travel time in minutes
        """
        if length_ft <= 0 or slope_pct <= 0 or mannings_n <= 0:
            return 0.0
        
        # Convert slope from percent to ft/ft
        slope_ftft = slope_pct / 100.0
        
        # Manning's equation for velocity (ft/s)
        velocity_fps = (1.49 / mannings_n) * (hydraulic_radius ** (2.0/3.0)) * (slope_ftft ** 0.5)
        
        if velocity_fps <= 0:
            return 0.0
        
        # Time = Length / Velocity, convert to minutes
        tt_seconds = length_ft / velocity_fps
        return tt_seconds / 60.0
    
    @staticmethod
    def pipe_flow_time(length_ft: float, slope_pct: float, mannings_n: float = 0.013,
                       diameter_ft: float = 1.5) -> float:
        """
        Pipe flow travel time using Manning's equation (full flow assumed)
        
        Args:
            length_ft: Pipe length in feet
            slope_pct: Pipe slope in percent
            mannings_n: Manning's n for pipe (default 0.013 for concrete)
            diameter_ft: Pipe diameter in feet
            
        Returns:
            Travel time in minutes
        """
        if length_ft <= 0 or slope_pct <= 0 or diameter_ft <= 0:
            return 0.0
        
        # Hydraulic radius for circular pipe flowing full = D/4
        hydraulic_radius = diameter_ft / 4.0
        
        return SegmentTravelTimeCalculator.channel_flow_time(
            length_ft, slope_pct, mannings_n, hydraulic_radius
        )


# =============================================================================
# Main TC Calculator Tool
# =============================================================================

class TCCalculatorTool(HydroToolInterface, LayerSelectionMixin):
    """
    Time of Concentration Calculator with TR-55 style segment-based approach
    
    Version 2.0 - Supports flowpath layer input with segment travel times
    """
    
    def __init__(self):
        super().__init__()
        self.name = "Time of Concentration Calculator"
        self.description = "Calculate TC using TR-55 segment-based travel times from flowpath layer"
        self.category = "Watershed Analysis"
        self.version = "2.0"
        self.author = "Hydro Suite"
        
        # Available whole-watershed methods (for comparison)
        self.methods = {
            'kirpich': KirpichMethod(),
            'faa': FAAMethod(),
            'scs_lag': SCSLagMethod(),
            'kerby': KerbyMethod()
        }
        
        # Tool-specific properties
        self.target_crs = QgsCoordinateReferenceSystem("EPSG:2273")  # SC State Plane
        self.selected_methods = ['kirpich', 'scs_lag']  # Default selection
        
        # GUI components
        self.flowpath_selector = None
        self.output_selector = None
        self.validation_panel = None
        self.progress_logger = None
        self.method_checkboxes = {}
        self.parameter_widgets = {}
        self.results_table = None
        
        # Field selectors
        self.field_subbasin_id = None
        self.field_length = None
        self.field_slope = None
        self.field_mannings_n = None
        self.field_flow_type = None
        
    def create_gui(self, parent_widget: QWidget) -> QWidget:
        """Create the TC Calculator GUI with tabbed interface"""
        # Create tab widget
        tab_widget = QTabWidget(parent_widget)
        
        # Main configuration tab
        main_tab = self.create_main_tab()
        tab_widget.addTab(main_tab, "Configuration")
        
        # Methods tab (for comparison methods)
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
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        main_widget = QWidget()
        scroll.setWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Title and description
        title_label = QLabel(f"<h2>{self.name}</h2>")
        layout.addWidget(title_label)
        
        desc_label = QLabel(
            "<p>This tool calculates time of concentration using TR-55 style "
            "segment-based travel times. Input a flowpaths layer with pre-calculated "
            "length, slope, and Manning's n values for each segment.</p>"
            "<p><b>Flow Types:</b> SHEET, SHALLOW_CONC, CHANNEL, PIPE</p>"
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #555; margin-bottom: 10px;")
        layout.addWidget(desc_label)
        
        # Validation panel
        self.validation_panel = ValidationPanel()
        layout.addWidget(self.validation_panel)
        
        # Input layer section
        inputs_frame = QFrame()
        inputs_frame.setFrameStyle(QFrame.StyledPanel)
        inputs_layout = QVBoxLayout(inputs_frame)
        
        inputs_title = QLabel("<h3>Input Data - Flowpaths Layer</h3>")
        inputs_layout.addWidget(inputs_title)
        
        # Flowpath layer selector
        self.flowpath_selector = LayerFieldSelector(
            "Flowpaths Layer",
            default_field="FP_ID",
            geometry_type=QgsWkbTypes.LineGeometry
        )
        inputs_layout.addWidget(self.flowpath_selector)
        
        # Field mapping section
        fields_group = QGroupBox("Field Mapping")
        fields_layout = QVBoxLayout(fields_group)
        
        # Subbasin ID field
        sb_layout = QHBoxLayout()
        sb_layout.addWidget(QLabel("Subbasin ID Field:"))
        self.field_subbasin_id = QComboBox()
        self.field_subbasin_id.setMinimumWidth(150)
        sb_layout.addWidget(self.field_subbasin_id)
        sb_layout.addStretch()
        fields_layout.addLayout(sb_layout)
        
        # Length field
        len_layout = QHBoxLayout()
        len_layout.addWidget(QLabel("Length (ft) Field:"))
        self.field_length = QComboBox()
        self.field_length.setMinimumWidth(150)
        len_layout.addWidget(self.field_length)
        len_layout.addStretch()
        fields_layout.addLayout(len_layout)
        
        # Slope field
        slope_layout = QHBoxLayout()
        slope_layout.addWidget(QLabel("Slope (%) Field:"))
        self.field_slope = QComboBox()
        self.field_slope.setMinimumWidth(150)
        slope_layout.addWidget(self.field_slope)
        slope_layout.addStretch()
        fields_layout.addLayout(slope_layout)
        
        # Manning's n field
        n_layout = QHBoxLayout()
        n_layout.addWidget(QLabel("Manning's n Field:"))
        self.field_mannings_n = QComboBox()
        self.field_mannings_n.setMinimumWidth(150)
        n_layout.addWidget(self.field_mannings_n)
        n_layout.addStretch()
        fields_layout.addLayout(n_layout)
        
        # Flow type field
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Flow Type Field:"))
        self.field_flow_type = QComboBox()
        self.field_flow_type.setMinimumWidth(150)
        type_layout.addWidget(self.field_flow_type)
        type_layout.addStretch()
        fields_layout.addLayout(type_layout)
        
        inputs_layout.addWidget(fields_group)
        layout.addWidget(inputs_frame)
        
        # Output section
        output_frame = QFrame()
        output_frame.setFrameStyle(QFrame.StyledPanel)
        output_layout = QVBoxLayout(output_frame)
        
        output_title = QLabel("<h3>Output</h3>")
        output_layout.addWidget(output_title)
        
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
        
        # Setup connections
        self.flowpath_selector.layer_changed.connect(self.on_layer_changed)
        self.setup_validation_monitoring()
        
        # Initial validation
        self.validate_and_update()
        
        return scroll
    
    def on_layer_changed(self, layer):
        """Update field combos when layer changes"""
        # Clear existing items
        for combo in [self.field_subbasin_id, self.field_length, self.field_slope,
                      self.field_mannings_n, self.field_flow_type]:
            combo.clear()
            combo.addItem("-- Select Field --", None)
        
        if not layer or not layer.isValid():
            return
        
        # Get field names
        field_names = [field.name() for field in layer.fields()]
        
        # Add fields to combos
        for field_name in field_names:
            for combo in [self.field_subbasin_id, self.field_length, self.field_slope,
                          self.field_mannings_n, self.field_flow_type]:
                combo.addItem(field_name, field_name)
        
        # Try to auto-select common field names
        field_map = {
            self.field_subbasin_id: ['Subbasin_ID', 'SubbasinID', 'SB_ID', 'SBID'],
            self.field_length: ['Length_ft', 'Length', 'LEN', 'LENGTH_FT'],
            self.field_slope: ['Slope_Pct', 'Slope', 'SLOPE', 'SLOPE_PCT'],
            self.field_mannings_n: ['Mannings_n', 'Manning_n', 'N', 'MANNINGS_N'],
            self.field_flow_type: ['Flow_Type', 'FlowType', 'TYPE', 'FLOW_TYPE'],
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
        
        self.progress_logger.log(f"Layer loaded: {layer.name()} ({len(field_names)} fields)")
        
    def create_methods_tab(self) -> QWidget:
        """Create methods selection tab for comparison calculations"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Title
        title = QLabel("<h3>Comparison Methods (Optional)</h3>")
        layout.addWidget(title)
        
        desc = QLabel(
            "Select whole-watershed methods to compare against segment-based TC. "
            "These use total flow length and average slope, useful for validation."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666; margin-bottom: 15px;")
        layout.addWidget(desc)
        
        # Method selection
        methods_frame = QFrame()
        methods_frame.setFrameStyle(QFrame.StyledPanel)
        methods_layout = QVBoxLayout(methods_frame)
        
        for method_id, method in self.methods.items():
            checkbox = QCheckBox(f"{method.name} - {method.description}")
            checkbox.setChecked(method_id in self.selected_methods)
            checkbox.toggled.connect(lambda checked, mid=method_id: self.on_method_toggled(mid, checked))
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
<b>Primary Method (always used):</b><br>
TR-55 Segment-Based: Sums travel times for sheet flow, shallow concentrated flow, 
and channel/pipe flow segments. Most accurate for complex flow paths.<br><br>

<b>Comparison Methods:</b><br>
<b>Kirpich (1940):</b> tc = 0.0078 * L^0.77 / S^0.385 - Best for rural watersheds<br>
<b>FAA (1965):</b> tc = 1.8 * (1.1-C) * L^0.5 / S^0.33 - Urban areas<br>
<b>SCS Lag:</b> Tc = Lag/0.6 where Lag = f(L, CN, S) - NRCS standard<br>
<b>Kerby:</b> tc = 1.44 * (nL)^0.467 / S^0.235 - Overland flow only<br>
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
        title = QLabel("<h3>Calculation Parameters</h3>")
        layout.addWidget(title)
        
        # TR-55 parameters
        tr55_group = QGroupBox("TR-55 Segment Parameters")
        tr55_layout = QVBoxLayout(tr55_group)
        
        # 2-year rainfall
        p2_layout = QHBoxLayout()
        p2_layout.addWidget(QLabel("2-yr 24-hr Rainfall (in):"))
        self.p2_spin = QDoubleSpinBox()
        self.p2_spin.setRange(1.0, 10.0)
        self.p2_spin.setValue(3.5)  # SC Lowcountry typical
        self.p2_spin.setSingleStep(0.1)
        self.p2_spin.setDecimals(1)
        self.p2_spin.setToolTip("Used for sheet flow calculation (TR-55 Eq. 3-3)")
        p2_layout.addWidget(self.p2_spin)
        p2_layout.addStretch()
        tr55_layout.addLayout(p2_layout)
        
        # Default hydraulic radius for channels
        hr_layout = QHBoxLayout()
        hr_layout.addWidget(QLabel("Default Hydraulic Radius (ft):"))
        self.hr_spin = QDoubleSpinBox()
        self.hr_spin.setRange(0.1, 10.0)
        self.hr_spin.setValue(1.0)
        self.hr_spin.setSingleStep(0.1)
        self.hr_spin.setDecimals(2)
        self.hr_spin.setToolTip("Used when not provided in layer attributes")
        hr_layout.addWidget(self.hr_spin)
        hr_layout.addStretch()
        tr55_layout.addLayout(hr_layout)
        
        layout.addWidget(tr55_group)
        
        # Comparison method parameters
        for method_id, method in self.methods.items():
            group = QGroupBox(f"{method.name} Parameters")
            group_layout = QVBoxLayout(group)
            
            method_widgets = {}
            
            if method_id == 'faa':
                rc_layout = QHBoxLayout()
                rc_layout.addWidget(QLabel("Runoff Coefficient:"))
                rc_spin = QDoubleSpinBox()
                rc_spin.setRange(0.1, 0.95)
                rc_spin.setValue(0.3)
                rc_spin.setSingleStep(0.05)
                rc_spin.setDecimals(2)
                rc_layout.addWidget(rc_spin)
                rc_layout.addStretch()
                group_layout.addLayout(rc_layout)
                method_widgets['runoff_coefficient'] = rc_spin
                
            elif method_id == 'scs_lag':
                cn_layout = QHBoxLayout()
                cn_layout.addWidget(QLabel("Curve Number:"))
                cn_spin = QSpinBox()
                cn_spin.setRange(30, 98)
                cn_spin.setValue(75)
                cn_layout.addWidget(cn_spin)
                cn_layout.addStretch()
                group_layout.addLayout(cn_layout)
                method_widgets['curve_number'] = cn_spin
                
            elif method_id == 'kerby':
                n_layout = QHBoxLayout()
                n_layout.addWidget(QLabel("Manning's n (avg):"))
                n_spin = QDoubleSpinBox()
                n_spin.setRange(0.01, 1.0)
                n_spin.setValue(0.4)
                n_spin.setSingleStep(0.05)
                n_spin.setDecimals(2)
                n_layout.addWidget(n_spin)
                n_layout.addStretch()
                group_layout.addLayout(n_layout)
                method_widgets['mannings_n'] = n_spin
                
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
        self.validation_panel.add_validation("flowpath", "Flowpaths layer")
        self.validation_panel.add_validation("fields", "Required field mapping")
        self.validation_panel.add_validation("output", "Output directory")
        
        self.flowpath_selector.selection_valid.connect(
            lambda valid: self.validation_panel.set_validation_status("flowpath", valid)
        )
        self.output_selector.directory_selected.connect(
            lambda dir: self.validation_panel.set_validation_status("output", bool(dir))
        )
        
    def validate_and_update(self):
        """Validate all inputs and update UI"""
        self.flowpath_selector.validate_selection()
        
        # Validate field selections
        fields_valid = all([
            self.field_subbasin_id.currentData() is not None,
            self.field_length.currentData() is not None,
            self.field_slope.currentData() is not None,
            self.field_mannings_n.currentData() is not None,
            self.field_flow_type.currentData() is not None,
        ])
        self.validation_panel.set_validation_status("fields", fields_valid)
        
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
        
        if not self.flowpath_selector.is_valid():
            errors.append("Invalid flowpaths layer selection")
            
        if not all([self.field_subbasin_id.currentData(),
                    self.field_length.currentData(),
                    self.field_slope.currentData(),
                    self.field_mannings_n.currentData(),
                    self.field_flow_type.currentData()]):
            errors.append("Not all required fields are mapped")
            
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
                
            # Get inputs
            flowpath_layer = self.flowpath_selector.get_selected_layer()
            output_dir = self.output_selector.get_selected_directory()
            
            # Get field names
            field_names = {
                'subbasin_id': self.field_subbasin_id.currentData(),
                'length': self.field_length.currentData(),
                'slope': self.field_slope.currentData(),
                'mannings_n': self.field_mannings_n.currentData(),
                'flow_type': self.field_flow_type.currentData(),
            }
            
            progress_callback(10, "Reading flowpath segments...")
            
            # Process flowpaths by subbasin
            results = self.calculate_tc_from_flowpaths(flowpath_layer, field_names, progress_callback)
            
            # Calculate comparison methods
            progress_callback(70, "Calculating comparison methods...")
            self.add_comparison_methods(results, field_names)
            
            # Create outputs
            progress_callback(85, "Creating output files...")
            self.create_outputs(results, output_dir)
            
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
            
    def calculate_tc_from_flowpaths(self, layer: QgsVectorLayer, field_names: dict,
                                    progress_callback: Callable) -> Dict:
        """
        Calculate TC for each subbasin by summing segment travel times
        
        Returns dict keyed by subbasin_id with segment details and total TC
        """
        results = {}
        p2_rainfall = self.p2_spin.value()
        default_hr = self.hr_spin.value()
        
        # Group features by subbasin
        subbasin_segments = {}
        
        for feature in layer.getFeatures():
            subbasin_id = str(feature[field_names['subbasin_id']])
            
            if subbasin_id not in subbasin_segments:
                subbasin_segments[subbasin_id] = []
            
            segment = {
                'length_ft': float(feature[field_names['length']] or 0),
                'slope_pct': float(feature[field_names['slope']] or 0),
                'mannings_n': float(feature[field_names['mannings_n']] or 0.035),
                'flow_type': str(feature[field_names['flow_type']] or 'CHANNEL').upper(),
            }
            subbasin_segments[subbasin_id].append(segment)
        
        # Calculate travel time for each subbasin
        total_subbasins = len(subbasin_segments)
        
        for i, (subbasin_id, segments) in enumerate(subbasin_segments.items()):
            total_tt = 0.0
            total_length = 0.0
            segment_details = []
            
            for seg in segments:
                flow_type = seg['flow_type']
                length = seg['length_ft']
                slope = seg['slope_pct']
                n = seg['mannings_n']
                
                # Calculate travel time based on flow type
                if 'SHEET' in flow_type:
                    tt = SegmentTravelTimeCalculator.sheet_flow_time(
                        length, slope, n, p2_rainfall
                    )
                elif 'SHALLOW' in flow_type or 'CONC' in flow_type:
                    # Determine if paved or unpaved from Manning's n
                    surface = 'PAVED' if n < 0.02 else 'UNPAVED'
                    tt = SegmentTravelTimeCalculator.shallow_concentrated_time(
                        length, slope, surface
                    )
                elif 'PIPE' in flow_type:
                    tt = SegmentTravelTimeCalculator.pipe_flow_time(
                        length, slope, n
                    )
                else:  # CHANNEL or default
                    tt = SegmentTravelTimeCalculator.channel_flow_time(
                        length, slope, n, default_hr
                    )
                
                total_tt += tt
                total_length += length
                
                segment_details.append({
                    'flow_type': flow_type,
                    'length_ft': length,
                    'slope_pct': slope,
                    'mannings_n': n,
                    'travel_time_min': tt
                })
            
            # Calculate average slope (length-weighted)
            if total_length > 0:
                avg_slope = sum(s['slope_pct'] * s['length_ft'] for s in segments) / total_length
            else:
                avg_slope = 0.0
            
            results[subbasin_id] = {
                'tc_segment_min': total_tt,
                'total_length_ft': total_length,
                'avg_slope_pct': avg_slope,
                'segment_count': len(segments),
                'segments': segment_details,
                'comparison_methods': {}
            }
            
            progress = 10 + int((i + 1) / total_subbasins * 55)
            progress_callback(progress, f"Processed {i + 1}/{total_subbasins} subbasins")
        
        return results
    
    def add_comparison_methods(self, results: Dict, field_names: dict):
        """Add comparison method calculations to results"""
        method_params = self.get_current_parameters()
        
        for subbasin_id, data in results.items():
            total_length = data['total_length_ft']
            avg_slope = data['avg_slope_pct']
            
            for method_id in self.selected_methods:
                method = self.methods[method_id]
                params = method_params.get(method_id, {})
                
                tc_minutes = method.calculate(total_length, avg_slope, **params)
                data['comparison_methods'][method_id] = {
                    'tc_minutes': tc_minutes,
                    'method_name': method.name
                }
    
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
        subbasin_count = len(results)
        
        # Columns: Subbasin, Segments, Length, Slope, TC (Segment), then comparison methods
        columns = ['Subbasin', 'Segments', 'Total Length (ft)', 'Avg Slope (%)', 
                   'TC Segment (min)']
        for method_id in self.selected_methods:
            method_name = self.methods[method_id].name
            columns.append(f'{method_name} (min)')
            
        self.results_table.setRowCount(subbasin_count)
        self.results_table.setColumnCount(len(columns))
        self.results_table.setHorizontalHeaderLabels(columns)
        
        all_tc_values = []
        
        for row, (subbasin_id, data) in enumerate(results.items()):
            self.results_table.setItem(row, 0, QTableWidgetItem(str(subbasin_id)))
            self.results_table.setItem(row, 1, QTableWidgetItem(str(data['segment_count'])))
            self.results_table.setItem(row, 2, QTableWidgetItem(f"{data['total_length_ft']:.0f}"))
            self.results_table.setItem(row, 3, QTableWidgetItem(f"{data['avg_slope_pct']:.2f}"))
            self.results_table.setItem(row, 4, QTableWidgetItem(f"{data['tc_segment_min']:.1f}"))
            
            all_tc_values.append(data['tc_segment_min'])
            
            # Comparison methods
            col = 5
            for method_id in self.selected_methods:
                if method_id in data['comparison_methods']:
                    tc_min = data['comparison_methods'][method_id]['tc_minutes']
                    self.results_table.setItem(row, col, QTableWidgetItem(f"{tc_min:.1f}"))
                    all_tc_values.append(tc_min)
                col += 1
                
        self.results_table.resizeColumnsToContents()
        
        # Update summary
        if all_tc_values:
            min_tc = min(all_tc_values)
            max_tc = max(all_tc_values)
            avg_tc = sum(all_tc_values) / len(all_tc_values)
            
            summary = f"""
<b>Calculation Summary:</b><br>
- Subbasins processed: {subbasin_count}<br>
- Primary method: TR-55 Segment-Based<br>
- Comparison methods: {', '.join([self.methods[m].name for m in self.selected_methods])}<br>
- TC range: {min_tc:.1f} - {max_tc:.1f} minutes<br>
            """
            self.summary_label.setText(summary)
            self.summary_label.setStyleSheet("color: #333; padding: 10px;")
            
    def create_outputs(self, results: Dict, output_dir: str):
        """Create output files"""
        # Save detailed CSV
        csv_path = os.path.join(output_dir, "tc_calculations.csv")
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header
            header = ['Subbasin_ID', 'Segment_Count', 'Total_Length_ft', 'Avg_Slope_pct',
                     'TC_Segment_min']
            for method_id in self.selected_methods:
                header.append(f'TC_{self.methods[method_id].name}_min')
            writer.writerow(header)
            
            # Data rows
            for subbasin_id, data in results.items():
                row = [
                    subbasin_id,
                    data['segment_count'],
                    round(data['total_length_ft'], 1),
                    round(data['avg_slope_pct'], 3),
                    round(data['tc_segment_min'], 2)
                ]
                for method_id in self.selected_methods:
                    if method_id in data['comparison_methods']:
                        row.append(round(data['comparison_methods'][method_id]['tc_minutes'], 2))
                    else:
                        row.append(None)
                writer.writerow(row)
        
        # Save segment details
        detail_path = os.path.join(output_dir, "tc_segment_details.csv")
        
        with open(detail_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Subbasin_ID', 'Flow_Type', 'Length_ft', 'Slope_pct', 
                            'Mannings_n', 'Travel_Time_min'])
            
            for subbasin_id, data in results.items():
                for seg in data['segments']:
                    writer.writerow([
                        subbasin_id,
                        seg['flow_type'],
                        round(seg['length_ft'], 1),
                        round(seg['slope_pct'], 3),
                        round(seg['mannings_n'], 3),
                        round(seg['travel_time_min'], 2)
                    ])
                    
        self.progress_logger.log(f"Outputs saved to {output_dir}")
        
    def show_completion_dialog(self, results: dict, output_dir: str):
        """Show completion dialog with results summary"""
        processed_count = len(results)
        
        message = f"""
Time of Concentration Calculation Completed!

Results Summary:
- Processed {processed_count} subbasins
- Primary method: TR-55 Segment-Based Travel Times
- Comparison methods: {', '.join([self.methods[m].name for m in self.selected_methods])}
- Outputs saved to: {output_dir}

Output Files:
- tc_calculations.csv - TC summary by subbasin
- tc_segment_details.csv - Individual segment travel times
"""
        
        QMessageBox.information(self.gui_widget, "Calculation Complete", message)
