
import cv2
import face_recognition
import os
import numpy as np
import pandas as pd
from datetime import datetime

known_encodings = []
known_names = []

dataset_path = "dataset"

for person_name in os.listdir(dataset_path):
    person_folder = os.path.join(dataset_path, person_name)

    for image_name in os.listdir(person_folder):
        image_path = os.path.join(person_folder, image_name)

        image = face_recognition.load_image_file(image_path)
        encodings = face_recognition.face_encodings(image)

        if encodings:
            known_encodings.append(encodings[0])
            known_names.append(person_name)

attendance_file = "attendance.csv"

if not os.path.exists(attendance_file):
    df = pd.DataFrame(columns=["Name", "Time"])
    df.to_csv(attendance_file, index=False)

marked_names = set()

video = cv2.VideoCapture(0)

while True:
    ret, frame = video.read()

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    face_locations = face_recognition.face_locations(rgb_frame)
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):

        matches = face_recognition.compare_faces(known_encodings, face_encoding)

        name = "Unknown"

        face_distances = face_recognition.face_distance(known_encodings, face_encoding)

        if len(face_distances) > 0:
            best_match_index = np.argmin(face_distances)

            if matches[best_match_index]:
                name = known_names[best_match_index]

        cv2.rectangle(frame, (left, top), (right, bottom), (0,255,0), 2)
        cv2.putText(frame, name, (left, top - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)

        if name != "Unknown" and name not in marked_names:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            df = pd.read_csv(attendance_file)

            new_row = pd.DataFrame([[name, now]], columns=["Name", "Time"])

            df = pd.concat([df, new_row], ignore_index=True)

            df.to_csv(attendance_file, index=False)

            marked_names.add(name)

            print(f"Attendance marked for {name}")

    cv2.imshow("Face Recognition Attendance", frame)

    if cv2.waitKey(1) == ord('q'):
        break

video.release()
cv2.destroyAllWindows()
