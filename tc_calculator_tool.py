"""
Time of Concentration Calculator Tool for Hydro Suite - ENHANCED VERSION
Multi-method TC calculator with per-subbasin custom parameters
Version 2.5 - January 2025

STANDALONE SCRIPT VERSION
Repository: https://github.com/Joeywoody124/hydro-suite-standalone

Features:
- THREE MODES: Flowpath-based (TR-55) OR Manual Entry OR DEM Extraction
- TR-55 segment-based travel time calculation
- DEM-based flowpath extraction with flat terrain fallback methods
- Auto-extract flowpath length and slope from DEM for each subbasin
- Per-subbasin custom parameters (CN, C, Manning's n)
- Per-subbasin channel/pipe geometry definitions
- Industry-standard low-slope adjustments (TxDOT/Cleveland 2012)
- Comparison methods with subbasin-specific inputs
- CSV import/export for subbasin parameters and geometry

Flat Terrain Fallback Methods (per TxDOT/Cleveland et al. 2012):
- If S < 0.2%: Add 0.0005 to slope
- If S between 0.2-0.3%: Transitional - flag for review
- If adverse slope (S < 0): Use minimum slope 0.05%
- Minimum TC: 6 min (default), 5 min (paved), 10 min (rural)

References:
- TR-55: Urban Hydrology for Small Watersheds (USDA-SCS, 1986)
- NEH Part 630, Chapter 15: Time of Concentration (NRCS, 2010)
- TxDOT Hydraulic Design Manual, Chapter 4 (2023)
- Cleveland et al. 2012: Time of Concentration for Low-Slope Watersheds
- Iowa DNR WinTR-55 Procedures
- California Highway Design Manual Section 816
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
    QTableWidgetItem, QHeaderView, QRadioButton, QButtonGroup,
    QFileDialog, QLineEdit, QSplitter, QStackedWidget, QProgressBar
)
from qgis.PyQt.QtCore import Qt, pyqtSignal, QVariant

from qgis.core import (
    QgsCoordinateReferenceSystem, QgsProject,
    QgsVectorFileWriter, QgsVectorLayer, QgsRasterLayer, QgsField, QgsFeature,
    QgsWkbTypes, QgsPointXY, QgsGeometry, QgsCoordinateTransform
)

# Import DEM extraction module for flowpath extraction from DEM
try:
    from dem_extraction import (
        DEMFlowpathExtractor,
        SCSLagDEMCalculator,
        TR55VelocityDEMCalculator
    )
    HAS_DEM_EXTRACTION = True
except ImportError:
    HAS_DEM_EXTRACTION = False
    DEMFlowpathExtractor = None
    SCSLagDEMCalculator = None
    TR55VelocityDEMCalculator = None

# Import our shared components
from hydro_suite_interface import HydroToolInterface, LayerSelectionMixin
from shared_widgets import (
    LayerFieldSelector, FileSelector, DirectorySelector, 
    ProgressLogger, ValidationPanel
)


# =============================================================================
# FLAT TERRAIN CONSTANTS (Industry Standards)
# =============================================================================

# TxDOT/Cleveland et al. 2012 low-slope adjustment thresholds
MIN_SLOPE_THRESHOLD = 0.002  # 0.2% - Below this, apply adjustment
TRANSITIONAL_SLOPE_UPPER = 0.003  # 0.3% - Between 0.2-0.3% is transitional
LOW_SLOPE_ADJUSTMENT = 0.0005  # Add to slope when S < MIN_SLOPE_THRESHOLD

# Minimum TC values (NRCS/California HDM)
MIN_TC_PAVED = 5.0  # minutes - for paved urban areas
MIN_TC_RURAL = 10.0  # minutes - for rural/undeveloped areas
MIN_TC_DEFAULT = 6.0  # minutes - NRCS default (0.1 hour)

# Sheet flow maximum length per TR-55
MAX_SHEET_FLOW_LENGTH = 300.0  # feet

# NRCS WinTR-55 valid ranges for SCS Lag method
SCS_LAG_MIN_CN = 50
SCS_LAG_MAX_CN = 95
SCS_LAG_MIN_SLOPE_PCT = 0.5
SCS_LAG_MAX_SLOPE_PCT = 64.0
SCS_LAG_MIN_LENGTH_FT = 200
SCS_LAG_MAX_LENGTH_FT = 26000


# =============================================================================
# FLAT TERRAIN ADJUSTMENT FUNCTIONS
# =============================================================================

def apply_slope_adjustment(slope_ftft: float) -> Tuple[float, bool, str]:
    """
    Apply industry-standard slope adjustments for flat terrain
    Based on TxDOT/Cleveland et al. 2012
    
    Returns: (adjusted_slope, was_adjusted, warning_message)
    """
    adjusted = False
    warning = None
    
    if slope_ftft < 0:
        # Adverse slope - physically impossible for gravity flow
        adjusted_slope = LOW_SLOPE_ADJUSTMENT
        adjusted = True
        warning = f"Adverse slope ({slope_ftft*100:.3f}%). Applied minimum slope of {LOW_SLOPE_ADJUSTMENT*100:.2f}%"
    elif slope_ftft < MIN_SLOPE_THRESHOLD:
        # Low slope condition - apply TxDOT adjustment
        adjusted_slope = slope_ftft + LOW_SLOPE_ADJUSTMENT
        adjusted = True
        warning = f"Low slope ({slope_ftft*100:.3f}%). Applied TxDOT adjustment: S + 0.0005 = {adjusted_slope*100:.3f}%"
    elif slope_ftft < TRANSITIONAL_SLOPE_UPPER:
        # Transitional - flag but don't adjust
        adjusted_slope = slope_ftft
        warning = f"Transitional slope ({slope_ftft*100:.3f}%). Consider reviewing."
    else:
        # Normal slope - no adjustment needed
        adjusted_slope = slope_ftft
    
    return adjusted_slope, adjusted, warning


def apply_tc_minimum(tc_minutes: float, land_type: str = 'rural') -> Tuple[float, bool, str]:
    """
    Apply minimum TC per NRCS/California HDM guidance
    
    Returns: (adjusted_tc, was_adjusted, warning_message)
    """
    if land_type.lower() in ['paved', 'urban', 'impervious', 'commercial']:
        min_tc = MIN_TC_PAVED
    elif land_type.lower() in ['rural', 'undeveloped', 'natural', 'woods', 'forest']:
        min_tc = MIN_TC_RURAL
    else:
        min_tc = MIN_TC_DEFAULT
    
    if tc_minutes < min_tc:
        warning = f"Computed TC ({tc_minutes:.1f} min) below minimum. Using {min_tc} min per NRCS guidance."
        return min_tc, True, warning
    
    return tc_minutes, False, None


# =============================================================================
# HYDRAULIC CALCULATIONS
# =============================================================================

def calc_hydraulic_radius(depth: float, bottom_width: float, side_slope: float) -> float:
    """Calculate hydraulic radius for trapezoidal channel"""
    if depth <= 0 or bottom_width <= 0:
        return 1.0
    top_width = bottom_width + 2 * side_slope * depth
    area = (bottom_width + top_width) / 2 * depth
    side_length = depth * math.sqrt(1 + side_slope**2)
    wetted_perimeter = bottom_width + 2 * side_length
    return area / wetted_perimeter if wetted_perimeter > 0 else 1.0


def calc_pipe_hydraulic_radius(diameter: float) -> float:
    """Calculate hydraulic radius for circular pipe flowing full (R = D/4)"""
    return diameter / 4.0 if diameter > 0 else 0.375


# =============================================================================
# TR-55 SEGMENT TRAVEL TIME CALCULATORS
# =============================================================================

class SegmentTravelTimeCalculator:
    """Calculate travel time for individual flow path segments per TR-55"""
    
    @staticmethod
    def sheet_flow_time(length_ft: float, slope_pct: float, mannings_n: float, 
                        rainfall_intensity: float = 3.5) -> float:
        """TR-55 Equation 3-3: Sheet Flow travel time (returns minutes)"""
        length_ft = min(length_ft, 300.0)  # Max 300 ft per TR-55
        if length_ft <= 0 or slope_pct <= 0 or mannings_n <= 0:
            return 0.0
        slope_ftft = slope_pct / 100.0
        tt_hours = (0.007 * ((mannings_n * length_ft) ** 0.8)) / \
                   ((rainfall_intensity ** 0.5) * (slope_ftft ** 0.4))
        return tt_hours * 60.0
    
    @staticmethod
    def shallow_concentrated_time(length_ft: float, slope_pct: float, 
                                  surface_type: str = 'UNPAVED') -> float:
        """TR-55 Shallow Concentrated Flow travel time (returns minutes)"""
        if length_ft <= 0 or slope_pct <= 0:
            return 0.0
        slope_ftft = slope_pct / 100.0
        if surface_type.upper() == 'PAVED':
            velocity_fps = 20.328 * (slope_ftft ** 0.5)
        else:
            velocity_fps = 16.135 * (slope_ftft ** 0.5)
        if velocity_fps <= 0:
            return 0.0
        return (length_ft / velocity_fps) / 60.0
    
    @staticmethod
    def channel_flow_time(length_ft: float, slope_pct: float, mannings_n: float,
                          hydraulic_radius: float = 1.0) -> float:
        """Open channel flow travel time using Manning's (returns minutes)"""
        if length_ft <= 0 or slope_pct <= 0 or mannings_n <= 0:
            return 0.0
        slope_ftft = slope_pct / 100.0
        velocity_fps = (1.49 / mannings_n) * (hydraulic_radius ** (2.0/3.0)) * (slope_ftft ** 0.5)
        if velocity_fps <= 0:
            return 0.0
        return (length_ft / velocity_fps) / 60.0
    
    @staticmethod
    def pipe_flow_time(length_ft: float, slope_pct: float, mannings_n: float = 0.013,
                       diameter_ft: float = 1.5) -> float:
        """Pipe flow travel time (full flow, returns minutes)"""
        if length_ft <= 0 or slope_pct <= 0 or diameter_ft <= 0:
            return 0.0
        hydraulic_radius = diameter_ft / 4.0
        return SegmentTravelTimeCalculator.channel_flow_time(
            length_ft, slope_pct, mannings_n, hydraulic_radius
        )


# =============================================================================
# WHOLE-WATERSHED TC METHODS
# =============================================================================

class TCMethodCalculator:
    """Base class for TC calculation methods"""
    
    def __init__(self, name: str, description: str, param_name: str = None):
        self.name = name
        self.description = description
        self.param_name = param_name
        
    def calculate(self, length_ft: float, slope_percent: float, **kwargs) -> float:
        raise NotImplementedError


class KirpichMethod(TCMethodCalculator):
    """Kirpich (1940) method"""
    
    def __init__(self):
        super().__init__("Kirpich", "Rural watersheds", None)
        
    def calculate(self, length_ft: float, slope_percent: float, **kwargs) -> float:
        if length_ft <= 0 or slope_percent <= 0:
            return 0.0
        slope_ftft = slope_percent / 100.0
        return 0.0078 * (length_ft ** 0.77) / (slope_ftft ** 0.385)


