# Example Data and Lookup Tables

**Author**: Joey Woody, PE - J. Bragg Consulting Inc.  
**Purpose**: Reference tables and example data for Hydro Suite tools  
**Last Updated**: January 2025

---

## Files in This Folder

| File | Description | Used By |
|------|-------------|---------|
| `cn_lookup_table.csv` | Curve Number by Land Use and HSG | CN Calculator |
| `cn_lookup_split_hsg.csv` | CN with dual HSG support (A/D, B/D, C/D) | CN Calculator |
| `c_lookup_table.csv` | Rational C by Land Use and Slope | Rational C Calculator |
| `example_subbasins.csv` | Sample watershed data | All tools |
| `example_channels.csv` | Sample channel designs | Channel Designer |
| `example_tc_flowpaths.csv` | Sample flow path data | TC Calculator |

---

## CN Lookup Table (`cn_lookup_table.csv`)

### Source
Based on USDA TR-55 (Technical Release 55) "Urban Hydrology for Small Watersheds" and NRCS National Engineering Handbook Part 630.

### Columns
| Column | Description |
|--------|-------------|
| `Land_Use` | Land use code (use this for joins) |
| `Description` | Human-readable description |
| `HSG_A` | Curve Number for Hydrologic Soil Group A |
| `HSG_B` | Curve Number for Hydrologic Soil Group B |
| `HSG_C` | Curve Number for Hydrologic Soil Group C |
| `HSG_D` | Curve Number for Hydrologic Soil Group D |

### Hydrologic Soil Groups
| HSG | Infiltration Rate | Description |
|-----|-------------------|-------------|
| A | High (>0.30 in/hr) | Deep, well-drained sands and gravels |
| B | Moderate (0.15-0.30 in/hr) | Moderately deep, moderately well-drained |
| C | Slow (0.05-0.15 in/hr) | Soils with layers that impede drainage |
| D | Very Slow (<0.05 in/hr) | Clay soils, high water table, shallow bedrock |

### Usage Example
```
Your GIS layer has: Land_Use = "RES_1_4_AC", HSG = "B"
Lookup result: CN = 75
```

---

## Split HSG Table (`cn_lookup_split_hsg.csv`)

### Purpose
For coastal areas and regions with seasonally high water tables, soils may be classified as dual groups (A/D, B/D, C/D). The first letter indicates drained condition; "D" indicates undrained.

### Additional Columns
| Column | Description |
|--------|-------------|
| `HSG_A_D_Drained` | A/D soil when adequately drained |
| `HSG_A_D_Undrained` | A/D soil when NOT drained (uses D value) |
| `HSG_B_D_Drained` | B/D soil when adequately drained |
| `HSG_B_D_Undrained` | B/D soil when NOT drained (uses D value) |
| `HSG_C_D_Drained` | C/D soil when adequately drained |
| `HSG_C_D_Undrained` | C/D soil when NOT drained (uses D value) |

### When to Use
- **Drained**: Site has adequate drainage infrastructure, ditches, or tile drains
- **Undrained**: Natural condition, high water table, wetland areas

---

## Rational C Lookup Table (`c_lookup_table.csv`)

### Source
Based on ASCE Manual of Practice No. 77, various state DOT manuals, and standard engineering practice.

### Columns
| Column | Description |
|--------|-------------|
| `Land_Use` | Land use code (use this for joins) |
| `Description` | Human-readable description |
| `C_Flat_0_2` | C value for slopes 0-2% |
| `C_Rolling_2_6` | C value for slopes 2-6% |
| `C_Steep_6_Plus` | C value for slopes >6% |

### Rational Method Formula
```
Q = C × i × A

Where:
  Q = Peak discharge (cfs or m³/s)
  C = Runoff coefficient (dimensionless, 0.0 to 1.0)
  i = Rainfall intensity (in/hr or mm/hr)
  A = Drainage area (acres or hectares)
```

### C Value Guidelines
| C Range | Typical Surfaces |
|---------|------------------|
| 0.00-0.20 | Forests, meadows, well-vegetated areas |
| 0.20-0.40 | Lawns, pastures, parks |
| 0.40-0.60 | Residential areas, unpaved surfaces |
| 0.60-0.80 | Commercial, industrial, streets |
| 0.80-1.00 | Impervious surfaces, roofs, pavement |

