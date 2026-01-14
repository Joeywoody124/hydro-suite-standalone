# Hydro Suite - Standalone Scripts for QGIS

**Version**: 2.5.0  
**Status**: Production Ready  
**Last Updated**: January 14, 2025  
**QGIS Compatibility**: 3.40+  
**Author**: Joey Woody, PE - J. Bragg Consulting Inc.

---

## Important: This is the Standalone Script Version

This repository contains the **standalone script version** of Hydro Suite, designed to run directly in the QGIS Python Console without plugin installation.

| Version | Repository | Status |
|---------|------------|--------|
| **Standalone Scripts (This Repo)** | [hydro-suite-standalone](https://github.com/Joeywoody124/hydro-suite-standalone) | ✅ Working |
| QGIS Plugin Version | [hydro-suite](https://github.com/Joeywoody124/hydro-suite) | Needs Fixes |

---

## What's New in v2.5.0

### CRITICAL BUG FIX: SCS Lag Slope Units

**Fixed in v2.5.0:** The SCS Lag method was incorrectly converting slope from percent to ft/ft before calculation. Per NRCS NEH Part 630 Chapter 15, SCS Lag uses slope in **percent** directly.

- **Impact:** Previous versions (v2.4.0 and earlier) produced TC values ~10x too high
- **Example:** A basin that should calculate 46 min TC was showing 492 min
- **Reference:** NRCS NEH Part 630, Chapter 15 (2010)

---

## What's New in v2.3.0/2.4.0

### TC Calculator - DEM Extraction Mode + Flat Terrain Fallbacks!

Three calculation modes are now available:

| Mode | Input Required | What You Get |
|------|----------------|---------------|
| **Flowpath Layer Mode** | Flowpath layer | TR-55 segment-based TC + comparison methods |
| **Manual Entry Mode** | None (enter directly) | Comparison methods only (quick estimates) |
| **DEM Extraction Mode** | DEM + Subbasins | Auto-extracted L/S + SCS Lag or TR-55 |

**New in v2.3.0:**
- **DEM-Based Flowpath Extraction**: Automatically extract length/slope from DEM
- **Industry-Standard Flat Terrain Fallbacks**: Per TxDOT/Cleveland et al. 2012
  - Low slope adjustment: Add 0.0005 when S < 0.2%
  - Minimum TC enforcement: 6 min (default), 5 min (paved), 10 min (rural)
  - Adverse slope handling: Use minimum 0.05% when S < 0
- **SCS Lag Method**: With DEM parameters and valid range warnings
- **TR-55 Simplified**: Estimates flow types from land use
- **Validation Warnings**: For out-of-range CN, slope, or length

**From v2.2.0:**
- Mode Selection: Radio buttons to choose calculation mode
- Manual Entry Table: Add subbasins, enter L/S/CN/C/n directly
- Per-Subbasin Parameters: Custom CN, C, Manning's n per subbasin
- Per-Subbasin Channel Geometry: Define channel/pipe dimensions per subbasin
- CSV Import/Export: Save and reload manual entry data

---

## Quick Start - How to Run

### Step 1: Download/Clone This Repository

```bash
git clone https://github.com/Joeywoody124/hydro-suite-standalone.git
```

Or download the ZIP and extract to your preferred location.

### Step 2: Launch in QGIS Python Console

1. Open **QGIS 3.40+**
2. Open the **Python Console** (`Plugins` > `Python Console` or `Ctrl+Alt+P`)
3. Copy and paste this command, updating the path to match your installation:

```python
exec(open(r'C:\path\to\hydro-suite-standalone\launch_hydro_suite.py').read())
```

**Example paths:**
```python
# Windows example:
exec(open(r'E:\GitHub\hydro-suite-standalone\launch_hydro_suite.py').read())
```

### Step 3: Use the Tools

Once launched, the Hydro Suite window will appear with all tools available in the left panel.

---

## Available Tools

### 1. Curve Number (CN) Calculator
Calculate area-weighted composite curve numbers for hydrological modeling.

- Multi-layer intersection (subbasins x land use x soils)
- Split HSG handling (A/D, B/D, C/D)
- CSV/Excel lookup table support
- SWMM/HEC-HMS compatible outputs

### 2. Rational C Calculator
Calculate composite runoff coefficients for rational method analysis.

- Slope-based C value determination (0-2%, 2-6%, 6%+)
- Project-wide slope category selection
- Professional reporting formats

### 3. Time of Concentration (TC) Calculator v2.3 ⭐ ENHANCED

**Three Modes Available:**

**Mode A: Flowpath Layer Mode** (requires flowpath layer)
- TR-55 segment-based methodology
- Supports: SHEET, SHALLOW_CONC, CHANNEL, PIPE flow types
- Per-subbasin parameters (CN, C, n)
- Per-subbasin channel/pipe geometry

**Mode B: Manual Entry Mode** (no layers required)
- Enter Length, Slope, CN, C, n directly per subbasin
- Comparison methods: Kirpich, FAA, SCS Lag, Kerby
- CSV import/export for data persistence

**Mode C: DEM Extraction Mode** ⭐ NEW (requires DEM + subbasins)
- Automatic flowpath length/slope extraction from DEM
- Industry-standard flat terrain fallbacks:
  - TxDOT/Cleveland 2012: Add 0.0005 when S < 0.2%
  - NRCS minimum TC: 6 min default, 5 min paved, 10 min rural
  - Adverse slope handling for DEM errors
- SCS Lag Method with valid range warnings
- TR-55 Simplified with estimated flow types
**Comparison Methods (all modes):**
- Kirpich (1940)
- FAA (1965)
- SCS Lag/NRCS
- Kerby

### 4. Channel Designer v2.0
Design trapezoidal channel cross-sections with hydraulic calculations.

- Interactive channel visualization
- GIS layer import capability
- Manning's equation for velocity and capacity
- SWMM-compatible output format

---

## TC Calculator Workflows

### Quick Estimate (Manual Entry Mode)

1. Open TC Calculator
2. Select "Manual Entry Mode"
3. Click "Add Subbasin" for each drainage area
4. Enter: Subbasin ID, Length (ft), Slope (%), CN, C, Manning's n
5. Select output directory
6. Click "Calculate"

**CSV Template:**
```csv
subbasin_id,length_ft,slope_pct,cn,c_value,mannings_n
SB-001,2100,2.0,75,0.42,0.10
SB-002,1050,1.1,92,0.78,0.012
```

### Detailed Analysis (Flowpath Layer Mode)

1. Create flowpaths layer with fields: Subbasin_ID, Length_ft, Slope_Pct, Mannings_n, Flow_Type
2. Open TC Calculator
3. Select "Flowpath Layer Mode"
4. Select flowpaths layer
5. Map fields
6. Click "Load Subbasins from Layer"
7. Set per-subbasin parameters in **Subbasin Parameters** tab
8. Set channel geometry in **Channel Geometry** tab (optional)
9. Click "Calculate"

---

## Repository Structure

```
hydro-suite-standalone/
├── launch_hydro_suite.py       # PRIMARY LAUNCHER SCRIPT
├── hydro_suite_main.py         # Main controller and GUI window
├── hydro_suite_interface.py    # Base classes and interfaces
├── shared_widgets.py           # Reusable UI components
├── style_loader.py             # GUI theming system
├── cn_calculator_tool.py       # Curve Number Calculator
├── rational_c_tool.py          # Rational C Calculator
├── tc_calculator_tool.py       # TC Calculator v2.3 (3 modes)
├── dem_extraction.py           # DEM-based flowpath extraction (NEW)
├── channel_designer_tool.py    # Channel Designer v2.0
├── validation_calculations.py  # Hand calculation verification
├── example_data/               # Sample data and lookup tables
├── README.md
├── CHANGELOG.md
├── HANDOFF.md
└── ...
```

---

## GUI Theming

Hydro Suite supports 9 visual themes switchable at runtime:

| Theme | Mode | Description |
|-------|------|-------------|
| Normal (Default) | Light | Classic appearance |
| Kinetic (Dark) | Dark | High-energy brutalist |
| Bauhaus (Light) | Light | Geometric modernist |
| Enterprise (Light) | Light | Corporate SaaS |
| Cyberpunk (Dark) | Dark | Neon dystopian |
| Academia (Dark) | Dark | Scholarly classical |
| Sketch (Light) | Light | Hand-drawn playful |
| Playful Geometric (Light) | Light | Memphis bouncy |
| Twisty (Dark) | Dark | Fintech modern |

Use the **Style dropdown** in the toolbar or **View > GUI Style** menu.

---

## Validation

Run the validation script to verify calculations against hand calcs:

```python
exec(open(r'C:\path\to\hydro-suite-standalone\validation_calculations.py').read())
```

---

## Requirements

- **QGIS**: Version 3.40 or higher
- **Python**: 3.9+ (included with QGIS)
- **Dependencies**: All included with QGIS (PyQt5, pandas)

---

## Documentation

| Document | Description |
|----------|-------------|
| [HANDOFF.md](HANDOFF.md) | Current state and usage guide |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
| [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) | How to extend and modify tools |

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| **2.3.0** | Jan 2025 | TC Calculator DEM Extraction Mode + flat terrain fallbacks |
| 2.2.0 | Jan 2025 | TC Calculator Manual Entry Mode (no flowpath layer required) |
| 2.0.0 | Jan 2025 | TC Calculator rewrite, Channel Designer GIS import |
| 1.2.0 | Jan 2025 | Example data, lookup tables, tutorials |
| 1.1.0 | Jan 2025 | Multi-style GUI theming system |
| 1.0.0 | Jan 2025 | Initial standalone release |

See [CHANGELOG.md](CHANGELOG.md) for detailed version history.

---

## License

MIT License - See [LICENSE](LICENSE) for details.

---

## Author

**Joey Woody, PE**  
J. Bragg Consulting Inc.  
Civil/Water Resources Engineer
