"""
Shared GUI Widgets for Hydro Suite
Common components used across multiple tools
Version 1.0 - 2025

Repository: https://github.com/Joeywoody124/hydro-suite-standalone
"""

import os
from pathlib import Path
from typing import Optional, List, Callable

from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QPushButton, QRadioButton, QButtonGroup, QFrame, QGroupBox,
    QFileDialog, QMessageBox, QProgressBar, QTextEdit
)
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QFont

from qgis.core import QgsProject, QgsVectorLayer, QgsWkbTypes
from qgis.gui import QgsFileWidget


class LayerFieldSelector(QWidget):
    """Widget for selecting a layer and field with validation"""
    
    # Signals
    layer_changed = pyqtSignal(QgsVectorLayer)
    field_changed = pyqtSignal(str)
    selection_valid = pyqtSignal(bool)
    
    def __init__(self, title: str, default_field: str = "", 
                 geometry_type: Optional[int] = None, parent=None):
        """
        Initialize layer and field selector
        
        Args:
            title: Display title for the selector
            default_field: Default field name to select
            geometry_type: Filter by geometry type (0=point, 1=line, 2=polygon)
            parent: Parent widget
        """
        super().__init__(parent)
        self.title = title
        self.default_field = default_field
        self.geometry_type = geometry_type
        self.selected_layer = None
        
        self.setup_ui()
        self.update_layer_list()
        
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Group box for this selector
        self.group_box = QGroupBox(self.title)
        group_layout = QVBoxLayout(self.group_box)
        
        # Selection method radio buttons
        method_layout = QHBoxLayout()
        self.button_group = QButtonGroup()
        
        self.radio_project = QRadioButton("Use project layer")
        self.radio_file = QRadioButton("Browse for file")
        self.radio_project.setChecked(True)
        
        self.button_group.addButton(self.radio_project, 1)
        self.button_group.addButton(self.radio_file, 2)
        
        method_layout.addWidget(self.radio_project)
        method_layout.addWidget(self.radio_file)
        method_layout.addStretch()
        
        group_layout.addLayout(method_layout)
        
        # Layer selection
        layer_layout = QHBoxLayout()
        layer_layout.addWidget(QLabel("Layer:"))
        
        self.combo_layers = QComboBox()
        self.combo_layers.setMinimumWidth(250)
        layer_layout.addWidget(self.combo_layers, 1)
        
        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setMaximumWidth(30)
        self.btn_refresh.setToolTip("Refresh layer list")
        layer_layout.addWidget(self.btn_refresh)
        
        group_layout.addLayout(layer_layout)
        
        # File selection (initially hidden)
        self.file_widget = QgsFileWidget()
        self.file_widget.setDialogTitle(f"Select {self.title} file")
        self.file_widget.setFilter("Vector files (*.shp *.gpkg *.geojson);;Shapefiles (*.shp);;GeoPackage (*.gpkg)")
        self.file_widget.setVisible(False)
        group_layout.addWidget(self.file_widget)
        
        # Field selection
        field_layout = QHBoxLayout()
        field_layout.addWidget(QLabel("Field:"))
        
        self.combo_fields = QComboBox()
        self.combo_fields.setMinimumWidth(150)
        field_layout.addWidget(self.combo_fields, 1)
        field_layout.addStretch()
        
        group_layout.addLayout(field_layout)
        
        # Status label
        self.lbl_status = QLabel("Select a layer")
        self.lbl_status.setStyleSheet("color: #666; font-style: italic;")
        group_layout.addWidget(self.lbl_status)
        
        layout.addWidget(self.group_box)
        
        # Connect signals
        self.combo_layers.currentTextChanged.connect(self.on_layer_changed)
        self.combo_fields.currentTextChanged.connect(self.on_field_changed)
        self.radio_project.toggled.connect(self.on_method_changed)
        self.radio_file.toggled.connect(self.on_method_changed)
        self.btn_refresh.clicked.connect(self.update_layer_list)
        self.file_widget.fileChanged.connect(self.on_file_selected)
        
    def update_layer_list(self):
        """Update the list of available layers"""
        self.combo_layers.clear()
        self.combo_layers.addItem("-- Select a layer --", None)
        
        # Get layers from project
        layers = self.get_project_layers()
        
        if not layers:
            self.combo_layers.addItem("No suitable layers found", None)
            self.radio_project.setEnabled(False)
            if self.radio_project.isChecked():
                self.radio_file.setChecked(True)
        else:
            self.radio_project.setEnabled(True)
            for layer in layers:
                self.combo_layers.addItem(layer.name(), layer)
        
        self.lbl_status.setText(f"Found {len(layers)} layers")
        
    def get_project_layers(self) -> List[QgsVectorLayer]:
        """Get suitable layers from the current project"""
        layers = []
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer):
                # Filter by geometry type if specified
                if self.geometry_type is None or layer.geometryType() == self.geometry_type:
                    layers.append(layer)
        return layers
        
    def on_method_changed(self):
        """Handle selection method change"""
        use_project = self.radio_project.isChecked()
        
        self.combo_layers.setVisible(use_project)
        self.btn_refresh.setVisible(use_project)
        self.file_widget.setVisible(not use_project)
        
        if use_project:
            self.on_layer_changed()
        else:
            self.combo_fields.clear()
            self.selected_layer = None
            self.lbl_status.setText("Browse for file")
            
    def on_layer_changed(self):
        """Handle layer selection change"""
        if self.radio_project.isChecked():
            layer = self.combo_layers.currentData()
            self.set_layer(layer)
        
    def on_file_selected(self, file_path: str):
        """Handle file selection"""
        if not file_path:
            self.set_layer(None)
            return
            
        try:
            # Load the layer
            layer = QgsVectorLayer(file_path, Path(file_path).stem, "ogr")
            if not layer.isValid():
                raise ValueError(f"Cannot load layer from {file_path}")
                
            self.set_layer(layer)
            self.lbl_status.setText(f"Loaded: {Path(file_path).name}")
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error loading file: {str(e)}")
            self.set_layer(None)
            self.lbl_status.setText("Error loading file")
            
    def set_layer(self, layer: Optional[QgsVectorLayer]):
        """Set the current layer and update fields"""
        self.selected_layer = layer
        self.populate_fields()
        self.layer_changed.emit(layer)
        self.validate_selection()
        
    def populate_fields(self):
        """Populate the field dropdown"""
        self.combo_fields.clear()
        
        if not self.selected_layer or not self.selected_layer.isValid():
            self.combo_fields.addItem("No layer selected", None)
            return
            
        # Get field names
        field_names = [field.name() for field in self.selected_layer.fields()]
        
        if not field_names:
            self.combo_fields.addItem("No fields found", None)
            return
            
        # Add fields to combo
        for field_name in field_names:
            self.combo_fields.addItem(field_name, field_name)
            
        # Select default field if it exists
        if self.default_field and self.default_field in field_names:
            self.combo_fields.setCurrentText(self.default_field)
            
        self.lbl_status.setText(f"Layer: {self.selected_layer.name()} ({len(field_names)} fields)")
        
    def on_field_changed(self):
        """Handle field selection change"""
        field_name = self.combo_fields.currentData()
        self.field_changed.emit(field_name or "")
        self.validate_selection()
        
    def validate_selection(self):
        """Validate current selection and emit signal"""
        is_valid = (self.selected_layer is not None and 
                   self.selected_layer.isValid() and
                   self.get_selected_field() is not None)
        self.selection_valid.emit(is_valid)
        
        # Update status styling
        if is_valid:
            self.lbl_status.setStyleSheet("color: #4caf50; font-weight: bold;")
        elif self.selected_layer:
            self.lbl_status.setStyleSheet("color: #ff9800; font-style: italic;")
        else:
            self.lbl_status.setStyleSheet("color: #666; font-style: italic;")
            
    def get_selected_layer(self) -> Optional[QgsVectorLayer]:
        """Get the currently selected layer"""
        return self.selected_layer
        
    def get_selected_field(self) -> Optional[str]:
        """Get the currently selected field"""
        return self.combo_fields.currentData()
        
    def is_valid(self) -> bool:
        """Check if current selection is valid"""
        return (self.selected_layer is not None and 
                self.selected_layer.isValid() and 
                self.get_selected_field() is not None)
        
    def set_enabled(self, enabled: bool):
        """Enable/disable the entire widget"""
        self.group_box.setEnabled(enabled)


