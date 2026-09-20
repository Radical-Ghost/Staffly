"""Payroll management widget - Salary calculations view with export."""

import csv
from decimal import Decimal
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLabel,
    QHeaderView,
    QMessageBox,
    QAbstractItemView,
    QMenu,
    QComboBox,
    QLineEdit,
    QStyledItemDelegate,
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QFileDialog,
    QCheckBox,
)
from PySide6.QtCore import Qt, QTimer, QEvent
from PySide6.QtGui import QShortcut, QKeySequence, QColor, QBrush, QDoubleValidator

from staffly.database import get_db
from staffly.database.repositories import (
    EmployeeRepository,
    PayrollPeriodRepository,
    MonthlyPayrollRepository,
    SalaryStructureRepository,
)
from staffly.services import PayrollService
from staffly.services.payroll_service import get_financial_year


class CurrencyEditDelegate(QStyledItemDelegate):
    """Delegate for editing currency values in cells."""

    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        validator = QDoubleValidator(0, 999999, 2, editor)
        editor.setValidator(validator)
        editor.setFrame(False)
        editor.setAlignment(Qt.AlignCenter)
        return editor

    def setEditorData(self, editor, index):
        text = index.model().data(index, Qt.DisplayRole) or "0"
        text = text.replace("₹", "").replace(",", "").strip()
        editor.setText(text)
        editor.setCursorPosition(len(text))

    def setModelData(self, editor, model, index):
        text = editor.text().strip()
        if not text:
            text = "0"
        model.setData(index, text, Qt.DisplayRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


class PayrollWidget(QWidget):
    """
    Payroll management widget showing salary calculations.

    Features:
    - View salary breakdown for each employee
    - Edit only Loan and TDS
    - Export payroll to CSV/Excel
    - Shows PF/ESIC applicability
    """

    # Column configuration: (name, width, editable)
    COLUMNS = [
        ("ID", 0, False),
        ("Emp Code", 120, False),
        ("Name", 160, False),
        ("Paid Days", 100, False),
        ("PF", 80, False),       # Applicability Y/N
        ("ESIC", 80, False),     # Applicability Y/N
        ("Basic", 95, False),
        ("HRA", 85, False),
        ("CCA", 85, False),
        ("Other+", 85, False),
        ("Bonus", 85, False),
        ("PF (Emp)", 90, False),  # Employer contribution
        ("Arrears", 95, False),    # Arrears (shown via checkbox)
        ("Gross", 100, False),
        ("PF (Ded)", 90, False),  # Employee deduction
        ("ESIC (Ded)", 110, False),
        ("PT", 75, False),
        ("Loan", 85, True),       # Editable
        ("TDS", 85, True),        # Editable
        ("Net Salary", 115, False),
    ]

    # Column indices
    COL_ID = 0
    COL_EMP_CODE = 1
    COL_NAME = 2
    COL_PAID_DAYS = 3
    COL_PF_APPLICABLE = 4
    COL_ESIC_APPLICABLE = 5
    COL_BASIC = 6
    COL_HRA = 7
    COL_CCA = 8
    COL_OTHER_EARN = 9
    COL_BONUS = 10
    COL_PF_EMPLOYER = 11
    COL_ARREARS = 12
    COL_GROSS = 13
    COL_PF_EMPLOYEE = 14
    COL_ESIC_EMPLOYEE = 15
    COL_PT = 16
    COL_LOAN = 17
    COL_TDS = 18
    COL_NET = 19

    def __init__(self, selected_company_id: int, selected_company_name: str):
        super().__init__()
        self.selected_company_id = selected_company_id
        self.selected_company_name = selected_company_name
        self._table_font_size = 12
        self._pending_changes = {}
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._save_pending_changes)
        self._is_loading = False
        self._setup_ui()
        self._setup_zoom_shortcuts()
        self._load_periods()

    def _setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        # Header card
        header_card = QFrame()
        header_card.setObjectName("card")
        header_layout = QVBoxLayout(header_card)
        header_layout.setContentsMargins(20, 16, 20, 16)
        header_layout.setSpacing(12)

        # Title row
        title_row = QHBoxLayout()
        title = QLabel("Payroll Management")
        title.setObjectName("cardHeader")
        title_row.addWidget(title)
        title_row.addStretch()

        company_badge = QLabel(self.selected_company_name)
        company_badge.setObjectName("badge")
        title_row.addWidget(company_badge)

        header_layout.addLayout(title_row)

        # Controls row
        controls_row = QHBoxLayout()
        controls_row.setSpacing(12)

        period_label = QLabel("Period:")
        controls_row.addWidget(period_label)

        self.period_combo = QComboBox()
        self.period_combo.setMinimumWidth(200)
        self.period_combo.currentIndexChanged.connect(self._on_period_changed)
        controls_row.addWidget(self.period_combo)

        # Arrears checkbox
        self.chk_arrears = QCheckBox("Show Arrears")
        self.chk_arrears.setChecked(False)
        self.chk_arrears.toggled.connect(self._on_arrears_toggled)
        controls_row.addWidget(self.chk_arrears)

        controls_row.addStretch()

        # Recalculate button
        self.btn_recalculate = QPushButton("Recalculate")
        self.btn_recalculate.setObjectName("secondaryButton")
        self.btn_recalculate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_recalculate.clicked.connect(self._on_recalculate_all)
        self.btn_recalculate.setEnabled(False)
        controls_row.addWidget(self.btn_recalculate)

        # Edit Menu button
        self.btn_edit_menu = QPushButton("Edit Menu")
        self.btn_edit_menu.setObjectName("secondaryButton")
        self.btn_edit_menu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_edit_menu.clicked.connect(self._show_edit_menu)
        self.btn_edit_menu.setEnabled(False)
        controls_row.addWidget(self.btn_edit_menu)

        # Export button
        self.btn_export = QPushButton("📥 Export")
        self.btn_export.setObjectName("primaryButton")
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export.clicked.connect(self._on_export_payroll)
        self.btn_export.setEnabled(False)
        controls_row.addWidget(self.btn_export)

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

        self.lbl_total_salary = QLabel("Total Net: ₹0")
        self.lbl_total_salary.setObjectName("grossInput")
        info_row.addWidget(self.lbl_total_salary)

        self.lbl_save_status = QLabel("")
        self.lbl_save_status.setObjectName("statusLabel")
        info_row.addWidget(self.lbl_save_status)

        info_row.addStretch()

        header_layout.addLayout(info_row)
        layout.addWidget(header_card)

        # Legend
        legend_card = QFrame()
        legend_card.setObjectName("card")
        legend_layout = QHBoxLayout(legend_card)
        legend_layout.setContentsMargins(16, 8, 16, 8)

        legend_layout.addWidget(QLabel("Editable columns: Loan, TDS"))
        legend_layout.addStretch()
        legend_layout.addWidget(QLabel("PF/ESIC shows applicability (Y/N)"))

        layout.addWidget(legend_card)

        # Placeholder for missing attendance
        self.placeholder_card = QFrame()
        self.placeholder_card.setObjectName("card")
        placeholder_layout = QVBoxLayout(self.placeholder_card)
        placeholder_layout.setContentsMargins(40, 80, 40, 80)
        placeholder_layout.setAlignment(Qt.AlignCenter)

        placeholder_icon = QLabel("📅")
        placeholder_icon.setAlignment(Qt.AlignCenter)
        placeholder_icon.setStyleSheet("font-size: 48px;")
        placeholder_layout.addWidget(placeholder_icon)

        placeholder_text = QLabel("Attendance data not found for this period.")
        placeholder_text.setAlignment(Qt.AlignCenter)
        placeholder_text.setObjectName("cardHeader")
        placeholder_layout.addWidget(placeholder_text)

        placeholder_hint = QLabel("Please fill attendance in the Attendance tab first,\nthen come back here to view the payroll.")
        placeholder_hint.setAlignment(Qt.AlignCenter)
        placeholder_layout.addWidget(placeholder_hint)

        self.placeholder_card.setVisible(False)
        layout.addWidget(self.placeholder_card)

        # Payroll table
        self.table_card = QFrame()
        self.table_card.setObjectName("card")
        table_layout = QVBoxLayout(self.table_card)
        table_layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setObjectName("payrollTable")
        self.table.setColumnCount(len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels([c[0] for c in self.COLUMNS])

        # Table settings
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(
            QAbstractItemView.DoubleClicked |
            QAbstractItemView.EditKeyPressed
        )

        # Set column widths
        for i, (_, width, _) in enumerate(self.COLUMNS):
            self.table.setColumnWidth(i, width)

        # Hide ID column and Arrears (hidden by default, shown via checkbox)
        self.table.setColumnHidden(self.COL_ID, True)
        self.table.setColumnHidden(self.COL_ARREARS, True)

        # Stretch name column
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(self.COL_NAME, QHeaderView.Stretch)

        # Set currency delegates for editable columns
        currency_delegate = CurrencyEditDelegate(parent=self.table)
        self.table.setItemDelegateForColumn(self.COL_LOAN, currency_delegate)
        self.table.setItemDelegateForColumn(self.COL_TDS, currency_delegate)

        # Connect signals
        self.table.cellChanged.connect(self._on_cell_changed)
        self.table.currentCellChanged.connect(self._on_current_cell_changed)
        self.table.installEventFilter(self)

        # Track currently highlighted row
        self._highlighted_row = -1

        self._apply_table_zoom()

        table_layout.addWidget(self.table)
        layout.addWidget(self.table_card, 1)

    def _on_arrears_toggled(self, checked: bool):
        """Show or hide the Arrears column based on checkbox state."""
        self.table.setColumnHidden(self.COL_ARREARS, not checked)

    def _load_periods(self):
        """Load payroll periods into combo box."""
        self.period_combo.clear()
        self.period_combo.addItem("-- Select Period --", None)

        db = get_db()
        with db.get_session() as session:
            repo = PayrollPeriodRepository(session)
            periods = repo.get_all_ordered()

            for period in periods:
                self.period_combo.addItem(f"📝 {period.period_label}", period.id)

    def _on_period_changed(self, index: int):
        """Handle period selection change."""
        period_id = self.period_combo.currentData()
        if period_id:
            self._load_payroll_data(period_id)
            self._update_buttons(period_id)
        else:
            self.table.setRowCount(0)
            self._clear_status()
            self.placeholder_card.setVisible(False)
            self.table_card.setVisible(True)

    def _load_payroll_data(self, period_id: int):
        """Load payroll data for selected period."""
        self._is_loading = True
        self.table.setRowCount(0)

        db = get_db()
        with db.get_session() as session:
            period_repo = PayrollPeriodRepository(session)
            payroll_repo = MonthlyPayrollRepository(session)
            salary_repo = SalaryStructureRepository(session)
            service = PayrollService(session)

            period = period_repo.get_by_id(period_id)
            payrolls = payroll_repo.get_all_for_period_and_company(period_id, self.selected_company_id)

            # Check if any payroll data exists
            if not payrolls:
                self.placeholder_card.setVisible(True)
                self.table_card.setVisible(False)
                self.lbl_period_status.setText("Status: No attendance data")
                self.lbl_employee_count.setText("Employees: 0")
                self.lbl_total_salary.setText("Total Net: ₹0")
                self._is_loading = False
                return

            self.placeholder_card.setVisible(False)
            self.table_card.setVisible(True)

            self.lbl_period_status.setText(f"Status: Active ({period.working_days} working days)")

            total_net = 0
            for payroll in payrolls:
                row = self.table.rowCount()
                self.table.insertRow(row)

                emp = payroll.employee

                # Get salary structure for PF/ESIC applicability
                salary_struct = salary_repo.get_active_for_employee(emp.id, period.start_date)
                pf_applicable = "Y" if (salary_struct and salary_struct.pf_applicable) else "N"

                # Evaluate ESIC with the 6-month buffer rule
                struct_esi = salary_struct.esi_applicable if salary_struct else False
                actual_esi = service._check_esic_buffer_rule(emp, period, salary_struct)

                if actual_esi and not struct_esi:
                    esic_applicable = "Y (Buffer)"
                else:
                    esic_applicable = "Y" if actual_esi else "N"

                # ID (hidden)
                self._set_readonly_item(row, self.COL_ID, str(payroll.id))

                # Employee info
                self._set_readonly_item(row, self.COL_EMP_CODE, emp.employee_code or "")
                self._set_readonly_item(row, self.COL_NAME, emp.full_name, align_left=True)

                # Paid days
                self._set_readonly_item(row, self.COL_PAID_DAYS, str(payroll.paid_days))

                # PF/ESIC applicability
                self._set_readonly_item(row, self.COL_PF_APPLICABLE, pf_applicable)
                self._set_readonly_item(row, self.COL_ESIC_APPLICABLE, esic_applicable)

                # Earnings
                self._set_readonly_item(row, self.COL_BASIC, f"₹{payroll.basic_salary:,.2f}")
                self._set_readonly_item(row, self.COL_HRA, f"₹{payroll.hra:,.2f}")
                self._set_readonly_item(row, self.COL_CCA, f"₹{payroll.cca:,.2f}")
                self._set_readonly_item(row, self.COL_OTHER_EARN, f"₹{payroll.other_allowance:,.2f}")
                self._set_readonly_item(row, self.COL_BONUS, f"₹{payroll.bonus:,.2f}")

                # PF Employer contribution
                pf_employer = float(getattr(payroll, 'pf_employer', 0) or 0)
                self._set_readonly_item(row, self.COL_PF_EMPLOYER, f"₹{pf_employer:,.2f}")

                # Arrears
                arrears = float(getattr(payroll, 'arrears', 0) or 0)
                self._set_readonly_item(row, self.COL_ARREARS, f"₹{arrears:,.2f}")

                # Gross (includes arrears if present)
                gross_total = float(payroll.gross_earnings) + arrears
                self._set_readonly_item(row, self.COL_GROSS, f"₹{gross_total:,.2f}")

                # Deductions
                self._set_readonly_item(row, self.COL_PF_EMPLOYEE, f"₹{payroll.pf_employee:,.2f}")
                self._set_readonly_item(row, self.COL_ESIC_EMPLOYEE, f"₹{payroll.esi_employee:,.2f}")
                self._set_readonly_item(row, self.COL_PT, f"₹{payroll.professional_tax:,.2f}")

                # Editable fields
                self._set_editable_item(row, self.COL_LOAN, f"₹{payroll.loan_deduction:,.2f}")
                self._set_editable_item(row, self.COL_TDS, f"₹{payroll.tds:,.2f}")

                # Net salary
                net_item = QTableWidgetItem(f"₹{payroll.net_salary:,.2f}")
                net_item.setFlags(net_item.flags() & ~Qt.ItemIsEditable)
                net_item.setBackground(QBrush(QColor("#FFF9C4")))
                net_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, self.COL_NET, net_item)

                total_net += float(payroll.net_salary)

            self.lbl_employee_count.setText(f"Employees: {len(payrolls)}")
            self.lbl_total_salary.setText(f"Total Net: ₹{total_net:,.2f}")

        self._is_loading = False

    def _set_readonly_item(self, row: int, col: int, text: str, align_left: bool = False):
        """Set a read-only cell."""
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        if align_left:
            item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        elif "₹" in text:
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        else:
            item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, col, item)

    def _set_editable_item(self, row: int, col: int, text: str):
        """Set an editable cell with highlight."""
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        item.setBackground(QBrush(QColor("#E8F5E9")))  # Light green for editable
        self.table.setItem(row, col, item)

    def _on_cell_changed(self, row: int, col: int):
        """Handle cell value change."""
        if self._is_loading:
            return

        # Only handle editable columns
        if col not in [self.COL_LOAN, self.COL_TDS]:
            return

        id_item = self.table.item(row, self.COL_ID)
        if not id_item:
            return

        payroll_id = int(id_item.text())
        item = self.table.item(row, col)
        if not item:
            return

        # Parse value
        text = item.text().replace("₹", "").replace(",", "").strip()
        if text == "":
            text = "0"
        try:
            value = float(text)
        except ValueError:
            return

        # Map column to field
        field_map = {
            self.COL_LOAN: "loan_deduction",
            self.COL_TDS: "tds",
        }

        field = field_map.get(col)
        if field:
            if payroll_id not in self._pending_changes:
                self._pending_changes[payroll_id] = {"row": row}
            self._pending_changes[payroll_id][field] = value

            self.lbl_save_status.setText("⏳ Pending...")
            self._save_timer.stop()
            self._save_timer.start(500)

    def _save_pending_changes(self):
        """Save pending changes to database."""
        if not self._pending_changes:
            return

        try:
            db = get_db()
            ui_updates = {}

            with db.get_session() as session:
                payroll_repo = MonthlyPayrollRepository(session)
                service = PayrollService(session)

                for payroll_id, change_data in self._pending_changes.items():
                    row = change_data.get("row")
                    payroll = payroll_repo.get_by_id(payroll_id)
                    if not payroll:
                        continue

                    for field, value in change_data.items():
                        if field == "row":
                            continue
                        value = max(0.0, float(value))
                        setattr(payroll, field, Decimal(str(value)))

                    service.recalculate_payroll(payroll_id)

                    if row is not None:
                        ui_updates[row] = {
                            "loan_deduction": float(payroll.loan_deduction),
                            "tds": float(payroll.tds),
                            "net_salary": float(payroll.net_salary),
                        }

                session.commit()

            # Update UI
            self._is_loading = True
            for row, data in ui_updates.items():
                self._update_cell(row, self.COL_LOAN, f"₹{data['loan_deduction']:,.2f}")
                self._update_cell(row, self.COL_TDS, f"₹{data['tds']:,.2f}")
                self._update_cell(row, self.COL_NET, f"₹{data['net_salary']:,.2f}")
            self._is_loading = False

            self._pending_changes.clear()
            self.lbl_save_status.setText("✅ Saved")
            QTimer.singleShot(2000, lambda: self.lbl_save_status.setText(""))
            self._update_totals()

        except Exception as e:
            self.lbl_save_status.setText("❌ Error saving")
            QMessageBox.critical(self, "Error", f"Failed to save changes:\n{str(e)}")

    def _update_cell(self, row: int, col: int, text: str):
        """Update a cell's text."""
        item = self.table.item(row, col)
        if item:
            item.setText(text)

    def _update_totals(self):
        """Update total salary display."""
        total_net = 0
        for row in range(self.table.rowCount()):
            net_item = self.table.item(row, self.COL_NET)
            if net_item:
                text = net_item.text().replace("₹", "").replace(",", "")
                try:
                    total_net += float(text)
                except ValueError:
                    pass
        self.lbl_total_salary.setText(f"Total Net: ₹{total_net:,.2f}")

    def _update_buttons(self, period_id: int):
        """Update button states."""
        db = get_db()
        with db.get_session() as session:
            payroll_repo = MonthlyPayrollRepository(session)
            has_payroll = payroll_repo.exists_for_period_and_company(period_id, self.selected_company_id)
            self.btn_recalculate.setEnabled(has_payroll)
            self.btn_edit_menu.setEnabled(has_payroll)
            self.btn_export.setEnabled(has_payroll)

    def _clear_status(self):
        """Clear status labels."""
        self.lbl_period_status.setText("Status: -")
        self.lbl_employee_count.setText("Employees: 0")
        self.lbl_total_salary.setText("Total Net: ₹0")
        self.btn_recalculate.setEnabled(False)
        self.btn_edit_menu.setEnabled(False)
        self.btn_export.setEnabled(False)

    def _show_edit_menu(self):
        """Show edit menu with options."""
        menu = QMenu(self)

        # Set all PT
        pt_action = menu.addAction("📝 Set PT for All (₹200)")
        pt_action.triggered.connect(lambda: self._set_all_field("professional_tax", Decimal("200")))

        # Clear all loans
        clear_loans = menu.addAction("💰 Clear All Loans")
        clear_loans.triggered.connect(lambda: self._set_all_field("loan_deduction", Decimal("0")))

        # Clear all TDS
        clear_tds = menu.addAction("📋 Clear All TDS")
        clear_tds.triggered.connect(lambda: self._set_all_field("tds", Decimal("0")))

        menu.exec(self.btn_edit_menu.mapToGlobal(self.btn_edit_menu.rect().bottomLeft()))

    def _set_all_field(self, field: str, value):
        """Set a field for all employees."""
        period_id = self.period_combo.currentData()
        if not period_id:
            return

        try:
            db = get_db()
            with db.get_session() as session:
                payroll_repo = MonthlyPayrollRepository(session)
                service = PayrollService(session)

                payrolls = payroll_repo.get_all_for_period_and_company(period_id, self.selected_company_id)
                for payroll in payrolls:
                    setattr(payroll, field, value)
                    service.recalculate_payroll(payroll.id)

                session.commit()

            self._load_payroll_data(period_id)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update:\n{str(e)}")

    def _on_recalculate_all(self):
        """Recalculate all payroll records."""
        period_id = self.period_combo.currentData()
        if not period_id:
            return

        self.table.clearFocus()
        QApplication.processEvents()

        if self._pending_changes:
            self._save_pending_changes()

        try:
            db = get_db()
            with db.get_session() as session:
                payroll_repo = MonthlyPayrollRepository(session)
                service = PayrollService(session)

                payrolls = payroll_repo.get_all_for_period_and_company(period_id, self.selected_company_id)
                for payroll in payrolls:
                    service.recalculate_payroll(payroll.id)

                session.commit()

            self._load_payroll_data(period_id)
            QMessageBox.information(self, "Done", "All payroll records recalculated.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to recalculate:\n{str(e)}")

    def _on_export_payroll(self):
        """Export payroll to CSV file."""
        period_id = self.period_combo.currentData()
        if not period_id:
            return

        period_label = self.period_combo.currentText().replace("📝 ", "").strip()
        default_name = f"Payroll_{self.selected_company_name}_{period_label}.csv"
        default_name = default_name.replace(" ", "_").replace("/", "-")

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Payroll",
            default_name,
            "CSV Files (*.csv);;All Files (*)",
        )

        if not file_path:
            return

        try:
            # Collect data from table
            include_arrears = self.chk_arrears.isChecked()
            skip_cols = {self.COL_ID}
            if not include_arrears:
                skip_cols.add(self.COL_ARREARS)
            headers = [
                col[0] for i, col in enumerate(self.COLUMNS)
                if i not in skip_cols
            ]
            rows = []

            for row_idx in range(self.table.rowCount()):
                row_data = []
                for col_idx in range(len(self.COLUMNS)):
                    if col_idx in skip_cols:
                        continue
                    item = self.table.item(row_idx, col_idx)
                    text = item.text() if item else ""
                    # Clean currency formatting for CSV
                    text = text.replace("₹", "").replace(",", "")
                    row_data.append(text)
                rows.append(row_data)

            # Write CSV
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(rows)

            QMessageBox.information(
                self,
                "Exported",
                f"Payroll exported successfully to:\n{file_path}",
            )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export:\n{str(e)}")

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
        if self._table_font_size < 20:
            self._table_font_size += 1
            self._apply_table_zoom()

    def _zoom_out(self):
        if self._table_font_size > 9:
            self._table_font_size -= 1
            self._apply_table_zoom()

    def _zoom_reset(self):
        self._table_font_size = 12
        self._apply_table_zoom()

    def _apply_table_zoom(self):
        self.table.setStyleSheet(f"""
            QTableWidget {{
                font-size: {self._table_font_size}px;
            }}
            QTableWidget::item {{
                padding: 4px;
            }}
        """)
        self.table.verticalHeader().setDefaultSectionSize(self._table_font_size * 2 + 10)

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

    def _on_current_cell_changed(self, current_row: int, current_col: int, prev_row: int, prev_col: int):
        """Handle cell selection change to highlight entire row with selected column darkened."""
        # Clear previous row highlighting
        if self._highlighted_row >= 0 and self._highlighted_row < self.table.rowCount():
            for col in range(self.table.columnCount()):
                item = self.table.item(self._highlighted_row, col)
                if item:
                    # Reset to default or editable/net color
                    if col in [self.COL_LOAN, self.COL_TDS]:
                        item.setBackground(QBrush(QColor("#E8F5E9")))  # Light green for editable
                    elif col == self.COL_NET:
                        item.setBackground(QBrush(QColor("#FFF9C4")))  # Yellow for net
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
            editable_cols = [self.COL_LOAN, self.COL_TDS]

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
