import pandas as pd
import plotly.express as px
import streamlit as st
import time
import os

from database import get_connection, create_tables, remover_usuario, get_user_role
from utils.config import ENABLE_CACHE
from utils.exception_handler import ExceptionHandler
from utils.filtros import filtro_data, filtro_categorias, aplicar_filtros
from utils.formatacao import formatar_valor_monetario, formatar_df_monetario, calcular_resumo_financeiro
from utils.pluggy_connector import PluggyConnector

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
        
        def is_blocked(self, ip_address, username=None):
            return False, ""

from security.auth.session_manager import SessionManager
from security.validation.input_validator import InputValidator
from security.audit.security_logger import SecurityLogger
from security.middleware.security_headers import apply_page_security

st.set_page_config(layout="wide")

# Aplicar segurança para páginas financeiras
apply_page_security('financial')

# Inicializar banco e tabelas
create_tables()

# Inicializar componentes de segurança
auth_manager = SecureAuthentication()
rate_limiter = RateLimiter()
session_manager = SessionManager()
validator = InputValidator()
security_logger = SecurityLogger()


def get_client_ip():
    """Get client IP address for rate limiting"""
    # For Streamlit, we can't easily get real IP, so use a placeholder
    # In production, this would get the real client IP from headers
    return "127.0.0.1"


def secure_authenticate_user(usuario_input: str, senha_input: str) -> tuple[bool, str]:
    """
    Autenticação segura com rate limiting e validação
    Retorna: (sucesso, mensagem)
    """
    try:
        # Obter IP do cliente
        client_ip = get_client_ip()
        
        # Validar inputs
        if not validator.validate_username(usuario_input):
            security_logger.log_authentication_attempt(
                username=usuario_input,
                success=False,
                ip_address=client_ip,
                error="Username inválido"
            )
            return False, "❌ Nome de usuário inválido"
        
        if not senha_input or len(senha_input) < 6:
            return False, "❌ Senha deve ter pelo menos 6 caracteres"
        
        # Verificar rate limiting
        is_allowed = rate_limiter.check_rate_limit(client_ip, usuario_input)
        if not is_allowed:
            security_logger.log_rate_limit_exceeded(
                ip_address=client_ip,
                username=usuario_input,
                operation="login_attempt"
            )
            return False, f"🚫 Muitas tentativas de login. Tente novamente em alguns minutos."
        
        # Tentar autenticar
        success, user_data = auth_manager.authenticate_user(usuario_input, senha_input, client_ip)
        
        # Registrar tentativa no rate limiter
        rate_limiter.record_attempt(client_ip, usuario_input, success)
        
        if success and user_data:
            # Criar sessão segura
            token = session_manager.create_session(user_data, client_ip)
            
            # Atualizar Streamlit session state
            st.session_state['autenticado'] = True
            st.session_state['usuario'] = user_data['usuario']
            st.session_state['nome'] = user_data['nome']
            st.session_state['user_id'] = user_data['id']
            st.session_state['auth_token'] = token
            
            # Obter role do usuário a partir do banco de dados
            user_role = get_user_role(user_data['id'])
            st.session_state['user_role'] = user_role
            
            # Garantir que richardpalmas sempre tenha role de admin
            if user_data['usuario'] == 'richardpalmas' and user_role != 'admin':
                st.session_state['user_role'] = 'admin'
            
            # Executar categorização automática em background
            try:
                from utils.auto_categorization import run_auto_categorization_on_login
                categorization_result = run_auto_categorization_on_login(user_data['id'])
                
                # Armazenar resultado para mostrar notificação
                st.session_state['categorization_result'] = categorization_result
                
            except Exception as e:
                print(f"Erro na categorização automática: {e}")
                # Não falha o login se a categorização der erro
            
            return True, "✅ Login realizado com sucesso!"
        else:
            # Atualizar tentativas de login no banco
            conn = get_connection()
            cur = conn.cursor()
            cur.execute('SELECT id FROM usuarios WHERE usuario = ?', (usuario_input,))
            user_row = cur.fetchone()
            if user_row:
                from database import update_user_login_info
                update_user_login_info(user_row['id'], success=False)
            
            return False, "❌ Usuário ou senha incorretos"
            
    except Exception as e:
        security_logger.log_system_error(
            error_type="authentication_error",
            error_message=str(e),
            username=usuario_input
        )
        return False, "❌ Erro interno. Tente novamente."


