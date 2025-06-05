import sqlite3
import os

print("Current directory:", os.getcwd())
print("Starting admin role setup...")

try:
    # Connect to database
    db_path = 'richness.db'
    print(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if the database is accessible
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1")
    table = cursor.fetchone()
    print(f"Database accessible, found table: {table[0] if table else 'none'}")
      # Look for richardpalmas user
    cursor.execute("SELECT id, usuario FROM usuarios WHERE usuario='richardpalmas'")
    user = cursor.fetchone()
    
    user_id = None
    if user:
        user_id = user[0]
        print(f"Found richardpalmas with ID: {user_id}")
        
        # Make sure user_roles table exists
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, role),
            FOREIGN KEY(user_id) REFERENCES usuarios(id)
        )
        """)
        print("user_roles table exists")
        
        # Add admin role for richardpalmas
        try:
            cursor.execute("INSERT OR IGNORE INTO user_roles (user_id, role) VALUES (?, ?)", 
                         (user_id, 'admin'))
            conn.commit()
            print("SUCCESS: richardpalmas set as admin")
        except sqlite3.Error as e:
            print(f"Error inserting role: {e}")
    else:
        print("ERROR: richardpalmas user not found")
      # Verify the role was set
    if user_id:
        cursor.execute("SELECT * FROM user_roles WHERE user_id=? AND role='admin'", (user_id,))
        role = cursor.fetchone()
        if role:
            print(f"VERIFIED: Admin role set for user_id {user_id}")
        else:
            print("ERROR: Failed to verify admin role")
    
except Exception as e:
    print(f"ERROR: {e}")
finally:
    if 'conn' in locals():
        conn.close()
        print("Database connection closed")

print("Setup complete.")
