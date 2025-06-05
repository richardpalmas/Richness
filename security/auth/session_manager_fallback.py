"""
Fallback session manager for environments with JWT issues
Uses simple token-based session management
"""
import secrets
import hashlib
import json
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta


class SessionManager:
    """
    Gerenciador de sessões fallback sem dependência do JWT
    """
    
    def __init__(self, secret_key: Optional[str] = None, session_timeout_hours: int = 2):
        self.secret_key = secret_key or secrets.token_hex(32)
        self.session_timeout_hours = session_timeout_hours
        self.active_sessions = {}  # Em produção, usar Redis ou banco de dados
    
    def create_session(self, user_data: Dict[str, Any]) -> Optional[str]:
        """
        Cria nova sessão e retorna token
        """
        try:
            # Gerar token único
            token = secrets.token_urlsafe(32)
            
            # Criar dados da sessão
            session_data = {
                'user_id': user_data.get('id'),
                'username': user_data.get('username'),
                'email': user_data.get('email'),
                'full_name': user_data.get('full_name'),
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(hours=self.session_timeout_hours)).isoformat(),
                'last_activity': datetime.now().isoformat()
            }
            
            # Armazenar sessão
            self.active_sessions[token] = session_data
            
            return token
            
        except Exception as e:
            print(f"Session creation error: {e}")
            return None
    
    def validate_session(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Valida token e retorna dados da sessão se válida
        """
        try:
            if not token or token not in self.active_sessions:
                return None
            
            session_data = self.active_sessions[token]
            
            # Verificar expiração
            expires_at = datetime.fromisoformat(session_data['expires_at'])
            if datetime.now() > expires_at:
                # Sessão expirada
                del self.active_sessions[token]
                return None
            
            # Atualizar última atividade
            session_data['last_activity'] = datetime.now().isoformat()
            self.active_sessions[token] = session_data
            
            return {
                'user_id': session_data['user_id'],
                'username': session_data['username'],
                'email': session_data['email'],
                'full_name': session_data['full_name']
            }
            
        except Exception as e:
            print(f"Session validation error: {e}")
            return None
    
    def destroy_session(self, token: str) -> bool:
        """
        Remove sessão (logout)
        """
        try:
            if token in self.active_sessions:
                del self.active_sessions[token]
                return True
            return False
        except Exception:
            return False
    
    def refresh_session(self, token: str) -> Optional[str]:
        """
        Renova sessão e retorna novo token
        """
        try:
            session_data = self.validate_session(token)
            if session_data:
                # Remover sessão antiga
                self.destroy_session(token)
                # Criar nova sessão
                return self.create_session(session_data)
            return None
        except Exception:
            return None
    
    def cleanup_expired_sessions(self):
        """
        Remove sessões expiradas
        """
        try:
            current_time = datetime.now()
            expired_tokens = []
            
            for token, session_data in self.active_sessions.items():
                expires_at = datetime.fromisoformat(session_data['expires_at'])
                if current_time > expires_at:
                    expired_tokens.append(token)
            
            for token in expired_tokens:
                del self.active_sessions[token]
                
        except Exception as e:
            print(f"Session cleanup error: {e}")
    
    def get_session_info(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Retorna informações completas da sessão
        """
        try:
            if token in self.active_sessions:
                session_data = self.active_sessions[token].copy()
                # Verificar se não expirou
                expires_at = datetime.fromisoformat(session_data['expires_at'])
                if datetime.now() > expires_at:
                    del self.active_sessions[token]
                    return None
                return session_data
            return None
        except Exception:
            return None
    
    def is_session_valid(self, token: str) -> bool:
        """
        Verifica se sessão é válida sem retornar dados
        """
        return self.validate_session(token) is not None


# Instância global para reutilização
_session_manager = None

def get_session_manager() -> SessionManager:
    """Retorna instância do gerenciador de sessões"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
