import face_recognition
import cv2
import numpy as np
import pickle
import os
import base64

FACES_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'known_faces')
PHOTOS_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'photos')
MODELS_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'models')
ENCODINGS_FILE = os.path.join(FACES_DIR, 'encodings.pkl')

GENDER_PROTO = os.path.join(MODELS_DIR, 'gender_deploy.prototxt')
GENDER_MODEL = os.path.join(MODELS_DIR, 'gender_net.caffemodel')
AGE_PROTO = os.path.join(MODELS_DIR, 'age_deploy.prototxt')
AGE_MODEL = os.path.join(MODELS_DIR, 'age_net.caffemodel')

GENDER_LIST = ['Male', 'Female']
AGE_LIST = ['0-2', '4-6', '8-12', '15-20', '25-32', '38-43', '48-53', '60-100']
MODEL_MEAN_VALUES = (78.4263377603, 87.7689143744, 114.895847746)


class FaceEngine:
    def __init__(self):
        os.makedirs(FACES_DIR, exist_ok=True)
        os.makedirs(PHOTOS_DIR, exist_ok=True)
        self.known_encodings = []
        self.known_names = []
        self.known_ids = []
        self.known_departments = []
        self.known_genders = []
        self.known_ages = []

        # Load Caffe Age & Gender Nets
        self.gender_net = None
        self.age_net = None
        if os.path.exists(GENDER_PROTO) and os.path.exists(GENDER_MODEL):
            try:
                self.gender_net = cv2.dnn.readNetFromCaffe(GENDER_PROTO, GENDER_MODEL)
            except Exception as e:
                print(f"Failed to load gender model: {e}")

        if os.path.exists(AGE_PROTO) and os.path.exists(AGE_MODEL):
            try:
                self.age_net = cv2.dnn.readNetFromCaffe(AGE_PROTO, AGE_MODEL)
            except Exception as e:
                print(f"Failed to load age model: {e}")

        self.load_encodings()

    def load_encodings(self):
        if os.path.exists(ENCODINGS_FILE):
            try:
                with open(ENCODINGS_FILE, 'rb') as f:
                    data = pickle.load(f)
                    self.known_encodings = data.get('encodings', [])
                    self.known_names = data.get('names', [])
                    self.known_ids = data.get('ids', [])
                    self.known_departments = data.get('departments', [])
                    self.known_genders = data.get('genders', ['Unknown'] * len(self.known_ids))
                    self.known_ages = data.get('ages', ['Unknown'] * len(self.known_ids))
            except Exception as e:
                print(f"Error loading encodings: {e}")

    def save_encodings(self):
        data = {
            'encodings': self.known_encodings,
            'names': self.known_names,
            'ids': self.known_ids,
            'departments': self.known_departments,
            'genders': self.known_genders,
            'ages': self.known_ages
        }
        with open(ENCODINGS_FILE, 'wb') as f:
            pickle.dump(data, f)

    def predict_age_gender(self, face_crop):
        """Predict gender and age for a cropped face image."""
        if face_crop is None or face_crop.size == 0:
            return "Unknown", 0.0, "Unknown", 0.0

        gender, gender_conf = "Unknown", 0.0
        age, age_conf = "Unknown", 0.0

        try:
            blob = cv2.dnn.blobFromImage(face_crop, 1.0, (227, 227), MODEL_MEAN_VALUES, swapRB=False)
            
            if self.gender_net is not None:
                self.gender_net.setInput(blob)
                gender_preds = self.gender_net.forward()
                g_idx = int(gender_preds[0].argmax())
                gender = GENDER_LIST[g_idx]
                gender_conf = round(float(gender_preds[0][g_idx]) * 100, 1)

            if self.age_net is not None:
                self.age_net.setInput(blob)
                age_preds = self.age_net.forward()
                a_idx = int(age_preds[0].argmax())
                age = AGE_LIST[a_idx]
                age_conf = round(float(age_preds[0][a_idx]) * 100, 1)

        except Exception as e:
            print(f"Error in predict_age_gender: {e}")

        return gender, gender_conf, age, age_conf

    def register_face(self, image_data, student_id, name, department):
        """Register a new face from base64 image data."""
        try:
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            img_bytes = base64.b64decode(image_data)
            nparr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return False, "Could not decode image", "Unknown", "Unknown"
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            face_locations = face_recognition.face_locations(rgb_img, model='hog')
            if not face_locations:
                return False, "No face detected. Please ensure your face is clearly visible.", "Unknown", "Unknown"

            encodings = face_recognition.face_encodings(rgb_img, face_locations)
            if not encodings:
                return False, "Could not encode face.", "Unknown", "Unknown"

            # Crop face for age & gender estimation
            top, right, bottom, left = face_locations[0]
            h, w = img.shape[:2]
            face_crop = img[max(0, top):min(h, bottom), max(0, left):min(w, right)]
            gender, _, age, _ = self.predict_age_gender(face_crop)

            # Save photo
            photo_path = os.path.join(PHOTOS_DIR, f'{student_id}.jpg')
            cv2.imwrite(photo_path, img)

            # Remove existing encoding if student re-registers
            if student_id in self.known_ids:
                idx = self.known_ids.index(student_id)
                self.known_encodings.pop(idx)
                self.known_names.pop(idx)
                self.known_ids.pop(idx)
                self.known_departments.pop(idx)
                if idx < len(self.known_genders): self.known_genders.pop(idx)
                if idx < len(self.known_ages): self.known_ages.pop(idx)

            self.known_encodings.append(encodings[0])
            self.known_names.append(name)
            self.known_ids.append(student_id)
            self.known_departments.append(department)
            self.known_genders.append(gender)
            self.known_ages.append(age)
            self.save_encodings()

            return True, photo_path, gender, age
        except Exception as e:
            return False, str(e), "Unknown", "Unknown"

    def recognize_faces(self, frame, tolerance=0.50):
        """Recognize faces in a frame. Returns list of result dicts including gender & age."""
        small = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_small, model='hog')
        face_encodings = face_recognition.face_encodings(rgb_small, face_locations)

        h, w = frame.shape[:2]
        results = []
        for encoding, location in zip(face_encodings, face_locations):
            name = "Unknown"
            student_id = None
            department = None
            confidence = 0

            if self.known_encodings:
                distances = face_recognition.face_distance(self.known_encodings, encoding)
                min_idx = int(np.argmin(distances))
                min_dist = distances[min_idx]
                if min_dist < tolerance:
                    name = self.known_names[min_idx]
                    student_id = self.known_ids[min_idx]
                    department = self.known_departments[min_idx]
                    confidence = round((1 - min_dist) * 100, 1)

            top, right, bottom, left = [v * 4 for v in location]
            face_crop = frame[max(0, top):min(h, bottom), max(0, left):min(w, right)]
            gender, gender_conf, age, age_conf = self.predict_age_gender(face_crop)

            # If student is known and has saved gender/age, use registered or live
            if student_id and student_id in self.known_ids:
                s_idx = self.known_ids.index(student_id)
                if s_idx < len(self.known_genders) and self.known_genders[s_idx] != "Unknown":
                    gender = self.known_genders[s_idx]
                if s_idx < len(self.known_ages) and self.known_ages[s_idx] != "Unknown":
                    age = self.known_ages[s_idx]

            results.append({
                'name': name,
                'student_id': student_id,
                'department': department,
                'confidence': confidence,
                'gender': gender,
                'age': age,
                'location': (top, right, bottom, left)
            })
        return results

    def delete_face(self, student_id):
        if student_id in self.known_ids:
            idx = self.known_ids.index(student_id)
            self.known_encodings.pop(idx)
            self.known_names.pop(idx)
            self.known_ids.pop(idx)
            self.known_departments.pop(idx)
            if idx < len(self.known_genders): self.known_genders.pop(idx)
            if idx < len(self.known_ages): self.known_ages.pop(idx)
            self.save_encodings()
        photo_path = os.path.join(PHOTOS_DIR, f'{student_id}.jpg')
        if os.path.exists(photo_path):
            os.remove(photo_path)

    def count(self):
        return len(self.known_ids)
