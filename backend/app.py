
from flask import Flask, jsonify, request, send_from_directory
import sqlite3
import os
import json
from datetime import datetime

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_FOLDER = os.path.join(BASE_DIR, "public")
DB_PATH = os.path.join(BASE_DIR, "college.db")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def time_minutes(value):
    for fmt in ("%I:%M %p", "%H:%M"):
        try:
            parsed = datetime.strptime(value.strip(), fmt)
            return parsed.hour * 60 + parsed.minute
        except ValueError:
            pass
    raise ValueError("Invalid time format: " + str(value))


def overlaps(start1, end1, start2, end2):
    return time_minutes(start1) < time_minutes(end2) and \
           time_minutes(start2) < time_minutes(end1)


def get_candidates(conn, teacher, date, subject, day, start, end):
    rows = conn.execute("""
        SELECT teacher_name FROM teachers
        WHERE subject = ? AND teacher_name != ?
    """, (subject, teacher)).fetchall()

    candidates = []

    for row in rows:
        name = row["teacher_name"]

        # Exclude teachers who have applied for leave.
        leave = conn.execute("""
            SELECT 1 FROM teacher_leave
            WHERE teacher_name = ? AND date = ?
        """, (name, date)).fetchone()

        if leave:
            continue

        # Exclude teachers who marked themselves unavailable.
        unavailable = conn.execute("""
            SELECT start_time, end_time FROM teacher_availability
            WHERE teacher_name = ? AND date = ?
        """, (name, date)).fetchall()

        if any(overlaps(start, end, x["start_time"], x["end_time"])
               for x in unavailable):
            continue

        # Exclude timetable clashes.
        timetable = conn.execute("""
            SELECT start_time, end_time FROM timetable
            WHERE teacher_name = ? AND day = ?
        """, (name, day)).fetchall()

        if any(overlaps(start, end, x["start_time"], x["end_time"])
               for x in timetable):
            continue

        # Exclude teachers already assigned or currently offered
        # another substitution during this period.
        requests = conn.execute("""
            SELECT start_time, end_time
            FROM substitution_requests
            WHERE date = ?
            AND (
                assigned_teacher = ?
                OR current_candidate = ?
            )
            AND status IN (
                'assigned', 'awaiting_acceptance',
                'replacement_requested'
            )
        """, (date, name, name)).fetchall()

        if any(overlaps(start, end, x["start_time"], x["end_time"])
               for x in requests):
            continue

        # Count previous accepted substitutions for workload ordering.
        workload = conn.execute("""
            SELECT COUNT(*) FROM substitution_requests
            WHERE date = ? AND assigned_teacher = ?
            AND status = 'assigned'
        """, (date, name)).fetchone()[0]

        candidates.append((workload, name))

    candidates.sort(key=lambda item: (item[0], item[1]))
    return [name for _, name in candidates]


def notify_coordinator(conn, request_id, message):
    conn.execute("""
        INSERT INTO coordinator_notifications (request_id, message)
        VALUES (?, ?)
    """, (request_id, message))


def offer_next_candidate(conn, req, start_index):
    candidates = json.loads(req["candidate_list"] or "[]")

    for index in range(start_index, len(candidates)):
        candidate = candidates[index]

        conn.execute("""
            UPDATE substitution_requests
            SET current_candidate = ?,
                candidate_index = ?,
                status = 'awaiting_acceptance',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (candidate, index, req["id"]))

        conn.execute("""
            INSERT INTO substitution_history
            (request_id, teacher_name, action)
            VALUES (?, ?, 'offered')
        """, (req["id"], candidate))

        return candidate

    conn.execute("""
        UPDATE substitution_requests
        SET current_candidate = NULL,
            candidate_index = ?,
            status = 'coordinator_required',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (len(candidates), req["id"]))

    notify_coordinator(
        conn,
        req["id"],
        "No eligible substitute accepted or remains available."
    )

    return None


# ---------------- TEACHERS ----------------

@app.route('/api/teachers', methods=['GET'])
def get_teachers():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM teachers").fetchall()
    conn.close()

    return jsonify([
        {
            "id": r["id"],
            "teacher_name": r["teacher_name"],
            "subject": r["subject"]
        }
        for r in rows
    ])


# ---------------- TIMETABLE ----------------

@app.route('/api/timetable', methods=['GET'])
def get_timetable():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM timetable").fetchall()
    conn.close()

    return jsonify([dict(r) for r in rows])


# ---------------- APPLY LEAVE ----------------

