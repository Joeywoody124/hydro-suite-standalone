# Changelog

All notable changes to Hydro Suite Standalone will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

## [1.0.0] - 2025-01-31

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
| 2.0.0 | 2025-01-01 | TC Calculator rewrite, Channel Designer GIS import |
| 1.2.0 | 2025-01-01 | Example data, lookup tables, tutorials |
| 1.1.0 | 2025-01-01 | Multi-style GUI theming system |
| 1.0.0 | 2025-01-01 | Initial standalone release |

---

## Migration Notes

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
