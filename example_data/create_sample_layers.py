"""
Generate Sample Data Layers for Hydro Suite
============================================
Creates GeoPackage layers with sample data for testing all Hydro Suite tools.

Run this script in QGIS Python Console to generate sample layers.

Author: Joey Woody, PE - J. Bragg Consulting Inc.
Date: January 2025
"""

import os
from pathlib import Path
from qgis.core import (
    QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY,
    QgsField, QgsFields, QgsProject, QgsCoordinateReferenceSystem,
    QgsVectorFileWriter, QgsWkbTypes, Qgis
)
from qgis.PyQt.QtCore import QVariant


def create_sample_data(output_folder: str = None):
    """
    Create all sample GeoPackage layers for Hydro Suite testing.
    
    Args:
        output_folder: Where to save files. Defaults to user's Documents folder.
    
    Returns:
        dict: Paths to created files
    """
    
    # Default output location
    if output_folder is None:
        output_folder = str(Path.home() / "Documents" / "HydroSuite_SampleData")
    
    # Create output folder
    os.makedirs(output_folder, exist_ok=True)
    
    print(f"Creating sample data in: {output_folder}")
    print("=" * 60)
    
    # Coordinate Reference System (SC State Plane - feet)
    # Change this to match your local CRS
    crs = QgsCoordinateReferenceSystem("EPSG:2273")  # SC State Plane South (feet)
    
    created_files = {}
    
    # Create each layer
    created_files['subbasins'] = create_subbasins_layer(output_folder, crs)
    created_files['landuse'] = create_landuse_layer(output_folder, crs)
    created_files['soils'] = create_soils_layer(output_folder, crs)
    created_files['flowpaths'] = create_flowpaths_layer(output_folder, crs)
    created_files['channels'] = create_channels_layer(output_folder, crs)
    created_files['outlets'] = create_outlets_layer(output_folder, crs)
    
    print("=" * 60)
    print("Sample data creation complete!")
    print(f"\nFiles created in: {output_folder}")
    print("\nTo load in QGIS:")
    print("  Layer > Add Layer > Add Vector Layer")
    print(f"  Browse to: {output_folder}")
    
    # Optionally add to current QGIS project
    add_to_project = True
    if add_to_project:
        print("\nAdding layers to current QGIS project...")
        for name, path in created_files.items():
            if path and os.path.exists(path):
                layer = QgsVectorLayer(path, f"Sample_{name}", "ogr")
                if layer.isValid():
                    QgsProject.instance().addMapLayer(layer)
                    print(f"  Added: Sample_{name}")
    
    return created_files


