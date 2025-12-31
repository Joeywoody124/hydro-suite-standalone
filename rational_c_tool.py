"""
Rational C Calculator Tool for Hydro Suite
Rational Method runoff coefficient calculator with full layer/field selection
Version 1.0 - 2025

Repository: https://github.com/Joeywoody124/hydro-suite-standalone
"""

import os
import csv
import traceback
from pathlib import Path
from typing import Optional, Tuple, Callable, Dict, Any

from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QMessageBox, QScrollArea, QFrame, QGroupBox, QRadioButton,
    QButtonGroup
)
from qgis.PyQt.QtCore import Qt, pyqtSignal

from qgis.core import (
    QgsCoordinateReferenceSystem, QgsProcessingFeedback, QgsProject,
    QgsVectorFileWriter, QgsVectorLayer, QgsField, QgsFeature,
    QgsWkbTypes, Qgis, QgsMessageLog
)
from qgis import processing

# Import our shared components
from hydro_suite_interface import HydroToolInterface, LayerSelectionMixin
from shared_widgets import (
    LayerFieldSelector, FileSelector, DirectorySelector, 
    ProgressLogger, ValidationPanel
)


class RationalCTool(HydroToolInterface, LayerSelectionMixin):
    """Rational Method C Calculator tool with full GUI integration"""
    
    def __init__(self):
        super().__init__()
        self.name = "Rational Method C Calculator"
        self.description = "Calculate area-weighted composite runoff coefficients for rational method analysis"
        self.category = "Runoff Analysis"
        self.version = "1.0"
        self.author = "Hydro Suite"
        
        # Tool-specific properties
        self.target_crs = QgsCoordinateReferenceSystem("EPSG:3361")
        self.lookup_data = {}
        self.selected_slope = "0-2%"  # Default slope category
        
        # GUI components
        self.catchment_selector = None
        self.landuse_selector = None
        self.soils_selector = None
        self.lookup_selector = None
        self.output_selector = None
        self.validation_panel = None
        self.progress_logger = None
        self.slope_group = None
        
    def create_gui(self, parent_widget: QWidget) -> QWidget:
        """Create the Rational C Calculator GUI"""
        # Create scroll area for the main content
        scroll = QScrollArea(parent_widget)
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Main widget
        main_widget = QWidget()
        scroll.setWidget(main_widget)
        
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(10)
        
        # Title and description
        title_label = QLabel(f"<h2>{self.name}</h2>")
        layout.addWidget(title_label)
        
        desc_label = QLabel(
            "<p>This tool calculates area-weighted composite runoff coefficients for rational method analysis. "
            "It performs intersection analysis between catchments, land use, and soils layers with slope-based C values.</p>"
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #555; margin-bottom: 10px;")
        layout.addWidget(desc_label)
        
        # Validation panel
        self.validation_panel = ValidationPanel()
        layout.addWidget(self.validation_panel)
        
        # Input layers section
        inputs_frame = QFrame()
        inputs_frame.setFrameStyle(QFrame.StyledPanel)
        inputs_layout = QVBoxLayout(inputs_frame)
        
        inputs_title = QLabel("<h3>Input Layers</h3>")
        inputs_layout.addWidget(inputs_title)
        
        # Catchment layer selector
        self.catchment_selector = LayerFieldSelector(
            "Catchment Layer", 
            default_field="Name",
            geometry_type=QgsWkbTypes.PolygonGeometry
        )
        inputs_layout.addWidget(self.catchment_selector)
        
        # Land use layer selector
        self.landuse_selector = LayerFieldSelector(
            "Land Use Layer",
            default_field="LU", 
            geometry_type=QgsWkbTypes.PolygonGeometry
        )
        inputs_layout.addWidget(self.landuse_selector)
        
        # Soils layer selector
        self.soils_selector = LayerFieldSelector(
            "Soils Layer",
            default_field="hydgrpdcd",
            geometry_type=QgsWkbTypes.PolygonGeometry
        )
        inputs_layout.addWidget(self.soils_selector)
        
        layout.addWidget(inputs_frame)
        
        # Slope selection section
        slope_frame = QFrame()
        slope_frame.setFrameStyle(QFrame.StyledPanel)
        slope_layout = QVBoxLayout(slope_frame)
        
        slope_title = QLabel("<h3>Project-Wide Land Slope Category</h3>")
        slope_layout.addWidget(slope_title)
        
        slope_desc = QLabel(
            "Select the predominant slope category for your project area. "
            "This affects the C values used in calculations."
        )
        slope_desc.setWordWrap(True)
        slope_desc.setStyleSheet("color: #666; font-style: italic; margin-bottom: 10px;")
        slope_layout.addWidget(slope_desc)
        
        # Slope radio buttons
        slope_button_layout = QHBoxLayout()
        self.slope_group = QButtonGroup()
        
        self.radio_slope1 = QRadioButton("0% - 2% (Flat)")
        self.radio_slope2 = QRadioButton("2% - 6% (Moderate)")
        self.radio_slope3 = QRadioButton("6%+ (Steep)")
        self.radio_slope1.setChecked(True)  # Default
        
        self.slope_group.addButton(self.radio_slope1, 1)
        self.slope_group.addButton(self.radio_slope2, 2)
        self.slope_group.addButton(self.radio_slope3, 3)
        
        slope_button_layout.addWidget(self.radio_slope1)
        slope_button_layout.addWidget(self.radio_slope2)
        slope_button_layout.addWidget(self.radio_slope3)
        slope_button_layout.addStretch()
        
        slope_layout.addLayout(slope_button_layout)
        layout.addWidget(slope_frame)
        
        # Lookup table and output section
        config_frame = QFrame()
        config_frame.setFrameStyle(QFrame.StyledPanel)
        config_layout = QVBoxLayout(config_frame)
        
        config_title = QLabel("<h3>Configuration</h3>")
        config_layout.addWidget(config_title)
        
        # Lookup table selector
        self.lookup_selector = FileSelector(
            "Rational C Lookup Table",
            "Data files (*.csv *.xlsx *.xls);;CSV files (*.csv);;Excel files (*.xlsx *.xls)",
            default_path=""
        )
        config_layout.addWidget(self.lookup_selector)
        
        # Output directory selector
        self.output_selector = DirectorySelector(
            "Output Directory",
            default_path=""
        )
        config_layout.addWidget(self.output_selector)
        
        layout.addWidget(config_frame)
        
        # Progress and logging
        self.progress_logger = ProgressLogger()
        layout.addWidget(self.progress_logger)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        validate_btn = QPushButton("Validate Inputs")
        validate_btn.clicked.connect(self.validate_and_update)
        button_layout.addWidget(validate_btn)
        
        button_layout.addStretch()
        
        self.run_btn = QPushButton("Run C Value Calculation")
        self.run_btn.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
                background-color: #28a745;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.run_btn.clicked.connect(self.run_calculation)
        button_layout.addWidget(self.run_btn)
        
        layout.addLayout(button_layout)
        
        # Setup validation monitoring
        self.setup_validation_monitoring()
        
        # Connect slope selection
        self.slope_group.buttonClicked.connect(self.on_slope_changed)
        
        # Initial validation
        self.validate_and_update()
        
        self.gui_widget = scroll
        return scroll
        
    def on_slope_changed(self, button):
        """Handle slope category change"""
        if button == self.radio_slope1:
            self.selected_slope = "0-2%"
        elif button == self.radio_slope2:
            self.selected_slope = "2-6%"
        else:
            self.selected_slope = "6%+"
            
        self.progress_logger.log(f"Slope category changed to: {self.selected_slope}")
        
        # Re-validate lookup table with new slope
        if self.lookup_selector.is_valid():
            self.validate_and_update()
        
    def setup_validation_monitoring(self):
        """Setup validation monitoring for all inputs"""
        # Add validation items
        self.validation_panel.add_validation("catchment", "Catchment layer and field")
        self.validation_panel.add_validation("landuse", "Land use layer and field")
        self.validation_panel.add_validation("soils", "Soils layer and field")
        self.validation_panel.add_validation("lookup", "C value lookup table")
        self.validation_panel.add_validation("output", "Output directory")
        
        # Connect validation signals
        self.catchment_selector.selection_valid.connect(
            lambda valid: self.validation_panel.set_validation_status("catchment", valid)
        )
        self.landuse_selector.selection_valid.connect(
            lambda valid: self.validation_panel.set_validation_status("landuse", valid)
        )
        self.soils_selector.selection_valid.connect(
            lambda valid: self.validation_panel.set_validation_status("soils", valid)
        )
        self.lookup_selector.file_selected.connect(
            lambda file: self.validation_panel.set_validation_status("lookup", bool(file))
        )
        self.output_selector.directory_selected.connect(
            lambda dir: self.validation_panel.set_validation_status("output", bool(dir))
        )
        
    def validate_and_update(self):
        """Validate all inputs and update UI"""
        # Trigger validation on all selectors
        self.catchment_selector.validate_selection()
        self.landuse_selector.validate_selection()
        self.soils_selector.validate_selection()
        
        # Validate lookup table
        lookup_valid = self.lookup_selector.is_valid()
        if lookup_valid:
            try:
                self.load_lookup_table()
                self.validation_panel.set_validation_status("lookup", True, "Lookup table loaded successfully")
            except Exception as e:
                self.validation_panel.set_validation_status("lookup", False, f"Error: {str(e)}")
                lookup_valid = False
        else:
            self.validation_panel.set_validation_status("lookup", False, "No lookup table selected")
            
        # Validate output directory
        output_valid = self.output_selector.is_valid()
        self.validation_panel.set_validation_status("output", output_valid)
        
        # Enable/disable run button
        all_valid = self.validation_panel.is_all_valid()
        self.run_btn.setEnabled(all_valid)
        
        if all_valid:
            self.progress_logger.log("✅ All inputs validated - ready to run", "success")
        else:
            invalid_items = self.validation_panel.get_invalid_items()
            self.progress_logger.log(f"⚠️ Please complete: {', '.join(invalid_items)}", "warning")
            
    def load_lookup_table(self):
        """Load and validate the C value lookup table"""
        lookup_file = self.lookup_selector.get_selected_file()
        if not lookup_file:
            raise ValueError("No lookup file selected")
            
        # Import pandas for reading the lookup table
        try:
            import pandas as pd
        except ImportError:
            raise ValueError("pandas library is required for reading lookup tables")
            
        # Read the file
        try:
            if lookup_file.lower().endswith('.csv'):
                df = pd.read_csv(lookup_file)
            else:
                df = pd.read_excel(lookup_file)
        except Exception as e:
            raise ValueError(f"Error reading lookup file: {str(e)}")
            
        # Clean column names
        df.columns = [c.strip().lower() for c in df.columns]
        
        # Validate format - expect columns like: landuse, a_0-2%, a_2-6%, a_6%+, b_0-2%, etc.
        if 'landuse' not in df.columns:
            raise ValueError("Lookup table missing required 'landuse' column")
            
        # Check for slope-specific columns for each soil group
        required_patterns = []
        for soil in ['a', 'b', 'c', 'd']:
            for slope in ['0-2%', '2-6%', '6%+']:
                required_patterns.append(f"{soil}_{slope}")
                
        missing_cols = []
        for pattern in required_patterns:
            if pattern not in df.columns:
                missing_cols.append(pattern)
                
        if missing_cols:
            available_cols = [col for col in df.columns if col != 'landuse']
            raise ValueError(
                f"Lookup table missing slope-specific columns:\n"
                f"Missing: {missing_cols}\n"
                f"Available: {available_cols}\n\n"
                f"Expected format: landuse, a_0-2%, a_2-6%, a_6%+, b_0-2%, b_2-6%, b_6%+, etc."
            )
            
        # Convert to lookup dictionary for current slope
        self.lookup_data = {}
        suffix = f"_{self.selected_slope}"
        
        for _, row in df.iterrows():
            landuse_key = str(row['landuse']).strip().lower()
            for soil_group in ['a', 'b', 'c', 'd']:
                col_name = f"{soil_group}{suffix}"
                if col_name in df.columns:
                    try:
                        c_value = float(row[col_name])
                        self.lookup_data[(landuse_key, soil_group)] = c_value
                    except (ValueError, TypeError):
                        pass  # Skip invalid values
                        
        if not self.lookup_data:
            raise ValueError(f"No valid C values found for slope category '{self.selected_slope}'")
            
        self.progress_logger.log(
            f"Loaded {len(self.lookup_data)} C value entries for slope '{self.selected_slope}' from {Path(lookup_file).name}"
        )
        
    def validate_inputs(self) -> Tuple[bool, str]:
        """Validate all inputs before processing"""
        errors = []
        
        if not self.catchment_selector.is_valid():
            errors.append("Invalid catchment layer or field selection")
        if not self.landuse_selector.is_valid():
            errors.append("Invalid land use layer or field selection")
        if not self.soils_selector.is_valid():
            errors.append("Invalid soils layer or field selection")
        if not self.lookup_selector.is_valid():
            errors.append("No lookup table selected")
        elif not self.lookup_data:
            errors.append("Lookup table not loaded or invalid")
        if not self.output_selector.is_valid():
            errors.append("No output directory selected")
            
        if errors:
            return False, "Please fix the following issues:\n• " + "\n• ".join(errors)
        return True, "All inputs valid"
        
    def run_calculation(self):
        """Run the C value calculation"""
        try:
            self.run(lambda progress, msg: self.progress_logger.update_progress(progress, msg))
        except Exception as e:
            self.progress_logger.log(f"❌ Error: {str(e)}", "error")
            QMessageBox.critical(self.gui_widget, "Calculation Error", str(e))
            
    def run(self, progress_callback: Optional[Callable[[int, str], None]] = None) -> bool:
        """Execute the C value calculation"""
        if not progress_callback:
            progress_callback = lambda p, m: None
            
        try:
            self.progress_logger.show_progress(True)
            progress_callback(0, "Starting C value calculation...")
            
            valid, message = self.validate_inputs()
            if not valid:
                raise ValueError(message)
                
            catchment_layer = self.catchment_selector.get_selected_layer()
            landuse_layer = self.landuse_selector.get_selected_layer()
            soils_layer = self.soils_selector.get_selected_layer()
            
            catchment_field = self.catchment_selector.get_selected_field()
            landuse_field = self.landuse_selector.get_selected_field()
            soils_field = self.soils_selector.get_selected_field()
            
            output_dir = self.output_selector.get_selected_directory()
            
            progress_callback(10, f"Using slope category: {self.selected_slope}")
            
            feedback = QgsProcessingFeedback()
            
            progress_callback(20, "Reprojecting layers...")
            catchment_reproj = self.reproject_layer(catchment_layer, feedback)
            landuse_reproj = self.reproject_layer(landuse_layer, feedback)
            soils_reproj = self.reproject_layer(soils_layer, feedback)
            
            progress_callback(40, "Intersecting land use with soils...")
            lu_soil = self.intersect_layers(landuse_reproj, soils_reproj, feedback)
            
            progress_callback(60, "Intersecting catchments with land use/soils...")
            final_intersection = self.intersect_layers(catchment_reproj, lu_soil, feedback)
            
            progress_callback(80, "Calculating composite C values...")
            results = self.calculate_composite_c(
                final_intersection, catchment_field, landuse_field, soils_field
            )
            
            progress_callback(90, "Creating output files...")
            self.create_outputs(catchment_reproj, results, catchment_field, output_dir)
            
            progress_callback(100, "✅ C value calculation completed successfully!")
            self.show_completion_dialog(results, output_dir)
            
            return True
            
        except Exception as e:
            progress_callback(0, f"❌ Error: {str(e)}")
            self.progress_logger.log(f"❌ Calculation failed: {str(e)}", "error")
            self.progress_logger.log(traceback.format_exc(), "error")
            raise
        finally:
            self.progress_logger.show_progress(False)
            
    def reproject_layer(self, layer: QgsVectorLayer, feedback) -> QgsVectorLayer:
        """Reproject layer to target CRS if needed"""
        if layer.crs() == self.target_crs:
            return layer
        self.progress_logger.log(f"Reprojecting {layer.name()}")
        params = {'INPUT': layer, 'TARGET_CRS': self.target_crs, 'OUTPUT': 'memory:'}
        result = processing.run("native:reprojectlayer", params, feedback=feedback)
        return result['OUTPUT']
        
    def intersect_layers(self, layer1: QgsVectorLayer, layer2: QgsVectorLayer, feedback) -> QgsVectorLayer:
        """Perform intersection between two layers"""
        self.progress_logger.log(f"Intersecting {layer1.name()} with {layer2.name()}")
        params = {'INPUT': layer1, 'OVERLAY': layer2, 'INPUT_FIELDS': [], 'OVERLAY_FIELDS': [], 'OUTPUT': 'memory:'}
        result = processing.run("native:intersection", params, feedback=feedback)
        intersection = result['OUTPUT']
        if intersection.featureCount() == 0:
            raise ValueError(f"Intersection resulted in no features")
        return intersection
        
    def calculate_composite_c(self, intersection_layer: QgsVectorLayer, 
                            catchment_field: str, landuse_field: str, soils_field: str) -> Dict:
        """Calculate composite C values for each catchment"""
        catchment_data = {}
        detailed_records = []
        
        for feature in intersection_layer.getFeatures():
            catchment_id = feature[catchment_field]
            landuse_code = str(feature[landuse_field]).strip().lower()
            soil_group_raw = str(feature[soils_field]).strip()
            
            soil_group = self.parse_soil_group(soil_group_raw)
            
            area_sqft = feature.geometry().area()
            area_acres = area_sqft / 43560.0
            
            if soil_group is None:
                c_value = 0.95
                self.progress_logger.log(f"Using default C=0.95 for unrecognized soil group: {soil_group_raw}")
            else:
                c_key = (landuse_code, soil_group)
                if c_key not in self.lookup_data:
                    self.progress_logger.log(f"Warning: No C value for '{landuse_code}' / '{soil_group}'", "warning")
                    continue
                c_value = self.lookup_data[c_key]
            
            if catchment_id not in catchment_data:
                catchment_data[catchment_id] = {'total_area': 0.0, 'c_area_sum': 0.0, 'details': []}
                
            catchment_data[catchment_id]['total_area'] += area_acres
            catchment_data[catchment_id]['c_area_sum'] += c_value * area_acres
            
            detail_record = {
                'catchment_id': catchment_id, 'landuse_code': landuse_code,
                'soil_group': soil_group or 'N/A', 'soil_group_original': soil_group_raw,
                'area_acres': area_acres, 'c_value': c_value, 'c_area_product': c_value * area_acres
            }
            catchment_data[catchment_id]['details'].append(detail_record)
            detailed_records.append(detail_record)
            
        return {'catchment_data': catchment_data, 'detailed_records': detailed_records}
        
    def parse_soil_group(self, soil_group_raw: str) -> Optional[str]:
        """Parse soil group, handling split HSGs"""
        if not soil_group_raw or str(soil_group_raw).strip() == '':
            return None
        soil_group = str(soil_group_raw).strip().upper()
        if '/' in soil_group:
            parts = soil_group.split('/')
            if len(parts) >= 2:
                soil_group = parts[1].strip()
        if soil_group in ['A', 'B', 'C', 'D']:
            return soil_group.lower()
        return None
            
    def create_outputs(self, catchment_layer: QgsVectorLayer, results: Dict, 
                      catchment_field: str, output_dir: str):
        """Create output files"""
        from qgis.PyQt.QtCore import QVariant
        
        output_layer = QgsVectorLayer(f"Polygon?crs={self.target_crs.authid()}", "catchments_c_value", "memory")
        output_provider = output_layer.dataProvider()
        
        original_fields = catchment_layer.fields()
        new_fields = [field for field in original_fields]
        new_fields.append(QgsField("C_Comp", QVariant.Double, "double", 10, 3))
        new_fields.append(QgsField("Area_acres", QVariant.Double, "double", 15, 2))
        
        output_provider.addAttributes(new_fields)
        output_layer.updateFields()
        
        output_features = []
        catchment_data = results['catchment_data']
        
        for orig_feature in catchment_layer.getFeatures():
            catchment_id = orig_feature[catchment_field]
            new_feature = QgsFeature()
            new_feature.setGeometry(orig_feature.geometry())
            attributes = list(orig_feature.attributes())
            
            if catchment_id in catchment_data and catchment_data[catchment_id]['total_area'] > 0:
                data = catchment_data[catchment_id]
                c_comp = data['c_area_sum'] / data['total_area']
                total_area = data['total_area']
            else:
                c_comp = None
                total_area = None
                
            attributes.extend([c_comp, total_area])
            new_feature.setAttributes(attributes)
            output_features.append(new_feature)
            
        output_provider.addFeatures(output_features)
        
        shp_path = os.path.join(output_dir, "catchments_with_c_value.shp")
        write_options = QgsVectorFileWriter.SaveVectorOptions()
        write_options.driverName = "ESRI Shapefile"
        write_options.fileEncoding = "UTF-8"
        
        error = QgsVectorFileWriter.writeAsVectorFormatV3(
            output_layer, shp_path, QgsProject.instance().transformContext(), write_options
        )
        
        if error[0] != QgsVectorFileWriter.NoError:
            raise ValueError(f"Error saving shapefile: {error[1]}")
            
        self.save_detailed_csv(results['detailed_records'], catchment_data, output_dir)
        self.save_summary_csv(catchment_data, output_dir)
        self.progress_logger.log(f"Outputs saved to {output_dir}")
        
    def save_detailed_csv(self, detailed_records: list, catchment_data: dict, output_dir: str):
        """Save detailed calculation CSV"""
        csv_path = os.path.join(output_dir, "c_value_calculations_detailed.csv")
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Catchment_ID', 'Landuse_Code', 'Soil_Group', 'Soil_Group_Original',
                           'Area_Acres', 'C_Value', 'C_x_Area'])
            for record in detailed_records:
                writer.writerow([
                    record['catchment_id'], record['landuse_code'].upper(),
                    record['soil_group'].upper() if record['soil_group'] != 'N/A' else 'N/A',
                    record['soil_group_original'], round(record['area_acres'], 4),
                    round(record['c_value'], 3), round(record['c_area_product'], 4)
                ])
                
    def save_summary_csv(self, catchment_data: dict, output_dir: str):
        """Save summary CSV"""
        summary_path = os.path.join(output_dir, "c_value_summary.csv")
        with open(summary_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Catchment_ID', 'Total_Area_Acres', 'Sum_C_x_Area', 'C_Composite'])
            for catchment_id, data in catchment_data.items():
                if data['total_area'] > 0:
                    c_comp = round(data['c_area_sum'] / data['total_area'], 3)
                    writer.writerow([catchment_id, round(data['total_area'], 3), 
                                   round(data['c_area_sum'], 3), c_comp])
                    
    def show_completion_dialog(self, results: dict, output_dir: str):
        """Show completion dialog"""
        catchment_data = results['catchment_data']
        processed_count = len([d for d in catchment_data.values() if d['total_area'] > 0])
        total_records = len(results['detailed_records'])
        
        message = f"""
Rational C Calculation Completed Successfully!

📊 Results Summary:
• Processed {processed_count} catchments
• Generated {total_records} detailed calculation records
• Slope category used: {self.selected_slope}

📁 Output Files saved to: {output_dir}

Would you like to load the results into QGIS?
"""
        
        reply = QMessageBox.question(self.gui_widget, "Calculation Complete", message,
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        
        if reply == QMessageBox.Yes:
            shp_path = os.path.join(output_dir, "catchments_with_c_value.shp")
            result_layer = QgsVectorLayer(shp_path, "Catchments with C Value", "ogr")
            QgsProject.instance().addMapLayer(result_layer)
            self.progress_logger.log("✅ Results loaded into QGIS project", "success")
