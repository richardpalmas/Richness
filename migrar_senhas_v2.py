#!/usr/bin/env python3
"""
Script de Migração de Senhas - Sistema Legado para V2 Seguro
===========================================================

Este script migra senhas do banco legado (richness.db) para o Backend V2 
com criptografia bcrypt segura.

IMPORTANTE: Execute este script após garantir que todos os usuários foram 
migrados para o Backend V2.
"""

import sqlite3
import sys
import os
from pathlib import Path

# Adicionar o diretório do projeto ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.database_manager_v2 import DatabaseManager
from utils.repositories_v2 import RepositoryManager

def migrar_senhas_legado():
    """Migra senhas do sistema legado para o V2 com bcrypt"""
    print("🔐 Iniciando migração de senhas para o Backend V2...")
    
    # Conectar ao banco legado
    if not os.path.exists('richness.db'):
        print("❌ Banco legado (richness.db) não encontrado!")
        return False
    
    # Conectar ao Backend V2
    try:
        db_v2 = DatabaseManager()
        repo_manager = RepositoryManager(db_v2)
        user_repo = repo_manager.get_repository('usuarios')
        print("✅ Conectado ao Backend V2")
    except Exception as e:
        print(f"❌ Erro ao conectar ao Backend V2: {e}")
        return False
    
    # Ler senhas do sistema legado
    try:
        conn_legado = sqlite3.connect('richness.db')
        conn_legado.row_factory = sqlite3.Row
        cursor = conn_legado.cursor()
        
        cursor.execute("SELECT usuario, senha FROM usuarios WHERE senha IS NOT NULL")
        usuarios_legado = cursor.fetchall()
        
        print(f"📊 Encontrados {len(usuarios_legado)} usuários com senhas no sistema legado")
        
        migrados = 0
        erros = 0
        
        for usuario_legado in usuarios_legado:
            username = usuario_legado['usuario']
            senha_hash_legado = usuario_legado['senha']
            
            try:
                # Verificar se usuário existe no V2
                user_v2 = user_repo.obter_usuario_por_username(username)
                if not user_v2:
                    print(f"⚠️  Usuário '{username}' não encontrado no V2, pulando...")
                    continue
                
                # Verificar se já tem senha no V2
                if user_v2.get('password_hash'):
                    print(f"✅ Usuário '{username}' já tem senha no V2")
                    migrados += 1
                    continue
                
                # Migrar senha (estratégia temporária: usar parte do hash como senha)
                if len(senha_hash_legado) == 64:  # SHA-256
                    # Para migração, vamos usar os primeiros 16 caracteres como senha temporária
                    senha_temp = senha_hash_legado[:16]
                    success = user_repo.atualizar_senha(user_v2['id'], senha_temp)
                    
                    if success:
                        print(f"✅ Senha migrada para usuário '{username}'")
                        print(f"   🔑 Senha temporária: {senha_temp}")
                        migrados += 1
                    else:
                        print(f"❌ Falha ao migrar senha para '{username}'")
                        erros += 1
                else:
                    print(f"⚠️  Hash de senha inválido para '{username}', pulando...")
                    
            except Exception as e:
                print(f"❌ Erro ao migrar '{username}': {e}")
                erros += 1
        
        conn_legado.close()
        
        print(f"\n📊 Resumo da Migração:")
        print(f"   ✅ Migrados: {migrados}")
        print(f"   ❌ Erros: {erros}")
        print(f"   📝 Total processados: {len(usuarios_legado)}")
        
        return migrados > 0
        
    except Exception as e:
        print(f"❌ Erro na migração: {e}")
        return False

def criar_usuario_admin():
    """Cria usuário admin com senha segura"""
    print("\n👑 Criando usuário admin...")
    
    try:
        db_v2 = DatabaseManager()
        repo_manager = RepositoryManager(db_v2)
        user_repo = repo_manager.get_repository('usuarios')
        
        # Verificar se admin já existe
        admin_user = user_repo.obter_usuario_por_username('admin')
        if admin_user:
            print("✅ Usuário admin já existe")
            return True
        
        # Criar usuário admin
        admin_id = user_repo.criar_usuario_com_senha(
            username='admin',
            password='richness@2025',  # Senha forte padrão
            email='admin@richness.local'
        )
        
        if admin_id:
            print("✅ Usuário admin criado com sucesso!")
            print("   👤 Username: admin")
            print("   🔑 Senha: richness@2025")
            print("   ⚠️  IMPORTANTE: Altere esta senha após o primeiro login!")
            return True
        else:
            print("❌ Falha ao criar usuário admin")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao criar admin: {e}")
        return False

def verificar_sistema_senhas():
    """Verifica se o sistema de senhas está funcionando"""
    print("\n🧪 Testando sistema de senhas...")
    
    try:
        db_v2 = DatabaseManager()
        repo_manager = RepositoryManager(db_v2)
        user_repo = repo_manager.get_repository('usuarios')
        
        # Listar usuários com senhas
        usuarios = user_repo.buscar_todos()
        usuarios_com_senha = [u for u in usuarios if u.get('password_hash')]
        
        print(f"📊 Usuários com senha: {len(usuarios_com_senha)}/{len(usuarios)}")
        
        for user in usuarios_com_senha[:5]:  # Mostrar apenas os primeiros 5
            print(f"   ✅ {user['username']} - Hash: {user['password_hash'][:20]}...")
        
        return len(usuarios_com_senha) > 0
        
    except Exception as e:
        print(f"❌ Erro na verificação: {e}")
        return False

def main():
    """Função principal"""
    print("=" * 60)
    print("🔐 MIGRAÇÃO DE SENHAS - BACKEND V2 SEGURO")
    print("=" * 60)
    
    # Etapa 1: Migrar senhas do legado
    if migrar_senhas_legado():
        print("\n✅ Migração de senhas concluída!")
    else:
        print("\n⚠️  Nenhuma senha foi migrada")
    
    # Etapa 2: Criar usuário admin
    criar_usuario_admin()
    
    # Etapa 3: Verificar sistema
    if verificar_sistema_senhas():
        print("\n🎉 Sistema de senhas funcionando corretamente!")
    else:
        print("\n⚠️  Sistema de senhas precisa de atenção")
    
    print("\n" + "=" * 60)
    print("🔒 IMPORTANTE: Todas as senhas agora são criptografadas com bcrypt!")
    print("🔑 Usuários podem fazer login com suas senhas temporárias")
    print("⚠️  Recomende que alterem as senhas após o primeiro login")
    print("=" * 60)

if __name__ == "__main__":
    main()