def create_subbasins_layer(output_folder: str, crs) -> str:
    """Create sample subbasins polygon layer."""
    
    output_path = os.path.join(output_folder, "sample_subbasins.gpkg")
    
    # Define fields
    fields = QgsFields()
    fields.append(QgsField("Subbasin_ID", QVariant.String, len=20))
    fields.append(QgsField("Name", QVariant.String, len=50))
    fields.append(QgsField("Area_Acres", QVariant.Double, len=10, prec=2))
    fields.append(QgsField("Slope_Pct", QVariant.Double, len=6, prec=2))
    fields.append(QgsField("Tc_min", QVariant.Double, len=8, prec=1))
    fields.append(QgsField("CN", QVariant.Int))
    fields.append(QgsField("C_Value", QVariant.Double, len=4, prec=2))
    fields.append(QgsField("Description", QVariant.String, len=100))
    
    # Create layer
    writer = QgsVectorFileWriter(
        output_path, "UTF-8", fields, QgsWkbTypes.Polygon, crs, "GPKG"
    )
    
    # Sample subbasin polygons (coordinates in feet, SC State Plane)
    # Base point around 2,100,000 E, 100,000 N (approximate Lowcountry SC)
    base_x, base_y = 2100000, 100000
    
    subbasins_data = [
        {
            "id": "SB-001", "name": "North Residential",
            "coords": [
                (base_x, base_y + 3000), (base_x + 2000, base_y + 3000),
                (base_x + 2500, base_y + 2000), (base_x + 2000, base_y + 1500),
                (base_x, base_y + 1500), (base_x, base_y + 3000)
            ],
            "area": 16.5, "slope": 3.2, "tc": 18.5, "cn": 75, "c": 0.42,
            "desc": "Single family residential - 1/4 acre lots"
        },
        {
            "id": "SB-002", "name": "Commercial Center",
            "coords": [
                (base_x + 2000, base_y + 3000), (base_x + 4000, base_y + 3000),
                (base_x + 4000, base_y + 1500), (base_x + 2500, base_y + 2000),
                (base_x + 2000, base_y + 3000)
            ],
            "area": 13.3, "slope": 1.5, "tc": 12.0, "cn": 92, "c": 0.78,
            "desc": "Strip mall and retail with parking"
        },
        {
            "id": "SB-003", "name": "South Woods",
            "coords": [
                (base_x, base_y + 1500), (base_x + 2000, base_y + 1500),
                (base_x + 2500, base_y + 2000), (base_x + 4000, base_y + 1500),
                (base_x + 4000, base_y), (base_x + 2000, base_y),
                (base_x, base_y + 500), (base_x, base_y + 1500)
            ],
            "area": 60.8, "slope": 8.5, "tc": 35.0, "cn": 55, "c": 0.12,
            "desc": "Undeveloped forested area with wetlands"
        },
        {
            "id": "SB-004", "name": "Industrial Park",
            "coords": [
                (base_x + 4000, base_y + 3000), (base_x + 6000, base_y + 3000),
                (base_x + 6000, base_y + 1500), (base_x + 4000, base_y + 1500),
                (base_x + 4000, base_y + 3000)
            ],
            "area": 23.6, "slope": 2.1, "tc": 15.0, "cn": 88, "c": 0.68,
            "desc": "Light industrial warehouse district"
        },
        {
            "id": "SB-005", "name": "East Farms",
            "coords": [
                (base_x + 4000, base_y + 1500), (base_x + 6000, base_y + 1500),
                (base_x + 6000, base_y), (base_x + 4000, base_y),
                (base_x + 4000, base_y + 1500)
            ],
            "area": 110.5, "slope": 4.5, "tc": 42.0, "cn": 74, "c": 0.35,
            "desc": "Cultivated farmland - row crops"
        },
    ]
    
    for sb in subbasins_data:
        feat = QgsFeature()
        points = [QgsPointXY(x, y) for x, y in sb["coords"]]
        feat.setGeometry(QgsGeometry.fromPolygonXY([points]))
        feat.setAttributes([
            sb["id"], sb["name"], sb["area"], sb["slope"],
            sb["tc"], sb["cn"], sb["c"], sb["desc"]
        ])
        writer.addFeature(feat)
    
    del writer
    print(f"Created: sample_subbasins.gpkg ({len(subbasins_data)} features)")
    return output_path


