import sqlite3

# Connect to your database
conn = sqlite3.connect("college.db")
cursor = conn.cursor()

# Create timetable table
cursor.execute("""
CREATE TABLE IF NOT EXISTS timetable (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_name TEXT NOT NULL,
    subject TEXT NOT NULL,
    class_name TEXT NOT NULL,
    day TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    room_no TEXT NOT NULL
);
""")

conn.commit()
conn.close()

print("✅ timetable table created successfully!")
