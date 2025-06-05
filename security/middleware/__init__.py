"""
Security Middleware Package
Módulos de middleware para proteção web avançada
"""

from .csrf_protection import (
    CSRFProtection,
    get_csrf_protection,
    csrf_protected_form,
    add_csrf_to_form,
    validate_csrf_token
)

from .security_headers import (
    SecurityHeaders,
    SecurityMiddleware,
    get_security_middleware,
    apply_page_security
)

__all__ = [
    'CSRFProtection',
    'get_csrf_protection', 
    'csrf_protected_form',
    'add_csrf_to_form',
    'validate_csrf_token',
    'SecurityHeaders',
    'SecurityMiddleware',
    'get_security_middleware',
    'apply_page_security'
]
