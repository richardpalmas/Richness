import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta, date

from database import (get_connection, delete_transaction, update_transaction_details, 
                     get_transaction_details, get_user_role)
from security.middleware.security_headers import apply_page_security
from utils.filtros import filtro_data, filtro_categorias, aplicar_filtros
from utils.formatacao import formatar_valor_monetario, formatar_df_monetario, calcular_resumo_financeiro
from utils.pluggy_connector import PluggyConnector
from utils.exception_handler import ExceptionHandler

# Configurar página
st.set_page_config(
    page_title="Gerenciar Transações",
    page_icon="⚙️",
    layout="wide"
)

# Aplicar segurança
apply_page_security('financial')

# Verificar autenticação usando o padrão das outras páginas
from utils.auth import verificar_autenticacao
verificar_autenticacao()

# Header da página
st.title("⚙️ Gerenciar Transações")
st.markdown("Edite, classifique ou remova transações incorretas")

# Sidebar com controles de período
st.sidebar.header("📅 Período de Análise")

# Opções predefinidas de período
periodos_predefinidos = {
    "🔥 Último mês": 30,
    "📊 Últimos 3 meses": 90,
    "📈 Últimos 6 meses (Recomendado)": 180,
    "📉 Último ano": 365,
    "🗂️ Todos os dados disponíveis": 1095  # ~3 anos
}

periodo_selecionado = st.sidebar.selectbox(
    "Escolha o período:",
    options=list(periodos_predefinidos.keys()),
    index=2,  # Padrão: 6 meses
    help="⚡ Períodos menores carregam mais rapidamente"
)

dias_periodo = periodos_predefinidos[periodo_selecionado]

# Opção avançada para período customizado
with st.sidebar.expander("🛠️ Período Customizado"):
    usar_customizado = st.checkbox("Usar período personalizado")
    if usar_customizado:
        col1, col2 = st.columns(2)
        with col1:
            data_inicio_custom = st.date_input(
                "Data Início:",
                value=date.today() - timedelta(days=180),
                max_value=date.today()
            )
        with col2:
            data_fim_custom = st.date_input(
                "Data Fim:",
                value=date.today(),
                max_value=date.today()
            )
        
        if data_inicio_custom <= data_fim_custom:
            dias_periodo = (data_fim_custom - data_inicio_custom).days
        else:
            st.sidebar.error("❌ Data início deve ser anterior à data fim")

# Mostrar informações do período selecionado
data_limite = date.today() - timedelta(days=dias_periodo)
st.sidebar.info(f"""
**📅 Período Ativo:**
- **De:** {data_limite.strftime('%d/%m/%Y')}
- **Até:** {date.today().strftime('%d/%m/%Y')}
- **Total:** {dias_periodo} dias
""")

if dias_periodo > 365:
    st.sidebar.warning("⚠️ Período longo pode impactar performance")
elif dias_periodo <= 30:
    st.sidebar.success("⚡ Carregamento rápido")
else:
    st.sidebar.info("⚖️ Período balanceado")

