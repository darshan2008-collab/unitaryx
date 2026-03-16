import sqlite3
import os
from werkzeug.security import generate_password_hash

db_path = r"c:\Users\ELCOT\Desktop\Unitary X\freelancer\unitaryx_v2.db"
new_password = "darshan@ux2026"

print(f"Updating all passwords in {db_path} to: {new_password}")

if not os.path.exists(db_path):
    print("Database not found!")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Generate the hash once
    hashed_pass = generate_password_hash(new_password)
    
    # Update all users (admins and standard users)
    cur.execute("UPDATE users SET password = ?", (hashed_pass,))
    rows_affected = cur.rowcount
    
    conn.commit()
    print(f"Successfully updated {rows_affected} users.")
    
    # Verify the roles reset
    cur.execute("SELECT name, email, role FROM users WHERE role = 'admin'")
    admins = cur.fetchall()
    print("\nVerified Admins:")
    for admin in admins:
        print(f" - {admin[0]} ({admin[1]})")
        
    conn.close()
    print("\nAll admins can now login with: darshan@ux2026")
    
except Exception as e:
    print(f"Error: {e}")
