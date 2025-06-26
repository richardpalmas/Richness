import sqlite3
import os

DB_PATH = 'richness_v2.db'

ALTER_SQL = """
ALTER TABLE personalidades_ia_usuario ADD COLUMN nome_customizado VARCHAR(20);
"""

def coluna_existe(conn, table, column):
    cur = conn.execute(f'PRAGMA table_info({table})')
    return any(row[1] == column for row in cur.fetchall())

def main():
    if not os.path.exists(DB_PATH):
        print(f"Arquivo de banco de dados não encontrado: {DB_PATH}")
        return
    conn = sqlite3.connect(DB_PATH)
    try:
        if coluna_existe(conn, 'personalidades_ia_usuario', 'nome_customizado'):
            print("Campo 'nome_customizado' já existe. Nenhuma alteração necessária.")
        else:
            conn.execute(ALTER_SQL)
            print("Campo 'nome_customizado' adicionado com sucesso.")
    except Exception as e:
        print(f"Erro ao executar migração: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main() 