# Funções auxiliares
@st.cache_data(ttl=300)
def carregar_dados_transacoes(usuario, dias_periodo=180):
    """
    Carrega transações do usuário com período otimizado
    Inclui transações da API Pluggy e transações manuais
    
    Args:
        usuario: Nome do usuário
        dias_periodo: Número de dias para buscar (padrão: 180 = 6 meses)
    """
    try:
        # 1. Carregar transações da API Pluggy
        pluggy = PluggyConnector()
        itemids_data = pluggy.load_itemids_db(usuario)
        
        all_dfs = []
        
        # Carregar transações da API se houver conexões
        if itemids_data:
            # Carregar extratos e cartões com período específico
            df_extratos = pluggy.buscar_extratos(itemids_data, dias=dias_periodo)
            df_cartoes = pluggy.buscar_cartoes(itemids_data, dias=dias_periodo)
            
            if not df_extratos.empty:
                df_extratos['origem'] = 'extrato'
                all_dfs.append(df_extratos)
                
            if not df_cartoes.empty:
                df_cartoes['origem'] = 'cartao'
                all_dfs.append(df_cartoes)
        
        # 2. Carregar transações manuais do banco de dados
        data_inicio = datetime.now() - timedelta(days=dias_periodo)
        
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar se a tabela existe
            cursor.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='transacoes_manuais'
            ''')
            
            if cursor.fetchone():
                # Buscar transações manuais do período
                cursor.execute('''
                    SELECT id, data, descricao, valor, categoria, conta
                    FROM transacoes_manuais 
                    WHERE usuario = ? AND data >= ?
                    ORDER BY data DESC
                ''', (usuario, data_inicio.strftime('%Y-%m-%d')))
                
                transacoes_manuais = cursor.fetchall()
                
                if transacoes_manuais:
                    # Converter para DataFrame
                    df_manual = pd.DataFrame(transacoes_manuais, columns=[
                        'id', 'Data', 'Descrição', 'Valor', 'Categoria', 'Conta'
                    ])
                    
                    df_manual['Data'] = pd.to_datetime(df_manual['Data'])
                    df_manual['Valor'] = pd.to_numeric(df_manual['Valor'], errors='coerce')
                    df_manual['origem'] = 'manual'
                    
                    all_dfs.append(df_manual)
        
        # 3. Combinar todas as transações
        if all_dfs:
            df = pd.concat(all_dfs, ignore_index=True)
            df["Data"] = pd.to_datetime(df["Data"])
            df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")
            
            # Garantir que todas as transações tenham um ID único
            if 'id' not in df.columns or df['id'].isna().any() or df['id'].eq('').any():
                # Gerar IDs únicos baseados no hash do conteúdo da transação
                import hashlib
                def gerar_id_unico(row):
                    # Usar dados da transação para gerar um ID único e determinístico
                    content = f"{row['Data']}-{row['Valor']}-{row['Descrição']}-{row['Conta']}"
                    return hashlib.md5(content.encode()).hexdigest()[:16]
                
                df['id'] = df.apply(gerar_id_unico, axis=1)
            
            # Ordenar por data (mais recentes primeiro)
            df = df.sort_values('Data', ascending=False)
            
            return df
        
        return pd.DataFrame()
        
    except Exception as e:
        st.error(f"Erro ao carregar transações: {e}")
        return pd.DataFrame()

def get_transaction_type_display(valor, categoria):
    """Determina como exibir o tipo da transação"""
    resumo = calcular_resumo_financeiro(pd.DataFrame([{
        'Valor': valor,
        'Categoria': categoria,
        'Data': datetime.now(),
        'Descrição': 'teste'
    }]))
    
    if resumo.get('é_receita_real', {}).get(0, False):
        return "💰 Receita"
    elif resumo.get('é_despesa_real', {}).get(0, False):
        return "💸 Despesa"
    else:
        return "🔄 Excluída"

def mostrar_modal_edicao(row):
    """Mostra modal para editar transação"""
    if f"edit_modal_{row['id']}" not in st.session_state:
        st.session_state[f"edit_modal_{row['id']}"] = False
    
    if st.session_state[f"edit_modal_{row['id']}"]:
        with st.container():
            st.markdown("### ✏️ Editar Transação")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Dados Atuais:**")
                st.write(f"**Data:** {row['Data'].strftime('%d/%m/%Y')}")
                st.write(f"**Valor:** {formatar_valor_monetario(row['Valor'])}")
                st.write(f"**Descrição:** {row['Descrição']}")
                st.write(f"**Categoria:** {row['Categoria']}")
                st.write(f"**Tipo:** {get_transaction_type_display(row['Valor'], row['Categoria'])}")
            
            with col2:
                st.markdown("**Novos Dados:**")
                
                with st.form(f"edit_form_{row['id']}"):
                    # Categoria
                    categorias_disponiveis = [
                        "Alimentação", "Transporte", "Moradia", "Saúde", "Educação",
                        "Lazer", "Vestuário", "Tecnologia", "Viagem", "Investimento",
                        "Salário", "Freelance", "Rendimento", "Outros",
                        "Transferência", "Pagamento Cartão", "PIX", "TED", "DOC"
                    ]
                    
                    nova_categoria = st.selectbox(
                        "Nova Categoria:",
                        options=categorias_disponiveis,
                        index=categorias_disponiveis.index(row['Categoria']) if row['Categoria'] in categorias_disponiveis else 0
                    )
                    
                    # Tipo (classificação manual)
                    tipos_disponiveis = ["💰 Receita", "💸 Despesa", "🔄 Excluída"]
                    tipo_atual = get_transaction_type_display(row['Valor'], row['Categoria'])
                    
                    novo_tipo = st.selectbox(
                        "Classificação:",
                        options=tipos_disponiveis,
                        index=tipos_disponiveis.index(tipo_atual) if tipo_atual in tipos_disponiveis else 2
                    )
                    
                    # Descrição (opcional)
                    nova_descricao = st.text_input(
                        "Nova Descrição (opcional):",
                        value=row['Descrição'],
                        max_chars=200
                    )
                    
                    col_btn1, col_btn2, col_btn3 = st.columns(3)
                    
                    salvar = col_btn1.form_submit_button("✅ Salvar", use_container_width=True)
                    cancelar = col_btn2.form_submit_button("❌ Cancelar", use_container_width=True)
                    deletar = col_btn3.form_submit_button("🗑️ Deletar", use_container_width=True, type="secondary")
                    
                    if salvar:
                        # Mapear tipo para valor do banco
                        tipo_db = None
                        if novo_tipo == "💰 Receita":
                            tipo_db = "CREDIT"
                        elif novo_tipo == "💸 Despesa":
                            tipo_db = "DEBIT"
                        else:
                            tipo_db = "EXCLUDED"
                        
                        # Atualizar transação
                        sucesso = update_transaction_details(
                            transaction_type=row['origem'],
                            transaction_id=row['id'],
                            usuario_id=st.session_state['user_id'],
                            new_category=nova_categoria,
                            new_type=tipo_db,
                            new_description=nova_descricao if nova_descricao != row['Descrição'] else None
                        )
                        
                        if sucesso:
                            st.success("✅ Transação atualizada com sucesso!")
                            # Limpar cache para forçar recarregamento
                            st.cache_data.clear()
                            st.session_state[f"edit_modal_{row['id']}"] = False
                            st.rerun()
                        else:
                            st.error("❌ Erro ao atualizar transação")
                    
                    if cancelar:
                        st.session_state[f"edit_modal_{row['id']}"] = False
                        st.rerun()
                    
                    if deletar:
                        # Confirmar exclusão
                        if st.checkbox("⚠️ Confirmo que desejo deletar esta transação"):
                            sucesso = delete_transaction(
                                transaction_type=row['origem'],
                                transaction_id=row['id'],
                                usuario_id=st.session_state['user_id']
                            )
                            
                            if sucesso:
                                st.success("✅ Transação deletada com sucesso!")
                                # Limpar cache para forçar recarregamento
                                st.cache_data.clear()
                                st.session_state[f"edit_modal_{row['id']}"] = False
                                st.rerun()
                            else:
                                st.error("❌ Erro ao deletar transação")

# Carregar dados com período otimizado
usuario = st.session_state.get('usuario', '')

# Indicador de carregamento com informações do período
with st.spinner(f'⏳ Carregando transações dos últimos {dias_periodo} dias...'):
    df = carregar_dados_transacoes(usuario, dias_periodo)

if df.empty:
    st.warning("⚠️ Nenhuma transação encontrada para o período selecionado!")
    st.info("💡 **Dicas:**")
    st.info("• Tente expandir o período de busca na sidebar")
    st.info("• Verifique suas conexões na página de Cadastro Pluggy")
    if st.button("➕ Conectar Contas"):
        st.switch_page("pages/Cadastro_Pluggy.py")
    st.stop()

# Mostrar estatísticas do período carregado
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("📊 Total Transações", len(df))
with col2:
    if 'Data' in df.columns:
        data_mais_antiga = df['Data'].min().strftime('%d/%m/%Y')
        st.metric("📅 Mais Antiga", data_mais_antiga)
with col3:
    receitas = len(df[df['Valor'] > 0]) if 'Valor' in df.columns else 0
    st.metric("💰 Receitas", receitas)
with col4:
    despesas = len(df[df['Valor'] < 0]) if 'Valor' in df.columns else 0
    st.metric("💸 Despesas", despesas)

# Separador visual
st.markdown("---")

# Sidebar com filtros adicionais
st.sidebar.markdown("---")
st.sidebar.header("🔍 Filtros Adicionais")

# Filtros de data (dentro do período já carregado)
start_date, end_date = filtro_data(df, "gerenciar")

# Mostrar aviso se filtro de data está fora do período carregado
if start_date < data_limite or end_date > date.today():
    st.sidebar.warning("⚠️ Filtro de data pode estar fora do período carregado")

# Filtros de categoria
categorias_selecionadas = filtro_categorias(df, "Filtrar por Categorias", "gerenciar")

# Filtro de tipo de transação
tipos_transacao = st.sidebar.multiselect(
    "Tipo de Classificação",
    options=["💰 Receita", "💸 Despesa", "🔄 Excluída"],
    default=["💰 Receita", "💸 Despesa", "🔄 Excluída"],
    help="Classifique transações por tipo financeiro"
)

# Filtro de origem
origens_disponiveis = df['origem'].unique().tolist() if 'origem' in df.columns else []
origens_selecionadas = st.sidebar.multiselect(
    "Origem dos Dados",
    options=origens_disponiveis,
    default=origens_disponiveis,
    help="Filtre por extratos bancários ou cartões de crédito"
)

# Filtro de valor (novo)
with st.sidebar.expander("💰 Filtro por Valor"):
    if 'Valor' in df.columns and not df.empty:
        valor_min = float(df['Valor'].min())
        valor_max = float(df['Valor'].max())
        
        usar_filtro_valor = st.checkbox("Filtrar por faixa de valor")
        if usar_filtro_valor:
            faixa_valor = st.slider(
                "Faixa de Valor (R$):",
                min_value=valor_min,
                max_value=valor_max,
                value=(valor_min, valor_max),
                step=10.0,
                format="R$ %.2f"
            )
        else:
            faixa_valor = (valor_min, valor_max)
    else:
        usar_filtro_valor = False
        faixa_valor = (0, 0)

# Aplicar filtros progressivamente
df_filtrado = aplicar_filtros(df, start_date, end_date, categorias_selecionadas)

# Filtrar por origem
if 'origem' in df_filtrado.columns and origens_selecionadas:
    df_filtrado = df_filtrado[df_filtrado['origem'].isin(origens_selecionadas)]

# Filtrar por valor se ativo
if usar_filtro_valor and 'Valor' in df_filtrado.columns:
    df_filtrado = df_filtrado[
        (df_filtrado['Valor'] >= faixa_valor[0]) & 
        (df_filtrado['Valor'] <= faixa_valor[1])
    ]

# Mostrar resumo dos filtros aplicados
filtros_ativos = []
if start_date != df['Data'].min().date() or end_date != df['Data'].max().date():
    filtros_ativos.append(f"📅 Data: {start_date.strftime('%d/%m')} a {end_date.strftime('%d/%m')}")
if len(categorias_selecionadas) < len(df['Categoria'].unique()):
    filtros_ativos.append(f"🏷️ Categorias: {len(categorias_selecionadas)} selecionadas")
if len(tipos_transacao) < 3:
    filtros_ativos.append(f"💰 Tipos: {', '.join(tipos_transacao)}")
if len(origens_selecionadas) < len(origens_disponiveis):
    filtros_ativos.append(f"📊 Origem: {', '.join(origens_selecionadas)}")
if usar_filtro_valor:
    filtros_ativos.append(f"💰 Valor: R$ {faixa_valor[0]:.2f} a R$ {faixa_valor[1]:.2f}")

if filtros_ativos:
    st.info(f"🔍 **Filtros ativos:** {' • '.join(filtros_ativos)}")
    
# Mostrar estatísticas filtradas
if not df_filtrado.empty:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 Transações Filtradas", len(df_filtrado), delta=len(df_filtrado) - len(df))
    with col2:
        valor_total = df_filtrado['Valor'].sum() if 'Valor' in df_filtrado.columns else 0
        st.metric("💰 Valor Total", f"R$ {valor_total:,.2f}")
    with col3:
        percentual = (len(df_filtrado) / len(df)) * 100 if len(df) > 0 else 0
        st.metric("📈 % do Total", f"{percentual:.1f}%")

# Classificar transações para filtrar por tipo
if not df_filtrado.empty and tipos_transacao:
    resumo_detalhado = calcular_resumo_financeiro(df_filtrado)
    
    indices_receitas = set(idx for idx, val in resumo_detalhado.get('é_receita_real', {}).items() if val)
    indices_despesas = set(idx for idx, val in resumo_detalhado.get('é_despesa_real', {}).items() if val)
    todos_indices = set(df_filtrado.index)
    indices_excluidas = todos_indices - indices_receitas - indices_despesas
    
    indices_filtrados = set()
    
    if "💰 Receita" in tipos_transacao:
        indices_filtrados.update(indices_receitas)
    if "💸 Despesa" in tipos_transacao:
        indices_filtrados.update(indices_despesas)
    if "🔄 Excluída" in tipos_transacao:
        indices_filtrados.update(indices_excluidas)
    
    if indices_filtrados:
        df_filtrado = df_filtrado.loc[list(indices_filtrados)]
    else:
        df_filtrado = pd.DataFrame()

# Mostrar resumo
if not df_filtrado.empty:
    st.subheader("📊 Resumo das Transações Filtradas")
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_transacoes = len(df_filtrado)
    valor_total = df_filtrado['Valor'].sum()
    
    # Calcular estatísticas por tipo
    resumo_detalhado = calcular_resumo_financeiro(df_filtrado)
    num_receitas = len([idx for idx, val in resumo_detalhado.get('é_receita_real', {}).items() if val])
    num_despesas = len([idx for idx, val in resumo_detalhado.get('é_despesa_real', {}).items() if val])
    num_excluidas = total_transacoes - num_receitas - num_despesas
    
    col1.metric("Total de Transações", total_transacoes)
    col2.metric("💰 Receitas", num_receitas)
    col3.metric("💸 Despesas", num_despesas)
    col4.metric("🔄 Excluídas", num_excluidas)

# Exibir transações
if not df_filtrado.empty:
    st.subheader("📋 Lista de Transações")
    
    # Ordenar por data (mais recentes primeiro)
    df_filtrado = df_filtrado.sort_values('Data', ascending=False)
    
    # Preparar dados para exibição
    df_display = df_filtrado.copy()
    df_display = formatar_df_monetario(df_display, "Valor")
    
    # Adicionar coluna de tipo/classificação
    df_display['Classificação'] = df_display.apply(
        lambda row: get_transaction_type_display(row['Valor'], row['Categoria']), 
        axis=1
    )
    
    # Adicionar coluna de ações
    df_display['Ações'] = '⚙️'
    
    # Configurar colunas para exibição
    colunas_exibir = ['Data', 'ValorFormatado', 'Categoria', 'Classificação', 'Descrição', 'origem', 'Ações']
    colunas_renomear = {
        'ValorFormatado': 'Valor',
        'origem': 'Origem',
        'Ações': 'Editar'
    }
    
    # Exibir tabela com botões de edição
    for idx, row in df_display.iterrows():
        with st.expander(
            f"📅 {row['Data'].strftime('%d/%m/%Y')} - {row['Categoria']} - {row['ValorFormatado']} - {row['Classificação']}"
        ):
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.write(f"**Descrição:** {row['Descrição']}")
                st.write(f"**Origem:** {row['origem'].upper()}")
            
            with col2:
                if st.button(f"✏️ Editar", key=f"edit_{row['id']}", use_container_width=True):
                    st.session_state[f"edit_modal_{row['id']}"] = True
                    st.rerun()
            
            with col3:
                st.write(f"**ID:** {row['id']}")
            
            # Mostrar modal de edição se ativo
            if st.session_state.get(f"edit_modal_{row['id']}", False):
                mostrar_modal_edicao(row)

else:
    st.info("📋 Nenhuma transação encontrada com os filtros aplicados.")

# Ações em lote aprimoradas
if not df_filtrado.empty:
    st.markdown("---")
    st.subheader("🔧 Ações em Lote")
    
    # Abas para diferentes tipos de ações
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Recategorizar", "🏷️ Renomear", "🧹 Limpeza", "➕ Adicionar"])
    
    with tab1:
        st.markdown("#### 📊 Recategorização em Lote")
        
        col1, col2 = st.columns(2)
        
        with col1:
            with st.form("recategorizar_lote"):
                categoria_origem = st.selectbox(
                    "Categoria Atual:",
                    options=["Todas"] + sorted(df_filtrado['Categoria'].unique().tolist())
                )
                
                nova_categoria_lote = st.selectbox(
                    "Nova Categoria:",
                    options=[
                        "Alimentação", "Transporte", "Moradia", "Saúde", "Educação",
                        "Lazer", "Vestuário", "Tecnologia", "Viagem", "Investimento",
                        "Salário", "Freelance", "Rendimento", "Outros",
                        "Transferência", "Pagamento Cartão", "PIX", "TED", "DOC"
                    ]
                )
                
                aplicar_lote = st.form_submit_button("🔄 Aplicar Recategorização")
                
                if aplicar_lote:
                    if categoria_origem == "Todas":
                        transacoes_alvo = df_filtrado
                    else:
                        transacoes_alvo = df_filtrado[df_filtrado['Categoria'] == categoria_origem]
                    
                    with st.spinner(f"🔄 Atualizando {len(transacoes_alvo)} transações..."):
                        sucesso_count = 0
                        erro_count = 0
                        
                        for idx, row in transacoes_alvo.iterrows():
                            sucesso = update_transaction_details(
                                transaction_type=row['origem'],
                                transaction_id=row['id'],
                                usuario_id=st.session_state['user_id'],
                                new_category=nova_categoria_lote
                            )
                            
                            if sucesso:
                                sucesso_count += 1
                            else:
                                erro_count += 1
                        
                        if sucesso_count > 0:
                            st.success(f"✅ {sucesso_count} transações atualizadas com sucesso!")
                            st.cache_data.clear()
                            st.rerun()
                        
                        if erro_count > 0:
                            st.error(f"❌ {erro_count} transações falharam na atualização")
        
        with col2:
            if categoria_origem and categoria_origem != "Todas":
                preview_count = len(df_filtrado[df_filtrado['Categoria'] == categoria_origem])
                st.info(f"🔍 **Preview:** {preview_count} transações serão afetadas")
                
                if preview_count > 0 and preview_count <= 10:
                    st.write("**Exemplos de transações que serão alteradas:**")
                    preview_df = df_filtrado[df_filtrado['Categoria'] == categoria_origem].head(5)
                    for _, row in preview_df.iterrows():
                        st.write(f"• {row['Data'].strftime('%d/%m')} - {row['Descrição'][:30]}...")
            else:
                st.info(f"🔍 **Preview:** {len(df_filtrado)} transações serão afetadas")
    
    with tab2:
        st.markdown("#### 🏷️ Padronização de Descrições")
        
        with st.form("padronizar_descricoes"):
            col1, col2 = st.columns(2)
            
            with col1:
                buscar_texto = st.text_input("Buscar por (texto na descrição):")
                substituir_por = st.text_input("Substituir por:")
            
            with col2:
                case_sensitive = st.checkbox("Diferenciar maiúsculas/minúsculas")
                apenas_palavra_completa = st.checkbox("Apenas palavra completa")
            
            aplicar_substituicao = st.form_submit_button("🔄 Aplicar Substituição")
            
            if aplicar_substituicao and buscar_texto and substituir_por:
                import re
                
                transacoes_afetadas = 0
                
                for idx, row in df_filtrado.iterrows():
                    descricao_atual = row['Descrição']
                    
                    if case_sensitive:
                        busca = buscar_texto
                    else:
                        busca = buscar_texto.lower()
                        descricao_atual = descricao_atual.lower()
                    
                    if apenas_palavra_completa:
                        pattern = rf'\b{re.escape(busca)}\b'
                        if re.search(pattern, descricao_atual):
                            nova_descricao = re.sub(pattern, substituir_por, row['Descrição'], flags=0 if case_sensitive else re.IGNORECASE)
                        else:
                            continue
                    else:
                        if busca in descricao_atual:
                            nova_descricao = row['Descrição'].replace(buscar_texto, substituir_por)
                        else:
                            continue
                    
                    sucesso = update_transaction_details(
                        transaction_type=row['origem'],
                        transaction_id=row['id'],
                        usuario_id=st.session_state['user_id'],
                        new_description=nova_descricao
                    )
                    
                    if sucesso:
                        transacoes_afetadas += 1
                
                if transacoes_afetadas > 0:
                    st.success(f"✅ {transacoes_afetadas} descrições atualizadas!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.info("ℹ️ Nenhuma transação encontrada com o texto especificado")
    
    with tab3:
        st.markdown("#### 🧹 Ferramentas de Limpeza")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Cache e Performance:**")
            if st.button("🧹 Limpar Cache", help="Recarregar dados do banco de dados"):
                st.cache_data.clear()
                st.success("Cache limpo! Recarregando dados...")
                st.rerun()
            
            if st.button("🔄 Forçar Recarga Completa", help="Recarregar dados da API"):
                import os
                os.environ["FORCE_REFRESH"] = "true"
                st.cache_data.clear()
                st.success("Forçando recarga da API...")
                st.rerun()
        
        with col2:
            st.markdown("**Estatísticas do Período:**")
            total_dias = (df['Data'].max() - df['Data'].min()).days if not df.empty else 0
            st.info(f"""
            📅 **Período carregado:** {total_dias} dias
            📊 **Total de transações:** {len(df)}
            🔍 **Transações filtradas:** {len(df_filtrado)}
            💾 **Uso de cache:** {100 if len(df) > 0 else 0}%
            """)
    
    with tab4:
        st.markdown("#### ➕ Adicionar Transação Manual")
        st.info("💡 Adicione transações que não foram capturadas automaticamente pela API ou de contas não conectadas")
        
        with st.form("adicionar_transacao_manual"):
            col1, col2 = st.columns(2)
            
            with col1:
                nova_data = st.date_input(
                    "📅 Data da Transação:",
                    value=date.today(),
                    max_value=date.today(),
                    help="Selecione a data em que a transação ocorreu"
                )
                
                nova_descricao = st.text_input(
                    "📝 Descrição:",
                    placeholder="Ex: Compra no supermercado",
                    help="Descreva a transação de forma clara"
                )
                
                novo_valor = st.number_input(
                    "💰 Valor:",
                    value=0.0,
                    step=0.01,
                    format="%.2f",
                    help="Use valores positivos para receitas e negativos para despesas"
                )
            
            with col2:
                # Obter categorias únicas existentes para sugerir
                categorias_existentes = sorted(df['Categoria'].unique().tolist()) if not df.empty else []
                categorias_sugeridas = [
                    "Alimentação", "Transporte", "Saúde", "Educação", "Lazer",
                    "Casa", "Vestuário", "Investimentos", "Renda", "Outros"
                ]
                
                # Combinar e remover duplicatas mantendo ordem
                opcoes_categoria = []
                seen = set()
                for cat in categorias_sugeridas + categorias_existentes:
                    if cat not in seen:
                        opcoes_categoria.append(cat)
                        seen.add(cat)
                
                nova_categoria = st.selectbox(
                    "🏷️ Categoria:",
                    options=opcoes_categoria,
                    help="Selecione ou escolha uma categoria existente"
                )
                
                # Campo para categoria personalizada
                categoria_personalizada = st.text_input(
                    "🎯 Categoria Personalizada (opcional):",
                    placeholder="Digite uma nova categoria",
                    help="Deixe vazio para usar a categoria selecionada acima"
                )
                
                # Obter contas existentes
                contas_existentes = sorted(df['Conta'].unique().tolist()) if not df.empty else []
                contas_sugeridas = ["Conta Corrente", "Poupança", "Cartão de Crédito", "Dinheiro", "PIX"]
                
                # Combinar opções de conta
                opcoes_conta = []
                seen_contas = set()
                for conta in contas_sugeridas + contas_existentes:
                    if conta not in seen_contas:
                        opcoes_conta.append(conta)
                        seen_contas.add(conta)
                
                nova_conta = st.selectbox(
                    "🏦 Conta:",
                    options=opcoes_conta,
                    help="Selecione a conta onde a transação ocorreu"
                )
            
            # Visualização prévia da transação
            st.markdown("---")
            st.markdown("**🔍 Prévia da Transação:**")
            
            if nova_descricao and novo_valor != 0:
                categoria_final = categoria_personalizada if categoria_personalizada else nova_categoria
                tipo_transacao = "💰 Receita" if novo_valor > 0 else "💸 Despesa"
                valor_formatado = formatar_valor_monetario(novo_valor)
                
                st.success(f"""
                **{tipo_transacao}**
                - 📅 **Data:** {nova_data.strftime('%d/%m/%Y')}
                - 📝 **Descrição:** {nova_descricao}
                - 💰 **Valor:** {valor_formatado}
                - 🏷️ **Categoria:** {categoria_final}
                - 🏦 **Conta:** {nova_conta}
                """)
            
            # Botões de ação
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                adicionar_transacao = st.form_submit_button(
                    "➕ Adicionar Transação",
                    type="primary",
                    use_container_width=True
                )
            
            with col_btn2:
                limpar_formulario = st.form_submit_button(
                    "🧹 Limpar Campos",
                    use_container_width=True
                )
            
            # Processar adição da transação
            if adicionar_transacao:
                if not nova_descricao:
                    st.error("❌ A descrição é obrigatória!")
                elif novo_valor == 0:
                    st.error("❌ O valor deve ser diferente de zero!")
                else:
                    try:
                        # Determinar categoria final
                        categoria_final = categoria_personalizada if categoria_personalizada else nova_categoria
                        
                        # Gerar ID único para a nova transação
                        import hashlib
                        content = f"{nova_data}-{novo_valor}-{nova_descricao}-{nova_conta}"
                        novo_id = hashlib.md5(content.encode()).hexdigest()[:16]
                        
                        # Criar novo registro de transação
                        nova_transacao = {
                            'id': novo_id,
                            'Data': pd.to_datetime(nova_data),
                            'Descrição': nova_descricao,
                            'Valor': float(novo_valor),
                            'Categoria': categoria_final,
                            'Conta': nova_conta,
                            'origem': 'manual'  # Marcar como transação manual
                        }
                        
                        # Verificar se já existe uma transação idêntica
                        if not df.empty:
                            transacao_existente = df[
                                (df['Data'].dt.date == nova_data) &
                                (df['Descrição'] == nova_descricao) &
                                (df['Valor'] == novo_valor) &
                                (df['Conta'] == nova_conta)
                            ]
                            
                            if not transacao_existente.empty:
                                st.warning("⚠️ Uma transação muito similar já existe. Tem certeza que deseja adicionar?")
                                
                                # Adicionar checkbox de confirmação
                                if st.checkbox("✅ Sim, adicionar mesmo assim"):
                                    # Adicionar timestamp ao ID para garantir unicidade
                                    from datetime import datetime
                                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                                    novo_id = f"{novo_id}_{timestamp}"
                                    nova_transacao['id'] = novo_id
                                else:
                                    st.stop()
                        
                        # Salvar transação no banco de dados
                        with get_connection() as conn:
                            cursor = conn.cursor()
                            
                            # Inserir na tabela de transações manuais (ou criar se não existir)
                            cursor.execute('''
                                CREATE TABLE IF NOT EXISTS transacoes_manuais (
                                    id TEXT PRIMARY KEY,
                                    usuario TEXT NOT NULL,
                                    data DATE NOT NULL,
                                    descricao TEXT NOT NULL,
                                    valor REAL NOT NULL,
                                    categoria TEXT NOT NULL,
                                    conta TEXT NOT NULL,
                                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                )
                            ''')
                            
                            cursor.execute('''
                                INSERT INTO transacoes_manuais 
                                (id, usuario, data, descricao, valor, categoria, conta)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                novo_id,
                                st.session_state.get('usuario', 'default'),
                                nova_data.strftime('%Y-%m-%d'),
                                nova_descricao,
                                novo_valor,
                                categoria_final,
                                nova_conta
                            ))
                            
                            conn.commit()
                        
                        st.success(f"✅ Transação adicionada com sucesso! ID: {novo_id}")
                        
                        # Limpar cache para mostrar a nova transação
                        st.cache_data.clear()
                        
                        # Aguardar um momento e recarregar
                        time.sleep(1)
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Erro ao adicionar transação: {str(e)}")
            
            elif limpar_formulario:
                st.rerun()

