"""
CSRF Protection Middleware
Protege formulários contra ataques Cross-Site Request Forgery
"""
import secrets
import hmac
import hashlib
from typing import Optional
import streamlit as st
from datetime import datetime, timedelta


class CSRFProtection:
    """Proteção CSRF para formulários Streamlit"""
    
    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or self._generate_secret_key()
        self.token_lifetime_minutes = 60  # Token válido por 1 hora
    
    def _generate_secret_key(self) -> str:
        """Gera chave secreta para CSRF tokens"""
        return secrets.token_urlsafe(32)
    
    def generate_csrf_token(self, session_id: str = None) -> str:
        """
        Gera token CSRF único para a sessão
        
        Args:
            session_id: ID da sessão (pode usar session_state.session_id)
            
        Returns:
            Token CSRF codificado
        """
        if not session_id:
            session_id = st.session_state.get('session_id', 'default')
        
        # Timestamp atual
        timestamp = str(int(datetime.now().timestamp()))
        
        # Dados para o token
        token_data = f"{session_id}:{timestamp}"
        
        # Gerar HMAC
        signature = hmac.new(
            self.secret_key.encode(),
            token_data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Token final
        csrf_token = f"{token_data}:{signature}"
        
        return csrf_token
    
    def validate_csrf_token(self, token: str, session_id: str = None) -> bool:
        """
        Valida token CSRF
        
        Args:
            token: Token CSRF recebido do formulário
            session_id: ID da sessão atual
            
        Returns:
            True se válido, False caso contrário
        """
        if not token:
            return False
        
        if not session_id:
            session_id = st.session_state.get('session_id', 'default')
        
        try:
            # Separar componentes do token
            parts = token.split(':')
            if len(parts) != 3:
                return False
            
            received_session_id, timestamp_str, received_signature = parts
            
            # Verificar session ID
            if received_session_id != session_id:
                return False
            
            # Verificar se token não expirou
            token_timestamp = datetime.fromtimestamp(int(timestamp_str))
            if datetime.now() - token_timestamp > timedelta(minutes=self.token_lifetime_minutes):
                return False
            
            # Verificar assinatura
            expected_data = f"{received_session_id}:{timestamp_str}"
            expected_signature = hmac.new(
                self.secret_key.encode(),
                expected_data.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(expected_signature, received_signature)
            
        except (ValueError, IndexError):
            return False
    
    def get_csrf_token_for_form(self) -> str:
        """
        Obtém token CSRF para usar em formulários
        Armazena no session_state para validação posterior
        """
        # Gerar ou recuperar session ID
        if 'session_id' not in st.session_state:
            st.session_state.session_id = secrets.token_urlsafe(16)
        
        # Gerar token
        token = self.generate_csrf_token(st.session_state.session_id)
        
        # Armazenar token atual no session_state
        st.session_state.csrf_token = token
        
        return token
    
    def validate_form_csrf_token(self, submitted_token: str) -> bool:
        """
        Valida token CSRF de formulário submetido
        
        Args:
            submitted_token: Token enviado pelo formulário
            
        Returns:
            True se válido, False caso contrário
        """
        return self.validate_csrf_token(
            submitted_token, 
            st.session_state.get('session_id')
        )
    
    def create_hidden_csrf_field(self) -> str:
        """
        Cria campo hidden HTML com token CSRF
        Para uso em formulários HTML personalizados
        """
        token = self.get_csrf_token_for_form()
        return f'<input type="hidden" name="csrf_token" value="{token}">'
    
    def middleware_check(self, form_data: dict) -> tuple[bool, Optional[str]]:
        """
        Middleware para verificar CSRF em formulários
        
        Args:
            form_data: Dados do formulário (deve conter 'csrf_token')
            
        Returns:
            (válido, mensagem_erro)
        """
        csrf_token = form_data.get('csrf_token')
        
        if not csrf_token:
            return False, "Token CSRF ausente"
        
        if not self.validate_form_csrf_token(csrf_token):
            return False, "Token CSRF inválido ou expirado"
        
        return True, None


# Singleton global
_csrf_protection_instance = None

def get_csrf_protection() -> CSRFProtection:
    """Retorna instância singleton da proteção CSRF"""
    global _csrf_protection_instance
    if _csrf_protection_instance is None:
        _csrf_protection_instance = CSRFProtection()
    return _csrf_protection_instance


def csrf_protected_form(form_key: str):
    """
    Decorator/context manager para formulários protegidos por CSRF
    
    Usage:
        with csrf_protected_form("my_form"):
            # conteúdo do formulário
            pass
    """
    class CSRFFormContext:
        def __init__(self, form_key: str):
            self.form_key = form_key
            self.csrf = get_csrf_protection()
            
        def __enter__(self):
            # Gerar token CSRF para o formulário
            self.token = self.csrf.get_csrf_token_for_form()
            return self
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass
            
        def validate_submission(self, submitted_token: str) -> bool:
            """Valida token do formulário submetido"""
            return self.csrf.validate_form_csrf_token(submitted_token)
    
    return CSRFFormContext(form_key)


# Utilitário para facilitar uso em Streamlit
def add_csrf_to_form() -> str:
    """
    Adiciona proteção CSRF a um formulário Streamlit
    Retorna o token que deve ser incluído como campo hidden
    """
    csrf = get_csrf_protection()
    return csrf.get_csrf_token_for_form()


def validate_csrf_token(submitted_token: str) -> bool:
    """
    Valida token CSRF submetido
    """
    csrf = get_csrf_protection()
    return csrf.validate_form_csrf_token(submitted_token)
