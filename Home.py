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
            st.info("💡 Para gerenciar seus compromissos, acesse a página [Minhas Economias](pages/Minhas_Economias)")
            
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

# Insights de IA Integrados
from componentes.insight_card import exibir_insight_card
def mostrar_insights_ia(usuario: str):
    """Exibe insights e status de IA integrados"""
    try:
        # Obter ID do usuário
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
        
        # Importar serviços de IA
        from services.ai_assistant_service import FinancialAIAssistant
        from services.ai_categorization_service import AICategorization
        from services.transacao_service_v2 import TransacaoService
        from utils.repositories_v2 import PersonalidadeIARepository
        
        ai_assistant = FinancialAIAssistant()
        ai_categorization = AICategorization()
        transacao_service = TransacaoService()
        personalidade_repo = PersonalidadeIARepository(db)
        
        # Buscar as 30 últimas transações do extrato e 30 da fatura/cartão
        df_todas = transacao_service.listar_transacoes_usuario(usuario, limite=5000)
        if df_todas.empty:
            st.info("Nenhuma transação encontrada para análise de insights.")
            return
        # Garantir coluna 'origem' minúscula
        df_todas['origem'] = df_todas['origem'].astype(str)
        # Garantir coluna 'data' como datetime se existir
        if 'data' in df_todas.columns:
            df_todas['data'] = pd.to_datetime(df_todas['data'], errors='coerce')
        # Extrato: não contém fatura/cartao/credit
        df_extrato = df_todas[~df_todas['origem'].str.contains('fatura|cartao|credit', case=False, na=False)]
        if not df_extrato.empty and 'data' in df_extrato.columns:
            # Garantir que é DataFrame e coluna existe
            if not isinstance(df_extrato, pd.DataFrame):
                df_extrato = pd.DataFrame(df_extrato)
            if not pd.api.types.is_datetime64_any_dtype(df_extrato['data']):
                df_extrato['data'] = pd.to_datetime(df_extrato['data'], errors='coerce')
            # Remover linhas com data nula
            df_extrato = df_extrato.dropna(subset=['data'])
            df_extrato_ultimas = df_extrato.sort_values(by="data", ascending=False).head(30)
        else:
            df_extrato_ultimas = df_extrato.head(30)
        # Fatura/cartão: contém fatura/cartao/credit
        df_cartao = df_todas[df_todas['origem'].str.contains('fatura|cartao|credit', case=False, na=False)]
        if not df_cartao.empty and 'data' in df_cartao.columns:
            if not isinstance(df_cartao, pd.DataFrame):
                df_cartao = pd.DataFrame(df_cartao)
            if not pd.api.types.is_datetime64_any_dtype(df_cartao['data']):
                df_cartao['data'] = pd.to_datetime(df_cartao['data'], errors='coerce')
            df_cartao = df_cartao.dropna(subset=['data'])
            df_cartao_ultimas = df_cartao.sort_values(by="data", ascending=False).head(30)
        else:
            df_cartao_ultimas = df_cartao.head(30)
        # Unir para análise
        df_insights = pd.concat([df_extrato_ultimas, df_cartao_ultimas], ignore_index=True)
        # Substituir seletor visual antigo pelo componente reutilizável
        render_personality_selector()
        # Definir personalidade selecionada
        personalidade_sel = st.session_state.get('ai_personality', 'clara')
        # O restante do fluxo de insights deve usar personalidade_sel
        # ... restante do código ...
    except Exception as e:
        st.error(f"❌ Erro ao carregar insights de IA: {str(e)}")

mostrar_insights_ia(usuario)

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
