import streamlit as st
import pandas as pd
import plotly.express as px
from componentes.profile_pic_component import boas_vindas_com_foto
from utils.ofx_reader import OFXReader
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
def get_ofx_reader():
    return OFXReader()

@st.cache_data(ttl=600)
def carregar_dados_economias(usuario):
    """Carrega dados de economias com cache para performance"""
    def _carregar_dados():
        ofx_reader = get_ofx_reader()
        
        # Carregar dados dos arquivos OFX
        df_extratos = ofx_reader.buscar_extratos()
        df_cartoes = ofx_reader.buscar_cartoes()
        
        # Combinar extratos e cartões
        df = pd.concat([df_extratos, df_cartoes], ignore_index=True) if not df_extratos.empty or not df_cartoes.empty else pd.DataFrame()
        
        # Calcular saldos por origem
        saldos_info = {}
        if not df.empty:
            for origem in df['Origem'].unique():
                df_origem = df[df['Origem'] == origem]
                saldo = df_origem['Valor'].sum()
                saldos_info[origem] = {
                    'saldo': saldo,
                    'tipo': 'credit_card' if 'fatura' in origem.lower() or 'nubank' in origem.lower() else 'checking'
                }
        
        return saldos_info, df
    
    return ExceptionHandler.safe_execute(
        func=_carregar_dados,
        error_handler=ExceptionHandler.handle_generic_error,
        default_return=({}, pd.DataFrame()),
        show_in_streamlit=True
    )

# Carregar dados principais
usuario = st.session_state.get('usuario', 'default')
with st.spinner("Carregando dados financeiros..."):
    saldos_info, df = carregar_dados_economias(usuario)

if df.empty:
    st.warning("📭 Nenhuma transação encontrada nos arquivos OFX!")
    st.info("💡 **Como adicionar dados:**")
    st.markdown("""
    1. 📁 Coloque seus extratos (.ofx) na pasta `extratos/`
    2. 💳 Coloque suas faturas de cartão (.ofx) na pasta `faturas/`
    3. 🔄 Atualize a página
    """)
    st.stop()

# Pré-processamento básico
df["Data"] = pd.to_datetime(df["Data"])
df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")

# Filtros essenciais
st.sidebar.header("🔍 Filtros")
start_date, end_date = filtro_data(df, "economias")
categorias_selecionadas = filtro_categorias(df, "Filtrar por Categorias", "economias")
df_filtrado = aplicar_filtros(df, start_date, end_date, categorias_selecionadas)

# Resumo financeiro atual baseado nos saldos calculados
if saldos_info:
    st.subheader("💰 Saldo Consolidado")
    
    saldo_total_positivo = 0
    saldo_total_negativo = 0
    
    # Calcular totais sem mostrar contas individuais
    for origem, info in saldos_info.items():
        saldo = info['saldo']
        
        if saldo >= 0:
            saldo_total_positivo += saldo
        else:
            saldo_total_negativo += saldo
    
    # Calcular saldo líquido total
    saldo_liquido_total = saldo_total_positivo + saldo_total_negativo
    
    # Mostrar apenas o saldo consolidado
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("🟢 Total Positivo", formatar_valor_monetario(saldo_total_positivo))
    
    with col2:
        st.metric("🔴 Total Negativo", formatar_valor_monetario(abs(saldo_total_negativo)))
    
    with col3:
        # Definir cor baseada no saldo
        delta_color = "normal" if saldo_liquido_total >= 0 else "inverse"
        st.metric("💳 Saldo Líquido Total", formatar_valor_monetario(saldo_liquido_total))

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
                
                fig = px.pie(categoria_resumo, 
                            names="Categoria", 
                            values="ValorAbs",
                            title="Por Categoria", 
                            template="plotly_white")
                
                # Configurações de layout consistentes
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
                
                # Configurações das fatias
                fig.update_traces(
                    textposition='inside',
                    textinfo='percent+label',
                    textfont_size=10,
                    pull=[0.1 if name == "Outros" else 0 for name in categoria_resumo["Categoria"]]
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
