# Changelog

All notable changes to Hydro Suite Standalone will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.5.1] - 2025-02-24

### Bug Fixes

#### CN Calculator - CRITICAL: Area Discrepancy After Intersections Fixed (v2.3)

- **FIXED: Intersection areas not matching dissolved subbasin areas**
  - Root cause: No geometry repair before/after spatial overlay operations
  - Sliver polygons and topology artifacts from input layer differences accumulated area error (observed 15+ acre discrepancies)
  - **Fix**: Added `fix_geometries()` (QGIS `native:fixgeometries`, Structure method) at three pipeline stages:
    1. After reprojection of each input layer
    2. After first intersection (land use × soils)
    3. After second intersection (subbasins × land use/soils)
  - **Additional**: Degenerate sliver features (< 1 sq ft) filtered out during CN accumulation
  - **Validation**: Reference area vs. post-intersection area logged, written to summary CSV, and shown in completion dialog

#### CN Calculator - NEW: Integer CN Output

- **Added `CN_Int` field** (rounded integer) alongside `CN_Comp` (decimal) in all outputs:
  - Shapefile: new `CN_Int` integer attribute field
  - Summary CSV: new `CN_Integer` column
  - Detailed CSV: integer CN shown in subbasin header rows
  - Summary CSV footer: area validation block (reference area, intersection area, difference)

### Technical Details
- `cn_calculator_tool.py` updated to v2.3
- New method: `fix_geometries()` — wraps `native:fixgeometries` with METHOD=1
- New method: `_calculate_total_layer_area()` — sums geometry areas for validation
- Sliver threshold: features with `area < 1.0 sq ft` skipped
- Area warning threshold: > 1% difference triggers log warning
- No changes to launch script or other tools — runner scripts remain compatible

---

## [2.5.0] - 2025-01-14

### Bug Fixes

#### TC Calculator - CRITICAL: SCS Lag Slope Units Corrected

- **FIXED: SCS Lag method was using wrong slope units**
  - Previous (INCORRECT): Converted slope from percent to ft/ft before calculation
  - Corrected: SCS Lag uses slope in PERCENT directly per NRCS NEH Part 630, Chapter 15
  - **Impact**: Previous versions produced TC values approximately 10x too high
  - Example: Area with L=902 ft, S=0.93%, CN=63 previously calculated 492 min, now correctly calculates ~46 min

- **Root Cause**: The original code had:
  ```python
  slope_ftft = slope_percent / 100.0
  lag_hours = ... / (1900.0 * (slope_ftft ** 0.5))
  ```
  This incorrectly divided by sqrt(0.0093) instead of sqrt(0.93)

- **Corrected Code**: Now uses slope_percent directly:
  ```python
  lag_hours = ... / (1900.0 * (slope_percent ** 0.5))
  ```

- **Added**: Comprehensive docstring to SCSLagMethod class documenting:
  - Reference citation (NRCS NEH Part 630, Chapter 15)
  - Complete equation with variable definitions
  - Explicit note that Y (slope) is in PERCENT, not ft/ft

### Reference
- NRCS NEH Part 630, Chapter 15: Time of Concentration (2010)
- Equation: Lag (hours) = (L^0.8 × S^0.7) / (1900 × Y^0.5)
  - L = hydraulic length (feet)
  - S = (1000/CN) - 9 = maximum retention (inches)
  - Y = average watershed slope in PERCENT

### Verification
Test case (Area 1 from user data):
- Input: L=902 ft, Y=0.93%, CN=63
- Storage: S = (1000/63) - 9 = 6.87
- Lag = (902^0.8 × 6.87^0.7) / (1900 × 0.93^0.5) = 0.456 hours
- Tc = 0.456 / 0.6 = 0.76 hours = **45.6 minutes** ✓

---

## [2.4.0] - 2025-01-08

### Major Changes

#### TC Calculator - DEM Extraction Mode Fully Integrated (v2.4)

