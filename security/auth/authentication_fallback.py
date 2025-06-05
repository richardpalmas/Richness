"""
Fallback authentication system for environments with bcrypt issues
Uses secure SHA-256 with multiple rounds as temporary fallback
"""
import hashlib
import secrets
import re
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import streamlit as st

from database import get_connection
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
    
    FORBIDDEN_PATTERNS = [
        r'123456', r'password', r'admin', r'user', r'guest',
        r'qwerty', r'abc123', r'111111', r'000000'
    ]


class SecureAuthentication:
    """
    Sistema de autenticação seguro com fallback para ambientes com problemas de bcrypt
    """
    
    def __init__(self):
        self.logger = SecurityLogger()
        self.validator = InputValidator()
        self.policy = PasswordPolicy()
        
    def _secure_hash_password(self, password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """Hash de senha seguro com múltiplas iterações SHA-256"""
        if salt is None:
            salt = secrets.token_hex(32)
          # Múltiplas iterações para aumentar segurança
        hashed = password.encode()
        for _ in range(100000):  # 100,000 iterações
            hashed = hashlib.sha256(hashed + salt.encode()).digest()
        
        return hashed.hex(), salt
    
    def _verify_password_hash(self, password: str, hashed: str, salt: str) -> bool:
        """Verifica hash de senha"""
        try:
            computed_hash, _ = self._secure_hash_password(password, salt)
            return secrets.compare_digest(hashed, computed_hash)
        except Exception as e:
            self.logger.log_system_error(                error_type="password_verification_error",
                error_message=str(e),
                username="unknown"
            )
            return False
    
    def hash_password(self, password: str) -> str:
        """
        Gera hash seguro da senha
        """
        try:
            hashed, salt = self._secure_hash_password(password)
            # Formato: salt$hash (compatível com verificação)
            return f"{salt}${hashed}"
        except Exception as e:
            self.logger.log_system_error(
                error_type="password_hashing_error",
                error_message=str(e),
                username="unknown"
            )
            raise
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """
        Verifica se a senha corresponde ao hash
        """
        try:
            if '$' in hashed_password:
                # Novo formato com salt
                salt, hashed = hashed_password.split('$', 1)
                return self._verify_password_hash(password, hashed, salt)
            else:
                # Compatibilidade com formato antigo
                return hashlib.sha256(password.encode()).hexdigest() == hashed_password
        except Exception as e:
            self.logger.log_system_error(
                error_type="password_verification_error",
                error_message=str(e),
                username="unknown"
            )
            return False
    
    def validate_password_strength(self, password: str) -> Tuple[bool, str]:
        """
        Valida força da senha baseada na política
        """
        if len(password) < self.policy.MIN_LENGTH:
            return False, f"A senha deve ter pelo menos {self.policy.MIN_LENGTH} caracteres"
        
        if len(password) > self.policy.MAX_LENGTH:
            return False, f"A senha deve ter no máximo {self.policy.MAX_LENGTH} caracteres"
        
        if self.policy.REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
            return False, "A senha deve conter pelo menos uma letra maiúscula"
        
        if self.policy.REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
            return False, "A senha deve conter pelo menos uma letra minúscula"
        
        if self.policy.REQUIRE_DIGITS and not re.search(r'\d', password):
            return False, "A senha deve conter pelo menos um número"
        
        if self.policy.REQUIRE_SYMBOLS and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "A senha deve conter pelo menos um símbolo especial"
        
        # Verificar padrões proibidos
        for pattern in self.policy.FORBIDDEN_PATTERNS:
            if re.search(pattern, password.lower()):
                return False, "A senha não pode conter padrões comuns ou previsíveis"
        
        return True, "Senha válida"
    
    def register_user(self, username: str, email: str, password: str, full_name: Optional[str] = None) -> Tuple[bool, str]:
        """
        Registra novo usuário com validação completa
        """
        try:
            # Validar entrada
            if not self.validator.validate_username(username):
                return False, "Nome de usuário inválido"
            
            if not self.validator.validate_email(email):
                return False, "Email inválido"
            
            # Validar força da senha
            is_valid, message = self.validate_password_strength(password)
            if not is_valid:
                return False, message
            
            # Verificar se usuário já existe
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
            if cursor.fetchone():
                self.logger.log_user_registration(
                    username=username,
                    success=False,
                    error="duplicate_user"
                )
                return False, "Usuário ou email já cadastrado"
            
            # Hash da senha
            password_hash = self.hash_password(password)
            
            # Inserir usuário
            cursor.execute("""
                INSERT INTO users (username, email, password, full_name, created_at, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (username, email, password_hash, full_name or username, datetime.now()))
            
            conn.commit()
            conn.close()
            
            self.logger.log_user_registration(
                username=username,
                success=True
            )
            
            return True, "Usuário cadastrado com sucesso"
            
        except Exception as e:
            self.logger.log_user_registration(
                username=username,
                success=False,
                error=str(e)
            )
            return False, "Erro interno durante o cadastro"
    
    def authenticate_user(self, username: str, password: str, client_ip: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Autentica usuário com logs de segurança
        """
        try:
            # Validar entrada
            if not username or not password:
                return False, None
            
            # Buscar usuário
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, username, email, password, full_name, is_active, 
                       failed_login_attempts, last_failed_login
                FROM users 
                WHERE username = ? OR email = ?            """, (username, username))
            user = cursor.fetchone()
            conn.close()
            
            if not user:
                self.logger.log_authentication_attempt(
                    username=username,
                    success=False,
                    ip_address=client_ip,
                    error="invalid_user"
                )
                return False, None
            
            user_data = {
                'id': user[0],
                'username': user[1],
                'email': user[2],
                'password_hash': user[3],
                'full_name': user[4],
                'is_active': user[5],
                'failed_attempts': user[6] or 0,
                'last_failed_login': user[7]            }
            
            # Verificar se conta está ativa
            if not user_data['is_active']:
                self.logger.log_authentication_attempt(
                    username=username,
                    success=False,
                    ip_address=client_ip,
                    error="inactive_account"
                )
                return False, None
            
            # Verificar senha
            if self.verify_password(password, user_data['password_hash']):
                # Login bem-sucedido - resetar tentativas falhadas
                self._reset_failed_attempts(user_data['id'])
                
                self.logger.log_authentication_attempt(
                    username=username,
                    success=True,                    ip_address=client_ip
                )
                
                return True, {
                    'id': user_data['id'],
                    'username': user_data['username'],
                    'email': user_data['email'],
                    'full_name': user_data['full_name']
                }
            else:
                # Login falhado - incrementar tentativas
                self._increment_failed_attempts(user_data['id'])
                
                self.logger.log_authentication_attempt(
                    username=username,
                    success=False,
                    ip_address=client_ip,
                    error="wrong_password"
                )
                return False, None
                
        except Exception as e:
            self.logger.log_system_error(
                error_type="authentication_error",
                error_message=str(e),
                username=username
            )
            return False, None
    
    def _reset_failed_attempts(self, user_id: int):
        """Reset failed login attempts"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET failed_login_attempts = 0, last_failed_login = NULL 
                WHERE id = ?
            """, (user_id,))
            conn.commit()
            conn.close()
        except Exception:
            pass
    
    def _increment_failed_attempts(self, user_id: int):
        """Increment failed login attempts"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET failed_login_attempts = COALESCE(failed_login_attempts, 0) + 1,
                    last_failed_login = ?
                WHERE id = ?
            """, (datetime.now(), user_id))
            conn.commit()
            conn.close()
        except Exception:
            pass


# Função de conveniência para obter instância do autenticador
def get_auth_manager() -> SecureAuthentication:
    """Retorna instância do gerenciador de autenticação"""
    return SecureAuthentication()
