import sys
import os
import unittest
import numpy as np
import cv2
import json

# Add backend dir to sys.path
sys.path.insert(0, os.path.dirname(__file__))

from database import init_db, get_connection, add_student, get_students, delete_student, mark_attendance, get_attendance, get_stats
from face_engine import FaceEngine
from app import app

class TestAttendanceSystem(unittest.TestCase):
    def setUp(self):
        init_db()
        self.client = app.test_client()
        self.client.testing = True
        self.engine = FaceEngine()

    def test_01_database_student_ops(self):
        test_id = "TEST-UNIT-001"
        test_name = "Unit Test User"
        test_dept = "CS-Testing"
        test_role = "Tester"
        test_gender = "Male"
        test_age = "25-32"

        # Cleanup if exists
        delete_student(test_id)
        conn = get_connection()
        conn.cursor().execute('DELETE FROM attendance WHERE student_id = ?', (test_id,))
        conn.commit()
        conn.close()

        # Test Add Student with Gender & Age
        res = add_student(test_id, test_name, test_dept, test_role, gender=test_gender, age=test_age, photo_path=None)
        self.assertTrue(res, "Adding new student should return True")

        # Test Get Students
        students = get_students()
        target = next((s for s in students if s['student_id'] == test_id), None)
        self.assertIsNotNone(target, "Registered student should be in get_students()")
        self.assertEqual(target['gender'], test_gender)
        self.assertEqual(target['age'], test_age)

        # Test Mark Attendance with Gender & Age
        marked = mark_attendance(test_id, test_name, test_dept, gender=test_gender, age=test_age)
        self.assertTrue(marked, "Marking attendance first time today should succeed")

        # Test Duplicate Mark Attendance same day
        marked_again = mark_attendance(test_id, test_name, test_dept, gender=test_gender, age=test_age)
        self.assertFalse(marked_again, "Marking attendance second time same day should return False")

        # Test Get Attendance
        records = get_attendance(search=test_id)
        self.assertGreater(len(records), 0, "Attendance record should exist for test student")
        self.assertEqual(records[0]['gender'], test_gender)
        self.assertEqual(records[0]['age'], test_age)

        # Cleanup
        delete_student(test_id)

    def test_02_flask_api_routes(self):
        # Test GET /api/stats
        response = self.client.get('/api/stats')
        self.assertEqual(response.status_code, 200)

        # Test GET /api/attendance
        response = self.client.get('/api/attendance')
        self.assertEqual(response.status_code, 200)

        # Test GET /api/students
        response = self.client.get('/api/students')
        self.assertEqual(response.status_code, 200)

    def test_03_age_gender_ai_inference(self):
        img_path = os.path.join(os.path.dirname(__file__), 'obama.jpg')
        if os.path.exists(img_path):
            img = cv2.imread(img_path)
            gender, g_conf, age, a_conf = self.engine.predict_age_gender(img)
            self.assertEqual(gender, 'Male', f"Predicted gender should be Male, got {gender}")
            self.assertIn(age, ['38-43', '25-32', '48-53'], f"Predicted age bracket should be realistic, got {age}")
            print(f"\n[AI Inference Test] Obama image -> Gender: {gender} ({g_conf}%), Age: {age} ({a_conf}%)")

if __name__ == '__main__':
    unittest.main()
