import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta
from dotenv import load_dotenv
import json
import os
import hashlib

from componentes.profile_pic_component import boas_vindas_com_foto
from database import get_connection
from utils.auth import verificar_autenticacao
from utils.filtros import filtro_data, filtro_categorias, aplicar_filtros
from utils.formatacao import formatar_valor_monetario, formatar_df_monetario
from utils.ofx_reader import OFXReader
from utils.exception_handler import ExceptionHandler

# Importações do novo backend V2
from utils.database_manager_v2 import DatabaseManager
from utils.repositories_v2 import RepositoryManager
from services.transacao_service_v2 import TransacaoService
from utils.database_monitoring import DatabaseMonitor

# Configuração da página
st.set_page_config(page_title="Cartão de Crédito", layout="wide")

# Verificar autenticação
verificar_autenticacao()

# Inicializar novo backend V2
@st.cache_resource
def init_backend_v2():
    """Inicializa o novo backend com cache para melhor performance"""
    try:
        # Inicializar componentes do novo backend
        db_manager = DatabaseManager()
        repository_manager = RepositoryManager(db_manager)
        transacao_service = TransacaoService()
        monitor = DatabaseMonitor(db_manager)
        
        return {
            'db_manager': db_manager,
            'repository_manager': repository_manager,
            'transacao_service': transacao_service,
            'monitor': monitor
        }
    except Exception as e:
        # Fallback para backend antigo em caso de erro
        st.warning(f"⚠️ Usando backend legado: {str(e)}")
        return None

# Inicializar backend
backend_v2 = init_backend_v2()
from utils.config import (
    get_cache_categorias_file,
    get_descricoes_personalizadas_file,
    get_transacoes_excluidas_file,
    get_current_user
)

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

# Verificação de autenticação
verificar_autenticacao()
usuario = st.session_state.get('usuario', 'default')

# Exibição de foto de perfil e mensagem de boas-vindas
if usuario:
    boas_vindas_com_foto(usuario)

st.title("💳 Cartão de Crédito")

# Aviso sobre sincronização
st.info("🔄 **Sincronização ativa:** Esta página reflete automaticamente todas as personalizações (categorias, descrições, exclusões) feitas na página 'Gerenciar Transações'.")

# Cache do leitor OFX
@st.cache_resource(ttl=300)
def get_ofx_reader():
    usuario_atual = get_current_user()
    return OFXReader(usuario_atual)

# Buscar dados com cache
@st.cache_data(ttl=600, show_spinner="Carregando transações...")
def carregar_dados_cartoes(dias):
    """Carregar dados de cartões com cache e aplicar personalizações do usuário - Nova versão com Backend V2"""
    def _load_data():
        # Tentar usar o novo backend V2
        if backend_v2:
            try:
                transacao_service = backend_v2['transacao_service']
                usuario_atual = get_current_user()
                
                # Carregar transações de cartão usando o novo serviço
                df = transacao_service.listar_transacoes_cartao(usuario_atual, dias_limite=dias)
                
                if not df.empty:
                    # Garantir que as colunas estão no formato correto
                    df["Data"] = pd.to_datetime(df["Data"])
                    df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")
                    
                    # Remover valores nulos
                    df = df.dropna(subset=["Valor"])
                    
                    # Ordenar por data (mais recente primeiro)
                    df = df.sort_values("Data", ascending=False)
                
                return df
                    
            except Exception as e:
                st.warning(f"⚠️ Erro no backend V2, usando fallback: {str(e)}")
                # Fallback para método antigo
                pass
        
        # Método antigo (fallback)
        ofx_reader = get_ofx_reader()
        df = ofx_reader.buscar_cartoes(dias)
        
        if not df.empty:
            # Garantir que as colunas estão no formato correto
            df["Data"] = pd.to_datetime(df["Data"])
            df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")
            
            # Remover valores nulos
            df = df.dropna(subset=["Valor"])
            
            # Aplicar personalizações do usuário (categorias, descrições, exclusões)
            df = aplicar_personalizacoes_usuario(df)
            
            # Ordenar por data (mais recente primeiro)
            df = df.sort_values("Data", ascending=False)
        
        return df
    
    return ExceptionHandler.safe_execute(
        func=_load_data,
        error_handler=ExceptionHandler.handle_generic_error,
        default_return=pd.DataFrame()
    )

