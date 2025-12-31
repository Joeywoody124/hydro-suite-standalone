"""
Style Loader for Hydro Suite (PyQt5 Version)
=============================================
Loads and normalizes style tokens from GUI Design Center Library.
Provides runtime GUI theme switching for QGIS applications.

Version: 1.0.0
Author: Joey Woody, PE - J. Bragg Consulting Inc.
Repository: https://github.com/Joeywoody124/hydro-suite-standalone
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List


# Default path to GUI Design Center Library styles folder
STYLES_BASE_PATH = Path(r"E:\CLAUDE_Workspace\Claude\Report_Files\GUI_Design_Center_Library\styles")

# Style mapping: display name -> token file path (relative to STYLES_BASE_PATH)
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
    """
    Load and normalize style tokens for PyQt5 applications.
    
    Usage:
        loader = StyleLoader()
        style = loader.load_style("Kinetic (Dark)")
        stylesheet = loader.generate_stylesheet(style)
        widget.setStyleSheet(stylesheet)
    """
    
    # Default "Normal" style (current Hydro Suite appearance)
    NORMAL_STYLE = {
        "name": "Normal (Default)",
        "background": "#f8f9fa",       # Light gray background
        "foreground": "#212529",       # Dark text
        "accent": "#007bff",           # Bootstrap blue
        "accent_secondary": "#17a2b8", # Info cyan
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
        """
        Initialize StyleLoader.
        
        Args:
            styles_base_path: Path to styles folder. Defaults to GUI Design Center Library.
        """
        self.base_path = styles_base_path or STYLES_BASE_PATH
        self.cache: Dict[str, Dict[str, Any]] = {}
        
    def get_available_styles(self) -> List[str]:
        """Return list of available style names."""
        return list(STYLE_MAP.keys())
    
    def load_style(self, style_key: str) -> Dict[str, Any]:
        """
        Load a style by name, with caching.
        
        Args:
            style_key: Style name from STYLE_MAP keys.
            
        Returns:
            Normalized style dictionary.
        """
        # Return Normal style for default or unknown styles
        if style_key == "Normal (Default)" or style_key not in STYLE_MAP:
            return self.NORMAL_STYLE.copy()
        
        # Check cache
        if style_key in self.cache:
            return self.cache[style_key]
        
        # Load from JSON
        token_path = self.base_path / STYLE_MAP[style_key]
        
        if not token_path.exists():
            print(f"[StyleLoader] Warning: Style file not found: {token_path}")
            return self.NORMAL_STYLE.copy()
        
        try:
            with open(token_path, "r", encoding="utf-8") as f:
                tokens = json.load(f)
            normalized = self._normalize_tokens(tokens)
            self.cache[style_key] = normalized
            return normalized
        except (json.JSONDecodeError, IOError) as e:
            print(f"[StyleLoader] Error loading style {style_key}: {e}")
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
            "button_hover": self._extract_color(tokens, "accentSecondary") or self._adjust_color(self._extract_color(tokens, "accent"), -20),
            "input_bg": self._extract_input_bg(tokens),
            "input_border": self._extract_color(tokens, "border"),
            "success": "#28a745",  # Keep consistent semantic colors
            "warning": "#ffc107",
            "error": "#dc3545",
            "font_family": self._extract_font(tokens),
            "is_dark": self._is_dark_mode(tokens),
        }
    
    def _extract_color(self, tokens: Dict, key: str) -> str:
        """Extract color value from tokens, handling nested structures."""
        colors = tokens.get("colors", {})
        
        # Direct string value
        if key in colors:
            val = colors[key]
            if isinstance(val, str):
                return val
            if isinstance(val, dict):
                return val.get("hex", "#808080")
        
        # Handle Bauhaus-style primary colors
        if key == "accent" and "primary" in colors:
            primary = colors["primary"]
            if isinstance(primary, dict):
                return primary.get("red", primary.get("hex", "#808080"))
        
        # Defaults
        defaults = {
            "background": "#1a1a1a", "foreground": "#ffffff",
            "accent": "#3b82f6", "accentSecondary": "#ec4899",
            "muted": "#374151", "mutedForeground": "#9ca3af",
            "border": "#4b5563", "card": "#2d2d2d",
        }
        return defaults.get(key, "#808080")
    
    def _extract_button_bg(self, tokens: Dict) -> str:
        """Extract button background color."""
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
        """Extract input background color."""
        components = tokens.get("components", {})
        inp = components.get("input", {})
        if isinstance(inp, dict):
            bg = inp.get("background", "")
            if isinstance(bg, str) and bg.startswith("#"):
                return bg
        # Fallback to card color
        return self._extract_color(tokens, "card")
    
    def _extract_font(self, tokens: Dict) -> str:
        """Extract font family."""
        typography = tokens.get("typography", {})
        font_family = typography.get("fontFamily", {})
        if isinstance(font_family, dict):
            primary = font_family.get("primary", "Arial")
            if isinstance(primary, str):
                # Clean font name (remove quotes, fallbacks)
                return primary.split(",")[0].strip().strip("'\"")
        return "Arial"
    
    def _is_dark_mode(self, tokens: Dict) -> bool:
        """Determine if dark mode based on background luminance."""
        # Check explicit mode first
        mode = tokens.get("mode", "")
        if mode.lower() == "dark":
            return True
        if mode.lower() == "light":
            return False
        
        # Calculate from background color
        bg = self._extract_color(tokens, "background")
        return self._is_dark_color(bg)
    
    def _is_dark_color(self, hex_color: str) -> bool:
        """Check if a hex color is dark (luminance < 0.5)."""
        if not hex_color or not hex_color.startswith("#"):
            return True
        try:
            r = int(hex_color[1:3], 16)
            g = int(hex_color[3:5], 16)
            b = int(hex_color[5:7], 16)
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            return luminance < 0.5
        except (ValueError, IndexError):
            return True
    
    def _adjust_color(self, hex_color: str, amount: int) -> str:
        """Adjust color brightness by amount (-255 to 255)."""
        if not hex_color or not hex_color.startswith("#"):
            return hex_color
        try:
            r = max(0, min(255, int(hex_color[1:3], 16) + amount))
            g = max(0, min(255, int(hex_color[3:5], 16) + amount))
            b = max(0, min(255, int(hex_color[5:7], 16) + amount))
            return f"#{r:02x}{g:02x}{b:02x}"
        except (ValueError, IndexError):
            return hex_color
    
    def generate_stylesheet(self, style: Dict[str, Any]) -> str:
        """
        Generate PyQt5 stylesheet from style tokens.
        
        Args:
            style: Normalized style dictionary from load_style().
            
        Returns:
            Qt Style Sheet string.
        """
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
        success = style["success"]
        warning = style["warning"]
        error = style["error"]
        font = style["font_family"]
        is_dark = style["is_dark"]
        
        # Adjust input text color based on background
        input_fg = fg if is_dark else "#212529"
        
        return f"""
        /* ============================================ */
        /* Hydro Suite Style: {style['name']}          */
        /* ============================================ */
        
        /* Main Window and Base Widgets */
        QMainWindow, QDialog {{
            background-color: {bg};
            color: {fg};
            font-family: {font};
        }}
        
        QWidget {{
            background-color: transparent;
            color: {fg};
            font-family: {font};
        }}
        
        /* Frames and Panels */
        QFrame {{
            background-color: transparent;
            border: none;
        }}
        
        QFrame[frameShape="4"], QFrame[frameShape="StyledPanel"] {{
            background-color: {card};
            border: 1px solid {border};
            border-radius: 4px;
        }}
        
        /* Splitter */
        QSplitter::handle {{
            background-color: {border};
        }}
        
        QSplitter::handle:horizontal {{
            width: 2px;
        }}
        
        QSplitter::handle:vertical {{
            height: 2px;
        }}
        
        /* Labels */
        QLabel {{
            background-color: transparent;
            color: {fg};
            border: none;
        }}
        
        /* Buttons */
        QPushButton {{
            background-color: {btn_bg};
            color: {btn_fg};
            border: none;
            border-radius: 5px;
            padding: 8px 16px;
            font-weight: bold;
            min-height: 20px;
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
            color: {input_fg};
            border: 2px solid {input_border};
            border-radius: 4px;
            padding: 6px;
            selection-background-color: {accent};
            selection-color: {btn_fg};
        }}
        
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border-color: {accent};
        }}
        
        QLineEdit:disabled, QTextEdit:disabled {{
            background-color: {muted};
            color: {muted_fg};
        }}
        
        /* ComboBox */
        QComboBox {{
            background-color: {input_bg};
            color: {input_fg};
            border: 2px solid {input_border};
            border-radius: 4px;
            padding: 6px 10px;
            min-height: 20px;
        }}
        
        QComboBox:focus {{
            border-color: {accent};
        }}
        
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        
        QComboBox::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid {fg};
            margin-right: 5px;
        }}
        
        QComboBox QAbstractItemView {{
            background-color: {card};
            color: {fg};
            border: 1px solid {border};
            selection-background-color: {accent};
            selection-color: {btn_fg};
        }}
        
        /* List Widget */
        QListWidget {{
            background-color: {card};
            color: {fg};
            border: 1px solid {border};
            border-radius: 4px;
            outline: none;
        }}
        
        QListWidget::item {{
            padding: 10px 12px;
            border-bottom: 1px solid {border};
        }}
        
        QListWidget::item:selected {{
            background-color: {accent};
            color: {btn_fg};
        }}
        
        QListWidget::item:hover:!selected {{
            background-color: {muted};
        }}
        
        /* Stacked Widget */
        QStackedWidget {{
            background-color: {bg};
        }}
        
        /* Tab Widget */
        QTabWidget::pane {{
            background-color: {card};
            border: 1px solid {border};
            border-radius: 4px;
            top: -1px;
        }}
        
        QTabBar::tab {{
            background-color: {muted};
            color: {fg};
            padding: 10px 20px;
            border: 1px solid {border};
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            margin-right: 2px;
        }}
        
        QTabBar::tab:selected {{
            background-color: {card};
            color: {accent};
            font-weight: bold;
        }}
        
        QTabBar::tab:hover:!selected {{
            background-color: {border};
        }}
        
        /* Scroll Area */
        QScrollArea {{
            background-color: transparent;
            border: none;
        }}
        
        QScrollArea > QWidget > QWidget {{
            background-color: transparent;
        }}
        
        /* Progress Bar */
        QProgressBar {{
            background-color: {muted};
            border: none;
            border-radius: 5px;
            height: 10px;
            text-align: center;
        }}
        
        QProgressBar::chunk {{
            background-color: {accent};
            border-radius: 5px;
        }}
        
        /* Scroll Bars */
        QScrollBar:vertical {{
            background-color: {bg};
            width: 12px;
            border: none;
            margin: 0;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {muted};
            border-radius: 6px;
            min-height: 30px;
            margin: 2px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {muted_fg};
        }}
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
            background: none;
        }}
        
        QScrollBar:horizontal {{
            background-color: {bg};
            height: 12px;
            border: none;
        }}
        
        QScrollBar::handle:horizontal {{
            background-color: {muted};
            border-radius: 6px;
            min-width: 30px;
            margin: 2px;
        }}
        
        QScrollBar::handle:horizontal:hover {{
            background-color: {muted_fg};
        }}
        
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0;
            background: none;
        }}
        
        /* Menu Bar */
        QMenuBar {{
            background-color: {bg};
            color: {fg};
            border-bottom: 1px solid {border};
            padding: 2px;
        }}
        
        QMenuBar::item {{
            padding: 6px 12px;
            background-color: transparent;
        }}
        
        QMenuBar::item:selected {{
            background-color: {accent};
            color: {btn_fg};
            border-radius: 4px;
        }}
        
        QMenu {{
            background-color: {card};
            color: {fg};
            border: 1px solid {border};
            border-radius: 4px;
            padding: 4px;
        }}
        
        QMenu::item {{
            padding: 8px 24px;
            border-radius: 4px;
        }}
        
        QMenu::item:selected {{
            background-color: {accent};
            color: {btn_fg};
        }}
        
        QMenu::separator {{
            height: 1px;
            background-color: {border};
            margin: 4px 8px;
        }}
        
        /* Status Bar */
        QStatusBar {{
            background-color: {muted};
            color: {muted_fg};
            border-top: 1px solid {border};
        }}
        
        QStatusBar::item {{
            border: none;
        }}
        
        /* Tool Bar */
        QToolBar {{
            background-color: {bg};
            border: none;
            border-bottom: 1px solid {border};
            spacing: 6px;
            padding: 4px;
        }}
        
        QToolBar::separator {{
            width: 1px;
            background-color: {border};
            margin: 4px 8px;
        }}
        
        QToolButton {{
            background-color: transparent;
            color: {fg};
            border: none;
            border-radius: 4px;
            padding: 6px 12px;
        }}
        
        QToolButton:hover {{
            background-color: {muted};
        }}
        
        QToolButton:pressed {{
            background-color: {accent};
            color: {btn_fg};
        }}
        
        /* Group Box */
        QGroupBox {{
            background-color: {card};
            border: 1px solid {border};
            border-radius: 6px;
            margin-top: 14px;
            padding-top: 14px;
            font-weight: bold;
        }}
        
        QGroupBox::title {{
            color: {accent};
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 12px;
            padding: 0 6px;
            background-color: {card};
        }}
        
        /* Table Widget */
        QTableWidget, QTableView {{
            background-color: {card};
            color: {fg};
            gridline-color: {border};
            border: 1px solid {border};
            border-radius: 4px;
            selection-background-color: {accent};
            selection-color: {btn_fg};
        }}
        
        QTableWidget::item, QTableView::item {{
            padding: 6px;
        }}
        
        QHeaderView::section {{
            background-color: {muted};
            color: {fg};
            padding: 8px;
            border: none;
            border-right: 1px solid {border};
            border-bottom: 1px solid {border};
            font-weight: bold;
        }}
        
        QHeaderView::section:hover {{
            background-color: {border};
        }}
        
        /* SpinBox */
        QSpinBox, QDoubleSpinBox {{
            background-color: {input_bg};
            color: {input_fg};
            border: 2px solid {input_border};
            border-radius: 4px;
            padding: 4px 8px;
            min-height: 20px;
        }}
        
        QSpinBox:focus, QDoubleSpinBox:focus {{
            border-color: {accent};
        }}
        
        QSpinBox::up-button, QDoubleSpinBox::up-button,
        QSpinBox::down-button, QDoubleSpinBox::down-button {{
            background-color: {muted};
            border: none;
            width: 16px;
        }}
        
        QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
        QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
            background-color: {border};
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
        
        QCheckBox::indicator:hover {{
            border-color: {accent};
        }}
        
        QCheckBox::indicator:checked {{
            background-color: {accent};
            border-color: {accent};
        }}
        
        /* Radio Button */
        QRadioButton {{
            color: {fg};
            spacing: 8px;
        }}
        
        QRadioButton::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {border};
            border-radius: 9px;
            background-color: {input_bg};
        }}
        
        QRadioButton::indicator:hover {{
            border-color: {accent};
        }}
        
        QRadioButton::indicator:checked {{
            background-color: {accent};
            border-color: {accent};
        }}
        
        /* Slider */
        QSlider::groove:horizontal {{
            height: 6px;
            background-color: {muted};
            border-radius: 3px;
        }}
        
        QSlider::handle:horizontal {{
            width: 18px;
            height: 18px;
            background-color: {accent};
            border-radius: 9px;
            margin: -6px 0;
        }}
        
        QSlider::handle:horizontal:hover {{
            background-color: {btn_hover};
        }}
        
        /* ToolTip */
        QToolTip {{
            background-color: {card};
            color: {fg};
            border: 1px solid {border};
            border-radius: 4px;
            padding: 6px;
        }}
        
        /* Message Box */
        QMessageBox {{
            background-color: {bg};
        }}
        
        QMessageBox QLabel {{
            color: {fg};
        }}
        """


def get_style_loader() -> StyleLoader:
    """Factory function to get StyleLoader instance."""
    return StyleLoader(STYLES_BASE_PATH)
