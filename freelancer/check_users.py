from app import db, User, app

with app.app_context():
    users = User.query.all()
    print("Listing users in database:")
    for u in users:
        print(f"ID: {u.id} | Email: {u.email} | Role: {u.role} | Active: {u.is_active}")
