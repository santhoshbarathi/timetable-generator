"""
Intelligent Department Timetable Scheduler - Database Layer

Uses SQLite with foreign key enforcement and connection management.
Provides schema initialization, seed data population, and query helpers.
"""

import os
import sqlite3
from typing import Optional, List, Dict, Any
from config import (
    DEFAULT_PART_TIME_WEEKLY_PERIODS,
    MAX_FULL_TIME_WEEKLY_PERIODS,
    WORK_TYPE_FULL_TIME,
    WORK_TYPE_PART_TIME,
)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scheduler.db")


def get_db_connection() -> sqlite3.Connection:
    """
    Creates and returns an SQLite database connection.
    Enables foreign keys and sets row_factory to sqlite3.Row for dictionary-like access.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(force: bool = False) -> None:
    """
    Initializes database tables.
    If force is True, drops existing tables and recreates them.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    if force:
        cursor.execute("DROP TABLE IF EXISTS timetable_entries;")
        cursor.execute("DROP TABLE IF EXISTS subjects;")
        cursor.execute("DROP TABLE IF EXISTS faculty;")
        cursor.execute("DROP TABLE IF EXISTS classes;")

    # 1. Classes / Sections Table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            code TEXT NOT NULL UNIQUE,
            semester INTEGER DEFAULT 1 CHECK(semester BETWEEN 1 AND 8),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    # 2. Faculty Table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS faculty (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            department TEXT DEFAULT '',
            work_type TEXT NOT NULL CHECK(work_type IN ('full_time', 'part_time')),
            weekly_period_limit INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    # 3. Subjects Table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            code TEXT NOT NULL,
            periods_per_week INTEGER NOT NULL CHECK(periods_per_week BETWEEN 1 AND 6),
            faculty_id INTEGER REFERENCES faculty(id) ON DELETE SET NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(class_id, code)
        );
        """
    )

    # 4. Timetable Entries Table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS timetable_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            semester INTEGER DEFAULT 1,
            day TEXT NOT NULL,
            period_num INTEGER NOT NULL CHECK(period_num BETWEEN 1 AND 8),
            subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
            faculty_id INTEGER NOT NULL REFERENCES faculty(id) ON DELETE CASCADE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(class_id, day, period_num)
        );
        """
    )

    conn.commit()
    conn.close()


