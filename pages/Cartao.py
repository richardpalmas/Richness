import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta, datetime
import json
import os
import hashlib

from componentes.profile_pic_component import boas_vindas_com_foto
from utils.formatacao import formatar_valor_monetario, formatar_df_monetario
from utils.filtros import filtro_data
from utils.config import (
    get_cache_categorias_file,
    get_descricoes_personalizadas_file,
    get_transacoes_excluidas_file,
    get_current_user
)

# BACKEND V2 OBRIGATÓRIO - Importações exclusivas
from utils.database_manager_v2 import DatabaseManager
from utils.repositories_v2 import TransacaoRepository, UsuarioRepository, CategoriaRepository
from services.transacao_service_v2 import TransacaoService

# Configuração da página
st.set_page_config(page_title="Cartão de Crédito V2", layout="wide")

# Verificar autenticação
def verificar_autenticacao():
    if 'authenticated' not in st.session_state or not st.session_state['authenticated']:
        st.error("❌ Acesso negado! Faça login na página inicial.")
        st.stop()

verificar_autenticacao()

# Inicializar Backend V2 (obrigatório)
@st.cache_resource
def init_backend_v2_cartao():
    """Inicializa o Backend V2 para a página de Cartão"""
    try:
        db_manager = DatabaseManager()
        transacao_repo = TransacaoRepository(db_manager)
        usuario_repo = UsuarioRepository(db_manager)
        categoria_repo = CategoriaRepository(db_manager)
        transacao_service = TransacaoService()
        
        return {
            'db_manager': db_manager,
            'transacao_repo': transacao_repo,
            'usuario_repo': usuario_repo,
            'categoria_repo': categoria_repo,
            'transacao_service': transacao_service
        }
    except Exception as e:
        st.error(f"❌ Erro ao inicializar Backend V2: {e}")
        st.stop()

backend_v2 = init_backend_v2_cartao()

# Funções para sincronização com personalizações do usuário
def gerar_hash_transacao(row):
    """Gera um hash único para identificar uma transação de forma consistente"""
    # Usar data, descrição e valor para criar um identificador único
    data_str = row["Data"].strftime("%Y-%m-%d") if hasattr(row["Data"], 'strftime') else str(row["Data"])
    chave = f"{data_str}|{row['Descrição']}|{row['Valor']}"
    return hashlib.md5(chave.encode()).hexdigest()

def carregar_cache_categorias():
    """Carrega o cache de categorizações personalizadas do usuário"""
    cache_file = get_cache_categorias_file()
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

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

