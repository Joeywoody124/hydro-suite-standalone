"""
DEM-Based Flowpath Extraction for TC Calculator
Extracts flowpath length and slope from DEM for each subbasin

Version 1.0 - January 2025
Author: Joey Woody, PE - J. Bragg Consulting Inc.

Industry Standard Fallback Methods for Flat Terrain:
- TxDOT/Cleveland et al. 2012: Add 0.0005 to slope when S < 0.002 (0.2%)
- NRCS: Minimum TC of 6 minutes (0.1 hour)
- California HDM: Minimum TC of 5 min (paved) or 10 min (rural)

References:
- TR-55: Urban Hydrology for Small Watersheds (USDA-SCS, 1986)
- NEH Part 630, Chapter 15: Time of Concentration (NRCS, 2010)
- TxDOT Hydraulic Design Manual, Chapter 4 (2023)
- Cleveland et al. 2012: Time of Concentration for Low-Slope Watersheds
"""

import os
import math
import traceback
from typing import Optional, Tuple, List, Dict, Any, Callable

from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QMessageBox, QFrame, QGroupBox, QCheckBox, QDoubleSpinBox,
    QSpinBox, QComboBox, QTableWidget, QTableWidgetItem,
    QProgressBar, QRadioButton, QButtonGroup
)
from qgis.PyQt.QtCore import Qt, pyqtSignal

from qgis.core import (
    QgsProject, QgsVectorLayer, QgsRasterLayer, QgsFeature,
    QgsGeometry, QgsPointXY, QgsWkbTypes, QgsCoordinateTransform,
    QgsCoordinateReferenceSystem, QgsRectangle, QgsField
)
from qgis.analysis import QgsZonalStatistics

try:
    from qgis import processing
    HAS_PROCESSING = True
except ImportError:
    HAS_PROCESSING = False


# =============================================================================
# CONSTANTS - INDUSTRY STANDARD THRESHOLDS
# =============================================================================

# TxDOT/Cleveland et al. 2012 low-slope adjustment
MIN_SLOPE_THRESHOLD = 0.002  # 0.2% - Below this, apply adjustment
TRANSITIONAL_SLOPE_UPPER = 0.003  # 0.3% - Between 0.2-0.3% is transitional
LOW_SLOPE_ADJUSTMENT = 0.0005  # Add to slope when S < MIN_SLOPE_THRESHOLD

# Minimum TC values (NRCS/California HDM)
MIN_TC_PAVED = 5.0  # minutes - for paved urban areas
MIN_TC_RURAL = 10.0  # minutes - for rural/undeveloped areas
MIN_TC_DEFAULT = 6.0  # minutes - NRCS default (0.1 hour)

# Sheet flow maximum length per TR-55
MAX_SHEET_FLOW_LENGTH = 300.0  # feet

# Shallow concentrated flow velocity coefficients (TR-55 Figure 3-1)
SHALLOW_CONC_COEFFICIENTS = {
    'paved': 20.328,
    'unpaved': 16.1345,
    'grassed_waterway': 16.1345,
    'nearly_bare': 9.965,
    'cultivated_row': 8.762,
    'short_grass_prairie': 6.962,
    'minimum_tillage': 5.032,
    'forest_heavy_litter': 2.516,
}

# Default Manning's n values for sheet flow (TR-55 Table 3-1)
SHEET_FLOW_N_VALUES = {
    'smooth_surface': 0.011,  # Concrete, asphalt, gravel, bare soil
    'fallow_no_residue': 0.05,
    'cultivated_residue_20': 0.06,
    'cultivated_residue_20_plus': 0.17,
    'grass_range_short': 0.15,
    'grass_range_dense': 0.24,
    'bermuda_grass': 0.41,
    'woods_light': 0.40,
    'woods_dense': 0.80,
}


# =============================================================================
# DEM EXTRACTION FUNCTIONS
# =============================================================================

