import sqlite3
conn = sqlite3.connect('scheduler.db')
conn.row_factory = sqlite3.Row

for cls in conn.execute('SELECT id, name, code, semester FROM classes ORDER BY code').fetchall():
    subs = conn.execute('SELECT code, name, periods_per_week FROM subjects WHERE class_id=?', (cls['id'],)).fetchall()
    total = sum(s['periods_per_week'] for s in subs)
    print(f"\n[{cls['code']}] {cls['name']}  Sem={cls['semester']}  TOTAL={total}")
    for s in subs:
        print(f"  {s['code']:20s} {s['name']:50s} {s['periods_per_week']} periods")
