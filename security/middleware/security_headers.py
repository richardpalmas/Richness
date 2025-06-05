"""
Security Headers Middleware
Implementa cabeçalhos de segurança para proteger contra ataques web
"""
from typing import Dict, List, Optional
import streamlit as st
from datetime import datetime, timedelta


class SecurityHeaders:
    """Gerenciador de cabeçalhos de segurança HTTP"""
    
    def __init__(self):
        self.default_headers = self._get_default_security_headers()
    
    def _get_default_security_headers(self) -> Dict[str, str]:
        """Define cabeçalhos de segurança padrão"""
        return {
            # Content Security Policy - Previne XSS
            'Content-Security-Policy': (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
                "https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
                "style-src 'self' 'unsafe-inline' "
                "https://fonts.googleapis.com https://cdn.jsdelivr.net; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: https:; "
                "connect-src 'self' https:; "
                "frame-ancestors 'none';"
            ),
            
            # HTTP Strict Transport Security - Força HTTPS
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            
            # Previne clickjacking
            'X-Frame-Options': 'DENY',
            
            # Previne MIME type sniffing
            'X-Content-Type-Options': 'nosniff',
            
            # XSS Protection (legacy, mas ainda útil)
            'X-XSS-Protection': '1; mode=block',
            
            # Referrer Policy - Controla informações de referência
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            
            # Permissions Policy - Controla APIs do navegador
            'Permissions-Policy': (
                'camera=(), microphone=(), geolocation=(), '
                'payment=(), usb=(), magnetometer=(), gyroscope=()'
            ),
            
            # Cache Control para páginas sensíveis
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
    
    def get_financial_app_headers(self) -> Dict[str, str]:
        """
        Cabeçalhos específicos para aplicações financeiras
        Mais restritivos que os padrão
        """
        headers = self.default_headers.copy()
        
        # CSP mais restritivo para apps financeiros
        headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "font-src 'self'; "
            "object-src 'none'; "
            "media-src 'none'; "
            "frame-src 'none'; "
            "frame-ancestors 'none'; "
            "base-uri 'self';"
        )
        
        # Headers adicionais para compliance bancário
        headers.update({
            'X-Permitted-Cross-Domain-Policies': 'none',
            'Cross-Origin-Embedder-Policy': 'require-corp',
            'Cross-Origin-Opener-Policy': 'same-origin',
            'Cross-Origin-Resource-Policy': 'same-origin'
        })
        
        return headers
    
    def get_public_page_headers(self) -> Dict[str, str]:
        """Cabeçalhos para páginas públicas (menos restritivos)"""
        headers = self.default_headers.copy()
        
        # CSP mais permissivo para páginas públicas
        headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' "
            "https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' "
            "https://fonts.googleapis.com https://cdn.jsdelivr.net; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https:;"
        )
        
        # Cache permitido para recursos estáticos
        headers['Cache-Control'] = 'public, max-age=3600'
        del headers['Pragma']
        del headers['Expires']
        
        return headers
    
    def apply_headers_to_streamlit(self, headers: Dict[str, str] = None):
        """
        Aplica cabeçalhos de segurança ao Streamlit
        Nota: Limitações do Streamlit podem impedir alguns cabeçalhos
        """
        if headers is None:
            headers = self.default_headers
        
        # Aplicar meta tags que o Streamlit suporta
        meta_tags = self._convert_headers_to_meta_tags(headers)
        
        for meta_tag in meta_tags:
            st.markdown(meta_tag, unsafe_allow_html=True)
    
    def _convert_headers_to_meta_tags(self, headers: Dict[str, str]) -> List[str]:
        """Converte cabeçalhos HTTP para meta tags HTML"""
        meta_tags = []
        
        # Mapeamento de cabeçalhos para meta tags
        header_to_meta = {
            'Content-Security-Policy': 'http-equiv="Content-Security-Policy"',
            'X-Frame-Options': 'http-equiv="X-Frame-Options"',
            'X-Content-Type-Options': 'http-equiv="X-Content-Type-Options"',
            'X-XSS-Protection': 'http-equiv="X-XSS-Protection"',
            'Referrer-Policy': 'name="referrer"'
        }
        
        for header, value in headers.items():
            if header in header_to_meta:
                meta_attr = header_to_meta[header]
                meta_tag = f'<meta {meta_attr} content="{value}">'
                meta_tags.append(meta_tag)
        
        return meta_tags
    
    def create_csp_nonce(self) -> str:
        """Cria nonce para CSP inline scripts"""
        import secrets
        return secrets.token_urlsafe(16)
    
    def validate_csp_compliance(self, content: str) -> List[str]:
        """
        Valida se conteúdo está em conformidade com CSP
        Retorna lista de violações encontradas
        """
        violations = []
        
        # Verificar scripts inline sem nonce
        if '<script>' in content and 'nonce=' not in content:
            violations.append("Script inline sem nonce detectado")
        
        # Verificar event handlers inline
        dangerous_handlers = ['onclick', 'onload', 'onerror', 'onmouseover']
        for handler in dangerous_handlers:
            if f'{handler}=' in content.lower():
                violations.append(f"Event handler inline detectado: {handler}")
        
        # Verificar eval() ou Function()
        if 'eval(' in content or 'Function(' in content:
            violations.append("Uso de eval() ou Function() detectado")
        
        return violations


