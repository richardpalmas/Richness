# Verificar se está sendo executado no contexto do Streamlit
try:
    # Tentar acessar algo específico do Streamlit
    import streamlit as st
    # Verificar se há contexto de execução do Streamlit ativo
    from streamlit.runtime.scriptrunner import get_script_run_ctx
    if get_script_run_ctx() is None:
        # Se não há contexto de execução, não está rodando via streamlit run
        exit()
except:
    # Se não conseguir importar ou acessar, sair silenciosamente
    exit()

import pandas as pd
import plotly.express as px
from datetime import date, timedelta, datetime
import json
import os
import hashlib
import time
import sys

from componentes.profile_pic_component import boas_vindas_com_foto
from utils.formatacao import formatar_valor_monetario, formatar_df_monetario
from utils.filtros import filtro_data
from utils.config import (
    get_cache_categorias_file,
    get_descricoes_personalizadas_file,
    get_transacoes_excluidas_file,
    get_current_user
)

# Importações para Insights e Personalidade IA
from componentes.personality_selector import render_personality_selector
from componentes.insight_card import exibir_insight_card
from services.llm_service import LLMService
from services.insights_service_v2 import InsightsServiceV2

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
@st.cache_data(ttl=1800, show_spinner="Carregando transações de cartão...")  # 30 minutos ao invés de 10
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

# Botão para ativar/desativar o modo depurador
if 'modo_depurador' not in st.session_state:
    st.session_state['modo_depurador'] = False
if st.sidebar.button(f"{'🛑 Desativar' if st.session_state['modo_depurador'] else '🐞 Ativar'} Modo Depurador", help="Exibe logs detalhados dos insights na tela"):
    st.session_state['modo_depurador'] = not st.session_state['modo_depurador']
    st.rerun()
st.sidebar.write(f"Modo Depurador: {'Ativo' if st.session_state['modo_depurador'] else 'Inativo'}")

# Ferramentas de Cache (apenas para modo depurador)
if st.session_state.get('modo_depurador'):
    st.sidebar.markdown("### 🗄️ Ferramentas de Cache (Cartão)")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("🗑️ Limpar Cache", help="Remove cache expirado do usuário", key="limpar_cache_cartao_btn"):
            try:
                from services.insights_cache_service import InsightsCacheService
                cache_service = InsightsCacheService()
                
                # Limpar apenas cache expirado
                removidos = cache_service.limpar_cache_expirado_automatico()
                
                st.sidebar.success(f"✅ {removidos} entradas expiradas removidas")
                
                # Rerun para atualizar
                time.sleep(0.5)
                st.rerun()
                
            except Exception as e:
                st.sidebar.error(f"❌ Erro: {e}")
    
    with col2:
        if st.button("🔄 Reset Cache", help="Remove TODO cache do usuário e força regeneração", key="reset_cache_cartao_btn"):
            try:
                from services.insights_cache_service import InsightsCacheService
                cache_service = InsightsCacheService()
                
                # Obter user_id
                db = DatabaseManager()
                usuario_repo = UsuarioRepository(db)
                user_data = usuario_repo.obter_usuario_por_username(usuario)
                user_id = user_data.get('id') if user_data else None
                
                if user_id:
                    # Invalidar TODO cache do usuário (válido e expirado)
                    removidos = cache_service.invalidar_cache_por_mudanca_dados(user_id)
                    
                    # Marcar flag para forçar regeneração específica do cartão
                    st.session_state['forcar_regeneracao_insights_cartao'] = True
                    
                    st.sidebar.success(f"✅ Cache resetado ({removidos} entradas)")
                    st.sidebar.warning("⚡ Próximos insights serão regenerados via LLM")
                    
                    # Rerun para regenerar
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.sidebar.error("❌ Usuário não encontrado")
            except Exception as e:
                st.sidebar.error(f"❌ Erro: {e}")
    
    # Botão para forçar regeneração sem limpar cache
    if st.sidebar.button("⚡ Forçar Regeneração", help="Força nova chamada ao LLM sem limpar cache", key="forcar_regeneracao_cartao_btn"):
        try:
            # Obter user_id
            db = DatabaseManager()
            usuario_repo = UsuarioRepository(db)
            user_data = usuario_repo.obter_usuario_por_username(usuario)
            user_id = user_data.get('id') if user_data else None
            
            if user_id:
                # NÃO limpar cache - apenas marcar flag para ignorá-lo
                st.session_state['forcar_regeneracao_insights_cartao'] = True
                
                st.sidebar.success("⚡ Regeneração forçada ativada!")
                st.sidebar.info("🔄 Próximos insights ignorarão cache e usarão LLM")
                
                # Rerun imediato
                time.sleep(0.5)
                st.rerun()
            else:
                st.sidebar.error("❌ Usuário não encontrado")
        except Exception as e:
            st.sidebar.error(f"❌ Erro: {e}")

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
            # Apenas recarregar os dados, sem limpar cache de insights
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

