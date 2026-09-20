"""Payroll service for payroll generation and management."""

from decimal import Decimal, ROUND_HALF_UP
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
    LeaveBalanceRepository,
)
from .calculation_service import CalculationService


def _to_decimal(value: Optional[Decimal]) -> Decimal:
    """Convert value to Decimal, treating None as 0."""
    if value is None:
        return Decimal("0.00")
    return value


def get_financial_year(year: int, month: int) -> int:
    """
    Return the financial-year start year for a given calendar month.
    Financial year runs April to March.
    April 2025 → FY 2025;  March 2026 → FY 2025.
    """
    if month >= 4:
        return year
    return year - 1


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
        self.leave_repo = LeaveBalanceRepository(session)
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
            # NOTE: Do NOT copy leaves, absents, late marks, TDS, or loans.
            # Only copy present_days and paid_days as defaults.
            if copy_from_previous:
                prev_payroll = self.payroll_repo.get_previous_month_payroll(
                    employee.id, payroll_period.id
                )
                if prev_payroll:
                    # Copy only paid/present days as starting defaults
                    payroll.paid_days = payroll_period.working_days
                    payroll.present_days = payroll_period.working_days
                else:
                    payroll.paid_days = payroll_period.working_days
                    payroll.present_days = payroll_period.working_days
            else:
                payroll.paid_days = payroll_period.working_days
                payroll.present_days = payroll_period.working_days

            # Leaves, absent, late marks, TDS, loans all start at 0 for new month

            # Calculate salary based on attendance
            self._calculate_payroll(
                payroll,
                salary_structure.pf_applicable,
                salary_structure.esi_applicable,
                _to_decimal(salary_structure.basic_salary),
                _to_decimal(salary_structure.hra),
                _to_decimal(salary_structure.bonus),
                _to_decimal(salary_structure.cca),
                _to_decimal(salary_structure.other_allowance),
                _to_decimal(salary_structure.pf_employer),
                employee.gender,
                payroll_period.working_days,
            )

            # Calculate arrears if salary structure changed this month
            payroll.arrears = self._calculate_arrears(
                employee.id, payroll_period, salary_structure
            )

            # Ensure leave balance record exists for this FY
            fy = get_financial_year(payroll_period.year, payroll_period.month)
            self.leave_repo.get_or_create_for_employee_fy(employee.id, fy)

            # Save
            self.payroll_repo.create(payroll)
            created_count += 1

        # Commit all at once
        self.session.commit()

        return created_count

    def generate_payroll_for_employee(
        self,
        employee_id: int,
        payroll_period: PayrollPeriod,
    ) -> MonthlyPayroll:
        """
        Generate a payroll record for a single employee in an existing period.

        Raises ValueError if a record already exists for this employee/period.
        """
        existing = self.payroll_repo.get_by_employee_and_period(employee_id, payroll_period.id)
        if existing:
            raise ValueError("Payroll record already exists for this employee in the selected period.")

        employee = self.employee_repo.get_by_id(employee_id)
        if not employee:
            raise ValueError(f"Employee {employee_id} not found.")

        salary_structure = self.salary_repo.get_active_for_employee(employee.id, payroll_period.start_date)
        if not salary_structure:
            raise ValueError(f"No active salary structure found for {employee.full_name}.")

        payroll = MonthlyPayroll(
            employee_id=employee.id,
            payroll_period_id=payroll_period.id,
        )
        payroll.basic_salary = _to_decimal(salary_structure.basic_salary)
        payroll.hra = _to_decimal(salary_structure.hra)
        payroll.bonus = _to_decimal(salary_structure.bonus)
        payroll.cca = _to_decimal(salary_structure.cca)
        payroll.other_allowance = _to_decimal(salary_structure.other_allowance)
        payroll.paid_days = payroll_period.working_days
        payroll.present_days = payroll_period.working_days

        self._calculate_payroll(
            payroll,
            salary_structure.pf_applicable,
            salary_structure.esi_applicable,
            _to_decimal(salary_structure.basic_salary),
            _to_decimal(salary_structure.hra),
            _to_decimal(salary_structure.bonus),
            _to_decimal(salary_structure.cca),
            _to_decimal(salary_structure.other_allowance),
            _to_decimal(salary_structure.pf_employer),
            employee.gender,
            payroll_period.working_days,
        )
        payroll.arrears = self._calculate_arrears(employee.id, payroll_period, salary_structure)

        fy = get_financial_year(payroll_period.year, payroll_period.month)
        self.leave_repo.get_or_create_for_employee_fy(employee.id, fy)

        self.payroll_repo.create(payroll)
        self.session.commit()
        return payroll

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

        # Recalculate present_days and paid_days based on attendance values
        working_days = payroll.payroll_period.working_days
        absent = float(payroll.absent_days or 0)
        pl = float(payroll.privilege_leave or 0)
        sl = float(payroll.sick_leave or 0)
        cl = float(payroll.casual_leave or 0)
        
        # present_days = days actually worked (excluding leaves and absents)
        payroll.present_days = int(working_days - absent - pl - sl - cl)
        
        # paid_days = present + leaves (only absents reduce payment)
        payroll.paid_days = int(working_days - absent)

        # Recalculate
        self._calculate_payroll(
            payroll,
            salary_structure.pf_applicable,
            salary_structure.esi_applicable,
            _to_decimal(salary_structure.basic_salary),
            _to_decimal(salary_structure.hra),
            _to_decimal(salary_structure.bonus),
            _to_decimal(salary_structure.cca),
            _to_decimal(salary_structure.other_allowance),
            _to_decimal(salary_structure.pf_employer),
            employee.gender if employee else None,
            payroll.payroll_period.working_days,
        )

        # Recalculate arrears (only non-zero in the month structure changed)
        payroll.arrears = self._calculate_arrears(
            payroll.employee_id, payroll.payroll_period, salary_structure
        )

        self.session.commit()
        return payroll

    def _calculate_payroll(
        self,
        payroll: MonthlyPayroll,
        pf_applicable: bool,
        esi_applicable: bool,
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
            esi_applicable=esi_applicable,
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

    def _calculate_arrears(
        self,
        employee_id: int,
        payroll_period: PayrollPeriod,
        current_structure,
    ) -> Decimal:
        """
        Calculate arrears when salary structure changed.

        Arrears = (new bonus – old bonus) * months_in_fy_before_this_month
        Only applies in the month the structure was created and only for the
        bonus difference within the current financial year.
        """
        period_start = payroll_period.start_date
        fy = get_financial_year(payroll_period.year, payroll_period.month)

        # Only calculate if the structure became effective this month
        if not current_structure.effective_from:
            return Decimal("0.00")
        if (current_structure.effective_from.year != period_start.year or
                current_structure.effective_from.month != period_start.month):
            return Decimal("0.00")

        # Find the previous structure (the one just before this one)
        structures = self.salary_repo.get_by_employee_id(employee_id)
        prev_structure = None
        found_current = False
        for s in structures:  # ordered by effective_from desc
            if s.id == current_structure.id:
                found_current = True
                continue
            if found_current:
                prev_structure = s
                break

        if not prev_structure:
            return Decimal("0.00")

        old_gross = (
            _to_decimal(prev_structure.basic_salary)
            + _to_decimal(prev_structure.hra)
            + _to_decimal(prev_structure.bonus)
            + _to_decimal(prev_structure.cca)
            + _to_decimal(prev_structure.other_allowance)
        )
        new_gross = (
            _to_decimal(current_structure.basic_salary)
            + _to_decimal(current_structure.hra)
            + _to_decimal(current_structure.bonus)
            + _to_decimal(current_structure.cca)
            + _to_decimal(current_structure.other_allowance)
        )
        diff = new_gross - old_gross

        if diff <= Decimal("0.00"):
            return Decimal("0.00")

        # Count months in this FY before the current month that had old structure
        fy_start_month = 4  # April
        fy_start_year = fy
        months_count = 0
        y, m = fy_start_year, fy_start_month
        while (y, m) != (payroll_period.year, payroll_period.month):
            months_count += 1
            m += 1
            if m > 12:
                m = 1
                y += 1

        if months_count <= 0:
            return Decimal("0.00")

        arrears = diff * Decimal(str(months_count))
        return arrears.quantize(Decimal("0.01"))

    def apply_leave_hierarchy(self, payroll: MonthlyPayroll) -> None:
        """
        Redistribute monthly leaves following the hierarchy PL > CL > SL → Absent.

        When the FY cumulative total for a leave type exceeds its 7-day entitlement,
        the overflow is cascaded to the next type in the hierarchy:
          PL overflow → CL → SL → Absent (unpaid)

        This is called after the user edits leave values, before recalculation.
        """
        period = payroll.payroll_period
        fy = get_financial_year(period.year, period.month)
        ENTITLEMENT = Decimal("7.0")

        # FY totals from *other* months (exclude the record being edited)
        other_payrolls = (
            self.session.query(MonthlyPayroll)
            .join(PayrollPeriod)
            .filter(
                MonthlyPayroll.employee_id == payroll.employee_id,
                MonthlyPayroll.id != payroll.id,
                (
                    (PayrollPeriod.year == fy) & (PayrollPeriod.month >= 4)
                ) | (
                    (PayrollPeriod.year == fy + 1) & (PayrollPeriod.month <= 3)
                ),
            )
            .all()
        )

        fy_pl_before = sum(Decimal(str(p.privilege_leave or 0)) for p in other_payrolls)
        fy_cl_before = sum(Decimal(str(p.casual_leave or 0)) for p in other_payrolls)
        fy_sl_before = sum(Decimal(str(p.sick_leave or 0)) for p in other_payrolls)

        cur_pl = Decimal(str(payroll.privilege_leave or 0))
        cur_cl = Decimal(str(payroll.casual_leave or 0))
        cur_sl = Decimal(str(payroll.sick_leave or 0))
        cur_absent = Decimal(str(payroll.absent_days or 0))

        def _absorb(overflow: Decimal, source: str) -> Decimal:
            """
            Route overflow into other leave types in priority order PL > CL > SL,
            skipping the source type. Remaining unabsorbed days go to Absent.
            Returns the amount that could not be absorbed (to add to Absent).
            """
            nonlocal cur_pl, cur_cl, cur_sl
            remaining = overflow
            for leave_type in ("PL", "CL", "SL"):
                if leave_type == source or remaining <= 0:
                    continue
                if leave_type == "PL":
                    space = max(Decimal("0"), ENTITLEMENT - fy_pl_before - cur_pl)
                    absorbed = min(remaining, space)
                    cur_pl += absorbed
                elif leave_type == "CL":
                    space = max(Decimal("0"), ENTITLEMENT - fy_cl_before - cur_cl)
                    absorbed = min(remaining, space)
                    cur_cl += absorbed
                else:  # SL
                    space = max(Decimal("0"), ENTITLEMENT - fy_sl_before - cur_sl)
                    absorbed = min(remaining, space)
                    cur_sl += absorbed
                remaining -= absorbed
            return remaining  # unabsorbed → Absent

        # PL overflow → CL → SL → Absent
        pl_total = fy_pl_before + cur_pl
        if pl_total > ENTITLEMENT:
            overflow = pl_total - ENTITLEMENT
            cur_pl = max(Decimal("0"), ENTITLEMENT - fy_pl_before)
            cur_absent += _absorb(overflow, "PL")

        # CL overflow → PL → SL → Absent
        cl_total = fy_cl_before + cur_cl
        if cl_total > ENTITLEMENT:
            overflow = cl_total - ENTITLEMENT
            cur_cl = max(Decimal("0"), ENTITLEMENT - fy_cl_before)
            cur_absent += _absorb(overflow, "CL")

        # SL overflow → PL → CL → Absent
        sl_total = fy_sl_before + cur_sl
        if sl_total > ENTITLEMENT:
            overflow = sl_total - ENTITLEMENT
            cur_sl = max(Decimal("0"), ENTITLEMENT - fy_sl_before)
            cur_absent += _absorb(overflow, "SL")

        payroll.privilege_leave = float(cur_pl.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
        payroll.casual_leave = float(cur_cl.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
        payroll.sick_leave = float(cur_sl.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
        payroll.absent_days = float(cur_absent.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))

    def update_leave_balances(self, payroll_period: PayrollPeriod, company_id: int | None = None) -> None:
        """
        Recalculate leave balances for all employees for the financial year
        of the given payroll period.
        """
        fy = get_financial_year(payroll_period.year, payroll_period.month)
        if company_id is not None:
            employees = self.employee_repo.get_active_by_company(company_id)
        else:
            employees = self.employee_repo.get_all_active()

        for emp in employees:
            self.leave_repo.recalculate_from_payroll(emp.id, fy, self.session)

    def finalize_period(self, payroll_period_id: int, company_id: int) -> bool:
        """
        Finalize is currently disabled while lock feature is turned off.
        """
        _ = payroll_period_id
        _ = company_id
        return True
