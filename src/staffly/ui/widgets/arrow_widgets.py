"""Custom widgets with visible arrow indicators."""

from PySide6.QtWidgets import QComboBox, QDateEdit, QWidget, QHBoxLayout, QCheckBox
from PySide6.QtGui import QPainter, QColor, QPolygon
from PySide6.QtCore import Qt, QPoint, QDate, Signal


class ArrowComboBox(QComboBox):
    """ComboBox with a visible triangle arrow indicator."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def paintEvent(self, event):
        super().paintEvent(event)
        self._draw_arrow()
    
    def _draw_arrow(self):
        """Draw triangle arrow on the right side."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Arrow position - centered in the dropdown area
        arrow_x = self.width() - 15
        arrow_y = self.height() // 2
        
        # Draw triangle (pointing down)
        arrow_color = QColor("#aeb3d4")  # Light color for visibility
        painter.setBrush(arrow_color)
        painter.setPen(Qt.NoPen)
        
        triangle = QPolygon([
            QPoint(arrow_x - 5, arrow_y - 3),
            QPoint(arrow_x + 5, arrow_y - 3),
            QPoint(arrow_x, arrow_y + 4),
        ])
        painter.drawPolygon(triangle)
        painter.end()


class ArrowDateEdit(QDateEdit):
    """DateEdit with a visible triangle arrow indicator and working calendar."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCalendarPopup(True)
        self.setDisplayFormat("dd-MM-yyyy")
        
    def paintEvent(self, event):
        super().paintEvent(event)
        self._draw_arrow()
    
    def _draw_arrow(self):
        """Draw triangle arrow on the right side."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Arrow position - centered in the dropdown area
        arrow_x = self.width() - 15
        arrow_y = self.height() // 2
        
        # Draw triangle (pointing down)
        arrow_color = QColor("#aeb3d4")  # Light color for visibility
        painter.setBrush(arrow_color)
        painter.setPen(Qt.NoPen)
        
        triangle = QPolygon([
            QPoint(arrow_x - 5, arrow_y - 3),
            QPoint(arrow_x + 5, arrow_y - 3),
            QPoint(arrow_x, arrow_y + 4),
        ])
        painter.drawPolygon(triangle)
        painter.end()


class OptionalDateEdit(QWidget):
    """
    A date edit with a checkbox to toggle between a date and 'No Date/Current'.
    
    When checkbox is checked, shows "Current (No End Date)".
    When unchecked, shows a date picker.
    """
    
    dateChanged = Signal(object)  # Emits QDate or None
    
    def __init__(self, parent=None, label: str = "Current (No End Date)"):
        super().__init__(parent)
        self._label = label
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Date edit
        self.date_edit = ArrowDateEdit()
        self.date_edit.setDisplayFormat("dd-MM-yyyy")
        self.date_edit.setMinimumWidth(150)
        self.date_edit.dateChanged.connect(self._on_date_changed)
        
        # Checkbox for "No Date"
        self.chk_no_date = QCheckBox(self._label)
        self.chk_no_date.setChecked(True)
        self.chk_no_date.toggled.connect(self._on_checkbox_toggled)
        
        layout.addWidget(self.date_edit)
        layout.addWidget(self.chk_no_date)
        layout.addStretch()
        
        # Initial state - no date selected
        self._update_state()
    
    def _on_checkbox_toggled(self, checked: bool):
        """Handle checkbox toggle."""
        self._update_state()
        if checked:
            self.dateChanged.emit(None)
        else:
            self.dateChanged.emit(self.date_edit.date())
    
    def _on_date_changed(self, date: QDate):
        """Handle date change."""
        if not self.chk_no_date.isChecked():
            self.dateChanged.emit(date)
    
    def _update_state(self):
        """Update widget state based on checkbox."""
        self.date_edit.setEnabled(not self.chk_no_date.isChecked())
        if self.chk_no_date.isChecked():
            self.date_edit.setStyleSheet("color: gray;")
        else:
            self.date_edit.setStyleSheet("")
    
    def date(self) -> QDate | None:
        """Get the selected date, or None if 'No Date' is checked."""
        if self.chk_no_date.isChecked():
            return None
        return self.date_edit.date()
    
    def setDate(self, date: QDate | None):
        """Set the date. Pass None to check 'No Date'."""
        if date is None:
            self.chk_no_date.setChecked(True)
        else:
            self.chk_no_date.setChecked(False)
            self.date_edit.setDate(date)
        self._update_state()
    
    def setNoDate(self, checked: bool = True):
        """Set whether 'No Date' is checked."""
        self.chk_no_date.setChecked(checked)
        self._update_state()
    
    def isNoDate(self) -> bool:
        """Check if 'No Date' is selected."""
        return self.chk_no_date.isChecked()