- **NEW: DEM Extraction Mode in TC Calculator GUI**
  - Third calculation mode alongside Flowpath and Manual Entry
  - Dedicated panel with DEM layer selector, subbasin layer selector, and field mapping
  - No hardcoded values - all parameters are user-configurable

- **NEW: Dynamic Layer and Field Selection**
  - DEM Raster selector - picks from all raster layers in project
  - Subbasin Polygon selector - picks from all polygon layers in project
  - Field mapping combos auto-populate based on selected layer
  - Auto-detection of common field names (ID, CN, etc.)
  - Real-time DEM info display (CRS, size, extent)

- **NEW: Configurable Default Parameters**
  - Default CN: 75 (adjustable 30-98)
  - Default C: 0.30 (adjustable 0.05-0.95)
  - Default n: 0.40 (adjustable 0.01-0.80)
  - P2 Rainfall: 3.5 in (adjustable 1.0-10.0)

- **NEW: Fallback When DEM Extraction Fails**
  - Uses geometric centroid-to-boundary method
  - Bounding box diagonal for length estimation
  - Conservative 0.2% slope as fallback
  - Full warning logging for transparency

- **ENHANCED: Results Display for DEM Mode**
  - Shows adjustment status (Yes/No) with yellow highlighting
  - Shows warnings with tooltips for full details
  - Summary shows count of adjusted subbasins

- **ENHANCED: CSV Output for DEM Mode**
  - Main output includes high/low elevations, adjustment status, warnings
  - New `tc_dem_extraction_summary.csv` with full extraction details
  - All warnings captured for review

### Technical Details
- `tc_calculator_tool.py` - v2.4 with MODE_DEM constant and `calculate_dem_mode()` method
- Full integration with `dem_extraction.py` module
- `HAS_DEM_EXTRACTION` flag for graceful handling when module unavailable
- `refresh_dem_layers()`, `on_dem_changed()`, `on_dem_subbasin_changed()` methods
- Updated `validate_and_update()`, `validate_inputs()`, `create_outputs()`, `show_completion_dialog()`

### Use Cases
- **No flowpath layer available**: Use DEM to extract length/slope automatically
- **Preliminary analysis**: Quick TC estimates from DEM without digitizing
- **Flat terrain**: Automatic fallback methods prevent unrealistic TC values
- **Field data verification**: Compare DEM-extracted vs field-measured values

---

## [2.3.0] - 2025-01-02

### Major Changes

#### TC Calculator - DEM Extraction Module Added (v2.3)
- **NEW: DEM-Based Flowpath Extraction**
  - Automatically extract flowpath length and slope from DEM for each subbasin
  - Uses elevation sampling to find high/low points within each subbasin
  - No pre-digitized flowpath layer required
  - Supports optional outlet points layer for precise outlet locations

- **NEW: Industry-Standard Flat Terrain Fallback Methods**
  - Based on TxDOT/Cleveland et al. 2012 research
  - Automatic slope adjustment when S < 0.2% (adds 0.0005)
  - Transitional slope warning when 0.2% ≤ S < 0.3%
  - Adverse slope handling (S < 0) uses minimum 0.05%
  - Minimum TC enforcement: 6 min (default), 5 min (paved), 10 min (rural)

- **NEW: SCS Lag Method with DEM Parameters**
  - Formula: Lag = (L^0.8 × S_retention^0.7) / (1900 × Y^0.5)
  - Valid range warnings per NRCS WinTR-55:
    - CN: 50-95
    - Slope: 0.5%-64%
    - Length: 200-26,000 ft
  - Automatic conversion to TC: Tc = Lag / 0.6

- **NEW: TR-55 Simplified Method**
  - Estimates flow types from land use category
  - Sheet flow (first 100 ft) + shallow concentrated + channel
  - Uses land-use-appropriate Manning's n values

- **NEW: DEM Extraction Widget**
  - Integrated GUI for DEM extraction workflow
  - Layer/field selectors for DEM, subbasins, outlets
  - Adjustment toggles with explanatory tooltips
  - Progress indicator with subbasin-by-subbasin status
  - Reference table showing fallback method thresholds

