# 🤖 FaceAttend AI — Smart Face Recognition Attendance System

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python" alt="Python"/>
  <img src="https://img.shields.io/badge/Flask-3.0%2B-black?style=for-the-badge&logo=flask" alt="Flask"/>
  <img src="https://img.shields.io/badge/OpenCV-4.x-green?style=for-the-badge&logo=opencv" alt="OpenCV"/>
  <img src="https://img.shields.io/badge/Socket.IO-Real--Time-red?style=for-the-badge&logo=socket.io" alt="Socket.IO"/>
  <img src="https://img.shields.io/badge/SQLite-Database-blue?style=for-the-badge&logo=sqlite" alt="SQLite"/>
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License"/>
</p>

A **state-of-the-art, full-stack AI attendance platform** featuring real-time facial recognition, **AI Gender Detection (Male/Female)**, **AI Age Estimation**, live webcam streaming, real-time WebSocket notifications, and a premium glassmorphic Single Page Application (SPA) dashboard.

---

## ✨ Features

- 🎥 **Real-time Face Recognition**: Live MJPEG video stream with bounding boxes, facial recognition confidence, and registered identity matching using dlib 128-d embeddings.
- 👨/👩 **AI Gender Detection**: Real-time neural network inference predicting gender (`Male` or `Female`) for each detected face.
- 🎂 **AI Age Estimation**: Real-time neural network inference predicting age groups (`0-2`, `4-6`, `8-12`, `15-20`, `25-32`, `38-43`, `48-53`, `60-100`).
- 📊 **Glassmorphic SPA Dashboard**: Live stats, animated counter metrics, and interactive SVG progress ring built with vanilla CSS.
- 🔔 **Socket.IO Real-Time Feed**: Instant check-in notifications and live activity feed streaming over WebSockets without manual page refresh.
- 🎓 **Webcam Face Registration**: Snap face photo from live webcam stream, enroll person details, and automatically store encodings.
- 📋 **Attendance History & Search**: Table view supporting text search (by Name or Student ID), department filtering, and date range filtering.
- 📁 **One-Click CSV Export**: Filtered attendance records download in standard CSV report format.
- 👥 **Student & Face Management**: View enrolled profile cards with gender/age badges, and manage or remove records.
- ⚙️ **Automated DB Auto-Migrations**: SQLite schema handles automatic database column additions (`gender`, `age`) and upserts seamlessly.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.10+, Flask, Flask-SocketIO, Flask-CORS, Pandas.
- **AI & Computer Vision**: OpenCV 4.x (Caffe Deep Learning DNN modules), `face_recognition` (dlib HOG model), NumPy.
- **Database**: SQLite3.
- **Frontend**: HTML5, Vanilla CSS3 (Custom Properties, Backdrop Filter Glassmorphism, CSS Grid/Flexbox), Vanilla JavaScript (ES6+), Socket.IO Client.

---

## 📁 Directory Structure

```text
face_recognition_attendance_system/
├── backend/
│   ├── app.py              ← Flask web server, API routes & Socket.IO events
│   ├── database.py         ← SQLite database layer with auto-migrations
│   ├── face_engine.py      ← OpenCV DNN + dlib face recognition & age/gender engine
│   ├── test_system.py      ← Automated unit & AI model integration test suite
│   ├── obama.jpg           ← Sample image for AI inference verification
│   └── requirements.txt    ← Python package dependencies
├── frontend/
│   ├── index.html          ← Glassmorphic SPA Dashboard
│   ├── style.css           ← Modern dark-mode glassmorphism styling
│   └── app.js              ← Single Page App logic & Socket.IO real-time client
├── data/
│   ├── models/             ← Pre-trained OpenCV Caffe Age & Gender DNN model files
│   ├── known_faces/        ← Serialized face encodings (encodings.pkl)
│   ├── photos/             ← Saved profile photos
│   ├── reports/            ← Exported CSV attendance reports
│   └── attendance.db       ← SQLite database
└── README.md
```

---

## 🚀 Quick Start & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/httpsasad/Face_Attendence_System.git
cd Face_Attendence_System
```

### 2. Install Dependencies
Ensure you have Python 3.10+ installed. Install all backend requirements:

```bash
cd backend
pip install -r requirements.txt
```

> 💡 **Tip (Windows users)**: `requirements.txt` includes `dlib-bin` pre-built wheels to bypass C++ compiler setup requirements.

### 3. Run Automated Tests
Verify database integrity, API routes, and AI age/gender inference:
```bash
python test_system.py
```

### 4. Launch the Server
```bash
python app.py
```

Open **`http://localhost:5000`** in your web browser! 🎉

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Serves the Single Page Application dashboard |
| `GET` | `/video_feed` | Live MJPEG camera stream with face overlays & AI labels |
| `GET` | `/api/stats` | Summary statistics (Total registered, Present, Absent, Rate) |
| `GET` | `/api/attendance` | Attendance records (Supports `search`, `department`, `date_from`, `date_to`) |
| `GET` | `/api/students` | List all registered students with profile details |
| `POST` | `/api/register` | Enroll a new face from base64 image capture |
| `DELETE` | `/api/students/<id>` | Delete a registered student and their encodings |
| `POST` | `/api/recognition/toggle` | Start or pause live face recognition |
| `GET` | `/api/recognition/status` | Get current recognition status (`active: true/false`) |
| `GET` | `/api/export` | Export filtered attendance records as a downloadable CSV file |
| `GET` | `/api/photo/<id>` | Serve student profile photo |

---

## 🧪 Testing & Verification

Run the comprehensive unit test suite to test all components:
```bash
python backend/test_system.py
```

**What it tests:**
1. **Database CRUD & Migrations**: Table initialization, student creation/deletion, attendance marking, daily duplicate prevention.
2. **REST API Endpoints**: Flask client endpoint status codes, payload structures, statistics calculations.
3. **AI Inference Engine**: OpenCV Caffe DNN model loading, gender classification, and age group estimation.

---

## 📄 License

This project is licensed under the **MIT License** — feel free to modify and use it in your own commercial or academic projects!
