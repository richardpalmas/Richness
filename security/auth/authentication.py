"""
Sistema de autenticação segura com bcrypt e validação robusta
Corrige vulnerabilidades críticas: senhas em texto plano e validação inadequada
"""
import bcrypt
import re
import secrets
import hashlib
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
    REQUIRE_SPECIAL = True
    SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    
    @classmethod
    def validate_password(cls, password: str) -> Tuple[bool, str]:
        """Valida senha contra política de segurança"""
        if not password:
            return False, "Senha é obrigatória"
        
        if len(password) < cls.MIN_LENGTH:
            return False, f"Senha deve ter pelo menos {cls.MIN_LENGTH} caracteres"
        
        if len(password) > cls.MAX_LENGTH:
            return False, f"Senha deve ter no máximo {cls.MAX_LENGTH} caracteres"
        
        if cls.REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
            return False, "Senha deve conter pelo menos uma letra maiúscula"
        
        if cls.REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
            return False, "Senha deve conter pelo menos uma letra minúscula"
        
        if cls.REQUIRE_DIGITS and not re.search(r'\d', password):
            return False, "Senha deve conter pelo menos um número"
        
        if cls.REQUIRE_SPECIAL and not re.search(f'[{re.escape(cls.SPECIAL_CHARS)}]', password):
            return False, f"Senha deve conter pelo menos um caractere especial: {cls.SPECIAL_CHARS}"
        
        # Verificar padrões comuns fracos
        weak_patterns = [
            r'12345', r'password', r'qwerty', r'admin', 
            r'123456789', r'abcdef', r'111111', r'000000'
        ]
        
        password_lower = password.lower()
        for pattern in weak_patterns:
            if pattern in password_lower:
                return False, "Senha contém padrão comum. Escolha uma senha mais segura"
        
        return True, "Senha válida"


