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

class BaseRepository:
    """Classe base para todos os repositories com funcionalidades comuns"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _log_operation(self, operation: str, details: str = ""):
        """Log interno de operações"""
        self.logger.debug(f"{operation}: {details}")

class UsuarioRepository(BaseRepository):
    """Repository para operações com usuários"""
    
    def criar_usuario(self, username: str, email: Optional[str] = None) -> int:
        """Cria novo usuário"""
        self._log_operation("criar_usuario", f"Username: {username}")
        return self.db.criar_usuario_se_nao_existe(username)
    
    def obter_usuario_por_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Obtém dados completos do usuário"""
        result = self.db.executar_query(
            "SELECT * FROM usuarios WHERE id = ?",
            [user_id]
        )
        return dict(result[0]) if result else None
    
    def obter_usuario_por_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Obtém usuário pelo username"""
        result = self.db.executar_query(
            "SELECT * FROM usuarios WHERE username = ?",
            [username]
        )
        return dict(result[0]) if result else None
    
    def atualizar_preferencias(self, user_id: int, preferencias: Dict[str, Any]) -> bool:
        """Atualiza preferências do usuário"""
        affected = self.db.executar_update(
            "UPDATE usuarios SET preferences = ? WHERE id = ?",
            [json.dumps(preferencias), user_id]
        )
        return affected > 0
    
    def obter_preferencias(self, user_id: int) -> Dict[str, Any]:
        """Obtém preferências do usuário"""
        result = self.db.executar_query(
            "SELECT preferences FROM usuarios WHERE id = ?",
            [user_id]
        )
        if result and result[0]['preferences']:
            try:
                return json.loads(result[0]['preferences'])
            except:
                return {}
        return {}
    
    def obter_estatisticas_usuario(self, user_id: int) -> Dict[str, Any]:
        """Obtém estatísticas completas do usuário"""
        return self.db.executar_query_df("""
            SELECT 
                COUNT(DISTINCT t.id) as total_transacoes,
                COUNT(DISTINCT cp.id) as categorias_personalizadas,
                COUNT(DISTINCT dp.id) as descricoes_personalizadas,
                COUNT(DISTINCT te.id) as transacoes_excluidas,
                COUNT(DISTINCT tm.id) as transacoes_manuais,
                SUM(CASE WHEN t.valor > 0 THEN t.valor ELSE 0 END) as receitas_totais,
                SUM(CASE WHEN t.valor < 0 THEN ABS(t.valor) ELSE 0 END) as despesas_totais,
                MAX(t.data) as ultima_transacao,
                MIN(t.data) as primeira_transacao
            FROM usuarios u
            LEFT JOIN transacoes t ON u.id = t.user_id
            LEFT JOIN categorias_personalizadas cp ON u.id = cp.user_id AND cp.is_active = 1
            LEFT JOIN descricoes_personalizadas dp ON u.id = dp.user_id
            LEFT JOIN transacoes_excluidas te ON u.id = te.user_id
            LEFT JOIN transacoes_manuais tm ON u.id = tm.user_id
            WHERE u.id = ?        """, [user_id]).iloc[0].to_dict()
    
    def atualizar_ultimo_login(self, user_id: int) -> bool:
        """Atualiza timestamp do último login"""
        affected = self.db.executar_update(
            "UPDATE usuarios SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
            [user_id]
        )
        return affected > 0
    
    def buscar_todos(self) -> List[Dict[str, Any]]:
        """Lista todos os usuários do sistema"""
        result = self.db.executar_query("SELECT * FROM usuarios ORDER BY username", [])
        return [dict(row) for row in result]
        result = self.db.executar_query("SELECT * FROM usuarios ORDER BY username", [])
        return [dict(row) for row in result]

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
        
        # Filtrar por categorias se especificado
        if categorias:
            placeholders = ','.join(['?'] * len(categorias))
            query += f" AND t.categoria IN ({placeholders})"
            params.extend(categorias)
        
        query += " ORDER BY t.data DESC, t.id DESC"
        
        # Paginação
        if limite:
            query += f" LIMIT {limite} OFFSET {offset}"
        
        return self.db.executar_query_df(query, params)
    
    def obter_transacoes_sem_categoria(self, user_id: int, limite: int = 50) -> pd.DataFrame:
        """Obtém transações que ainda não foram categorizadas"""
        return self.db.executar_query_df("""
            SELECT t.id, t.hash_transacao, t.descricao, t.valor, t.categoria, t.data
            FROM transacoes t
            LEFT JOIN transacoes_excluidas te 
                ON t.user_id = te.user_id AND t.hash_transacao = te.hash_transacao
            WHERE t.user_id = ? 
                AND t.categoria = 'Outros'
                AND te.hash_transacao IS NULL
            ORDER BY t.data DESC
            LIMIT ?
        """, [user_id, limite])
    
    def obter_estatisticas_categoria(self, user_id: int, periodo_meses: int = 12) -> pd.DataFrame:
        """Estatísticas agregadas por categoria com cache"""
        return self.db.executar_query_df("""
            SELECT 
                t.categoria,
                COUNT(*) as total_transacoes,
                SUM(CASE WHEN t.valor > 0 THEN t.valor ELSE 0 END) as total_receitas,
                SUM(CASE WHEN t.valor < 0 THEN ABS(t.valor) ELSE 0 END) as total_despesas,
                AVG(CASE WHEN t.valor < 0 THEN ABS(t.valor) END) as media_despesas,
                MIN(t.data) as primeira_transacao,
                MAX(t.data) as ultima_transacao
            FROM transacoes t
            LEFT JOIN transacoes_excluidas te 
                ON t.user_id = te.user_id AND t.hash_transacao = te.hash_transacao
            WHERE t.user_id = ? 
                AND t.data >= date('now', '-{} months')
                AND te.hash_transacao IS NULL
            GROUP BY t.categoria
            ORDER BY total_despesas DESC, total_receitas DESC
        """.format(periodo_meses), [user_id])
    
    def obter_evolucao_mensal(self, user_id: int, meses: int = 12) -> pd.DataFrame:
        """Evolução de receitas e despesas por mês"""
        return self.db.executar_query_df("""
            SELECT 
                strftime('%Y-%m', t.data) as mes,
                SUM(CASE WHEN t.valor > 0 THEN t.valor ELSE 0 END) as receitas,
                SUM(CASE WHEN t.valor < 0 THEN ABS(t.valor) ELSE 0 END) as despesas,
                SUM(t.valor) as saldo_mensal,
                COUNT(*) as total_transacoes,
                COUNT(DISTINCT t.categoria) as categorias_distintas
            FROM transacoes t
            LEFT JOIN transacoes_excluidas te 
                ON t.user_id = te.user_id AND t.hash_transacao = te.hash_transacao
            WHERE t.user_id = ? 
                AND t.data >= date('now', '-{} months')
                AND te.hash_transacao IS NULL
            GROUP BY strftime('%Y-%m', t.data)
            ORDER BY mes
        """.format(meses), [user_id])
    
    def obter_tendencias_categoria(self, user_id: int, categoria: str, meses: int = 6) -> pd.DataFrame:
        """Análise de tendências para uma categoria específica"""
        return self.db.executar_query_df("""
            SELECT 
                strftime('%Y-%m', t.data) as mes,
                COUNT(*) as transacoes,
                SUM(ABS(t.valor)) as total_valor,
                AVG(ABS(t.valor)) as valor_medio,
                MIN(ABS(t.valor)) as valor_minimo,
                MAX(ABS(t.valor)) as valor_maximo
            FROM transacoes t
            LEFT JOIN transacoes_excluidas te 
                ON t.user_id = te.user_id AND t.hash_transacao = te.hash_transacao
            WHERE t.user_id = ? 
                AND t.categoria = ?
                AND t.data >= date('now', '-{} months')
                AND te.hash_transacao IS NULL
            GROUP BY strftime('%Y-%m', t.data)
            ORDER BY mes
        """.format(meses), [user_id, categoria])
    
    def atualizar_categoria_lote(self, user_id: int, mapeamento_categorias: Dict[str, str]) -> int:
        """Atualiza categorias em lote baseado em mapeamento hash->categoria"""
        if not mapeamento_categorias:
            return 0
        
        queries = []
        for hash_transacao, nova_categoria in mapeamento_categorias.items():
            queries.append(("""
                UPDATE transacoes 
                SET categoria = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND hash_transacao = ?
            """, [nova_categoria, user_id, hash_transacao]))
        
        results = self.db.executar_batch(queries)
        return sum(results)
    
    def obter_duplicatas_potenciais(self, user_id: int, similaridade_threshold: float = 0.8) -> pd.DataFrame:
        """Identifica possíveis transações duplicadas"""
        return self.db.executar_query_df("""
            SELECT 
                t1.id as id1,
                t2.id as id2,
                t1.data,
                t1.descricao,
                t1.valor,
                ABS(julianday(t1.data) - julianday(t2.data)) as dias_diferenca
            FROM transacoes t1
            JOIN transacoes t2 ON t1.user_id = t2.user_id 
                AND t1.id < t2.id
                AND ABS(t1.valor - t2.valor) < 0.01
                AND ABS(julianday(t1.data) - julianday(t2.data)) <= 3
            WHERE t1.user_id = ?
            ORDER BY t1.data DESC
        """, [user_id])

class CategoriaRepository(BaseRepository):
    """Repository para operações com categorias"""
    
    @lru_cache(maxsize=1)
    def obter_categorias_padrao(self) -> List[str]:
        """Obtém lista de categorias padrão do sistema (cached)"""
        return [
            "Alimentação", "Transporte", "Saúde", "Educação", "Lazer",
            "Casa e Utilidades", "Vestuário", "Investimentos", 
            "Transferências", "Salário", "Freelance", "Bancos e Taxas",
            "Compras Online", "Supermercado", "Restaurantes", "Combustível",
            "Internet", "Telefone", "Academia", "Farmácia", "Streaming",
            "Beleza", "Pets", "Seguros", "Impostos", "Outros"
        ]
    
    def obter_todas_categorias(self, user_id: int) -> List[str]:
        """Obtém categorias padrão + personalizadas do usuário"""
        categorias_padrao = self.obter_categorias_padrao()
        
        personalizadas = self.db.executar_query("""
            SELECT nome FROM categorias_personalizadas 
            WHERE user_id = ? AND is_active = 1
            ORDER BY nome
        """, [user_id])
        
        categorias_personalizadas = [cat['nome'] for cat in personalizadas]
        return sorted(list(set(categorias_padrao + categorias_personalizadas)))
    
    def criar_categoria_personalizada(self, user_id: int, nome: str, 
                                    cor: Optional[str] = None, icone: Optional[str] = None) -> int:
        """Cria nova categoria personalizada"""
        return self.db.executar_insert("""
            INSERT INTO categorias_personalizadas (user_id, nome, cor, icone)
            VALUES (?, ?, ?, ?)
        """, [user_id, nome, cor or '#6c757d', icone or '🏷️'])
    
    def remover_categoria_personalizada(self, user_id: int, nome: str) -> bool:
        """Remove categoria personalizada (soft delete)"""
        affected = self.db.executar_update("""
            UPDATE categorias_personalizadas 
            SET is_active = 0
            WHERE user_id = ? AND nome = ?
        """, [user_id, nome])
        return affected > 0
    
    def obter_categorias_personalizadas(self, user_id: int) -> List[Dict[str, Any]]:
        """Obtém todas as categorias personalizadas do usuário"""
        result = self.db.executar_query("""
            SELECT id, nome, cor, icone, created_at
            FROM categorias_personalizadas
            WHERE user_id = ? AND is_active = 1
            ORDER BY nome
        """, [user_id])
        
        return [dict(row) for row in result]
    
    def obter_estatisticas_uso_categorias(self, user_id: int) -> pd.DataFrame:
        """Estatísticas de uso das categorias"""
        return self.db.executar_query_df("""
            SELECT 
                t.categoria,
                COUNT(*) as uso_total,
                AVG(ABS(t.valor)) as valor_medio,
                MAX(t.data) as ultimo_uso,
                cp.cor,
                cp.icone
            FROM transacoes t
            LEFT JOIN categorias_personalizadas cp 
                ON t.user_id = cp.user_id AND t.categoria = cp.nome AND cp.is_active = 1
            LEFT JOIN transacoes_excluidas te 
                ON t.user_id = te.user_id AND t.hash_transacao = te.hash_transacao
            WHERE t.user_id = ? AND te.hash_transacao IS NULL
            GROUP BY t.categoria
            ORDER BY uso_total DESC
        """, [user_id])

class DescricaoRepository(BaseRepository):
    """Repository para descrições personalizadas"""
    
    def salvar_descricao(self, user_id: int, hash_transacao: str, descricao: str) -> int:
        """Salva ou atualiza descrição personalizada"""
        return self.db.executar_insert("""
            INSERT INTO descricoes_personalizadas (user_id, hash_transacao, descricao)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, hash_transacao)
            DO UPDATE SET 
                descricao = excluded.descricao,
                updated_at = CURRENT_TIMESTAMP
        """, [user_id, hash_transacao, descricao])
    
    def salvar_descricoes_lote(self, user_id: int, mapeamento: Dict[str, str]) -> int:
        """Salva múltiplas descrições em lote"""
        if not mapeamento:
            return 0
            
        queries = []
        for hash_transacao, descricao in mapeamento.items():
            queries.append(("""
                INSERT OR REPLACE INTO descricoes_personalizadas (user_id, hash_transacao, descricao)
                VALUES (?, ?, ?)
            """, [user_id, hash_transacao, descricao]))
        
        results = self.db.executar_batch(queries)
        return sum(results)
    
    def obter_descricao(self, user_id: int, hash_transacao: str) -> Optional[str]:
        """Obtém descrição personalizada"""
        result = self.db.executar_query("""
            SELECT descricao FROM descricoes_personalizadas
            WHERE user_id = ? AND hash_transacao = ?
        """, [user_id, hash_transacao])
        
        return result[0]['descricao'] if result else None
    
    def obter_todas_descricoes(self, user_id: int) -> Dict[str, str]:
        """Obtém todas as descrições do usuário"""
        result = self.db.executar_query("""
            SELECT hash_transacao, descricao
            FROM descricoes_personalizadas
            WHERE user_id = ?
        """, [user_id])
        
        return {row['hash_transacao']: row['descricao'] for row in result}
    
    def remover_descricao(self, user_id: int, hash_transacao: str) -> bool:
        """Remove descrição personalizada"""
        affected = self.db.executar_update("""
            DELETE FROM descricoes_personalizadas
            WHERE user_id = ? AND hash_transacao = ?
        """, [user_id, hash_transacao])
        return affected > 0

class ExclusaoRepository(BaseRepository):
    """Repository para transações excluídas"""
    
    def excluir_transacao(self, user_id: int, hash_transacao: str, motivo: Optional[str] = None) -> int:
        """Exclui transação (soft delete)"""
        return self.db.executar_insert("""
            INSERT INTO transacoes_excluidas (user_id, hash_transacao, motivo)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, hash_transacao) DO NOTHING
        """, [user_id, hash_transacao, motivo])
    
    def excluir_transacoes_lote(self, user_id: int, hashes: List[str], motivo: Optional[str] = None) -> int:
        """Exclui múltiplas transações em lote"""
        if not hashes:
            return 0
            
        queries = []
        for hash_transacao in hashes:
            queries.append(("""
                INSERT OR IGNORE INTO transacoes_excluidas (user_id, hash_transacao, motivo)
                VALUES (?, ?, ?)
            """, [user_id, hash_transacao, motivo]))
        
        results = self.db.executar_batch(queries)
        return sum(results)
    
    def restaurar_transacao(self, user_id: int, hash_transacao: str) -> bool:
        """Restaura transação excluída"""
        affected = self.db.executar_update("""
            DELETE FROM transacoes_excluidas
            WHERE user_id = ? AND hash_transacao = ?
        """, [user_id, hash_transacao])
        return affected > 0
    
    def obter_transacoes_excluidas(self, user_id: int) -> List[str]:
        """Obtém lista de hashes das transações excluídas"""
        result = self.db.executar_query("""
            SELECT hash_transacao FROM transacoes_excluidas
            WHERE user_id = ?
        """, [user_id])
        
        return [row['hash_transacao'] for row in result]
    
    def obter_historico_exclusoes(self, user_id: int) -> pd.DataFrame:
        """Obtém histórico completo de exclusões"""
        return self.db.executar_query_df("""
            SELECT 
                te.hash_transacao,
                te.motivo,
                te.excluded_at,
                t.data,
                t.descricao,
                t.valor,
                t.categoria
            FROM transacoes_excluidas te
            LEFT JOIN transacoes t 
                ON te.user_id = t.user_id AND te.hash_transacao = t.hash_transacao
            WHERE te.user_id = ?
            ORDER BY te.excluded_at DESC
        """, [user_id])

class CacheIARepository(BaseRepository):
    """Repository para cache de categorização por IA"""
    
    def salvar_sugestao_ia(self, user_id: int, descricao: str, categoria: str, 
                          confianca: float = 0.0, modelo: str = 'gpt-4o-mini') -> int:
        """Salva sugestão de categoria da IA"""
        descricao_hash = hashlib.md5(descricao.lower().strip().encode()).hexdigest()
        
        return self.db.executar_insert("""
            INSERT INTO cache_categorizacao_ia 
            (user_id, descricao_hash, descricao_original, categoria_sugerida, confianca, modelo_usado)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, descricao_hash)
            DO UPDATE SET 
                categoria_sugerida = excluded.categoria_sugerida,
                confianca = excluded.confianca,
                modelo_usado = excluded.modelo_usado
        """, [user_id, descricao_hash, descricao, categoria, confianca, modelo])
    
    def salvar_sugestoes_lote(self, user_id: int, sugestoes: List[Dict[str, Any]]) -> int:
        """Salva múltiplas sugestões em lote"""
        if not sugestoes:
            return 0
            
        queries = []
        for sugestao in sugestoes:
            descricao_hash = hashlib.md5(sugestao['descricao'].lower().strip().encode()).hexdigest()
            queries.append(("""
                INSERT OR REPLACE INTO cache_categorizacao_ia 
                (user_id, descricao_hash, descricao_original, categoria_sugerida, confianca, modelo_usado)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [
                user_id, descricao_hash, sugestao['descricao'],
                sugestao['categoria'], sugestao.get('confianca', 0.0),
                sugestao.get('modelo', 'gpt-4o-mini')
            ]))
        
        results = self.db.executar_batch(queries)
        return sum(results)
    
    def obter_sugestao_cache(self, user_id: int, descricao: str) -> Optional[Dict[str, Any]]:
        """Obtém sugestão do cache se existir"""
        descricao_hash = hashlib.md5(descricao.lower().strip().encode()).hexdigest()
        
        result = self.db.executar_query("""
            SELECT categoria_sugerida, confianca, aprovada, used_count, modelo_usado
            FROM cache_categorizacao_ia
            WHERE user_id = ? AND descricao_hash = ?
        """, [user_id, descricao_hash])
        
        return dict(result[0]) if result else None
    
    def aprovar_sugestao(self, user_id: int, descricao: str) -> bool:
        """Marca sugestão como aprovada"""
        descricao_hash = hashlib.md5(descricao.lower().strip().encode()).hexdigest()
        
        affected = self.db.executar_update("""
            UPDATE cache_categorizacao_ia 
            SET aprovada = 1
            WHERE user_id = ? AND descricao_hash = ?
        """, [user_id, descricao_hash])
        return affected > 0
    
    def obter_estatisticas_ia(self, user_id: int) -> Dict[str, Any]:
        """Obtém estatísticas do uso da IA"""
        result = self.db.executar_query_df("""
            SELECT 
                COUNT(*) as total_sugestoes,
                SUM(CASE WHEN aprovada = 1 THEN 1 ELSE 0 END) as aprovadas,
                AVG(confianca) as confianca_media,
                SUM(used_count) as total_usos,
                COUNT(DISTINCT modelo_usado) as modelos_diferentes,
                MAX(created_at) as ultima_sugestao
            FROM cache_categorizacao_ia
            WHERE user_id = ?
        """, [user_id])
        
        return result.iloc[0].to_dict() if not result.empty else {}
    
    def obter_sugestoes_por_confianca(self, user_id: int, min_confianca: float = 0.7) -> pd.DataFrame:
        """Obtém sugestões com alta confiança para aplicação automática"""
        return self.db.executar_query_df("""
            SELECT 
                descricao_original,
                categoria_sugerida,
                confianca,
                aprovada,
                used_count
            FROM cache_categorizacao_ia
            WHERE user_id = ? 
                AND confianca >= ?
                AND aprovada = 0
            ORDER BY confianca DESC, used_count DESC
        """, [user_id, min_confianca])