# Obter leitor OFX
ofx_reader = get_ofx_reader()

# Verificar arquivos disponíveis
resumo_arquivos = ofx_reader.get_resumo_arquivos()

# Carregar todos os dados disponíveis
# (para garantir que o filtro de data funcione corretamente)
df_cartoes_raw = ofx_reader.buscar_cartoes(365)  # 1 ano para garantir datas amplas

# Definir período padrão: últimos 30 dias, mas limitado ao range dos dados
from datetime import timedelta, date

data_fim_default = date.today()
data_inicio_default = data_fim_default - timedelta(days=30)

# Ajustar para não ultrapassar o range dos dados
if not df_cartoes_raw.empty and "Data" in df_cartoes_raw.columns:
    min_data_val = df_cartoes_raw["Data"].min()
    max_data_val = df_cartoes_raw["Data"].max()
    if hasattr(min_data_val, 'date'):
        min_data = min_data_val.date()
    else:
        min_data = min_data_val
    if hasattr(max_data_val, 'date'):
        max_data = max_data_val.date()
    else:
        max_data = max_data_val
    data_inicio_default = max(min_data, data_inicio_default)
    data_fim_default = min(max_data, data_fim_default)

# Carregar dados (sempre busca 365 dias para garantir todos os dados para o filtro)
df_cartoes = carregar_dados_cartoes(365)

# Garantir que a coluna 'Data' existe e está no formato datetime
if not df_cartoes.empty:
    if 'data' in df_cartoes.columns and 'Data' not in df_cartoes.columns:
        df_cartoes['Data'] = pd.to_datetime(df_cartoes['data'])
    elif 'Data' in df_cartoes.columns:
        df_cartoes['Data'] = pd.to_datetime(df_cartoes['Data'])
    else:
        st.error("O arquivo de cartão não possui coluna de data válida.")
        st.stop()
else:
    st.warning("Nenhuma transação encontrada para o período selecionado.")
    st.stop()

# Gerar lista de meses/anos disponíveis
if not df_cartoes.empty:
    df_cartoes['AnoMes'] = df_cartoes['Data'].dt.strftime('%Y-%m')
    meses_disponiveis = sorted(df_cartoes['AnoMes'].unique(), reverse=True)
    if not meses_disponiveis:
        st.warning("Nenhum mês disponível para seleção.")
        st.stop()
    mes_ano_selecionado = st.sidebar.selectbox(
        "Selecione o mês",
        meses_disponiveis,
        index=0
    )
    ano, mes = map(int, mes_ano_selecionado.split('-'))
    data_inicio = pd.Timestamp(year=ano, month=mes, day=1).date()
    if mes == 12:
        data_fim = pd.Timestamp(year=ano+1, month=1, day=1).date() - pd.Timedelta(days=1)
    else:
        data_fim = pd.Timestamp(year=ano, month=mes+1, day=1).date() - pd.Timedelta(days=1)
else:
    st.warning("Nenhuma transação encontrada para o período selecionado.")
    st.stop()

# Filtrar dados do mês selecionado
df_cartoes_filtrado = df_cartoes[
    (df_cartoes["Data"].dt.date >= data_inicio) & 
    (df_cartoes["Data"].dt.date <= data_fim)
]

if df_cartoes_filtrado.empty:
    st.warning("🔍 Nenhuma transação encontrada no período selecionado.")
    st.stop()

# Filtros adicionais
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
top_gastos = df_final.nsmallest(10, "Valor")

