import cv2
import sys

def test_camera():
    indices_to_try = [0, 1]
    for index in indices_to_try:
        try:
            cam = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            if cam.isOpened():
                success, frame = cam.read()
                if success and frame is not None:
                    print(f"Camera WORKS on index {index} (DSHOW)")
                    cam.release()
                    return True
            cam.release()
            
            cam = cv2.VideoCapture(index)
            if cam.isOpened():
                success, frame = cam.read()
                if success and frame is not None:
                    print(f"Camera WORKS on index {index} (DEFAULT)")
                    cam.release()
                    return True
            cam.release()
        except Exception as e:
            print(f"Exception on {index}: {e}")
            
    print("Camera FAILED")
    return False

if __name__ == '__main__':
    test_camera()