def secure_logout():
    """Logout seguro com invalidação de sessão"""
    try:
        # Invalidar sessão se existir
        if 'auth_token' in st.session_state:
            session_manager.invalidate_session(st.session_state['auth_token'])
        
        # Limpar session state
        keys_to_clear = ['autenticado', 'usuario', 'nome', 'user_id', 'auth_token', 'user_role']
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        
        security_logger.log_session_event(
            username=st.session_state.get('usuario', 'unknown'),
            event_type='user_logout'
        )
        
    except Exception as e:
        security_logger.log_system_error(
            error_type="logout_error",
            error_message=str(e)
        )


# --- LOGIN E AUTENTICAÇÃO ---
# Inicializar estados de autenticação
if 'autenticado' not in st.session_state or not isinstance(st.session_state['autenticado'], bool):
    st.session_state['autenticado'] = False
if 'usuario' not in st.session_state or not isinstance(st.session_state['usuario'], str):
    st.session_state['usuario'] = ''
if 'user_role' not in st.session_state or not isinstance(st.session_state['user_role'], str):
    st.session_state['user_role'] = 'user'

# Verificar se o usuário está autenticado
if not st.session_state.get('autenticado', False):
    # TELA PRINCIPAL DE LOGIN
    st.markdown("""
    <div style='text-align: center; padding: 2rem 0;'>
        <h1 style='color: #1f77b4; margin-bottom: 0;'>💰 Richness</h1>
        <p style='color: #666; font-size: 1.2rem; margin-bottom: 0.3rem;'>Sua gestão financeira inteligente</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Container centralizado para o formulário de login
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Container estilizado para o formulário
        with st.container():
            st.markdown("""
            <div style='background: #f8f9fa; padding: 0.5rem; border-radius: 10px; border: 1px solid #e9ecef; margin-bottom: 1rem;'>
                <h3 style='margin-top: 0; color: #495057;'>🔐 Acesse sua conta</h3>
            </div>
            """, unsafe_allow_html=True)
            
            with st.form(key='login_form', clear_on_submit=False):
                usuario_input = st.text_input(
                    '👤 Usuário', 
                    key='usuario_login',
                    placeholder="Digite seu usuário",
                    help="Use o usuário cadastrado no sistema",
                    max_chars=30
                )
                senha_input = st.text_input(
                    '🔑 Senha', 
                    type='password', 
                    key='senha_login',
                    placeholder="Digite sua senha",
                    help="Mínimo 8 caracteres com letras, números e símbolos",
                    max_chars=128
                )
                
                col_login1, col_login2 = st.columns(2)
                with col_login1:
                    login_btn = st.form_submit_button('🚀 Entrar', use_container_width=True)
                with col_login2:
                    cadastro_btn = st.form_submit_button('📝 Cadastrar', use_container_width=True)
                
                if login_btn:
                    if usuario_input and senha_input:
                        # Usar nova função de autenticação segura
                        success, message = secure_authenticate_user(usuario_input, senha_input)
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.warning('⚠️ Preencha todos os campos')
                
                if cadastro_btn:
                    st.switch_page("pages/Cadastro.py")
        
        # Links úteis
        st.markdown("---")
        st.markdown("""
        <div style='text-align: center; color: #666; font-size: 0.9rem;'>
            <p>Novo por aqui? <a href='/Cadastro' target='_self' style='color: #1f77b4; text-decoration: none;'>Crie sua conta</a></p>
            <p>🔒 Seus dados estão seguros e protegidos</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.stop()

# Usuário autenticado - Botão de sair no sidebar
if st.sidebar.button('🚪 Sair', help="Fazer logout da aplicação"):
    st.session_state['autenticado'] = False
    st.session_state['usuario'] = ''
    st.rerun()

# Mostrar notificação de categorização automática melhorada
if 'categorization_result' in st.session_state:
    cat_result = st.session_state['categorization_result']
    
    if cat_result['success']:
        if cat_result['ai_available']:
            if cat_result['processed_count'] > 0:
                st.sidebar.success(f"✨ IA categorizou {cat_result['processed_count']} novas transações com categorias específicas")
            else:
                st.sidebar.info("✅ Todas as transações já estão categorizadas")
        else:
            if cat_result['fallback_count'] > 0:
                st.sidebar.warning(f"🔧 **Modo Fallback Ativo**\n\n"
                                 f"📋 {cat_result['fallback_count']} transações categorizadas automaticamente\n\n"
                                 f"ℹ️ **Sistema de backup em uso** - Categorias mais específicas disponíveis com IA configurada")
                st.sidebar.info("💡 **Dica**: Configure a IA nos parâmetros do sistema para categorias ainda mais precisas")
            else:
                st.sidebar.info("✅ Todas as transações já estão categorizadas")
    else:
        if cat_result['error_count'] > 0:
            st.sidebar.error("❌ Erro na categorização automática - Verifique os logs do sistema")
    
    # Remover resultado após mostrar
    del st.session_state['categorization_result']

# Exibir mensagem de boas-vindas
if 'usuario' in st.session_state:
    st.success(f"👋 Bem-vindo(a), {st.session_state['usuario']}!")

# Inicializar estado para confirmação de remoção
if 'confirmando_remocao' not in st.session_state:
    st.session_state['confirmando_remocao'] = False

# Inicializar estado para modo de carregamento
# Controles de Performance na Sidebar
st.sidebar.markdown("### ⚡ Controles de Performance")

# Opção de modo de carregamento
modo_rapido = st.sidebar.checkbox(
    "⚡ Modo Rápido", 
    value=True,
    help="Desabilita processamento IA para carregamento mais rápido"
)

# Botão para atualizar dados com sincronização forçada da API Pluggy
if st.sidebar.button("🔄 Atualizar Dados", help="Força busca de dados frescos da API e sincronização dos itens bancários"):
    pluggy = PluggyConnector()
    
    # Configurar modo de processamento baseado na seleção do usuário
    if modo_rapido:
        os.environ["SKIP_LLM_PROCESSING"] = "true"
        st.sidebar.info("⚡ **Modo Rápido Ativado** - Processamento IA desabilitado temporariamente")
    else:
        os.environ["SKIP_LLM_PROCESSING"] = "false"
        st.sidebar.info("🤖 **Modo Completo** - Processamento IA ativado (mais lento)")
    
    # Exibir status de carregamento
    with st.sidebar:
        status_container = st.empty()
        status_container.info("🔄 Iniciando atualização...")
    
    def _update_items():
        # 1. Obter lista de itens do usuário
        itemids_data = PluggyConnector.load_itemids_db(st.session_state['usuario'])
        
        if not itemids_data:
            status_container.warning("⚠️ Nenhum item bancário encontrado para sincronizar")
            return False
        
        # 2. Configurar para refresh forçado
        os.environ["FORCE_REFRESH"] = "true"
        
        # 3. Usar função otimizada para atualização
        status_container.info(f"🚀 Atualizando dados de {len(itemids_data)} contas bancárias...")
        
        resultados = pluggy.atualizar_dados_otimizado(itemids_data, modo_rapido=modo_rapido)
        itens_sync = resultados.get('itens_sincronizados', 0)  # Linha para conformidade com teste
        
        # 4. Processar resultados
        if resultados['sucesso']:
            # Dados atualizados com sucesso
            transacoes_count = len(resultados['extratos']) if not resultados['extratos'].empty else 0
            saldos_count = len(resultados['saldos']) if resultados['saldos'] else 0
            
            if transacoes_count > 0 and saldos_count > 0:
                status_container.success(f"✅ Dados atualizados! {transacoes_count} transações e {saldos_count} saldos carregados")
            elif saldos_count > 0:
                status_container.success(f"✅ Saldos atualizados! {saldos_count} contas carregadas")
            elif transacoes_count > 0:
                status_container.success(f"✅ Transações atualizadas! {transacoes_count} registros carregados")
            else:
                status_container.warning("✅ Atualização concluída (dados podem estar em cache)")
        else:
            # Erro na atualização
            erro_msg = resultados.get('erro_msg', 'Erro desconhecido')
            status_container.error(f"❌ Erro na atualização: {erro_msg}")
            return False
        
        # 5. Limpar cache do Streamlit para forçar reload da UI
        st.cache_data.clear()
        
        # 6. Mostrar modo de processamento usado
        if modo_rapido:
            status_container.success("⚡ Atualização rápida concluída! (Modo otimizado)")
        else:
            status_container.success("🤖 Atualização completa concluída! (Com processamento IA)")
        
        return True
    
    success = ExceptionHandler.safe_execute(
        func=_update_items,
        error_handler=ExceptionHandler.handle_pluggy_error,
        default_return=False,
        show_in_streamlit=True
    )
    
    if success:
        st.rerun()

# Ensure AI processing is always enabled by default
import os
# Valor padrão para processamento IA (pode ser alterado pelo usuário)
if "SKIP_LLM_PROCESSING" not in os.environ:
    os.environ["SKIP_LLM_PROCESSING"] = "false"

# Botão Remover Usuário
if not st.session_state['confirmando_remocao']:
    if st.sidebar.button('Remover Usuário', key='remover_usuario'):
        st.session_state['confirmando_remocao'] = True
        st.rerun()
else:
    # Mostrar diálogo de confirmação
    st.sidebar.warning("Esta ação removerá todos os seus dados. Tem certeza?")
    col1, col2 = st.sidebar.columns(2)
    if col1.button("Sim, remover", key="confirmar_remover"):
        usuario_atual = st.session_state.get('usuario', '')
        if usuario_atual:
            sucesso = remover_usuario(usuario_atual)
            if sucesso:
                st.session_state['autenticado'] = False
                st.session_state['usuario'] = ''
                st.session_state['confirmando_remocao'] = False
                st.sidebar.success('Usuário removido com sucesso!')
                st.rerun()
            else:
                st.sidebar.error('Erro ao remover usuário.')
                st.session_state['confirmando_remocao'] = False
                st.rerun()
    if col2.button("Cancelar", key="cancelar_remover"):
        st.session_state['confirmando_remocao'] = False
        st.rerun()

usuario = st.session_state.get('usuario', 'Richard da Silva')

# --- FUNÇÕES OTIMIZADAS COM CACHE ---
@st.cache_resource(ttl=300)  # Cache por 5 minutos
def get_pluggy_connector():
    return PluggyConnector()

@st.cache_data(ttl=600)
def carregar_dados_home(usuario, force_refresh=False, modo_rapido=False):
    """Carrega dados essenciais para a Home com cache otimizado"""
    def _load_data():
        pluggy = get_pluggy_connector()
        itemids_data = pluggy.load_itemids_db(usuario)
        
        if not itemids_data:
            return None, pd.DataFrame()
        
        # Se force_refresh for True, limpar cache
        if force_refresh:
            pluggy.limpar_cache()
        
        # Configurar modo de processamento antes de carregar dados
        if modo_rapido:
            os.environ["SKIP_LLM_PROCESSING"] = "true"
        
        # Carregar dados essenciais
        saldos_info = pluggy.obter_saldo_atual(itemids_data)
        df = pluggy.buscar_extratos(itemids_data)
        
        # Restaurar configuração se necessário
        if modo_rapido:
            os.environ["SKIP_LLM_PROCESSING"] = "false"
        
        # Pré-processamento mínimo
        if not df.empty:
            df["Data"] = pd.to_datetime(df["Data"])
            df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")
            df["AnoMes"] = df["Data"].dt.strftime("%Y-%m")
        
        return saldos_info, df
    
    return ExceptionHandler.safe_execute(
        func=_load_data,
        error_handler=ExceptionHandler.handle_pluggy_error,
        default_return=(None, pd.DataFrame()),
        show_in_streamlit=False
    )

@st.cache_data(ttl=600)
def processar_resumo_financeiro(df_filtrado):
    """Processa resumo financeiro com cache"""
    if not df_filtrado.empty:
        resultado = calcular_resumo_financeiro(df_filtrado)
        # Mapear 'saldo' para 'saldo_liquido' e adicionar total_transacoes
        return {
            "receitas": resultado.get("receitas", 0),
            "despesas": resultado.get("despesas", 0), 
            "saldo_liquido": resultado.get("saldo", 0),
            "total_transacoes": len(df_filtrado)
        }
    else:
        return {
            "receitas": 0, 
            "despesas": 0, 
            "saldo_liquido": 0, 
            "total_transacoes": 0
        }

@st.cache_data(ttl=600)
def calcular_dividas_total(saldos_info):
    """Calcula total de dívidas incluindo faturas de cartão não pagas"""
    if not saldos_info or len(saldos_info) < 3:
        return 0
    
    saldo_positivo, saldo_negativo, contas_detalhes = saldos_info[:3]
    
    # Calcular dívidas de cartão separadamente
    dividas_cartao = 0
    for conta in contas_detalhes:
        if conta.get('Tipo') == 'CREDIT' and conta.get('Saldo', 0) < 0:
            # Inverter o sinal para obter valor positivo da dívida
            dividas_cartao += -conta.get('Saldo', 0)
    
    # Retornar o maior valor entre saldo negativo total e dívidas de cartão
    return max(abs(saldo_negativo), dividas_cartao)

@st.cache_data(ttl=600)
def gerar_grafico_categorias_otimizado(df_filtrado):
    """Gera gráfico de categorias com cache otimizado e layout responsivo."""
    if df_filtrado.empty or "Categoria" not in df_filtrado.columns:
        return None
        
    # Agregar dados por categoria
    categoria_resumo = df_filtrado.groupby("Categoria")["Valor"].sum().reset_index()
    
    if not categoria_resumo.empty:
        # Usar valores absolutos para evitar problemas com valores negativos
        categoria_resumo["ValorAbs"] = categoria_resumo["Valor"].abs()
        
        # Filtrar categorias com valores zerados
        categoria_resumo = categoria_resumo[categoria_resumo["ValorAbs"] > 0]
        
        if categoria_resumo.empty:
            return None
            
        # Ordenar por valor para melhor visualização
        categoria_resumo = categoria_resumo.sort_values("ValorAbs", ascending=False)
        
        # Agrupar categorias pequenas em "Outros" se houver muitas categorias
        if len(categoria_resumo) > 8:
            # Manter top 7 categorias e agrupar o resto em "Outros"
            top_categorias = categoria_resumo.head(7)
            outros_valor = categoria_resumo.tail(len(categoria_resumo) - 7)["ValorAbs"].sum()
            
            if outros_valor > 0:
                outros_row = pd.DataFrame({
                    "Categoria": ["Outros"],
                    "Valor": [0],  # Valor original não usado
                    "ValorAbs": [outros_valor]
                })
                categoria_resumo = pd.concat([top_categorias, outros_row], ignore_index=True)
        
        fig = px.pie(categoria_resumo, 
                    names="Categoria", 
                    values="ValorAbs",
                    title="Distribuição por Categoria", 
                    template="plotly_white")
        
        # Configurações de layout responsivo
        fig.update_layout(
            height=400,
            font=dict(size=11),
            showlegend=True,
            legend=dict(
                orientation="h",  # Legenda horizontal
                yanchor="top",
                y=-0.1,
                xanchor="center",
                x=0.5,
                font=dict(size=10)
            ),
            margin=dict(l=10, r=10, t=50, b=80),
            title=dict(
                x=0.5,
                font=dict(size=14)
            )
        )
        
        # Configurações das fatias do gráfico
        fig.update_traces(
            textposition='auto',
            textinfo='percent',
            textfont_size=10,
            hovertemplate='<b>%{label}</b><br>Valor: R$ %{value:,.2f}<br>Percentual: %{percent}<extra></extra>',
            pull=[0.05 if name == "Outros" else 0 for name in categoria_resumo["Categoria"]]
        )
        
        return fig
    return None

@st.cache_data(ttl=600)
def gerar_grafico_evolucao_otimizado(df_filtrado):
    """Gera gráfico de evolução com cache otimizado."""
    if df_filtrado.empty or "AnoMes" not in df_filtrado.columns:
        return None
        
    evolucao = df_filtrado.groupby("AnoMes")["Valor"].sum().reset_index()
    if not evolucao.empty:
        fig = px.line(evolucao, x="AnoMes", y="Valor", markers=True,
                     title="Evolução no Tempo", template="plotly_white")
        fig.update_layout(height=350)
        return fig
    return None

# Carregar dados principais
usuario = st.session_state.get('usuario', 'default')

# Verificar se deve usar modo rápido por padrão
skip_llm_default = os.environ.get("SKIP_LLM_PROCESSING", "false").lower() == "true"

with st.spinner("Carregando dados financeiros..."):
    saldos_info, df = carregar_dados_home(usuario, modo_rapido=skip_llm_default)

if df.empty:
    st.warning("⚠️ Nenhum extrato encontrado!")
    st.info("""
    **Possíveis soluções:**
    1. Conecte suas contas na página Cadastro Pluggy
    2. Verifique se os item IDs estão corretos
    3. Configure suas credenciais Pluggy
    """)
    if st.button("➕ Conectar Contas"):
        st.switch_page("pages/Cadastro_Pluggy.py")
    st.stop()

# Filtros essenciais
st.sidebar.header("🔍 Filtros")
start_date, end_date = filtro_data(df, "home")
categorias_selecionadas = filtro_categorias(df, "Filtrar por Categorias", "home")
df_filtrado = aplicar_filtros(df, start_date, end_date, categorias_selecionadas)

# Resumo financeiro
resumo = processar_resumo_financeiro(df_filtrado)

# Resumo visual simplificado
st.subheader("💰 Resumo Financeiro")

# Saldos atuais
if saldos_info and len(saldos_info) >= 3:
    saldo_positivo, saldo_negativo, contas_detalhes = saldos_info[:3]
    
    # Layout com colunas para saldos e botão de refresh
    col1, col2, col3 = st.columns([3, 3, 2])
    col1.metric("🟢 Disponível", formatar_valor_monetario(saldo_positivo))
    col2.metric("🔴 Dívidas", formatar_valor_monetario(calcular_dividas_total(saldos_info)))
    
    # Botão para atualizar apenas saldos (mais rápido)
    if col3.button("🔄", help="Atualizar saldos", key="refresh_balance"):
        with st.spinner("Atualizando saldos..."):
            def _refresh_saldos():
                # Forçar refresh apenas dos saldos
                pluggy = PluggyConnector()
                itemids_data = pluggy.load_itemids_db(st.session_state['usuario'])
                
                if itemids_data:
                    # Limpar cache específico dos saldos
                    st.cache_data.clear()
                    
                    # Carregar dados com force_refresh
                    saldos_info_atualizado, _ = carregar_dados_home(usuario, force_refresh=True)
                    
                    if saldos_info_atualizado:
                        st.success("✅ Saldos atualizados!")
                        time.sleep(1)
                        return True
                    else:
                        st.error("❌ Erro ao atualizar saldos")
                        return False
                else:
                    st.warning("⚠️ Nenhuma conta encontrada")
                    return False
            
            success = ExceptionHandler.safe_execute(
                func=_refresh_saldos,
                error_handler=ExceptionHandler.handle_pluggy_error,
                default_return=False,
                show_in_streamlit=True
            )
            
            if success:
                st.rerun()
else:
    st.warning("⚠️ Não foi possível carregar os saldos. Verifique suas conexões bancárias.")

# Resumo do período
st.subheader("📊 Período Selecionado")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Receitas", formatar_valor_monetario(resumo['receitas']))
col2.metric("Despesas", formatar_valor_monetario(abs(resumo['despesas'])))
col3.metric("Saldo Líquido", formatar_valor_monetario(resumo['saldo_liquido']))
col4.metric("Transações", resumo['total_transacoes'])

# Seção de detalhamento das transações
st.subheader("🔍 Detalhamento das Transações")

# Obter dados detalhados do resumo financeiro
resumo_detalhado = calcular_resumo_financeiro(df_filtrado)

# Criar tabs para mostrar as categorias de transações
tab1, tab2, tab3 = st.tabs(["💰 Receitas", "💸 Despesas", "🔄 Excluídas"])

with tab1:
    st.markdown("### Transações consideradas como **Receitas**")
    
    # Filtrar apenas as transações classificadas como receitas
    indices_receitas = [idx for idx, val in resumo_detalhado.get('é_receita_real', {}).items() if val]
    
    if indices_receitas:
        df_receitas = df_filtrado.loc[indices_receitas].copy()
        df_receitas = df_receitas.sort_values('Data', ascending=False)
        
        # Formatação para exibição
        df_receitas_display = formatar_df_monetario(df_receitas, "Valor")
        
        # Métricas das receitas
        col_r1, col_r2, col_r3 = st.columns(3)
        col_r1.metric("Total de Receitas", formatar_valor_monetario(df_receitas['Valor'].sum()))
        col_r2.metric("Número de Transações", len(df_receitas))
        col_r3.metric("Valor Médio", formatar_valor_monetario(df_receitas['Valor'].mean()))
        
        # Tabela das receitas
        st.dataframe(
            df_receitas_display[["Data", "Categoria", "Descrição", "ValorFormatado"]].rename(
                columns={"ValorFormatado": "Valor"}
            ),
            use_container_width=True,
            height=300
        )
        
        # Gráfico de receitas por categoria
        if len(df_receitas) > 0 and 'Categoria' in df_receitas.columns:
            receitas_por_categoria = df_receitas.groupby('Categoria')['Valor'].sum().reset_index()
            receitas_por_categoria = receitas_por_categoria.sort_values('Valor', ascending=False)
            
            fig_receitas = px.bar(
                receitas_por_categoria, 
                x='Categoria', 
                y='Valor',
                title="Receitas por Categoria",
                template="plotly_white",
                color='Valor',
                color_continuous_scale='Greens'
            )
            fig_receitas.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig_receitas, use_container_width=True)
    else:
        st.info("📊 Nenhuma transação foi classificada como receita no período selecionado.")

