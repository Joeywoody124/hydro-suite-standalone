# Hydro Suite - Standalone Scripts for QGIS

**Version**: 1.1.0  
**Status**: Production Ready  
**Last Updated**: January 2025  
**QGIS Compatibility**: 3.40+  
**Author**: Joey Woody, PE - J. Bragg Consulting Inc.

---

## Important: This is the Standalone Script Version

This repository contains the **standalone script version** of Hydro Suite, designed to run directly in the QGIS Python Console without plugin installation.

| Version | Repository | Status |
|---------|------------|--------|
| **Standalone Scripts (This Repo)** | [hydro-suite-standalone](https://github.com/Joeywoody124/hydro-suite-standalone) | Working |
| QGIS Plugin Version | [hydro-suite](https://github.com/Joeywoody124/hydro-suite) | Needs Fixes |

---

## What's New in v1.1.0

**Multi-Style GUI Theming** - Switch between 9 visual themes at runtime!

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
# ============================================================
# HYDRO SUITE STANDALONE LAUNCHER
# Update the path below to your installation location
# ============================================================

exec(open(r'C:\path\to\hydro-suite-standalone\launch_hydro_suite.py').read())
```

**Example paths:**
```python
# Windows example:
exec(open(r'E:\GitHub\hydro-suite-standalone\launch_hydro_suite.py').read())

# Another Windows path:
exec(open(r'C:\Users\YourName\Documents\hydro-suite-standalone\launch_hydro_suite.py').read())
```

### Step 3: Use the Tools

Once launched, the Hydro Suite window will appear with all tools available in the left panel.

---

## Repository Structure

```
hydro-suite-standalone/
│
├── launch_hydro_suite.py       # PRIMARY LAUNCHER SCRIPT
│
├── hydro_suite_main.py         # Main controller and GUI window
├── hydro_suite_interface.py    # Base classes and interfaces
├── shared_widgets.py           # Reusable UI components
├── style_loader.py             # GUI theming system (NEW in v1.1)
│
├── cn_calculator_tool.py       # Curve Number Calculator
├── rational_c_tool.py          # Rational C Calculator
├── tc_calculator_tool.py       # Time of Concentration Calculator
├── channel_designer_tool.py    # Trapezoidal Channel Designer
│
├── DEVELOPER_GUIDE.md          # Development patterns and extension guide
├── CHANGELOG.md                # Version history
├── CONTRIBUTING.md             # Contribution guidelines
├── HANDOFF_GUI_STYLES.md       # GUI customization implementation guide
│
├── .gitignore
├── LICENSE
└── README.md                   # This file
```

**Note**: All files are in a flat structure for simplicity. This makes imports straightforward when running from the QGIS Python Console.

---

## Available Tools

### 1. Curve Number (CN) Calculator
Calculate area-weighted composite curve numbers for hydrological modeling.

**Features:**
- Multi-layer intersection (subbasins x land use x soils)
- Split HSG handling (A/D, B/D, C/D)
- CSV/Excel lookup table support
- SWMM/HEC-HMS compatible outputs

### 2. Rational C Calculator
Calculate composite runoff coefficients for rational method analysis.

**Features:**
- Slope-based C value determination (0-2%, 2-6%, 6%+)
- Project-wide slope category selection
- Unrecognized soil group handling
- Professional reporting formats

### 3. Time of Concentration (TC) Calculator
Calculate time of concentration using multiple industry-standard methods.

**Methods Included:**
- Kirpich (1940)
- FAA (1965)
- SCS/NRCS (1972)
- Kerby

### 4. Channel Designer
Design trapezoidal channel cross-sections with hydraulic calculations.

**Features:**
- Interactive channel visualization
- Real-time hydraulic property calculations
- SWMM-compatible output format
- Batch processing from CSV

---

## GUI Theming

Hydro Suite supports 9 visual themes that can be switched at runtime:

1. **Toolbar**: Use the "Style:" dropdown at the top
2. **Menu**: Go to `View` > `GUI Style` and select a theme

Your theme preference is automatically saved between sessions.

### Theme Dependencies

The advanced themes (Kinetic, Bauhaus, etc.) load tokens from the GUI Design Center Library. If the library is not available, the application gracefully falls back to the "Normal (Default)" theme.

**Library Location**: `E:\CLAUDE_Workspace\Claude\Report_Files\GUI_Design_Center_Library\styles`

To use without the library, simply use the "Normal (Default)" theme which has all styles built-in.

---

## Requirements

- **QGIS**: Version 3.40 or higher
- **Python**: 3.9+ (included with QGIS)
- **Dependencies**: All dependencies are included with QGIS installation
  - PyQt5
  - pandas
  - QGIS Processing Framework

---

## Troubleshooting

### Common Issues

**1. "Module not found" errors**

Ensure the launcher script path is correct and all files are in the same directory.

```python
# Check if files exist
import os
script_dir = r'C:\path\to\hydro-suite-standalone'
print(os.listdir(script_dir))
```

**2. Window doesn't appear**

Try closing any existing Hydro Suite windows first:

```python
# Close existing window if open
try:
    hydro_suite_window.close()
except:
    pass

# Then relaunch
exec(open(r'C:\path\to\hydro-suite-standalone\launch_hydro_suite.py').read())
```

**3. Import errors in QGIS Console**

Restart QGIS and try again. The Python environment sometimes needs a fresh start.

**4. Theme not loading**

If a theme doesn't load, check that the GUI Design Center Library path is accessible. The application will fall back to "Normal (Default)" if theme files are missing.

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Then launch
exec(open(r'C:\path\to\hydro-suite-standalone\launch_hydro_suite.py').read())
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) | How to extend and modify tools |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution guidelines |
| [HANDOFF_GUI_STYLES.md](HANDOFF_GUI_STYLES.md) | GUI theming implementation details |
| [example_data/README.md](example_data/README.md) | Lookup tables and example data documentation |

---

## Example Data and Lookup Tables

The `example_data/` folder contains reference tables and sample data:

| File | Description |
|------|-------------|
| `cn_lookup_table.csv` | Curve Number by Land Use and HSG (TR-55) |
| `cn_lookup_split_hsg.csv` | CN with dual HSG support (A/D, B/D, C/D) |
| `c_lookup_table.csv` | Rational C by Land Use and Slope (ASCE) |
| `example_subbasins.csv` | Sample watershed/subbasin data |
| `example_channels.csv` | Sample channel design parameters |
| `example_tc_flowpaths.csv` | Sample TC flow path data |

See [example_data/README.md](example_data/README.md) for detailed documentation and references.

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-tool`)
3. Follow the patterns in `DEVELOPER_GUIDE.md`
4. Test thoroughly in QGIS
5. Submit a Pull Request

### Code Style
- PEP 8 compliant
- Inline comments preferred
- Type hints where appropriate
- Comprehensive docstrings

---

## License

MIT License - See [LICENSE](LICENSE) for details.

---

## Author

**Joey Woody, PE**  
J. Bragg Consulting Inc.  
Civil/Water Resources Engineer

---

## Related Projects

- [hydro-suite](https://github.com/Joeywoody124/hydro-suite) - QGIS Plugin version (currently needs fixes)

---

## Version History

See [CHANGELOG.md](CHANGELOG.md) for detailed version history.

### v1.1.0 (January 2025)
- Multi-style GUI theming system (9 themes)
- Style preference persistence
- Toolbar style selector

### v1.0.0 (January 2025)
- Initial standalone release
- Four integrated tools (CN, Rational C, TC, Channel Designer)
- Professional GUI with real-time validation
- Comprehensive documentation
