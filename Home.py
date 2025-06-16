import pandas as pd
import plotly.express as px
import streamlit as st
import time
import os
import json
import hashlib
from datetime import datetime

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

def mostrar_formulario_login():
    """Exibe formulário de login profissional do Richness"""
    
    # Configurar layout para centralizar o login
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Cabeçalho da marca
        st.markdown("---")
        st.markdown("# 💰 Richness")
        st.markdown("### Sua plataforma de gestão financeira pessoal")
        st.markdown("**Tome controle das suas finanças de forma inteligente e segura**")
        
        # Formulário de login
        with st.form("login_form", clear_on_submit=False):
            st.markdown("#### 🔐 Acesse sua conta")
            
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
            
            # Processar login
            if login_button:
                if not usuario or not senha:
                    st.error("❌ Por favor, preencha todos os campos!")
                else:
                    resultado = autenticar_usuario_v2(usuario, senha)
                    
                    if resultado['success']:
                        # Login bem-sucedido
                        st.session_state['authenticated'] = True
                        st.session_state['autenticado'] = True
                        st.session_state['usuario'] = usuario
                        
                        st.success("✅ Bem-vindo(a) ao Richness!")
                        st.info("🔄 Carregando seu dashboard financeiro...")
                        time.sleep(1)
                        st.rerun()
                        
                    else:
                        st.error(f"❌ {resultado.get('message', 'Erro na autenticação')}")
        
        # Informações sobre o Richness
        st.markdown("---")
        
        with st.expander("� Por que escolher o Richness?"):
            st.write("""
            **Gestão Financeira Inteligente**
            - 📊 Análises detalhadas de receitas e despesas
            - 📈 Gráficos e relatórios visuais
            - 🏷️ Categorização automática de transações
            - 📅 Acompanhamento temporal de seu progresso
            
            **Segurança e Privacidade**
            - 🔒 Seus dados são protegidos e organizados por usuário
            - 🛡️ Criptografia avançada para suas informações
            - 🚀 Performance otimizada para melhor experiência
            - � Interface intuitiva e profissional
            
            **Recursos Avançados**
            - � Separação clara entre receitas e despesas
            - 🎯 Cálculo de ticket médio e métricas importantes
            - 📋 Transações organizadas por categoria
            - 🔄 Atualizações em tempo real
            """)
            
        # Rodapé profissional
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

