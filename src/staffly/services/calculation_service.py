"""Calculation service for payroll computations."""

from decimal import Decimal, ROUND_HALF_UP
import decimal
from typing import Tuple, Optional, Dict

from staffly.config import get_config


def _to_decimal(value: Optional[Decimal]) -> Decimal:
    """Convert value to Decimal, treating None as 0."""
    if value is None:
        return Decimal("0.00")
    return value


def _round_decimal(value: Decimal) -> Decimal:
    """Round to 2 decimal places."""
    return value.quantize(Decimal("0.01"))


def _round_rupee(value: Decimal) -> Decimal:
    """Round to nearest whole rupee using 0.5 half-up rule."""
    return value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


class CalculationService:
    """
    Service for payroll calculations.

    Handles:
    - Salary structure calculation from gross
    - Pro-rata salary calculations
    - PF/ESI calculations
    - Net salary computation
    """

    def __init__(self):
        self.config = get_config()

    # ═══════════════════════════════════════════════════════════════════════════
    # SALARY STRUCTURE CALCULATION (From Gross)
    # ═══════════════════════════════════════════════════════════════════════════

    def calculate_salary_structure_from_gross(
        self, gross_salary: Decimal, pf_applicable: bool = True, esi_applicable: bool = False
    ) -> Dict[str, Decimal]:
        """
        Calculate salary structure components from CTC (gross salary).

        Formulas (CTC = Cost to Company per month):
        - Basic = MIN(25000, CTC * 50%)
        - HRA = Basic * 40%
        - Bonus = FLOOR(Basic * 8.33%)  (round down)
        - CCA = IF(CTC > 50000, CTC * 20%, 0)
        - PF (Employer) = IF(PF, MIN(1800, ROUND((CTC - HRA - Bonus - (CTC * 8.125%)) * 12%)), 0)
        - Other Allowance = CEIL(CTC - Basic - HRA - Bonus - CCA - PF (Employer))  (round up)
        - Gross Total = Basic + HRA + Bonus + CCA + Other + PF_Employer + arrears (if present)
        - PF (Employee) = PF (Employer)
        - ESIC (Employee) = Controlled entirely by the esi_applicable boolean flag

        Args:
            gross_salary: The CTC per month (input)
            pf_applicable: Whether PF is applicable for this employee
            esi_applicable: Whether ESIC is applicable for this employee

        Returns:
            Dictionary with all calculated components
        """
        import math
        ctc = _to_decimal(gross_salary)

        # Basic Salary: MIN(25000, CTC * 50%)
        basic_50_pct = ctc * Decimal("0.50")
        basic = min(Decimal("25000"), basic_50_pct)
        basic = _round_decimal(basic)

        # HRA: Basic * 40%
        hra = _round_decimal(basic * Decimal("0.40"))

        # Bonus: FLOOR(Basic * 8.33%) - round down to no decimal points
        bonus_raw = basic * Decimal("0.0833")
        bonus = Decimal(str(math.floor(bonus_raw)))

        # CCA: IF(CTC > 50000, CTC * 20%, 0)
        if ctc > Decimal("50000"):
            cca = _round_decimal(ctc * Decimal("0.20"))
        else:
            cca = Decimal("0.00")

        # PF (Employer): IF(PF, MIN(1800, ROUND((CTC - HRA - Bonus - (CTC*8.125%)) * 12%)), 0)
        if pf_applicable:
            pf_base = ctc - hra - bonus - (ctc * Decimal("0.08125"))
            pf_calculated = _round_decimal(pf_base * Decimal("0.12"))
            pf_employer = Decimal(str(math.floor((max(Decimal("0.00"), min(Decimal("1800"), pf_calculated))))))
        else:
            pf_employer = Decimal("0.00")

        # Other Allowance: CEIL(CTC - Basic - HRA - Bonus - CCA - PF_Employer) - round up
        other_raw = ctc - basic - hra - bonus - cca - pf_employer
        other_allowance = Decimal(str(math.ceil(other_raw)))

        # Gross Total (Earnings): Basic + HRA + Bonus + CCA + Other + PF_Employer
        gross_total = basic + hra + bonus + cca + other_allowance + pf_employer
        gross_total = _round_rupee(gross_total)

        # PF (Employee): Same as PF (Employer)
        pf_employee = pf_employer

        # ESIC (Employee): Controlled strictly by the esi_applicable parameter (allows 6-month buffer rule)
        if esi_applicable:
            esi_employee = _round_rupee(basic * Decimal("0.0075"))
        else:
            esi_employee = Decimal("0.00")

        return {
            "basic_salary": basic,
            "hra": hra,
            "bonus": bonus,
            "cca": cca,
            "other_allowance": other_allowance,
            "pf_employer": pf_employer,
            "gross_total": gross_total,
            "pf_employee": pf_employee,
            "esi_employee": esi_employee,
        }

    def calculate_pro_rata_amount(
        self, monthly_amount: Decimal, paid_days: int, total_working_days: int
    ) -> Decimal:
        """
        Calculate pro-rated amount based on paid days.

        Formula: (monthly_amount / total_working_days) * paid_days
        """
        if total_working_days == 0:
            return Decimal("0.00")

        daily_rate = monthly_amount / Decimal(total_working_days)
        pro_rata = daily_rate * Decimal(paid_days)
        return pro_rata.quantize(Decimal("0.01"))

    def calculate_pf_employee(self, basic_salary: Decimal) -> Decimal:
        """Calculate employee PF contribution (12% of Basic)."""
        pf = basic_salary * Decimal(str(self.config.pf_rate_employee))
        return pf.quantize(Decimal("0.01"))

    def calculate_pf_employer(self, basic_salary: Decimal) -> Decimal:
        """Calculate employer PF contribution (12% of Basic)."""
        pf = basic_salary * Decimal(str(self.config.pf_rate_employer))
        return pf.quantize(Decimal("0.01"))

    def calculate_esi_employee(self, gross_earnings: Decimal) -> Decimal:
        """Calculate employee ESI contribution (0.75% of Gross)."""
        esi = gross_earnings * Decimal(str(self.config.esi_rate_employee))
        return esi.quantize(Decimal("0.01"))

    def calculate_esi_employer(self, gross_earnings: Decimal) -> Decimal:
        """Calculate employer ESI contribution (3.25% of Gross)."""
        esi = gross_earnings * Decimal(str(self.config.esi_rate_employer))
        return esi.quantize(Decimal("0.01"))

    def is_esi_applicable(self, gross_salary: Decimal) -> bool:
        """Check if ESI is applicable based on gross salary threshold."""
        return gross_salary <= Decimal(str(self.config.esi_gross_limit))

    def calculate_gross_earnings(
        self,
        basic: Decimal,
        hra: Decimal,
        bonus: Decimal,
        cca: Decimal,
        other: Decimal,
        pf_employer: Decimal,
        paid_days: int,
        total_working_days: int
    ) -> Decimal:
        """
        Calculate gross earnings with pro-rata.

        Sums all components and applies pro-rata based on paid days.
        """
        # Convert None values to 0
        basic = _to_decimal(basic)
        hra = _to_decimal(hra)
        bonus = _to_decimal(bonus)
        cca = _to_decimal(cca)
        other = _to_decimal(other)
        pf_employer = _to_decimal(pf_employer)

        monthly_gross = basic + hra + bonus + cca + other + pf_employer

        if paid_days == total_working_days:
            return monthly_gross.quantize(Decimal("0.01"))

        return self.calculate_pro_rata_amount(monthly_gross, paid_days, total_working_days)

    def calculate_total_deductions(
        self,
        pf_employee: Decimal,
        pf_employer: Decimal,
        esi_employee: Decimal,
        professional_tax: Decimal,
        loan_deduction: Decimal,
        tds: Decimal,
        other_deductions: Decimal,
    ) -> Decimal:
        """Calculate total deductions."""
        total = (
            _to_decimal(pf_employee)
            + _to_decimal(pf_employer)
            + _to_decimal(esi_employee)
            + _to_decimal(professional_tax)
            + _to_decimal(loan_deduction)
            + _to_decimal(tds)
            + _to_decimal(other_deductions)
        )
        return _round_rupee(total)

    def calculate_net_salary(
        self, gross_earnings: Decimal, total_deductions: Decimal
    ) -> Decimal:
        """Calculate net salary (take-home)."""
        net = gross_earnings - total_deductions
        return _round_rupee(net)

    def calculate_ctc_monthly(
        self,
        gross_earnings: Decimal,
        pf_employer: Decimal,
        esi_employer: Decimal,
    ) -> Decimal:
        """Calculate monthly Cost to Company."""
        ctc = gross_earnings + pf_employer
        return _round_rupee(ctc)

    def calculate_complete_payroll(
        self,
        basic: Decimal,
        hra: Decimal,
        bonus: Decimal,
        cca: Decimal,
        other_allowance: Decimal,
        paid_days: int,
        total_working_days: int,
        pf_applicable: bool,
        esi_applicable: bool = False,
        pf_employer_monthly: Decimal | None = None,
        gender: str | None = None,
        loan_deduction: Decimal = Decimal("0.00"),
        tds: Decimal = Decimal("0.00"),
        other_deductions: Decimal = Decimal("0.00"),
    ) -> dict:
        """
        Complete payroll calculation using updated formulas.

        PF Formula: MIN(₹1,800, (Gross - HRA - Bonus - (Gross×8.125%)) × 12%)
        ESIC Formula: Controlled entirely by the esi_applicable boolean flag
        Prof Tax Formula: IF(Female, IF(Gross > 24999, 200, 0), IF(Gross > 7500, 200, 0))

        Returns a dictionary with all calculated values.
        """
        import math

        # Pro-rate all earnings components from the existing salary structure values.
        # This preserves structure applicability (e.g., CCA remains if originally present).
        pro_rated_basic = _round_rupee(self.calculate_pro_rata_amount(_to_decimal(basic), paid_days, total_working_days))
        pro_rated_hra = _round_rupee(self.calculate_pro_rata_amount(_to_decimal(hra), paid_days, total_working_days))
        pro_rated_bonus = _round_rupee(self.calculate_pro_rata_amount(_to_decimal(bonus), paid_days, total_working_days))
        pro_rated_cca = _round_rupee(self.calculate_pro_rata_amount(_to_decimal(cca), paid_days, total_working_days))
        pro_rated_other = _round_rupee(self.calculate_pro_rata_amount(_to_decimal(other_allowance), paid_days, total_working_days))

        provisional_gross = (
            pro_rated_basic
            + pro_rated_hra
            + pro_rated_bonus
            + pro_rated_cca
            + pro_rated_other
        )

        # ═══════════════════════════════════════════════════════════════════
        # PF Calculation: MIN(₹1,800, (Basic + CCA + Other Allowance) × 12%)
        # ═══════════════════════════════════════════════════════════════════
        pf_employee = Decimal("0.00")
        pf_employer = Decimal("0.00")
        if pf_applicable:
            pf_base = pro_rated_basic + pro_rated_cca + pro_rated_other
            pf_calculated = _round_rupee(pf_base * Decimal("0.12"))
            pf_employer = max(Decimal("0.00"), min(Decimal("1800"), pf_calculated))
            pf_employee = pf_employer  # Both are same

        # Final gross includes employer PF
        gross_earnings = _round_rupee(provisional_gross + pf_employer)

        # ═══════════════════════════════════════════════════════════════════
        # ESIC Calculation
        # Employer ESIC is not used in this system.
        # ═══════════════════════════════════════════════════════════════════
        esi_employee = Decimal("0.00")
        esi_employer = Decimal("0.00")

        # Uses explicit esi_applicable flag (which handles 6-month statutory buffers)
        if esi_applicable:
            esi_employee = _round_rupee(pro_rated_basic * Decimal("0.0075"))

        # ═══════════════════════════════════════════════════════════════════
        # Professional Tax Calculation:
        # IF(Female, IF(Gross > 24999, 200, 0), IF(Gross > 7500, 200, 0))
        # ═══════════════════════════════════════════════════════════════════
        professional_tax = self.calculate_professional_tax(gross_earnings, gender)

        # Calculate totals
        total_deductions = self.calculate_total_deductions(
            pf_employee, pf_employer, esi_employee, professional_tax,
            loan_deduction, tds, other_deductions
        )
        net_salary = self.calculate_net_salary(gross_earnings, total_deductions)
        ctc_monthly = self.calculate_ctc_monthly(
            gross_earnings, pf_employer, esi_employer
        )

        return {
            "basic_salary": pro_rated_basic,
            "hra": pro_rated_hra,
            "bonus": pro_rated_bonus,
            "cca": pro_rated_cca,
            "other_allowance": pro_rated_other,
            "gross_earnings": gross_earnings,
            "pf_employee": pf_employee,
            "pf_employer": pf_employer,
            "esi_employee": esi_employee,
            "esi_employer": esi_employer,
            "professional_tax": professional_tax,
            "total_deductions": total_deductions,
            "net_salary": net_salary,
            "ctc_monthly": ctc_monthly,
        }

    def calculate_professional_tax(
        self, gross_salary: Decimal, gender: str | None = None
    ) -> Decimal:
        """
        Calculate professional tax based on gender and gross salary.

        Formula:
        - IF(Female, IF(Gross > 24999, 200, 0), IF(Gross > 7500, 200, 0))

        Args:
            gross_salary: The gross salary for the month
            gender: Employee's gender ('Male', 'Female', 'Other', or None)

        Returns:
            Professional tax amount (₹200 or ₹0)
        """
        gross = _to_decimal(gross_salary)

        if gender and gender.lower() == "female":
            # Female: PT applicable only if Gross > 24999
            if gross > Decimal("24999"):
                return Decimal("200")
            else:
                return Decimal("0")
        else:
            # Male/Other/Unknown: PT applicable if Gross > 7500
            if gross > Decimal("7500"):
                return Decimal("200")
            else:
                return Decimal("0")