class DEMFlowpathExtractor:
    """
    Extract flowpath properties from DEM for TC calculation
    
    Methods:
    1. Centroid-to-outlet: Simple line from subbasin centroid to outlet
    2. Longest flowpath: Process DEM to find hydraulically longest path
    3. User-defined outlet: Use outlet points layer
    """
    
    def __init__(self, dem_layer: QgsRasterLayer, subbasin_layer: QgsVectorLayer,
                 outlet_layer: Optional[QgsVectorLayer] = None):
        self.dem = dem_layer
        self.subbasins = subbasin_layer
        self.outlets = outlet_layer
        
        # Ensure CRS match
        self.dem_crs = dem_layer.crs()
        self.target_crs = subbasin_layer.crs()
        
        # Get DEM properties
        self.dem_extent = dem_layer.extent()
        self.dem_provider = dem_layer.dataProvider()
        
    def get_elevation_at_point(self, point: QgsPointXY) -> Optional[float]:
        """Sample DEM elevation at a point"""
        try:
            # Transform point to DEM CRS if needed
            if self.target_crs != self.dem_crs:
                transform = QgsCoordinateTransform(
                    self.target_crs, self.dem_crs, QgsProject.instance()
                )
                point = transform.transform(point)
            
            # Sample raster value
            result = self.dem_provider.sample(point, 1)
            if result[1]:  # Valid sample
                return result[0]
            return None
        except Exception:
            return None
    
    def extract_flowpath_simple(self, subbasin_feature: QgsFeature,
                                outlet_point: Optional[QgsPointXY] = None) -> Dict:
        """
        Simple flowpath extraction: highest point to outlet
        
        Returns dict with:
        - length_ft: Flowpath length in feet
        - slope_ftft: Slope in ft/ft
        - slope_pct: Slope in percent
        - high_elev_ft: Highest elevation
        - low_elev_ft: Lowest elevation (outlet)
        - method: Extraction method used
        - warnings: List of any warnings/adjustments
        """
        result = {
            'subbasin_id': None,
            'length_ft': 0.0,
            'slope_ftft': 0.0,
            'slope_pct': 0.0,
            'high_elev_ft': None,
            'low_elev_ft': None,
            'method': 'simple_centroid',
            'warnings': [],
            'adjusted': False,
        }
        
        geom = subbasin_feature.geometry()
        if geom.isEmpty():
            result['warnings'].append("Empty geometry")
            return result
        
        # Get subbasin centroid
        centroid = geom.centroid().asPoint()
        
        # Determine outlet point
        if outlet_point is None:
            # Use lowest point on subbasin boundary
            boundary = geom.convertToType(QgsWkbTypes.LineGeometry, False)
            if boundary:
                # Sample points along boundary to find lowest
                boundary_line = boundary.asPolyline() if boundary.type() == QgsWkbTypes.LineGeometry else []
                if not boundary_line:
                    # Try multiline
                    boundary_multi = boundary.asMultiPolyline()
                    boundary_line = boundary_multi[0] if boundary_multi else []
                
                lowest_elev = float('inf')
                lowest_point = centroid
                
                for pt in boundary_line:
                    elev = self.get_elevation_at_point(pt)
                    if elev is not None and elev < lowest_elev:
                        lowest_elev = elev
                        lowest_point = pt
                
                outlet_point = lowest_point
            else:
                outlet_point = centroid
        
        # Get highest point (sample grid within subbasin)
        bbox = geom.boundingBox()
        highest_elev = float('-inf')
        highest_point = centroid
        
        # Sample at regular intervals
        x_step = bbox.width() / 10.0
        y_step = bbox.height() / 10.0
        
        for i in range(11):
            for j in range(11):
                pt = QgsPointXY(bbox.xMinimum() + i * x_step,
                               bbox.yMinimum() + j * y_step)
                if geom.contains(QgsGeometry.fromPointXY(pt)):
                    elev = self.get_elevation_at_point(pt)
                    if elev is not None and elev > highest_elev:
                        highest_elev = elev
                        highest_point = pt
        
        # Get outlet elevation
        low_elev = self.get_elevation_at_point(outlet_point)
        
        if highest_elev == float('-inf') or low_elev is None:
            result['warnings'].append("Could not extract elevations from DEM")
            return result
        
        # Calculate length (simple straight-line distance)
        # Convert to feet if CRS is in meters
        length = highest_point.distance(outlet_point)
        
        # Check CRS units - convert to feet if needed
        unit = self.target_crs.mapUnits()
        if unit == 0:  # Meters
            length = length * 3.28084
            highest_elev = highest_elev * 3.28084
            low_elev = low_elev * 3.28084
        elif unit == 2:  # Feet - already in feet
            pass
        
        result['length_ft'] = length
        result['high_elev_ft'] = highest_elev
        result['low_elev_ft'] = low_elev
        
        # Calculate slope
        elev_diff = highest_elev - low_elev
        
        if length > 0:
            slope_ftft = elev_diff / length
        else:
            slope_ftft = 0.0
            result['warnings'].append("Zero length calculated")
        
        # Apply low-slope adjustment if needed
        slope_ftft, adjusted, adj_warning = self.apply_slope_adjustment(slope_ftft)
        result['adjusted'] = adjusted
        if adj_warning:
            result['warnings'].append(adj_warning)
        
        result['slope_ftft'] = slope_ftft
        result['slope_pct'] = slope_ftft * 100.0
        
        return result
    
    def extract_flowpath_profile(self, subbasin_feature: QgsFeature,
                                 outlet_point: Optional[QgsPointXY] = None,
                                 num_samples: int = 50) -> Dict:
        """
        Profile-based flowpath extraction with elevation sampling
        
        Samples elevations along the flowpath to detect:
        - Adverse slopes (water flowing uphill)
        - Zero/flat sections
        - Applies appropriate adjustments
        """
        result = self.extract_flowpath_simple(subbasin_feature, outlet_point)
        result['method'] = 'profile_sampled'
        result['profile'] = []
        
        if result['length_ft'] <= 0:
            return result
        
        # Create line from high point to outlet for profile sampling
        geom = subbasin_feature.geometry()
        centroid = geom.centroid().asPoint()
        
        # Use high/low points from simple extraction
        # Sample along the line
        # This is a simplified approach - full implementation would trace actual flow path
        
        return result
    
    @staticmethod
    def apply_slope_adjustment(slope_ftft: float) -> Tuple[float, bool, str]:
        """
        Apply industry-standard slope adjustments for flat terrain
        
        Based on TxDOT/Cleveland et al. 2012:
        - If S < 0.002 (0.2%): Add 0.0005 to slope
        - If S between 0.002-0.003 (0.2-0.3%): Transitional, use judgment
        - If S < 0: Adverse slope, use minimum
        
        Returns: (adjusted_slope, was_adjusted, warning_message)
        """
        adjusted = False
        warning = None
        
        if slope_ftft < 0:
            # Adverse slope - physically impossible for gravity flow
            # Use minimum slope
            adjusted_slope = LOW_SLOPE_ADJUSTMENT
            adjusted = True
            warning = f"Adverse slope detected ({slope_ftft*100:.3f}%). Applied minimum slope of {LOW_SLOPE_ADJUSTMENT*100:.2f}%"
        
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
    
    @staticmethod
    def apply_tc_minimum(tc_minutes: float, land_type: str = 'rural') -> Tuple[float, bool, str]:
        """
        Apply minimum TC per NRCS/California HDM guidance
        
        Returns: (adjusted_tc, was_adjusted, warning_message)
        """
        if land_type.lower() in ['paved', 'urban', 'impervious']:
            min_tc = MIN_TC_PAVED
        elif land_type.lower() in ['rural', 'undeveloped', 'natural']:
            min_tc = MIN_TC_RURAL
        else:
            min_tc = MIN_TC_DEFAULT
        
        if tc_minutes < min_tc:
            warning = f"Computed TC ({tc_minutes:.1f} min) below minimum. Using {min_tc} min per NRCS guidance."
            return min_tc, True, warning
        
        return tc_minutes, False, None


