# Staffly - Desktop Payroll Application

A Windows desktop payroll application designed to replace Excel-based salary management with proper data separation and audit-safe history.

## Overview

Staffly manages employee payroll with clean separation between:

-   **Salary Definition** → What the employee is entitled to (contractual)
-   **Payroll Period** → Which month the payroll belongs to
-   **Monthly Payroll Execution** → What actually happened (attendance + calculations)

## Tech Stack

Component

Technology

Logic

Python 3.11+

UI

PySide6

Database

SQLite

ORM

SQLAlchemy

Reports

ReportLab

Packaging

PyInstaller

Package Manager

uv

## Database Schema

### Tables

1.  **employees** - Employee master data
2.  **salary_structures** - Salary definitions with effective dates
3.  **payroll_periods** - Month registry with lock status
4.  **monthly_payroll** - Snapshot of monthly calculations

## Core Features

-   Employee CRUD operations
-   Salary structure management with effective dates
-   Payroll period management with locking
-   Attendance entry per employee per month
-   Automatic payroll calculations
-   Salary slip generation (PDF)
-   Historical data preservation

## Payroll Calculation Rules

### Earnings

-   Basic Salary
-   House Rent Allowance (HRA)
-   Conveyance Allowance
-   Bonus
-   City Compensatory Allowance (CCA)
-   Other Allowance

### Deductions

-   Provident Fund (Employee) - 12% of Basic if applicable
-   Employee State Insurance (Employee) - 0.75% of Gross if applicable
-   Professional Tax
-   Loan Deduction
-   Tax Deducted at Source (TDS)

### Employer Contributions

-   Provident Fund (Employer) - 12% of Basic
-   Employee State Insurance (Employer) - 3.25% of Gross

## Setup

```bash
# Clone repository
git clone <repo-url>
cd Staffly

# Install dependencies using uv
uv sync

# Run application
uv run python -m staffly.main
```

## Building Executable

```bash
# Build single-file .exe using existing spec
uv run pyinstaller --noconfirm --clean Staffly.spec
```

## License

Proprietary - All rights reserved
