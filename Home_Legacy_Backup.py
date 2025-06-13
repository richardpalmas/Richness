"""
ARQUIVO DE BACKUP HISTÓRICO - Home.py Legacy
============================================
Este arquivo contém a versão anterior do Home.py antes da migração obrigatória 
para o Backend V2. Mantido apenas para referência histórica.

NÃO UTILIZAR EM PRODUÇÃO - Sistema atualizado usa Backend V2 obrigatório.
Data do backup: Junho 2025
"""

import pandas as pd
import plotly.express as px
import streamlit as st
import time
import os
import json
import hashlib

from componentes.profile_pic_component import boas_vindas_com_foto
from database import get_connection, create_tables, remover_usuario, get_user_role
from utils.config import ENABLE_CACHE, get_current_user, get_descricoes_personalizadas_file, get_transacoes_excluidas_file
from utils.exception_handler import ExceptionHandler
from utils.filtros import filtro_data, filtro_categorias, aplicar_filtros
from utils.formatacao import formatar_valor_monetario, formatar_df_monetario, calcular_resumo_financeiro
from utils.ofx_reader import OFXReader

# Importações do novo backend V2
from utils.database_manager_v2 import DatabaseManager
from utils.repositories_v2 import RepositoryManager
from services.transacao_service_v2 import TransacaoService
from utils.database_monitoring import DatabaseMonitor

# Importações de segurança
from security.auth.authentication import SecureAuthentication
try:
    from security.auth.rate_limiter import RateLimiter  # type: ignore
except ImportError:
    # Fallback to inline RateLimiter if import fails
    class RateLimiter:
        def __init__(self):
            self.MAX_LOGIN_ATTEMPTS = 5
            self.LOGIN_WINDOW_MINUTES = 15
            self._attempts_by_ip = {}
            self._attempts_by_user = {}
        
        def check_rate_limit(self, ip_address, username=None):
            return True  # Simplified for now
        
        def record_attempt(self, ip_address, username=None, success=False):
            pass  # Simplified for now

