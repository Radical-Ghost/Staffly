"""
Theme management for Staffly application.
Supports Catppuccin Mocha (dark) and Catppuccin Latte (light) themes.

Usage:
    from staffly.ui.theme import load_theme, get_current_theme, ThemeMode

    # Load a theme (applies globally)
    load_theme("mocha")  # Dark theme
    load_theme("latte")  # Light theme

    # Get current theme info
    mode = get_current_theme()  # Returns "mocha" or "latte"
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional
import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings


def _get_base_dir() -> Path:
    """Return base resource directory, handling both source and PyInstaller bundle."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "staffly" / "ui" / "resources"
    return Path(__file__).parent / "resources"


class ThemeMode(Enum):
    """Available theme modes."""
    MOCHA = "mocha"   # Dark theme
    LATTE = "latte"   # Light theme


@dataclass
class ThemeColors:
    """Color definitions for a theme."""
    # Base colors
    background: str
    surface: str
    surface_alt: str
    text_primary: str
    text_secondary: str
    border: str
    overlay: str

    # Accent colors
    primary: str
    primary_hover: str

    # Status colors
    success: str
    danger: str
    warning: str
    info: str
    selection: str
    selection_text: str


# ═══════════════════════════════════════════════════════════════════════════
# CATPPUCCIN COLOR PALETTES
# ═══════════════════════════════════════════════════════════════════════════

CATPPUCCIN_MOCHA = ThemeColors(
    background="#1e1e2e",
    surface="#181825",
    surface_alt="#313244",
    text_primary="#cdd6f4",
    text_secondary="#a6adc8",
    border="#45475a",
    overlay="#6c7086",
    primary="#cba6f7",
    primary_hover="#b48cf2",
    success="#a6e3a1",
    danger="#f38ba8",
    warning="#f9e2af",
    info="#89b4fa",
    selection="#89b4fa",
    selection_text="#1e1e2e",
)

CATPPUCCIN_LATTE = ThemeColors(
    background="#eff1f5",
    surface="#e6e9ef",
    surface_alt="#dce0e8",
    text_primary="#4c4f69",
    text_secondary="#6c6f85",
    border="#bcc0cc",
    overlay="#9ca0b0",
    primary="#8839ef",
    primary_hover="#9b5df0",
    success="#40a02b",
    danger="#d20f39",
    warning="#df8e1d",
    info="#1e66f5",
    selection="#1e66f5",
    selection_text="#ffffff",
)


# ═══════════════════════════════════════════════════════════════════════════
# THEME MANAGER
# ═══════════════════════════════════════════════════════════════════════════

