# Hydro Suite - Tool Tutorials with Sample Data

**Author**: Joey Woody, PE - J. Bragg Consulting Inc.  
**Purpose**: Step-by-step tutorials for each Hydro Suite tool using sample data  
**Last Updated**: January 2025  
**Version**: 2.0.0

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Creating Sample GIS Layers](#creating-sample-gis-layers)
3. [Tutorial 1: CN Calculator](#tutorial-1-cn-calculator)
4. [Tutorial 2: Rational C Calculator](#tutorial-2-rational-c-calculator)
5. [Tutorial 3: TC Calculator (v2.0)](#tutorial-3-tc-calculator-v20)
6. [Tutorial 4: Channel Designer (v2.0)](#tutorial-4-channel-designer-v20)
7. [Common Workflows](#common-workflows)

---

## Getting Started

### Prerequisites

1. **QGIS 3.40+** installed
2. **Hydro Suite Standalone** downloaded
3. **Sample Data** created (see next section)

### Launch Hydro Suite

Open QGIS Python Console and run:

```python
exec(open(r'E:\path\to\hydro-suite-standalone\launch_hydro_suite.py').read())
```

---

## Creating Sample GIS Layers

### Step 1: Run the Layer Generator

In QGIS Python Console:

```python
# Run the sample data generator
exec(open(r'E:\path\to\hydro-suite-standalone\example_data\create_sample_layers.py').read())

# Create the layers
create_sample_data()

# Files created in: Documents/HydroSuite_SampleData/
```

### Step 2: Verify Layers Created

The script creates 6 GeoPackage files:

| File | Type | Features | Purpose |
|------|------|----------|---------|
| `sample_subbasins.gpkg` | Polygon | 5 | Drainage area boundaries |
| `sample_landuse.gpkg` | Polygon | 10 | Land use/cover polygons |
| `sample_soils.gpkg` | Polygon | 6 | SSURGO-style soils with HSG |
| `sample_flowpaths.gpkg` | Line | 9 | **TC flow path segments (v2.0)** |
| `sample_channels.gpkg` | Line | 5 | **Channel import data (v2.0)** |
| `sample_outlets.gpkg` | Point | 6 | Outlet/pour points |

### Step 3: Load Layers in QGIS

The script automatically adds layers to your project. If not:

1. `Layer` > `Add Layer` > `Add Vector Layer`
2. Browse to `Documents/HydroSuite_SampleData/`
3. Select all `.gpkg` files

---

## Tutorial 1: CN Calculator

### Objective
Calculate area-weighted composite Curve Numbers for each subbasin by intersecting land use and soils data.

### Input Layers Required

| Layer | Key Field | Description |
|-------|-----------|-------------|
| Subbasins | `Subbasin_ID` | Drainage boundaries |
| Land Use | `Land_Use` | Land use codes matching lookup table |
| Soils | `HSG` | Hydrologic Soil Group (A, B, C, D, A/D, etc.) |

### Step-by-Step

**Step 1: Select Input Layers**

1. Open Hydro Suite
2. Click **Curve Number Calculator**
3. Select inputs:
   - Subbasins Layer: `Sample_subbasins`
   - Subbasin ID Field: `Subbasin_ID`
   - Land Use Layer: `Sample_landuse`
   - Land Use Field: `Land_Use`
   - Soils Layer: `Sample_soils`
   - HSG Field: `HSG`

**Step 2: Load Lookup Table**

1. Click **Load CN Lookup Table**
2. Navigate to: `example_data/cn_lookup_table.csv`
3. Click **Open**

**Step 3: Handle Dual HSG (Optional)**

For coastal areas with A/D, B/D, C/D soils:

1. Check **Handle Split HSG**
2. Select drainage condition: `Drained` or `Undrained`

**Step 4: Run Analysis**

1. Click **Calculate CN**
2. Wait for processing
3. Review results in the log panel

### Expected Results

| Subbasin | Area (ac) | Composite CN | Description |
|----------|-----------|--------------|-------------|
| SB-001 | 16.5 | 73-77 | Residential mix |
| SB-002 | 13.3 | 90-94 | Commercial/impervious |
| SB-003 | 60.8 | 52-58 | Woods/wetland |
| SB-004 | 23.6 | 86-90 | Industrial |
| SB-005 | 110.5 | 72-76 | Agricultural |

---

## Tutorial 2: Rational C Calculator

### Objective
Calculate area-weighted composite Runoff Coefficients (C values) for each subbasin based on land use and slope.

### Input Layers Required

| Layer | Key Field | Description |
|-------|-----------|-------------|
| Subbasins | `Subbasin_ID` | Drainage boundaries |
| Land Use | `Land_Use` | Land use codes |

### Step-by-Step

**Step 1: Select Input Layers**

1. Click **Rational C Calculator**
2. Select inputs:
   - Subbasins Layer: `Sample_subbasins`
   - Subbasin ID Field: `Subbasin_ID`
   - Land Use Layer: `Sample_landuse`
   - Land Use Field: `Land_Use`

**Step 2: Select Slope Category**

Choose project-wide slope category:
- **Flat (0-2%)**: Low slopes, slower runoff
- **Rolling (2-6%)**: Moderate slopes
- **Steep (6%+)**: High slopes, faster runoff

**Step 3: Load Lookup Table**

1. Click **Load C Lookup Table**
2. Navigate to: `example_data/c_lookup_table.csv`
3. Click **Open**

**Step 4: Run Analysis**

1. Click **Calculate C**
2. Review results

### Expected Results

| Subbasin | Slope | Composite C | Interpretation |
|----------|-------|-------------|----------------|
| SB-001 | Rolling | 0.40-0.45 | Moderate runoff |
| SB-002 | Flat | 0.75-0.80 | High runoff (impervious) |
| SB-003 | Steep | 0.10-0.15 | Low runoff (forest) |
| SB-004 | Rolling | 0.65-0.70 | High runoff (industrial) |
| SB-005 | Rolling | 0.32-0.38 | Moderate (agriculture) |

---

## Tutorial 3: TC Calculator (v2.0)

### What's New in v2.0
- **Flowpaths layer input** - Uses TR-55 segment-based methodology
- **Automatic grouping** - Segments grouped by Subbasin_ID
- **Flow type support** - SHEET, SHALLOW_CONC, CHANNEL, PIPE
- **Segment detail output** - CSV with individual segment travel times
- **Comparison methods** - Kirpich, FAA, SCS Lag, Kerby for validation

### Objective
Calculate Time of Concentration (Tc) using TR-55 segment-based travel times from a flowpaths layer.

### Input Layer Required

| Layer | Required Fields | Description |
|-------|-----------------|-------------|
| Flowpaths | `Subbasin_ID` | Links segment to subbasin |
| | `Length_ft` | Segment length in feet |
| | `Slope_Pct` | Slope in percent |
| | `Mannings_n` | Manning's roughness coefficient |
| | `Flow_Type` | SHEET, SHALLOW_CONC, CHANNEL, or PIPE |

### Step-by-Step

**Step 1: Open TC Calculator**

1. Open Hydro Suite
2. Click **Time of Concentration Calculator**
3. You'll see the Configuration tab

**Step 2: Select Flowpaths Layer**

1. In "Flowpaths Layer" dropdown, select `Sample_flowpaths`
2. The tool auto-detects common field names

**Step 3: Map Fields**

Verify or adjust field mapping:
- Subbasin ID Field: `Subbasin_ID`
- Length (ft) Field: `Length_ft`
- Slope (%) Field: `Slope_Pct`
- Manning's n Field: `Mannings_n`
- Flow Type Field: `Flow_Type`

**Step 4: Configure Parameters (Optional)**

Click the **Parameters** tab to adjust:
- 2-yr 24-hr Rainfall: `3.5` in (SC Lowcountry typical)
- Default Hydraulic Radius: `1.0` ft

**Step 5: Select Comparison Methods (Optional)**

Click the **Methods** tab to enable:
- [x] Kirpich - Rural watersheds
- [x] SCS Lag - NRCS standard
- [ ] FAA - Urban areas
- [ ] Kerby - Overland flow only

**Step 6: Select Output Directory**

1. Click **Browse...** for Output Directory
2. Select or create output folder

**Step 7: Run Calculation**

1. Click **Calculate Time of Concentration**
2. Wait for processing
3. View results in Results tab

### Understanding Flow Types

| Flow Type | Method Used | TR-55 Reference |
|-----------|-------------|-----------------|
| SHEET | Equation 3-3 | Limited to 300 ft max |
| SHALLOW_CONC | Velocity method | Figure 3-1 |
| CHANNEL | Manning's equation | Open channel flow |
| PIPE | Manning's (full) | Storm pipe flow |

### Expected Results (Sample Data)

| Subbasin | Segments | Total Length | TC Segment | Kirpich | SCS Lag |
|----------|----------|--------------|------------|---------|---------|
| SB-001 | 3 | 2100 ft | 15-20 min | 15 min | 18 min |
| SB-002 | 3 | 1050 ft | 8-12 min | 9 min | 11 min |
| SB-003 | 3 | 3600 ft | 25-35 min | 28 min | 32 min |

### Output Files

| File | Description |
|------|-------------|
| `tc_calculations.csv` | TC summary by subbasin |
| `tc_segment_details.csv` | Individual segment travel times |

### Tips

- **Sheet flow limit**: TR-55 limits sheet flow to 300 ft maximum
- **Manning's n threshold**: n < 0.02 assumed paved for shallow concentrated flow
- **Use multiple methods**: Compare segment-based TC with whole-watershed methods
- **Check segment details**: Review `tc_segment_details.csv` to verify each segment

---

## Tutorial 4: Channel Designer (v2.0)

### What's New in v2.0
- **GIS Layer Import** - Import channels directly from vector layers
- **Field mapping** - Flexible field assignment for any layer structure
- **Capacity calculation** - Manning's equation for velocity and Q
- **Enhanced export** - CSV includes all hydraulic properties

### Objective
Design trapezoidal open channels and calculate hydraulic properties, with option to import from GIS layers.

### Input Options

| Method | Use Case |
|--------|----------|
| Manual Design | Interactive single-channel design |
| Import from Layer | Bulk import from GIS (e.g., `sample_channels.gpkg`) |
| Batch CSV | Import from CSV file |

### Step-by-Step: Import from Layer (Recommended)

**Step 1: Open Channel Designer**

1. Open Hydro Suite
2. Click **Channel Designer**
3. Click the **Import from Layer** tab

**Step 2: Select Channel Layer**

1. In "Channels Layer", select `Sample_channels`
2. Fields auto-populate based on common names

**Step 3: Map Fields**

| Field | Sample Layer Field | Required |
|-------|-------------------|----------|
| Channel ID | `Channel_ID` | Yes |
| Depth (ft) | `Depth_ft` | Yes |
| Bottom Width (ft) | `Bottom_W_ft` | Yes |
| Side Slope (H:1V) | `Side_Slope` | Yes |
| Manning's n | `Mannings_n` | No (default 0.035) |
| Channel Slope (ft/ft) | `Slope_ftft` | No (default 0.005) |

**Step 4: Import Channels**

1. Click **Import Channels from Layer**
2. Wait for processing
3. Success message shows count of imported channels

**Step 5: View Results**

1. Click the **Results** tab
2. Review table with all hydraulic properties:
   - Depth, Width, Side Slope
   - Top Width, Area, Hydraulic Radius
   - **Velocity (fps)** and **Capacity (cfs)**

**Step 6: Export SWMM Format**

1. Copy text from "SWMM Cross-Section Format" box
2. Or click **Export to CSV** for full data

### Step-by-Step: Manual Design

**Step 1: Open Manual Design Tab**

1. Click **Manual Design** tab
2. Enter channel parameters:
   - Channel ID: `CH-001`
   - Depth: `4.0` ft
   - Bottom Width: `8.0` ft
   - Left/Right Slope: `2.0` (2:1 H:V)
   - Manning's n: `0.035` (grass-lined)
   - Channel Slope: `0.005` ft/ft

**Step 2: Preview Results**

The cross-section preview updates automatically showing:
- Geometric visualization
- Calculated properties
- **Flow Capacity (Q)**

**Step 3: Add to List**

1. Click **Add to Design List**
2. Channel appears in Results tab
3. Channel ID auto-increments

### Expected Results (Sample Channels)

| Channel | Depth | Width | Slope | Velocity | Capacity |
|---------|-------|-------|-------|----------|----------|
| CH-001 (Main Outfall) | 4.0 | 8.0 | 0.005 | 5.2 fps | 333 cfs |
| CH-002 (Collector) | 2.0 | 4.0 | 0.008 | 4.8 fps | 77 cfs |
| CH-003 (Concrete) | 2.5 | 3.0 | 0.010 | 8.1 fps | 97 cfs |
| CH-004 (Rip-rap) | 3.0 | 6.0 | 0.012 | 5.5 fps | 149 cfs |
| CH-005 (Natural) | 3.5 | 10.0 | 0.003 | 3.8 fps | 200 cfs |

### Manning's n Reference

| Channel Type | n Value |
|--------------|---------|
| Concrete (smooth) | 0.012-0.014 |
| Concrete (rough) | 0.015-0.017 |
| Asphalt | 0.013-0.016 |
| Grass (short) | 0.025-0.035 |
| Grass (tall) | 0.035-0.050 |
| Rip-rap | 0.035-0.045 |
| Natural stream | 0.040-0.070 |

### Manning's Equation

```
Q = (1.49/n) × A × R^(2/3) × S^(1/2)

Where:
- Q = Discharge (cfs)
- n = Manning's roughness
- A = Flow area (sq ft)
- R = Hydraulic radius (ft) = A / P
- S = Channel slope (ft/ft)
```

---

## Common Workflows

### Workflow 1: Complete Watershed Analysis

```
┌─────────────────────────────────────────┐
│  1. Create/Load Subbasins Layer         │
└─────────────────┬───────────────────────┘
                  ▼
┌─────────────────────────────────────────┐
│  2. Run CN Calculator                   │
│     - Load lookup table                 │
│     - Handle split HSG if coastal       │
└─────────────────┬───────────────────────┘
                  ▼
┌─────────────────────────────────────────┐
│  3. Run Rational C Calculator           │
│     - Select slope category             │
└─────────────────┬───────────────────────┘
                  ▼
┌─────────────────────────────────────────┐
│  4. Create Flowpaths Layer (manually)   │
│     - Digitize segments per subbasin    │
│     - Assign Flow_Type, Length, Slope   │
└─────────────────┬───────────────────────┘
                  ▼
┌─────────────────────────────────────────┐
│  5. Run TC Calculator v2.0              │
│     - Load flowpaths layer              │
│     - Map fields                        │
│     - Compare with Kirpich/SCS          │
└─────────────────┬───────────────────────┘
                  ▼
┌─────────────────────────────────────────┐
│  6. Design Channels                     │
│     - Import from layer or manual       │
│     - Check capacity vs design Q        │
└─────────────────┬───────────────────────┘
                  ▼
┌─────────────────────────────────────────┐
│  7. Export to H&H Model                 │
│     (SWMM, HEC-HMS, etc.)               │
└─────────────────────────────────────────┘
```

### Workflow 2: Creating Flowpaths Layer

To create a flowpaths layer for TC Calculator:

1. **Digitize flow paths** in QGIS for each subbasin
2. **Add required fields**:
   ```
   Subbasin_ID (text) - e.g., "SB-001"
   Length_ft (double) - measured or from geometry
   Slope_Pct (double) - from DEM or survey
   Mannings_n (double) - based on surface type
   Flow_Type (text) - SHEET, SHALLOW_CONC, CHANNEL, PIPE
   ```
3. **Break into segments** by flow type (TR-55 requirement)
4. **Sheet flow max 300 ft** per TR-55

### Workflow 3: Channel Capacity Check

1. Run Rational Method: `Q = C × i × A`
2. Import channels to Channel Designer
3. Compare design Q to calculated Capacity
4. Adjust channel dimensions if capacity insufficient

---

## Troubleshooting

### "No features imported" (Channel Designer)
- Check that required fields are mapped
- Verify layer has valid geometry
- Check for NULL values in depth/width fields

### "TC Calculator shows 0 minutes"
- Check that Length_ft and Slope_Pct are not zero
- Verify Flow_Type values match expected (SHEET, SHALLOW_CONC, etc.)
- Check Manning's n is reasonable (0.01-0.80)

### "Layer not appearing in dropdown"
- TC Calculator v2.0 requires LINE geometry for flowpaths
- Channel Designer requires LINE geometry for channels
- CN/C Calculators require POLYGON geometry

### "Comparison methods give very different results"
- This is expected! Methods have different assumptions
- Use segment-based TC as primary (most accurate)
- Use whole-watershed methods for validation/comparison

---

## References

1. **TR-55**: USDA NRCS (1986) "Urban Hydrology for Small Watersheds"
2. **NEH Part 630**: NRCS National Engineering Handbook
3. **HEC-22**: FHWA "Urban Drainage Design Manual"
4. **ASCE MOP 77**: "Design of Urban Stormwater Management Systems"
5. **Chow (1959)**: "Open-Channel Hydraulics"

---

*Last Updated: January 2025 (v2.0.0)*  
*Author: Joey Woody, PE - J. Bragg Consulting Inc.*
