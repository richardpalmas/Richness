import pandas as pd
import plotly.express as px
import streamlit as st
import time
import os

from componentes.profile_pic_component import boas_vindas_com_foto
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

# Exibir foto de perfil e mensagem de boas-vindas
if 'usuario' in st.session_state:
    boas_vindas_com_foto(st.session_state['usuario'])

# Inicializar estado para confirmação de remoção
if 'confirmando_remocao' not in st.session_state:
    st.session_state['confirmando_remocao'] = False

# Inicializar estado para modo de carregamento
if 'carregamento_rapido' not in st.session_state:
    st.session_state['carregamento_rapido'] = True  # Padrão: carregamento rápido

# Controles de Performance na Sidebar
st.sidebar.markdown("### ⚡ Controles de Performance")

# Botão para atualizar dados com sincronização forçada da API Pluggy
if st.sidebar.button("🔄 Atualizar Dados", help="Força busca de dados frescos da API e sincronização dos itens bancários"):
    pluggy = PluggyConnector()
    
    # Exibir status de carregamento
    with st.sidebar:
        status_container = st.empty()
        status_container.info("🔄 Iniciando atualização...")
    
    def _update_items():
        # 1. Obter lista de itens do usuário
        itemids_data = PluggyConnector.load_itemids_db(st.session_state['usuario'])
        
        if itemids_data:
            status_container.info(f"🔄 Forçando sincronização de {len(itemids_data)} itens bancários...")
            
            # 2. Testar conectividade e forçar refresh dos dados
            sucesso = 0
            erro = 0
            
            # Primeiro, testar a autenticação
            if pluggy.testar_autenticacao():
                # Limpar cache para forçar dados frescos
                pluggy.limpar_cache()
                
                # Testar cada item ID individualmente
                for item in itemids_data:
                    if pluggy.testar_item_id(item['item_id']):
                        sucesso += 1
                    else:
                        erro += 1
                
                # 3. Mostrar resultados da sincronização
                if sucesso > 0:
                    status_container.success(f"✅ {sucesso} itens validados com sucesso!")
                if erro > 0:
                    status_container.warning(f"⚠️ {erro} itens com erro ou inválidos")
            else:
                status_container.error("❌ Falha na autenticação com a API Pluggy")
                erro = len(itemids_data)
            
            # 4. Aguardar um momento para completar
            time.sleep(2)
            status_container.info("🔄 Limpando cache e recarregando dados...")
        else:
            status_container.warning("⚠️ Nenhum item bancário encontrado para sincronizar")
        
        # 5. Limpar caches
        st.cache_data.clear()
        pluggy.limpar_cache()
        
        status_container.success("✅ Atualização concluída! Dados sincronizados.")
        time.sleep(1)
        return True
    
    success = ExceptionHandler.safe_execute(
        func=_update_items,
        error_handler=ExceptionHandler.handle_pluggy_error,
        default_return=False,
        show_in_streamlit=True
    )
    
    if success:
        st.rerun()

carregamento_rapido = st.sidebar.checkbox(
    "Carregamento Rápido (sem IA)", 
    value=st.session_state.get('carregamento_rapido', True),
    help="Desabilita processamento de IA para carregamento mais rápido. Use 'Processar com IA' depois para categorização completa."
)

# Atualizar variável de ambiente com base na escolha
import os
os.environ["SKIP_LLM_PROCESSING"] = "true" if carregamento_rapido else "false"
st.session_state['carregamento_rapido'] = carregamento_rapido

# Botão para processar com IA após carregamento rápido
if carregamento_rapido:
    if st.sidebar.button("🤖 Processar com IA", help="Aplica categorização e enriquecimento de IA aos dados já carregados"):
        # Limpar cache para forçar reprocessamento com IA
        pluggy = PluggyConnector()
        pluggy.limpar_cache()
        os.environ["SKIP_LLM_PROCESSING"] = "false"
        st.cache_data.clear()
        st.sidebar.success("Processamento com IA concluído!")
        st.rerun()

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
def carregar_dados_home(usuario, force_refresh=False):
    """Carrega dados essenciais para a Home com cache otimizado"""
    def _load_data():
        pluggy = get_pluggy_connector()
        itemids_data = pluggy.load_itemids_db(usuario)
        
        if not itemids_data:
            return None, pd.DataFrame()
        
        # Se force_refresh for True, limpar cache
        if force_refresh:
            pluggy.limpar_cache()
        
        # Carregar dados essenciais
        saldos_info = pluggy.obter_saldo_atual(itemids_data)
        df = pluggy.buscar_extratos(itemids_data)
        
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
    """Gera gráfico de categorias com cache otimizado."""
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
        
        fig = px.pie(categoria_resumo, 
                    names="Categoria", 
                    values="ValorAbs",
                    title="Distribuição por Categoria", 
                    template="plotly_white")
        
        # Configurações de layout para melhor alinhamento
        fig.update_layout(
            height=350,
            font=dict(size=12),
            legend=dict(
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=1.01
            ),
            margin=dict(l=20, r=80, t=50, b=20)
        )
        
        # Configurações das fatias do gráfico
        fig.update_traces(
            textposition='inside',
            textinfo='percent+label',
            textfont_size=10,
            pull=[0.1 if name == "Outros" else 0 for name in categoria_resumo["Categoria"]]
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
with st.spinner("Carregando dados financeiros..."):
    saldos_info, df = carregar_dados_home(usuario)

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

# Extrato detalhado (colapsado)
with st.expander("📋 Ver Extrato Detalhado"):
    df_formatado = formatar_df_monetario(df_filtrado, "Valor")
    st.dataframe(
        df_formatado[["Data", "Categoria", "Descrição", "ValorFormatado"]].rename(
            columns={"ValorFormatado": "Valor"}
        ),
        use_container_width=True
    )
