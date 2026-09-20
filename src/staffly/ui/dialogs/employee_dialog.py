"""Employee add/edit dialog."""

from datetime import date
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QCheckBox,
    QPushButton,
    QMessageBox,
    QGroupBox,
    QTabWidget,
    QWidget,
    QComboBox,
)
from PySide6.QtCore import Qt, QDate

from staffly.database import get_db
from staffly.database.models import Employee
from staffly.database.repositories import EmployeeRepository, CompanyRepository
from staffly.ui.widgets.arrow_widgets import ArrowDateEdit, OptionalDateEdit


class EmployeeDialog(QDialog):
    """
    Dialog for adding/editing employee.

    Usage:
        # Add new
        dialog = EmployeeDialog(parent)

        # Edit existing
        dialog = EmployeeDialog(parent, employee_id=5)
    """

    def __init__(
        self,
        parent=None,
        employee_id: int = None,
        fixed_company_id: int | None = None,
        fixed_company_name: str | None = None,
    ):
        super().__init__(parent)
        self.employee_id = employee_id
        self.is_edit_mode = employee_id is not None
        self.fixed_company_id = fixed_company_id
        self.fixed_company_name = fixed_company_name
        self._setup_ui()

        if self.is_edit_mode:
            self._load_employee()

    def _setup_ui(self):
        """Setup the dialog UI."""
        self.setWindowTitle("Edit Employee" if self.is_edit_mode else "Add Employee")
        self.setMinimumSize(700, 600)
        self.resize(750, 650)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Tab widget for organized form
        tab_widget = QTabWidget()

        # ═══════════════════════════════════════════════════════════════════
        # TAB 1: Basic Info
        # ═══════════════════════════════════════════════════════════════════
        basic_tab = QWidget()
        basic_layout = QFormLayout(basic_tab)

        # Company selector (required)
        self.cmb_company = QComboBox()
        if self.fixed_company_id:
            display_name = self.fixed_company_name or "Selected Company"
            self.cmb_company.addItem(display_name, self.fixed_company_id)
            self.cmb_company.setEnabled(False)
        else:
            self.cmb_company.addItem("-- Select Company --", None)
            self._load_companies()
        basic_layout.addRow("Company*:", self.cmb_company)

        self.txt_code = QLineEdit()
        self.txt_code.setPlaceholderText("e.g., EMP001")
        self.txt_code.setMaxLength(20)
        basic_layout.addRow("Employee Code*:", self.txt_code)

        self.txt_first_name = QLineEdit()
        self.txt_first_name.setMaxLength(50)
        basic_layout.addRow("First Name*:", self.txt_first_name)

        self.txt_middle_name = QLineEdit()
        self.txt_middle_name.setMaxLength(50)
        basic_layout.addRow("Middle Name:", self.txt_middle_name)

        self.txt_last_name = QLineEdit()
        self.txt_last_name.setMaxLength(50)
        basic_layout.addRow("Last Name*:", self.txt_last_name)

        # Gender dropdown
        self.cmb_gender = QComboBox()
        self.cmb_gender.addItem("-- Select Gender --", None)
        self.cmb_gender.addItem("Male", "Male")
        self.cmb_gender.addItem("Female", "Female")
        self.cmb_gender.addItem("Other", "Other")
        basic_layout.addRow("Gender*:", self.cmb_gender)

        self.txt_designation = QLineEdit()
        self.txt_designation.setMaxLength(100)
        basic_layout.addRow("Designation*:", self.txt_designation)

        self.txt_department = QLineEdit()
        self.txt_department.setMaxLength(100)
        basic_layout.addRow("Department*:", self.txt_department)

        self.txt_branch = QLineEdit()
        self.txt_branch.setMaxLength(100)
        self.txt_branch.setPlaceholderText("e.g., Head Office, Mumbai Branch")
        basic_layout.addRow("Branch*:", self.txt_branch)

        tab_widget.addTab(basic_tab, "Basic Info")

        # ═══════════════════════════════════════════════════════════════════
        # TAB 2: Employment
        # ═══════════════════════════════════════════════════════════════════
        emp_tab = QWidget()
        emp_layout = QFormLayout(emp_tab)

        self.date_joining = ArrowDateEdit()
        self.date_joining.setDate(QDate.currentDate())
        self.date_joining.setDisplayFormat("dd-MM-yyyy")
        self.date_joining.setMinimumWidth(180)
        emp_layout.addRow("Date of Joining*:", self.date_joining)

        # Optional date with checkbox for "Not Set"
        self.date_leaving = OptionalDateEdit(label="Still Employed (No Leave Date)")
        emp_layout.addRow("Date of Leaving:", self.date_leaving)

        self.chk_active = QCheckBox("Employee is active")
        self.chk_active.setChecked(True)
        emp_layout.addRow("Status:", self.chk_active)

        # Probation fields
        self.chk_probation = QCheckBox("Employee is on probation")
        self.chk_probation.setChecked(False)
        self.chk_probation.toggled.connect(self._on_probation_toggled)
        emp_layout.addRow("Probation:", self.chk_probation)

        self.date_probation_end = ArrowDateEdit()
        self.date_probation_end.setDisplayFormat("dd-MM-yyyy")
        self.date_probation_end.setEnabled(False)
        emp_layout.addRow("Probation End Date:", self.date_probation_end)

        self.btn_end_probation = QPushButton("🎓 End Probation & Update Salary")
        self.btn_end_probation.setStyleSheet("background-color: #9C27B0; color: white; font-weight: bold; padding: 6px; border-radius: 4px;")
        self.btn_end_probation.setVisible(False)
        self.btn_end_probation.clicked.connect(self._on_end_probation)
        emp_layout.addRow("", self.btn_end_probation)

        # Auto-calculate probation end date on joining date change
        self.date_joining.dateChanged.connect(self._auto_set_probation_end)

        tab_widget.addTab(emp_tab, "Employment")

        # ═══════════════════════════════════════════════════════════════════
        # TAB 3: Contact
        # ═══════════════════════════════════════════════════════════════════
        contact_tab = QWidget()
        contact_layout = QFormLayout(contact_tab)

        self.txt_email = QLineEdit()
        self.txt_email.setPlaceholderText("email@example.com")
        contact_layout.addRow("Email:", self.txt_email)

        self.txt_phone = QLineEdit()
        self.txt_phone.setPlaceholderText("+91 XXXXX XXXXX")
        contact_layout.addRow("Phone:", self.txt_phone)

        self.txt_address = QLineEdit()
        contact_layout.addRow("Address:", self.txt_address)

        tab_widget.addTab(contact_tab, "Contact")

        # ═══════════════════════════════════════════════════════════════════
        # TAB 4: Statutory
        # ═══════════════════════════════════════════════════════════════════
        stat_tab = QWidget()
        stat_layout = QFormLayout(stat_tab)

        self.txt_aadhar = QLineEdit()
        self.txt_aadhar.setPlaceholderText("12 digit Aadhar number")
        self.txt_aadhar.setMaxLength(12)
        stat_layout.addRow("Aadhar Number:", self.txt_aadhar)

        self.txt_pan = QLineEdit()
        self.txt_pan.setPlaceholderText("ABCDE1234F")
        self.txt_pan.setMaxLength(10)
        stat_layout.addRow("PAN Number:", self.txt_pan)

        self.txt_uan = QLineEdit()
        self.txt_uan.setPlaceholderText("Enter UAN or NA if PF not applicable")
        stat_layout.addRow("UAN (PF)*:", self.txt_uan)

        self.txt_esi = QLineEdit()
        self.txt_esi.setPlaceholderText("Enter ESI number or NA if ESIC not applicable")
        stat_layout.addRow("ESI Number*:", self.txt_esi)

        tab_widget.addTab(stat_tab, "Statutory")

        layout.addWidget(tab_widget)

        # ═══════════════════════════════════════════════════════════════════
        # BUTTONS - styled via global QSS
        # ═══════════════════════════════════════════════════════════════════
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.btn_save = QPushButton("Save Employee")
        self.btn_save.setObjectName("primaryButton")
        self.btn_save.setFixedHeight(44)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.clicked.connect(self._on_save)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("secondaryButton")
        self.btn_cancel.setFixedHeight(44)
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

    def _load_companies(self):
        """Load companies into the dropdown."""
        db = get_db()
        with db.get_session() as session:
            repo = CompanyRepository(session)
            companies = repo.get_all_active()
            for company in companies:
                self.cmb_company.addItem(company.name, company.id)

    def _on_probation_toggled(self, checked: bool):
        """Toggle probation end date field based on checkbox."""
        self.date_probation_end.setEnabled(checked)
        if checked and self.date_probation_end.date() <= self.date_joining.date():
            self._auto_set_probation_end(self.date_joining.date())

    def _auto_set_probation_end(self, joining_date: QDate):
        """Automatically set probation end date to 6 months after joining."""
        if self.chk_probation.isChecked():
            self.date_probation_end.setDate(joining_date.addMonths(6))

    def _on_end_probation(self):
        """Handle manual early end of probation."""
        if not self._validate():
            return

        reply = QMessageBox.question(
            self, "End Probation",
            "Are you sure you want to end this employee's probation now?\n\n"
            "This will uncheck the probation status, save the employee, and prompt you to create a new confirmation salary structure.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            # CAPTURE THE DATE BEFORE SAVING/CLOSING
            probation_end = self.date_probation_end.date()

            # Snap to the 1st of the NEXT month
            target_effective_date = QDate(probation_end.year(), probation_end.month(), 1).addMonths(1)

            self.chk_probation.setChecked(False)
            self._on_save()

            from staffly.ui.dialogs.salary_structure_dialog import SalaryStructureDialog
            sal_dialog = SalaryStructureDialog(self.parentWidget(), employee_id=self.employee_id)

            # Inject the calculated start date (User can still edit it manually in the UI)
            sal_dialog.date_from.setDate(target_effective_date)

            sal_dialog.exec()

    def _load_employee(self):
        """Load employee data into form."""
        db = get_db()
        with db.get_session() as session:
            repo = EmployeeRepository(session)
            emp = repo.get_by_id(self.employee_id)

            if emp:
                # Set company
                company_idx = self.cmb_company.findData(emp.company_id)
                if company_idx >= 0:
                    self.cmb_company.setCurrentIndex(company_idx)

                self.txt_code.setText(emp.employee_code)
                self.txt_first_name.setText(emp.first_name)
                self.txt_middle_name.setText(emp.middle_name or "")
                self.txt_last_name.setText(emp.last_name)

                # Set gender
                gender_idx = self.cmb_gender.findData(emp.gender)
                if gender_idx >= 0:
                    self.cmb_gender.setCurrentIndex(gender_idx)

                self.txt_designation.setText(emp.designation)
                self.txt_department.setText(emp.department or "")
                self.txt_branch.setText(emp.branch or "")
                self.txt_email.setText(emp.email or "")
                self.txt_phone.setText(emp.phone or "")
                self.txt_address.setText(emp.address or "")
                self.txt_aadhar.setText(emp.aadhar_number or "")
                self.txt_pan.setText(emp.pan_number or "")
                self.txt_uan.setText(emp.uan_number or "")
                self.txt_esi.setText(emp.esi_number or "")
                self.chk_active.setChecked(emp.is_active)

                self.chk_probation.setChecked(emp.is_on_probation)
                if emp.probation_end_date:
                    self.date_probation_end.setDate(QDate(
                        emp.probation_end_date.year,
                        emp.probation_end_date.month,
                        emp.probation_end_date.day
                    ))

                # Show End Probation button if in edit mode and currently on probation
                if self.is_edit_mode and emp.is_on_probation:
                    self.btn_end_probation.setVisible(True)

                self.date_joining.setDate(QDate(
                    emp.date_of_joining.year,
                    emp.date_of_joining.month,
                    emp.date_of_joining.day
                ))

                if emp.date_of_leaving:
                    self.date_leaving.setDate(QDate(
                        emp.date_of_leaving.year,
                        emp.date_of_leaving.month,
                        emp.date_of_leaving.day
                    ))
                else:
                    self.date_leaving.setNoDate(True)

    def _validate(self) -> bool:
        """Validate form data."""
        if not self.cmb_company.currentData():
            QMessageBox.warning(self, "Validation", "Please select a Company.")
            self.cmb_company.setFocus()
            return False

        if not self.txt_code.text().strip():
            QMessageBox.warning(self, "Validation", "Employee Code is required.")
            self.txt_code.setFocus()
            return False

        if not self.txt_first_name.text().strip():
            QMessageBox.warning(self, "Validation", "First Name is required.")
            self.txt_first_name.setFocus()
            return False

        if not self.txt_last_name.text().strip():
            QMessageBox.warning(self, "Validation", "Last Name is required.")
            self.txt_last_name.setFocus()
            return False

        if not self.txt_designation.text().strip():
            QMessageBox.warning(self, "Validation", "Designation is required.")
            self.txt_designation.setFocus()
            return False

        if not self.cmb_gender.currentData():
            QMessageBox.warning(self, "Validation", "Gender is required.")
            self.cmb_gender.setFocus()
            return False

        if not self.txt_department.text().strip():
            QMessageBox.warning(self, "Validation", "Department is required.")
            self.txt_department.setFocus()
            return False

        if not self.txt_branch.text().strip():
            QMessageBox.warning(self, "Validation", "Branch is required.")
            self.txt_branch.setFocus()
            return False

        if not self.txt_uan.text().strip():
            QMessageBox.warning(self, "Validation", "UAN (PF) is required. Enter 'NA' if PF is not applicable.")
            self.txt_uan.setFocus()
            return False

        if not self.txt_esi.text().strip():
            QMessageBox.warning(self, "Validation", "ESI Number is required. Enter 'NA' if ESIC is not applicable.")
            self.txt_esi.setFocus()
            return False

        return True

    def _on_save(self):
        """Save employee data."""
        if not self._validate():
            return

        db = get_db()
        with db.get_session() as session:
            repo = EmployeeRepository(session)

            # Check for duplicate code (if new or code changed)
            code = self.txt_code.text().strip().upper()
            existing = repo.get_by_code(code)
            if existing and (not self.is_edit_mode or existing.id != self.employee_id):
                QMessageBox.warning(self, "Duplicate", f"Employee code '{code}' already exists.")
                return

            if self.is_edit_mode:
                emp = repo.get_by_id(self.employee_id)
            else:
                emp = Employee()

            # Set values
            emp.company_id = self.cmb_company.currentData()
            emp.employee_code = code
            emp.first_name = self.txt_first_name.text().strip()
            emp.middle_name = self.txt_middle_name.text().strip() or None
            emp.last_name = self.txt_last_name.text().strip()
            emp.gender = self.cmb_gender.currentData()
            emp.designation = self.txt_designation.text().strip()
            emp.department = self.txt_department.text().strip() or None
            emp.branch = self.txt_branch.text().strip() or None
            emp.email = self.txt_email.text().strip() or None
            emp.phone = self.txt_phone.text().strip() or None
            emp.address = self.txt_address.text().strip() or None
            emp.aadhar_number = self.txt_aadhar.text().strip() or None
            emp.pan_number = self.txt_pan.text().strip().upper() or None
            uan_text = self.txt_uan.text().strip()
            esi_text = self.txt_esi.text().strip()
            emp.uan_number = "NA" if uan_text.upper() == "NA" else uan_text
            emp.esi_number = "NA" if esi_text.upper() == "NA" else esi_text
            emp.is_active = self.chk_active.isChecked()

            emp.is_on_probation = self.chk_probation.isChecked()
            if self.chk_probation.isChecked():
                qdate_prob = self.date_probation_end.date()
                emp.probation_end_date = date(qdate_prob.year(), qdate_prob.month(), qdate_prob.day())
            else:
                emp.probation_end_date = None

            # Dates
            qdate = self.date_joining.date()
            emp.date_of_joining = date(qdate.year(), qdate.month(), qdate.day())

            # Handle optional leaving date
            qdate_leave = self.date_leaving.date()
            if qdate_leave is not None:
                emp.date_of_leaving = date(qdate_leave.year(), qdate_leave.month(), qdate_leave.day())
            else:
                emp.date_of_leaving = None

            if not self.is_edit_mode:
                repo.create(emp)

            repo.commit()

        self.accept()