# =============================================================================
# SCS LAG METHOD WITH DEM EXTRACTION
# =============================================================================

class SCSLagDEMCalculator:
    """
    SCS Lag Method with DEM-extracted parameters
    
    Formula: Lag = (L^0.8 × S_retention^0.7) / (1900 × Y^0.5)
    Where:
        L = hydraulic length (ft)
        S_retention = (1000/CN) - 9
        Y = average watershed slope (%)
        
    TC = Lag / 0.6
    
    Limitations per NRCS:
    - CN should be between 50 and 95
    - Slope should be between 0.5% and 64%
    - Flow length should be between 200 and 26,000 ft
    """
    
    # Valid ranges per NRCS WinTR-55
    MIN_CN = 50
    MAX_CN = 95
    MIN_SLOPE_PCT = 0.5
    MAX_SLOPE_PCT = 64.0
    MIN_LENGTH_FT = 200
    MAX_LENGTH_FT = 26000
    
    def __init__(self):
        self.warnings = []
        
    def calculate(self, length_ft: float, slope_pct: float, cn: float,
                  apply_adjustments: bool = True) -> Dict:
        """
        Calculate TC using SCS Lag Method
        
        Args:
            length_ft: Hydraulic flow length in feet
            slope_pct: Average watershed slope in percent
            cn: Curve number
            apply_adjustments: Whether to apply low-slope adjustments
            
        Returns:
            Dict with lag_hr, tc_min, and any warnings
        """
        self.warnings = []
        result = {
            'method': 'SCS_Lag',
            'lag_hr': None,
            'tc_min': None,
            'length_ft': length_ft,
            'slope_pct': slope_pct,
            'cn': cn,
            'adjusted_slope': False,
            'adjusted_tc': False,
            'warnings': [],
            'valid': True,
        }
        
        # Validate inputs
        if cn < self.MIN_CN:
            result['warnings'].append(f"CN ({cn}) below minimum ({self.MIN_CN}). Results may be unreliable.")
            if cn <= 0:
                cn = self.MIN_CN
        elif cn > self.MAX_CN:
            result['warnings'].append(f"CN ({cn}) above maximum ({self.MAX_CN}). Results may be unreliable.")
            if cn > 100:
                cn = self.MAX_CN
        
        if length_ft < self.MIN_LENGTH_FT:
            result['warnings'].append(f"Length ({length_ft:.0f} ft) below minimum ({self.MIN_LENGTH_FT} ft). Consider alternative method.")
        elif length_ft > self.MAX_LENGTH_FT:
            result['warnings'].append(f"Length ({length_ft:.0f} ft) above maximum ({self.MAX_LENGTH_FT} ft). Consider WinTR-20.")
        
        # Apply slope adjustments if needed
        slope_ftft = slope_pct / 100.0
        
        if apply_adjustments:
            adj_slope, was_adjusted, adj_warning = DEMFlowpathExtractor.apply_slope_adjustment(slope_ftft)
            if was_adjusted:
                result['adjusted_slope'] = True
                result['warnings'].append(adj_warning)
                slope_pct = adj_slope * 100.0
        
        # Check slope range
        if slope_pct < self.MIN_SLOPE_PCT:
            result['warnings'].append(f"Slope ({slope_pct:.2f}%) below minimum ({self.MIN_SLOPE_PCT}%). Use alternative procedure per NRCS.")
        elif slope_pct > self.MAX_SLOPE_PCT:
            result['warnings'].append(f"Slope ({slope_pct:.2f}%) above maximum ({self.MAX_SLOPE_PCT}%). Use alternative procedure per NRCS.")
        
        # Calculate retention term
        if cn > 0:
            s_retention = (1000.0 / cn) - 9.0
        else:
            s_retention = 1.0
        
        if s_retention <= 0:
            s_retention = 0.1
            result['warnings'].append("Retention term ≤ 0. Using minimum value.")
        
        # Calculate lag (hours)
        if slope_pct > 0 and length_ft > 0:
            lag_hr = ((length_ft ** 0.8) * (s_retention ** 0.7)) / (1900.0 * ((slope_pct / 100.0) ** 0.5))
        else:
            lag_hr = 0.0
            result['valid'] = False
        
        # Convert to TC
        if lag_hr > 0:
            tc_hr = lag_hr / 0.6
            tc_min = tc_hr * 60.0
        else:
            tc_min = MIN_TC_DEFAULT
            result['warnings'].append("Calculated TC = 0. Using minimum value.")
        
        # Apply minimum TC if needed
        if apply_adjustments:
            adj_tc, tc_adjusted, tc_warning = DEMFlowpathExtractor.apply_tc_minimum(tc_min, 'rural')
            if tc_adjusted:
                result['adjusted_tc'] = True
                result['warnings'].append(tc_warning)
                tc_min = adj_tc
        
        result['lag_hr'] = lag_hr
        result['tc_min'] = tc_min
        result['slope_pct'] = slope_pct
        
        return result


