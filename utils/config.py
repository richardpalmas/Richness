import os
from dotenv import load_dotenv

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
