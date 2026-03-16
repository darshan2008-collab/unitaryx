import sqlite3
import os

db_path = r"c:\Users\ELCOT\Desktop\Unitary X\freelancer\unitaryx_v2.db"

if not os.path.exists(db_path):
    print(f"Error: {db_path} not found.")
    exit(1)

conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT name, email, role FROM users WHERE role = 'admin'")
admins = cur.fetchall()

print(f"Total Admins: {len(admins)}")
for admin in admins:
    print(f" - {admin[0]} | {admin[1]} | {admin[2]}")

conn.close()
