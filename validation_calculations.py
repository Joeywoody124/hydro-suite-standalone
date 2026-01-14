"""
Hydro Suite v2.1 - Validation Calculations
==========================================
Hand calculations to verify TC Calculator and Channel Designer outputs
With per-subbasin parameters and channel geometry

Author: Joey Woody, PE - J. Bragg Consulting Inc.
Date: January 2025

Run this in QGIS Python Console to validate tool outputs.
"""

import math

# =============================================================================
# HYDRAULIC CALCULATIONS
# =============================================================================

def calc_hydraulic_radius(depth: float, bottom_width: float, side_slope: float) -> float:
    """Calculate hydraulic radius for trapezoidal channel"""
    if depth <= 0 or bottom_width <= 0:
        return 1.0
    top_width = bottom_width + 2 * side_slope * depth
    area = (bottom_width + top_width) / 2 * depth
    side_length = depth * math.sqrt(1 + side_slope**2)
    wetted_perimeter = bottom_width + 2 * side_length
    return area / wetted_perimeter if wetted_perimeter > 0 else 1.0


def sheet_flow_time(length_ft: float, slope_pct: float, mannings_n: float, 
                    p2_rainfall: float = 3.5) -> float:
    """TR-55 Equation 3-3: Sheet Flow Travel Time (returns minutes)"""
    length_ft = min(length_ft, 300.0)  # Max 300 ft per TR-55
    if length_ft <= 0 or slope_pct <= 0 or mannings_n <= 0:
        return 0.0
    slope_ftft = slope_pct / 100.0
    tt_hours = (0.007 * ((mannings_n * length_ft) ** 0.8)) / \
               ((p2_rainfall ** 0.5) * (slope_ftft ** 0.4))
    return tt_hours * 60.0


def shallow_concentrated_time(length_ft: float, slope_pct: float, 
                              surface_type: str = 'UNPAVED') -> float:
    """TR-55 Shallow Concentrated Flow Travel Time (returns minutes)"""
    if length_ft <= 0 or slope_pct <= 0:
        return 0.0
    slope_ftft = slope_pct / 100.0
    if surface_type.upper() == 'PAVED':
        velocity_fps = 20.328 * (slope_ftft ** 0.5)
    else:
        velocity_fps = 16.135 * (slope_ftft ** 0.5)
    return (length_ft / velocity_fps) / 60.0


def channel_flow_time(length_ft: float, slope_pct: float, mannings_n: float,
                      hydraulic_radius: float = 1.0) -> float:
    """Open Channel Flow Travel Time using Manning's (returns minutes)"""
    if length_ft <= 0 or slope_pct <= 0 or mannings_n <= 0:
        return 0.0
    slope_ftft = slope_pct / 100.0
    velocity_fps = (1.49 / mannings_n) * (hydraulic_radius ** (2.0/3.0)) * (slope_ftft ** 0.5)
    return (length_ft / velocity_fps) / 60.0


def pipe_flow_time(length_ft: float, slope_pct: float, mannings_n: float = 0.013,
                   diameter_ft: float = 1.5) -> float:
    """Pipe Flow Travel Time (full flow, returns minutes)"""
    hydraulic_radius = diameter_ft / 4.0
    return channel_flow_time(length_ft, slope_pct, mannings_n, hydraulic_radius)


# Whole-watershed methods
def kirpich_tc(length_ft: float, slope_pct: float) -> float:
    """Kirpich (1940) Method - returns TC in minutes"""
    if length_ft <= 0 or slope_pct <= 0:
        return 0.0
    slope_ftft = slope_pct / 100.0
    return 0.0078 * (length_ft ** 0.77) / (slope_ftft ** 0.385)


def faa_tc(length_ft: float, slope_pct: float, c_value: float = 0.3) -> float:
    """FAA (1965) Method - returns TC in minutes"""
    if length_ft <= 0 or slope_pct <= 0:
        return 0.0
    return (1.8 * (1.1 - c_value) * (length_ft ** 0.5)) / (slope_pct ** 0.33)


