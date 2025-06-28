import streamlit as st
import pandas as pd
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
from utils.filtros import filtro_data, filtro_categorias, aplicar_filtros
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
st.sidebar.header("� Selecionar Período")

# Filtro de período (igual ao da página Home)
data_inicio, data_fim = None, None
if not df.empty:
    # Usar filtro_data da mesma forma que na Home
    data_inicio, data_fim = filtro_data(df, key_prefix="economias")
    
    st.sidebar.success(f"📅 Período: {data_inicio} a {data_fim}")
    
    # Filtro de categorias usando a função padrão
    categorias_selecionadas = filtro_categorias(df, key_prefix="economias")
    
    # Aplicar filtros usando a função padrão
    df_filtrado = aplicar_filtros(df, data_inicio, data_fim, categorias_selecionadas)
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

# Análises avançadas
st.subheader("📊 Análises Detalhadas")

col1, col2, col3 = st.columns(3)

with col1:
    # Top 10 maiores receitas
    if not df_filtrado.empty:
        df_receitas = df_filtrado[df_filtrado['Valor'] > 0].copy()
        if not df_receitas.empty:
            st.markdown("**💰 Top 10 Maiores Receitas**")
            top_receitas = df_receitas.nlargest(10, 'Valor')
            top_receitas_display = top_receitas[['Data', 'Descrição', 'Valor', 'Categoria']].copy()
            top_receitas_display = formatar_df_monetario(top_receitas_display, col_valor="Valor")
            st.dataframe(
                top_receitas_display[['Data', 'Descrição', 'ValorFormatado', 'Categoria']].rename(columns={
                    'ValorFormatado': 'Valor'
                }),
                use_container_width=True,
                height=300
            )

with col2:
    # Top 10 maiores despesas
    if not df_filtrado.empty:
        df_despesas = df_filtrado[df_filtrado['Valor'] < 0].copy()
        if not df_despesas.empty:
            st.markdown("**💸 Top 10 Maiores Despesas**")
            top_despesas = df_despesas.nsmallest(10, 'Valor')
            top_despesas_display = top_despesas[['Data', 'Descrição', 'Valor', 'Categoria']].copy()
            top_despesas_display['Valor'] = top_despesas_display['Valor'].abs()
            top_despesas_display = formatar_df_monetario(top_despesas_display, col_valor="Valor")
            st.dataframe(
                top_despesas_display[['Data', 'Descrição', 'ValorFormatado', 'Categoria']].rename(columns={
                    'ValorFormatado': 'Valor'
                }),
                use_container_width=True,
                height=300
            )

with col3:
    # Análise por origem
    if not df_filtrado.empty and 'Origem' in df_filtrado.columns:
        st.markdown("**🏦 Análise por Origem**")
        origem_resumo = df_filtrado.groupby('Origem').agg({
            'Valor': ['count', 'sum']
        }).round(2)
        origem_resumo.columns = ['Transações', 'Total']
        origem_resumo['Total_Formatado'] = origem_resumo['Total'].apply(formatar_valor_monetario)
        
        st.dataframe(
            origem_resumo[['Transações', 'Total_Formatado']].rename(columns={
                'Total_Formatado': 'Valor Total'
            }),
            use_container_width=True,
            height=300
        )




