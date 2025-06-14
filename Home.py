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
    """Autentica usuário usando Backend V2 com senhas criptografadas"""
    try:
        # Inicializar Backend V2
        db_manager = DatabaseManager()
        user_repo = UsuarioRepository(db_manager)
        
        # Verificar senha usando método seguro
        user_data = user_repo.verificar_senha(usuario, senha)
        
        if user_data:
            return {
                'success': True,
                'message': 'Login realizado com sucesso (Backend V2 Seguro)',
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
            'message': f'Erro no Backend V2: {str(e)}'
        }

# Verificar se o sistema V2 está disponível
def init_backend_v2_obrigatorio():
    """Inicializa o Backend V2 - OBRIGATÓRIO"""
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
        
        # Teste básico de funcionamento
        try:
            # Verificar se o banco V2 está acessível
            usuarios = usuario_repo.buscar_todos()
            if isinstance(usuarios, list):  # Se retornou uma lista, está funcionando
                pass  # Tudo OK
        except Exception as e:
            st.error("❌ **Backend V2 não está funcionando corretamente!**")
            st.error("🔧 Verifique a conexão com o banco de dados V2")
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
        st.error(f"❌ **Falha crítica no Backend V2!**")
        st.error(f"🔧 **Erro**: {str(e)}")
        st.error("📋 **Ação necessária**: Verifique se o sistema V2 foi inicializado corretamente")
        st.stop()

# Verificar autenticação
verificar_autenticacao()

# Limpar caches se necessário (debug)
if st.sidebar.button("🔄 Limpar Cache", help="Limpa cache do sistema"):
    st.cache_data.clear()
    st.cache_resource.clear()
    st.success("✅ Cache limpo!")
    st.rerun()

# Inicializar Backend V2 (obrigatório)
try:
    backend_v2 = init_backend_v2_obrigatorio()
except Exception as e:
    st.error(f"❌ Erro na inicialização do Backend V2: {e}")
    st.stop()

# Obter usuário da sessão
usuario = st.session_state.get('usuario', 'default')

# Boas-vindas com foto de perfil
if usuario:
    boas_vindas_com_foto(usuario)

# Título principal
st.title("🚀 Dashboard Financeiro")

# Carregar dados principais do usuário
@st.cache_data(ttl=600)
def carregar_dados_v2(usuario, data_inicio=None, data_fim=None, force_refresh=False):
    """Carrega dados do usuário usando APENAS o Backend V2"""
    try:
        transacao_service = backend_v2['transacao_service']
        
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
        st.error(f"❌ Erro ao carregar dados V2: {str(e)}")
        return {}, pd.DataFrame()

# Sidebar - Configurações e Filtros (configurar antes de carregar dados)
st.sidebar.header("⚙️ Configurações V2")
st.sidebar.markdown("**Backend V2 Ativo** 🚀")

# Carregar dados iniciais para definir range de datas
saldos_info_inicial, df_inicial = carregar_dados_v2(usuario)

# Filtros na sidebar
st.sidebar.markdown("### � Selecionar Período")

# Filtro de período
data_inicio, data_fim = None, None
if not df_inicial.empty and 'data' in df_inicial.columns:
    # Converter coluna de data se necessário
    df_for_filter = df_inicial.copy()
    df_for_filter['Data'] = pd.to_datetime(df_for_filter['data'])
    data_inicio, data_fim = filtro_data(df_for_filter, key_prefix="home")
    
    st.sidebar.success(f"📅 Período: {data_inicio} a {data_fim}")

# Carregar dados com filtro aplicado
saldos_info, df = carregar_dados_v2(usuario, data_inicio, data_fim)

st.markdown("---")

# Informações do usuário na sidebar
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
st.subheader("📊 Resumo Financeiro V2")

# Estatísticas do carregamento
col1, col2, col3, col4 = st.columns(4)

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

with col4:
    st.metric("🔒 Isolamento", "✅ Por Usuário")

# Calcular resumo financeiro
resumo = calcular_resumo_financeiro(df, col_valor="valor", col_descricao="descricao", col_categoria="categoria")

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
    ticket_medio = abs(resumo["despesas"]) / len(df[df['valor'] < 0]) if len(df[df['valor'] < 0]) > 0 else 0
    st.metric(
        "🎯 Ticket Médio",
        formatar_valor_monetario(ticket_medio)
    )

st.markdown("---")

# Gráficos e análises (usando apenas dados V2)
col1, col2 = st.columns(2)

with col1:
    # Gráfico de gastos por categoria
    if not df.empty and 'categoria' in df.columns:
        df_despesas = df[df['valor'] < 0].copy()
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
        df_receitas = df[df['valor'] > 0].copy()
        if not df_receitas.empty:
            receitas_categoria = df_receitas.groupby('categoria')['valor'].sum().sort_values(ascending=False)
            
            fig_receitas = px.pie(
                values=receitas_categoria.values,
                names=receitas_categoria.index,
                title="💰 Receitas por Categoria (V2)"
            )
            st.plotly_chart(fig_receitas, use_container_width=True)

# Evolução temporal
st.subheader("📈 Análise Temporal")
if not df.empty and 'data' in df.columns:
    try:
        df_temp = df.copy()
        df_temp['data'] = pd.to_datetime(df_temp['data'])
        df_temp['Mes'] = df_temp['data'].dt.to_period('M')
        
        # Separar receitas e despesas
        df_temp_receitas = df_temp[df_temp['valor'] > 0].copy()
        df_temp_despesas = df_temp[df_temp['valor'] < 0].copy()
        
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
st.subheader("📊 Transações por Categoria")

if not df.empty and 'categoria' in df.columns:
    categorias_periodo = sorted(df['categoria'].unique())
    
    # Criar lista de abas: "Todas" + categorias específicas
    abas_disponiveis = ["📊 Todas"] + [f"🏷️ {cat}" for cat in categorias_periodo]
    
    # Criar abas usando st.tabs
    tabs = st.tabs(abas_disponiveis)
    
    with tabs[0]:  # Aba "Todas"
        st.markdown("**Todas as transações no período**")
        
        # Mostrar resumo
        total_transacoes = len(df)
        receitas_total = df[df['valor'] > 0]['valor'].sum()
        despesas_total = abs(df[df['valor'] < 0]['valor'].sum())
        
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
            df_display_todas[['data', 'descricao', 'ValorFormatado', 'categoria', 'origem']].rename(
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
    
    # Abas para cada categoria
    for i, categoria in enumerate(categorias_periodo, 1):
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
                    df_display_cat[['data', 'descricao', 'ValorFormatado', 'origem']].rename(
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
st.subheader("🕒 Transações Recentes")
if not df.empty:
    df_recentes = df.head(10).copy()
    df_recentes = formatar_df_monetario(df_recentes, col_valor="valor")
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