def create_landuse_layer(output_folder: str, crs) -> str:
    """Create sample land use polygon layer."""
    
    output_path = os.path.join(output_folder, "sample_landuse.gpkg")
    
    # Define fields
    fields = QgsFields()
    fields.append(QgsField("LU_ID", QVariant.Int))
    fields.append(QgsField("Land_Use", QVariant.String, len=30))
    fields.append(QgsField("Description", QVariant.String, len=100))
    fields.append(QgsField("Imperv_Pct", QVariant.Double, len=5, prec=1))
    
    writer = QgsVectorFileWriter(
        output_path, "UTF-8", fields, QgsWkbTypes.Polygon, crs, "GPKG"
    )
    
    base_x, base_y = 2100000, 100000
    
    # Land use polygons that overlap subbasins
    landuse_data = [
        # Residential area
        {
            "id": 1, "lu": "RES_1_4_AC", "desc": "Residential 1/4 acre lots", "imperv": 38.0,
            "coords": [
                (base_x, base_y + 3000), (base_x + 1800, base_y + 3000),
                (base_x + 1800, base_y + 1600), (base_x, base_y + 1600),
                (base_x, base_y + 3000)
            ]
        },
        # Streets in residential
        {
            "id": 2, "lu": "STREETS_PAVED", "desc": "Paved streets with curbs", "imperv": 100.0,
            "coords": [
                (base_x + 800, base_y + 3000), (base_x + 1000, base_y + 3000),
                (base_x + 1000, base_y + 1600), (base_x + 800, base_y + 1600),
                (base_x + 800, base_y + 3000)
            ]
        },
        # Open space in residential
        {
            "id": 3, "lu": "OPEN_SPACE_GOOD", "desc": "Park/common area", "imperv": 5.0,
            "coords": [
                (base_x + 1800, base_y + 2800), (base_x + 2400, base_y + 2200),
                (base_x + 2000, base_y + 1600), (base_x + 1800, base_y + 1600),
                (base_x + 1800, base_y + 2800)
            ]
        },
        # Commercial buildings
        {
            "id": 4, "lu": "COMMERCIAL", "desc": "Strip mall retail", "imperv": 85.0,
            "coords": [
                (base_x + 2400, base_y + 3000), (base_x + 3800, base_y + 3000),
                (base_x + 3800, base_y + 2200), (base_x + 2400, base_y + 2200),
                (base_x + 2400, base_y + 3000)
            ]
        },
        # Commercial parking
        {
            "id": 5, "lu": "PARKING_PAVED", "desc": "Paved parking lots", "imperv": 100.0,
            "coords": [
                (base_x + 2400, base_y + 2200), (base_x + 3800, base_y + 2200),
                (base_x + 3800, base_y + 1600), (base_x + 2600, base_y + 2000),
                (base_x + 2400, base_y + 2200)
            ]
        },
        # Woods - good condition
        {
            "id": 6, "lu": "WOODS_GOOD", "desc": "Undeveloped forest", "imperv": 0.0,
            "coords": [
                (base_x, base_y + 1600), (base_x + 1500, base_y + 1600),
                (base_x + 2000, base_y + 800), (base_x + 2000, base_y),
                (base_x, base_y + 500), (base_x, base_y + 1600)
            ]
        },
        # Wetland
        {
            "id": 7, "lu": "WETLAND", "desc": "Riparian wetland", "imperv": 0.0,
            "coords": [
                (base_x + 1500, base_y + 1600), (base_x + 2600, base_y + 2000),
                (base_x + 3800, base_y + 1600), (base_x + 3800, base_y + 800),
                (base_x + 2000, base_y + 800), (base_x + 1500, base_y + 1600)
            ]
        },
        # Industrial
        {
            "id": 8, "lu": "INDUSTRIAL", "desc": "Light industrial", "imperv": 72.0,
            "coords": [
                (base_x + 4000, base_y + 3000), (base_x + 5800, base_y + 3000),
                (base_x + 5800, base_y + 1600), (base_x + 4000, base_y + 1600),
                (base_x + 4000, base_y + 3000)
            ]
        },
        # Row crops
        {
            "id": 9, "lu": "ROW_CROP_GOOD_SR", "desc": "Row crops - corn/soybeans", "imperv": 0.0,
            "coords": [
                (base_x + 4000, base_y + 1600), (base_x + 5800, base_y + 1600),
                (base_x + 5800, base_y + 400), (base_x + 4000, base_y + 400),
                (base_x + 4000, base_y + 1600)
            ]
        },
        # Pasture
        {
            "id": 10, "lu": "PASTURE_GOOD", "desc": "Grazing pasture", "imperv": 0.0,
            "coords": [
                (base_x + 4000, base_y + 400), (base_x + 5800, base_y + 400),
                (base_x + 5800, base_y), (base_x + 4000, base_y),
                (base_x + 4000, base_y + 400)
            ]
        },
    ]
    
    for lu in landuse_data:
        feat = QgsFeature()
        points = [QgsPointXY(x, y) for x, y in lu["coords"]]
        feat.setGeometry(QgsGeometry.fromPolygonXY([points]))
        feat.setAttributes([lu["id"], lu["lu"], lu["desc"], lu["imperv"]])
        writer.addFeature(feat)
    
    del writer
    print(f"Created: sample_landuse.gpkg ({len(landuse_data)} features)")
    return output_path


