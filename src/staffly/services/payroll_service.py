"""Payroll service for payroll generation and management."""

import math
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

    def _check_esic_buffer_rule(self, employee, payroll_period, current_structure) -> bool:
        """
        ESIC 6-Month Statutory Rule:
        Contribution periods are Apr-Sep and Oct-Mar.
        If ESIC was applicable at the start of the contribution period
        (or at joining date if joined mid-period), it remains applicable
        for the entire period even if salary crosses the threshold.
        """
        if current_structure and current_structure.esi_applicable:
            return True

        if 4 <= payroll_period.month <= 9:
            period_start = date(payroll_period.year, 4, 1)
        else:
            year = payroll_period.year if payroll_period.month >= 10 else payroll_period.year - 1
            period_start = date(year, 10, 1)

        check_date = max(period_start, employee.date_of_joining)

        if check_date >= payroll_period.start_date:
            return current_structure.esi_applicable if current_structure else False

        base_structure = self.salary_repo.get_active_for_employee(employee.id, check_date)
        if base_structure and base_structure.esi_applicable:
            return True

        return current_structure.esi_applicable if current_structure else False

    def _is_probation_active_for_period(self, employee, period: PayrollPeriod) -> bool:
        """Check if probation applies for the entirety of this payroll period."""
        if not getattr(employee, 'is_on_probation', False):
            return False
        if not employee.probation_end_date:
            return True

        doj = employee.date_of_joining
        end_date = employee.probation_end_date

        # If joined mid-month, probation pushes to the END of the end_date's month
        if doj.day > 1:
            if period.start_date.year < end_date.year:
                return True
            if period.start_date.year == end_date.year and period.start_date.month <= end_date.month:
                return True
            return False
        else:
            # Joined on the 1st, normal comparison
            return period.start_date < end_date

    def _calculate_leave_entitlements(self, employee, period: PayrollPeriod) -> dict:
        """
        Calculates dynamic leave entitlements.
        Formula: (Remaining months in FY) * 21/12
        Rounds .01-.49 to .5, and .51-.99 to +1.
        Distributes extra in priority PL > SL > CL.
        """
        if self._is_probation_active_for_period(employee, period):
            return {"PL": Decimal("0.0"), "SL": Decimal("0.0"), "CL": Decimal("0.0")}

        doj = employee.date_of_joining
        probation_end = employee.probation_end_date

        # Determine the exact date they became a permanent employee
        if getattr(employee, 'is_on_probation', False) and probation_end:
            if doj.day > 1:
                y, m = probation_end.year, probation_end.month
                m += 1
                if m > 12:
                    m = 1
                    y += 1
                perm_start = date(y, m, 1)
            else:
                perm_start = probation_end
        else:
            if probation_end:
                if doj.day > 1:
                    y, m = probation_end.year, probation_end.month
                    m += 1
                    if m > 12:
                        m = 1
                        y += 1
                    perm_start = date(y, m, 1)
                else:
                    perm_start = probation_end
            else:
                perm_start = doj

        # If the period being processed is BEFORE they became permanent, no leaves
        if period.start_date < perm_start:
            return {"PL": Decimal("0.0"), "SL": Decimal("0.0"), "CL": Decimal("0.0")}

        fy = get_financial_year(period.year, period.month)
        fy_start = date(fy, 4, 1)
        fy_end = date(fy + 1, 3, 31)

        accrual_start = max(fy_start, perm_start)

        months_remaining = 0
        curr_y, curr_m = accrual_start.year, accrual_start.month
        while (curr_y < fy_end.year) or (curr_y == fy_end.year and curr_m <= 3):
            months_remaining += 1
            curr_m += 1
            if curr_m > 12:
                curr_m = 1
                curr_y += 1

        raw_leaves = Decimal(months_remaining) * Decimal("21") / Decimal("12")

        # Custom rounding rule
        int_part = math.floor(raw_leaves)
        frac_part = raw_leaves - Decimal(int_part)

        if frac_part == 0:
            total_leaves = Decimal(int_part)
        elif frac_part < Decimal("0.50"):
            total_leaves = Decimal(int_part) + Decimal("0.5")
        else:
            total_leaves = Decimal(int_part) + Decimal("1.0")

        # Distribute equally in 0.5 increments, prioritizing PL > SL > CL
        pl = sl = cl = Decimal("0.0")
        rem = total_leaves
        while rem >= Decimal("0.5"):
            if pl <= sl and pl <= cl:
                pl += Decimal("0.5")
            elif sl <= cl:
                sl += Decimal("0.5")
            else:
                cl += Decimal("0.5")
            rem -= Decimal("0.5")

        return {"PL": pl, "SL": sl, "CL": cl}

    def generate_payroll_for_period(
        self,
        payroll_period: PayrollPeriod,
        copy_from_previous: bool = True,
        company_id: int | None = None,
    ) -> int:
        """Automatically generate monthly payroll records."""
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

        period_start = payroll_period.start_date
        period_end = payroll_period.end_date

        # Fetch active by END of month to catch mid-month joiners
        if company_id is not None:
            active_employees = self.employee_repo.get_active_on_date_by_company(period_end, company_id)
        else:
            active_employees = self.employee_repo.get_active_on_date(period_end)

        created_count = 0

        for employee in active_employees:
            effective_date = max(period_start, employee.date_of_joining)
            salary_structure = self.salary_repo.get_active_for_employee(
                employee.id, effective_date
            )

            if not salary_structure:
                print(f"Warning: No salary structure for {employee.full_name}, skipping")
                continue

            payroll = MonthlyPayroll(
                employee_id=employee.id,
                payroll_period_id=payroll_period.id,
            )

            payroll.basic_salary = _to_decimal(salary_structure.basic_salary)
            payroll.hra = _to_decimal(salary_structure.hra)
            payroll.bonus = _to_decimal(salary_structure.bonus)
            payroll.cca = _to_decimal(salary_structure.cca)
            payroll.other_allowance = _to_decimal(salary_structure.other_allowance)

            # Auto-subtract unworked days for mid-month joiners
            unworked_days = 0
            if employee.date_of_joining > period_start:
                unworked_days = (employee.date_of_joining - period_start).days
            base_working_days = max(0, payroll_period.working_days - unworked_days)

            if copy_from_previous:
                prev_payroll = self.payroll_repo.get_previous_month_payroll(
                    employee.id, payroll_period.id
                )
                if prev_payroll and unworked_days == 0:
                    payroll.paid_days = prev_payroll.paid_days
                    payroll.present_days = prev_payroll.present_days
                else:
                    payroll.paid_days = base_working_days
                    payroll.present_days = base_working_days
            else:
                payroll.paid_days = base_working_days
                payroll.present_days = base_working_days

            is_esi_applicable = self._check_esic_buffer_rule(employee, payroll_period, salary_structure)

            self._calculate_payroll(
                payroll,
                salary_structure.pf_applicable,
                is_esi_applicable,
                _to_decimal(salary_structure.basic_salary),
                _to_decimal(salary_structure.hra),
                _to_decimal(salary_structure.bonus),
                _to_decimal(salary_structure.cca),
                _to_decimal(salary_structure.other_allowance),
                _to_decimal(salary_structure.pf_employer),
                employee.gender,
                payroll_period.working_days,
            )

            payroll.arrears = self._calculate_arrears(
                employee.id, payroll_period, salary_structure
            )

            fy = get_financial_year(payroll_period.year, payroll_period.month)
            self.leave_repo.get_or_create_for_employee_fy(employee.id, fy)

            self.payroll_repo.create(payroll)
            created_count += 1

        self.session.commit()
        return created_count

    def generate_payroll_for_employee(
        self,
        employee_id: int,
        payroll_period: PayrollPeriod,
    ) -> MonthlyPayroll:
        """Generate a payroll record for a single employee in an existing period."""
        existing = self.payroll_repo.get_by_employee_and_period(employee_id, payroll_period.id)
        if existing:
            raise ValueError("Payroll record already exists for this employee in the selected period.")

        employee = self.employee_repo.get_by_id(employee_id)
        if not employee:
            raise ValueError(f"Employee {employee_id} not found.")

        effective_date = max(payroll_period.start_date, employee.date_of_joining)
        salary_structure = self.salary_repo.get_active_for_employee(employee.id, effective_date)
        if not salary_structure:
            raise ValueError(f"No active salary structure found for {employee.full_name}.")

        unworked_days = 0
        if employee.date_of_joining > payroll_period.start_date:
            unworked_days = (employee.date_of_joining - payroll_period.start_date).days
        base_working_days = max(0, payroll_period.working_days - unworked_days)

        payroll = MonthlyPayroll(
            employee_id=employee.id,
            payroll_period_id=payroll_period.id,
        )
        payroll.basic_salary = _to_decimal(salary_structure.basic_salary)
        payroll.hra = _to_decimal(salary_structure.hra)
        payroll.bonus = _to_decimal(salary_structure.bonus)
        payroll.cca = _to_decimal(salary_structure.cca)
        payroll.other_allowance = _to_decimal(salary_structure.other_allowance)
        payroll.paid_days = base_working_days
        payroll.present_days = base_working_days

        is_esi_applicable = self._check_esic_buffer_rule(employee, payroll_period, salary_structure)

        self._calculate_payroll(
            payroll,
            salary_structure.pf_applicable,
            is_esi_applicable,
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
        """Recalculate payroll after user edits attendance."""
        payroll = self.payroll_repo.get_by_id(payroll_id)
        if not payroll:
            raise ValueError(f"Payroll record {payroll_id} not found")

        employee = self.employee_repo.get_by_id(payroll.employee_id)

        # Fix for mid-month joiners: check effective date against DOJ
        effective_date = payroll.payroll_period.start_date
        if employee and employee.date_of_joining > effective_date:
            effective_date = employee.date_of_joining

        salary_structure = self.salary_repo.get_active_for_employee(
            payroll.employee_id,
            effective_date
        )

        if not salary_structure:
            raise ValueError(f"No salary structure found for employee")

        # ---------------------------------------------------------
        # LEAVE ROUTING (Zero-Leave Redirect OR Dynamic Entitlements)
        # ---------------------------------------------------------
        if employee:
            self.apply_leave_hierarchy(payroll)

        working_days = payroll.payroll_period.working_days
        unworked_days = 0
        if employee and employee.date_of_joining > payroll.payroll_period.start_date:
            unworked_days = (employee.date_of_joining - payroll.payroll_period.start_date).days
        base_working_days = max(0, working_days - unworked_days)

        absent = float(payroll.absent_days or 0)
        pl = float(payroll.privilege_leave or 0)
        sl = float(payroll.sick_leave or 0)
        cl = float(payroll.casual_leave or 0)

        payroll.present_days = int(base_working_days - absent - pl - sl - cl)
        payroll.paid_days = int(base_working_days - absent)

        is_esi_applicable = self._check_esic_buffer_rule(employee, payroll.payroll_period, salary_structure)

        self._calculate_payroll(
            payroll,
            salary_structure.pf_applicable,
            is_esi_applicable,
            _to_decimal(salary_structure.basic_salary),
            _to_decimal(salary_structure.hra),
            _to_decimal(salary_structure.bonus),
            _to_decimal(salary_structure.cca),
            _to_decimal(salary_structure.other_allowance),
            _to_decimal(salary_structure.pf_employer),
            employee.gender if employee else None,
            payroll.payroll_period.working_days,
        )

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
        """Internal method to calculate payroll values."""
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
        """Calculate arrears when salary structure changed."""
        period_start = payroll_period.start_date
        fy = get_financial_year(payroll_period.year, payroll_period.month)

        if not current_structure.effective_from:
            return Decimal("0.00")
        if (current_structure.effective_from.year != period_start.year or
                current_structure.effective_from.month != period_start.month):
            return Decimal("0.00")

        structures = self.salary_repo.get_by_employee_id(employee_id)
        prev_structure = None
        found_current = False
        for s in structures:
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

        fy_start_month = 4
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
        """Redistribute monthly leaves following the hierarchy PL > CL > SL → Absent."""
        if self._is_probation_active_for_period(payroll.employee, payroll.payroll_period):
            # Redirect any typed leaves directly into absent
            total_typed = Decimal(str(payroll.privilege_leave or 0)) + Decimal(str(payroll.casual_leave or 0)) + Decimal(str(payroll.sick_leave or 0))
            if total_typed > 0:
                payroll.absent_days = float(Decimal(str(payroll.absent_days or 0)) + total_typed)
            payroll.privilege_leave = 0.0
            payroll.casual_leave = 0.0
            payroll.sick_leave = 0.0
            return

        # Fetch dynamic leave limits
        entitlements = self._calculate_leave_entitlements(payroll.employee, payroll.payroll_period)
        ent_pl = entitlements["PL"]
        ent_sl = entitlements["SL"]
        ent_cl = entitlements["CL"]

        period = payroll.payroll_period
        fy = get_financial_year(period.year, period.month)

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
            nonlocal cur_pl, cur_cl, cur_sl
            remaining = overflow
            for leave_type in ("PL", "CL", "SL"):
                if leave_type == source or remaining <= 0:
                    continue
                if leave_type == "PL":
                    space = max(Decimal("0"), ent_pl - fy_pl_before - cur_pl)
                    absorbed = min(remaining, space)
                    cur_pl += absorbed
                elif leave_type == "CL":
                    space = max(Decimal("0"), ent_cl - fy_cl_before - cur_cl)
                    absorbed = min(remaining, space)
                    cur_cl += absorbed
                else:  # SL
                    space = max(Decimal("0"), ent_sl - fy_sl_before - cur_sl)
                    absorbed = min(remaining, space)
                    cur_sl += absorbed
                remaining -= absorbed
            return remaining  # unabsorbed → Absent

        # PL overflow → CL → SL → Absent
        pl_total = fy_pl_before + cur_pl
        if pl_total > ent_pl:
            overflow = pl_total - ent_pl
            cur_pl = max(Decimal("0"), ent_pl - fy_pl_before)
            cur_absent += _absorb(overflow, "PL")

        # CL overflow → PL → SL → Absent
        cl_total = fy_cl_before + cur_cl
        if cl_total > ent_cl:
            overflow = cl_total - ent_cl
            cur_cl = max(Decimal("0"), ent_cl - fy_cl_before)
            cur_absent += _absorb(overflow, "CL")

        # SL overflow → PL → CL → Absent
        sl_total = fy_sl_before + cur_sl
        if sl_total > ent_sl:
            overflow = sl_total - ent_sl
            cur_sl = max(Decimal("0"), ent_sl - fy_sl_before)
            cur_absent += _absorb(overflow, "SL")

        payroll.privilege_leave = float(cur_pl.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
        payroll.casual_leave = float(cur_cl.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
        payroll.sick_leave = float(cur_sl.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
        payroll.absent_days = float(cur_absent.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))

    def update_leave_balances(self, payroll_period: PayrollPeriod, company_id: int | None = None) -> None:
        """Recalculate leave balances for all employees for the financial year."""
        fy = get_financial_year(payroll_period.year, payroll_period.month)
        if company_id is not None:
            employees = self.employee_repo.get_active_by_company(company_id)
        else:
            employees = self.employee_repo.get_all_active()

        for emp in employees:
            bal = self.leave_repo.recalculate_from_payroll(emp.id, fy, self.session)

            # Update the database entitlements to match the dynamic calculation
            entitlements = self._calculate_leave_entitlements(emp, payroll_period)
            bal.pl_entitlement = entitlements["PL"]
            bal.sl_entitlement = entitlements["SL"]
            bal.cl_entitlement = entitlements["CL"]

    def finalize_period(self, payroll_period_id: int, company_id: int) -> bool:
        """Finalize is currently disabled while lock feature is turned off."""
        _ = payroll_period_id
        _ = company_id
        return True
