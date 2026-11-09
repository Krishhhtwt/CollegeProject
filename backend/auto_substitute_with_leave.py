import sqlite3

# Connect to database
conn = sqlite3.connect("college.db")
cursor = conn.cursor()

# Get all teachers on leave
cursor.execute("SELECT teacher_name, date FROM teacher_leave WHERE status = 'Pending'")
leaves = cursor.fetchall()

for teacher_name, date in leaves:
    print(f"\n🔍 Checking substitute for {teacher_name} on {date}...")

    # Find all classes that teacher has
    cursor.execute("""
        SELECT subject, day, start_time, end_time
        FROM timetable
        WHERE teacher_name = ?
    """, (teacher_name,))
    classes = cursor.fetchall()

    if not classes:
        print("❌ No classes found for this teacher.")
        continue

    substitute_found = False  # Track if any substitute was found

    for subject, day, start_time, end_time in classes:
        # Search for available substitute
        cursor.execute("""
            SELECT teacher_name
            FROM teachers
            WHERE subject = ? AND teacher_name != ?
            AND teacher_name NOT IN (
                SELECT teacher_name FROM timetable
                WHERE day = ? AND (
                    (start_time <= ? AND end_time > ?)
                    OR (start_time < ? AND end_time >= ?)
                )
            )
        """, (subject, teacher_name, day, start_time, start_time, end_time, end_time))
        substitute = cursor.fetchone()

        if substitute:
            substitute_name = substitute[0]
            substitute_found = True

            print(f"✅ Substitute Found: {substitute_name} for {teacher_name}'s {subject} class on {day} ({start_time}-{end_time})")

            # Update the leave record
            cursor.execute("""
                UPDATE teacher_leave
                SET substitute_teacher = ?, status = 'Substitute Assigned'
                WHERE teacher_name = ? AND date = ?
            """, (substitute_name, teacher_name, date))
            conn.commit()

        else:
            print(f"❌ No substitute available for {subject} on {day} ({start_time}-{end_time})")

    if not substitute_found:
        print("⚠️ No substitutes found for any class — keeping status as Pending.")

conn.close()
print("\n✅ All leave records processed successfully.")

