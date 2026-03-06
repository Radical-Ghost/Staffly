"""Repository for company-specific payroll period lock statuses."""

from typing import Optional
from sqlalchemy.orm import Session

from staffly.database.models.payroll_period_company_status import PayrollPeriodCompanyStatus
from .base_repository import BaseRepository


class PayrollPeriodCompanyStatusRepository(BaseRepository[PayrollPeriodCompanyStatus]):
    """Repository for PayrollPeriodCompanyStatus operations."""

    def __init__(self, session: Session):
        super().__init__(session, PayrollPeriodCompanyStatus)

    def get_by_period_and_company(
        self, payroll_period_id: int, company_id: int
    ) -> Optional[PayrollPeriodCompanyStatus]:
        """Get status row for a period and company."""
        return self.session.query(PayrollPeriodCompanyStatus).filter(
            PayrollPeriodCompanyStatus.payroll_period_id == payroll_period_id,
            PayrollPeriodCompanyStatus.company_id == company_id,
        ).first()

    def set_locked(self, payroll_period_id: int, company_id: int, is_locked: bool) -> None:
        """Create/update lock status for a period-company pair."""
        status = self.get_by_period_and_company(payroll_period_id, company_id)
        if not status:
            status = PayrollPeriodCompanyStatus(
                payroll_period_id=payroll_period_id,
                company_id=company_id,
                is_locked=is_locked,
            )
            self.create(status)
        else:
            status.is_locked = is_locked

        self.session.flush()
