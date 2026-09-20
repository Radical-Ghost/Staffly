"""Monthly Payroll model - stores what actually happened in a payroll month."""

from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Numeric, Integer, Boolean, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .employee import Employee
    from .payroll_period import PayrollPeriod


class MonthlyPayroll(BaseModel):
    """
    Monthly Payroll Snapshot table.
    
    Stores what ACTUALLY happened for one employee in one payroll month.
    This is the database equivalent of one row in the Excel monthly sheet.
    
    CRITICAL RULES:
    1. This is a SNAPSHOT - salary values are copied at generation time
    2. Once the period is locked, this data MUST NOT change
    3. Past months remain unchanged even if salary structure changes
    4. Salary slips are generated from this data
    
    Flow: Generate → Review → Lock → Generate Salary Slip
    """

    __tablename__ = "monthly_payroll"

    # Ensure one record per employee per period
    __table_args__ = (
        UniqueConstraint(
            "employee_id", "payroll_period_id",
            name="uq_monthly_payroll_employee_period"
        ),
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # FOREIGN KEYS
    # ═══════════════════════════════════════════════════════════════════════════

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    payroll_period_id: Mapped[int] = mapped_column(
        ForeignKey("payroll_periods.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # A. ATTENDANCE & LEAVE (Monthly Reality - varies every month)
    # ═══════════════════════════════════════════════════════════════════════════

    # Days actually present at work
    present_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Days for which salary is paid (Present + Paid Leaves)
    paid_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Absent days (unpaid) - decimal for half-day support
    absent_days: Mapped[Decimal] = mapped_column(
        Numeric(4, 1), default=Decimal("0.0"), nullable=False
    )

    # Late marks (decimal) - beside absent
    late_marks: Mapped[Decimal] = mapped_column(
        Numeric(4, 1), default=Decimal("0.0"), nullable=False
    )

    # Leave breakdown
    privilege_leave: Mapped[Decimal] = mapped_column(
        Numeric(4, 1), default=Decimal("0.0"), nullable=False
    )  # PL/Earned Leave
    sick_leave: Mapped[Decimal] = mapped_column(
        Numeric(4, 1), default=Decimal("0.0"), nullable=False
    )  # SL
    casual_leave: Mapped[Decimal] = mapped_column(
        Numeric(4, 1), default=Decimal("0.0"), nullable=False
    )  # CL

    # ═══════════════════════════════════════════════════════════════════════════
    # B. SALARY COMPONENTS (Snapshot from salary_structures at generation time)
    # ═══════════════════════════════════════════════════════════════════════════

    # These are COPIED from salary_structures so history is preserved
    # even if salary_structures is later modified

    basic_salary: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    hra: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    bonus: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    cca: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    other_allowance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # C. CALCULATED EARNINGS
    # ═══════════════════════════════════════════════════════════════════════════

    # Gross Total (sum of all earnings, pro-rated for paid days)
    gross_earnings: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # D. EMPLOYEE DEDUCTIONS
    # ═══════════════════════════════════════════════════════════════════════════

    # Provident Fund - Employee contribution (typically 12% of Basic)
    pf_employee: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )

    # Employee State Insurance - Employee contribution (0.75% of Gross)
    esi_employee: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )

    # Professional Tax (state-specific, usually fixed slab)
    professional_tax: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )

    # Loan/Advance Deduction (if any)
    loan_deduction: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )

    # Tax Deducted at Source (TDS) on salary
    tds: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )

    # Other deductions (catch-all)
    other_deductions: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )

    # Total Deductions (sum of all above)
    total_deductions: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # E. EMPLOYER CONTRIBUTIONS (Not deducted from salary, but tracked)
    # ═══════════════════════════════════════════════════════════════════════════

    # Provident Fund - Employer contribution (typically 12% of Basic)
    pf_employer: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )

    # Employee State Insurance - Employer contribution (3.25% of Gross)
    esi_employer: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # F. FINAL AMOUNTS
    # ═══════════════════════════════════════════════════════════════════════════

    # Net Salary = Gross Earnings - Total Deductions
    net_salary: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )

    # Cost to Company for this month (Gross + Employer contributions)
    ctc_monthly: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )

    # Arrears (paid when salary structure changes mid-year)
    arrears: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # G. STATUS & METADATA
    # ═══════════════════════════════════════════════════════════════════════════

    # Is this payroll record finalized?
    is_finalized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Optional remarks
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # RELATIONSHIPS
    # ═══════════════════════════════════════════════════════════════════════════

    employee: Mapped["Employee"] = relationship("Employee", back_populates="monthly_payrolls")
    payroll_period: Mapped["PayrollPeriod"] = relationship(
        "PayrollPeriod", back_populates="monthly_payrolls"
    )

    def __repr__(self) -> str:
        return (
            f"<MonthlyPayroll(id={self.id}, employee_id={self.employee_id}, "
            f"period_id={self.payroll_period_id}, net={self.net_salary})>"
        )
