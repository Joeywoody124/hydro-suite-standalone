# HANDOFF: Hydro Suite Standalone - v2.0.0

**Date**: January 2025  
**Author**: Joey Woody, PE - J. Bragg Consulting Inc.  
**Status**: ✅ UPDATED - Major Tool Improvements  
**Repository**: https://github.com/Joeywoody124/hydro-suite-standalone

---

## Current State Summary

Hydro Suite Standalone is a QGIS Python Console-based hydrological analysis toolbox. Version 2.0.0 includes major improvements to the TC Calculator and Channel Designer tools.

### What's Working

| Component | Status | Notes |
|-----------|--------|-------|
| Main GUI Framework | ✅ Working | Launches via `launch_hydro_suite.py` |
| Style/Theme System | ✅ Working | 9 themes, toolbar selector, persistence |
| CN Calculator | ✅ Working | Tested with sample data |
| Rational C Calculator | ✅ Working | Tested with sample data |
| TC Calculator | ✅ **v2.0** | Rewritten with flowpaths layer support |
| Channel Designer | ✅ **v2.0** | Added GIS layer import |
| Sample GIS Layers | ✅ Working | Generated via `create_sample_layers.py` |
| Lookup Tables | ✅ Working | CN and C tables validated |

### Version 2.0.0 Changes

#### TC Calculator (Complete Rewrite)
- **Fixed:** Removed broken DEM selector (was showing vector layers instead of raster)
- **New:** Flowpaths layer input with TR-55 segment-based methodology
- **New:** Supports flow types: SHEET, SHALLOW_CONC, CHANNEL, PIPE
- **New:** Automatic grouping by Subbasin_ID
- **New:** Segment detail CSV output
- **New:** Comparison methods (Kirpich, FAA, SCS Lag, Kerby) for validation

#### Channel Designer (Enhanced)
- **New:** "Import from Layer" tab for GIS layer import
- **New:** Field mapping UI for flexible layer support
- **New:** Manning's equation capacity calculation (Q, velocity)
- **New:** Enhanced results table with hydraulic properties
- **New:** Enhanced CSV export with all properties

---

## File Structure

```
github_standalone/
├── launch_hydro_suite.py      # Entry point - run this in QGIS console
├── hydro_suite_main.py        # Main window, menus, toolbar, style selector
├── hydro_suite_interface.py   # Base classes for tools
├── shared_widgets.py          # Reusable GUI components
├── style_loader.py            # Theme system (9 styles)
├── cn_calculator_tool.py      # Curve Number calculator
├── rational_c_tool.py         # Rational C calculator  
├── tc_calculator_tool.py      # **v2.0** Time of Concentration calculator
├── channel_designer_tool.py   # **v2.0** Open channel designer
├── example_data/
│   ├── README.md              # Data documentation
│   ├── TUTORIALS.md           # Step-by-step tool tutorials
│   ├── create_sample_layers.py # GIS layer generator script
│   ├── cn_lookup_table.csv    # CN by landuse + HSG
│   ├── c_lookup_table.csv     # C by landuse + HSG + slope
│   ├── cn_lookup_split_hsg.csv # CN with dual HSG support
│   └── *.csv                  # Tabular reference data
├── README.md
├── CHANGELOG.md
├── DEVELOPER_GUIDE.md
├── CONTRIBUTING.md
├── HANDOFF.md                 # This file
├── LICENSE
└── .gitignore
```

---

## How to Launch

```python
# In QGIS Python Console:
exec(open(r'E:\CLAUDE_Workspace\Claude\Report_Files\Finished_Code\Hydro_Suite_Data_Backup_v1\github_standalone\launch_hydro_suite.py').read())
```

---

## How to Generate Sample GIS Layers

```python
# In QGIS Python Console:
exec(open(r'E:\CLAUDE_Workspace\Claude\Report_Files\Finished_Code\Hydro_Suite_Data_Backup_v1\github_standalone\example_data\create_sample_layers.py').read())
create_sample_data()
```

