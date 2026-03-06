"""Payroll management widget - Excel-like in-place editing."""

import calendar
from decimal import Decimal, ROUND_HALF_UP
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
    QGroupBox,
    QMenu,
    QComboBox,
    QLineEdit,
    QStyledItemDelegate,
    QApplication,
)
from PySide6.QtCore import Qt, QTimer, QEvent
from PySide6.QtGui import QShortcut, QKeySequence, QColor, QBrush, QDoubleValidator, QIntValidator

from staffly.database import get_db
from staffly.database.repositories import PayrollPeriodRepository, MonthlyPayrollRepository
from staffly.services import PayrollService
from staffly.ui.dialogs.period_dialog import PeriodDialog


class NumericEditDelegate(QStyledItemDelegate):
    """
    Delegate that provides a simple in-place line edit for numbers only.
    No popup - just direct text editing in the cell.
    """
    
    def __init__(self, decimals=0, parent=None):
        super().__init__(parent)
        self.decimals = decimals
    
    def createEditor(self, parent, option, index):
        """Create a simple line edit that only accepts numbers."""
        editor = QLineEdit(parent)
        if self.decimals > 0:
            validator = QDoubleValidator(0, 999999, self.decimals, editor)
        else:
            validator = QIntValidator(0, 999999, editor)
        editor.setValidator(validator)
        editor.setFrame(False)
        editor.setAlignment(Qt.AlignCenter)
        return editor
    
    def setEditorData(self, editor, index):
        """Set the editor's value from the cell."""
        text = index.model().data(index, Qt.DisplayRole) or "0"
        # Remove currency symbols and commas
        text = text.replace("₹", "").replace(",", "").strip()
        editor.setText(text)
        editor.setCursorPosition(len(text))
    
    def setModelData(self, editor, model, index):
        """Set the cell's value from the editor."""
        text = editor.text().strip()
        if not text:
            text = "0"
        model.setData(index, text, Qt.DisplayRole)
    
    def updateEditorGeometry(self, editor, option, index):
        """Make editor fill the cell exactly."""
        editor.setGeometry(option.rect)


