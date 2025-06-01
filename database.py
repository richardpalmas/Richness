import sqlite3
from pathlib import Path
import functools
import threading
import time

DB_PATH = Path('richness.db')

# Conexão persistente para cada thread
_local = threading.local()
# Cache para consultas frequentes
_query_cache = {}
_cache_ttl = 60  # Tempo de vida do cache em segundos

def get_connection():
    """
    Retorna uma conexão com o banco de dados otimizada para performance.
    Mantém uma conexão por thread para evitar custos de abertura/fechamento.
    """
    if not hasattr(_local, 'conn') or _local.conn is None:
        _local.conn = sqlite3.connect(DB_PATH)
        _local.conn.row_factory = sqlite3.Row
        # Otimizações de performance
        _local.conn.execute("PRAGMA journal_mode = WAL")  # Write-Ahead Logging
        _local.conn.execute("PRAGMA synchronous = NORMAL")  # Menos sincronizações com disco
        _local.conn.execute("PRAGMA cache_size = 10000")  # Cache maior
        _local.conn.execute("PRAGMA temp_store = MEMORY")  # Tabelas temporárias em memória
        _local.conn.execute("PRAGMA mmap_size = 30000000")  # Usar mapeamento de memória
        _local.conn.execute("PRAGMA page_size = 4096")  # Tamanho de página otimizado
    return _local.conn

# Cache para consultas frequentes
@functools.lru_cache(maxsize=128)
def _cached_query(query, params_str):
    """Cache interno para consultas frequentes"""
    conn = get_connection()
    cur = conn.cursor()
    # Converter string de parâmetros de volta para tupla
    params = eval(params_str) if params_str else ()
    cur.execute(query, params)
    return [dict(row) for row in cur.fetchall()]

def query_with_cache(query, params=None, ttl=_cache_ttl):
    """Executa consulta com cache para melhorar performance"""
    # Converter parâmetros para string para uso com cache
    params_str = str(params) if params else ""
    cache_key = f"{query}:{params_str}"

    # Verificar cache
    current_time = time.time()
    if cache_key in _query_cache:
        cached_result, timestamp = _query_cache[cache_key]
        if current_time - timestamp < ttl:
            return cached_result

    # Executar consulta
    result = _cached_query(query, params_str)

    # Armazenar no cache
    _query_cache[cache_key] = (result, current_time)
    return result

def execute_batch(statements):
    """
    Executa múltiplas declarações SQL em uma única transação
    para melhorar performance de operações em lote.    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        conn.execute("BEGIN TRANSACTION")
        for stmt, params in statements:
            cur.execute(stmt, params if params else ())
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        return False

def create_tables():
    conn = get_connection()
    cur = conn.cursor()
    # Tabela de usuários
    cur.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            usuario TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            email TEXT,
            profile_pic TEXT
        )
    ''')
    # Tabela de economias
    cur.execute('''
        CREATE TABLE IF NOT EXISTS economias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            data TEXT NOT NULL,
            valor REAL NOT NULL,
            tipo TEXT,
            descricao TEXT,
            categoria TEXT,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    ''')
    # Tabela de cartões
    cur.execute('''
        CREATE TABLE IF NOT EXISTS cartoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            data TEXT NOT NULL,
            valor REAL NOT NULL,
            tipo TEXT,
            descricao TEXT,
            categoria TEXT,
            cartao_nome TEXT,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    ''')
    # Tabela de extratos
    cur.execute('''
        CREATE TABLE IF NOT EXISTS extratos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            data TEXT NOT NULL,
            valor REAL NOT NULL,
            tipo TEXT,
            descricao TEXT,
            categoria TEXT,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    ''')
    # Tabela de itemIds Pluggy
    cur.execute('''
        CREATE TABLE IF NOT EXISTS pluggy_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            item_id TEXT NOT NULL,
            nome TEXT,
            UNIQUE(usuario_id, item_id),
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    ''')

    # Índices para melhorar performance de consultas
    cur.execute('CREATE INDEX IF NOT EXISTS idx_usuarios_usuario ON usuarios(usuario)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_economias_usuario_id ON economias(usuario_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_cartoes_usuario_id ON cartoes(usuario_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_extratos_usuario_id ON extratos(usuario_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pluggy_items_usuario_id ON pluggy_items(usuario_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pluggy_items_item_id ON pluggy_items(item_id)')
    # Índices adicionais para melhorar performance de consultas frequentes
    cur.execute('CREATE INDEX IF NOT EXISTS idx_economias_data ON economias(data)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_cartoes_data ON cartoes(data)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_extratos_data ON extratos(data)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_extratos_categoria ON extratos(categoria)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_cartoes_categoria ON cartoes(categoria)')

    conn.commit()

def remover_usuario(usuario):
    """
    Remove o usuário e todos os seus dados relacionados do banco de dados.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT id FROM usuarios WHERE usuario = ?', (usuario,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return False
    usuario_id = row['id']

    # Usar transação para garantir atomicidade e melhorar performance
    conn.execute('BEGIN TRANSACTION')
    try:
        # Remover dados relacionados
        cur.execute('DELETE FROM economias WHERE usuario_id = ?', (usuario_id,))
        cur.execute('DELETE FROM cartoes WHERE usuario_id = ?', (usuario_id,))
        cur.execute('DELETE FROM extratos WHERE usuario_id = ?', (usuario_id,))
        cur.execute('DELETE FROM pluggy_items WHERE usuario_id = ?', (usuario_id,))
        # Remover usuário
        cur.execute('DELETE FROM usuarios WHERE id = ?', (usuario_id,))
        conn.commit()

        # Limpar cache após mudanças
        limpar_cache_consultas()
        return True
    except Exception:
        conn.rollback()
        return False

def limpar_cache_consultas():
    """Limpa o cache de consultas para forçar dados atualizados"""
    global _query_cache
    _query_cache = {}
    _cached_query.cache_clear()

def get_usuario_por_nome(usuario, campos="*"):
    """
    Função otimizada para buscar dados do usuário pelo nome, com cache.
    """
    query = f"SELECT {campos} FROM usuarios WHERE usuario = ?"
    result = query_with_cache(query, (usuario,))
    return result[0] if result else None

if __name__ == '__main__':
    create_tables()

