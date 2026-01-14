# HANDOFF: Hydro Suite Standalone - v2.4.0

**Date**: January 2025
**Author**: Joey Woody, PE - J. Bragg Consulting Inc.
**Status**: ✅ UPDATED - DEM Extraction Mode Fully Integrated
**Repository**: https://github.com/Joeywoody124/hydro-suite-standalone

---

## Current State Summary

Hydro Suite Standalone is a QGIS Python Console-based hydrological analysis toolbox. Version 2.4.0 **fully integrates DEM-based flowpath extraction** into the TC Calculator with industry-standard fallback methods for flat terrain.

### What's Working

| Component | Status | Notes |
|-----------|--------|-------|
| Main GUI Framework | ✅ Working | Launches via `launch_hydro_suite.py` |
| Style/Theme System | ✅ Working | 9 themes, toolbar selector, persistence |
| CN Calculator | ✅ Working | Tested with sample data |
| Rational C Calculator | ✅ Working | Tested with sample data |
| TC Calculator | ✅ **v2.4** | Three modes: Flowpath, Manual, or DEM Extraction |
| Channel Designer | ✅ **v2.0** | Added GIS layer import |
| DEM Extraction Module | ✅ **Integrated** | Now part of TC Calculator |
| Validation Script | ✅ Working | Hand calculations for verification |

---

## Version 2.4.0 Changes (DEM Extraction Fully Integrated)

### Three Calculation Modes

| Mode | Input Required | Output |
|------|----------------|--------|
| **Flowpath Layer Mode** | Flowpath layer with segments | TR-55 segment TC + comparison methods |
| **Manual Entry Mode** | None (enter data directly) | Comparison methods only |
| **DEM Extraction Mode** | DEM raster + Subbasins polygon layer | Auto-extracted L/S + all comparison methods |

### v2.4.0 DEM Extraction Features
- **Fully integrated into TC Calculator GUI** with dedicated mode panel
- **DEM layer selector** - pick any raster DEM from project
- **Subbasin layer selector** - select polygon layer containing subbasins
- **Field mapping** - map ID, CN, and land type fields dynamically (no hardcoding)
- **Automatic flowpath extraction** from DEM for each subbasin
- **Elevation sampling** to determine high/low points
- **Industry-standard flat terrain fallbacks** (see below)
- **Fallback when DEM fails** - uses geometric centroid-to-boundary method
- **Adjustable default parameters** - CN, C, n, P2 rainfall
- **Real-time validation** - shows DEM info, validates selections
- **Results display** with adjustment status and warnings
- **CSV export** includes DEM extraction details and warnings

### Flat Terrain Fallback Methods

Based on TxDOT/Cleveland et al. 2012 and NRCS guidance:

| Condition | Threshold | Action | Source |
|-----------|-----------|--------|--------|
| Low slope | S < 0.2% | Add 0.0005 to slope | TxDOT/Cleveland 2012 |
| Transitional slope | 0.2% ≤ S < 0.3% | Flag for review | TxDOT |
| Adverse slope | S < 0 | Use minimum 0.05% | Engineering judgment |
| Very short TC | TC < 6 min | Use 6 min minimum | NRCS |
| Short TC (paved) | TC < 5 min | Use 5 min minimum | Caltrans HDM |
| Short TC (rural) | TC < 10 min | Use 10 min minimum | Caltrans HDM |

### SCS Lag Method Valid Ranges (per NRCS WinTR-55)

| Parameter | Minimum | Maximum | Notes |
|-----------|---------|---------|-------|
| CN | 50 | 95 | Outside range: results unreliable |
| Slope | 0.5% | 64% | Use alternative procedure if outside |
| Length | 200 ft | 26,000 ft | Use WinTR-20 if > 26,000 ft |

---

## File Structure

```
github_standalone/
├── launch_hydro_suite.py      # Entry point
├── hydro_suite_main.py        # Main window
├── hydro_suite_interface.py   # Base classes
├── shared_widgets.py          # Reusable GUI components
├── style_loader.py            # Theme system
├── cn_calculator_tool.py      # Curve Number calculator
├── rational_c_tool.py         # Rational C calculator  
├── tc_calculator_tool.py      # **v2.3** TC calculator (3 modes)
├── dem_extraction.py          # **NEW** DEM extraction module
├── channel_designer_tool.py   # Channel designer v2.0
├── validation_calculations.py # Hand calculation verification
├── example_data/              # Sample data and lookup tables
├── README.md
├── CHANGELOG.md
├── HANDOFF.md                 # This file
└── ...
```

---

## DEM Extraction Module (dem_extraction.py)

### Classes

| Class | Purpose |
|-------|---------|
| `DEMFlowpathExtractor` | Extract length/slope from DEM for subbasins |
| `SCSLagDEMCalculator` | SCS Lag TC with DEM-extracted parameters |
| `TR55VelocityDEMCalculator` | TR-55 Simplified with estimated flow types |
| `DEMExtractionWidget` | GUI widget for DEM extraction mode |

### Key Functions

