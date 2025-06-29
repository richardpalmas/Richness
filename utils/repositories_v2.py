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

    def atualizar_categoria_transacao(self, user_id: int, 
                                     hash_transacao: str, nova_categoria: str) -> bool:
        """Atualiza categoria de uma transação específica"""
        affected = self.db.executar_update("""
            UPDATE transacoes 
            SET categoria = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND hash_transacao = ?
        """, [nova_categoria, user_id, hash_transacao])
        return affected > 0

    def excluir_transacao(self, user_id: int, hash_transacao: str) -> bool:
        """Marca uma transação como excluída (usando tabela separada)"""
        affected = self.db.executar_update("""
            INSERT OR IGNORE INTO transacoes_excluidas (user_id, hash_transacao, motivo)
            VALUES (?, ?, 'Excluída pelo usuário')
        """, [user_id, hash_transacao])
        return affected > 0

    def excluir_transacoes_lote(self, user_id: int, hashes_transacoes: List[str]) -> int:
        """Exclui múltiplas transações em lote"""
        if not hashes_transacoes:
            return 0
            
        queries = []
        for hash_transacao in hashes_transacoes:
            queries.append(("""
                INSERT OR IGNORE INTO transacoes_excluidas (user_id, hash_transacao, motivo)
                VALUES (?, ?, 'Excluída em lote pelo usuário')
            """, [user_id, hash_transacao]))
        
        results = self.db.executar_batch(queries)
        return sum(results)

    def obter_transacoes_usuario_categorizado(self, user_id: int) -> pd.DataFrame:
        """Obtém transações do usuário que já foram categorizadas"""
        try:
            query = """
                SELECT t.hash_transacao, t.data, t.descricao, t.valor, t.categoria, t.tipo, t.origem
                FROM transacoes t
                LEFT JOIN transacoes_excluidas te ON t.user_id = te.user_id AND t.hash_transacao = te.hash_transacao
                WHERE t.user_id = ? 
                  AND t.categoria IS NOT NULL 
                  AND t.categoria != 'Outros'
                  AND te.hash_transacao IS NULL
                ORDER BY t.data DESC
            """
            
            with self.db.get_connection() as conn:
                df = pd.read_sql_query(query, conn, params=[user_id])
            return df
        except Exception:
            return pd.DataFrame()

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

    def criar_usuario_com_senha(self, username: str, password: str, email: Optional[str] = None, profile_pic: Optional[str] = None) -> int:
        """Cria novo usuário com senha criptografada e foto de perfil opcional"""
        self._log_operation("criar_usuario_com_senha", f"Username: {username}")
        
        # Gerar hash da senha usando bcrypt
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Gerar user_hash único
        user_hash = hashlib.md5(f"{username}_{datetime.now().isoformat()}".encode()).hexdigest()[:16]
        
        return self.db.executar_insert("""
            INSERT INTO usuarios (username, user_hash, password_hash, email, profile_pic) 
            VALUES (?, ?, ?, ?, ?)
        """, [username, user_hash, password_hash, email, profile_pic])
    
    def atualizar_senha(self, user_id: int, nova_senha: str) -> bool:
        """Atualiza senha do usuário com criptografia segura"""
        self._log_operation("atualizar_senha", f"User ID: {user_id}")
        
        # Gerar novo hash da senha
        password_hash = bcrypt.hashpw(nova_senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        affected = self.db.executar_update(
            "UPDATE usuarios SET password_hash = ? WHERE id = ?",
            [password_hash, user_id]
        )
        return affected > 0
    
    def verificar_senha(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Verifica senha e retorna dados do usuário se válida"""
        self._log_operation("verificar_senha", f"Username: {username}")
        
        # Buscar usuário
        user_data = self.obter_usuario_por_username(username)
        if not user_data:
            return None
        
        stored_hash = user_data.get('password_hash')
        if not stored_hash:
            # Usuário não tem senha definida (migração pendente)
            return None
        
        # Verificar senha
        try:
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
                # Atualizar último login
                self.atualizar_ultimo_login(user_data['id'])
                return user_data
        except Exception as e:
            self._log_operation("verificar_senha_error", f"Error: {str(e)}")
        
        return None
    
    def migrar_senha_legado(self, username: str, senha_legado_hash: str) -> bool:
        """Migra hash de senha do sistema legado para bcrypt"""
        self._log_operation("migrar_senha_legado", f"Username: {username}")
        
        user_data = self.obter_usuario_por_username(username)
        if not user_data:
            return False
        
        # Se já tem password_hash, não migrar
        if user_data.get('password_hash'):
            return True
        
        # Para migração, vamos assumir que o hash legado é a senha temporária
        # Em produção real, você precisaria de uma estratégia melhor
        try:
            # Converter hash SHA-256 para bcrypt (estratégia temporária)
            temp_password = senha_legado_hash[:12]  # Usar parte do hash como senha temp
            password_hash = bcrypt.hashpw(temp_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            affected = self.db.executar_update(
                "UPDATE usuarios SET password_hash = ? WHERE id = ?",
                [password_hash, user_data['id']]
            )
            return affected > 0
        except Exception as e:
            self._log_operation("migrar_senha_error", f"Error: {str(e)}")
            return False
    
    def atualizar_profile_pic(self, user_id: int, profile_pic_path: str) -> bool:
        """Atualiza o caminho da foto de perfil do usuário"""
        self._log_operation("atualizar_profile_pic", f"User ID: {user_id}")
        
        affected = self.db.executar_update(
            "UPDATE usuarios SET profile_pic = ? WHERE id = ?",
            [profile_pic_path, user_id]
        )
        return affected > 0

class CategoriaRepository(BaseRepository):
    """Repository para operações com categorias personalizadas"""
    
    def criar_categoria(self, user_id: int, descricao: str, categoria: str) -> int:
        """Cria ou atualiza regra de categorização personalizada"""
        self._log_operation("criar_categoria", f"User: {user_id}, Desc: {descricao}")
        return self.db.executar_insert("""
            INSERT INTO categorias_personalizadas (user_id, descricao, categoria)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, descricao) 
            DO UPDATE SET categoria = excluded.categoria
        """, [user_id, descricao, categoria])
    
    def obter_categorias(self, user_id: int) -> List[Dict[str, Any]]:
        """Obtém todas as regras de categorização do usuário"""
        result = self.db.executar_query(
            "SELECT * FROM categorias_personalizadas WHERE user_id = ?",
            [user_id]
        )
        return [dict(row) for row in result]
    
    def remover_categoria(self, user_id: int, descricao: str) -> bool:
        """Remove uma regra de categorização"""
        affected = self.db.executar_update(
            "DELETE FROM categorias_personalizadas WHERE user_id = ? AND descricao = ?",
            [user_id, descricao]
        )
        return affected > 0

class DescricaoRepository(BaseRepository):
    """Repository para operações com descrições personalizadas"""
    
    def criar_descricao(self, user_id: int, hash_transacao: str, descricao: str) -> int:
        """Cria ou atualiza descrição personalizada"""
        self._log_operation("criar_descricao", f"User: {user_id}, Hash: {hash_transacao}")
        return self.db.executar_insert("""
            INSERT INTO descricoes_personalizadas (user_id, hash_transacao, descricao)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, hash_transacao) 
            DO UPDATE SET descricao = excluded.descricao
        """, [user_id, hash_transacao, descricao])
    
    def obter_descricoes(self, user_id: int) -> List[Dict[str, Any]]:
        """Obtém todas as descrições personalizadas do usuário"""
        result = self.db.executar_query(
            "SELECT * FROM descricoes_personalizadas WHERE user_id = ?",
            [user_id]
        )
        return [dict(row) for row in result]

class ExclusaoRepository(BaseRepository):
    """Repository para operações com transações excluídas"""
    
    def marcar_excluida(self, user_id: int, hash_transacao: str, motivo: Optional[str] = None) -> int:
        """Marca uma transação como excluída"""
        self._log_operation("marcar_excluida", f"User: {user_id}, Hash: {hash_transacao}")
        return self.db.executar_insert("""
            INSERT INTO transacoes_excluidas (user_id, hash_transacao, motivo)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, hash_transacao) DO NOTHING
        """, [user_id, hash_transacao, motivo])
    
    def verificar_excluida(self, user_id: int, hash_transacao: str) -> bool:
        """Verifica se uma transação está marcada como excluída"""
        result = self.db.executar_query(
            "SELECT 1 FROM transacoes_excluidas WHERE user_id = ? AND hash_transacao = ?",
            [user_id, hash_transacao]
        )
        return bool(result)

class CacheIARepository(BaseRepository):
    """Repository para operações com cache de categorização IA"""
    
    def salvar_cache(self, hash_descricao: str, categoria: str, confianca: float) -> int:
        """Salva resultado de categorização no cache"""
        self._log_operation("salvar_cache", f"Hash: {hash_descricao}, Cat: {categoria}")
        return self.db.executar_insert("""
            INSERT INTO cache_categorizacao_ia (hash_descricao, categoria, confianca)
            VALUES (?, ?, ?)
            ON CONFLICT(hash_descricao) 
            DO UPDATE SET 
                categoria = excluded.categoria,
                confianca = excluded.confianca
        """, [hash_descricao, categoria, confianca])
    
    def buscar_cache(self, hash_descricao: str) -> Optional[Dict[str, Any]]:
        """Busca categorização no cache"""
        result = self.db.executar_query(
            "SELECT * FROM cache_categorizacao_ia WHERE hash_descricao = ?",
            [hash_descricao]
        )
        return dict(result[0]) if result else None

class ArquivoOFXRepository(BaseRepository):
    """Repository para operações com arquivos OFX processados"""
    
    def registrar_arquivo(self, user_id: int, nome_arquivo: str, hash_arquivo: str) -> int:
        """Registra arquivo OFX processado"""
        self._log_operation("registrar_arquivo", f"User: {user_id}, Arquivo: {nome_arquivo}")
        return self.db.executar_insert("""
            INSERT INTO arquivos_ofx_processados (user_id, nome_arquivo, hash_arquivo)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, hash_arquivo) DO NOTHING
        """, [user_id, nome_arquivo, hash_arquivo])
    
    def verificar_arquivo(self, user_id: int, hash_arquivo: str) -> bool:
        """Verifica se arquivo já foi processado"""
        result = self.db.executar_query(
            "SELECT 1 FROM arquivos_ofx_processados WHERE user_id = ? AND hash_arquivo = ?",
            [user_id, hash_arquivo]
        )
        return bool(result)

class SystemLogRepository(BaseRepository):
    """Repository para operações com logs do sistema"""
    
    def registrar_log(self, tipo: str, mensagem: str, dados: Optional[Dict[str, Any]] = None) -> int:
        """Registra log do sistema"""
        self._log_operation("registrar_log", f"Tipo: {tipo}")
        return self.db.executar_insert("""
            INSERT INTO system_logs (tipo, mensagem, dados)            VALUES (?, ?, ?)
        """, [tipo, mensagem, json.dumps(dados) if dados else None])
    
    def buscar_logs(self, tipo: Optional[str] = None, limite: int = 100) -> List[Dict[str, Any]]:
        """Busca logs do sistema com filtros"""
        query = "SELECT * FROM system_logs"
        params = []
        
        if tipo:
            query += " WHERE tipo = ?"
            params.append(tipo)
            
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limite)
        
        result = self.db.executar_query(query, params)
        return [dict(row) for row in result]


class CompromissoRepository(BaseRepository):
    """Repository para operações com compromissos (pagamentos futuros)"""
    
    def criar_compromisso(self, user_id: int, descricao: str, valor: float, 
                         data_vencimento: str, categoria: str = "Compromisso", 
                         observacoes: str = "") -> int:
        """Cria um novo compromisso"""
        self._log_operation("criar_compromisso", f"User: {user_id}, Desc: {descricao}")
        
        return self.db.executar_insert("""
            INSERT INTO compromissos (
                user_id, descricao, valor, data_vencimento, categoria, observacoes
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, [user_id, descricao, valor, data_vencimento, categoria, observacoes])
    
    def obter_compromissos(self, user_id: int, status: str = "pendente") -> pd.DataFrame:
        """Obtém compromissos do usuário filtrados por status"""
        query = """
            SELECT id, descricao, valor, data_vencimento, categoria, status, observacoes, created_at
            FROM compromissos
            WHERE user_id = ? AND status = ?
            ORDER BY data_vencimento ASC
        """
        
        result = self.db.executar_query(query, [user_id, status])
        
        if result:
            df = pd.DataFrame([dict(row) for row in result])
            # Converter data_vencimento para datetime
            if 'data_vencimento' in df.columns:
                df['data_vencimento'] = pd.to_datetime(df['data_vencimento'])
            return df
        
        return pd.DataFrame()
    
    def atualizar_status_compromisso(self, user_id: int, compromisso_id: int, 
                                   novo_status: str) -> bool:
        """Atualiza o status de um compromisso"""
        self._log_operation("atualizar_status_compromisso", 
                          f"User: {user_id}, ID: {compromisso_id}, Status: {novo_status}")
        
        rows_affected = self.db.executar_update("""
            UPDATE compromissos 
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
        """, [novo_status, compromisso_id, user_id])
        
        return rows_affected > 0
    
    def excluir_compromisso(self, user_id: int, compromisso_id: int) -> bool:
        """Exclui um compromisso"""
        self._log_operation("excluir_compromisso", f"User: {user_id}, ID: {compromisso_id}")
        
        rows_affected = self.db.executar_update("""
            DELETE FROM compromissos 
            WHERE id = ? AND user_id = ?
        """, [compromisso_id, user_id])
        
        return rows_affected > 0
    
    def obter_compromissos_proximos(self, user_id: int, dias: int = 7) -> pd.DataFrame:
        """Obtém compromissos que vencem nos próximos X dias"""
        from datetime import datetime, timedelta
        
        data_limite = (datetime.now() + timedelta(days=dias)).strftime('%Y-%m-%d')
        
        query = """
            SELECT id, descricao, valor, data_vencimento, categoria, status, observacoes
            FROM compromissos
            WHERE user_id = ? AND status = 'pendente' 
              AND data_vencimento <= ?
            ORDER BY data_vencimento ASC
        """
        
        result = self.db.executar_query(query, [user_id, data_limite])
        
        if result:
            df = pd.DataFrame([dict(row) for row in result])
            if 'data_vencimento' in df.columns:
                df['data_vencimento'] = pd.to_datetime(df['data_vencimento'])
            return df
        
        return pd.DataFrame()

