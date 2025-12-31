"""
Hydro Suite - Main Controller (Standalone Version)
Unified hydrological analysis toolbox for QGIS 3.40+
Version 1.1 - 2025

STANDALONE SCRIPT VERSION
Repository: https://github.com/Joeywoody124/hydro-suite-standalone

This is the standalone script version that runs in QGIS Python Console.
For the plugin version (currently needs fixes), see:
https://github.com/Joeywoody124/hydro-suite.git

Features:
- Multi-style GUI theming (Normal, Kinetic, Bauhaus, etc.)
- Curve Number Calculator
- Rational C Calculator
- Time of Concentration Calculator
- Channel Designer
"""

import os
import sys
import importlib
import json
from pathlib import Path
from typing import Dict, Optional, Any

from qgis.PyQt.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QStackedWidget,
    QLabel, QPushButton, QProgressBar, QMessageBox,
    QFrame, QSplitter, QTextEdit, QToolBar, QAction,
    QMenuBar, QMenu, QStatusBar, QComboBox
)
from qgis.PyQt.QtCore import Qt, QSettings, pyqtSignal, QThread
from qgis.PyQt.QtGui import QIcon, QFont, QPixmap
from qgis.core import QgsProject, QgsMessageLog, Qgis
from qgis.gui import QgsGui

# Import the tool interface base class
from hydro_suite_interface import HydroToolInterface

# Import style system
from style_loader import StyleLoader, STYLE_MAP


class HydroSuiteController:
    """Main controller for the Hydro Suite toolbox"""
    
    def __init__(self):
        self.tools_registry = {}
        self.settings = QSettings("HydroSuite", "MainController")
        self.components_path = Path(__file__).parent / "Components"
        self.resources_path = Path(__file__).parent / "Resources"
        
        # Initialize logging
        QgsMessageLog.logMessage("Hydro Suite Controller initializing...", "HydroSuite", Qgis.Info)
        
        # Load available tools
        self.discover_tools()
    
    def discover_tools(self):
        """Discover and register available tools"""
        # Define tool configurations
        tool_configs = {
            "cn_calculator": {
                "name": "Curve Number Calculator",
                "module": "cn_calculator_tool",
                "class": "CNCalculatorTool",
                "icon": "cn_icon.png",
                "category": "Runoff Analysis",
                "description": "Calculate area-weighted composite curve numbers for hydrological modeling"
            },
            "c_calculator": {
                "name": "Rational C Calculator",
                "module": "rational_c_tool",
                "class": "RationalCTool",
                "icon": "c_icon.png",
                "category": "Runoff Analysis",
                "description": "Calculate composite runoff coefficients for rational method analysis"
            },
            "tc_calculator": {
                "name": "Time of Concentration",
                "module": "tc_calculator_tool",
                "class": "TCCalculatorTool",
                "icon": "tc_icon.png",
                "category": "Watershed Analysis",
                "description": "Calculate time of concentration using multiple methods"
            },
            "channel_designer": {
                "name": "Channel Designer",
                "module": "channel_designer_tool",
                "class": "ChannelDesignerTool",
                "icon": "channel_icon.png",
                "category": "Hydraulic Design",
                "description": "Design trapezoidal channel cross-sections with SWMM integration"
            }
        }
        
        # Register each tool
        for tool_id, config in tool_configs.items():
            self.register_tool(tool_id, config)
            
        QgsMessageLog.logMessage(
            f"Discovered {len(self.tools_registry)} tools", 
            "HydroSuite", 
            Qgis.Info
        )
    
    def register_tool(self, tool_id: str, config: Dict[str, Any]):
        """Register a tool in the registry"""
        self.tools_registry[tool_id] = {
            "id": tool_id,
            "config": config,
            "instance": None,
            "loaded": False
        }
    
    def load_tool(self, tool_id: str) -> Optional[HydroToolInterface]:
        """Load a tool instance (lazy loading)"""
        if tool_id not in self.tools_registry:
            QgsMessageLog.logMessage(
                f"Tool {tool_id} not found in registry", 
                "HydroSuite", 
                Qgis.Warning
            )
            return None
        
        tool_info = self.tools_registry[tool_id]
        
        if tool_info["loaded"] and tool_info["instance"]:
            return tool_info["instance"]
        
        try:
            QgsMessageLog.logMessage(
                f"Loading tool: {tool_id}", 
                "HydroSuite", 
                Qgis.Info
            )
            
            tool_info["instance"] = self.create_tool_wrapper(tool_id, tool_info["config"])
            tool_info["loaded"] = True
            
            return tool_info["instance"]
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Error loading tool {tool_id}: {str(e)}", 
                "HydroSuite", 
                Qgis.Critical
            )
            return None
    
    def create_tool_wrapper(self, tool_id: str, config: Dict[str, Any]) -> HydroToolInterface:
        """Create a wrapper for tools"""
        
        # Import actual tools
        if tool_id == "cn_calculator":
            from cn_calculator_tool import CNCalculatorTool
            return CNCalculatorTool()
        elif tool_id == "c_calculator":
            from rational_c_tool import RationalCTool
            return RationalCTool()
        elif tool_id == "tc_calculator":
            from tc_calculator_tool import TCCalculatorTool
            return TCCalculatorTool()
        elif tool_id == "channel_designer":
            from channel_designer_tool import ChannelDesignerTool
            return ChannelDesignerTool()
        
        # Return mock for unimplemented tools
        class MockTool(HydroToolInterface):
            def __init__(self):
                super().__init__()
                self.name = config["name"]
                self.description = config["description"]
                self.category = config["category"]
            
            def create_gui(self, parent_widget):
                widget = QWidget(parent_widget)
                layout = QVBoxLayout(widget)
                layout.addWidget(QLabel(f"<h2>{self.name}</h2>"))
                layout.addWidget(QLabel("Tool under development"))
                layout.addStretch()
                return widget
            
            def validate_inputs(self):
                return True, ""
            
            def run(self, progress_callback):
                return True
        
        return MockTool()
    
    def get_tool_categories(self) -> Dict[str, list]:
        """Get tools organized by category"""
        categories = {}
        for tool_id, tool_info in self.tools_registry.items():
            category = tool_info["config"]["category"]
            if category not in categories:
                categories[category] = []
            categories[category].append(tool_id)
        return categories


