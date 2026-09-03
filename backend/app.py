from flask import Flask, Response, request, jsonify, send_from_directory, send_file
from flask_socketio import SocketIO
from flask_cors import CORS
import cv2
import threading
import time
import os
import pandas as pd
from datetime import datetime

from database import init_db, add_student, get_students, delete_student, mark_attendance, get_attendance, get_stats
from face_engine import FaceEngine

# ── App Setup ──────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(__file__)
FRONTEND_DIR = os.path.join(BASE_DIR, '..', 'frontend')
REPORTS_DIR = os.path.join(BASE_DIR, '..', 'data', 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ── Initialize ─────────────────────────────────────────────────────────────────
init_db()
face_engine = FaceEngine()

# ── Camera State ───────────────────────────────────────────────────────────────
camera = None
camera_lock = threading.Lock()
recognition_active = False
last_recognition = {}   # student_id → timestamp
COOLDOWN_SECONDS = 30


def open_camera():
    global camera
    if camera is None or not camera.isOpened():
        indices_to_try = [
            (0, cv2.CAP_DSHOW), 
            (1, cv2.CAP_DSHOW), 
            (0, cv2.CAP_ANY), 
            (1, cv2.CAP_ANY)
        ]
        
        for index, backend in indices_to_try:
            camera = cv2.VideoCapture(index, backend)
            if camera.isOpened():
                print(f"Successfully opened camera at index {index} with backend {backend}")
                break
                
        if camera and camera.isOpened():
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            camera.set(cv2.CAP_PROP_FPS, 30)
        else:
            print("Failed to open any camera!")
            
    return camera


def generate_frames():
    global recognition_active, last_recognition
    while True:
        with camera_lock:
            cam = open_camera()
            success, frame = cam.read()
        if not success:
            time.sleep(0.1)
            continue

        if recognition_active and face_engine.count() > 0:
            results = face_engine.recognize_faces(frame)
            for res in results:
                top, right, bottom, left = res['location']
                name = res['name']
                sid = res['student_id']
                dept = res['department']
                conf = res['confidence']
                gender = res.get('gender', 'Unknown')
                age = res.get('age', 'Unknown')

                if name != 'Unknown' and sid:
                    now = time.time()
                    if sid not in last_recognition or (now - last_recognition[sid]) > COOLDOWN_SECONDS:
                        marked = mark_attendance(sid, name, dept, gender=gender, age=age)
                        if marked:
                            last_recognition[sid] = now
                            socketio.emit('attendance_marked', {
                                'student_id': sid,
                                'name': name,
                                'department': dept,
                                'gender': gender,
                                'age': age,
                                'time': datetime.now().strftime('%H:%M:%S'),
                                'confidence': conf
                            })
                    color = (0, 230, 120)
                    label = f"{name} | {gender} ({age}) | {conf}%"
                else:
                    color = (60, 60, 255)
                    label = f"Unknown | {gender} ({age})"

                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                cv2.rectangle(frame, (left, bottom - 28), (right, bottom), color, cv2.FILLED)
                cv2.putText(frame, label, (left + 5, bottom - 8),
                            cv2.FONT_HERSHEY_DUPLEX, 0.5, (10, 10, 10), 1)

        _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')


@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/stats')
def api_stats():
    return jsonify(get_stats())


@app.route('/api/attendance')
def api_attendance():
    records = get_attendance(
        date_from=request.args.get('date_from'),
        date_to=request.args.get('date_to'),
        department=request.args.get('department'),
        search=request.args.get('search')
    )
    return jsonify(records)


@app.route('/api/students')
def api_students():
    return jsonify(get_students())


@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.json or {}
    sid = data.get('student_id', '').strip()
    name = data.get('name', '').strip()
    dept = data.get('department', '').strip()
    role = data.get('role', 'Student').strip()
    image = data.get('image', '')

    if not all([sid, name, dept, image]):
        return jsonify({'success': False, 'message': 'All fields are required.'}), 400

    ok, result, gender, age = face_engine.register_face(image, sid, name, dept)
    if not ok:
        return jsonify({'success': False, 'message': result}), 400

    db_ok = add_student(sid, name, dept, role, gender=gender, age=age, photo_path=result)

    socketio.emit('student_registered', {'name': name, 'student_id': sid, 'gender': gender, 'age': age})
    return jsonify({
        'success': True,
        'message': f'{name} ({gender}, Age {age}) registered successfully!',
        'gender': gender,
        'age': age
    })


@app.route('/api/students/<student_id>', methods=['DELETE'])
def api_delete_student(student_id):
    delete_student(student_id)
    face_engine.delete_face(student_id)
    return jsonify({'success': True})


@app.route('/api/recognition/toggle', methods=['POST'])
def toggle_recognition():
    global recognition_active
    recognition_active = not recognition_active
    return jsonify({'active': recognition_active})


@app.route('/api/recognition/status')
def recognition_status():
    return jsonify({'active': recognition_active})


@app.route('/api/export')
def export_csv():
    records = get_attendance(
        date_from=request.args.get('date_from'),
        date_to=request.args.get('date_to'),
        department=request.args.get('department')
    )
    if not records:
        return jsonify({'success': False, 'message': 'No records found for export.'}), 404
    df = pd.DataFrame(records)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'attendance_{ts}.csv'
    filepath = os.path.join(REPORTS_DIR, filename)
    df.to_csv(filepath, index=False)
    return send_file(filepath, as_attachment=True, download_name=filename)


@app.route('/api/photo/<student_id>')
def get_photo(student_id):
    photos_dir = os.path.join(BASE_DIR, '..', 'data', 'photos')
    path = os.path.join(photos_dir, f'{student_id}.jpg')
    if os.path.exists(path):
        return send_file(path, mimetype='image/jpeg')
    return '', 404


# ── SocketIO ───────────────────────────────────────────────────────────────────

@socketio.on('connect')
def on_connect():
    stats = get_stats()
    socketio.emit('stats_update', stats)


# ── Entry Point ────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=" * 55)
    print("  FaceAttend AI -- Attendance System")
    print("  Open http://localhost:5000 in your browser")
    print("=" * 55)
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