class FileSelector(QWidget):
    """Widget for selecting files with validation"""
    
    file_selected = pyqtSignal(str)
    
    def __init__(self, title: str, file_filter: str = "All files (*.*)", 
                 default_path: str = "", parent=None):
        super().__init__(parent)
        self.title = title
        self.file_filter = file_filter
        self.default_path = default_path
        self.selected_file = ""
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Group box
        group_box = QGroupBox(self.title)
        group_layout = QVBoxLayout(group_box)
        
        # File selection layout
        file_layout = QHBoxLayout()
        
        self.lbl_file = QLabel("No file selected")
        self.lbl_file.setStyleSheet("color: #666; font-style: italic;")
        file_layout.addWidget(self.lbl_file, 1)
        
        self.btn_browse = QPushButton("Browse...")
        file_layout.addWidget(self.btn_browse)
        
        group_layout.addLayout(file_layout)
        layout.addWidget(group_box)
        
        # Connect signals
        self.btn_browse.clicked.connect(self.browse_file)
        
    def browse_file(self):
        """Open file browser dialog"""
        start_dir = self.default_path if os.path.exists(self.default_path) else ""
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, f"Select {self.title}", start_dir, self.file_filter
        )
        
        if file_path:
            self.set_file(file_path)
            
    def set_file(self, file_path: str):
        """Set the selected file"""
        self.selected_file = file_path
        
        if file_path:
            self.lbl_file.setText(Path(file_path).name)
            self.lbl_file.setStyleSheet("color: #4caf50; font-weight: bold;")
            self.lbl_file.setToolTip(file_path)
        else:
            self.lbl_file.setText("No file selected")
            self.lbl_file.setStyleSheet("color: #666; font-style: italic;")
            self.lbl_file.setToolTip("")
            
        self.file_selected.emit(file_path)
        
    def get_selected_file(self) -> str:
        """Get the selected file path"""
        return self.selected_file
        
    def is_valid(self) -> bool:
        """Check if a valid file is selected"""
        return bool(self.selected_file and os.path.exists(self.selected_file))


