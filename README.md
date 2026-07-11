<div align="center">

# 💧 Hydro Suite

### Professional Stormwater & Hydrology Automation for QGIS

*A modular toolkit that turns hours of hydrologic spreadsheet work into minutes of guided, auditable calculation — right inside QGIS.*

![Version](https://img.shields.io/badge/version-2.5.1-2563eb?style=for-the-badge)
![QGIS](https://img.shields.io/badge/QGIS-3.40%2B-589632?style=for-the-badge&logo=qgis&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.9%2B-3776ab?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-64748b?style=for-the-badge)
![Status](https://img.shields.io/badge/status-production%20ready-16a34a?style=for-the-badge)

<sub>Built by <b>Joey Woody, PE</b> · J. Bragg Consulting Inc. · Civil / Water Resources Engineering</sub>

</div>

---

## Overview

**Hydro Suite** is a collection of purpose-built engineering tools for stormwater and watershed
analysis, designed to run directly in the **QGIS Python Console** — no plugin installation required.
Each tool pairs a clean, guided interface with defensible, standards-based calculations and
clean exports for downstream modeling in **SWMM, PCSWMM, HEC-HMS, and HEC-RAS**.

The mission is simple: **automate the repetitive, error-prone parts of drainage design** so engineers
can spend their time on judgment, not data wrangling — while keeping every number traceable back to
its source methodology.

> **This is the standalone script edition.** It runs from the QGIS Python Console with zero setup.
> A packaged plugin version lives in a separate repository (see [Editions](#editions)).

---

## 🚀 Development Focus

The next chapter of Hydro Suite is about **reporting and quality control** — closing the loop between
your models and the deliverables reviewers actually read. These are the flagship capabilities in
active development:

### 📑 Automated Report Development — PCSWMM & HY-8

Turn raw model output into review-ready reports, automatically.

- **PCSWMM report automation** — parse model results and assemble formatted summary tables,
  node/link inventories, and design-storm comparisons ready to drop into a drainage report.
- **HY-8 culvert reporting** — capture HY-8 culvert hydraulic analysis outputs and generate
  clean, consistent tables and rating summaries for permit and design submittals.
- **One consistent template** — standardized formatting across every project so deliverables
  look the same regardless of who ran the model.

### 📊 SWMM QC Reporting Dashboard

A quality-control cockpit for your SWMM models — catch problems *before* the reviewer does.

- **Automated model QC checks** — flag disconnected nodes, missing invert data, negative slopes,
  suspect Manning's values, and continuity-error outliers.
- **At-a-glance dashboard** — surface model health, network statistics, and QC flags in a single
  visual summary instead of buried log files.
- **Audit-ready output** — export the QC results as a report section that documents your
  model-review process.

> These features are the current priority on the [roadmap](#roadmap). The sections below cover the
> tools available and battle-tested **today**.

---

## 🧰 The Toolkit

Four production tools ship today, each launchable from a single Hydro Suite window.

| Tool | What it does | Key outputs |
|------|--------------|-------------|
| **🔢 Curve Number Calculator** | Area-weighted composite CN from subbasins × land use × soils | SWMM / HEC-HMS-ready CN tables |
| **💦 Rational C Calculator** | Composite runoff coefficients for the rational method | Slope-based C reports |
| **⏱️ Time of Concentration** | TC via three modes and multiple methods | Per-subbasin TC, method comparison |
| **📐 Channel Designer** | Trapezoidal channel design with hydraulics | SWMM / HEC-RAS cross-sections |

<details>
<summary><b>🔢 Curve Number (CN) Calculator</b></summary>

Calculate area-weighted composite curve numbers for hydrologic modeling.

- Multi-layer intersection (subbasins × land use × soils)
- Split HSG handling (A/D, B/D, C/D)
- CSV / Excel lookup table support
- SWMM- and HEC-HMS-compatible outputs
</details>

<details>
<summary><b>💦 Rational C Calculator</b></summary>

Calculate composite runoff coefficients for rational method analysis.

- Slope-based C-value determination (0–2%, 2–6%, 6%+)
- Project-wide slope category selection
- Professional reporting formats
</details>

<details>
<summary><b>⏱️ Time of Concentration (TC) Calculator</b></summary>

Calculate time of concentration three ways, with automatic method comparison.

| Mode | Input required | What you get |
|------|----------------|--------------|
| **Flowpath Layer** | Flowpath layer | TR-55 segment-based TC + comparison methods |
| **Manual Entry** | None (enter directly) | Comparison methods (quick estimates) |
| **DEM Extraction** | DEM + subbasins | Auto-extracted length/slope + SCS Lag or TR-55 |

**Comparison methods:** Kirpich (1940), FAA (1965), SCS Lag / NRCS, Kerby.

**Industry-standard flat-terrain fallbacks** (per TxDOT / Cleveland et al. 2012):
low-slope adjustment, minimum-TC enforcement, and adverse-slope handling for DEM errors —
with validation warnings for out-of-range CN, slope, or length.
</details>

<details>
<summary><b>📐 Channel Designer</b></summary>

Design trapezoidal channel cross-sections with full hydraulic calculations.

- Interactive channel visualization
- GIS layer import
- Manning's equation for velocity and capacity
- SWMM- and HEC-RAS-compatible coordinate output
</details>

---

## ⚡ Quick Start

**1. Clone the repository**

```bash
git clone https://github.com/Joeywoody124/hydro-suite-standalone.git
```

**2. Launch from the QGIS Python Console**

1. Open **QGIS 3.40+**
2. Open the Python Console — `Plugins ▸ Python Console` (or `Ctrl+Alt+P`)
3. Paste the launcher, updating the path to your clone:

```python
exec(open(r'C:\path\to\hydro-suite-standalone\launch_hydro_suite.py').read())
```

**3. Pick a tool** from the left panel of the Hydro Suite window — and go.

---

## 🎨 Themes

Hydro Suite ships **9 runtime-switchable visual themes** — from a clean corporate light mode to a
neon dark cyberpunk look. Switch instantly via the **Style dropdown** in the toolbar or
**View ▸ GUI Style**.

`Normal` · `Kinetic` · `Bauhaus` · `Enterprise` · `Cyberpunk` · `Academia` · `Sketch` · `Playful Geometric` · `Twisty`

---

## 📋 Requirements

| Requirement | Version |
|-------------|---------|
| **QGIS** | 3.40 or higher |
| **Python** | 3.9+ (bundled with QGIS) |
| **Dependencies** | PyQt5, pandas (all included with QGIS) |

No `pip install`, no virtual environment — if QGIS runs, Hydro Suite runs.

---

## 🗺️ Roadmap

| Priority | Feature | Status |
|----------|---------|--------|
| ⭐ **1** | PCSWMM & HY-8 automated report development | In active development |
| ⭐ **2** | SWMM QC reporting dashboard | In active development |
| 3 | Watershed delineation tool | Planned |
| 4 | Storm event analysis | Planned |
| 5 | Export to HEC-HMS format | Planned |
| 6 | Additional TC methods & custom theme editor | Planned |

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [HANDOFF.md](HANDOFF.md) | Current state and usage guide |
| [CHANGELOG.md](CHANGELOG.md) | Full version history |
| [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) | How to extend and modify tools |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution guidelines |
| [example_data/TUTORIALS.md](example_data/TUTORIALS.md) | Step-by-step tutorials with sample data |

---

## Editions

| Edition | Repository | Status |
|---------|------------|--------|
| **Standalone Scripts** *(this repo)* | [hydro-suite-standalone](https://github.com/Joeywoody124/hydro-suite-standalone) | ✅ Production ready |
| QGIS Plugin | [hydro-suite](https://github.com/Joeywoody124/hydro-suite) | 🔧 Under maintenance |

---

## 📄 License

Released under the **MIT License** — see [LICENSE](LICENSE) for details.

---

<div align="center">

**Joey Woody, PE** · J. Bragg Consulting Inc.
Civil / Water Resources Engineer

<sub>Hydro Suite — hydrology automation that keeps every number traceable.</sub>

</div>
