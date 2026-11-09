import sqlite3

def find_substitute(teacher_name, leave_day):
    conn = sqlite3.connect("college.db")
    cursor = conn.cursor()

    # 1️⃣ Get the classes of the teacher who is on leave
    cursor.execute("""
        SELECT subject, start_time, end_time, class_name
        FROM timetable
        WHERE teacher_name = ? AND day = ?
    """, (teacher_name, leave_day))
    leave_classes = cursor.fetchall()

    if not leave_classes:
        print("No classes found for this teacher on that day.")
        return

    substitutes = []

    for subject, start_time, end_time, class_name in leave_classes:
        # 2️⃣ Find teachers who teach the same subject
        cursor.execute("""
            SELECT DISTINCT teacher_name
            FROM timetable
            WHERE subject = ? AND teacher_name != ?
        """, (subject, teacher_name))
        eligible_teachers = [t[0] for t in cursor.fetchall()]

        for t in eligible_teachers:
            # 3️⃣ Check if they are free at that time
            cursor.execute("""
                SELECT COUNT(*)
                FROM timetable
                WHERE teacher_name = ?
                AND day = ?
                AND (
                    (start_time <= ? AND end_time > ?) OR
                    (start_time < ? AND end_time >= ?)
                )
            """, (t, leave_day, start_time, start_time, end_time, end_time))
            busy = cursor.fetchone()[0]

            if busy == 0:
                # 4️⃣ Count total lectures that day (to find least busy teacher)
                cursor.execute("""
                    SELECT COUNT(*) FROM timetable
                    WHERE teacher_name = ? AND day = ?
                """, (t, leave_day))
                total_classes = cursor.fetchone()[0]
                substitutes.append((t, subject, total_classes))

    conn.close()

    if not substitutes:
        print("❌ No available substitute teachers found.")
    else:
        # 5️⃣ Sort by fewest lectures that day
        substitutes.sort(key=lambda x: x[2])
        print("✅ Substitute teachers available:")
        for s in substitutes:
            print(f"Teacher: {s[0]} | Subject: {s[1]} | Total Lectures Today: {s[2]}")
        print(f"📢 Best Substitute: {substitutes[0][0]} (Least Busy)")

# Example run
find_substitute("Mr. Sharma", "Monday")
