"""Monthly Payroll repository for database operations."""

from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from staffly.database.models.employee import Employee

from staffly.database.models.monthly_payroll import MonthlyPayroll
from .base_repository import BaseRepository


class MonthlyPayrollRepository(BaseRepository[MonthlyPayroll]):
    """Repository for MonthlyPayroll operations."""

    def __init__(self, session: Session):
        super().__init__(session, MonthlyPayroll)

    def get_by_employee_and_period(
        self, employee_id: int, payroll_period_id: int
    ) -> Optional[MonthlyPayroll]:
        """Get monthly payroll for specific employee and period."""
        return self.session.query(MonthlyPayroll).filter(
            MonthlyPayroll.employee_id == employee_id,
            MonthlyPayroll.payroll_period_id == payroll_period_id
        ).first()

    def get_all_for_period(self, payroll_period_id: int) -> List[MonthlyPayroll]:
        """Get all monthly payrolls for a specific period."""
        return self.session.query(MonthlyPayroll).options(
            joinedload(MonthlyPayroll.employee),
            joinedload(MonthlyPayroll.payroll_period)
        ).filter(
            MonthlyPayroll.payroll_period_id == payroll_period_id
        ).all()

    def get_all_for_period_and_company(self, payroll_period_id: int, company_id: int) -> List[MonthlyPayroll]:
        """Get all payroll rows for a period scoped to one company."""
        payrolls = self.get_all_for_period(payroll_period_id)
        return [
            payroll
            for payroll in payrolls
            if payroll.employee and payroll.employee.company_id == company_id
        ]

    def get_all_for_employee(self, employee_id: int) -> List[MonthlyPayroll]:
        """Get all payroll records for a specific employee."""
        return self.session.query(MonthlyPayroll).options(
            joinedload(MonthlyPayroll.payroll_period)
        ).filter(
            MonthlyPayroll.employee_id == employee_id
        ).order_by(
            MonthlyPayroll.payroll_period_id.desc()
        ).all()

    def get_previous_month_payroll(
        self, employee_id: int, current_period_id: int
    ) -> Optional[MonthlyPayroll]:
        """
        Get the most recent payroll record for an employee before the current period.
        Used for copying attendance data.
        """
        return self.session.query(MonthlyPayroll).filter(
            MonthlyPayroll.employee_id == employee_id,
            MonthlyPayroll.payroll_period_id < current_period_id
        ).order_by(
            MonthlyPayroll.payroll_period_id.desc()
        ).first()

    def exists_for_period(self, payroll_period_id: int) -> bool:
        """Check if any payroll records exist for a period."""
        count = self.session.query(MonthlyPayroll).filter(
            MonthlyPayroll.payroll_period_id == payroll_period_id
        ).count()
        return count > 0

    def exists_for_period_and_company(self, payroll_period_id: int, company_id: int) -> bool:
        """Check if payroll records exist for a period in one company."""
        count = self.session.query(MonthlyPayroll).join(Employee).filter(
            MonthlyPayroll.payroll_period_id == payroll_period_id,
            Employee.company_id == company_id,
        ).count()
        return count > 0

    def finalize_payroll(self, payroll_id: int) -> bool:
        """Finalize a payroll record. Returns True if successful."""
        payroll = self.get_by_id(payroll_id)
        if payroll and not payroll.is_finalized:
            payroll.is_finalized = True
            self.session.flush()
            return True
        return False

    def delete_for_period(self, payroll_period_id: int) -> int:
        """Delete all payroll records for a period. Returns count deleted."""
        count = self.session.query(MonthlyPayroll).filter(
            MonthlyPayroll.payroll_period_id == payroll_period_id
        ).delete()
        self.session.flush()
        return count

    def delete_for_period_and_company(self, payroll_period_id: int, company_id: int) -> int:
        """Delete payroll records for a period limited to one company. Returns count deleted."""
        payrolls = self.session.query(MonthlyPayroll).join(Employee).filter(
            MonthlyPayroll.payroll_period_id == payroll_period_id,
            Employee.company_id == company_id,
        ).all()

        count = len(payrolls)
        for payroll in payrolls:
            self.session.delete(payroll)

        self.session.flush()
        return count

    def delete_payroll(self, payroll_id: int) -> bool:
        """Delete a specific payroll record. Returns True if successful."""
        payroll = self.get_by_id(payroll_id)
        if payroll:
            self.session.delete(payroll)
            self.session.flush()
            return True
        return False
