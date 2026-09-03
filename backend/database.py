import sqlite3
import os
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'attendance.db')


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            department TEXT,
            role TEXT DEFAULT 'Student',
            gender TEXT,
            age TEXT,
            photo_path TEXT,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            name TEXT NOT NULL,
            department TEXT,
            gender TEXT,
            age TEXT,
            date DATE NOT NULL,
            time TIME NOT NULL,
            status TEXT DEFAULT 'Present'
        )
    ''')
    # Auto-migrations for existing databases
    for col in ['gender', 'age']:
        try:
            cursor.execute(f"ALTER TABLE students ADD COLUMN {col} TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute(f"ALTER TABLE attendance ADD COLUMN {col} TEXT")
        except sqlite3.OperationalError:
            pass

    conn.commit()
    conn.close()


def add_student(student_id, name, department, role, gender=None, age=None, photo_path=None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            '''INSERT INTO students (student_id, name, department, role, gender, age, photo_path)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(student_id) DO UPDATE SET
               name=excluded.name, department=excluded.department, role=excluded.role,
               gender=COALESCE(excluded.gender, students.gender),
               age=COALESCE(excluded.age, students.age),
               photo_path=COALESCE(excluded.photo_path, students.photo_path)''',
            (student_id, name, department, role, gender, age, photo_path)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_students():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM students ORDER BY registered_at DESC')
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_student(student_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM students WHERE student_id = ?', (student_id,))
    conn.commit()
    conn.close()


def mark_attendance(student_id, name, department, gender=None, age=None):
    today = date.today().isoformat()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id FROM attendance WHERE student_id = ? AND date = ?',
        (student_id, today)
    )
    if cursor.fetchone():
        conn.close()
        return False  # already marked today
    now_time = datetime.now().strftime('%H:%M:%S')
    hour = datetime.now().hour
    status = 'Late' if hour >= 9 else 'Present'
    cursor.execute(
        'INSERT INTO attendance (student_id, name, department, gender, age, date, time, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (student_id, name, department, gender, age, today, now_time, status)
    )
    conn.commit()
    conn.close()
    return True


def get_attendance(date_from=None, date_to=None, department=None, search=None):
    conn = get_connection()
    cursor = conn.cursor()
    query = 'SELECT * FROM attendance WHERE 1=1'
    params = []
    if date_from:
        query += ' AND date >= ?'
        params.append(date_from)
    if date_to:
        query += ' AND date <= ?'
        params.append(date_to)
    if department:
        query += ' AND department = ?'
        params.append(department)
    if search:
        query += ' AND (name LIKE ? OR student_id LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])
    query += ' ORDER BY date DESC, time DESC'
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats():
    conn = get_connection()
    cursor = conn.cursor()
    today = date.today().isoformat()
    cursor.execute('SELECT COUNT(*) as c FROM students')
    total = cursor.fetchone()['c']
    cursor.execute('SELECT COUNT(DISTINCT student_id) as c FROM attendance WHERE date = ?', (today,))
    present = cursor.fetchone()['c']
    absent = max(0, total - present)
    pct = round((present / total * 100) if total > 0 else 0, 1)
    cursor.execute('SELECT * FROM attendance ORDER BY date DESC, time DESC LIMIT 10')
    recent = [dict(r) for r in cursor.fetchall()]
    cursor.execute('SELECT DISTINCT department FROM students WHERE department IS NOT NULL')
    depts = [r[0] for r in cursor.fetchall()]
    conn.close()
    return {
        'total_students': total,
        'present_today': present,
        'absent_today': absent,
        'attendance_percentage': pct,
        'recent_activity': recent,
        'departments': depts
    }
