"""
Página de Insights Financeiros - Demonstração das funcionalidades implementadas
"""

import streamlit as st
import pandas as pd
from datetime import datetime

# Configurações da página
st.set_page_config(
    page_title="Richness - Insights Financeiros",
    page_icon="📊",
    layout="wide"
)

# Verificar autenticação
if 'authenticated' not in st.session_state or not st.session_state['authenticated']:
    st.error("🔒 Acesso negado. Faça login primeiro.")
    st.stop()

# Importações do sistema
from utils.database_manager_v2 import DatabaseManager
from utils.repositories_v2 import UsuarioRepository
from services.insights_service_v2 import InsightsServiceV2
from componentes.insights_dashboard import exibir_insights_dashboard

st.title("📊 Insights Financeiros Avançados")
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

# Exibir dashboard principal de insights
try:
    exibir_insights_dashboard(user_id)
except Exception as e:
    st.error(f"❌ Erro ao carregar insights: {str(e)}")

st.markdown("---")

# Seção de configurações e testes
with st.expander("🔧 Configurações e Testes", expanded=False):
    st.subheader("Funcionalidades Implementadas")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### ✅ Funcionalidades Ativas")
        st.write("- 💰 Cálculo de Valor Restante Mensal")
        st.write("- 📊 Análise de Gastos por Categoria")
        st.write("- 🚨 Sistema de Alertas Financeiros")
        st.write("- 💡 Sugestões de Otimização")
        st.write("- 📈 Comparativo Mensal")
        st.write("- 🏷️ Categorias Pré-definidas")
    
    with col2:
        st.markdown("### 🎯 Baseado na Planilha")
        st.write("- Receitas: Salário, Investimentos, Crédito")
        st.write("- Gastos Fixos: Casa, Energia, Água, Internet")
        st.write("- Gastos Variáveis: Cartão, Gasolina, Viagem")
        st.write("- Metas: Poupança e planejamento")
        st.write("- Alertas inteligentes de orçamento")
        st.write("- Insights automáticos de economia")
    
    st.markdown("### 🧪 Testar Funcionalidades")
    
    if st.button("🔄 Inicializar Categorias Pré-definidas"):
        try:
            insights_service = InsightsServiceV2()
            sucesso = insights_service.inicializar_categorias_predefinidas(user_id)
            if sucesso:
                st.success("✅ Categorias inicializadas com sucesso!")
            else:
                st.warning("⚠️ Categorias já existem ou erro na inicialização")
        except Exception as e:
            st.error(f"❌ Erro: {e}")
    
    if st.button("📊 Testar Análise de Gastos"):
        try:
            insights_service = InsightsServiceV2()
            analise = insights_service.analisar_gastos_por_categoria(user_id, 3)
            st.json(analise)
        except Exception as e:
            st.error(f"❌ Erro: {e}")
    
    if st.button("🚨 Testar Alertas"):
        try:
            insights_service = InsightsServiceV2()
            alertas = insights_service.detectar_alertas_financeiros(user_id)
            if alertas:
                for alerta in alertas:
                    st.warning(f"{alerta['titulo']}: {alerta['mensagem']}")
            else:
                st.success("✅ Nenhum alerta no momento")
        except Exception as e:
            st.error(f"❌ Erro: {e}")

st.markdown("---")
st.caption("💡 Esta página demonstra as funcionalidades de insights implementadas baseadas na planilha de referência")
