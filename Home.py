import pandas as pd
import plotly.express as px
import streamlit as st

from componentes.profile_pic_component import boas_vindas_com_foto
from database import get_connection, create_tables, remover_usuario
from utils.config import ENABLE_CACHE
from utils.filtros import filtro_data, filtro_categorias, aplicar_filtros
from utils.formatacao import formatar_valor_monetario, formatar_df_monetario, calcular_resumo_financeiro
from utils.pluggy_connector import PluggyConnector

st.set_page_config(layout="wide")

# Inicializar banco e tabelas
create_tables()


def autenticar_usuario(usuario, senha):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT nome, senha FROM usuarios WHERE usuario = ?', (usuario,))
    row = cur.fetchone()
    # Não fechamos a conexão aqui, pois é gerenciada pelo get_connection()
    if row and senha == row['senha']:
        st.session_state['nome'] = row['nome']
        return True
    return False


# --- LOGIN E AUTENTICAÇÃO ---
# Exibe campos de login apenas se não estiver autenticado
if 'autenticado' not in st.session_state or not isinstance(st.session_state['autenticado'], bool):
    st.session_state['autenticado'] = False
if 'usuario' not in st.session_state or not isinstance(st.session_state['usuario'], str):
    st.session_state['usuario'] = ''

login_placeholder = st.sidebar.empty()
show_login = not st.session_state.get('autenticado', False)

if show_login:
    with login_placeholder:
        with st.form(key='login_form'):
            st.header('Login')
            usuario_input = st.text_input('Usuário', key='usuario_login', label_visibility='visible')
            senha_input = st.text_input('Senha', type='password', key='senha_login', label_visibility='visible')
            login_btn = st.form_submit_button('Entrar')
            if login_btn:
                if autenticar_usuario(usuario_input, senha_input):
                    st.session_state['autenticado'] = True
                    st.session_state['usuario'] = usuario_input
                    st.rerun()
                else:
                    st.session_state['autenticado'] = False
                    st.error('Usuário ou senha incorretos')
else:
    login_placeholder.empty()

    # Botão de Sair
    if st.sidebar.button('Sair'):
        st.session_state['autenticado'] = False
        st.session_state['usuario'] = ''
        st.rerun()

if not st.session_state.get('autenticado', False):
    st.stop()

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

# Botão para limpar cache (útil para forçar atualização dos dados)
if ENABLE_CACHE and st.sidebar.button("🔄 Atualizar dados"):
    # Limpar cache do Pluggy Connector
    pluggy = PluggyConnector()
    pluggy.limpar_cache()
    
    # Limpar todos os caches do Streamlit desta sessão
    st.cache_data.clear()
    
    st.sidebar.success("Cache limpo! Os dados serão recarregados.")
    st.rerun()

# Botão Remover Usuário abaixo do botão Atualizar dados
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
def carregar_dados_home(usuario):
    """Carrega dados essenciais para a Home com cache otimizado"""
    pluggy = get_pluggy_connector()
    itemids_data = pluggy.load_itemids_db(usuario)
    
    if not itemids_data:
        return None, pd.DataFrame()
    
    # Carregar dados essenciais
    saldos_info = pluggy.obter_saldo_atual(itemids_data)
    df = pluggy.buscar_extratos(itemids_data)
    
    # Pré-processamento mínimo
    if not df.empty:
        df["Data"] = pd.to_datetime(df["Data"])
        df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")
        df["AnoMes"] = df["Data"].dt.strftime("%Y-%m")
    
    return saldos_info, df

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
    
    saldo_positivo, saldo_negativo, contas_detalhes, saldo_total = saldos_info
    
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
if saldos_info and len(saldos_info) >= 4:
    saldo_positivo, saldo_negativo, contas_detalhes, saldo_total = saldos_info
    
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Saldo Total", formatar_valor_monetario(saldo_total))
    col2.metric("🟢 Disponível", formatar_valor_monetario(saldo_positivo))
    col3.metric("🔴 Dívidas", formatar_valor_monetario(calcular_dividas_total(saldos_info)))

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
