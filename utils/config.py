import os
from dotenv import load_dotenv
import streamlit as st

# Carregar variáveis de ambiente do arquivo .env (se existir)
load_dotenv()

# Configurações do Pluggy
PLUGGY_CLIENT_ID = os.getenv("PLUGGY_CLIENT_ID", "472c3d2e-2e10-4ab2-9797-d07bfb405b7b")
PLUGGY_CLIENT_SECRET = os.getenv("PLUGGY_CLIENT_SECRET", "d09c7f48-bc59-4dec-8b56-61abc7fd9228")
PLUGGY_API_URL = os.getenv("PLUGGY_API_URL", "https://api.pluggy.ai")

# Configurações gerais do aplicativo
APP_NAME = "Richness"
APP_DESCRIPTION = "Gerenciador financeiro pessoal"
DEFAULT_PERIOD_DAYS = 365  # Período padrão para busca de transações

# Configurações de cache
ENABLE_CACHE = True
CACHE_TTL = 300  # Tempo de vida do cache em segundos (5 minutos)

# Configurações do banco de dados
DB_PATH = os.getenv("DB_PATH", "richness.db")

# Configurações de perfil
PROFILE_PICS_DIR = os.getenv("PROFILE_PICS_DIR", "profile_pics")

# Configurações de categorias padrão
DEFAULT_CATEGORIES = [
    "Salário",
    "Transferência",
    "Alimentação",
    "Transporte",
    "Moradia",
    "Saúde",
    "Educação",
    "Lazer",
    "Vestuário",
    "Outros"
]

# Funções para caminhos isolados por usuário
def get_user_data_path(filename, username=None):
    """Obtém o caminho para um arquivo de dados específico do usuário"""
    try:
        from utils.user_data_manager import user_data_manager
        return user_data_manager.get_user_file_path(filename, username)
    except ImportError:
        # Fallback para compatibilidade
        return filename

def get_user_ofx_directories(username=None):
    """Obtém os diretórios de extratos e faturas específicos do usuário"""
    try:
        from utils.user_data_manager import user_data_manager
        return user_data_manager.get_user_ofx_directories(username)
    except ImportError:
        # Fallback para compatibilidade
        return "extratos", "faturas"

def get_current_user():
    """Obtém o usuário atual da sessão"""
    return st.session_state.get('usuario', 'default')

# Arquivos de dados isolados por usuário
def get_cache_categorias_file(username=None):
    return get_user_data_path("cache_categorias_usuario.json", username)

def get_descricoes_personalizadas_file(username=None):
    return get_user_data_path("descricoes_personalizadas.json", username)

def get_transacoes_excluidas_file(username=None):
    return get_user_data_path("transacoes_excluidas.json", username)

def get_categorias_personalizadas_file(username=None):
    return get_user_data_path("categorias_personalizadas.json", username)

def get_transacoes_manuais_file(username=None):
    return get_user_data_path("transacoes_manuais.json", username)