### New Files
- `dem_extraction.py` - Complete DEM extraction module with:
  - `DEMFlowpathExtractor` class for length/slope extraction
  - `SCSLagDEMCalculator` class for SCS Lag with adjustments
  - `TR55VelocityDEMCalculator` class for simplified TR-55
  - `DEMExtractionWidget` GUI component
  - `apply_slope_adjustment()` and `apply_tc_minimum()` functions
  - Industry-standard constants and thresholds

### Technical Details
- New constants for flat terrain handling:
  - `MIN_SLOPE_THRESHOLD = 0.002` (0.2%)
  - `TRANSITIONAL_SLOPE_UPPER = 0.003` (0.3%)
  - `LOW_SLOPE_ADJUSTMENT = 0.0005`
  - `MIN_TC_PAVED = 5.0` minutes
  - `MIN_TC_RURAL = 10.0` minutes
  - `MIN_TC_DEFAULT = 6.0` minutes
- SCS Lag valid range constants per NRCS WinTR-55
- Coordinate transformation handling for DEM/subbasin CRS differences

### References Added
- TR-55: Urban Hydrology for Small Watersheds (USDA-SCS, 1986)
- NEH Part 630, Chapter 15: Time of Concentration (NRCS, 2010)
- TxDOT Hydraulic Design Manual, Chapter 4 (2023)
- Cleveland et al. 2012: Time of Concentration for Low-Slope Watersheds
- Iowa DNR WinTR-55 Procedures
- California Highway Design Manual Section 816

### Use Cases
- **Preliminary analysis**: Extract L/S from DEM without digitizing flowpaths
- **Flat terrain (SC Lowcountry)**: Automatic fallback adjustments prevent unrealistic TCs
- **Quick estimates**: DEM extraction + SCS Lag for rapid watershed assessment
- **Method comparison**: Run multiple methods to bracket TC estimates

---

## [2.2.0] - 2025-01-01

### Major Changes

#### TC Calculator - Manual Entry Mode Added (v2.2)
- **NEW: Two Calculation Modes**
  - **Flowpath Layer Mode**: TR-55 segment-based + comparison methods (requires flowpath layer)
  - **Manual Entry Mode**: Comparison methods only (NO flowpath layer required)
- **NEW: Manual Entry Table**
  - Add/remove subbasins directly
  - Enter Length, Slope, CN, C, Manning's n per subbasin
  - CSV import/export for saving/loading manual data
- **NEW: Per-Subbasin Parameters Tab**
  - Set custom CN (SCS Lag), C (FAA), and n (Kerby) per subbasin
  - CSV import/export for batch parameter loading
- **NEW: Per-Subbasin Channel Geometry Tab**
  - Define channel depth, width, side slope per subbasin
  - Define pipe diameter per subbasin
  - Global defaults with per-subbasin overrides
  - Automatic hydraulic radius calculation
- **NEW: Validation Script**
  - `validation_calculations.py` - Hand calculations for verification
  - Run in QGIS Console to verify tool outputs

### Technical Details
- `tc_calculator_tool.py` - v2.2 with mode selection and manual entry
- `validation_calculations.py` - New file for hand calculation verification
- Added `ManualEntryTable` widget class
- Added `ChannelGeometryTable` widget class
- Enhanced `SubbasinParametersTable` widget class

### Use Cases
- **With flowpath layer**: Full TR-55 analysis + comparison methods
- **Without flowpath layer**: Quick estimates using comparison methods only
- **Preliminary analysis**: Use Manual Entry for early project phases
- **Final analysis**: Use Flowpath Layer mode with detailed segment data

---

## [2.0.0] - 2025-01-01

### Major Changes

#### TC Calculator - Complete Rewrite (v2.0)
- **NEW: Flowpaths Layer Input** - Uses TR-55 style segment-based travel times
  - Supports flow types: SHEET, SHALLOW_CONC, CHANNEL, PIPE
  - Groups segments by Subbasin_ID for automatic aggregation
  - Properly calculates travel time per flow type per TR-55
