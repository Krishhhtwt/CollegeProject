# create_db.py
import sqlite3

conn = sqlite3.connect('database.db')
c = conn.cursor()

# teachers
c.execute('''
CREATE TABLE IF NOT EXISTS teachers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  email TEXT NOT NULL,
  department TEXT
)
''')

# timetable: day is weekday name like Monday, Tuesday
c.execute('''
CREATE TABLE IF NOT EXISTS timetable (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  teacher_id INTEGER,
  day TEXT,
  time_slot TEXT,      -- e.g. "9:00-10:00"
  class_name TEXT,
  FOREIGN KEY(teacher_id) REFERENCES teachers(id)
)
''')

# leaves
c.execute('''
CREATE TABLE IF NOT EXISTS leaves (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  teacher_id INTEGER,
  date TEXT,          -- YYYY-MM-DD
  reason TEXT,
  status TEXT DEFAULT 'Pending',
  applied_on TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(teacher_id) REFERENCES teachers(id)
)
''')

# sample teachers
c.execute("INSERT INTO teachers (name, email, department) VALUES (?, ?, ?)",
          ('Krish Saini', 'krish@example.com', 'CSE'))
c.execute("INSERT INTO teachers (name, email, department) VALUES (?, ?, ?)",
          ('Anu Sharma', 'anu@example.com', 'CSE'))
c.execute("INSERT INTO teachers (name, email, department) VALUES (?, ?, ?)",
          ('Mr. Sharma', 'sharma@example.com', 'CSE'))

# sample timetable (Mon-Fri), only DBMS subject example
# Krish: Monday 9:00-10:00, Tuesday 10:00-11:00
c.execute("INSERT INTO timetable (teacher_id, day, time_slot, class_name) VALUES (?, ?, ?, ?)",
          (1, 'Monday', '9:00-10:00', 'CS-3A'))
c.execute("INSERT INTO timetable (teacher_id, day, time_slot, class_name) VALUES (?, ?, ?, ?)",
          (1, 'Tuesday', '10:00-11:00', 'CS-2A'))

# Anu (teacher 2) is busy Monday 9:00-10:00 -> so not free for Krish's Monday slot.
c.execute("INSERT INTO timetable (teacher_id, day, time_slot, class_name) VALUES (?, ?, ?, ?)",
          (2, 'Monday', '9:00-10:00', 'CS-3B'))

# Mr. Sharma (teacher 3) is free on Monday 9:00-10:00 (no timetable row) — good substitute
conn.commit()
conn.close()

print("DB created and sample data inserted (database.db).")
