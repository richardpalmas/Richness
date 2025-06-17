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
    try:
        st.subheader("🤖 Conversa com IA")
        # Inicializar histórico de chat
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
            
            # Mensagem de boas-vindas personalizada
            personalidade = st.session_state.get('ai_personality', 'clara')
            welcome_msg = st.session_state.ai_assistant._get_generic_help_response()
            welcome_msg = st.session_state.ai_assistant._apply_personality_style(welcome_msg, personalidade)
            
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
            send_button = st.button("💬 Enviar", type="primary")
        with col2:
            if st.button("🗑️ Limpar Chat"):
                st.session_state.chat_history = []
                st.rerun()
        
        # Processar mensagem quando enviada
        if send_button and user_input.strip():
            process_user_message(user_id, user_input.strip())
            st.rerun()
    except Exception as e:
        st.error(f"Erro na interface de chat: {str(e)}")


def process_user_message(user_id: int, message: str):
    """Processa mensagem do usuário e gera resposta"""
    try:
        # Adicionar mensagem do usuário ao histórico
        st.session_state.chat_history.append({
            'type': 'user',
            'message': message,
            'timestamp': datetime.now()
        })
        
        # Gerar resposta da IA
        with st.spinner("🤖 Analisando..."):
            # Obter personalidade selecionada
            personalidade = st.session_state.get('ai_personality', 'clara')
            
            # Processar mensagem com personalidade
            response_data = st.session_state.ai_assistant.process_message_with_personality(
                user_id, message, personalidade
            )
            response = response_data['response']
        
        # Adicionar resposta da IA ao histórico
        st.session_state.chat_history.append({
            'type': 'assistant',
            'message': response,
            'timestamp': datetime.now()
        })
        
    except Exception as e:
        error_msg = f"⚠️ Erro ao processar sua pergunta: {str(e)}"
        st.session_state.chat_history.append({
            'type': 'assistant',
            'message': error_msg,
            'timestamp': datetime.now()
        })


