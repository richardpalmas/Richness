import sqlite3
import bcrypt

# Connect and get user
conn = sqlite3.connect('richness.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute('SELECT id, usuario, senha FROM usuarios WHERE usuario = "richardpalmas"')
user = cur.fetchone()
print(f'Current password for {user["usuario"]}: {user["senha"]}')

# Generate bcrypt hash for new password
new_password = 'SecurePass@2024!'
hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt(12)).decode()
print(f'New bcrypt hash: {hashed[:50]}...')

# Update user
cur.execute('UPDATE usuarios SET senha = ?, account_locked = 0 WHERE id = ?', (hashed, user['id']))
conn.commit()
print('✅ Password updated successfully!')

# Verify
cur.execute('SELECT senha, account_locked FROM usuarios WHERE id = ?', (user['id'],))
updated = cur.fetchone()
print(f'Updated password starts with bcrypt: {updated["senha"].startswith("$2b$")}')
print(f'Account unlocked: {updated["account_locked"] == 0}')

conn.close()
