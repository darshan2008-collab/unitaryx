import requests

session = requests.Session()

login_data = {
    'login_type': 'admin',
    'email': 'admin@unitaryx.com',
    'password': 'Admin@123'
}

print("Attempting to login...")
r1 = session.post('http://127.0.0.1:5005/login', data=login_data, headers={'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest'})
print("Login response:", r1.text)

print("Attempting to submit contact form...")
contact_data = {
    "name": "AI Test User",
    "email": "test@example.com",
    "phone": "9876543210",
    "service": "software",
    "deadline": "2026-12-31",
    "message": "This is a test message to verify email notifications are working perfectly!"
}
r2 = session.post('http://127.0.0.1:5005/api/contact', json=contact_data)
print("Contact API response:", r2.text)
