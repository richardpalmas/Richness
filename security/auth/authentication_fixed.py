"""
Sistema de Autenticação Segura - Backend V2
Implementação robusta com criptografia avançada e auditoria completa
"""

import hashlib
import hmac
import secrets
import bcrypt
from datetime import datetime, timedelta
from typing import Optional
import streamlit as st

# Imports Backend V2
from utils.repositories_v2 import UsuarioRepository
from utils.database_manager_v2 import DatabaseManager
from security.audit.security_logger import SecurityLogger
from security.validation.input_validator import InputValidator


class PasswordPolicy:
    """Política de senhas fortes baseada em melhores práticas"""
    
    MIN_LENGTH = 8
    MAX_LENGTH = 128
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGITS = True
    REQUIRE_SYMBOLS = True
    FORBIDDEN_SEQUENCES = ["123456", "password", "qwerty", "abc123"]
    
    @classmethod
    def validate_password(cls, password: str) -> tuple[bool, str]:
        """Valida se a senha atende aos critérios de segurança"""
        if len(password) < cls.MIN_LENGTH:
            return False, f"Senha deve ter pelo menos {cls.MIN_LENGTH} caracteres"
        
        if len(password) > cls.MAX_LENGTH:
            return False, f"Senha deve ter no máximo {cls.MAX_LENGTH} caracteres"
        
        if cls.REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
            return False, "Senha deve conter pelo menos uma letra maiúscula"
        
        if cls.REQUIRE_LOWERCASE and not any(c.islower() for c in password):
            return False, "Senha deve conter pelo menos uma letra minúscula"
        
        if cls.REQUIRE_DIGITS and not any(c.isdigit() for c in password):
            return False, "Senha deve conter pelo menos um dígito"
        
        if cls.REQUIRE_SYMBOLS and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            return False, "Senha deve conter pelo menos um símbolo especial"
        
        password_lower = password.lower()
        for forbidden in cls.FORBIDDEN_SEQUENCES:
            if forbidden in password_lower:
                return False, f"Senha não pode conter sequência comum: {forbidden}"
        
        return True, "Senha válida"


