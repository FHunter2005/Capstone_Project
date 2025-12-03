"""
Date Calculator Tool - Date-related calculations

These are precise calculations that should NOT use AI.
AI is probabilistic - dates require exactness.
"""

from datetime import datetime, timedelta
from langfuse import observe


class DateCalculator:
    """Tool for date calculations in contracts."""

    @observe()
    def days_until(self, target_date: str) -> int:
        """Calculate days until target date.

        Args:
            target_date: Date in YYYY-MM-DD format

        Returns:
            Days until date (negative if past)

        Example:
            >>> calc = DateCalculator()
            >>> calc.days_until("2024-12-31")
            45  # (if today is Nov 16, 2024)
        """
        target = datetime.fromisoformat(target_date)
        today = datetime.now()
        delta = target - today
        return delta.days

    @observe()
    def get_renewal_date(self, expiry_date: str, days_before: int = 90) -> str:
        """Calculate when renewal discussion should start.

        Args:
            expiry_date: Contract expiration date (YYYY-MM-DD)
            days_before: Days before expiry to start renewal (default 90)

        Returns:
            Renewal start date in YYYY-MM-DD format

        Example:
            >>> calc = DateCalculator()
            >>> calc.get_renewal_date("2024-12-31", days_before=90)
            "2024-10-02"
        """
        expiry = datetime.fromisoformat(expiry_date)
        renewal = expiry - timedelta(days=days_before)
        return renewal.date().isoformat()

    @observe()
    def add_business_days(self, start_date: str, days: int) -> str:
        """Add business days to a date (skipping weekends).

        Args:
            start_date: Starting date (YYYY-MM-DD)
            days: Number of business days to add

        Returns:
            Resulting date in YYYY-MM-DD format

        Example:
            >>> calc = DateCalculator()
            >>> calc.add_business_days("2024-11-15", 5)  # Friday
            "2024-11-22"  # Next Friday (skips weekend)
        """
        current = datetime.fromisoformat(start_date)
        added = 0

        while added < days:
            current += timedelta(days=1)
            # Monday = 0, Friday = 4, Saturday = 5, Sunday = 6
            if current.weekday() < 5:  # Weekday
                added += 1

        return current.date().isoformat()

    @observe()
    def get_duration_months(self, start_date: str, end_date: str) -> float:
        """Calculate duration in months between two dates.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Duration in months (approximate)

        Example:
            >>> calc = DateCalculator()
            >>> calc.get_duration_months("2024-01-01", "2024-07-01")
            6.0
        """
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        delta = end - start
        # Approximate: 30.44 days per month
        return delta.days / 30.44

    @observe()
    def is_weekend(self, date: str) -> bool:
        """Check if date falls on a weekend.

        Args:
            date: Date to check (YYYY-MM-DD)

        Returns:
            True if Saturday or Sunday

        Example:
            >>> calc = DateCalculator()
            >>> calc.is_weekend("2024-11-16")  # Saturday
            True
        """
        dt = datetime.fromisoformat(date)
        return dt.weekday() >= 5  # Saturday = 5, Sunday = 6
