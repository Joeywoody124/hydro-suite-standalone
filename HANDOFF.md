# HANDOFF: Hydro Suite Standalone - v2.5.0

**Date**: February 2025
**Author**: Joey Woody, PE - J. Bragg Consulting Inc.
**Status**: ✅ UPDATED - CN Calculator Area Fix + Integer CN Output
**Repository**: https://github.com/Joeywoody124/hydro-suite-standalone

---

## Current State Summary

Hydro Suite Standalone is a QGIS Python Console-based hydrological analysis toolbox. Version 2.5.0 fixes area discrepancy issues in the CN Calculator by adding geometry repair steps after every spatial operation and provides CN results in both decimal and integer formats.

### What's Working

| Component | Status | Notes |
|-----------|--------|-------|
| Main GUI Framework | ✅ Working | Launches via `launch_hydro_suite.py` |
| Style/Theme System | ✅ Working | 9 themes, toolbar selector, persistence |
| CN Calculator | ✅ **v2.3** | Area fix, geometry repair, integer CN output |
| Rational C Calculator | ✅ Working | Tested with sample data |
| TC Calculator | ✅ **v2.4** | Three modes: Flowpath, Manual, or DEM Extraction |
| Channel Designer | ✅ **v2.0** | Added GIS layer import |
| DEM Extraction Module | ✅ **Integrated** | Now part of TC Calculator |
| Validation Script | ✅ Working | Hand calculations for verification |

---

## Version 2.5.0 Changes (CN Calculator Area Fix + Integer CN)

### Bug Fixes

#### CN Calculator - CRITICAL: Area Discrepancy After Intersections Fixed

- **FIXED: Areas not summing correctly after intersection operations**
  - Previous behavior: intersection results carried geometric artifacts (slivers, self-intersections) from input layer topology differences, inflating or deflating summed areas by up to 15+ acres
  - Root cause: no geometry repair was performed before or after intersection operations; sliver polygons from overlay misalignment accumulated area error
  - **Fix applied**: Added `fix_geometries()` step using QGIS `native:fixgeometries` (Structure method) at three points:
    1. After reprojection of each input layer (before any intersection)
    2. After the first intersection (land use × soils)
    3. After the second intersection (subbasins × land use/soils)
  - **Additional fix**: Degenerate sliver features (< 1 sq ft) are now filtered out during CN calculation to prevent micro-polygon accumulation
  - **Area validation**: Reference subbasin area vs. post-intersection area is now logged, reported in the summary CSV footer, and displayed in the completion dialog with a percentage difference

#### CN Calculator - NEW: Integer CN Output

- **Added `CN_Int` field** (integer, rounded) alongside existing `CN_Comp` (decimal) in:
  - Output shapefile (`subbasins_cn.shp`) — new attribute field
  - Detailed CSV (`cn_calculations_detailed.csv`) — new column per subbasin header
  - Summary CSV (`cn_summary.csv`) — new `CN_Integer` column
- Both values derived from the same area-weighted calculation: `CN_Comp` is the raw decimal, `CN_Int` is `round(CN_Comp)`

### Processing Pipeline (Updated)

The CN calculation now follows this sequence:

```
1. Load & validate inputs
2. Reproject all layers to EPSG:3361
3. ** Fix geometries on all three reprojected layers **
4. Log reference area (sum of subbasin geometries)
5. Intersect land use × soils
6. ** Fix geometries on intersection result **
7. Intersect subbasins × (land use/soils)
8. ** Fix geometries on final intersection **
9. Log post-intersection area + diff vs reference
10. Calculate composite CN (skip slivers < 1 sq ft)
11. Write outputs with CN_Comp + CN_Int + area validation
```

Steps marked with ** are new in v2.5.0.

### Output Changes

**Shapefile fields (subbasins_cn.shp):**
| Field | Type | Description |
|-------|------|-------------|
| CN_Comp | Double (10,2) | Area-weighted composite CN (decimal) |
| CN_Int | Integer (5,0) | Rounded composite CN |
| Area_acres | Double (15,2) | Total area from intersection (acres) |

**Summary CSV (cn_summary.csv):**
- New column: `CN_Integer`
- New footer section: Area Validation block with reference area, intersection area, difference in acres and percent

**Detailed CSV (cn_calculations_detailed.csv):**
- Subbasin header rows now include both `Composite CN (decimal)` and `Composite CN (integer)`

---

## File Structure

