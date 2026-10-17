"""
Simulation test for 40 periods per week for all 7 classes (280 total periods, 0 free periods).
"""

import sys
sys.path.insert(0, '.')
from scratch.test_class_by_class import solve_class_by_class as solve_timetable

# Construct test data
classes = [
    {"id": 1, "name": "AI & DS - 2nd Year", "code": "AIDS-2"},
    {"id": 2, "name": "AI & DS - 3rd Year", "code": "AIDS-3"},
    {"id": 3, "name": "AI & DS - 4th Year", "code": "AIDS-4"},
    {"id": 4, "name": "Information Technology - 2nd Year", "code": "IT-2"},
    {"id": 5, "name": "Information Technology - 3rd Year", "code": "IT-3"},
    {"id": 6, "name": "Information Technology - 4th Year", "code": "IT-4"},
    {"id": 7, "name": "Science & Humanities - 1st Year", "code": "SH-1"},
]

# 27 faculty + Librarian + Placement
faculty = [
    {"id": 1, "name": "SULOCHANADEVI.P", "department": "Mathematics", "work_type": "part_time", "weekly_period_limit": 16},
    {"id": 2, "name": "KAYAL VIZHI.S", "department": "AI & DS", "work_type": "full_time", "weekly_period_limit": 40},
    {"id": 3, "name": "AMIRTHAM.S", "department": "AI & DS", "work_type": "full_time", "weekly_period_limit": 40},
    {"id": 4, "name": "THENMOZHI.K", "department": "AI & DS", "work_type": "full_time", "weekly_period_limit": 40},
    {"id": 5, "name": "SANGEETHA.P", "department": "AI & DS", "work_type": "full_time", "weekly_period_limit": 40},
    {"id": 6, "name": "VIGNESH.T.R", "department": "AI & DS", "work_type": "full_time", "weekly_period_limit": 40},
    {"id": 7, "name": "SUNDARI.P", "department": "Computer Science", "work_type": "full_time", "weekly_period_limit": 40},
    {"id": 8, "name": "LATHA", "department": "AI & DS", "work_type": "full_time", "weekly_period_limit": 40},
    {"id": 9, "name": "GRACEPRIYADHARASINI", "department": "English / S&H", "work_type": "part_time", "weekly_period_limit": 16},
    {"id": 10, "name": "PRAKASH.P.K", "department": "AI & DS", "work_type": "full_time", "weekly_period_limit": 40},
    {"id": 11, "name": "SHAMPAVI.T", "department": "AI & DS", "work_type": "full_time", "weekly_period_limit": 40},
    {"id": 12, "name": "SANTHOSH C.R", "department": "Humanities / Management", "work_type": "full_time", "weekly_period_limit": 40},
    {"id": 13, "name": "KANAGARAJ.S", "department": "Management Studies", "work_type": "full_time", "weekly_period_limit": 40},
    {"id": 14, "name": "BALASUBRAMANIAM.J", "department": "Electrical & Renewable", "work_type": "full_time", "weekly_period_limit": 40},
    {"id": 15, "name": "KAMALAVENI.P", "department": "Mathematics", "work_type": "part_time", "weekly_period_limit": 16},
    {"id": 16, "name": "MADESWARAN.K", "department": "Information Technology", "work_type": "full_time", "weekly_period_limit": 40},
    {"id": 17, "name": "KARTHIKA.V", "department": "Information Technology", "work_type": "full_time", "weekly_period_limit": 40},
    {"id": 18, "name": "JREEJA.J", "department": "Information Technology", "work_type": "full_time", "weekly_period_limit": 40},
    {"id": 19, "name": "RAJA.M", "department": "Information Technology", "work_type": "full_time", "weekly_period_limit": 40},
    {"id": 20, "name": "KIRUTHIKA.M", "department": "Information Technology", "work_type": "full_time", "weekly_period_limit": 40},
    {"id": 21, "name": "AROCKIA SELVARAJ.A", "department": "Information Technology", "work_type": "full_time", "weekly_period_limit": 40},
    {"id": 22, "name": "BHARATHI.B", "department": "Information Technology", "work_type": "full_time", "weekly_period_limit": 40},
    {"id": 23, "name": "REVATHI.P", "department": "Tamil / S&H", "work_type": "part_time", "weekly_period_limit": 16},
    {"id": 24, "name": "GIRIJA.V", "department": "English / S&H", "work_type": "full_time", "weekly_period_limit": 40},
    {"id": 25, "name": "MEKALADEVI.A", "department": "Mathematics", "work_type": "full_time", "weekly_period_limit": 40},
    {"id": 26, "name": "MUTHULAKSHMI.S", "department": "Physics", "work_type": "full_time", "weekly_period_limit": 40},
    {"id": 27, "name": "KANAGAVALLI.K", "department": "Chemistry", "work_type": "full_time", "weekly_period_limit": 40},
    {"id": 28, "name": "LIBRARIAN", "department": "Library & Info Services", "work_type": "full_time", "weekly_period_limit": 40},
    {"id": 29, "name": "PLACEMENT OFFICER", "department": "Training & Placement", "work_type": "full_time", "weekly_period_limit": 40},
]

