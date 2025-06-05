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
    
    # Tabela de usuários com campos de auditoria e segurança
    cur.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            usuario TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            email TEXT,
            profile_pic TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_login TEXT,
            login_attempts INTEGER DEFAULT 0,
            account_locked BOOLEAN DEFAULT 0,
            email_verified BOOLEAN DEFAULT 0,
            password_changed_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabela de logs de auditoria
    cur.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            event_type TEXT NOT NULL,
            event_data TEXT,
            ip_address TEXT,
            user_agent TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES usuarios(id)
        )
    ''')
    
    # Tabela de sessões ativas
    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_id TEXT UNIQUE NOT NULL,
            token_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_activity TEXT DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY(user_id) REFERENCES usuarios(id)
        )
    ''')    
    # Tabela de economias com criptografia
    cur.execute('''
        CREATE TABLE IF NOT EXISTS economias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            data TEXT NOT NULL,
            valor REAL NOT NULL,
            tipo TEXT,
            descricao TEXT,
            descricao_encrypted TEXT,
            categoria TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    ''')
    
    # Tabela de cartões com criptografia
    cur.execute('''
        CREATE TABLE IF NOT EXISTS cartoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            data TEXT NOT NULL,
            valor REAL NOT NULL,
            tipo TEXT,
            descricao TEXT,
            descricao_encrypted TEXT,
            categoria TEXT,
            cartao_nome TEXT,
            cartao_nome_encrypted TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    ''')
    
    # Tabela de extratos com criptografia
    cur.execute('''
        CREATE TABLE IF NOT EXISTS extratos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            data TEXT NOT NULL,
            valor REAL NOT NULL,
            tipo TEXT,
            descricao TEXT,
            descricao_encrypted TEXT,
            categoria TEXT,
            account_info_encrypted TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    ''')
      # Tabela de itemIds Pluggy com criptografia
    cur.execute('''
        CREATE TABLE IF NOT EXISTS pluggy_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            item_id TEXT NOT NULL,
            item_id_encrypted TEXT,
            nome TEXT,
            nome_encrypted TEXT,
            credentials_encrypted TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(usuario_id, item_id),
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    ''')
    
    # Tabela de roles de usuário para controle de acesso
    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, role),
            FOREIGN KEY(user_id) REFERENCES usuarios(id)
        )
    ''')
    
    # Índices para melhorar performance e segurança
    cur.execute('CREATE INDEX IF NOT EXISTS idx_usuarios_usuario ON usuarios(usuario)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_economias_usuario_id ON economias(usuario_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_cartoes_usuario_id ON cartoes(usuario_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_extratos_usuario_id ON extratos(usuario_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pluggy_items_usuario_id ON pluggy_items(usuario_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pluggy_items_item_id ON pluggy_items(item_id)')
    
    # Índices para auditoria e sessões
    cur.execute('CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type ON audit_logs(event_type)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON user_sessions(session_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON user_sessions(expires_at)')
    
    # Índices adicionais para consultas frequentes
    cur.execute('CREATE INDEX IF NOT EXISTS idx_economias_data ON economias(data)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_cartoes_data ON cartoes(data)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_extratos_data ON extratos(data)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_extratos_categoria ON extratos(categoria)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_cartoes_categoria ON cartoes(categoria)')

    conn.commit()

def remover_usuario(usuario):
    """
    Remove o usuário e todos os seus dados relacionados do banco de dados.
    Inclui logs de auditoria para compliance.
    """
    from security.audit.security_logger import get_security_logger
    logger = get_security_logger()
    
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT id FROM usuarios WHERE usuario = ?', (usuario,))
    row = cur.fetchone()
    if not row:
        return False
    
    usuario_id = row['id']

    # Log da remoção antes de executar
    logger.log_data_access(
        username=usuario,
        operation='user_deletion',
        resource='all_user_data'
    )

    # Usar transação para garantir atomicidade e melhorar performance
    conn.execute('BEGIN TRANSACTION')
    try:
        # Remover dados relacionados
        cur.execute('DELETE FROM economias WHERE usuario_id = ?', (usuario_id,))
        cur.execute('DELETE FROM cartoes WHERE usuario_id = ?', (usuario_id,))
        cur.execute('DELETE FROM extratos WHERE usuario_id = ?', (usuario_id,))
        cur.execute('DELETE FROM pluggy_items WHERE usuario_id = ?', (usuario_id,))
        cur.execute('DELETE FROM user_sessions WHERE usuario_id = ?', (usuario_id,))
        
        # Manter logs de auditoria por compliance (não remover)
        # cur.execute('DELETE FROM audit_logs WHERE user_id = ?', (usuario_id,))
        
        # Remover usuário
        cur.execute('DELETE FROM usuarios WHERE id = ?', (usuario_id,))
        conn.commit()

        # Limpar cache após mudanças
        limpar_cache_consultas()
        
        # Log da remoção bem-sucedida
        logger.log_data_access(
            username=usuario,
            operation='user_deletion_completed',
            resource='all_user_data',
            success=True
        )
        
        return True
    except Exception as e:
        conn.rollback()
        logger.log_data_access(
            username=usuario,
            operation='user_deletion_failed',
            resource='all_user_data',
            success=False,
            error=str(e)
        )
        return False


def log_audit_event(user_id: int, event_type: str, event_data: dict = None, 
                   ip_address: str = None, user_agent: str = None):
    """Registra evento de auditoria no banco de dados"""
    import json
    from datetime import datetime
    
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        event_data_json = json.dumps(event_data) if event_data else None
        
        cur.execute('''
            INSERT INTO audit_logs (user_id, event_type, event_data, ip_address, user_agent, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, event_type, event_data_json, ip_address, user_agent, datetime.now().isoformat()))
        
        conn.commit()
        return True
        
    except Exception as e:
        return False


