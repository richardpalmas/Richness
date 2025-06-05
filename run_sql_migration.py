import sqlite3
import os

def run_sql_migration():
    """Execute the SQL migration script"""
    
    # Connect to database
    conn = sqlite3.connect('richness.db')
    
    try:
        # Read and execute SQL file
        with open('migration.sql', 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        # Execute the script
        conn.executescript(sql_script)
        
        print("✅ SQL migration executed successfully")
        
        # Add audit fields to usuarios table
        cur = conn.cursor()
        
        # Check existing columns
        cur.execute("PRAGMA table_info(usuarios)")
        existing_columns = [row[1] for row in cur.fetchall()]
        
        audit_fields = [
            ('account_locked', 'INTEGER DEFAULT 0'),
            ('login_attempts', 'INTEGER DEFAULT 0'),
            ('last_login', 'DATETIME'),
            ('created_at', 'DATETIME DEFAULT CURRENT_TIMESTAMP')
        ]
        
        for field_name, field_def in audit_fields:
            if field_name not in existing_columns:
                cur.execute(f"ALTER TABLE usuarios ADD COLUMN {field_name} {field_def}")
                print(f"✅ Added audit field: {field_name}")
            else:
                print(f"⚠️  Field {field_name} already exists")
        
        conn.commit()
        print("✅ All migration steps completed")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    
    finally:
        conn.close()

if __name__ == "__main__":
    print("🔐 Running Security Migration...")
    run_sql_migration()
    print("Migration process finished.")
