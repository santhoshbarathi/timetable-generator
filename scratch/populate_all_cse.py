"""
Script to populate CSE Department:
1. II CSE-A (Semester 3)
2. II CSE-B (Semester 3)
3. Update III CSE (Semester 5)

Adds all faculty, theory subjects, lab subjects, and faculty advisors to scheduler.db.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scheduler.db")

def populate_cse():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Faculty Pool Setup
    faculty_definitions = [
        # (Exact Name, Department, Work Type, Weekly Limit)
        ("Dr.A.Divya", "Mathematics", "full_time", 40),
        ("Mrs.R.Jamunarani", "Mathematics", "full_time", 40),
        ("Mrs.P.Gokila", "CSE", "full_time", 40),
        ("Mrs.V.Suganthi", "CSE", "full_time", 40),
        ("Mrs.M.Nagarasan", "CSE", "full_time", 40),
        ("Mrs.R.Saranya", "CSE", "full_time", 40),
        ("Mrs.S.Annapooraneswari", "CSE", "full_time", 40),
        ("Mrs.Swarna", "CSE", "full_time", 40),
        ("Dr.C.Saravana Raja", "English", "full_time", 40),
        ("Mrs.S.Vijaya Samundeeswari", "CSE", "full_time", 40),
        ("Dr.K.Baskaran", "CSE", "full_time", 40),
        ("Dr.G.Selvavinayagam", "CSE", "full_time", 40),
        ("Mr.A.Arockia Selvaraj", "IT", "full_time", 40),
        ("Mrs.A.Saranya", "CSE", "full_time", 40),
        ("Mrs.S.Amirtham", "CSE", "full_time", 40),
    ]

    faculty_id_map = {}
    for name, dept, wtype, limit in faculty_definitions:
        cursor.execute("SELECT id FROM faculty WHERE name = ?;", (name,))
        row = cursor.fetchone()
        if not row:
            cursor.execute(
                "INSERT INTO faculty (name, department, work_type, weekly_period_limit) VALUES (?, ?, ?, ?);",
                (name, dept, wtype, limit)
            )
            fid = cursor.lastrowid
            print(f"Created faculty: {name} (ID: {fid})")
        else:
            fid = row["id"]
            cursor.execute("UPDATE faculty SET department = ? WHERE id = ?;", (dept, fid))
            print(f"Existing faculty found: {name} (ID: {fid})")
        faculty_id_map[name] = fid

    # 2. Classes Setup
    classes_definitions = [
        ("Computer Science and Engineering - 2nd Year (Section A)", "CSE-2A", 3),
        ("Computer Science and Engineering - 2nd Year (Section B)", "CSE-2B", 3),
        ("Computer Science and Engineering - 3rd Year", "CSE-3", 5),
    ]

    class_id_map = {}
    for cname, ccode, csem in classes_definitions:
        cursor.execute("SELECT id FROM classes WHERE code = ?;", (ccode,))
        row = cursor.fetchone()
        if not row:
            cursor.execute(
                "INSERT INTO classes (name, code, semester) VALUES (?, ?, ?);",
                (cname, ccode, csem)
            )
            cid = cursor.lastrowid
            print(f"Created class: {cname} [{ccode}] (ID: {cid})")
        else:
            cid = row["id"]
            cursor.execute("UPDATE classes SET name = ?, semester = ? WHERE id = ?;", (cname, csem, cid))
            print(f"Updated class: {cname} [{ccode}] (ID: {cid})")
        class_id_map[ccode] = cid

    # 3. Subjects Definition:
    # (class_code, sub_code, sub_name, periods_per_week, faculty_key)
    subjects_definitions = [
        # =========================================================================
        # II CSE - A SECTION (Semester III)
        # =========================================================================
        ("CSE-2A", "MA25C08", "Discrete Mathematics", 5, "Dr.A.Divya"),
        ("CSE-2A", "CS25C08", "Data Structures", 5, "Mrs.P.Gokila"),
        ("CSE-2A", "CS25C11", "Operating Systems", 5, "Mrs.V.Suganthi"),
        ("CSE-2A", "CS25C10", "Object Oriented Software Engineering", 5, "Mrs.M.Nagarasan"),
        ("CSE-2A", "CS25C09", "Java Programming", 5, "Mrs.R.Saranya"),
        ("CSE-2A", "CS25C08_LAB", "Data Structures Laboratory", 4, "Mrs.Swarna"),
        ("CSE-2A", "CS25C09_LAB", "Java Programming Laboratory", 4, "Mrs.R.Saranya"),
        ("CSE-2A", "CS25C11_LAB", "Operating Systems Laboratory", 2, "Mrs.V.Suganthi"),
        ("CSE-2A", "EN25C03_LAB", "English Communication Skills Laboratory-I", 2, "Dr.C.Saravana Raja"),
        ("CSE-2A", "LIB201", "Library", 1, "Mrs.V.Suganthi"),
        ("CSE-2A", "SDC201", "Skill Development Course - I / Value Added Course", 4, "Mrs.S.Vijaya Samundeeswari"),

        # =========================================================================
        # II CSE - B SECTION (Semester III)
        # =========================================================================
        ("CSE-2B", "MA25C08", "Discrete Mathematics", 5, "Mrs.R.Jamunarani"),
        ("CSE-2B", "CS25C08", "Data Structures", 5, "Mrs.P.Gokila"),
        ("CSE-2B", "CS25C11", "Operating Systems", 5, "Mrs.V.Suganthi"),
        ("CSE-2B", "CS25C10", "Object Oriented Software Engineering", 5, "Mrs.M.Nagarasan"),
        ("CSE-2B", "CS25C09", "Java Programming", 5, "Mrs.S.Annapooraneswari"),
        ("CSE-2B", "CS25C08_LAB", "Data Structures Laboratory", 4, "Mrs.Swarna"),
        ("CSE-2B", "CS25C09_LAB", "Java Programming Laboratory", 4, "Mrs.S.Annapooraneswari"),
        ("CSE-2B", "CS25C11_LAB", "Operating Systems Laboratory", 2, "Mrs.V.Suganthi"),
        ("CSE-2B", "EN25C03_LAB", "English Communication Skills Laboratory-I", 2, "Dr.C.Saravana Raja"),
        ("CSE-2B", "LIB202", "Library", 1, "Mrs.S.Annapooraneswari"),
        ("CSE-2B", "SDC202", "Skill Development Course - I / Value Added Course", 4, "Mrs.S.Annapooraneswari"),

        # =========================================================================
        # III CSE (Semester V)
        # =========================================================================
        ("CSE-3", "CS3551", "Distributed Computing", 4, "Mrs.S.Annapooraneswari"),
        ("CSE-3", "CS3591", "Computer Networks", 5, "Dr.K.Baskaran"),
        ("CSE-3", "CB3491", "Cryptography and Cyber Security", 5, "Dr.G.Selvavinayagam"),
        ("CSE-3", "CCS366", "Software Testing and Automation", 4, "Mr.A.Arockia Selvaraj"),
        ("CSE-3", "CCS335", "Cloud Computing", 4, "Mrs.S.Vijaya Samundeeswari"),
        ("CSE-3", "CS3501", "Compiler Design", 5, "Mrs.A.Saranya"),
        ("CSE-3", "MX3082", "Elements of Literature", 2, "Dr.C.Saravana Raja"),
        ("CSE-3", "CS3591_LAB", "Computer Networks Lab", 2, "Mrs.S.Amirtham"),
        ("CSE-3", "CCS366_LAB", "Software Testing and Automation Lab", 2, "Mr.A.Arockia Selvaraj"),
        ("CSE-3", "CS3501_LAB", "Compiler Design Lab", 2, "Mrs.A.Saranya"),
        ("CSE-3", "CCS335_LAB", "Cloud Computing Lab", 2, "Mrs.S.Vijaya Samundeeswari"),
        ("CSE-3", "LIB302", "Library", 1, "Mrs.S.Vijaya Samundeeswari"),
    ]

    for ccode, scode, sname, periods, fname in subjects_definitions:
        cid = class_id_map[ccode]
        fid = faculty_id_map[fname]
        cursor.execute("SELECT id FROM subjects WHERE class_id = ? AND code = ?;", (cid, scode))
        existing = cursor.fetchone()
        if existing:
            cursor.execute(
                "UPDATE subjects SET name = ?, periods_per_week = ?, faculty_id = ? WHERE id = ?;",
                (sname, periods, fid, existing["id"])
            )
            print(f"Updated: [{ccode}] {sname} ({scode}) -> {fname}")
        else:
            cursor.execute(
                "INSERT INTO subjects (class_id, code, name, periods_per_week, faculty_id) VALUES (?, ?, ?, ?, ?);",
                (cid, scode, sname, periods, fid)
            )
            print(f"Inserted: [{ccode}] {sname} ({scode}) -> {fname} ({periods} periods)")

    conn.commit()
    conn.close()
    print("\nSUCCESS: All CSE 2nd & 3rd Year data inserted into database!")

if __name__ == "__main__":
    populate_cse()