class ArquivoOFXRepository(BaseRepository):
    """Repository para controle de arquivos OFX processados"""
    
    def marcar_arquivo_processado(self, user_id: int, nome_arquivo: str, 
                                 hash_arquivo: str, tipo: str, total_transacoes: int = 0) -> int:
        """Marca arquivo como processado"""
        return self.db.executar_insert("""
            INSERT INTO arquivos_ofx_processados 
            (user_id, nome_arquivo, hash_arquivo, tipo, total_transacoes)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, hash_arquivo) DO NOTHING
        """, [user_id, nome_arquivo, hash_arquivo, tipo, total_transacoes])
    
    def arquivo_ja_processado(self, user_id: int, hash_arquivo: str) -> bool:
        """Verifica se arquivo já foi processado"""
        result = self.db.executar_query("""
            SELECT 1 FROM arquivos_ofx_processados
            WHERE user_id = ? AND hash_arquivo = ?
        """, [user_id, hash_arquivo])
        
        return len(result) > 0
    
    def obter_historico_arquivos(self, user_id: int) -> pd.DataFrame:
        """Obtém histórico de arquivos processados"""
        return self.db.executar_query_df("""
            SELECT 
                nome_arquivo,
                tipo,
                data_processamento,
                total_transacoes
            FROM arquivos_ofx_processados
            WHERE user_id = ?
            ORDER BY data_processamento DESC
        """, [user_id])

