"""Reports widget - generate salary slips and reports."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QGroupBox,
    QMessageBox,
    QFileDialog,
    QProgressDialog,
)
from PySide6.QtCore import Qt

from staffly.database import get_db
from staffly.database.repositories import PayrollPeriodRepository, MonthlyPayrollRepository, EmployeeRepository
from PySide6.QtWidgets import QComboBox
from staffly.reports import SalarySlipGenerator


class ReportsWidget(QWidget):
    """
    Reports generation page.
    
    Features:
    - Select period
    - Select employee (or all)
    - Generate salary slips
    - Export data
    """

    def __init__(self, selected_company_id: int, selected_company_name: str, selected_company_code: str = ""):
        super().__init__()
        self.selected_company_id = selected_company_id
        self.selected_company_name = selected_company_name
        self.selected_company_code = selected_company_code
        self._setup_ui()
        self._load_periods()

    def _setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(10, 8, 10, 10)

        # ═══════════════════════════════════════════════════════════════════
        # SALARY SLIP GENERATION
        # ═══════════════════════════════════════════════════════════════════
        slip_group = QGroupBox("Salary Slip Generation")
        slip_layout = QVBoxLayout(slip_group)

        # Period selector
        period_row = QHBoxLayout()
        period_label = QLabel("Select Period:")
        self.period_combo = QComboBox()
        self.period_combo.setMinimumWidth(200)
        self.period_combo.currentIndexChanged.connect(self._on_period_changed)

        self.lbl_company_scope = QLabel(f"Company: {self.selected_company_name}")
        self.lbl_company_scope.setStyleSheet("font-weight: 600;")

        # Refresh button
        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setFixedSize(40, 40)
        self.btn_refresh.setToolTip("Refresh periods list")
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: #607D8B;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #546E7A;
            }
        """)
        self.btn_refresh.clicked.connect(self._refresh_periods)

        period_row.addWidget(period_label)
        period_row.addWidget(self.period_combo)
        period_row.addWidget(self.btn_refresh)
        period_row.addSpacing(12)
        period_row.addWidget(self.lbl_company_scope)
        period_row.addStretch()
        slip_layout.addLayout(period_row)

        # Employee selector
        emp_row = QHBoxLayout()
        emp_label = QLabel("Select Employee:")
        self.employee_combo = QComboBox()
        self.employee_combo.setMinimumWidth(300)
        self.employee_combo.addItem("-- All Employees --", None)

        emp_row.addWidget(emp_label)
        emp_row.addWidget(self.employee_combo)
        emp_row.addStretch()
        slip_layout.addLayout(emp_row)

        # Button style - 150x50
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
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
                border: none;
            }
        """

        # Generate button
        btn_row = QHBoxLayout()
        self.btn_generate_slip = QPushButton("📄 Generate Slip(s)")
        self.btn_generate_slip.setFixedSize(150, 50)
        self.btn_generate_slip.setStyleSheet(btn_style + """
            QPushButton { background-color: #4CAF50; color: white; }
            QPushButton:hover { background-color: #45a049; }
        """)
        self.btn_generate_slip.clicked.connect(self._on_generate_slip)
        self.btn_generate_slip.setEnabled(False)

        btn_row.addWidget(self.btn_generate_slip)
        btn_row.addStretch()
        slip_layout.addLayout(btn_row)

        layout.addWidget(slip_group)

        # ═══════════════════════════════════════════════════════════════════
        # EXPORT OPTIONS
        # ═══════════════════════════════════════════════════════════════════
        export_group = QGroupBox("Export Data")
        export_layout = QVBoxLayout(export_group)

        export_row = QHBoxLayout()
        
        self.btn_export_excel = QPushButton("📊 Export to Excel")
        self.btn_export_excel.setFixedSize(150, 50)
        self.btn_export_excel.setStyleSheet(btn_style + """
            QPushButton { background-color: #2196F3; color: white; }
            QPushButton:hover { background-color: #1976D2; }
        """)
        self.btn_export_excel.clicked.connect(self._on_export_excel)
        self.btn_export_excel.setEnabled(False)

        self.btn_export_csv = QPushButton("📋 Export to CSV")
        self.btn_export_csv.setFixedSize(150, 50)
        self.btn_export_csv.setStyleSheet(btn_style + """
            QPushButton { background-color: #607D8B; color: white; }
            QPushButton:hover { background-color: #546E7A; }
        """)
        self.btn_export_csv.clicked.connect(self._on_export_csv)
        self.btn_export_csv.setEnabled(False)

        export_row.addWidget(self.btn_export_excel)
        export_row.addWidget(self.btn_export_csv)
        export_row.addStretch()
        export_layout.addLayout(export_row)

        layout.addWidget(export_group)

        # ═══════════════════════════════════════════════════════════════════
        # INFO
        # ═══════════════════════════════════════════════════════════════════
        info_group = QGroupBox("Information")
        info_layout = QVBoxLayout(info_group)

        self.info_label = QLabel("Select a period to view options.")
        info_layout.addWidget(self.info_label)

        layout.addWidget(info_group)

        # Spacer
        layout.addStretch()

    def _load_periods(self):
        """Load payroll periods (no lock requirement) into combo box."""
        self.period_combo.clear()
        self.period_combo.addItem("-- Select Period --", None)

        db = get_db()
        with db.get_session() as session:
            repo = PayrollPeriodRepository(session)
            payroll_repo = MonthlyPayrollRepository(session)
            periods = repo.get_all_ordered()

            for period in periods:
                has_data = payroll_repo.exists_for_period_and_company(period.id, self.selected_company_id)
                if has_data:
                    self.period_combo.addItem(
                        f"📝 {period.period_label}",
                        period.id
                    )

    def _refresh_periods(self):
        """Refresh the periods list."""
        current_period = self.period_combo.currentData()
        self._load_periods()
        
        # Restore selection if still exists
        if current_period:
            for i in range(self.period_combo.count()):
                if self.period_combo.itemData(i) == current_period:
                    self.period_combo.setCurrentIndex(i)
                    break

    def _on_period_changed(self, index: int):
        """Handle period selection change."""
        period_id = self.period_combo.currentData()
        self._load_employees_for_period(period_id)
        self._update_info(period_id)

        has_period = period_id is not None
        self.btn_generate_slip.setEnabled(has_period)
        self.btn_export_excel.setEnabled(has_period)
        self.btn_export_csv.setEnabled(has_period)

    def _load_employees_for_period(self, period_id: int | None):
        """Load employees who have payroll in selected period."""
        self.employee_combo.clear()
        self.employee_combo.addItem("-- All Employees --", None)

        if not period_id:
            return

        db = get_db()
        with db.get_session() as session:
            repo = MonthlyPayrollRepository(session)
            payrolls = repo.get_all_for_period(period_id)
            payrolls = [
                payroll for payroll in payrolls
                if payroll.employee and payroll.employee.company_id == self.selected_company_id
            ]

            for payroll in payrolls:
                self.employee_combo.addItem(
                    f"{payroll.employee.employee_code} - {payroll.employee.full_name}",
                    payroll.employee.id
                )

    def _update_info(self, period_id: int | None):
        """Update info label."""
        if not period_id:
            self.info_label.setText("Select a period to view options.")
            return

        db = get_db()
        with db.get_session() as session:
            period_repo = PayrollPeriodRepository(session)
            payroll_repo = MonthlyPayrollRepository(session)

            period = period_repo.get_by_id(period_id)
            payrolls = payroll_repo.get_all_for_period_and_company(period_id, self.selected_company_id)

            total_net = sum(float(p.net_salary) for p in payrolls)

            self.info_label.setText(
                f"Period: {period.period_label}\n"
                f"Status: Editable\n"
                f"Employees: {len(payrolls)}\n"
                f"Total Net Salary: ₹{total_net:,.2f}"
            )

    def _on_generate_slip(self):
        """Generate salary slip(s)."""
        period_id = self.period_combo.currentData()
        employee_id = self.employee_combo.currentData()

        if not period_id:
            return

        # Ask for output directory
        output_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            "",
            QFileDialog.ShowDirsOnly
        )
        
        if not output_dir:
            return

        try:
            db = get_db()
            with db.get_session() as session:
                payroll_repo = MonthlyPayrollRepository(session)
                
                if employee_id:
                    # Single employee
                    payroll = payroll_repo.get_by_employee_and_period(employee_id, period_id)
                    if not payroll:
                        QMessageBox.warning(self, "Not Found", "No payroll record found for this employee.")
                        return
                    payrolls = [payroll]
                else:
                    # All employees
                    payrolls = payroll_repo.get_all_for_period(period_id)
                    payrolls = [
                        payroll for payroll in payrolls
                        if payroll.employee and payroll.employee.company_id == self.selected_company_id
                    ]
                
                if not payrolls:
                    QMessageBox.warning(self, "No Data", "No payroll records found for this period.")
                    return
                
                # Show progress
                progress = QProgressDialog(
                    "Generating salary slips...", "Cancel", 0, len(payrolls), self
                )
                progress.setWindowModality(Qt.WindowModal)
                progress.setMinimumDuration(0)

                # Template is auto-selected from currently selected company
                company_key = (self.selected_company_code or self.selected_company_name or "").upper()
                template_name = "HNL" if "HNL" in company_key else "Endee"
                generator = SalarySlipGenerator(template_name=template_name)
                from pathlib import Path
                generated = []
                
                for i, payroll in enumerate(payrolls):
                    if progress.wasCanceled():
                        break
                    
                    progress.setValue(i)
                    progress.setLabelText(f"Generating slip for {payroll.employee.full_name}...")
                    
                    period = payroll.payroll_period
                    filename = f"Salary_Slip_{payroll.employee.employee_code}_{period.period_label.replace(' ', '_')}.pdf"
                    output_path = Path(output_dir) / filename
                    
                    generator.generate_slip(payroll, output_path)
                    generated.append(output_path)
                
                progress.setValue(len(payrolls))
                
                QMessageBox.information(
                    self,
                    "Success",
                    f"Generated {len(generated)} salary slip(s) in:\n{output_dir}"
                )
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate slips:\n{str(e)}")

    def _on_export_excel(self):
        """Export payroll data to Excel."""
        period_id = self.period_combo.currentData()
        if not period_id:
            return

        # TODO: Implement Excel export
        QMessageBox.information(
            self,
            "Coming Soon",
            "Excel export will be implemented next!"
        )

    def _on_export_csv(self):
        """Export payroll data to CSV."""
        period_id = self.period_combo.currentData()
        if not period_id:
            return

        # TODO: Implement CSV export
        QMessageBox.information(
            self,
            "Coming Soon",
            "CSV export will be implemented next!"
        )
