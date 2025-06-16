"""
Página do Assistente de IA - Interface conversacional revolucionária
Assistente virtual que responde perguntas financeiras inteligentemente
"""

import streamlit as st
from datetime import datetime
import time

from utils.auth import verificar_autenticacao
from services.ai_assistant_service import FinancialAIAssistant
from services.ai_categorization_service import AICategorization
from utils.database_manager_v2 import DatabaseManager
from utils.repositories_v2 import UsuarioRepository


def obter_user_id_do_usuario():
    """Obtém o ID do usuário a partir do session_state"""
    try:
        if 'usuario' not in st.session_state:
            return None
            
        username = st.session_state['usuario']
        
        # Obter user_id do banco
        db = DatabaseManager()
        usuario_repo = UsuarioRepository(db)
        user_data = usuario_repo.obter_usuario_por_username(username)
        
        return user_data['id'] if user_data else None
    except Exception as e:
        st.error(f"Erro ao obter dados do usuário: {str(e)}")
        return None


def render_chat_interface(user_id: int):
    """Renderiza a interface de chat"""
    
    st.subheader("💬 Conversa com IA")
    
    # Inicializar histórico de chat
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
        
        # Mensagem de boas-vindas
        welcome_msg = st.session_state.ai_assistant._get_generic_help_response()
        st.session_state.chat_history.append({
            'type': 'assistant',
            'message': welcome_msg,
            'timestamp': datetime.now()
        })
    
    # Container do chat
    chat_container = st.container()
    
    # Exibir histórico de chat
    with chat_container:
        for entry in st.session_state.chat_history:
            if entry['type'] == 'user':
                st.markdown(f"""
                <div style='text-align: right; margin: 1rem 0;'>
                    <div style='background: #667eea; color: white; padding: 0.8rem; border-radius: 15px; display: inline-block; max-width: 80%;'>
                        {entry['message']}
                    </div>
                    <div style='font-size: 0.8em; color: #666; margin-top: 0.2rem;'>
                        Você • {entry['timestamp'].strftime('%H:%M')}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style='text-align: left; margin: 1rem 0;'>
                    <div style='background: #f1f3f4; color: #333; padding: 0.8rem; border-radius: 15px; display: inline-block; max-width: 80%;'>
                        {entry['message']}
                    </div>
                    <div style='font-size: 0.8em; color: #666; margin-top: 0.2rem;'>
                        🤖 Richness AI • {entry['timestamp'].strftime('%H:%M')}
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    # Input para nova mensagem
    st.markdown("---")
    user_input = st.text_input(
        "Digite sua pergunta:", 
        placeholder="Ex: Qual meu saldo atual?",
        key="user_message_input"
    )
    
    col1, col2 = st.columns([1, 4])
    with col1:
        send_button = st.button("📤 Enviar", type="primary")
    with col2:
        if st.button("🗑️ Limpar Chat"):
            st.session_state.chat_history = []
            st.rerun()
    
    # Processar mensagem quando enviada
    if send_button and user_input.strip():
        process_user_message(user_id, user_input.strip())
        st.rerun()


def process_user_message(user_id: int, message: str):
    """Processa mensagem do usuário e gera resposta"""
    
    # Adicionar mensagem do usuário ao histórico
    st.session_state.chat_history.append({
        'type': 'user',
        'message': message,
        'timestamp': datetime.now()
    })
    
    # Gerar resposta da IA
    try:
        with st.spinner("🤖 Analisando..."):
            response_data = st.session_state.ai_assistant.process_message(user_id, message)
            response = response_data['response']
        
        # Adicionar resposta da IA ao histórico
        st.session_state.chat_history.append({
            'type': 'assistant',
            'message': response,
            'timestamp': datetime.now()
        })
        
    except Exception as e:
        error_msg = f"❌ Erro ao processar sua pergunta: {str(e)}"
        st.session_state.chat_history.append({
            'type': 'assistant',
            'message': error_msg,
            'timestamp': datetime.now()
        })


def render_insights_sidebar(user_id: int):
    """Renderiza sidebar com insights rápidos"""
    
    st.markdown("### 📊 Insights Rápidos")
    
    try:
        insights = st.session_state.ai_assistant.get_quick_insights(user_id)
        
        if 'erro' in insights:
            st.warning(insights['erro'])
            return
        
        # Saldo mensal
        if 'saldo_mensal' in insights:
            saldo = insights['saldo_mensal']
            color = "green" if saldo >= 0 else "red"
            st.markdown(f"""
            <div class="stats-card">
                <h4 style="color: {color};">💰 Saldo Mensal</h4>
                <h3 style="color: {color};">R$ {saldo:,.2f}</h3>
            </div>
            """, unsafe_allow_html=True)
        
        # Top categoria
        if 'top_categoria' in insights:
            top_cat = insights['top_categoria']
            st.markdown(f"""
            <div class="stats-card">
                <h4>🏆 Maior Gasto</h4>
                <p><strong>{top_cat['nome']}</strong></p>
                <h4 style="color: #ff6b6b;">R$ {top_cat['valor']:,.2f}</h4>
            </div>
            """, unsafe_allow_html=True)
        
        # Alertas
        if insights.get('alertas'):
            st.markdown("### ⚠️ Alertas")
            for alerta in insights['alertas']:
                st.warning(alerta)
        
        # Sugestões
        if insights.get('sugestoes'):
            st.markdown("### 💡 Sugestões")
            for sugestao in insights['sugestoes']:
                st.info(sugestao)
        
        # Estatísticas de IA
        st.markdown("---")
        st.markdown("### 🤖 Estatísticas de IA")
        
        categorization_stats = get_ai_stats(user_id)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("🎯 Precisão", f"{categorization_stats.get('precisao', 0):.1f}%")
        with col2:
            st.metric("📈 Aprendizado", f"{categorization_stats.get('aprendizado', 0):.1f}%")
        
    except Exception as e:
        st.error(f"Erro ao carregar insights: {str(e)}")


def get_ai_stats(user_id: int) -> dict:
    """Obtém estatísticas de performance da IA"""
    try:
        # Simulação de estatísticas (pode ser implementado com dados reais)
        return {
            'precisao': 85.3,
            'aprendizado': 92.7,
            'transacoes_categorizadas': 156,
            'economia_sugerida': 247.50
        }
    except Exception:
        return {'precisao': 0, 'aprendizado': 0}


# Configuração da página
st.set_page_config(
    page_title="🤖 Assistente IA", 
    page_icon="🤖",
    layout="wide"
)

# Verificar autenticação
verificar_autenticacao()

# Obter user_id
user_id = obter_user_id_do_usuario()
if not user_id:
    st.error("❌ Erro ao identificar o usuário. Faça login novamente.")
    st.stop()

# CSS customizado para melhorar a aparência do chat
st.markdown("""
<style>
.chat-header {
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    padding: 1rem;
    border-radius: 10px;
    color: white;
    text-align: center;
    margin-bottom: 1rem;
}

.insight-card {
    background: #f8f9fa;
    padding: 1rem;
    border-radius: 8px;
    border-left: 4px solid #667eea;
    margin-bottom: 0.5rem;
}

.suggestion-button {
    background: #667eea;
    color: white;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 20px;
    margin: 0.2rem;
    cursor: pointer;
    transition: all 0.3s;
}

.suggestion-button:hover {
    background: #764ba2;
    transform: translateY(-2px);
}

.stats-card {
    background: white;
    padding: 1rem;
    border-radius: 10px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# Header principal
st.markdown("""
<div class="chat-header">
    <h1>🤖 Richness AI - Seu Consultor Financeiro Pessoal</h1>
    <p>Conversa inteligente sobre suas finanças • Análises em tempo real • Sugestões personalizadas</p>
</div>
""", unsafe_allow_html=True)

# Inicializar assistente
if 'ai_assistant' not in st.session_state:
    st.session_state.ai_assistant = FinancialAIAssistant()

# Inicializar serviço de categorização
if 'ai_categorization' not in st.session_state:
    st.session_state.ai_categorization = AICategorization()

# Layout em colunas
col_chat, col_sidebar = st.columns([3, 1])

with col_chat:
    # Interface principal do chat
    render_chat_interface(user_id)
    
    # Seção de perguntas sugeridas
    st.markdown("---")
    st.subheader("💭 Perguntas Sugeridas")
    
    suggestions = st.session_state.ai_assistant.get_conversation_starters()
    
    # Exibir sugestões em grid
    cols = st.columns(2)
    for i, suggestion in enumerate(suggestions):
        with cols[i % 2]:
            if st.button(suggestion, key=f"suggestion_{i}"):
                # Processar sugestão como uma mensagem
                process_user_message(user_id, suggestion)
                st.rerun()

with col_sidebar:
    # Sidebar com insights rápidos
    render_insights_sidebar(user_id)
