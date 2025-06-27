import sqlite3
import os

DB_PATH = 'richness_v2.db'

ALTER_SQL = """
ALTER TABLE personalidades_ia_usuario ADD COLUMN nome_customizado VARCHAR(20);
"""

def coluna_existe(conn, table, column):
    cur = conn.execute(f'PRAGMA table_info({table})')
    return any(row[1] == column for row in cur.fetchall())

def add_campos_personalidade_customizada():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        alter_cmds = [
            "ALTER TABLE personalidades_ia_usuario ADD COLUMN foto_path TEXT",
            "ALTER TABLE personalidades_ia_usuario ADD COLUMN idioma TEXT",
            "ALTER TABLE personalidades_ia_usuario ADD COLUMN amigavel TEXT",
            "ALTER TABLE personalidades_ia_usuario ADD COLUMN regionalismo TEXT",
            "ALTER TABLE personalidades_ia_usuario ADD COLUMN cultura TEXT",
            "ALTER TABLE personalidades_ia_usuario ADD COLUMN arquetipo TEXT",
            "ALTER TABLE personalidades_ia_usuario ADD COLUMN tom_voz TEXT",
            "ALTER TABLE personalidades_ia_usuario ADD COLUMN estilo_comunicacao TEXT",
            "ALTER TABLE personalidades_ia_usuario ADD COLUMN nivel_humor TEXT",
            "ALTER TABLE personalidades_ia_usuario ADD COLUMN empatia TEXT",
            "ALTER TABLE personalidades_ia_usuario ADD COLUMN autoridade_conselho TEXT",
            "ALTER TABLE personalidades_ia_usuario ADD COLUMN profundidade_expertise TEXT",
            "ALTER TABLE personalidades_ia_usuario ADD COLUMN perfil_risco TEXT",
            "ALTER TABLE personalidades_ia_usuario ADD COLUMN motivacao_call TEXT",
            "ALTER TABLE personalidades_ia_usuario ADD COLUMN valores_centrais TEXT",
            "ALTER TABLE personalidades_ia_usuario ADD COLUMN reacao_fracasso TEXT"
        ]
        for cmd in alter_cmds:
            try:
                cursor.execute(cmd)
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    print(f"Coluna já existe: {cmd}")
                else:
                    print(f"Erro ao executar: {cmd}", e)
        print("Migração concluída.")
    finally:
        conn.commit()
        conn.close()

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
    add_campos_personalidade_customizada() 