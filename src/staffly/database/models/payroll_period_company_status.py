"""Company-specific lock status for payroll periods."""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .company import Company
    from .payroll_period import PayrollPeriod


class PayrollPeriodCompanyStatus(BaseModel):
    """Stores lock state of a payroll period for a specific company."""

    __tablename__ = "payroll_period_company_status"

    __table_args__ = (
        UniqueConstraint(
            "payroll_period_id",
            "company_id",
            name="uq_payroll_period_company_status",
        ),
    )

    payroll_period_id: Mapped[int] = mapped_column(
        ForeignKey("payroll_periods.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    payroll_period: Mapped["PayrollPeriod"] = relationship(
        "PayrollPeriod",
        back_populates="company_lock_statuses",
    )
    company: Mapped["Company"] = relationship("Company")

    def __repr__(self) -> str:
        status = "LOCKED" if self.is_locked else "OPEN"
        return (
            f"<PayrollPeriodCompanyStatus(period_id={self.payroll_period_id}, "
            f"company_id={self.company_id}, {status})>"
        )