class DirectorySelector(QWidget):
    """Widget for selecting output directories"""
    
    directory_selected = pyqtSignal(str)
    
    def __init__(self, title: str = "Output Directory", 
                 default_path: str = "", parent=None):
        super().__init__(parent)
        self.title = title
        self.default_path = default_path
        self.selected_directory = ""
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Group box
        group_box = QGroupBox(self.title)
        group_layout = QVBoxLayout(group_box)
        
        # Directory selection layout
        dir_layout = QHBoxLayout()
        
        self.lbl_directory = QLabel("No directory selected")
        self.lbl_directory.setStyleSheet("color: #666; font-style: italic;")
        dir_layout.addWidget(self.lbl_directory, 1)
        
        self.btn_browse = QPushButton("Browse...")
        dir_layout.addWidget(self.btn_browse)
        
        group_layout.addLayout(dir_layout)
        layout.addWidget(group_box)
        
        # Connect signals
        self.btn_browse.clicked.connect(self.browse_directory)
        
    def browse_directory(self):
        """Open directory browser dialog"""
        start_dir = self.default_path if os.path.exists(self.default_path) else ""
        
        directory = QFileDialog.getExistingDirectory(
            self, f"Select {self.title}", start_dir
        )
        
        if directory:
            self.set_directory(directory)
            
    def set_directory(self, directory: str):
        """Set the selected directory"""
        self.selected_directory = directory
        
        if directory:
            self.lbl_directory.setText(str(Path(directory).name))
            self.lbl_directory.setStyleSheet("color: #4caf50; font-weight: bold;")
            self.lbl_directory.setToolTip(directory)
        else:
            self.lbl_directory.setText("No directory selected")
            self.lbl_directory.setStyleSheet("color: #666; font-style: italic;")
            self.lbl_directory.setToolTip("")
            
        self.directory_selected.emit(directory)
        
    def get_selected_directory(self) -> str:
        """Get the selected directory path"""
        return self.selected_directory
        
    def is_valid(self) -> bool:
        """Check if a valid directory is selected"""
        return bool(self.selected_directory and os.path.exists(self.selected_directory))


