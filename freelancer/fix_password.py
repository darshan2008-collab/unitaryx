from app import db, User, app
from werkzeug.security import generate_password_hash

EMAIL = "harikavi1301@gamil.com"
NEW_PASS = "hari@123"

with app.app_context():
    # Try exact email first
    user = User.query.filter_by(email=EMAIL).first()
    if not user:
        # Try case-insensitive search
        user = User.query.filter(db.func.lower(User.email) == EMAIL.lower()).first()
    
    if user:
        print(f"Found user: {user.id} | {user.email} | role={user.role} | active={user.is_active}")
        user.password_hash = generate_password_hash(NEW_PASS)
        db.session.commit()
        print(f"Password reset to: {NEW_PASS}")
    else:
        print(f"User '{EMAIL}' NOT found. Existing users:")
        for u in User.query.all():
            print(f"  - {u.email} | role={u.role}")
