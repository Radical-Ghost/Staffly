"""Populate database with Jan 2026 payroll data from Excel images.

This script:
1. Truncates all existing data
2. Creates two companies: ENDEE ENGINEERS PVT. LTD. and HNL
3. Populates employees with salary structures
4. Creates January 2026 payroll period with attendance and payroll data
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from datetime import date
from decimal import Decimal

from staffly.database import get_db, init_db
from staffly.database.models import Company, Employee, SalaryStructure, PayrollPeriod, MonthlyPayroll


def truncate_database():
    """Clear all data from the database."""
    db = get_db()
    
    with db.get_session() as session:
        print("Truncating existing data...")
        session.query(MonthlyPayroll).delete()
        session.query(PayrollPeriod).delete()
        session.query(SalaryStructure).delete()
        session.query(Employee).delete()
        session.query(Company).delete()
        session.commit()
        print("  ✓ Database truncated")


def create_companies():
    """Create the two companies."""
    db = get_db()
    
    companies_data = [
        {
            "name": "ENDEE ENGINEERS PVT. LTD.",
            "code": "Endee",
            "address": "Mumbai, Maharashtra",
            "is_active": True,
        },
        {
            "name": "HNL",
            "code": "HNL",
            "address": "Mumbai, Maharashtra",
            "is_active": True,
        },
    ]
    
    with db.get_session() as session:
        print("\nCreating companies...")
        for data in companies_data:
            company = Company(**data)
            session.add(company)
            print(f"  ✓ {data['name']} ({data['code']})")
        session.commit()
    
    return companies_data


def get_company_id(session, code: str) -> int:
    """Get company ID by code."""
    company = session.query(Company).filter(Company.code == code).first()
    return company.id if company else None


def create_employees_and_payroll():
    """Create employees, salary structures, and Jan 2026 payroll data."""
    
    # Data extracted from Excel images for Jan 2026
    # Format: name, present_days, pl, sl, cl, paid_days, absent_days, late_marks,
    #         pf_applicable, esic_applicable, basic, hra, conveyance, bonus, cca, other_allowance,
    #         epf_employer, esic_employer, gross, pf_employee, epf_employee, esic_employee, 
    #         esic_employer_ded, prof_tax, loan, tds, net_total, pl_balance, sl_balance, cl_balance,
    #         company_code
    
    employees_data = [
        # From Sheet 1 (Endee employees - based on Excel image 1)
        {"code": "W007", "name": "Munna Prasad Vishwakarma", "company": "Endee",
         "designation": "Production Engineer", "department": "Production",
         "doj": date(1992, 1, 1), "gender": "Male",
         "present": 27, "pl": 0, "sl": 0, "cl": 0, "paid": 27, "absent": 0, "late": 0,
         "pf": True, "esic": False,
         "basic": 25000, "hra": 10000, "conveyance": 0, "bonus": 2083, "cca": 36917, "other": 0,
         "gross": 74000,
         "pf_emp": 3000, "epf_emp": 550, "esic_emp": 0, "prof_tax": 200, "loan": 0, "tds": 0,
         "net": 70250},
         
        {"code": "W003", "name": "Ramesh Poojari", "company": "Endee",
         "designation": "Technician", "department": "Production",
         "doj": date(1998, 6, 1), "gender": "Male",
         "present": 27, "pl": 0, "sl": 0, "cl": 0, "paid": 27, "absent": 0, "late": 0,
         "pf": True, "esic": False,
         "basic": 14350, "hra": 5740, "conveyance": 0, "bonus": 1196, "cca": 14464, "other": 0,
         "gross": 35750,
         "pf_emp": 1722, "epf_emp": 550, "esic_emp": 0, "prof_tax": 200, "loan": 0, "tds": 0,
         "net": 33278},
         
        {"code": "W008", "name": "Sanjay Jadhav", "company": "Endee",
         "designation": "Logistic Executive", "department": "Production",
         "doj": date(2004, 6, 28), "gender": "Male",
         "present": 27, "pl": 0, "sl": 0, "cl": 0, "paid": 27, "absent": 0, "late": 0,
         "pf": True, "esic": False,
         "basic": 14350, "hra": 5740, "conveyance": 0, "bonus": 1196, "cca": 3514, "other": 1800,
         "gross": 26600,
         "pf_emp": 1722, "epf_emp": 550, "esic_emp": 0, "prof_tax": 200, "loan": 0, "tds": 0,
         "net": 24128},
         
        {"code": "W005", "name": "Darshana Bhagat", "company": "Endee",
         "designation": "PCB Assembler", "department": "Production",
         "doj": date(2007, 5, 11), "gender": "Female",
         "present": 27, "pl": 0, "sl": 0, "cl": 0, "paid": 27, "absent": 0, "late": 0,
         "pf": True, "esic": False,
         "basic": 14350, "hra": 5740, "conveyance": 0, "bonus": 1196, "cca": 14464, "other": 0,
         "gross": 35750,
         "pf_emp": 1722, "epf_emp": 550, "esic_emp": 0, "prof_tax": 200, "loan": 0, "tds": 0,
         "net": 33278},
         
        {"code": "D002", "name": "Pankaj Kumar Chodhary", "company": "Endee",
         "designation": "Service Engineer", "department": "Service",
         "doj": date(2013, 3, 11), "gender": "Male",
         "present": 27, "pl": 0, "sl": 0, "cl": 0, "paid": 27, "absent": 0, "late": 0,
         "pf": True, "esic": False,
         "basic": 20600, "hra": 8240, "conveyance": 0, "bonus": 1717, "cca": 13443, "other": 0,
         "gross": 44000,
         "pf_emp": 2472, "epf_emp": 550, "esic_emp": 0, "prof_tax": 200, "loan": 0, "tds": 0,
         "net": 40778},
         
        {"code": "W050", "name": "Ankit Parmar", "company": "Endee",
         "designation": "Accounts & Admin Executive", "department": "Accounts",
         "doj": date(2016, 10, 17), "gender": "Male",
         "present": 27, "pl": 0, "sl": 0, "cl": 0, "paid": 27, "absent": 0, "late": 0,
         "pf": True, "esic": False,
         "basic": 20600, "hra": 8240, "conveyance": 0, "bonus": 1717, "cca": 14443, "other": 0,
         "gross": 45000,
         "pf_emp": 2472, "epf_emp": 550, "esic_emp": 0, "prof_tax": 200, "loan": 0, "tds": 0,
         "net": 41778},
         
        {"code": "W051", "name": "Jayesh Chogle", "company": "Endee",
         "designation": "Production Engineer", "department": "Production",
         "doj": date(2016, 11, 14), "gender": "Male",
         "present": 27, "pl": 0, "sl": 0, "cl": 0, "paid": 27, "absent": 0, "late": 0,
         "pf": True, "esic": False,
         "basic": 20600, "hra": 8240, "conveyance": 0, "bonus": 1717, "cca": 11943, "other": 0,
         "gross": 42500,
         "pf_emp": 2472, "epf_emp": 550, "esic_emp": 0, "prof_tax": 200, "loan": 0, "tds": 0,
         "net": 39278},
         
        {"code": "W052", "name": "Gaurav Sune", "company": "Endee",
         "designation": "Software Engineer", "department": "Production",
         "doj": date(2018, 4, 9), "gender": "Male",
         "present": 27, "pl": 0, "sl": 0, "cl": 0, "paid": 27, "absent": 0, "late": 0,
         "pf": True, "esic": False,
         "basic": 20600, "hra": 8240, "conveyance": 0, "bonus": 1717, "cca": 3443, "other": 0,
         "gross": 34000,
         "pf_emp": 2472, "epf_emp": 550, "esic_emp": 0, "prof_tax": 200, "loan": 0, "tds": 0,
         "net": 30778},
         
        {"code": "W053", "name": "Hasanul Bana Siddiqui", "company": "Endee",
         "designation": "Production Engineer", "department": "Production",
         "doj": date(2018, 11, 1), "gender": "Male",
         "present": 26, "pl": 1, "sl": 0, "cl": 0, "paid": 27, "absent": 0, "late": 0,
         "pf": True, "esic": False,
         "basic": 20600, "hra": 8240, "conveyance": 0, "bonus": 1717, "cca": 1943, "other": 0,
         "gross": 32500,
         "pf_emp": 2472, "epf_emp": 550, "esic_emp": 0, "prof_tax": 200, "loan": 0, "tds": 0,
         "net": 29278},
         
        {"code": "EW055", "name": "Mayur Bhoir", "company": "Endee",
         "designation": "PCB Assembler", "department": "Production",
         "doj": date(2021, 9, 1), "gender": "Male",
         "present": 27, "pl": 0, "sl": 0, "cl": 0, "paid": 27, "absent": 0, "late": 0,
         "pf": True, "esic": True,
         "basic": 10000, "hra": 4000, "conveyance": 0, "bonus": 833, "cca": 8067, "other": 1800,
         "gross": 24700,
         "pf_emp": 1200, "epf_emp": 550, "esic_emp": 185, "prof_tax": 200, "loan": 0, "tds": 0,
         "net": 22565},
         
        {"code": "EW056", "name": "Supriya Padel", "company": "Endee",
         "designation": "PCB Assembler", "department": "Production",
         "doj": date(2022, 1, 1), "gender": "Female",
         "present": 27, "pl": 0, "sl": 0, "cl": 0, "paid": 27, "absent": 0, "late": 0,
         "pf": True, "esic": True,
         "basic": 10000, "hra": 4000, "conveyance": 0, "bonus": 833, "cca": 5067, "other": 1800,
         "gross": 21700,
         "pf_emp": 1200, "epf_emp": 550, "esic_emp": 163, "prof_tax": 200, "loan": 0, "tds": 0,
         "net": 19587},
         
        {"code": "EW060", "name": "Yash Ghumre", "company": "Endee",
         "designation": "Jr. Technician", "department": "Production",
         "doj": date(2022, 9, 1), "gender": "Male",
         "present": 27, "pl": 0, "sl": 0, "cl": 0, "paid": 27, "absent": 0, "late": 0,
         "pf": True, "esic": True,
         "basic": 10000, "hra": 4000, "conveyance": 0, "bonus": 833, "cca": 8567, "other": 1800,
         "gross": 25200,
         "pf_emp": 1200, "epf_emp": 550, "esic_emp": 189, "prof_tax": 200, "loan": 0, "tds": 0,
         "net": 23061},
         
        {"code": "EW063", "name": "Shivraj Mahajan", "company": "Endee",
         "designation": "Service Engineer", "department": "Service",
         "doj": date(2023, 10, 3), "gender": "Male",
         "present": 27, "pl": 0, "sl": 0, "cl": 0, "paid": 27, "absent": 0, "late": 0,
         "pf": True, "esic": False,
         "basic": 14350, "hra": 5740, "conveyance": 0, "bonus": 1196, "cca": 10514, "other": 1800,
         "gross": 33600,
         "pf_emp": 1722, "epf_emp": 550, "esic_emp": 0, "prof_tax": 200, "loan": 0, "tds": 0,
         "net": 31128},
         
        {"code": "EW064", "name": "Akash Gholap", "company": "Endee",
         "designation": "Service Engineer", "department": "Service",
         "doj": date(2023, 10, 16), "gender": "Male",
         "present": 27, "pl": 0, "sl": 0, "cl": 0, "paid": 27, "absent": 0, "late": 0,
         "pf": True, "esic": False,
         "basic": 14350, "hra": 5740, "conveyance": 0, "bonus": 1196, "cca": 7114, "other": 1800,
         "gross": 30200,
         "pf_emp": 1722, "epf_emp": 550, "esic_emp": 0, "prof_tax": 200, "loan": 0, "tds": 0,
         "net": 27728},
         
        {"code": "EW065", "name": "Jatin Bhosale", "company": "Endee",
         "designation": "Embedded Engineer", "department": "R&D",
         "doj": date(2023, 12, 11), "gender": "Male",
         "present": 27, "pl": 0, "sl": 0, "cl": 0, "paid": 27, "absent": 0, "late": 0,
         "pf": True, "esic": False,
         "basic": 18750, "hra": 7500, "conveyance": 0, "bonus": 1563, "cca": 44887, "other": 1800,
         "gross": 74500,
         "pf_emp": 2250, "epf_emp": 550, "esic_emp": 0, "prof_tax": 200, "loan": 0, "tds": 0,
         "net": 71500},
         
        {"code": "EW066", "name": "Pratik Lotankar", "company": "Endee",
         "designation": "Embedded Engineer", "department": "R&D",
         "doj": date(2023, 12, 11), "gender": "Male",
         "present": 27, "pl": 0, "sl": 0, "cl": 0, "paid": 27, "absent": 0, "late": 0,
         "pf": True, "esic": False,
         "basic": 18750, "hra": 7500, "conveyance": 0, "bonus": 1563, "cca": 40887, "other": 1800,
         "gross": 70500,
         "pf_emp": 2250, "epf_emp": 550, "esic_emp": 0, "prof_tax": 200, "loan": 0, "tds": 0,
         "net": 67500},
         
        {"code": "EW067", "name": "Jyoti Sawant", "company": "Endee",
         "designation": "Quality Incharge", "department": "Quality",
         "doj": date(2024, 1, 2), "gender": "Female",
         "present": 27, "pl": 0, "sl": 0, "cl": 0, "paid": 27, "absent": 0, "late": 0,
         "pf": True, "esic": False,
         "basic": 12500, "hra": 5000, "conveyance": 0, "bonus": 1042, "cca": 10658, "other": 1800,
         "gross": 31000,
         "pf_emp": 1500, "epf_emp": 550, "esic_emp": 0, "prof_tax": 200, "loan": 0, "tds": 0,
         "net": 28750},
         
        {"code": "EW068", "name": "Vicky Kumar", "company": "Endee",
         "designation": "Fitter", "department": "Production",
         "doj": date(2024, 6, 1), "gender": "Male",
         "present": 27, "pl": 0, "sl": 0, "cl": 0, "paid": 27, "absent": 0, "late": 0,
         "pf": True, "esic": True,
         "basic": 10000, "hra": 4000, "conveyance": 0, "bonus": 833, "cca": 4567, "other": 1800,
         "gross": 21200,
         "pf_emp": 1200, "epf_emp": 550, "esic_emp": 159, "prof_tax": 200, "loan": 0, "tds": 0,
         "net": 19091},
         
        {"code": "EW069", "name": "Waman Bandekar", "company": "Endee",
         "designation": "Technician", "department": "Production",
         "doj": date(2024, 7, 4), "gender": "Male",
         "present": 27, "pl": 0, "sl": 0, "cl": 0, "paid": 27, "absent": 0, "late": 0,
         "pf": True, "esic": True,
         "basic": 10000, "hra": 4000, "conveyance": 0, "bonus": 833, "cca": 767, "other": 0,
         "gross": 15600,
         "pf_emp": 1200, "epf_emp": 550, "esic_emp": 117, "prof_tax": 0, "loan": 0, "tds": 0,
         "net": 13733},
         
        {"code": "EW070", "name": "Omkar More", "company": "Endee",
         "designation": "Embedded Engineer", "department": "R&D",
         "doj": date(2024, 7, 1), "gender": "Male",
         "present": 27, "pl": 0, "sl": 0, "cl": 0, "paid": 27, "absent": 0, "late": 0,
         "pf": True, "esic": True,
         "basic": 10000, "hra": 4000, "conveyance": 0, "bonus": 833, "cca": 6067, "other": 1800,
         "gross": 22700,
         "pf_emp": 1200, "epf_emp": 550, "esic_emp": 170, "prof_tax": 200, "loan": 0, "tds": 0,
         "net": 20580},
         
        {"code": "EW071", "name": "Swapnil Gaikwad", "company": "Endee",
         "designation": "Jr. Technician", "department": "Production",
         "doj": date(2024, 10, 1), "gender": "Male",
         "present": 27, "pl": 0, "sl": 0, "cl": 0, "paid": 27, "absent": 0, "late": 0,
         "pf": True, "esic": True,
         "basic": 10000, "hra": 4000, "conveyance": 0, "bonus": 833, "cca": 3067, "other": 1800,
         "gross": 19700,
         "pf_emp": 1200, "epf_emp": 550, "esic_emp": 148, "prof_tax": 200, "loan": 0, "tds": 0,
         "net": 17602},
         
        {"code": "EW072", "name": "Aishwarya Jari", "company": "Endee",
         "designation": "Jr. Technician", "department": "Production",
         "doj": date(2024, 10, 1), "gender": "Female",
         "present": 27, "pl": 0, "sl": 0, "cl": 0, "paid": 27, "absent": 0, "late": 0,
         "pf": True, "esic": True,
         "basic": 10000, "hra": 4000, "conveyance": 0, "bonus": 833, "cca": 3067, "other": 1800,
         "gross": 19700,
         "pf_emp": 1200, "epf_emp": 550, "esic_emp": 148, "prof_tax": 200, "loan": 0, "tds": 0,
         "net": 17602},
         
        {"code": "EW073", "name": "Ajit Lokhande", "company": "Endee",
         "designation": "Service Engineer", "department": "Service",
         "doj": date(2024, 12, 2), "gender": "Male",
         "present": 27, "pl": 0, "sl": 0, "cl": 0, "paid": 27, "absent": 0, "late": 0,
         "pf": True, "esic": True,
         "basic": 10000, "hra": 4000, "conveyance": 0, "bonus": 833, "cca": 8067, "other": 1800,
         "gross": 24700,
         "pf_emp": 1200, "epf_emp": 550, "esic_emp": 185, "prof_tax": 200, "loan": 0, "tds": 0,
         "net": 22565},
         
        # HNL Employees (from Sheet 2)
        {"code": "H003", "name": "Rajan Fernandes", "company": "HNL",
         "designation": "General Manager - Marketing", "department": "Sales",
         "doj": date(2001, 11, 23), "gender": "Male",
         "present": 27, "pl": 0, "sl": 0, "cl": 0, "paid": 27, "absent": 0, "late": 0,
         "pf": True, "esic": False,
         "basic": 25000, "hra": 10000, "conveyance": 0, "bonus": 2083, "cca": 20417, "other": 0,
         "gross": 57500,
         "pf_emp": 3000, "epf_emp": 550, "esic_emp": 0, "prof_tax": 200, "loan": 0, "tds": 0,
         "net": 53750},
         
        {"code": "H002", "name": "Kavita Sawant", "company": "HNL",
         "designation": "Accounts Manager", "department": "Accounts",
         "doj": date(2007, 9, 3), "gender": "Female",
         "present": 27, "pl": 0, "sl": 0, "cl": 0, "paid": 27, "absent": 0, "late": 0,
         "pf": True, "esic": False,
         "basic": 25000, "hra": 10000, "conveyance": 0, "bonus": 2083, "cca": 32917, "other": 0,
         "gross": 70000,
         "pf_emp": 3000, "epf_emp": 550, "esic_emp": 0, "prof_tax": 200, "loan": 0, "tds": 0,
         "net": 66250},
         
        {"code": "W022", "name": "Komal Patil", "company": "HNL",
         "designation": "Production Manager", "department": "Production",
         "doj": date(2015, 6, 17), "gender": "Female",
         "present": 27, "pl": 0, "sl": 0, "cl": 0, "paid": 27, "absent": 0, "late": 0,
         "pf": True, "esic": False,
         "basic": 25000, "hra": 10000, "conveyance": 0, "bonus": 2083, "cca": 39417, "other": 0,
         "gross": 76500,
         "pf_emp": 3000, "epf_emp": 550, "esic_emp": 0, "prof_tax": 200, "loan": 0, "tds": 0,
         "net": 72750},
         
        {"code": "H014", "name": "Aparna Raithatha", "company": "HNL",
         "designation": "Sales Executive", "department": "Sales",
         "doj": date(2017, 2, 7), "gender": "Female",
         "present": 27, "pl": 0, "sl": 0, "cl": 0, "paid": 27, "absent": 0, "late": 0,
         "pf": True, "esic": False,
         "basic": 20600, "hra": 8240, "conveyance": 0, "bonus": 1717, "cca": 21943, "other": 0,
         "gross": 52500,
         "pf_emp": 2472, "epf_emp": 550, "esic_emp": 0, "prof_tax": 200, "loan": 0, "tds": 0,
         "net": 49278},
         
        {"code": "H018", "name": "Ravin Gaikwad", "company": "HNL",
         "designation": "Sales Executive", "department": "Sales",
         "doj": date(2018, 1, 15), "gender": "Male",
         "present": 27, "pl": 0, "sl": 0, "cl": 0, "paid": 27, "absent": 0, "late": 0,
         "pf": True, "esic": False,
         "basic": 14350, "hra": 5740, "conveyance": 0, "bonus": 1196, "cca": 30514, "other": 1800,
         "gross": 53600,
         "pf_emp": 1722, "epf_emp": 550, "esic_emp": 0, "prof_tax": 200, "loan": 0, "tds": 0,
         "net": 51128},
         
        {"code": "H020", "name": "Aniket Sawant", "company": "HNL",
         "designation": "Project Engineer", "department": "Sales",
         "doj": date(2020, 12, 10), "gender": "Male",
         "present": 27, "pl": 0, "sl": 0, "cl": 0, "paid": 27, "absent": 0, "late": 0,
         "pf": True, "esic": False,
         "basic": 20600, "hra": 8240, "conveyance": 0, "bonus": 1717, "cca": 27443, "other": 0,
         "gross": 58000,
         "pf_emp": 2472, "epf_emp": 550, "esic_emp": 0, "prof_tax": 200, "loan": 0, "tds": 0,
         "net": 54778},
         
        {"code": "HO023", "name": "Sagar Kadam", "company": "HNL",
         "designation": "Office Assistant", "department": "Sales",
         "doj": date(2022, 8, 1), "gender": "Male",
         "present": 27, "pl": 0, "sl": 0, "cl": 0, "paid": 27, "absent": 0, "late": 0,
         "pf": True, "esic": True,
         "basic": 10000, "hra": 4000, "conveyance": 0, "bonus": 833, "cca": 3567, "other": 0,
         "gross": 18400,
         "pf_emp": 1200, "epf_emp": 550, "esic_emp": 138, "prof_tax": 0, "loan": 0, "tds": 0,
         "net": 16512},
         
        {"code": "HO024", "name": "Rahul Jadhav", "company": "HNL",
         "designation": "Office Assistant", "department": "Sales",
         "doj": date(2022, 8, 1), "gender": "Male",
         "present": 27, "pl": 0, "sl": 0, "cl": 0, "paid": 27, "absent": 0, "late": 0,
         "pf": True, "esic": True,
         "basic": 10000, "hra": 4000, "conveyance": 0, "bonus": 833, "cca": 4067, "other": 0,
         "gross": 18900,
         "pf_emp": 1200, "epf_emp": 550, "esic_emp": 142, "prof_tax": 0, "loan": 0, "tds": 0,
         "net": 17008},
         
        {"code": "HO067", "name": "Deepu Raj", "company": "HNL",
         "designation": "Sales Engineer", "department": "Sales",
         "doj": date(2024, 4, 2), "gender": "Male",
         "present": 27, "pl": 0, "sl": 0, "cl": 0, "paid": 27, "absent": 0, "late": 0,
         "pf": True, "esic": False,
         "basic": 18750, "hra": 7500, "conveyance": 0, "bonus": 1563, "cca": 7187, "other": 0,
         "gross": 35000,
         "pf_emp": 2250, "epf_emp": 550, "esic_emp": 0, "prof_tax": 200, "loan": 0, "tds": 0,
         "net": 32000},
         
        {"code": "HO068", "name": "Narsingh Chauhan", "company": "HNL",
         "designation": "PCB Assembler", "department": "Production",
         "doj": date(2024, 6, 1), "gender": "Male",
         "present": 27, "pl": 0, "sl": 0, "cl": 0, "paid": 27, "absent": 0, "late": 0,
         "pf": True, "esic": True,
         "basic": 10000, "hra": 4000, "conveyance": 0, "bonus": 833, "cca": 1567, "other": 1800,
         "gross": 18200,
         "pf_emp": 1200, "epf_emp": 550, "esic_emp": 137, "prof_tax": 0, "loan": 0, "tds": 0,
         "net": 16313},
         
        {"code": "HO069", "name": "Vaibhavi Halankar", "company": "HNL",
         "designation": "Office Executive", "department": "Sales",
         "doj": date(2024, 9, 2), "gender": "Female",
         "present": 27, "pl": 0, "sl": 0, "cl": 0, "paid": 27, "absent": 0, "late": 0,
         "pf": True, "esic": True,
         "basic": 10000, "hra": 4000, "conveyance": 0, "bonus": 833, "cca": 3067, "other": 1800,
         "gross": 19700,
         "pf_emp": 1200, "epf_emp": 550, "esic_emp": 148, "prof_tax": 200, "loan": 0, "tds": 0,
         "net": 17602},
         
        {"code": "HO070", "name": "Rajeshwari Nikam", "company": "HNL",
         "designation": "Admin Executive", "department": "Admin",
         "doj": date(2024, 10, 1), "gender": "Female",
         "present": 27, "pl": 0, "sl": 0, "cl": 0, "paid": 27, "absent": 0, "late": 0,
         "pf": True, "esic": True,
         "basic": 10000, "hra": 4000, "conveyance": 0, "bonus": 833, "cca": 1567, "other": 1800,
         "gross": 18200,
         "pf_emp": 1200, "epf_emp": 550, "esic_emp": 137, "prof_tax": 0, "loan": 0, "tds": 0,
         "net": 16313},
    ]
    
    db = get_db()
    
    with db.get_session() as session:
        # Get company IDs
        endee_id = get_company_id(session, "Endee")
        hnl_id = get_company_id(session, "HNL")
        
        print("\nCreating employees and salary structures...")
        
        created_employees = []
        
        for emp_data in employees_data:
            # Parse name
            name_parts = emp_data["name"].split()
            first_name = name_parts[0]
            if len(name_parts) == 2:
                middle_name = None
                last_name = name_parts[1]
            else:
                middle_name = " ".join(name_parts[1:-1]) if len(name_parts) > 2 else None
                last_name = name_parts[-1]
            
            company_id = endee_id if emp_data["company"] == "Endee" else hnl_id
            
            # Create employee
            employee = Employee(
                company_id=company_id,
                employee_code=emp_data["code"],
                first_name=first_name,
                middle_name=middle_name,
                last_name=last_name,
                gender=emp_data.get("gender"),
                designation=emp_data.get("designation", "Staff"),
                department=emp_data.get("department"),
                branch="Head Office",
                date_of_joining=emp_data["doj"],
                is_active=True,
            )
            session.add(employee)
            session.flush()
            
            # Create salary structure (effective from Jan 2026 for this data)
            salary = SalaryStructure(
                employee_id=employee.id,
                effective_from=date(2026, 1, 1),
                effective_to=None,
                basic_salary=Decimal(str(emp_data["basic"])),
                hra=Decimal(str(emp_data["hra"])),
                bonus=Decimal(str(emp_data["bonus"])),
                cca=Decimal(str(emp_data["cca"])),
                other_allowance=Decimal(str(emp_data.get("other", 0))),
                pf_applicable=emp_data["pf"],
                esi_applicable=emp_data["esic"],
                pt_applicable=emp_data["prof_tax"] > 0,
            )
            session.add(salary)
            
            created_employees.append({
                "id": employee.id,
                "code": emp_data["code"],
                "name": emp_data["name"],
                "data": emp_data
            })
            
            print(f"  ✓ {emp_data['code']} - {emp_data['name']} ({emp_data['company']})")
        
        session.commit()
        
        # Create payroll period for January 2026
        print("\nCreating payroll period: January 2026...")
        period = PayrollPeriod(
            year=2026,
            month=1,
            period_label="Jan 2026",
            working_days=27,
            is_locked=False,
        )
        session.add(period)
        session.flush()
        
        # Create monthly payroll records
        print("\nCreating monthly payroll records...")
        for emp_info in created_employees:
            emp_data = emp_info["data"]
            
            payroll = MonthlyPayroll(
                employee_id=emp_info["id"],
                payroll_period_id=period.id,
                
                # Attendance
                present_days=emp_data["present"],
                paid_days=emp_data["paid"],
                absent_days=emp_data["absent"],
                late_marks=emp_data["late"],
                privilege_leave=Decimal(str(emp_data["pl"])),
                sick_leave=Decimal(str(emp_data["sl"])),
                casual_leave=Decimal(str(emp_data["cl"])),
                
                # Salary components (snapshot)
                basic_salary=Decimal(str(emp_data["basic"])),
                hra=Decimal(str(emp_data["hra"])),
                bonus=Decimal(str(emp_data["bonus"])),
                cca=Decimal(str(emp_data["cca"])),
                other_allowance=Decimal(str(emp_data.get("other", 0))),
                
                # Earnings
                gross_earnings=Decimal(str(emp_data["gross"])),
                
                # Deductions
                pf_employee=Decimal(str(emp_data["pf_emp"])),
                esi_employee=Decimal(str(emp_data["esic_emp"])),
                professional_tax=Decimal(str(emp_data["prof_tax"])),
                loan_deduction=Decimal(str(emp_data["loan"])),
                tds=Decimal(str(emp_data["tds"])),
                other_deductions=Decimal(str(emp_data.get("epf_emp", 0))),  # EPF admin charges
                total_deductions=Decimal(str(
                    emp_data["pf_emp"] + emp_data.get("epf_emp", 0) + 
                    emp_data["esic_emp"] + emp_data["prof_tax"] + 
                    emp_data["loan"] + emp_data["tds"]
                )),
                
                # Employer contributions (calculated)
                pf_employer=Decimal(str(int(emp_data["basic"] * 0.12))) if emp_data["pf"] else Decimal("0"),
                esi_employer=Decimal(str(int(emp_data["gross"] * 0.0325))) if emp_data["esic"] else Decimal("0"),
                
                # Net
                net_salary=Decimal(str(emp_data["net"])),
                ctc_monthly=Decimal(str(emp_data["gross"])),
                
                is_finalized=False,
            )
            session.add(payroll)
        
        session.commit()
        
        print(f"\n✅ Created {len(employees_data)} employees")
        print(f"✅ Created {len(employees_data)} salary structures")
        print(f"✅ Created payroll period: January 2026")
        print(f"✅ Created {len(employees_data)} monthly payroll records")


if __name__ == "__main__":
    print("=" * 60)
    print("Staffly - January 2026 Data Population Script")
    print("=" * 60)
    
    from staffly.config import get_config
    config = get_config()
    init_db(config.db_path)
    
    truncate_database()
    create_companies()
    create_employees_and_payroll()
    
    print("\n🎉 Done! Database populated with January 2026 data.")
    print("   Companies: ENDEE ENGINEERS PVT. LTD., HNL")
