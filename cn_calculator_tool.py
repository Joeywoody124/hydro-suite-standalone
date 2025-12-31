"""
CN Calculator Tool for Hydro Suite
Composite Curve Number calculator with full layer/field selection
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
    QMessageBox, QScrollArea, QFrame, QGroupBox
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


class CNCalculatorTool(HydroToolInterface, LayerSelectionMixin):
    """Curve Number Calculator tool with full GUI integration"""
    
    def __init__(self):
        super().__init__()
        self.name = "Curve Number Calculator"
        self.description = "Calculate area-weighted composite curve numbers for hydrological modeling"
        self.category = "Runoff Analysis" 
        self.version = "2.2"
        self.author = "Hydro Suite"
        
        # Tool-specific properties
        self.target_crs = QgsCoordinateReferenceSystem("EPSG:3361")
        self.lookup_data = {}
        
        # GUI components
        self.subbasin_selector = None
        self.landuse_selector = None
        self.soils_selector = None
        self.lookup_selector = None
        self.output_selector = None
        self.validation_panel = None
        self.progress_logger = None
        
    def create_gui(self, parent_widget: QWidget) -> QWidget:
        """Create the CN Calculator GUI"""
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
            "<p>This tool calculates area-weighted composite curve numbers for hydrological modeling. "
            "It performs intersection analysis between subbasins, land use, and soils layers.</p>"
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
        
        # Subbasin layer selector
        self.subbasin_selector = LayerFieldSelector(
            "Subbasin Layer", 
            default_field="Name",
            geometry_type=QgsWkbTypes.PolygonGeometry
        )
        inputs_layout.addWidget(self.subbasin_selector)
        
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
        
        # Lookup table and output section
        config_frame = QFrame()
        config_frame.setFrameStyle(QFrame.StyledPanel)
        config_layout = QVBoxLayout(config_frame)
        
        config_title = QLabel("<h3>Configuration</h3>")
        config_layout.addWidget(config_title)
        
        # Lookup table selector
        self.lookup_selector = FileSelector(
            "CN Lookup Table",
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
        
        self.run_btn = QPushButton("Run CN Calculation")
        self.run_btn.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
                background-color: #007bff;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #0056b3;
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
        
        # Initial validation
        self.validate_and_update()
        
        self.gui_widget = scroll
        return scroll
        
    def setup_validation_monitoring(self):
        """Setup validation monitoring for all inputs"""
        # Add validation items
        self.validation_panel.add_validation("subbasin", "Subbasin layer and field")
        self.validation_panel.add_validation("landuse", "Land use layer and field")
        self.validation_panel.add_validation("soils", "Soils layer and field")
        self.validation_panel.add_validation("lookup", "CN lookup table")
        self.validation_panel.add_validation("output", "Output directory")
        
        # Connect validation signals
        self.subbasin_selector.selection_valid.connect(
            lambda valid: self.validation_panel.set_validation_status("subbasin", valid)
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
        self.subbasin_selector.validate_selection()
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
        """Load and validate the CN lookup table"""
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
        
        # Validate format
        required_cols = {'landuse', 'a', 'b', 'c', 'd'}
        if not required_cols.issubset(set(df.columns)):
            raise ValueError(f"Lookup table missing required columns: {required_cols - set(df.columns)}")
            
        # Convert to lookup dictionary
        self.lookup_data = {}
        for _, row in df.iterrows():
            landuse_key = str(row['landuse']).strip().lower()
            for soil_group in ['a', 'b', 'c', 'd']:
                try:
                    cn_value = float(row[soil_group])
                    self.lookup_data[(landuse_key, soil_group)] = cn_value
                except (ValueError, TypeError):
                    pass  # Skip invalid values
                    
        if not self.lookup_data:
            raise ValueError("No valid CN values found in lookup table")
            
        self.progress_logger.log(f"Loaded {len(self.lookup_data)} CN lookup entries from {Path(lookup_file).name}")
        
    def validate_inputs(self) -> Tuple[bool, str]:
        """Validate all inputs before processing"""
        errors = []
        
        # Check layer selections
        if not self.subbasin_selector.is_valid():
            errors.append("Invalid subbasin layer or field selection")
            
        if not self.landuse_selector.is_valid():
            errors.append("Invalid land use layer or field selection")
            
        if not self.soils_selector.is_valid():
            errors.append("Invalid soils layer or field selection")
            
        # Check lookup table
        if not self.lookup_selector.is_valid():
            errors.append("No lookup table selected")
        elif not self.lookup_data:
            errors.append("Lookup table not loaded or invalid")
            
        # Check output directory
        if not self.output_selector.is_valid():
            errors.append("No output directory selected")
            
        if errors:
            return False, "Please fix the following issues:\n• " + "\n• ".join(errors)
            
        return True, "All inputs valid"
        
    def run_calculation(self):
        """Run the CN calculation"""
        try:
            self.run(lambda progress, msg: self.progress_logger.update_progress(progress, msg))
        except Exception as e:
            self.progress_logger.log(f"❌ Error: {str(e)}", "error")
            QMessageBox.critical(self.gui_widget, "Calculation Error", str(e))
            
    def run(self, progress_callback: Optional[Callable[[int, str], None]] = None) -> bool:
        """Execute the CN calculation"""
        if not progress_callback:
            progress_callback = lambda p, m: None
            
        try:
            self.progress_logger.show_progress(True)
            progress_callback(0, "Starting CN calculation...")
            
            # Validate inputs
            valid, message = self.validate_inputs()
            if not valid:
                raise ValueError(message)
                
            # Get input layers and fields
            subbasin_layer = self.subbasin_selector.get_selected_layer()
            landuse_layer = self.landuse_selector.get_selected_layer()
            soils_layer = self.soils_selector.get_selected_layer()
            
            subbasin_field = self.subbasin_selector.get_selected_field()
            landuse_field = self.landuse_selector.get_selected_field()
            soils_field = self.soils_selector.get_selected_field()
            
            output_dir = self.output_selector.get_selected_directory()
            
            progress_callback(10, "Validating layer geometry and CRS...")
            
            # Create feedback object for QGIS processing
            feedback = QgsProcessingFeedback()
            
            # Reproject layers to target CRS if needed
            progress_callback(20, "Reprojecting layers...")
            subbasin_reproj = self.reproject_layer(subbasin_layer, feedback)
            landuse_reproj = self.reproject_layer(landuse_layer, feedback)
            soils_reproj = self.reproject_layer(soils_layer, feedback)
            
            # First intersection: land use with soils
            progress_callback(40, "Intersecting land use with soils...")
            lu_soil = self.intersect_layers(landuse_reproj, soils_reproj, feedback)
            
            # Second intersection: subbasins with land use/soils
            progress_callback(60, "Intersecting subbasins with land use/soils...")
            final_intersection = self.intersect_layers(subbasin_reproj, lu_soil, feedback)
            
            # Calculate composite CN values
            progress_callback(80, "Calculating composite CN values...")
            results = self.calculate_composite_cn(
                final_intersection, subbasin_field, landuse_field, soils_field
            )
            
            # Create output
            progress_callback(90, "Creating output files...")
            self.create_outputs(subbasin_reproj, results, subbasin_field, output_dir)
            
            progress_callback(100, "✅ CN calculation completed successfully!")
            
            # Show completion dialog
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
            
        self.progress_logger.log(f"Reprojecting {layer.name()} from {layer.crs().authid()} to {self.target_crs.authid()}")
        
        params = {
            'INPUT': layer,
            'TARGET_CRS': self.target_crs,
            'OUTPUT': 'memory:'
        }
        result = processing.run("native:reprojectlayer", params, feedback=feedback)
        return result['OUTPUT']
        
    def intersect_layers(self, layer1: QgsVectorLayer, layer2: QgsVectorLayer, feedback) -> QgsVectorLayer:
        """Perform intersection between two layers"""
        self.progress_logger.log(f"Intersecting {layer1.name()} with {layer2.name()}")
        
        params = {
            'INPUT': layer1,
            'OVERLAY': layer2,
            'INPUT_FIELDS': [],
            'OVERLAY_FIELDS': [],
            'OUTPUT': 'memory:'
        }
        result = processing.run("native:intersection", params, feedback=feedback)
        intersection = result['OUTPUT']
        
        if intersection.featureCount() == 0:
            raise ValueError(f"Intersection between {layer1.name()} and {layer2.name()} resulted in no features")
            
        return intersection
        
    def calculate_composite_cn(self, intersection_layer: QgsVectorLayer, 
                             subbasin_field: str, landuse_field: str, soils_field: str) -> Dict:
        """Calculate composite CN values for each subbasin"""
        subbasin_data = {}
        detailed_records = []
        
        for feature in intersection_layer.getFeatures():
            # Get attributes
            subbasin_id = feature[subbasin_field]
            landuse_code = str(feature[landuse_field]).strip().lower()
            soil_group_raw = str(feature[soils_field]).strip()
            
            # Parse soil group (handle split HSGs)
            soil_group = self.parse_soil_group(soil_group_raw)
            
            # Calculate area in acres
            area_sqft = feature.geometry().area()
            area_acres = area_sqft / 43560.0
            
            # Look up CN value
            cn_key = (landuse_code, soil_group)
            if cn_key not in self.lookup_data:
                self.progress_logger.log(
                    f"Warning: No CN found for land use '{landuse_code}' and soil group '{soil_group}'", 
                    "warning"
                )
                continue
                
            cn_value = self.lookup_data[cn_key]
            
            # Accumulate data for subbasin
            if subbasin_id not in subbasin_data:
                subbasin_data[subbasin_id] = {
                    'total_area': 0.0,
                    'cn_area_sum': 0.0,
                    'details': []
                }
                
            subbasin_data[subbasin_id]['total_area'] += area_acres
            subbasin_data[subbasin_id]['cn_area_sum'] += cn_value * area_acres
            
            # Store detailed record
            detail_record = {
                'subbasin_id': subbasin_id,
                'landuse_code': landuse_code,
                'soil_group': soil_group,
                'soil_group_original': soil_group_raw,
                'area_acres': area_acres,
                'cn_value': cn_value,
                'cn_area_product': cn_value * area_acres
            }
            subbasin_data[subbasin_id]['details'].append(detail_record)
            detailed_records.append(detail_record)
            
        return {
            'subbasin_data': subbasin_data,
            'detailed_records': detailed_records
        }
        
    def parse_soil_group(self, soil_group_raw: str) -> str:
        """Parse soil group, handling split HSGs"""
        soil_group = str(soil_group_raw).strip().upper()
        
        # Handle split soil groups (e.g., 'A/D', 'B/D', 'C/D')
        if '/' in soil_group:
            parts = soil_group.split('/')
            if len(parts) >= 2:
                soil_group = parts[1].strip()  # Use more restrictive group
                self.progress_logger.log(f"Split HSG detected: '{soil_group_raw}' -> using '{soil_group}'")
                
        # Validate and return lowercase
        if soil_group in ['A', 'B', 'C', 'D']:
            return soil_group.lower()
        else:
            self.progress_logger.log(f"Warning: Invalid soil group '{soil_group_raw}', using 'd' as default", "warning")
            return 'd'  # Default to most restrictive
            
    def create_outputs(self, subbasin_layer: QgsVectorLayer, results: Dict, 
                      subbasin_field: str, output_dir: str):
        """Create output files"""
        from qgis.PyQt.QtCore import QVariant
        
        # Create output layer with CN_Comp field
        output_layer = QgsVectorLayer(f"Polygon?crs={self.target_crs.authid()}", "subbasins_cn", "memory")
        output_provider = output_layer.dataProvider()
        
        # Copy fields from original layer and add CN fields
        original_fields = subbasin_layer.fields()
        new_fields = [field for field in original_fields]
        new_fields.append(QgsField("CN_Comp", QVariant.Double, "double", 10, 2))
        new_fields.append(QgsField("Area_acres", QVariant.Double, "double", 15, 2))
        
        output_provider.addAttributes(new_fields)
        output_layer.updateFields()
        
        # Add features with calculated CN values
        output_features = []
        subbasin_data = results['subbasin_data']
        
        for orig_feature in subbasin_layer.getFeatures():
            subbasin_id = orig_feature[subbasin_field]
            
            new_feature = QgsFeature()
            new_feature.setGeometry(orig_feature.geometry())
            
            # Copy original attributes
            attributes = list(orig_feature.attributes())
            
            # Calculate and add CN_Comp
            if subbasin_id in subbasin_data and subbasin_data[subbasin_id]['total_area'] > 0:
                data = subbasin_data[subbasin_id]
                cn_comp = data['cn_area_sum'] / data['total_area']
                total_area = data['total_area']
            else:
                cn_comp = None
                total_area = None
                
            attributes.extend([cn_comp, total_area])
            new_feature.setAttributes(attributes)
            output_features.append(new_feature)
            
        output_provider.addFeatures(output_features)
        
        # Save shapefile
        shp_path = os.path.join(output_dir, "subbasins_cn.shp")
        write_options = QgsVectorFileWriter.SaveVectorOptions()
        write_options.driverName = "ESRI Shapefile"
        write_options.fileEncoding = "UTF-8"
        
        error = QgsVectorFileWriter.writeAsVectorFormatV3(
            output_layer, shp_path, QgsProject.instance().transformContext(), write_options
        )
        
        if error[0] != QgsVectorFileWriter.NoError:
            raise ValueError(f"Error saving shapefile: {error[1]}")
            
        # Save detailed CSV
        self.save_detailed_csv(results['detailed_records'], subbasin_data, output_dir)
        
        # Save summary CSV
        self.save_summary_csv(subbasin_data, output_dir)
        
        self.progress_logger.log(f"Outputs saved to {output_dir}")
        
    def save_detailed_csv(self, detailed_records: list, subbasin_data: dict, output_dir: str):
        """Save detailed calculation CSV"""
        csv_path = os.path.join(output_dir, "cn_calculations_detailed.csv")
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Group by subbasin
            subbasin_groups = {}
            for record in detailed_records:
                subbasin_id = record['subbasin_id']
                if subbasin_id not in subbasin_groups:
                    subbasin_groups[subbasin_id] = []
                subbasin_groups[subbasin_id].append(record)
                
            # Write grouped data
            for subbasin_id in sorted(subbasin_groups.keys()):
                data = subbasin_data[subbasin_id]
                cn_composite = data['cn_area_sum'] / data['total_area'] if data['total_area'] > 0 else 0
                
                # Subbasin header
                writer.writerow(['Subbasin ID', 'Total Area (acres)', 'Composite CN', '', '', '', ''])
                writer.writerow([subbasin_id, round(data['total_area'], 2), round(cn_composite, 2), '', '', '', ''])
                
                # Detail header
                writer.writerow(['', 'Land Use', 'Soil Type', 'Area (acres)', 'CN Value', 'CN x Area', 'Original HSG'])
                
                # Detail rows
                for record in subbasin_groups[subbasin_id]:
                    writer.writerow([
                        '',
                        record['landuse_code'].upper(),
                        record['soil_group'].upper(), 
                        round(record['area_acres'], 2),
                        int(record['cn_value']),
                        round(record['cn_area_product'], 2),
                        record['soil_group_original']
                    ])
                    
                writer.writerow([''] * 7)  # Empty separator row
                
    def save_summary_csv(self, subbasin_data: dict, output_dir: str):
        """Save summary CSV"""
        summary_path = os.path.join(output_dir, "cn_summary.csv")
        
        with open(summary_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Subbasin_ID', 'Total_Area_Acres', 'Sum_CN_x_Area', 'CN_Composite'])
            
            for subbasin_id, data in subbasin_data.items():
                if data['total_area'] > 0:
                    cn_comp = round(data['cn_area_sum'] / data['total_area'], 2)
                    area_acres = round(data['total_area'], 3)
                    cn_area_sum = round(data['cn_area_sum'], 3)
                    writer.writerow([subbasin_id, area_acres, cn_area_sum, cn_comp])
                    
    def show_completion_dialog(self, results: dict, output_dir: str):
        """Show completion dialog with results summary"""
        subbasin_data = results['subbasin_data']
        processed_count = len([d for d in subbasin_data.values() if d['total_area'] > 0])
        total_records = len(results['detailed_records'])
        
        message = f"""
CN Calculation Completed Successfully!

📊 Results Summary:
• Processed {processed_count} subbasins
• Generated {total_records} detailed calculation records
• Outputs saved to: {output_dir}

📁 Output Files:
• subbasins_cn.shp - Shapefile with CN_Comp field
• cn_calculations_detailed.csv - Detailed calculations
• cn_summary.csv - Summary table

Would you like to load the results into QGIS?
"""
        
        reply = QMessageBox.question(
            self.gui_widget,
            "Calculation Complete",
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            # Load result layer into QGIS
            shp_path = os.path.join(output_dir, "subbasins_cn.shp")
            result_layer = QgsVectorLayer(shp_path, "Subbasins with CN", "ogr")
            QgsProject.instance().addMapLayer(result_layer)
            self.progress_logger.log("✅ Results loaded into QGIS project", "success")
