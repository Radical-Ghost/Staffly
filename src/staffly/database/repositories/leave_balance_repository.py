"""Leave Balance repository for database operations."""

from decimal import Decimal
from typing import Optional, List
from sqlalchemy.orm import Session

from staffly.database.models.leave_balance import LeaveBalance
from .base_repository import BaseRepository


class LeaveBalanceRepository(BaseRepository[LeaveBalance]):
    """Repository for LeaveBalance operations."""

    def __init__(self, session: Session):
        super().__init__(session, LeaveBalance)

    def get_for_employee_fy(
        self, employee_id: int, financial_year: int
    ) -> Optional[LeaveBalance]:
        """Get leave balance for an employee in a specific financial year."""
        return self.session.query(LeaveBalance).filter(
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.financial_year == financial_year,
        ).first()

    def get_or_create_for_employee_fy(
        self, employee_id: int, financial_year: int
    ) -> LeaveBalance:
        """Get or create leave balance for an employee in a financial year."""
        balance = self.get_for_employee_fy(employee_id, financial_year)
        if not balance:
            balance = LeaveBalance(
                employee_id=employee_id,
                financial_year=financial_year,
                pl_entitlement=Decimal("7.0"),
                sl_entitlement=Decimal("7.0"),
                cl_entitlement=Decimal("7.0"),
                pl_used=Decimal("0.0"),
                sl_used=Decimal("0.0"),
                cl_used=Decimal("0.0"),
            )
            self.create(balance)
        return balance

    def get_all_for_employee(self, employee_id: int) -> List[LeaveBalance]:
        """Get all leave balances for an employee ordered by financial year desc."""
        return self.session.query(LeaveBalance).filter(
            LeaveBalance.employee_id == employee_id,
        ).order_by(LeaveBalance.financial_year.desc()).all()

    def recalculate_from_payroll(
        self, employee_id: int, financial_year: int, session
    ) -> LeaveBalance:
        """
        Recalculate leave usage from monthly payroll records for a financial year.
        
        Financial year runs April (fy_year) to March (fy_year+1).
        Sums PL, SL, CL from all monthly payroll records in that range.
        """
        from staffly.database.models.monthly_payroll import MonthlyPayroll
        from staffly.database.models.payroll_period import PayrollPeriod

        balance = self.get_or_create_for_employee_fy(employee_id, financial_year)

        # FY runs from April of financial_year to March of financial_year+1
        payrolls = (
            session.query(MonthlyPayroll)
            .join(PayrollPeriod)
            .filter(
                MonthlyPayroll.employee_id == employee_id,
                (
                    (PayrollPeriod.year == financial_year) & (PayrollPeriod.month >= 4)
                ) | (
                    (PayrollPeriod.year == financial_year + 1) & (PayrollPeriod.month <= 3)
                ),
            )
            .all()
        )

        pl_total = Decimal("0.0")
        sl_total = Decimal("0.0")
        cl_total = Decimal("0.0")
        for p in payrolls:
            pl_total += Decimal(str(p.privilege_leave or 0))
            sl_total += Decimal(str(p.sick_leave or 0))
            cl_total += Decimal(str(p.casual_leave or 0))

        balance.pl_used = pl_total
        balance.sl_used = sl_total
        balance.cl_used = cl_total
        self.session.flush()
        return balance