class HydroSuiteMainWindow(QMainWindow):
    """Main window for the Hydro Suite toolbox"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.controller = HydroSuiteController()
        self.current_tool = None
        
        # Initialize style system
        self.style_loader = StyleLoader()
        self.current_style_name = "Normal (Default)"
        
        self.setWindowTitle("Hydro Suite - Standalone Scripts for QGIS")
        self.setMinimumSize(1000, 700)
        
        self.setup_ui()
        self.setup_menu()
        self.setup_toolbar()
        self.setup_statusbar()
        self.load_settings()
        
        # Apply initial style (use saved preference or default)
        saved_style = QSettings("HydroSuite", "MainWindow").value("gui_style", "Kinetic (Dark)")
        if saved_style in self.style_loader.get_available_styles():
            self.style_combo.setCurrentText(saved_style)
            self._apply_style(saved_style)
        else:
            self._apply_style("Kinetic (Dark)")
        
        if self.tool_list.count() > 0:
            self.tool_list.setCurrentRow(0)
    
    def setup_ui(self):
        """Setup the main UI layout"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        splitter.setSizes([300, 700])
    
    def create_left_panel(self) -> QWidget:
        """Create the left tool selection panel"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        panel.setMinimumWidth(250)
        
        layout = QVBoxLayout(panel)
        
        self.tools_title = QLabel("Available Tools")
        self.tools_title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                padding: 10px;
                background-color: #2c3e50;
                color: white;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.tools_title)
        
        self.tool_list = QListWidget()
        
        categories = self.controller.get_tool_categories()
        for category, tool_ids in categories.items():
            category_item = QListWidgetItem(f"-- {category} --")
            category_item.setFlags(Qt.NoItemFlags)
            category_item.setFont(QFont("Arial", 10, QFont.Bold))
            self.tool_list.addItem(category_item)
            
            for tool_id in tool_ids:
                tool_info = self.controller.tools_registry[tool_id]
                tool_item = QListWidgetItem(f"  > {tool_info['config']['name']}")
                tool_item.setData(Qt.UserRole, tool_id)
                self.tool_list.addItem(tool_item)
        
        self.tool_list.currentItemChanged.connect(self.on_tool_selected)
        layout.addWidget(self.tool_list)
        
        self.info_btn = QPushButton("About Selected Tool")
        self.info_btn.clicked.connect(self.show_tool_info)
        layout.addWidget(self.info_btn)
        
        return panel
    
    def create_right_panel(self) -> QWidget:
        """Create the right panel with tool interface and log"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        
        v_splitter = QSplitter(Qt.Vertical)
        layout.addWidget(v_splitter)
        
        self.tool_stack = QStackedWidget()
        self.tool_stack.setMinimumHeight(400)
        
        welcome = self.create_welcome_screen()
        self.tool_stack.addWidget(welcome)
        
        v_splitter.addWidget(self.tool_stack)
        
        log_frame = QFrame()
        log_frame.setFrameStyle(QFrame.StyledPanel)
        log_frame.setMaximumHeight(200)
        
        log_layout = QVBoxLayout(log_frame)
        
        self.log_header = QLabel("Processing Log")
        log_layout.addWidget(self.log_header)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        v_splitter.addWidget(log_frame)
        v_splitter.setSizes([500, 200])
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        return panel
    
    def create_welcome_screen(self) -> QWidget:
        """Create the welcome screen"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)
        
        self.welcome_logo = QLabel("~")
        self.welcome_logo.setStyleSheet("font-size: 64px;")
        self.welcome_logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.welcome_logo)
        
        self.welcome_title = QLabel("Welcome to Hydro Suite")
        self.welcome_title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                margin: 20px;
            }
        """)
        self.welcome_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.welcome_title)
        
        self.welcome_version = QLabel(
            "<b>Standalone Scripts Version 1.1</b><br>"
            "Runs in QGIS Python Console<br><br>"
            "Repository: github.com/Joeywoody124/hydro-suite-standalone"
        )
        self.welcome_version.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.welcome_version)
        
        self.welcome_desc = QLabel("Select a tool from the left panel to begin.")
        self.welcome_desc.setStyleSheet("font-size: 14px; margin: 20px;")
        self.welcome_desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.welcome_desc)
        
        self.welcome_stats = QLabel(f"[OK] {len(self.controller.tools_registry)} tools available")
        self.welcome_stats.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.welcome_stats)
        
        return widget
    
    def setup_menu(self):
        """Setup the menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu (for style selection)
        view_menu = menubar.addMenu("&View")
        
        style_menu = view_menu.addMenu("GUI Style")
        for style_name in self.style_loader.get_available_styles():
            action = QAction(style_name, self)
            action.triggered.connect(lambda checked, s=style_name: self._apply_style(s))
            style_menu.addAction(action)
        
        # Tools menu
        tools_menu = menubar.addMenu("&Tools")
        categories = self.controller.get_tool_categories()
        for category, tool_ids in categories.items():
            category_menu = tools_menu.addMenu(category)
            for tool_id in tool_ids:
                tool_info = self.controller.tools_registry[tool_id]
                action = QAction(tool_info['config']['name'], self)
                action.setData(tool_id)
                action.triggered.connect(lambda checked, tid=tool_id: self.select_tool(tid))
                category_menu.addAction(action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about = QAction("&About Hydro Suite", self)
        about.triggered.connect(self.show_about)
        help_menu.addAction(about)
    
    def setup_toolbar(self):
        """Setup the toolbar with style selector"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Style selector
        style_label = QLabel("  Style: ")
        toolbar.addWidget(style_label)
        
        self.style_combo = QComboBox()
        self.style_combo.addItems(self.style_loader.get_available_styles())
        self.style_combo.setCurrentText("Kinetic (Dark)")
        self.style_combo.currentTextChanged.connect(self._on_style_change)
        self.style_combo.setMinimumWidth(180)
        toolbar.addWidget(self.style_combo)
        
        toolbar.addSeparator()
        
        # Run button
        run_action = QAction("Run", self)
        run_action.setShortcut("F5")
        run_action.triggered.connect(self.run_current_tool)
        toolbar.addAction(run_action)
        
        toolbar.addSeparator()
        
        # Help button
        help_action = QAction("Help", self)
        help_action.setShortcut("F1")
        help_action.triggered.connect(self.show_about)
        toolbar.addAction(help_action)
    
    def setup_statusbar(self):
        """Setup the status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready - Standalone Scripts Version")
    
    def _on_style_change(self, style_name: str):
        """Handle style dropdown change"""
        self._apply_style(style_name)
    
    def _apply_style(self, style_name: str):
        """Apply selected style to the entire application"""
        style = self.style_loader.load_style(style_name)
        if not style:
            self.log(f"Failed to load style: {style_name}", level="error")
            return
        
        self.current_style_name = style_name
        
        # Generate and apply stylesheet
        stylesheet = self.style_loader.generate_stylesheet(style)
        self.setStyleSheet(stylesheet)
        
        # Update style combo if called from menu
        if self.style_combo.currentText() != style_name:
            self.style_combo.blockSignals(True)
            self.style_combo.setCurrentText(style_name)
            self.style_combo.blockSignals(False)
        
        # Save preference
        QSettings("HydroSuite", "MainWindow").setValue("gui_style", style_name)
        
        # Update status bar
        self.status_bar.showMessage(f"Style: {style['name']} | Ready")
        
        # Log the change
        self.log(f"Applied GUI style: {style_name}")
    
    def on_tool_selected(self, current, previous):
        """Handle tool selection change"""
        if not current:
            return
        
        tool_id = current.data(Qt.UserRole)
        if not tool_id:
            return
        
        self.select_tool(tool_id)
    
    def select_tool(self, tool_id: str):
        """Select and load a tool"""
        self.log(f"Loading {tool_id}...")
        
        tool = self.controller.load_tool(tool_id)
        if not tool:
            self.log(f"Failed to load {tool_id}", level="error")
            return
        
        if tool_id not in [self.tool_stack.widget(i).property("tool_id") 
                          for i in range(self.tool_stack.count())]:
            tool_widget = tool.create_gui(self.tool_stack)
            tool_widget.setProperty("tool_id", tool_id)
            self.tool_stack.addWidget(tool_widget)
        
        for i in range(self.tool_stack.count()):
            if self.tool_stack.widget(i).property("tool_id") == tool_id:
                self.tool_stack.setCurrentIndex(i)
                break
        
        self.current_tool = tool
        self.status_bar.showMessage(f"Style: {self.current_style_name} | Loaded: {tool.name}")
        self.log(f"Tool {tool.name} ready")
    
    def run_current_tool(self):
        """Run the currently selected tool"""
        if not self.current_tool:
            QMessageBox.warning(self, "No Tool Selected", 
                              "Please select a tool before running.")
            return
        
        valid, message = self.current_tool.validate_inputs()
        if not valid:
            QMessageBox.warning(self, "Validation Error", message)
            return
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        def progress_callback(value, message=""):
            self.progress_bar.setValue(value)
            if message:
                self.status_bar.showMessage(f"Style: {self.current_style_name} | {message}")
        
        try:
            self.log(f"Running {self.current_tool.name}...")
            self.current_tool.run(progress_callback)
            self.log(f"{self.current_tool.name} completed successfully", level="success")
        except Exception as e:
            self.log(f"Error running {self.current_tool.name}: {str(e)}", level="error")
            QMessageBox.critical(self, "Execution Error", str(e))
        finally:
            self.progress_bar.setVisible(False)
            self.status_bar.showMessage(f"Style: {self.current_style_name} | Ready")
    
    def show_tool_info(self):
        """Show information about the selected tool"""
        current = self.tool_list.currentItem()
        if not current:
            return
        
        tool_id = current.data(Qt.UserRole)
        if not tool_id:
            return
        
        tool_info = self.controller.tools_registry[tool_id]
        config = tool_info['config']
        
        info_text = f"""