# Subjects list
subjects = []
sid = 1

def add_subj(cid, name, code, fid, periods):
    global sid
    subjects.append({"id": sid, "class_id": cid, "name": name, "code": code, "faculty_id": fid, "periods_per_week": periods})
    sid += 1

# 1. AIDS-2 (40 periods)
# 5 Theory subjects x 6 = 30 periods
add_subj(1, "Discrete Mathematics", "MA25C08", 1, 6) # PT Sulochanadevi
add_subj(1, "Data Structures", "CS25C08", 2, 6)
add_subj(1, "Java Programming", "CS25C09", 3, 6)
add_subj(1, "Exploratory Data Analysis", "AD25C01", 4, 6)
add_subj(1, "Operating Systems", "CS25C11", 5, 6)
# Labs (2 hrs each = 6 periods)
add_subj(1, "Data Structures Laboratory", "CS25C18", 2, 2)
add_subj(1, "Java & EDA Laboratory", "AD25C11", 3, 2)
add_subj(1, "Operating Systems Laboratory", "CS25C12", 5, 2)
# Library (1) + Placement (2) + Skill/Seminar (1) = 4 periods
add_subj(1, "Library", "LIB201", 28, 1)
add_subj(1, "Placement Training", "PLC201", 29, 2)
add_subj(1, "Technical Seminar", "SEM201", 4, 1)

# 2. AIDS-3 (40 periods)
# 7 Theory subjects x 5 = 35 periods
add_subj(2, "Deep Learning", "AD3501", 6, 5)
add_subj(2, "Cloud Computing", "CCS335", 7, 5)
add_subj(2, "Distributed Computing", "CS3551", 2, 5)
add_subj(2, "Big Data Analytics", "CCS334", 8, 5)
add_subj(2, "Elements of Literature", "MX3082", 9, 5) # PT Gracepriyadharasini
add_subj(2, "Ethics & AI", "CCS34", 10, 5)
add_subj(2, "Data and Information Security", "CW3551", 11, 5)
# Lab (2 hrs = 2 periods)
add_subj(2, "Deep Learning & Big Data Laboratory", "AD3511", 6, 2)
# Library (1) + Placement (2) = 3 periods
add_subj(2, "Library", "LIB301", 28, 1)
add_subj(2, "Placement Training", "PLC301", 29, 2)

# 3. AIDS-4 (40 periods)
# 5 Theory subjects x 6 = 30 periods
add_subj(3, "Human Value & Ethics", "GE3791", 12, 6)
add_subj(3, "IT in Agricultural System", "AI3021", 5, 6)
add_subj(3, "Human Resource Management", "GE3754", 13, 6)
add_subj(3, "Renewable Energy Technologies", "CME365", 14, 6)
add_subj(3, "Basics of Integrated Water Resource Management", "OCE354", 6, 6)
# Labs (2 hrs each = 6 periods)
add_subj(3, "AI Applications Laboratory", "AI3711", 5, 2)
add_subj(3, "Project Work / Internship", "PR3711", 12, 2)
add_subj(3, "Renewable Energy Laboratory", "CME368", 14, 2)
# Library (1) + Placement (2) + Seminar (1) = 4 periods
add_subj(3, "Library", "LIB401", 28, 1)
add_subj(3, "Placement Training", "PLC401", 29, 2)
add_subj(3, "Professional Development Seminar", "SEM401", 13, 1)

