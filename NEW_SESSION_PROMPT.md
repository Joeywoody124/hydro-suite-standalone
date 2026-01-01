# Hydro Suite Bug Fix Session Prompt

Copy and paste this into a new Claude session to continue working on Hydro Suite.

---

## Prompt to Paste:

```
I need help debugging and testing Hydro Suite, a QGIS Python Console-based hydrological analysis toolbox.

**Repository**: https://github.com/Joeywoody124/hydro-suite-standalone

**Local Path**: E:\CLAUDE_Workspace\Claude\Report_Files\Finished_Code\Hydro_Suite_Data_Backup_v1\github_standalone

**Current Version**: 1.2.0

## What's Working
- Main GUI framework with 9-theme styling system
- CN Calculator (tested with sample data)
- Rational C Calculator (tested with sample data)
- Sample GIS layer generator (`create_sample_layers.py`)
- Lookup tables (CN and Rational C)

## What Needs Testing/Fixing

### Priority 1: Test Remaining Tools
1. **TC Calculator** - Run full workflow with sample flowpaths layer
2. **Channel Designer** - Run full workflow with sample channels layer

### Priority 2: Known Issues
1. Better error messages when layers don't spatially overlap
2. Validate split HSG handling (A/D, B/D, C/D soils) in CN Calculator
3. Test with real project data (not just sample layers)

### Priority 3: Enhancements
1. SWMM export format validation
2. Report generation improvements

## Key Files
- `launch_hydro_suite.py` - Entry point
- `tc_calculator_tool.py` - TC tool (needs testing)
- `channel_designer_tool.py` - Channel tool (needs testing)
- `example_data/create_sample_layers.py` - Generates test GIS layers
- `HANDOFF.md` - Full status and documentation

## How to Launch in QGIS
```python
exec(open(r'E:\CLAUDE_Workspace\Claude\Report_Files\Finished_Code\Hydro_Suite_Data_Backup_v1\github_standalone\launch_hydro_suite.py').read())
```

## How to Generate Sample Layers
```python
exec(open(r'E:\CLAUDE_Workspace\Claude\Report_Files\Finished_Code\Hydro_Suite_Data_Backup_v1\github_standalone\example_data\create_sample_layers.py').read())
create_sample_data()
```

Please start by reading the HANDOFF.md file to understand the current state, then help me test and fix issues.
```

---

## Files to Read First

1. `HANDOFF.md` - Current status, file structure, testing checklist
2. `tc_calculator_tool.py` - If testing TC tool
3. `channel_designer_tool.py` - If testing Channel Designer
4. `TUTORIALS.md` - Step-by-step usage guides

---

*Created: January 2025*