class FAAMethod(TCMethodCalculator):
    """FAA (1965) method - uses runoff coefficient C"""
    
    def __init__(self):
        super().__init__("FAA", "Urban areas (uses C)", "c_value")
        
    def calculate(self, length_ft: float, slope_percent: float, **kwargs) -> float:
        if length_ft <= 0 or slope_percent <= 0:
            return 0.0
        c_value = kwargs.get('c_value', 0.3)
        return (1.8 * (1.1 - c_value) * (length_ft ** 0.5)) / (slope_percent ** 0.33)


class SCSLagMethod(TCMethodCalculator):
    """
    SCS/NRCS Lag Method - uses curve number CN
    
    Reference: NRCS NEH Part 630, Chapter 15 (2010)
    
    Equation:
        Lag (hours) = (L^0.8 * S^0.7) / (1900 * Y^0.5)
        Tc = Lag / 0.6
    
    Where:
        L = hydraulic length of watershed (feet)
        S = (1000/CN) - 9 = maximum retention (inches)
        Y = average watershed slope in PERCENT (not ft/ft!)
    
    IMPORTANT: Unlike other methods, SCS Lag uses slope in PERCENT directly.
    This is per the original NRCS documentation and WinTR-55.
    """
    
    def __init__(self):
        super().__init__("SCS Lag", "NRCS standard (uses CN)", "cn")
        
    def calculate(self, length_ft: float, slope_percent: float, **kwargs) -> float:
        if length_ft <= 0 or slope_percent <= 0:
            return 0.0
        cn = kwargs.get('cn', 75)
        if cn <= 0 or cn > 100:
            cn = 75
        # Calculate storage term S = (1000/CN) - 9
        storage_term = (1000.0 / cn) - 9.0
        if storage_term <= 0:
            storage_term = 0.1
        # NRCS SCS Lag equation uses slope in PERCENT directly (not ft/ft)
        # Lag (hours) = (L^0.8 * S^0.7) / (1900 * Y^0.5)
        lag_hours = ((length_ft ** 0.8) * (storage_term ** 0.7)) / (1900.0 * (slope_percent ** 0.5))
        # Tc = Lag / 0.6, then convert hours to minutes
        return (lag_hours / 0.6) * 60.0


class KerbyMethod(TCMethodCalculator):
    """Kerby method - uses Manning's n for overland flow"""
    
    def __init__(self):
        super().__init__("Kerby", "Overland flow (uses n)", "mannings_n")
        
    def calculate(self, length_ft: float, slope_percent: float, **kwargs) -> float:
        if length_ft <= 0 or slope_percent <= 0:
            return 0.0
        n = kwargs.get('mannings_n', 0.4)
        slope_ftft = slope_percent / 100.0
        return 1.44 * ((n * length_ft) ** 0.467) / (slope_ftft ** 0.235)


# =============================================================================
# MANUAL ENTRY TABLE WIDGET
# =============================================================================

