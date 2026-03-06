"""Payroll period creation dialog."""

import calendar
from datetime import date
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QPushButton,
    QMessageBox,
    QLabel,
    QWidget,
)
from PySide6.QtCore import Qt

from staffly.database import get_db
from staffly.database.models import PayrollPeriod
from staffly.database.repositories import PayrollPeriodRepository


class PeriodDialog(QDialog):
    """
    Dialog for creating a new payroll period.
    """

    MONTHS = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]

    def __init__(self, parent=None, selected_company_id: int | None = None, selected_company_name: str | None = None):
        super().__init__(parent)
        self.selected_company_id = selected_company_id
        self.selected_company_name = selected_company_name
        self._setup_ui()
        self._set_defaults()
        self._update_working_days_preview()

    def _setup_ui(self):
        """Setup the dialog UI."""
        self.setWindowTitle("Create New Payroll Period")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)

        # Form
        form_layout = QFormLayout()

        # Month/Year picker - two combo boxes side by side
        period_widget = QWidget()
        period_layout = QHBoxLayout(period_widget)
        period_layout.setContentsMargins(0, 0, 0, 0)
        period_layout.setSpacing(10)

        from PySide6.QtWidgets import QComboBox
        self.combo_month = QComboBox()
        self.combo_month.addItems(self.MONTHS)
        self.combo_month.setMinimumWidth(150)

        self.combo_year = QComboBox()
        current_year = date.today().year
        years = [str(y) for y in range(current_year - 2, current_year + 5)]
        self.combo_year.addItems(years)
        self.combo_year.setMinimumWidth(100)

        self.combo_month.currentIndexChanged.connect(self._update_working_days_preview)
        self.combo_year.currentIndexChanged.connect(self._update_working_days_preview)

        period_layout.addWidget(self.combo_month)
        period_layout.addWidget(self.combo_year)
        period_layout.addStretch()

        form_layout.addRow("Period:", period_widget)

        # Working days (auto-calculated from selected month/year)
        self.lbl_working_days = QLabel("-")
        self.lbl_working_days.setStyleSheet("font-weight: 600;")
        form_layout.addRow("Working Days:", self.lbl_working_days)

        layout.addLayout(form_layout)

        # Info
        info_label = QLabel(
            "💡 After creating, click 'Generate Payroll' to create records for all active employees."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray;")
        if self.selected_company_name:
            info_label.setText(
                f"💡 Company: {self.selected_company_name}. After creating, click 'Generate Payroll' to create records for active employees."
            )
        layout.addWidget(info_label)

        # Buttons
        btn_layout = QHBoxLayout()

        btn_style = """
            QPushButton {
                font-size: 13px;
                font-weight: bold;
                border-radius: 4px;
                border: 2px solid transparent;
            }
            QPushButton:hover {
                border: 2px solid #333;
            }
            QPushButton:pressed {
                border: 2px solid #000;
            }
        """

        self.btn_create = QPushButton("📅 Create Period")
        self.btn_create.setFixedSize(150, 50)
        self.btn_create.setStyleSheet(btn_style + """
            QPushButton { background-color: #4CAF50; color: white; }
            QPushButton:hover { background-color: #45a049; }
        """)
        self.btn_create.clicked.connect(self._on_create)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setFixedSize(150, 50)
        self.btn_cancel.setStyleSheet(btn_style + """
            QPushButton { background-color: #9e9e9e; color: white; }
            QPushButton:hover { background-color: #757575; }
        """)
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_create)
        btn_layout.addWidget(self.btn_cancel)

        layout.addLayout(btn_layout)

    def _set_defaults(self):
        """Set default values based on existing periods."""
        db = get_db()
        current_year = date.today().year
        
        with db.get_session() as session:
            repo = PayrollPeriodRepository(session)
            latest = repo.get_latest()

            if latest:
                # Set to next month
                next_year = latest.year
                next_month = latest.month + 1
                if next_month > 12:
                    next_month = 1
                    next_year += 1

                self.combo_month.setCurrentIndex(next_month - 1)
                year_index = self.combo_year.findText(str(next_year))
                if year_index >= 0:
                    self.combo_year.setCurrentIndex(year_index)
            else:
                # Default to current month
                today = date.today()
                self.combo_month.setCurrentIndex(today.month - 1)
                year_index = self.combo_year.findText(str(today.year))
                if year_index >= 0:
                    self.combo_year.setCurrentIndex(year_index)

        self._update_working_days_preview()

    def _get_days_in_selected_month(self) -> int:
        """Return total days for selected month/year (handles leap years)."""
        month = self.combo_month.currentIndex() + 1
        year = int(self.combo_year.currentText())
        return calendar.monthrange(year, month)[1]

    def _update_working_days_preview(self):
        """Update read-only working days preview from selected month/year."""
        self.lbl_working_days.setText(str(self._get_days_in_selected_month()))

    def _on_create(self):
        """Create the payroll period."""
        month = self.combo_month.currentIndex() + 1
        year = int(self.combo_year.currentText())
        working_days = self._get_days_in_selected_month()
        month_name = self.combo_month.currentText()

        db = get_db()
        with db.get_session() as session:
            repo = PayrollPeriodRepository(session)

            # Check if period already exists
            existing = repo.get_by_year_month(year, month)
            if existing:
                QMessageBox.warning(
                    self,
                    "Already Exists",
                    f"Payroll period for {month_name} {year} already exists."
                )
                return

            # Create new period
            period = PayrollPeriod(
                year=year,
                month=month,
                period_label=PayrollPeriod.generate_label(year, month),
                working_days=working_days,
                is_locked=False,
            )

            repo.create(period)
            repo.commit()

        QMessageBox.information(
            self,
            "Created",
            f"Payroll period '{month_name} {year}' created successfully."
        )
        self.accept()
