import sqlite3

# Connect to your database
conn = sqlite3.connect("college.db")
cursor = conn.cursor()

# Sample timetable data — make sure each tuple has 7 values:
# (teacher_name, subject, class_name, day, start_time, end_time, room_no)
timetable_data = [
    ("Mr. Sharma", "Mathematics", "CSE-A", "Monday", "09:00 AM", "10:00 AM", "101"),
    ("Ms. Gupta", "Physics", "CSE-B", "Tuesday", "10:00 AM", "11:00 AM", "102"),
    ("Mr. Verma", "Chemistry", "CSE-A", "Wednesday", "11:00 AM", "12:00 PM", "103"),
    ("Mrs. Singh", "Computer Networks", "CSE-B", "Thursday", "12:00 PM", "01:00 PM", "104"),
    ("Mr. Mehta", "Data Structures", "CSE-A", "Friday", "01:00 PM", "02:00 PM", "105"),
]

# Insert data into the timetable table
cursor.executemany("""
INSERT INTO timetable (
    teacher_name, subject, class_name, day, start_time, end_time, room_no
) VALUES (?, ?, ?, ?, ?, ?, ?)
""", timetable_data)

# Commit changes and close connection
conn.commit()
conn.close()

print("✅ Timetable data inserted successfully!")