def create_soils_layer(output_folder: str, crs) -> str:
    """Create sample soils polygon layer with HSG."""
    
    output_path = os.path.join(output_folder, "sample_soils.gpkg")
    
    # Define fields (similar to SSURGO format)
    fields = QgsFields()
    fields.append(QgsField("MUKEY", QVariant.String, len=20))
    fields.append(QgsField("MUSYM", QVariant.String, len=10))
    fields.append(QgsField("MUNAME", QVariant.String, len=100))
    fields.append(QgsField("HSG", QVariant.String, len=5))
    fields.append(QgsField("Hydric_Pct", QVariant.Int))
    fields.append(QgsField("Ksat_um_s", QVariant.Double, len=8, prec=2))
    
    writer = QgsVectorFileWriter(
        output_path, "UTF-8", fields, QgsWkbTypes.Polygon, crs, "GPKG"
    )
    
    base_x, base_y = 2100000, 100000
    
    soils_data = [
        # Well-drained sandy loam (HSG A)
        {
            "mukey": "123456", "musym": "LaB", "muname": "Lakeland sand, 0-6% slopes",
            "hsg": "A", "hydric": 0, "ksat": 42.0,
            "coords": [
                (base_x, base_y + 3000), (base_x + 2000, base_y + 3000),
                (base_x + 2000, base_y + 2000), (base_x, base_y + 2000),
                (base_x, base_y + 3000)
            ]
        },
        # Moderately well-drained loam (HSG B)
        {
            "mukey": "234567", "musym": "NoB", "muname": "Norfolk loamy sand, 2-6% slopes",
            "hsg": "B", "hydric": 0, "ksat": 14.0,
            "coords": [
                (base_x + 2000, base_y + 3000), (base_x + 6000, base_y + 3000),
                (base_x + 6000, base_y + 2000), (base_x + 2000, base_y + 2000),
                (base_x + 2000, base_y + 3000)
            ]
        },
        # Somewhat poorly drained (HSG C)
        {
            "mukey": "345678", "musym": "GoA", "muname": "Goldsboro sandy loam, 0-2% slopes",
            "hsg": "C", "hydric": 15, "ksat": 4.0,
            "coords": [
                (base_x, base_y + 2000), (base_x + 3000, base_y + 2000),
                (base_x + 3000, base_y + 1000), (base_x, base_y + 1000),
                (base_x, base_y + 2000)
            ]
        },
        # Poorly drained clay (HSG D)
        {
            "mukey": "456789", "musym": "Ly", "muname": "Lynn Haven fine sand",
            "hsg": "D", "hydric": 85, "ksat": 1.0,
            "coords": [
                (base_x + 3000, base_y + 2000), (base_x + 6000, base_y + 2000),
                (base_x + 6000, base_y + 1000), (base_x + 3000, base_y + 1000),
                (base_x + 3000, base_y + 2000)
            ]
        },
        # Dual HSG (B/D) - coastal plain
        {
            "mukey": "567890", "musym": "BaA", "muname": "Bayboro mucky loam",
            "hsg": "B/D", "hydric": 95, "ksat": 10.0,
            "coords": [
                (base_x, base_y + 1000), (base_x + 3000, base_y + 1000),
                (base_x + 3000, base_y), (base_x, base_y),
                (base_x, base_y + 1000)
            ]
        },
        # Dual HSG (A/D) - sandy with high water table
        {
            "mukey": "678901", "musym": "MuA", "muname": "Mulat fine sand",
            "hsg": "A/D", "hydric": 80, "ksat": 35.0,
            "coords": [
                (base_x + 3000, base_y + 1000), (base_x + 6000, base_y + 1000),
                (base_x + 6000, base_y), (base_x + 3000, base_y),
                (base_x + 3000, base_y + 1000)
            ]
        },
    ]
    
    for soil in soils_data:
        feat = QgsFeature()
        points = [QgsPointXY(x, y) for x, y in soil["coords"]]
        feat.setGeometry(QgsGeometry.fromPolygonXY([points]))
        feat.setAttributes([
            soil["mukey"], soil["musym"], soil["muname"],
            soil["hsg"], soil["hydric"], soil["ksat"]
        ])
        writer.addFeature(feat)
    
    del writer
    print(f"Created: sample_soils.gpkg ({len(soils_data)} features)")
    return output_path


