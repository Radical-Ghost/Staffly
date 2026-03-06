"""Application configuration settings."""

from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AppConfig:
    """
    Application configuration.
    
    Centralizes all configuration settings for the application.
    """

    # Application Info
    app_name: str = "Staffly"
    app_version: str = "0.1.0"

    # Company Info (for salary slips)
    company_name: str = "ENDEE ENGINEERS PVT. LTD."
    company_address: str = "D-120, Ansa Industrial Estate, Saki Vihar Road, Saki Naka, Andheri (East), Mumbai - 400072."

    # Paths - config.py is at src/staffly/config.py, so parent.parent.parent = Staffly/
    base_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent)
    data_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "data")

    @property
    def db_path(self) -> Path:
        """Get the database file path."""
        return self.data_dir / "staffly.db"

    # Database Settings
    db_echo: bool = False  # Set True to log SQL queries

    # Payroll Calculation Settings
    pf_rate_employee: float = 0.12  # 12% of Basic
    pf_rate_employer: float = 0.12  # 12% of Basic
    esi_rate_employee: float = 0.0075  # 0.75% of Gross
    esi_rate_employer: float = 0.0325  # 3.25% of Gross
    esi_gross_limit: float = 21000.00  # ESI applicable if gross <= this

    # Default Working Days per Month
    default_working_days: int = 26

    # UI Settings
    window_title: str = "Staffly - Payroll Management"
    window_width: int = 1200
    window_height: int = 800

    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)


# Global config instance
config = AppConfig()


def get_config() -> AppConfig:
    """Get the global configuration instance."""
    return config