```
github_standalone/
├── launch_hydro_suite.py      # Entry point
├── hydro_suite_main.py        # Main window
├── hydro_suite_interface.py   # Base classes
├── shared_widgets.py          # Reusable GUI components
├── style_loader.py            # Theme system
├── cn_calculator_tool.py      # **v2.3** CN calculator (area fix + integer CN)
├── rational_c_tool.py         # Rational C calculator
├── tc_calculator_tool.py      # **v2.4** TC calculator (3 modes)
├── dem_extraction.py          # DEM extraction module
├── channel_designer_tool.py   # Channel designer v2.0
├── validation_calculations.py # Hand calculation verification
├── example_data/              # Sample data and lookup tables
├── README.md
├── CHANGELOG.md
├── HANDOFF.md                 # This file
└── ...
```

---

## CN Calculator v2.3 Technical Details

### Geometry Repair Method

Uses `native:fixgeometries` with `METHOD=1` (Structure method), which:
- Repairs self-intersections
- Removes duplicate vertices
- Fixes ring orientation
- Eliminates topology errors that cause area inflation

### Sliver Filtering

Features with `geometry().area() < 1.0` sq ft (< 0.00002 acres) are skipped during CN accumulation. These are artifacts of overlay operations where polygon boundaries nearly coincide but not exactly.

### Area Validation

The tool computes:
- **Reference area**: Sum of all subbasin polygon areas before intersection
- **Intersection area**: Sum of all final intersection polygon areas after geometry repair
- **Difference**: Logged to progress, written to summary CSV footer, shown in completion dialog
- **Threshold**: Warning issued if difference exceeds 1% of reference area

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

### Mode C: DEM Extraction Mode

1. Select "DEM Extraction Mode" radio button
2. Select DEM raster layer from project
3. Select Subbasins polygon layer from project
4. Map fields dynamically (ID, CN, Land Type)
5. Set default parameters (CN, C, n, P2 Rainfall)
6. Configure adjustment options
7. Click "Calculate TC"
8. Review results — adjusted values shown in yellow with tooltips
9. Check output CSV files for full details and warnings

---

## Comparison Methods (All TC Modes)

| Method | Formula | Requires |
|--------|---------|----------|
| **Kirpich** | tc = 0.0078 × L^0.77 / S^0.385 | L, S only |
| **FAA** | tc = 1.8 × (1.1-C) × L^0.5 / S^0.33 | L, S, C |
| **SCS Lag** | Lag = (L^0.8 × ((1000/CN)-9)^0.7) / (1900 × S^0.5) | L, S, CN |
| **Kerby** | tc = 1.44 × (n×L)^0.467 / S^0.235 | L, S, n |

Where: L = length (ft), S = slope (% for SCS Lag, ft/ft for others), C = runoff coefficient, CN = curve number, n = Manning's n

---

## How to Launch

```python
# In QGIS Python Console:
exec(open(r'E:\CLAUDE_Workspace\Claude\Report_Files\Finished_Code\Hydro_Suite_Data_Backup_v1\github_standalone\launch_hydro_suite.py').read())
```

---

## Testing Checklist

### CN Calculator v2.3
- [ ] Run with sample data — verify CN_Comp and CN_Int in shapefile
- [ ] Check cn_summary.csv for CN_Integer column and area validation footer
- [ ] Compare reference area vs intersection area (should be < 1% difference)
- [ ] Test with real project data — confirm area discrepancy is resolved
- [ ] Verify sliver filtering log message appears when slivers exist
- [ ] Test with split HSG soils (A/D, B/D, C/D)

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

1. **CN Area Validation**: Small differences (< 1%) between reference and intersection areas are normal due to floating-point precision in polygon overlay operations. Differences > 1% typically indicate input layer topology issues (overlapping polygons, gaps).

2. **DEM Extraction**: Uses simplified centroid-to-boundary approach. More sophisticated flow path tracing would require QGIS Processing tools. Current method good for preliminary analysis.

3. **Flat Terrain**: TC adjustments are conservative. May overestimate TC in very flat areas. Always review flagged results.

4. **SCS Lag Limits**: NRCS recommends alternative methods when:
   - CN < 50 or > 95
   - Slope < 0.5% or > 64%
   - Length < 200 ft or > 26,000 ft

---

## References

1. **TR-55**: Urban Hydrology for Small Watersheds (USDA-SCS, 1986)
2. **NEH Part 630, Chapter 15**: Time of Concentration (NRCS, 2010)
3. **TxDOT Hydraulic Design Manual**, Chapter 4 (2023)
4. **Cleveland et al. 2012**: Time of Concentration for Low-Slope Watersheds
5. **Iowa DNR**: WinTR-55 Procedures
6. **California Highway Design Manual**: Section 816

---

## Contact

Joey Woody, PE
J. Bragg Consulting Inc.
Civil/Water Resources Engineer