def exibir_grid_insights_cartao(usuario):
    """Exibe insights personalizados específicos para cartão de crédito com cache inteligente"""
    try:
        # Importar o serviço de cache
        from services.insights_cache_service import InsightsCacheService
        
        # Obter user_id
        db = DatabaseManager()
        usuario_repo = UsuarioRepository(db)
        user_data = usuario_repo.obter_usuario_por_username(usuario)
        if not user_data:
            st.error("Usuário não encontrado")
            return
        user_id = user_data.get('id')
        if not user_id:
            st.error("Erro ao identificar o usuário")
            return
        
        # Inicializar serviços
        insights_service = InsightsServiceV2()
        cache_service = InsightsCacheService()
        
        # Obter personalidade selecionada
        personalidade_sel = st.session_state.get('ai_personality', 'clara')
        
        # Obter nome amigável/avatar
        avatar_map = {
            'clara': 'imgs/perfil_amigavel_fem.png',
            'tecnica': 'imgs/perfil_tecnico_masc.png',
            'durona': 'imgs/perfil_durao_mas.png'
        }
        nome_map = {
            'clara': 'Ana',
            'tecnica': 'Fernando',
            'durona': 'Jorge'
        }
        avatar_path = avatar_map.get(personalidade_sel, 'imgs/perfil_amigavel_fem.png')
        nome_ia = nome_map.get(personalidade_sel, 'Ana')
        
        # Buscar APENAS as últimas 30 transações de FATURA/CARTÃO
        transacao_service = TransacaoService()
        df_todas = transacao_service.listar_transacoes_usuario(usuario, limite=5000)
        
        # Filtrar apenas transações de cartão/fatura
        if 'origem' in df_todas.columns:
            df_todas['origem'] = df_todas['origem'].astype(str)
            df_fatura = df_todas[df_todas['origem'].str.contains('fatura|cartao|credit', case=False, na=False)]
        else:
            df_fatura = pd.DataFrame()
        
        # Pegar as últimas 30 transações de fatura
        if not df_fatura.empty and 'data' in df_fatura.columns:
            df_fatura['data'] = pd.to_datetime(df_fatura['data'], errors='coerce')
            mask = pd.Series(df_fatura['data']).notnull()
            df_fatura_filtrado = df_fatura[mask]
            if isinstance(df_fatura_filtrado, pd.DataFrame):
                ultimas_fatura = df_fatura_filtrado.sort_values(by='data', ascending=False).head(30)
            else:
                ultimas_fatura = df_fatura_filtrado
        else:
            ultimas_fatura = df_fatura.head(30) if not df_fatura.empty else pd.DataFrame()
        
        # Calcular métricas específicas do cartão
        total_gastos_cartao = abs(ultimas_fatura['valor'].sum()) if isinstance(ultimas_fatura, pd.DataFrame) and not ultimas_fatura.empty else 0
        maior_gasto_cartao = abs(ultimas_fatura['valor'].min()) if isinstance(ultimas_fatura, pd.DataFrame) and not ultimas_fatura.empty else 0
        gasto_medio_cartao = total_gastos_cartao / len(ultimas_fatura) if isinstance(ultimas_fatura, pd.DataFrame) and not ultimas_fatura.empty else 0
        
        # Obter parâmetros de personalidade para o cache
        from utils.repositories_v2 import PersonalidadeIARepository
        personalidade_repo = PersonalidadeIARepository(db)
        
        perfil_nome_amigavel = "Clara e Acolhedora"
        perfil_nome_tecnico = "Técnico e Formal"
        perfil_nome_durao = "Durão e Informal"
        
        if personalidade_sel == 'clara':
            params_db = personalidade_repo.obter_personalidade(user_id, perfil_nome_amigavel)
            params_ss = st.session_state.get('perfil_amigavel_parametros', {})
            params = params_db if params_db and params_db.get('emojis') not in [None, ''] else params_ss
            if params and (not params.get('emojis') or params.get('emojis') == ''):
                params['emojis'] = 'Nenhum'
        elif personalidade_sel == 'tecnica':
            params_db = personalidade_repo.obter_personalidade(user_id, perfil_nome_tecnico)
            params_ss = st.session_state.get('perfil_tecnico_parametros', {})
            params = params_db if params_db and params_db.get('emojis') not in [None, ''] else params_ss
            if params and (not params.get('emojis') or params.get('emojis') == ''):
                params['emojis'] = 'Nenhum'
        elif personalidade_sel == 'durona':
            params_db = personalidade_repo.obter_personalidade(user_id, perfil_nome_durao)
            params_ss = st.session_state.get('perfil_durao_parametros', {})
            params = params_db if params_db and params_db.get('emojis') not in [None, ''] else params_ss
            if params and (not params.get('emojis') or params.get('emojis') == ''):
                params['emojis'] = 'Nenhum'
        else:
            # Para perfil customizado
            perfil_custom = next((p for p in st.session_state.get('perfis_customizados', []) if p.get('nome_perfil') == personalidade_sel), None)
            if perfil_custom:
                params = {
                    'formalidade': perfil_custom.get('formalidade', ''),
                    'emojis': perfil_custom.get('uso_emojis', ''),
                    'tom': perfil_custom.get('tom', ''),
                    'foco': perfil_custom.get('foco', '')
                }
            else:
                params = {}
        
        # Verificar se deve forçar regeneração
        forcar_regeneracao = st.session_state.get('forcar_regeneracao_insights_cartao', False)
        
        # Limpar flag após usar
        if forcar_regeneracao:
            st.session_state['forcar_regeneracao_insights_cartao'] = False
        
        # Gerar insights específicos do cartão usando cache inteligente
        insights = []
        
        # Insight 1: Total de gastos no cartão
        contexto_total_cartao = {
            'personalidade': personalidade_sel,
            'total_gastos': total_gastos_cartao,
            'ultimas_transacoes_cartao': ultimas_fatura.to_dict('records') if isinstance(ultimas_fatura, pd.DataFrame) and not ultimas_fatura.empty else [],
            'usuario': user_data,
            'periodo_analise': '30 últimas transações'
        }
        prompt_total_cartao = "Analise o total de gastos no cartão de crédito baseado nas últimas transações, considerando o perfil da IA. Cite o valor e dê uma opinião objetiva em até 250 caracteres. NÃO inclua saudações como 'Olá' ou cumprimentos."
        
        insight_total_cartao = cache_service.gerar_insight_com_cache(
            user_id=user_id,
            insight_type='total_gastos_cartao',
            personalidade=personalidade_sel,
            data_context=contexto_total_cartao,
            prompt=prompt_total_cartao,
            personalidade_params=params or {},
            forcar_regeneracao=forcar_regeneracao
        )
        
        insights.append({
            'tipo': 'neutro' if total_gastos_cartao <= gasto_medio_cartao * 20 else 'alerta',
            'titulo': insight_total_cartao['titulo'],
            'valor': insight_total_cartao['valor'] or formatar_valor_monetario(total_gastos_cartao),
            'comentario': insight_total_cartao['comentario'][:250] + ('...' if len(insight_total_cartao['comentario']) > 250 else ''),
            'assinatura': nome_ia,
            'avatar': avatar_path,
            'saudacao': None,
            'cache_info': f"Cache: {insight_total_cartao['source']}" if st.session_state.get('modo_depurador') else None
        })
        
        # Insight 2: Maior gasto do cartão
        maior_gasto_info = None
        if isinstance(ultimas_fatura, pd.DataFrame) and not ultimas_fatura.empty and 'valor' in ultimas_fatura.columns:
            idx_min = ultimas_fatura['valor'].idxmin()
            maior_gasto_info = ultimas_fatura.loc[idx_min]
        
        contexto_maior_gasto_cartao = {
            'personalidade': personalidade_sel,
            'maior_gasto': maior_gasto_info.to_dict() if maior_gasto_info is not None and hasattr(maior_gasto_info, 'to_dict') else {},
            'valor_maior_gasto': maior_gasto_cartao,
            'ultimas_transacoes_cartao': ultimas_fatura.to_dict('records') if isinstance(ultimas_fatura, pd.DataFrame) and not ultimas_fatura.empty else [],
            'usuario': user_data
        }
        prompt_maior_gasto_cartao = "Analise o maior gasto no cartão de crédito, citando categoria, valor e contexto de forma personalizada, em até 250 caracteres. NÃO inclua saudações como 'Olá' ou cumprimentos."
        
        insight_maior_gasto_cartao = cache_service.gerar_insight_com_cache(
            user_id=user_id,
            insight_type='maior_gasto_cartao',
            personalidade=personalidade_sel,
            data_context=contexto_maior_gasto_cartao,
            prompt=prompt_maior_gasto_cartao,
            personalidade_params=params or {},
            forcar_regeneracao=forcar_regeneracao
        )
        
        insights.append({
            'tipo': 'negativo',
            'titulo': insight_maior_gasto_cartao['titulo'],
            'valor': insight_maior_gasto_cartao['valor'] or formatar_valor_monetario(maior_gasto_cartao),
            'comentario': insight_maior_gasto_cartao['comentario'][:250] + ('...' if len(insight_maior_gasto_cartao['comentario']) > 250 else ''),
            'assinatura': nome_ia,
            'avatar': avatar_path,
            'saudacao': None,
            'cache_info': f"Cache: {insight_maior_gasto_cartao['source']}" if st.session_state.get('modo_depurador') else None
        })
        
        # Insight 3: Padrão de gastos no cartão
        categoria_mais_gasta = None
        if isinstance(ultimas_fatura, pd.DataFrame) and not ultimas_fatura.empty and 'categoria' in ultimas_fatura.columns:
            gastos_por_categoria = ultimas_fatura.groupby('categoria')['valor'].sum().abs()
            categoria_mais_gasta = gastos_por_categoria.idxmax() if not gastos_por_categoria.empty else None
        
        contexto_padrao_cartao = {
            'personalidade': personalidade_sel,
            'categoria_predominante': categoria_mais_gasta,
            'gasto_medio': gasto_medio_cartao,
            'total_transacoes': len(ultimas_fatura) if isinstance(ultimas_fatura, pd.DataFrame) and not ultimas_fatura.empty else 0,
            'ultimas_transacoes_cartao': ultimas_fatura.to_dict('records') if isinstance(ultimas_fatura, pd.DataFrame) and not ultimas_fatura.empty else [],
            'usuario': user_data
        }
        prompt_padrao_cartao = "Analise o padrão de gastos no cartão, identificando a categoria predominante e dando dicas personalizadas, em até 250 caracteres. NÃO inclua saudações como 'Olá' ou cumprimentos."
        
        insight_padrao_cartao = cache_service.gerar_insight_com_cache(
            user_id=user_id,
            insight_type='padrao_gastos_cartao',
            personalidade=personalidade_sel,
            data_context=contexto_padrao_cartao,
            prompt=prompt_padrao_cartao,
            personalidade_params=params or {},
            forcar_regeneracao=forcar_regeneracao
        )
        
        insights.append({
            'tipo': 'positivo',
            'titulo': insight_padrao_cartao['titulo'],
            'valor': insight_padrao_cartao['valor'] or f"{len(ultimas_fatura)} transações",
            'comentario': insight_padrao_cartao['comentario'][:250] + ('...' if len(insight_padrao_cartao['comentario']) > 250 else ''),
            'assinatura': nome_ia,
            'avatar': avatar_path,
            'saudacao': None,
            'cache_info': f"Cache: {insight_padrao_cartao['source']}" if st.session_state.get('modo_depurador') else None
        })
        
        # Insight 4: Recomendação de controle do cartão
        contexto_controle_cartao = {
            'personalidade': personalidade_sel,
            'total_gastos': total_gastos_cartao,
            'maior_gasto': maior_gasto_cartao,
            'gasto_medio': gasto_medio_cartao,
            'ultimas_transacoes_cartao': ultimas_fatura.to_dict('records') if isinstance(ultimas_fatura, pd.DataFrame) and not ultimas_fatura.empty else [],
            'usuario': user_data
        }
        prompt_controle_cartao = "Dê uma recomendação personalizada sobre controle de gastos no cartão de crédito, considerando os padrões identificados, em até 250 caracteres. NÃO inclua saudações como 'Olá' ou cumprimentos."
        
        insight_controle_cartao = cache_service.gerar_insight_com_cache(
            user_id=user_id,
            insight_type='controle_cartao',
            personalidade=personalidade_sel,
            data_context=contexto_controle_cartao,
            prompt=prompt_controle_cartao,
            personalidade_params=params or {},
            forcar_regeneracao=forcar_regeneracao
        )
        
        insights.append({
            'tipo': 'alerta',
            'titulo': insight_controle_cartao['titulo'],
            'valor': '',
            'comentario': insight_controle_cartao['comentario'][:250] + ('...' if len(insight_controle_cartao['comentario']) > 250 else ''),
            'assinatura': nome_ia,
            'avatar': avatar_path,
            'saudacao': None,
            'cache_info': f"Cache: {insight_controle_cartao['source']}" if st.session_state.get('modo_depurador') else None
        })
        
        # Modo Depurador: logs visuais e estatísticas de cache
        if st.session_state.get('modo_depurador'):
            st.subheader('🪲 Logs do Modo Depurador (Insights Cartão com Cache)')
            
            # Mostrar se regeneração foi forçada
            if forcar_regeneracao:
                st.error("⚡ **REGENERAÇÃO FORÇADA ATIVA** - Todos os insights foram gerados via LLM ignorando cache")
                st.info("🔄 Cache foi ignorado propositalmente para esta sessão")
            else:
                st.success("💾 **CACHE ATIVO** - Insights podem vir do cache quando disponível")
            
            # Estatísticas de cache
            cache_stats = cache_service.obter_estatisticas_cache_usuario(user_id)
            
            col1, col2, col3, col4 = st.columns(4)
            
            cache_hits = len([i for i in insights if i.get('cache_info', '').endswith('cache')])
            llm_calls = len([i for i in insights if i.get('cache_info', '').endswith('llm')])
            total_insights = len(insights)
            
            with col1:
                st.metric("💾 Cache Hits", cache_hits, help="Insights que vieram do cache")
            with col2:
                st.metric("🔄 LLM Calls", llm_calls, help="Insights gerados via LLM")
            with col3:
                efficiency = (cache_hits / total_insights * 100) if total_insights > 0 else 0
                st.metric("⚡ Eficiência Sessão", f"{efficiency:.1f}%", help="% de insights que vieram do cache nesta sessão")
            with col4:
                st.metric("💾 Eficiência Geral", f"{cache_stats.get('eficiencia_cache', 0):.1f}%", help="Eficiência geral do cache do usuário")
            
            # Debug de hashes (apenas em modo depurador)
            with st.expander("🔍 Debug Cache - Hashes Gerados", expanded=False):
                st.write("**Contextos usados para geração de cache:**")
                
                # Mostrar hashes dos 4 insights
                debug_contexts = [
                    ("total_gastos_cartao", contexto_total_cartao),
                    ("maior_gasto_cartao", contexto_maior_gasto_cartao), 
                    ("padrao_gastos_cartao", contexto_padrao_cartao),
                    ("controle_cartao", contexto_controle_cartao)
                ]
                
                for insight_type, contexto in debug_contexts:
                    try:
                        data_hash = cache_service.gerar_data_hash(contexto)
                        prompt_hash = cache_service.gerar_prompt_hash(
                            f"prompt_{insight_type}", params or {}
                        )
                        
                        st.write(f"**{insight_type}:**")
                        st.write(f"- Data Hash: `{data_hash[:16]}...`")
                        st.write(f"- Prompt Hash: `{prompt_hash[:16]}...`")
                        st.write(f"- Transações: {len(contexto.get('ultimas_transacoes_cartao', []))}")
                        st.write("---")
                    except Exception as e:
                        st.error(f"Erro ao gerar hash para {insight_type}: {e}")
            
            with st.expander("📈 Estatísticas Detalhadas do Cache"):
                st.json(cache_stats)
            
            st.info(f"📋 **Dados analisados**: {len(ultimas_fatura)} transações de cartão/fatura")
            
            # Mostrar detalhes das transações carregadas (debug)
            if len(ultimas_fatura) > 0:
                with st.expander("🔍 Transações Carregadas (Debug)", expanded=False):
                    st.write(f"**Total de transações encontradas**: {len(ultimas_fatura)}")
                    
                    # Verificar se é DataFrame antes de usar métodos específicos
                    if isinstance(ultimas_fatura, pd.DataFrame):
                        st.write("**Primeiras 5 transações:**")
                        for i, row in ultimas_fatura.head(5).iterrows():
                            st.write(f"- {row.get('data', 'N/A')}: {row.get('descricao', 'N/A')} - R$ {row.get('valor', 0):,.2f} ({row.get('categoria', 'N/A')})")
                        
                        st.write("**Estrutura dos dados:**")
                        st.write(f"Colunas: {list(ultimas_fatura.columns)}")
                        st.write(f"Tipos: {ultimas_fatura.dtypes.to_dict()}")
                    else:
                        st.write("**Tipo de dados:**")
                        st.write(f"Tipo: {type(ultimas_fatura)}")
                        st.write(f"Formato: {ultimas_fatura}")
            else:
                st.warning("⚠️ Nenhuma transação de cartão/fatura foi encontrada!")
            
            for idx, insight in enumerate(insights):
                st.write(f'Insight #{idx+1} - {insight["titulo"]}:')
                st.write(f'- Fonte: {insight.get("cache_info", "N/A")}')
                st.write(f'- Comentário: {insight["comentario"]}')
                st.divider()
        
        # Exibir em grid (2 por linha)
        for i in range(0, len(insights), 2):
            cols = st.columns(2)
            for j, insight in enumerate(insights[i:i+2]):
                with cols[j]:
                    exibir_insight_card(
                        avatar_path=insight['avatar'],
                        nome_ia=nome_ia,
                        saudacao=insight['saudacao'],
                        tipo=insight['tipo'],
                        titulo=insight['titulo'],
                        valor=insight['valor'],
                        comentario=insight['comentario'],
                        assinatura=insight['assinatura']
                    )
                    
                    # Mostrar info de cache se modo depurador ativo
                    if st.session_state.get('modo_depurador') and insight.get('cache_info'):
                        st.caption(f"🔍 {insight['cache_info']}")
    
    except Exception as e:
        st.error(f"Erro ao exibir insights do cartão: {str(e)}")
        # Fallback para versão sem cache em caso de erro
        if st.session_state.get('modo_depurador'):
            st.exception(e)

