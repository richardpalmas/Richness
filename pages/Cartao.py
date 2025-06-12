import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta
from dotenv import load_dotenv

from componentes.profile_pic_component import boas_vindas_com_foto
from database import get_connection
from utils.auth import verificar_autenticacao
from utils.filtros import filtro_data, filtro_categorias, aplicar_filtros
from utils.formatacao import formatar_valor_monetario, formatar_df_monetario
from utils.ofx_reader import OFXReader
from utils.exception_handler import ExceptionHandler

# Configuração da página
st.set_page_config(page_title="Cartão de Crédito", layout="wide")

# Verificação de autenticação
verificar_autenticacao()
usuario = st.session_state.get('usuario', 'default')

# Exibição de foto de perfil e mensagem de boas-vindas
if usuario:
    boas_vindas_com_foto(usuario)

st.title("💳 Cartão de Crédito")

# Cache do leitor OFX
@st.cache_resource(ttl=300)
def get_ofx_reader():
    return OFXReader()

# Interface de seleção simplificada
st.subheader("📅 Período de Análise")

# Calcular período padrão: 6 meses antes até hoje
data_atual = date.today()
data_inicio_padrao = data_atual - timedelta(days=180)  # Aproximadamente 6 meses

col1, col2 = st.columns(2)
with col1:
    data_inicio = st.date_input("Data inicial", value=data_inicio_padrao)
with col2:
    data_fim = st.date_input("Data final", value=data_atual)

# Obter leitor OFX
ofx_reader = get_ofx_reader()

# Verificar arquivos disponíveis
resumo_arquivos = ofx_reader.get_resumo_arquivos()

st.subheader("💳 Arquivos de Fatura Disponíveis")
if resumo_arquivos['total_faturas'] == 0:
    st.warning("⚠️ Nenhuma fatura de cartão encontrada!")
    st.info("💡 **Como adicionar faturas:**")
    st.markdown("""
    1. 📁 Baixe suas faturas de cartão em formato .ofx do seu banco
    2. 📂 Coloque os arquivos na pasta `faturas/`
    3. 🔄 Atualize a página
    """)
    st.stop()

# Mostrar informações dos arquivos
col1, col2 = st.columns(2)
with col1:
    st.metric("📄 Total de Faturas", resumo_arquivos['total_faturas'])
with col2:
    if resumo_arquivos['periodo_faturas']['inicio']:
        periodo_texto = f"{resumo_arquivos['periodo_faturas']['inicio']} a {resumo_arquivos['periodo_faturas']['fim']}"
        st.text(f"Período: {periodo_texto}")

# Buscar dados com cache
@st.cache_data(ttl=600, show_spinner="Carregando transações...")
def carregar_dados_cartoes(dias):
    """Carregar dados de cartões com cache"""
    def _load_data():
        ofx_reader = get_ofx_reader()
        df = ofx_reader.buscar_cartoes(dias)
        
        if not df.empty:
            # Garantir que as colunas estão no formato correto
            df["Data"] = pd.to_datetime(df["Data"])
            df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")
            
            # Remover valores nulos
            df = df.dropna(subset=["Valor"])
            
            # Ordenar por data (mais recente primeiro)
            df = df.sort_values("Data", ascending=False)
        
        return df
    
    return ExceptionHandler.safe_execute(
        func=_load_data,
        error_handler=ExceptionHandler.handle_generic_error,
        default_return=pd.DataFrame()
    )

# Calcular dias entre as datas
dias_periodo = (data_fim - data_inicio).days

# Carregar dados
df_cartoes = carregar_dados_cartoes(dias_periodo)

# Verificar se existem dados
if df_cartoes.empty:
    st.warning("📭 Nenhuma transação de cartão encontrada no período selecionado!")
    st.info("Tente ajustar o período de análise ou verificar se há arquivos de fatura na pasta `faturas/`.")
    st.stop()

# Aplicar filtro de data aos dados carregados
df_cartoes_filtrado = df_cartoes[
    (df_cartoes["Data"].dt.date >= data_inicio) & 
    (df_cartoes["Data"].dt.date <= data_fim)
]

if df_cartoes_filtrado.empty:
    st.warning("🔍 Nenhuma transação encontrada no período selecionado.")
    st.stop()

# Filtros adicionais
st.subheader("🔍 Filtros Avançados")
col1, col2 = st.columns(2)