def seed_sample_data_if_empty() -> bool:
    """
    Seeds the institutional department structure from the academic curriculum:
      - Department of AI & DS (2nd, 3rd, and 4th Year)
      - Department of IT (2nd, 3rd, and 4th Year)
      - Department of Science and Humanities (1st Year)
      - 27 Faculty members across departments
      - 40 Academic subjects with assigned faculty and weekly period counts
    Returns True if seeded, False if data already existed.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS count FROM classes;")
    if cursor.fetchone()["count"] > 0:
        conn.close()
        return False

    # 1. Classes / Sections
    classes_data = [
        ("AI & DS - 2nd Year", "AIDS-2"),
        ("AI & DS - 3rd Year", "AIDS-3"),
        ("AI & DS - 4th Year", "AIDS-4"),
        ("Information Technology - 2nd Year", "IT-2"),
        ("Information Technology - 3rd Year", "IT-3"),
        ("Information Technology - 4th Year", "IT-4"),
        ("Science & Humanities - 1st Year", "SH-1"),
    ]
    cursor.executemany("INSERT INTO classes (name, code) VALUES (?, ?);", classes_data)

    # 2. Faculty Pool
    faculty_data = [
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
        ("KAMALAVENI.P", "Mathematics", WORK_TYPE_PART_TIME, 16),
        ("MADESWARAN.K", "Information Technology", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
        ("KARTHIKA.V", "Information Technology", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
        ("JREEJA.J", "Information Technology", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
        ("RAJA.M", "Information Technology", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
        ("KIRUTHIKA.M", "Information Technology", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
        ("AROCKIA SELVARAJ.A", "Information Technology", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
        ("BHARATHI.B", "Information Technology", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
        ("REVATHI.P", "Tamil / S&H", WORK_TYPE_PART_TIME, 16),
        ("GIRIJA.V", "English / S&H", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
        ("MEKALADEVI.A", "Mathematics / S&H", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
        ("MUTHULAKSHMI.S", "Physics / S&H", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
        ("KANAGAVALLI.K", "Chemistry / S&H", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
        # Lab faculty
        ("SWARNA.S", "AI & DS", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
        ("KIRUTHIKA DEVI.M", "Information Technology", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
        ("SARANYA.T", "Information Technology", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
        ("SARANYA.R", "Science and Humanities", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
        ("DHIVAKARAN.S", "Science and Humanities", WORK_TYPE_FULL_TIME, MAX_FULL_TIME_WEEKLY_PERIODS),
    ]
    cursor.executemany(
        """
        INSERT INTO faculty (name, department, work_type, weekly_period_limit)
        VALUES (?, ?, ?, ?);
        """,
        faculty_data,
    )

    # 3. Lookup maps
    cursor.execute("SELECT id, code FROM classes;")
    classes_by_code = {row["code"]: row["id"] for row in cursor.fetchall()}

    cursor.execute("SELECT id, name FROM faculty;")
    faculty_by_name = {row["name"]: row["id"] for row in cursor.fetchall()}

    # 4. Subjects across all departments
    subjects_data = [
        # --- Department of AI&DS: 2nd Year (AIDS-2) ---
        (classes_by_code["AIDS-2"], "Discrete Mathematics", "MA25C08", 4, faculty_by_name["SULOCHANADEVI.P"]),
        (classes_by_code["AIDS-2"], "Data Structures", "CS25C08", 4, faculty_by_name["KAYAL VIZHI.S"]),
        (classes_by_code["AIDS-2"], "Java Programming", "CS25C09", 4, faculty_by_name["AMIRTHAM.S"]),
        (classes_by_code["AIDS-2"], "Exploratory Data Analysis", "AD25C01", 4, faculty_by_name["THENMOZHI.K"]),
        (classes_by_code["AIDS-2"], "Operating Systems", "CS25C11", 4, faculty_by_name["SANGEETHA.P"]),

        # --- Department of AI&DS: 3rd Year (AIDS-3) ---
        (classes_by_code["AIDS-3"], "Deep Learning", "AD3501", 4, faculty_by_name["VIGNESH.T.R"]),
        (classes_by_code["AIDS-3"], "Cloud Computing", "CCS335", 4, faculty_by_name["SUNDARI.P"]),
        (classes_by_code["AIDS-3"], "Distributed Computing", "CS3551", 4, faculty_by_name["KAYAL VIZHI.S"]),
        (classes_by_code["AIDS-3"], "Big Data Analytics", "CCS334", 4, faculty_by_name["LATHA"]),
        (classes_by_code["AIDS-3"], "Elements of Literature", "MX3082", 3, faculty_by_name["GRACEPRIYADARSHINI"]),
        (classes_by_code["AIDS-3"], "Ethics & AI", "CCS34", 3, faculty_by_name["PRAKASH.P.K"]),
        (classes_by_code["AIDS-3"], "Data and Information Security", "CW3551", 4, faculty_by_name["SHAMPAVI.T"]),
        # AI&DS 3rd Year Labs (2 periods/week = 1 continuous 2hr block/week)
        (classes_by_code["AIDS-3"], "Deep Learning Lab", "AD3501L", 2, faculty_by_name["VIGNESH.T.R"]),
        (classes_by_code["AIDS-3"], "Big Data Analytics Lab", "CCS334L", 2, faculty_by_name["LATHA"]),
        (classes_by_code["AIDS-3"], "Ethics & AI Lab", "CCS34L", 2, faculty_by_name["PRAKASH.P.K"]),
        (classes_by_code["AIDS-3"], "Cloud Computing Lab", "CCS335L", 2, faculty_by_name["SWARNA.S"]),

        # --- Department of AI&DS: 4th Year (AIDS-4) ---
        (classes_by_code["AIDS-4"], "Human Values & Ethics", "GE3791", 3, faculty_by_name["SANTHOSH C.R"]),
        (classes_by_code["AIDS-4"], "IT in Agricultural System", "AI3021", 4, faculty_by_name["SANGEETHA.P"]),
        (classes_by_code["AIDS-4"], "Human Resource Management", "GE3754", 4, faculty_by_name["KANAGARAJ.S"]),
        (classes_by_code["AIDS-4"], "Renewable Energy Technologies", "CME365", 4, faculty_by_name["BALASUBRAMANIAM.J"]),
        (classes_by_code["AIDS-4"], "Basics of Integrated Water Resource Management", "OCE354", 4, faculty_by_name["VIGNESH.T.R"]),

        # --- Department of IT: 2nd Year (IT-2) ---
        (classes_by_code["IT-2"], "Discrete Mathematics", "MA25C08", 4, faculty_by_name["KAMALAVENI.P"]),
        (classes_by_code["IT-2"], "Computer Organization and Architecture", "CW25201", 4, faculty_by_name["MADESWARAN.K"]),
        (classes_by_code["IT-2"], "Data Structures", "CS25C08", 4, faculty_by_name["KARTHIKA.V"]),
        (classes_by_code["IT-2"], "Object Oriented Programming", "CS25C07", 4, faculty_by_name["JREEJA.J"]),
        (classes_by_code["IT-2"], "Web Technologies", "IT25301", 4, faculty_by_name["RAJA.M"]),

        # --- Department of IT: 3rd Year (IT-3) ---
        (classes_by_code["IT-3"], "Distributed Computing", "CS3551", 4, faculty_by_name["MADESWARAN.K"]),
        (classes_by_code["IT-3"], "Computer Networks", "CS3591", 4, faculty_by_name["KIRUTHIKA.M"]),
        (classes_by_code["IT-3"], "Full Stack Web Development", "IT3501", 4, faculty_by_name["RAJA.M"]),
        (classes_by_code["IT-3"], "Software Testing and Automation", "CCS366", 4, faculty_by_name["AROCKIA SELVARAJ.A"]),
        (classes_by_code["IT-3"], "Cloud Computing", "CCS335", 4, faculty_by_name["SUNDARI.P"]),
        (classes_by_code["IT-3"], "Embedded Systems & IoT", "CS3691", 4, faculty_by_name["BHARATHI.B"]),
        (classes_by_code["IT-3"], "Elements of Literature", "MX3082", 3, faculty_by_name["GRACEPRIYADARSHINI"]),
        # IT 3rd Year Labs (2 periods/week = 1 continuous 2hr block/week)
        (classes_by_code["IT-3"], "Computer Networks Lab", "CS3591L1", 2, faculty_by_name["KIRUTHIKA DEVI.M"]),
        (classes_by_code["IT-3"], "Software Testing & Automation Lab", "CCS366L", 2, faculty_by_name["LATHA"]),
        (classes_by_code["IT-3"], "Full Stack Web Development Lab", "IT3501L", 2, faculty_by_name["SUNDARI.P"]),
        (classes_by_code["IT-3"], "Embedded Systems & IoT Lab", "CS3691L", 2, faculty_by_name["SARANYA.T"]),
        (classes_by_code["IT-3"], "Computer Networks Lab (Batch 2)", "CS3591L2", 2, faculty_by_name["SUNDARI.P"]),

        # --- Department of IT: 4th Year (IT-4) ---
        (classes_by_code["IT-4"], "Human Values and Ethics", "GE3791", 3, faculty_by_name["SANTHOSH C.R"]),
        (classes_by_code["IT-4"], "Principles of Management", "GE3751", 4, faculty_by_name["KANAGARAJ.S"]),
        (classes_by_code["IT-4"], "IT in Agricultural System", "AI3021", 4, faculty_by_name["SANGEETHA.P"]),
        (classes_by_code["IT-4"], "Renewable Energy Technologies", "OEE351", 4, faculty_by_name["BALASUBRAMANIAM.J"]),
        (classes_by_code["IT-4"], "Production and Operation Management for Entrepreneurs", "OIE353", 4, faculty_by_name["BHARATHI.B"]),

        # --- Department of Science & Humanities: 1st Year (SH-1) ---
        (classes_by_code["SH-1"], "Heritage of Tamil", "26TA101T", 3, faculty_by_name["REVATHI.P"]),
        (classes_by_code["SH-1"], "Professional English 1", "26EN101T", 4, faculty_by_name["GIRIJA.V"]),
        (classes_by_code["SH-1"], "Matrics and Calculus", "26MA103T", 4, faculty_by_name["MEKALADEVI.A"]),
        (classes_by_code["SH-1"], "Engineering Physics", "26PH101T", 4, faculty_by_name["MUTHULAKSHMI.S"]),
        (classes_by_code["SH-1"], "Engineering Chemistry", "26CY101T", 4, faculty_by_name["KANAGAVALLI.K"]),
        (classes_by_code["SH-1"], "Programming in C", "26CS104T", 4, faculty_by_name["KARTHIKA.V"]),
        # S&H 1st Year Labs (2 periods/week = 1 continuous 2hr block/week)
        (classes_by_code["SH-1"], "Physics / Chemistry Lab", "26PHCYL", 2, faculty_by_name["MUTHULAKSHMI.S"]),
        (classes_by_code["SH-1"], "PC Lab", "26PCL", 2, faculty_by_name["SARANYA.R"]),
        (classes_by_code["SH-1"], "EP Lab", "26EPL", 2, faculty_by_name["DHIVAKARAN.S"]),
    ]

    cursor.executemany(
        """
        INSERT INTO subjects (class_id, name, code, periods_per_week, faculty_id)
        VALUES (?, ?, ?, ?, ?);
        """,
        subjects_data,
    )

    conn.commit()
    conn.close()
    return True
