import sqlite3
import os

db_paths = [
    r"c:\Users\ELCOT\Desktop\Unitary X\unitaryx_v2.db",
    r"c:\Users\ELCOT\Desktop\Unitary X\freelancer\unitaryx_v2.db",
    r"c:\Users\ELCOT\Desktop\Unitary X\freelancer\instance\unitaryx_v2.db",
    r"c:\Users\ELCOT\Desktop\Unitary X\unitaryx.db"
]

for path in db_paths:
    if os.path.exists(path):
        print(f"\nChecking: {path}")
        try:
            conn = sqlite3.connect(path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            print(f"Tables: {tables}")
            for table in tables:
                table_name = table[0]
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"  - {table_name}: {count} rows")
                if table_name == 'users':
                    cursor.execute("SELECT id, name, email, role FROM users")
                    users = cursor.fetchall()
                    for user in users:
                        print(f"    User: {user}")
            conn.close()
        except Exception as e:
            print(f"Error checking {path}: {e}")
    else:
        print(f"\nNot found: {path}")
