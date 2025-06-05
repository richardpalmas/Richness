import sqlite3

try:
    # Connect to the database
    conn = sqlite3.connect('richness.db')
    cursor = conn.cursor()
    
    # Find richardpalmas user ID
    cursor.execute("SELECT id FROM usuarios WHERE usuario = 'richardpalmas'")
    user = cursor.fetchone()
    
    if not user:
        print("❌ User richardpalmas not found")
        exit(1)
    
    user_id = user[0]
    print(f"✅ Found user richardpalmas with ID {user_id}")
    
    # Create user_roles table if not exists
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, role),
        FOREIGN KEY(user_id) REFERENCES usuarios(id)
    )
    ''')
    print("✅ Ensured user_roles table exists")
    
    # Add admin role for richardpalmas
    cursor.execute("INSERT OR IGNORE INTO user_roles (user_id, role) VALUES (?, ?)", 
                  (user_id, 'admin'))
    conn.commit()
    print("✅ Set richardpalmas as admin")
    
except Exception as e:
    print(f"❌ Error: {e}")
finally:
    if 'conn' in locals():
        conn.close()
    print("✅ Done")
