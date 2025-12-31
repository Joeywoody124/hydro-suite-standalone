# Hydro Suite Standalone - GUI Style Customization Handoff

**Project**: Hydro Suite Standalone  
**Feature**: Multi-Style GUI Customization  
**Date**: January 2025  
**Author**: Joey Woody, PE - J. Bragg Consulting Inc.

---

## Executive Summary

Add a dropdown selector to the Hydro Suite Standalone application that allows users to switch between multiple visual themes at runtime. The default theme is "Normal" (current appearance), with additional options from the GUI Design Center Library.

---

## Current State

**Location**: `E:\CLAUDE_Workspace\Claude\Report_Files\Finished_Code\Hydro_Suite_Data_Backup_v1\github_standalone`

**Files to Modify**:
- `hydro_suite_main.py` - Main window (add style selector and apply_style method)
- `shared_widgets.py` - Shared UI components (may need style-aware updates)

**New Files to Create**:
- `style_loader.py` - StyleLoader class for PyQt5
- `styles/` - Local copy of required style tokens (or reference library path)

---

## GUI Design Center Library Reference

**Library Location**: `E:\CLAUDE_Workspace\Claude\Report_Files\GUI_Design_Center_Library`

**Available Styles (8 total)**:

| Style Name | Mode | Primary Accent | Vibe |
|------------|------|----------------|------|
| Normal (Default) | Current | Current | Keep existing appearance |
| Kinetic (Dark) | Dark | Acid Yellow #DFE104 | High-energy, brutalist |
| Bauhaus (Light) | Light | Red #D02020 | Geometric, modernist |
| Enterprise (Light) | Light | Indigo #4F46E5 | Corporate, SaaS |
| Cyberpunk (Dark) | Dark | Matrix Green #00ff88 | Dystopian, neon |
| Academia (Dark) | Dark | Brass #C9A962 | Scholarly, classical |
| Sketch (Light) | Light | Red Marker #ff4d4d | Hand-drawn, playful |
| Playful Geometric (Light) | Light | Violet #8B5CF6 | Memphis, bouncy |
| Twisty (Dark) | Dark | Violet #8B5CF6 | Fintech, modern |

**Token Files Location**: `E:\CLAUDE_Workspace\Claude\Report_Files\GUI_Design_Center_Library\styles\{style_name}\tokens.json`

---

## Implementation Requirements

### 1. Style Selector UI

Add a combobox/dropdown near the top of the main window:

```
┌─────────────────────────────────────────────────────┐
│  GUI Style: [Normal (Default)    ▼]                 │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Available Tools                                    │
│  ━━ Runoff Analysis ━━                              │
│    ▸ Curve Number Calculator                        │
│    ▸ Rational C Calculator                          │
│  ...                                                │
└─────────────────────────────────────────────────────┘
```

**Requirements**:
- Dropdown positioned in toolbar or above tool list
- Default selection: "Normal (Default)"
- Change applies immediately (no restart needed)
- Style preference NOT persisted between sessions (optional enhancement)

### 2. StyleLoader Class for PyQt5

Create `style_loader.py` based on the tkinter version but adapted for PyQt5/QGIS:

```python
"""
Style Loader for Hydro Suite (PyQt5 Version)
Loads and normalizes style tokens from GUI Design Center Library.

Version: 1.0.0
Author: Joey Woody, PE
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

# Default: Reference GUI Design Center Library
STYLES_BASE_PATH = Path(r"E:\CLAUDE_Workspace\Claude\Report_Files\GUI_Design_Center_Library\styles")

# Style mapping
STYLE_MAP = {
    "Normal (Default)": None,  # No token file - use hardcoded defaults
    "Kinetic (Dark)": "kinetic/tokens.json",
    "Bauhaus (Light)": "bauhaus/tokens.json",
    "Enterprise (Light)": "enterprise/tokens.json",
    "Cyberpunk (Dark)": "cyberpunk/tokens.json",
    "Academia (Dark)": "academia/tokens.json",
    "Sketch (Light)": "sketch/tokens.json",
    "Playful Geometric (Light)": "playful-geometric/tokens.json",
    "Twisty (Dark)": "twisty/tokens.json",
}


class StyleLoader:
    """Load and normalize style tokens for PyQt5 applications."""
    
    # Default "Normal" style (current Hydro Suite appearance)
    NORMAL_STYLE = {
        "name": "Normal (Default)",
        "background": "#f8f9fa",      # Light gray background
        "foreground": "#212529",       # Dark text
        "accent": "#007bff",           # Bootstrap blue
        "accent_secondary": "#6c757d", # Secondary gray
        "muted": "#e9ecef",            # Muted background
        "muted_fg": "#6c757d",         # Muted text
        "border": "#dee2e6",           # Border color
        "card": "#ffffff",             # Card/panel background
        "button_bg": "#007bff",        # Primary button
        "button_fg": "#ffffff",        # Button text
        "button_hover": "#0056b3",     # Button hover
        "input_bg": "#ffffff",         # Input background
        "input_border": "#ced4da",     # Input border
        "success": "#28a745",          # Success green
        "warning": "#ffc107",          # Warning yellow
        "error": "#dc3545",            # Error red
        "font_family": "Arial",
        "is_dark": False,
    }
    
    def __init__(self, styles_base_path: Path = None):
        self.base_path = styles_base_path or STYLES_BASE_PATH
        self.cache: Dict[str, Dict[str, Any]] = {}
        
    def get_available_styles(self) -> list:
        """Return list of available style names."""
        return list(STYLE_MAP.keys())
    
    def load_style(self, style_key: str) -> Optional[Dict[str, Any]]:
        """Load a style by name, with caching."""
        # Return Normal style for default
        if style_key == "Normal (Default)" or style_key not in STYLE_MAP:
            return self.NORMAL_STYLE.copy()
        
        # Check cache
        if style_key in self.cache:
            return self.cache[style_key]
        
        # Load from JSON
        token_path = self.base_path / STYLE_MAP[style_key]
        
        if not token_path.exists():
            print(f"Warning: Style file not found: {token_path}")
            return self.NORMAL_STYLE.copy()
        
        try:
            with open(token_path, "r", encoding="utf-8") as f:
                tokens = json.load(f)
            normalized = self._normalize_tokens(tokens)
            self.cache[style_key] = normalized
            return normalized
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading style {style_key}: {e}")
            return self.NORMAL_STYLE.copy()
    
    def _normalize_tokens(self, tokens: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize token structure to consistent format."""
        return {
            "name": tokens.get("name", "Unknown"),
            "background": self._extract_color(tokens, "background"),
            "foreground": self._extract_color(tokens, "foreground"),
            "accent": self._extract_color(tokens, "accent") or self._extract_color(tokens, "primary"),
            "accent_secondary": self._extract_color(tokens, "accentSecondary") or self._extract_color(tokens, "secondary"),
            "muted": self._extract_color(tokens, "muted"),
            "muted_fg": self._extract_color(tokens, "mutedForeground"),
            "border": self._extract_color(tokens, "border"),
            "card": self._extract_color(tokens, "card") or self._extract_color(tokens, "surface"),
            "button_bg": self._extract_button_bg(tokens),
            "button_fg": self._extract_button_fg(tokens),
            "button_hover": self._extract_color(tokens, "accentSecondary") or self._extract_color(tokens, "accent"),
            "input_bg": self._extract_input_bg(tokens),
            "input_border": self._extract_color(tokens, "border"),
            "success": "#28a745",  # Keep consistent semantic colors
            "warning": "#ffc107",
            "error": "#dc3545",
            "font_family": self._extract_font(tokens),
            "is_dark": self._is_dark_mode(tokens),
        }
    
    def _extract_color(self, tokens: Dict, key: str) -> str:
        """Extract color value from tokens."""
        colors = tokens.get("colors", {})
        
        if key in colors:
            val = colors[key]
            if isinstance(val, str):
                return val
            if isinstance(val, dict):
                return val.get("hex", "#808080")
        
        # Defaults
        defaults = {
            "background": "#1a1a1a", "foreground": "#ffffff",
            "accent": "#3b82f6", "accentSecondary": "#ec4899",
            "muted": "#374151", "mutedForeground": "#9ca3af",
            "border": "#4b5563", "card": "#2d2d2d",
        }
        return defaults.get(key, "#808080")
    
    def _extract_button_bg(self, tokens: Dict) -> str:
        """Extract button background."""
        components = tokens.get("components", {})
        button = components.get("button", {})
        primary = button.get("primary", {})
        if isinstance(primary, dict):
            bg = primary.get("background", "")
            if isinstance(bg, str) and bg.startswith("#"):
                return bg
        return self._extract_color(tokens, "accent")
    
    def _extract_button_fg(self, tokens: Dict) -> str:
        """Extract button text color."""
        components = tokens.get("components", {})
        button = components.get("button", {})
        primary = button.get("primary", {})
        if isinstance(primary, dict):
            text = primary.get("text", "")
            if isinstance(text, str) and text.startswith("#"):
                return text
        return "#ffffff"
    
    def _extract_input_bg(self, tokens: Dict) -> str:
        """Extract input background."""
        components = tokens.get("components", {})
        inp = components.get("input", {})
        if isinstance(inp, dict):
            bg = inp.get("background", "")
            if isinstance(bg, str) and bg.startswith("#"):
                return bg
        return self._extract_color(tokens, "card")
    
    def _extract_font(self, tokens: Dict) -> str:
        """Extract font family."""
        typography = tokens.get("typography", {})
        font_family = typography.get("fontFamily", {})
        if isinstance(font_family, dict):
            primary = font_family.get("primary", "Arial")
            if isinstance(primary, str):
                return primary.split(",")[0].strip().strip("'\"")
        return "Arial"
    
    def _is_dark_mode(self, tokens: Dict) -> bool:
        """Determine if dark mode based on background."""
        mode = tokens.get("mode", "")
        if mode.lower() == "dark":
            return True
        if mode.lower() == "light":
            return False
        
        bg = self._extract_color(tokens, "background")
        if bg.startswith("#"):
            try:
                r = int(bg[1:3], 16)
                g = int(bg[3:5], 16)
                b = int(bg[5:7], 16)
                luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
                return luminance < 0.5
            except ValueError:
                pass
        return True
```

