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
from utils.formatacao import formatar_valor_monetario, formatar_df_monetario, calcular_resumo_financeiro

# BACKEND V2 OBRIGATÓRIO - Importações exclusivas
from utils.database_manager_v2 import DatabaseManager
from utils.repositories_v2 import RepositoryManager
from services.transacao_service_v2 import TransacaoService
from utils.database_monitoring import DatabaseMonitor

# Importações de segurança
from security.auth.authentication import SecureAuthentication

# Configurações da página
st.set_page_config(
    page_title="Richness V2 - Dashboard", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Verificar autenticação
def verificar_autenticacao():
    if 'authenticated' not in st.session_state or not st.session_state['authenticated']:
        mostrar_formulario_login()
        st.stop()

def mostrar_formulario_login():
    """Exibe formulário de login na página Home"""
    
    # Configurar layout para centralizar o login
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("---")
        st.markdown("## 🔐 Login - Sistema V2")
        st.markdown("**Backend V2 Obrigatório** - Para acessar o dashboard, faça login:")
        
        # Formulário de login
        with st.form("login_form", clear_on_submit=False):
            usuario = st.text_input(
                "👤 Usuário",
                placeholder="Digite seu nome de usuário",
                help="Nome de usuário cadastrado no sistema V2"
            )
            
            senha = st.text_input(
                "🔒 Senha",
                type="password",
                placeholder="Digite sua senha",
                help="Senha do seu usuário"
            )
            
            col_login, col_register = st.columns(2)
            
            with col_login:
                login_button = st.form_submit_button(
                    "🚀 Entrar V2",
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
                        
                        st.success("✅ Login realizado com sucesso no Backend V2!")
                        st.info("🔄 Redirecionando para o dashboard...")
                        time.sleep(1)
                        st.rerun()
                        
                    else:
                        st.error(f"❌ {resultado.get('message', 'Erro na autenticação')}")
        
        # Informações sobre o V2
        st.markdown("---")
        
        with st.expander("🚀 Sobre o Backend V2"):
            st.write("""
            **Sistema Totalmente Novo!**
            - 🔒 Dados organizados por usuário
            - 🚀 Performance otimizada
            - 📊 Recursos avançados de análise
            - 🛡️ Segurança aprimorada
            
            **Migração Automática**
            - Seus dados do sistema anterior foram migrados
            - Funcionalidades aprimoradas
            - Interface mais intuitiva
            """)

def autenticar_usuario_v2(usuario, senha):
    """Autentica usuário usando apenas o Backend V2"""
    try:
        # Inicializar Backend V2
        db_manager = DatabaseManager()
        repository_manager = RepositoryManager(db_manager)
        user_repo = repository_manager.get_repository('usuarios')
        
        # Buscar usuário no V2
        user_data = user_repo.buscar_por_username(usuario)
        
        if not user_data:
            return {
                'success': False,
                'message': 'Usuário não encontrado no Backend V2. Execute a migração obrigatória.'
            }
        
        # Verificar senha (implementação simplificada)
        import hashlib
        import bcrypt
        
        stored_hash = user_data.get('senha_hash', '')
        
        # Verificar se é hash SHA-256 (64 caracteres)
        if len(stored_hash) == 64:
            provided_hash = hashlib.sha256(senha.encode()).hexdigest()
            senha_valida = (provided_hash == stored_hash)
        else:
            # Tentar com bcrypt
            try:
                senha_valida = bcrypt.checkpw(senha.encode('utf-8'), stored_hash.encode('utf-8'))
            except:
                senha_valida = False
        
        if senha_valida:
            return {
                'success': True,
                'message': 'Login realizado com sucesso',
                'user_data': user_data
            }
        else:
            return {
                'success': False,
                'message': 'Senha incorreta'
            }
            
    except Exception as e:
        return {
            'success': False,
            'message': f'Erro no Backend V2: {str(e)}'
        }

# Verificar se o sistema V2 está disponível
@st.cache_resource
def init_backend_v2_obrigatorio():
    """Inicializa o Backend V2 - OBRIGATÓRIO"""
    try:
        db_manager = DatabaseManager()
        repository_manager = RepositoryManager(db_manager)
        transacao_service = TransacaoService()
          # Teste básico de funcionamento
        try:
            # Verificar se o banco V2 está acessível
            usuarios_repo = repository_manager.get_repository('usuarios')
            test_count = usuarios_repo.contar_total()
            if test_count >= 0:  # Qualquer resultado >= 0 indica que está funcionando
                pass  # Tudo OK
        except Exception:
            st.error("❌ **Backend V2 não está funcionando corretamente!**")
            st.error("🔧 Verifique a conexão com o banco de dados V2")
            st.stop()
        
        return {
            'db_manager': db_manager,
            'repository_manager': repository_manager,
            'transacao_service': transacao_service
        }
    except Exception as e:
        st.error(f"❌ **Falha crítica no Backend V2!**")
        st.error(f"🔧 **Erro**: {str(e)}")
        st.error("📋 **Ação necessária**: Verifique se o sistema V2 foi inicializado corretamente")
        st.stop()

# Verificar autenticação
verificar_autenticacao()

# Inicializar Backend V2 (obrigatório)
backend_v2 = init_backend_v2_obrigatorio()

# Obter usuário da sessão
usuario = st.session_state.get('usuario', 'default')

# Boas-vindas com foto de perfil
if usuario:
    boas_vindas_com_foto(usuario)

# Título principal
st.title("🚀 Dashboard Financeiro V2")
st.markdown("**Sistema de nova geração com dados organizados por usuário**")

# Verificar se usuário tem dados no V2
@st.cache_data(ttl=300)
def verificar_dados_usuario_v2(usuario):
    """Verifica se o usuário tem dados no Backend V2"""
    try:
        transacao_service = backend_v2['transacao_service']
        df_transacoes = transacao_service.listar_transacoes_usuario(usuario)
        
        if df_transacoes.empty:
            return {
                'tem_dados': False,
                'total_transacoes': 0,
                'mensagem': 'Nenhuma transação encontrada'
            }
        
        return {
            'tem_dados': True,
            'total_transacoes': len(df_transacoes),
            'mensagem': f'{len(df_transacoes)} transações encontradas'
        }
        
    except Exception as e:
        return {
            'tem_dados': False,
            'total_transacoes': 0,
            'mensagem': f'Erro ao verificar dados: {str(e)}'
        }

# Verificar dados do usuário
dados_status = verificar_dados_usuario_v2(usuario)

if not dados_status['tem_dados']:
    st.warning("⚠️ **Dados não encontrados no Backend V2**")
    st.info(f"📋 Status: {dados_status['mensagem']}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 🔄 Migração Necessária
        
        Seus dados precisam ser migrados para o Backend V2.
        
        **Execute o comando:**
        ```bash
        python migration_to_v2_mandatory.py
        ```
        """)
    
    with col2:
        st.markdown("""
        ### 📁 Upload de Dados
        
        Alternativamente, faça upload de novos arquivos OFX:
        
        1. Vá para **Atualizar Dados**
        2. Faça upload dos arquivos OFX
        3. Os dados serão automaticamente organizados por usuário
        """)
    
    if st.button("🔄 Tentar Recarregar", type="primary"):
        st.cache_data.clear()
        st.rerun()
    
    st.stop()

# Carregar dados principais do usuário
@st.cache_data(ttl=600)
def carregar_dados_v2(usuario, force_refresh=False):
    """Carrega dados do usuário usando APENAS o Backend V2"""
    try:
        transacao_service = backend_v2['transacao_service']
        
        # Carregar transações
        df_transacoes = transacao_service.listar_transacoes_usuario(usuario)
        
        if df_transacoes.empty:
            return {}, pd.DataFrame()
        
        # Calcular saldos por origem
        saldos_info = transacao_service.calcular_saldos_por_origem(usuario)
        
        return saldos_info, df_transacoes
        
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados V2: {str(e)}")
        return {}, pd.DataFrame()

# Carregar dados
saldos_info, df = carregar_dados_v2(usuario)

# Seção de status do sistema V2
with st.expander("🔧 Status do Backend V2", expanded=False):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("🚀 Backend", "V2", "✅ Ativo")
    
    with col2:
        try:
            monitor = backend_v2['monitor']
            health_info = monitor.get_system_health()
            status = "✅ Saudável" if health_info.get('healthy', False) else "⚠️ Atenção"
            st.metric("💗 Saúde", status)
        except:
            st.metric("💗 Saúde", "❓ Verificando")
    
    with col3:
        try:
            db_manager = backend_v2['db_manager']
            cache_stats = db_manager.get_cache_stats()
            hit_rate = cache_stats.get('hit_rate', 0)
            st.metric("⚡ Cache", f"{hit_rate:.1f}%")
        except:
            st.metric("⚡ Cache", "N/A")
    
    # Métricas detalhadas
    if st.checkbox("📊 Métricas detalhadas"):
        try:
            monitor = backend_v2['monitor']
            metrics = monitor.get_performance_metrics()
            
            st.json({
                "Conexões ativas": metrics.get('active_connections', 0),
                "Queries executadas": metrics.get('total_queries', 0),
                "Cache entries": metrics.get('cache_size', 0),
                "Uptime": f"{metrics.get('uptime', 0):.1f}s"
            })
        except Exception as e:
            st.error(f"Erro ao carregar métricas: {e}")

st.markdown("---")

# Sidebar - Configurações
st.sidebar.header("⚙️ Configurações V2")
st.sidebar.markdown("**Backend V2 Ativo** 🚀")

# Informações do usuário
if st.sidebar.expander("👤 Informações do Usuário"):
    st.sidebar.write(f"**Usuário**: {usuario}")
    st.sidebar.write(f"**Transações**: {len(df) if not df.empty else 0}")
    st.sidebar.write(f"**Sistema**: Backend V2")

# Botão de Sair
st.sidebar.markdown("---")
if st.sidebar.button('🚪 Sair', help="Fazer logout da aplicação", type="primary"):
    st.session_state.clear()
    st.rerun()

# Verificar se há dados
if df.empty:
    st.warning("📭 Nenhuma transação encontrada para este usuário!")
    st.info("💡 **Como adicionar dados no V2:**")
    st.markdown("""
    1. 📁 Vá para **Atualizar Dados** na barra lateral
    2. 📤 Faça upload de arquivos OFX
    3. 🔄 Os dados serão automaticamente organizados por usuário
    4. 🔒 Apenas você terá acesso aos seus dados
    """)
    st.stop()

# Dashboard principal
st.subheader("📊 Resumo Financeiro V2")

# Estatísticas do carregamento
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("📈 Total Transações", len(df))

with col2:
    origem_count = len(df['Origem'].unique()) if 'Origem' in df.columns else 0
    st.metric("🏦 Origens", origem_count)

with col3:
    periodo_dias = (df['Data'].max() - df['Data'].min()).days if not df.empty and 'Data' in df.columns else 0
    st.metric("📅 Período", f"{periodo_dias} dias")

with col4:
    st.metric("🔒 Isolamento", "✅ Por Usuário")

# Calcular resumo financeiro
resumo = calcular_resumo_financeiro(df)

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
    ticket_medio = abs(resumo["despesas"]) / len(df[df['Valor'] < 0]) if len(df[df['Valor'] < 0]) > 0 else 0
    st.metric(
        "🎯 Ticket Médio",
        formatar_valor_monetario(ticket_medio)
    )

st.markdown("---")

# Gráficos e análises (usando apenas dados V2)
col1, col2 = st.columns(2)

with col1:
    # Gráfico de gastos por categoria
    if not df.empty and 'Categoria' in df.columns:
        df_despesas = df[df['Valor'] < 0].copy()
        if not df_despesas.empty:
            gastos_categoria = df_despesas.groupby('Categoria')['Valor'].sum().abs().sort_values(ascending=False)
            
            fig_cat = px.pie(
                values=gastos_categoria.values,
                names=gastos_categoria.index,
                title="💸 Gastos por Categoria (V2)"
            )
            st.plotly_chart(fig_cat, use_container_width=True)

with col2:
    # Evolução temporal
    if not df.empty and 'Data' in df.columns:
        df_temp = df.copy()
        df_temp['Data'] = pd.to_datetime(df_temp['Data'])
        df_temp['Mes'] = df_temp['Data'].dt.to_period('M')
        
        evolucao = df_temp.groupby('Mes')['Valor'].sum()
        
        fig_evolucao = px.line(
            x=evolucao.index.astype(str),
            y=evolucao.values,
            title="📈 Evolução Mensal (V2)",
            labels={'x': 'Mês', 'y': 'Valor'}
        )
        st.plotly_chart(fig_evolucao, use_container_width=True)

# Transações recentes
st.subheader("🕒 Transações Recentes")
if not df.empty:
    df_recentes = df.head(10).copy()
    df_recentes = formatar_df_monetario(df_recentes)
    st.dataframe(df_recentes, use_container_width=True)
else:
    st.info("Nenhuma transação para exibir")

# Informações sobre o V2
st.markdown("---")
with st.expander("ℹ️ Sobre o Backend V2"):
    st.markdown("""
    ### 🚀 Características do Backend V2
    
    **🔒 Isolamento por Usuário**
    - Cada usuário tem acesso apenas aos seus próprios dados
    - Arquivos organizados em pastas específicas por usuário
    - Nenhum vazamento de dados entre usuários
    
    **⚡ Performance Otimizada**
    - Cache inteligente para consultas rápidas
    - Queries otimizadas para grandes volumes de dados
    - Interface responsiva e moderna
    
    **📊 Recursos Avançados**
    - Análises automatizadas com IA
    - Detecção de anomalias
    - Relatórios personalizados
    - Categorização inteligente
    
    **🛡️ Segurança Aprimorada**
    - Dados criptografados
    - Auditoria completa de acessos
    - Backups automáticos
    - Monitoramento em tempo real
    """)

st.success("✅ **Dashboard V2 carregado com sucesso!** Todos os dados são específicos do seu usuário.")
