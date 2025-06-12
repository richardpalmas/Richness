import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Script utilitário para listar usuários ativos e conceder admin ao richarddasilva
from database import listar_usuarios_ativos, conceder_admin_para_usuario

if __name__ == "__main__":
    print("Usuários ativos:")
    usuarios = listar_usuarios_ativos()
    for u in usuarios:
        print(f"ID: {u['id']}, Usuário: {u['usuario']}, Nome: {u['nome']}, Email: {u['email']}")

    print("\nConcedendo permissão de admin ao usuário 'richarddasilva'...")
    if conceder_admin_para_usuario('richarddasilva'):
        print("Permissão concedida com sucesso!")
    else:
        print("Usuário 'richarddasilva' não encontrado ou erro ao conceder permissão.")
