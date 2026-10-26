"""
WSGI Entry Point for Production Hosting (Gunicorn / uWSGI / Render / Railway / Heroku)
"""
import os
from app import app
from database import init_db, seed_sample_data_if_empty
from scheduler import TimetableScheduler

# Ensure database and sample data are populated before serving requests
try:
    init_db()
    seeded = seed_sample_data_if_empty()
    if seeded:
        try:
            TimetableScheduler().generate()
        except Exception as se:
            print(f"WSGI Initial timetable generation note: {se}")
except Exception as e:
    print(f"WSGI Startup database initialization: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