<h3>{config['name']}</h3>
<p><b>Category:</b> {config['category']}</p>
<p><b>Description:</b> {config['description']}</p>
"""
        
        QMessageBox.information(self, "Tool Information", info_text)
    
    def show_about(self):
        """Show about dialog"""
        about_text = f"""
<h2>Hydro Suite - Standalone Scripts</h2>
<p>Version 1.1 - 2025</p>
<p>A comprehensive QGIS toolbox for hydrological and stormwater analysis.</p>

<p><b>This is the Standalone Scripts Version</b></p>
<p>Runs directly in QGIS Python Console without plugin installation.</p>

<p><b>Repository:</b> github.com/Joeywoody124/hydro-suite-standalone</p>

<p><b>Features:</b></p>
<ul>
<li>Multi-Style GUI Theming ({len(self.style_loader.get_available_styles())} styles)</li>
<li>Curve Number Calculator</li>
<li>Rational Method C Calculator</li>
<li>Time of Concentration (Multi-Method)</li>
<li>Trapezoidal Channel Designer</li>
</ul>

<p><b>Current Style:</b> {self.current_style_name}</p>

<p><b>Author:</b> Joey Woody, PE</p>
<p><b>Company:</b> J. Bragg Consulting Inc.</p>
"""
        QMessageBox.about(self, "About Hydro Suite", about_text)
    
    def log(self, message: str, level: str = "info"):
        """Add message to log"""
        QgsMessageLog.logMessage(message, "HydroSuite", 
                                getattr(Qgis, level.capitalize(), Qgis.Info))
        
        colors = {
            "info": "#888888",
            "warning": "#ff9800",
            "error": "#f44336",
            "success": "#4caf50"
        }
        color = colors.get(level, "#888888")
        
        self.log_text.append(f'<span style="color: {color}">[{level.upper()}] {message}</span>')
    
    def load_settings(self):
        """Load saved settings"""
        settings = QSettings("HydroSuite", "MainWindow")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
    
    def save_settings(self):
        """Save current settings"""
        settings = QSettings("HydroSuite", "MainWindow")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("gui_style", self.current_style_name)
    
    def closeEvent(self, event):
        """Handle window close event"""
        self.save_settings()
        event.accept()


def run_hydro_suite():
    """Main entry point for Hydro Suite"""
    window = HydroSuiteMainWindow()
    window.show()
    return window


if __name__ == "__main__":
    window = run_hydro_suite()