Creates 6 GeoPackage layers in `Documents/HydroSuite_SampleData/`:
- `sample_subbasins.gpkg` (5 polygons)
- `sample_landuse.gpkg` (10 polygons)
- `sample_soils.gpkg` (6 polygons with HSG A, B, C, D, A/D, B/D)
- `sample_flowpaths.gpkg` (9 lines) - **Required for TC Calculator**
- `sample_channels.gpkg` (5 lines) - **For Channel Designer import**
- `sample_outlets.gpkg` (6 points)

---

## TC Calculator v2.0 Usage

### Required Flowpaths Layer Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| Subbasin_ID | String | Links segment to subbasin | "SB-001" |
| Length_ft | Double | Segment length in feet | 800.0 |
| Slope_Pct | Double | Slope in percent | 3.5 |
| Mannings_n | Double | Manning's roughness | 0.035 |
| Flow_Type | String | Type of flow | "SHEET", "SHALLOW_CONC", "CHANNEL", "PIPE" |

### Flow Type Calculations

| Flow Type | Method | Notes |
|-----------|--------|-------|
| SHEET | TR-55 Eq. 3-3 | Limited to 300 ft per TR-55 |
| SHALLOW_CONC | TR-55 velocity | Paved vs unpaved based on n |
| CHANNEL | Manning's equation | Uses hydraulic radius |
| PIPE | Manning's (full flow) | Circular pipe assumed |

### Workflow
1. Open TC Calculator
2. Select flowpaths layer (e.g., `sample_flowpaths.gpkg`)
3. Map fields: Subbasin_ID, Length_ft, Slope_Pct, Mannings_n, Flow_Type
4. Select output directory
5. Click "Calculate Time of Concentration"
6. Results grouped by subbasin with segment details

---

## Channel Designer v2.0 Usage

### Import from Layer Tab
1. Open Channel Designer
2. Click "Import from Layer" tab
3. Select channels layer (e.g., `sample_channels.gpkg`)
4. Map fields:
   - Channel ID
   - Depth (ft)
   - Bottom Width (ft)
   - Side Slope (H:1V)
   - Manning's n (optional)
   - Channel Slope (optional)
5. Click "Import Channels from Layer"
6. View results in Results tab

### Required/Optional Fields

| Field | Required | Default if Missing |
|-------|----------|-------------------|
| Channel ID | Yes | - |
| Depth | Yes | - |
| Bottom Width | Yes | - |
| Side Slope | Yes | - |
| Manning's n | No | 0.035 |
| Channel Slope | No | 0.005 ft/ft |

---

## Testing Checklist

### Completed ✅
- [x] Launch Hydro Suite GUI
- [x] Style switching (all 9 themes)
- [x] Generate sample GIS layers
- [x] CN Calculator with sample data
- [x] Rational C Calculator with sample data
- [x] TC Calculator v2.0 code implementation
- [x] Channel Designer v2.0 code implementation

### Ready for Testing
- [ ] TC Calculator v2.0 with sample_flowpaths.gpkg
- [ ] Channel Designer v2.0 with sample_channels.gpkg
- [ ] TC Calculator segment detail CSV output
- [ ] Channel Designer capacity calculations
- [ ] Test with real project data

---

## Known Limitations

1. **TC Calculator**: Requires pre-calculated flowpath attributes (length, slope, n)
   - Does not extract from DEM automatically
   - Manual flow path delineation still needed

2. **Channel Designer**: Side slopes are symmetric when importing from layer
   - Left and right use same value
   - Manual design allows asymmetric

3. **Sample Data**: Uses SC State Plane (EPSG:2273)
   - May need coordinate transformation for other areas

---

## Dependencies

- QGIS 3.40+
- PyQt5 (bundled with QGIS)
- pandas (for CSV/Excel reading)
- qgis.core, qgis.gui, qgis.processing

---

## Git Status

Last commit: v2.0.0 - TC Calculator rewrite, Channel Designer GIS import
Branch: main
Remote: https://github.com/Joeywoody124/hydro-suite-standalone

---

## Next Steps

1. **Test TC Calculator v2.0** in QGIS with sample_flowpaths.gpkg
2. **Test Channel Designer v2.0** import with sample_channels.gpkg
3. **Validate results** against hand calculations
4. **Push updates** to GitHub repository
5. **Update tutorials** if workflow changes needed

---

## Contact

Joey Woody, PE  
J. Bragg Consulting Inc.  
Civil/Water Resources Engineer
