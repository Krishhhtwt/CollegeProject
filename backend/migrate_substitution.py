import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "college.db")

conn = sqlite3.connect(DB_PATH)

conn.executescript("""
CREATE TABLE IF NOT EXISTS substitution_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    leave_id INTEGER NOT NULL,
    teacher_name TEXT NOT NULL,
    date TEXT NOT NULL,
    subject TEXT NOT NULL,
    class_name TEXT NOT NULL,
    day TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    room_no TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    current_candidate TEXT,
    assigned_teacher TEXT,
    candidate_list TEXT DEFAULT '[]',
    candidate_index INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS substitution_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER NOT NULL,
    teacher_name TEXT NOT NULL,
    action TEXT NOT NULL,
    reason TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(request_id) REFERENCES substitution_requests(id)
);

CREATE TABLE IF NOT EXISTS teacher_availability (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_name TEXT NOT NULL,
    date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    reason TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS coordinator_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    resolved_at TEXT,
    FOREIGN KEY(request_id) REFERENCES substitution_requests(id)
);

CREATE INDEX IF NOT EXISTS idx_substitution_date
ON substitution_requests(date);

CREATE INDEX IF NOT EXISTS idx_substitution_status
ON substitution_requests(status);

CREATE INDEX IF NOT EXISTS idx_teacher_availability
ON teacher_availability(teacher_name, date);
""")

conn.commit()

tables = conn.execute("""
SELECT name FROM sqlite_master
WHERE type = 'table'
ORDER BY name
""").fetchall()

print("Database migration completed successfully!")
print("\nAvailable tables:")
for table in tables:
    print("-", table[0])

conn.close()
