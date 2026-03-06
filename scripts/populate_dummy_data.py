"""Populate database with dummy data for testing."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from datetime import date
from decimal import Decimal

from staffly.database import get_db, init_db
from staffly.database.models import Employee, SalaryStructure, PayrollPeriod, MonthlyPayroll
from staffly.services.calculation_service import CalculationService


def create_dummy_data():
    """Create dummy employees and salary structures."""
    
    # Sample employee data based on the reference image
    employees_data = [
        {
            "code": "W007",
            "first_name": "Munna",
            "middle_name": "Prasad",
            "last_name": "Vishwakarma",
            "gender": "Male",
            "designation": "Production Engineer",
            "department": "Production",
            "branch": "Head Office",
            "doj": date(1992, 1, 1),
            "ctc": 74000
        },
        {
            "code": "W003",
            "first_name": "Ramesh",
            "last_name": "Poojari",
            "gender": "Male",
            "designation": "Technician",
            "department": "Production",
            "branch": "Head Office",
            "doj": date(1998, 6, 1),
            "ctc": 35500
        },
        {
            "code": "H003",
            "first_name": "Rajan",
            "last_name": "Fernandes",
            "gender": "Male",
            "designation": "General Manager - Marketing",
            "department": "Sales",
            "branch": "Head Office",
            "doj": date(2001, 11, 23),
            "ctc": 57500
        },
        {
            "code": "W008",
            "first_name": "Sanjay",
            "last_name": "Jadhav",
            "gender": "Male",
            "designation": "Logistic Executive",
            "department": "Production",
            "branch": "Head Office",
            "doj": date(2004, 6, 28),
            "ctc": 25200
        },
        {
            "code": "W005",
            "first_name": "Darshana",
            "last_name": "Bhagat",
            "gender": "Female",
            "designation": "PCB Assembler",
            "department": "Production",
            "branch": "Head Office",
            "doj": date(2007, 5, 11),
            "ctc": 35500
        },
        {
            "code": "H002",
            "first_name": "Kavita",
            "last_name": "Sawant",
            "gender": "Female",
            "designation": "Accounts Manager",
            "department": "Accounts",
            "branch": "Head Office",
            "doj": date(2007, 9, 3),
            "ctc": 70200
        },
        {
            "code": "D002",
            "first_name": "Pankaj",
            "middle_name": "Kumar",
            "last_name": "Chodhary",
            "gender": "Male",
            "designation": "Service Engineer",
            "department": "Service",
            "branch": "Delhi Branch",
            "doj": date(2013, 3, 11),
            "ctc": 44000
        },
        {
            "code": "W022",
            "first_name": "Komal",
            "last_name": "Patil",
            "gender": "Female",
            "designation": "Production Manager",
            "department": "Production",
            "branch": "Head Office",
            "doj": date(2015, 6, 17),
            "ctc": 66500
        },
        {
            "code": "W050",
            "first_name": "Ankit",
            "last_name": "Pamar",
            "gender": "Male",
            "designation": "Accounts & Admin Executive",
            "department": "Accounts",
            "branch": "Head Office",
            "doj": date(2016, 10, 17),
            "ctc": 45000
        },
        {
            "code": "W051",
            "first_name": "Jayesh",
            "last_name": "Chogle",
            "gender": "Male",
            "designation": "Production Engineer",
            "department": "Production",
            "branch": "Head Office",
            "doj": date(2016, 11, 14),
            "ctc": 42500
        },
        {
            "code": "H014",
            "first_name": "Aparna",
            "last_name": "Raithatha",
            "gender": "Female",
            "designation": "Sales Executive",
            "department": "Sales",
            "branch": "Head Office",
            "doj": date(2017, 2, 7),
            "ctc": 52500
        },
        {
            "code": "H018",
            "first_name": "Ravin",
            "last_name": "Gaikwad",
            "gender": "Male",
            "designation": "Sales Executive",
            "department": "Sales",
            "branch": "Head Office",
            "doj": date(2018, 1, 15),
            "ctc": 53200
        },
        {
            "code": "W052",
            "first_name": "Gaurav",
            "last_name": "Sune",
            "gender": "Male",
            "designation": "Software Engineer",
            "department": "Production",
            "branch": "Head Office",
            "doj": date(2018, 4, 9),
            "ctc": 34000
        },
        {
            "code": "W053",
            "first_name": "Hasanul",
            "middle_name": "Bana",
            "last_name": "Siddiqui",
            "gender": "Male",
            "designation": "Production Engineer",
            "department": "Production",
            "branch": "Head Office",
            "doj": date(2018, 11, 1),
            "ctc": 32500
        },
        {
            "code": "H020",
            "first_name": "Aniket",
            "last_name": "Sawant",
            "gender": "Male",
            "designation": "Project Engineer",
            "department": "Sales",
            "branch": "Head Office",
            "doj": date(2020, 12, 10),
            "ctc": 58000
        },
        {
            "code": "EW055",
            "first_name": "Mayur",
            "last_name": "Bhoir",
            "gender": "Male",
            "designation": "PCB Assembler",
            "department": "Production",
            "branch": "Head Office",
            "doj": date(2021, 9, 1),
            "ctc": 24600
        },
        {
            "code": "EW056",
            "first_name": "Supriya",
            "last_name": "Padel",
            "gender": "Female",
            "designation": "PCB Assembler",
            "department": "Production",
            "branch": "Head Office",
            "doj": date(2022, 1, 1),
            "ctc": 21600
        },
        {
            "code": "HO023",
            "first_name": "Sagar",
            "last_name": "Kadam",
            "gender": "Male",
            "designation": "Office Assistant",
            "department": "Sales",
            "branch": "Head Office",
            "doj": date(2022, 8, 1),
            "ctc": 18250
        },
        {
            "code": "HO024",
            "first_name": "Rahul",
            "last_name": "Jadhav",
            "gender": "Male",
            "designation": "Office Assistant",
            "department": "Sales",
            "branch": "Head Office",
            "doj": date(2022, 8, 1),
            "ctc": 18750
        },
        {
            "code": "EW060",
            "first_name": "Yash",
            "last_name": "Ghumre",
            "gender": "Male",
            "designation": "Jr. Technician",
            "department": "Production",
            "branch": "Head Office",
            "doj": date(2022, 9, 1),
            "ctc": 25100
        },
        {
            "code": "EW063",
            "first_name": "Shivraj",
            "last_name": "Mahajan",
            "gender": "Male",
            "designation": "Service Engineer",
            "department": "Service",
            "branch": "Delhi Branch",
            "doj": date(2023, 10, 3),
            "ctc": 33200
        },
        {
            "code": "EW064",
            "first_name": "Akash",
            "last_name": "Gholap",
            "gender": "Male",
            "designation": "Service Engineer",
            "department": "Service",
            "branch": "Mumbai Branch",
            "doj": date(2023, 10, 16),
            "ctc": 29800
        },
        {
            "code": "EW065",
            "first_name": "Jatin",
            "last_name": "Bhosale",
            "gender": "Male",
            "designation": "Embedded Engineer",
            "department": "R&D",
            "branch": "Head Office",
            "doj": date(2023, 12, 11),
            "ctc": 73200
        },
        {
            "code": "EW066",
            "first_name": "Pratik",
            "last_name": "Lotankar",
            "gender": "Male",
            "designation": "Embedded Engineer",
            "department": "R&D",
            "branch": "Head Office",
            "doj": date(2023, 12, 11),
            "ctc": 69200
        },
        {
            "code": "EW067",
            "first_name": "Jyoti",
            "last_name": "Sawant",
            "gender": "Female",
            "designation": "Quality Incharge",
            "department": "Quality",
            "branch": "Head Office",
            "doj": date(2024, 1, 2),
            "ctc": 29100
        },
        {
            "code": "HO067",
            "first_name": "Deepu",
            "last_name": "Raj",
            "gender": "Male",
            "designation": "Sales Engineer",
            "department": "Sales",
            "branch": "Chennai Branch",
            "doj": date(2024, 4, 2),
            "ctc": 35000
        },
        {
            "code": "EW068",
            "first_name": "Vicky",
            "last_name": "Kumar",
            "gender": "Male",
            "designation": "Fitter",
            "department": "Production",
            "branch": "Head Office",
            "doj": date(2024, 6, 1),
            "ctc": 21200
        },
        {
            "code": "EW069",
            "first_name": "Waman",
            "last_name": "Bandekar",
            "gender": "Male",
            "designation": "Technician",
            "department": "Production",
            "branch": "Head Office",
            "doj": date(2024, 4, 7),
            "ctc": 15750
        },
    ]
    
    db = get_db()
    calc_service = CalculationService()
    
    with db.get_session() as session:
        # Check if data already exists
        existing = session.query(Employee).count()
        if existing > 0:
            print(f"Database already has {existing} employees. Clearing existing data...")
            session.query(MonthlyPayroll).delete()
            session.query(PayrollPeriod).delete()
            session.query(SalaryStructure).delete()
            session.query(Employee).delete()
            session.commit()
        
        print("Creating employees and salary structures...")
        
        for emp_data in employees_data:
            # Create employee
            employee = Employee(
                employee_code=emp_data["code"],
                first_name=emp_data["first_name"],
                middle_name=emp_data.get("middle_name"),
                last_name=emp_data["last_name"],
                gender=emp_data.get("gender"),
                designation=emp_data.get("designation", "Staff"),
                department=emp_data.get("department"),
                branch=emp_data.get("branch"),
                date_of_joining=emp_data.get("doj", date(2024, 1, 1)),
                is_active=True,
            )
            session.add(employee)
            session.flush()  # Get the ID
            
            # Create salary structure
            ctc = Decimal(str(emp_data.get("ctc", 0)))
            calc = calc_service.calculate_salary_structure_from_gross(ctc, pf_applicable=True)
            salary = SalaryStructure(
                employee_id=employee.id,
                effective_from=emp_data.get("doj", date(2024, 1, 1)),
                effective_to=None,  # Current
                basic_salary=calc["basic_salary"],
                hra=calc["hra"],
                bonus=calc["bonus"],
                cca=calc["cca"],
                other_allowance=calc["other_allowance"],
                pf_employer=calc["pf_employer"],
            )
            session.add(salary)
            
            full_name = f"{emp_data['first_name']} {emp_data.get('middle_name', '')} {emp_data['last_name']}".replace("  ", " ")
            print(f"  ✓ {emp_data['code']} - {full_name}")
        
        session.commit()
        
        # Create a payroll period for testing
        period = PayrollPeriod(
            year=2026,
            month=1,
            period_label="Jan 2026",
            working_days=26,
            is_locked=False,
        )
        session.add(period)
        session.commit()
        
        print(f"\n✅ Created {len(employees_data)} employees with salary structures")
        print(f"✅ Created payroll period: January 2026")


if __name__ == "__main__":
    print("=" * 60)
    print("Staffly - Dummy Data Generator")
    print("=" * 60)
    
    from staffly.config import get_config
    config = get_config()
    init_db(config.db_path)
    create_dummy_data()
    
    print("\n🎉 Done! You can now run the application.")
