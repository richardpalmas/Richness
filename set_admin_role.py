#!/usr/bin/env python3
"""
Script para definir o usuário richardpalmas como administrador
"""
import sqlite3
from pathlib import Path
import sys
import os

# Adicionar o diretório atual ao path para importar módulos locais
sys.path.insert(0, os.getcwd())

def set_richardpalmas_as_admin():
    """Define o usuário richardpalmas como administrador no banco de dados"""
    print("Definindo richardpalmas como administrador...")
    
    # Conexão com o banco de dados
    conn = sqlite3.connect('richness.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Verificar se o usuário richardpalmas existe
        cursor.execute("SELECT id FROM usuarios WHERE usuario = ?", ("richardpalmas",))
        user = cursor.fetchone()
        
        if not user:
            print("❌ Usuário richardpalmas não encontrado no banco de dados.")
            return False
        
        user_id = user['id']
        
        # Criar tabela user_roles se não existir
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
        
        # Verificar se já existe um registro de admin para richardpalmas
        cursor.execute('''
            SELECT id FROM user_roles 
            WHERE user_id = ? AND role = ?
        ''', (user_id, 'admin'))
        
        if cursor.fetchone():
            print("✅ O usuário richardpalmas já é administrador.")
            return True
        
        # Adicionar role de admin para richardpalmas
        cursor.execute('''
            INSERT INTO user_roles (user_id, role, created_at, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''', (user_id, 'admin'))
        
        conn.commit()
        print("✅ Usuário richardpalmas definido como administrador com sucesso!")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Erro ao definir richardpalmas como admin: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    set_richardpalmas_as_admin()