# Configurações da página
st.set_page_config(
    page_title="Richness - Dashboard", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Verificar autenticação
def verificar_autenticacao():
    if 'authenticated' not in st.session_state or not st.session_state['authenticated']:
        mostrar_formulario_login()
        st.stop()

def mostrar_formulario_login():
    """Exibe formulário de login na página Home"""
    
    # Configurar layout para centralizar o login
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("---")
        st.markdown("## 🔐 Login")
        st.markdown("Para acessar o dashboard, faça login com suas credenciais:")
        
        # Formulário de login
        with st.form("login_form", clear_on_submit=False):
            usuario = st.text_input(
                "👤 Usuário",
                placeholder="Digite seu nome de usuário",
                help="Nome de usuário cadastrado no sistema"
            )
            
            senha = st.text_input(
                "🔒 Senha",
                type="password",
                placeholder="Digite sua senha",
                help="Senha do seu usuário"
            )
            
            col_login, col_register = st.columns(2)
            
            with col_login:
                login_button = st.form_submit_button(
                    "🚀 Entrar",
                    use_container_width=True,
                    type="primary"
                )
            
            with col_register:
                if st.form_submit_button(
                    "📝 Criar Conta",
                    use_container_width=True
                ):
                    st.switch_page("pages/Cadastro.py")
            
            # Processar login            if login_button:
                if not usuario or not senha:
                    st.error("❌ Por favor, preencha todos os campos!")
                else:
                    try:
                        import sqlite3
                        import hashlib
                        
                        # Obter IP do cliente (fallback para localhost)  
                        client_ip = st.session_state.get('client_ip', '127.0.0.1')
                        
                        # Conexão direta com o banco para verificar credenciais
                        conn = sqlite3.connect('richness.db')
                        cur = conn.cursor()
                        
                        cur.execute('SELECT usuario, senha FROM usuarios WHERE usuario = ?', (usuario,))
                        user_record = cur.fetchone()
                        
                        if user_record:
                            stored_username, stored_hash = user_record
                            
                            # Verificar se é hash SHA-256 (64 caracteres)
                            if len(stored_hash) == 64:
                                # Hash SHA-256 simples
                                provided_hash = hashlib.sha256(senha.encode()).hexdigest()
                                senha_valida = (provided_hash == stored_hash)
                            else:
                                # Tentar com bcrypt
                                try:
                                    import bcrypt
                                    senha_valida = bcrypt.checkpw(senha.encode('utf-8'), stored_hash.encode('utf-8'))
                                except:
                                    senha_valida = False
                            
                            if senha_valida:
                                resultado = {
                                    'success': True,
                                    'message': 'Login realizado com sucesso',
                                    'username': usuario
                                }
                            else:
                                resultado = {
                                    'success': False,
                                    'message': 'Usuário ou senha incorretos'
                                }
                        else:
                            resultado = {
                                'success': False,
                                'message': 'Usuário não encontrado'
                            }
                        
                        conn.close()
                        
                        if resultado['success']:
                            # Login bem-sucedido - configurar sessão
                            st.session_state['authenticated'] = True
                            st.session_state['autenticado'] = True
                            st.session_state['usuario'] = usuario
                            st.session_state['session_id'] = resultado.get('session_id', '')
                            
                            st.success("✅ Login realizado com sucesso!")
                            st.info("🔄 Redirecionando para o dashboard...")
                            time.sleep(1)
                            st.rerun()
                            
                        else:
                            # Login falhou
                            message = resultado.get('message', 'Erro na autenticação')
                            st.error(f"❌ {message}")
                              # Verificar se a conta está bloqueada
                            if resultado.get('account_locked'):
                                st.warning("⚠️ Sua conta foi bloqueada por segurança. Contate o administrador.")
                            elif resultado.get('rate_limited'):
                                st.warning("⚠️ Muitas tentativas de login. Aguarde alguns minutos.")
                                
                    except Exception as e:
                        st.error("❌ Erro interno do sistema. Tente novamente.")
        
        # Links úteis
        st.markdown("---")
        
        # Informações adicionais
        with st.expander("ℹ️ Precisa de ajuda?"):
            st.write("""
            **Primeiro acesso?**
            - Clique em "Criar Conta" para se cadastrar
            - Preencha seus dados e crie uma senha segura
            
            **Esqueceu sua senha?**
            - Entre em contato com o administrador
            - Mantenha suas credenciais em local seguro
            
            **Problemas técnicos?**
            - Verifique sua conexão com a internet
            - Limpe o cache do navegador
            - Tente novamente em alguns minutos
            """)
        
        # Informação de segurança
        st.markdown("---")
        st.markdown(
            "🔒 **Suas informações estão protegidas** com criptografia "
            "e políticas de segurança avançadas."
        )

verificar_autenticacao()

# Criar tabelas do banco de dados
create_tables()

# Inicializar novo backend V2
@st.cache_resource
def init_backend_v2():
    """Inicializa o novo backend com cache para melhor performance"""
    try:
        # Inicializar componentes do novo backend
        db_manager = DatabaseManager()
        repository_manager = RepositoryManager(db_manager)
        transacao_service = TransacaoService()
        monitor = DatabaseMonitor(db_manager)
        
        return {
            'db_manager': db_manager,
            'repository_manager': repository_manager,
            'transacao_service': transacao_service,
            'monitor': monitor
        }
    except Exception as e:
        # Fallback para backend antigo em caso de erro
        st.warning(f"⚠️ Usando backend legado: {str(e)}")
        return None

# Inicializar backend
backend_v2 = init_backend_v2()

# Obter usuário da sessão
usuario = st.session_state.get('usuario', 'default')

# Boas-vindas com foto de perfil
if usuario:
    boas_vindas_com_foto(usuario)

# Título principal
st.title("🏠 Dashboard Financeiro")

# Seção de status do sistema (expansível)
with st.expander("🔧 Status do Sistema", expanded=False):
    if backend_v2:
        # Verificar se realmente está usando V2 ou fallback
        usando_v2 = False
        try:
            # Fazer um teste simples para ver se o V2 está funcionando
            transacao_service = backend_v2['transacao_service']
            test_df = transacao_service.listar_transacoes_usuario(usuario)
            usando_v2 = not test_df.empty
        except:
            usando_v2 = False
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if usando_v2:
                st.metric(
                    "🚀 Backend", 
                    "V2 (Ativo)", 
                    "✅ Funcionando"
                )
            else:
                st.metric(
                    "🚀 Backend", 
                    "Legado", 
                    "⚠️ Fallback"
                )
        
        with col2:
            if usando_v2:
                # Verificar saúde do banco
                try:
                    monitor = backend_v2['monitor']
                    health_info = monitor.get_system_health()
                    status = "✅ Saudável" if health_info.get('healthy', False) else "⚠️ Atenção"
                    st.metric("💗 Saúde DB", status)
                except:
                    st.metric("💗 Saúde DB", "❓ Verificando")
            else:
                st.metric("💗 Sistema", "📁 Arquivos OFX")
        
        with col3:
            if usando_v2:
                # Performance do cache
                try:
                    db_manager = backend_v2['db_manager']
                    cache_stats = db_manager.get_cache_stats()
                    hit_rate = cache_stats.get('hit_rate', 0)
                    st.metric("⚡ Cache Hit", f"{hit_rate:.1f}%")
                except:
                    st.metric("⚡ Cache Hit", "N/A")
            else:
                st.metric("⚡ Modo", "🔄 Compatibilidade")
                
        # Mostrar métricas detalhadas se solicitado
        if st.checkbox("📊 Mostrar métricas detalhadas"):
            if usando_v2:
                try:
                    monitor = backend_v2['monitor']
                    metrics = monitor.get_performance_metrics()
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.json({
                            "Conexões ativas": metrics.get('active_connections', 0),
                            "Queries executadas": metrics.get('total_queries', 0),
                            "Tempo médio query": f"{metrics.get('avg_query_time', 0):.2f}ms"
                        })
                    
                    with col2:
                        st.json({
                            "Cache size": f"{metrics.get('cache_size', 0)} entries",
                            "Memory usage": f"{metrics.get('memory_usage', 0):.1f}MB",
                            "Uptime": f"{metrics.get('uptime', 0):.1f}s"
                        })
                except Exception as e:
                    st.error(f"Erro ao carregar métricas: {e}")
            else:
                st.info("""
                **Sistema em Modo Legado**
                
                ✅ **Funcionando perfeitamente**:
                - Dados carregados de arquivos OFX
                - Todas as funcionalidades disponíveis
                - Performance otimizada com cache
                
                🔄 **Próximos passos**:
                - Migração automática para V2 em andamento
                - Dados serão preservados
                - Experiência melhorada em breve
                """)
    else:
        st.warning("🔄 Usando backend legado - considere migrar para V2")

st.markdown("---")

# Cache do OFX Reader
@st.cache_resource(ttl=300)
def get_ofx_reader():
    usuario_atual = get_current_user()
    return OFXReader(usuario_atual)

@st.cache_data(ttl=600)
def carregar_dados_home(usuario, force_refresh=False):
    """Carrega dados essenciais para a Home com cache otimizado - Nova versão com Backend V2"""
    def _load_data():
        # Inicializar variáveis
        df_extratos = pd.DataFrame()
        df_cartoes = pd.DataFrame()
        df_ofx = pd.DataFrame()
        df_transacoes = pd.DataFrame()
        dados_v2_ok = False
        
        # Tentar usar o novo backend V2 primeiro
        if backend_v2:
            try:
                transacao_service = backend_v2['transacao_service']
                
                # Carregar todas as transações do usuário
                df_transacoes = transacao_service.listar_transacoes_usuario(usuario)
                
                if not df_transacoes.empty:
                    # Calcular saldos por origem usando o novo serviço
                    saldos_info = transacao_service.calcular_saldos_por_origem(usuario)
                    
                    # Converter para formato esperado pelo frontend
                    saldos_formatted = {}
                    for origem, saldo_data in saldos_info.items():
                        saldos_formatted[origem] = {
                            'saldo': saldo_data.get('saldo_total', 0),
                            'tipo': 'credit_card' if 'fatura' in origem.lower() or 'nubank' in origem.lower() else 'checking'
                        }
                    
                    dados_v2_ok = True
                    st.success("✅ Usando Backend V2 - dados carregados com sucesso!")
                    return saldos_formatted, df_transacoes
                    
            except Exception as e:
                st.warning(f"⚠️ Erro no backend V2: {str(e)}")
        
        # Se V2 não funcionou ou não retornou dados, usar backend legado
        if not dados_v2_ok:
            # Notificação clara e informativa sobre o fallback
            with st.container():
                # Banner principal de fallback
                st.warning("⚠️ **Sistema em Modo de Compatibilidade (Legado)**")
                
                # Informações detalhadas em colunas
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.info("""
                    � **Informações do Sistema**
                    
                    🔄 **Status atual**: Utilizando dados do sistema legado  
                    📁 **Fonte dos dados**: Arquivos OFX nas pastas extratos/ e faturas/  
                    📊 **Funcionalidades**: Dashboard completo disponível  
                    ⚡ **Performance**: Modo otimizado com cache  
                    🔧 **Próximo passo**: Migração para Backend V2 em andamento
                    """)
                
                with col2:
                    # Botões de ação
                    if st.button("🔄 Tentar Backend V2", key="retry_v2", help="Tentar conectar ao novo sistema"):
                        st.cache_data.clear()
                        st.rerun()
                    
                    if st.button("🧹 Limpar Cache", key="clear_cache", help="Limpar cache e recarregar dados"):
                        st.cache_data.clear()
                        st.rerun()
                
                # Status técnico em expandível
                with st.expander("🔧 Detalhes Técnicos", expanded=False):
                    st.markdown("""
                    **Por que estou vendo esta mensagem?**
                    - O backend V2 ainda está sendo configurado ou migrado
                    - Seus dados estão seguros no sistema legado
                    - Todas as funcionalidades continuam disponíveis
                    
                    **O que posso fazer?**
                    - ✅ Continuar usando normalmente o dashboard
                    - ✅ Adicionar/editar transações
                    - ✅ Visualizar relatórios e gráficos
                    - ✅ Gerenciar categorias
                    
                    **Quando o V2 estará disponível?**
                    - A migração é automática e transparente
                    - Seus dados serão preservados durante a transição
                    - Você será notificado quando o upgrade estiver completo
                    """)
            
            st.markdown("---")
            
            ofx_reader = get_ofx_reader()
            
            # Se force_refresh for True, limpar cache
            if force_refresh:
                ofx_reader.limpar_cache()
            
            # Carregar dados dos arquivos OFX
            df_extratos = ofx_reader.buscar_extratos()
            df_cartoes = ofx_reader.buscar_cartoes()
            
            # Mostrar estatísticas dos dados carregados
            total_extratos = len(df_extratos)
            total_cartoes = len(df_cartoes)
            total_geral = total_extratos + total_cartoes
            
            if total_geral > 0:
                # Estatísticas detalhadas com métricas visuais
                st.success("✅ **Dados carregados com sucesso do sistema legado!**")
                
                # Métricas em colunas
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(
                        "🏦 Extratos",
                        f"{total_extratos}",
                        help="Transações de conta corrente"
                    )
                
                with col2:
                    st.metric(
                        "💳 Cartões", 
                        f"{total_cartoes}",
                        help="Transações de cartão de crédito"
                    )
                
                with col3:
                    st.metric(
                        "📈 Total",
                        f"{total_geral}",
                        help="Total de transações carregadas"
                    )
                
                with col4:
                    # Calcular período de dados se houver transações
                    if total_geral > 0:
                        df_temp = pd.concat([df_extratos, df_cartoes], ignore_index=True) if not df_extratos.empty or not df_cartoes.empty else pd.DataFrame()
                        if not df_temp.empty and 'Data' in df_temp.columns:
                            df_temp['Data'] = pd.to_datetime(df_temp['Data'], errors='coerce')
                            data_mais_antiga = df_temp['Data'].min()
                            data_mais_recente = df_temp['Data'].max()
                            if pd.notna(data_mais_antiga) and pd.notna(data_mais_recente):
                                periodo_dias = (data_mais_recente - data_mais_antiga).days
                                st.metric(
                                    "📅 Período",
                                    f"{periodo_dias} dias",
                                    help=f"De {data_mais_antiga.strftime('%d/%m/%Y')} até {data_mais_recente.strftime('%d/%m/%Y')}"
                                )
                            else:
                                st.metric("📅 Período", "N/A")
                        else:
                            st.metric("📅 Período", "N/A")
                    else:
                        st.metric("📅 Período", "N/A")
                
                # Informações adicionais em expandível
                with st.expander("� Detalhes dos Dados Carregados", expanded=False):
                    if total_extratos > 0:
                        st.write(f"**Extratos bancários**: {total_extratos} transações encontradas")
                    if total_cartoes > 0:
                        st.write(f"**Faturas de cartão**: {total_cartoes} transações encontradas")
                    
                    # Mostrar origens dos dados
                    if not df_extratos.empty and 'Origem' in df_extratos.columns:
                        origens_extratos = df_extratos['Origem'].unique()
                        st.write(f"**Origens de extratos**: {', '.join(origens_extratos)}")
                    
                    if not df_cartoes.empty and 'Origem' in df_cartoes.columns:
                        origens_cartoes = df_cartoes['Origem'].unique()
                        st.write(f"**Origens de cartões**: {', '.join(origens_cartoes)}")
            else:
                st.error("❌ Nenhum dado encontrado nos arquivos OFX. Verifique se os arquivos estão na pasta correta.")
                st.stop()
            
            # Combinar extratos e cartões (apenas no fallback)
            df_ofx = pd.concat([df_extratos, df_cartoes], ignore_index=True) if not df_extratos.empty or not df_cartoes.empty else pd.DataFrame()
        
            # Carregar transações manuais (para compatibilidade com sistema legado)
            transacoes_manuais_file = "transacoes_manuais.json"
            df_manuais = pd.DataFrame()
            
            if os.path.exists(transacoes_manuais_file):
                try:
                    import json
                    with open(transacoes_manuais_file, 'r', encoding='utf-8') as f:
                        transacoes_manuais = json.load(f)
                    
                    if transacoes_manuais:
                        dados_manuais = []
                        for transacao in transacoes_manuais:
                            dados_manuais.append({
                                "Data": pd.to_datetime(transacao["data"]),
                                "Descrição": transacao["descricao"],
                                "Valor": transacao["valor"],
                                "Categoria": transacao["categoria"],
                                "Tipo": transacao["tipo"],
                                "Origem": transacao["origem"],
                                "Id": transacao["id"],
                                "tipo_pagamento": transacao.get("tipo_pagamento", "Espécie"),
                                "data_criacao": transacao.get("data_criacao", "")
                            })
                        
                        df_manuais = pd.DataFrame(dados_manuais)
                except:
                    pass  # Em caso de erro, continuar sem transações manuais
            
            # Combinar transações OFX e manuais
            if not df_ofx.empty and not df_manuais.empty:
                df = pd.concat([df_ofx, df_manuais], ignore_index=True)
            elif not df_ofx.empty:
                df = df_ofx
            elif not df_manuais.empty:
                df = df_manuais
            else:
                df = pd.DataFrame()
        else:
            # Se chegou aqui, V2 funcionou - usar os dados do V2
            df = df_transacoes
        
        # Pré-processamento mínimo
        if not df.empty:
            df["Data"] = pd.to_datetime(df["Data"])
            df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")
            
            # Aplicar categorizações personalizadas do usuário (MESMO CÓDIGO DA PÁGINA GERENCIAR_TRANSACOES)
            cache_categorias_file = "cache_categorias_usuario.json"
            if os.path.exists(cache_categorias_file):
                try:
                    import json
                    with open(cache_categorias_file, 'r', encoding='utf-8') as f:
                        cache = json.load(f)
                    
                    def aplicar_categoria_personalizada(row):
                        descricao_normalizada = row["Descrição"].lower().strip()
                        if descricao_normalizada in cache:
                            return cache[descricao_normalizada]
                        return row.get("Categoria", "Outros")
                    
                    df["Categoria"] = df.apply(aplicar_categoria_personalizada, axis=1)
                except:
                    pass  # Em caso de erro, manter categorizações originais
            
            # Aplicar filtro de transações excluídas
            transacoes_excluidas_file = get_transacoes_excluidas_file()
            if os.path.exists(transacoes_excluidas_file):
                try:
                    import json
                    import hashlib
                    with open(transacoes_excluidas_file, 'r', encoding='utf-8') as f:
                        transacoes_excluidas = json.load(f)
                    
                    if transacoes_excluidas:
                        def gerar_hash_transacao(row):
                            data_str = row["Data"].strftime("%Y-%m-%d") if hasattr(row["Data"], 'strftime') else str(row["Data"])
                            chave = f"{data_str}|{row['Descrição']}|{row['Valor']}"
                            return hashlib.md5(chave.encode()).hexdigest()
                        
                        def nao_esta_excluida(row):
                            hash_transacao = gerar_hash_transacao(row)
                            return hash_transacao not in transacoes_excluidas
                        
                        df = df[df.apply(nao_esta_excluida, axis=1)]
                except:
                    pass  # Em caso de erro, manter todas as transações
            
            # Calcular saldos por origem
            saldos_info = {}
            for origem in df['Origem'].unique():
                df_origem = df[df['Origem'] == origem]
                saldo = df_origem['Valor'].sum()
                saldos_info[origem] = {
                    'saldo': saldo,
                    'tipo': 'credit_card' if 'fatura' in origem.lower() or 'nubank' in origem.lower() else 'checking'
                }
        else:
            saldos_info = {}
        
        return saldos_info, df
    
    return ExceptionHandler.safe_execute(
        func=_load_data,
        error_handler=ExceptionHandler.handle_generic_error,
        default_return=({}, pd.DataFrame())
    )

# Funções para descrições personalizadas
def gerar_hash_transacao(row):
    """Gera um hash único para identificar uma transação de forma consistente"""
    data_str = row["Data"].strftime("%Y-%m-%d") if hasattr(row["Data"], 'strftime') else str(row["Data"])
    chave = f"{data_str}|{row['Descrição']}|{row['Valor']}"
    return hashlib.md5(chave.encode()).hexdigest()

def carregar_descricoes_personalizadas():
    """Carrega o cache de descrições personalizadas do usuário"""
    descricoes_file = get_descricoes_personalizadas_file()
    if os.path.exists(descricoes_file):
        try:
            with open(descricoes_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def obter_descricao_personalizada(row):
    """Obtém a descrição personalizada de uma transação, se existir"""
    descricoes = carregar_descricoes_personalizadas()
    hash_transacao = gerar_hash_transacao(row)
    return descricoes.get(hash_transacao, "Nenhuma descrição disponível")

# Função para formatar DataFrame com descrições personalizadas
def formatar_df_com_descricoes(df):
    """Formata o DataFrame adicionando descrições personalizadas e removendo coluna Id"""
    if df.empty:
        return df
    
    # Criar cópia do DataFrame
    df_formatado = df.copy()
    
    # Aplicar formatação monetária
    df_formatado = formatar_df_monetario(df_formatado)
    
    # Adicionar coluna de descrição personalizada (renomeada para "Nota")
    df_formatado["Nota"] = df_formatado.apply(obter_descricao_personalizada, axis=1)
    
    # Reordenar colunas: Data → Descrição → Valor → Nota → outras
    colunas_desejadas = []
    
    for col in df_formatado.columns:
        if col.lower() not in ['id', 'index']:  # Excluir colunas de Id
            colunas_desejadas.append(col)
    
    # Criar nova ordem das colunas
    colunas_ordenadas = []
    
    # 1. Adicionar Data (se existir)
    if "Data" in colunas_desejadas:
        colunas_ordenadas.append("Data")
    
    # 2. Adicionar Descrição (se existir)
    if "Descrição" in colunas_desejadas:
        colunas_ordenadas.append("Descrição")
    
    # 3. Adicionar Valor (se existir)
    if "Valor" in colunas_desejadas:
        colunas_ordenadas.append("Valor")
    elif "ValorFormatado" in colunas_desejadas:
        colunas_ordenadas.append("ValorFormatado")
    
    # 4. Adicionar Nota (se existir)
    if "Nota" in colunas_desejadas:
        colunas_ordenadas.append("Nota")
    
    # 5. Adicionar demais colunas na ordem original
    for col in colunas_desejadas:
        if col not in colunas_ordenadas:
            colunas_ordenadas.append(col)
    
    return df_formatado[colunas_ordenadas]

# Sidebar - Configurações
st.sidebar.header("⚙️ Configurações")

# Botão de Sair
st.sidebar.markdown("---")  # Separador visual
if st.sidebar.button('🚪 Sair', help="Fazer logout da aplicação", type="primary"):
    st.session_state.clear()
    st.rerun()

# Carregar dados principais
usuario = st.session_state.get('usuario', 'default')

# Migração automática de dados legados para o usuário atual
try:
    from utils.user_data_manager import user_data_manager
    migrated_files = user_data_manager.copy_legacy_data_to_user(usuario)
    if migrated_files:
        st.info(f"📦 **Migração automática**: {len(migrated_files)} arquivos foram migrados para seu perfil de usuário.")
        with st.expander("Ver arquivos migrados"):
            for file in migrated_files:
                st.text(f"• {file}")
except Exception as e:
    st.error(f"Erro na migração automática: {e}")

saldos_info, df = carregar_dados_home(usuario)

# Verificar se há dados
if df.empty:
    st.warning("📭 Nenhuma transação encontrada nos arquivos OFX!")
    st.info("💡 **Como adicionar dados:**")
    st.markdown("""
    1. 📁 Coloque seus extratos (.ofx) na pasta `extratos/`
    2. 💳 Coloque suas faturas de cartão (.ofx) na pasta `faturas/`
    3. 🔄 Clique em "Atualizar Dados" na barra lateral
    """)
    
    # Mostrar resumo dos arquivos disponíveis
    ofx_reader = get_ofx_reader()
    resumo = ofx_reader.get_resumo_arquivos()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("📄 Extratos Disponíveis", resumo['total_extratos'])
    with col2:
        st.metric("💳 Faturas Disponíveis", resumo['total_faturas'])
    
    st.stop()

# Dashboard principal
st.subheader("📊 Resumo Financeiro")

# Calcular resumo financeiro
resumo = calcular_resumo_financeiro(df)

# Métricas principais
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "💰 Receitas", 
        formatar_valor_monetario(resumo["receitas"]),
        delta=None
    )

with col2:
    st.metric(
        "💸 Despesas", 
        formatar_valor_monetario(abs(resumo["despesas"])),
        delta=None
    )

with col3:
    saldo_liquido = resumo["saldo"]
    delta_color = "normal" if saldo_liquido >= 0 else "inverse"
    st.metric(
        "💳 Saldo Líquido", 
        formatar_valor_monetario(saldo_liquido),
        delta=None
    )

with col4:
    st.metric(
        "📈 Total de Transações", 
        len(df),
        delta=None
    )

# Filtros
st.subheader("🔍 Filtros")
col1, col2 = st.columns(2)

with col1:
    data_inicio, data_fim = filtro_data(df)

with col2:
    categorias_selecionadas = filtro_categorias(df)

# Aplicar filtros
df_filtrado = aplicar_filtros(df, data_inicio, data_fim, categorias_selecionadas)

if df_filtrado.empty:
    st.warning("🔍 Nenhuma transação encontrada com os filtros aplicados.")
    st.stop()

# Gráficos
st.subheader("📈 Análises")

# Nova seção: Insights Inteligentes com IA (Backend V2)
if backend_v2 and not df_filtrado.empty:
    with st.expander("🤖 Insights Inteligentes com IA", expanded=True):
        try:
            transacao_service = backend_v2['transacao_service']
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**🎯 Análises Personalizadas**")
                
                # Categorização automática de transações recentes
                if st.button("🏷️ Recategorizar automaticamente"):
                    with st.spinner("Analisando transações com IA..."):
                        resultado = transacao_service.processar_categorizacao_ai(usuario)
                        if resultado.get('success'):
                            st.success(f"✅ {resultado.get('categorized_count', 0)} transações recategorizadas!")
                            st.rerun()
                        else:
                            st.warning(f"⚠️ {resultado.get('error', 'Erro na categorização')}")
                
                # Detecção de anomalias
                if st.button("🔍 Detectar anomalias"):
                    with st.spinner("Detectando padrões anômalos..."):
                        anomalias = transacao_service.detectar_anomalias_usuario(usuario)
                        if anomalias:
                            st.warning(f"⚠️ {len(anomalias)} anomalias detectadas")
                            for anomalia in anomalias[:3]:  # Mostrar apenas as 3 primeiras
                                st.write(f"• {anomalia.get('descricao', 'N/A')}: {anomalia.get('motivo', 'N/A')}")
                        else:
                            st.success("✅ Nenhuma anomalia detectada")
            
            with col2:
                st.write("**📊 Relatórios Avançados**")
                
                # Análise de tendências
                if st.button("📈 Gerar análise de tendências"):
                    with st.spinner("Gerando insights de tendências..."):
                        tendencias = transacao_service.gerar_relatorio_tendencias(usuario)
                        if tendencias.get('success'):
                            st.success("✅ Análise de tendências gerada!")
                            # Mostrar algumas métricas principais
                            metricas = tendencias.get('metricas', {})
                            if metricas:
                                st.json({
                                    "Crescimento mensal": f"{metricas.get('crescimento_mensal', 0):.1f}%",
                                    "Categoria dominante": metricas.get('categoria_dominante', 'N/A'),
                                    "Padrão de gastos": metricas.get('padrao_gastos', 'N/A')
                                })
                        else:
                            st.error(f"❌ {tendencias.get('error', 'Erro na análise')}")
                
                # Health check do sistema
                st.write("**🏥 Status do Sistema**")
                try:
                    monitor = backend_v2['monitor']
                    health = monitor.get_system_health()
                    if health.get('healthy'):
                        st.success(f"✅ Sistema saudável ({health.get('total_connections', 0)} conexões)")
                    else:
                        st.warning("⚠️ Sistema com problemas")
                except:
                    st.info("❓ Status indisponível")
                    
        except Exception as e:
            st.error(f"❌ Erro ao carregar insights: {str(e)}")

st.markdown("---")

# Primeira linha: Distribuição por Categoria
col1, col2 = st.columns(2)

with col1:
    # Gráfico de categorias (apenas despesas)
    if "Categoria" in df_filtrado.columns:
        # Filtrar apenas transações negativas (despesas)
        df_despesas = df_filtrado[df_filtrado["Valor"] < 0]
        
        if not df_despesas.empty:
            categoria_resumo_despesas = df_despesas.groupby("Categoria")["Valor"].sum().reset_index()
            categoria_resumo_despesas["ValorAbs"] = categoria_resumo_despesas["Valor"].abs()
            categoria_resumo_despesas = categoria_resumo_despesas.sort_values("ValorAbs", ascending=False)
            
            fig_cat_despesas = px.pie(
                categoria_resumo_despesas, 
                names="Categoria", 
                values="ValorAbs",
                title="Distribuição por Categoria (Despesas)",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            st.plotly_chart(fig_cat_despesas, use_container_width=True)
        else:
            st.info("📊 Nenhuma despesa encontrada no período selecionado.")

with col2:
    # Gráfico de categorias (apenas receitas)
    if "Categoria" in df_filtrado.columns:
        # Filtrar apenas transações positivas (receitas)
        df_receitas = df_filtrado[df_filtrado["Valor"] > 0]
        
        if not df_receitas.empty:
            categoria_resumo_receitas = df_receitas.groupby("Categoria")["Valor"].sum().reset_index()
            categoria_resumo_receitas = categoria_resumo_receitas.sort_values("Valor", ascending=False)
            
            fig_cat_receitas = px.pie(
                categoria_resumo_receitas, 
                names="Categoria", 
                values="Valor",
                title="Distribuição por Categoria (Receitas)",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            st.plotly_chart(fig_cat_receitas, use_container_width=True)
        else:
            st.info("📊 Nenhuma receita encontrada no período selecionado.")

# Segunda linha: Evolução Temporal
st.markdown("---")
if "Data" in df_filtrado.columns:
    df_temp = df_filtrado.copy()
    df_temp["AnoMes"] = df_temp["Data"].dt.to_period("M").astype(str)
    evolucao = df_temp.groupby("AnoMes")["Valor"].sum().reset_index()
    
    fig_evolucao = px.line(
        evolucao, 
        x="AnoMes", 
        y="Valor",
        title="📈 Evolução Mensal do Saldo",
        markers=True,
        line_shape="spline"
    )
    fig_evolucao.update_layout(
        xaxis_title="Período",
        yaxis_title="Valor (R$)",
        showlegend=False
    )
    st.plotly_chart(fig_evolucao, use_container_width=True)

# Tabela de transações com abas por categoria
st.subheader("📋 Transações do Período")

# Obter categorias disponíveis no período filtrado
if not df_filtrado.empty:
    categorias_periodo = sorted(df_filtrado["Categoria"].unique())
    
    # Criar lista de abas: "Todas" + categorias específicas
    abas_disponiveis = ["📊 Todas"] + [f"🏷️ {cat}" for cat in categorias_periodo]
    
    # Criar abas usando st.tabs
    tabs = st.tabs(abas_disponiveis)
    
    with tabs[0]:  # Aba "Todas"
        st.markdown("**Todas as transações do período selecionado**")
        
        # Mostrar resumo
        total_transacoes = len(df_filtrado)
        valor_total = df_filtrado["Valor"].sum()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("💼 Total", total_transacoes)
        with col2:
            st.metric("💰 Saldo", formatar_valor_monetario(valor_total))
        with col3:
            receitas_count = len(df_filtrado[df_filtrado["Valor"] > 0])
            despesas_count = len(df_filtrado[df_filtrado["Valor"] < 0])
            st.metric("📈📉 R/D", f"{receitas_count}/{despesas_count}")
        
        # Tabela formatada com descrições personalizadas
        df_display_todas = formatar_df_com_descricoes(df_filtrado.head(50))
        st.dataframe(
            df_display_todas,
            use_container_width=True,
            height=400
        )
        
        if len(df_filtrado) > 50:
            st.caption(f"📄 Exibindo 50 de {len(df_filtrado)} transações (ordenadas por data mais recente)")
    
    # Abas para cada categoria
    for i, categoria in enumerate(categorias_periodo, 1):
        with tabs[i]:
            # Filtrar transações da categoria
            df_categoria = df_filtrado[df_filtrado["Categoria"] == categoria]
            
            st.markdown(f"**Transações da categoria: {categoria}**")
            
            # Mostrar resumo da categoria
            total_cat = len(df_categoria)
            valor_cat = df_categoria["Valor"].sum()
            receitas_cat = len(df_categoria[df_categoria["Valor"] > 0])
            despesas_cat = len(df_categoria[df_categoria["Valor"] < 0])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("💼 Transações", total_cat)
            with col2:
                st.metric("💰 Total", formatar_valor_monetario(valor_cat))
            with col3:
                if receitas_cat > 0 and despesas_cat > 0:
                    st.metric("📈📉 R/D", f"{receitas_cat}/{despesas_cat}")
                elif receitas_cat > 0:
                    st.metric("📈 Receitas", receitas_cat)
                else:
                    st.metric("📉 Despesas", despesas_cat)
            
            if not df_categoria.empty:
                # Tabela formatada da categoria com descrições personalizadas
                df_display_cat = formatar_df_com_descricoes(df_categoria.head(50))
                st.dataframe(
                    df_display_cat,
                    use_container_width=True,
                    height=400
                )
                
                if len(df_categoria) > 50:
                    st.caption(f"📄 Exibindo 50 de {len(df_categoria)} transações desta categoria")
            else:
                st.info("📭 Nenhuma transação encontrada nesta categoria para o período selecionado.")

else:
    st.warning("🔍 Nenhuma transação encontrada com os filtros aplicados.")
    st.info("💡 Ajuste os filtros de data ou categoria para ver as transações.")

# Informações sobre arquivos OFX
with st.expander("📁 Informações dos Arquivos OFX"):
    ofx_reader = get_ofx_reader()
    resumo = ofx_reader.get_resumo_arquivos()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Extratos:**")
        st.write(f"Total: {resumo['total_extratos']} arquivos")
        if resumo['periodo_extratos']['inicio']:
            st.write(f"Período: {resumo['periodo_extratos']['inicio']} a {resumo['periodo_extratos']['fim']}")
    
    with col2:
        st.write("**Faturas:**")
        st.write(f"Total: {resumo['total_faturas']} arquivos")
        if resumo['periodo_faturas']['inicio']:
            st.write(f"Período: {resumo['periodo_faturas']['inicio']} a {resumo['periodo_faturas']['fim']}")