def scs_lag_tc(length_ft: float, slope_pct: float, cn: float = 75) -> float:
    """SCS/NRCS Lag Method - returns TC in minutes"""
    if length_ft <= 0 or slope_pct <= 0:
        return 0.0
    slope_ftft = slope_pct / 100.0
    storage_term = (1000.0 / cn) - 9.0
    if storage_term <= 0:
        storage_term = 0.1
    lag_hours = ((length_ft ** 0.8) * (storage_term ** 0.7)) / (1900.0 * (slope_ftft ** 0.5))
    return (lag_hours / 0.6) * 60.0


def kerby_tc(length_ft: float, slope_pct: float, mannings_n: float = 0.4) -> float:
    """Kerby Method - returns TC in minutes"""
    if length_ft <= 0 or slope_pct <= 0:
        return 0.0
    slope_ftft = slope_pct / 100.0
    return 1.44 * ((mannings_n * length_ft) ** 0.467) / (slope_ftft ** 0.235)


# Channel hydraulics
def trapezoidal_properties(depth: float, bottom_width: float, side_slope: float):
    """Calculate trapezoidal channel hydraulic properties"""
    top_width = bottom_width + 2 * side_slope * depth
    area = (bottom_width + top_width) / 2 * depth
    side_length = depth * math.sqrt(1 + side_slope**2)
    wetted_perimeter = bottom_width + 2 * side_length
    hydraulic_radius = area / wetted_perimeter
    return {
        'area': area, 'wetted_perimeter': wetted_perimeter,
        'hydraulic_radius': hydraulic_radius, 'top_width': top_width
    }


def manning_capacity(area: float, hydraulic_radius: float, slope_ftft: float, 
                     mannings_n: float) -> tuple:
    """Manning's equation: returns (velocity_fps, capacity_cfs)"""
    velocity = (1.49 / mannings_n) * (hydraulic_radius ** (2.0/3.0)) * (slope_ftft ** 0.5)
    return velocity, velocity * area


# =============================================================================
# VALIDATION DATA
# =============================================================================

print("=" * 70)
print("HYDRO SUITE v2.1 - VALIDATION CALCULATIONS")
print("With Per-Subbasin Parameters and Channel Geometry")
print("=" * 70)
print()

# Flowpath segments from sample_flowpaths.gpkg
flowpaths = {
    'SB-001': [
        {'type': 'SHEET', 'length': 100, 'slope': 2.0, 'n': 0.24, 'desc': 'Lawn sheet flow'},
        {'type': 'SHALLOW_CONC', 'length': 800, 'slope': 3.0, 'n': 0.05, 'desc': 'Paved shallow conc'},
        {'type': 'CHANNEL', 'length': 1200, 'slope': 1.5, 'n': 0.035, 'desc': 'Grass channel'},
    ],
    'SB-002': [
        {'type': 'SHEET', 'length': 50, 'slope': 1.0, 'n': 0.011, 'desc': 'Parking lot sheet'},
        {'type': 'SHALLOW_CONC', 'length': 600, 'slope': 1.5, 'n': 0.013, 'desc': 'Gutter flow'},
        {'type': 'PIPE', 'length': 400, 'slope': 0.8, 'n': 0.013, 'desc': 'Storm pipe'},
    ],
    'SB-003': [
        {'type': 'SHEET', 'length': 100, 'slope': 8.0, 'n': 0.80, 'desc': 'Forest litter'},
        {'type': 'SHALLOW_CONC', 'length': 1500, 'slope': 6.0, 'n': 0.15, 'desc': 'Woods swale'},
        {'type': 'CHANNEL', 'length': 2000, 'slope': 2.0, 'n': 0.045, 'desc': 'Natural stream'},
    ],
}

# Per-subbasin comparison method parameters (from CN/C calculators)
subbasin_params = {
    'SB-001': {'cn': 75, 'c_value': 0.42, 'mannings_n': 0.10, 'desc': 'North Residential'},
    'SB-002': {'cn': 92, 'c_value': 0.78, 'mannings_n': 0.012, 'desc': 'Commercial Center'},
    'SB-003': {'cn': 55, 'c_value': 0.12, 'mannings_n': 0.45, 'desc': 'South Woods'},
}

