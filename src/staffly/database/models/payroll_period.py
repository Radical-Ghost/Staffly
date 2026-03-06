"""Payroll Period model - defines official payroll months."""

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Integer, String, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .monthly_payroll import MonthlyPayroll
    from .payroll_period_company_status import PayrollPeriodCompanyStatus


class PayrollPeriod(BaseModel):
    """
    Payroll Period table.
    
    Defines official payroll months and prevents accidental regeneration.
    Each row represents exactly one month (e.g., April 2025, May 2025).
    
    Key Rules:
    - One row per month
    - Once locked, payroll data for that month MUST NOT change
    - Used as reference for all monthly payroll records
    """

    __tablename__ = "payroll_periods"

    # Ensure unique year-month combination
    __table_args__ = (
        UniqueConstraint("year", "month", name="uq_payroll_period_year_month"),
    )

    # Year (e.g., 2025)
    year: Mapped[int] = mapped_column(Integer, nullable=False)

    # Month (1-12)
    month: Mapped[int] = mapped_column(Integer, nullable=False)

    # Human-readable label (e.g., "Apr 2025")
    period_label: Mapped[str] = mapped_column(String(20), nullable=False)

    # Lock status - once True, no changes allowed to payroll data
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Total working days in this period (can vary by company policy)
    working_days: Mapped[int] = mapped_column(Integer, default=26, nullable=False)

    # Relationships
    monthly_payrolls: Mapped[list["MonthlyPayroll"]] = relationship(
        "MonthlyPayroll",
        back_populates="payroll_period",
        cascade="all, delete-orphan",
    )
    company_lock_statuses: Mapped[list["PayrollPeriodCompanyStatus"]] = relationship(
        "PayrollPeriodCompanyStatus",
        back_populates="payroll_period",
        cascade="all, delete-orphan",
    )

    @property
    def start_date(self) -> date:
        """Return the first day of this period."""
        return date(self.year, self.month, 1)

    @property
    def end_date(self) -> date:
        """Return the last day of this period."""
        # Get first day of next month, then subtract one day
        if self.month == 12:
            next_month_start = date(self.year + 1, 1, 1)
        else:
            next_month_start = date(self.year, self.month + 1, 1)
        from datetime import timedelta
        return next_month_start - timedelta(days=1)

    @classmethod
    def generate_label(cls, year: int, month: int) -> str:
        """Generate a human-readable label for the period."""
        month_names = [
            "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
        ]
        return f"{month_names[month]} {year}"

    def __repr__(self) -> str:
        status = "LOCKED" if self.is_locked else "OPEN"
        return f"<PayrollPeriod(id={self.id}, {self.period_label}, {status})>"
