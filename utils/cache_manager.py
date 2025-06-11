"""
Gerenciador de Cache para o Pluggy - Responsável por operações de cache
"""
import hashlib
import pickle
from datetime import datetime
from pathlib import Path
from utils.config import ENABLE_CACHE, CACHE_TTL

class CacheManager:
    """Gerencia operações de cache para os dados obtidos da API Pluggy"""
    
    def __init__(self):
        self._cache = {}
        self._categorias_cache = {}  # Cache específico para categorias
        self._descricoes_cache = {}  # Cache específico para descrições enriquecidas
        self._CACHE_DIR = Path("cache")  # Diretório para cache persistente
        
        # Criar diretório de cache se não existir
        if not self._CACHE_DIR.exists():
            self._CACHE_DIR.mkdir(exist_ok=True)
            
        # Carregar cache existente
        self._load_persistent_cache()
    
    def _load_persistent_cache(self):
        """Carregar cache persistente do disco"""
        cache_file = self._CACHE_DIR / "cache.pkl"
        if cache_file.exists():
            with cache_file.open("rb") as f:
                try:
                    self._cache = pickle.load(f)
                except Exception as e:
                    print(f"Erro ao carregar cache: {e}")
                    self._cache = {}

        categorias_cache_file = self._CACHE_DIR / "categorias_cache.pkl"
        if categorias_cache_file.exists():
            with categorias_cache_file.open("rb") as f:
                try:
                    self._categorias_cache = pickle.load(f)
                except Exception as e:
                    print(f"Erro ao carregar cache de categorias: {e}")
                    self._categorias_cache = {}

        descricoes_cache_file = self._CACHE_DIR / "descricoes_cache.pkl"
        if descricoes_cache_file.exists():
            with descricoes_cache_file.open("rb") as f:
                try:
                    self._descricoes_cache = pickle.load(f)
                except Exception as e:
                    print(f"Erro ao carregar cache de descrições: {e}")
                    self._descricoes_cache = {}

    def _save_persistent_cache(self):
        """Salvar cache persistente no disco"""
        cache_file = self._CACHE_DIR / "cache.pkl"
        with cache_file.open("wb") as f:
            pickle.dump(self._cache, f)

        categorias_cache_file = self._CACHE_DIR / "categorias_cache.pkl"
        with categorias_cache_file.open("wb") as f:
            pickle.dump(self._categorias_cache, f)

        descricoes_cache_file = self._CACHE_DIR / "descricoes_cache.pkl"
        with descricoes_cache_file.open("wb") as f:
            pickle.dump(self._descricoes_cache, f)
            
    def get_from_cache(self, cache_key, force_refresh=False):
        """Recuperar dados do cache se estiverem válidos"""
        if not ENABLE_CACHE or force_refresh:
            return None

        if cache_key in self._cache:
            entry = self._cache[cache_key]
            # Verificar se o cache ainda é válido
            if (datetime.now() - entry['timestamp']).total_seconds() < CACHE_TTL:
                return entry['data']

        return None
        
    def save_to_cache(self, cache_key, data):
        """Salvar dados no cache"""
        if not ENABLE_CACHE:
            return

        self._cache[cache_key] = {
            'data': data,
            'timestamp': datetime.now()
        }
        self._save_persistent_cache()
        
    def get_from_category_cache(self, cache_key):
        """Recuperar categoria do cache"""
        if not ENABLE_CACHE:
            return None
            
        return self._categorias_cache.get(cache_key)
        
    def save_to_category_cache(self, cache_key, category):
        """Salvar categoria no cache"""
        if not ENABLE_CACHE:
            return
            
        self._categorias_cache[cache_key] = category
        self._save_persistent_cache()
        
    def get_from_description_cache(self, cache_key):
        """Recuperar descrição do cache"""
        if not ENABLE_CACHE:
            return None
            
        return self._descricoes_cache.get(cache_key)
        
    def save_to_description_cache(self, cache_key, description):
        """Salvar descrição no cache"""
        if not ENABLE_CACHE:
            return
            
        self._descricoes_cache[cache_key] = description
        self._save_persistent_cache()

    @staticmethod
    def get_hash(text):
        """Gera um hash para um texto para usar como chave de cache"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
        
    def limpar_cache(self):
        """Limpa todos os caches para forçar a obtenção de dados atualizados"""
        self._cache = {}
        self._categorias_cache = {}
        self._descricoes_cache = {}
        self._save_persistent_cache()
        print("🧹 Cache limpo com sucesso")