# Per-subbasin channel geometry (when not in layer data)
subbasin_geometry = {
    'SB-001': {
        'channel_depth': 2.0, 'channel_width': 4.0, 'side_slope': 3.0, 'pipe_diameter': 1.5,
        'description': 'Residential swales and 18" pipes'
    },
    'SB-002': {
        'channel_depth': 2.5, 'channel_width': 3.0, 'side_slope': 1.0, 'pipe_diameter': 2.0,
        'description': 'Concrete channels and 24" pipes'
    },
    'SB-003': {
        'channel_depth': 3.5, 'channel_width': 10.0, 'side_slope': 2.5, 'pipe_diameter': 3.0,
        'description': 'Natural stream and 36" culverts'
    },
}

# Global defaults
global_defaults = {'channel_depth': 2.0, 'channel_width': 4.0, 'side_slope': 2.0, 'pipe_diameter': 1.5}
p2_rainfall = 3.5  # inches

print("INPUT PARAMETERS")
print("=" * 70)
print(f"2-yr 24-hr Rainfall (P2): {p2_rainfall} inches")
print()

print("GLOBAL DEFAULTS (fallback when subbasin not defined):")
default_hr = calc_hydraulic_radius(global_defaults['channel_depth'], global_defaults['channel_width'], global_defaults['side_slope'])
print(f"  Channel: {global_defaults['channel_depth']} ft x {global_defaults['channel_width']} ft, {global_defaults['side_slope']}:1 → R = {default_hr:.3f} ft")
print(f"  Pipe: {global_defaults['pipe_diameter']} ft → R = {global_defaults['pipe_diameter']/4:.3f} ft")
print()

print("PER-SUBBASIN PARAMETERS:")
print("-" * 70)
for sb_id in sorted(subbasin_params.keys()):
    params = subbasin_params[sb_id]
    geom = subbasin_geometry[sb_id]
    ch_r = calc_hydraulic_radius(geom['channel_depth'], geom['channel_width'], geom['side_slope'])
    pipe_r = geom['pipe_diameter'] / 4.0
    print(f"{sb_id}: {params['desc']}")
    print(f"  Method params: CN={params['cn']}, C={params['c_value']}, n={params['mannings_n']}")
    print(f"  Channel: {geom['channel_depth']} ft x {geom['channel_width']} ft, {geom['side_slope']}:1 → R = {ch_r:.3f} ft")
    print(f"  Pipe: {geom['pipe_diameter']} ft ({geom['pipe_diameter']*12:.0f}\") → R = {pipe_r:.3f} ft")
print()

# =============================================================================
# TC CALCULATIONS BY SUBBASIN
# =============================================================================

print("=" * 70)
print("SEGMENT-BASED TC CALCULATIONS (TR-55 Method)")
print("=" * 70)

results = {}

