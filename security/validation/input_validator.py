"""
Sistema de validação de entrada robusto
Previne ataques de injeção e valida todos os inputs de usuário
"""
import re
import bleach
from typing import Any, List, Dict, Optional, Union
from urllib.parse import urlparse
import html


class InputValidator:
    """Validador de entrada com sanitização e whitelist de caracteres permitidos"""
    
    # Padrões de validação
    USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{3,30}$')
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    NAME_PATTERN = re.compile(r'^[a-zA-ZÀ-ÿ\s]{2,100}$')
    PHONE_PATTERN = re.compile(r'^\+?[\d\s\-\(\)]{10,20}$')
    
    # Listas de caracteres permitidos
    ALPHANUMERIC_CHARS = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
    USERNAME_CHARS = ALPHANUMERIC_CHARS | set('_-')
    NAME_CHARS = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZÀ-ÿ ')
    DESCRIPTION_CHARS = ALPHANUMERIC_CHARS | set(' .,!?-_()[]{}:;')
    
    # Palavras proibidas (SQL injection, XSS, etc.)
    FORBIDDEN_KEYWORDS = {
        'select', 'insert', 'update', 'delete', 'drop', 'create', 'alter',
        'union', 'script', 'javascript', 'onload', 'onerror', 'onclick',
        'eval', 'expression', 'vbscript', 'iframe', 'object', 'embed',
        'applet', 'form', 'input', 'meta', 'link', 'style'
    }
    
    @classmethod
    def sanitize_string(cls, value: str, allowed_chars: set = None) -> str:
        """Sanitiza string removendo caracteres não permitidos"""
        if not isinstance(value, str):
            return ""
        
        if allowed_chars is None:
            allowed_chars = cls.DESCRIPTION_CHARS
        
        # Remover caracteres não permitidos
        sanitized = ''.join(char for char in value if char in allowed_chars)
        
        # Escapar HTML
        sanitized = html.escape(sanitized)
        
        # Verificar palavras proibidas
        sanitized_lower = sanitized.lower()
        for forbidden in cls.FORBIDDEN_KEYWORDS:
            if forbidden in sanitized_lower:
                sanitized = sanitized_lower.replace(forbidden, '')
        
        return sanitized.strip()
    
    @classmethod
    def validate_username(cls, username: str) -> bool:
        """Valida username"""
        if not isinstance(username, str):
            return False
        
        # Verificar padrão
        if not cls.USERNAME_PATTERN.match(username):
            return False
        
        # Verificar palavras proibidas
        username_lower = username.lower()
        for forbidden in cls.FORBIDDEN_KEYWORDS:
            if forbidden in username_lower:
                return False
        
        # Verificar se não é apenas números
        if username.isdigit():
            return False
        
        return True
    
    @classmethod
    def validate_email(cls, email: str) -> bool:
        """Valida email"""
        # Se o email estiver vazio, é válido (opcional)
        if not email:
            return True
            
        if not isinstance(email, str):
            return False
        
        # Verificar padrão básico
        if not cls.EMAIL_PATTERN.match(email):
            return False
        
        # Verificar comprimento
        if len(email) > 254:  # RFC 5321
            return False
        
        # Verificar domínio
        try:
            local, domain = email.split('@')
            if len(local) > 64 or len(domain) > 253:
                return False
        except ValueError:
            return False
        
        return True
    
    @classmethod
    def validate_name(cls, name: str) -> bool:
        """Valida nome"""
        if not isinstance(name, str):
            return False
        
        # Verificar padrão
        if not cls.NAME_PATTERN.match(name):
            return False
        
        # Verificar se não é apenas espaços
        if not name.strip():
            return False
        
        # Verificar palavras consecutivas
        words = name.strip().split()
        if len(words) > 10:  # Limite razoável de palavras
            return False
        
        return True
    
    @classmethod
    def validate_phone(cls, phone: str) -> bool:
        """Valida telefone"""
        if not isinstance(phone, str):
            return False
        
        return bool(cls.PHONE_PATTERN.match(phone))
    
    @classmethod
    def validate_numeric(cls, value: Any, min_val: float = None, max_val: float = None) -> bool:
        """Valida valor numérico"""
        try:
            num_val = float(value)
            
            if min_val is not None and num_val < min_val:
                return False
            
            if max_val is not None and num_val > max_val:
                return False
            
            return True
        except (ValueError, TypeError):
            return False
    
    @classmethod
    def validate_date_string(cls, date_str: str) -> bool:
        """Valida string de data ISO"""
        if not isinstance(date_str, str):
            return False
        
        # Padrão ISO básico
        iso_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
        if not iso_pattern.match(date_str):
            return False
        
        try:
            from datetime import datetime
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    @classmethod
    def validate_file_path(cls, file_path: str) -> bool:
        """Valida caminho de arquivo (path traversal protection)"""
        if not isinstance(file_path, str):
            return False
        
        # Verificar caracteres perigosos
        dangerous_chars = ['..', '\\', '|', ';', '&', '$', '>', '<', '`']
        for char in dangerous_chars:
            if char in file_path:
                return False
        
        # Verificar extensões perigosas
        dangerous_extensions = ['.exe', '.bat', '.cmd', '.com', '.scr', '.vbs', '.js']
        for ext in dangerous_extensions:
            if file_path.lower().endswith(ext):
                return False
        
        return True
    
    @classmethod
    def validate_url(cls, url: str) -> bool:
        """Valida URL"""
        if not isinstance(url, str):
            return False
        
        try:
            parsed = urlparse(url)
            
            # Verificar esquema permitido
            allowed_schemes = ['http', 'https']
            if parsed.scheme not in allowed_schemes:
                return False
            
            # Verificar se tem domínio
            if not parsed.netloc:
                return False
            
            return True
        except Exception:
            return False
    
    @classmethod
    def sanitize_html(cls, html_content: str) -> str:
        """Sanitiza conteúdo HTML removendo tags perigosas"""
        if not isinstance(html_content, str):
            return ""
        
        # Tags permitidas (whitelist)
        allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li']
        
        # Atributos permitidos
        allowed_attributes = {}
        
        # Sanitizar usando bleach
        sanitized = bleach.clean(
            html_content,
            tags=allowed_tags,
            attributes=allowed_attributes,
            strip=True
        )
        
        return sanitized
    
    @classmethod
    def validate_json_keys(cls, data: Dict[str, Any], allowed_keys: List[str]) -> bool:
        """Valida que JSON contém apenas chaves permitidas"""
        if not isinstance(data, dict):
            return False
        
        for key in data.keys():
            if key not in allowed_keys:
                return False
        
        return True
    
    @classmethod
    def validate_transaction_description(cls, description: str) -> bool:
        """Valida descrição de transação"""
        if not isinstance(description, str):
            return False
        
        # Limites de tamanho
        if len(description) > 500:
            return False
        
        # Verificar caracteres permitidos
        sanitized = cls.sanitize_string(description, cls.DESCRIPTION_CHARS)
        return len(sanitized) > 0
    
    @classmethod
    def validate_category_name(cls, category: str) -> bool:
        """Valida nome de categoria"""
        if not isinstance(category, str):
            return False
        
        # Limites
        if not (2 <= len(category) <= 50):
            return False
        
        # Apenas letras, números e espaços
        return bool(re.match(r'^[a-zA-ZÀ-ÿ0-9\s]+$', category))
    
    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Sanitiza nome de arquivo para uso seguro"""
        if not isinstance(filename, str):
            return ""
        
        # Remover caracteres perigosos para nomes de arquivo
        sanitized = re.sub(r'[<>:"/\\|?*]', '', filename)
        
        # Remover caracteres de controle
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', sanitized)
        
        # Limitar tamanho
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
        
        # Remover espaços no início e fim
        sanitized = sanitized.strip()
        
        # Se ficou vazio, usar nome padrão
        if not sanitized:
            sanitized = "file"
            
        return sanitized
