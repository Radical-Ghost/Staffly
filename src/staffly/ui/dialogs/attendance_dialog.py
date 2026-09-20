"""Attendance edit dialog."""

from decimal import Decimal
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QSpinBox,
    QDoubleSpinBox,
    QPushButton,
    QMessageBox,
    QGroupBox,
    QLabel,
)
from PySide6.QtCore import Qt

from staffly.database import get_db
from staffly.database.repositories import MonthlyPayrollRepository
from staffly.services import PayrollService


class AttendanceDialog(QDialog):
    """
    Dialog for editing attendance and viewing calculated salary.
    """

    def __init__(self, parent=None, payroll_id: int = None):
        super().__init__(parent)
        self.payroll_id = payroll_id
        self._setup_ui()
        self._load_payroll()

    def _setup_ui(self):
        """Setup the dialog UI."""
        self.setWindowTitle("Edit Attendance")
        self.setMinimumWidth(450)

        layout = QVBoxLayout(self)

        # ═══════════════════════════════════════════════════════════════════
        # EMPLOYEE INFO
        # ═══════════════════════════════════════════════════════════════════
        info_group = QGroupBox("Employee")
        info_layout = QFormLayout(info_group)

        self.lbl_employee = QLabel("-")
        self.lbl_period = QLabel("-")
        self.lbl_working_days = QLabel("-")

        info_layout.addRow("Employee:", self.lbl_employee)
        info_layout.addRow("Period:", self.lbl_period)
        info_layout.addRow("Working Days:", self.lbl_working_days)

        layout.addWidget(info_group)

        # ═══════════════════════════════════════════════════════════════════
        # ATTENDANCE
        # ═══════════════════════════════════════════════════════════════════
        att_group = QGroupBox("Attendance")
        att_layout = QFormLayout(att_group)

        self.spin_present = QSpinBox()
        self.spin_present.setRange(0, 31)
        self.spin_present.valueChanged.connect(self._on_attendance_changed)
        att_layout.addRow("Present Days:", self.spin_present)

        self.spin_absent = QSpinBox()
        self.spin_absent.setRange(0, 31)
        self.spin_absent.valueChanged.connect(self._on_attendance_changed)
        att_layout.addRow("Absent Days:", self.spin_absent)

        self.spin_late = QSpinBox()
        self.spin_late.setRange(0, 31)
        att_layout.addRow("Late Marks:", self.spin_late)

        layout.addWidget(att_group)

        # ═══════════════════════════════════════════════════════════════════
        # LEAVES
        # ═══════════════════════════════════════════════════════════════════
        leave_group = QGroupBox("Leaves Taken")
        leave_layout = QFormLayout(leave_group)

        self.spin_pl = QDoubleSpinBox()
        self.spin_pl.setRange(0, 31)
        self.spin_pl.setSingleStep(0.5)
        self.spin_pl.setDecimals(1)
        leave_layout.addRow("Privilege Leave (PL):", self.spin_pl)

        self.spin_sl = QDoubleSpinBox()
        self.spin_sl.setRange(0, 31)
        self.spin_sl.setSingleStep(0.5)
        self.spin_sl.setDecimals(1)
        leave_layout.addRow("Sick Leave (SL):", self.spin_sl)

        self.spin_cl = QDoubleSpinBox()
        self.spin_cl.setRange(0, 31)
        self.spin_cl.setSingleStep(0.5)
        self.spin_cl.setDecimals(1)
        leave_layout.addRow("Casual Leave (CL):", self.spin_cl)

        layout.addWidget(leave_group)

        # ═══════════════════════════════════════════════════════════════════
        # DEDUCTIONS (Manual Entry)
        # ═══════════════════════════════════════════════════════════════════
        ded_group = QGroupBox("Manual Deductions")
        ded_layout = QFormLayout(ded_group)

        self.spin_pt = QDoubleSpinBox()
        self.spin_pt.setRange(0, 99999)
        self.spin_pt.setPrefix("₹")
        self.spin_pt.setDecimals(2)
        ded_layout.addRow("Professional Tax:", self.spin_pt)

        self.spin_loan = QDoubleSpinBox()
        self.spin_loan.setRange(0, 999999)
        self.spin_loan.setPrefix("₹")
        self.spin_loan.setDecimals(2)
        ded_layout.addRow("Loan Deduction:", self.spin_loan)

        self.spin_tds = QDoubleSpinBox()
        self.spin_tds.setRange(0, 999999)
        self.spin_tds.setPrefix("₹")
        self.spin_tds.setDecimals(2)
        ded_layout.addRow("TDS:", self.spin_tds)

        self.spin_other_ded = QDoubleSpinBox()
        self.spin_other_ded.setRange(0, 999999)
        self.spin_other_ded.setPrefix("₹")
        self.spin_other_ded.setDecimals(2)
        ded_layout.addRow("Other Deductions:", self.spin_other_ded)

        layout.addWidget(ded_group)

        # ═══════════════════════════════════════════════════════════════════
        # CALCULATED VALUES (Read Only)
        # ═══════════════════════════════════════════════════════════════════
        calc_group = QGroupBox("Calculated (Read Only)")
        calc_layout = QFormLayout(calc_group)

        self.lbl_paid_days = QLabel("-")
        self.lbl_gross = QLabel("-")
        self.lbl_deductions = QLabel("-")
        self.lbl_net = QLabel("-")
        self.lbl_net.setStyleSheet("font-weight: bold; font-size: 14px;")

        calc_layout.addRow("Paid Days:", self.lbl_paid_days)
        calc_layout.addRow("Gross Earnings:", self.lbl_gross)
        calc_layout.addRow("Total Deductions:", self.lbl_deductions)
        calc_layout.addRow("Net Salary:", self.lbl_net)

        layout.addWidget(calc_group)

        # ═══════════════════════════════════════════════════════════════════
        # BUTTONS - styled via global QSS
        # ═══════════════════════════════════════════════════════════════════
        btn_layout = QHBoxLayout()

        self.btn_save = QPushButton("💾 Save & Recalculate")
        self.btn_save.setObjectName("successButton")
        self.btn_save.setFixedSize(150, 50)
        self.btn_save.clicked.connect(self._on_save)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("secondaryButton")
        self.btn_cancel.setFixedSize(150, 50)
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)

        layout.addLayout(btn_layout)

    def _load_payroll(self):
        """Load payroll data into form."""
        if not self.payroll_id:
            return

        db = get_db()
        with db.get_session() as session:
            repo = MonthlyPayrollRepository(session)
            payroll = repo.get_by_id(self.payroll_id)

            if payroll:
                self.lbl_employee.setText(
                    f"{payroll.employee.employee_code} - {payroll.employee.full_name}"
                )
                self.lbl_period.setText(payroll.payroll_period.period_label)
                self.lbl_working_days.setText(str(payroll.payroll_period.working_days))

                self.spin_present.setValue(payroll.present_days)
                self.spin_absent.setValue(payroll.absent_days)
                self.spin_late.setValue(payroll.late_marks)

                self.spin_pl.setValue(float(payroll.privilege_leave))
                self.spin_sl.setValue(float(payroll.sick_leave))
                self.spin_cl.setValue(float(payroll.casual_leave))

                self.spin_pt.setValue(float(payroll.professional_tax))
                self.spin_loan.setValue(float(payroll.loan_deduction))
                self.spin_tds.setValue(float(payroll.tds))
                self.spin_other_ded.setValue(float(payroll.other_deductions))

                self._update_calculated(payroll)

                # Store working days for validation
                self._working_days = payroll.payroll_period.working_days

    def _on_attendance_changed(self):
        """Auto-adjust when attendance changes."""
        # Simple validation feedback
        present = self.spin_present.value()
        absent = self.spin_absent.value()
        
        if hasattr(self, '_working_days'):
            total = present + absent
            if total > self._working_days:
                self.spin_absent.setStyleSheet("background-color: #ffcccc;")
            else:
                self.spin_absent.setStyleSheet("")

    def _update_calculated(self, payroll):
        """Update calculated display fields."""
        self.lbl_paid_days.setText(str(payroll.paid_days))
        self.lbl_gross.setText(f"₹{payroll.gross_earnings:,.2f}")
        self.lbl_deductions.setText(f"₹{payroll.total_deductions:,.2f}")
        self.lbl_net.setText(f"₹{payroll.net_salary:,.2f}")

    def _on_save(self):
        """Save attendance and recalculate."""
        db = get_db()
        with db.get_session() as session:
            repo = MonthlyPayrollRepository(session)
            payroll = repo.get_by_id(self.payroll_id)

            if not payroll:
                QMessageBox.critical(self, "Error", "Payroll record not found.")
                return

            # Update attendance
            payroll.present_days = self.spin_present.value()
            payroll.absent_days = self.spin_absent.value()
            payroll.late_marks = self.spin_late.value()

            # Update leaves
            payroll.privilege_leave = Decimal(str(self.spin_pl.value()))
            payroll.sick_leave = Decimal(str(self.spin_sl.value()))
            payroll.casual_leave = Decimal(str(self.spin_cl.value()))

            # Calculate paid days
            working_days = payroll.payroll_period.working_days
            total_leaves = payroll.privilege_leave + payroll.sick_leave + payroll.casual_leave
            payroll.paid_days = int(working_days - payroll.absent_days)

            # Update manual deductions
            payroll.professional_tax = Decimal(str(self.spin_pt.value()))
            payroll.loan_deduction = Decimal(str(self.spin_loan.value()))
            payroll.tds = Decimal(str(self.spin_tds.value()))
            payroll.other_deductions = Decimal(str(self.spin_other_ded.value()))

            session.commit()

            # Recalculate using service
            service = PayrollService(session)
            updated = service.recalculate_payroll(self.payroll_id)

            QMessageBox.information(
                self,
                "Saved",
                f"Attendance saved and salary recalculated.\n\n"
                f"Net Salary: ₹{updated.net_salary:,.2f}"
            )

        self.accept()