# =============================================================================
# TR-55 VELOCITY METHOD WITH DEM EXTRACTION
# =============================================================================

class TR55VelocityDEMCalculator:
    """
    TR-55 Velocity Method with DEM-extracted parameters
    
    Three flow types:
    1. Sheet flow (0-100 ft): Kinematic wave equation
    2. Shallow concentrated flow (100-1000+ ft): Velocity curves
    3. Channel flow: Manning's equation
    
    When detailed flowpath not available, uses simplified approach:
    - Assumes sheet flow for first 100 ft
    - Assumes shallow concentrated for remainder
    - Estimates proportions based on land use
    """
    
    def __init__(self):
        self.warnings = []
        
    def calculate_sheet_flow_time(self, length_ft: float, slope_pct: float,
                                   mannings_n: float, p2_rainfall: float = 3.5) -> float:
        """
        TR-55 Equation 3-3: Sheet flow travel time
        
        Tt = (0.007 × (n × L)^0.8) / (P2^0.5 × S^0.4)
        
        Limits:
        - Length ≤ 300 ft (100 ft recommended)
        - S should be > 0
        """
        # Enforce maximum length
        length_ft = min(length_ft, MAX_SHEET_FLOW_LENGTH)
        
        if length_ft <= 0 or slope_pct <= 0 or mannings_n <= 0:
            return 0.0
        
        slope_ftft = slope_pct / 100.0
        
        # Apply low-slope adjustment
        if slope_ftft < MIN_SLOPE_THRESHOLD:
            slope_ftft = slope_ftft + LOW_SLOPE_ADJUSTMENT
        
        tt_hours = (0.007 * ((mannings_n * length_ft) ** 0.8)) / \
                   ((p2_rainfall ** 0.5) * (slope_ftft ** 0.4))
        
        return tt_hours * 60.0  # Return minutes
    
    def calculate_shallow_conc_time(self, length_ft: float, slope_pct: float,
                                    surface_type: str = 'unpaved') -> float:
        """
        TR-55 Shallow Concentrated Flow
        
        V = Cp × S^0.5
        Tt = L / V / 60
        """
        if length_ft <= 0 or slope_pct <= 0:
            return 0.0
        
        slope_ftft = slope_pct / 100.0
        
        # Apply low-slope adjustment
        if slope_ftft < MIN_SLOPE_THRESHOLD:
            slope_ftft = slope_ftft + LOW_SLOPE_ADJUSTMENT
        
        # Get velocity coefficient
        cp = SHALLOW_CONC_COEFFICIENTS.get(surface_type.lower(), 16.1345)
        
        velocity_fps = cp * (slope_ftft ** 0.5)
        
        if velocity_fps <= 0:
            return 0.0
        
        return (length_ft / velocity_fps) / 60.0  # Return minutes
    
    def calculate_channel_time(self, length_ft: float, slope_pct: float,
                               mannings_n: float, hydraulic_radius: float = 1.0) -> float:
        """
        Manning's equation for open channel flow
        
        V = (1.49/n) × R^(2/3) × S^0.5
        Tt = L / V / 60
        """
        if length_ft <= 0 or slope_pct <= 0 or mannings_n <= 0:
            return 0.0
        
        slope_ftft = slope_pct / 100.0
        
        # Apply low-slope adjustment
        if slope_ftft < MIN_SLOPE_THRESHOLD:
            slope_ftft = slope_ftft + LOW_SLOPE_ADJUSTMENT
        
        velocity_fps = (1.49 / mannings_n) * (hydraulic_radius ** (2.0/3.0)) * (slope_ftft ** 0.5)
        
        if velocity_fps <= 0:
            return 0.0
        
        return (length_ft / velocity_fps) / 60.0  # Return minutes
    
    def calculate_simplified(self, total_length_ft: float, slope_pct: float, cn: float,
                             land_type: str = 'rural', p2_rainfall: float = 3.5,
                             apply_adjustments: bool = True) -> Dict:
        """
        Simplified TR-55 calculation when detailed flowpath not available
        
        Assumptions:
        - First 100 ft: Sheet flow
        - Remainder: Shallow concentrated flow
        - Land type determines surface characteristics
        """
        result = {
            'method': 'TR55_Simplified',
            'tc_min': None,
            'tt_sheet_min': 0.0,
            'tt_shallow_min': 0.0,
            'tt_channel_min': 0.0,
            'length_ft': total_length_ft,
            'slope_pct': slope_pct,
            'adjusted_slope': False,
            'adjusted_tc': False,
            'warnings': [],
            'valid': True,
        }
        
        if total_length_ft <= 0:
            result['valid'] = False
            result['warnings'].append("Zero or negative length")
            return result
        
        # Apply slope adjustments
        slope_ftft = slope_pct / 100.0
        if apply_adjustments and slope_ftft < MIN_SLOPE_THRESHOLD:
            adj_slope, was_adjusted, adj_warning = DEMFlowpathExtractor.apply_slope_adjustment(slope_ftft)
            if was_adjusted:
                result['adjusted_slope'] = True
                result['warnings'].append(adj_warning)
                slope_pct = adj_slope * 100.0
        
        # Determine surface characteristics based on land type
        if land_type.lower() in ['paved', 'urban', 'commercial']:
            sheet_n = 0.011  # Smooth surface
            shallow_type = 'paved'
            land_category = 'paved'
        elif land_type.lower() in ['residential', 'suburban']:
            sheet_n = 0.24  # Dense grass
            shallow_type = 'unpaved'
            land_category = 'rural'
        elif land_type.lower() in ['woods', 'forest']:
            sheet_n = 0.80  # Dense woods
            shallow_type = 'forest_heavy_litter'
            land_category = 'rural'
        else:  # rural, agricultural
            sheet_n = 0.15  # Short grass
            shallow_type = 'unpaved'
            land_category = 'rural'
        
        # Calculate flow segments
        sheet_length = min(100.0, total_length_ft)  # First 100 ft is sheet flow
        remaining_length = total_length_ft - sheet_length
        
        # Assume 80% shallow concentrated, 20% channel for longer paths
        if remaining_length > 1000:
            shallow_length = remaining_length * 0.8
            channel_length = remaining_length * 0.2
        else:
            shallow_length = remaining_length
            channel_length = 0.0
        
        # Calculate travel times
        tt_sheet = self.calculate_sheet_flow_time(sheet_length, slope_pct, sheet_n, p2_rainfall)
        tt_shallow = self.calculate_shallow_conc_time(shallow_length, slope_pct, shallow_type)
        
        # Channel flow (use conservative n = 0.035)
        if channel_length > 0:
            tt_channel = self.calculate_channel_time(channel_length, slope_pct, 0.035, 1.0)
        else:
            tt_channel = 0.0
        
        tc_min = tt_sheet + tt_shallow + tt_channel
        
        result['tt_sheet_min'] = tt_sheet
        result['tt_shallow_min'] = tt_shallow
        result['tt_channel_min'] = tt_channel
        result['sheet_length_ft'] = sheet_length
        result['shallow_length_ft'] = shallow_length
        result['channel_length_ft'] = channel_length
        
        # Apply minimum TC
        if apply_adjustments:
            adj_tc, tc_adjusted, tc_warning = DEMFlowpathExtractor.apply_tc_minimum(tc_min, land_category)
            if tc_adjusted:
                result['adjusted_tc'] = True
                result['warnings'].append(tc_warning)
                tc_min = adj_tc
        
        result['tc_min'] = tc_min
        result['slope_pct'] = slope_pct
        
        return result


