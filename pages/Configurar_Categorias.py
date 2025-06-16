"""
Configuração de Categorias - Baseado na planilha de referência
Permite configurar categorias pré-definidas e personalizadas
"""

import streamlit as st
import pandas as pd

# Configurações da página
st.set_page_config(
    page_title="Richness - Categorias",
    page_icon="🏷️",
    layout="wide"
)

# Verificar autenticação
if 'authenticated' not in st.session_state or not st.session_state['authenticated']:
    st.error("🔒 Acesso negado. Faça login primeiro.")
    st.stop()

# Importações do sistema
from utils.database_manager_v2 import DatabaseManager
from utils.repositories_v2 import UsuarioRepository, CategoriaRepository
from services.insights_service_v2 import InsightsServiceV2

st.title("🏷️ Configuração de Categorias")
st.markdown("---")

# Obter usuário
usuario = st.session_state.get('usuario', 'default')

def obter_user_id(usuario):
    """Obtém o ID do usuário a partir do username"""
    try:
        db_manager = DatabaseManager()
        usuario_repo = UsuarioRepository(db_manager)
        user_data = usuario_repo.obter_usuario_por_username(usuario)
        return user_data['id'] if user_data else None
    except Exception as e:
        st.error(f"Erro ao obter user_id: {e}")
        return None

# Obter user_id
user_id = obter_user_id(usuario)

if not user_id:
    st.error("❌ Usuário não encontrado")
    st.stop()

# Inicializar serviços
insights_service = InsightsServiceV2()
db_manager = DatabaseManager()
categoria_repo = CategoriaRepository(db_manager)

# Seção 1: Categorias Pré-definidas baseadas na planilha
st.subheader("📋 Categorias Baseadas na sua Planilha")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 💰 Receitas")
    categorias_receitas = insights_service.CATEGORIAS_PREDEFINIDAS['RECEITAS']
    for categoria, config in categorias_receitas.items():
        tipo_icon = "📌" if config['tipo'] == 'fixo' else "🔄"
        st.markdown(f"{tipo_icon} **{categoria}** - {config['tipo'].title()}")
    
    st.markdown("### 🏠 Gastos Fixos")
    categorias_fixos = insights_service.CATEGORIAS_PREDEFINIDAS['GASTOS_FIXOS']
    for categoria, config in categorias_fixos.items():
        st.markdown(f"📌 **{categoria}**")

with col2:
    st.markdown("### 💸 Gastos Variáveis")
    categorias_variaveis = insights_service.CATEGORIAS_PREDEFINIDAS['GASTOS_VARIAVEIS']
    for categoria, config in categorias_variaveis.items():
        st.markdown(f"🔄 **{categoria}**")
    
    st.markdown("### 🎯 Metas")
    categorias_metas = insights_service.CATEGORIAS_PREDEFINIDAS['METAS']
    for categoria, config in categorias_metas.items():
        st.markdown(f"🎯 **{categoria}**")

st.markdown("---")

# Seção 2: Inicialização de Categorias
st.subheader("⚙️ Configuração do Sistema")

col1, col2 = st.columns(2)

with col1:
    if st.button("🚀 Inicializar Categorias Pré-definidas", type="primary"):
        try:
            sucesso = insights_service.inicializar_categorias_predefinidas(user_id)
            if sucesso:
                st.success("✅ Categorias inicializadas com sucesso!")
                st.rerun()
            else:
                st.warning("⚠️ Categorias já existem")
        except Exception as e:
            st.error(f"❌ Erro: {e}")

with col2:
    if st.button("🔄 Resetar Categorias"):
        try:
            # Implementar reset se necessário
            st.info("🔧 Funcionalidade de reset em desenvolvimento")
        except Exception as e:
            st.error(f"❌ Erro: {e}")

st.markdown("---")

# Seção 3: Categorias Personalizadas Atuais
st.subheader("📊 Suas Categorias Personalizadas")

try:
    categorias_personalizadas = categoria_repo.obter_categorias(user_id)
    
    if categorias_personalizadas:
        df_categorias = pd.DataFrame(categorias_personalizadas)
        st.dataframe(
            df_categorias[['descricao', 'categoria', 'created_at']],
            column_config={
                'descricao': 'Descrição',
                'categoria': 'Categoria',
                'created_at': 'Criado em'
            },
            use_container_width=True
        )
    else:
        st.info("📋 Nenhuma categoria personalizada configurada ainda")
        
except Exception as e:
    st.error(f"❌ Erro ao carregar categorias: {e}")

st.markdown("---")

# Seção 4: Adicionar Nova Categoria
st.subheader("➕ Adicionar Nova Categoria Personalizada")

with st.form("nova_categoria"):
    col1, col2 = st.columns(2)
    
    with col1:
        descricao = st.text_input(
            "Descrição/Palavra-chave",
            placeholder="Ex: MERCADO, POSTO, FARMACIA",
            help="Palavra-chave que aparece nas transações"
        )
    
    with col2:
        # Lista de todas as categorias disponíveis
        todas_categorias = []
        for grupo in insights_service.CATEGORIAS_PREDEFINIDAS.values():
            todas_categorias.extend(grupo.keys())
        
        categoria_selecionada = st.selectbox(
            "Categoria",
            options=todas_categorias,
            help="Selecione a categoria para esta palavra-chave"
        )
    
    submitted = st.form_submit_button("💾 Adicionar Categoria")
    
    if submitted:
        if descricao and categoria_selecionada:
            try:
                categoria_repo.criar_categoria(user_id, descricao.upper(), categoria_selecionada)
                st.success(f"✅ Categoria adicionada: '{descricao}' → '{categoria_selecionada}'")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Erro ao adicionar categoria: {e}")
        else:
            st.warning("⚠️ Preencha todos os campos")

st.markdown("---")

# Seção 5: Mapeamento Automático
st.subheader("🤖 Mapeamento Automático")

st.info("""
💡 **Como funciona o mapeamento automático:**

1. **Palavras-chave**: Configure palavras-chave que aparecem frequentemente nas suas transações
2. **Categorização**: Transações com essas palavras serão automaticamente categorizadas
3. **Baseado na planilha**: As categorias seguem o padrão da sua planilha de controle
4. **Aprendizado**: O sistema aprende com suas categorizações manuais

**Exemplo**: Se você adicionar "MERCADO" → "Compra Mensal", todas as transações com "MERCADO" 
na descrição serão automaticamente categorizadas como "Compra Mensal".
""")

st.markdown("---")
st.caption("🏷️ Sistema de categorização baseado na planilha de referência do usuário")
