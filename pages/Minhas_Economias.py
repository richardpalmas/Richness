import streamlit as st
import pandas as pd
import plotly.express as px
from componentes.profile_pic_component import boas_vindas_com_foto
from utils.pluggy_connector import PluggyConnector
from utils.auth import verificar_autenticacao
from utils.filtros import filtro_data, filtro_categorias, aplicar_filtros
from utils.formatacao import formatar_valor_monetario, formatar_df_monetario, calcular_resumo_financeiro
from utils.exception_handler import ExceptionHandler

st.set_page_config(layout="wide")

# Verificar autenticação
verificar_autenticacao()

# Exibir foto de perfil
if 'usuario' in st.session_state:
    boas_vindas_com_foto(st.session_state['usuario'])

st.title("💰 Minhas Economias")

# Função otimizada com cache
@st.cache_resource(ttl=300)
def get_pluggy_connector():
    return PluggyConnector()

@st.cache_data(ttl=600)
def carregar_dados_economias(usuario):
    """Carrega dados de economias com cache para performance"""
    def _carregar_dados():
        pluggy = get_pluggy_connector()
        itemids_data = pluggy.load_itemids_db(usuario) if usuario else None
        
        if itemids_data:
            df = pluggy.buscar_extratos(itemids_data)
            saldos_info = pluggy.obter_saldo_atual(itemids_data)
            return saldos_info, df
        return None, pd.DataFrame()
    
    return ExceptionHandler.safe_execute(
        func=_carregar_dados,
        error_handler=ExceptionHandler.handle_pluggy_error,
        default_return=(None, pd.DataFrame()),
        show_in_streamlit=True
    )

# Carregar dados principais
usuario = st.session_state.get('usuario', 'default')
with st.spinner("Carregando dados financeiros..."):
    saldos_info, df = carregar_dados_economias(usuario)

if df.empty:
    st.warning("⚠️ Nenhuma movimentação encontrada!")
    if st.button("➕ Conectar Contas"):
        st.switch_page("pages/Cadastro_Pluggy.py")
    st.stop()

# Pré-processamento básico
df["Data"] = pd.to_datetime(df["Data"])
df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")

# Filtros essenciais
st.sidebar.header("🔍 Filtros")
start_date, end_date = filtro_data(df, "economias")
categorias_selecionadas = filtro_categorias(df, "Filtrar por Categorias", "economias")
df_filtrado = aplicar_filtros(df, start_date, end_date, categorias_selecionadas)

# Resumo financeiro atual
if saldos_info and len(saldos_info) >= 3:
    saldo_positivo, saldo_negativo, contas_detalhes = saldos_info[:3]
    col1, col2 = st.columns(2)
    col1.metric("🟢 Ativos", formatar_valor_monetario(saldo_positivo))
    col2.metric("🔴 Passivos", formatar_valor_monetario(abs(saldo_negativo)))

# Resumo do período filtrado
resumo = calcular_resumo_financeiro(df_filtrado)
st.subheader("📊 Resumo do Período")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Receitas", formatar_valor_monetario(resumo['receitas']))
col2.metric("Despesas", formatar_valor_monetario(abs(resumo['despesas'])))
col3.metric("Saldo Líquido", formatar_valor_monetario(resumo['saldo']))
col4.metric("Transações", len(df_filtrado))

# Visualizações essenciais
if not df_filtrado.empty:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Distribuição por Categoria")
        categoria_resumo = df_filtrado.groupby("Categoria")["Valor"].sum().reset_index()
        if not categoria_resumo.empty:
            # Usar valores absolutos e filtrar categorias zeradas
            categoria_resumo["ValorAbs"] = categoria_resumo["Valor"].abs()
            categoria_resumo = categoria_resumo[categoria_resumo["ValorAbs"] > 0]
            
            if not categoria_resumo.empty:
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
                            title="Por Categoria", 
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
                
                # Configurações das fatias
                fig.update_traces(
                    textposition='auto',
                    textinfo='percent',
                    textfont_size=10,
                    hovertemplate='<b>%{label}</b><br>Valor: R$ %{value:,.2f}<br>Percentual: %{percent}<extra></extra>',
                    pull=[0.05 if name == "Outros" else 0 for name in categoria_resumo["Categoria"]]
                )
                
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    
    with col2:
        st.subheader("📈 Evolução Mensal")
        df_filtrado["AnoMes"] = df_filtrado["Data"].dt.strftime("%Y-%m")
        evolucao = df_filtrado.groupby("AnoMes")["Valor"].sum().reset_index()
        if not evolucao.empty:
            fig2 = px.line(evolucao, x="AnoMes", y="Valor", markers=True,
                          title="Evolução no Tempo", template="plotly_white")
            fig2.update_layout(height=350)
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

# Extrato detalhado (colapsado para economia de espaço)
with st.expander("📋 Ver Extrato Detalhado"):
    df_formatado = formatar_df_monetario(df_filtrado, "Valor")
    st.dataframe(
        df_formatado[["Data", "Categoria", "Descrição", "ValorFormatado"]].rename(
            columns={"ValorFormatado": "Valor"}
        ),
        use_container_width=True
    )