class ManualEntryTable(QWidget):
    """Widget for manual entry of subbasin parameters (no flowpath layer required)"""
    
    data_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Instructions
        desc = QLabel(
            "<b>Manual Entry Mode</b> - Enter subbasin data directly without a flowpath layer.<br>"
            "All comparison methods will be calculated. Segment-based TC is not available in this mode."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #555; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            'Subbasin ID', 'Length (ft)', 'Slope (%)', 'CN', 'C Value', "Manning's n"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("Add Subbasin")
        add_btn.clicked.connect(self.add_row)
        btn_layout.addWidget(add_btn)
        
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self.remove_selected)
        btn_layout.addWidget(remove_btn)
        
        load_btn = QPushButton("Load from CSV")
        load_btn.clicked.connect(self.load_from_csv)
        btn_layout.addWidget(load_btn)
        
        save_btn = QPushButton("Save to CSV")
        save_btn.clicked.connect(self.save_to_csv)
        btn_layout.addWidget(save_btn)
        
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self.clear_table)
        btn_layout.addWidget(clear_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Connect cell changes
        self.table.cellChanged.connect(lambda: self.data_changed.emit())
        
        # Add initial row
        self.add_row()
        
    def add_row(self):
        """Add a new row with default values"""
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Default values
        defaults = [f'SB-{row+1:03d}', '2100', '2.0', '75', '0.3', '0.4']
        for col, val in enumerate(defaults):
            self.table.setItem(row, col, QTableWidgetItem(val))
        
        self.data_changed.emit()
        
    def remove_selected(self):
        """Remove selected rows"""
        rows = set(item.row() for item in self.table.selectedItems())
        for row in sorted(rows, reverse=True):
            self.table.removeRow(row)
        self.data_changed.emit()
        
    def clear_table(self):
        """Clear all rows"""
        self.table.setRowCount(0)
        self.add_row()
        self.data_changed.emit()
        
    def get_data(self) -> List[Dict]:
        """Get all data from the table"""
        data = []
        for row in range(self.table.rowCount()):
            try:
                entry = {
                    'subbasin_id': self.table.item(row, 0).text() if self.table.item(row, 0) else f'SB-{row+1:03d}',
                    'length_ft': float(self.table.item(row, 1).text()) if self.table.item(row, 1) else 2100,
                    'slope_pct': float(self.table.item(row, 2).text()) if self.table.item(row, 2) else 2.0,
                    'cn': float(self.table.item(row, 3).text()) if self.table.item(row, 3) else 75,
                    'c_value': float(self.table.item(row, 4).text()) if self.table.item(row, 4) else 0.3,
                    'mannings_n': float(self.table.item(row, 5).text()) if self.table.item(row, 5) else 0.4,
                }
                if entry['subbasin_id']:
                    data.append(entry)
            except (ValueError, AttributeError):
                continue
        return data
    
    def has_valid_data(self) -> bool:
        """Check if table has at least one valid row"""
        return len(self.get_data()) > 0
    
    def load_from_csv(self):
        """Load data from CSV file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Subbasin Data", "", "CSV files (*.csv)"
        )
        if not file_path:
            return
        
        try:
            self.table.setRowCount(0)
            with open(file_path, 'r') as f:
                reader = csv.DictReader(f)
                for row_data in reader:
                    row = self.table.rowCount()
                    self.table.insertRow(row)
                    
                    # Map various column name formats
                    sb_id = row_data.get('subbasin_id', row_data.get('Subbasin_ID', f'SB-{row+1:03d}'))
                    length = row_data.get('length_ft', row_data.get('Length_ft', row_data.get('Length', '2100')))
                    slope = row_data.get('slope_pct', row_data.get('Slope_Pct', row_data.get('Slope', '2.0')))
                    cn = row_data.get('cn', row_data.get('CN', '75'))
                    c_val = row_data.get('c_value', row_data.get('C_Value', row_data.get('C', '0.3')))
                    n_val = row_data.get('mannings_n', row_data.get('Mannings_n', row_data.get('n', '0.4')))
                    
                    values = [sb_id, length, slope, cn, c_val, n_val]
                    for col, val in enumerate(values):
                        self.table.setItem(row, col, QTableWidgetItem(str(val)))
            
            self.data_changed.emit()
            QMessageBox.information(self, "Loaded", f"Loaded {self.table.rowCount()} subbasins from CSV")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading CSV: {str(e)}")
    
    def save_to_csv(self):
        """Save data to CSV file"""
        data = self.get_data()
        if not data:
            QMessageBox.warning(self, "No Data", "No data to save")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Subbasin Data", "subbasin_manual_entry.csv", "CSV files (*.csv)"
        )
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['subbasin_id', 'length_ft', 'slope_pct', 'cn', 'c_value', 'mannings_n'])
                for entry in data:
                    writer.writerow([
                        entry['subbasin_id'], entry['length_ft'], entry['slope_pct'],
                        entry['cn'], entry['c_value'], entry['mannings_n']
                    ])
            QMessageBox.information(self, "Saved", f"Saved to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving CSV: {str(e)}")


# =============================================================================
# SUBBASIN PARAMETERS TABLE WIDGET
# =============================================================================

class SubbasinParametersTable(QWidget):
    """Widget for managing per-subbasin custom parameters"""
    
    parameters_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.subbasin_params = {}
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("<b>Subbasin Parameters</b> (for comparison methods)")
        layout.addWidget(title)
        
        desc = QLabel("Set CN (SCS Lag), C (FAA), and n (Kerby) per subbasin.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(desc)
        
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(['Subbasin ID', 'CN', 'C Value', "Manning's n"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)
        
        btn_layout = QHBoxLayout()
        load_btn = QPushButton("Load from CSV")
        load_btn.clicked.connect(self.load_from_csv)
        btn_layout.addWidget(load_btn)
        
        save_btn = QPushButton("Save to CSV")
        save_btn.clicked.connect(self.save_to_csv)
        btn_layout.addWidget(save_btn)
        
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self.clear_table)
        btn_layout.addWidget(clear_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.table.cellChanged.connect(self.on_cell_changed)
        
    def populate_from_flowpaths(self, subbasin_ids: List[str], defaults: dict = None):
        """Populate table with subbasin IDs"""
        if defaults is None:
            defaults = {'cn': 75, 'c_value': 0.3, 'mannings_n': 0.4}
        
        self.table.blockSignals(True)
        self.table.setRowCount(len(subbasin_ids))
        
        for row, sb_id in enumerate(sorted(subbasin_ids)):
            params = self.subbasin_params.get(sb_id, defaults)
            
            id_item = QTableWidgetItem(str(sb_id))
            id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 0, id_item)
            
            self.table.setItem(row, 1, QTableWidgetItem(str(params.get('cn', defaults['cn']))))
            self.table.setItem(row, 2, QTableWidgetItem(str(params.get('c_value', defaults['c_value']))))
            self.table.setItem(row, 3, QTableWidgetItem(str(params.get('mannings_n', defaults['mannings_n']))))
            
            self.subbasin_params[sb_id] = {
                'cn': params.get('cn', defaults['cn']),
                'c_value': params.get('c_value', defaults['c_value']),
                'mannings_n': params.get('mannings_n', defaults['mannings_n'])
            }
        
        self.table.blockSignals(False)
        self.table.resizeColumnsToContents()
        
    def on_cell_changed(self, row, col):
        if col == 0:
            return
        sb_id = self.table.item(row, 0).text()
        if sb_id not in self.subbasin_params:
            self.subbasin_params[sb_id] = {}
        try:
            value = float(self.table.item(row, col).text())
            if col == 1:
                self.subbasin_params[sb_id]['cn'] = value
            elif col == 2:
                self.subbasin_params[sb_id]['c_value'] = value
            elif col == 3:
                self.subbasin_params[sb_id]['mannings_n'] = value
            self.parameters_changed.emit()
        except ValueError:
            pass
    
    def get_params(self, subbasin_id: str) -> dict:
        return self.subbasin_params.get(subbasin_id, {'cn': 75, 'c_value': 0.3, 'mannings_n': 0.4})
    
    def load_from_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Subbasin Parameters", "", "CSV files (*.csv)")
        if not file_path:
            return
        try:
            with open(file_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    sb_id = row.get('subbasin_id', row.get('Subbasin_ID', ''))
                    if sb_id:
                        self.subbasin_params[sb_id] = {
                            'cn': float(row.get('cn', row.get('CN', 75))),
                            'c_value': float(row.get('c_value', row.get('C', 0.3))),
                            'mannings_n': float(row.get('mannings_n', row.get('n', 0.4)))
                        }
            self.populate_from_flowpaths(list(self.subbasin_params.keys()))
            self.parameters_changed.emit()
            QMessageBox.information(self, "Loaded", f"Loaded parameters for {len(self.subbasin_params)} subbasins")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading CSV: {str(e)}")
    
    def save_to_csv(self):
        if not self.subbasin_params:
            QMessageBox.warning(self, "No Data", "No subbasin parameters to save")
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Subbasin Parameters", "subbasin_params.csv", "CSV files (*.csv)")
        if not file_path:
            return
        try:
            with open(file_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['subbasin_id', 'cn', 'c_value', 'mannings_n'])
                for sb_id, params in self.subbasin_params.items():
                    writer.writerow([sb_id, params.get('cn', 75), params.get('c_value', 0.3), params.get('mannings_n', 0.4)])
            QMessageBox.information(self, "Saved", f"Parameters saved to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving CSV: {str(e)}")
    
    def clear_table(self):
        self.subbasin_params = {}
        self.table.setRowCount(0)
        self.parameters_changed.emit()


# =============================================================================
# CHANNEL GEOMETRY TABLE WIDGET
# =============================================================================

class ChannelGeometryTable(QWidget):
    """Widget for managing per-subbasin channel and pipe geometry"""
    
    geometry_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.subbasin_geometry = {}
        self.global_defaults = {
            'channel_depth': 2.0, 'channel_width': 4.0,
            'side_slope': 2.0, 'pipe_diameter': 1.5
        }
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("<b>Channel & Pipe Geometry</b> (for hydraulic radius)")
        layout.addWidget(title)
        
        desc = QLabel("Define channel/pipe dimensions per subbasin for hydraulic radius calculation.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(desc)
        
        # Global defaults section
        defaults_group = QGroupBox("Global Defaults")
        defaults_layout = QVBoxLayout(defaults_group)
        
        ch_row = QHBoxLayout()
        ch_row.addWidget(QLabel("Channel:"))
        
        ch_row.addWidget(QLabel("Depth:"))
        self.default_depth = QDoubleSpinBox()
        self.default_depth.setRange(0.5, 20.0)
        self.default_depth.setValue(2.0)
        self.default_depth.setDecimals(1)
        self.default_depth.valueChanged.connect(self.update_global_defaults)
        ch_row.addWidget(self.default_depth)
        
        ch_row.addWidget(QLabel("Width:"))
        self.default_width = QDoubleSpinBox()
        self.default_width.setRange(0.5, 50.0)
        self.default_width.setValue(4.0)
        self.default_width.setDecimals(1)
        self.default_width.valueChanged.connect(self.update_global_defaults)
        ch_row.addWidget(self.default_width)
        
        ch_row.addWidget(QLabel("Slope (H:1V):"))
        self.default_slope = QDoubleSpinBox()
        self.default_slope.setRange(0.0, 6.0)
        self.default_slope.setValue(2.0)
        self.default_slope.setDecimals(1)
        self.default_slope.valueChanged.connect(self.update_global_defaults)
        ch_row.addWidget(self.default_slope)
        
        ch_row.addStretch()
        defaults_layout.addLayout(ch_row)
        
        pipe_row = QHBoxLayout()
        pipe_row.addWidget(QLabel("Pipe D (ft):"))
        self.default_pipe = QDoubleSpinBox()
        self.default_pipe.setRange(0.25, 10.0)
        self.default_pipe.setValue(1.5)
        self.default_pipe.setDecimals(2)
        self.default_pipe.valueChanged.connect(self.update_global_defaults)
        pipe_row.addWidget(self.default_pipe)
        
        pipe_row.addWidget(QLabel("    R:"))
        self.default_r_label = QLabel("Ch: 0.80 ft | Pipe: 0.38 ft")
        self.default_r_label.setStyleSheet("font-weight: bold; color: #007bff;")
        pipe_row.addWidget(self.default_r_label)
        pipe_row.addStretch()
        defaults_layout.addLayout(pipe_row)
        
        layout.addWidget(defaults_group)
        
        # Per-subbasin table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            'Subbasin ID', 'Ch Depth', 'Ch Width', 'Side Slope', 'Pipe D', 'Calc R'
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)
        
        btn_layout = QHBoxLayout()
        load_btn = QPushButton("Load CSV")
        load_btn.clicked.connect(self.load_from_csv)
        btn_layout.addWidget(load_btn)
        
        save_btn = QPushButton("Save CSV")
        save_btn.clicked.connect(self.save_to_csv)
        btn_layout.addWidget(save_btn)
        
        apply_btn = QPushButton("Apply Defaults to All")
        apply_btn.clicked.connect(self.apply_defaults_to_all)
        btn_layout.addWidget(apply_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.table.cellChanged.connect(self.on_cell_changed)
        self.update_global_defaults()
        
    def update_global_defaults(self):
        self.global_defaults = {
            'channel_depth': self.default_depth.value(),
            'channel_width': self.default_width.value(),
            'side_slope': self.default_slope.value(),
            'pipe_diameter': self.default_pipe.value()
        }
        channel_r = calc_hydraulic_radius(
            self.global_defaults['channel_depth'],
            self.global_defaults['channel_width'],
            self.global_defaults['side_slope']
        )
        pipe_r = calc_pipe_hydraulic_radius(self.global_defaults['pipe_diameter'])
        self.default_r_label.setText(f"Ch: {channel_r:.2f} ft | Pipe: {pipe_r:.2f} ft")
        self.geometry_changed.emit()
        
    def populate_from_flowpaths(self, subbasin_ids: List[str]):
        self.table.blockSignals(True)
        self.table.setRowCount(len(subbasin_ids))
        
        for row, sb_id in enumerate(sorted(subbasin_ids)):
            geom = self.subbasin_geometry.get(sb_id, {})
            
            id_item = QTableWidgetItem(str(sb_id))
            id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 0, id_item)
            
            depth_val = geom.get('channel_depth', '')
            self.table.setItem(row, 1, QTableWidgetItem(str(depth_val) if depth_val else ''))
            
            width_val = geom.get('channel_width', '')
            self.table.setItem(row, 2, QTableWidgetItem(str(width_val) if width_val else ''))
            
            slope_val = geom.get('side_slope', '')
            self.table.setItem(row, 3, QTableWidgetItem(str(slope_val) if slope_val else ''))
            
            pipe_val = geom.get('pipe_diameter', '')
            self.table.setItem(row, 4, QTableWidgetItem(str(pipe_val) if pipe_val else ''))
            
            r_item = QTableWidgetItem(self._calc_r_display(sb_id))
            r_item.setFlags(r_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 5, r_item)
        
        self.table.blockSignals(False)
        self.table.resizeColumnsToContents()
        
    def _calc_r_display(self, subbasin_id: str) -> str:
        geom = self.get_geometry(subbasin_id)
        channel_r = calc_hydraulic_radius(geom['channel_depth'], geom['channel_width'], geom['side_slope'])
        pipe_r = calc_pipe_hydraulic_radius(geom['pipe_diameter'])
        return f"Ch:{channel_r:.2f} | P:{pipe_r:.2f}"
        
    def on_cell_changed(self, row, col):
        if col == 0 or col == 5:
            return
        sb_id = self.table.item(row, 0).text()
        if sb_id not in self.subbasin_geometry:
            self.subbasin_geometry[sb_id] = {}
        try:
            text = self.table.item(row, col).text().strip()
            value = float(text) if text else None
            if col == 1:
                self.subbasin_geometry[sb_id]['channel_depth'] = value
            elif col == 2:
                self.subbasin_geometry[sb_id]['channel_width'] = value
            elif col == 3:
                self.subbasin_geometry[sb_id]['side_slope'] = value
            elif col == 4:
                self.subbasin_geometry[sb_id]['pipe_diameter'] = value
            
            self.table.blockSignals(True)
            r_item = QTableWidgetItem(self._calc_r_display(sb_id))
            r_item.setFlags(r_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 5, r_item)
            self.table.blockSignals(False)
            
            self.geometry_changed.emit()
        except ValueError:
            pass
    
    def get_geometry(self, subbasin_id: str) -> dict:
        geom = self.subbasin_geometry.get(subbasin_id, {})
        return {
            'channel_depth': geom.get('channel_depth') or self.global_defaults['channel_depth'],
            'channel_width': geom.get('channel_width') or self.global_defaults['channel_width'],
            'side_slope': geom.get('side_slope') or self.global_defaults['side_slope'],
            'pipe_diameter': geom.get('pipe_diameter') or self.global_defaults['pipe_diameter'],
        }
    
    def get_hydraulic_radius(self, subbasin_id: str, flow_type: str) -> float:
        geom = self.get_geometry(subbasin_id)
        if 'PIPE' in flow_type.upper():
            return calc_pipe_hydraulic_radius(geom['pipe_diameter'])
        else:
            return calc_hydraulic_radius(geom['channel_depth'], geom['channel_width'], geom['side_slope'])
    
    def apply_defaults_to_all(self):
        for row in range(self.table.rowCount()):
            sb_id = self.table.item(row, 0).text()
            self.subbasin_geometry[sb_id] = dict(self.global_defaults)
        self.populate_from_flowpaths([self.table.item(r, 0).text() for r in range(self.table.rowCount())])
        self.geometry_changed.emit()
        
    def load_from_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Channel Geometry", "", "CSV files (*.csv)")
        if not file_path:
            return
        try:
            with open(file_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    sb_id = row.get('subbasin_id', row.get('Subbasin_ID', ''))
                    if sb_id:
                        self.subbasin_geometry[sb_id] = {
                            'channel_depth': float(row.get('channel_depth', '')) if row.get('channel_depth', '') else None,
                            'channel_width': float(row.get('channel_width', '')) if row.get('channel_width', '') else None,
                            'side_slope': float(row.get('side_slope', '')) if row.get('side_slope', '') else None,
                            'pipe_diameter': float(row.get('pipe_diameter', '')) if row.get('pipe_diameter', '') else None,
                        }
            self.populate_from_flowpaths(list(self.subbasin_geometry.keys()))
            self.geometry_changed.emit()
            QMessageBox.information(self, "Loaded", f"Loaded geometry for {len(self.subbasin_geometry)} subbasins")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading CSV: {str(e)}")
    
    def save_to_csv(self):
        if not self.subbasin_geometry:
            QMessageBox.warning(self, "No Data", "No geometry data to save")
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Channel Geometry", "channel_geometry.csv", "CSV files (*.csv)")
        if not file_path:
            return
        try:
            with open(file_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['subbasin_id', 'channel_depth', 'channel_width', 'side_slope', 'pipe_diameter'])
                for sb_id, geom in self.subbasin_geometry.items():
                    writer.writerow([sb_id, geom.get('channel_depth', ''), geom.get('channel_width', ''),
                                    geom.get('side_slope', ''), geom.get('pipe_diameter', '')])
            QMessageBox.information(self, "Saved", f"Geometry saved to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving CSV: {str(e)}")


# =============================================================================
# ENHANCED TC CALCULATOR TOOL
# =============================================================================

class TCCalculatorToolEnhanced(HydroToolInterface, LayerSelectionMixin):
    """
    Enhanced Time of Concentration Calculator

    Version 2.4 - Three calculation modes:
    - Mode A: Flowpath layer-based (TR-55 segment method + comparisons)
    - Mode B: Manual entry (comparison methods only)
    - Mode C: DEM Extraction (auto-extract flowpath from DEM + comparisons)
    """

    # Calculation mode constants
    MODE_FLOWPATH = 'flowpath'
    MODE_MANUAL = 'manual'
    MODE_DEM = 'dem'

    def __init__(self):
        super().__init__()
        self.name = "Time of Concentration Calculator"
        self.description = "Calculate TC with Flowpath, Manual Entry, or DEM Extraction"
        self.category = "Watershed Analysis"
        self.version = "2.5"
        self.author = "Hydro Suite"

        self.methods = {
            'kirpich': KirpichMethod(),
            'faa': FAAMethod(),
            'scs_lag': SCSLagMethod(),
            'kerby': KerbyMethod()
        }

        self.target_crs = QgsCoordinateReferenceSystem("EPSG:2273")
        self.selected_methods = ['kirpich', 'scs_lag', 'faa', 'kerby']

        # Mode selection - now supports three modes
        self.current_mode = self.MODE_FLOWPATH
        self.use_flowpath_mode = True  # Legacy compatibility

        # GUI components
        self.flowpath_selector = None
        self.output_selector = None
        self.validation_panel = None
        self.progress_logger = None
        self.method_checkboxes = {}
        self.results_table = None

        # Tables
        self.manual_entry_table = None
        self.subbasin_params_table = None
        self.channel_geometry_table = None

        # Field selectors (flowpath mode)
        self.field_subbasin_id = None
        self.field_length = None
        self.field_slope = None
        self.field_mannings_n = None
        self.field_flow_type = None

        # DEM Extraction mode components
        self.dem_combo = None
        self.dem_subbasin_combo = None
        self.dem_subbasin_id_field = None
        self.dem_cn_field = None
        self.dem_land_type_field = None
        self.apply_slope_adj_checkbox = None
        self.apply_tc_min_checkbox = None
        
    def create_gui(self, parent_widget: QWidget) -> QWidget:
        """Create the TC Calculator GUI"""
        tab_widget = QTabWidget(parent_widget)
        
        # Main configuration tab (with mode selection)
        main_tab = self.create_main_tab()
        tab_widget.addTab(main_tab, "Configuration")
        
        # Subbasin parameters tab (flowpath mode only)
        params_tab = self.create_subbasin_params_tab()
        tab_widget.addTab(params_tab, "Subbasin Parameters")
        
        # Channel geometry tab (flowpath mode only)
        channel_tab = self.create_channel_geometry_tab()
        tab_widget.addTab(channel_tab, "Channel Geometry")
        
        # Methods tab
        methods_tab = self.create_methods_tab()
        tab_widget.addTab(methods_tab, "Methods")
        
        # Results tab
        results_tab = self.create_results_tab()
        tab_widget.addTab(results_tab, "Results")
        
        self.gui_widget = tab_widget
        return tab_widget
        
    def create_main_tab(self) -> QWidget:
        """Create main configuration tab with mode selection"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        main_widget = QWidget()
        scroll.setWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Title
        title_label = QLabel(f"<h2>{self.name} v{self.version}</h2>")
        layout.addWidget(title_label)
        
        # Mode selection
        mode_frame = QFrame()
        mode_frame.setFrameStyle(QFrame.StyledPanel)
        mode_frame.setStyleSheet("background-color: #f8f9fa; border: 2px solid #007bff; border-radius: 5px;")
        mode_layout = QVBoxLayout(mode_frame)

        mode_title = QLabel("<b>Select Calculation Mode</b>")
        mode_layout.addWidget(mode_title)

        self.mode_group = QButtonGroup()

        self.flowpath_mode_radio = QRadioButton("Flowpath Layer Mode (TR-55 segment + comparison methods)")
        self.flowpath_mode_radio.setChecked(True)
        self.flowpath_mode_radio.toggled.connect(self.on_mode_changed)
        self.mode_group.addButton(self.flowpath_mode_radio)
        mode_layout.addWidget(self.flowpath_mode_radio)

        flowpath_desc = QLabel("    Uses flowpath layer segments for TR-55 travel time calculation.")
        flowpath_desc.setStyleSheet("color: #666; font-size: 11px; margin-left: 20px;")
        mode_layout.addWidget(flowpath_desc)

        self.manual_mode_radio = QRadioButton("Manual Entry Mode (comparison methods only)")
        self.manual_mode_radio.toggled.connect(self.on_mode_changed)
        self.mode_group.addButton(self.manual_mode_radio)
        mode_layout.addWidget(self.manual_mode_radio)

        manual_desc = QLabel("    Enter subbasin length/slope/parameters directly - no flowpath layer needed.")
        manual_desc.setStyleSheet("color: #666; font-size: 11px; margin-left: 20px;")
        mode_layout.addWidget(manual_desc)

        # NEW: DEM Extraction Mode
        self.dem_mode_radio = QRadioButton("DEM Extraction Mode (auto-extract flowpath from DEM)")
        self.dem_mode_radio.toggled.connect(self.on_mode_changed)
        self.mode_group.addButton(self.dem_mode_radio)
        mode_layout.addWidget(self.dem_mode_radio)

        dem_desc = QLabel("    Extract flowpath length and slope from DEM for each subbasin automatically.")
        dem_desc.setStyleSheet("color: #666; font-size: 11px; margin-left: 20px;")
        mode_layout.addWidget(dem_desc)

        # Show warning if DEM extraction not available
        if not HAS_DEM_EXTRACTION:
            dem_warning = QLabel("    ⚠ DEM extraction module not found. Install dem_extraction.py to enable.")
            dem_warning.setStyleSheet("color: #dc3545; font-size: 11px; margin-left: 20px; font-weight: bold;")
            mode_layout.addWidget(dem_warning)
            self.dem_mode_radio.setEnabled(False)

        layout.addWidget(mode_frame)
        
        # Stacked widget for mode-specific content
        self.mode_stack = QStackedWidget()

        # Flowpath mode widget (index 0)
        flowpath_widget = self.create_flowpath_mode_widget()
        self.mode_stack.addWidget(flowpath_widget)

        # Manual entry mode widget (index 1)
        manual_widget = self.create_manual_mode_widget()
        self.mode_stack.addWidget(manual_widget)

        # DEM extraction mode widget (index 2)
        dem_widget = self.create_dem_mode_widget()
        self.mode_stack.addWidget(dem_widget)

        layout.addWidget(self.mode_stack)
        
        # Output section (common to both modes)
        output_frame = QFrame()
        output_frame.setFrameStyle(QFrame.StyledPanel)
        output_layout = QVBoxLayout(output_frame)
        
        output_title = QLabel("<h3>Output</h3>")
        output_layout.addWidget(output_title)
        
        self.output_selector = DirectorySelector("Output Directory", default_path="")
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
                font-size: 14px; font-weight: bold; padding: 10px 20px;
                background-color: #17a2b8; color: white; border-radius: 5px;
            }
            QPushButton:hover { background-color: #138496; }
            QPushButton:disabled { background-color: #6c757d; }
        """)
        self.run_btn.clicked.connect(self.run_calculation)
        button_layout.addWidget(self.run_btn)
        
        layout.addLayout(button_layout)
        
        # Setup validation
        self.setup_validation_monitoring()
        self.validate_and_update()
        
        return scroll
    
    def create_flowpath_mode_widget(self) -> QWidget:
        """Create widget for flowpath layer mode"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Validation panel
        self.validation_panel = ValidationPanel()
        layout.addWidget(self.validation_panel)
        
        # Input layer section
        inputs_frame = QFrame()
        inputs_frame.setFrameStyle(QFrame.StyledPanel)
        inputs_layout = QVBoxLayout(inputs_frame)
        
        inputs_title = QLabel("<h3>Input Data - Flowpaths Layer</h3>")
        inputs_layout.addWidget(inputs_title)
        
        self.flowpath_selector = LayerFieldSelector(
            "Flowpaths Layer", default_field="FP_ID", geometry_type=QgsWkbTypes.LineGeometry
        )
        self.flowpath_selector.layer_changed.connect(self.on_layer_changed)
        inputs_layout.addWidget(self.flowpath_selector)
        
        # Field mapping
        fields_group = QGroupBox("Field Mapping")
        fields_layout = QVBoxLayout(fields_group)
        
        field_configs = [
            ("Subbasin ID:", "field_subbasin_id"),
            ("Length (ft):", "field_length"),
            ("Slope (%):", "field_slope"),
            ("Manning's n:", "field_mannings_n"),
            ("Flow Type:", "field_flow_type"),
        ]
        
        for label_text, attr_name in field_configs:
            row_layout = QHBoxLayout()
            row_layout.addWidget(QLabel(label_text))
            combo = QComboBox()
            combo.setMinimumWidth(150)
            setattr(self, attr_name, combo)
            row_layout.addWidget(combo)
            row_layout.addStretch()
            fields_layout.addLayout(row_layout)
        
        inputs_layout.addWidget(fields_group)
        layout.addWidget(inputs_frame)
        
        # TR-55 parameters
        tr55_frame = QFrame()
        tr55_frame.setFrameStyle(QFrame.StyledPanel)
        tr55_layout = QVBoxLayout(tr55_frame)
        
        tr55_title = QLabel("<h3>TR-55 Parameters</h3>")
        tr55_layout.addWidget(tr55_title)
        
        p2_layout = QHBoxLayout()
        p2_layout.addWidget(QLabel("2-yr 24-hr Rainfall (in):"))
        self.p2_spin = QDoubleSpinBox()
        self.p2_spin.setRange(1.0, 10.0)
        self.p2_spin.setValue(3.5)
        self.p2_spin.setSingleStep(0.1)
        self.p2_spin.setDecimals(1)
        p2_layout.addWidget(self.p2_spin)
        p2_layout.addStretch()
        tr55_layout.addLayout(p2_layout)
        
        layout.addWidget(tr55_frame)
        
        # Load subbasins button
        load_btn = QPushButton("Load Subbasins from Layer")
        load_btn.setStyleSheet("background-color: #6c757d; color: white;")
        load_btn.clicked.connect(self.load_subbasins_from_layer)
        layout.addWidget(load_btn)
        
        return widget
    
    def create_manual_mode_widget(self) -> QWidget:
        """Create widget for manual entry mode"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Manual entry table
        self.manual_entry_table = ManualEntryTable()
        layout.addWidget(self.manual_entry_table)

        return widget

    def create_dem_mode_widget(self) -> QWidget:
        """Create widget for DEM extraction mode - extracts flowpath from DEM"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Description
        desc_frame = QFrame()
        desc_frame.setFrameStyle(QFrame.StyledPanel)
        desc_frame.setStyleSheet("background-color: #d4edda; border: 1px solid #28a745; border-radius: 5px;")
        desc_layout = QVBoxLayout(desc_frame)
        desc_label = QLabel(
            "<b>DEM Extraction Mode</b><br>"
            "Automatically extract flowpath length and slope from DEM for each subbasin.<br>"
            "The tool will find the highest and lowest elevation points within each subbasin "
            "and calculate the flow path parameters.<br><br>"
            "<b>Flat Terrain Handling:</b> Per TxDOT/Cleveland 2012, slopes < 0.2% are adjusted."
        )
        desc_label.setWordWrap(True)
        desc_layout.addWidget(desc_label)
        layout.addWidget(desc_frame)

        # DEM Layer Selection
        dem_group = QGroupBox("DEM Input Layer")
        dem_layout = QVBoxLayout(dem_group)

        dem_row = QHBoxLayout()
        dem_row.addWidget(QLabel("DEM Raster:"))
        self.dem_combo = QComboBox()
        self.dem_combo.setMinimumWidth(250)
        self.dem_combo.setToolTip("Select a DEM raster layer from the project")
        dem_row.addWidget(self.dem_combo)

        refresh_btn = QPushButton("Refresh Layers")
        refresh_btn.setToolTip("Reload available layers from the project")
        refresh_btn.clicked.connect(self.refresh_dem_layers)
        dem_row.addWidget(refresh_btn)
        dem_row.addStretch()
        dem_layout.addLayout(dem_row)

        # DEM info label
        self.dem_info_label = QLabel("No DEM selected")
        self.dem_info_label.setStyleSheet("color: #666; font-size: 11px;")
        dem_layout.addWidget(self.dem_info_label)
        self.dem_combo.currentIndexChanged.connect(self.on_dem_changed)

        layout.addWidget(dem_group)

        # Subbasin Layer Selection
        sb_group = QGroupBox("Subbasin Layer")
        sb_layout = QVBoxLayout(sb_group)

        sb_row = QHBoxLayout()
        sb_row.addWidget(QLabel("Subbasin Polygons:"))
        self.dem_subbasin_combo = QComboBox()
        self.dem_subbasin_combo.setMinimumWidth(250)
        self.dem_subbasin_combo.setToolTip("Select a polygon layer containing subbasins")
        sb_row.addWidget(self.dem_subbasin_combo)
        sb_row.addStretch()
        sb_layout.addLayout(sb_row)

        # Field mapping for subbasins
        field_grid = QHBoxLayout()

        id_col = QVBoxLayout()
        id_col.addWidget(QLabel("Subbasin ID Field:"))
        self.dem_subbasin_id_field = QComboBox()
        self.dem_subbasin_id_field.setMinimumWidth(120)
        id_col.addWidget(self.dem_subbasin_id_field)
        field_grid.addLayout(id_col)

        cn_col = QVBoxLayout()
        cn_col.addWidget(QLabel("CN Field (optional):"))
        self.dem_cn_field = QComboBox()
        self.dem_cn_field.setMinimumWidth(120)
        self.dem_cn_field.addItem("-- Use Default --", None)
        cn_col.addWidget(self.dem_cn_field)
        field_grid.addLayout(cn_col)

        land_col = QVBoxLayout()
        land_col.addWidget(QLabel("Land Type Field (optional):"))
        self.dem_land_type_field = QComboBox()
        self.dem_land_type_field.setMinimumWidth(120)
        self.dem_land_type_field.addItem("-- Use Default --", None)
        land_col.addWidget(self.dem_land_type_field)
        field_grid.addLayout(land_col)

        field_grid.addStretch()
        sb_layout.addLayout(field_grid)

        self.dem_subbasin_combo.currentIndexChanged.connect(self.on_dem_subbasin_changed)
        layout.addWidget(sb_group)

        # Parameters and Adjustments
        params_group = QGroupBox("Calculation Parameters")
        params_layout = QVBoxLayout(params_group)

        # Default values row
        defaults_row = QHBoxLayout()

        defaults_row.addWidget(QLabel("Default CN:"))
        self.dem_default_cn = QDoubleSpinBox()
        self.dem_default_cn.setRange(30, 98)
        self.dem_default_cn.setValue(75)
        self.dem_default_cn.setDecimals(0)
        self.dem_default_cn.setToolTip("Used when CN field is not specified or value is missing")
        defaults_row.addWidget(self.dem_default_cn)

        defaults_row.addWidget(QLabel("Default C:"))
        self.dem_default_c = QDoubleSpinBox()
        self.dem_default_c.setRange(0.05, 0.95)
        self.dem_default_c.setValue(0.30)
        self.dem_default_c.setDecimals(2)
        defaults_row.addWidget(self.dem_default_c)

        defaults_row.addWidget(QLabel("Default n:"))
        self.dem_default_n = QDoubleSpinBox()
        self.dem_default_n.setRange(0.01, 0.80)
        self.dem_default_n.setValue(0.40)
        self.dem_default_n.setDecimals(2)
        defaults_row.addWidget(self.dem_default_n)

        defaults_row.addWidget(QLabel("P2 Rainfall (in):"))
        self.dem_p2_rainfall = QDoubleSpinBox()
        self.dem_p2_rainfall.setRange(1.0, 10.0)
        self.dem_p2_rainfall.setValue(3.5)
        self.dem_p2_rainfall.setDecimals(1)
        self.dem_p2_rainfall.setToolTip("2-year 24-hour rainfall depth for TR-55")
        defaults_row.addWidget(self.dem_p2_rainfall)

        defaults_row.addStretch()
        params_layout.addLayout(defaults_row)

        # Adjustment checkboxes
        self.apply_slope_adj_checkbox = QCheckBox(
            "Apply TxDOT low-slope adjustment (add 0.0005 when S < 0.2%)"
        )
        self.apply_slope_adj_checkbox.setChecked(True)
        self.apply_slope_adj_checkbox.setToolTip(
            "Per TxDOT/Cleveland et al. 2012: adds 0.0005 to slopes below 0.2%"
        )
        params_layout.addWidget(self.apply_slope_adj_checkbox)

        self.apply_tc_min_checkbox = QCheckBox(
            "Apply minimum TC (6 min default, 5 min paved, 10 min rural)"
        )
        self.apply_tc_min_checkbox.setChecked(True)
        self.apply_tc_min_checkbox.setToolTip(
            "Per NRCS/California HDM: enforces minimum TC based on land type"
        )
        params_layout.addWidget(self.apply_tc_min_checkbox)

        layout.addWidget(params_group)

        # Fallback Info
        fallback_frame = QFrame()
        fallback_frame.setFrameStyle(QFrame.StyledPanel)
        fallback_layout = QVBoxLayout(fallback_frame)
        fallback_label = QLabel(
            "<b>Fallback Methods (per TxDOT/Cleveland et al. 2012):</b><br>"
            "• S < 0.2%: Add 0.0005 to slope<br>"
            "• 0.2% ≤ S < 0.3%: Transitional - flag for review<br>"
            "• S < 0 (adverse): Use minimum 0.05%<br>"
            "• TC < 6 min: Use 6 min minimum (NRCS)<br>"
            "• If DEM extraction fails: Uses geometric centroid-to-boundary method"
        )
        fallback_label.setWordWrap(True)
        fallback_label.setStyleSheet("color: #555; font-size: 11px;")
        fallback_layout.addWidget(fallback_label)
        layout.addWidget(fallback_frame)

        # Initialize layer combos
        self.refresh_dem_layers()

        return widget

    def refresh_dem_layers(self):
        """Refresh the DEM and subbasin layer combo boxes"""
        # Save current selections
        current_dem = self.dem_combo.currentData() if self.dem_combo else None
        current_sb = self.dem_subbasin_combo.currentData() if self.dem_subbasin_combo else None

        # Clear combos
        self.dem_combo.clear()
        self.dem_subbasin_combo.clear()

        self.dem_combo.addItem("-- Select DEM Layer --", None)
        self.dem_subbasin_combo.addItem("-- Select Subbasin Layer --", None)

        # Add raster layers to DEM combo
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsRasterLayer) and layer.isValid():
                self.dem_combo.addItem(f"{layer.name()} ({layer.crs().authid()})", layer.id())

        # Add polygon layers to subbasin combo
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer) and layer.isValid():
                if layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                    self.dem_subbasin_combo.addItem(
                        f"{layer.name()} ({layer.featureCount()} features)", layer.id()
                    )

        # Restore selections if possible
        if current_dem:
            idx = self.dem_combo.findData(current_dem)
            if idx >= 0:
                self.dem_combo.setCurrentIndex(idx)
        if current_sb:
            idx = self.dem_subbasin_combo.findData(current_sb)
            if idx >= 0:
                self.dem_subbasin_combo.setCurrentIndex(idx)

    def on_dem_changed(self):
        """Update DEM info when selection changes"""
        layer_id = self.dem_combo.currentData()
        if layer_id:
            layer = QgsProject.instance().mapLayer(layer_id)
            if layer and isinstance(layer, QgsRasterLayer):
                extent = layer.extent()
                self.dem_info_label.setText(
                    f"CRS: {layer.crs().authid()} | "
                    f"Size: {layer.width()}x{layer.height()} | "
                    f"Extent: {extent.width():.1f} x {extent.height():.1f}"
                )
            else:
                self.dem_info_label.setText("Invalid DEM layer")
        else:
            self.dem_info_label.setText("No DEM selected")
        self.validate_and_update()

    def on_dem_subbasin_changed(self):
        """Update field combos when subbasin layer changes"""
        # Clear field combos
        self.dem_subbasin_id_field.clear()
        self.dem_cn_field.clear()
        self.dem_land_type_field.clear()

        self.dem_cn_field.addItem("-- Use Default --", None)
        self.dem_land_type_field.addItem("-- Use Default --", None)

        layer_id = self.dem_subbasin_combo.currentData()
        if layer_id:
            layer = QgsProject.instance().mapLayer(layer_id)
            if layer and isinstance(layer, QgsVectorLayer):
                for field in layer.fields():
                    field_name = field.name()
                    self.dem_subbasin_id_field.addItem(field_name, field_name)
                    self.dem_cn_field.addItem(field_name, field_name)
                    self.dem_land_type_field.addItem(field_name, field_name)

                # Auto-select likely field names
                for i in range(self.dem_subbasin_id_field.count()):
                    name = self.dem_subbasin_id_field.itemText(i).upper()
                    if 'ID' in name or 'NAME' in name or 'SUB' in name:
                        self.dem_subbasin_id_field.setCurrentIndex(i)
                        break

                for i in range(self.dem_cn_field.count()):
                    name = self.dem_cn_field.itemText(i).upper()
                    if name == 'CN' or 'CURVE' in name:
                        self.dem_cn_field.setCurrentIndex(i)
                        break

        self.validate_and_update()

    def create_subbasin_params_tab(self) -> QWidget:
        """Create subbasin parameters tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        title = QLabel("<h3>Per-Subbasin Parameters</h3>")
        layout.addWidget(title)
        
        note = QLabel("<i>Note: This tab is only used in <b>Flowpath Layer Mode</b>. "
                     "In Manual Entry Mode, parameters are entered directly in the main table.</i>")
        note.setWordWrap(True)
        note.setStyleSheet("color: #856404; background-color: #fff3cd; padding: 10px; border-radius: 5px;")
        layout.addWidget(note)
        
        self.subbasin_params_table = SubbasinParametersTable()
        layout.addWidget(self.subbasin_params_table)
        
        return widget
    
    def create_channel_geometry_tab(self) -> QWidget:
        """Create channel geometry tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        title = QLabel("<h3>Channel & Pipe Geometry</h3>")
        layout.addWidget(title)
        
        note = QLabel("<i>Note: This tab is only used in <b>Flowpath Layer Mode</b> for calculating "
                     "hydraulic radius for CHANNEL and PIPE flow types.</i>")
        note.setWordWrap(True)
        note.setStyleSheet("color: #856404; background-color: #fff3cd; padding: 10px; border-radius: 5px;")
        layout.addWidget(note)
        
        self.channel_geometry_table = ChannelGeometryTable()
        layout.addWidget(self.channel_geometry_table)
        
        return widget
    
    def create_methods_tab(self) -> QWidget:
        """Create methods selection tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        title = QLabel("<h3>Comparison Methods</h3>")
        layout.addWidget(title)
        
        methods_frame = QFrame()
        methods_frame.setFrameStyle(QFrame.StyledPanel)
        methods_layout = QVBoxLayout(methods_frame)
        
        method_info = {
            'kirpich': ("Kirpich (1940)", "Uses L and S only"),
            'faa': ("FAA (1965)", "Uses C value"),
            'scs_lag': ("SCS Lag", "Uses CN"),
            'kerby': ("Kerby", "Uses Manning's n"),
        }
        
        for method_id, (name, desc) in method_info.items():
            checkbox = QCheckBox(f"{name} - {desc}")
            checkbox.setChecked(method_id in self.selected_methods)
            checkbox.toggled.connect(lambda checked, mid=method_id: self.on_method_toggled(mid, checked))
            methods_layout.addWidget(checkbox)
            self.method_checkboxes[method_id] = checkbox
            
        layout.addWidget(methods_frame)
        
        # Formulas
        formulas_frame = QFrame()
        formulas_frame.setFrameStyle(QFrame.StyledPanel)
        formulas_layout = QVBoxLayout(formulas_frame)
        formulas_layout.addWidget(QLabel("<b>Formulas:</b>"))
        formulas_layout.addWidget(QLabel(
            "• Kirpich: tc = 0.0078 × L^0.77 / S^0.385\n"
            "• FAA: tc = 1.8 × (1.1-C) × L^0.5 / S^0.33\n"
            "• SCS Lag: Lag = (L^0.8 × ((1000/CN)-9)^0.7) / (1900 × S^0.5), Tc=Lag/0.6\n"
            "• Kerby: tc = 1.44 × (n×L)^0.467 / S^0.235"
        ))
        layout.addWidget(formulas_frame)
        layout.addStretch()
        
        return widget
        
    def create_results_tab(self) -> QWidget:
        """Create results display tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        title = QLabel("<h3>Calculation Results</h3>")
        layout.addWidget(title)
        
        self.results_table = QTableWidget()
        self.results_table.setAlternatingRowColors(True)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.results_table)
        
        self.summary_label = QLabel("Run calculation to see results...")
        self.summary_label.setStyleSheet("color: #666; font-style: italic; padding: 10px;")
        layout.addWidget(self.summary_label)
        
        return widget
    
    def on_mode_changed(self, checked):
        """Handle mode selection change - supports three modes"""
        if self.flowpath_mode_radio.isChecked():
            self.current_mode = self.MODE_FLOWPATH
            self.use_flowpath_mode = True  # Legacy compatibility
            self.mode_stack.setCurrentIndex(0)
        elif self.manual_mode_radio.isChecked():
            self.current_mode = self.MODE_MANUAL
            self.use_flowpath_mode = False
            self.mode_stack.setCurrentIndex(1)
        elif self.dem_mode_radio.isChecked():
            self.current_mode = self.MODE_DEM
            self.use_flowpath_mode = False
            self.mode_stack.setCurrentIndex(2)
            # Refresh DEM layers when switching to DEM mode
            self.refresh_dem_layers()
        self.validate_and_update()
    
    def on_layer_changed(self, layer):
        """Update field combos when layer changes"""
        for combo in [self.field_subbasin_id, self.field_length, self.field_slope,
                      self.field_mannings_n, self.field_flow_type]:
            combo.clear()
            combo.addItem("-- Select Field --", None)
        
        if not layer or not layer.isValid():
            return
        
        field_names = [field.name() for field in layer.fields()]
        for field_name in field_names:
            for combo in [self.field_subbasin_id, self.field_length, self.field_slope,
                          self.field_mannings_n, self.field_flow_type]:
                combo.addItem(field_name, field_name)
        
        # Auto-select common field names
        field_map = {
            self.field_subbasin_id: ['Subbasin_ID', 'SubbasinID', 'SB_ID'],
            self.field_length: ['Length_ft', 'Length', 'LEN'],
            self.field_slope: ['Slope_Pct', 'Slope', 'SLOPE'],
            self.field_mannings_n: ['Mannings_n', 'Manning_n', 'N'],
            self.field_flow_type: ['Flow_Type', 'FlowType', 'TYPE'],
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
        
        self.progress_logger.log(f"Layer loaded: {layer.name()}")
        self.validate_and_update()
    
    def load_subbasins_from_layer(self):
        """Load unique subbasin IDs from flowpaths layer"""
        layer = self.flowpath_selector.get_selected_layer()
        if not layer or not layer.isValid():
            QMessageBox.warning(self.gui_widget, "No Layer", "Please select a flowpaths layer first.")
            return
        
        sb_field = self.field_subbasin_id.currentData()
        if not sb_field:
            QMessageBox.warning(self.gui_widget, "No Field", "Please select the Subbasin ID field first.")
            return
        
        subbasin_ids = set()
        for feature in layer.getFeatures():
            sb_id = str(feature[sb_field])
            if sb_id:
                subbasin_ids.add(sb_id)
        
        if not subbasin_ids:
            QMessageBox.warning(self.gui_widget, "No Subbasins", "No subbasin IDs found in the layer.")
            return
        
        self.subbasin_params_table.populate_from_flowpaths(list(subbasin_ids))
        self.channel_geometry_table.populate_from_flowpaths(list(subbasin_ids))
        
        self.progress_logger.log(f"Loaded {len(subbasin_ids)} subbasins", "success")
        QMessageBox.information(self.gui_widget, "Loaded", 
                               f"Loaded {len(subbasin_ids)} subbasins.\n\n"
                               "Edit values in Subbasin Parameters and Channel Geometry tabs.")
        
    def on_method_toggled(self, method_id: str, checked: bool):
        if checked and method_id not in self.selected_methods:
            self.selected_methods.append(method_id)
        elif not checked and method_id in self.selected_methods:
            self.selected_methods.remove(method_id)
            
    def setup_validation_monitoring(self):
        """Setup validation monitoring"""
        self.validation_panel.add_validation("flowpath", "Flowpaths layer")
        self.validation_panel.add_validation("fields", "Required field mapping")
        self.validation_panel.add_validation("output", "Output directory")
        
    def validate_and_update(self):
        """Validate all inputs based on current mode"""
        output_valid = self.output_selector.is_valid()

        if self.current_mode == self.MODE_FLOWPATH:
            # Flowpath mode validation
            self.flowpath_selector.validate_selection()
            flowpath_valid = self.flowpath_selector.is_valid()

            fields_valid = all([
                self.field_subbasin_id.currentData() is not None,
                self.field_length.currentData() is not None,
                self.field_slope.currentData() is not None,
                self.field_mannings_n.currentData() is not None,
                self.field_flow_type.currentData() is not None,
            ])

            self.validation_panel.set_validation_status("flowpath", flowpath_valid)
            self.validation_panel.set_validation_status("fields", fields_valid)
            self.validation_panel.set_validation_status("output", output_valid)

            all_valid = flowpath_valid and fields_valid and output_valid

        elif self.current_mode == self.MODE_MANUAL:
            # Manual mode validation
            manual_valid = self.manual_entry_table.has_valid_data() if self.manual_entry_table else False

            self.validation_panel.set_validation_status("flowpath", True)  # Not needed
            self.validation_panel.set_validation_status("fields", manual_valid)
            self.validation_panel.set_validation_status("output", output_valid)

            all_valid = manual_valid and output_valid

        elif self.current_mode == self.MODE_DEM:
            # DEM Extraction mode validation
            dem_valid = (
                self.dem_combo is not None and
                self.dem_combo.currentData() is not None
            )
            subbasin_valid = (
                self.dem_subbasin_combo is not None and
                self.dem_subbasin_combo.currentData() is not None and
                self.dem_subbasin_id_field is not None and
                self.dem_subbasin_id_field.currentText() != ""
            )

            self.validation_panel.set_validation_status("flowpath", dem_valid)
            self.validation_panel.set_validation_status("fields", subbasin_valid)
            self.validation_panel.set_validation_status("output", output_valid)

            all_valid = dem_valid and subbasin_valid and output_valid and HAS_DEM_EXTRACTION

        else:
            all_valid = False

        self.run_btn.setEnabled(all_valid)
        
    def validate_inputs(self) -> Tuple[bool, str]:
        """Validate all inputs before processing"""
        errors = []

        if self.current_mode == self.MODE_FLOWPATH:
            if not self.flowpath_selector.is_valid():
                errors.append("Invalid flowpaths layer selection")
            if not all([self.field_subbasin_id.currentData(), self.field_length.currentData(),
                        self.field_slope.currentData(), self.field_mannings_n.currentData(),
                        self.field_flow_type.currentData()]):
                errors.append("Not all required fields are mapped")

        elif self.current_mode == self.MODE_MANUAL:
            if not self.manual_entry_table.has_valid_data():
                errors.append("No valid subbasin data in manual entry table")

        elif self.current_mode == self.MODE_DEM:
            if not HAS_DEM_EXTRACTION:
                errors.append("DEM extraction module not available. Install dem_extraction.py")
            if not self.dem_combo.currentData():
                errors.append("No DEM layer selected")
            if not self.dem_subbasin_combo.currentData():
                errors.append("No subbasin layer selected")
            if not self.dem_subbasin_id_field.currentText():
                errors.append("No subbasin ID field selected")

        if not self.output_selector.is_valid():
            errors.append("No output directory selected")

        if errors:
            return False, "Please fix:\n- " + "\n- ".join(errors)
        return True, "All inputs valid"
        
    def run_calculation(self):
        """Run the TC calculation"""
        try:
            self.run(lambda p, m: self.progress_logger.update_progress(p, m))
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
            
            valid, message = self.validate_inputs()
            if not valid:
                raise ValueError(message)

            output_dir = self.output_selector.get_selected_directory()

            if self.current_mode == self.MODE_FLOWPATH:
                # Flowpath layer mode
                progress_callback(10, "Processing flowpath segments...")
                results = self.calculate_flowpath_mode(progress_callback)
            elif self.current_mode == self.MODE_MANUAL:
                # Manual entry mode
                progress_callback(10, "Processing manual entry data...")
                results = self.calculate_manual_mode(progress_callback)
            elif self.current_mode == self.MODE_DEM:
                # DEM extraction mode
                progress_callback(10, "Extracting flowpaths from DEM...")
                results = self.calculate_dem_mode(progress_callback)
            else:
                raise ValueError(f"Unknown calculation mode: {self.current_mode}")
            
            progress_callback(85, "Creating output files...")
            self.create_outputs(results, output_dir)
            
            progress_callback(95, "Updating results...")
            self.update_results_display(results)
            
            progress_callback(100, "TC calculation completed!")
            self.show_completion_dialog(results, output_dir)
            
            return True
            
        except Exception as e:
            progress_callback(0, f"Error: {str(e)}")
            self.progress_logger.log(traceback.format_exc(), "error")
            raise
        finally:
            self.progress_logger.show_progress(False)
    
    def calculate_flowpath_mode(self, progress_callback) -> Dict:
        """Calculate TC using flowpath layer (TR-55 + comparison methods)"""
        flowpath_layer = self.flowpath_selector.get_selected_layer()
        p2_rainfall = self.p2_spin.value()
        
        field_names = {
            'subbasin_id': self.field_subbasin_id.currentData(),
            'length': self.field_length.currentData(),
            'slope': self.field_slope.currentData(),
            'mannings_n': self.field_mannings_n.currentData(),
            'flow_type': self.field_flow_type.currentData(),
        }
        
        results = {}
        subbasin_segments = {}
        
        # Group features by subbasin
        for feature in flowpath_layer.getFeatures():
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
        
        total = len(subbasin_segments)
        
        for i, (subbasin_id, segments) in enumerate(subbasin_segments.items()):
            total_tt = 0.0
            total_length = 0.0
            segment_details = []
            
            for seg in segments:
                flow_type = seg['flow_type']
                length = seg['length_ft']
                slope = seg['slope_pct']
                n = seg['mannings_n']
                
                if 'SHEET' in flow_type:
                    tt = SegmentTravelTimeCalculator.sheet_flow_time(length, slope, n, p2_rainfall)
                    r_used = None
                elif 'SHALLOW' in flow_type or 'CONC' in flow_type:
                    surface = 'PAVED' if n < 0.02 else 'UNPAVED'
                    tt = SegmentTravelTimeCalculator.shallow_concentrated_time(length, slope, surface)
                    r_used = None
                elif 'PIPE' in flow_type:
                    geom = self.channel_geometry_table.get_geometry(subbasin_id)
                    pipe_d = geom['pipe_diameter']
                    tt = SegmentTravelTimeCalculator.pipe_flow_time(length, slope, n, pipe_d)
                    r_used = calc_pipe_hydraulic_radius(pipe_d)
                else:  # CHANNEL
                    r_used = self.channel_geometry_table.get_hydraulic_radius(subbasin_id, 'CHANNEL')
                    tt = SegmentTravelTimeCalculator.channel_flow_time(length, slope, n, r_used)
                
                total_tt += tt
                total_length += length
                segment_details.append({
                    'flow_type': flow_type, 'length_ft': length, 'slope_pct': slope,
                    'mannings_n': n, 'travel_time_min': tt, 'hydraulic_radius': r_used
                })
            
            avg_slope = sum(s['slope_pct'] * s['length_ft'] for s in segments) / total_length if total_length > 0 else 0
            sb_params = self.subbasin_params_table.get_params(subbasin_id)
            
            results[subbasin_id] = {
                'tc_segment_min': total_tt,
                'total_length_ft': total_length,
                'avg_slope_pct': avg_slope,
                'segment_count': len(segments),
                'segments': segment_details,
                'cn': sb_params['cn'],
                'c_value': sb_params['c_value'],
                'mannings_n_avg': sb_params['mannings_n'],
                'comparison_methods': {},
                'mode': 'flowpath'
            }
            
            progress_callback(10 + int((i + 1) / total * 55), f"Processed {i + 1}/{total}")
        
        # Add comparison methods
        progress_callback(70, "Calculating comparison methods...")
        for subbasin_id, data in results.items():
            for method_id in self.selected_methods:
                method = self.methods[method_id]
                kwargs = {}
                if method.param_name == 'cn':
                    kwargs['cn'] = data['cn']
                elif method.param_name == 'c_value':
                    kwargs['c_value'] = data['c_value']
                elif method.param_name == 'mannings_n':
                    kwargs['mannings_n'] = data['mannings_n_avg']
                
                tc = method.calculate(data['total_length_ft'], data['avg_slope_pct'], **kwargs)
                data['comparison_methods'][method_id] = {'tc_minutes': tc, 'method_name': method.name}
        
        return results
    
    def calculate_manual_mode(self, progress_callback) -> Dict:
        """Calculate TC using manual entry (comparison methods only)"""
        manual_data = self.manual_entry_table.get_data()
        results = {}
        total = len(manual_data)
        
        for i, entry in enumerate(manual_data):
            subbasin_id = entry['subbasin_id']
            length = entry['length_ft']
            slope = entry['slope_pct']
            
            results[subbasin_id] = {
                'tc_segment_min': None,  # Not available in manual mode
                'total_length_ft': length,
                'avg_slope_pct': slope,
                'segment_count': 0,
                'segments': [],
                'cn': entry['cn'],
                'c_value': entry['c_value'],
                'mannings_n_avg': entry['mannings_n'],
                'comparison_methods': {},
                'mode': 'manual'
            }
            
            # Calculate all comparison methods
            for method_id in self.selected_methods:
                method = self.methods[method_id]
                kwargs = {}
                if method.param_name == 'cn':
                    kwargs['cn'] = entry['cn']
                elif method.param_name == 'c_value':
                    kwargs['c_value'] = entry['c_value']
                elif method.param_name == 'mannings_n':
                    kwargs['mannings_n'] = entry['mannings_n']
                
                tc = method.calculate(length, slope, **kwargs)
                results[subbasin_id]['comparison_methods'][method_id] = {
                    'tc_minutes': tc, 'method_name': method.name
                }
            
            progress_callback(10 + int((i + 1) / total * 60), f"Processed {i + 1}/{total}")

        return results

    def calculate_dem_mode(self, progress_callback) -> Dict:
        """
        Calculate TC using DEM extraction - extracts flowpath from DEM for each subbasin

        This method:
        1. Loads the DEM and subbasin layers
        2. For each subbasin, extracts highest and lowest elevation points
        3. Calculates flowpath length and slope from DEM
        4. Applies industry-standard fallback methods for flat terrain
        5. Calculates TC using selected comparison methods
        """
        if not HAS_DEM_EXTRACTION:
            raise ValueError("DEM extraction module not available. Cannot proceed.")

        # Get layers
        dem_layer_id = self.dem_combo.currentData()
        sb_layer_id = self.dem_subbasin_combo.currentData()
        id_field = self.dem_subbasin_id_field.currentText()
        cn_field = self.dem_cn_field.currentData()
        land_type_field = self.dem_land_type_field.currentData()

        dem_layer = QgsProject.instance().mapLayer(dem_layer_id)
        sb_layer = QgsProject.instance().mapLayer(sb_layer_id)

        if not dem_layer or not sb_layer:
            raise ValueError("Could not load DEM or subbasin layer")

        # Get default parameters
        default_cn = self.dem_default_cn.value()
        default_c = self.dem_default_c.value()
        default_n = self.dem_default_n.value()
        p2_rainfall = self.dem_p2_rainfall.value()
        apply_slope_adjustments = self.apply_slope_adj_checkbox.isChecked()
        apply_tc_minimum = self.apply_tc_min_checkbox.isChecked()

        # Initialize the DEM extractor
        progress_callback(15, "Initializing DEM extractor...")
        extractor = DEMFlowpathExtractor(dem_layer, sb_layer, outlet_layer=None)

        results = {}
        features = list(sb_layer.getFeatures())
        total = len(features)

        if total == 0:
            raise ValueError("No features found in subbasin layer")

        progress_callback(20, f"Processing {total} subbasins...")

        for i, feature in enumerate(features):
            # Get subbasin ID
            subbasin_id = str(feature[id_field]) if id_field else f"SB-{i+1:03d}"

            # Get CN from field or use default
            if cn_field and feature[cn_field] is not None:
                try:
                    cn = float(feature[cn_field])
                except (ValueError, TypeError):
                    cn = default_cn
            else:
                cn = default_cn

            # Get land type from field or use default
            if land_type_field and feature[land_type_field] is not None:
                land_type = str(feature[land_type_field])
            else:
                land_type = 'rural'

            # Extract flowpath from DEM
            try:
                extraction_result = extractor.extract_flowpath_simple(feature)
                length_ft = extraction_result.get('length_ft', 0)
                slope_pct = extraction_result.get('slope_pct', 0)
                high_elev = extraction_result.get('high_elev_ft')
                low_elev = extraction_result.get('low_elev_ft')
                extraction_warnings = extraction_result.get('warnings', [])
                was_adjusted = extraction_result.get('adjusted', False)

            except Exception as e:
                # Fallback: use geometric estimation
                extraction_warnings = [f"DEM extraction failed: {str(e)}. Using geometric fallback."]
                geom = feature.geometry()
                if geom and not geom.isEmpty():
                    # Use bounding box diagonal as rough length estimate
                    bbox = geom.boundingBox()
                    length_ft = math.sqrt(bbox.width()**2 + bbox.height()**2)

                    # Check CRS units and convert if needed
                    crs = sb_layer.crs()
                    if crs.mapUnits() == 0:  # Meters
                        length_ft = length_ft * 3.28084

                    # Use minimum slope as fallback
                    slope_pct = 0.2  # Use transitional slope as conservative estimate
                else:
                    length_ft = 2100  # Default per NRCS typical
                    slope_pct = 0.2

                high_elev = None
                low_elev = None
                was_adjusted = True
                extraction_warnings.append("Using conservative defaults for length and slope")

            # Apply slope adjustments if needed and enabled
            if apply_slope_adjustments:
                slope_ftft = slope_pct / 100.0
                adj_slope, adjusted, adj_warning = DEMFlowpathExtractor.apply_slope_adjustment(slope_ftft)
                if adjusted:
                    slope_pct = adj_slope * 100.0
                    was_adjusted = True
                    if adj_warning:
                        extraction_warnings.append(adj_warning)

            # Build result for this subbasin
            results[subbasin_id] = {
                'tc_segment_min': None,  # Not applicable for DEM mode
                'total_length_ft': length_ft,
                'avg_slope_pct': slope_pct,
                'segment_count': 0,
                'segments': [],
                'cn': cn,
                'c_value': default_c,
                'mannings_n_avg': default_n,
                'comparison_methods': {},
                'mode': 'dem',
                'high_elev_ft': high_elev,
                'low_elev_ft': low_elev,
                'adjusted': was_adjusted,
                'warnings': extraction_warnings,
                'land_type': land_type,
            }

            # Calculate all comparison methods
            for method_id in self.selected_methods:
                method = self.methods[method_id]
                kwargs = {}
                if method.param_name == 'cn':
                    kwargs['cn'] = cn
                elif method.param_name == 'c_value':
                    kwargs['c_value'] = default_c
                elif method.param_name == 'mannings_n':
                    kwargs['mannings_n'] = default_n

                tc = method.calculate(length_ft, slope_pct, **kwargs)

                # Apply minimum TC if enabled
                if apply_tc_minimum and tc > 0:
                    adj_tc, tc_adjusted, tc_warning = DEMFlowpathExtractor.apply_tc_minimum(tc, land_type)
                    if tc_adjusted:
                        tc = adj_tc
                        if tc_warning and tc_warning not in extraction_warnings:
                            extraction_warnings.append(tc_warning)

                results[subbasin_id]['comparison_methods'][method_id] = {
                    'tc_minutes': tc, 'method_name': method.name
                }

            # Update warnings in result
            results[subbasin_id]['warnings'] = extraction_warnings

            progress_callback(20 + int((i + 1) / total * 50), f"Processed {subbasin_id} ({i + 1}/{total})")

        # Log summary
        adjusted_count = sum(1 for r in results.values() if r.get('adjusted', False))
        warning_count = sum(1 for r in results.values() if r.get('warnings', []))
        self.progress_logger.log(
            f"DEM extraction complete: {total} subbasins, {adjusted_count} with slope adjustments",
            "success" if adjusted_count < total / 2 else "warning"
        )

        return results

    def update_results_display(self, results: Dict):
        """Update the results table"""
        is_flowpath_mode = any(d.get('mode') == 'flowpath' for d in results.values())
        is_dem_mode = any(d.get('mode') == 'dem' for d in results.values())

        if is_flowpath_mode:
            columns = ['Subbasin', 'CN', 'C', 'n', 'Length', 'Slope', 'TC Segment']
        elif is_dem_mode:
            columns = ['Subbasin', 'CN', 'C', 'n', 'Length', 'Slope', 'Adj', 'Warnings']
        else:
            columns = ['Subbasin', 'CN', 'C', 'n', 'Length', 'Slope']
        
        for method_id in self.selected_methods:
            columns.append(self.methods[method_id].name)
            
        self.results_table.setRowCount(len(results))
        self.results_table.setColumnCount(len(columns))
        self.results_table.setHorizontalHeaderLabels(columns)
        
        for row, (subbasin_id, data) in enumerate(results.items()):
            col = 0
            self.results_table.setItem(row, col, QTableWidgetItem(str(subbasin_id))); col += 1
            self.results_table.setItem(row, col, QTableWidgetItem(f"{data['cn']:.0f}")); col += 1
            self.results_table.setItem(row, col, QTableWidgetItem(f"{data['c_value']:.2f}")); col += 1
            self.results_table.setItem(row, col, QTableWidgetItem(f"{data['mannings_n_avg']:.2f}")); col += 1
            self.results_table.setItem(row, col, QTableWidgetItem(f"{data['total_length_ft']:.0f}")); col += 1
            self.results_table.setItem(row, col, QTableWidgetItem(f"{data['avg_slope_pct']:.2f}")); col += 1

            if is_flowpath_mode:
                tc_seg = data['tc_segment_min']
                self.results_table.setItem(row, col, QTableWidgetItem(f"{tc_seg:.1f}" if tc_seg else "N/A")); col += 1
            elif is_dem_mode:
                # Show adjustment status and warnings
                adj_status = "Yes" if data.get('adjusted', False) else "No"
                adj_item = QTableWidgetItem(adj_status)
                if data.get('adjusted', False):
                    adj_item.setBackground(Qt.yellow)
                self.results_table.setItem(row, col, adj_item); col += 1

                warnings = data.get('warnings', [])
                warnings_text = "; ".join(warnings[:2]) if warnings else "None"  # Show first 2 warnings
                warn_item = QTableWidgetItem(warnings_text if len(warnings_text) <= 50 else warnings_text[:47] + "...")
                if warnings:
                    warn_item.setToolTip("\n".join(warnings))  # Full list in tooltip
                self.results_table.setItem(row, col, warn_item); col += 1

            for method_id in self.selected_methods:
                if method_id in data['comparison_methods']:
                    tc = data['comparison_methods'][method_id]['tc_minutes']
                    self.results_table.setItem(row, col, QTableWidgetItem(f"{tc:.1f}"))
                col += 1

        self.results_table.resizeColumnsToContents()

        # Summary
        all_methods_tc = []
        for d in results.values():
            for m in d['comparison_methods'].values():
                all_methods_tc.append(m['tc_minutes'])

        if is_flowpath_mode:
            mode_str = "Flowpath Mode"
        elif is_dem_mode:
            adjusted_count = sum(1 for d in results.values() if d.get('adjusted', False))
            mode_str = f"DEM Extraction Mode ({adjusted_count} adjusted)"
        else:
            mode_str = "Manual Entry Mode"

        self.summary_label.setText(
            f"<b>{mode_str}:</b> {len(results)} subbasins | "
            f"TC range: {min(all_methods_tc):.1f} - {max(all_methods_tc):.1f} min"
        )
        self.summary_label.setStyleSheet("color: #333; padding: 10px;")
        
    def create_outputs(self, results: Dict, output_dir: str):
        """Create output CSV files"""
        is_flowpath_mode = any(d.get('mode') == 'flowpath' for d in results.values())
        is_dem_mode = any(d.get('mode') == 'dem' for d in results.values())

        csv_path = os.path.join(output_dir, "tc_calculations.csv")

        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            header = ['Subbasin_ID', 'Mode', 'CN', 'C_Value', 'Mannings_n',
                     'Total_Length_ft', 'Avg_Slope_pct']
            if is_flowpath_mode:
                header.append('TC_Segment_min')
            if is_dem_mode:
                header.extend(['High_Elev_ft', 'Low_Elev_ft', 'Adjusted', 'Warnings'])
            for method_id in self.selected_methods:
                header.append(f'TC_{self.methods[method_id].name}_min')
            writer.writerow(header)

            for subbasin_id, data in results.items():
                row = [
                    subbasin_id,
                    data.get('mode', 'unknown'),
                    data['cn'],
                    data['c_value'],
                    data['mannings_n_avg'],
                    round(data['total_length_ft'], 1),
                    round(data['avg_slope_pct'], 3),
                ]
                if is_flowpath_mode:
                    tc_seg = data['tc_segment_min']
                    row.append(round(tc_seg, 2) if tc_seg else '')
                if is_dem_mode:
                    high_elev = data.get('high_elev_ft')
                    low_elev = data.get('low_elev_ft')
                    row.append(round(high_elev, 1) if high_elev is not None else '')
                    row.append(round(low_elev, 1) if low_elev is not None else '')
                    row.append('Yes' if data.get('adjusted', False) else 'No')
                    row.append('; '.join(data.get('warnings', [])))

                for method_id in self.selected_methods:
                    if method_id in data['comparison_methods']:
                        row.append(round(data['comparison_methods'][method_id]['tc_minutes'], 2))
                    else:
                        row.append('')
                writer.writerow(row)

        # Segment details (flowpath mode only)
        if is_flowpath_mode:
            detail_path = os.path.join(output_dir, "tc_segment_details.csv")
            with open(detail_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Subbasin_ID', 'Flow_Type', 'Length_ft', 'Slope_pct',
                                'Mannings_n', 'Hydraulic_Radius_ft', 'Travel_Time_min'])
                for subbasin_id, data in results.items():
                    for seg in data.get('segments', []):
                        writer.writerow([
                            subbasin_id, seg['flow_type'], round(seg['length_ft'], 1),
                            round(seg['slope_pct'], 3), round(seg['mannings_n'], 3),
                            round(seg['hydraulic_radius'], 3) if seg['hydraulic_radius'] else '',
                            round(seg['travel_time_min'], 2)
                        ])

        # DEM extraction summary (dem mode only)
        if is_dem_mode:
            dem_path = os.path.join(output_dir, "tc_dem_extraction_summary.csv")
            with open(dem_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Subbasin_ID', 'Length_ft', 'Slope_pct', 'High_Elev_ft',
                                'Low_Elev_ft', 'Adjusted', 'Land_Type', 'Warnings'])
                for subbasin_id, data in results.items():
                    high_elev = data.get('high_elev_ft')
                    low_elev = data.get('low_elev_ft')
                    writer.writerow([
                        subbasin_id,
                        round(data['total_length_ft'], 1),
                        round(data['avg_slope_pct'], 3),
                        round(high_elev, 1) if high_elev is not None else '',
                        round(low_elev, 1) if low_elev is not None else '',
                        'Yes' if data.get('adjusted', False) else 'No',
                        data.get('land_type', 'rural'),
                        '; '.join(data.get('warnings', []))
                    ])

        self.progress_logger.log(f"Outputs saved to {output_dir}", "success")
        
    def show_completion_dialog(self, results: dict, output_dir: str):
        """Show completion dialog"""
        is_flowpath_mode = any(d.get('mode') == 'flowpath' for d in results.values())
        is_dem_mode = any(d.get('mode') == 'dem' for d in results.values())

        if is_flowpath_mode:
            mode_str = "Flowpath Layer Mode (TR-55 + Comparison)"
        elif is_dem_mode:
            adjusted_count = sum(1 for d in results.values() if d.get('adjusted', False))
            mode_str = f"DEM Extraction Mode ({adjusted_count} subbasins with slope adjustments)"
        else:
            mode_str = "Manual Entry Mode (Comparison Methods Only)"

        message = f"""
TC Calculation Complete (v{self.version})

Mode: {mode_str}
Subbasins: {len(results)}
Methods: {', '.join(self.methods[m].name for m in self.selected_methods)}

Output Files:
• tc_calculations.csv - Summary by subbasin
"""
        if is_flowpath_mode:
            message += "• tc_segment_details.csv - Individual segment travel times\n"
        if is_dem_mode:
            message += "• tc_dem_extraction_summary.csv - DEM extraction details and warnings\n"

        message += f"\nSaved to: {output_dir}"

        QMessageBox.information(self.gui_widget, "Calculation Complete", message)


# =============================================================================
# EXPORT ALIAS
# =============================================================================

TCCalculatorTool = TCCalculatorToolEnhanced
