import sqlite3

DB_PATH = 'richness_v2.db'

def add_created_at():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE personalidades_ia_usuario ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        print("Coluna 'created_at' adicionada com sucesso.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Coluna 'created_at' já existe.")
        else:
            print("Erro:", e)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_created_at() 