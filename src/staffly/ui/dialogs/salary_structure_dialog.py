"""Salary structure add/edit dialog."""

from datetime import date
from decimal import Decimal
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
    QLabel,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QDoubleValidator

from staffly.database import get_db
from staffly.database.models import SalaryStructure
from staffly.database.repositories import SalaryStructureRepository
from staffly.ui.widgets.arrow_widgets import ArrowDateEdit, OptionalDateEdit
from staffly.services.calculation_service import CalculationService


class SalaryStructureDialog(QDialog):
    """
    Dialog for adding/editing salary structure.
    
    Features:
    - Enter Gross Salary → Auto-calculate all components
    - Manual override possible for each component
    
    Usage:
        # Add new
        dialog = SalaryStructureDialog(parent, employee_id=5)
        
        # Edit existing
        dialog = SalaryStructureDialog(parent, employee_id=5, structure_id=10)
    """

    def __init__(self, parent=None, employee_id: int = None, structure_id: int = None):
        super().__init__(parent)
        self.employee_id = employee_id
        self.structure_id = structure_id
        self.is_edit_mode = structure_id is not None
        self.calc_service = CalculationService()
        self._auto_calculating = False  # Flag to prevent recursion
        self._setup_ui()
        
        if self.is_edit_mode:
            self._load_structure()

    def _setup_ui(self):
        """Setup the dialog UI with 2-column horizontal layout."""
        self.setWindowTitle("Edit Salary Structure" if self.is_edit_mode else "Add Salary Structure")
        self.setMinimumWidth(750)

        main_layout = QVBoxLayout(self)

        # Validator for money fields
        money_validator = QDoubleValidator(0, 9999999.99, 2)

        # ═══════════════════════════════════════════════════════════════════
        # TWO COLUMN LAYOUT
        # ═══════════════════════════════════════════════════════════════════
        columns_layout = QHBoxLayout()

        # ═══════════════════════════════════════════════════════════════════
        # LEFT COLUMN - INPUTS
        # ═══════════════════════════════════════════════════════════════════
        left_column = QVBoxLayout()

        # EFFECTIVE DATES
        dates_group = QGroupBox("Effective Period")
        dates_layout = QFormLayout(dates_group)

        self.date_from = ArrowDateEdit()
        self.date_from.setDate(QDate.currentDate())
        self.date_from.setDisplayFormat("dd-MM-yyyy")
        self.date_from.setMinimumWidth(150)
        dates_layout.addRow("Effective From*:", self.date_from)

        self.date_to = OptionalDateEdit(label="Current (No End Date)")
        dates_layout.addRow("Effective To:", self.date_to)

        left_column.addWidget(dates_group)

        # GROSS SALARY INPUT
        gross_group = QGroupBox("💰 Gross Salary")
        gross_layout = QVBoxLayout(gross_group)
        
        gross_input_layout = QHBoxLayout()
        self.txt_gross = QLineEdit("0.00")
        self.txt_gross.setValidator(money_validator)
        self.txt_gross.setStyleSheet("""
            QLineEdit {
                font-size: 18px;
                font-weight: bold;
                padding: 8px;
                border: 2px solid #4CAF50;
                border-radius: 4px;
                background-color: #E8F5E9;
            }
        """)
        
        self.btn_calculate = QPushButton("🧮 Calculate")
        self.btn_calculate.setFixedSize(100, 40)
        self.btn_calculate.setStyleSheet("""
            QPushButton {
                font-size: 13px;
                font-weight: bold;
                background-color: #4CAF50;
                color: white;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.btn_calculate.clicked.connect(self._on_calculate_clicked)
        
        gross_input_layout.addWidget(self.txt_gross)
        gross_input_layout.addWidget(self.btn_calculate)
        gross_layout.addLayout(gross_input_layout)
        
        left_column.addWidget(gross_group)

        # STATUTORY APPLICABILITY
        stat_group = QGroupBox("Statutory Applicability")
        stat_layout = QVBoxLayout(stat_group)

        self.chk_pf = QCheckBox("Provident Fund (PF)")
        self.chk_pf.setChecked(True)
        self.chk_pf.stateChanged.connect(self._on_pf_changed)
        stat_layout.addWidget(self.chk_pf)

        # Note: ESI is auto-calculated based on gross salary (if Gross*50% < 21000)
        # Professional Tax is mandatory and calculated based on gender and gross

        left_column.addWidget(stat_group)

        # NOTES
        notes_group = QGroupBox("Notes")
        notes_layout = QFormLayout(notes_group)
        self.txt_notes = QLineEdit()
        self.txt_notes.setPlaceholderText("e.g., Post appraisal 2025")
        notes_layout.addRow("Notes:", self.txt_notes)
        left_column.addWidget(notes_group)

        left_column.addStretch()

        # ═══════════════════════════════════════════════════════════════════
        # RIGHT COLUMN - CALCULATED COMPONENTS (Read-only)
        # ═══════════════════════════════════════════════════════════════════
        right_column = QVBoxLayout()

        salary_group = QGroupBox("📊 Salary Breakdown (Auto-Calculated)")
        salary_layout = QFormLayout(salary_group)

        component_style = """
            QLineEdit {
                padding: 6px;
                border: 1px solid #ccc;
                border-radius: 3px;
                background-color: #f5f5f5;
                color: #333;
                font-size: 14px;
            }
        """

        self.txt_basic = QLineEdit("0.00")
        self.txt_basic.setReadOnly(True)
        self.txt_basic.setStyleSheet(component_style)
        salary_layout.addRow("Basic Salary:", self.txt_basic)

        self.txt_hra = QLineEdit("0.00")
        self.txt_hra.setReadOnly(True)
        self.txt_hra.setStyleSheet(component_style)
        salary_layout.addRow("HRA:", self.txt_hra)

        self.txt_bonus = QLineEdit("0.00")
        self.txt_bonus.setReadOnly(True)
        self.txt_bonus.setStyleSheet(component_style)
        salary_layout.addRow("Bonus:", self.txt_bonus)

        self.txt_cca = QLineEdit("0.00")
        self.txt_cca.setReadOnly(True)
        self.txt_cca.setStyleSheet(component_style)
        salary_layout.addRow("CCA:", self.txt_cca)

        self.txt_other = QLineEdit("0.00")
        self.txt_other.setReadOnly(True)
        self.txt_other.setStyleSheet(component_style)
        salary_layout.addRow("Other Allowance:", self.txt_other)

        # Separator
        separator = QLabel("─" * 30)
        separator.setStyleSheet("color: #ccc;")
        salary_layout.addRow(separator)

        # PF & ESI info - with proper left alignment
        self.lbl_pf_info = QLabel("PF (Employer): ₹0.00")
        self.lbl_pf_info.setStyleSheet("color: #666; font-size: 13px;")
        salary_layout.addRow("PF (Employer):", self.lbl_pf_info)

        self.lbl_esi_info = QLabel("₹0.00")
        self.lbl_esi_info.setStyleSheet("color: #666; font-size: 13px;")
        salary_layout.addRow("ESIC (Employee):", self.lbl_esi_info)

        # Total (saved gross includes PF employer)
        self.lbl_calculated_gross = QLabel("₹0.00")
        self.lbl_calculated_gross.setStyleSheet("font-weight: bold; font-size: 14px; color: #4CAF50;")
        salary_layout.addRow("Components Sum:", self.lbl_calculated_gross)

        right_column.addWidget(salary_group)
        right_column.addStretch()

        # Add columns to layout
        columns_layout.addLayout(left_column)
        columns_layout.addLayout(right_column)

        main_layout.addLayout(columns_layout)

        # ═══════════════════════════════════════════════════════════════════
        # BUTTONS
        # ═══════════════════════════════════════════════════════════════════
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

        self.btn_save = QPushButton("💾 Save")
        self.btn_save.setFixedSize(120, 45)
        self.btn_save.setStyleSheet(btn_style + """
            QPushButton { background-color: #4CAF50; color: white; }
            QPushButton:hover { background-color: #45a049; }
        """)
        self.btn_save.clicked.connect(self._on_save)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setFixedSize(120, 45)
        self.btn_cancel.setStyleSheet(btn_style + """
            QPushButton { background-color: #9e9e9e; color: white; }
            QPushButton:hover { background-color: #757575; }
        """)
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)

        main_layout.addLayout(btn_layout)

    def _get_decimal(self, text: str) -> Decimal:
        """Convert text to Decimal safely."""
        try:
            return Decimal(text or "0")
        except:
            return Decimal("0")

    def _on_pf_changed(self, state):
        """Called when PF checkbox changes."""
        # Recalculate if gross is entered
        gross = self._get_decimal(self.txt_gross.text())
        if gross > 0:
            self._on_calculate_clicked()

    def _on_calculate_clicked(self):
        """Calculate all components from gross salary."""
        if self._auto_calculating:
            return
            
        self._auto_calculating = True
        try:
            gross = self._get_decimal(self.txt_gross.text())
            pf_applicable = self.chk_pf.isChecked()
            
            if gross <= 0:
                QMessageBox.warning(self, "Input Required", "Please enter a Gross Salary greater than 0.")
                return
            
            # Calculate all components
            result = self.calc_service.calculate_salary_structure_from_gross(gross, pf_applicable)
            
            # Update fields
            self.txt_basic.setText(f"{result['basic_salary']:.2f}")
            self.txt_hra.setText(f"{result['hra']:.2f}")
            self.txt_bonus.setText(f"{result['bonus']:.2f}")
            self.txt_cca.setText(f"{result['cca']:.2f}")
            self.txt_other.setText(f"{result['other_allowance']:.2f}")
            
            # Update info labels
            self.lbl_pf_info.setText(f"₹{result['pf_employer']:,.2f}")
            self.lbl_esi_info.setText(f"₹{result['esi_employee']:,.2f}")
            
            # Update sum display
            self._update_sum_display()
            
        finally:
            self._auto_calculating = False

    def _update_sum_display(self):
        """Update the calculated gross display."""
        # Extract PF Employer value from label (format: "₹X,XXX.XX")
        pf_employer = Decimal("0")
        pf_text = self.lbl_pf_info.text()
        if pf_text.startswith("₹"):
            try:
                pf_employer = Decimal(pf_text[1:].replace(",", ""))
            except:
                pf_employer = Decimal("0")
        
        # Saved gross includes PF Employer
        saved_gross_sum = (
            self._get_decimal(self.txt_basic.text()) +
            self._get_decimal(self.txt_hra.text()) +
            self._get_decimal(self.txt_bonus.text()) +
            self._get_decimal(self.txt_cca.text()) +
            self._get_decimal(self.txt_other.text()) +
            pf_employer
        )
        gross = self._get_decimal(self.txt_gross.text())
        
        if gross > 0 and abs(saved_gross_sum - gross) > Decimal("1"):
            # Mismatch - show in red
            self.lbl_calculated_gross.setText(f"₹{saved_gross_sum:,.2f} ⚠️ (≠ Gross)")
            self.lbl_calculated_gross.setStyleSheet("font-weight: bold; font-size: 14px; color: #F44336;")
        else:
            self.lbl_calculated_gross.setText(f"₹{saved_gross_sum:,.2f}")
            self.lbl_calculated_gross.setStyleSheet("font-weight: bold; font-size: 14px; color: #4CAF50;")

    def _load_structure(self):
        """Load salary structure data into form."""
        db = get_db()
        with db.get_session() as session:
            repo = SalaryStructureRepository(session)
            struct = repo.get_by_id(self.structure_id)

            if struct:
                self.date_from.setDate(QDate(
                    struct.effective_from.year,
                    struct.effective_from.month,
                    struct.effective_from.day
                ))

                if struct.effective_to:
                    self.date_to.setDate(QDate(
                        struct.effective_to.year,
                        struct.effective_to.month,
                        struct.effective_to.day
                    ))
                else:
                    self.date_to.setNoDate(True)

                # Set component values first
                self._auto_calculating = True
                self.txt_basic.setText(str(struct.basic_salary))
                self.txt_hra.setText(str(struct.hra))
                self.txt_bonus.setText(str(struct.bonus))
                self.txt_cca.setText(str(struct.cca))
                self.txt_other.setText(str(struct.other_allowance))
                self.lbl_pf_info.setText(f"₹{struct.pf_employer:,.2f}")
                self._auto_calculating = False

                # Calculate and set gross (includes PF employer)
                gross = struct.gross_salary
                self.txt_gross.setText(f"{gross:.2f}")

                self.chk_pf.setChecked(struct.pf_applicable)

                self.txt_notes.setText(struct.notes or "")

                self._update_sum_display()

    def _validate(self) -> bool:
        """Validate form data."""
        basic = self._get_decimal(self.txt_basic.text())
        if basic <= 0:
            QMessageBox.warning(self, "Validation", "Basic Salary must be greater than 0.\nPlease enter Gross Salary and click Calculate.")
            self.txt_gross.setFocus()
            return False

        return True

    def _on_save(self):
        """Save salary structure."""
        if not self._validate():
            return

        db = get_db()
        with db.get_session() as session:
            repo = SalaryStructureRepository(session)

            if self.is_edit_mode:
                struct = repo.get_by_id(self.structure_id)
            else:
                struct = SalaryStructure()
                struct.employee_id = self.employee_id

            # Set values
            qdate = self.date_from.date()
            struct.effective_from = date(qdate.year(), qdate.month(), qdate.day())

            # Handle optional end date
            qdate_to = self.date_to.date()
            if qdate_to is not None:
                struct.effective_to = date(qdate_to.year(), qdate_to.month(), qdate_to.day())
            else:
                struct.effective_to = None

            struct.basic_salary = self._get_decimal(self.txt_basic.text())
            struct.hra = self._get_decimal(self.txt_hra.text())
            struct.bonus = self._get_decimal(self.txt_bonus.text())
            struct.cca = self._get_decimal(self.txt_cca.text())
            struct.other_allowance = self._get_decimal(self.txt_other.text())

            # Recalculate from CTC at save time (single source of truth)
            ctc = self._get_decimal(self.txt_gross.text())
            result = self.calc_service.calculate_salary_structure_from_gross(
                ctc,
                self.chk_pf.isChecked(),
            )
            struct.basic_salary = result["basic_salary"]
            struct.hra = result["hra"]
            struct.bonus = result["bonus"]
            struct.cca = result["cca"]
            struct.other_allowance = result["other_allowance"]
            struct.pf_employer = result["pf_employer"]

            struct.pf_applicable = self.chk_pf.isChecked()
            # ESI is auto-calculated based on gross salary
            # PT is mandatory for all employees
            struct.esi_applicable = True  # Will be checked against gross during payroll
            struct.pt_applicable = True   # Always applicable

            struct.notes = self.txt_notes.text().strip() or None

            if not self.is_edit_mode:
                # Close any current structure
                repo.close_current_structure(
                    self.employee_id,
                    struct.effective_from
                )
                repo.create(struct)

            repo.commit()

        self.accept()