class ThemeManager:
    """
    Singleton class to manage application theming.

    Loads QSS files and applies them globally via QApplication.setStyleSheet().
    """

    _instance: Optional["ThemeManager"] = None
    _current_mode: ThemeMode = ThemeMode.MOCHA
    _settings: QSettings
    _initialized: bool = False

    def __new__(cls) -> "ThemeManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._settings = QSettings("Staffly", "Staffly")
        self._load_saved_theme()

    def _load_saved_theme(self) -> None:
        """Load saved theme preference from settings."""
        saved = self._settings.value("theme/mode", "mocha")
        if saved == "latte":
            self._current_mode = ThemeMode.LATTE
        else:
            self._current_mode = ThemeMode.MOCHA

    def _save_theme(self) -> None:
        """Save current theme preference to settings."""
        self._settings.setValue("theme/mode", self._current_mode.value)
        self._settings.sync()

    @property
    def mode(self) -> ThemeMode:
        """Get current theme mode."""
        return self._current_mode

    @property
    def colors(self) -> ThemeColors:
        """Get current theme colors."""
        if self._current_mode == ThemeMode.LATTE:
            return CATPPUCCIN_LATTE
        return CATPPUCCIN_MOCHA

    @property
    def is_dark(self) -> bool:
        """Check if dark theme is active."""
        return self._current_mode == ThemeMode.MOCHA

    def _get_styles_dir(self) -> Path:
        """Get the path to the styles directory."""
        return _get_base_dir() / "styles"

    def _load_qss_file(self, theme_name: str) -> str:
        """Load QSS file content for the given theme."""
        qss_file = self._get_styles_dir() / f"catppuccin_{theme_name}.qss"

        if not qss_file.exists():
            return ""

        with open(qss_file, "r", encoding="utf-8") as f:
            return f.read()

    def _process_stylesheet(self, qss: str) -> str:
        """Process stylesheet and inject robust native UI fixes."""
        c = self.colors

        # Prevent terminal warnings about missing SVGs from the base QSS
        qss = qss.replace("url(chevron-down.svg)", "none")
        qss = qss.replace("url(chevron-down-dark.svg)", "none")

        supplementary_fixes = f"""
        /* ═══════════════════════════════════════════════════════════════
           DROPDOWN ARROWS (ComboBox & DateEdit)
           ═══════════════════════════════════════════════════════════════ */

        QComboBox:focus, QDateEdit:focus {{
            border: 2px solid {c.primary};
        }}

        /* ═══════════════════════════════════════════════════════════════
           CALENDAR WIDGET REWRITE
           ═══════════════════════════════════════════════════════════════ */

        QCalendarWidget {{
            background-color: {c.background};
            border: 1px solid {c.border};
            border-radius: 8px;
        }}

        /* Top Navigation Bar */
        QCalendarWidget QWidget#qt_calendar_navigationbar {{
            background-color: {c.surface};
            border-bottom: 1px solid {c.border};
            min-height: 44px;
        }}

        /* Month/Year Buttons */
        QCalendarWidget QToolButton {{
            background-color: transparent;
            color: {c.text_primary};
            border: none;
            border-radius: 4px;
            padding: 4px 8px;
            margin: 2px;
            font-weight: bold;
            font-size: 14px;
        }}

        QCalendarWidget QToolButton:hover {{
            background-color: {c.surface_alt};
        }}

        QCalendarWidget QToolButton::menu-indicator {{
            image: none; /* Strip the glitchy arrow */
        }}

        /* Year Spinbox */
        QCalendarWidget QSpinBox {{
            background-color: transparent;
            color: {c.text_primary};
            border: none;
            font-size: 14px;
            font-weight: bold;
        }}
        QCalendarWidget QSpinBox::up-button, QCalendarWidget QSpinBox::down-button {{
            width: 0px;
            border: none;
        }}

        /* Calendar Table Grid */
        QCalendarWidget QTableView {{
            background-color: {c.background};
            alternate-background-color: {c.background};
            selection-background-color: {c.primary};
            selection-color: {c.background};
            font-size: 13px;
            outline: none;
            border: none;
        }}

        /* Day Headers (Mon, Tue, etc.) */
        QCalendarWidget QHeaderView::section {{
            background-color: {c.background};
            color: {c.text_secondary};
            border: none;
            font-weight: bold;
            padding: 6px;
        }}

        /* Fix the weird artifact on selected columns */
        QCalendarWidget QHeaderView::section:checked {{
            background-color: transparent;
            color: {c.text_primary};
        }}

        /* Day Cells */
        QCalendarWidget QTableView::item {{
            color: {c.text_primary};
            border-radius: 4px;
            padding: 4px;
        }}

        QCalendarWidget QTableView::item:selected {{
            background-color: {c.primary};
            color: {c.background};
            font-weight: bold;
            border-radius: 4px;
        }}

        QCalendarWidget QTableView::item:hover {{
            background-color: {c.surface_alt};
            border-radius: 4px;
        }}

        /* Fix Popup Menus for Calendar */
        QCalendarWidget QMenu {{
            background-color: {c.surface};
            color: {c.text_primary};
            border: 1px solid {c.border};
        }}
        QCalendarWidget QMenu::item:selected {{
            background-color: {c.primary};
            color: {c.background};
        }}
        """

        return qss + supplementary_fixes

    def apply_theme(self, mode: ThemeMode) -> None:
        """
        Apply a theme to the entire application.

        Args:
            mode: ThemeMode.MOCHA or ThemeMode.LATTE
        """
        self._current_mode = mode
        self._save_theme()

        # Load and process the QSS file
        qss = self._load_qss_file(mode.value)
        qss = self._process_stylesheet(qss)

        # Apply globally to the application
        app = QApplication.instance()
        if app:
            app.setStyleSheet(qss)

    def toggle_theme(self) -> None:
        """Toggle between dark (mocha) and light (latte) themes."""
        if self._current_mode == ThemeMode.MOCHA:
            self.apply_theme(ThemeMode.LATTE)
        else:
            self.apply_theme(ThemeMode.MOCHA)

    def get_stylesheet(self) -> str:
        """
        Get the current theme stylesheet.
        Useful for applying to specific widgets.
        """
        qss = self._load_qss_file(self._current_mode.value)
        return self._process_stylesheet(qss)


# ═══════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

_theme_manager: Optional[ThemeManager] = None


def get_theme() -> ThemeManager:
    """
    Get the global ThemeManager instance.

    Returns:
        ThemeManager: The singleton theme manager instance.
    """
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager


def load_theme(theme: str) -> None:
    """
    Load and apply a theme globally.

    Args:
        theme: Theme name - "mocha" for dark, "latte" for light

    Example:
        load_theme("mocha")  # Apply dark theme
        load_theme("latte")  # Apply light theme
    """
    manager = get_theme()

    if theme.lower() == "latte":
        manager.apply_theme(ThemeMode.LATTE)
    else:
        manager.apply_theme(ThemeMode.MOCHA)


def get_current_theme() -> str:
    """
    Get the name of the currently active theme.

    Returns:
        str: "mocha" or "latte"
    """
    return get_theme().mode.value


def get_theme_colors() -> ThemeColors:
    """
    Get the color palette for the current theme.

    Returns:
        ThemeColors: Current theme color definitions
    """
    return get_theme().colors


def toggle_theme() -> None:
    """Toggle between dark and light themes."""
    get_theme().toggle_theme()


def is_dark_theme() -> bool:
    """
    Check if the dark theme is currently active.

    Returns:
        bool: True if dark (mocha) theme is active
    """
    return get_theme().is_dark