# Seção de ajuda e dicas
st.markdown("---")
with st.expander("💡 Guia de Uso e Dicas"):
    st.markdown("""
    ### 📋 Como Usar o Gerenciador de Transações
    
    #### 🎯 **Controle de Período**
    - **Período Recomendado**: 6 meses oferece bom equilíbrio entre dados e performance
    - **Carregamento Rápido**: Use períodos menores (1-3 meses) para análises rápidas
    - **Análise Completa**: Use períodos maiores (1 ano+) para relatórios anuais
    
    #### 🔍 **Filtros Inteligentes**
    - **Data**: Refine ainda mais dentro do período carregado
    - **Categoria**: Foque em tipos específicos de gastos
    - **Valor**: Encontre transações grandes ou pequenas rapidamente
    - **Origem**: Separe extratos bancários de cartões de crédito
    
    #### ⚙️ **Edição de Transações**
    - **Individual**: Clique em "✏️ Editar" para ajustes precisos
    - **Em Lote**: Use as abas de ações para mudanças em massa
    - **Segurança**: Todas as alterações são registradas nos logs
    
    #### 🏷️ **Classificação Manual**
    - **💰 Receita**: Inclui nos cálculos como entrada de dinheiro
    - **💸 Despesa**: Inclui nos cálculos como saída de dinheiro  
    - **🔄 Excluída**: Remove dos cálculos (útil para transferências internas)
    
    #### ⚠️ **Importante**
    - **Backup**: Mudanças são permanentes - tenha certeza antes de aplicar
    - **Performance**: Períodos longos podem demorar mais para carregar
    - **Cache**: Use "Limpar Cache" se os dados parecerem desatualizados
    """)

# Footer com informações do sistema
st.markdown("---")
st.caption(f"""
🔧 **Sistema:** Gerenciamento de Transações v2.0 | 
📅 **Período Ativo:** {(date.today() - timedelta(days=dias_periodo)).strftime('%d/%m/%Y')} a {date.today().strftime('%d/%m/%Y')} | 
⚡ **Performance:** {"Rápida" if dias_periodo <= 90 else "Balanceada" if dias_periodo <= 180 else "Completa"}
""")