for sb_id, segments in flowpaths.items():
    params = subbasin_params[sb_id]
    geom = subbasin_geometry[sb_id]
    
    # Calculate R for this subbasin
    channel_r = calc_hydraulic_radius(geom['channel_depth'], geom['channel_width'], geom['side_slope'])
    pipe_d = geom['pipe_diameter']
    
    print()
    print(f"SUBBASIN: {sb_id} - {params['desc']}")
    print(f"  Params: CN={params['cn']}, C={params['c_value']}, n={params['mannings_n']}")
    print(f"  Geometry: Channel R={channel_r:.3f} ft, Pipe D={pipe_d} ft (R={pipe_d/4:.3f} ft)")
    print("-" * 50)
    
    total_tt = 0.0
    total_length = 0.0
    weighted_slope_sum = 0.0
    
    for i, seg in enumerate(segments, 1):
        flow_type = seg['type']
        length = seg['length']
        slope = seg['slope']
        n = seg['n']
        
        if flow_type == 'SHEET':
            tt = sheet_flow_time(length, slope, n, p2_rainfall)
            method_note = f"TR-55 Eq 3-3 (n={n}, P2={p2_rainfall})"
        elif flow_type == 'SHALLOW_CONC':
            surface = 'PAVED' if n < 0.02 else 'UNPAVED'
            tt = shallow_concentrated_time(length, slope, surface)
            method_note = f"TR-55 Fig 3-1 ({surface})"
        elif flow_type == 'PIPE':
            tt = pipe_flow_time(length, slope, n, pipe_d)
            method_note = f"Manning's (D={pipe_d} ft, R={pipe_d/4:.3f} ft)"
        elif flow_type == 'CHANNEL':
            tt = channel_flow_time(length, slope, n, channel_r)
            method_note = f"Manning's (R={channel_r:.3f} ft)"
        else:
            tt = channel_flow_time(length, slope, n, channel_r)
            method_note = "Default: Manning's"
        
        total_tt += tt
        total_length += length
        weighted_slope_sum += slope * length
        
        print(f"  Seg {i}: {flow_type} - {seg['desc']}")
        print(f"         L={length} ft, S={slope}%, n={n}")
        print(f"         Tt = {tt:.2f} min  [{method_note}]")
    
    avg_slope = weighted_slope_sum / total_length if total_length > 0 else 0
    
    print("-" * 50)
    print(f"  TOTAL LENGTH: {total_length:.0f} ft")
    print(f"  AVG SLOPE: {avg_slope:.2f}%")
    print(f"  TC (Segment): {total_tt:.2f} min")
    
    results[sb_id] = {
        'tc_segment': total_tt,
        'total_length': total_length,
        'avg_slope': avg_slope,
        'cn': params['cn'],
        'c_value': params['c_value'],
        'avg_n': params['mannings_n'],
        'channel_r': channel_r,
        'pipe_d': pipe_d,
    }

# =============================================================================
# COMPARISON METHOD CALCULATIONS
# =============================================================================

print()
print("=" * 70)
print("COMPARISON METHOD CALCULATIONS (Using Per-Subbasin Parameters)")
print("=" * 70)

for sb_id, data in results.items():
    length = data['total_length']
    slope = data['avg_slope']
    cn = data['cn']
    c_value = data['c_value']
    avg_n = data['avg_n']
    
    tc_kirpich = kirpich_tc(length, slope)
    tc_faa = faa_tc(length, slope, c_value)
    tc_scs = scs_lag_tc(length, slope, cn)
    tc_kerby = kerby_tc(length, slope, avg_n)
    
    results[sb_id]['tc_kirpich'] = tc_kirpich
    results[sb_id]['tc_faa'] = tc_faa
    results[sb_id]['tc_scs'] = tc_scs
    results[sb_id]['tc_kerby'] = tc_kerby
    
    print()
    print(f"SUBBASIN: {sb_id}")
    print(f"  Input: L={length:.0f} ft, S={slope:.2f}%")
    print(f"  Custom params: CN={cn}, C={c_value}, n={avg_n}")
    print("-" * 50)
    print(f"  Kirpich:  {tc_kirpich:>6.2f} min  [tc = 0.0078 × L^0.77 / S^0.385]")
    print(f"  FAA:      {tc_faa:>6.2f} min  [tc = 1.8×(1.1-C)×L^0.5 / S^0.33, C={c_value}]")
    print(f"  SCS Lag:  {tc_scs:>6.2f} min  [Tc = Lag/0.6, CN={cn}]")
    print(f"  Kerby:    {tc_kerby:>6.2f} min  [tc = 1.44×(nL)^0.467 / S^0.235, n={avg_n}]")

# =============================================================================
# SUMMARY TABLE
# =============================================================================

print()
print("=" * 70)
print("SUMMARY: TC VALUES BY METHOD (minutes)")
print("=" * 70)
print()
print(f"{'Subbasin':<10} {'Segment':<10} {'Kirpich':<10} {'FAA':<10} {'SCS Lag':<10} {'Kerby':<10}")
print("-" * 70)

