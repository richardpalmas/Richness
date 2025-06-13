import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Script utilitário para listar usuários ativos e conceder admin - Backend V2
from utils.database_manager_v2 import DatabaseManager
from utils.repositories_v2 import UsuarioRepository

def listar_usuarios_ativos():
    """Lista usuários ativos usando Backend V2"""
    db_manager = DatabaseManager()
    user_repo = UsuarioRepository(db_manager)
    
    # Buscar todos os usuários
    result = db_manager.executar_query(
        "SELECT id, username, email, created_at FROM usuarios ORDER BY created_at DESC"
    )
    
    usuarios = []
    for row in result:
        usuarios.append({
            'id': row['id'],
            'usuario': row['username'],
            'nome': row['username'],  # Backend V2 não tem campo nome separado
            'email': row['email'] or ''
        })
    
    return usuarios

def conceder_admin_para_usuario(username):
    """Concede permissão de admin para um usuário usando Backend V2"""
    try:
        db_manager = DatabaseManager()
        
        # Verificar se usuário existe
        result = db_manager.executar_query(
            "SELECT id FROM usuarios WHERE username = ?",
            [username]
        )
        
        if not result:
            return False
        
        user_id = result[0]['id']
        
        # Adicionar/atualizar permissão de admin
        db_manager.executar_insert(
            """INSERT OR REPLACE INTO user_permissions 
               (user_id, permission_type, granted_at) 
               VALUES (?, 'admin', CURRENT_TIMESTAMP)""",
            [user_id]
        )
        
        return True
        
    except Exception as e:
        print(f"Erro ao conceder admin: {e}")
        return False

if __name__ == "__main__":
    print("Usuários ativos (Backend V2):")
    usuarios = listar_usuarios_ativos()
    for u in usuarios:
        print(f"ID: {u['id']}, Usuário: {u['usuario']}, Nome: {u['nome']}, Email: {u['email']}")

    print("\nConcedendo permissão de admin ao usuário 'richarddasilva'...")
    if conceder_admin_para_usuario('richarddasilva'):
        print("Permissão concedida com sucesso!")
    else:
        print("Usuário 'richarddasilva' não encontrado ou erro ao conceder permissão.")