with col2:
    categorias_selecionadas = filtro_categorias(df_cartoes_filtrado)

# Aplicar filtros
df_final = aplicar_filtros(df_cartoes_filtrado, data_inicio, data_fim, categorias_selecionadas)

if df_final.empty:
    st.warning("🔍 Nenhuma transação encontrada com os filtros aplicados.")
    st.stop()

# Resumo financeiro
st.subheader("📊 Resumo do Cartão")

# Calcular métricas
total_gastos = df_final["Valor"].sum()
num_transacoes = len(df_final)
gasto_medio = total_gastos / num_transacoes if num_transacoes > 0 else 0
maior_gasto = df_final["Valor"].min() if not df_final.empty else 0  # Min porque valores negativos

# Exibir métricas
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "💸 Total de Gastos", 
        formatar_valor_monetario(abs(total_gastos))
    )

with col2:
    st.metric(
        "📊 Número de Transações", 
        f"{num_transacoes:,}"
    )

with col3:
    st.metric(
        "💰 Gasto Médio", 
        formatar_valor_monetario(abs(gasto_medio))
    )

with col4:
    st.metric(
        "🔥 Maior Gasto", 
        formatar_valor_monetario(abs(maior_gasto))
    )

# Gráficos de análise
st.subheader("📈 Análises")

col1, col2 = st.columns(2)

with col1:
    # Gráfico de gastos por categoria
    if "Categoria" in df_final.columns:
        categoria_gastos = df_final.groupby("Categoria")["Valor"].sum().reset_index()
        categoria_gastos["Valor_Abs"] = categoria_gastos["Valor"].abs()
        categoria_gastos = categoria_gastos.sort_values("Valor_Abs", ascending=False)
        
        fig_categorias = px.pie(
            categoria_gastos,
            names="Categoria",
            values="Valor_Abs",
            title="Gastos por Categoria",
            template="plotly_white"
        )
        
        fig_categorias.update_layout(height=400)
        st.plotly_chart(fig_categorias, use_container_width=True)

with col2:
    # Gráfico de evolução temporal
    df_temp = df_final.copy()
    df_temp["Mes"] = df_temp["Data"].dt.to_period("M").astype(str)
    evolucao_mensal = df_temp.groupby("Mes")["Valor"].sum().reset_index()
    evolucao_mensal["Valor_Abs"] = evolucao_mensal["Valor"].abs()
    
    fig_evolucao = px.bar(
        evolucao_mensal,
        x="Mes",
        y="Valor_Abs",
        title="Gastos Mensais",
        template="plotly_white"
    )
    
    fig_evolucao.update_layout(height=400)
    st.plotly_chart(fig_evolucao, use_container_width=True)

# Top gastos
st.subheader("🔝 Maiores Gastos")
top_gastos = df_final.nsmallest(10, "Valor")[["Data", "Descrição", "Valor", "Categoria"]]
top_gastos["Valor"] = top_gastos["Valor"].abs()
top_gastos = formatar_df_monetario(top_gastos)

st.dataframe(top_gastos, use_container_width=True)

# Tabela completa de transações
st.subheader("📋 Todas as Transações")

# Preparar dados para exibição
df_display = df_final.copy()
df_display["Valor"] = df_display["Valor"].abs()  # Mostrar valores positivos
df_display = formatar_df_monetario(df_display)

# Paginação simples
num_registros = st.selectbox(
    "Registros por página:", 
    [25, 50, 100, 200], 
    index=1
)

st.dataframe(
    df_display.head(num_registros),
    use_container_width=True,
    height=400
)

# Informações adicionais
with st.expander("ℹ️ Informações Técnicas"):
    st.write(f"**Período analisado:** {data_inicio} a {data_fim}")
    st.write(f"**Total de registros:** {len(df_final):,}")
    st.write(f"**Arquivos processados:** {resumo_arquivos['total_faturas']} faturas")
    
    if resumo_arquivos['periodo_faturas']['inicio']:
        st.write(f"**Período dos arquivos:** {resumo_arquivos['periodo_faturas']['inicio']} a {resumo_arquivos['periodo_faturas']['fim']}")
    
    # Botão para limpar cache
    if st.button("🧹 Limpar Cache"):
        ofx_reader.limpar_cache()
        st.cache_data.clear()
        st.success("Cache limpo! Recarregue a página para ver os dados atualizados.")
