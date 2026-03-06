"""Theme management for Staffly application."""

from dataclasses import dataclass
from enum import Enum
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings


class ThemeMode(Enum):
    """Available theme modes."""
    LIGHT = "light"
    DARK = "dark"


@dataclass
class ThemeColors:
    """Color definitions for a theme."""
    # Base colors
    background: str
    text: str
    border: str
    
    # Table specific
    table_header: str
    selection_text: str
    

# Define theme color palettes
DARK_THEME = ThemeColors(
    background="#1d1d26",
    text="#aeb3d4",
    border="#3a3a41",
    table_header="#1f1f29",
    selection_text="#ffffff",
)

LIGHT_THEME = ThemeColors(
    background="#f4f5f9",
    text="#191918",
    border="#d8dfe7",
    table_header="#e8eaef",
    selection_text="#191918",
)


class ThemeManager:
    """
    Manages application theming and scaling.
    
    Usage:
        theme = ThemeManager()
        theme.apply_theme(ThemeMode.DARK)
        theme.set_scale(1.0)  # 100%
        
        # Get current colors
        colors = theme.colors
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._settings = QSettings("Staffly", "Staffly")
        self._current_mode = self._load_saved_theme()
        self._colors = LIGHT_THEME if self._current_mode == ThemeMode.LIGHT else DARK_THEME
        self._scale_factor = self._load_saved_scale()
    
    def _load_saved_theme(self) -> ThemeMode:
        """Load saved theme preference."""
        saved = self._settings.value("theme/mode", "dark")
        return ThemeMode.LIGHT if saved == "light" else ThemeMode.DARK
    
    def _save_theme(self, mode: ThemeMode):
        """Save theme preference."""
        self._settings.setValue("theme/mode", mode.value)
    
    def _load_saved_scale(self) -> float:
        """Load saved scale factor."""
        return self._settings.value("ui_scale_factor", 1.0, type=float)
    
    def _save_scale(self, scale: float):
        """Save scale factor."""
        self._settings.setValue("ui_scale_factor", scale)
        self._settings.sync()
    
    @property
    def mode(self) -> ThemeMode:
        """Get current theme mode."""
        return self._current_mode
    
    @property
    def colors(self) -> ThemeColors:
        """Get current theme colors."""
        return self._colors
    
    @property
    def is_dark(self) -> bool:
        """Check if dark mode is active."""
        return self._current_mode == ThemeMode.DARK
    
    @property
    def scale_factor(self) -> float:
        """Get current scale factor."""
        return self._scale_factor
    
    def set_scale(self, scale: float):
        """Set UI scale factor and apply immediately."""
        self._scale_factor = scale
        self._save_scale(scale)
        self._apply_current_settings()
    
    def toggle_theme(self):
        """Toggle between light and dark mode."""
        new_mode = ThemeMode.LIGHT if self._current_mode == ThemeMode.DARK else ThemeMode.DARK
        self.apply_theme(new_mode)
    
    def apply_theme(self, mode: ThemeMode):
        """Apply a theme to the application."""
        self._current_mode = mode
        self._colors = LIGHT_THEME if mode == ThemeMode.LIGHT else DARK_THEME
        self._save_theme(mode)
        self._apply_current_settings()
    
    def _apply_current_settings(self):
        """Apply current theme and scale to the application."""
        app = QApplication.instance()
        if app:
            app.setStyleSheet(self.get_stylesheet())
    
    def _scaled(self, value: int) -> int:
        """Scale a pixel value by the current scale factor."""
        return int(value * self._scale_factor)
    
    def get_stylesheet(self) -> str:
        """Generate the global stylesheet for current theme with scaling."""
        c = self._colors
        s = self._scaled  # Shorthand for scaling
        
        return f"""
            /* ═══════════════════════════════════════════════════════════════
               GLOBAL BASE STYLES
               ═══════════════════════════════════════════════════════════════ */
            
            QWidget {{
                background-color: {c.background};
                color: {c.text};
                font-size: {s(14)}px;
            }}
            
            QMainWindow {{
                background-color: {c.background};
            }}
            
            /* ═══════════════════════════════════════════════════════════════
               TABS
               ═══════════════════════════════════════════════════════════════ */
            
            QTabWidget::pane {{
                border: 1px solid {c.border};
                background-color: {c.background};
            }}
            
            QTabBar::tab {{
                background-color: {c.background};
                color: {c.text};
                border: 1px solid {c.border};
                padding: {s(10)}px {s(20)}px;
                font-size: {s(14)}px;
                font-weight: bold;
            }}
            
            QTabBar::tab:selected {{
                background-color: {c.border};
            }}
            
            QTabBar::tab:hover:!selected {{
                background-color: {c.border};
            }}
            
            /* ═══════════════════════════════════════════════════════════════
               INPUTS
               ═══════════════════════════════════════════════════════════════ */
            
            QLineEdit, QTextEdit, QPlainTextEdit {{
                background-color: {c.background};
                color: {c.text};
                border: 1px solid {c.border};
                border-radius: {s(4)}px;
                padding: {s(6)}px;
                font-size: {s(14)}px;
                min-height: {s(30)}px;
            }}
            
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
                border: 2px solid {c.border};
            }}
            
            QComboBox {{
                background-color: {c.background};
                color: {c.text};
                border: 1px solid {c.border};
                border-radius: {s(4)}px;
                padding: {s(6)}px {s(10)}px;
                padding-right: {s(35)}px;
                font-size: {s(14)}px;
                min-height: {s(30)}px;
            }}
            
            QComboBox::drop-down {{
                subcontrol-origin: border;
                subcontrol-position: center right;
                width: {s(30)}px;
                border-left: 1px solid {c.border};
                background-color: {c.border};
                border-top-right-radius: {s(4)}px;
                border-bottom-right-radius: {s(4)}px;
            }}
            
            QComboBox::drop-down:hover {{
                background-color: {c.text};
            }}
            
            QComboBox::down-arrow {{
                image: url(none);
                border: none;
            }}
            
            QComboBox QAbstractItemView {{
                background-color: {c.background};
                color: {c.text};
                border: 1px solid {c.border};
                selection-background-color: {c.border};
            }}
            
            QSpinBox, QDoubleSpinBox {{
                background-color: {c.background};
                color: {c.text};
                border: 1px solid {c.border};
                border-radius: {s(4)}px;
                padding: {s(6)}px;
                font-size: {s(14)}px;
                min-height: {s(30)}px;
            }}
            
            QDateEdit {{
                background-color: {c.background};
                color: {c.text};
                border: 1px solid {c.border};
                border-radius: {s(4)}px;
                padding: {s(6)}px;
                padding-right: {s(30)}px;
                font-size: {s(14)}px;
                min-height: {s(30)}px;
            }}
            
            QDateEdit::drop-down {{
                subcontrol-origin: border;
                subcontrol-position: center right;
                width: {s(30)}px;
                border-left: 1px solid {c.border};
                background-color: {c.border};
                border-top-right-radius: {s(4)}px;
                border-bottom-right-radius: {s(4)}px;
            }}
            
            QDateEdit::drop-down:hover {{
                background-color: {c.text};
            }}
            
            QDateEdit::down-arrow {{
                image: none;
                width: 0;
                height: 0;
                border-left: {s(6)}px solid transparent;
                border-right: {s(6)}px solid transparent;
                border-top: {s(8)}px solid {c.background};
                margin: 0;
            }}
            
            QDateEdit QAbstractItemView {{
                background-color: {c.background};
                color: {c.text};
                selection-background-color: {c.border};
            }}
            
            /* ═══════════════════════════════════════════════════════════════
               TABLES
               ═══════════════════════════════════════════════════════════════ */
            
            QTableWidget, QTableView {{
                background-color: {c.background};
                alternate-background-color: {c.background};
                color: {c.text};
                border: 1px solid {c.border};
                gridline-color: {c.border};
                font-size: {s(14)}px;
                outline: none;
                selection-background-color: {c.border};
                selection-color: {c.selection_text};
            }}
            
            QTableWidget::item, QTableView::item {{
                background-color: {c.background};
                padding: {s(8)}px;
                border: none;
                outline: none;
            }}
            
            QTableWidget::item:selected, QTableView::item:selected {{
                background-color: {c.border};
                color: {c.selection_text};
                border: none;
                outline: none;
            }}
            
            QTableWidget::item:focus, QTableView::item:focus {{
                border: none;
                outline: none;
            }}
            
            QTableWidget:focus, QTableView:focus {{
                border: 2px solid {c.border};
                outline: none;
            }}
            
            QHeaderView {{
                background-color: {c.table_header};
            }}
            
            QHeaderView::section {{
                background-color: {c.table_header};
                color: {c.text};
                border: none;
                border-bottom: 1px solid {c.border};
                border-right: 1px solid {c.border};
                padding: {s(8)}px;
                font-size: {s(14)}px;
                font-weight: bold;
            }}
            
            QHeaderView::section:horizontal {{
                background-color: {c.table_header};
            }}
            
            QHeaderView::section:vertical {{
                background-color: {c.table_header};
            }}
            
            /* ═══════════════════════════════════════════════════════════════
               GROUP BOXES
               ═══════════════════════════════════════════════════════════════ */
            
            QGroupBox {{
                background-color: {c.background};
                border: 1px solid {c.border};
                border-radius: {s(4)}px;
                margin-top: {s(12)}px;
                padding-top: {s(10)}px;
                font-size: {s(14)}px;
                font-weight: bold;
            }}
            
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: {s(10)}px;
                padding: 0 {s(5)}px;
                color: {c.text};
            }}
            
            /* ═══════════════════════════════════════════════════════════════
               LABELS
               ═══════════════════════════════════════════════════════════════ */
            
            QLabel {{
                font-size: {s(14)}px;
                background-color: transparent;
            }}
            
            /* ═══════════════════════════════════════════════════════════════
               CHECKBOXES
               ═══════════════════════════════════════════════════════════════ */
            
            QCheckBox {{
                font-size: {s(14)}px;
                spacing: {s(8)}px;
            }}
            
            QCheckBox::indicator {{
                width: {s(20)}px;
                height: {s(20)}px;
                border: 2px solid {c.border};
                border-radius: {s(4)}px;
                background-color: {c.background};
            }}
            
            QCheckBox::indicator:hover {{
                border: 2px solid {c.text};
            }}
            
            QCheckBox::indicator:checked {{
                background-color: #4CAF50;
                border: 2px solid #4CAF50;
            }}
            
            QCheckBox::indicator:checked:hover {{
                background-color: #45a049;
                border: 2px solid #45a049;
            }}
            
            /* ═══════════════════════════════════════════════════════════════
               SCROLLBARS
               ═══════════════════════════════════════════════════════════════ */
            
            QScrollBar:vertical {{
                background-color: {c.background};
                width: {s(12)}px;
                border: none;
            }}
            
            QScrollBar::handle:vertical {{
                background-color: {c.border};
                border-radius: {s(4)}px;
                min-height: {s(30)}px;
                margin: 2px;
            }}
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            
            QScrollBar:horizontal {{
                background-color: {c.background};
                height: {s(12)}px;
                border: none;
            }}
            
            QScrollBar::handle:horizontal {{
                background-color: {c.border};
                border-radius: {s(4)}px;
                min-width: {s(30)}px;
                margin: 2px;
            }}
            
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            
            /* ═══════════════════════════════════════════════════════════════
               DIALOGS
               ═══════════════════════════════════════════════════════════════ */
            
            QDialog {{
                background-color: {c.background};
                color: {c.text};
            }}
            
            /* ═══════════════════════════════════════════════════════════════
               MESSAGE BOXES
               ═══════════════════════════════════════════════════════════════ */
            
            QMessageBox {{
                background-color: {c.background};
            }}
            
            QMessageBox QLabel {{
                color: {c.text};
            }}
            
            /* ═══════════════════════════════════════════════════════════════
               MENUS (Fixed size - not affected by scaling)
               ═══════════════════════════════════════════════════════════════ */
            
            QMenuBar {{
                background-color: {c.background};
                color: {c.text};
                border-bottom: 1px solid {c.border};
                font-size: 15px;
            }}
            
            QMenuBar::item {{
                padding: 7px 13px;
            }}
            
            QMenuBar::item:selected {{
                background-color: {c.border};
            }}
            
            QMenu {{
                background-color: {c.background};
                color: {c.text};
                border: 1px solid {c.border};
                font-size: 15px;
            }}
            
            QMenu::item {{
                padding: 9px 28px;
            }}
            
            QMenu::item:selected {{
                background-color: {c.border};
            }}
            
            /* ═══════════════════════════════════════════════════════════════
               TOOLTIPS
               ═══════════════════════════════════════════════════════════════ */
            
            QToolTip {{
                background-color: {c.background};
                color: {c.text};
                border: 1px solid {c.border};
                padding: {s(4)}px;
                font-size: {s(13)}px;
            }}
            
            /* ═══════════════════════════════════════════════════════════════
               STATUS BAR
               ═══════════════════════════════════════════════════════════════ */
            
            QStatusBar {{
                background-color: {c.background};
                color: {c.text};
                border-top: 1px solid {c.border};
                font-size: {s(13)}px;
            }}
            
            /* ═══════════════════════════════════════════════════════════════
               CALENDAR WIDGET
               ═══════════════════════════════════════════════════════════════ */
            
            QCalendarWidget {{
                background-color: {c.background};
                min-width: {s(350)}px;
                min-height: {s(300)}px;
            }}
            
            QCalendarWidget QTableView {{
                background-color: {c.background};
                selection-background-color: {c.border};
                font-size: {s(14)}px;
                min-width: {s(320)}px;
            }}
            
            QCalendarWidget QTableView::item {{
                padding: {s(8)}px;
                min-width: {s(40)}px;
                min-height: {s(30)}px;
            }}
            
            QCalendarWidget QWidget#qt_calendar_navigationbar {{
                background-color: {c.background};
                min-height: {s(40)}px;
            }}
            
            QCalendarWidget QToolButton {{
                color: {c.text};
                background-color: {c.background};
                border: 1px solid {c.border};
                border-radius: {s(4)}px;
                padding: {s(6)}px {s(10)}px;
                font-size: {s(14)}px;
                min-width: {s(30)}px;
            }}
            
            QCalendarWidget QToolButton:hover {{
                background-color: {c.border};
            }}
            
            QCalendarWidget QSpinBox {{
                background-color: {c.background};
                color: {c.text};
                border: 1px solid {c.border};
                font-size: {s(14)}px;
                min-width: {s(60)}px;
            }}
            
            QCalendarWidget QMenu {{
                background-color: {c.background};
                color: {c.text};
            }}
            
            QCalendarWidget #qt_calendar_monthbutton {{
                min-width: {s(100)}px;
            }}
            
            QCalendarWidget #qt_calendar_yearbutton {{
                min-width: {s(60)}px;
            }}
            
            /* ═══════════════════════════════════════════════════════════════
               BUTTONS (Generic)
               ═══════════════════════════════════════════════════════════════ */
            
            QPushButton {{
                font-size: {s(13)}px;
                padding: {s(8)}px {s(16)}px;
                border-radius: {s(4)}px;
            }}
            
            /* ═══════════════════════════════════════════════════════════════
               INPUT DIALOG
               ═══════════════════════════════════════════════════════════════ */
            
            QInputDialog {{
                min-width: {s(300)}px;
            }}
        """


# Global theme manager instance
def get_theme() -> ThemeManager:
    """Get the global theme manager instance."""
    return ThemeManager()
