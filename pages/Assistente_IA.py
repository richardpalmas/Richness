"""
Página do Assistente de IA - Interface conversacional revolucionária
Assistente virtual que responde perguntas financeiras inteligentemente
"""

import streamlit as st
from datetime import datetime
import time
import pandas as pd

from utils.auth import verificar_autenticacao
from services.ai_assistant_service import FinancialAIAssistant
from services.ai_categorization_service import AICategorization
from utils.database_manager_v2 import DatabaseManager
from utils.repositories_v2 import UsuarioRepository, TransacaoRepository
from utils.filtros import filtro_data


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
        # Criar abas de menu para a conversa com IA e Gerenciar Perfis IA
        tabs = st.tabs(["💬 Conversa com IA", "👤 Gerenciar Perfis IA"])
        with tabs[0]:
            # Exibir período selecionado acima do chat
            data_inicio = st.session_state.get('ia_periodo_inicio', '')
            data_fim = st.session_state.get('ia_periodo_fim', '')
            if data_inicio and data_fim:
                st.info(f"🗓️ Período selecionado: {data_inicio} a {data_fim}")
            else:
                st.info("🗓️ Período: Todas as transações disponíveis")
            # Inicializar histórico de chat
            if 'chat_history' not in st.session_state:
                st.session_state.chat_history = []
            # Inicializar input controlado
            if 'user_message_input' not in st.session_state:
                st.session_state.user_message_input = ''
            # Exibir histórico de chat
            for message in st.session_state.chat_history:
                if message["role"] == "user":
                    with st.chat_message("user"):
                        st.write(message["content"])
                else:
                    with st.chat_message("assistant", avatar="🤖"):
                        st.write(message["content"])
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
                    st.session_state.user_message_input = ''
                    st.rerun()
            # Processar mensagem quando enviada
            if send_button and user_input.strip():
                process_user_message(user_id, user_input.strip())
        with tabs[1]:
            st.markdown("### 👤 Gerenciar Perfis IA")
            # Card 1: Clara e Acolhedora
            col_img1, col_details1 = st.columns([1, 2])

            if 'show_perfil_amigavel' not in st.session_state:
                st.session_state.show_perfil_amigavel = False
            def toggle_perfil_amigavel():
                st.session_state.show_perfil_amigavel = True
                st.session_state.show_editar_caracteristicas_amigavel = False

            def editar_caracteristicas_amigavel():
                st.session_state.show_perfil_amigavel = True
                st.session_state.show_editar_caracteristicas_amigavel = True

            with col_img1:
                st.image(
                    "imgs/perfil_amigavel_fem.png",
                    width=310,
                    caption="Clara e Acolhedora"
                )
                if st.button("Ver detalhes do perfil Clara e Acolhedora", key="btn_perfil_amigavel", help="Clique na imagem para ver detalhes do perfil", use_container_width=True):
                    toggle_perfil_amigavel()
                if st.button("Editar Características", key="btn_editar_caracteristicas_amigavel", use_container_width=True):
                    editar_caracteristicas_amigavel()

            with col_details1:
                if st.session_state.show_perfil_amigavel:
                    if st.session_state.show_editar_caracteristicas_amigavel:
                        st.markdown("#### ✏️ Personalize os traços deste perfil")
                        if 'perfil_amigavel_parametros' not in st.session_state:
                            st.session_state.perfil_amigavel_parametros = {
                                'formalidade': 'Informal',
                                'emojis': 'Alto',
                                'tom': 'Muito Amigável',
                                'foco': 'Motivacional'
                            }
                        with st.form("form_editar_perfil_amigavel"):
                            formalidade = st.selectbox(
                                "Formalidade",
                                ["Informal", "Neutro", "Formal"],
                                index=["Informal", "Neutro", "Formal"].index(st.session_state.perfil_amigavel_parametros['formalidade'])
                            )
                            emojis = st.selectbox(
                                "Uso de Emojis",
                                ["Nenhum", "Moderado", "Alto"],
                                index=["Nenhum", "Moderado", "Alto"].index(st.session_state.perfil_amigavel_parametros['emojis'])
                            )
                            tom = st.selectbox(
                                "Tom",
                                ["Amigável", "Muito Amigável", "Melhor Amiga"],
                                index=["Amigável", "Muito Amigável", "Melhor Amiga"].index(st.session_state.perfil_amigavel_parametros['tom'])
                            )
                            foco = st.selectbox(
                                "Foco",
                                ["Neutro", "Motivacional", "Voa Meu Bem"],
                                index=["Neutro", "Motivacional", "Voa Meu Bem"].index(st.session_state.perfil_amigavel_parametros['foco'])
                            )
                            submit = st.form_submit_button("Salvar alterações")
                            if submit:
                                st.session_state.perfil_amigavel_parametros = {
                                    'formalidade': formalidade,
                                    'emojis': emojis,
                                    'tom': tom,
                                    'foco': foco
                                }
                                st.success("Parâmetros atualizados com sucesso!")
                    else:
                        st.markdown("""
                            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 24px; border-radius: 16px; color: #fff; box-shadow: 0 4px 18px rgba(0,0,0,0.10);'>
                                <h3 style='margin-top:0;'>🌟 Perfil: Clara e Acolhedora</h3>
                                <ul style='font-size: 16px;'>
                                    <li>Comunicação leve, positiva e empática</li>
                                    <li>Uso de emojis e linguagem acessível</li>
                                    <li>Foco em motivar e acolher o usuário</li>
                                    <li>Respostas descontraídas e amigáveis</li>
                                </ul>
                                <p style='margin-top: 18px; font-size: 15px; color: #e0e0e0;'>
                                    <b>Descrição:</b> Ideal para quem busca uma experiência acolhedora, com dicas e orientações de forma leve e motivacional.
                                </p>
                            </div>
                        """, unsafe_allow_html=True)

            st.markdown("---")
            # Card 2: Técnico e Formal
            col_img2, col_details2 = st.columns([1, 2])

            if 'show_perfil_tecnico' not in st.session_state:
                st.session_state.show_perfil_tecnico = False
            if 'show_editar_caracteristicas_tecnico' not in st.session_state:
                st.session_state.show_editar_caracteristicas_tecnico = False
            def toggle_perfil_tecnico():
                st.session_state.show_perfil_tecnico = True
                st.session_state.show_editar_caracteristicas_tecnico = False

            def editar_caracteristicas_tecnico():
                st.session_state.show_perfil_tecnico = True
                st.session_state.show_editar_caracteristicas_tecnico = True

            with col_img2:
                st.image(
                    "imgs/perfil_tecnico_masc.png",
                    width=310,
                    caption="Técnico e Formal"
                )
                if st.button("Ver detalhes do perfil Técnico e Formal", key="btn_perfil_tecnico", help="Clique na imagem para ver detalhes do perfil", use_container_width=True):
                    toggle_perfil_tecnico()
                if st.button("Editar Características", key="btn_editar_caracteristicas_tecnico", use_container_width=True):
                    editar_caracteristicas_tecnico()

            with col_details2:
                if st.session_state.show_perfil_tecnico:
                    if st.session_state.show_editar_caracteristicas_tecnico:
                        st.markdown("#### ✏️ Personalize os traços deste perfil")
                        if 'perfil_tecnico_parametros' not in st.session_state:
                            st.session_state.perfil_tecnico_parametros = {
                                'formalidade': 'Formal',
                                'emojis': 'Nenhum',
                                'tom': 'Objetivo',
                                'foco': 'Analítico'
                            }
                        with st.form("form_editar_perfil_tecnico"):
                            formalidade = st.selectbox(
                                "Formalidade",
                                ["Informal", "Neutro", "Formal"],
                                index=["Informal", "Neutro", "Formal"].index(st.session_state.perfil_tecnico_parametros['formalidade'])
                            )
                            emojis = st.selectbox(
                                "Uso de Emojis",
                                ["Nenhum", "Moderado", "Alto"],
                                index=["Nenhum", "Moderado", "Alto"].index(st.session_state.perfil_tecnico_parametros['emojis'])
                            )
                            tom = st.selectbox(
                                "Tom",
                                ["Objetivo", "Preciso", "Formal"],
                                index=["Objetivo", "Preciso", "Formal"].index(st.session_state.perfil_tecnico_parametros['tom'])
                            )
                            foco = st.selectbox(
                                "Foco",
                                ["Analítico", "Neutro", "Recomendação"],
                                index=["Analítico", "Neutro", "Recomendação"].index(st.session_state.perfil_tecnico_parametros['foco'])
                            )
                            submit = st.form_submit_button("Salvar alterações")
                            if submit:
                                st.session_state.perfil_tecnico_parametros = {
                                    'formalidade': formalidade,
                                    'emojis': emojis,
                                    'tom': tom,
                                    'foco': foco
                                }
                                st.success("Parâmetros atualizados com sucesso!")
                    else:
                        st.markdown("""
                            <div style='background: linear-gradient(135deg, #232526 0%, #414345 100%); padding: 24px; border-radius: 16px; color: #fff; box-shadow: 0 4px 18px rgba(0,0,0,0.10);'>
                                <h3 style='margin-top:0;'>📊 Perfil: Técnico e Formal</h3>
                                <ul style='font-size: 16px;'>
                                    <li>Comunicação objetiva, precisa e sem rodeios</li>
                                    <li>Uso de termos técnicos e linguagem formal</li>
                                    <li>Foco em dados, análises e recomendações fundamentadas</li>
                                    <li>Respostas detalhadas e baseadas em evidências</li>
                                </ul>
                                <p style='margin-top: 18px; font-size: 15px; color: #e0e0e0;'>
                                    <b>Descrição:</b> Ideal para quem prefere uma abordagem analítica, com explicações técnicas e foco em resultados financeiros.</p>
                            </div>
                        """, unsafe_allow_html=True)

            # Card 3: Durão e Informal
            st.markdown("---")
            col_img3, col_details3 = st.columns([1, 2])

            if 'show_perfil_durao' not in st.session_state:
                st.session_state.show_perfil_durao = False
            if 'show_editar_caracteristicas_durao' not in st.session_state:
                st.session_state.show_editar_caracteristicas_durao = False
            def toggle_perfil_durao():
                st.session_state.show_perfil_durao = True
                st.session_state.show_editar_caracteristicas_durao = False

            def editar_caracteristicas_durao():
                st.session_state.show_perfil_durao = True
                st.session_state.show_editar_caracteristicas_durao = True

            with col_img3:
                st.image(
                    "imgs/perfil_durao_fem.png",
                    width=310,
                    caption="Durona e Informal"
                )
                if st.button("Ver detalhes do perfil Durão e Informal", key="btn_perfil_durao", help="Clique na imagem para ver detalhes do perfil", use_container_width=True):
                    toggle_perfil_durao()
                if st.button("Editar Características", key="btn_editar_caracteristicas_durao", use_container_width=True):
                    editar_caracteristicas_durao()

            with col_details3:
                if st.session_state.show_perfil_durao:
                    if st.session_state.show_editar_caracteristicas_durao:
                        st.markdown("#### ✏️ Personalize os traços deste perfil")
                        if 'perfil_durao_parametros' not in st.session_state:
                            st.session_state.perfil_durao_parametros = {
                                'formalidade': 'Informal',
                                'emojis': 'Nenhum',
                                'tom': 'Durão',
                                'foco': 'Disciplina'
                            }
                        with st.form("form_editar_perfil_durao"):
                            formalidade = st.selectbox(
                                "Formalidade",
                                ["Informal", "Neutro", "Formal"],
                                index=["Informal", "Neutro", "Formal"].index(st.session_state.perfil_durao_parametros['formalidade'])
                            )
                            emojis = st.selectbox(
                                "Uso de Emojis",
                                ["Nenhum", "Moderado", "Alto"],
                                index=["Nenhum", "Moderado", "Alto"].index(st.session_state.perfil_durao_parametros['emojis'])
                            )
                            tom = st.selectbox(
                                "Tom",
                                ["Durão", "Direto", "Motivacional"],
                                index=["Durão", "Direto", "Motivacional"].index(st.session_state.perfil_durao_parametros['tom'])
                            )
                            foco = st.selectbox(
                                "Foco",
                                ["Disciplina", "Resultados", "Cobrança"],
                                index=["Disciplina", "Resultados", "Cobrança"].index(st.session_state.perfil_durao_parametros['foco'])
                            )
                            submit = st.form_submit_button("Salvar alterações")
                            if submit:
                                st.session_state.perfil_durao_parametros = {
                                    'formalidade': formalidade,
                                    'emojis': emojis,
                                    'tom': tom,
                                    'foco': foco
                                }
                                st.success("Parâmetros atualizados com sucesso!")
                    else:
                        st.markdown("""
                            <div style='background: linear-gradient(135deg, #b31217 0%, #e52d27 100%); padding: 24px; border-radius: 16px; color: #fff; box-shadow: 0 4px 18px rgba(0,0,0,0.10);'>
                                <h3 style='margin-top:0;'>💪 Perfil: Durão e Informal</h3>
                                <ul style='font-size: 16px;'>
                                    <li>Comunicação direta, sem rodeios e com tom firme</li>
                                    <li>Uso de expressões informais e objetivas</li>
                                    <li>Foco em disciplina, cobrança e resultados</li>
                                    <li>Respostas rápidas e motivacionais, sem "passar a mão na cabeça"</li>
                                </ul>
                                <p style='margin-top: 18px; font-size: 15px; color: #e0e0e0;'>
                                    <b>Descrição:</b> Ideal para quem gosta de uma abordagem mais dura, com cobranças e incentivos diretos para alcançar metas financeiras.</p>
                            </div>
                        """, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Erro na interface de chat: {str(e)}")


def process_user_message(user_id: int, message: str):
    """Processa mensagem do usuário e gera resposta"""
    try:
        st.session_state.chat_history.append({
            'role': 'user',
            'content': message,
            'timestamp': datetime.now()
        })
        with st.spinner("🤖 Analisando..."):
            personalidade = st.session_state.get('ai_personality', 'clara')
            data_inicio = st.session_state.get('ia_periodo_inicio', '') or ''
            data_fim = st.session_state.get('ia_periodo_fim', '') or ''
            qtd_transacoes = st.session_state.get('ia_qtd_transacoes', 50)
            response_data = st.session_state.ai_assistant.process_message_with_personality(
                user_id, message, personalidade, data_inicio, data_fim, qtd_transacoes
            )
            response = response_data['response']
        st.session_state.chat_history.append({
            'role': 'assistant',
            'content': response,
            'timestamp': datetime.now()
        })
    except Exception as e:
        st.error(f"Erro na interface de chat: {str(e)}")


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
            user_id = obter_user_id_do_usuario() if 'obter_user_id_do_usuario' in globals() else None
            st.rerun()
        
        # Mostrar descrição da personalidade selecionada
        personality_descriptions = {
            "clara": "💬 Comunicação amigável e descontraída com uso de emojis",
            "tecnica": "📊 Linguagem técnica e precisa com terminologia financeira",
            "durona": "🎯 Comunicação direta e sem rodeios, mais informal"
        }
        
        st.markdown(f"""
        <div style=\"background: #00008B; padding: 10px; border-radius: 8px; margin: 10px 0;\">
            <small>{personality_descriptions[personalidade_selecionada]}</small>
        </div>
        """, unsafe_allow_html=True)

        # Exemplos de resposta para cada personalidade (balão de fala)
        exemplos = {
            "clara": "Oi! 😊 Seu saldo está positivo este mês, parabéns! Se precisar de dicas para economizar ainda mais, é só perguntar! 💡",
            "tecnica": "De acordo com os dados fornecidos, seu saldo mensal é positivo. Recomenda-se manter a disciplina financeira para potencializar seus investimentos.",
            "durona": "Olha, seu saldo tá no azul. Mas não vacila: continue controlando os gastos se quiser ver resultado de verdade! 💪"
        }
        st.markdown("<div style='margin-top: 10px; margin-bottom: 10px;'><b>Exemplo de resposta:</b></div>", unsafe_allow_html=True)
        for key, exemplo in exemplos.items():
            icone = personalidade_opcoes[key].split()[0]
            st.markdown(f"""
            <div style='display: flex; align-items: flex-start; margin-bottom: 8px;'>
                <div style='font-size: 22px; margin-right: 8px;'>{icone}</div>
                <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 16px; padding: 10px 16px; max-width: 320px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); font-size: 15px; color: white;'>
                    <span style='font-weight: 500;'>{key.capitalize()}:</span> {exemplo}
                </div>
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
        
        # --- Filtro de período na sidebar ---
        st.sidebar.header("🗓️ Período de Referência para a IA")
        db = DatabaseManager()
        transacao_repo = TransacaoRepository(db)
        df_transacoes = transacao_repo.obter_transacoes_periodo(user_id, '1900-01-01', '2100-12-31')
        if not df_transacoes.empty:
            df_transacoes['Data'] = pd.to_datetime(df_transacoes['data'])
            data_inicio, data_fim = filtro_data(df_transacoes, key_prefix="ia")
            st.session_state['ia_periodo_inicio'] = data_inicio
            st.session_state['ia_periodo_fim'] = data_fim
        else:
            st.session_state['ia_periodo_inicio'] = None
            st.session_state['ia_periodo_fim'] = None
        # --- Seletor de quantidade de transações ---
        st.sidebar.markdown("### 📋 Quantidade de Transações para IA")
        # Filtrar transações do período selecionado
        if st.session_state['ia_periodo_inicio'] and st.session_state['ia_periodo_fim']:
            df_periodo = df_transacoes[(df_transacoes['Data'] >= pd.to_datetime(st.session_state['ia_periodo_inicio'])) & (df_transacoes['Data'] <= pd.to_datetime(st.session_state['ia_periodo_fim']))]
        else:
            df_periodo = df_transacoes
        total_disponiveis = len(df_periodo)
        valor_padrao = 50 if total_disponiveis > 50 else total_disponiveis
        qtd = st.sidebar.slider(
            "Quantas transações enviar para a IA?",
            min_value=1,
            max_value=total_disponiveis if total_disponiveis > 0 else 1,
            value=valor_padrao,
            step=1,
            help="Quanto maior o número, mais contexto a IA terá, mas pode aumentar o custo de tokenização e impactar a performance."
        )
        st.session_state['ia_qtd_transacoes'] = qtd
        if qtd > 50:
            st.sidebar.info("⚠️ Você selecionou mais de 50 transações. Isso pode aumentar o custo de tokenização e impactar a performance da IA.")
        # --- Fim do seletor ---
        
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
