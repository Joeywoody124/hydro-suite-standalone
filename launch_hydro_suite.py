"""
Hydro Suite - Standalone Launcher for QGIS Python Console
=========================================================

USAGE:
------
In QGIS Python Console, run:

    exec(open(r'PATH_TO_THIS_FILE\launch_hydro_suite.py').read())

Example:
    exec(open(r'E:\GitHub\hydro-suite-standalone\launch_hydro_suite.py').read())

This launcher auto-detects its location and loads all required modules.

Version: 1.0.0
Repository: https://github.com/Joeywoody124/hydro-suite-standalone
Author: Joey Woody, PE - J. Bragg Consulting Inc.
"""

import sys
import os
import importlib.util


def launch_hydro_suite():
    """
    Main launcher function for Hydro Suite standalone scripts.
    Auto-detects the script directory and loads all modules.
    """
    print("=" * 60)
    print("HYDRO SUITE - Standalone Scripts for QGIS")
    print("=" * 60)
    print("Version: 1.0.0")
    print("Repository: https://github.com/Joeywoody124/hydro-suite-standalone")
    print("-" * 60)
    
    # Auto-detect script directory
    # When using exec(open(...).read()), __file__ isn't available
    # So we need to find it from the call stack or use a known location
    
    script_dir = None
    
    # Method 1: Check if __file__ is defined (won't work with exec)
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        print(f"Detected directory from __file__: {script_dir}")
    except NameError:
        pass
    
    # Method 2: Check common locations if Method 1 failed
    if script_dir is None or not os.path.exists(os.path.join(script_dir, 'hydro_suite_main.py')):
        # List of possible locations to check
        # Add your installation path here if auto-detection fails
        possible_locations = [
            # GitHub repository locations
            r'E:\GitHub\hydro-suite-standalone',
            r'C:\Users\Public\Documents\hydro-suite-standalone',
            # Development locations
            r'E:\CLAUDE_Workspace\Claude\Report_Files\Finished_Code\Hydro_Suite_Data_Backup_v1\github_standalone',
            # User-specific locations
            os.path.expanduser('~/Documents/hydro-suite-standalone'),
            os.path.expanduser('~/GitHub/hydro-suite-standalone'),
        ]
        
        for loc in possible_locations:
            if os.path.exists(loc) and os.path.exists(os.path.join(loc, 'hydro_suite_main.py')):
                script_dir = loc
                print(f"Found installation at: {script_dir}")
                break
    
    # If still not found, prompt user
    if script_dir is None or not os.path.exists(os.path.join(script_dir, 'hydro_suite_main.py')):
        print("\nERROR: Could not find Hydro Suite installation directory.")
        print("\nPlease edit this file and add your installation path to 'possible_locations'")
        print("Or use the manual launcher below:\n")
        print("    script_dir = r'YOUR_PATH_HERE'")
        print("    exec(open(os.path.join(script_dir, 'launch_hydro_suite.py')).read())")
        return None
    
    print(f"\nLoading from: {script_dir}")
    
    # Add to sys.path if not already there
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
        print("Added to Python path")
    
    # Helper function to load modules from file
    def load_module_from_file(module_name, file_path):
        """Load a module directly from file path"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Module file not found: {file_path}")
        
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None:
            raise ImportError(f"Could not load spec for {module_name}")
        
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    
    # List of modules to load in dependency order
    modules_to_load = [
        ('shared_widgets', 'shared_widgets.py'),
        ('hydro_suite_interface', 'hydro_suite_interface.py'),
        ('style_loader', 'style_loader.py'),  # GUI theming system
        ('cn_calculator_tool', 'cn_calculator_tool.py'),
        ('rational_c_tool', 'rational_c_tool.py'),
        ('tc_calculator_tool', 'tc_calculator_tool.py'),
        ('channel_designer_tool', 'channel_designer_tool.py'),
        ('hydro_suite_main', 'hydro_suite_main.py'),
    ]
    
    print("\nLoading modules...")
    
    try:
        for module_name, file_name in modules_to_load:
            file_path = os.path.join(script_dir, file_name)
            print(f"   Loading {module_name}...", end=" ")
            load_module_from_file(module_name, file_path)
            print("OK")
        
        print("\nLaunching Hydro Suite GUI...")
        
        # Close existing window if open
        global hydro_suite_window
        try:
            if 'hydro_suite_window' in globals() and hydro_suite_window:
                hydro_suite_window.close()
                hydro_suite_window.deleteLater()
                print("   Closed previous window")
        except:
            pass
        
        # Import and create main window
        from hydro_suite_main import HydroSuiteMainWindow
        
        hydro_suite_window = HydroSuiteMainWindow()
        hydro_suite_window.show()
        
        print("\n" + "=" * 60)
        print("HYDRO SUITE LAUNCHED SUCCESSFULLY!")
        print("=" * 60)
        print("\nQuick Guide:")
        print("   1. Select a tool from the left panel")
        print("   2. Configure inputs (watch for validation)")
        print("   3. Click 'Run' when all inputs are valid")
        print("\nDocumentation: See README.md and DEVELOPER_GUIDE.md")
        print("Issues: https://github.com/Joeywoody124/hydro-suite-standalone/issues")
        print("-" * 60)
        
        return hydro_suite_window
        
    except FileNotFoundError as e:
        print(f"\nFILE NOT FOUND: {e}")
        print("\nMake sure all required files are in the same directory:")
        for _, file_name in modules_to_load:
            file_path = os.path.join(script_dir, file_name)
            status = "OK" if os.path.exists(file_path) else "MISSING"
            print(f"   [{status}] {file_name}")
        return None
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        print(f"\nFull traceback:\n{traceback.format_exc()}")
        return None


# ============================================================
# LAUNCH THE APPLICATION
# ============================================================
launch_hydro_suite()