```python
# Apply low-slope adjustment
apply_slope_adjustment(slope_ftft) -> (adjusted_slope, was_adjusted, warning)

# Apply minimum TC
apply_tc_minimum(tc_minutes, land_type) -> (adjusted_tc, was_adjusted, warning)

# Compare multiple TC methods
compare_tc_methods(length_ft, slope_pct, cn, land_type, p2_rainfall) -> dict
```

### Constants

```python
MIN_SLOPE_THRESHOLD = 0.002    # 0.2% - below this, apply adjustment
LOW_SLOPE_ADJUSTMENT = 0.0005  # Add to slope when S < 0.2%
MIN_TC_PAVED = 5.0            # minutes
MIN_TC_RURAL = 10.0           # minutes
MIN_TC_DEFAULT = 6.0          # minutes
```

---

## TC Calculator v2.4 Usage

### Mode A: Flowpath Layer Mode

Requires flowpath layer with: Subbasin_ID, Length_ft, Slope_Pct, Mannings_n, Flow_Type

### Mode B: Manual Entry Mode

Enter subbasin data directly in table: ID, Length, Slope, CN, C, n

### Mode C: DEM Extraction Mode (ENHANCED in v2.4)

1. Select "DEM Extraction Mode" radio button
2. **Select DEM raster layer** from project (CRS info displayed automatically)
3. **Select Subbasins polygon layer** from project
4. **Map fields dynamically:**
   - Subbasin ID Field (required)
   - CN Field (optional - uses default if not mapped)
   - Land Type Field (optional - uses 'rural' default if not mapped)
5. **Set default parameters:**
   - Default CN: 75 (used when field not mapped or value missing)
   - Default C: 0.30
   - Default n: 0.40
   - P2 Rainfall: 3.5 in (for TR-55)
6. **Configure adjustment options:**
   - ☑ Apply TxDOT low-slope adjustment (add 0.0005 when S < 0.2%)
   - ☑ Apply minimum TC (6 min default, 5 min paved, 10 min rural)
7. Click "Calculate TC" button
8. Review results - adjusted values shown in yellow with tooltips
9. Check output CSV files for full details and warnings

**Output Files (DEM Mode):**
- tc_calculations.csv - Summary with elevations and adjustments
- tc_dem_extraction_summary.csv - Detailed extraction results and warnings

---

## Comparison Methods (All Modes)

| Method | Formula | Requires |
|--------|---------|----------|
| **Kirpich** | tc = 0.0078 × L^0.77 / S^0.385 | L, S only |
| **FAA** | tc = 1.8 × (1.1-C) × L^0.5 / S^0.33 | L, S, C |
| **SCS Lag** | Lag = (L^0.8 × ((1000/CN)-9)^0.7) / (1900 × S^0.5) | L, S, CN |
| **Kerby** | tc = 1.44 × (n×L)^0.467 / S^0.235 | L, S, n |

Where: L = length (ft), S = slope (ft/ft), C = runoff coefficient, CN = curve number, n = Manning's n

---

## References

1. **TR-55**: Urban Hydrology for Small Watersheds (USDA-SCS, 1986)
2. **NEH Part 630, Chapter 15**: Time of Concentration (NRCS, 2010)
3. **TxDOT Hydraulic Design Manual**, Chapter 4 (2023)
4. **Cleveland et al. 2012**: Time of Concentration for Low-Slope Watersheds
5. **Iowa DNR**: WinTR-55 Procedures
6. **California Highway Design Manual**: Section 816

---

## How to Launch

```python
# In QGIS Python Console:
exec(open(r'E:\CLAUDE_Workspace\Claude\Report_Files\Finished_Code\Hydro_Suite_Data_Backup_v1\github_standalone\launch_hydro_suite.py').read())
```

---

## Testing Checklist

### DEM Extraction Mode
- [ ] Load DEM and subbasins layers
- [ ] Run extraction with flat terrain (test adjustments)
- [ ] Run extraction with normal terrain
- [ ] Verify SCS Lag results against hand calculations
- [ ] Verify TR-55 Simplified results
- [ ] Test with adverse slopes (DEM errors)
- [ ] Verify minimum TC enforcement

### Integration
- [ ] Mode switching works correctly
- [ ] Results table displays adjustment warnings
- [ ] CSV export includes adjustment flags
- [ ] Validation script matches tool output

---

## Known Limitations

1. **DEM Extraction**: Uses simplified centroid-to-boundary approach
   - More sophisticated flow path tracing would require QGIS Processing tools
   - Current method good for preliminary analysis

2. **Flat Terrain**: Adjustments are conservative
   - May overestimate TC in very flat areas
   - Always review flagged results

3. **SCS Lag Limits**: NRCS recommends alternative methods when:
   - CN < 50 or > 95
   - Slope < 0.5% or > 64%
   - Length < 200 ft or > 26,000 ft

---

## Next Steps

1. **Test DEM extraction** with sample data
2. **Validate flat terrain adjustments** against known cases
3. **Push updates** to GitHub repository
4. **Create tutorial** for DEM extraction workflow

---

## Contact

Joey Woody, PE  
J. Bragg Consulting Inc.  
Civil/Water Resources Engineer