def create_flowpaths_layer(output_folder: str, crs) -> str:
    """Create sample flow path lines for TC calculations."""
    
    output_path = os.path.join(output_folder, "sample_flowpaths.gpkg")
    
    # Define fields
    fields = QgsFields()
    fields.append(QgsField("FP_ID", QVariant.String, len=20))
    fields.append(QgsField("Subbasin_ID", QVariant.String, len=20))
    fields.append(QgsField("Segment", QVariant.Int))
    fields.append(QgsField("Flow_Type", QVariant.String, len=20))
    fields.append(QgsField("Length_ft", QVariant.Double, len=10, prec=1))
    fields.append(QgsField("Slope_Pct", QVariant.Double, len=6, prec=2))
    fields.append(QgsField("Mannings_n", QVariant.Double, len=6, prec=3))
    fields.append(QgsField("Description", QVariant.String, len=100))
    
    writer = QgsVectorFileWriter(
        output_path, "UTF-8", fields, QgsWkbTypes.LineString, crs, "GPKG"
    )
    
    base_x, base_y = 2100000, 100000
    
    flowpaths_data = [
        # SB-001: Residential - Sheet flow to shallow concentrated to channel
        {
            "fp_id": "FP-001-1", "sb_id": "SB-001", "seg": 1,
            "type": "SHEET", "length": 100, "slope": 2.0, "n": 0.24,
            "desc": "Sheet flow over lawn",
            "coords": [(base_x + 500, base_y + 2800), (base_x + 600, base_y + 2750)]
        },
        {
            "fp_id": "FP-001-2", "sb_id": "SB-001", "seg": 2,
            "type": "SHALLOW_CONC", "length": 800, "slope": 3.0, "n": 0.05,
            "desc": "Shallow concentrated - paved",
            "coords": [(base_x + 600, base_y + 2750), (base_x + 1200, base_y + 2200)]
        },
        {
            "fp_id": "FP-001-3", "sb_id": "SB-001", "seg": 3,
            "type": "CHANNEL", "length": 1200, "slope": 1.5, "n": 0.035,
            "desc": "Grass channel to outfall",
            "coords": [(base_x + 1200, base_y + 2200), (base_x + 2000, base_y + 1600)]
        },
        # SB-002: Commercial - mostly impervious
        {
            "fp_id": "FP-002-1", "sb_id": "SB-002", "seg": 1,
            "type": "SHEET", "length": 50, "slope": 1.0, "n": 0.011,
            "desc": "Sheet flow over parking",
            "coords": [(base_x + 3000, base_y + 2800), (base_x + 3050, base_y + 2770)]
        },
        {
            "fp_id": "FP-002-2", "sb_id": "SB-002", "seg": 2,
            "type": "SHALLOW_CONC", "length": 600, "slope": 1.5, "n": 0.013,
            "desc": "Gutter flow",
            "coords": [(base_x + 3050, base_y + 2770), (base_x + 3200, base_y + 2000)]
        },
        {
            "fp_id": "FP-002-3", "sb_id": "SB-002", "seg": 3,
            "type": "PIPE", "length": 400, "slope": 0.8, "n": 0.013,
            "desc": "Storm pipe to outfall",
            "coords": [(base_x + 3200, base_y + 2000), (base_x + 3000, base_y + 1600)]
        },
        # SB-003: Woods - natural flow path
        {
            "fp_id": "FP-003-1", "sb_id": "SB-003", "seg": 1,
            "type": "SHEET", "length": 100, "slope": 8.0, "n": 0.80,
            "desc": "Sheet flow through forest litter",
            "coords": [(base_x + 500, base_y + 1200), (base_x + 550, base_y + 1150)]
        },
        {
            "fp_id": "FP-003-2", "sb_id": "SB-003", "seg": 2,
            "type": "SHALLOW_CONC", "length": 1500, "slope": 6.0, "n": 0.15,
            "desc": "Natural swale through woods",
            "coords": [(base_x + 550, base_y + 1150), (base_x + 1500, base_y + 600)]
        },
        {
            "fp_id": "FP-003-3", "sb_id": "SB-003", "seg": 3,
            "type": "CHANNEL", "length": 2000, "slope": 2.0, "n": 0.045,
            "desc": "Natural stream channel",
            "coords": [(base_x + 1500, base_y + 600), (base_x + 3000, base_y + 200)]
        },
    ]
    
    for fp in flowpaths_data:
        feat = QgsFeature()
        points = [QgsPointXY(x, y) for x, y in fp["coords"]]
        feat.setGeometry(QgsGeometry.fromPolylineXY(points))
        feat.setAttributes([
            fp["fp_id"], fp["sb_id"], fp["seg"], fp["type"],
            fp["length"], fp["slope"], fp["n"], fp["desc"]
        ])
        writer.addFeature(feat)
    
    del writer
    print(f"Created: sample_flowpaths.gpkg ({len(flowpaths_data)} features)")
    return output_path


