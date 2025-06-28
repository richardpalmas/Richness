import pandas as pd
import plotly.express as px
import streamlit as st
import time
import os
import json
import hashlib
from datetime import datetime
import base64
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from componentes.profile_pic_component import boas_vindas_com_foto
from utils.exception_handler import ExceptionHandler
from utils.formatacao import formatar_valor_monetario, formatar_df_monetario
from utils.filtros import filtro_data, filtro_categorias, aplicar_filtros

# BACKEND V2 OBRIGATÓRIO - Importações exclusivas
from utils.database_manager_v2 import DatabaseManager
from utils.repositories_v2 import TransacaoRepository, UsuarioRepository, CategoriaRepository
from services.transacao_service_v2 import TransacaoService
from utils.database_monitoring import DatabaseMonitor

# Importações de segurança
from security.auth.authentication import SecureAuthentication

# Adicionar importação do seletor de personalidade
from componentes.personality_selector import render_personality_selector

from componentes.insight_card import exibir_insight_card

from services.llm_service import LLMService
from services.insights_service_v2 import InsightsServiceV2

# Configurações da página
st.set_page_config(
    page_title="Richness - Dashboard Financeiro", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Verificar autenticação
def verificar_autenticacao():
    if 'authenticated' not in st.session_state or not st.session_state['authenticated']:
        mostrar_formulario_login()
        st.stop()

def img_to_base64(path):
    with open(path, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def mostrar_formulario_login():
    """Exibe formulário de login profissional do Richness com destaque para o Assistente IA"""
    # Converter imagens para base64
    img_ana = img_to_base64('imgs/perfil_amigavel_fem.png')
    img_fernando = img_to_base64('imgs/perfil_tecnico_masc.png')
    img_jorge = img_to_base64('imgs/perfil_durao_mas.png')

    # Banner completo em um bloco HTML/CSS
    st.markdown(f'''
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 18px; padding: 32px 24px 24px 24px; margin-bottom: 32px; box-shadow: 0 4px 24px rgba(0,0,0,0.08); text-align: center; max-width: 900px; margin-left: auto; margin-right: auto;">
        <div style="font-size: 2.2em; font-weight: bold; color: #fff; margin-bottom: 8px;">
            Richness: A Sua Solução Financeira Prática e Revolucionária
        </div>
        <div style="font-size: 1.2em; color: #e0e0e0; margin-bottom: 24px;">
            Escolha seu assistente financeiro ou crie o seu!
        </div>
        <div style="display: flex; justify-content: center; gap: 56px; flex-wrap: wrap; margin-bottom: 18px;">
            <div>
                <img src="data:image/png;base64,{img_ana}" width="80" style="border-radius: 16px; border: 3px solid #fff; box-shadow: 0 2px 8px rgba(102,126,234,0.15); margin-bottom: 8px;" />
                <div style="color: #fff; font-weight: 600; font-size: 1.1em;">Ana</div>
                <div style="color: #e0e0e0; font-size: 0.98em;">Clara e Amigável</div>
            </div>
            <div>
                <img src="data:image/png;base64,{img_fernando}" width="80" style="border-radius: 16px; border: 3px solid #fff; box-shadow: 0 2px 8px rgba(102,126,234,0.15); margin-bottom: 8px;" />
                <div style="color: #fff; font-weight: 600; font-size: 1.1em;">Fernando</div>
                <div style="color: #e0e0e0; font-size: 0.98em;">Técnico e Analítico</div>
            </div>
            <div>
                <img src="data:image/png;base64,{img_jorge}" width="80" style="border-radius: 16px; border: 3px solid #fff; box-shadow: 0 2px 8px rgba(102,126,234,0.15); margin-bottom: 8px;" />
                <div style="color: #fff; font-weight: 600; font-size: 1.1em;">Jorge</div>
                <div style="color: #e0e0e0; font-size: 0.98em;">Durão e Direto</div>
            </div>
        </div>
        <div style="font-size: 1.1em; color: #fff; margin-top: 10px;">
            Descubra como a IA pode transformar sua vida financeira. Faça login ou crie sua conta!
        </div>
    </div>
    ''', unsafe_allow_html=True)

    # Expander Saiba Mais
    with st.expander("ℹ️ Saiba mais sobre o Assistente IA"): 
        st.markdown("""
        O Assistente IA do Richness é uma ferramenta inovadora que analisa seus dados financeiros, responde dúvidas, sugere melhorias e se adapta ao seu perfil. 
        <ul>
        <li>Perfis personalizáveis: escolha entre Ana (amigável), Fernando (analítico), Jorge (direto) ou crie o seu próprio perfil de IA.</li>
        <li>Respostas inteligentes e contextualizadas para sua realidade financeira.</li>
        <li>Experiência única, divertida e eficiente para transformar sua relação com o dinheiro.</li>
        </ul>
        """, unsafe_allow_html=True)

    # Layout do formulário de login centralizado, mas abaixo do banner
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("---")
        st.markdown("**Tome controle das suas finanças de forma inteligente e segura**")
        with st.form("login_form", clear_on_submit=False):
            st.markdown("#### Acesse sua conta")
            usuario = st.text_input(
                "👤 Usuário",
                placeholder="Digite seu nome de usuário",
                help="Seu nome de usuário cadastrado no Richness"
            )
            senha = st.text_input(
                "🔒 Senha",
                type="password",
                placeholder="Digite sua senha segura",
                help="Sua senha de acesso ao Richness"
            )
            col_login, col_register = st.columns(2)
            with col_login:
                login_button = st.form_submit_button(
                    "🚀 Entrar",
                    use_container_width=True,
                    type="primary"
                )
            with col_register:
                if st.form_submit_button(
                    "📝 Criar Conta",
                    use_container_width=True
                ):
                    st.switch_page("pages/Cadastro.py")
            if login_button:
                if not usuario or not senha:
                    st.error("❌ Por favor, preencha todos os campos!")
                else:
                    resultado = autenticar_usuario_v2(usuario, senha)
                    if resultado['success']:
                        st.session_state['authenticated'] = True
                        st.session_state['autenticado'] = True
                        st.session_state['usuario'] = usuario
                        st.success("✅ Bem-vindo(a) ao Richness!")
                        st.info("🔄 Carregando seu dashboard financeiro...")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ {resultado.get('message', 'Erro na autenticação')}")
        st.markdown("---")
        with st.expander("Por que escolher o Richness?"):
            st.write("""
            **Gestão Financeira Inteligente com IA**
            - 🤖 Assistente financeiro inteligente e personalizado
            - 🧠 Categorização automática de transações com IA
            - 💡 Insights e recomendações personalizadas por IA
            - 📊 Análises detalhadas de receitas e despesas
            - 📈 Gráficos e relatórios visuais
            - 🏷️ Organização automática das suas finanças
            - ⏳ Acompanhamento temporal do seu progresso
            
            **Segurança e Privacidade**
            - 🔒 Seus dados são protegidos e organizados por usuário
            - 🛡️ Criptografia avançada para suas informações
            - 🚀 Performance otimizada para melhor experiência
            - 💻 Interface intuitiva e profissional
            
            **Recursos Avançados**
            - 🔄 Separação clara entre receitas e despesas
            - 🎯 Cálculo de ticket médio e métricas importantes
            - 📋 Transações organizadas por categoria
            """)
        st.markdown("---")
        st.markdown(
            "<div style='text-align: center; color: #666; font-size: 0.9em;'>"
            "© 2025 Richness - Plataforma de Gestão Financeira Pessoal<br>"
            "Desenvolvido para ajudar você a alcançar seus objetivos financeiros"
            "</div>", 
            unsafe_allow_html=True
        )

def autenticar_usuario_v2(usuario, senha):
    """Autentica usuário no sistema Richness com segurança avançada"""
    try:
        # Inicializar sistema de autenticação
        db_manager = DatabaseManager()
        user_repo = UsuarioRepository(db_manager)
        
        # Verificar credenciais usando método seguro
        user_data = user_repo.verificar_senha(usuario, senha)
        
        if user_data:
            return {
                'success': True,
                'message': 'Autenticação realizada com sucesso',
                'user_data': user_data
            }
        else:
            return {
                'success': False,
                'message': 'Usuário não encontrado ou senha incorreta'
            }
            
    except Exception as e:
        return {
            'success': False,
            'message': f'Erro na autenticação: {str(e)}'
        }

# Verificar se o sistema está disponível
@st.cache_resource
def init_backend_sistema():
    """Inicializa o sistema Richness"""
    try:
        db_manager = DatabaseManager()
        usuario_repo = UsuarioRepository(db_manager)
        transacao_repo = TransacaoRepository(db_manager)
        categoria_repo = CategoriaRepository(db_manager)
        transacao_service = TransacaoService()
        
        # Inicializar monitor opcionalmente (sem falhar se não existir)
        monitor = None
        try:
            monitor = DatabaseMonitor(db_manager)
        except Exception:
            # Monitor é opcional, continuar sem ele
            pass
        
        try:
            # Verificar se o banco V2 está acessível
            usuarios = usuario_repo.buscar_todos()
            if isinstance(usuarios, list):  # Se retornou uma lista, está funcionando
                pass  # Tudo OK
        except Exception as e:
            st.error("❌ **Sistema não está funcionando corretamente!**")
            st.error("🔧 Verifique a conexão com o banco de dados")
            st.error(f"🔍 **Erro técnico**: {str(e)}")
            st.stop()
        
        return {
            'db_manager': db_manager,
            'usuario_repo': usuario_repo,
            'transacao_repo': transacao_repo,
            'categoria_repo': categoria_repo,
            'transacao_service': transacao_service,
            'monitor': monitor
        }
    except Exception as e:
        st.error(f"❌ **Falha crítica no sistema!**")
        st.error(f"🔧 **Erro**: {str(e)}")
        st.error("📋 **Ação necessária**: Verifique se o sistema foi inicializado corretamente")
        st.stop()

# Obter instância do backend
backend_sistema = init_backend_sistema()

# Verificar autenticação
verificar_autenticacao()

# Limpar caches se necessário
if st.sidebar.button("🔄 Limpar Cache", help="Limpa cache do sistema"):
    st.cache_data.clear()
    st.cache_resource.clear()
    st.success("✅ Cache limpo!")
    st.rerun()

# Obter usuário da sessão
usuario = st.session_state.get('usuario', 'default')

# Função auxiliar para obter user_id
def obter_user_id(usuario):
    """Obtém o ID do usuário a partir do username"""
    try:
        user_data = backend_sistema['usuario_repo'].obter_usuario_por_username(usuario)
        user_id = user_data['id'] if user_data else None
        return user_id
    except Exception as e:
        return None

# Boas-vindas com foto de perfil
if usuario:
    boas_vindas_com_foto(usuario)

# ===================== NOTIFICAÇÕES DE COMPROMISSOS =====================
def mostrar_notificacoes(usuario, dias_alerta=7):
    """Exibe notificações de compromissos próximos baseado na tabela de compromissos"""
    try:
        # Importar aqui para evitar imports circulares
        from utils.repositories_v2 import CompromissoRepository
        
        # Obter user_id
        user_data = backend_sistema['usuario_repo'].obter_usuario_por_username(usuario)
        if not user_data:
            return
            
        user_id = user_data['id']
        
        # Buscar compromissos próximos
        compromisso_repo = CompromissoRepository(backend_sistema['db_manager'])
        df_compromissos = compromisso_repo.obter_compromissos_proximos(user_id, dias_alerta)
        
        if not df_compromissos.empty:
            # Calcular total de valor dos compromissos próximos
            valor_total = df_compromissos['valor'].sum()
            
            # Notificação principal
            st.warning(
                f"🔔 **Notificações**: Você possui {len(df_compromissos)} compromisso(s) com vencimento nos próximos {dias_alerta} dias - Total: {formatar_valor_monetario(valor_total)}", 
                icon="🔔"
            )
            
            # Container expansível com detalhes
            with st.expander("📋 Ver detalhes dos compromissos", expanded=False):
                for idx, row in df_compromissos.iterrows():
                    # Garantir acesso escalar
                    data_vencimento = df_compromissos.at[idx, 'data_vencimento']
                    if not pd.isnull(data_vencimento) and not isinstance(data_vencimento, pd.Timestamp):
                        data_vencimento = pd.to_datetime(data_vencimento)
                    data_fmt = data_vencimento.strftime('%d/%m/%Y') if not pd.isnull(data_vencimento) else '-'
                    valor_fmt = formatar_valor_monetario(df_compromissos.at[idx, 'valor'])
                    desc = df_compromissos.at[idx, 'descricao']
                    categoria = df_compromissos.at[idx, 'categoria']
                    hoje = datetime.now().date()
                    dias_restantes = (data_vencimento.date() - hoje).days if not pd.isnull(data_vencimento) and hasattr(data_vencimento, 'date') else '-'
                    if dias_restantes != '-' and dias_restantes < 0:
                        urgencia = "🔴 VENCIDO"
                        cor = "red"
                    elif dias_restantes == 0:
                        urgencia = "🟡 VENCE HOJE"
                        cor = "orange"
                    elif dias_restantes != '-' and dias_restantes <= 3:
                        urgencia = f"🟠 {dias_restantes} dias"
                        cor = "orange"
                    elif dias_restantes != '-':
                        urgencia = f"🟢 {dias_restantes} dias"
                        cor = "green"
                    else:
                        urgencia = "-"
                        cor = "gray"
                    col1, col2, col3 = st.columns([3, 2, 1])
                    with col1:
                        st.markdown(f"**{desc}**")
                        st.caption(f"🏷️ {categoria}")
                    with col2:
                        st.markdown(f"📅 **{data_fmt}**")
                        st.markdown(f"💰 **{valor_fmt}**")
                    with col3:
                        st.markdown(f"<span style='color: {cor};'><b>{urgencia}</b></span>", unsafe_allow_html=True)
                    observacoes = df_compromissos.at[idx, 'observacoes'] if 'observacoes' in df_compromissos.columns and pd.notna(df_compromissos.at[idx, 'observacoes']) else None
                    if observacoes:
                        st.caption(f"📝 {observacoes}")
                    st.divider()
            
            # Link para gerenciar compromissos
            st.info("💡 Para gerenciar seus compromissos, acesse a página Metas e Compromissos")
            
    except Exception as e:
        # Silenciosamente falhar para não quebrar o dashboard
        st.error(f"⚠️ Erro ao carregar notificações: {str(e)}")
        pass

# Título principal
st.title("🚀 Dashboard Financeiro")

# Carregar dados principais do usuário
@st.cache_data(ttl=600)
def carregar_dados_usuario(usuario, data_inicio=None, data_fim=None, force_refresh=False):
    """Carrega dados financeiros do usuário"""
    try:
        transacao_service = backend_sistema['transacao_service']
        
        # Carregar transações
        df_transacoes = transacao_service.listar_transacoes_usuario(usuario)
        
        if df_transacoes.empty:
            return {}, pd.DataFrame()
        
        # Aplicar filtro de período se especificado
        if data_inicio and data_fim and 'data' in df_transacoes.columns:
            df_transacoes['data_dt'] = pd.to_datetime(df_transacoes['data'])
            df_transacoes = df_transacoes[
                (df_transacoes['data_dt'] >= pd.to_datetime(data_inicio)) & 
                (df_transacoes['data_dt'] <= pd.to_datetime(data_fim))
            ].drop('data_dt', axis=1)
        
        # Calcular saldos por origem
        saldos_info = transacao_service.calcular_saldos_por_origem(usuario)
        
        return saldos_info, df_transacoes
        
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {str(e)}")
        return {}, pd.DataFrame()

# Sidebar - Configurações e Filtros (configurar antes de carregar dados)
st.sidebar.header("⚙️ Configurações")
st.sidebar.markdown("**Sistema Richness Ativo**")

# Botão para ativar/desativar o modo depurador
if 'modo_depurador' not in st.session_state:
    st.session_state['modo_depurador'] = False
if st.sidebar.button(f"{'🛑 Desativar' if st.session_state['modo_depurador'] else '🐞 Ativar'} Modo Depurador", help="Exibe logs detalhados dos insights na tela"):
    st.session_state['modo_depurador'] = not st.session_state['modo_depurador']
    st.rerun()
st.sidebar.write(f"Modo Depurador: {'Ativo' if st.session_state['modo_depurador'] else 'Inativo'}")

# Carregar dados iniciais para definir range de datas
saldos_info_inicial, df_inicial = carregar_dados_usuario(usuario)

# Filtros na sidebar
st.sidebar.markdown("### 📅 Selecionar Período")

# Filtro de período
data_inicio, data_fim = None, None
if not df_inicial.empty and 'data' in df_inicial.columns:
    # Converter coluna de data se necessário
    df_for_filter = df_inicial.copy()
    df_for_filter['Data'] = pd.to_datetime(df_for_filter['data'])
    data_inicio, data_fim = filtro_data(df_for_filter, key_prefix="home")
    
    st.sidebar.success(f"📅 Período: {data_inicio} a {data_fim}")

# Configurações de notificação
st.sidebar.markdown("### 🔔 Configurações de Notificação")
dias_alerta = st.sidebar.slider(
    "Dias de antecedência para alertas",
    min_value=1,
    max_value=30,
    value=7,
    help="Quantos dias antes do vencimento você quer ser alertado"
)

# Checkbox para ativar/desativar notificações
notificacoes_ativas = st.sidebar.checkbox(
    "📢 Ativar notificações de compromissos",
    value=True,
    help="Mostrar ou ocultar alertas de compromissos próximos"
)

# Carregar dados com filtro aplicado
saldos_info, df = carregar_dados_usuario(usuario, data_inicio, data_fim)

# Chamar notificações se ativadas
if notificacoes_ativas:
    mostrar_notificacoes(usuario, dias_alerta)

st.markdown("---")

# Informações do usuário na sidebar
if st.sidebar.expander("👤 Informações do Usuário"):
    st.sidebar.write(f"**Usuário**: {usuario}")
    st.sidebar.write(f"**Transações**: {len(df) if not df.empty else 0}")
    st.sidebar.write(f"**Sistema**: Richness Platform")

# Ferramentas de Cache (apenas para modo depurador)
if st.session_state.get('modo_depurador'):
    st.sidebar.markdown("### 🗄️ Ferramentas de Cache")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("🗑️ Limpar Cache", help="Remove cache expirado do usuário", key="limpar_cache_btn"):
            try:
                from services.insights_cache_service import InsightsCacheService
                cache_service = InsightsCacheService()
                
                # Limpar apenas cache expirado
                removidos = cache_service.limpar_cache_expirado_automatico()
                
                # Limpar cache do Streamlit
                st.cache_data.clear()
                
                st.sidebar.success(f"✅ {removidos} entradas expiradas removidas")
                st.sidebar.info("🔄 Cache do Streamlit limpo")
                
                # Rerun para atualizar
                time.sleep(0.5)
                st.rerun()
                
            except Exception as e:
                st.sidebar.error(f"❌ Erro: {e}")
    
    with col2:
        if st.button("🔄 Reset Cache", help="Remove TODO cache do usuário e força regeneração", key="reset_cache_btn"):
            try:
                from services.insights_cache_service import InsightsCacheService
                cache_service = InsightsCacheService()
                user_id = obter_user_id(st.session_state.get('usuario'))
                if user_id:
                    # Invalidar TODO cache do usuário (válido e expirado)
                    removidos = cache_service.invalidar_cache_por_mudanca_dados(user_id)
                    
                    # Limpar cache do Streamlit
                    st.cache_data.clear()
                    st.cache_resource.clear()
                    
                    # Marcar flag para forçar regeneração
                    st.session_state['forcar_regeneracao_insights'] = True
                    
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
    if st.sidebar.button("⚡ Forçar Regeneração", help="Força nova chamada ao LLM sem limpar cache", key="forcar_regeneracao_btn"):
        try:
            user_id = obter_user_id(st.session_state.get('usuario'))
            
            if user_id:
                # NÃO limpar cache - apenas marcar flag para ignorá-lo
                st.session_state['forcar_regeneracao_insights'] = True
                
                # Limpar cache do Streamlit para forçar recarregamento da página
                st.cache_data.clear()
                
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

# Verificar se há dados
if df.empty:
    st.warning("📭 Nenhuma transação encontrada!")
    st.info("💡 **Possíveis motivos:**")
    st.markdown("""
    1. 📁 Nenhum arquivo foi importado
    2. 🔍 O período selecionado não contém transações
    3. 📋 Os dados não foram migrados para o Backend V2
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

# Dashboard principal
st.subheader("📊 Resumo Financeiro")

# Estatísticas do carregamento
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("📈 Total Transações", len(df))

with col2:
    origem_count = len(df['origem'].unique()) if 'origem' in df.columns else 0
    st.metric("🏦 Origens", origem_count)

with col3:
    if not df.empty and 'data' in df.columns:
        try:
            # Converter strings para datetime para cálculo do período
            df_temp_periodo = df.copy()
            df_temp_periodo['data'] = pd.to_datetime(df_temp_periodo['data'])
            periodo_dias = (df_temp_periodo['data'].max() - df_temp_periodo['data'].min()).days
        except:
            periodo_dias = 0
    else:
        periodo_dias = 0
    st.metric("📅 Período", f"{periodo_dias} dias")

# Calcular resumo financeiro usando lógica simples (igual à aba Despesas)
if not df.empty and 'valor' in df.columns:
    # Calcular receitas (valores positivos)
    receitas_simples = df.loc[df['valor'] > 0, 'valor'].sum()
    
    # Calcular despesas (valores negativos) - mesma lógica da aba Despesas
    despesas_simples = abs(df.loc[df['valor'] < 0, 'valor'].sum())
    
    # Calcular saldo
    saldo_simples = receitas_simples - despesas_simples
    
    resumo = {
        "receitas": receitas_simples,
        "despesas": despesas_simples,
        "saldo": saldo_simples
    }
else:
    resumo = {"receitas": 0, "despesas": 0, "saldo": 0}

# Métricas principais
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "💰 Receitas", 
        formatar_valor_monetario(resumo["receitas"])
    )

with col2:
    st.metric(
        "💸 Despesas", 
        formatar_valor_monetario(abs(resumo["despesas"]))
    )

with col3:
    saldo_liquido = resumo["saldo"]
    st.metric(
        "💳 Saldo Líquido", 
        formatar_valor_monetario(saldo_liquido),
        delta=None
    )

with col4:
    despesas_mask = df['valor'] < 0
    ticket_medio = abs(resumo["despesas"]) / len(df.loc[despesas_mask]) if len(df.loc[despesas_mask]) > 0 else 0
    st.metric(
        "🎯 Ticket Médio",
        formatar_valor_monetario(ticket_medio)
    )

st.markdown("---")

def exibir_grid_insights_personalizados(usuario):
    """Exibe um grid de insights personalizados conforme a personalidade selecionada com cache inteligente"""
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
        
        # Saldos e dados principais
        saldo_info = insights_service.obter_valor_restante_mensal(user_id)
        sugestoes = insights_service.sugerir_otimizacoes(user_id)
        alertas = insights_service.detectar_alertas_financeiros(user_id)
        
        # Buscar últimas 15 transações de extrato e fatura separadamente
        from services.transacao_service_v2 import TransacaoService
        transacao_service = TransacaoService()
        df_todas = transacao_service.listar_transacoes_usuario(usuario, limite=5000)
        if 'origem' in df_todas.columns:
            df_todas['origem'] = df_todas['origem'].astype(str)
        if 'data' in df_todas.columns:
            df_todas['data'] = pd.to_datetime(df_todas['data'], errors='coerce')
        
        # Extrato
        df_extrato = df_todas[~df_todas['origem'].str.contains('fatura|cartao|credit', case=False, na=False)]
        if not df_extrato.empty and 'data' in df_extrato.columns and pd.api.types.is_datetime64_any_dtype(df_extrato['data']):
            mask = pd.Series(df_extrato['data']).notnull()
            df_extrato_filtrado = df_extrato[mask]
            if isinstance(df_extrato_filtrado, pd.DataFrame):
                ultimas_extrato = df_extrato_filtrado.sort_values(by='data', ascending=False).head(15)
            else:
                ultimas_extrato = df_extrato_filtrado
        else:
            ultimas_extrato = df_extrato.head(15)
        
        # Fatura
        df_fatura = df_todas[df_todas['origem'].str.contains('fatura|cartao|credit', case=False, na=False)]
        if not df_fatura.empty and 'data' in df_fatura.columns and pd.api.types.is_datetime64_any_dtype(df_fatura['data']):
            mask = pd.Series(df_fatura['data']).notnull()
            df_fatura_filtrado = df_fatura[mask]
            if isinstance(df_fatura_filtrado, pd.DataFrame):
                ultimas_fatura = df_fatura_filtrado.sort_values(by='data', ascending=False).head(15)
            else:
                ultimas_fatura = df_fatura_filtrado
        else:
            ultimas_fatura = df_fatura.head(15)
        
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
        forcar_regeneracao = st.session_state.get('forcar_regeneracao_insights', False)
        
        # Limpar flag após usar
        if forcar_regeneracao:
            st.session_state['forcar_regeneracao_insights'] = False
        
        # Gerar insights usando cache inteligente
        insights = []
        
        # Insight 1: Saldo do mês
        contexto_saldo = {
            'personalidade': personalidade_sel,
            'saldo': saldo_info,
            'ultimas_transacoes': ultimas_extrato.to_dict('records') if isinstance(ultimas_extrato, pd.DataFrame) and not ultimas_extrato.empty else [],
            'usuario': user_data
        }
        prompt_saldo = "Analise o saldo do mês de forma personalizada, considerando o perfil da IA. Cite o valor de forma objetiva, em até 250 caracteres. NÃO inclua saudações como 'Olá' ou cumprimentos."
        
        insight_saldo = cache_service.gerar_insight_com_cache(
            user_id=user_id,
            insight_type='saldo_mensal',
            personalidade=personalidade_sel,
            data_context=contexto_saldo,
            prompt=prompt_saldo,
            personalidade_params=params or {},
            forcar_regeneracao=forcar_regeneracao
        )
        
        insights.append({
            'tipo': 'neutro' if saldo_info['valor_restante'] >= 0 else 'negativo',
            'titulo': insight_saldo['titulo'],
            'valor': insight_saldo['valor'],
            'comentario': insight_saldo['comentario'][:250] + ('...' if len(insight_saldo['comentario']) > 250 else ''),
            'assinatura': nome_ia,
            'avatar': avatar_path,
            'saudacao': None,
            'cache_info': f"Cache: {insight_saldo['source']}" if st.session_state.get('modo_depurador') else None
        })
        
        # Insight 2: Maior gasto
        maior_gasto = None
        if isinstance(ultimas_extrato, pd.DataFrame) and not ultimas_extrato.empty and 'valor' in ultimas_extrato.columns:
            idx_min = ultimas_extrato['valor'].idxmin()
            maior_gasto_row = ultimas_extrato.loc[idx_min]
            maior_gasto = maior_gasto_row
        elif isinstance(ultimas_fatura, pd.DataFrame) and not ultimas_fatura.empty and 'valor' in ultimas_fatura.columns:
            idx_min = ultimas_fatura['valor'].idxmin()
            maior_gasto_row = ultimas_fatura.loc[idx_min]
            maior_gasto = maior_gasto_row
        
        contexto_maior_gasto = {
            'personalidade': personalidade_sel,
            'maior_gasto': maior_gasto.to_dict() if maior_gasto is not None and hasattr(maior_gasto, 'to_dict') else {},
            'ultimas_transacoes': ultimas_extrato.to_dict('records') if isinstance(ultimas_extrato, pd.DataFrame) and not ultimas_extrato.empty else [],
            'usuario': user_data
        }
        prompt_maior_gasto = "Analise de forma personalizada qual foi o maior gasto recente, citando categoria, valor e contexto de forma objetiva, em até 250 caracteres. NÃO inclua saudações como 'Olá' ou cumprimentos."
        
        insight_maior_gasto = cache_service.gerar_insight_com_cache(
            user_id=user_id,
            insight_type='maior_gasto',
            personalidade=personalidade_sel,
            data_context=contexto_maior_gasto,
            prompt=prompt_maior_gasto,
            personalidade_params=params or {},
            forcar_regeneracao=forcar_regeneracao
        )
        
        insights.append({
            'tipo': 'negativo',
            'titulo': insight_maior_gasto['titulo'],
            'valor': insight_maior_gasto['valor'],
            'comentario': insight_maior_gasto['comentario'][:250] + ('...' if len(insight_maior_gasto['comentario']) > 250 else ''),
            'assinatura': nome_ia,
            'avatar': avatar_path,
            'saudacao': None,
            'cache_info': f"Cache: {insight_maior_gasto['source']}" if st.session_state.get('modo_depurador') else None
        })
        
        # Insight 3: Economia potencial
        economia_potencial = sugestoes[0] if sugestoes else None
        contexto_economia = {
            'personalidade': personalidade_sel,
            'sugestao': economia_potencial,
            'usuario': user_data
        }
        prompt_economia = "Analise e sugira de forma personalizada uma economia potencial para o usuário, citando categoria e valor de forma objetiva, em até 250 caracteres. NÃO inclua saudações como 'Olá' ou cumprimentos."
        
        insight_economia = cache_service.gerar_insight_com_cache(
            user_id=user_id,
            insight_type='economia_potencial',
            personalidade=personalidade_sel,
            data_context=contexto_economia,
            prompt=prompt_economia,
            personalidade_params=params or {},
            forcar_regeneracao=forcar_regeneracao
        )
        
        insights.append({
            'tipo': 'positivo',
            'titulo': insight_economia['titulo'],
            'valor': insight_economia['valor'],
            'comentario': insight_economia['comentario'][:250] + ('...' if len(insight_economia['comentario']) > 250 else ''),
            'assinatura': nome_ia,
            'avatar': avatar_path,
            'saudacao': None,
            'cache_info': f"Cache: {insight_economia['source']}" if st.session_state.get('modo_depurador') else None
        })
        
        # Insight 4: Alerta de gastos
        alerta = alertas[0] if alertas else None
        contexto_alerta = {
            'personalidade': personalidade_sel,
            'alerta': alerta,
            'ultimas_transacoes': ultimas_fatura.to_dict('records') if isinstance(ultimas_fatura, pd.DataFrame) and not ultimas_fatura.empty else [],
            'usuario': user_data
        }
        prompt_alerta = "Analise e alerte de forma personalizada sobre gastos, citando o motivo e recomendação de forma objetiva, em até 250 caracteres. NÃO inclua saudações como 'Olá' ou cumprimentos."
        
        insight_alerta = cache_service.gerar_insight_com_cache(
            user_id=user_id,
            insight_type='alerta_gastos',
            personalidade=personalidade_sel,
            data_context=contexto_alerta,
            prompt=prompt_alerta,
            personalidade_params=params or {},
            forcar_regeneracao=forcar_regeneracao
        )
        
        insights.append({
            'tipo': 'alerta',
            'titulo': insight_alerta['titulo'],
            'valor': '',
            'comentario': insight_alerta['comentario'][:250] + ('...' if len(insight_alerta['comentario']) > 250 else ''),
            'assinatura': nome_ia,
            'avatar': avatar_path,
            'saudacao': None,
            'cache_info': f"Cache: {insight_alerta['source']}" if st.session_state.get('modo_depurador') else None
        })
        
        # Modo Depurador: logs visuais e estatísticas de cache
        if st.session_state.get('modo_depurador'):
            st.subheader('🪲 Logs do Modo Depurador (Insights com Cache)')
            
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
                st.metric("📊 Cache Hits", cache_hits, help="Insights que vieram do cache")
            with col2:
                st.metric("🔄 LLM Calls", llm_calls, help="Insights gerados via LLM")
            with col3:
                efficiency = (cache_hits / total_insights * 100) if total_insights > 0 else 0
                st.metric("⚡ Eficiência Sessão", f"{efficiency:.1f}%", help="% de insights que vieram do cache nesta sessão")
            with col4:
                st.metric("💾 Eficiência Geral", f"{cache_stats.get('eficiencia_cache', 0):.1f}%", help="Eficiência geral do cache do usuário")
            
            with st.expander("📈 Estatísticas Detalhadas do Cache"):
                st.json(cache_stats)
            
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
        st.error(f"Erro ao exibir insights personalizados: {str(e)}")
        # Fallback para versão sem cache em caso de erro
        if st.session_state.get('modo_depurador'):
            st.exception(e)

# Layout principal em colunas (dashboard à esquerda, seletor à direita)
col_main, col_persona = st.columns([2.5, 1])

with col_persona:
    render_personality_selector()

with col_main:
    exibir_grid_insights_personalizados(usuario)

st.markdown("---")

# Gráficos e análises (usando apenas dados V2)
with st.expander("📊 Gráficos por Categoria", expanded=False):
    col1, col2 = st.columns(2)

    with col1:
        # Gráfico de gastos por categoria
        if not df.empty and 'categoria' in df.columns:
            df_despesas = df.loc[df['valor'] < 0].copy()
            if not df_despesas.empty:
                gastos_categoria = df_despesas.groupby('categoria')['valor'].sum().abs().sort_values(ascending=False)
                
                fig_cat = px.pie(
                    values=gastos_categoria.values,
                    names=gastos_categoria.index,
                    title="💸 Gastos por Categoria (V2)"
                )
                st.plotly_chart(fig_cat, use_container_width=True)

    with col2:
        # Gráfico de receitas por categoria
        if not df.empty and 'categoria' in df.columns:
            df_receitas = df.loc[df['valor'] > 0].copy()
            if not df_receitas.empty:
                receitas_categoria = df_receitas.groupby('categoria')['valor'].sum().sort_values(ascending=False)
                
                fig_receitas = px.pie(
                    values=receitas_categoria.values,
                    names=receitas_categoria.index,
                    title="💰 Receitas por Categoria (V2)"
                )
                st.plotly_chart(fig_receitas, use_container_width=True)

# Evolução temporal
with st.expander("📈 Análise Temporal", expanded=False):
    if not df.empty and 'data' in df.columns:
        try:
            df_temp = df.copy()
            df_temp['data'] = pd.to_datetime(df_temp['data'])
            df_temp['Mes'] = df_temp['data'].dt.to_period('M')
            
            # Separar receitas e despesas
            df_temp_receitas = df_temp.loc[df_temp['valor'] > 0].copy()
            df_temp_despesas = df_temp.loc[df_temp['valor'] < 0].copy()
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Evolução das receitas
                if not df_temp_receitas.empty:
                    evolucao_receitas = df_temp_receitas.groupby('Mes')['valor'].sum()
                    
                    fig_evolucao_receitas = px.line(
                        x=evolucao_receitas.index.astype(str),
                        y=evolucao_receitas.values,
                        title="📈 Evolução das Receitas (V2)",
                        labels={'x': 'Mês', 'y': 'Valor'}
                    )
                    fig_evolucao_receitas.update_traces(line_color='green')
                    st.plotly_chart(fig_evolucao_receitas, use_container_width=True)
            
            with col2:
                # Evolução das despesas
                if not df_temp_despesas.empty:
                    evolucao_despesas = df_temp_despesas.groupby('Mes')['valor'].sum().abs()
                    
                    fig_evolucao_despesas = px.line(
                        x=evolucao_despesas.index.astype(str),
                        y=evolucao_despesas.values,
                        title="📉 Evolução das Despesas (V2)",
                        labels={'x': 'Mês', 'y': 'Valor'}
                    )
                    fig_evolucao_despesas.update_traces(line_color='red')
                    st.plotly_chart(fig_evolucao_despesas, use_container_width=True)
                    
        except Exception as e:
            st.warning(f"⚠️ Erro ao gerar gráficos de evolução temporal: {str(e)}")

# Análise detalhada por categorias com abas
with st.expander("📊 Transações por Categoria", expanded=False):
    if not df.empty and 'categoria' in df.columns:
        categorias_periodo = sorted(df['categoria'].unique())
        
        # Criar lista de abas: "Todas" + "Receitas" + "Despesas" + categorias específicas
        abas_disponiveis = ["📊 Todas", "💰 Receitas", "💸 Despesas"] + [f"🏷️ {cat}" for cat in categorias_periodo]
        
        # Criar abas usando st.tabs
        tabs = st.tabs(abas_disponiveis)
        
        with tabs[0]:  # Aba "Todas"
            st.markdown("**Todas as transações no período**")
            
            # Mostrar resumo
            total_transacoes = len(df)
            receitas_total = df.loc[df['valor'] > 0, 'valor'].sum()
            despesas_total = abs(df.loc[df['valor'] < 0, 'valor'].sum())
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("💼 Total", total_transacoes)
            with col2:
                st.metric("💰 Receitas", formatar_valor_monetario(receitas_total))
            with col3:
                st.metric("💸 Despesas", formatar_valor_monetario(despesas_total))
            with col4:
                st.metric("💳 Saldo", formatar_valor_monetario(receitas_total - despesas_total))
            
            # Tabela formatada
            df_display_todas = df.head(50).copy()
            df_display_todas = formatar_df_monetario(df_display_todas, col_valor="valor")
            
            st.dataframe(
                df_display_todas.loc[:, ['data', 'descricao', 'ValorFormatado', 'categoria', 'origem']].rename(
                    columns={
                        'data': 'Data',
                        'descricao': 'Descrição', 
                        'ValorFormatado': 'Valor',
                        'categoria': 'Categoria',
                        'origem': 'Origem'
                    }
                ),
                use_container_width=True,
                height=400
            )
            
            if len(df) > 50:
                st.caption(f"📄 Exibindo 50 de {len(df)} transações (ordenadas por data mais recente)")
        
        with tabs[1]:  # Aba "Receitas"
            st.markdown("**Receitas no período**")
            
            # Filtrar apenas receitas (valores positivos)
            df_receitas = df.loc[df['valor'] > 0]
            
            if not df_receitas.empty:
                # Mostrar resumo das receitas
                total_receitas = len(df_receitas)
                valor_total_receitas = df_receitas['valor'].sum()
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("💼 Total de Receitas", total_receitas)
                with col2:
                    st.metric("💰 Valor Total", formatar_valor_monetario(valor_total_receitas))
                with col3:
                    st.metric("📊 Receita Média", formatar_valor_monetario(valor_total_receitas / total_receitas))
                
                # Tabela formatada das receitas
                df_display_receitas = df_receitas.head(50).copy()
                df_display_receitas = formatar_df_monetario(df_display_receitas, col_valor="valor")
                
                st.dataframe(
                    df_display_receitas.loc[:, ['data', 'descricao', 'ValorFormatado', 'categoria', 'origem']].rename(
                        columns={
                            'data': 'Data',
                            'descricao': 'Descrição', 
                            'ValorFormatado': 'Valor',
                            'categoria': 'Categoria',
                            'origem': 'Origem'
                        }
                    ),
                    use_container_width=True,
                    height=400
                )
                
                if len(df_receitas) > 50:
                    st.caption(f"📄 Exibindo 50 de {len(df_receitas)} receitas (ordenadas por data mais recente)")
            else:
                st.info("📭 Nenhuma receita encontrada no período selecionado.")
        
        with tabs[2]:  # Aba "Despesas"
            st.markdown("**Despesas no período**")
            
            # Filtrar apenas despesas (valores negativos)
            df_despesas = df.loc[df['valor'] < 0]
            
            if not df_despesas.empty:
                # Mostrar resumo das despesas
                total_despesas = len(df_despesas)
                valor_total_despesas = abs(df_despesas['valor'].sum())
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("💼 Total de Despesas", total_despesas)
                with col2:
                    st.metric("💸 Valor Total", formatar_valor_monetario(valor_total_despesas))
                with col3:
                    st.metric("📊 Despesa Média", formatar_valor_monetario(valor_total_despesas / total_despesas))
                
                # Tabela formatada das despesas
                df_display_despesas = df_despesas.head(50).copy()
                df_display_despesas = formatar_df_monetario(df_display_despesas, col_valor="valor")
                
                st.dataframe(
                    df_display_despesas.loc[:, ['data', 'descricao', 'ValorFormatado', 'categoria', 'origem']].rename(
                        columns={
                            'data': 'Data',
                            'descricao': 'Descrição', 
                            'ValorFormatado': 'Valor',
                            'categoria': 'Categoria',
                            'origem': 'Origem'
                        }
                    ),
                    use_container_width=True,
                    height=400
                )
                
                if len(df_despesas) > 50:
                    st.caption(f"📄 Exibindo 50 de {len(df_despesas)} despesas (ordenadas por data mais recente)")
            else:
                st.info("📭 Nenhuma despesa encontrada no período selecionado.")
        
        # Abas para cada categoria
        for i, categoria in enumerate(categorias_periodo, 3):
            with tabs[i]:
                # Filtrar transações da categoria
                df_categoria = df[df['categoria'] == categoria]
                
                st.markdown(f"**Transações da categoria: {categoria}**")
                
                # Mostrar resumo da categoria
                total_cat = len(df_categoria)
                receitas_cat = df_categoria[df_categoria['valor'] > 0]['valor'].sum()
                despesas_cat = abs(df_categoria[df_categoria['valor'] < 0]['valor'].sum())
                saldo_cat = receitas_cat - despesas_cat
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("💼 Transações", total_cat)
                with col2:
                    st.metric("💰 Receitas", formatar_valor_monetario(receitas_cat))
                with col3:
                    st.metric("💸 Despesas", formatar_valor_monetario(despesas_cat))
                with col4:
                    st.metric("💳 Saldo", formatar_valor_monetario(saldo_cat))
                
                if not df_categoria.empty:
                    # Tabela formatada da categoria
                    df_display_cat = df_categoria.head(50).copy()
                    df_display_cat = formatar_df_monetario(df_display_cat, col_valor="valor")
                    
                    st.dataframe(
                        df_display_cat.loc[:, ['data', 'descricao', 'ValorFormatado', 'origem']].rename(
                            columns={
                                'data': 'Data',
                                'descricao': 'Descrição',
                                'ValorFormatado': 'Valor',
                                'origem': 'Origem'
                            }
                        ),
                        use_container_width=True,
                        height=400
                    )
                    
                    if len(df_categoria) > 50:
                        st.caption(f"📄 Exibindo 50 de {len(df_categoria)} transações desta categoria")
                else:
                    st.info("📭 Nenhuma transação encontrada nesta categoria.")
    else:
        st.info("📊 Nenhuma transação disponível para análise por categorias.")

st.markdown("---")

# Transações recentes
with st.expander("🕒 Transações Recentes", expanded=False):
    if not df.empty:
        df_recentes = df.head(10).copy()
        df_recentes = formatar_df_monetario(df_recentes, col_valor="valor")
        st.dataframe(df_recentes, use_container_width=True)
    else:
        st.info("Nenhuma transação para exibir")