# 4. IT-2 (40 periods)
# 5 Theory subjects x 6 = 30 periods
add_subj(4, "Discrete Mathematics", "MA25C08", 15, 6) # PT Kamalaveni
add_subj(4, "Computer Organization and Architecture", "CW25201", 16, 6)
add_subj(4, "Data Structures", "CS25C08", 17, 6)
add_subj(4, "Object Oriented Programming", "CS25C07", 18, 6)
add_subj(4, "Web Technologies", "IT25301", 19, 6)
# Labs (2 hrs each = 6 periods)
add_subj(4, "Data Structures Laboratory", "CS25C18", 17, 2)
add_subj(4, "Web Technologies Laboratory", "IT25311", 19, 2)
add_subj(4, "Object Oriented Programming Laboratory", "CS25C17", 18, 2)
# Library (1) + Placement (2) + Seminar (1) = 4 periods
add_subj(4, "Library", "LIB202", 28, 1)
add_subj(4, "Placement Training", "PLC202", 29, 2)
add_subj(4, "Programming Skills Seminar", "SEM202", 18, 1)

# 5. IT-3 (40 periods)
# 7 Theory subjects x 5 = 35 periods
add_subj(5, "Distributed Computing", "CS3551", 16, 5)
add_subj(5, "Computer Networks", "CS3591", 20, 5)
add_subj(5, "Full Stack Web Development", "IT3501", 19, 5)
add_subj(5, "Software Testing and Automation", "CCS366", 21, 5)
add_subj(5, "Cloud Computing", "CCS335", 7, 5)
add_subj(5, "Embedded Systems & IoT", "CS3691", 22, 5)
add_subj(5, "Elements of Literature", "MX3082", 9, 5) # PT Gracepriyadharasini
# Lab (2 hrs = 2 periods)
add_subj(5, "Full Stack Web Development Laboratory", "IT3511", 19, 2)
# Library (1) + Placement (2) = 3 periods
add_subj(5, "Library", "LIB302", 28, 1)
add_subj(5, "Placement Training", "PLC302", 29, 2)

# 6. IT-4 (40 periods)
# 5 Theory subjects x 6 = 30 periods
add_subj(6, "Human Values and Ethics", "GE3791", 12, 6)
add_subj(6, "Principles of Management", "GE3751", 13, 6)
add_subj(6, "IT in Agricultural System", "AI3021", 5, 6)
add_subj(6, "Renewable Energy Technologies", "OEE351", 14, 6)
add_subj(6, "Production and Operation Management for Entrepreneurs", "OIE353", 22, 6)
# Labs (2 hrs each = 6 periods)
add_subj(6, "Advanced IT Systems Laboratory", "IT4711", 22, 2)
add_subj(6, "Project Work / Internship", "PR4711", 12, 2)
add_subj(6, "Renewable Energy Laboratory", "OEE358", 14, 2)
# Library (1) + Placement (2) + Seminar (1) = 4 periods
add_subj(6, "Library", "LIB402", 28, 1)
add_subj(6, "Placement Training", "PLC402", 29, 2)
add_subj(6, "Entrepreneurship Seminar", "SEM402", 13, 1)

# 7. SH-1 (40 periods)
# 6 Theory subjects = 33 periods
add_subj(7, "Heritage of Tamil", "26TA101T", 23, 5) # PT Revathi
add_subj(7, "Professional English 1", "26EN101T", 24, 5)
add_subj(7, "Matrices and Calculus", "26MA103T", 25, 6)
add_subj(7, "Engineering Physics", "26PH101T", 26, 6)
add_subj(7, "Engineering Chemistry", "26CY101T", 27, 6)
add_subj(7, "Programming in C", "26CS104T", 17, 5)
# Labs (2 hrs each = 4 periods)
add_subj(7, "Physics & Chemistry Laboratory", "26BS101P", 26, 2)
add_subj(7, "Programming in C Laboratory", "26CS101P", 17, 2)
# Library (1) + Placement (2) = 3 periods
add_subj(7, "Library", "LIB101", 28, 1)
add_subj(7, "Placement Training & Foundational Skills", "PLC101", 29, 2)

if __name__ == '__main__':
    for c in classes:
        p_sum = sum(s["periods_per_week"] for s in subjects if s["class_id"] == c["id"])
        print(f"Class {c['code']} total weekly periods: {p_sum}")

    print(f"Total subjects: {len(subjects)}, total periods: {sum(s['periods_per_week'] for s in subjects)}")

    res = solve_timetable(classes, faculty, subjects)
    if res:
        print(f"SUCCESS: Scheduled all {len(res)} periods conflict-free!")
        from collections import Counter
        cnts = Counter(e["class_id"] for e in res)
        for c in classes:
            print(f"  Class {c['code']}: {cnts[c['id']]}/40 periods scheduled")
    else:
        print("FAILED to solve")
