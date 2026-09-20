"""Attendance widget for managing employee attendance data."""

from decimal import Decimal
from typing import Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
    QHeaderView,
    QPushButton,
    QComboBox,
    QLabel,
    QFrame,
    QMessageBox,
    QStyledItemDelegate,
    QLineEdit,
    QApplication,
)
from PySide6.QtCore import Qt, QTimer, QEvent
from PySide6.QtGui import QBrush, QColor, QDoubleValidator, QShortcut, QKeySequence

from staffly.database.connection import get_db
from staffly.database.repositories import (
    PayrollPeriodRepository,
    MonthlyPayrollRepository,
    EmployeeRepository,
    LeaveBalanceRepository,
)
from staffly.services.payroll_service import PayrollService, get_financial_year
from staffly.ui.dialogs.period_dialog import PeriodDialog


class NumericEditDelegate(QStyledItemDelegate):
    """Delegate for editing numeric cells with proper validation."""

    def __init__(self, decimals: int = 1, parent=None):
        super().__init__(parent)
        self.decimals = decimals

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        validator = QDoubleValidator(0, 999999, self.decimals, editor)
        editor.setValidator(validator)
        return editor

    def setEditorData(self, editor, index):
        text = index.model().data(index, Qt.DisplayRole) or "0"
        # Remove currency symbols
        text = text.replace("₹", "").replace(",", "").strip()
        editor.setText(text)

    def setModelData(self, editor, model, index):
        text = editor.text().strip()
        if text == "":
            text = "0"
        try:
            val = float(text)
            formatted = f"{val:.{self.decimals}f}"
            model.setData(index, formatted, Qt.DisplayRole)
        except ValueError:
            pass


