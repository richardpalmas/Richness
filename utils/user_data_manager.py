"""
Gerenciador de dados por usuário para isolamento de informações financeiras.
"""

import os
import streamlit as st
import hashlib
import json
from pathlib import Path

class UserDataManager:
    """Gerencia o isolamento de dados por usuário"""
    
    def __init__(self):
        self.base_data_dir = "user_data"
        self._ensure_base_directory()
    
    def _ensure_base_directory(self):
        """Garante que o diretório base existe"""
        os.makedirs(self.base_data_dir, exist_ok=True)
    
    def _get_current_user(self):
        """Obtém o usuário atual da sessão"""
        return st.session_state.get('usuario', 'default')
    
    def _sanitize_username(self, username):
        """Sanitiza o nome do usuário para uso como nome de diretório"""
        # Criar hash do username para evitar problemas com caracteres especiais
        username_hash = hashlib.md5(username.encode()).hexdigest()[:16]
        return f"user_{username_hash}"
    
    def get_user_directory(self, username=None):
        """Obtém o diretório específico do usuário"""
        if username is None:
            username = self._get_current_user()
        
        sanitized_username = self._sanitize_username(username)
        user_dir = os.path.join(self.base_data_dir, sanitized_username)
        
        # Criar diretório do usuário se não existir
        os.makedirs(user_dir, exist_ok=True)
        
        return user_dir
    
    def get_user_file_path(self, filename, username=None):
        """Obtém o caminho completo para um arquivo específico do usuário"""
        user_dir = self.get_user_directory(username)
        return os.path.join(user_dir, filename)
    
    def get_user_ofx_directories(self, username=None):
        """Obtém os diretórios de extratos e faturas específicos do usuário"""
        user_dir = self.get_user_directory(username)
        
        extratos_dir = os.path.join(user_dir, "extratos")
        faturas_dir = os.path.join(user_dir, "faturas")
        
        # Criar diretórios se não existirem
        os.makedirs(extratos_dir, exist_ok=True)
        os.makedirs(faturas_dir, exist_ok=True)        
        return extratos_dir, faturas_dir
    
    def backup_user_data(self, username=None):
        """Cria backup dos dados do usuário"""
        if username is None:
            username = self._get_current_user()
        
        user_dir = self.get_user_directory(username)
        
        try:
            import shutil
            from datetime import datetime
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{self._sanitize_username(username)}_{timestamp}"
            backup_path = os.path.join("backups", backup_name)
            
            os.makedirs("backups", exist_ok=True)
            shutil.copytree(user_dir, backup_path)
            
            return backup_path
        except Exception as e:
            st.error(f"Erro ao criar backup: {e}")
            return None
    
    def list_user_files(self, username=None):
        """Lista todos os arquivos do usuário"""
        user_dir = self.get_user_directory(username)
        
        files = []
        for root, dirs, file_list in os.walk(user_dir):
            for file in file_list:
                rel_path = os.path.relpath(os.path.join(root, file), user_dir)
                files.append(rel_path)
        
        return files
    
    def get_user_stats(self, username=None):
        """Obtém estatísticas dos dados do usuário"""
        user_dir = self.get_user_directory(username)
        extratos_dir, faturas_dir = self.get_user_ofx_directories(username)
        
        stats = {
            'total_files': 0,
            'extratos_count': 0,
            'faturas_count': 0,
            'json_files': [],
            'disk_usage': 0
        }
        
        # Contar arquivos
        for root, dirs, files in os.walk(user_dir):
            for file in files:
                file_path = os.path.join(root, file)
                stats['total_files'] += 1
                
                # Calcular tamanho
                try:
                    stats['disk_usage'] += os.path.getsize(file_path)
                except:
                    pass
                
                # Categorizar arquivos
                if file.endswith('.ofx'):
                    if 'extratos' in root:
                        stats['extratos_count'] += 1
                    elif 'faturas' in root:
                        stats['faturas_count'] += 1
                elif file.endswith('.json'):
                    stats['json_files'].append(file)
        
        return stats

# Instância global do gerenciador
user_data_manager = UserDataManager()
