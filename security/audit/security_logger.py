"""
Sistema de auditoria e logging de segurança
Registra todos os eventos críticos para monitoramento e compliance
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import os
from pathlib import Path


class SecurityLogger:
    """Logger especializado para eventos de segurança"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Configurar loggers
        self._setup_loggers()
    
    def _setup_loggers(self):
        """Configura diferentes loggers para tipos de eventos"""
        
        # Logger de autenticação
        self.auth_logger = logging.getLogger('security.auth')
        self.auth_logger.setLevel(logging.INFO)
        
        auth_handler = logging.FileHandler(
            self.log_dir / 'auth_security.log',
            encoding='utf-8'
        )
        auth_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        )
        self.auth_logger.addHandler(auth_handler)
        
        # Logger de acesso a dados
        self.data_logger = logging.getLogger('security.data')
        self.data_logger.setLevel(logging.INFO)
        
        data_handler = logging.FileHandler(
            self.log_dir / 'data_access.log',
            encoding='utf-8'
        )
        data_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        )
        self.data_logger.addHandler(data_handler)
        
        # Logger de sistema
        self.system_logger = logging.getLogger('security.system')
        self.system_logger.setLevel(logging.WARNING)
        
        system_handler = logging.FileHandler(
            self.log_dir / 'system_security.log',
            encoding='utf-8'
        )
        system_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        )
        self.system_logger.addHandler(system_handler)
    
    def _create_base_event(self, event_type: str, **kwargs) -> Dict[str, Any]:
        """Cria evento base com metadados padrão"""
        return {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'session_id': self._get_session_id(),
            **kwargs
        }
    
    def _get_session_id(self) -> str:
        """Obtém ID da sessão atual"""
        try:
            import streamlit as st
            if hasattr(st, 'session_state') and hasattr(st.session_state, 'session_id'):
                return st.session_state.session_id
            return 'unknown'
        except Exception:
            return 'unknown'
    
    def log_authentication_attempt(self, username: str, success: bool, 
                                 ip_address: Optional[str] = None, error: Optional[str] = None):
        """Registra tentativa de autenticação"""
        event = self._create_base_event(
            'authentication_attempt',
            username=username,
            success=success,
            ip_address=ip_address or 'unknown',
            error=error
        )
        
        level = logging.INFO if success else logging.WARNING
        self.auth_logger.log(level, json.dumps(event, ensure_ascii=False))
        
        # Log crítico para falhas múltiplas
        if not success:
            self._check_multiple_failures(username, ip_address)
    
    def log_user_registration(self, username: str, success: bool, 
                            ip_address: Optional[str] = None, error: Optional[str] = None):
        """Registra tentativa de registro de usuário"""
        event = self._create_base_event(
            'user_registration',
            username=username,
            success=success,
            ip_address=ip_address or 'unknown',
            error=error
        )
        
        level = logging.INFO if success else logging.WARNING
        self.auth_logger.log(level, json.dumps(event, ensure_ascii=False))
    
    def log_password_change(self, username: Optional[str] = None, success: bool = True, error: Optional[str] = None):
        """Registra alteração de senha"""
        event = self._create_base_event(
            'password_change',
            username=username or 'unknown',
            success=success,
            error=error
        )
        
        level = logging.INFO if success else logging.ERROR
        self.auth_logger.log(level, json.dumps(event, ensure_ascii=False))
    
    def log_data_access(self, username: str, operation: str, resource: str, 
                       success: bool = True, error: Optional[str] = None):
        """Registra acesso a dados sensíveis"""
        event = self._create_base_event(
            'data_access',
            username=username,
            operation=operation,
            resource=resource,
            success=success,
            error=error
        )
        
        level = logging.INFO if success else logging.ERROR
        self.data_logger.log(level, json.dumps(event, ensure_ascii=False))
    
    def log_financial_data_access(self, username: str, data_type: str, 
                                record_count: Optional[int] = None):
        """Registra acesso específico a dados financeiros"""
        event = self._create_base_event(
            'financial_data_access',
            username=username,
            data_type=data_type,
            record_count=record_count
        )
        
        self.data_logger.info(json.dumps(event, ensure_ascii=False))
    
    def log_permission_denied(self, username: str, operation: str, 
                            resource: str, reason: Optional[str] = None):
        """Registra tentativa de acesso negado"""
        event = self._create_base_event(
            'permission_denied',
            username=username,
            operation=operation,
            resource=resource,
            reason=reason
        )
        
        self.system_logger.warning(json.dumps(event, ensure_ascii=False))
    
    def log_rate_limit_exceeded(self, ip_address: str, username: Optional[str] = None, 
                              operation: Optional[str] = None):
        """Registra violação de rate limit"""
        event = self._create_base_event(
            'rate_limit_exceeded',
            ip_address=ip_address,
            username=username,
            operation=operation
        )
        
        self.system_logger.warning(json.dumps(event, ensure_ascii=False))
    
    def log_suspicious_activity(self, description: str, username: Optional[str] = None, 
                              ip_address: Optional[str] = None, severity: str = 'medium'):
        """Registra atividade suspeita"""
        event = self._create_base_event(
            'suspicious_activity',
            description=description,
            username=username,
            ip_address=ip_address,
            severity=severity
        )
        
        self.system_logger.error(json.dumps(event, ensure_ascii=False))
    
    def log_system_error(self, error_type: str, error_message: str, 
                        username: Optional[str] = None, traceback: Optional[str] = None):
        """Registra erro de sistema"""
        event = self._create_base_event(
            'system_error',
            error_type=error_type,
            error_message=error_message,
            username=username,
            traceback=traceback
        )
        
        self.system_logger.error(json.dumps(event, ensure_ascii=False))
    
    def log_configuration_change(self, username: str, setting: str, 
                               old_value: Optional[str] = None, new_value: Optional[str] = None):
        """Registra mudança de configuração"""
        event = self._create_base_event(
            'configuration_change',
            username=username,
            setting=setting,
            old_value=old_value,
            new_value=new_value
        )
        
        self.system_logger.warning(json.dumps(event, ensure_ascii=False))
    
    def log_session_event(self, username: str, event_type: str, 
                         session_duration: Optional[int] = None):
        """Registra eventos de sessão"""
        event = self._create_base_event(
            'session_event',
            username=username,
            session_event_type=event_type,
            session_duration_seconds=session_duration
        )
        
        self.auth_logger.info(json.dumps(event, ensure_ascii=False))
    
    def log_system_event(self, event_type: str, details: Optional[Dict[str, Any]] = None, 
                        username: Optional[str] = None, severity: str = 'info'):
        """Registra evento genérico do sistema"""
        event = self._create_base_event(
            'system_event',
            username=username,
            severity=severity,
            system_event_type=event_type,
            details=details
        )
        
        if severity == 'error':
            self.system_logger.error(json.dumps(event, ensure_ascii=False))
        elif severity == 'warning':
            self.system_logger.warning(json.dumps(event, ensure_ascii=False))
        else:
            self.system_logger.info(json.dumps(event, ensure_ascii=False))
    
    def _check_multiple_failures(self, username: str, ip_address: Optional[str]):
        """Verifica se há múltiplas falhas e alerta"""
        # Implementação simples - pode ser expandida com análise mais sofisticada
        self.log_suspicious_activity(
            f"Multiple authentication failures for user {username} from IP {ip_address or 'unknown'}",
            username=username,
            ip_address=ip_address,
            severity='high'
        )
    
    def generate_security_report(self, hours: int = 24) -> Dict[str, Any]:
        """Gera relatório de segurança das últimas N horas"""
        from datetime import timedelta
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        report = {
            'period_hours': hours,
            'generated_at': datetime.now().isoformat(),
            'events': {
                'authentication_attempts': 0,
                'failed_logins': 0,
                'successful_logins': 0,
                'data_access_events': 0,
                'permission_denials': 0,
                'rate_limit_violations': 0,
                'suspicious_activities': 0,
                'system_errors': 0
            },
            'top_users': [],
            'top_ips': [],
            'alerts': []
        }
        
        # Analisar logs e popular relatório
        # Esta é uma implementação básica - pode ser expandida
        
        return report
    def _log_user_operation(self, operation: str, username: str, details: Optional[Dict[str, Any]] = None):
        """Log específico para operações com usuários"""
        try:
            message = {
                'timestamp': datetime.now().isoformat(),
                'operation': operation,
                'username': username,
                'details': details if details is not None else {}
            }
            
            self.auth_logger.info(
                f"USER_OP - {json.dumps(message, ensure_ascii=False)}"
            )
            
            # Log adicional no arquivo do sistema
            with open(self.log_dir / 'system_security.log', 'a', encoding='utf-8') as f:
                f.write(f"{datetime.now().isoformat()} - USER_OPERATION - {json.dumps(message, ensure_ascii=False)}\n")
                
        except Exception as e:
            self.auth_logger.error(f"Error logging user operation: {str(e)}")


# Singleton global
_security_logger_instance = None

def get_security_logger() -> SecurityLogger:
    """Retorna instância singleton do security logger"""
    global _security_logger_instance
    if _security_logger_instance is None:
        _security_logger_instance = SecurityLogger()
    return _security_logger_instance