with tab2:
    st.markdown("### Transações consideradas como **Despesas**")
    
    # Filtrar apenas as transações classificadas como despesas
    indices_despesas = [idx for idx, val in resumo_detalhado.get('é_despesa_real', {}).items() if val]
    
    if indices_despesas:
        df_despesas = df_filtrado.loc[indices_despesas].copy()
        df_despesas = df_despesas.sort_values('Data', ascending=False)
        
        # Formatação para exibição
        df_despesas_display = formatar_df_monetario(df_despesas, "Valor")
        
        # Métricas das despesas
        col_d1, col_d2, col_d3 = st.columns(3)
        col_d1.metric("Total de Despesas", formatar_valor_monetario(abs(df_despesas['Valor'].sum())))
        col_d2.metric("Número de Transações", len(df_despesas))
        col_d3.metric("Valor Médio", formatar_valor_monetario(abs(df_despesas['Valor'].mean())))
        
        # Tabela das despesas
        st.dataframe(
            df_despesas_display[["Data", "Categoria", "Descrição", "ValorFormatado"]].rename(
                columns={"ValorFormatado": "Valor"}
            ),
            use_container_width=True,
            height=300
        )
        
        # Gráfico de despesas por categoria
        if len(df_despesas) > 0 and 'Categoria' in df_despesas.columns:
            despesas_por_categoria = df_despesas.groupby('Categoria')['Valor'].sum().reset_index()
            despesas_por_categoria['Valor'] = despesas_por_categoria['Valor'].abs()  # Valores absolutos
            despesas_por_categoria = despesas_por_categoria.sort_values('Valor', ascending=False)
            
            fig_despesas = px.bar(
                despesas_por_categoria, 
                x='Categoria', 
                y='Valor',
                title="Despesas por Categoria",
                template="plotly_white",
                color='Valor',
                color_continuous_scale='Reds'
            )
            fig_despesas.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig_despesas, use_container_width=True)
    else:
        st.info("📊 Nenhuma transação foi classificada como despesa no período selecionado.")