# Dashboard principal
st.subheader("📊 Resumo do Cartão")

# Verificar se df_final tem dados e colunas necessárias
if df_final.empty or 'Valor' not in df_final.columns:
    st.warning("🔍 Dados do cartão não disponíveis ou estrutura incorreta.")
    st.stop()

# Métricas principais usando dados filtrados
total_transacoes = len(df_final)
total_gastos = abs(df_final['Valor'].sum())  # Valores de cartão são geralmente negativos
gasto_medio = total_gastos / total_transacoes if total_transacoes > 0 else 0
maior_gasto = abs(df_final['Valor'].min()) if not df_final.empty and isinstance(df_final, pd.DataFrame) else 0

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

# Layout principal em colunas (dashboard à esquerda, seletor à direita)
col_main, col_persona = st.columns([2.5, 1])

with col_persona:
    render_personality_selector()

with col_main:
    exibir_grid_insights_cartao(usuario)

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
        if not df_final.empty and isinstance(df_final, pd.DataFrame):
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
    if not df_final.empty and isinstance(df_final, pd.DataFrame):
        top_gastos = df_final.nsmallest(10, "Valor").copy()
        
        # Incluir coluna Nota se existe e tem dados
        colunas_exibir = ["Data", "Descrição", "Valor", "Categoria"]
        if "Nota" in top_gastos.columns:
            # Verificação segura evitando operações boolean em Series
            try:
                # Converter para lista para evitar problemas de Series boolean
                nota_values = top_gastos["Nota"].tolist()
                # Verificar se há valores não nulos e não vazios
                has_data = any(val is not None and val != "" and pd.notna(val) for val in nota_values)
                
                if has_data:
                    colunas_exibir.insert(-1, "Nota")  # Inserir antes da Categoria
            except Exception:
                # Se houver qualquer problema, simplesmente não incluir a coluna Nota
                pass
        
        top_gastos = top_gastos[colunas_exibir]
        # Corrigir problema com .abs() usando abordagem robusta
        try:
            # Converter para DataFrame se necessário e aplicar abs
            if isinstance(top_gastos, pd.DataFrame):
                top_gastos = top_gastos.copy()
                top_gastos["Valor"] = top_gastos["Valor"].astype(float).abs()
            else:
                # Fallback para casos extremos
                top_gastos = pd.DataFrame(top_gastos)
                top_gastos["Valor"] = top_gastos["Valor"].astype(float).abs()
        except Exception:
            # Último recurso: conversão manual
            try:
                valores = []
                for val in top_gastos["Valor"]:
                    try:
                        valores.append(abs(float(val)))
                    except (ValueError, TypeError):
                        valores.append(0.0)
                top_gastos["Valor"] = valores
            except Exception:
                pass
        top_gastos_formatado = formatar_df_monetario(top_gastos)
        
        st.dataframe(top_gastos_formatado, use_container_width=True)

    # Análise detalhada por categorias com abas
    with st.expander("📊 Transações por Categoria", expanded=False):
        if not df_final.empty and isinstance(df_final, pd.DataFrame) and 'Categoria' in df_final.columns:
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
                    
                    if not df_categoria.empty and isinstance(df_categoria, pd.DataFrame):
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