### 3. PyQt5 Stylesheet Generation

Create method to generate PyQt5 stylesheets from tokens:

```python
def generate_stylesheet(self, style: Dict[str, Any]) -> str:
    """Generate PyQt5 stylesheet from style tokens."""
    
    bg = style["background"]
    fg = style["foreground"]
    accent = style["accent"]
    accent_sec = style["accent_secondary"]
    muted = style["muted"]
    muted_fg = style["muted_fg"]
    border = style["border"]
    card = style["card"]
    btn_bg = style["button_bg"]
    btn_fg = style["button_fg"]
    btn_hover = style["button_hover"]
    input_bg = style["input_bg"]
    input_border = style["input_border"]
    font = style["font_family"]
    
    return f"""
    /* Main Window */
    QMainWindow, QWidget {{
        background-color: {bg};
        color: {fg};
        font-family: {font};
    }}
    
    /* Frames and Panels */
    QFrame {{
        background-color: {bg};
        border: 1px solid {border};
    }}
    
    QFrame[frameShape="StyledPanel"] {{
        background-color: {card};
        border: 1px solid {border};
        border-radius: 4px;
    }}
    
    /* Labels */
    QLabel {{
        background-color: transparent;
        color: {fg};
    }}
    
    QLabel[class="title"] {{
        color: {accent};
        font-weight: bold;
    }}
    
    QLabel[class="muted"] {{
        color: {muted_fg};
    }}
    
    /* Buttons */
    QPushButton {{
        background-color: {btn_bg};
        color: {btn_fg};
        border: none;
        border-radius: 4px;
        padding: 8px 16px;
        font-weight: bold;
    }}
    
    QPushButton:hover {{
        background-color: {btn_hover};
    }}
    
    QPushButton:pressed {{
        background-color: {accent};
    }}
    
    QPushButton:disabled {{
        background-color: {muted};
        color: {muted_fg};
    }}
    
    /* Input Fields */
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {input_bg};
        color: {fg};
        border: 2px solid {input_border};
        border-radius: 4px;
        padding: 6px;
    }}
    
    QLineEdit:focus, QTextEdit:focus {{
        border-color: {accent};
    }}
    
    /* ComboBox */
    QComboBox {{
        background-color: {input_bg};
        color: {fg};
        border: 2px solid {input_border};
        border-radius: 4px;
        padding: 6px;
    }}
    
    QComboBox:focus {{
        border-color: {accent};
    }}
    
    QComboBox::drop-down {{
        border: none;
    }}
    
    QComboBox::down-arrow {{
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 5px solid {fg};
    }}
    
    QComboBox QAbstractItemView {{
        background-color: {card};
        color: {fg};
        selection-background-color: {accent};
        selection-color: {btn_fg};
    }}
    
    /* List Widget */
    QListWidget {{
        background-color: {card};
        color: {fg};
        border: 1px solid {border};
        border-radius: 4px;
    }}
    
    QListWidget::item {{
        padding: 8px;
        border-bottom: 1px solid {border};
    }}
    
    QListWidget::item:selected {{
        background-color: {accent};
        color: {btn_fg};
    }}
    
    QListWidget::item:hover {{
        background-color: {muted};
    }}
    
    /* Tabs */
    QTabWidget::pane {{
        background-color: {card};
        border: 1px solid {border};
    }}
    
    QTabBar::tab {{
        background-color: {muted};
        color: {fg};
        padding: 8px 16px;
        border: 1px solid {border};
        border-bottom: none;
    }}
    
    QTabBar::tab:selected {{
        background-color: {card};
        color: {accent};
    }}
    
    /* Progress Bar */
    QProgressBar {{
        background-color: {muted};
        border: none;
        border-radius: 4px;
        height: 10px;
    }}
    
    QProgressBar::chunk {{
        background-color: {accent};
        border-radius: 4px;
    }}
    
    /* Scroll Bars */
    QScrollBar:vertical {{
        background-color: {bg};
        width: 12px;
        border: none;
    }}
    
    QScrollBar::handle:vertical {{
        background-color: {muted};
        border-radius: 6px;
        min-height: 20px;
    }}
    
    QScrollBar::handle:vertical:hover {{
        background-color: {muted_fg};
    }}
    
    /* Menu Bar */
    QMenuBar {{
        background-color: {bg};
        color: {fg};
    }}
    
    QMenuBar::item:selected {{
        background-color: {accent};
        color: {btn_fg};
    }}
    
    QMenu {{
        background-color: {card};
        color: {fg};
        border: 1px solid {border};
    }}
    
    QMenu::item:selected {{
        background-color: {accent};
        color: {btn_fg};
    }}
    
    /* Status Bar */
    QStatusBar {{
        background-color: {muted};
        color: {muted_fg};
    }}
    
    /* Tool Bar */
    QToolBar {{
        background-color: {bg};
        border: none;
        spacing: 4px;
    }}
    
    /* Group Box */
    QGroupBox {{
        background-color: {card};
        border: 1px solid {border};
        border-radius: 4px;
        margin-top: 12px;
        padding-top: 12px;
    }}
    
    QGroupBox::title {{
        color: {accent};
        subcontrol-origin: margin;
        left: 10px;
    }}
    
    /* Table */
    QTableWidget {{
        background-color: {card};
        color: {fg};
        gridline-color: {border};
        border: 1px solid {border};
    }}
    
    QTableWidget::item:selected {{
        background-color: {accent};
        color: {btn_fg};
    }}
    
    QHeaderView::section {{
        background-color: {muted};
        color: {fg};
        padding: 8px;
        border: 1px solid {border};
    }}
    
    /* SpinBox */
    QSpinBox, QDoubleSpinBox {{
        background-color: {input_bg};
        color: {fg};
        border: 2px solid {input_border};
        border-radius: 4px;
        padding: 4px;
    }}
    
    QSpinBox:focus, QDoubleSpinBox:focus {{
        border-color: {accent};
    }}
    
    /* CheckBox */
    QCheckBox {{
        color: {fg};
        spacing: 8px;
    }}
    
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border: 2px solid {border};
        border-radius: 4px;
        background-color: {input_bg};
    }}
    
    QCheckBox::indicator:checked {{
        background-color: {accent};
        border-color: {accent};
    }}
    """
```