class SecureAuthentication:
    """
    Sistema de autenticação robusta com múltiplas camadas de segurança
    """
    
    def __init__(self):
        self.logger = SecurityLogger()
        self.validator = InputValidator()
        self.db_manager = DatabaseManager()
        self.user_repo = UsuarioRepository(self.db_manager)
        
        # Configurações de segurança
        self.MAX_LOGIN_ATTEMPTS = 5
        self.LOCKOUT_DURATION = 30  # minutos
        self.SESSION_TIMEOUT = 60  # minutos
        self.PASSWORD_SALT_ROUNDS = 12
    
    def hash_password(self, password: str) -> str:
        """Gera hash seguro da senha usando bcrypt"""
        try:
            salt = bcrypt.gensalt(rounds=self.PASSWORD_SALT_ROUNDS)
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
            return hashed.decode('utf-8')
        except Exception as e:
            self.logger.log_system_error(
                error_type="password_hash_error",
                error_message=f"Erro ao gerar hash de senha: {str(e)}"
            )
            raise
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verifica senha contra hash armazenado"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception as e:
            self.logger.log_system_error(
                error_type="password_verify_error",
                error_message=f"Erro ao verificar senha: {str(e)}"
            )
            return False
    
    def authenticate_user(self, username: str, password: str, ip_address: Optional[str] = None) -> tuple[bool, str, dict]:
        """
        Autentica usuário com validação robusta
        
        Returns:
            tuple: (sucesso, mensagem, dados_usuario)
        """
        
        try:
            # Validar inputs
            if not self.validator.validate_username(username):
                self.logger.log_authentication_attempt(
                    username=username,
                    success=False,
                    error="Username inválido",
                    ip_address=ip_address
                )
                return False, "Username inválido", {}
            
            # Buscar usuário
            user_data = self.user_repo.obter_usuario_por_username(username)
            if not user_data:
                self.logger.log_authentication_attempt(
                    username=username,
                    success=False,
                    error="Usuário não encontrado",
                    ip_address=ip_address
                )
                return False, "Credenciais inválidas", {}
            
            # Verificar senha
            password_hash = user_data.get('password_hash', '')
            if not self.verify_password(password, password_hash):
                self.logger.log_authentication_attempt(
                    username=username,
                    success=False,
                    error="Senha incorreta",
                    ip_address=ip_address
                )
                return False, "Credenciais inválidas", {}
            
            # Login bem-sucedido
            self.logger.log_authentication_attempt(
                username=username,
                success=True,
                ip_address=ip_address
            )
            
            # Retornar dados do usuário (sem informações sensíveis)
            safe_user_data = {
                'id': user_data['id'],
                'username': user_data['username'],
                'email': user_data.get('email', ''),
                'created_at': user_data.get('created_at', ''),
                'last_login': datetime.now().isoformat()
            }
            
            return True, "Login realizado com sucesso", safe_user_data
            
        except Exception as e:
            # Log erro de sistema
            self.logger.log_system_error(
                error_type="authentication_system_error",
                error_message=f"Erro no sistema de autenticação: {str(e)}"
            )
            return False, "Erro interno do sistema", {}
    
    def create_user(self, username: str, password: str, email: Optional[str] = None) -> tuple[bool, str]:
        """
        Cria novo usuário com validações de segurança
        """
        try:
            # Validar username
            if not self.validator.validate_username(username):
                return False, "Username inválido"
            
            # Validar senha
            password_valid, password_message = PasswordPolicy.validate_password(password)
            if not password_valid:
                return False, password_message
            
            # Verificar se usuário já existe
            existing_user = self.user_repo.obter_usuario_por_username(username)
            if existing_user:
                self.logger.log_user_registration(
                    username=username,
                    success=False,
                    error="Usuário já existe"
                )
                return False, "Username já está em uso"
              # Criar usuário usando o método correto do repository
            user_id = self.user_repo.criar_usuario_com_senha(username, password, email)
            
            if user_id:
                self.logger.log_user_registration(
                    username=username,
                    success=True
                )
                return True, "Usuário criado com sucesso"
            else:
                self.logger.log_user_registration(
                    username=username,
                    success=False,
                    error="Falha ao criar usuário no banco"
                )
                return False, "Erro ao criar usuário"
                
        except Exception as e:
            self.logger.log_system_error(
                error_type="user_creation_error", 
                error_message=f"Erro ao criar usuário: {str(e)}"
            )
            return False, "Erro interno do sistema"
    
    def validate_session(self, username: str) -> bool:
        """Valida se a sessão do usuário ainda é válida"""
        try:
            # Verificar se o usuário existe e está ativo
            user_data = self.user_repo.obter_usuario_por_username(username)
            if not user_data or not user_data.get('is_active', False):
                return False
            
            # Aqui poderia adicionar validações adicionais de sessão
            # como timeout, verificação de IP, etc.
            
            return True
            
        except Exception as e:
            self.logger.log_system_error(
                error_type="session_validation_error",
                error_message=f"Erro ao validar sessão: {str(e)}"
            )
            return False


# Instância global para uso em todo o sistema
secure_auth = SecureAuthentication()


# Funções de conveniência para uso direto
def authenticate_user(username: str, password: str, ip_address: Optional[str] = None) -> tuple[bool, str, dict]:
    """Função de conveniência para autenticação"""
    return secure_auth.authenticate_user(username, password, ip_address)


def create_user(username: str, password: str, email: Optional[str] = None) -> tuple[bool, str]:
    """Função de conveniência para criação de usuário"""
    return secure_auth.create_user(username, password, email)


def validate_session(username: str) -> bool:
    """Função de conveniência para validação de sessão"""
    return secure_auth.validate_session(username)