# Incluir coluna Nota se existe e tem dados
colunas_exibir = ["Data", "Descrição", "Valor", "Categoria"]
if "Nota" in top_gastos.columns and top_gastos["Nota"].notna().any() and (top_gastos["Nota"] != "").any():
    colunas_exibir.insert(-1, "Nota")  # Inserir antes da Categoria

top_gastos = top_gastos[colunas_exibir]
top_gastos["Valor"] = top_gastos["Valor"].abs()
top_gastos = formatar_df_monetario(top_gastos)

st.dataframe(top_gastos, use_container_width=True)

# Tabela completa de transações
st.subheader("📋 Transações do Período")

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

# Obter categorias disponíveis no período filtrado
if not df_final.empty:
    categorias_periodo = sorted(df_final["Categoria"].unique())
    
    # Criar lista de abas: "Todas" + categorias específicas
    abas_disponiveis = ["📊 Todas"] + [f"🏷️ {cat}" for cat in categorias_periodo]
    
    # Criar abas usando st.tabs
    tabs = st.tabs(abas_disponiveis)
    
    with tabs[0]:  # Aba "Todas"
        st.markdown("**Todas as transações do cartão no período selecionado**")
        
        # Mostrar resumo
        total_transacoes = len(df_final)
        valor_total = df_final["Valor"].sum()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("💼 Total", total_transacoes)
        with col2:
            st.metric("💰 Total Gasto", formatar_valor_monetario(abs(valor_total)))
        with col3:
            despesas_count = len(df_final[df_final["Valor"] < 0])
            st.metric("💳 Despesas", despesas_count)
        
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
            valor_cat = df_categoria["Valor"].sum()
            despesas_cat = len(df_categoria[df_categoria["Valor"] < 0])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("💼 Transações", total_cat)
            with col2:
                st.metric("💰 Total", formatar_valor_monetario(abs(valor_cat)))
            with col3:
                st.metric("💳 Despesas", despesas_cat)
            
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
    st.warning("🔍 Nenhuma transação encontrada com os filtros aplicados.")
    st.info("💡 Ajuste os filtros de data ou categoria para ver as transações.")

# Informações adicionais
with st.expander("ℹ️ Informações Técnicas"):
    st.write(f"**Período analisado:** {data_inicio} a {data_fim}")
    st.write(f"**Total de registros:** {len(df_final):,}")
    st.write(f"**Arquivos processados:** {resumo_arquivos['total_faturas']} faturas")
    
    if resumo_arquivos['periodo_faturas']['inicio']:
        st.write(f"**Período dos arquivos:** {resumo_arquivos['periodo_faturas']['inicio']} a {resumo_arquivos['periodo_faturas']['fim']}")
    
    # Estatísticas de personalizações
    st.markdown("**📊 Personalizações aplicadas:**")
    
    cache_categorias = carregar_cache_categorias()
    descricoes_personalizadas = carregar_descricoes_personalizadas()
    transacoes_excluidas = carregar_transacoes_excluidas()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🏷️ Categorias personalizadas", len(cache_categorias))
    with col2:
        st.metric("📝 Descrições personalizadas", len(descricoes_personalizadas))
    with col3:
        st.metric("🗑️ Transações excluídas", len(transacoes_excluidas))
    
    if cache_categorias or descricoes_personalizadas or transacoes_excluidas:
        st.info("💡 As personalizações feitas na página 'Gerenciar Transações' são aplicadas automaticamente aqui.")
    
    # Botão para limpar cache
    if st.button("🧹 Limpar Cache"):
        ofx_reader.limpar_cache()
        st.cache_data.clear()
        st.success("Cache limpo! Recarregue a página para ver os dados atualizados.")

# Botão sair sempre visível
if st.session_state.get('autenticado', False):
    if st.button('🚪 Sair', key='logout_btn'):
        st.session_state.clear()
        st.success('Você saiu do sistema.')
        st.rerun()