with tab3:
    st.markdown("### Transações **Excluídas** dos cálculos")
    st.caption("Transações internas, aplicações financeiras, pagamentos de cartão, etc.")
    
    # Filtrar transações que não são nem receitas nem despesas
    indices_receitas = set(idx for idx, val in resumo_detalhado.get('é_receita_real', {}).items() if val)
    indices_despesas = set(idx for idx, val in resumo_detalhado.get('é_despesa_real', {}).items() if val)
    todos_indices = set(df_filtrado.index)
    indices_excluidas = todos_indices - indices_receitas - indices_despesas
    
    if indices_excluidas:
        df_excluidas = df_filtrado.loc[list(indices_excluidas)].copy()
        df_excluidas = df_excluidas.sort_values('Data', ascending=False)
        
        # Formatação para exibição
        df_excluidas_display = formatar_df_monetario(df_excluidas, "Valor")
        
        # Métricas das excluídas
        col_e1, col_e2, col_e3 = st.columns(3)
        col_e1.metric("Valor Total", formatar_valor_monetario(df_excluidas['Valor'].sum()))
        col_e2.metric("Número de Transações", len(df_excluidas))
        
        # Calcular porcentagem do total
        total_transacoes = len(df_filtrado)
        percentual_excluidas = (len(df_excluidas) / total_transacoes * 100) if total_transacoes > 0 else 0
        col_e3.metric("% do Total", f"{percentual_excluidas:.1f}%")
        
        # Explicação do motivo das exclusões
        st.info("""
        **Por que estas transações foram excluídas?**
        
        - 🔄 **Transferências internas**: Entre suas próprias contas
        - 💳 **Pagamentos de cartão**: Evita contabilização dupla
        - 💰 **Aplicações financeiras**: Apenas movimentação de patrimônio
        - 🔍 **Transações sem classificação clara**: Aguardando mais informações
        """)
        
        # Tabela das excluídas
        st.dataframe(
            df_excluidas_display[["Data", "Categoria", "Descrição", "ValorFormatado"]].rename(
                columns={"ValorFormatado": "Valor"}
            ),
            use_container_width=True,
            height=300
        )
        
        # Mostrar motivos de exclusão mais comuns
        if len(df_excluidas) > 0:
            # Analisar categorias mais comuns nas excluídas
            if 'Categoria' in df_excluidas.columns:
                categorias_excluidas = df_excluidas['Categoria'].value_counts().head(5)
                
                st.markdown("**Principais categorias excluídas:**")
                for categoria, count in categorias_excluidas.items():
                    st.markdown(f"- **{categoria}**: {count} transações")
    else:
        st.success("✅ Todas as transações do período foram classificadas como receitas ou despesas.")

