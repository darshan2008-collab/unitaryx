import sqlite3
import os

source_db = r"c:\Users\ELOT\Desktop\Unitary X\freelancer\instance\unitaryx_v2.db"
target_db = r"c:\Users\ELCOT\Desktop\Unitary X\freelancer\unitaryx_v2.db"

# Fix typo in source_db path
source_db = source_db.replace("ELOT", "ELCOT")

print(f"Merging users from {source_db} to {target_db}")

if not os.path.exists(source_db):
    print("Source DB not found!")
    exit(1)
if not os.path.exists(target_db):
    print("Target DB not found!")
    exit(1)

try:
    s_conn = sqlite3.connect(source_db)
    t_conn = sqlite3.connect(target_db)
    
    s_cur = s_conn.cursor()
    t_cur = t_conn.cursor()
    
    # Get all users from source
    s_cur.execute("SELECT * FROM users")
    users = s_cur.fetchall()
    
    # Get column names
    s_cur.execute("PRAGMA table_info(users)")
    cols = [col[1] for col in s_cur.fetchall()]
    placeholders = ", ".join(["?"] * len(cols))
    col_str = ", ".join(cols)
    
    print(f"Found {len(users)} users to merge.")
    
    for user in users:
        # Check if user already exists by email
        email_idx = cols.index('email')
        email = user[email_idx]
        
        t_cur.execute("SELECT id FROM users WHERE email=?", (email,))
        ext = t_cur.fetchone()
        
        if ext:
            print(f"User {email} already exists, skipping.")
        else:
            print(f"Adding user {email}...")
            # Use REPLACE or INSERT IGNORE equivalent
            t_cur.execute(f"INSERT INTO users ({col_str}) VALUES ({placeholders})", user)
            
    t_conn.commit()
    print("Merge complete!")
    
    s_conn.close()
    t_conn.close()
    
except Exception as e:
    print(f"Error: {e}")