def create_channels_layer(output_folder: str, crs) -> str:
    """Create sample channel lines for Channel Designer."""
    
    output_path = os.path.join(output_folder, "sample_channels.gpkg")
    
    # Define fields
    fields = QgsFields()
    fields.append(QgsField("Channel_ID", QVariant.String, len=20))
    fields.append(QgsField("Name", QVariant.String, len=50))
    fields.append(QgsField("Bottom_W_ft", QVariant.Double, len=8, prec=2))
    fields.append(QgsField("Side_Slope", QVariant.Double, len=6, prec=2))
    fields.append(QgsField("Depth_ft", QVariant.Double, len=6, prec=2))
    fields.append(QgsField("Mannings_n", QVariant.Double, len=6, prec=3))
    fields.append(QgsField("Slope_ftft", QVariant.Double, len=8, prec=5))
    fields.append(QgsField("Lining", QVariant.String, len=30))
    fields.append(QgsField("Q_Design_cfs", QVariant.Double, len=10, prec=2))
    
    writer = QgsVectorFileWriter(
        output_path, "UTF-8", fields, QgsWkbTypes.LineString, crs, "GPKG"
    )
    
    base_x, base_y = 2100000, 100000
    
    channels_data = [
        {
            "id": "CH-001", "name": "Main Outfall Channel",
            "bottom_w": 8.0, "side_slope": 2.0, "depth": 4.0,
            "n": 0.035, "slope": 0.005, "lining": "Grass-lined",
            "q_design": 125.0,
            "coords": [
                (base_x + 2000, base_y + 1600),
                (base_x + 2500, base_y + 1200),
                (base_x + 3000, base_y + 800),
                (base_x + 3500, base_y + 400)
            ]
        },
        {
            "id": "CH-002", "name": "North Collector Swale",
            "bottom_w": 4.0, "side_slope": 3.0, "depth": 2.0,
            "n": 0.030, "slope": 0.008, "lining": "Grass-lined",
            "q_design": 45.0,
            "coords": [
                (base_x + 1200, base_y + 2200),
                (base_x + 1600, base_y + 1900),
                (base_x + 2000, base_y + 1600)
            ]
        },
        {
            "id": "CH-003", "name": "Commercial Concrete Channel",
            "bottom_w": 3.0, "side_slope": 1.0, "depth": 2.5,
            "n": 0.015, "slope": 0.010, "lining": "Concrete",
            "q_design": 85.0,
            "coords": [
                (base_x + 3200, base_y + 2000),
                (base_x + 3000, base_y + 1600),
                (base_x + 2800, base_y + 1200)
            ]
        },
        {
            "id": "CH-004", "name": "Industrial Rip-Rap Channel",
            "bottom_w": 6.0, "side_slope": 2.0, "depth": 3.0,
            "n": 0.040, "slope": 0.012, "lining": "Rip-rap",
            "q_design": 95.0,
            "coords": [
                (base_x + 5000, base_y + 2500),
                (base_x + 4800, base_y + 2000),
                (base_x + 4500, base_y + 1500),
                (base_x + 4200, base_y + 1000)
            ]
        },
        {
            "id": "CH-005", "name": "Natural Stream",
            "bottom_w": 10.0, "side_slope": 2.5, "depth": 3.5,
            "n": 0.045, "slope": 0.003, "lining": "Natural",
            "q_design": 200.0,
            "coords": [
                (base_x + 3500, base_y + 400),
                (base_x + 4000, base_y + 200),
                (base_x + 4500, base_y + 100),
                (base_x + 5500, base_y + 50)
            ]
        },
    ]
    
    for ch in channels_data:
        feat = QgsFeature()
        points = [QgsPointXY(x, y) for x, y in ch["coords"]]
        feat.setGeometry(QgsGeometry.fromPolylineXY(points))
        feat.setAttributes([
            ch["id"], ch["name"], ch["bottom_w"], ch["side_slope"],
            ch["depth"], ch["n"], ch["slope"], ch["lining"], ch["q_design"]
        ])
        writer.addFeature(feat)
    
    del writer
    print(f"Created: sample_channels.gpkg ({len(channels_data)} features)")
    return output_path


