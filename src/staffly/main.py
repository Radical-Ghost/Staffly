"""Staffly - Desktop Payroll Application entry point."""

import sys

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt

from staffly.config import get_config
from staffly.database import init_db, get_db
from staffly.database.models.company import Company
from staffly.database.repositories import CompanyRepository


def initialize_application() -> None:
    """Initialize the application (database, config, etc.)."""
    config = get_config()

    # Ensure data directory exists
    config.ensure_directories()

    # Initialize database
    print(f"Initializing database at: {config.db_path}")
    init_db(config.db_path, echo=config.db_echo)
    print("Database initialized successfully.")


def ensure_default_companies() -> None:
    """Ensure ENDEE and HNL always exist and are the only active companies."""
    default_companies = [
        {"code": "ENDEE", "name": "ENDEE ENGINEERS PVT. LTD."},
        {"code": "HNL", "name": "HNL"},
    ]
    allowed_codes = {item["code"] for item in default_companies}

    db = get_db()
    with db.get_session() as session:
        company_repo = CompanyRepository(session)
        existing_companies = company_repo.get_all_ordered()
        by_code_upper = {(company.code or "").upper(): company for company in existing_companies}

        for item in default_companies:
            company = by_code_upper.get(item["code"])
            if company is None:
                company = Company(
                    code=item["code"],
                    name=item["name"],
                    is_active=True,
                )
                session.add(company)
            else:
                company.code = item["code"]
                company.name = item["name"]
                company.is_active = True

        for company in existing_companies:
            if (company.code or "").upper() not in allowed_codes:
                company.is_active = False

        session.commit()


def main() -> int:
    """Main entry point for the application."""
    try:
        # Initialize backend
        initialize_application()
        ensure_default_companies()

        # Enable high DPI support (must be set before QApplication)
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

        # Create Qt application
        app = QApplication(sys.argv)
        app.setApplicationName("Staffly")
        app.setApplicationVersion("1.0.0")
        app.setOrganizationName("Staffly")

        # Apply global theme before creating any windows
        from staffly.ui.theme import load_theme, get_current_theme
        current_theme = get_current_theme()  # Returns saved preference (mocha/latte)
        load_theme(current_theme)

        # Load active companies (used by in-app splash selector)
        db = get_db()
        with db.get_session() as session:
            company_repo = CompanyRepository(session)
            companies = company_repo.get_all_active()

        if not companies:
            QMessageBox.critical(
                None,
                "No Companies",
                "No active companies found. Please seed company data first."
            )
            return 1

        selector_items = [
            (company.id, company.code, company.name)
            for company in companies
            if (company.code or "").upper() in {"HNL", "ENDEE"}
        ]
        if not selector_items:
            selector_items = [(company.id, company.code, company.name) for company in companies]

        # Import and create main window
        from staffly.ui import MainWindow
        window = MainWindow(companies=selector_items)
        window.showMaximized()

        # Run the event loop
        return app.exec()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

    finally:
        # Clean up database connection
        db = get_db()
        if db.is_initialized:
            db.close()


if __name__ == "__main__":
    sys.exit(main())
