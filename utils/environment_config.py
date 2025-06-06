"""
Módulo de configuração de ambiente robusto para produção e desenvolvimento.
Lida com variáveis de ambiente com fallbacks seguros.
"""

import os
import streamlit as st
from typing import Optional, Dict, Any
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnvironmentConfig:
    """Classe para gerenciar configurações de ambiente de forma robusta."""
    
    def __init__(self):
        """Inicializa o gerenciador de configuração."""
        self._load_environment()
        self._validate_config()
    
    def _load_environment(self):
        """Carrega variáveis de ambiente com fallbacks seguros."""
        try:
            # Tenta carregar o arquivo .env se existir
            env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
            if os.path.exists(env_file):
                from dotenv import load_dotenv
                load_dotenv(env_file)
                logger.info("Arquivo .env carregado com sucesso")
            else:
                logger.info("Arquivo .env não encontrado, usando variáveis de sistema")
        except ImportError:
            logger.warning("python-dotenv não instalado, usando apenas variáveis de sistema")
        except Exception as e:
            logger.error(f"Erro ao carregar .env: {e}")
    
    def _clean_api_key(self, api_key: str) -> str:
        """Limpa e valida a chave da API OpenAI."""
        if not api_key:
            return ""
        
        # Remove quebras de linha, espaços e caracteres inválidos
        cleaned = api_key.strip().replace('\n', '').replace('\r', '').replace(' ', '')
        
        # Valida o formato básico da chave OpenAI
        if cleaned.startswith('sk-') and len(cleaned) >= 40:
            return cleaned
        
        logger.warning(f"Formato de chave API suspeito: {len(cleaned)} caracteres")
        return cleaned
    
    def _validate_config(self):
        """Valida configurações críticas."""
        openai_key = self.get_openai_api_key()
        if not openai_key:
            logger.warning("OPENAI_API_KEY não configurada")
        elif len(openai_key) < 40:
            logger.warning("OPENAI_API_KEY parece estar incompleta")
    
    def get_openai_api_key(self) -> str:
        """Obtém a chave da API OpenAI limpa e validada."""
        # Tenta várias fontes em ordem de prioridade
        sources = [
            lambda: os.getenv('OPENAI_API_KEY'),
            lambda: st.secrets.get('OPENAI_API_KEY') if hasattr(st, 'secrets') else None,
            lambda: os.getenv('OPENAI_KEY'),  # Fallback alternativo
        ]
        
        for source in sources:
            try:
                key = source()
                if key:
                    cleaned_key = self._clean_api_key(key)
                    if cleaned_key:
                        return cleaned_key
            except Exception as e:
                logger.debug(f"Erro ao obter chave de uma fonte: {e}")
                continue
        
        return ""
    
    def get_huggingface_token(self) -> str:
        """Obtém o token do HuggingFace."""
        return os.getenv('HUGGINGFACEHUB_API_TOKEN', '')
    
    def get_pluggy_config(self) -> Dict[str, str]:
        """Obtém configurações do Pluggy."""
        return {
            'client_id': os.getenv('PLUGGY_CLIENT_ID', ''),
            'client_secret': os.getenv('PLUGGY_CLIENT_SECRET', ''),
            'api_url': os.getenv('PLUGGY_API_URL', 'https://api.pluggy.ai')
        }
    
    def is_development(self) -> bool:
        """Verifica se está em ambiente de desenvolvimento."""
        return os.getenv('ENV', 'development').lower() == 'development'
    
    def is_production(self) -> bool:
        """Verifica se está em ambiente de produção."""
        return os.getenv('ENV', 'development').lower() == 'production'
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Retorna informações de debug sobre a configuração."""
        openai_key = self.get_openai_api_key()
        return {
            'openai_key_configured': bool(openai_key),
            'openai_key_length': len(openai_key) if openai_key else 0,
            'openai_key_prefix': openai_key[:10] + '...' if openai_key else '',
            'huggingface_configured': bool(self.get_huggingface_token()),
            'pluggy_configured': bool(self.get_pluggy_config()['client_id']),
            'environment': 'production' if self.is_production() else 'development',
            'env_file_exists': os.path.exists(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
        }

# Singleton global
_config_instance = None

def get_config() -> EnvironmentConfig:
    """Retorna a instância singleton da configuração."""
    global _config_instance
    if _config_instance is None:
        _config_instance = EnvironmentConfig()
    return _config_instance

# Funções de conveniência
def get_openai_api_key() -> str:
    """Função de conveniência para obter a chave OpenAI."""
    return get_config().get_openai_api_key()

def get_huggingface_token() -> str:
    """Função de conveniência para obter o token HuggingFace."""
    return get_config().get_huggingface_token()

def validate_openai_key(api_key: str = None) -> tuple[bool, str]:
    """Valida se a chave OpenAI está correta."""
    if not api_key:
        api_key = get_openai_api_key()
    
    if not api_key:
        return False, "Chave da API não configurada"
    
    if not api_key.startswith('sk-'):
        return False, "Formato de chave inválido (deve começar com 'sk-')"
    
    if len(api_key) < 40:
        return False, f"Chave muito curta ({len(api_key)} caracteres)"
    
    if len(api_key) > 200:
        return False, f"Chave muito longa ({len(api_key)} caracteres) - pode ter formatação incorreta"
    
    return True, "Chave válida"