def carregar_transacoes_excluidas():
    """Carrega a lista de transações excluídas pelo usuário"""
    excluidas_file = get_transacoes_excluidas_file()
    if os.path.exists(excluidas_file):
        try:
            with open(excluidas_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def filtrar_transacoes_excluidas(df):
    """Filtra as transações excluídas do DataFrame"""
    if df.empty:
        return df
    
    transacoes_excluidas = carregar_transacoes_excluidas()
    if not transacoes_excluidas:
        return df
    
    # Aplicar filtro
    def nao_esta_excluida(row):
        hash_transacao = gerar_hash_transacao(row)
        return hash_transacao not in transacoes_excluidas
    
    df_filtrado = df[df.apply(nao_esta_excluida, axis=1)]
    return df_filtrado

def aplicar_personalizacoes_usuario(df):
    """Aplica todas as personalizações do usuário ao DataFrame"""
    if df.empty:
        return df
    
    # Aplicar categorias personalizadas
    cache_categorias = carregar_cache_categorias()
    if cache_categorias:
        def aplicar_categoria_personalizada(row):
            descricao_normalizada = row["Descrição"].lower().strip()
            if descricao_normalizada in cache_categorias:
                return cache_categorias[descricao_normalizada]
            return row.get("Categoria", "Outros")
        
        df["Categoria"] = df.apply(aplicar_categoria_personalizada, axis=1)
    
    # Aplicar descrições personalizadas (adicionar coluna "Nota")
    descricoes = carregar_descricoes_personalizadas()
    if descricoes:
        def obter_descricao_personalizada(row):
            hash_transacao = gerar_hash_transacao(row)
            return descricoes.get(hash_transacao, "")
        
        df["Nota"] = df.apply(obter_descricao_personalizada, axis=1)
    else:
        df["Nota"] = ""
    
    # Filtrar transações excluídas
    df = filtrar_transacoes_excluidas(df)
    
    return df

# Obter usuário da sessão
usuario = st.session_state.get('usuario', 'default')

# Boas-vindas com foto de perfil
if usuario:
    boas_vindas_com_foto(usuario)

# Título principal
st.title("💳 Cartão de Crédito")
st.markdown("**Análise completa de transações de cartão de crédito**")

# Carregar dados de cartão usando Backend V2
@st.cache_data(ttl=600, show_spinner="Carregando transações de cartão...")
def carregar_dados_cartao_v2(usuario, dias_limite):
    """Carrega dados de cartão usando APENAS o Backend V2 com personalizações"""
    try:
        transacao_service = backend_v2['transacao_service']
        
        # Carregar transações de cartão
        df_cartao = transacao_service.listar_transacoes_cartao(usuario, dias_limite)
        
        if not df_cartao.empty:
            # Garantir que as colunas estão no formato correto
            df_cartao["Data"] = pd.to_datetime(df_cartao["Data"])
            df_cartao["Valor"] = pd.to_numeric(df_cartao["Valor"], errors="coerce")
            
            # Remover valores nulos
            df_cartao = df_cartao.dropna(subset=["Valor"])
            
            # Aplicar personalizações do usuário (categorias, descrições, exclusões)
            df_cartao = aplicar_personalizacoes_usuario(df_cartao)
            
            # Ordenar por data (mais recente primeiro)
            df_cartao = df_cartao.sort_values("Data", ascending=False)
        
        return df_cartao
        
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados do cartão V2: {str(e)}")
        return pd.DataFrame()

# Sidebar - Configurações
st.sidebar.header("⚙️ Configurações do Cartão V2")
st.sidebar.markdown("**Backend V2 Ativo** 🚀")

# Carregar dados iniciais para definir range de datas
df_cartao_completo = carregar_dados_cartao_v2(usuario, 365)  # 1 ano para ter range completo

# Filtros na sidebar
st.sidebar.markdown("### 📅 Período de Análise")

# Filtro de período com a mesma lógica da Home
data_inicio, data_fim = None, None
df_cartao = pd.DataFrame()

if not df_cartao_completo.empty and 'Data' in df_cartao_completo.columns:
    # Converter coluna de data se necessário
    df_for_filter = df_cartao_completo.copy()
    df_for_filter['Data'] = pd.to_datetime(df_for_filter['Data'])
    data_inicio, data_fim = filtro_data(df_for_filter, key_prefix="cartao")
    
    st.sidebar.success(f"📅 Período: {data_inicio} a {data_fim}")
    
    # Aplicar filtro de data aos dados do cartão
    df_cartao = df_cartao_completo[
        (pd.to_datetime(df_cartao_completo["Data"]).dt.date >= data_inicio) & 
        (pd.to_datetime(df_cartao_completo["Data"]).dt.date <= data_fim)
    ]
    
    periodo_info = f"{data_inicio} a {data_fim}"
else:
    # Fallback se não há dados
    st.sidebar.warning("Nenhum dado disponível para filtro")
    df_cartao = pd.DataFrame()
    periodo_info = "Sem dados"

# Informações do usuário
if st.sidebar.expander("👤 Informações do Usuário"):
    st.sidebar.write(f"**Usuário**: {usuario}")
    st.sidebar.write(f"**Sistema**: Backend V2")
    st.sidebar.write(f"**Período**: {periodo_info}")

# Botão de Sair
st.sidebar.markdown("---")
if st.sidebar.button('🚪 Sair', help="Fazer logout da aplicação", type="primary"):
    st.session_state.clear()
    st.rerun()

# Verificar se temos dados para continuar
if df_cartao.empty:
    df_cartao = carregar_dados_cartao_v2(usuario, 90)  # Fallback para 90 dias

# Verificar se há dados
if df_cartao.empty:
    st.warning("📭 Nenhuma transação de cartão encontrada!")
    st.info("💡 **Possíveis motivos:**")
    st.markdown("""
    1. 📁 Nenhum arquivo de fatura foi importado
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

# Aplicar dados sem filtros avançados - usar todos os dados do cartão
df_final = df_cartao

if df_final.empty:
    st.warning("🔍 Nenhuma transação encontrada.")
    st.info("💡 Verifique se há dados de cartão disponíveis.")
    st.stop()
    st.stop()

# Dashboard principal
st.subheader("📊 Resumo do Cartão")

# Métricas principais usando dados filtrados
total_transacoes = len(df_final)
total_gastos = abs(df_final['Valor'].sum())  # Valores de cartão são geralmente negativos
gasto_medio = total_gastos / total_transacoes if total_transacoes > 0 else 0
maior_gasto = abs(df_final['Valor'].min()) if not df_final.empty else 0

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "💸 Total de Gastos", 
        formatar_valor_monetario(total_gastos)
    )

with col2:
    st.metric(
        "📊 Transações", 
        f"{total_transacoes:,}"
    )

with col3:
    st.metric(
        "💰 Gasto Médio", 
        formatar_valor_monetario(gasto_medio)
    )

with col4:
    st.metric(
        "🔥 Maior Gasto", 
        formatar_valor_monetario(maior_gasto)
    )

st.markdown("---")

# Gráficos de análise
with st.expander("📈 Análises do Cartão", expanded=False):
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
                title="💸 Gastos por Categoria",
                template="plotly_white"
            )
            
            fig_categorias.update_layout(height=400)
            st.plotly_chart(fig_categorias, use_container_width=True)

    with col2:
        # Gráfico de evolução temporal
        if not df_final.empty:
            df_temp = df_final.copy()
            df_temp["Data"] = pd.to_datetime(df_temp["Data"])
            df_temp["Mes"] = df_temp["Data"].dt.to_period("M").astype(str)
            evolucao_mensal = df_temp.groupby("Mes")["Valor"].sum().reset_index()
            evolucao_mensal["Valor_Abs"] = evolucao_mensal["Valor"].abs()
            
            fig_evolucao = px.bar(
                evolucao_mensal,
                x="Mes",
                y="Valor_Abs",
                title="📊 Gastos Mensais",
                template="plotly_white"
            )
            
            fig_evolucao.update_layout(height=400)
            st.plotly_chart(fig_evolucao, use_container_width=True)

# Top gastos
with st.expander("🔝 Maiores Gastos do Período", expanded=False):
    if not df_final.empty:
        top_gastos = df_final.nsmallest(10, "Valor").copy()
        
        # Incluir coluna Nota se existe e tem dados
        colunas_exibir = ["Data", "Descrição", "Valor", "Categoria"]
        if "Nota" in top_gastos.columns and top_gastos["Nota"].notna().any() and (top_gastos["Nota"] != "").any():
            colunas_exibir.insert(-1, "Nota")  # Inserir antes da Categoria
        
        top_gastos = top_gastos[colunas_exibir]
        top_gastos["Valor"] = top_gastos["Valor"].abs()
        top_gastos_formatado = formatar_df_monetario(top_gastos)
        
        st.dataframe(top_gastos_formatado, use_container_width=True)

# Análise detalhada por categorias com abas
# Função para formatar DataFrame com descrições personalizadas (igual à Home)
def formatar_df_com_descricoes(df):
    """Formata o DataFrame adicionando descrições personalizadas e removendo coluna Id"""
    if df.empty:
        return df
    
    # Criar cópia do DataFrame
    df_formatado = df.copy()
    
    # Aplicar formatação monetária
    df_formatado = formatar_df_monetario(df_formatado)
    
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
    
    # 4. Adicionar Nota (se existir e tem dados)
    if "Nota" in colunas_desejadas:
        colunas_ordenadas.append("Nota")
    
    # 5. Adicionar demais colunas na ordem original
    for col in colunas_desejadas:
        if col not in colunas_ordenadas:
            colunas_ordenadas.append(col)
    
    return df_formatado[colunas_ordenadas]

with st.expander("📊 Transações por Categoria", expanded=False):
    if not df_final.empty and 'Categoria' in df_final.columns:
        categorias_periodo = sorted(df_final['Categoria'].unique())
        
        # Criar lista de abas: "Todas" + categorias específicas
        abas_disponiveis = ["📊 Todas"] + [f"🏷️ {cat}" for cat in categorias_periodo]
        
        # Criar abas usando st.tabs
        tabs = st.tabs(abas_disponiveis)
        
        with tabs[0]:  # Aba "Todas"
            st.markdown("**Todas as transações do cartão no período**")
            
            # Mostrar resumo
            total_transacoes_aba = len(df_final)
            valor_total_aba = abs(df_final["Valor"].sum())
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("💼 Total", total_transacoes_aba)
            with col2:
                st.metric("💰 Total Gasto", formatar_valor_monetario(valor_total_aba))
            with col3:
                despesas_count = len(df_final[df_final["Valor"] < 0])
                st.metric("💸 Despesas", despesas_count)
            
            # Tabela formatada com descrições personalizadas
            df_display_todas = formatar_df_com_descricoes(df_final.head(50))
            # Para cartão, mostrar valores como positivos na tabela
            if "Valor" in df_display_todas.columns:
                df_display_todas["Valor"] = df_display_todas["Valor"].abs()
                df_display_todas = formatar_df_monetario(df_display_todas)
            
            st.dataframe(
                df_display_todas,
                use_container_width=True,
                height=400
            )
            
            if len(df_final) > 50:
                st.caption(f"📄 Exibindo 50 de {len(df_final)} transações (ordenadas por data mais recente)")
        
        # Abas para cada categoria
        for i, categoria in enumerate(categorias_periodo, 1):
            with tabs[i]:
                # Filtrar transações da categoria
                df_categoria = df_final[df_final["Categoria"] == categoria]
                
                st.markdown(f"**Transações da categoria: {categoria}**")
                
                # Mostrar resumo da categoria
                total_cat = len(df_categoria)
                valor_cat = abs(df_categoria["Valor"].sum())
                despesas_cat = len(df_categoria[df_categoria["Valor"] < 0])
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("💼 Transações", total_cat)
                with col2:
                    st.metric("💰 Total", formatar_valor_monetario(valor_cat))
                with col3:
                    st.metric("💸 Despesas", despesas_cat)
                
                if not df_categoria.empty:
                    # Tabela formatada da categoria com descrições personalizadas
                    df_display_cat = formatar_df_com_descricoes(df_categoria.head(50))
                    # Para cartão, mostrar valores como positivos na tabela
                    if "Valor" in df_display_cat.columns:
                        df_display_cat["Valor"] = df_display_cat["Valor"].abs()
                        df_display_cat = formatar_df_monetario(df_display_cat)
                    
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
        st.info("📊 Nenhuma transação de cartão disponível para análise por categorias.")