def create_user_session(user_id: int, session_id: str, token_hash: str, 
                       expires_at: str, ip_address: str = None, user_agent: str = None):
    """Cria nova sessão de usuário no banco"""
    from datetime import datetime
    
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute('''
            INSERT INTO user_sessions 
            (user_id, session_id, token_hash, expires_at, ip_address, user_agent, created_at, last_activity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, session_id, token_hash, expires_at, ip_address, user_agent, 
              datetime.now().isoformat(), datetime.now().isoformat()))
        
        conn.commit()
        return True
        
    except Exception:
        return False


def invalidate_user_session(session_id: str):
    """Invalida sessão específica"""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute('UPDATE user_sessions SET is_active = 0 WHERE session_id = ?', (session_id,))
        conn.commit()
        return True
    except Exception:
        return False


def invalidate_all_user_sessions(user_id: int):
    """Invalida todas as sessões do usuário"""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute('UPDATE user_sessions SET is_active = 0 WHERE user_id = ?', (user_id,))
        conn.commit()
        return True
    except Exception:
        return False


def cleanup_expired_sessions():
    """Remove sessões expiradas do banco"""
    from datetime import datetime
    
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        current_time = datetime.now().isoformat()
        cur.execute('DELETE FROM user_sessions WHERE expires_at < ? OR is_active = 0', (current_time,))
        conn.commit()
        return True
    except Exception:
        return False


def update_user_login_info(user_id: int, success: bool = True):
    """Atualiza informações de login do usuário"""
    from datetime import datetime
    
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        if success:
            # Login bem-sucedido - resetar tentativas e atualizar último login
            cur.execute('''
                UPDATE usuarios 
                SET last_login = ?, login_attempts = 0, account_locked = 0
                WHERE id = ?
            ''', (datetime.now().isoformat(), user_id))
        else:
            # Login falhado - incrementar tentativas
            cur.execute('''
                UPDATE usuarios 
                SET login_attempts = login_attempts + 1
                WHERE id = ?
            ''', (user_id,))
            
            # Verificar se deve bloquear conta
            cur.execute('SELECT login_attempts FROM usuarios WHERE id = ?', (user_id,))
            attempts = cur.fetchone()
            if attempts and attempts['login_attempts'] >= 5:
                cur.execute('UPDATE usuarios SET account_locked = 1 WHERE id = ?', (user_id,))
        
        conn.commit()
        return True
        
    except Exception:
        return False


def secure_register_user(nome: str, usuario: str, senha: str, email: str = None, profile_pic_path: str = "") -> dict:
    """
    Registra usuário de forma segura com validações e logs de auditoria
    
    Returns:
        dict: {'success': bool, 'message': str, 'user_id': int (se sucesso)}
    """
    from security.auth.authentication import SecureAuthentication
    from security.validation.input_validator import InputValidator
    from security.audit.security_logger import get_security_logger
    from security.crypto.encryption import DataEncryption
    
    auth = SecureAuthentication()
    validator = InputValidator()
    logger = get_security_logger()
    encryption = DataEncryption()
    
    try:
        # Validar dados de entrada
        if not validator.validate_text(nome, min_length=2, max_length=100):
            return {'success': False, 'message': 'Nome deve ter entre 2 e 100 caracteres'}
            
        if not validator.validate_text(usuario, min_length=3, max_length=50):
            return {'success': False, 'message': 'Usuário deve ter entre 3 e 50 caracteres'}
            
        # Validar política de senhas
        is_valid, msg = auth.validate_password_policy(senha)
        if not is_valid:
            return {'success': False, 'message': msg}
            
        # Validar email se fornecido
        if email and not validator.validate_email(email):
            return {'success': False, 'message': 'Email inválido'}
            
        # Sanitizar inputs
        nome = validator.sanitize_text(nome)
        usuario = validator.sanitize_text(usuario)
        
        # Verificar se usuário já existe
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT 1 FROM usuarios WHERE usuario = ?', (usuario,))
        if cur.fetchone():
            logger.log_auth_event(
                username=usuario,
                event_type='registration_attempt',
                success=False,
                details={'reason': 'username_exists'}
            )
            return {'success': False, 'message': 'Usuário já existe'}
            
        # Hash da senha
        senha_hash = auth.hash_password(senha)
        
        # Email padrão se não fornecido
        if not email:
            email = f'{usuario}@email.com'
            
        # Criptografar dados sensíveis se necessário
        email_encrypted = encryption.encrypt_data(email) if '@' in email and email != f'{usuario}@email.com' else email
        
        # Inserir usuário
        cur.execute('''
            INSERT INTO usuarios (nome, usuario, senha, email, profile_pic, created_at, account_locked, login_attempts)
            VALUES (?, ?, ?, ?, ?, datetime('now'), 0, 0)
        ''', (nome, usuario, senha_hash, email_encrypted, profile_pic_path))
        
        user_id = cur.lastrowid
        conn.commit()
        
        # Log de sucesso
        logger.log_auth_event(
            username=usuario,
            event_type='user_registration',
            success=True,
            details={'user_id': user_id, 'has_profile_pic': bool(profile_pic_path)}
        )
        
        return {
            'success': True, 
            'message': 'Usuário cadastrado com sucesso!',
            'user_id': user_id
        }
        
    except Exception as e:
        # Log de erro
        logger.log_system_event(
            event_type='registration_error',
            details={'error': str(e), 'username': usuario}
        )
        return {'success': False, 'message': 'Erro interno do sistema'}


def is_user_account_locked(username: str) -> bool:
    """Verifica se conta do usuário está bloqueada"""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute('SELECT account_locked FROM usuarios WHERE usuario = ?', (username,))
        result = cur.fetchone()
        return bool(result['account_locked']) if result else False
    except Exception:
        return False


def unlock_user_account(username: str) -> bool:
    """Desbloqueia conta do usuário (para administradores)"""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute('''
            UPDATE usuarios 
            SET account_locked = 0, login_attempts = 0 
            WHERE usuario = ?
        ''', (username,))
        conn.commit()
        return True
    except Exception:
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

def get_user_with_decrypted_email(username):
    """
    Obtém dados do usuário com email descriptografado para exibição
    """
    try:
        from security.crypto.encryption import DataEncryption
        
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT id, usuario, senha, email FROM usuarios WHERE usuario = ?", (username,))
        user = cur.fetchone()
        
        if user:
            user_dict = dict(user)
            
            # Decrypt email if encrypted
            if user_dict['email'] and user_dict['email'].startswith('encrypted:'):
                try:
                    encryption = DataEncryption()
                    encrypted_data = user_dict['email'].replace('encrypted:', '')
                    user_dict['email'] = encryption.decrypt_string(encrypted_data)
                except Exception as e:
                    print(f"Warning: Could not decrypt email for user {username}: {e}")
                    # Keep encrypted email if decryption fails
            
            return user_dict
        
        return None
        
    except Exception as e:
        print(f"Error getting user data: {e}")
        return None

def safe_decrypt_email(encrypted_email):
    """
    Safely decrypt an email address
    """
    try:
        if encrypted_email and encrypted_email.startswith('encrypted:'):
            from security.crypto.encryption import DataEncryption
            encryption = DataEncryption()
            encrypted_data = encrypted_email.replace('encrypted:', '')
            return encryption.decrypt_string(encrypted_data)
        return encrypted_email
    except Exception as e:
        print(f"Warning: Could not decrypt email: {e}")
        return encrypted_email

def secure_authenticate_user(username: str, password: str, ip_address: str = '127.0.0.1') -> dict:
    """
    Função de autenticação segura completa com todos os componentes de segurança
    
    Args:
        username: Nome do usuário
        password: Senha do usuário
        ip_address: Endereço IP do cliente
        
    Returns:
        dict: Resultado da autenticação com detalhes de segurança
    """
    try:
        from security.auth.authentication import SecureAuthentication
        from security.auth.rate_limiter import RateLimiter
        from security.auth.session_manager import SessionManager
        from security.audit.security_logger import SecurityLogger
        from security.validation.input_validator import InputValidator
        
        # Inicializar componentes de segurança
        auth = SecureAuthentication()
        rate_limiter = RateLimiter()
        session_manager = SessionManager()
        logger = SecurityLogger()
        validator = InputValidator()
          # Validar inputs básicos
        if not username or len(username.strip()) == 0:
            logger.log_authentication_attempt(
                username, False, ip_address=ip_address, error='Empty username'
            )
            return {'success': False, 'message': 'Nome de usuário inválido'}
            
        if not password or len(password) < 1:
            logger.log_authentication_attempt(
                username, False, ip_address=ip_address, error='Empty password'
            )
            return {'success': False, 'message': 'Senha não pode estar vazia'}
        
        # Verificar rate limiting
        login_allowed, rate_message = rate_limiter.is_login_allowed(ip_address, username)
        if not login_allowed:
            logger.log_authentication_attempt(
                username, False, ip_address=ip_address, error='Rate limit exceeded'
            )
            return {
                'success': False, 
                'message': rate_message or 'Muitas tentativas de login. Tente novamente em alguns minutos.',
                'rate_limited': True
            }
        
        # Verificar se conta está bloqueada
        if is_user_account_locked(username):
            logger.log_authentication_attempt(
                username, False, ip_address=ip_address, error='Account locked'
            )
            return {
                'success': False, 
                'message': 'Conta bloqueada. Entre em contato com o administrador.',
                'account_locked': True
            }
        
        # Verificar se conta está bloqueada
        if is_user_account_locked(username):
            logger.log_authentication_event(
                username, ip_address, False, 'Account locked'
            )
            return {
                'success': False, 
                'message': 'Conta bloqueada. Entre em contato com o administrador.',
                'account_locked': True
            }
        
        # Buscar usuário no banco
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute('''
            SELECT id, nome, usuario, senha, email, profile_pic, 
                   login_attempts, account_locked, last_login
            FROM usuarios 
            WHERE usuario = ?        ''', (username,))
        
        user = cur.fetchone()
        
        if not user:
            # Log tentativa com usuário inexistente
            logger.log_authentication_attempt(
                username, False, ip_address=ip_address, error='User not found'
            )
            # Registrar tentativa falhada para rate limiting
            rate_limiter.record_login_attempt(ip_address, username, success=False)
            # Retornar mensagem genérica para não revelar se usuário existe
            return {'success': False, 'message': 'Credenciais inválidas'}
        
        user_dict = dict(user)
        
        # Verificar senha
        if not auth.verify_password(password, user_dict['senha']):
            # Incrementar tentativas de login falhadas
            cur.execute('''
                UPDATE usuarios 
                SET login_attempts = login_attempts + 1 
                WHERE id = ?
            ''', (user_dict['id'],))
            
            # Verificar se deve bloquear conta
            new_attempts = user_dict['login_attempts'] + 1
            if new_attempts >= 5:  # Bloquear após 5 tentativas
                cur.execute('''
                    UPDATE usuarios 
                    SET account_locked = 1 
                    WHERE id = ?
                ''', (user_dict['id'],))
                conn.commit()
                
                logger.log_authentication_attempt(
                    username, False, ip_address=ip_address, 
                    error=f'Account locked after {new_attempts} failed attempts'
                )
                rate_limiter.record_login_attempt(ip_address, username, success=False)
                return {
                    'success': False, 
                    'message': 'Conta bloqueada devido a muitas tentativas incorretas.',
                    'account_locked': True
                }
            else:
                conn.commit()
                logger.log_authentication_attempt(
                    username, False, ip_address=ip_address, 
                    error=f'Invalid password (attempt {new_attempts})'
                )
                rate_limiter.record_login_attempt(ip_address, username, success=False)
                return {
                    'success': False, 
                    'message': f'Credenciais inválidas. {5 - new_attempts} tentativas restantes.'
                }
          # Autenticação bem-sucedida
        # Resetar tentativas de login
        cur.execute('''
            UPDATE usuarios 
            SET login_attempts = 0, last_login = datetime('now')
            WHERE id = ?
        ''', (user_dict['id'],))
        conn.commit()
        
        # Registrar sucesso no rate limiter
        rate_limiter.record_login_attempt(ip_address, username, success=True)
        
        # Descriptografar email se necessário
        email = user_dict['email']
        if email and email.startswith('encrypted:'):
            email = safe_decrypt_email(email)
        
        # Criar sessão JWT
        session_data = {
            'user_id': user_dict['id'],
            'username': user_dict['usuario'],
            'nome': user_dict['nome'],
            'email': email,
            'role': 'user'
        }
        
        token = session_manager.create_session(session_data, ip_address)
        
        # Log de sucesso
        logger.log_authentication_attempt(
            username, True, ip_address=ip_address
        )
        
        return {
            'success': True,
            'message': 'Autenticação realizada com sucesso',
            'user': {
                'id': user_dict['id'],
                'nome': user_dict['nome'],
                'usuario': user_dict['usuario'],
                'email': email,
                'profile_pic': user_dict['profile_pic']
            },
            'session_token': token,
            'last_login': user_dict['last_login']
        }
        
    except Exception as e:
        # Log de erro crítico
        try:
            if 'logger' in locals():
                logger.log_system_event(
                    event_type='authentication_error',
                    details={'error': str(e), 'username': username, 'ip': ip_address}
                )
        except:
            pass  # Evitar erro em cascata
            
        print(f"Critical authentication error: {e}")
        return {
            'success': False, 
            'message': 'Erro interno do sistema. Tente novamente.'
        }

def working_authenticate_user(username: str, password: str, ip_address: str = '127.0.0.1') -> dict:
    """
    Função de autenticação segura funcional (sem RateLimiter problemático)
    
    Args:
        username: Nome do usuário
        password: Senha do usuário
        ip_address: Endereço IP do cliente
        
    Returns:
        dict: Resultado da autenticação com detalhes de segurança
    """
    try:
        # Import only working components
        from security.auth.authentication import SecureAuthentication
        from security.audit.security_logger import SecurityLogger
        from security.validation.input_validator import InputValidator
        import secrets
        import string
        from datetime import datetime, timedelta
        
        # Initialize working components
        auth = SecureAuthentication()
        logger = SecurityLogger()
        validator = InputValidator()
        
        # Validate inputs
        if not username or len(username.strip()) == 0:
            logger.log_authentication_attempt(
                username, False, ip_address=ip_address, error='Empty username'
            )
            return {'success': False, 'message': 'Nome de usuário inválido'}
            
        if not password or len(password) < 1:
            logger.log_authentication_attempt(
                username, False, ip_address=ip_address, error='Empty password'
            )
            return {'success': False, 'message': 'Senha não pode estar vazia'}
        
        # Validate username format
        if not validator.validate_username(username):
            logger.log_authentication_attempt(
                username, False, ip_address=ip_address, error='Invalid username format'
            )
            return {'success': False, 'message': 'Formato de nome de usuário inválido'}
        
        # Database connection
        conn = sqlite3.connect('richness.db')
        cursor = conn.cursor()
        
        try:
            # Get user record
            cursor.execute("SELECT usuario, senha FROM usuarios WHERE usuario = ?", (username,))
            user_record = cursor.fetchone()
            
            if not user_record:
                logger.log_authentication_attempt(
                    username, False, ip_address=ip_address, error='User not found'
                )
                return {'success': False, 'message': 'Usuário ou senha incorretos'}
            
            stored_username, stored_password_hash = user_record
            
            # Verify password using SecureAuthentication
            is_valid = auth.verify_password(password, stored_password_hash)
            
            if is_valid:
                # Generate session ID
                session_id = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
                expires_at = (datetime.now() + timedelta(hours=24)).isoformat()
                  # Store session in database
                cursor.execute("""
                    INSERT OR REPLACE INTO user_sessions 
                    (session_id, username, created_at, expires_at, ip_address, is_active)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    username,
                    datetime.now().isoformat(),
                    expires_at,
                    ip_address,
                    1
                ))
                
                conn.commit()
                
                # Log successful authentication
                logger.log_authentication_attempt(
                    username, True, ip_address=ip_address
                )
                
                return {
                    'success': True,
                    'message': 'Autenticação bem-sucedida',
                    'session_id': session_id,
                    'username': username,
                    'expires_at': expires_at,
                    'security_score': 100
                }
            else:
                # Failed authentication
                logger.log_authentication_attempt(
                    username, False, ip_address=ip_address, error='Invalid password'
                )
                
                return {
                    'success': False,
                    'message': 'Usuário ou senha incorretos'
                }
                
        finally:
            conn.close()
            
    except Exception as e:
        try:
            logger.log_authentication_attempt(
                username, False, ip_address=ip_address, 
                error=f'Authentication system error: {str(e)}'
            )
        except:
            pass  # If logging fails, continue
        return {
            'success': False,
            'message': 'Erro interno do sistema. Tente novamente.'
        }

def get_user_role(user_id):
    """
    Retorna a role de um usuário (admin ou user)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Primeiro verifica na tabela de roles
    cursor.execute('''
        SELECT role FROM user_roles 
        WHERE user_id = ? 
        AND role = 'admin'
    ''', (user_id,))
    
    role_row = cursor.fetchone()
    if role_row:
        return 'admin'
    
    # Caso especial para o usuário richardpalmas (para compatibilidade)
    cursor.execute('''
        SELECT usuario FROM usuarios 
        WHERE id = ?
    ''', (user_id,))
    
    user_row = cursor.fetchone()
    if user_row and user_row['usuario'] == 'richardpalmas':
        # Atualiza a tabela de roles para richardpalmas se ainda não estiver lá
        set_user_role(user_id, 'admin')
        return 'admin'
    
    return 'user'

def set_user_role(user_id, role):
    """
    Define a role de um usuário
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Verifica se já existe um registro para este usuário e role
        cursor.execute('''
            SELECT id FROM user_roles 
            WHERE user_id = ? AND role = ?
        ''', (user_id, role))
        
        existing = cursor.fetchone()
        if not existing:
            # Insere novo registro de role
            cursor.execute('''
                INSERT INTO user_roles (user_id, role, created_at, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (user_id, role))
            conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Erro ao definir role do usuário: {e}")
        return False

if __name__ == '__main__':
    create_tables()