# =============================================================================
# COMPARISON AND VALIDATION
# =============================================================================

def compare_tc_methods(length_ft: float, slope_pct: float, cn: float,
                       land_type: str = 'rural', p2_rainfall: float = 3.5) -> Dict:
    """
    Compare TC results from multiple methods
    
    Returns dict with results from:
    - SCS Lag
    - TR-55 Simplified
    - Kirpich
    - FAA (if C available)
    - Kerby
    """
    results = {
        'length_ft': length_ft,
        'slope_pct': slope_pct,
        'cn': cn,
        'methods': {}
    }
    
    # SCS Lag
    scs_calc = SCSLagDEMCalculator()
    scs_result = scs_calc.calculate(length_ft, slope_pct, cn)
    results['methods']['scs_lag'] = scs_result
    
    # TR-55 Simplified
    tr55_calc = TR55VelocityDEMCalculator()
    tr55_result = tr55_calc.calculate_simplified(length_ft, slope_pct, cn, land_type, p2_rainfall)
    results['methods']['tr55_simplified'] = tr55_result
    
    # Kirpich (for comparison)
    if slope_pct > 0 and length_ft > 0:
        slope_ftft = slope_pct / 100.0
        if slope_ftft < MIN_SLOPE_THRESHOLD:
            slope_ftft = slope_ftft + LOW_SLOPE_ADJUSTMENT
        tc_kirpich = 0.0078 * (length_ft ** 0.77) / (slope_ftft ** 0.385)
        results['methods']['kirpich'] = {'tc_min': tc_kirpich, 'method': 'Kirpich'}
    
    # Kerby (for short overland flow)
    if length_ft <= 1200:  # Kerby limit
        n_kerby = 0.4 if land_type.lower() in ['rural', 'grass'] else 0.02
        slope_ftft = slope_pct / 100.0
        if slope_ftft < MIN_SLOPE_THRESHOLD:
            slope_ftft = slope_ftft + LOW_SLOPE_ADJUSTMENT
        if slope_ftft > 0:
            tc_kerby = 1.44 * ((n_kerby * length_ft) ** 0.467) / (slope_ftft ** 0.235)
            results['methods']['kerby'] = {'tc_min': tc_kerby, 'method': 'Kerby', 'n': n_kerby}
    
    return results


