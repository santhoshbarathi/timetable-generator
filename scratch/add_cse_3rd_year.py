"""
Script to add CSE Department 3rd Year (Class: III CSE, Semester V)
along with all Theory subjects, Practical Labs, and Faculty to scheduler.db.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scheduler.db")

def add_cse_3rd_year():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Ensure Class 'CSE - 3rd Year' ('CSE-3') exists
    cursor.execute("SELECT id FROM classes WHERE code = 'CSE-3' OR name = 'CSE - 3rd Year';")
    class_row = cursor.fetchone()
    if class_row:
        class_id = class_row["id"]
        print(f"Class already exists with ID: {class_id}")
    else:
        cursor.execute(
            "INSERT INTO classes (name, code, semester) VALUES (?, ?, ?);",
            ("Computer Science and Engineering - 3rd Year", "CSE-3", 5)
        )
        class_id = cursor.lastrowid
        print(f"Created Class 'Computer Science and Engineering - 3rd Year' (CSE-3, Sem 5) with ID: {class_id}")

    # 2. Faculty list from document:
    # (Name, Department, Work Type, Weekly Limit)
    faculty_data = [
        ("Mrs.S.Annapooraneswari", "CSE", "full_time", 40),
        ("Dr.K.Baskaran", "CSE", "full_time", 40),
        ("Dr.G.Selvavinayagam", "CSE", "full_time", 40),
        ("Mr.A.Arockia Selvaraj", "IT", "full_time", 40),
        ("Mrs.S.Vijaya Samundeeswari", "CSE", "full_time", 40),
        ("Mrs.A.Saranya", "CSE", "full_time", 40),
        ("Dr.C.Saravana Raja", "English", "full_time", 40),
        ("Mrs.S.Amirtham", "CSE", "full_time", 40),
    ]

    faculty_id_map = {}
    for name, dept, wtype, limit in faculty_data:
        # Check if faculty exists by name or similar pattern
        cursor.execute("SELECT id FROM faculty WHERE name = ?;", (name,))
        fac_row = cursor.fetchone()
        if not fac_row:
            # Check without dots/prefix or case-insensitive
            cursor.execute("SELECT id FROM faculty WHERE name LIKE ?;", (f"%{name.split('.')[-1]}%",))
            fac_row = cursor.fetchone()

        if fac_row:
            faculty_id = fac_row["id"]
            print(f"Faculty '{name}' mapped to existing ID: {faculty_id}")
        else:
            cursor.execute(
                "INSERT INTO faculty (name, department, work_type, weekly_period_limit) VALUES (?, ?, ?, ?);",
                (name, dept, wtype, limit)
            )
            faculty_id = cursor.lastrowid
            print(f"Created new Faculty '{name}' with ID: {faculty_id}")
        faculty_id_map[name] = faculty_id

    # 3. Subjects data from document:
    # (Subject Code, Subject Name, Periods/Week, Faculty Key, Type)
    subjects_data = [
        # Theory
        ("CS3551", "Distributed Computing", 4, "Mrs.S.Annapooraneswari"),
        ("CS3591", "Computer Networks", 5, "Dr.K.Baskaran"),
        ("CB3491", "Cryptography and Cyber Security", 5, "Dr.G.Selvavinayagam"),
        ("CCS366", "Software Testing and Automation", 4, "Mr.A.Arockia Selvaraj"),
        ("CCS335", "Cloud Computing", 4, "Mrs.S.Vijaya Samundeeswari"),
        ("CS3501", "Compiler Design", 5, "Mrs.A.Saranya"),
        ("MX3082", "Elements of Literature", 2, "Dr.C.Saravana Raja"),
        # Practicals / Labs
        ("CS3591_LAB", "Computer Networks Lab", 2, "Mrs.S.Amirtham"),
        ("CCS366_LAB", "Software Testing and Automation Lab", 2, "Mr.A.Arockia Selvaraj"),
        ("CS3501_LAB", "Compiler Design Lab", 2, "Mrs.A.Saranya"),
        ("CCS335_LAB", "Cloud Computing Lab", 2, "Mrs.S.Vijaya Samundeeswari"),
        # Other regular slots
        ("LIB302", "Library", 1, "Mrs.S.Vijaya Samundeeswari"),
    ]

    for sub_code, sub_name, periods, fac_name in subjects_data:
        fac_id = faculty_id_map[fac_name]
        cursor.execute("SELECT id FROM subjects WHERE class_id = ? AND code = ?;", (class_id, sub_code))
        existing_sub = cursor.fetchone()
        if existing_sub:
            cursor.execute(
                "UPDATE subjects SET name = ?, periods_per_week = ?, faculty_id = ? WHERE id = ?;",
                (sub_name, periods, fac_id, existing_sub["id"])
            )
            print(f"Updated subject '{sub_name}' ({sub_code}) for class {class_id}")
        else:
            cursor.execute(
                "INSERT INTO subjects (class_id, code, name, periods_per_week, faculty_id) VALUES (?, ?, ?, ?, ?);",
                (class_id, sub_code, sub_name, periods, fac_id)
            )
            print(f"Added subject '{sub_name}' ({sub_code}) with {periods} periods/wk, faculty '{fac_name}'")

    conn.commit()
    conn.close()
    print("Database update successfully completed!")

if __name__ == "__main__":
    add_cse_3rd_year()