def render_insights_sidebar(user_id: int):
    """Renderiza sidebar com insights rápidos"""
    try:
        # CSS para cards visuais melhorados
        st.markdown("""
        <style>
        .insight-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            border-radius: 15px;
            margin: 10px 0;
            color: white;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            text-align: center;
        }
        .insight-card-positive {
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            padding: 20px;
            border-radius: 15px;
            margin: 10px 0;
            color: white;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            text-align: center;
        }
        .insight-card-negative {
            background: linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%);
            padding: 20px;
            border-radius: 15px;
            margin: 10px 0;
            color: white;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            text-align: center;
        }
        .insight-value {
            font-size: 28px;
            font-weight: bold;
            margin: 10px 0;
        }
        .insight-label {
            font-size: 16px;
            margin-bottom: 5px;
            opacity: 0.9;
        }
        .alert-box {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            padding: 15px;
            border-radius: 10px;
            margin: 10px 0;
            color: #856404;
        }
        .suggestion-box {
            background: linear-gradient(135deg, #d1ecf1 0%, #e8f4f8 100%);
            border: 1px solid #bee5eb;
            padding: 15px;
            border-radius: 10px;
            margin: 10px 0;
            color: #0c5460;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            line-height: 1.5;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown("### 📊 Insights Rápidos")
        
        try:
            insights = st.session_state.ai_assistant.get_quick_insights(user_id)
            
            if 'erro' in insights:
                st.error("⚠️ Não foi possível carregar os insights")
                return
            
            # Saldo mensal com card visual melhorado
            if 'saldo_mensal' in insights:
                saldo = insights['saldo_mensal']
                card_class = "insight-card-positive" if saldo >= 0 else "insight-card-negative"
                icon = "💰" if saldo >= 0 else "⚠️"
                status = "Sobra Mensal" if saldo >= 0 else "Déficit Mensal"
                
                st.markdown(f"""
                <div class="{card_class}">
                    <div class="insight-label">{icon} {status}</div>
                    <div class="insight-value">R$ {abs(saldo):,.2f}</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Top categoria com visual melhorado
            if 'top_categoria' in insights:
                top_cat = insights['top_categoria']
                st.markdown(f"""
                <div class="insight-card">
                    <div class="insight-label">📈 Maior Gasto</div>
                    <div style="font-size: 18px; margin: 10px 0; font-weight: bold;">{top_cat['nome']}</div>
                    <div class="insight-value">R$ {top_cat['valor']:,.2f}</div>
                </div>
                """, unsafe_allow_html=True)
                
            # Alertas com estilo melhorado
            if insights.get('alertas'):
                st.markdown("#### ⚠️ Alertas Importantes")
                for alerta in insights['alertas'][:2]:  # Limitar a 2 alertas
                    st.markdown(f"""
                    <div class="alert-box">
                        <strong>⚠️</strong> {alerta}
                    </div>
                    """, unsafe_allow_html=True)
            
            # Sugestões com estilo melhorado
            if insights.get('sugestoes'):
                st.markdown("#### 💡 Dicas Inteligentes")
                for sugestao in insights['sugestoes'][:2]:  # Limitar a 2 sugestões
                    titulo, descricao, economia, dificuldade = formatar_dica_inteligente(sugestao)
                    
                    # Ícone baseado na dificuldade
                    dificuldade_icon = {
                        'facil': '🟢',
                        'media': '🟡', 
                        'dificil': '🔴'
                    }.get(dificuldade, '🟡')
                    
                    # Formatar economia
                    economia_display = ""
                    if economia > 0:
                        economia_display = f"<br><small><strong>💰 Economia potencial:</strong> R$ {economia:,.2f}</small>"
                    
                    st.markdown(f"""
                    <div class="suggestion-box">
                        <div style="display: flex; align-items: center; margin-bottom: 8px;">
                            <strong>💡 {titulo}</strong>
                            <span style="margin-left: auto;">{dificuldade_icon}</span>
                        </div>
                        <div style="margin-bottom: 5px;">{descricao}</div>
                        {economia_display}
                    </div>
                    """, unsafe_allow_html=True)
                    
            # Separador visual
            st.markdown("---")
            
            # Estatísticas de IA com métricas visuais
            st.markdown("#### 🤖 Estatísticas de IA")
            
            categorization_stats = get_ai_stats(user_id)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("🎯 Precisão", f"{categorization_stats.get('precisao', 0):.1f}%")
            with col2:
                st.metric("📈 Aprendizado", f"{categorization_stats.get('aprendizado', 0):.1f}%")
            
        except Exception as e:
            st.error(f"Erro ao carregar insights: {str(e)}")
            
    except Exception as e:
        st.error(f"Erro ao renderizar insights: {str(e)}")


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


def formatar_dica_inteligente(sugestao) -> tuple:
    """Formata uma dica inteligente para exibição amigável"""
    if isinstance(sugestao, dict):
        titulo = sugestao.get('titulo', 'Dica Financeira')
        descricao = sugestao.get('descricao', '')
        economia = sugestao.get('economia_potencial', 0)
        dificuldade = sugestao.get('dificuldade', 'media')
        
        # Limpar e formatar a descrição
        if 'R$' not in descricao and economia > 0:
            descricao = descricao.replace(f"R$ {economia:,.2f}", f"R$ {economia:,.2f}")
        
        return titulo, descricao, economia, dificuldade
    else:
        # Para strings simples
        return str(sugestao), "", 0, "media"


def render_personality_selector():
    """Renderiza o seletor de personalidade da IA"""
    try:
        # Definir opções de personalidade
        personalidade_opcoes = {
            "clara": "🌟 Mais clara, acolhedora e engraçada",
            "tecnica": "📊 Mais técnica e formal", 
            "durona": "💪 Mais durona e informal"
        }
        
        st.markdown("### 🎭 Personalidade da IA")
        
        # Obter personalidade atual
        personalidade_anterior = st.session_state.get('ai_personality', 'clara')
        
        personalidade_selecionada = st.selectbox(
            "Como você gostaria que a IA se comunique?",
            options=list(personalidade_opcoes.keys()),
            format_func=lambda x: personalidade_opcoes[x],
            index=list(personalidade_opcoes.keys()).index(personalidade_anterior),
            key="personality_selector",
            help="Escolha o estilo de comunicação que você prefere para suas análises e respostas"
        )
        
        # Verificar se houve mudança na personalidade
        if personalidade_selecionada != personalidade_anterior:
            st.session_state['ai_personality'] = personalidade_selecionada
            # Funcionalidade de atualização movida para inline
            st.rerun()
        
        # Armazenar personalidade no session_state
        st.session_state['ai_personality'] = personalidade_selecionada
        
        # Mostrar descrição da personalidade selecionada
        personality_descriptions = {
            "clara": "💬 Comunicação amigável e descontraída com uso de emojis",
            "tecnica": "📊 Linguagem técnica e precisa com terminologia financeira",
            "durona": "🎯 Comunicação direta e sem rodeios, mais informal"
        }
        
        st.markdown(f"""
        <div style="background: #00008B; padding: 10px; border-radius: 8px; margin: 10px 0;">
            <small>{personality_descriptions[personalidade_selecionada]}</small>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
    except Exception as e:
        st.error(f"Erro ao renderizar seletor de personalidade: {str(e)}")


# Página principal
def main():
    try:
        # Verificar autenticação
        if not verificar_autenticacao():
            st.warning("🔒 Faça login para acessar essa página")
            return
        
        # Inicializar FinancialAIAssistant se ainda não existir
        if 'ai_assistant' not in st.session_state:
            st.session_state.ai_assistant = FinancialAIAssistant()
        
        # Obter ID do usuário
        user_id = obter_user_id_do_usuario()
        if not user_id:
            st.error("❌ Não foi possível obter os dados do usuário")
            return
        
        # Configurar layout da página
        st.title("🤖 Assistente IA")
        
        # Dividir em duas colunas principais
        col1, col2 = st.columns([2.5, 1])
        
        with col1:
            # Interface de chat principal
            render_chat_interface(user_id)
            
        with col2:
            # Seletor de personalidade no sidebar
            render_personality_selector()
            
            # Insights no sidebar
            render_insights_sidebar(user_id)
            
    except Exception as e:
        st.error(f"Erro ao carregar a página: {str(e)}")
        st.error("Por favor, recarregue a página ou contate o suporte se o problema persistir.")


if __name__ == "__main__":
    main()