### 4. Integration into HydroSuiteMainWindow

Modify `hydro_suite_main.py`:

```python
# Add to imports
from style_loader import StyleLoader, STYLE_MAP

class HydroSuiteMainWindow(QMainWindow):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.controller = HydroSuiteController()
        self.current_tool = None
        
        # Initialize style system
        self.style_loader = StyleLoader()
        self.current_style_name = "Normal (Default)"
        
        # ... existing code ...
        
        self.setup_ui()
        self.setup_menu()
        self.setup_toolbar()  # Add style selector here
        self.setup_statusbar()
        self.load_settings()
        
        # Apply initial style
        self._apply_style("Normal (Default)")
    
    def setup_toolbar(self):
        """Setup the toolbar with style selector."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Style selector
        style_label = QLabel("  Style: ")
        toolbar.addWidget(style_label)
        
        self.style_combo = QComboBox()
        self.style_combo.addItems(self.style_loader.get_available_styles())
        self.style_combo.setCurrentText("Normal (Default)")
        self.style_combo.currentTextChanged.connect(self._on_style_change)
        self.style_combo.setMinimumWidth(180)
        toolbar.addWidget(self.style_combo)
        
        toolbar.addSeparator()
        
        # ... rest of toolbar setup ...
    
    def _on_style_change(self, style_name: str):
        """Handle style dropdown change."""
        self._apply_style(style_name)
    
    def _apply_style(self, style_name: str):
        """Apply selected style to the entire application."""
        style = self.style_loader.load_style(style_name)
        if not style:
            return
        
        self.current_style_name = style_name
        
        # Generate and apply stylesheet
        stylesheet = self.style_loader.generate_stylesheet(style)
        self.setStyleSheet(stylesheet)
        
        # Update status bar
        self.status_bar.showMessage(f"Style: {style['name']}")
        
        # Log the change
        self.log(f"Applied style: {style_name}")
```