for sb_id, data in results.items():
    print(f"{sb_id:<10} {data['tc_segment']:<10.1f} {data['tc_kirpich']:<10.1f} "
          f"{data['tc_faa']:<10.1f} {data['tc_scs']:<10.1f} {data['tc_kerby']:<10.1f}")

print()
print("NOTES:")
print("• Segment method sums individual travel times (TR-55 approach)")
print("• Comparison methods use total length and average slope")
print("• FAA uses subbasin-specific runoff coefficient (C)")
print("• SCS Lag uses subbasin-specific curve number (CN)")
print("• Kerby uses average Manning's n for the subbasin")
print("• Channel/pipe R calculated from per-subbasin geometry")

# =============================================================================
# CHANNEL DESIGNER VALIDATION
# =============================================================================

print()
print("=" * 70)
print("CHANNEL DESIGNER VALIDATION")
print("=" * 70)
print()

channels = [
    {'id': 'CH-001', 'name': 'Main Outfall', 'depth': 4.0, 'width': 8.0, 'slope': 2.0, 
     'n': 0.035, 'ch_slope': 0.005},
    {'id': 'CH-002', 'name': 'Collector Swale', 'depth': 2.0, 'width': 4.0, 'slope': 3.0, 
     'n': 0.030, 'ch_slope': 0.008},
    {'id': 'CH-003', 'name': 'Concrete Channel', 'depth': 2.5, 'width': 3.0, 'slope': 1.0, 
     'n': 0.015, 'ch_slope': 0.010},
    {'id': 'CH-004', 'name': 'Rip-rap Channel', 'depth': 3.0, 'width': 6.0, 'slope': 2.0, 
     'n': 0.040, 'ch_slope': 0.012},
    {'id': 'CH-005', 'name': 'Natural Stream', 'depth': 3.5, 'width': 10.0, 'slope': 2.5, 
     'n': 0.045, 'ch_slope': 0.003},
]

print(f"{'Channel':<10} {'Depth':<8} {'Width':<8} {'Slope':<8} {'n':<8} "
      f"{'Area':<10} {'R':<8} {'V (fps)':<10} {'Q (cfs)':<10}")
print("-" * 90)

for ch in channels:
    props = trapezoidal_properties(ch['depth'], ch['width'], ch['slope'])
    velocity, capacity = manning_capacity(props['area'], props['hydraulic_radius'], ch['ch_slope'], ch['n'])
    
    print(f"{ch['id']:<10} {ch['depth']:<8.1f} {ch['width']:<8.1f} {ch['slope']:<8.1f} "
          f"{ch['n']:<8.3f} {props['area']:<10.2f} {props['hydraulic_radius']:<8.3f} "
          f"{velocity:<10.2f} {capacity:<10.1f}")

# =============================================================================
# EXPECTED VALUES FOR HYDRO SUITE COMPARISON
# =============================================================================

print()
print("=" * 70)
print("EXPECTED VALUES FOR HYDRO SUITE TOOL COMPARISON")
print("=" * 70)
print()
print("When running TC Calculator v2.1 with sample_flowpaths.gpkg:")
print()
print("TC Calculator Results should match:")
for sb_id, data in results.items():
    print(f"  {sb_id}: TC = {data['tc_segment']:.1f} min (segment-based)")
    print(f"          Kirpich = {data['tc_kirpich']:.1f} min, FAA = {data['tc_faa']:.1f} min, "
          f"SCS Lag = {data['tc_scs']:.1f} min, Kerby = {data['tc_kerby']:.1f} min")
print()
print("When running Channel Designer v2.0 with sample_channels.gpkg:")
print()
print("Channel Designer Results should show:")
for ch in channels:
    props = trapezoidal_properties(ch['depth'], ch['width'], ch['slope'])
    velocity, capacity = manning_capacity(props['area'], props['hydraulic_radius'], ch['ch_slope'], ch['n'])
    print(f"  {ch['id']}: V = {velocity:.2f} fps, Q = {capacity:.1f} cfs")

print()
print("=" * 70)
print("VALIDATION COMPLETE")
print("=" * 70)
