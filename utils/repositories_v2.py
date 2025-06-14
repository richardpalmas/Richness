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
            INSERT INTO system_logs (tipo, mensagem, dados)
            VALUES (?, ?, ?)
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