---

## Example Subbasins (`example_subbasins.csv`)

### Purpose
Sample watershed data representing a mixed-use development for testing CN and C calculators.

### Columns
| Column | Description |
|--------|-------------|
| `Subbasin_ID` | Unique identifier for subbasin |
| `Subbasin_Name` | Descriptive name |
| `Land_Use` | Land use code (matches lookup tables) |
| `HSG` | Hydrologic Soil Group (A, B, C, D) |
| `Area_Acres` | Area in acres |
| `Area_SqFt` | Area in square feet |
| `Slope_Percent` | Average slope (%) |
| `Description` | Additional notes |

### Example Analysis
For SB-001 (North Residential):
- Total area: 16.5 acres
- Land uses: Residential (12.5 ac), Streets (1.8 ac), Open Space (2.2 ac)
- Composite CN (HSG B): Area-weighted average ~73

---

## Example Channels (`example_channels.csv`)

### Purpose
Sample channel design data for the Channel Designer tool.

### Columns
| Column | Description |
|--------|-------------|
| `Channel_ID` | Unique identifier |
| `Name` | Channel name |
| `Bottom_Width_ft` | Bottom width (feet) |
| `Side_Slope_H_V` | Side slope ratio (H:V, e.g., 2.0 = 2:1) |
| `Depth_ft` | Design depth (feet) |
| `Mannings_n` | Manning's roughness coefficient |
| `Slope_ft_ft` | Longitudinal slope (ft/ft) |
| `Description` | Channel type/lining |

### Manning's n Reference
| Surface | n Value |
|---------|---------|
| Concrete | 0.013-0.017 |
| Asphalt | 0.015-0.017 |
| Grass (maintained) | 0.025-0.035 |
| Grass (dense) | 0.035-0.050 |
| Rip-rap | 0.035-0.045 |
| Natural stream | 0.040-0.070 |
| Wetland | 0.050-0.120 |

---

## Example Flow Paths (`example_tc_flowpaths.csv`)

### Purpose
Sample flow path data for Time of Concentration calculations.

### Columns
| Column | Description |
|--------|-------------|
| `Watershed_ID` | Unique identifier |
| `Watershed_Name` | Watershed name |
| `Flow_Length_ft` | Total flow path length (feet) |
| `Slope_Percent` | Average slope along flow path (%) |
| `Surface_Type` | Dominant surface type |
| `Mannings_n` | Representative Manning's n |
| `CN` | Representative Curve Number |
| `C_Value` | Representative Rational C |
| `Description` | Flow path notes |

### TC Method Selection Guide
| Method | Best For |
|--------|----------|
| Kirpich | Small rural/agricultural watersheds |
| FAA | Urban areas, airports |
| SCS/NRCS | General use, requires CN |
| Kerby | Overland flow, short paths |

---

## How to Use These Tables

### In QGIS
1. Load CSV as a layer: `Layer` > `Add Layer` > `Add Delimited Text Layer`
2. Join to your polygon layer using `Land_Use` field
3. Run Hydro Suite tools with joined data

### Direct Import
1. Open Hydro Suite tool
2. Click "Load Lookup Table"
3. Navigate to this folder
4. Select appropriate CSV file

### Custom Tables
You can create your own lookup tables following the same format:
1. Keep column headers exactly as shown
2. Use consistent `Land_Use` codes
3. Save as UTF-8 CSV

---

## References

1. **TR-55**: USDA NRCS (1986) "Urban Hydrology for Small Watersheds"
2. **NEH Part 630**: NRCS National Engineering Handbook, Chapter 9 "Hydrologic Soil-Cover Complexes"
3. **ASCE MOP 77**: ASCE Manual of Practice No. 77 "Design and Construction of Urban Stormwater Management Systems"
4. **HEC-22**: FHWA "Urban Drainage Design Manual"
5. **SCDOT**: South Carolina Department of Transportation Drainage Manual

---

## Disclaimer

These tables are provided as general engineering references. Values may need adjustment based on:
- Local regulations and standards
- Site-specific conditions
- Project requirements
- Professional engineering judgment

Always verify lookup values against applicable local standards and project criteria.

---

*Last Updated: January 2025*  
*Author: Joey Woody, PE - J. Bragg Consulting Inc.*