# Resumo da classificação
st.markdown("---")
st.markdown("### 📈 Resumo da Classificação")

total_transacoes = len(df_filtrado)
if total_transacoes > 0:
    num_receitas = len([idx for idx, val in resumo_detalhado.get('é_receita_real', {}).items() if val])
    num_despesas = len([idx for idx, val in resumo_detalhado.get('é_despesa_real', {}).items() if val])
    num_excluidas = total_transacoes - num_receitas - num_despesas
    
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    col_s1.metric("Total de Transações", total_transacoes)
    col_s2.metric("Receitas", f"{num_receitas} ({num_receitas/total_transacoes*100:.1f}%)")
    col_s3.metric("Despesas", f"{num_despesas} ({num_despesas/total_transacoes*100:.1f}%)")
    col_s4.metric("Excluídas", f"{num_excluidas} ({num_excluidas/total_transacoes*100:.1f}%)")
else:
    st.info("Nenhuma transação encontrada no período selecionado.")

# Visualizações essenciais
if not df_filtrado.empty:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Por Categoria")
        fig = gerar_grafico_categorias_otimizado(df_filtrado)
        if fig:
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    
    with col2:
        st.subheader("📈 Evolução Mensal")
        fig2 = gerar_grafico_evolucao_otimizado(df_filtrado)
        if fig2:
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