@app.route('/api/leave', methods=['POST'])
def apply_teacher_leave():
    data = request.get_json(silent=True) or {}

    teacher = data.get("teacher_name")
    date = data.get("date")
    reason = data.get("reason", "")

    if not teacher or not date:
        return jsonify({"error": "Teacher name and date are required"}), 400

    try:
        day = datetime.strptime(date, "%Y-%m-%d").strftime("%A")
    except ValueError:
        return jsonify({"error": "Date must use YYYY-MM-DD format"}), 400

    conn = get_db_connection()

    teacher_exists = conn.execute("""
        SELECT 1 FROM teachers WHERE teacher_name = ?
    """, (teacher,)).fetchone()

    if not teacher_exists:
        conn.close()
        return jsonify({"error": "Teacher not found"}), 404

    cur = conn.execute("""
        INSERT INTO teacher_leave
        (teacher_name, date, reason, status, substitute_teacher)
        VALUES (?, ?, ?, 'Pending', 'Awaiting acceptance')
    """, (teacher, date, reason))

    leave_id = cur.lastrowid

    lectures = conn.execute("""
        SELECT * FROM timetable
        WHERE teacher_name = ? AND day = ?
    """, (teacher, day)).fetchall()

    created = []

    for lecture in lectures:
        candidates = get_candidates(
            conn, teacher, date, lecture["subject"], day,
            lecture["start_time"], lecture["end_time"]
        )

        cur = conn.execute("""
            INSERT INTO substitution_requests (
                leave_id, teacher_name, date, subject,
                class_name, day, start_time, end_time,
                room_no, candidate_list, candidate_index
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, -1)
        """, (
            leave_id, teacher, date, lecture["subject"],
            lecture["class_name"], day, lecture["start_time"],
            lecture["end_time"], lecture["room_no"],
            json.dumps(candidates)
        ))

        request_id = cur.lastrowid
        req = conn.execute("""
            SELECT * FROM substitution_requests WHERE id = ?
        """, (request_id,)).fetchone()

        candidate = offer_next_candidate(conn, req, 0)

        created.append({
            "request_id": request_id,
            "subject": lecture["subject"],
            "class_name": lecture["class_name"],
            "candidate": candidate,
            "status": "awaiting_acceptance" if candidate
                      else "coordinator_required"
        })

    if not lectures:
        notify_coordinator(
            conn, 0,
            f"No timetable lectures found for {teacher} on {date}. "
            "Please review the leave request."
        )

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Leave request submitted.",
        "leave_id": leave_id,
        "lectures_found": len(lectures),
        "substitution_requests": created
    }), 201


# ---------------- ALL LEAVES ----------------

@app.route('/api/leaves', methods=['GET'])
def get_all_leaves():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM teacher_leave").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# ---------------- SUBSTITUTION REQUESTS ----------------

@app.route('/api/substitution-requests', methods=['GET'])
def get_substitution_requests():
    conn = get_db_connection()
    teacher = request.args.get("teacher_name")

    if teacher:
        rows = conn.execute("""
            SELECT * FROM substitution_requests
            WHERE current_candidate = ? OR assigned_teacher = ?
            ORDER BY date, start_time
        """, (teacher, teacher)).fetchall()
    else:
        rows = conn.execute("""
            SELECT * FROM substitution_requests
            ORDER BY date, start_time
        """).fetchall()

    conn.close()
    return jsonify([dict(r) for r in rows])


# ---------------- ACCEPT / DECLINE ----------------

@app.route('/api/substitution-requests/<int:request_id>/respond',
           methods=['POST'])
def respond_to_substitution(request_id):
    data = request.get_json(silent=True) or {}
    teacher = data.get("teacher_name")
    action = data.get("action")
    reason = data.get("reason", "")

    if not teacher or action not in ("accept", "decline"):
        return jsonify({"error": "Provide teacher_name and accept/decline action"}), 400

    conn = get_db_connection()
    req = conn.execute("""
        SELECT * FROM substitution_requests WHERE id = ?
    """, (request_id,)).fetchone()

    if not req:
        conn.close()
        return jsonify({"error": "Request not found"}), 404

    if req["current_candidate"] != teacher or \
       req["status"] != "awaiting_acceptance":
        conn.close()
        return jsonify({"error": "This offer is not assigned to you"}), 403

    if action == "accept":
        conn.execute("""
            UPDATE substitution_requests
            SET assigned_teacher = ?,
                current_candidate = NULL,
                status = 'assigned',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (teacher, request_id))

    else:
        conn.execute("""
            INSERT INTO substitution_history
            (request_id, teacher_name, action, reason)
            VALUES (?, ?, 'declined', ?)
        """, (request_id, teacher, reason))

        offer_next_candidate(conn, req, req["candidate_index"] + 1)

    if action == "accept":
        conn.execute("""
            INSERT INTO substitution_history
            (request_id, teacher_name, action)
            VALUES (?, ?, 'accepted')
        """, (request_id, teacher))

    conn.commit()
    updated = conn.execute("""
        SELECT * FROM substitution_requests WHERE id = ?
    """, (request_id,)).fetchone()
    result = dict(updated)
    conn.close()

    return jsonify({
        "message": "Response recorded",
        "request": result
    })


# ---------------- REQUEST REPLACEMENT ----------------

@app.route('/api/substitution-requests/<int:request_id>/replacement',
           methods=['POST'])
def request_replacement(request_id):
    data = request.get_json(silent=True) or {}
    teacher = data.get("teacher_name")
    reason = data.get("reason", "")

    conn = get_db_connection()
    req = conn.execute("""
        SELECT * FROM substitution_requests WHERE id = ?
    """, (request_id,)).fetchone()

    if not req:
        conn.close()
        return jsonify({"error": "Request not found"}), 404

    if req["assigned_teacher"] != teacher or req["status"] != "assigned":
        conn.close()
        return jsonify({"error": "You are not the assigned substitute"}), 403

    conn.execute("""
        INSERT INTO substitution_history
        (request_id, teacher_name, action, reason)
        VALUES (?, ?, 'replacement_requested', ?)
    """, (request_id, teacher, reason))

    conn.execute("""
        UPDATE substitution_requests
        SET status = 'replacement_requested',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (request_id,))

    updated_req = conn.execute("""
        SELECT * FROM substitution_requests WHERE id = ?
    """, (request_id,)).fetchone()

    next_candidate = offer_next_candidate(
        conn, updated_req, req["candidate_index"] + 1
    )

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Replacement search started",
        "next_candidate": next_candidate,
        "status": "awaiting_acceptance" if next_candidate
                  else "coordinator_required"
    })