- **FIXED: DEM Selector Bug** - Removed broken raster layer selector (was showing vector layers only)
- **NEW: Field Mapping UI** - Map your layer fields to required inputs
- **NEW: Segment Detail Output** - CSV with individual segment travel times
- **Comparison Methods** - Kirpich, FAA, SCS Lag, Kerby available for validation
- **Parameters Tab** - Configure 2-yr rainfall, hydraulic radius, method-specific values

#### Channel Designer - Enhanced (v2.0)
- **NEW: GIS Layer Import Tab** - Import channels directly from vector layers
  - Works with `sample_channels.gpkg` and similar layers
  - Field mapping for depth, width, slope, Manning's n
  - Auto-detects common field names
- **NEW: Capacity Calculation** - Manning's equation for flow capacity (Q)
  - Added Manning's n and channel slope inputs
  - Results now show Velocity (fps) and Capacity (cfs)
- **Enhanced Results Table** - Added velocity and capacity columns
- **Enhanced CSV Export** - Includes all hydraulic properties

### Fixed
- TC Calculator no longer shows vector layers in DEM selector (was a bug)
- TC Calculator now properly implements TR-55 segment-based methodology
- Channel Designer can now import from GIS layers (previously CSV only)

### Technical Details
- `tc_calculator_tool.py` - Complete rewrite with SegmentTravelTimeCalculator class
- `channel_designer_tool.py` - Added GIS import tab and capacity calculations
- Both tools now v2.0

---

## [1.2.0] - 2025-01-01

### Added
- **Example Data Package**
  - `create_sample_layers.py` - GIS layer generator for testing
  - 6 GeoPackage layers: subbasins, landuse, soils, flowpaths, channels, outlets
  - All layers spatially aligned (SC State Plane EPSG:2273)
  - Sample soils include standard and dual HSG (A/D, B/D)
- **Lookup Tables (Corrected Formats)**
  - `cn_lookup_table.csv` - 39 land use types with HSG columns (a, b, c, d)
  - `c_lookup_table.csv` - 31 land use types with slope+HSG columns (a_0-2%, a_2-6%, etc.)
  - `cn_lookup_split_hsg.csv` - CN with dual HSG support
- **Documentation**
  - `TUTORIALS.md` - Step-by-step tutorials for each tool
  - `HANDOFF.md` - Session handoff document for continuity
  - Updated `README.md` with example data section

### Fixed
- CN lookup table format (columns: landuse, a, b, c, d)
- Rational C lookup table format (columns: landuse, a_0-2%, a_2-6%, a_6%+, b_0-2%, etc.)

### Tested
- CN Calculator - full workflow with sample data ✅
- Rational C Calculator - full workflow with sample data ✅
- Sample layer generation script ✅

---

## [1.1.0] - 2025-01-01

### Added
- **Multi-Style GUI Theming System**
  - Runtime style switching via toolbar dropdown
  - 9 built-in themes:
    - Normal (Default) - Classic light theme
    - Kinetic (Dark) - High-energy brutalist dark theme
    - Bauhaus (Light) - Geometric modernist light theme
    - Enterprise (Light) - Corporate SaaS light theme
    - Cyberpunk (Dark) - Neon dystopian dark theme
    - Academia (Dark) - Scholarly classical dark theme
    - Sketch (Light) - Hand-drawn playful light theme
    - Playful Geometric (Light) - Memphis bouncy light theme
    - Twisty (Dark) - Fintech modern dark theme
  - Style preference persists between sessions
  - Also accessible via View > GUI Style menu
- `style_loader.py` - New module for loading and applying GUI themes
- Integrated with GUI Design Center Library for token-based styling

### Changed
- Updated `hydro_suite_main.py` to version 1.1 with style system
- Updated `launch_hydro_suite.py` to load style_loader module
- Default theme changed to Kinetic (Dark)
- Status bar now shows current style name