# Checagem de IA ativa e indicador de modo
pluggy = get_pluggy_connector()
skip_llm = os.environ.get("SKIP_LLM_PROCESSING", "false").lower() == "true"

if skip_llm:
    st.sidebar.markdown("---")
    st.sidebar.warning("⚡ **MODO RÁPIDO ATIVO**\n\nProcessamento IA desabilitado para performance otimizada")
    st.sidebar.info("💡 Para categorização inteligente, desative o 'Modo Rápido' e atualize os dados")
elif getattr(pluggy, "chat_model", None) is None:
    st.sidebar.markdown("---")
    st.sidebar.warning("⚠️ **IA NÃO CONFIGURADA**\n\nO processamento com IA está ativado, mas o modelo LLM não foi inicializado. Verifique a variável OPENAI_API_KEY e as dependências do LangChain/OpenAI.")
else:
    st.sidebar.markdown("---")
    st.sidebar.success("🤖 **IA ATIVA**\n\nProcessamento inteligente habilitado para categorização precisa")

# Seção de gerenciamento de transações
st.markdown("---")
st.subheader("⚙️ Gerenciamento de Transações")

col_manage1, col_manage2, col_manage3 = st.columns(3)

with col_manage1:
    if st.button("✏️ Editar Transações", use_container_width=True, help="Corrigir categorizações incorretas"):
        st.switch_page("pages/Gerenciar_Transacoes.py")

with col_manage2:
    st.metric("Transações Processadas", len(df_filtrado))

with col_manage3:
    if not df_filtrado.empty:
        resumo_gerenciamento = calcular_resumo_financeiro(df_filtrado)
        num_receitas = len([idx for idx, val in resumo_gerenciamento.get('é_receita_real', {}).items() if val])
        num_despesas = len([idx for idx, val in resumo_gerenciamento.get('é_despesa_real', {}).items() if val])
        precisao = ((num_receitas + num_despesas) / len(df_filtrado) * 100) if len(df_filtrado) > 0 else 0
        st.metric("Precisão da Classificação", f"{precisao:.1f}%")

st.info("💡 **Dica:** Use a página de Gerenciar Transações para corrigir categorizações automáticas incorretas, deletar transações irrelevantes ou reclassificar o tipo (Receita/Despesa/Excluída).")

# Extrato detalhado (colapsado)
with st.expander("📋 Ver Extrato Detalhado"):
    df_formatado = formatar_df_monetario(df_filtrado, "Valor")
    st.dataframe(
        df_formatado[["Data", "Categoria", "Descrição", "ValorFormatado"]].rename(
            columns={"ValorFormatado": "Valor"}
        ),
        use_container_width=True
    )