class SystemLogRepository(BaseRepository):
    """Repository para logs do sistema"""
    
    def log_action(self, user_id: Optional[int], action: str, details: Optional[str] = None, 
                  ip_address: Optional[str] = None) -> int:
        """Registra ação no log do sistema"""
        return self.db.executar_insert("""
            INSERT INTO system_logs (user_id, action, details, ip_address)
            VALUES (?, ?, ?, ?)
        """, [user_id, action, details, ip_address])
    
    def obter_logs_usuario(self, user_id: int, limite: int = 100) -> pd.DataFrame:
        """Obtém logs de um usuário específico"""
        return self.db.executar_query_df("""
            SELECT action, details, timestamp, ip_address
            FROM system_logs
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, [user_id, limite])
    
    def obter_logs_sistema(self, limite: int = 500) -> pd.DataFrame:
        """Obtém logs gerais do sistema"""
        return self.db.executar_query_df("""
            SELECT u.username, sl.action, sl.details, sl.timestamp, sl.ip_address
            FROM system_logs sl
            LEFT JOIN usuarios u ON sl.user_id = u.id
            ORDER BY sl.timestamp DESC
            LIMIT ?
        """, [limite])


class RepositoryManager:
    """Gerenciador centralizado de todos os repositories"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self._repositories = {}
        
        # Inicializar todos os repositories
        self._init_repositories()
    
    def _init_repositories(self):
        """Inicializa todos os repositories disponíveis"""
        self._repositories = {
            'usuarios': UsuarioRepository(self.db_manager),
            'transacoes': TransacaoRepository(self.db_manager),
            'categorias': CategoriaRepository(self.db_manager),
            'descricoes': DescricaoRepository(self.db_manager),
            'exclusoes': ExclusaoRepository(self.db_manager),
            'cache_ia': CacheIARepository(self.db_manager),
            'arquivos_ofx': ArquivoOFXRepository(self.db_manager),
            'system_logs': SystemLogRepository(self.db_manager)
        }
    
    def get_repository(self, nome: str):
        """Obtém um repository específico"""
        if nome not in self._repositories:
            raise ValueError(f"Repository '{nome}' não encontrado")
        return self._repositories[nome]
    
    def listar_repositories(self) -> list:
        """Lista todos os repositories disponíveis"""
        return list(self._repositories.keys())
    
    def health_check(self) -> dict:
        """Verifica a saúde de todos os repositories"""
        status = {'healthy': True, 'repositories': {}}
        
        for nome, repo in self._repositories.items():
            try:
                # Teste básico - tentar acessar o banco
                repo.db.executar_query("SELECT 1", [])
                status['repositories'][nome] = {'status': 'healthy'}
            except Exception as e:
                status['repositories'][nome] = {'status': 'error', 'error': str(e)}
                status['healthy'] = False
        
        return status
