"""
Gerenciador de sessões seguras com JWT e timeout
Implementa gestão de sessões com expiração automática e invalidação segura
"""
import jwt
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
import streamlit as st
import os
from pathlib import Path

from security.audit.security_logger import get_security_logger


class SessionManager:
    """Gerenciador de sessões seguras com JWT"""
    
    def __init__(self):
        self.logger = get_security_logger()
        self.secret_key = self._get_or_create_secret_key()
        self.algorithm = 'HS256'
        
        # Configurações de timeout
        self.session_timeout_minutes = 120  # 2 horas
        self.inactivity_timeout_minutes = 30  # 30 minutos
        self.max_concurrent_sessions = 3
        
        # Armazenamento de sessões ativas
        self._active_sessions = {}
        self._session_activity = {}
    
    def _get_or_create_secret_key(self) -> str:
        """Obtém ou cria chave secreta para JWT"""
        key_file = Path('.session_key')
        
        if key_file.exists():
            try:
                with open(key_file, 'r') as f:
                    return f.read().strip()
            except Exception:
                pass
        
        # Gerar nova chave secreta
        secret_key = secrets.token_urlsafe(64)
        
        try:
            with open(key_file, 'w') as f:
                f.write(secret_key)
            # Tornar arquivo legível apenas pelo proprietário
            os.chmod(key_file, 0o600)
        except Exception:
            # Se não conseguir salvar, usar chave temporária
            pass
        
        return secret_key
    
    def create_session(self, user_data: Dict[str, Any], ip_address: str = None) -> str:
        """
        Cria nova sessão segura
        Retorna: token JWT da sessão
        """
        try:
            current_time = datetime.now()
            session_id = secrets.token_urlsafe(32)
            
            # Payload do JWT
            payload = {
                'session_id': session_id,
                'user_id': user_data.get('id'),
                'username': user_data.get('usuario'),
                'nome': user_data.get('nome'),
                'email': user_data.get('email'),
                'iat': current_time.timestamp(),
                'exp': (current_time + timedelta(minutes=self.session_timeout_minutes)).timestamp(),
                'ip_address': ip_address
            }
            
            # Gerar token JWT
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            
            # Armazenar sessão ativa
            self._active_sessions[session_id] = {
                'user_id': user_data.get('id'),
                'username': user_data.get('usuario'),
                'created_at': current_time,
                'ip_address': ip_address,
                'last_activity': current_time
            }
            
            # Limitar sessões concorrentes
            self._cleanup_old_sessions(user_data.get('usuario'))
            
            # Log da criação de sessão
            self.logger.log_session_event(
                username=user_data.get('usuario'),
                event_type='session_created'
            )
            
            return token
            
        except Exception as e:
            self.logger.log_system_error(
                error_type='session_creation_error',
                error_message=str(e),
                username=user_data.get('usuario')
            )
            raise
    
    def validate_session(self, token: str, ip_address: str = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Valida sessão e retorna dados do usuário
        Retorna: (válida, dados_usuario)
        """
        try:
            if not token:
                return False, None
            
            # Decodificar JWT
            try:
                payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            except jwt.ExpiredSignatureError:
                self._log_session_event('session_expired', payload.get('username') if 'username' in locals() else 'unknown')
                return False, None
            except jwt.InvalidTokenError:
                self._log_session_event('invalid_token', 'unknown')
                return False, None
            
            session_id = payload.get('session_id')
            username = payload.get('username')
            
            # Verificar se sessão ainda está ativa
            if session_id not in self._active_sessions:
                self._log_session_event('session_not_found', username)
                return False, None
            
            session_data = self._active_sessions[session_id]
            
            # Verificar IP (opcional, dependendo da configuração)
            if ip_address and session_data.get('ip_address') != ip_address:
                self.logger.log_suspicious_activity(
                    f"IP address mismatch for session {session_id}",
                    username=username,
                    ip_address=ip_address,
                    severity='high'
                )
                # Pode optar por invalidar a sessão ou apenas loggar
            
            # Verificar timeout de inatividade
            last_activity = session_data.get('last_activity')
            if last_activity:
                time_since_activity = datetime.now() - last_activity
                if time_since_activity.total_seconds() > (self.inactivity_timeout_minutes * 60):
                    self._invalidate_session(session_id)
                    self._log_session_event('session_timeout', username)
                    return False, None
            
            # Atualizar última atividade
            session_data['last_activity'] = datetime.now()
            
            return True, payload
            
        except Exception as e:
            self.logger.log_system_error(
                error_type='session_validation_error',
                error_message=str(e)
            )
            return False, None
    
    def invalidate_session(self, token: str = None, session_id: str = None, username: str = None):
        """Invalida sessão específica"""
        try:
            if token:
                try:
                    payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
                    session_id = payload.get('session_id')
                    username = payload.get('username')
                except jwt.InvalidTokenError:
                    return
            
            if session_id:
                self._invalidate_session(session_id)
                self._log_session_event('session_invalidated', username)
        
        except Exception as e:
            self.logger.log_system_error(
                error_type='session_invalidation_error',
                error_message=str(e),
                username=username
            )
    
    def invalidate_all_user_sessions(self, username: str):
        """Invalida todas as sessões de um usuário"""
        try:
            sessions_to_remove = []
            
            for session_id, session_data in self._active_sessions.items():
                if session_data.get('username') == username:
                    sessions_to_remove.append(session_id)
            
            for session_id in sessions_to_remove:
                self._invalidate_session(session_id)
            
            self._log_session_event('all_sessions_invalidated', username)
            
        except Exception as e:
            self.logger.log_system_error(
                error_type='bulk_session_invalidation_error',
                error_message=str(e),
                username=username
            )
    
    def _invalidate_session(self, session_id: str):
        """Remove sessão do armazenamento ativo"""
        if session_id in self._active_sessions:
            del self._active_sessions[session_id]
        if session_id in self._session_activity:
            del self._session_activity[session_id]
    
    def _cleanup_old_sessions(self, username: str):
        """Remove sessões expiradas e limita sessões concorrentes"""
        current_time = datetime.now()
        sessions_to_remove = []
        user_sessions = []
        
        # Identificar sessões expiradas e do usuário atual
        for session_id, session_data in self._active_sessions.items():
            # Verificar expiração por timeout de inatividade
            last_activity = session_data.get('last_activity')
            if last_activity:
                time_since_activity = current_time - last_activity
                if time_since_activity.total_seconds() > (self.inactivity_timeout_minutes * 60):
                    sessions_to_remove.append(session_id)
                    continue
            
            # Coletar sessões do usuário atual
            if session_data.get('username') == username:
                user_sessions.append((session_id, session_data.get('created_at', current_time)))
        
        # Remover sessões expiradas
        for session_id in sessions_to_remove:
            self._invalidate_session(session_id)
        
        # Limitar sessões concorrentes (manter apenas as mais recentes)
        if len(user_sessions) >= self.max_concurrent_sessions:
            # Ordenar por data de criação (mais antigas primeiro)
            user_sessions.sort(key=lambda x: x[1])
            
            # Remover sessões mais antigas
            sessions_to_remove = user_sessions[:-self.max_concurrent_sessions + 1]
            for session_id, _ in sessions_to_remove:
                self._invalidate_session(session_id)
    
    def _log_session_event(self, event_type: str, username: str):
        """Log de eventos de sessão"""
        self.logger.log_session_event(username, event_type)
    
    def refresh_session(self, token: str) -> Optional[str]:
        """
        Renova sessão se estiver próxima do vencimento
        Retorna: novo token ou None se não foi possível renovar
        """
        try:
            is_valid, payload = self.validate_session(token)
            if not is_valid:
                return None
            
            # Verificar se precisa renovar (se expira em menos de 30 minutos)
            exp_timestamp = payload.get('exp')
            if exp_timestamp:
                exp_datetime = datetime.fromtimestamp(exp_timestamp)
                time_to_expire = exp_datetime - datetime.now()
                
                if time_to_expire.total_seconds() < (30 * 60):  # 30 minutos
                    # Criar nova sessão
                    user_data = {
                        'id': payload.get('user_id'),
                        'usuario': payload.get('username'),
                        'nome': payload.get('nome'),
                        'email': payload.get('email')
                    }
                    
                    # Invalidar sessão atual
                    self.invalidate_session(token)
                    
                    # Criar nova sessão
                    return self.create_session(user_data, payload.get('ip_address'))
            
            return token  # Não precisa renovar
            
        except Exception as e:
            self.logger.log_system_error(
                error_type='session_refresh_error',
                error_message=str(e)
            )
            return None
    
    def get_session_info(self, token: str) -> Optional[Dict[str, Any]]:
        """Retorna informações da sessão atual"""
        try:
            is_valid, payload = self.validate_session(token)
            if not is_valid:
                return None
            
            session_id = payload.get('session_id')
            session_data = self._active_sessions.get(session_id)
            
            if session_data:
                return {
                    'session_id': session_id,
                    'username': payload.get('username'),
                    'created_at': session_data.get('created_at'),
                    'last_activity': session_data.get('last_activity'),
                    'ip_address': session_data.get('ip_address'),
                    'expires_at': datetime.fromtimestamp(payload.get('exp'))
                }
            
            return None
            
        except Exception:
            return None


# Singleton global
_session_manager_instance = None

def get_session_manager() -> SessionManager:
    """Retorna instância singleton do session manager"""
    global _session_manager_instance
    if _session_manager_instance is None:
        _session_manager_instance = SessionManager()
    return _session_manager_instance


def streamlit_session_wrapper():
    """Wrapper para integração com Streamlit session state"""
    session_manager = get_session_manager()
    
    # Verificar se há token na sessão
    if 'auth_token' in st.session_state:
        token = st.session_state['auth_token']
        
        # Validar token
        is_valid, user_data = session_manager.validate_session(token)
        
        if is_valid:
            # Atualizar dados do usuário na sessão
            st.session_state['autenticado'] = True
            st.session_state['usuario'] = user_data.get('username')
            st.session_state['nome'] = user_data.get('nome')
            st.session_state['user_id'] = user_data.get('user_id')
            
            # Tentar renovar sessão se necessário
            new_token = session_manager.refresh_session(token)
            if new_token != token:
                st.session_state['auth_token'] = new_token
        else:
            # Sessão inválida - limpar estado
            _clear_streamlit_session()
    else:
        # Sem token - garantir que estado está limpo
        _clear_streamlit_session()


def _clear_streamlit_session():
    """Limpa dados de autenticação do Streamlit session state"""
    keys_to_clear = ['autenticado', 'usuario', 'nome', 'user_id', 'auth_token']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
