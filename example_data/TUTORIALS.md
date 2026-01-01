# Hydro Suite - Tool Tutorials with Sample Data

**Author**: Joey Woody, PE - J. Bragg Consulting Inc.  
**Purpose**: Step-by-step tutorials for each Hydro Suite tool using sample data  
**Last Updated**: January 2025

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Creating Sample GIS Layers](#creating-sample-gis-layers)
3. [Tutorial 1: CN Calculator](#tutorial-1-cn-calculator)
4. [Tutorial 2: Rational C Calculator](#tutorial-2-rational-c-calculator)
5. [Tutorial 3: TC Calculator](#tutorial-3-tc-calculator)
6. [Tutorial 4: Channel Designer](#tutorial-4-channel-designer)
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

# This creates GeoPackage layers in:
# Documents/HydroSuite_SampleData/
```

### Step 2: Verify Layers Created

The script creates 6 GeoPackage files:

| File | Type | Features | Purpose |
|------|------|----------|---------|
| `sample_subbasins.gpkg` | Polygon | 5 | Drainage area boundaries |
| `sample_landuse.gpkg` | Polygon | 10 | Land use/cover polygons |
| `sample_soils.gpkg` | Polygon | 6 | SSURGO-style soils with HSG |
| `sample_flowpaths.gpkg` | Line | 9 | TC flow path segments |
| `sample_channels.gpkg` | Line | 5 | Drainage channels |
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

### Understanding the Output

The tool calculates:

```
CN_composite = Σ(CN_i × Area_i) / Σ(Area_i)

Where:
- CN_i = Curve Number for each land use/soil combination
- Area_i = Area of each polygon from intersection
```

### Tips

- **Missing Land Use Codes**: If a land use code isn't in the lookup table, it will be flagged in the log
- **Split HSG**: Use "Undrained" for natural conditions, "Drained" if site has drainage infrastructure
- **CN Range**: Valid CN values are 30-100. Values outside this range indicate data issues

---

## Tutorial 2: Rational C Calculator

### Objective
Calculate area-weighted composite Runoff Coefficients (C values) for each subbasin based on land use and slope.

### Input Layers Required

| Layer | Key Field | Description |
|-------|-----------|-------------|
| Subbasins | `Subbasin_ID` | Drainage boundaries |
| Land Use | `Land_Use` | Land use codes |
| (Optional) | `Slope_Pct` | Slope field for variable C |

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

Or check **Use Slope Field** and select the slope attribute.

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

### Understanding C Values

| C Range | Runoff Potential | Typical Surfaces |
|---------|------------------|------------------|
| 0.00-0.20 | Very Low | Forest, meadow |
| 0.20-0.40 | Low | Lawns, parks, pasture |
| 0.40-0.60 | Moderate | Residential |
| 0.60-0.80 | High | Commercial, industrial |
| 0.80-1.00 | Very High | Pavement, roofs |

### Rational Method Application

Use the composite C in the Rational Method:

```
Q = C × i × A

Where:
- Q = Peak discharge (cfs)
- C = Runoff coefficient (from this tool)
- i = Rainfall intensity (in/hr) from IDF curves
- A = Drainage area (acres)
```

---

## Tutorial 3: TC Calculator

### Objective
Calculate Time of Concentration (Tc) using multiple methods for comparison.

### Input Options

**Option A: Manual Entry**
Enter flow path parameters directly

**Option B: From GIS Layer**
Use flow path line features with attributes

### Step-by-Step (Manual Entry)

**Step 1: Enter Watershed Parameters**

1. Click **Time of Concentration**
2. Enter:
   - Flow Length: `2100` ft
   - Average Slope: `3.2` %
   - Surface Type: Select from dropdown

**Step 2: Select Calculation Methods**

Check methods to calculate:
- [x] Kirpich (1940)
- [x] FAA (1965)
- [x] SCS/NRCS (1972)
- [x] Kerby

**Step 3: Enter Method-Specific Parameters**

For SCS method:
- Curve Number: `75`

For Kerby method:
- Retardance Coefficient: `0.40` (grass)

**Step 4: Calculate**

1. Click **Calculate Tc**
2. Compare results from each method

### Step-by-Step (From GIS Layer)

**Step 1: Load Flow Path Layer**

1. Select Layer: `Sample_flowpaths`
2. Select Fields:
   - Length: `Length_ft`
   - Slope: `Slope_Pct`
   - Manning's n: `Mannings_n`

**Step 2: Select Subbasin**

Choose subbasin from dropdown or process all.

**Step 3: Calculate**

The tool sums segments by flow type:
- Sheet flow (limited to 100 ft max)
- Shallow concentrated flow
- Channel/pipe flow

### Expected Results

| Subbasin | Kirpich | FAA | SCS | Recommended |
|----------|---------|-----|-----|-------------|
| SB-001 | 15.2 min | 18.5 min | 16.8 min | 17.0 min |
| SB-002 | 8.5 min | 12.0 min | 10.2 min | 10.0 min |
| SB-003 | 28.5 min | 35.0 min | 32.1 min | 32.0 min |

### Method Selection Guide

| Method | Best For | Limitations |
|--------|----------|-------------|
| **Kirpich** | Small rural watersheds (<200 ac) | Underestimates urban |
| **FAA** | Airports, urban areas | Requires C value |
| **SCS/NRCS** | General use | Requires CN |
| **Kerby** | Overland flow only | Max 1200 ft length |

### Tips

- **Multi-segment paths**: Break flow path into sheet, shallow concentrated, and channel segments
- **Sheet flow limit**: NRCS limits sheet flow to 100 ft maximum
- **Use multiple methods**: Compare results and use engineering judgment

---

## Tutorial 4: Channel Designer

### Objective
Design trapezoidal open channels and calculate hydraulic properties using Manning's equation.

### Input Options

**Option A: Manual Design**
Enter channel geometry and compute capacity

**Option B: From GIS Layer**
Use channel line features with attributes

**Option C: Target Capacity**
Specify required Q and solve for geometry

### Step-by-Step (Manual Design)

**Step 1: Enter Channel Geometry**

1. Click **Channel Designer**
2. Enter:
   - Bottom Width: `8.0` ft
   - Side Slope (H:V): `2.0` (2:1 slope)
   - Design Depth: `4.0` ft
   - Manning's n: `0.035` (grass-lined)
   - Channel Slope: `0.005` ft/ft

**Step 2: Calculate Properties**

Click **Calculate** to compute:
- Flow Area (sq ft)
- Wetted Perimeter (ft)
- Hydraulic Radius (ft)
- Top Width (ft)
- Velocity (ft/s)
- Capacity Q (cfs)

**Step 3: View Cross-Section**

The tool displays an interactive cross-section diagram showing:
- Channel geometry
- Water surface at design depth
- Freeboard (if specified)

### Expected Results (8 ft bottom, 2:1 slopes, 4 ft depth)

| Property | Value | Units |
|----------|-------|-------|
| Flow Area | 64.0 | sq ft |
| Wetted Perimeter | 25.89 | ft |
| Hydraulic Radius | 2.47 | ft |
| Top Width | 24.0 | ft |
| Velocity | 5.2 | ft/s |
| Capacity | 333 | cfs |

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

### Trapezoidal Geometry

```
        ←─── Top Width (T) ───→
        ╱                      ╲
       ╱  ←── z:1 side slope    ╲
      ╱                          ╲
     ╱____________________________╲
           ←─ Bottom Width (b) ─→

T = b + 2zd
A = (b + zd) × d
P = b + 2d × sqrt(1 + z²)
```

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

### SWMM Output Format

The tool can export channel data in SWMM-compatible format:

```
[XSECTIONS]
;;Link    Shape    Geom1    Geom2    Geom3    Geom4
CH-001    TRAPEZOIDAL    4.0    8.0    2.0    2.0
```

---

## Common Workflows

### Workflow 1: Pre-Development Analysis

1. Load existing conditions land use and soils
2. Calculate CN for each subbasin
3. Calculate Tc for each subbasin
4. Export results for hydrologic model (SWMM, HEC-HMS)

### Workflow 2: Post-Development Analysis

1. Create proposed land use layer (digitize or modify existing)
2. Run CN Calculator with proposed conditions
3. Compare pre vs post CN values
4. Size detention/retention based on CN increase

### Workflow 3: Channel Sizing

1. Determine design flow (Q) from Rational Method:
   ```
   Q = C × i × A
   ```
2. Open Channel Designer
3. Enter target Q and channel constraints
4. Iterate geometry to achieve required capacity
5. Check velocity limits (erosion/deposition)

### Workflow 4: Complete Watershed Study

```
┌─────────────────────────────────────────┐
│  1. Delineate Subbasins                 │
│     (Manual or from DEM)                │
└─────────────────┬───────────────────────┘
                  ▼
┌─────────────────────────────────────────┐
│  2. Overlay Land Use + Soils            │
│     (Intersection in QGIS)              │
└─────────────────┬───────────────────────┘
                  ▼
┌─────────────────────────────────────────┐
│  3. Calculate CN (Hydro Suite)          │
│     - Load lookup table                 │
│     - Handle split HSG                  │
└─────────────────┬───────────────────────┘
                  ▼
┌─────────────────────────────────────────┐
│  4. Calculate C (Hydro Suite)           │
│     - Select slope category             │
└─────────────────┬───────────────────────┘
                  ▼
┌─────────────────────────────────────────┐
│  5. Delineate Flow Paths                │
│     (Manual or from DEM)                │
└─────────────────┬───────────────────────┘
                  ▼
┌─────────────────────────────────────────┐
│  6. Calculate Tc (Hydro Suite)          │
│     - Multi-method comparison           │
│     - Select appropriate value          │
└─────────────────┬───────────────────────┘
                  ▼
┌─────────────────────────────────────────┐
│  7. Design Channels (Hydro Suite)       │
│     - Size for design storm             │
│     - Check velocities                  │
└─────────────────┬───────────────────────┘
                  ▼
┌─────────────────────────────────────────┐
│  8. Export to H&H Model                 │
│     (SWMM, HEC-HMS, etc.)               │
└─────────────────────────────────────────┘
```

---

## Troubleshooting

### "Land use code not found"
- Check that `Land_Use` field values match lookup table exactly
- Land use codes are case-sensitive
- Check for leading/trailing spaces

### "No intersection results"
- Verify layers overlap spatially
- Check CRS matches between layers
- Try running QGIS Vector > Geoprocessing > Intersection manually

### "Invalid CN value"
- CN must be 30-100
- Check soils HSG field for invalid values
- Verify lookup table format

### "Tc seems too low/high"
- Verify flow length units (feet vs meters)
- Check slope is in percent, not decimal
- Compare multiple methods

---

## References

1. **TR-55**: USDA NRCS (1986) "Urban Hydrology for Small Watersheds"
2. **NEH Part 630**: NRCS National Engineering Handbook
3. **HEC-22**: FHWA "Urban Drainage Design Manual"
4. **ASCE MOP 77**: "Design of Urban Stormwater Management Systems"
5. **Chow (1959)**: "Open-Channel Hydraulics"

---

*Last Updated: January 2025*  
*Author: Joey Woody, PE - J. Bragg Consulting Inc.*