class ConversaIARepository(BaseRepository):
    """Repository para conversas com IA"""
    
    def salvar_conversa(self, user_id: int, pergunta: str, resposta: str, personalidade: str = "clara") -> int:
        """Salva uma conversa com a IA"""
        return self.db.executar_insert("""
            INSERT INTO conversas_ia (user_id, pergunta, resposta, personalidade)
            VALUES (?, ?, ?, ?)
        """, [user_id, pergunta, resposta, personalidade])
    
    def obter_conversas_usuario(self, user_id: int, limite: int = 50) -> pd.DataFrame:
        """Obtém as conversas do usuário ordenadas por data (mais recentes primeiro)"""
        query = """
            SELECT id, pergunta, resposta, personalidade, created_at
            FROM conversas_ia
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """
        
        result = self.db.executar_query(query, [user_id, limite])
        
        if result:
            df = pd.DataFrame([dict(row) for row in result])
            if 'created_at' in df.columns:
                df['created_at'] = pd.to_datetime(df['created_at'])
            return df
        
        return pd.DataFrame()
    
    def obter_conversa_por_id(self, conversa_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Obtém uma conversa específica por ID"""
        query = """
            SELECT id, pergunta, resposta, personalidade, created_at
            FROM conversas_ia
            WHERE id = ? AND user_id = ?
        """
        
        result = self.db.executar_query(query, [conversa_id, user_id])
        
        if result:
            return dict(result[0])
        
        return None
    
    def excluir_conversa(self, conversa_id: int, user_id: int) -> bool:
        """Exclui uma conversa específica"""
        rows_affected = self.db.executar_update("""
            DELETE FROM conversas_ia
            WHERE id = ? AND user_id = ?
        """, [conversa_id, user_id])
        
        return rows_affected > 0
    
    def contar_conversas_usuario(self, user_id: int) -> int:
        """Conta o total de conversas do usuário"""
        query = """
            SELECT COUNT(*) as total
            FROM conversas_ia
            WHERE user_id = ?
        """
        
        result = self.db.executar_query(query, [user_id])
        
        if result:
            return result[0]['total']
        
        return 0
    
    def limpar_conversas_antigas(self, user_id: int, dias: int = 30) -> int:
        """Remove conversas mais antigas que X dias"""
        from datetime import datetime, timedelta
        
        data_limite = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d %H:%M:%S')
        
        rows_affected = self.db.executar_update("""
            DELETE FROM conversas_ia
            WHERE user_id = ? AND created_at < ?
        """, [user_id, data_limite])
        
        return rows_affected

class PersonalidadeIARepository(BaseRepository):
    """Repository para operações com personalidades customizadas de IA do usuário"""
    
    def obter_personalidade(self, user_id: int, nome_perfil: str) -> Optional[Dict[str, Any]]:
        result = self.db.executar_query(
            "SELECT * FROM personalidades_ia_usuario WHERE user_id = ? AND nome_perfil = ?",
            [user_id, nome_perfil]
        )
        return dict(result[0]) if result else None

    def salvar_personalidade_completa(self, user_id: int, nome_perfil: str, dados: dict) -> int:
        # Todos os campos possíveis
        campos = [
            'foto_path', 'idioma', 'amigavel', 'regionalismo', 'cultura', 'formalidade', 'uso_emojis', 'tom', 'foco',
            'arquetipo', 'tom_voz', 'estilo_comunicacao', 'nivel_humor', 'empatia', 'autoridade_conselho',
            'profundidade_expertise', 'perfil_risco', 'motivacao_call', 'valores_centrais', 'reacao_fracasso',
            'prompt_base', 'nome_customizado'
        ]
        colunas = ', '.join(['user_id', 'nome_perfil'] + campos)
        placeholders = ', '.join(['?'] * (2 + len(campos)))
        update_set = ', '.join([f"{campo} = excluded.{campo}" for campo in campos])
        values = [user_id, nome_perfil] + [dados.get(campo) for campo in campos]
        return self.db.executar_insert(
            f"""
            INSERT INTO personalidades_ia_usuario ({colunas})
            VALUES ({placeholders})
            ON CONFLICT(user_id, nome_perfil)
            DO UPDATE SET {update_set}, updated_at = CURRENT_TIMESTAMP
            """,
            values
        )

    def atualizar_personalidade(self, user_id: int, nome_perfil: str, campos: Dict[str, Any]) -> int:
        sets = []
        params = []
        for campo, valor in campos.items():
            sets.append(f"{campo} = ?")
            params.append(valor)
        params.extend([user_id, nome_perfil])
        query = f"UPDATE personalidades_ia_usuario SET {', '.join(sets)}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ? AND nome_perfil = ?"
        return self.db.executar_update(query, params)

    def deletar_personalidade(self, user_id: int, nome_perfil: str) -> int:
        return self.db.executar_update(
            "DELETE FROM personalidades_ia_usuario WHERE user_id = ? AND nome_perfil = ?",
            [user_id, nome_perfil]
        )

    def listar_personalidades_usuario(self, user_id: int) -> list:
        result = self.db.executar_query(
            "SELECT * FROM personalidades_ia_usuario WHERE user_id = ?",
            [user_id]
        )
        return [dict(row) for row in result]

class CacheInsightsRepository(BaseRepository):
    """Repository para operações com cache de insights LLM"""
    
    def salvar_insight_cache(self, user_id: int, insight_type: str, personalidade: str, 
                           data_hash: str, prompt_hash: str, titulo: str, valor: str, 
                           comentario: str, expires_hours: int = 6) -> int:
        """Salva insight no cache com tempo de expiração"""
        from datetime import datetime, timedelta
        
        expires_at = (datetime.now() + timedelta(hours=expires_hours)).isoformat()
        
        self._log_operation("salvar_insight_cache", 
                          f"User: {user_id}, Type: {insight_type}, Personalidade: {personalidade}")
        
        return self.db.executar_insert("""
            INSERT OR REPLACE INTO cache_insights_llm (
                user_id, insight_type, personalidade, data_hash, prompt_hash,
                insight_titulo, insight_valor, insight_comentario, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [user_id, insight_type, personalidade, data_hash, prompt_hash,
              titulo, valor, comentario, expires_at])
    
    def buscar_insight_cache(self, user_id: int, insight_type: str, personalidade: str,
                           data_hash: str, prompt_hash: str) -> Optional[Dict[str, Any]]:
        """Busca insight no cache se ainda válido"""
        from datetime import datetime
        
        result = self.db.executar_query("""
            SELECT * FROM cache_insights_llm 
            WHERE user_id = ? AND insight_type = ? AND personalidade = ? 
            AND data_hash = ? AND prompt_hash = ? 
            AND expires_at > ?
            ORDER BY created_at DESC
            LIMIT 1
        """, [user_id, insight_type, personalidade, data_hash, prompt_hash, 
              datetime.now().isoformat()])
        
        if result:
            # Incrementar contador de uso
            self.db.executar_insert("""
                UPDATE cache_insights_llm 
                SET used_count = used_count + 1 
                WHERE id = ?
            """, [result[0]['id']])
            
            self._log_operation("buscar_insight_cache", f"Cache HIT - Type: {insight_type}")
            return dict(result[0])
        
        self._log_operation("buscar_insight_cache", f"Cache MISS - Type: {insight_type}")
        return None
    
    def limpar_cache_expirado(self, user_id: Optional[int] = None) -> int:
        """Remove insights expirados do cache"""
        from datetime import datetime
        
        if user_id:
            query = """
                DELETE FROM cache_insights_llm 
                WHERE user_id = ? AND expires_at <= ?
            """
            params = [user_id, datetime.now().isoformat()]
        else:
            query = """
                DELETE FROM cache_insights_llm 
                WHERE expires_at <= ?
            """
            params = [datetime.now().isoformat()]
        
        with self.db.get_connection() as conn:
            cursor = conn.execute(query, params)
            rows_deleted = cursor.rowcount
        
        self._log_operation("limpar_cache_expirado", f"Removidos: {rows_deleted} insights")
        return rows_deleted
    
    def obter_estatisticas_cache(self, user_id: int) -> Dict[str, Any]:
        """Obtém estatísticas do cache de insights para o usuário"""
        from datetime import datetime, timedelta
        
        # Cache válido
        cache_valido = self.db.executar_query("""
            SELECT COUNT(*) as count, insight_type
            FROM cache_insights_llm 
            WHERE user_id = ? AND expires_at > ?
            GROUP BY insight_type
        """, [user_id, datetime.now().isoformat()])
        
        # Cache total (incluindo expirado)
        cache_total = self.db.executar_query("""
            SELECT COUNT(*) as count
            FROM cache_insights_llm 
            WHERE user_id = ?
        """, [user_id])
        
        # Mais usados
        mais_usados = self.db.executar_query("""
            SELECT insight_type, personalidade, used_count
            FROM cache_insights_llm 
            WHERE user_id = ? AND expires_at > ?
            ORDER BY used_count DESC
            LIMIT 5
        """, [user_id, datetime.now().isoformat()])
        
        # Cache das últimas 24h
        ontem = (datetime.now() - timedelta(hours=24)).isoformat()
        cache_recente = self.db.executar_query("""
            SELECT COUNT(*) as count
            FROM cache_insights_llm 
            WHERE user_id = ? AND created_at > ?
        """, [user_id, ontem])
        
        return {
            'cache_valido_por_tipo': {row['insight_type']: row['count'] for row in cache_valido},
            'total_cache_entries': cache_total[0]['count'] if cache_total else 0,
            'insights_mais_usados': [dict(row) for row in mais_usados],
            'cache_criado_24h': cache_recente[0]['count'] if cache_recente else 0,
            'ultima_verificacao': datetime.now().isoformat()
        }
    
    def invalidar_cache_usuario(self, user_id: int, insight_type: Optional[str] = None) -> int:
        """Invalida cache específico ou todo cache do usuário"""
        if insight_type:
            query = """
                DELETE FROM cache_insights_llm 
                WHERE user_id = ? AND insight_type = ?
            """
            params = [user_id, insight_type]
            self._log_operation("invalidar_cache_usuario", 
                              f"User: {user_id}, Type: {insight_type}")
        else:
            query = """
                DELETE FROM cache_insights_llm 
                WHERE user_id = ?
            """
            params = [user_id]
            self._log_operation("invalidar_cache_usuario", f"User: {user_id}, ALL types")
        
        with self.db.get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.rowcount

class MetaEconomiaRepository(BaseRepository):
    """Repository para operações com metas de economia"""
    
    def criar_meta(self, user_id: int, nome: str, valor_total: float, 
                   prazo_meses: int, observacoes: str = "") -> int:
        """Cria uma nova meta de economia"""
        valor_mensal = valor_total / prazo_meses
        data_criacao = datetime.now().strftime('%Y-%m-%d')
        data_conclusao_prevista = (datetime.now() + timedelta(days=prazo_meses * 30)).strftime('%Y-%m-%d')
        
        meta_id = self.db.executar_insert("""
            INSERT INTO metas_economia (
                user_id, nome, valor_total, prazo_meses, valor_mensal,
                data_criacao, data_conclusao_prevista, observacoes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            user_id, nome, valor_total, prazo_meses, valor_mensal,
            data_criacao, data_conclusao_prevista, observacoes
        ])
        
        self._log_operation("criar_meta", f"User: {user_id}, Nome: {nome}, Valor: {valor_total}")
        return meta_id
    
    def obter_metas_usuario(self, user_id: int, status: Optional[str] = None) -> pd.DataFrame:
        """Obtém todas as metas de um usuário, opcionalmente filtradas por status"""
        if status:
            query = """
                SELECT id, nome, valor_total, prazo_meses, valor_mensal,
                       valor_economizado, data_criacao, data_conclusao_prevista,
                       observacoes, status, created_at, updated_at
                FROM metas_economia
                WHERE user_id = ? AND status = ?
                ORDER BY data_criacao DESC
            """
            params = [user_id, status]
        else:
            query = """
                SELECT id, nome, valor_total, prazo_meses, valor_mensal,
                       valor_economizado, data_criacao, data_conclusao_prevista,
                       observacoes, status, created_at, updated_at
                FROM metas_economia
                WHERE user_id = ?
                ORDER BY data_criacao DESC
            """
            params = [user_id]
        
        return self.db.executar_query_df(query, params)
    
    def obter_meta_por_id(self, user_id: int, meta_id: int) -> Optional[Dict[str, Any]]:
        """Obtém uma meta específica pelo ID"""
        results = self.db.executar_query("""
            SELECT id, nome, valor_total, prazo_meses, valor_mensal,
                   valor_economizado, data_criacao, data_conclusao_prevista,
                   observacoes, status, created_at, updated_at
            FROM metas_economia
            WHERE user_id = ? AND id = ?
        """, [user_id, meta_id])
        
        return dict(results[0]) if results else None
    
    def atualizar_valor_economizado(self, user_id: int, meta_id: int, valor_adicional: float) -> bool:
        """Adiciona um valor à meta de economia"""
        affected = self.db.executar_update("""
            UPDATE metas_economia 
            SET valor_economizado = valor_economizado + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND id = ?
        """, [valor_adicional, user_id, meta_id])
        
        if affected > 0:
            self._log_operation("atualizar_valor_economizado", f"User: {user_id}, Meta: {meta_id}, Valor: {valor_adicional}")
        
        return affected > 0
    
    def atualizar_status_meta(self, user_id: int, meta_id: int, novo_status: str) -> bool:
        """Atualiza o status de uma meta"""
        affected = self.db.executar_update("""
            UPDATE metas_economia 
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND id = ?
        """, [novo_status, user_id, meta_id])
        
        if affected > 0:
            self._log_operation("atualizar_status_meta", f"User: {user_id}, Meta: {meta_id}, Status: {novo_status}")
        
        return affected > 0
    
    def excluir_meta(self, user_id: int, meta_id: int) -> bool:
        """Exclui uma meta de economia"""
        affected = self.db.executar_update("""
            DELETE FROM metas_economia 
            WHERE user_id = ? AND id = ?
        """, [user_id, meta_id])
        
        if affected > 0:
            self._log_operation("excluir_meta", f"User: {user_id}, Meta: {meta_id}")
        
        return affected > 0
    
    def obter_resumo_metas(self, user_id: int) -> Dict[str, Any]:
        """Obtém resumo estatístico das metas do usuário"""
        results = self.db.executar_query("""
            SELECT 
                COUNT(*) as total_metas,
                COUNT(CASE WHEN status = 'ativa' THEN 1 END) as metas_ativas,
                COUNT(CASE WHEN status = 'concluida' THEN 1 END) as metas_concluidas,
                COALESCE(SUM(CASE WHEN status = 'ativa' THEN valor_total ELSE 0 END), 0) as valor_total_ativo,
                COALESCE(SUM(CASE WHEN status = 'ativa' THEN valor_mensal ELSE 0 END), 0) as economia_mensal_necessaria,
                COALESCE(SUM(CASE WHEN status = 'ativa' THEN valor_economizado ELSE 0 END), 0) as valor_ja_economizado
            FROM metas_economia
            WHERE user_id = ?
        """, [user_id])
        
        if results:
            resumo = dict(results[0])
            # Calcular progresso médio
            if resumo['valor_total_ativo'] > 0:
                resumo['progresso_medio'] = (resumo['valor_ja_economizado'] / resumo['valor_total_ativo']) * 100
            else:
                resumo['progresso_medio'] = 0
            
            return resumo
        
        return {
            'total_metas': 0,
            'metas_ativas': 0, 
            'metas_concluidas': 0,
            'valor_total_ativo': 0,
            'economia_mensal_necessaria': 0,
            'valor_ja_economizado': 0,
            'progresso_medio': 0
        }
    
    def obter_metas_proximas_vencimento(self, user_id: int, dias: int = 30) -> pd.DataFrame:
        """Obtém metas que estão próximas do vencimento"""
        data_limite = (datetime.now() + timedelta(days=dias)).strftime('%Y-%m-%d')
        
        return self.db.executar_query_df("""
            SELECT id, nome, valor_total, valor_economizado,
                   data_conclusao_prevista, 
                   (julianday(data_conclusao_prevista) - julianday('now')) as dias_restantes,
                   ((valor_economizado / valor_total) * 100) as progresso_percentual
            FROM metas_economia
            WHERE user_id = ? AND status = 'ativa' 
            AND data_conclusao_prevista <= ?
            ORDER BY data_conclusao_prevista ASC
        """, [user_id, data_limite])
