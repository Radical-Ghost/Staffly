"""Payroll service for payroll generation and management."""

from decimal import Decimal
from typing import List, Optional
from datetime import date

from sqlalchemy.orm import Session

from staffly.database.models.monthly_payroll import MonthlyPayroll
from staffly.database.models.payroll_period import PayrollPeriod
from staffly.database.repositories import (
    EmployeeRepository,
    SalaryStructureRepository,
    PayrollPeriodRepository,
    MonthlyPayrollRepository,
)
from .calculation_service import CalculationService


def _to_decimal(value: Optional[Decimal]) -> Decimal:
    """Convert value to Decimal, treating None as 0."""
    if value is None:
        return Decimal("0.00")
    return value


class PayrollService:
    """
    Service for payroll operations.
    
    Handles:
    - Automatic payroll generation for a period
    - Copying data from previous month
    - Recalculating payroll after attendance edits
    """

    def __init__(self, session: Session):
        self.session = session
        self.employee_repo = EmployeeRepository(session)
        self.salary_repo = SalaryStructureRepository(session)
        self.period_repo = PayrollPeriodRepository(session)
        self.payroll_repo = MonthlyPayrollRepository(session)
        self.calc_service = CalculationService()

    def generate_payroll_for_period(
        self,
        payroll_period: PayrollPeriod,
        copy_from_previous: bool = True,
        company_id: int | None = None,
    ) -> int:
        """
        Automatically generate monthly payroll records for all eligible employees.
        
        Rules:
        1. Only includes employees active on the period's start date
        2. Skips employees who have left before the period
        3. Copies attendance from previous month if exists
        4. User can then edit attendance and recalculate
        
        Args:
            payroll_period: The period to generate payroll for
            copy_from_previous: Whether to copy attendance from previous month
            company_id: Optional company scope for generation
        
        Returns:
            Number of payroll records created
        """
        # Check if payroll already exists for this period
        if company_id is not None and self.payroll_repo.exists_for_period_and_company(payroll_period.id, company_id):
            raise ValueError(
                f"Payroll already exists for {payroll_period.period_label} ({company_id}). "
                "Delete existing records first."
            )
        if company_id is None and self.payroll_repo.exists_for_period(payroll_period.id):
            raise ValueError(
                f"Payroll already exists for {payroll_period.period_label}. "
                "Delete existing records first."
            )

        # Get all employees active on period start date
        period_start = payroll_period.start_date
        if company_id is not None:
            active_employees = self.employee_repo.get_active_on_date_by_company(period_start, company_id)
        else:
            active_employees = self.employee_repo.get_active_on_date(period_start)

        created_count = 0

        for employee in active_employees:
            # Get active salary structure for this period
            salary_structure = self.salary_repo.get_active_for_employee(
                employee.id, period_start
            )

            if not salary_structure:
                # Skip employees without salary structure
                print(f"Warning: No salary structure for {employee.full_name}, skipping")
                continue

            # Create base payroll record
            payroll = MonthlyPayroll(
                employee_id=employee.id,
                payroll_period_id=payroll_period.id,
            )

            # Copy salary components from salary_structure (snapshot)
            payroll.basic_salary = _to_decimal(salary_structure.basic_salary)
            payroll.hra = _to_decimal(salary_structure.hra)
            payroll.bonus = _to_decimal(salary_structure.bonus)
            payroll.cca = _to_decimal(salary_structure.cca)
            payroll.other_allowance = _to_decimal(salary_structure.other_allowance)

            # Copy attendance from previous month if requested
            if copy_from_previous:
                prev_payroll = self.payroll_repo.get_previous_month_payroll(
                    employee.id, payroll_period.id
                )
                if prev_payroll:
                    payroll.present_days = prev_payroll.present_days
                    payroll.paid_days = prev_payroll.paid_days
                    payroll.absent_days = prev_payroll.absent_days
                    payroll.late_marks = prev_payroll.late_marks
                    payroll.privilege_leave = prev_payroll.privilege_leave
                    payroll.sick_leave = prev_payroll.sick_leave
                    payroll.casual_leave = prev_payroll.casual_leave
                else:
                    # No previous month, set defaults
                    payroll.paid_days = payroll_period.working_days
                    payroll.present_days = payroll_period.working_days
            else:
                # Set defaults
                payroll.paid_days = payroll_period.working_days
                payroll.present_days = payroll_period.working_days

            # Calculate salary based on attendance
            self._calculate_payroll(
                payroll,
                salary_structure.pf_applicable,
                _to_decimal(salary_structure.basic_salary),
                _to_decimal(salary_structure.hra),
                _to_decimal(salary_structure.bonus),
                _to_decimal(salary_structure.cca),
                _to_decimal(salary_structure.other_allowance),
                _to_decimal(salary_structure.pf_employer),
                employee.gender,
                payroll_period.working_days,
            )

            # Save
            self.payroll_repo.create(payroll)
            created_count += 1

        # Commit all at once
        self.session.commit()

        return created_count

    def recalculate_payroll(self, payroll_id: int) -> MonthlyPayroll:
        """
        Recalculate payroll after user edits attendance.
        
        Args:
            payroll_id: The payroll record to recalculate
        
        Returns:
            Updated payroll record
        """
        payroll = self.payroll_repo.get_by_id(payroll_id)
        if not payroll:
            raise ValueError(f"Payroll record {payroll_id} not found")

        # Get salary structure and employee to check PF applicability and gender
        salary_structure = self.salary_repo.get_active_for_employee(
            payroll.employee_id,
            payroll.payroll_period.start_date
        )

        if not salary_structure:
            raise ValueError(f"No salary structure found for employee")

        # Get employee for gender
        employee = self.employee_repo.get_by_id(payroll.employee_id)

        # Recalculate
        self._calculate_payroll(
            payroll,
            salary_structure.pf_applicable,
            _to_decimal(salary_structure.basic_salary),
            _to_decimal(salary_structure.hra),
            _to_decimal(salary_structure.bonus),
            _to_decimal(salary_structure.cca),
            _to_decimal(salary_structure.other_allowance),
            _to_decimal(salary_structure.pf_employer),
            employee.gender if employee else None,
            payroll.payroll_period.working_days,
        )

        self.session.commit()
        return payroll

    def _calculate_payroll(
        self,
        payroll: MonthlyPayroll,
        pf_applicable: bool,
        basic_monthly: Decimal,
        hra_monthly: Decimal,
        bonus_monthly: Decimal,
        cca_monthly: Decimal,
        other_allowance_monthly: Decimal,
        pf_employer_monthly: Decimal,
        gender: str | None,
        working_days: int,
    ) -> None:
        """
        Internal method to calculate payroll values.
        
        Updates the payroll object in place.
        ESI is auto-calculated based on gross salary.
        Professional Tax is auto-calculated based on gender and gross.
        """
        result = self.calc_service.calculate_complete_payroll(
            basic=basic_monthly,
            hra=hra_monthly,
            bonus=bonus_monthly,
            cca=cca_monthly,
            other_allowance=other_allowance_monthly,
            paid_days=payroll.paid_days,
            total_working_days=working_days,
            pf_applicable=pf_applicable,
            pf_employer_monthly=pf_employer_monthly,
            gender=gender,
            loan_deduction=payroll.loan_deduction,
            tds=payroll.tds,
            other_deductions=payroll.other_deductions,
        )

        # Update payroll with calculated values
        payroll.basic_salary = result["basic_salary"]
        payroll.hra = result["hra"]
        payroll.bonus = result["bonus"]
        payroll.cca = result["cca"]
        payroll.other_allowance = result["other_allowance"]
        payroll.gross_earnings = result["gross_earnings"]
        payroll.pf_employee = result["pf_employee"]
        payroll.pf_employer = result["pf_employer"]
        payroll.esi_employee = result["esi_employee"]
        payroll.esi_employer = result["esi_employer"]
        payroll.professional_tax = result["professional_tax"]
        payroll.total_deductions = result["total_deductions"]
        payroll.net_salary = result["net_salary"]
        payroll.ctc_monthly = result["ctc_monthly"]

    def finalize_period(self, payroll_period_id: int, company_id: int) -> bool:
        """
        Finalize is currently disabled while lock feature is turned off.
        """
        _ = payroll_period_id
        _ = company_id
        return True