def create_outlets_layer(output_folder: str, crs) -> str:
    """Create sample outlet/pour points."""
    
    output_path = os.path.join(output_folder, "sample_outlets.gpkg")
    
    # Define fields
    fields = QgsFields()
    fields.append(QgsField("Outlet_ID", QVariant.String, len=20))
    fields.append(QgsField("Subbasin_ID", QVariant.String, len=20))
    fields.append(QgsField("Name", QVariant.String, len=50))
    fields.append(QgsField("Type", QVariant.String, len=20))
    fields.append(QgsField("Invert_Elev", QVariant.Double, len=10, prec=2))
    
    writer = QgsVectorFileWriter(
        output_path, "UTF-8", fields, QgsWkbTypes.Point, crs, "GPKG"
    )
    
    base_x, base_y = 2100000, 100000
    
    outlets_data = [
        {"id": "OUT-001", "sb_id": "SB-001", "name": "North Residential Outfall",
         "type": "Channel", "elev": 28.5, "coords": (base_x + 2000, base_y + 1600)},
        {"id": "OUT-002", "sb_id": "SB-002", "name": "Commercial Pipe Outfall",
         "type": "Pipe", "elev": 26.0, "coords": (base_x + 3000, base_y + 1600)},
        {"id": "OUT-003", "sb_id": "SB-003", "name": "Woods Stream Confluence",
         "type": "Natural", "elev": 18.0, "coords": (base_x + 3000, base_y + 200)},
        {"id": "OUT-004", "sb_id": "SB-004", "name": "Industrial Outfall",
         "type": "Channel", "elev": 22.0, "coords": (base_x + 4200, base_y + 1000)},
        {"id": "OUT-005", "sb_id": "SB-005", "name": "Farm Ditch Outlet",
         "type": "Ditch", "elev": 15.0, "coords": (base_x + 5500, base_y + 50)},
        {"id": "OUT-MAIN", "sb_id": "ALL", "name": "Main Watershed Outlet",
         "type": "Stream", "elev": 12.0, "coords": (base_x + 5500, base_y + 50)},
    ]
    
    for out in outlets_data:
        feat = QgsFeature()
        feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(*out["coords"])))
        feat.setAttributes([out["id"], out["sb_id"], out["name"], out["type"], out["elev"]])
        writer.addFeature(feat)
    
    del writer
    print(f"Created: sample_outlets.gpkg ({len(outlets_data)} features)")
    return output_path


# ============================================================
# RUN THIS TO CREATE ALL SAMPLE DATA
# ============================================================
if __name__ == "__main__":
    # Specify output folder (change as needed)
    output_folder = r"E:\CLAUDE_Workspace\Claude\Report_Files\Finished_Code\Hydro_Suite_Data_Backup_v1\github_standalone\example_data\gis_layers"
    
    # Create all sample layers
    created = create_sample_data(output_folder)
    
    print("\n" + "=" * 60)
    print("DONE! Sample GeoPackage layers created.")
    print("=" * 60)
