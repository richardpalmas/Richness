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
from utils.pluggy_connector import PluggyConnector

# Configuração da página
st.set_page_config(page_title="Cartão de Crédito", layout="wide")

# Verificação de autenticação
verificar_autenticacao()
usuario = st.session_state.get('usuario', 'default')

# Exibição de foto de perfil e mensagem de boas-vindas
if usuario:
    boas_vindas_com_foto(usuario)

st.title("💳 Cartão de Crédito")

# Cache do conector
@st.cache_resource(ttl=300)
def get_pluggy_connector():
    return PluggyConnector()

# Funções auxiliares otimizadas
@st.cache_data(ttl=300)
def get_usuario_id(usuario):
    """Obter ID do usuário com cache"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT id FROM usuarios WHERE usuario = ?', (usuario,))
    row = cur.fetchone()
    return row[0] if row else None

@st.cache_data(ttl=300)
def load_items_db(usuario):
    """Carregar itemIds do usuário com cache"""
    usuario_id = get_usuario_id(usuario)
    if usuario_id is None:
        return []
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT item_id, nome FROM pluggy_items WHERE usuario_id = ?', (usuario_id,))
    return [{'item_id': row['item_id'], 'nome': row['nome']} for row in cur.fetchall()]

# Carregar dados
itemids_data = load_items_db(usuario)

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

st.subheader("💳 Selecionar Cartões")
if itemids_data:
    opcoes = [f"{item['nome']}" for item in itemids_data]
    selecionados = st.multiselect("Escolha seus cartões:", opcoes, default=opcoes)
    item_ids = [item['item_id'] for item in itemids_data if item['nome'] in selecionados]
else:
    st.warning("⚠️ Nenhuma conexão Pluggy encontrada!")
    if st.button("➕ Conectar Cartões"):
        st.switch_page("pages/Cadastro_Pluggy.py")
    st.stop()

# Validação
if not item_ids:
    st.info("👆 Selecione pelo menos um cartão para continuar.")
    st.stop()

# Buscar dados com cache
@st.cache_data(ttl=600, show_spinner="Carregando transações...")
def buscar_dados_cartoes(item_ids_tuple, data_inicio_str, data_fim_str):
    """Buscar dados dos cartões com cache"""
    pluggy = get_pluggy_connector()
    item_data = [{'item_id': item_id, 'nome': item_id} for item_id in item_ids_tuple]
    return pluggy.buscar_cartoes(item_data)

# Converter para tipos compatíveis com cache
df = buscar_dados_cartoes(tuple(item_ids), str(data_inicio), str(data_fim))

# Filtrar apenas transações de cartão de crédito (TipoConta)
if 'TipoConta' in df.columns:
    df = df[df['TipoConta'] == 'CREDIT']
    df = df.drop(columns=['TipoConta'])

if df.empty:
    st.error("❌ Nenhuma transação encontrada para o período selecionado.")
    st.info("💡 Tente:")
    st.markdown("- Expandir o período de busca")
    st.markdown("- Verificar se os cartões têm movimentações")
    st.markdown("- Conferir se as conexões estão ativas")
# Preparação e limpeza dos dados
if "ID" in df.columns:
    df = df.drop("ID", axis=1)

df["Data"] = pd.to_datetime(df["Data"])
df["Ano"] = df["Data"].dt.year
df["Mes"] = df["Data"].dt.month
df["AnoMes"] = df["Data"].dt.strftime("%Y-%m")
df["Valor"] = pd.to_numeric(df["Valor"], errors='coerce')

# Filtrar por data selecionada
df = df[(df['Data'].dt.date >= data_inicio) & (df['Data'].dt.date <= data_fim)]

# Aplicação de filtros usando componentes centralizados
st.sidebar.header("🔍 Filtros")
start_date, end_date = filtro_data(df, "cartao")
categorias_selecionadas = filtro_categorias(df, "Filtrar por Categorias", "cartao")
df_filtered = aplicar_filtros(df, start_date, end_date, categorias_selecionadas)

if df_filtered.empty:
    st.warning("❌ Nenhuma transação encontrada com os filtros atuais.")
    st.stop()

# 📊 Resumo financeiro
despesas = df_filtered["Valor"].sum()
col1, col2 = st.columns(2)
col1.metric("💰 Total de Gastos", formatar_valor_monetario(abs(despesas)))
col2.metric("📄 Transações", len(df_filtered))

# 📋 Tabela de transações
st.subheader("📋 Transações do Cartão")
df_formatado = formatar_df_monetario(df_filtered, "Valor")
st.dataframe(
    df_formatado[["Data", "Categoria", "Descrição", "ValorFormatado"]].rename(
        columns={"ValorFormatado": "Valor"}
    ),
    use_container_width=True
)

# 📊 Gráficos
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Gastos por Categoria")
    gastos_categoria = df_filtered.copy()
    gastos_categoria["Valor"] = gastos_categoria["Valor"].abs()
    category_distribution = gastos_categoria.groupby("Categoria")["Valor"].sum().reset_index()
    
    if not category_distribution.empty:
        fig = px.pie(
            category_distribution,
            names="Categoria",
            values="Valor",
            title="Distribuição por Categoria",
            hole=0.3
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📊 Sem dados para gráfico")

with col2:
    st.subheader("📈 Evolução Mensal")
    df_evolucao = df_filtered.copy()
    df_evolucao["Valor"] = df_evolucao["Valor"].abs()
    evolucao = df_evolucao.groupby("AnoMes")["Valor"].sum().reset_index()
    
    if not evolucao.empty:
        fig2 = px.line(evolucao, x="AnoMes", y="Valor", markers=True, title="Gastos por Mês")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("📈 Sem dados para evolução")

# 🏆 Ranking de maiores gastos
st.subheader("🏆 Top 5 Maiores Gastos")
gastos_mes = df_filtered.copy()
gastos_mes["ValorAbs"] = gastos_mes["Valor"].abs()
gastos_formatados = formatar_df_monetario(gastos_mes, "ValorAbs")
top_gastos = gastos_formatados.sort_values("ValorAbs", ascending=False).head(5)

if not top_gastos.empty:
    st.dataframe(
        top_gastos[["Data", "Categoria", "Descrição", "ValorFormatado"]].rename(
            columns={"ValorFormatado": "Valor"}
        ),
        use_container_width=True
    )
else:
    st.info("🏆 Nenhum gasto registrado para o período")