class SecurityMiddleware:
    """Middleware principal de segurança"""
    
    def __init__(self):
        self.headers = SecurityHeaders()
        self.session_timeout_minutes = 120  # 2 horas
        self.inactivity_timeout_minutes = 30  # 30 minutos
    
    def apply_page_security(self, page_type: str = 'default'):
        """
        Aplica segurança baseada no tipo de página
        
        Args:
            page_type: 'financial', 'public', 'admin', 'default'
        """
        # Aplicar cabeçalhos apropriados
        if page_type == 'financial':
            headers = self.headers.get_financial_app_headers()
        elif page_type == 'public':
            headers = self.headers.get_public_page_headers()
        else:
            headers = self.headers.default_headers
        
        self.headers.apply_headers_to_streamlit(headers)
        
        # Verificar timeout de sessão
        self._check_session_timeout()
        
        # Aplicar outras proteções
        self._apply_additional_protections()
    
    def _check_session_timeout(self):
        """Verifica e força logout por timeout"""
        if not st.session_state.get('autenticado', False):
            return
        
        now = datetime.now()
        
        # Verificar timeout absoluto
        login_time = st.session_state.get('login_time')
        if login_time:
            if now - login_time > timedelta(minutes=self.session_timeout_minutes):
                self._force_logout("Sessão expirada por tempo limite")
                return
        
        # Verificar inatividade
        last_activity = st.session_state.get('last_activity')
        if last_activity:
            if now - last_activity > timedelta(minutes=self.inactivity_timeout_minutes):
                self._force_logout("Sessão expirada por inatividade")
                return
        
        # Atualizar última atividade
        st.session_state.last_activity = now
    
    def _force_logout(self, reason: str):
        """Força logout com limpeza de sessão"""
        from security.audit.security_logger import get_security_logger
        
        logger = get_security_logger()
        logger.log_session_event(
            username=st.session_state.get('usuario', 'unknown'),
            event_type='forced_logout',
            session_duration=None
        )
        
        # Limpar session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        st.error(f"🔒 {reason}")
        st.info("Redirecionando para login...")
        st.rerun()
    
    def _apply_additional_protections(self):
        """Aplica proteções adicionais"""
        # Prevenir cache de páginas sensíveis
        if st.session_state.get('autenticado', False):
            st.markdown(
                """
                <script>
                window.addEventListener('beforeunload', function() {
                    // Limpar dados sensíveis antes de sair
                    if (window.sessionStorage) {
                        sessionStorage.clear();
                    }
                });
                </script>
                """,
                unsafe_allow_html=True
            )


# Singleton global
_security_middleware_instance = None

def get_security_middleware() -> SecurityMiddleware:
    """Retorna instância singleton do middleware de segurança"""
    global _security_middleware_instance
    if _security_middleware_instance is None:
        _security_middleware_instance = SecurityMiddleware()
    return _security_middleware_instance


def apply_page_security(page_type: str = 'default'):
    """
    Função utilitária para aplicar segurança a uma página
    
    Usage:
        apply_page_security('financial')  # Para páginas financeiras
        apply_page_security('public')     # Para páginas públicas
    """
    middleware = get_security_middleware()
    middleware.apply_page_security(page_type)
