"""
Repositories otimizados para acesso a dados seguindo o padrão Repository.
Versão 2.0 com melhorias de performance e funcionalidades avançadas.
"""

from typing import List, Optional, Dict, Tuple, Any
import pandas as pd
from datetime import datetime, timedelta
from .database_manager_v2 import DatabaseManager
import hashlib
import json
from functools import lru_cache
import logging
import bcrypt

class BaseRepository:
    """Classe base para todos os repositories com funcionalidades comuns"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _log_operation(self, operation: str, details: str = ""):
        """Log interno de operações"""
        self.logger.debug(f"{operation}: {details}")

class TransacaoRepository(BaseRepository):
    """Repository para operações com transações"""
    
    @lru_cache(maxsize=1000)
    def gerar_hash_transacao(self, data: str, descricao: str, valor: float) -> str:
        """Gera hash único para identificar transação (com cache)"""
        chave = f"{data}|{descricao}|{valor}"
        return hashlib.md5(chave.encode()).hexdigest()
    
    def criar_ou_atualizar_transacao(self, user_id: int, transacao: Dict[str, Any]) -> int:
        """Cria ou atualiza transação usando UPSERT"""
        hash_transacao = self.gerar_hash_transacao(
            transacao['data'], transacao['descricao'], transacao['valor']
        )
        
        return self.db.executar_insert("""
            INSERT INTO transacoes (
                user_id, hash_transacao, data, descricao, valor, 
                categoria, tipo, origem, conta, arquivo_origem
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, hash_transacao) 
            DO UPDATE SET
                categoria = excluded.categoria,
                updated_at = CURRENT_TIMESTAMP
        """, [
            user_id, hash_transacao, transacao['data'],
            transacao['descricao'], transacao['valor'],
            transacao.get('categoria', 'Outros'),
            'receita' if transacao['valor'] > 0 else 'despesa',
            transacao.get('origem', 'ofx_extrato'),
            transacao.get('conta'),
            transacao.get('arquivo_origem')
        ])
    
    def criar_transacoes_lote(self, user_id: int, transacoes: List[Dict[str, Any]]) -> int:
        """Cria múltiplas transações em lote para performance"""
        queries = []
        for transacao in transacoes:
            hash_transacao = self.gerar_hash_transacao(
                transacao['data'], transacao['descricao'], transacao['valor']
            )
            
            queries.append(("""
                INSERT OR IGNORE INTO transacoes (
                    user_id, hash_transacao, data, descricao, valor, 
                    categoria, tipo, origem, conta, arquivo_origem
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                user_id, hash_transacao, transacao['data'],
                transacao['descricao'], transacao['valor'],
                transacao.get('categoria', 'Outros'),
                'receita' if transacao['valor'] > 0 else 'despesa',
                transacao.get('origem', 'ofx_extrato'),
                transacao.get('conta'),
                transacao.get('arquivo_origem')
            ]))
        
        results = self.db.executar_batch(queries)
        return sum(results)

    def remover_transacoes_por_arquivo(self, user_id: int, arquivo_origem: str) -> int:
        """Remove todas as transações associadas a um arquivo específico"""
        self._log_operation("remover_transacoes_por_arquivo", f"User: {user_id}, Arquivo: {arquivo_origem}")
        query = """
            DELETE FROM transacoes 
            WHERE user_id = ? AND arquivo_origem = ?
        """
        return self.db.executar_update(query, [user_id, arquivo_origem])

    def obter_transacoes_periodo(self, user_id: int, data_inicio: str, 
                                data_fim: str, categorias: Optional[List[str]] = None,
                                incluir_excluidas: bool = False,
                                limite: Optional[int] = None,
                                offset: int = 0) -> pd.DataFrame:
        """Obtém transações com filtros otimizados e paginação"""
        
        # Query base com joins otimizados
        query = """
            SELECT 
                t.id,
                t.hash_transacao,
                t.data,
                t.descricao,
                t.valor,
                t.categoria,
                t.tipo,
                t.origem,
                t.conta,
                t.arquivo_origem,
                dp.descricao as nota,
                t.created_at,
                t.updated_at,
                CASE WHEN te.hash_transacao IS NOT NULL THEN 1 ELSE 0 END as excluida
            FROM transacoes t
            LEFT JOIN descricoes_personalizadas dp 
                ON t.user_id = dp.user_id AND t.hash_transacao = dp.hash_transacao
            LEFT JOIN transacoes_excluidas te 
                ON t.user_id = te.user_id AND t.hash_transacao = te.hash_transacao
            WHERE t.user_id = ? AND t.data BETWEEN ? AND ?
        """
        
        params = [user_id, data_inicio, data_fim]
        
        # Filtrar excluídas se solicitado
        if not incluir_excluidas:
            query += " AND te.hash_transacao IS NULL"
        
        # Filtrar por categorias
        if categorias:
            placeholders = ','.join(['?' for _ in categorias])
            query += f" AND t.categoria IN ({placeholders})"
            params.extend(categorias)
        
        # Ordenar por data mais recente
        query += " ORDER BY t.data DESC, t.id DESC"
        
        # Aplicar limite e paginação se especificados
        if limite:
            query += " LIMIT ? OFFSET ?"
            params.extend([limite, offset])
        
        return self.db.executar_query_df(query, params)

    def atualizar_categorias_lote(self, user_id: int, 
                               mapeamento: Dict[str, str]) -> int:
        """Atualiza categorias em lote"""
        if not mapeamento:
            return 0
            
        queries = []
        for hash_transacao, nova_categoria in mapeamento.items():
            queries.append(("""
                UPDATE transacoes 
                SET categoria = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND hash_transacao = ?
            """, [nova_categoria, user_id, hash_transacao]))
        
        results = self.db.executar_batch(queries)
        return sum(results)
