import sqlite3
import os

basedir = os.path.abspath(os.path.dirname(__file__))
db_paths = [
    os.path.join(basedir, 'unitaryx_v2.db'),
    os.path.join(basedir, 'instance', 'unitaryx_v2.db'),
    os.path.join(basedir, 'unitaryx.db')
]

new_columns = [
    ("priority", "VARCHAR(20) DEFAULT 'Medium'"),
    ("value", "INTEGER DEFAULT 0"),
    ("internal_notes", "TEXT")
]

for db_path in db_paths:
    if not os.path.exists(db_path):
        continue
    
    print(f"Migrating: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    for col_name, col_def in new_columns:
        try:
            cursor.execute(f"ALTER TABLE project_requests ADD COLUMN {col_name} {col_def}")
            print(f"  Added column: {col_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"  Column {col_name} already exists.")
            else:
            
                print(f"  Error adding {col_name}: {e}")
    
    conn.commit()
    conn.close()
