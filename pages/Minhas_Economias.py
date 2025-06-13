import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import warnings
import hashlib

# Imports Backend V2
from componentes.profile_pic_component import boas_vindas_com_foto
from utils.repositories_v2 import UsuarioRepository, TransacaoRepository
from utils.database_manager_v2 import DatabaseManager
from services.transacao_service_v2 import TransacaoService
from utils.auth import verificar_autenticacao
from utils.formatacao import formatar_valor_monetario, formatar_df_monetario, calcular_resumo_financeiro
from utils.exception_handler import ExceptionHandler

warnings.filterwarnings('ignore')

st.set_page_config(layout="wide")

# Verificar autenticação
verificar_autenticacao()

# Exibir foto de perfil
if 'usuario' in st.session_state:
    boas_vindas_com_foto(st.session_state['usuario'])

st.title("💰 Minhas Economias")

# Função otimizada com cache para Backend V2
@st.cache_data(ttl=600)
def carregar_dados_economias(usuario):
    """Carrega dados de economias usando Backend V2 com cache para performance"""
    def _carregar_dados():
        try:
            # Inicializar Backend V2
            db_manager = DatabaseManager()
            user_repo = UsuarioRepository(db_manager)
            transacao_repo = TransacaoRepository(db_manager)
            
            # Obter usuário usando o username da sessão
            usuario_atual = user_repo.obter_usuario_por_username(usuario)
            
            if not usuario_atual:
                return {}, pd.DataFrame()
            
            user_id = usuario_atual.get('id')
            if not user_id:
                return {}, pd.DataFrame()
            
            # Carregar transações do Backend V2 - usando período amplo para obter todas
            from datetime import datetime, timedelta
            data_fim = datetime.now().strftime('%Y-%m-%d')
            data_inicio = (datetime.now() - timedelta(days=365*3)).strftime('%Y-%m-%d')  # 3 anos atrás
            
            df = transacao_repo.obter_transacoes_periodo(
                user_id=user_id,
                data_inicio=data_inicio,
                data_fim=data_fim,
                incluir_excluidas=False,
                limite=None  # Sem limite para obter todas
            )
            
            # Calcular saldos por origem/conta
            saldos_info = {}
            if not df.empty:
                for origem in df['origem'].unique():
                    df_origem = df[df['origem'] == origem]
                    saldo = df_origem['valor'].sum()
                    saldos_info[origem] = {
                        'saldo': saldo,
                        'tipo': 'credit_card' if 'cartao' in origem.lower() or 'nubank' in origem.lower() else 'checking'
                    }
                
                # Padronizar colunas para compatibilidade
                df = df.rename(columns={
                    'valor': 'Valor',
                    'descricao': 'Descrição',
                    'categoria': 'Categoria',
                    'data': 'Data',
                    'origem': 'Origem'
                })
                
                # Garantir que a coluna Data seja datetime
                if 'Data' in df.columns:
                    df['Data'] = pd.to_datetime(df['Data'])
            
            return saldos_info, df
            
        except Exception as e:
            st.error(f"Erro ao carregar dados: {str(e)}")
            return {}, pd.DataFrame()
    
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
    st.warning("📭 Nenhuma transação encontrada!")
    st.info("💡 **Possíveis motivos:**")
    st.markdown("""
    1. 📁 Nenhum arquivo foi importado
    2. 🗓️ O período selecionado não contém transações
    3. 🔍 Os dados não foram migrados para o Backend V2
    """)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Tentar Recarregar", type="primary"):
            st.cache_data.clear()
            st.rerun()
    
    with col2:
        if st.button("📁 Ir para Atualizar Dados"):
            st.switch_page("pages/Atualizar_Dados.py")
    
    st.stop()

# Pré-processamento básico
df["Data"] = pd.to_datetime(df["Data"])
df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")

# Filtros essenciais
st.sidebar.header("🔍 Filtros")

# Filtro de data simples
if not df.empty:
    min_date = df["Data"].min().date()
    max_date = df["Data"].max().date()
    
    start_date = st.sidebar.date_input(
        "Data Inicial",
        min_date,
        min_value=min_date,
        max_value=max_date,
        key="economias_start_date"
    )
    
    end_date = st.sidebar.date_input(
        "Data Final",
        max_date,
        min_value=min_date,
        max_value=max_date,
        key="economias_end_date"
    )
    
    # Filtro de categorias
    categorias_unicas = sorted(df["Categoria"].dropna().unique())
    categorias_selecionadas = st.sidebar.multiselect(
        "Filtrar por Categorias",
        categorias_unicas,
        default=categorias_unicas,
        key="economias_categorias"
    )
    
    # Aplicar filtros
    df_filtrado = df[
        (df["Data"].dt.date >= start_date) &
        (df["Data"].dt.date <= end_date) &
        (df["Categoria"].isin(categorias_selecionadas))
    ].copy()
else:
    df_filtrado = df.copy()

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

# Botão sair sempre visível
if st.session_state.get('autenticado', False):
    if st.button('🚪 Sair', key='logout_btn'):
        st.session_state.clear()
        st.success('Você saiu do sistema.')
        st.rerun()
