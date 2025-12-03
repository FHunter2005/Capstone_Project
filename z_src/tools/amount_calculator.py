"""
Amount Calculator Tool - Financial calculations

These are precise calculations that should NOT use AI.
Money requires exactness - AI is probabilistic.
"""

from datetime import datetime
from langfuse import observe


class AmountCalculator:
    """Tool for financial calculations in contracts."""

    @observe()
    def calculate_total_value(
        self,
        amount: float,
        frequency: str,
        start_date: str,
        end_date: str
    ) -> float:
        """Calculate total contract value over duration.

        Args:
            amount: Payment amount per period
            frequency: Payment frequency (monthly, annual, quarterly, etc.)
            start_date: Contract start date (YYYY-MM-DD)
            end_date: Contract end date (YYYY-MM-DD)

        Returns:
            Total value over contract lifetime

        Example:
            >>> calc = AmountCalculator()
            >>> calc.calculate_total_value(1000, "monthly", "2024-01-01", "2024-12-31")
            12000.0
        """
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        duration_days = (end - start).days

        # Determine periods based on frequency
        frequency_lower = frequency.lower()

        if 'month' in frequency_lower:
            periods = duration_days / 30.44  # Average month length
        elif 'year' in frequency_lower or 'annual' in frequency_lower:
            periods = duration_days / 365.25  # Account for leap years
        elif 'quarter' in frequency_lower:
            periods = duration_days / 91.31  # ~3 months
        elif 'week' in frequency_lower:
            periods = duration_days / 7
        elif 'day' in frequency_lower or 'daily' in frequency_lower:
            periods = duration_days
        else:
            # One-time payment
            periods = 1

        return round(amount * periods, 2)

    @observe()
    def calculate_monthly_rate(self, annual_amount: float) -> float:
        """Convert annual amount to monthly.

        Args:
            annual_amount: Annual payment amount

        Returns:
            Monthly payment amount

        Example:
            >>> calc = AmountCalculator()
            >>> calc.calculate_monthly_rate(12000)
            1000.0
        """
        return round(annual_amount / 12, 2)

    @observe()
    def calculate_payment_for_period(
        self,
        total_amount: float,
        start_date: str,
        end_date: str,
        period_days: int
    ) -> float:
        """Calculate proportional payment for a partial period.

        Args:
            total_amount: Full period payment amount
            start_date: Period start date
            end_date: Period end date
            period_days: Days in a full period

        Returns:
            Proportional payment amount

        Example:
            >>> calc = AmountCalculator()
            >>> # 15 days of a 30-day month at $1000/month
            >>> calc.calculate_payment_for_period(1000, "2024-01-01", "2024-01-15", 30)
            500.0
        """
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        actual_days = (end - start).days

        return round((total_amount / period_days) * actual_days, 2)

    @observe()
    def calculate_discount(
        self,
        original_amount: float,
        discount_percent: float
    ) -> dict:
        """Calculate discount and final amount.

        Args:
            original_amount: Original price
            discount_percent: Discount percentage (e.g., 10 for 10%)

        Returns:
            Dictionary with discount_amount and final_amount

        Example:
            >>> calc = AmountCalculator()
            >>> calc.calculate_discount(1000, 10)
            {'discount_amount': 100.0, 'final_amount': 900.0}
        """
        discount_amount = round(original_amount * (discount_percent / 100), 2)
        final_amount = round(original_amount - discount_amount, 2)

        return {
            "discount_amount": discount_amount,
            "final_amount": final_amount
        }

    @observe()
    def calculate_penalty(
        self,
        base_amount: float,
        penalty_percent: float,
        days_late: int
    ) -> dict:
        """Calculate late payment penalty.

        Args:
            base_amount: Base payment amount
            penalty_percent: Penalty rate per day (as percentage)
            days_late: Number of days late

        Returns:
            Dictionary with penalty_amount and total_owed

        Example:
            >>> calc = AmountCalculator()
            >>> calc.calculate_penalty(1000, 0.1, 30)  # 0.1% per day for 30 days
            {'penalty_amount': 30.0, 'total_owed': 1030.0}
        """
        penalty_amount = round(
            base_amount * (penalty_percent / 100) * days_late,
            2
        )
        total_owed = round(base_amount + penalty_amount, 2)

        return {
            "penalty_amount": penalty_amount,
            "total_owed": total_owed
        }

    @observe()
    def compare_amounts(self, amount1: float, amount2: float) -> dict:
        """Compare two amounts and calculate difference.

        Args:
            amount1: First amount
            amount2: Second amount

        Returns:
            Dictionary with difference and percent_change

        Example:
            >>> calc = AmountCalculator()
            >>> calc.compare_amounts(1000, 1200)
            {'difference': 200.0, 'percent_change': 20.0}
        """
        difference = round(amount2 - amount1, 2)
        percent_change = round((difference / amount1) * 100, 2) if amount1 != 0 else 0

        return {
            "difference": difference,
            "percent_change": percent_change
        }
