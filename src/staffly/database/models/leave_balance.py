"""Leave Balance model - tracks annual leave balances per employee per financial year."""

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .employee import Employee


class LeaveBalance(BaseModel):
    """
    Leave Balance table.

    Stores annual leave entitlements and usage for each employee
    per financial year (April - March).

    Each employee gets 7 PL, 7 SL, 7 CL per financial year.
    The financial year is identified by the starting year
    (e.g., FY 2025 = April 2025 - March 2026).
    """

    __tablename__ = "leave_balances"

    __table_args__ = (
        UniqueConstraint(
            "employee_id", "financial_year",
            name="uq_leave_balance_employee_fy"
        ),
    )

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Financial year start year (e.g., 2025 for April 2025 - March 2026)
    financial_year: Mapped[int] = mapped_column(Integer, nullable=False)

    # Annual entitlements (default 7 each)
    pl_entitlement: Mapped[Decimal] = mapped_column(
        Numeric(4, 1), default=Decimal("7.0"), nullable=False
    )
    sl_entitlement: Mapped[Decimal] = mapped_column(
        Numeric(4, 1), default=Decimal("7.0"), nullable=False
    )
    cl_entitlement: Mapped[Decimal] = mapped_column(
        Numeric(4, 1), default=Decimal("7.0"), nullable=False
    )

    # Consumed leaves (updated from monthly payroll)
    pl_used: Mapped[Decimal] = mapped_column(
        Numeric(5, 1), default=Decimal("0.0"), nullable=False
    )
    sl_used: Mapped[Decimal] = mapped_column(
        Numeric(5, 1), default=Decimal("0.0"), nullable=False
    )
    cl_used: Mapped[Decimal] = mapped_column(
        Numeric(5, 1), default=Decimal("0.0"), nullable=False
    )

    # Relationships
    employee: Mapped["Employee"] = relationship("Employee", back_populates="leave_balances")

    @property
    def pl_balance(self) -> Decimal:
        return self.pl_entitlement - self.pl_used

    @property
    def sl_balance(self) -> Decimal:
        return self.sl_entitlement - self.sl_used

    @property
    def cl_balance(self) -> Decimal:
        return self.cl_entitlement - self.cl_used
