#!/usr/bin/env python3
"""
Simple migration runner for security updates
"""
import sqlite3
import os
import sys
from datetime import datetime
import shutil

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_backup():
    """Create database backup"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"richness_backup_{timestamp}.db"
    
    try:
        shutil.copy2("richness.db", backup_name)
        print(f"✅ Backup created: {backup_name}")
        return backup_name
    except Exception as e:
        print(f"❌ Error creating backup: {e}")
        raise

def create_audit_tables():
    """Create audit tables for security logging"""
    conn = sqlite3.connect('richness.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    try:
        # Create audit tables
        audit_tables = [
            """
            CREATE TABLE IF NOT EXISTS audit_authentication (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER,
                username TEXT,
                event_type TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                success BOOLEAN,
                failure_reason TEXT,
                details TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS audit_data_access (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER,
                username TEXT,
                resource TEXT,
                action TEXT,
                ip_address TEXT,
                success BOOLEAN,
                details TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS audit_system_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                event_type TEXT NOT NULL,
                severity TEXT DEFAULT 'info',
                username TEXT,
                ip_address TEXT,
                details TEXT,
                system_info TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME NOT NULL,
                last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT,
                user_agent TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (user_id) REFERENCES usuarios (id)
            )
            """
        ]
        
        for table_sql in audit_tables:
            cur.execute(table_sql)
            
        print("✅ Audit tables created successfully")
        
        # Add audit fields to usuarios table if they don't exist
        cur.execute("PRAGMA table_info(usuarios)")
        existing_columns = [row['name'] for row in cur.fetchall()]
        
        audit_fields = {
            'account_locked': 'INTEGER DEFAULT 0',
            'login_attempts': 'INTEGER DEFAULT 0',
            'last_login': 'DATETIME',
            'created_at': 'DATETIME DEFAULT CURRENT_TIMESTAMP'
        }
        
        for field, definition in audit_fields.items():
            if field not in existing_columns:
                cur.execute(f"ALTER TABLE usuarios ADD COLUMN {field} {definition}")
                print(f"✅ Added audit field: {field}")
        
        conn.commit()
        print("✅ User table audit fields added")
        
    except Exception as e:
        print(f"❌ Error creating audit tables: {e}")
        raise
    finally:
        conn.close()

def migrate_passwords():
    """Migrate passwords from SHA-256 to bcrypt format"""
    try:
        # Import security modules
        from security.auth.authentication import SecureAuthentication
        
        auth = SecureAuthentication()
        conn = sqlite3.connect('richness.db')
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Find users with legacy passwords (8-64 chars, not starting with $2b$)
        cur.execute("SELECT id, usuario, senha FROM usuarios WHERE LENGTH(senha) < 65 AND senha NOT LIKE '$2b$%'")
        users_to_migrate = cur.fetchall()
        
        migrated_count = 0
        
        for user in users_to_migrate:
            user_id, username, old_password = user['id'], user['usuario'], user['senha']
            
            try:
                # Since we can't recover the original password from hash,
                # we'll create a temporary password and require reset
                temp_password = f"TempReset{user_id}!"
                new_hash = auth.hash_password(temp_password)
                
                # Update with new hash and lock account for reset
                cur.execute("""
                    UPDATE usuarios 
                    SET senha = ?, 
                        account_locked = 1,
                        login_attempts = 0
                    WHERE id = ?
                """, (new_hash, user_id))
                
                migrated_count += 1
                print(f"✅ User {username}: password migrated to bcrypt (reset required)")
                
            except Exception as e:
                print(f"❌ Error migrating user {username}: {e}")
        
        conn.commit()
        conn.close()
        
        print(f"✅ Migrated {migrated_count} passwords to bcrypt")
        
        if migrated_count > 0:
            print("\n⚠️  IMPORTANT:")
            print("- Users with migrated passwords need to reset their passwords")
            print("- Their accounts are temporarily locked")
            print("- Use the admin panel or reset function to unlock")
        
        return migrated_count
        
    except ImportError as e:
        print(f"❌ Could not import security modules: {e}")
        print("Please ensure security modules are properly installed")
        return 0
    except Exception as e:
        print(f"❌ Error during password migration: {e}")
        return 0

def log_migration_event():
    """Log the migration event"""
    try:
        from security.audit.security_logger import get_security_logger
        
        logger = get_security_logger()
        logger.log_system_event(
            event_type='security_migration_completed',
            details={
                'migration_type': 'passwords_and_audit_tables',
                'timestamp': datetime.now().isoformat()
            }
        )
        print("✅ Migration event logged")
        
    except ImportError:
        print("⚠️  Could not log migration event - security logger not available")
    except Exception as e:
        print(f"⚠️  Could not log migration event: {e}")

def main():
    """Run the security migration"""
    print("🔐 RICHNESS SECURITY MIGRATION")
    print("=" * 40)
    print()
    
    try:
        # Step 1: Create backup
        print("📁 Creating database backup...")
        backup_file = create_backup()
        print()
        
        # Step 2: Create audit tables
        print("🗄️  Creating audit tables...")
        create_audit_tables()
        print()
        
        # Step 3: Migrate passwords
        print("🔒 Migrating passwords to bcrypt...")
        migrated_count = migrate_passwords()
        print()
        
        # Step 4: Log migration
        print("📝 Logging migration event...")
        log_migration_event()
        print()
        
        print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        print(f"📄 Backup saved as: {backup_file}")
        print(f"🔐 Passwords migrated: {migrated_count}")
        
        if migrated_count > 0:
            print("\n⚠️  NEXT STEPS:")
            print("1. Users will need to reset their passwords")
            print("2. Test the login system")
            print("3. Verify audit logging is working")
            print("4. Check the Security Dashboard")
        
    except Exception as e:
        print(f"💥 MIGRATION FAILED: {e}")
        print("Please check the error and try again")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