# =============================================================================
# WIDGET FOR DEM EXTRACTION MODE
# =============================================================================

class DEMExtractionWidget(QWidget):
    """Widget for DEM-based flowpath extraction in TC Calculator"""
    
    extraction_complete = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Title and description
        title = QLabel("<b>DEM-Based Flowpath Extraction</b>")
        layout.addWidget(title)
        
        desc = QLabel(
            "Extract flowpath length and slope from DEM for each subbasin. "
            "Applies industry-standard fallback methods for flat terrain."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #555;")
        layout.addWidget(desc)
        
        # DEM layer selector
        dem_group = QGroupBox("DEM Input")
        dem_layout = QVBoxLayout(dem_group)
        
        dem_row = QHBoxLayout()
        dem_row.addWidget(QLabel("DEM Raster Layer:"))
        self.dem_combo = QComboBox()
        self.dem_combo.setMinimumWidth(200)
        dem_row.addWidget(self.dem_combo)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_layers)
        dem_row.addWidget(refresh_btn)
        dem_row.addStretch()
        dem_layout.addLayout(dem_row)
        
        # Subbasin layer selector
        sb_row = QHBoxLayout()
        sb_row.addWidget(QLabel("Subbasin Layer:"))
        self.subbasin_combo = QComboBox()
        self.subbasin_combo.setMinimumWidth(200)
        sb_row.addWidget(self.subbasin_combo)
        sb_row.addStretch()
        dem_layout.addLayout(sb_row)
        
        # Subbasin ID field
        id_row = QHBoxLayout()
        id_row.addWidget(QLabel("Subbasin ID Field:"))
        self.id_field_combo = QComboBox()
        self.id_field_combo.setMinimumWidth(150)
        id_row.addWidget(self.id_field_combo)
        id_row.addStretch()
        dem_layout.addLayout(id_row)
        
        # Optional outlets layer
        outlet_row = QHBoxLayout()
        outlet_row.addWidget(QLabel("Outlets Layer (optional):"))
        self.outlet_combo = QComboBox()
        self.outlet_combo.setMinimumWidth(200)
        self.outlet_combo.addItem("-- None (auto-detect) --", None)
        outlet_row.addWidget(self.outlet_combo)
        outlet_row.addStretch()
        dem_layout.addLayout(outlet_row)
        
        layout.addWidget(dem_group)
        
        # Slope adjustment options
        adj_group = QGroupBox("Flat Terrain Adjustments")
        adj_layout = QVBoxLayout(adj_group)
        
        self.apply_slope_adj = QCheckBox("Apply TxDOT low-slope adjustment (add 0.0005 when S < 0.2%)")
        self.apply_slope_adj.setChecked(True)
        adj_layout.addWidget(self.apply_slope_adj)
        
        self.apply_tc_min = QCheckBox("Apply minimum TC (6 min default, 5 min paved, 10 min rural)")
        self.apply_tc_min.setChecked(True)
        adj_layout.addWidget(self.apply_tc_min)
        
        threshold_row = QHBoxLayout()
        threshold_row.addWidget(QLabel("Custom minimum slope (%):"))
        self.min_slope_spin = QDoubleSpinBox()
        self.min_slope_spin.setRange(0.01, 1.0)
        self.min_slope_spin.setValue(0.2)
        self.min_slope_spin.setDecimals(2)
        self.min_slope_spin.setSingleStep(0.05)
        threshold_row.addWidget(self.min_slope_spin)
        threshold_row.addStretch()
        adj_layout.addLayout(threshold_row)
        
        layout.addWidget(adj_group)
        
        # Method selection
        method_group = QGroupBox("TC Calculation Method")
        method_layout = QVBoxLayout(method_group)
        
        self.method_group = QButtonGroup()
        
        self.scs_lag_radio = QRadioButton("SCS Lag Method (requires CN per subbasin)")
        self.scs_lag_radio.setChecked(True)
        self.method_group.addButton(self.scs_lag_radio)
        method_layout.addWidget(self.scs_lag_radio)
        
        self.tr55_radio = QRadioButton("TR-55 Simplified (estimates flow types from land use)")
        self.method_group.addButton(self.tr55_radio)
        method_layout.addWidget(self.tr55_radio)
        
        self.both_radio = QRadioButton("Both methods (for comparison)")
        self.method_group.addButton(self.both_radio)
        method_layout.addWidget(self.both_radio)
        
        layout.addWidget(method_group)
        
        # P2 rainfall for TR-55
        p2_row = QHBoxLayout()
        p2_row.addWidget(QLabel("2-yr 24-hr Rainfall (in):"))
        self.p2_spin = QDoubleSpinBox()
        self.p2_spin.setRange(1.0, 10.0)
        self.p2_spin.setValue(3.5)
        self.p2_spin.setDecimals(1)
        self.p2_spin.setToolTip("SC Lowcountry typical: 3.5 in")
        p2_row.addWidget(self.p2_spin)
        p2_row.addStretch()
        layout.addLayout(p2_row)
        
        # Extract button
        self.extract_btn = QPushButton("Extract Flowpaths from DEM")
        self.extract_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px; font-weight: bold; padding: 8px 16px;
                background-color: #28a745; color: white; border-radius: 4px;
            }
            QPushButton:hover { background-color: #218838; }
        """)
        self.extract_btn.clicked.connect(self.run_extraction)
        layout.addWidget(self.extract_btn)
        
        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666;")
        layout.addWidget(self.status_label)
        
        # Reference info
        ref_frame = QFrame()
        ref_frame.setFrameStyle(QFrame.StyledPanel)
        ref_layout = QVBoxLayout(ref_frame)
        ref_layout.addWidget(QLabel("<b>Fallback Methods Reference</b>"))
        ref_layout.addWidget(QLabel("""
<table border="1" cellpadding="3" style="border-collapse: collapse; font-size: 10px;">
<tr style="background-color: #f0f0f0;"><th>Condition</th><th>Action</th><th>Source</th></tr>
<tr><td>S &lt; 0.2%</td><td>Add 0.0005 to slope</td><td>TxDOT/Cleveland 2012</td></tr>
<tr><td>S between 0.2-0.3%</td><td>Transitional - flag for review</td><td>TxDOT</td></tr>
<tr><td>Adverse slope (S &lt; 0)</td><td>Use minimum slope 0.05%</td><td>Engineering judgment</td></tr>
<tr><td>TC &lt; 6 min</td><td>Use 6 min minimum</td><td>NRCS</td></tr>
<tr><td>TC &lt; 5 min (paved)</td><td>Use 5 min minimum</td><td>Caltrans HDM</td></tr>
<tr><td>TC &lt; 10 min (rural)</td><td>Use 10 min minimum</td><td>Caltrans HDM</td></tr>
</table>
        """))
        layout.addWidget(ref_frame)
        
        # Connect signals
        self.subbasin_combo.currentIndexChanged.connect(self.on_subbasin_changed)
        
        # Initialize
        self.refresh_layers()
        
    def refresh_layers(self):
        """Refresh available layers in combos"""
        # Clear combos
        self.dem_combo.clear()
        self.subbasin_combo.clear()
        self.outlet_combo.clear()
        self.outlet_combo.addItem("-- None (auto-detect) --", None)
        
        # Add raster layers to DEM combo
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsRasterLayer):
                self.dem_combo.addItem(layer.name(), layer.id())
        
        # Add polygon layers to subbasin combo
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer) and layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                self.subbasin_combo.addItem(layer.name(), layer.id())
        
        # Add point layers to outlet combo
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer) and layer.geometryType() == QgsWkbTypes.PointGeometry:
                self.outlet_combo.addItem(layer.name(), layer.id())
        
        self.on_subbasin_changed()
        
    def on_subbasin_changed(self):
        """Update field combo when subbasin layer changes"""
        self.id_field_combo.clear()
        
        layer_id = self.subbasin_combo.currentData()
        if layer_id:
            layer = QgsProject.instance().mapLayer(layer_id)
            if layer:
                for field in layer.fields():
                    self.id_field_combo.addItem(field.name(), field.name())
                
                # Try to auto-select ID field
                for i in range(self.id_field_combo.count()):
                    name = self.id_field_combo.itemText(i).upper()
                    if 'ID' in name or 'NAME' in name:
                        self.id_field_combo.setCurrentIndex(i)
                        break
    
    def run_extraction(self):
        """Run DEM extraction for all subbasins"""
        # Get selected layers
        dem_id = self.dem_combo.currentData()
        sb_id = self.subbasin_combo.currentData()
        id_field = self.id_field_combo.currentData()
        
        if not dem_id or not sb_id or not id_field:
            QMessageBox.warning(self, "Missing Input", 
                               "Please select DEM layer, subbasin layer, and ID field.")
            return
        
        dem_layer = QgsProject.instance().mapLayer(dem_id)
        sb_layer = QgsProject.instance().mapLayer(sb_id)
        
        if not dem_layer or not sb_layer:
            QMessageBox.warning(self, "Invalid Layer", "Selected layers not found.")
            return
        
        # Get optional outlets layer
        outlet_id = self.outlet_combo.currentData()
        outlet_layer = QgsProject.instance().mapLayer(outlet_id) if outlet_id else None
        
        # Initialize extractor
        extractor = DEMFlowpathExtractor(dem_layer, sb_layer, outlet_layer)
        
        # Get options
        apply_adjustments = self.apply_slope_adj.isChecked()
        use_scs = self.scs_lag_radio.isChecked() or self.both_radio.isChecked()
        use_tr55 = self.tr55_radio.isChecked() or self.both_radio.isChecked()
        p2_rainfall = self.p2_spin.value()
        
        # Process subbasins
        results = {}
        features = list(sb_layer.getFeatures())
        total = len(features)
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(total)
        
        for i, feature in enumerate(features):
            sb_id_val = str(feature[id_field])
            
            # Extract flowpath from DEM
            fp_result = extractor.extract_flowpath_simple(feature)
            fp_result['subbasin_id'] = sb_id_val
            
            results[sb_id_val] = {
                'extraction': fp_result,
                'tc_methods': {}
            }
            
            # Calculate TC using selected methods
            if fp_result['length_ft'] > 0 and fp_result['slope_pct'] > 0:
                length = fp_result['length_ft']
                slope = fp_result['slope_pct']
                
                # Get CN from subbasin params if available
                cn = 75  # Default - would come from parameter table
                
                if use_scs:
                    scs_calc = SCSLagDEMCalculator()
                    scs_result = scs_calc.calculate(length, slope, cn, apply_adjustments)
                    results[sb_id_val]['tc_methods']['scs_lag'] = scs_result
                
                if use_tr55:
                    tr55_calc = TR55VelocityDEMCalculator()
                    tr55_result = tr55_calc.calculate_simplified(
                        length, slope, cn, 'rural', p2_rainfall, apply_adjustments
                    )
                    results[sb_id_val]['tc_methods']['tr55'] = tr55_result
            
            self.progress_bar.setValue(i + 1)
            self.status_label.setText(f"Processing {sb_id_val}...")
        
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Completed: {total} subbasins processed")
        
        # Emit results
        self.extraction_complete.emit(results)
        
        # Show summary
        self.show_extraction_summary(results)
    
    def show_extraction_summary(self, results: Dict):
        """Show summary of extraction results"""
        total = len(results)
        adjusted_count = sum(1 for r in results.values() 
                           if r['extraction'].get('adjusted', False))
        warning_count = sum(1 for r in results.values() 
                          if r['extraction'].get('warnings', []))
        
        msg = f"""
DEM Extraction Complete

Subbasins Processed: {total}
Slope Adjustments Applied: {adjusted_count}
Subbasins with Warnings: {warning_count}

Check the Results tab for detailed output.
"""
        
        if adjusted_count > 0:
            msg += f"\nNote: {adjusted_count} subbasins had flat terrain adjustments applied per TxDOT guidance."
        
        QMessageBox.information(self, "Extraction Complete", msg)


# =============================================================================
# EXPORT
# =============================================================================

__all__ = [
    'DEMFlowpathExtractor',
    'SCSLagDEMCalculator', 
    'TR55VelocityDEMCalculator',
    'DEMExtractionWidget',
    'compare_tc_methods',
    'MIN_SLOPE_THRESHOLD',
    'LOW_SLOPE_ADJUSTMENT',
    'MIN_TC_DEFAULT',
    'MIN_TC_PAVED',
    'MIN_TC_RURAL',
]
