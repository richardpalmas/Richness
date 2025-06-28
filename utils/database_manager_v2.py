"""
Gerenciador de banco de dados otimizado para a aplicação Richness.
Implementa melhores práticas de banco de dados, segurança e performance.
Versão 2.0 com melhorias avançadas.
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
from contextlib import contextmanager
from typing import List, Dict, Optional, Tuple, Any
import streamlit as st
import json
import os
import threading
import time
from functools import lru_cache
import logging
from concurrent.futures import ThreadPoolExecutor

class DatabaseManager:
    """Gerenciador central do banco de dados com melhores práticas e otimizações"""
    
    def __init__(self, db_path="richness_v2.db", pool_size=5):
        self.db_path = db_path
        self.pool_size = pool_size
        self._connection_pool = []
        self._pool_lock = threading.Lock()
        self._query_cache = {}
        self._cache_lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=3)
        self._health_stats = {
            'connections_created': 0,
            'queries_executed': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'last_backup': None,
            'errors': 0
        }
        
        # Configurar logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        self.init_database()
        self._schedule_maintenance()
    
    def _create_connection(self) -> sqlite3.Connection:
        """Cria nova conexão otimizada"""
        conn = sqlite3.connect(
            self.db_path,
            timeout=30.0,
            check_same_thread=False,
            isolation_level=None  # Autocommit mode
        )
        
        # Configurações otimizadas
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL") 
        conn.execute("PRAGMA cache_size = 10000")
        conn.execute("PRAGMA temp_store = MEMORY")
        conn.execute("PRAGMA mmap_size = 268435456")  # 256MB
        
        conn.row_factory = sqlite3.Row
        self._health_stats['connections_created'] += 1
        return conn
    
    @contextmanager
    def get_connection(self):
        """Context manager para conexões com pooling otimizado"""
        conn = None
        
        # Tentar reutilizar conexão do pool
        with self._pool_lock:
            if self._connection_pool:
                conn = self._connection_pool.pop()
        
        # Criar nova se necessário
        if conn is None:
            conn = self._create_connection()
        
        try:
            yield conn
            # Retornar para o pool se não estiver cheio
            with self._pool_lock:
                if len(self._connection_pool) < self.pool_size:
                    self._connection_pool.append(conn)
                    conn = None
        except Exception as e:
            self._health_stats['errors'] += 1
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    @lru_cache(maxsize=100)
    def _get_cached_query_plan(self, query: str) -> str:
        """Cache para planos de execução de queries"""
        return query
    
    def _should_cache_query(self, query: str) -> bool:
        """Determina se query deve ser cacheada"""
        query_lower = query.lower().strip()
        return (
            query_lower.startswith('select') and
            'current_timestamp' not in query_lower and
            'random()' not in query_lower and
            len(query) < 1000
        )

    def init_database(self):
        """Inicializa o banco com as tabelas necessárias usando melhores práticas"""
        with self.get_connection() as conn:
            # Tabela de usuários
            conn.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    user_hash TEXT UNIQUE NOT NULL,
                    password_hash TEXT, -- Hash bcrypt da senha
                    email TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    preferences TEXT, -- JSON com preferências
                    is_active BOOLEAN DEFAULT 1,
                    CONSTRAINT username_length CHECK (length(username) >= 2),
                    CONSTRAINT user_hash_length CHECK (length(user_hash) = 16)
                )
            """)
            
            # Tabela principal de transações
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transacoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    hash_transacao TEXT NOT NULL,
                    data DATE NOT NULL,
                    descricao TEXT NOT NULL,
                    valor DECIMAL(15,2) NOT NULL,
                    categoria TEXT DEFAULT 'Outros',
                    tipo TEXT CHECK(tipo IN ('receita', 'despesa')) NOT NULL,
                    origem TEXT CHECK(origem IN ('ofx_extrato', 'ofx_cartao', 'manual')) NOT NULL,
                    conta TEXT,
                    arquivo_origem TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                    UNIQUE(user_id, hash_transacao),
                    CONSTRAINT valor_not_zero CHECK (valor != 0)
                )
            """)
            
            # Tabela de categorias personalizadas
            conn.execute("""
                CREATE TABLE IF NOT EXISTS categorias_personalizadas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    nome TEXT NOT NULL,
                    cor TEXT DEFAULT '#6c757d',
                    icone TEXT DEFAULT '🏷️',
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                    UNIQUE(user_id, nome),
                    CONSTRAINT nome_length CHECK (length(nome) >= 2 AND length(nome) <= 50)
                )
            """)
            
            # Tabela de descrições personalizadas
            conn.execute("""
                CREATE TABLE IF NOT EXISTS descricoes_personalizadas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    hash_transacao TEXT NOT NULL,
                    descricao TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                    UNIQUE(user_id, hash_transacao),
                    CONSTRAINT descricao_length CHECK (length(descricao) <= 250)
                )
            """)
            
            # Tabela de transações excluídas (soft delete)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transacoes_excluidas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    hash_transacao TEXT NOT NULL,
                    motivo TEXT,
                    excluded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                    UNIQUE(user_id, hash_transacao)
                )
            """)
            
            # Tabela de metas de economia
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metas_economia (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    nome TEXT NOT NULL,
                    valor_total DECIMAL(15,2) NOT NULL CHECK (valor_total > 0),
                    prazo_meses INTEGER NOT NULL CHECK (prazo_meses > 0),
                    valor_mensal DECIMAL(15,2) NOT NULL CHECK (valor_mensal > 0),
                    valor_economizado DECIMAL(15,2) DEFAULT 0 CHECK (valor_economizado >= 0),
                    data_criacao DATE NOT NULL,
                    data_conclusao_prevista DATE NOT NULL,
                    observacoes TEXT,
                    status TEXT DEFAULT 'ativa' CHECK (status IN ('ativa', 'concluida', 'cancelada')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                    CONSTRAINT nome_length CHECK (length(nome) >= 2 AND length(nome) <= 200),
                    CONSTRAINT valor_economizado_max CHECK (valor_economizado <= valor_total),
                    CONSTRAINT data_conclusao_valida CHECK (data_conclusao_prevista >= data_criacao)
                )
            """)
            
            # Tabela de cache de categorização IA
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_categorizacao_ia (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    descricao_hash TEXT NOT NULL,
                    descricao_original TEXT NOT NULL,
                    categoria_sugerida TEXT NOT NULL,
                    confianca DECIMAL(4,3) DEFAULT 0.0,
                    modelo_usado TEXT DEFAULT 'gpt-4o-mini',
                    aprovada BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    used_count INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                    UNIQUE(user_id, descricao_hash),
                    CONSTRAINT confianca_range CHECK (confianca >= 0.0 AND confianca <= 1.0)
                )
            """)
            
            # Tabela de cache de insights LLM
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_insights_llm (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    insight_type TEXT NOT NULL, -- 'saldo_mensal', 'maior_gasto', 'economia_potencial', 'alerta_gastos'
                    personalidade TEXT NOT NULL, -- 'clara', 'tecnica', 'durona', ou nome do perfil customizado
                    data_hash TEXT NOT NULL, -- Hash dos dados usados para gerar o insight
                    prompt_hash TEXT NOT NULL, -- Hash do prompt usado
                    insight_titulo TEXT NOT NULL,
                    insight_valor TEXT,
                    insight_comentario TEXT NOT NULL,
                    modelo_usado TEXT DEFAULT 'gpt-4o-mini',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL, -- Data de expiração do cache
                    used_count INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                    UNIQUE(user_id, insight_type, personalidade, data_hash, prompt_hash),
                    CONSTRAINT insight_type_valid CHECK (insight_type IN ('saldo_mensal', 'maior_gasto', 'economia_potencial', 'alerta_gastos', 'total_gastos_cartao', 'maior_gasto_cartao', 'padrao_gastos_cartao', 'controle_cartao'))
                )
            """)
            
            # Tabela de transações manuais (histórico separado)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transacoes_manuais (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    data DATE NOT NULL,
                    descricao TEXT NOT NULL,
                    valor DECIMAL(15,2) NOT NULL,
                    categoria TEXT DEFAULT 'Outros',
                    tipo_pagamento TEXT CHECK(tipo_pagamento IN ('Espécie', 'PIX', 'Cartão Débito', 'Cartão Crédito', 'Transferência')) NOT NULL,
                    observacoes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                    CONSTRAINT valor_manual_not_zero CHECK (valor != 0)
                )
            """)
            
            # Tabela de arquivos OFX processados (evitar reprocessamento)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS arquivos_ofx_processados (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    nome_arquivo TEXT NOT NULL,
                    hash_arquivo TEXT NOT NULL,
                    tipo TEXT CHECK(tipo IN ('extrato', 'cartao')) NOT NULL,
                    data_processamento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_transacoes INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                    UNIQUE(user_id, hash_arquivo)
                )
            """)
              # Tabela de logs de sistema
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT NOT NULL,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ip_address TEXT,
                    FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE SET NULL
                )
            """)
            
            # Tabela de compromissos (pagamentos futuros)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS compromissos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    descricao TEXT NOT NULL,
                    valor DECIMAL(15,2) NOT NULL,
                    data_vencimento DATE NOT NULL,
                    categoria TEXT DEFAULT 'Compromisso',
                    status TEXT CHECK(status IN ('pendente', 'pago', 'cancelado')) DEFAULT 'pendente',
                    observacoes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                    CONSTRAINT valor_compromisso_not_zero CHECK (valor != 0),
                    CONSTRAINT descricao_length CHECK (length(descricao) >= 2 AND length(descricao) <= 200)                )
            """)
            
            # Tabela de conversas com IA
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversas_ia (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    pergunta TEXT NOT NULL,
                    resposta TEXT NOT NULL,
                    personalidade TEXT NOT NULL DEFAULT 'clara',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                    CONSTRAINT pergunta_length CHECK (length(pergunta) >= 1 AND length(pergunta) <= 1000),
                    CONSTRAINT resposta_length CHECK (length(resposta) >= 1)
                )
            """)
            
            # Tabela de personalidades customizadas de IA por usuário
            conn.execute("""
                CREATE TABLE IF NOT EXISTS personalidades_ia_usuario (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    nome_perfil TEXT NOT NULL,
                    formalidade TEXT,
                    uso_emojis TEXT,
                    tom TEXT,
                    foco TEXT,
                    prompt_base TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                    UNIQUE(user_id, nome_perfil)
                )
            """)
            
            # Índices para performance otimizada
            self._criar_indices(conn)
            
            # Triggers para auditoria automática
            self._criar_triggers(conn)
              # Views materializadas para relatórios
            self._criar_views(conn)
            
            # Executar migrações necessárias
            self._migrate_database()
    
    def _criar_indices(self, conn):
        """Cria índices otimizados para performance"""
        indices = [
            # Índices principais para transações (compostos otimizados)
            "CREATE INDEX IF NOT EXISTS idx_transacoes_user_data_valor ON transacoes(user_id, data DESC, valor)",
            "CREATE INDEX IF NOT EXISTS idx_transacoes_categoria_data ON transacoes(user_id, categoria, data DESC)",
            "CREATE INDEX IF NOT EXISTS idx_transacoes_hash ON transacoes(user_id, hash_transacao)",
            "CREATE INDEX IF NOT EXISTS idx_transacoes_origem_data ON transacoes(user_id, origem, data DESC)",
            
            # Índices para joins otimizados
            "CREATE INDEX IF NOT EXISTS idx_descricoes_hash ON descricoes_personalizadas(user_id, hash_transacao)",
            "CREATE INDEX IF NOT EXISTS idx_excluidas_hash ON transacoes_excluidas(user_id, hash_transacao)",
            
            # Índices para cache IA
            "CREATE INDEX IF NOT EXISTS idx_cache_ia_hash ON cache_categorizacao_ia(user_id, descricao_hash)",
            "CREATE INDEX IF NOT EXISTS idx_cache_ia_aprovada ON cache_categorizacao_ia(user_id, aprovada, used_count)",
            
            # Índices para cache de insights LLM
            "CREATE INDEX IF NOT EXISTS idx_cache_insights_user_type ON cache_insights_llm(user_id, insight_type, personalidade)",
            "CREATE INDEX IF NOT EXISTS idx_cache_insights_hash ON cache_insights_llm(user_id, data_hash, prompt_hash)",
            "CREATE INDEX IF NOT EXISTS idx_cache_insights_expires ON cache_insights_llm(expires_at)",
            "CREATE INDEX IF NOT EXISTS idx_cache_insights_used ON cache_insights_llm(user_id, used_count DESC)",
            
            # Índices para categorias
            "CREATE INDEX IF NOT EXISTS idx_categorias_user_active ON categorias_personalizadas(user_id, is_active)",
            
            # Índices para conversas IA
            "CREATE INDEX IF NOT EXISTS idx_conversas_ia_user_data ON conversas_ia(user_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_conversas_ia_personalidade ON conversas_ia(user_id, personalidade, created_at DESC)",
            
            # Índices para arquivos processados
            "CREATE INDEX IF NOT EXISTS idx_arquivos_user_tipo ON arquivos_ofx_processados(user_id, tipo, data_processamento)",
            
            # Índices para logs
            "CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON system_logs(timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_logs_user_action ON system_logs(user_id, action, timestamp)",
              # Índices para manuais
            "CREATE INDEX IF NOT EXISTS idx_manuais_user_data ON transacoes_manuais(user_id, data DESC)",
            
            # Índices para compromissos
            "CREATE INDEX IF NOT EXISTS idx_compromissos_user_data ON compromissos(user_id, data_vencimento DESC)",
            "CREATE INDEX IF NOT EXISTS idx_compromissos_status ON compromissos(user_id, status, data_vencimento)",
            
            # Índices para metas de economia
            "CREATE INDEX IF NOT EXISTS idx_metas_economia_user_status ON metas_economia(user_id, status, data_criacao DESC)",
            "CREATE INDEX IF NOT EXISTS idx_metas_economia_user_data ON metas_economia(user_id, data_criacao DESC)",
            "CREATE INDEX IF NOT EXISTS idx_metas_economia_conclusao ON metas_economia(user_id, data_conclusao_prevista)",
        ]
        
        for indice in indices:
            try:
                conn.execute(indice)
            except sqlite3.Error as e:
                self.logger.warning(f"Erro ao criar índice: {e}")
    
    def _criar_triggers(self, conn):
        """Cria triggers para auditoria e integridade"""
        # Trigger para atualizar updated_at automaticamente
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS update_transacoes_timestamp 
            AFTER UPDATE ON transacoes
            BEGIN
                UPDATE transacoes SET updated_at = CURRENT_TIMESTAMP 
                WHERE id = NEW.id;
            END
        """)
        
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS update_descricoes_timestamp 
            AFTER UPDATE ON descricoes_personalizadas
            BEGIN
                UPDATE descricoes_personalizadas SET updated_at = CURRENT_TIMESTAMP 
                WHERE id = NEW.id;
            END
        """)
        
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS update_metas_economia_timestamp 
            AFTER UPDATE ON metas_economia
            BEGIN
                UPDATE metas_economia SET updated_at = CURRENT_TIMESTAMP 
                WHERE id = NEW.id;
            END
        """)
        
        # Trigger para incrementar contador de uso do cache IA
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS increment_cache_usage
            AFTER UPDATE OF aprovada ON cache_categorizacao_ia
            WHEN NEW.aprovada = 1 AND OLD.aprovada = 0
            BEGIN
                UPDATE cache_categorizacao_ia SET used_count = used_count + 1
                WHERE id = NEW.id;
            END
        """)
        
        # Trigger para log de exclusões
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS log_exclusoes
            AFTER INSERT ON transacoes_excluidas
            BEGIN
                INSERT INTO system_logs (user_id, action, details)
                VALUES (NEW.user_id, 'transacao_excluida', 
                       'Hash: ' || NEW.hash_transacao || ' | Motivo: ' || COALESCE(NEW.motivo, 'Não informado'));
            END
        """)
    
    def _criar_views(self, conn):
        """Cria views materializadas para relatórios"""
        # View para dashboard resumo
        conn.execute("""
            CREATE VIEW IF NOT EXISTS vw_dashboard_resumo AS
            SELECT 
                t.user_id,
                COUNT(*) as total_transacoes,
                SUM(CASE WHEN t.valor > 0 THEN t.valor ELSE 0 END) as receitas_totais,
                SUM(CASE WHEN t.valor < 0 THEN ABS(t.valor) ELSE 0 END) as despesas_totais,
                MAX(t.data) as ultima_transacao,
                COUNT(DISTINCT t.categoria) as categorias_utilizadas
            FROM transacoes t
            LEFT JOIN transacoes_excluidas te ON t.user_id = te.user_id AND t.hash_transacao = te.hash_transacao
            WHERE te.hash_transacao IS NULL
            GROUP BY t.user_id
        """)
        
        # View para estatísticas por categoria
        conn.execute("""
            CREATE VIEW IF NOT EXISTS vw_estatisticas_categoria AS
            SELECT 
                t.user_id,
                t.categoria,
                COUNT(*) as total_transacoes,
                SUM(CASE WHEN t.valor > 0 THEN t.valor ELSE 0 END) as receitas,
                SUM(CASE WHEN t.valor < 0 THEN ABS(t.valor) ELSE 0 END) as despesas,
                AVG(CASE WHEN t.valor < 0 THEN ABS(t.valor) END) as media_despesas,
                strftime('%Y-%m', MAX(t.data)) as ultimo_mes
            FROM transacoes t
            LEFT JOIN transacoes_excluidas te ON t.user_id = te.user_id AND t.hash_transacao = te.hash_transacao
            WHERE te.hash_transacao IS NULL
            GROUP BY t.user_id, t.categoria
        """)
    
    def _schedule_maintenance(self):
        """Agenda tarefas de manutenção automática"""
        def maintenance_worker():
            while True:
                try:
                    time.sleep(3600)  # A cada hora
                    self._run_maintenance()
                except Exception as e:
                    self.logger.error(f"Erro na manutenção: {e}")
        
        maintenance_thread = threading.Thread(target=maintenance_worker, daemon=True)
        maintenance_thread.start()
    
    def _run_maintenance(self):
        """Executa tarefas de manutenção"""
        try:
            # Limpeza de cache antigo
            with self._cache_lock:
                if len(self._query_cache) > 500:
                    # Manter apenas os 200 mais recentes
                    items = list(self._query_cache.items())[-200:]
                    self._query_cache = dict(items)
            
            # Backup automático diário
            now = datetime.now()
            last_backup = self._health_stats.get('last_backup')
            
            if not last_backup or (now - last_backup).days >= 1:
                self.backup_database()
                self._health_stats['last_backup'] = now
            
            # VACUUM periódico
            if now.hour == 3:  # 3h da manhã
                with self.get_connection() as conn:
                    conn.execute("VACUUM")
                    
        except Exception as e:
            self.logger.error(f"Erro na manutenção: {e}")

    def executar_query(self, query: str, params: Optional[List[Any]] = None) -> List[sqlite3.Row]:
        """Executa query SELECT de forma segura com cache"""
        cache_key = f"{query}|{str(params or [])}"
        
        # Verificar cache
        if self._should_cache_query(query):
            with self._cache_lock:
                if cache_key in self._query_cache:
                    self._health_stats['cache_hits'] += 1
                    return self._query_cache[cache_key]
                else:
                    self._health_stats['cache_misses'] += 1
        
        with self.get_connection() as conn:
            self._health_stats['queries_executed'] += 1
            if params:
                result = conn.execute(query, params).fetchall()
            else:
                result = conn.execute(query).fetchall()
            
            # Salvar no cache se apropriado
            if self._should_cache_query(query) and len(result) < 1000:
                with self._cache_lock:
                    self._query_cache[cache_key] = result
            
            return result
    
    def executar_query_df(self, query: str, params: Optional[List[Any]] = None) -> pd.DataFrame:
        """Executa query e retorna DataFrame pandas"""
        with self.get_connection() as conn:
            self._health_stats['queries_executed'] += 1
            return pd.read_sql_query(query, conn, params=params or [])
    
    def executar_insert(self, query: str, params: Optional[List[Any]] = None) -> int:
        """Executa INSERT e retorna o ID gerado"""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params or [])
            return cursor.lastrowid or 0
    
    def executar_update(self, query: str, params: Optional[List[Any]] = None) -> int:
        """Executa UPDATE/DELETE e retorna quantidade de linhas afetadas"""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params or [])
            return cursor.rowcount
    
    def executar_batch(self, queries: List[Tuple[str, List[Any]]]) -> List[int]:
        """Executa múltiplas queries em uma transação"""
        results = []
        with self.get_connection() as conn:
            conn.execute("BEGIN TRANSACTION")
            try:
                for query, params in queries:
                    cursor = conn.execute(query, params)
                    results.append(cursor.rowcount)
                conn.execute("COMMIT")
                return results
            except Exception as e:
                conn.execute("ROLLBACK")
                raise e
    
    def criar_usuario_se_nao_existe(self, username: str) -> int:
        """Cria usuário se não existir e retorna o ID"""
        user_hash = hashlib.md5(username.encode()).hexdigest()[:16]
        
        # Verificar se usuário já existe
        existing = self.executar_query(
            "SELECT id FROM usuarios WHERE username = ? OR user_hash = ?",
            [username, user_hash]
        )
        
        if existing:
            # Atualizar last_login
            self.executar_update(
                "UPDATE usuarios SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                [existing[0]['id']]
            )
            return existing[0]['id']
        
        # Criar novo usuário
        return self.executar_insert(
            "INSERT INTO usuarios (username, user_hash) VALUES (?, ?)",
            [username, user_hash]
        )
    
    def obter_usuario_id(self, username: str) -> Optional[int]:
        """Obtém ID do usuário pelo username"""
        result = self.executar_query(
            "SELECT id FROM usuarios WHERE username = ?",
            [username]
        )
        return result[0]['id'] if result else None
    
    def backup_database(self, backup_path: Optional[str] = None) -> str:
        """Cria backup do banco de dados"""
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"backups/richness_backup_{timestamp}.db"
        
        # Criar diretório de backup
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        
        # Backup usando SQL dump
        with self.get_connection() as source:
            with sqlite3.connect(backup_path) as backup:
                source.backup(backup)
        
        self.logger.info(f"Backup criado: {backup_path}")
        return backup_path
    
    def health_check(self) -> Dict[str, Any]:
        """Verifica saúde do banco de dados"""
        try:
            start_time = time.time()
            
            # Teste de conectividade
            with self.get_connection() as conn:
                conn.execute("SELECT 1").fetchone()
            
            connection_time = time.time() - start_time
            
            # Estatísticas do banco
            stats = self.obter_estatisticas_db()
            
            # Integridade do banco
            integrity_result = self.executar_query("PRAGMA integrity_check")
            is_healthy = integrity_result[0][0] == 'ok' if integrity_result else False
            
            return {
                'status': 'healthy' if is_healthy else 'unhealthy',
                'connection_time_ms': round(connection_time * 1000, 2),
                'database_stats': stats,
                'performance_stats': self._health_stats.copy(),
                'pool_status': {
                    'pool_size': len(self._connection_pool),
                    'max_pool_size': self.pool_size
                },
                'cache_status': {
                    'cache_size': len(self._query_cache),
                    'hit_ratio': self._calculate_cache_hit_ratio()
                }
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _calculate_cache_hit_ratio(self) -> float:
        """Calcula taxa de acerto do cache"""
        hits = self._health_stats['cache_hits']
        misses = self._health_stats['cache_misses']
        total = hits + misses
        return round(hits / total * 100, 2) if total > 0 else 0.0
    
    def obter_estatisticas_db(self) -> Dict[str, Any]:
        """Obtém estatísticas gerais do banco"""
        stats = {}
        
        # Estatísticas por tabela
        tabelas = [
            'usuarios', 'transacoes', 'categorias_personalizadas',
            'descricoes_personalizadas', 'transacoes_excluidas',
            'cache_categorizacao_ia', 'transacoes_manuais', 'system_logs'
        ]
        
        for tabela in tabelas:
            try:
                result = self.executar_query(f"SELECT COUNT(*) as total FROM {tabela}")
                stats[f'total_{tabela}'] = result[0]['total']
            except Exception:
                stats[f'total_{tabela}'] = 0
        
        # Tamanho do banco
        db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
        stats['database_size_mb'] = round(db_size / (1024 * 1024), 2)
        
        return stats
    
    def migrar_schema(self, versao_alvo: int = 2) -> bool:
        """Sistema de migração de esquema"""
        try:
            with self.get_connection() as conn:
                # Verificar versão atual
                try:
                    result = conn.execute("PRAGMA user_version").fetchone()
                    versao_atual = result[0] if result else 0
                except:
                    versao_atual = 0
                
                if versao_atual >= versao_alvo:
                    return True
                
                # Aplicar migrações
                if versao_atual < 1:
                    self._migrar_para_v1(conn)
                
                if versao_atual < 2:
                    self._migrar_para_v2(conn)
                
                # Atualizar versão
                conn.execute(f"PRAGMA user_version = {versao_alvo}")
                self.logger.info(f"Schema migrado para versão {versao_alvo}")
                return True
                
        except Exception as e:
            self.logger.error(f"Erro na migração: {e}")
            return False
    
    def _migrar_para_v1(self, conn):
        """Migração para versão 1"""
        # Adicionar colunas que podem estar faltando
        try:
            conn.execute("ALTER TABLE usuarios ADD COLUMN preferences TEXT")
        except sqlite3.OperationalError:
            pass  # Coluna já existe
    
    def _migrar_para_v2(self, conn):
        """Migração para versão 2"""
        # Adicionar tabela de logs se não existir
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT NOT NULL,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ip_address TEXT,
                    FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE SET NULL
                )
            """)
        except sqlite3.Error:
            pass
    
    def _migrate_database(self):
        """Executa migrações necessárias no banco de dados"""
        with self.get_connection() as conn:
            # Verificar se a coluna profile_pic existe na tabela usuarios
            cursor = conn.execute("PRAGMA table_info(usuarios)")
            columns = [row[1] for row in cursor.fetchall()]
            
            # Adicionar coluna profile_pic se não existir
            if 'profile_pic' not in columns:
                conn.execute("ALTER TABLE usuarios ADD COLUMN profile_pic TEXT")
                self.logger.info("Adicionada coluna profile_pic à tabela usuarios")

    def close_pool(self):
        """Fecha todas as conexões do pool"""
        with self._pool_lock:
            for conn in self._connection_pool:
                conn.close()
            self._connection_pool.clear()
        
        self._executor.shutdown(wait=True)

# Instância global do gerenciador otimizado
db_manager = DatabaseManager()
