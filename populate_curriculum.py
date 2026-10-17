import sqlite3
import os
from config import WORK_TYPE_FULL_TIME, WORK_TYPE_PART_TIME, MAX_FULL_TIME_WEEKLY_PERIODS, DEFAULT_PART_TIME_WEEKLY_PERIODS
from database import init_db, get_db_connection
from scheduler import TimetableScheduler

# Define the exact data from the user's document:
CLASSES = [
    # Department of AI&DS
    ("AI & DS - 2nd Year", "AIDS-2"),
    ("AI & DS - 3rd Year", "AIDS-3"),
    ("AI & DS - 4th Year", "AIDS-4"),
    # Department of IT
    ("Information Technology - 2nd Year", "IT-2"),
    ("Information Technology - 3rd Year", "IT-3"),
    ("Information Technology - 4th Year", "IT-4"),
    # Department of Science & Humanities
    ("Science & Humanities - 1st Year", "SH-1"),
]

# Faculty details: Name, Department, Work Type, Weekly Limit
FACULTY = [
    # AI & DS / Math / CSE
    ("SULOCHANADEVI.P", "Mathematics", WORK_TYPE_PART_TIME, 16),
    ("KAYAL VIZHI.S", "AI & DS", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
    ("AMIRTHAM.S", "AI & DS", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
    ("THENMOZHI.K", "AI & DS", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
    ("SANGEETHA.P", "AI & DS", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
    ("VIGNESH.T.R", "AI & DS", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
    ("SUNDARI.P", "Computer Science", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
    ("LATHA", "AI & DS", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
    ("GRACEPRIYADARSHINI", "English / S&H", WORK_TYPE_PART_TIME, 16),
    ("PRAKASH.P.K", "AI & DS", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
    ("SHAMPAVI.T", "AI & DS", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
    ("SANTHOSH C.R", "Humanities / Management", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
    ("KANAGARAJ.S", "Management Studies", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
    ("BALASUBRAMANIAM.J", "Electrical & Renewable", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
    # IT Faculty
    ("KAMALAVENI.P", "Mathematics", WORK_TYPE_PART_TIME, 16),
    ("MADESWARAN.K", "Information Technology", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
    ("KARTHIKA.V", "Information Technology", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
    ("JREEJA.J", "Information Technology", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
    ("RAJA.M", "Information Technology", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
    ("KIRUTHIKA.M", "Information Technology", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
    ("AROCKIA SELVARAJ.A", "Information Technology", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
    ("BHARATHI.B", "Information Technology", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
    # Science & Humanities Faculty
    ("REVATHI.P", "Tamil / S&H", WORK_TYPE_PART_TIME, 16),
    ("GIRIJA.V", "English / S&H", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
    ("MEKALADEVI.A", "Mathematics / S&H", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
    ("MUTHULAKSHMI.S", "Physics / S&H", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
    ("KANAGAVALLI.K", "Chemistry / S&H", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
]

# Subjects: (Class Code, Subject Code, Subject Name, Periods/Week, Faculty Name)
SUBJECTS = [
    # --- Department of AI&DS: 2nd Year (AIDS-2) ---
    ("AIDS-2", "MA25C08", "Discrete Mathematics", 4, "SULOCHANADEVI.P"),
    ("AIDS-2", "CS25C08", "Data Structures", 4, "KAYAL VIZHI.S"),
    ("AIDS-2", "CS25C09", "Java Programming", 4, "AMIRTHAM.S"),
    ("AIDS-2", "AD25C01", "Exploratory Data Analysis", 4, "THENMOZHI.K"),
    ("AIDS-2", "CS25C11", "Operating Systems", 4, "SANGEETHA.P"),

    # --- Department of AI&DS: 3rd Year (AIDS-3) ---
    ("AIDS-3", "AD3501", "Deep Learning", 4, "VIGNESH.T.R"),
    ("AIDS-3", "CCS335", "Cloud Computing", 4, "SUNDARI.P"),
    ("AIDS-3", "CS3551", "Distributed Computing", 4, "KAYAL VIZHI.S"),
    ("AIDS-3", "CCS334", "Big Data Analytics", 4, "LATHA"),
    ("AIDS-3", "MX3082", "Elements of Literature", 3, "GRACEPRIYADARSHINI"),
    ("AIDS-3", "CCS34", "Ethics & AI", 3, "PRAKASH.P.K"),
    ("AIDS-3", "CW3551", "Data and Information Security", 4, "SHAMPAVI.T"),

    # --- Department of AI&DS: 4th Year (AIDS-4) ---
    ("AIDS-4", "GE3791", "Human Value & Ethics", 3, "SANTHOSH C.R"),
    ("AIDS-4", "AI3021", "IT in Agricultural System", 4, "SANGEETHA.P"),
    ("AIDS-4", "GE3754", "Human Resource Management", 4, "KANAGARAJ.S"),
    ("AIDS-4", "CME365", "Renewable Energy Technologies", 4, "BALASUBRAMANIAM.J"),
    ("AIDS-4", "OCE354", "Basics of Integrated Water Resource Management", 4, "VIGNESH.T.R"),

    # --- Department of IT: 2nd Year (IT-2) ---
    ("IT-2", "MA25C08", "Discrete Mathematics", 4, "KAMALAVENI.P"),
    ("IT-2", "CW25201", "Computer Organization and Architecture", 4, "MADESWARAN.K"),
    ("IT-2", "CS25C08", "Data Structures", 4, "KARTHIKA.V"),
    ("IT-2", "CS25C07", "Object Oriented Programming", 4, "JREEJA.J"),
    ("IT-2", "IT25301", "Web Technologies", 4, "RAJA.M"),

    # --- Department of IT: 3rd Year (IT-3) ---
    ("IT-3", "CS3551", "Distributed Computing", 4, "MADESWARAN.K"),
    ("IT-3", "CS3591", "Computer Networks", 4, "KIRUTHIKA.M"),
    ("IT-3", "IT3501", "Full Stack Web Development", 4, "RAJA.M"),
    ("IT-3", "CCS366", "Software Testing and Automation", 4, "AROCKIA SELVARAJ.A"),
    ("IT-3", "CCS335", "Cloud Computing", 4, "SUNDARI.P"),
    ("IT-3", "CS3691", "Embedded Systems & IoT", 4, "BHARATHI.B"),
    ("IT-3", "MX3082", "Elements of Literature", 3, "GRACEPRIYADARSHINI"),

    # --- Department of IT: 4th Year (IT-4) ---
    ("IT-4", "GE3791", "Human Values and Ethics", 3, "SANTHOSH C.R"),
    ("IT-4", "GE3751", "Principles of Management", 4, "KANAGARAJ.S"),
    ("IT-4", "AI3021", "IT in Agricultural System", 4, "SANGEETHA.P"),
    ("IT-4", "OEE351", "Renewable Energy Technologies", 4, "BALASUBRAMANIAM.J"),
    ("IT-4", "OIE353", "Production and Operation Management for Entrepreneurs", 4, "BHARATHI.B"),

    # --- Department of Science & Humanities: 1st Year (SH-1) ---
    ("SH-1", "26TA101T", "Heritage of Tamil", 3, "REVATHI.P"),
    ("SH-1", "26EN101T", "Professional English 1", 4, "GIRIJA.V"),
    ("SH-1", "26MA103T", "Matrics and Calculus", 4, "MEKALADEVI.A"),
    ("SH-1", "26PH101T", "Engineering Physics", 4, "MUTHULAKSHMI.S"),
    ("SH-1", "26CY101T", "Engineering Chemistry", 4, "KANAGAVALLI.K"),
    ("SH-1", "26CS104T", "Programming in C", 4, "KARTHIKA.V"),
]

def apply_new_curriculum():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Clear old data
    cursor.execute("DELETE FROM timetable_entries;")
    cursor.execute("DELETE FROM subjects;")
    cursor.execute("DELETE FROM faculty;")
    cursor.execute("DELETE FROM classes;")

    # Insert Classes
    for name, code in CLASSES:
        cursor.execute("INSERT INTO classes (name, code) VALUES (?, ?);", (name, code))
    
    # Insert Faculty
    for name, dept, wtype, limit in FACULTY:
        cursor.execute("INSERT INTO faculty (name, department, work_type, weekly_period_limit) VALUES (?, ?, ?, ?);",
                       (name, dept, wtype, limit))

    conn.commit()

    # Map lookups
    cursor.execute("SELECT id, code FROM classes;")
    class_map = {row["code"]: row["id"] for row in cursor.fetchall()}

    cursor.execute("SELECT id, name FROM faculty;")
    faculty_map = {row["name"]: row["id"] for row in cursor.fetchall()}

    # Insert Subjects
    for class_code, sub_code, sub_name, periods, fac_name in SUBJECTS:
        cid = class_map[class_code]
        fid = faculty_map[fac_name]
        cursor.execute(
            "INSERT INTO subjects (class_id, code, name, periods_per_week, faculty_id) VALUES (?, ?, ?, ?, ?);",
            (cid, sub_code, sub_name, periods, fid)
        )

    conn.commit()
    conn.close()
    print(f"Successfully inserted {len(CLASSES)} classes, {len(FACULTY)} faculty members, and {len(SUBJECTS)} subjects!")

if __name__ == "__main__":
    apply_new_curriculum()
    print("Testing TimetableScheduler.generate()...")
    scheduler = TimetableScheduler(seed=42)
    result = scheduler.generate()
    print("Timetable generation SUCCESSFUL!")
    print(f"Total scheduled entries: {len(result['entries'])}")
    print(f"Classes scheduled: {list(result['schedules_by_class'].keys())}")
    for cid, sched in result['schedules_by_class'].items():
        print(f" - Class {sched['class_name']} ({sched['class_code']}): {len(sched['entries'])} periods scheduled")