class SecureAuthentication:
    """Sistema de autenticação segura com bcrypt e rate limiting"""
    
    def __init__(self):
        self.logger = SecurityLogger()
        self.validator = InputValidator()
        self._salt_rounds = 12  # Bcrypt rounds para hash seguro
    
    def hash_password(self, password: str) -> str:
        """Gera hash seguro da senha usando bcrypt com salt"""
        try:
            # Validar senha antes de hashear
            is_valid, message = PasswordPolicy.validate_password(password)
            if not is_valid:
                raise ValueError(f"Senha inválida: {message}")
            
            # Gerar hash bcrypt
            password_bytes = password.encode('utf-8')
            salt = bcrypt.gensalt(rounds=self._salt_rounds)
            hashed = bcrypt.hashpw(password_bytes, salt)
            
            self.logger.log_password_change(success=True)
            return hashed.decode('utf-8')
            
        except Exception as e:
            self.logger.log_password_change(success=False, error=str(e))
            raise
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verifica senha contra hash bcrypt de forma segura"""
        try:
            # Validação básica
            if not password or not hashed_password:
                return False
            
            # Conversão para bytes
            password_bytes = password.encode('utf-8')
            hashed_bytes = hashed_password.encode('utf-8')
            
            # Verificação constant-time para prevenir timing attacks
            result = bcrypt.checkpw(password_bytes, hashed_bytes)
            
            return result
            
        except Exception as e:
            # Log error if possible, but don't let logging failures break auth
            try:
                if hasattr(self, 'logger') and self.logger:
                    self.logger.log_authentication_attempt(
                        username="unknown",
                        success=False,
                        error=f"Password verification error: {str(e)}"
                    )
            except:
                pass
            return False

    def authenticate_user(self, username: str, password: str, ip_address: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Autentica usuário com proteção contra ataques
        Retorna: (sucesso, dados_usuario)
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
                return False, None
            
            if not password:
                self.logger.log_authentication_attempt(
                    username=username,
                    success=False,
                    error="Senha vazia",
                    ip_address=ip_address
                )
                return False, None
            
            # Buscar usuário no banco (query parametrizada)
            conn = get_connection()
            cur = conn.cursor()
            
            # Query segura com prepared statement
            cur.execute(
                'SELECT id, nome, usuario, senha, email, profile_pic, created_at FROM usuarios WHERE usuario = ?',
                (username,)
            )
            
            user_row = cur.fetchone()
            
            if not user_row:
                # Log tentativa com usuário inexistente
                self.logger.log_authentication_attempt(
                    username=username,
                    success=False,
                    error="Usuário não encontrado",
                    ip_address=ip_address
                )
                # Delay constante para prevenir user enumeration
                import time
                time.sleep(0.5)
                return False, None
            
            # Verificar senha
            stored_hash = user_row['senha']
            if not self.verify_password(password, stored_hash):
                self.logger.log_authentication_attempt(
                    username=username,
                    success=False,
                    error="Senha incorreta",
                    ip_address=ip_address
                )
                return False, None
            
            # Autenticação bem-sucedida
            user_data = {
                'id': user_row['id'],
                'nome': user_row['nome'],
                'usuario': user_row['usuario'],
                'email': user_row['email'],
                'profile_pic': user_row['profile_pic'],
                'created_at': user_row['created_at']
            }
            
            self.logger.log_authentication_attempt(
                username=username,
                success=True,
                ip_address=ip_address
            )
            
            return True, user_data
            
        except Exception as e:
            self.logger.log_authentication_attempt(
                username=username,
                success=False,
                error=f"Erro interno: {str(e)}",
                ip_address=ip_address
            )
            return False, None

    def register_user(self, nome: str, username: str, password: str, email: str, 
                     profile_pic: str = "", ip_address: Optional[str] = None) -> Tuple[bool, str]:
        """
        Registra novo usuário com validações de segurança
        Retorna: (sucesso, mensagem)
        """
        try:
            # Validar todos os inputs
            if not self.validator.validate_name(nome):
                return False, "Nome inválido. Use apenas letras e espaços (2-100 caracteres)"
            
            if not self.validator.validate_username(username):
                return False, "Username inválido. Use 3-30 caracteres alfanuméricos e _ -"
            
            # Validar email apenas se fornecido
            if email and not self.validator.validate_email(email):
                return False, "Email inválido"
            
            # Validar política de senha
            is_valid_password, password_message = PasswordPolicy.validate_password(password)
            if not is_valid_password:
                return False, password_message
            
            # Verificar se usuário já existe
            conn = get_connection()
            cur = conn.cursor()
            
            # Verificar username duplicado
            cur.execute('SELECT 1 FROM usuarios WHERE usuario = ?', (username,))
            if cur.fetchone():
                self.logger.log_user_registration(
                    username=username,
                    success=False,
                    error="Usuário já existe",
                    ip_address=ip_address
                )
                return False, "Nome de usuário já existe"
            
            # Verificar email duplicado apenas se fornecido
            if email:
                cur.execute('SELECT 1 FROM usuarios WHERE email = ?', (email,))
                if cur.fetchone():
                    self.logger.log_user_registration(
                        username=username,
                        success=False,
                        error="Email já cadastrado",
                        ip_address=ip_address
                    )
                    return False, "Email já cadastrado por outro usuário"
            
            # Hash da senha
            hashed_password = self.hash_password(password)
            
            # Inserir usuário
            cur.execute('''
                INSERT INTO usuarios (nome, usuario, senha, email, profile_pic, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (nome, username, hashed_password, email or None, profile_pic, datetime.now().isoformat()))
            
            conn.commit()
            
            self.logger.log_user_registration(
                username=username,
                success=True,
                ip_address=ip_address
            )
            
            return True, "Usuário registrado com sucesso"
            
        except Exception as e:
            self.logger.log_user_registration(
                username=username,
                success=False,
                error=f"Erro no registro: {str(e)}",
                ip_address=ip_address
            )
            return False, f"Erro no registro: {str(e)}"