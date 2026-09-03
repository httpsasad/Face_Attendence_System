import requests
payload = {
    "student_id": "TEST-123",
    "name": "Test",
    "department": "Test",
    "role": "User",
    "image": "data:image/jpeg;base64,invalidbase64data=="
}
res = requests.post("http://127.0.0.1:5000/api/register", json=payload)
print(res.status_code, res.text)
