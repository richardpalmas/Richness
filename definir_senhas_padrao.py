#!/usr/bin/env python3
"""
Script para definir senhas padrão para usuários V2 existentes
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.database_manager_v2 import DatabaseManager
from utils.repositories_v2 import RepositoryManager

def definir_senhas_padrao():
    """Define senhas padrão para usuários que não têm senha"""
    print("🔑 Definindo senhas padrão para usuários V2...")
    
    try:
        db_v2 = DatabaseManager()
        repo_manager = RepositoryManager(db_v2)
        user_repo = repo_manager.get_repository('usuarios')
        
        # Buscar usuários sem senha
        todos_usuarios = user_repo.buscar_todos()
        usuarios_sem_senha = [u for u in todos_usuarios if not u.get('password_hash')]
        
        print(f"📊 Encontrados {len(usuarios_sem_senha)} usuários sem senha")
        
        for user in usuarios_sem_senha:
            username = user['username']
            # Senha padrão: username + "@2025"
            senha_padrao = f"{username}@2025"
            
            success = user_repo.atualizar_senha(user['id'], senha_padrao)
            if success:
                print(f"✅ Senha definida para '{username}' → {senha_padrao}")
            else:
                print(f"❌ Falha ao definir senha para '{username}'")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

if __name__ == "__main__":
    definir_senhas_padrao()