---

## File Structure After Implementation

```
hydro-suite-standalone/
├── launch_hydro_suite.py
├── hydro_suite_main.py         # Modified - add style selector
├── hydro_suite_interface.py
├── shared_widgets.py
├── style_loader.py             # NEW - StyleLoader for PyQt5
├── cn_calculator_tool.py
├── rational_c_tool.py
├── tc_calculator_tool.py
├── channel_designer_tool.py
├── README.md
├── DEVELOPER_GUIDE.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── LICENSE
└── .gitignore
```

---

## Testing Checklist

- [ ] Style dropdown appears in toolbar
- [ ] Default "Normal (Default)" style matches current appearance
- [ ] Each style applies without errors:
  - [ ] Kinetic (Dark)
  - [ ] Bauhaus (Light)
  - [ ] Enterprise (Light)
  - [ ] Cyberpunk (Dark)
  - [ ] Academia (Dark)
  - [ ] Sketch (Light)
  - [ ] Playful Geometric (Light)
  - [ ] Twisty (Dark)
- [ ] All widgets update (buttons, labels, inputs, lists, tabs)
- [ ] Text remains readable in all styles
- [ ] Tool interfaces remain functional after style change
- [ ] No crashes when switching styles rapidly
- [ ] Graceful fallback if style file missing

---

## Optional Enhancements (Future)

1. **Persist style preference** - Save selected style to QSettings
2. **Per-tool styling** - Allow different styles per tool
3. **Custom colors** - Allow user to customize accent colors
4. **Font scaling** - Add font size preference
5. **High contrast mode** - Accessibility option
6. **Export theme** - Export current theme as JSON

---

## Reference Files

| File | Location |
|------|----------|
| GUI Library README | `E:\CLAUDE_Workspace\Claude\Report_Files\GUI_Design_Center_Library\README.md` |
| Retrofit Guide | `E:\CLAUDE_Workspace\Claude\Report_Files\GUI_Design_Center_Library\GUI_MULTI_STYLE_RETROFIT_GUIDE.md` |
| Example (tkinter) | `E:\CLAUDE_Workspace\Claude\Report_Files\GUI_Design_Center_Library\Example\mortgage_calculator_multi_style.py` |
| Style Tokens | `E:\CLAUDE_Workspace\Claude\Report_Files\GUI_Design_Center_Library\styles\{style}\tokens.json` |

---

## Dependencies

- No new Python dependencies required
- Uses existing PyQt5 from QGIS
- Reads JSON files from GUI Design Center Library

---

## Notes

1. **PyQt5 vs tkinter**: The GUI Design Center Library guide is for tkinter. This handoff adapts the approach for PyQt5 using stylesheets instead of widget.configure().

2. **QGIS Integration**: Since Hydro Suite runs in QGIS Python Console, all styles must work within QGIS's Qt environment.

3. **Style File Location**: The implementation references the GUI Design Center Library path. If deploying standalone, consider copying token files into the repo.

4. **Kinetic as Default**: Per user preferences, Kinetic (Dark) is the recommended default. However, "Normal (Default)" is used to preserve current appearance unless explicitly changed.

---

*Handoff Version: 1.0*
*Created: January 2025*
*Author: Joey Woody, PE - J. Bragg Consulting Inc.*