class AttendanceWidget(QWidget):
    """Widget for managing employee attendance data."""

    # Column configuration: (name, width, editable, decimals)
    COLUMNS = [
        ("ID", 50, False, 0),
        ("Emp Code", 120, False, 0),
        ("Name", 160, False, 0),
        ("Total Days", 110, False, 0),
        ("Paid", 100, False, 0),
        ("Present", 100, False, 0),
        ("PL", 100, True, 1),
        ("SL", 100, True, 1),
        ("CL", 100, True, 1),
        ("Absent", 100, True, 1),
        ("Late", 100, True, 1),
        ("Bal PL", 100, False, 1),
        ("Bal SL", 100, False, 1),
        ("Bal CL", 100, False, 1),
    ]

    # Column indices
    COL_ID = 0
    COL_EMP_CODE = 1
    COL_NAME = 2
    COL_TOTAL_DAYS = 3
    COL_PAID = 4
    COL_PRESENT = 5
    COL_PL = 6
    COL_SL = 7
    COL_CL = 8
    COL_ABSENT = 9
    COL_LATE = 10
    COL_BAL_PL = 11
    COL_BAL_SL = 12
    COL_BAL_CL = 13

    def __init__(
        self,
        selected_company_id: int,
        selected_company_name: str,
        parent=None,
    ):
        super().__init__(parent)
        self.selected_company_id = selected_company_id
        self.selected_company_name = selected_company_name
        self._pending_changes: dict = {}
        self._is_loading = False
        self._auto_save_timer = QTimer(self)
        self._auto_save_timer.setSingleShot(True)
        self._auto_save_timer.timeout.connect(self._save_pending_changes)

        self._setup_ui()
        self._setup_zoom_shortcuts()
        self._load_periods()

    def _setup_ui(self):
        """Initialize the widget layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Header card
        header_card = QFrame()
        header_card.setObjectName("card")
        header_layout = QVBoxLayout(header_card)
        header_layout.setContentsMargins(20, 16, 20, 16)
        header_layout.setSpacing(12)

        # Title row
        title_row = QHBoxLayout()
        title = QLabel("Attendance Management")
        title.setObjectName("cardHeader")
        title_row.addWidget(title)
        title_row.addStretch()

        # Company badge
        company_badge = QLabel(self.selected_company_name)
        company_badge.setObjectName("badge")
        title_row.addWidget(company_badge)

        header_layout.addLayout(title_row)

        # Controls row
        controls_row = QHBoxLayout()
        controls_row.setSpacing(12)

        # Period selector
        period_label = QLabel("Period:")
        controls_row.addWidget(period_label)

        self.period_combo = QComboBox()
        self.period_combo.setMinimumWidth(200)
        self.period_combo.currentIndexChanged.connect(self._on_period_changed)
        controls_row.addWidget(self.period_combo)

        # New Period button
        self.btn_new_period = QPushButton("+ New Period")
        self.btn_new_period.setObjectName("primaryButton")
        self.btn_new_period.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new_period.clicked.connect(self._on_new_period)
        controls_row.addWidget(self.btn_new_period)

        # Delete Period button
        self.btn_delete_period = QPushButton("🗑 Delete Period")
        self.btn_delete_period.setObjectName("dangerButton")
        self.btn_delete_period.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete_period.clicked.connect(self._on_delete_period)
        controls_row.addWidget(self.btn_delete_period)

        controls_row.addStretch()

        # Refresh button
        self.btn_refresh = QPushButton("↻ Refresh")
        self.btn_refresh.setObjectName("secondaryButton")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.clicked.connect(self._refresh_all)
        controls_row.addWidget(self.btn_refresh)

        header_layout.addLayout(controls_row)

        # Info row
        info_row = QHBoxLayout()
        info_row.setSpacing(24)

        self.lbl_period_status = QLabel("Status: -")
        info_row.addWidget(self.lbl_period_status)

        self.lbl_employee_count = QLabel("Employees: 0")
        info_row.addWidget(self.lbl_employee_count)

        self.lbl_save_status = QLabel("")
        self.lbl_save_status.setObjectName("statusLabel")
        info_row.addWidget(self.lbl_save_status)

        info_row.addStretch()

        # Generate button
        self.btn_generate = QPushButton("Generate Attendance")
        self.btn_generate.setObjectName("successButton")
        self.btn_generate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_generate.clicked.connect(self._on_generate_attendance)
        self.btn_generate.setEnabled(False)
        info_row.addWidget(self.btn_generate)

        header_layout.addLayout(info_row)

        layout.addWidget(header_card)

        # Legend row
        legend_card = QFrame()
        legend_card.setObjectName("card")
        legend_layout = QHBoxLayout(legend_card)
        legend_layout.setContentsMargins(16, 8, 16, 8)

        legend_layout.addStretch()
        legend_layout.addWidget(QLabel("Editable: PL, SL, CL, Absent, Late"))

        layout.addWidget(legend_card)

        # Table card
        table_card = QFrame()
        table_card.setObjectName("card")
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(0, 0, 0, 0)

        # Attendance table
        self.table = QTableWidget()
        self.table.setObjectName("dataTable")
        self.table.setColumnCount(len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels([col[0] for col in self.COLUMNS])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)

        # Set column widths
        for i, (_, width, _, _) in enumerate(self.COLUMNS):
            self.table.setColumnWidth(i, width)

        # Hide ID column
        self.table.setColumnHidden(self.COL_ID, True)

        # Stretch the name column
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(self.COL_NAME, QHeaderView.Stretch)

        # Set up delegates for editable columns
        numeric_delegate = NumericEditDelegate(decimals=1, parent=self.table)
        for col_idx in [self.COL_PL, self.COL_SL, self.COL_CL, self.COL_ABSENT, self.COL_LATE]:
            self.table.setItemDelegateForColumn(col_idx, numeric_delegate)

        # Connect signals
        self.table.cellChanged.connect(self._on_cell_changed)
        self.table.currentCellChanged.connect(self._on_current_cell_changed)
        self.table.installEventFilter(self)

        # Track currently highlighted row
        self._highlighted_row = -1

        table_layout.addWidget(self.table)
        layout.addWidget(table_card, 1)

    def _load_periods(self):
        """Load available payroll periods."""
        self.period_combo.blockSignals(True)
        self.period_combo.clear()

        db = get_db()
        with db.get_session() as session:
            period_repo = PayrollPeriodRepository(session)
            periods = period_repo.get_all()

            for period in periods:
                self.period_combo.addItem(period.period_label, userData=period.id)

        self.period_combo.blockSignals(False)

        if self.period_combo.count() > 0:
            self.period_combo.setCurrentIndex(0)
            self._on_period_changed()
        else:
            self._clear_status()

    def _on_period_changed(self):
        """Handle period selection change."""
        period_id = self.period_combo.currentData()
        if period_id:
            self._load_attendance_data(period_id)
            self._update_buttons(period_id)

    def _on_delete_period(self):
        """Delete the selected payroll period."""
        period_id = self.period_combo.currentData()
        if not period_id:
            QMessageBox.warning(self, "No Period", "Please select a period to delete.")
            return

        period_label = self.period_combo.currentText()
        reply = QMessageBox.warning(
            self,
            "Delete Period",
            f"Are you sure you want to delete the period '{period_label}'?\n\n"
            "This will also delete ALL payroll data for this period.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            try:
                db = get_db()
                with db.get_session() as session:
                    payroll_repo = MonthlyPayrollRepository(session)
                    period_repo = PayrollPeriodRepository(session)

                    # Delete all payroll records first
                    payroll_repo.delete_for_period(period_id)

                    # Delete the period
                    period_repo.delete_by_id(period_id)
                    session.commit()

                QMessageBox.information(self, "Deleted", f"Period '{period_label}' has been deleted.")
                self._load_periods()

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete period:\n{str(e)}")

    def _load_attendance_data(self, period_id: int):
        """Load attendance data for the selected period."""
        self._is_loading = True
        self.table.setRowCount(0)

        db = get_db()
        with db.get_session() as session:
            period_repo = PayrollPeriodRepository(session)
            payroll_repo = MonthlyPayrollRepository(session)
            leave_repo = LeaveBalanceRepository(session)

            period = period_repo.get_by_id(period_id)
            if not period:
                self._is_loading = False
                return

            payrolls = payroll_repo.get_all_for_period_and_company(
                period_id, self.selected_company_id
            )

            if not payrolls:
                self.lbl_period_status.setText("Status: No attendance data")
                self.lbl_employee_count.setText("Employees: 0")
                self._is_loading = False
                return

            self.lbl_period_status.setText(f"Status: Active ({period.working_days} working days)")
            self.lbl_employee_count.setText(f"Employees: {len(payrolls)}")

            self.table.setRowCount(len(payrolls))

            fy = get_financial_year(period.year, period.month)

            for row, payroll in enumerate(payrolls):
                emp = payroll.employee

                # Get leave balances
                balance = leave_repo.get_or_create_for_employee_fy(emp.id, fy)
                pl_bal = float(balance.pl_balance)
                sl_bal = float(balance.sl_balance)
                cl_bal = float(balance.cl_balance)

                # ID (hidden)
                self._set_readonly_item(row, self.COL_ID, str(payroll.id))

                # Employee info
                self._set_readonly_item(row, self.COL_EMP_CODE, emp.employee_code or "")
                self._set_readonly_item(row, self.COL_NAME, emp.full_name)

                # Attendance summary
                self._set_readonly_item(row, self.COL_TOTAL_DAYS, str(period.working_days))
                self._set_readonly_item(row, self.COL_PAID, str(payroll.paid_days))
                self._set_readonly_item(row, self.COL_PRESENT, str(payroll.present_days))

                # Editable attendance fields
                self._set_editable_item(row, self.COL_PL, f"{float(payroll.privilege_leave or 0):.1f}")
                self._set_editable_item(row, self.COL_SL, f"{float(payroll.sick_leave or 0):.1f}")
                self._set_editable_item(row, self.COL_CL, f"{float(payroll.casual_leave or 0):.1f}")
                self._set_editable_item(row, self.COL_ABSENT, f"{float(payroll.absent_days or 0):.1f}")
                self._set_editable_item(row, self.COL_LATE, f"{float(payroll.late_marks or 0):.1f}")

                # Leave balances (readonly)
                self._set_readonly_item(row, self.COL_BAL_PL, f"{pl_bal:.1f}")
                self._set_readonly_item(row, self.COL_BAL_SL, f"{sl_bal:.1f}")
                self._set_readonly_item(row, self.COL_BAL_CL, f"{cl_bal:.1f}")

                # Apply balance highlighting
                self._apply_leave_highlight(row, self.COL_BAL_PL, pl_bal)
                self._apply_leave_highlight(row, self.COL_BAL_SL, sl_bal)
                self._apply_leave_highlight(row, self.COL_BAL_CL, cl_bal)

            session.commit()

        self._is_loading = False

    def _set_readonly_item(self, row: int, col: int, text: str):
        """Set a readonly table cell."""
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        if col in [self.COL_EMP_CODE, self.COL_NAME]:
            item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        else:
            item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, col, item)

    def _set_editable_item(self, row: int, col: int, text: str):
        """Set an editable table cell."""
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, col, item)

    def _apply_leave_highlight(self, row: int, col: int, balance: float):
        """Apply color coding to leave balance cells."""
        item = self.table.item(row, col)
        if item:
            if balance < 0:
                item.setBackground(QBrush(QColor("#FFCDD2")))
                item.setForeground(QBrush(QColor("#C62828")))
            else:
                item.setBackground(QBrush(QColor("#C8E6C9")))
                item.setForeground(QBrush(QColor("#2E7D32")))

    def _on_cell_changed(self, row: int, col: int):
        """Handle cell value changes."""
        if self._is_loading:
            return

        # Only track editable columns
        if col not in [self.COL_PL, self.COL_SL, self.COL_CL, self.COL_ABSENT, self.COL_LATE]:
            return

        payroll_id = int(self.table.item(row, self.COL_ID).text())
        item = self.table.item(row, col)
        if not item:
            return

        text = item.text().strip()
        try:
            value = float(text) if text else 0.0
        except ValueError:
            value = 0.0

        # Apply leave overflow logic for PL, SL, CL columns
        if col in [self.COL_PL, self.COL_SL, self.COL_CL] and value > 7:
            overflow = value - 7
            value = 7.0  # Cap the original leave

            # Update the current cell to show capped value
            self._is_loading = True
            item.setText(f"{value:.1f}")
            self._is_loading = False

            # Get current values for other leaves
            pl_val = float(self.table.item(row, self.COL_PL).text() or 0) if col != self.COL_PL else value
            sl_val = float(self.table.item(row, self.COL_SL).text() or 0) if col != self.COL_SL else value
            cl_val = float(self.table.item(row, self.COL_CL).text() or 0) if col != self.COL_CL else value
            absent_val = float(self.table.item(row, self.COL_ABSENT).text() or 0)

            # Determine order of redistribution (skip the current leave type)
            redistrib_order = []
            if col == self.COL_PL:
                redistrib_order = [(self.COL_SL, sl_val), (self.COL_CL, cl_val)]
            elif col == self.COL_SL:
                redistrib_order = [(self.COL_PL, pl_val), (self.COL_CL, cl_val)]
            else:  # COL_CL
                redistrib_order = [(self.COL_PL, pl_val), (self.COL_SL, sl_val)]

            # Try to redistribute overflow to other leaves (up to 7 each)
            self._is_loading = True
            for leave_col, current_leave_val in redistrib_order:
                if overflow <= 0:
                    break
                room = 7 - current_leave_val
                if room > 0:
                    add_amount = min(room, overflow)
                    new_leave_val = current_leave_val + add_amount
                    overflow -= add_amount
                    self.table.item(row, leave_col).setText(f"{new_leave_val:.1f}")

                    # Store in pending changes
                    leave_field_map = {
                        self.COL_PL: "privilege_leave",
                        self.COL_SL: "sick_leave",
                        self.COL_CL: "casual_leave",
                    }
                    if payroll_id not in self._pending_changes:
                        self._pending_changes[payroll_id] = {}
                    self._pending_changes[payroll_id][leave_field_map[leave_col]] = new_leave_val

            # Any remaining overflow goes to absent (capped at total_days - all_leaves)
            if overflow > 0:
                # Get final leave values after redistribution
                final_pl = float(self.table.item(row, self.COL_PL).text() or 0)
                final_sl = float(self.table.item(row, self.COL_SL).text() or 0)
                final_cl = float(self.table.item(row, self.COL_CL).text() or 0)
                total_days = float(self.table.item(row, self.COL_TOTAL_DAYS).text() or 0)
                absent_max = max(0.0, total_days - final_pl - final_sl - final_cl)
                absent_val = min(absent_val + overflow, absent_max)
                self.table.item(row, self.COL_ABSENT).setText(f"{absent_val:.1f}")
                if payroll_id not in self._pending_changes:
                    self._pending_changes[payroll_id] = {}
                self._pending_changes[payroll_id]["absent_days"] = absent_val

            self._is_loading = False

        # For direct absent edits, clamp to total_days - pl - sl - cl
        if col == self.COL_ABSENT:
            pl = float(self.table.item(row, self.COL_PL).text() or 0)
            sl = float(self.table.item(row, self.COL_SL).text() or 0)
            cl = float(self.table.item(row, self.COL_CL).text() or 0)
            total_days = float(self.table.item(row, self.COL_TOTAL_DAYS).text() or 0)
            absent_max = max(0.0, total_days - pl - sl - cl)
            if value > absent_max:
                value = absent_max
                self._is_loading = True
                item.setText(f"{value:.1f}")
                self._is_loading = False

        # Map column to field name
        field_map = {
            self.COL_PL: "privilege_leave",
            self.COL_SL: "sick_leave",
            self.COL_CL: "casual_leave",
            self.COL_ABSENT: "absent_days",
            self.COL_LATE: "late_marks",
        }

        field = field_map.get(col)
        if field:
            if payroll_id not in self._pending_changes:
                self._pending_changes[payroll_id] = {}
            self._pending_changes[payroll_id][field] = value

            self.lbl_save_status.setText("⏳ Saving...")
            self._auto_save_timer.start(500)

    def _save_pending_changes(self):
        """Save all pending attendance changes to the database."""
        if not self._pending_changes:
            return

        period_id = self.period_combo.currentData()

        try:
            db = get_db()
            ui_updates = {}
            _bal_updates = {}

            with db.get_session() as session:
                payroll_repo = MonthlyPayrollRepository(session)
                service = PayrollService(session)

                for payroll_id, changes in self._pending_changes.items():
                    payroll = payroll_repo.get_by_id(payroll_id)
                    if not payroll:
                        continue

                    for field, value in changes.items():
                        setattr(payroll, field, Decimal(str(value)))

                    # Recalculate payroll
                    service.recalculate_payroll(payroll_id)
                    payroll = payroll_repo.get_by_id(payroll_id)

                    # Find the row for this payroll
                    for row in range(self.table.rowCount()):
                        row_id = int(self.table.item(row, self.COL_ID).text())
                        if row_id == payroll_id:
                            ui_updates[row] = {
                                "total_days": payroll.payroll_period.working_days,
                                "paid_days": payroll.paid_days,
                                "present_days": payroll.present_days,
                                "privilege_leave": float(payroll.privilege_leave),
                                "sick_leave": float(payroll.sick_leave),
                                "casual_leave": float(payroll.casual_leave),
                                "absent_days": float(payroll.absent_days),
                                "late_marks": float(payroll.late_marks),
                                "employee_id": payroll.employee_id,
                            }
                            if not hasattr(self, '_period_for_leave_update'):
                                self._period_for_leave_update = payroll.payroll_period

                # Update leave balances
                if hasattr(self, '_period_for_leave_update') and self._period_for_leave_update:
                    _upd_period = self._period_for_leave_update
                    service.update_leave_balances(
                        _upd_period,
                        company_id=self.selected_company_id,
                    )
                    fy = get_financial_year(_upd_period.year, _upd_period.month)
                    leave_repo = LeaveBalanceRepository(session)
                    for row, data in ui_updates.items():
                        bal = leave_repo.get_for_employee_fy(data["employee_id"], fy)
                        if bal:
                            _bal_updates[row] = {
                                "pl_bal": float(bal.pl_balance),
                                "sl_bal": float(bal.sl_balance),
                                "cl_bal": float(bal.cl_balance),
                            }
                    delattr(self, '_period_for_leave_update')

                session.commit()

            # Update UI
            self._is_loading = True
            for row, data in ui_updates.items():
                self._update_cell(row, self.COL_PAID, str(data["paid_days"]))
                self._update_cell(row, self.COL_PRESENT, str(data["present_days"]))
                self._update_cell(row, self.COL_PL, f"{data['privilege_leave']:.1f}")
                self._update_cell(row, self.COL_SL, f"{data['sick_leave']:.1f}")
                self._update_cell(row, self.COL_CL, f"{data['casual_leave']:.1f}")
                self._update_cell(row, self.COL_ABSENT, f"{data['absent_days']:.1f}")
                self._update_cell(row, self.COL_LATE, f"{data['late_marks']:.1f}")

                for bal_row, bal_data in _bal_updates.items():
                    if bal_row == row:
                        self._update_cell(row, self.COL_BAL_PL, f"{bal_data['pl_bal']:.1f}")
                        self._update_cell(row, self.COL_BAL_SL, f"{bal_data['sl_bal']:.1f}")
                        self._update_cell(row, self.COL_BAL_CL, f"{bal_data['cl_bal']:.1f}")
                        self._apply_leave_highlight(row, self.COL_BAL_PL, bal_data['pl_bal'])
                        self._apply_leave_highlight(row, self.COL_BAL_SL, bal_data['sl_bal'])
                        self._apply_leave_highlight(row, self.COL_BAL_CL, bal_data['cl_bal'])
            self._is_loading = False

            self._pending_changes.clear()
            self.lbl_save_status.setText("✅ Saved")
            QTimer.singleShot(2000, lambda: self.lbl_save_status.setText(""))

        except Exception as e:
            self.lbl_save_status.setText("❌ Error saving")
            QMessageBox.critical(self, "Error", f"Failed to save changes:\n{str(e)}")

    def _update_cell(self, row: int, col: int, text: str):
        """Update a cell's text without triggering signals."""
        item = self.table.item(row, col)
        if item:
            item.setText(text)

    def _update_buttons(self, period_id: int):
        """Update button states based on period status."""
        db = get_db()
        with db.get_session() as session:
            payroll_repo = MonthlyPayrollRepository(session)
            has_payroll = payroll_repo.exists_for_period_and_company(period_id, self.selected_company_id)
            self.btn_generate.setEnabled(not has_payroll)

    def _clear_status(self):
        """Clear status labels."""
        self.lbl_period_status.setText("Status: -")
        self.lbl_employee_count.setText("Employees: 0")
        self.btn_generate.setEnabled(False)

    def _on_new_period(self):
        """Open dialog to create new period."""
        dialog = PeriodDialog(
            self,
            selected_company_id=self.selected_company_id,
            selected_company_name=self.selected_company_name,
        )
        if dialog.exec():
            self._load_periods()

    def _on_generate_attendance(self):
        """Generate attendance records for all active employees."""
        period_id = self.period_combo.currentData()
        if not period_id:
            return

        reply = QMessageBox.question(
            self,
            "Generate Attendance",
            f"Generate attendance records for active employees in {self.selected_company_name}?\n\n"
            "This will create empty attendance records for the selected period.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )

        if reply == QMessageBox.Yes:
            try:
                db = get_db()
                with db.get_session() as session:
                    period_repo = PayrollPeriodRepository(session)
                    period = period_repo.get_by_id(period_id)

                    service = PayrollService(session)
                    count = service.generate_payroll_for_period(
                        period,
                        copy_from_previous=False,
                        company_id=self.selected_company_id,
                    )

                QMessageBox.information(self, "Success", f"Generated attendance for {count} employees.")
                self._load_attendance_data(period_id)
                self._update_buttons(period_id)

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to generate attendance:\n{str(e)}")

    def _refresh_all(self):
        """Refresh periods and data."""
        current_period = self.period_combo.currentData()
        self._load_periods()
        if current_period:
            for i in range(self.period_combo.count()):
                if self.period_combo.itemData(i) == current_period:
                    self.period_combo.setCurrentIndex(i)
                    break

    def _setup_zoom_shortcuts(self):
        """Setup keyboard shortcuts for zooming."""
        zoom_in = QShortcut(QKeySequence("Ctrl++"), self)
        zoom_in.activated.connect(self._zoom_in)
        zoom_in2 = QShortcut(QKeySequence("Ctrl+="), self)
        zoom_in2.activated.connect(self._zoom_in)
        zoom_out = QShortcut(QKeySequence("Ctrl+-"), self)
        zoom_out.activated.connect(self._zoom_out)
        zoom_reset = QShortcut(QKeySequence("Ctrl+0"), self)
        zoom_reset.activated.connect(self._zoom_reset)

    def _zoom_in(self):
        """Increase table font size."""
        font = self.table.font()
        if font.pointSize() < 20:
            font.setPointSize(font.pointSize() + 1)
            self.table.setFont(font)
            self.table.horizontalHeader().setFont(font)
            self.table.verticalHeader().setDefaultSectionSize(font.pointSize() * 2 + 10)

    def _zoom_out(self):
        """Decrease table font size."""
        font = self.table.font()
        if font.pointSize() > 8:
            font.setPointSize(font.pointSize() - 1)
            self.table.setFont(font)
            self.table.horizontalHeader().setFont(font)
            self.table.verticalHeader().setDefaultSectionSize(font.pointSize() * 2 + 10)

    def _zoom_reset(self):
        """Reset table font size."""
        font = self.table.font()
        font.setPointSize(11)
        self.table.setFont(font)
        self.table.horizontalHeader().setFont(font)
        self.table.verticalHeader().setDefaultSectionSize(32)

    def _on_current_cell_changed(self, current_row: int, current_col: int, prev_row: int, prev_col: int):
        """Handle cell selection change to highlight entire row with selected column darkened."""
        # Clear previous row highlighting
        if self._highlighted_row >= 0 and self._highlighted_row < self.table.rowCount():
            for col in range(self.table.columnCount()):
                item = self.table.item(self._highlighted_row, col)
                if item:
                    # Reset to default or balance color
                    if col in [self.COL_BAL_PL, self.COL_BAL_SL, self.COL_BAL_CL]:
                        try:
                            balance = float(item.text())
                            self._apply_leave_highlight(self._highlighted_row, col, balance)
                        except ValueError:
                            item.setBackground(QBrush())
                    else:
                        item.setBackground(QBrush())

        # Highlight new row
        if current_row >= 0 and current_row < self.table.rowCount():
            self._highlighted_row = current_row
            row_color = QColor("#3f4f6f")  # Base row highlight color (darker blue)
            selected_color = QColor("#1a73e8")  # Selected cell color (bright blue)

            for col in range(self.table.columnCount()):
                item = self.table.item(current_row, col)
                if item:
                    if col == current_col:
                        # Darken the selected cell
                        item.setBackground(QBrush(selected_color))
                    else:
                        # Highlight rest of row
                        item.setBackground(QBrush(row_color))

    def eventFilter(self, obj, event):
        """Handle keyboard events for table navigation."""
        if obj == self.table and event.type() == QEvent.KeyPress:
            key = event.key()
            modifiers = event.modifiers()
            current = self.table.currentItem()

            if not current:
                return super().eventFilter(obj, event)

            row, col = current.row(), current.column()
            editable_cols = [self.COL_PL, self.COL_SL, self.COL_CL, self.COL_ABSENT, self.COL_LATE]

            # Arrow Up
            if key == Qt.Key_Up and not modifiers:
                if row > 0:
                    self.table.setCurrentCell(row - 1, col)
                return True

            # Arrow Down
            if key == Qt.Key_Down and not modifiers:
                if row < self.table.rowCount() - 1:
                    self.table.setCurrentCell(row + 1, col)
                return True

            # Arrow Left
            if key == Qt.Key_Left and not modifiers:
                if col > 1:  # Skip hidden ID column
                    self.table.setCurrentCell(row, col - 1)
                return True

            # Arrow Right
            if key == Qt.Key_Right and not modifiers:
                if col < self.table.columnCount() - 1:
                    self.table.setCurrentCell(row, col + 1)
                return True

            # Number key pressed in editable column - start editing
            if key >= Qt.Key_0 and key <= Qt.Key_9:
                if col in editable_cols:
                    item = self.table.item(row, col)
                    if item and item.flags() & Qt.ItemIsEditable:
                        self.table.editItem(item)
                        # Insert the pressed number
                        editor = self.table.findChild(QLineEdit)
                        if editor:
                            editor.setText(chr(key))
                            editor.setCursorPosition(1)
                        return True

            # Enter: move down
            if key == Qt.Key_Return and not modifiers:
                if row < self.table.rowCount() - 1:
                    self.table.setCurrentCell(row + 1, col)
                return True

            # Shift+Enter: move up
            if key == Qt.Key_Return and modifiers == Qt.ShiftModifier:
                if row > 0:
                    self.table.setCurrentCell(row - 1, col)
                return True

            # Tab: move to next editable column
            if key == Qt.Key_Tab and not modifiers:
                try:
                    idx = editable_cols.index(col)
                    if idx < len(editable_cols) - 1:
                        self.table.setCurrentCell(row, editable_cols[idx + 1])
                    elif row < self.table.rowCount() - 1:
                        self.table.setCurrentCell(row + 1, editable_cols[0])
                except ValueError:
                    self.table.setCurrentCell(row, editable_cols[0])
                return True

            # Shift+Tab: move to previous editable column
            if key == Qt.Key_Tab and modifiers == Qt.ShiftModifier:
                try:
                    idx = editable_cols.index(col)
                    if idx > 0:
                        self.table.setCurrentCell(row, editable_cols[idx - 1])
                    elif row > 0:
                        self.table.setCurrentCell(row - 1, editable_cols[-1])
                except ValueError:
                    self.table.setCurrentCell(row, editable_cols[-1])
                return True

        return super().eventFilter(obj, event)

    def wheelEvent(self, event):
        """Handle mouse wheel for zooming with Ctrl key."""
        if event.modifiers() == Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                self._zoom_in()
            else:
                self._zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)
