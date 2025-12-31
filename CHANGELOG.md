# Changelog

All notable changes to Hydro Suite Standalone will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
| 1.1.0 | 2025-01-01 | Multi-style GUI theming system |
| 1.0.0 | 2025-01-31 | Initial standalone release |

---

## Migration Notes

### From Plugin to Standalone

If migrating from the plugin version:
1. The standalone version uses flat file structure (no subdirectories)
2. Launch via Python Console exec() instead of plugin menu
3. All functionality is preserved
4. Settings may need to be reconfigured

---

**Author**: Joey Woody, PE - J. Bragg Consulting Inc.