class PayrollWidget(QWidget):
    """
    Excel-like payroll management with in-place editing.
    
    Features:
    - Direct cell editing (double-click or F2 to edit)
    - Auto-save with debouncing (saves after 2 seconds of inactivity)
    - All columns visible for comprehensive view
    - Recalculates automatically on changes (updates only affected cells)
    - Ctrl+Scroll or Ctrl+Plus/Minus to zoom table
    """

    def __init__(self, selected_company_id: int, selected_company_name: str):
        super().__init__()
        self.selected_company_id = selected_company_id
        self.selected_company_name = selected_company_name
        self._table_font_size = 12
        self._pending_changes = {}  # {payroll_id: {field: value}}
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._save_pending_changes)
        self._current_period_locked = False
        self._is_loading = False  # Flag to prevent cellChanged during load
        self._setup_ui()
        self._setup_zoom_shortcuts()
        self._load_periods()

    def _setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 8, 10, 10)

        # ═══════════════════════════════════════════════════════════════════
        # PERIOD SELECTOR & ACTIONS
        # ═══════════════════════════════════════════════════════════════════
        period_group = QGroupBox("Payroll Period")
        period_layout = QHBoxLayout(period_group)

        period_label = QLabel("Select Period:")
        self.period_combo = QComboBox()
        self.period_combo.setMinimumWidth(200)
        self.period_combo.currentIndexChanged.connect(self._on_period_changed)

        self.company_scope_label = QLabel(f"Company: {self.selected_company_name}")
        self.company_scope_label.setStyleSheet("font-weight: 600;")

        # Button style
        btn_style = """
            QPushButton {
                font-size: 12px;
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
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
                border: none;
            }
        """

        self.btn_new_period = QPushButton("📅 New Period")
        self.btn_new_period.setFixedSize(120, 40)
        self.btn_new_period.setStyleSheet(btn_style + """
            QPushButton { background-color: #9C27B0; color: white; }
            QPushButton:hover { background-color: #7B1FA2; }
        """)
        self.btn_new_period.clicked.connect(self._on_new_period)

        self.btn_delete_period = QPushButton("🗑️ Delete Period")
        self.btn_delete_period.setFixedSize(130, 40)
        self.btn_delete_period.setStyleSheet(btn_style + """
            QPushButton { background-color: #D32F2F; color: white; }
            QPushButton:hover { background-color: #B71C1C; }
        """)
        self.btn_delete_period.clicked.connect(self._on_delete_period)
        self.btn_delete_period.setEnabled(False)

        self.btn_generate = QPushButton("⚡ Generate")
        self.btn_generate.setFixedSize(120, 40)
        self.btn_generate.setStyleSheet(btn_style + """
            QPushButton { background-color: #4CAF50; color: white; }
            QPushButton:hover { background-color: #45a049; }
        """)
        self.btn_generate.clicked.connect(self._on_generate_payroll)
        self.btn_generate.setEnabled(False)

        self.btn_recalculate = QPushButton("🔄 Recalculate")
        self.btn_recalculate.setFixedSize(130, 40)
        self.btn_recalculate.setStyleSheet(btn_style + """
            QPushButton { background-color: #00ACC1; color: white; }
            QPushButton:hover { background-color: #0097A7; }
        """)
        self.btn_recalculate.clicked.connect(self._on_recalculate_all)
        self.btn_recalculate.setEnabled(False)

        self.btn_edit_menu = QPushButton("✏️ Edit Menu")
        self.btn_edit_menu.setFixedSize(120, 40)
        self.btn_edit_menu.setStyleSheet(btn_style + """
            QPushButton { background-color: #2196F3; color: white; }
            QPushButton:hover { background-color: #1976D2; }
        """)
        self.btn_edit_menu.clicked.connect(self._show_edit_menu)
        self.btn_edit_menu.setEnabled(False)

        self.btn_finalize = QPushButton("🔒 Finalize")
        self.btn_finalize.setFixedSize(120, 40)
        self.btn_finalize.setStyleSheet(btn_style + """
            QPushButton { background-color: #FF9800; color: white; }
            QPushButton:hover { background-color: #F57C00; }
        """)
        self.btn_finalize.clicked.connect(self._on_finalize)
        self.btn_finalize.setEnabled(False)
        self.btn_finalize.setVisible(False)

        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setFixedSize(40, 40)
        self.btn_refresh.setToolTip("Refresh")
        self.btn_refresh.setStyleSheet(btn_style + """
            QPushButton { background-color: #607D8B; color: white; }
            QPushButton:hover { background-color: #546E7A; }
        """)
        self.btn_refresh.clicked.connect(self._refresh_all)

        period_layout.addWidget(period_label)
        period_layout.addWidget(self.period_combo)
        period_layout.addWidget(self.btn_new_period)
        period_layout.addWidget(self.btn_delete_period)
        period_layout.addSpacing(12)
        period_layout.addWidget(self.company_scope_label)
        period_layout.addStretch()
        period_layout.addWidget(self.btn_generate)
        period_layout.addWidget(self.btn_recalculate)
        period_layout.addWidget(self.btn_edit_menu)
        period_layout.addWidget(self.btn_finalize)
        period_layout.addWidget(self.btn_refresh)

        layout.addWidget(period_group)

        # ═══════════════════════════════════════════════════════════════════
        # STATUS BAR
        # ═══════════════════════════════════════════════════════════════════
        status_layout = QHBoxLayout()

        self.lbl_period_status = QLabel("Status: -")
        self.lbl_employee_count = QLabel("Employees: 0")
        self.lbl_total_salary = QLabel("Total Net: ₹0")
        self.lbl_save_status = QLabel("")
        self.lbl_save_status.setStyleSheet("color: #4CAF50; font-weight: bold;")

        status_layout.addWidget(self.lbl_period_status)
        status_layout.addWidget(self.lbl_employee_count)
        status_layout.addStretch()
        status_layout.addWidget(self.lbl_save_status)
        status_layout.addWidget(self.lbl_total_salary)

        layout.addLayout(status_layout)

        # ═══════════════════════════════════════════════════════════════════
        # PAYROLL TABLE - Excel Style
        # ═══════════════════════════════════════════════════════════════════
        # Columns definition: (name, width, editable, data_type)
        self.COLUMNS = [
            ("ID", 0, False, None),
            ("Code", 80, False, None),
            ("Name", 150, False, None),
            ("Branch", 100, False, None),
            # Attendance & Leave
            ("Total Days", 85, False, None),
            ("Paid", 60, False, None),
            ("Present", 70, False, None),
            ("PL", 50, True, "decimal"),
            ("SL", 50, True, "decimal"),
            ("CL", 50, True, "decimal"),
            ("Absent", 65, True, "int"),
            # Earnings - Read only (from salary structure)
            ("Basic", 80, False, None),
            ("HRA", 70, False, None),
            ("Bonus", 70, False, None),
            ("CCA", 70, False, None),
            ("Other+", 70, False, None),
            ("Gross", 90, False, None),
            # Deductions - Editable
            ("PF", 70, False, None),  # Calculated
            ("ESI", 60, False, None),  # Calculated
            ("PT", 70, True, "currency"),
            ("TDS", 70, True, "currency"),
            ("Loan", 70, True, "currency"),
            ("Other-", 70, True, "currency"),
            ("Ded.", 80, False, None),  # Total Deductions - calculated
            ("Net Salary", 100, False, None),  # Calculated
        ]
        
        # Column index mapping for quick access
        self.COL_ID = 0
        self.COL_TOTAL_DAYS = 4
        self.COL_PAID = 5
        self.COL_PRESENT = 6
        self.COL_PL = 7
        self.COL_SL = 8
        self.COL_CL = 9
        self.COL_ABSENT = 10
        self.COL_PF = 17
        self.COL_ESI = 18
        self.COL_PT = 19
        self.COL_TDS = 20
        self.COL_LOAN = 21
        self.COL_OTHER_DED = 22
        self.COL_TOTAL_DED = 23
        self.COL_NET = 24
        
        self.table = QTableWidget()
        self.table.setObjectName("payrollTable")
        self.table.setColumnCount(len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels([c[0] for c in self.COLUMNS])

        # Table settings - select entire rows, allow extended selection
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)  # Highlight whole row
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)  # Allows Shift+Click & Ctrl+Click
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.setEditTriggers(
            QAbstractItemView.DoubleClicked | 
            QAbstractItemView.EditKeyPressed
        )
        
        # Track which column we're editing for multi-row edits
        self._edit_column = None
        
        # Install event filter for Excel-like keyboard navigation
        self.table.installEventFilter(self)
        
        # Connect selection changed to track current column
        self.table.currentCellChanged.connect(self._on_current_cell_changed)
        
        # Set numeric delegates for editable columns (no popup, just inline editing)
        int_delegate = NumericEditDelegate(decimals=0, parent=self.table)
        decimal_delegate = NumericEditDelegate(decimals=1, parent=self.table)
        
        # Integer columns (Absent)
        for col in [self.COL_ABSENT]:
            self.table.setItemDelegateForColumn(col, int_delegate)
        
        # Decimal columns (PL, SL, CL - allow half days)
        for col in [self.COL_PL, self.COL_SL, self.COL_CL]:
            self.table.setItemDelegateForColumn(col, decimal_delegate)
        
        # Connect cell changed signal
        self.table.cellChanged.connect(self._on_cell_changed)

        # Apply styling
        self._apply_table_zoom()

        # Hide ID column
        self.table.setColumnHidden(0, True)

        # Set column widths
        header = self.table.horizontalHeader()
        for col_idx, (name, width, editable, dtype) in enumerate(self.COLUMNS):
            if width > 0:
                if name == "Name":
                    header.setSectionResizeMode(col_idx, QHeaderView.Stretch)
                else:
                    self.table.setColumnWidth(col_idx, width)

        layout.addWidget(self.table)

        # ═══════════════════════════════════════════════════════════════════
        # BOTTOM INFO
        # ═══════════════════════════════════════════════════════════════════
        info_layout = QHBoxLayout()
        info_label = QLabel("💡 Double-click or press any key on highlighted cells to edit • Changes auto-save after 2 seconds • Blue = Attendance • Green = Deductions")
        info_label.setStyleSheet("color: gray; font-size: 11px;")
        info_layout.addWidget(info_label)
        
        # Legend
        legend_layout = QHBoxLayout()
        legend_layout.addStretch()
        
        att_legend = QLabel("■ Attendance")
        att_legend.setStyleSheet("color: #1565C0; background-color: #E3F2FD; padding: 2px 6px; border-radius: 3px;")
        legend_layout.addWidget(att_legend)
        
        ded_legend = QLabel("■ Deductions")
        ded_legend.setStyleSheet("color: #2E7D32; background-color: #E8F5E9; padding: 2px 6px; border-radius: 3px;")
        legend_layout.addWidget(ded_legend)
        
        info_layout.addLayout(legend_layout)
        layout.addLayout(info_layout)

    def _get_column_index(self, name: str) -> int:
        """Get column index by name."""
        for idx, (col_name, _, _, _) in enumerate(self.COLUMNS):
            if col_name == name:
                return idx
        return -1

    def _load_periods(self):
        """Load payroll periods into combo box."""
        self.period_combo.clear()
        self.period_combo.addItem("-- Select Period --", None)

        db = get_db()
        with db.get_session() as session:
            repo = PayrollPeriodRepository(session)
            periods = repo.get_all_ordered()

            for period in periods:
                status = "📝"
                self.period_combo.addItem(
                    f"{status} {period.period_label}",
                    period.id
                )

    def _on_period_changed(self, index: int):
        """Handle period selection change."""
        period_id = self.period_combo.currentData()
        self.btn_delete_period.setEnabled(bool(period_id))
        if period_id:
            self._load_payroll_data(period_id)
            self._update_buttons(period_id)
        else:
            self.table.setRowCount(0)
            self._clear_status()

    def _on_delete_period(self):
        """Delete selected payroll period and optionally create a new one."""
        period_id = self.period_combo.currentData()
        if not period_id:
            QMessageBox.information(self, "Select Period", "Please select a payroll period first.")
            return

        period_label = self.period_combo.currentText().replace("📝 ", "").strip()

        reply = QMessageBox.warning(
            self,
            "Delete Payroll Period",
            f"⚠️ Delete payroll period '{period_label}'?\n\n"
            "This will also delete payroll records linked to this period.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            db = get_db()
            with db.get_session() as session:
                period_repo = PayrollPeriodRepository(session)
                deleted = period_repo.delete_by_id(period_id)
                if not deleted:
                    QMessageBox.warning(self, "Not Found", "Selected payroll period was not found.")
                    return
                session.commit()

            self._load_periods()
            self.period_combo.setCurrentIndex(0)
            self.table.setRowCount(0)
            self._clear_status()

            create_new = QMessageBox.question(
                self,
                "Period Deleted",
                "Payroll period deleted successfully.\n\nCreate a new payroll period now?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if create_new == QMessageBox.Yes:
                self._on_new_period()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete payroll period:\n{str(e)}")

    def _load_payroll_data(self, period_id: int):
        """Load payroll data for selected period."""
        # Set loading flag to prevent cellChanged triggering
        self._is_loading = True
        self.table.setRowCount(0)

        db = get_db()
        with db.get_session() as session:
            period_repo = PayrollPeriodRepository(session)
            payroll_repo = MonthlyPayrollRepository(session)

            period = period_repo.get_by_id(period_id)
            payrolls = payroll_repo.get_all_for_period_and_company(period_id, self.selected_company_id)
            self._current_period_locked = False

            # Update status
            status_text = "📝 OPEN (editable)"
            self.lbl_period_status.setText(f"Status: {status_text}")

            total_net = 0
            for payroll in payrolls:
                row = self.table.rowCount()
                self.table.insertRow(row)
                
                # Store payroll ID in row
                id_item = QTableWidgetItem(str(payroll.id))
                self.table.setItem(row, 0, id_item)
                
                # Employee info (read-only)
                self._set_readonly_item(row, 1, payroll.employee.employee_code)
                self._set_readonly_item(row, 2, payroll.employee.full_name)
                self._set_readonly_item(row, 3, payroll.employee.branch or "-")
                
                # Attendance (driven by editable PL/SL/CL/Absent)
                self._set_readonly_item(row, self.COL_TOTAL_DAYS, str(period.working_days))
                self._set_readonly_item(row, self.COL_PAID, str(payroll.paid_days))
                self._set_readonly_item(row, self.COL_PRESENT, str(payroll.present_days))
                self._set_editable_item(row, self.COL_PL, f"{float(payroll.privilege_leave):.1f}", "attendance")
                self._set_editable_item(row, self.COL_SL, f"{float(payroll.sick_leave):.1f}", "attendance")
                self._set_editable_item(row, self.COL_CL, f"{float(payroll.casual_leave):.1f}", "attendance")
                self._set_editable_item(row, self.COL_ABSENT, str(payroll.absent_days), "attendance")
                
                # Earnings (read-only - from salary structure)
                self._set_readonly_item(row, 11, f"₹{payroll.basic_salary:,.2f}")
                self._set_readonly_item(row, 12, f"₹{payroll.hra:,.2f}")
                self._set_readonly_item(row, 13, f"₹{payroll.bonus:,.2f}")
                self._set_readonly_item(row, 14, f"₹{payroll.cca:,.2f}")
                self._set_readonly_item(row, 15, f"₹{payroll.other_allowance:,.2f}")
                self._set_readonly_item(row, 16, f"₹{payroll.gross_earnings:,.2f}")
                
                # Deductions
                self._set_readonly_item(row, self.COL_PF, f"₹{payroll.pf_employee:,.2f}")  # Calculated
                self._set_readonly_item(row, self.COL_ESI, f"₹{payroll.esi_employee:,.2f}")  # Calculated
                self._set_readonly_item(row, self.COL_PT, f"₹{payroll.professional_tax:,.2f}")
                self._set_readonly_item(row, self.COL_TDS, f"₹{payroll.tds:,.2f}")
                self._set_readonly_item(row, self.COL_LOAN, f"₹{payroll.loan_deduction:,.2f}")
                self._set_readonly_item(row, self.COL_OTHER_DED, f"₹{payroll.other_deductions:,.2f}")
                self._set_readonly_item(row, self.COL_TOTAL_DED, f"₹{payroll.total_deductions:,.2f}")
                
                # Net salary
                net_item = QTableWidgetItem(f"₹{payroll.net_salary:,.2f}")
                net_item.setFlags(net_item.flags() & ~Qt.ItemIsEditable)
                net_item.setBackground(QBrush(QColor("#FFF9C4")))  # Light yellow for net
                net_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, self.COL_NET, net_item)

                total_net += float(payroll.net_salary)

            self.lbl_employee_count.setText(f"Employees: {len(payrolls)}")
            self.lbl_total_salary.setText(f"Total Net: ₹{total_net:,.2f}")

        # Clear loading flag
        self._is_loading = False

    def _set_readonly_item(self, row: int, col: int, text: str):
        """Set a read-only cell."""
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter if "₹" in text else Qt.AlignCenter)
        self.table.setItem(row, col, item)

    def _set_editable_item(self, row: int, col: int, text: str, category: str):
        """Set an editable cell with color coding."""
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)

        if category == "attendance":
            item.setBackground(QBrush(QColor("#E3F2FD")))  # Light blue
        elif category == "deduction":
            item.setBackground(QBrush(QColor("#E8F5E9")))  # Light green
        
        self.table.setItem(row, col, item)

    def _on_cell_changed(self, row: int, col: int):
        """Handle cell value change - queue for saving."""
        # Skip while loading table data
        if self._is_loading:
            return
            
        # Get payroll ID
        id_item = self.table.item(row, 0)
        if not id_item:
            return
        
        payroll_id = int(id_item.text())
        
        # Map column to field
        field_map = {
            self.COL_ABSENT: "absent_days",
            self.COL_PL: "privilege_leave",
            self.COL_SL: "sick_leave",
            self.COL_CL: "casual_leave",
        }
        
        if col not in field_map:
            return
        
        field = field_map[col]
        item = self.table.item(row, col)
        if not item:
            return
        
        # Parse value - remove any currency symbols or commas
        text = item.text().replace("₹", "").replace(",", "").strip()
        if text == "":
            text = "0"
        try:
            if col in [self.COL_PL, self.COL_SL, self.COL_CL]:  # Decimal fields (leaves)
                value = float(text)
            else:  # Integer fields (attendance)
                value = int(float(text))
        except ValueError:
            return
        
        # Queue the change
        if payroll_id not in self._pending_changes:
            self._pending_changes[payroll_id] = {"row": row}
        self._pending_changes[payroll_id][field] = value
        
        # Show saving indicator
        self.lbl_save_status.setText("⏳ Pending...")
        
        # Restart save timer (debounce) for near real-time updates
        self._save_timer.stop()
        self._save_timer.start(500)

    def _save_pending_changes(self):
        """Save all pending changes to database and update calculated cells in-place."""
        if not self._pending_changes:
            return
        
        try:
            db = get_db()
            # Store UI update data (extracted before session closes)
            ui_updates = {}
            
            with db.get_session() as session:
                payroll_repo = MonthlyPayrollRepository(session)
                service = PayrollService(session)
                
                for payroll_id, change_data in self._pending_changes.items():
                    row = change_data.get("row")
                    payroll = payroll_repo.get_by_id(payroll_id)
                    if not payroll:
                        continue

                    period = payroll.payroll_period
                    month_days = calendar.monthrange(period.year, period.month)[1]
                    
                    # Apply changes with validation
                    for field, value in change_data.items():
                        if field == "row":
                            continue
                        # Validate absence field
                        if field == "absent_days":
                            value = max(0, min(month_days, int(value)))
                        # Validate leave fields (max 31)
                        elif field in ["privilege_leave", "sick_leave", "casual_leave"]:
                            value = max(0.0, min(float(month_days), float(value)))
                        
                        setattr(payroll, field, value)

                    total_days = Decimal(str(month_days))
                    leave_total = (
                        Decimal(str(payroll.privilege_leave))
                        + Decimal(str(payroll.sick_leave))
                        + Decimal(str(payroll.casual_leave))
                    )
                    absent_days = Decimal(str(payroll.absent_days))

                    # Keep leaves + absent within total days by capping absent first.
                    max_absent_allowed = total_days - leave_total
                    if max_absent_allowed < Decimal("0"):
                        max_absent_allowed = Decimal("0")
                    capped_absent = min(absent_days, max_absent_allowed)
                    payroll.absent_days = int(capped_absent.to_integral_value(rounding=ROUND_HALF_UP))

                    paid_days_dec = total_days - Decimal(str(payroll.absent_days))
                    if paid_days_dec < Decimal("0"):
                        paid_days_dec = Decimal("0")
                    payroll.paid_days = int(paid_days_dec.to_integral_value(rounding=ROUND_HALF_UP))

                    present_days_dec = paid_days_dec - leave_total
                    if present_days_dec < Decimal("0"):
                        present_days_dec = Decimal("0")
                    payroll.present_days = int(present_days_dec.to_integral_value(rounding=ROUND_HALF_UP))
                    
                    # Recalculate payroll
                    service.recalculate_payroll(payroll_id)
                    
                    # Extract values BEFORE session closes (to avoid detached instance error)
                    if row is not None:
                        ui_updates[row] = {
                            "present_days": int(payroll.present_days),
                            "absent_days": int(payroll.absent_days),
                            "privilege_leave": float(payroll.privilege_leave),
                            "sick_leave": float(payroll.sick_leave),
                            "casual_leave": float(payroll.casual_leave),
                            "total_days": int(month_days),
                            "paid_days": payroll.paid_days,
                            "basic_salary": float(payroll.basic_salary),
                            "hra": float(payroll.hra),
                            "bonus": float(payroll.bonus),
                            "cca": float(payroll.cca),
                            "other_allowance": float(payroll.other_allowance),
                            "gross_earnings": float(payroll.gross_earnings),
                            "pf_employee": float(payroll.pf_employee),
                            "esi_employee": float(payroll.esi_employee),
                            "professional_tax": float(payroll.professional_tax),
                            "tds": float(payroll.tds),
                            "loan_deduction": float(payroll.loan_deduction),
                            "other_deductions": float(payroll.other_deductions),
                            "total_deductions": float(payroll.total_deductions),
                            "net_salary": float(payroll.net_salary),
                        }
                
                session.commit()
            
            # Update calculated cells in-place without reloading the whole table
            self._is_loading = True  # Prevent triggering cellChanged
            for row, data in ui_updates.items():
                self._update_cell(row, self.COL_TOTAL_DAYS, str(data["total_days"]))
                self._update_cell(row, self.COL_PRESENT, str(data["present_days"]))
                self._update_cell(row, self.COL_ABSENT, str(data["absent_days"]))
                self._update_cell(row, self.COL_PL, f"{data['privilege_leave']:.1f}")
                self._update_cell(row, self.COL_SL, f"{data['sick_leave']:.1f}")
                self._update_cell(row, self.COL_CL, f"{data['casual_leave']:.1f}")
                self._update_cell(row, 11, f"₹{data['basic_salary']:,.2f}")
                self._update_cell(row, 12, f"₹{data['hra']:,.2f}")
                self._update_cell(row, 13, f"₹{data['bonus']:,.2f}")
                self._update_cell(row, 14, f"₹{data['cca']:,.2f}")
                self._update_cell(row, 15, f"₹{data['other_allowance']:,.2f}")
                self._update_cell(row, 16, f"₹{data['gross_earnings']:,.2f}")
                self._update_cell(row, self.COL_PT, f"₹{data['professional_tax']:,.2f}")
                self._update_cell(row, self.COL_TDS, f"₹{data['tds']:,.2f}")
                self._update_cell(row, self.COL_LOAN, f"₹{data['loan_deduction']:,.2f}")
                self._update_cell(row, self.COL_OTHER_DED, f"₹{data['other_deductions']:,.2f}")
                self._update_cell(row, self.COL_PAID, str(data["paid_days"]))
                self._update_cell(row, self.COL_PF, f"₹{data['pf_employee']:,.2f}")
                self._update_cell(row, self.COL_ESI, f"₹{data['esi_employee']:,.2f}")
                self._update_cell(row, self.COL_TOTAL_DED, f"₹{data['total_deductions']:,.2f}")
                self._update_cell(row, self.COL_NET, f"₹{data['net_salary']:,.2f}")
            self._is_loading = False
            
            self._pending_changes.clear()
            self.lbl_save_status.setText("✅ Saved")
            
            # Clear the saved message after 2 seconds
            QTimer.singleShot(2000, lambda: self.lbl_save_status.setText(""))
            
            # Update totals
            self._update_totals()
                
        except Exception as e:
            self.lbl_save_status.setText("❌ Error saving")
            QMessageBox.critical(self, "Error", f"Failed to save changes:\n{str(e)}")

    def _update_cell(self, row: int, col: int, text: str):
        """Update a cell's text without triggering signals."""
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
        """Update button states based on period status."""
        db = get_db()
        with db.get_session() as session:
            period_repo = PayrollPeriodRepository(session)
            payroll_repo = MonthlyPayrollRepository(session)

            period = period_repo.get_by_id(period_id)
            has_payroll = payroll_repo.exists_for_period_and_company(period_id, self.selected_company_id)
            self.btn_generate.setEnabled(not has_payroll)
            self.btn_recalculate.setEnabled(has_payroll)
            self.btn_edit_menu.setEnabled(has_payroll)
            self.btn_finalize.setEnabled(False)

    def _clear_status(self):
        """Clear status labels."""
        self.lbl_period_status.setText("Status: -")
        self.lbl_employee_count.setText("Employees: 0")
        self.lbl_total_salary.setText("Total Net: ₹0")
        self.btn_generate.setEnabled(False)
        self.btn_recalculate.setEnabled(False)
        self.btn_edit_menu.setEnabled(False)
        self.btn_finalize.setEnabled(False)

    def _show_edit_menu(self):
        """Show the edit menu with additional options."""
        menu = QMenu(self)
        
        # Clear payroll action
        clear_action = menu.addAction("🗑️ Clear All Payroll")
        clear_action.triggered.connect(self._on_clear_payroll)
        
        menu.addSeparator()
        
        # Delete selected employee
        delete_action = menu.addAction("❌ Remove Selected Employee")
        delete_action.triggered.connect(self._on_delete_selected)
        
        menu.addSeparator()
        
        # Set all PT
        pt_action = menu.addAction("📝 Set PT for All (₹200)")
        pt_action.triggered.connect(lambda: self._set_all_field("professional_tax", Decimal("200")))
        
        # Clear all loans
        clear_loans = menu.addAction("💰 Clear All Loans")
        clear_loans.triggered.connect(lambda: self._set_all_field("loan_deduction", Decimal("0")))
        
        # Show menu at button
        menu.exec(self.btn_edit_menu.mapToGlobal(self.btn_edit_menu.rect().bottomLeft()))

    def _on_delete_selected(self):
        """Delete the selected employee's payroll."""
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.information(self, "Select", "Please select an employee row first.")
            return
        
        row = selected[0].row()
        payroll_id = int(self.table.item(row, 0).text())
        name = self.table.item(row, 2).text()
        
        reply = QMessageBox.question(
            self,
            "Remove Employee",
            f"Remove {name} from this payroll?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                db = get_db()
                with db.get_session() as session:
                    payroll_repo = MonthlyPayrollRepository(session)
                    payroll_repo.delete_payroll(payroll_id)
                    session.commit()
                
                period_id = self.period_combo.currentData()
                self._load_payroll_data(period_id)
                self._update_buttons(period_id)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to remove employee:\n{str(e)}")

    def _on_recalculate_all(self):
        """Recalculate all payroll records."""
        period_id = self.period_combo.currentData()
        if not period_id:
            return

        # Ensure in-progress cell edits are committed before recalculation
        self.table.clearFocus()
        QApplication.processEvents()

        # Persist any queued edits first, so recalculate uses latest values
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

    def _set_all_field(self, field: str, value):
        """Set a field value for all employees."""
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

    def _on_new_period(self):
        """Open dialog to create new period."""
        dialog = PeriodDialog(
            self,
            selected_company_id=self.selected_company_id,
            selected_company_name=self.selected_company_name,
        )
        if dialog.exec():
            self._load_periods()

    def _on_generate_payroll(self):
        """Generate payroll for all active employees."""
        period_id = self.period_combo.currentData()
        if not period_id:
            return

        reply = QMessageBox.question(
            self,
            "Generate Payroll",
            f"Generate payroll for active employees in {self.selected_company_name}?\n\n"
            "Attendance will be copied from the previous month if available.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
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
                        copy_from_previous=True,
                        company_id=self.selected_company_id,
                    )

                QMessageBox.information(self, "Success", f"Generated payroll for {count} employees.")
                self._load_payroll_data(period_id)
                self._update_buttons(period_id)

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to generate payroll:\n{str(e)}")

    def _on_finalize(self):
        """Finalize is disabled while lock feature is turned off."""
        QMessageBox.information(
            self,
            "Locking Disabled",
            "Period locking/finalize is currently disabled. Data remains editable.",
        )

    def _on_clear_payroll(self):
        """Clear all payroll records for the selected period."""
        period_id = self.period_combo.currentData()
        if not period_id:
            return

        reply = QMessageBox.warning(
            self,
            "Clear Payroll",
            f"⚠️ This will DELETE payroll records for {self.selected_company_name} in this period!\n\n"
            "Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                db = get_db()
                with db.get_session() as session:
                    payroll_repo = MonthlyPayrollRepository(session)
                    count = payroll_repo.delete_for_period_and_company(period_id, self.selected_company_id)
                    session.commit()

                QMessageBox.information(self, "Cleared", f"Deleted {count} payroll records.")
                self._load_payroll_data(period_id)
                self._update_buttons(period_id)

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to clear payroll:\n{str(e)}")

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

    def _on_current_cell_changed(self, row, col, prev_row, prev_col):
        """Track current column for multi-row editing and highlight it."""
        self._edit_column = col
        self._highlight_current_column(col, prev_col)
    
    def _highlight_current_column(self, col, prev_col):
        """Highlight the current column with a darker shade."""
        if prev_col is not None and prev_col != col:
            # Reset previous column header
            prev_header = self.table.horizontalHeaderItem(prev_col)
            if prev_header:
                prev_header.setBackground(QBrush(QColor("#f0f0f0")))
        
        # Highlight current column header
        current_header = self.table.horizontalHeaderItem(col)
        if current_header:
            current_header.setBackground(QBrush(QColor("#64B5F6")))  # Darker blue

    def eventFilter(self, obj, event):
        """
        Excel-like keyboard navigation for the table.
        
        - Tab: Move to next editable cell (right)
        - Shift+Tab: Move to previous editable cell (left)
        - Enter: Move down to next row (same column)
        - Shift+Enter: Move up to previous row
        - Delete/Backspace: Clear selected cells
        - Number keys: Type value into all selected rows (same column)
        - Ctrl+C: Copy selected cells
        - Ctrl+V: Paste to selected cells
        """
        if obj == self.table and event.type() == QEvent.KeyPress:
            key = event.key()
            modifiers = event.modifiers()
            
            current = self.table.currentItem()
            if not current:
                return super().eventFilter(obj, event)
            
            row, col = current.row(), current.column()
            
            # Check if we're in editing mode
            is_editing = self.table.state() == QAbstractItemView.EditingState
            
            # Tab - move to next editable cell
            if key == Qt.Key_Tab and not (modifiers & Qt.ShiftModifier):
                self._move_to_next_editable(row, col, forward=True)
                return True
            
            # Shift+Tab - move to previous editable cell
            if key == Qt.Key_Tab and (modifiers & Qt.ShiftModifier):
                self._move_to_next_editable(row, col, forward=False)
                return True
            
            # Enter handling
            if key == Qt.Key_Return or key == Qt.Key_Enter:
                if is_editing:
                    # Let Qt commit editor value naturally.
                    return super().eventFilter(obj, event)
                if modifiers & Qt.ShiftModifier:
                    new_row = max(0, row - 1)
                else:
                    new_row = min(self.table.rowCount() - 1, row + 1)
                self.table.setCurrentCell(new_row, col)
                return True
            
            # Delete/Backspace - clear all selected rows in current column
            if key in (Qt.Key_Delete, Qt.Key_Backspace) and not is_editing:
                self._clear_selected_cells()
                return True
            
            # Ctrl+C - Copy
            if key == Qt.Key_C and (modifiers & Qt.ControlModifier):
                self._copy_selected_cells()
                return True
            
            # Ctrl+V - Paste
            if key == Qt.Key_V and (modifiers & Qt.ControlModifier):
                self._paste_to_selected_cells()
                return True
            
            # Number keys - only intercept for true multi-row bulk edit.
            if not is_editing and not (modifiers & Qt.ControlModifier):
                text = event.text()
                if text and (text.isdigit() or text == '.'):
                    editable_cols = {
                        self.COL_PL, self.COL_SL, self.COL_CL, self.COL_ABSENT
                    }
                    selected_rows = {item.row() for item in self.table.selectedItems()}
                    if col in editable_cols and len(selected_rows) > 1:
                        self._start_multi_edit(text)
                        return True
        
        return super().eventFilter(obj, event)

    def _start_multi_edit(self, initial_text: str):
        """Start editing multiple selected rows with initial text."""
        col = self._edit_column
        if col is None:
            return
        
        editable_cols = {
            self.COL_PL, self.COL_SL, self.COL_CL, self.COL_ABSENT
        }
        
        if col not in editable_cols:
            return
        
        # Get all selected rows
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())
        
        if len(selected_rows) <= 1:
            # Single row: use default Qt editor behavior.
            current_item = self.table.item(self.table.currentRow(), col)
            if current_item:
                self.table.editItem(current_item)
            return
        
        # Multiple rows - show input dialog for bulk edit
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QDialogButtonBox
        
        col_name = self.COLUMNS[col][0]
        
        # Create custom dialog that doesn't select all text
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Edit {col_name}")
        dialog.setMinimumWidth(250)
        
        layout = QVBoxLayout(dialog)
        label = QLabel(f"Enter value for {len(selected_rows)} selected rows:")
        layout.addWidget(label)
        
        line_edit = QLineEdit()
        line_edit.setText(initial_text)
        layout.addWidget(line_edit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        # Use timer to move cursor to end AFTER dialog is shown (avoids Qt auto-select)
        def move_cursor_to_end():
            line_edit.deselect()
            line_edit.setCursorPosition(len(line_edit.text()))
        
        QTimer.singleShot(10, move_cursor_to_end)
        
        if dialog.exec() == QDialog.Accepted:
            value = line_edit.text()
            if value:
                try:
                    # Validate it's a number
                    float(value)
                    self._apply_value_to_selected_rows(col, value)
                except ValueError:
                    pass

    def _move_to_next_editable(self, row: int, col: int, forward: bool = True):
        """Move to the next/previous editable cell."""
        # List of editable column indices
        editable_cols = [
            self.COL_PL, self.COL_SL, self.COL_CL, self.COL_ABSENT
        ]
        
        total_rows = self.table.rowCount()
        if total_rows == 0:
            return
        
        # Find current position in editable columns
        try:
            current_idx = editable_cols.index(col)
        except ValueError:
            # Not in an editable column, find nearest
            current_idx = 0 if forward else len(editable_cols) - 1
        
        if forward:
            # Move right, then down
            if current_idx < len(editable_cols) - 1:
                new_col = editable_cols[current_idx + 1]
                new_row = row
            else:
                new_col = editable_cols[0]
                new_row = min(row + 1, total_rows - 1)
        else:
            # Move left, then up
            if current_idx > 0:
                new_col = editable_cols[current_idx - 1]
                new_row = row
            else:
                new_col = editable_cols[-1]
                new_row = max(row - 1, 0)
        
        self.table.setCurrentCell(new_row, new_col)

    def _clear_selected_cells(self):
        """Clear (set to 0) all selected rows in current column."""
        col = self._edit_column
        if col is None:
            return
        
        editable_cols = {
            self.COL_PL, self.COL_SL, self.COL_CL, self.COL_ABSENT
        }
        
        if col not in editable_cols:
            return
        
        # Get all selected rows
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())
        
        self._is_loading = True
        for row in selected_rows:
            item = self.table.item(row, col)
            if item:
                item.setText("0")
        self._is_loading = False
        
        # Trigger save for all modified cells
        for row in selected_rows:
            self._on_cell_changed(row, col)

    def _apply_value_to_selected_rows(self, col: int, value: str):
        """Apply a value to all selected rows in a specific column."""
        # Get all selected rows
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())
        
        self._is_loading = True
        for row in selected_rows:
            item = self.table.item(row, col)
            if item:
                item.setText(value)
        self._is_loading = False
        
        # Trigger save for all modified cells
        for row in selected_rows:
            self._on_cell_changed(row, col)

    def _copy_selected_cells(self):
        """Copy selected rows' current column values to clipboard."""
        from PySide6.QtWidgets import QApplication
        
        col = self._edit_column
        if col is None:
            return
        
        # Get all selected rows
        selected_rows = sorted(set(item.row() for item in self.table.selectedItems()))
        
        values = []
        for row in selected_rows:
            item = self.table.item(row, col)
            values.append(item.text() if item else "")
        
        text = "\n".join(values)
        QApplication.clipboard().setText(text)

    def _paste_to_selected_cells(self):
        """Paste from clipboard to selected rows in current column."""
        from PySide6.QtWidgets import QApplication
        
        text = QApplication.clipboard().text()
        if not text:
            return
        
        col = self._edit_column
        if col is None:
            return
        
        editable_cols = {
            self.COL_PL, self.COL_SL, self.COL_CL, self.COL_ABSENT
        }
        
        if col not in editable_cols:
            return
        
        # Get all selected rows
        selected_rows = sorted(set(item.row() for item in self.table.selectedItems()))
        
        # Parse pasted values (one per line)
        values = text.strip().split("\n")
        
        self._is_loading = True
        for i, row in enumerate(selected_rows):
            if i < len(values):
                value = values[i].strip().replace(",", "").replace("₹", "")
                try:
                    float(value)  # Validate it's a number
                    item = self.table.item(row, col)
                    if item:
                        item.setText(value)
                except ValueError:
                    pass
        self._is_loading = False
        
        # Trigger save
        for row in selected_rows:
            self._on_cell_changed(row, col)

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
                gridline-color: #ccc;
            }}
            QTableWidget::item {{
                padding: 4px;
            }}
            QTableWidget::item:selected {{
                background-color: #BBDEFB;
                color: black;
            }}
            QTableWidget::item:focus {{
                background-color: #1565C0;
                color: white;
            }}
            QHeaderView::section {{
                font-size: {self._table_font_size - 1}px;
                font-weight: bold;
                padding: 6px;
                background-color: #f0f0f0;
                border: 1px solid #ccc;
            }}
        """)
        self.table.verticalHeader().setDefaultSectionSize(int(self._table_font_size * 2.2))