class ProgressLogger(QWidget):
    """Widget for showing progress and logging"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Log area
        log_group = QGroupBox("Processing Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                font-family: Consolas, Monaco, monospace;
                font-size: 11px;
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
            }
        """)
        log_layout.addWidget(self.log_text)
        
        # Clear button
        clear_btn = QPushButton("Clear Log")
        clear_btn.clicked.connect(self.clear_log)
        log_layout.addWidget(clear_btn)
        
        layout.addWidget(log_group)
        
    def show_progress(self, visible: bool = True):
        """Show/hide progress bar"""
        self.progress_bar.setVisible(visible)
        
    def update_progress(self, value: int, message: str = ""):
        """Update progress bar and log message"""
        self.progress_bar.setValue(value)
        if message:
            self.log(message)
            
    def log(self, message: str, level: str = "info"):
        """Add message to log"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        # Color coding
        colors = {
            "info": "#000000",
            "warning": "#ff9800", 
            "error": "#f44336",
            "success": "#4caf50"
        }
        color = colors.get(level, "#000000")
        
        # Add to log
        self.log_text.append(
            f'<span style="color: {color}">[{timestamp}] {message}</span>'
        )
        
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def clear_log(self):
        """Clear the log"""
        self.log_text.clear()


class ValidationPanel(QWidget):
    """Panel showing validation status for multiple inputs"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.validations = {}
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Status group
        self.status_group = QGroupBox("Input Validation")
        self.status_layout = QVBoxLayout(self.status_group)
        
        self.status_label = QLabel("Configure inputs below")
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        self.status_layout.addWidget(self.status_label)
        
        layout.addWidget(self.status_group)
        
    def add_validation(self, name: str, description: str):
        """Add a validation item"""
        validation_widget = QWidget()
        validation_layout = QHBoxLayout(validation_widget)
        validation_layout.setContentsMargins(0, 0, 0, 0)
        
        # Status icon
        status_icon = QLabel("⏳")
        status_icon.setFixedWidth(20)
        validation_layout.addWidget(status_icon)
        
        # Description
        desc_label = QLabel(description)
        validation_layout.addWidget(desc_label, 1)
        
        self.validations[name] = {
            'widget': validation_widget,
            'icon': status_icon,
            'description': desc_label,
            'valid': False
        }
        
        self.status_layout.addWidget(validation_widget)
        self.update_overall_status()
        
    def set_validation_status(self, name: str, valid: bool, message: str = ""):
        """Update validation status for an item"""
        if name not in self.validations:
            return
            
        validation = self.validations[name]
        validation['valid'] = valid
        
        if valid:
            validation['icon'].setText("✅")
            validation['icon'].setStyleSheet("color: #4caf50;")
        else:
            validation['icon'].setText("❌")
            validation['icon'].setStyleSheet("color: #f44336;")
            
        if message:
            validation['description'].setToolTip(message)
            
        self.update_overall_status()
        
    def update_overall_status(self):
        """Update overall validation status"""
        if not self.validations:
            return
            
        all_valid = all(v['valid'] for v in self.validations.values())
        valid_count = sum(1 for v in self.validations.values() if v['valid'])
        total_count = len(self.validations)
        
        if all_valid:
            self.status_label.setText(f"✅ All inputs valid ({valid_count}/{total_count})")
            self.status_label.setStyleSheet("color: #4caf50; font-weight: bold;")
        else:
            self.status_label.setText(f"⚠️ Inputs incomplete ({valid_count}/{total_count})")
            self.status_label.setStyleSheet("color: #ff9800; font-weight: bold;")
            
    def is_all_valid(self) -> bool:
        """Check if all validations are valid"""
        return all(v['valid'] for v in self.validations.values())
        
    def get_invalid_items(self) -> List[str]:
        """Get list of invalid item names"""
        return [name for name, v in self.validations.items() if not v['valid']]