# ---------------- TEACHER AVAILABILITY ----------------

@app.route('/api/availability', methods=['POST'])
def mark_unavailable():
    data = request.get_json(silent=True) or {}

    teacher = data.get("teacher_name")
    date = data.get("date")
    start = data.get("start_time")
    end = data.get("end_time")
    reason = data.get("reason", "")

    if not all([teacher, date, start, end]):
        return jsonify({"error": "All availability fields are required"}), 400

    try:
        if time_minutes(start) >= time_minutes(end):
            return jsonify({"error": "End time must be after start time"}), 400
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    conn = get_db_connection()
    conn.execute("""
        INSERT INTO teacher_availability
        (teacher_name, date, start_time, end_time, reason)
        VALUES (?, ?, ?, ?, ?)
    """, (teacher, date, start, end, reason))

    conn.commit()
    conn.close()

    return jsonify({"message": "Unavailability recorded"}), 201


@app.route('/api/availability', methods=['GET'])
def get_availability():
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT * FROM teacher_availability ORDER BY date
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# ---------------- COORDINATOR ----------------

@app.route('/api/coordinator/substitutions', methods=['GET'])
def coordinator_substitutions():
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT * FROM substitution_requests
        WHERE status = 'coordinator_required'
        ORDER BY date, start_time
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/coordinator/substitutions/<int:request_id>/resolve',
           methods=['POST'])
def resolve_substitution(request_id):
    data = request.get_json(silent=True) or {}
    teacher = data.get("teacher_name")

    if not teacher:
        return jsonify({"error": "Provide teacher_name"}), 400

    conn = get_db_connection()
    req = conn.execute("""
        SELECT * FROM substitution_requests WHERE id = ?
    """, (request_id,)).fetchone()

    if not req:
        conn.close()
        return jsonify({"error": "Request not found"}), 404

    eligible = conn.execute("""
        SELECT 1 FROM teachers
        WHERE teacher_name = ? AND subject = ?
    """, (teacher, req["subject"])).fetchone()

    if not eligible or teacher == req["teacher_name"]:
        conn.close()
        return jsonify({"error": "Teacher is not eligible for this subject"}), 400

    conn.execute("""
        UPDATE substitution_requests
        SET assigned_teacher = ?,
            current_candidate = NULL,
            status = 'assigned',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (teacher, request_id))

    conn.execute("""
        INSERT INTO substitution_history
        (request_id, teacher_name, action, reason)
        VALUES (?, ?, 'coordinator_assigned', 'Manual coordinator assignment')
    """, (request_id, teacher))

    conn.execute("""
        UPDATE coordinator_notifications
        SET status = 'resolved', resolved_at = CURRENT_TIMESTAMP
        WHERE request_id = ? AND status = 'pending'
    """, (request_id,))

    conn.commit()
    conn.close()

    return jsonify({"message": "Substitute assigned successfully"})


# ---------------- HISTORY ----------------

@app.route('/api/substitution-history/<int:request_id>', methods=['GET'])
def substitution_history(request_id):
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT * FROM substitution_history
        WHERE request_id = ?
        ORDER BY created_at, id
    """, (request_id,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# ---------------- FRONTEND ----------------

@app.route('/')
def serve_index():
    return send_from_directory(FRONTEND_FOLDER, 'index.html')


@app.route('/<path:path>')
def serve_static_files(path):
    return send_from_directory(FRONTEND_FOLDER, path)


if __name__ == '__main__':
    print("College Management System API running")
    print("Database:", DB_PATH)
    app.run(debug=True, port=5000)