# Limpar caches se necessário (debug)
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
                for _, row in df_compromissos.iterrows():
                    data_vencimento = row['data_vencimento']
                    data_fmt = data_vencimento.strftime('%d/%m/%Y')
                    valor_fmt = formatar_valor_monetario(row['valor'])
                    desc = row['descricao']
                    categoria = row['categoria']
                    
                    # Calcular dias restantes
                    hoje = datetime.now().date()
                    dias_restantes = (data_vencimento.date() - hoje).days
                    
                    # Determinar urgência
                    if dias_restantes < 0:
                        urgencia = "🔴 VENCIDO"
                        cor = "red"
                    elif dias_restantes == 0:
                        urgencia = "🟡 VENCE HOJE"
                        cor = "orange"
                    elif dias_restantes <= 3:
                        urgencia = f"🟠 {dias_restantes} dias"
                        cor = "orange"
                    else:
                        urgencia = f"🟢 {dias_restantes} dias"
                        cor = "green"
                    
                    # Linha do compromisso
                    col1, col2, col3 = st.columns([3, 2, 1])
                    
                    with col1:
                        st.markdown(f"**{desc}**")
                        st.caption(f"🏷️ {categoria}")
                    
                    with col2:
                        st.markdown(f"📅 **{data_fmt}**")
                        st.markdown(f"💰 **{valor_fmt}**")
                    
                    with col3:
                        st.markdown(f"<span style='color: {cor};'><b>{urgencia}</b></span>", unsafe_allow_html=True)
                    
                    # Observações se existirem
                    if row.get('observacoes') and pd.notna(row['observacoes']):
                        st.caption(f"📝 {row['observacoes']}")
                    
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
st.sidebar.markdown("**Sistema Richness Ativo** �")

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
    2. �️ O período selecionado não contém transações
    3. � Os dados não foram migrados para o Backend V2
    """)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("� Tentar Recarregar", type="primary"):
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
def mostrar_insights_ia(usuario: str):
    """Exibe insights e status de IA integrados"""
    try:
        # Obter ID do usuário
        db = DatabaseManager()
        usuario_repo = UsuarioRepository(db)
        user_data = usuario_repo.obter_usuario_por_username(usuario)
        
        if not user_data:
            st.error(f"DEBUG: Usuário '{usuario}' não encontrado no banco de dados")
            return
        
        user_id = user_data.get('id')
        if not user_id:
            st.error(f"DEBUG: user_id não encontrado para usuário '{usuario}', user_data: {user_data}")
            return
            
        st.info(f"DEBUG: Processando insights para user_id={user_id}, usuario='{usuario}'")
        
        # Importar serviços de IA
        from services.ai_assistant_service import FinancialAIAssistant
        from services.ai_categorization_service import AICategorization
        
        ai_assistant = FinancialAIAssistant()
        ai_categorization = AICategorization()
        
        # Container para insights de IA
        with st.expander("🤖 **Insights de IA** - Inteligência Artificial Financeira", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 🎯 Insights Rápidos")
                
                # Obter insights rápidos
                insights = ai_assistant.get_quick_insights(user_id)
                
                if 'erro' not in insights:
                    # Saldo mensal
                    if 'saldo_mensal' in insights:
                        saldo = insights['saldo_mensal']
                        if saldo > 0:
                            st.success(f"💰 Sobra mensal: R$ {saldo:,.2f}")
                        elif saldo < 0:
                            st.error(f"⚠️ Déficit mensal: R$ {abs(saldo):,.2f}")
                        else:
                            st.info("⚖️ Receitas e despesas equilibradas")
                    
                    # Top categoria
                    if 'top_categoria' in insights:
                        cat = insights['top_categoria']
                        st.info(f"📊 Maior gasto: {cat['nome']} (R$ {cat['valor']:,.2f})")
                    
                    # Alertas
                    if insights.get('alertas'):
                        st.warning("⚠️ " + insights['alertas'][0])
                        
                    # Mostrar erros específicos para debug
                    if 'erro_saldo' in insights:
                        st.error(f"Erro no saldo: {insights['erro_saldo']}")
                    if 'erro_alertas' in insights:
                        st.error(f"Erro nos alertas: {insights['erro_alertas']}")
                    if 'erro_categoria' in insights:
                        st.error(f"Erro na categoria: {insights['erro_categoria']}")
                    if 'erro_sugestoes' in insights:
                        st.error(f"Erro nas sugestões: {insights['erro_sugestoes']}")
                else:
                    st.warning(f"⚠️ Erro geral nos insights: {insights.get('erro', 'Erro desconhecido')}")
            
            with col2:
                st.markdown("#### 🔬 Status de Categorização IA")
                
                # Obter estatísticas de categorização
                stats = ai_categorization.obter_estatisticas_precisao(user_id)
                
                if stats:
                    total = stats.get('total_transacoes', 0)
                    categorizadas = stats.get('transacoes_categorizadas', 0)
                    precisao = stats.get('precisao_geral', 0)
                    
                    if total > 0:
                        progress = categorizadas / total if total > 0 else 0
                        st.progress(progress, text=f"Categorização: {categorizadas}/{total}")
                        
                        if precisao > 80:
                            st.success(f"🎯 Alta precisão: {precisao:.1f}%")
                        elif precisao > 60:
                            st.info(f"📈 Precisão moderada: {precisao:.1f}%")
                        else:
                            st.warning(f"⚠️ Precisão baixa: {precisao:.1f}%")
                    else:
                        st.info("📝 Aguardando mais dados para análise")
                else:
                    st.info("🤖 Sistema de IA sendo inicializado...")
                
                # Botão para ir ao assistente
                if st.button("💬 Conversar com IA", type="secondary"):
                    st.switch_page("pages/Assistente_IA.py")
    
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
