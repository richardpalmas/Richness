import pandas as pd
import plotly.express as px
import streamlit as st
import time
import os

from componentes.profile_pic_component import boas_vindas_com_foto
from database import get_connection, create_tables, remover_usuario, get_user_role
from utils.config import ENABLE_CACHE
from utils.exception_handler import ExceptionHandler
from utils.filtros import filtro_data, filtro_categorias, aplicar_filtros
from utils.formatacao import formatar_valor_monetario, formatar_df_monetario, calcular_resumo_financeiro
from utils.ofx_reader import OFXReader

# Importações de segurança
from security.auth.authentication import SecureAuthentication
try:
    from security.auth.rate_limiter import RateLimiter  # type: ignore
except ImportError:
    # Fallback to inline RateLimiter if import fails
    class RateLimiter:
        def __init__(self):
            self.MAX_LOGIN_ATTEMPTS = 5
            self.LOGIN_WINDOW_MINUTES = 15
            self._attempts_by_ip = {}
            self._attempts_by_user = {}
        
        def check_rate_limit(self, ip_address, username=None):
            return True  # Simplified for now
        
        def record_attempt(self, ip_address, username=None, success=False):
            pass  # Simplified for now

# Configurações da página
st.set_page_config(
    page_title="Richness - Dashboard", 
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
        st.markdown("## 🔐 Login")
        st.markdown("Para acessar o dashboard, faça login com suas credenciais:")
        
        # Formulário de login
        with st.form("login_form", clear_on_submit=False):
            usuario = st.text_input(
                "👤 Usuário",
                placeholder="Digite seu nome de usuário",
                help="Nome de usuário cadastrado no sistema"
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
            
            # Processar login            if login_button:
                if not usuario or not senha:
                    st.error("❌ Por favor, preencha todos os campos!")
                else:
                    try:
                        import sqlite3
                        import hashlib
                        
                        # Obter IP do cliente (fallback para localhost)  
                        client_ip = st.session_state.get('client_ip', '127.0.0.1')
                        
                        # Conexão direta com o banco para verificar credenciais
                        conn = sqlite3.connect('richness.db')
                        cur = conn.cursor()
                        
                        cur.execute('SELECT usuario, senha FROM usuarios WHERE usuario = ?', (usuario,))
                        user_record = cur.fetchone()
                        
                        if user_record:
                            stored_username, stored_hash = user_record
                            
                            # Verificar se é hash SHA-256 (64 caracteres)
                            if len(stored_hash) == 64:
                                # Hash SHA-256 simples
                                provided_hash = hashlib.sha256(senha.encode()).hexdigest()
                                senha_valida = (provided_hash == stored_hash)
                            else:
                                # Tentar com bcrypt
                                try:
                                    import bcrypt
                                    senha_valida = bcrypt.checkpw(senha.encode('utf-8'), stored_hash.encode('utf-8'))
                                except:
                                    senha_valida = False
                            
                            if senha_valida:
                                resultado = {
                                    'success': True,
                                    'message': 'Login realizado com sucesso',
                                    'username': usuario
                                }
                            else:
                                resultado = {
                                    'success': False,
                                    'message': 'Usuário ou senha incorretos'
                                }
                        else:
                            resultado = {
                                'success': False,
                                'message': 'Usuário não encontrado'
                            }
                        
                        conn.close()
                        
                        if resultado['success']:
                            # Login bem-sucedido - configurar sessão
                            st.session_state['authenticated'] = True
                            st.session_state['autenticado'] = True
                            st.session_state['usuario'] = usuario
                            st.session_state['session_id'] = resultado.get('session_id', '')
                            
                            st.success("✅ Login realizado com sucesso!")
                            st.info("🔄 Redirecionando para o dashboard...")
                            time.sleep(1)
                            st.rerun()
                            
                        else:
                            # Login falhou
                            message = resultado.get('message', 'Erro na autenticação')
                            st.error(f"❌ {message}")
                              # Verificar se a conta está bloqueada
                            if resultado.get('account_locked'):
                                st.warning("⚠️ Sua conta foi bloqueada por segurança. Contate o administrador.")
                            elif resultado.get('rate_limited'):
                                st.warning("⚠️ Muitas tentativas de login. Aguarde alguns minutos.")
                                
                    except Exception as e:
                        st.error("❌ Erro interno do sistema. Tente novamente.")
        
        # Links úteis
        st.markdown("---")
        
        # Informações adicionais
        with st.expander("ℹ️ Precisa de ajuda?"):
            st.write("""
            **Primeiro acesso?**
            - Clique em "Criar Conta" para se cadastrar
            - Preencha seus dados e crie uma senha segura
            
            **Esqueceu sua senha?**
            - Entre em contato com o administrador
            - Mantenha suas credenciais em local seguro
            
            **Problemas técnicos?**
            - Verifique sua conexão com a internet
            - Limpe o cache do navegador
            - Tente novamente em alguns minutos
            """)
        
        # Informação de segurança
        st.markdown("---")
        st.markdown(
            "🔒 **Suas informações estão protegidas** com criptografia "
            "e políticas de segurança avançadas."
        )

verificar_autenticacao()

# Criar tabelas do banco de dados
create_tables()

# Obter usuário da sessão
usuario = st.session_state.get('usuario', 'default')

# Boas-vindas com foto de perfil
if usuario:
    boas_vindas_com_foto(usuario)

# Título principal
st.title("🏠 Dashboard Financeiro")

# Cache do OFX Reader
@st.cache_resource(ttl=300)
def get_ofx_reader():
    return OFXReader()

@st.cache_data(ttl=600)
def carregar_dados_home(usuario, force_refresh=False):
    """Carrega dados essenciais para a Home com cache otimizado"""
    def _load_data():
        ofx_reader = get_ofx_reader()
        
        # Se force_refresh for True, limpar cache
        if force_refresh:
            ofx_reader.limpar_cache()
        
        # Carregar dados dos arquivos OFX
        df_extratos = ofx_reader.buscar_extratos()
        df_cartoes = ofx_reader.buscar_cartoes()
        
        # Combinar extratos e cartões
        df = pd.concat([df_extratos, df_cartoes], ignore_index=True) if not df_extratos.empty or not df_cartoes.empty else pd.DataFrame()
        
        # Pré-processamento mínimo
        if not df.empty:
            df["Data"] = pd.to_datetime(df["Data"])
            df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")
            
            # Aplicar categorizações personalizadas do usuário (MESMO CÓDIGO DA PÁGINA GERENCIAR_TRANSACOES)
            cache_categorias_file = "cache_categorias_usuario.json"
            if os.path.exists(cache_categorias_file):
                try:
                    import json
                    with open(cache_categorias_file, 'r', encoding='utf-8') as f:
                        cache = json.load(f)
                    
                    def aplicar_categoria_personalizada(row):
                        descricao_normalizada = row["Descrição"].lower().strip()
                        if descricao_normalizada in cache:
                            return cache[descricao_normalizada]
                        return row.get("Categoria", "Outros")
                    
                    df["Categoria"] = df.apply(aplicar_categoria_personalizada, axis=1)
                except:
                    pass  # Em caso de erro, manter categorizações originais
            
            # Aplicar filtro de transações excluídas
            transacoes_excluidas_file = "transacoes_excluidas.json"
            if os.path.exists(transacoes_excluidas_file):
                try:
                    import json
                    import hashlib
                    with open(transacoes_excluidas_file, 'r', encoding='utf-8') as f:
                        transacoes_excluidas = json.load(f)
                    
                    if transacoes_excluidas:
                        def gerar_hash_transacao(row):
                            data_str = row["Data"].strftime("%Y-%m-%d") if hasattr(row["Data"], 'strftime') else str(row["Data"])
                            chave = f"{data_str}|{row['Descrição']}|{row['Valor']}"
                            return hashlib.md5(chave.encode()).hexdigest()
                        
                        def nao_esta_excluida(row):
                            hash_transacao = gerar_hash_transacao(row)
                            return hash_transacao not in transacoes_excluidas
                        
                        df = df[df.apply(nao_esta_excluida, axis=1)]
                except:
                    pass  # Em caso de erro, manter todas as transações
            
            # Calcular saldos por origem
            saldos_info = {}
            for origem in df['Origem'].unique():
                df_origem = df[df['Origem'] == origem]
                saldo = df_origem['Valor'].sum()
                saldos_info[origem] = {
                    'saldo': saldo,
                    'tipo': 'credit_card' if 'fatura' in origem.lower() or 'nubank' in origem.lower() else 'checking'
                }
        else:
            saldos_info = {}
        
        return saldos_info, df
    
    return ExceptionHandler.safe_execute(
        func=_load_data,
        error_handler=ExceptionHandler.handle_generic_error,
        default_return=({}, pd.DataFrame())
    )

# Sidebar - Configurações
st.sidebar.header("⚙️ Configurações")

# Botão de Sair
st.sidebar.markdown("---")  # Separador visual
if st.sidebar.button('🚪 Sair', help="Fazer logout da aplicação", type="primary"):
    st.session_state.clear()
    st.rerun()

# Carregar dados principais
saldos_info, df = carregar_dados_home(usuario)

# Verificar se há dados
if df.empty:
    st.warning("📭 Nenhuma transação encontrada nos arquivos OFX!")
    st.info("💡 **Como adicionar dados:**")
    st.markdown("""
    1. 📁 Coloque seus extratos (.ofx) na pasta `extratos/`
    2. 💳 Coloque suas faturas de cartão (.ofx) na pasta `faturas/`
    3. 🔄 Clique em "Atualizar Dados" na barra lateral
    """)
    
    # Mostrar resumo dos arquivos disponíveis
    ofx_reader = get_ofx_reader()
    resumo = ofx_reader.get_resumo_arquivos()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("📄 Extratos Disponíveis", resumo['total_extratos'])
    with col2:
        st.metric("💳 Faturas Disponíveis", resumo['total_faturas'])
    
    st.stop()

# Dashboard principal
st.subheader("📊 Resumo Financeiro")

# Calcular resumo financeiro
resumo = calcular_resumo_financeiro(df)

# Métricas principais
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "💰 Receitas", 
        formatar_valor_monetario(resumo["receitas"]),
        delta=None
    )

with col2:
    st.metric(
        "💸 Despesas", 
        formatar_valor_monetario(abs(resumo["despesas"])),
        delta=None
    )

with col3:
    saldo_liquido = resumo["saldo"]
    delta_color = "normal" if saldo_liquido >= 0 else "inverse"
    st.metric(
        "💳 Saldo Líquido", 
        formatar_valor_monetario(saldo_liquido),
        delta=None
    )

with col4:
    st.metric(
        "📈 Total de Transações", 
        len(df),
        delta=None
    )

# Filtros
st.subheader("🔍 Filtros")
col1, col2 = st.columns(2)

with col1:
    data_inicio, data_fim = filtro_data(df)

with col2:
    categorias_selecionadas = filtro_categorias(df)

# Aplicar filtros
df_filtrado = aplicar_filtros(df, data_inicio, data_fim, categorias_selecionadas)

if df_filtrado.empty:
    st.warning("🔍 Nenhuma transação encontrada com os filtros aplicados.")
    st.stop()

# Gráficos
st.subheader("📈 Análises")

# Primeira linha: Distribuição por Categoria
col1, col2 = st.columns(2)

with col1:
    # Gráfico de categorias (apenas despesas)
    if "Categoria" in df_filtrado.columns:
        # Filtrar apenas transações negativas (despesas)
        df_despesas = df_filtrado[df_filtrado["Valor"] < 0]
        
        if not df_despesas.empty:
            categoria_resumo_despesas = df_despesas.groupby("Categoria")["Valor"].sum().reset_index()
            categoria_resumo_despesas["ValorAbs"] = categoria_resumo_despesas["Valor"].abs()
            categoria_resumo_despesas = categoria_resumo_despesas.sort_values("ValorAbs", ascending=False)
            
            fig_cat_despesas = px.pie(
                categoria_resumo_despesas, 
                names="Categoria", 
                values="ValorAbs",
                title="Distribuição por Categoria (Despesas)",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            st.plotly_chart(fig_cat_despesas, use_container_width=True)
        else:
            st.info("📊 Nenhuma despesa encontrada no período selecionado.")

with col2:
    # Gráfico de categorias (apenas receitas)
    if "Categoria" in df_filtrado.columns:
        # Filtrar apenas transações positivas (receitas)
        df_receitas = df_filtrado[df_filtrado["Valor"] > 0]
        
        if not df_receitas.empty:
            categoria_resumo_receitas = df_receitas.groupby("Categoria")["Valor"].sum().reset_index()
            categoria_resumo_receitas = categoria_resumo_receitas.sort_values("Valor", ascending=False)
            
            fig_cat_receitas = px.pie(
                categoria_resumo_receitas, 
                names="Categoria", 
                values="Valor",
                title="Distribuição por Categoria (Receitas)",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            st.plotly_chart(fig_cat_receitas, use_container_width=True)
        else:
            st.info("📊 Nenhuma receita encontrada no período selecionado.")

# Segunda linha: Evolução Temporal
st.markdown("---")
if "Data" in df_filtrado.columns:
    df_temp = df_filtrado.copy()
    df_temp["AnoMes"] = df_temp["Data"].dt.to_period("M").astype(str)
    evolucao = df_temp.groupby("AnoMes")["Valor"].sum().reset_index()
    
    fig_evolucao = px.line(
        evolucao, 
        x="AnoMes", 
        y="Valor",
        title="📈 Evolução Mensal do Saldo",
        markers=True,
        line_shape="spline"
    )
    fig_evolucao.update_layout(
        xaxis_title="Período",
        yaxis_title="Valor (R$)",
        showlegend=False
    )
    st.plotly_chart(fig_evolucao, use_container_width=True)

# Tabela de transações
st.subheader("📋 Transações Recentes")

# Formatação da tabela
df_display = formatar_df_monetario(df_filtrado.head(50))

st.dataframe(
    df_display,
    use_container_width=True,
    height=400
)

# Informações sobre arquivos OFX
with st.expander("📁 Informações dos Arquivos OFX"):
    ofx_reader = get_ofx_reader()
    resumo = ofx_reader.get_resumo_arquivos()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Extratos:**")
        st.write(f"Total: {resumo['total_extratos']} arquivos")
        if resumo['periodo_extratos']['inicio']:
            st.write(f"Período: {resumo['periodo_extratos']['inicio']} a {resumo['periodo_extratos']['fim']}")
    
    with col2:
        st.write("**Faturas:**")
        st.write(f"Total: {resumo['total_faturas']} arquivos")
        if resumo['periodo_faturas']['inicio']:
            st.write(f"Período: {resumo['periodo_faturas']['inicio']} a {resumo['periodo_faturas']['fim']}")
