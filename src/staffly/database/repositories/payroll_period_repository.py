"""Payroll Period repository for database operations."""

from typing import List, Optional
from sqlalchemy.orm import Session

from staffly.database.models.payroll_period import PayrollPeriod
from staffly.database.models.payroll_period_company_status import PayrollPeriodCompanyStatus
from .base_repository import BaseRepository


class PayrollPeriodRepository(BaseRepository[PayrollPeriod]):
    """Repository for PayrollPeriod operations."""

    def __init__(self, session: Session):
        super().__init__(session, PayrollPeriod)

    def get_by_year_month(self, year: int, month: int) -> Optional[PayrollPeriod]:
        """Get payroll period by year and month."""
        return self.session.query(PayrollPeriod).filter(
            PayrollPeriod.year == year,
            PayrollPeriod.month == month
        ).first()

    def get_all_ordered(self) -> List[PayrollPeriod]:
        """Get all payroll periods ordered by year, month descending."""
        return self.session.query(PayrollPeriod).order_by(
            PayrollPeriod.year.desc(),
            PayrollPeriod.month.desc()
        ).all()

    def get_unlocked(self) -> List[PayrollPeriod]:
        """Get all unlocked payroll periods."""
        return self.session.query(PayrollPeriod).filter(
            PayrollPeriod.is_locked == False
        ).order_by(
            PayrollPeriod.year.desc(),
            PayrollPeriod.month.desc()
        ).all()

    def get_unlocked_by_company(self, company_id: int) -> List[PayrollPeriod]:
        """Get periods that are unlocked for a specific company."""
        periods = self.get_all_ordered()
        return [p for p in periods if not self.is_locked_for_company(p.id, company_id)]

    def get_locked(self) -> List[PayrollPeriod]:
        """Get all locked/finalized payroll periods."""
        return self.session.query(PayrollPeriod).filter(
            PayrollPeriod.is_locked == True
        ).order_by(
            PayrollPeriod.year.desc(),
            PayrollPeriod.month.desc()
        ).all()

    def get_locked_by_company(self, company_id: int) -> List[PayrollPeriod]:
        """Get periods that are locked for a specific company."""
        periods = self.get_all_ordered()
        return [p for p in periods if self.is_locked_for_company(p.id, company_id)]

    def get_latest(self) -> Optional[PayrollPeriod]:
        """Get the most recent payroll period."""
        return self.session.query(PayrollPeriod).order_by(
            PayrollPeriod.year.desc(),
            PayrollPeriod.month.desc()
        ).first()

    def lock_period(self, period_id: int) -> bool:
        """Lock a payroll period. Returns True if successful."""
        period = self.get_by_id(period_id)
        if period and not period.is_locked:
            period.is_locked = True
            self.session.flush()
            return True
        return False

    def get_company_lock_status(self, period_id: int, company_id: int) -> Optional[PayrollPeriodCompanyStatus]:
        """Get lock status row for period/company."""
        return self.session.query(PayrollPeriodCompanyStatus).filter(
            PayrollPeriodCompanyStatus.payroll_period_id == period_id,
            PayrollPeriodCompanyStatus.company_id == company_id,
        ).first()

    def is_locked_for_company(self, period_id: int, company_id: int) -> bool:
        """Check lock status for one company (falls back to legacy global lock)."""
        status = self.get_company_lock_status(period_id, company_id)
        if status is not None:
            return status.is_locked

        period = self.get_by_id(period_id)
        if period and period.is_locked:
            # Lazy migration path from legacy global lock to company-specific lock
            self.set_locked_for_company(period_id, company_id, True)
            return True

        return False

    def set_locked_for_company(self, period_id: int, company_id: int, is_locked: bool) -> None:
        """Set lock status for one company in a period."""
        status = self.get_company_lock_status(period_id, company_id)
        if not status:
            status = PayrollPeriodCompanyStatus(
                payroll_period_id=period_id,
                company_id=company_id,
                is_locked=is_locked,
            )
            self.session.add(status)
        else:
            status.is_locked = is_locked

        self.session.flush()