### Technical
- StyleLoader class handles JSON token parsing
- Automatic stylesheet generation for all PyQt5 widgets
- Graceful fallback to Normal style if theme files missing

---

## [1.0.0] - 2025-01-01

### Added
- Initial standalone release (non-plugin version for QGIS Python Console)
- **Curve Number (CN) Calculator**
  - Multi-layer intersection (subbasins x land use x soils)
  - Split HSG handling (A/D, B/D, C/D)
  - CSV/Excel lookup table support
  - SWMM/HEC-HMS compatible outputs
- **Rational C Calculator**
  - Slope-based C value determination (0-2%, 2-6%, 6%+)
  - Project-wide slope category selection
  - Unrecognized soil group handling
  - Professional reporting formats
- **Time of Concentration (TC) Calculator**
  - Kirpich (1940) method
  - FAA (1965) method
  - SCS/NRCS (1972) method
  - Kerby method
  - Multi-method comparison
- **Channel Designer**
  - Interactive trapezoidal channel visualization
  - Real-time hydraulic property calculations
  - SWMM-compatible output format
  - Batch processing from CSV
- Core Framework
  - `launch_hydro_suite.py` - Single-file launcher for QGIS Console
  - `hydro_suite_main.py` - Main controller and GUI window
  - `hydro_suite_interface.py` - Base classes and interfaces
  - `shared_widgets.py` - Reusable UI components
- Documentation
  - README.md with quick start guide
  - DEVELOPER_GUIDE.md for extending the framework
  - CONTRIBUTING.md for contribution guidelines

### Notes
- This is the standalone script version designed to run in QGIS Python Console
- The plugin version (hydro-suite) is available separately but currently needs fixes
- Tested with QGIS 3.40+

---

## [Unreleased]

### Planned
- Watershed delineation tool
- Storm event analysis
- Additional TC methods
- Export to HEC-HMS format
- Report generation
- Custom theme editor

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 2.5.1 | 2025-02-24 | CN Calculator area fix, geometry repair, integer CN output |
| 2.5.0 | 2025-01-14 | TC Calculator SCS Lag slope units corrected |
| 2.4.0 | 2025-01-08 | TC Calculator DEM Extraction fully integrated into GUI |
| 2.3.0 | 2025-01-02 | DEM Extraction module created (dem_extraction.py) |
| 2.2.0 | 2025-01-01 | TC Calculator Manual Entry Mode (no flowpath layer required) |
| 2.0.0 | 2025-01-01 | TC Calculator rewrite, Channel Designer GIS import |
| 1.2.0 | 2025-01-01 | Example data, lookup tables, tutorials |
| 1.1.0 | 2025-01-01 | Multi-style GUI theming system |
| 1.0.0 | 2025-01-01 | Initial standalone release |

---

## Migration Notes

### From v2.0 to v2.2

**TC Calculator Changes:**
- New mode selector at top of Configuration tab
- "Flowpath Layer Mode" = same as v2.0 behavior
- "Manual Entry Mode" = NEW - no flowpath layer needed
- Subbasin Parameters and Channel Geometry tabs only used in Flowpath Mode

### From v1.x to v2.0

**TC Calculator Changes:**
- The DEM input has been removed (was non-functional)
- Now requires a flowpaths layer with pre-calculated segment data
- Use `sample_flowpaths.gpkg` from example data as template
- Required fields: Subbasin_ID, Length_ft, Slope_Pct, Mannings_n, Flow_Type

**Channel Designer Changes:**
- New "Import from Layer" tab added
- Can now import directly from GIS layers like `sample_channels.gpkg`
- Results table now shows velocity and capacity

### From Plugin to Standalone

If migrating from the plugin version:
1. The standalone version uses flat file structure (no subdirectories)
2. Launch via Python Console exec() instead of plugin menu
3. All functionality is preserved
4. Settings may need to be reconfigured

---

**Author**: Joey Woody, PE - J. Bragg Consulting Inc.
