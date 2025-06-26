"""
Página do Assistente de IA - Interface conversacional revolucionária
Assistente virtual que responde perguntas financeiras inteligentemente
"""

import streamlit as st
from datetime import datetime
import time
import pandas as pd
from typing import Optional
import json
import os

from utils.auth import verificar_autenticacao
from services.ai_assistant_service import FinancialAIAssistant
from services.ai_categorization_service import AICategorization
from utils.database_manager_v2 import DatabaseManager
from utils.repositories_v2 import UsuarioRepository, TransacaoRepository, PersonalidadeIARepository
from utils.filtros import filtro_data
from componentes.profile_pic_component import get_profile_pic_path

# Nomes padrões dos perfis
NOMES_PADRAO = {
    'clara': 'Ana',
    'tecnica': 'Fernando',
    'durona': 'Jorge'
}

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
        # Inicializar variáveis de perfil e repositório no início da função
        personalidade_repo = PersonalidadeIARepository(DatabaseManager())
        perfil_nome_amigavel = "Clara e Acolhedora"
        perfil_nome_tecnico = "Técnico e Formal"
        perfil_nome_durao = "Durão e Informal"

        # Função utilitária para obter nome customizado
        def get_nome_customizado(user_id, nome_perfil, chave):
            dados = personalidade_repo.obter_personalidade(user_id, nome_perfil)
            if dados and dados.get('nome_customizado'):
                return dados['nome_customizado']
            return NOMES_PADRAO[chave]

        # Criar abas de menu para a conversa com Assistente e Gerenciar Perfis IA
        tabs = st.tabs(["💬 Conversar Com Assistente", "👤 Gerenciar Perfis IA", "✨ Criar Perfil IA"])
        with tabs[0]:
            # Exibir período selecionado acima do chat
            data_inicio = st.session_state.get('ia_periodo_inicio', '')
            data_fim = st.session_state.get('ia_periodo_fim', '')
            if data_inicio and data_fim:
                st.info(f"🗓️ Período selecionado: {data_inicio} a {data_fim}")
            else:
                st.info("🗓️ Período: Todas as transações disponíveis")

            # Avatar da IA conforme personalidade
            avatar_map = {
                'clara': 'imgs/perfil_amigavel_fem.png',
                'tecnica': 'imgs/perfil_tecnico_masc.png',
                'durona': 'imgs/perfil_durao_mas.png'
            }
            personalidade = st.session_state.get('ai_personality', 'clara')
            avatar_path = avatar_map.get(personalidade, 'imgs/perfil_amigavel_fem.png')

            # Avatar do usuário (foto de perfil, se disponível)
            usuario_username = st.session_state.get('usuario', None)
            user_avatar_path = None
            if usuario_username:
                user_avatar_path = get_profile_pic_path(usuario_username)
                if user_avatar_path and not os.path.isabs(user_avatar_path):
                    user_avatar_path = os.path.join(os.getcwd(), user_avatar_path)
                if not user_avatar_path or not os.path.exists(user_avatar_path):
                    user_avatar_path = 'imgs/perfil_amigavel_fem.png'
            else:
                user_avatar_path = 'imgs/perfil_amigavel_fem.png'

            # Parâmetros atuais da personalidade
            params = {}
            if personalidade == 'clara':
                params_db = personalidade_repo.obter_personalidade(user_id, perfil_nome_amigavel)
                params_ss = st.session_state.get('perfil_amigavel_parametros', {})
                params = params_db if params_db and params_db.get('emojis') not in [None, ''] else params_ss
                if params and (not params.get('emojis') or params.get('emojis') == ''):
                    params['emojis'] = 'Nenhum'
            elif personalidade == 'tecnica':
                params_db = personalidade_repo.obter_personalidade(user_id, perfil_nome_tecnico)
                params_ss = st.session_state.get('perfil_tecnico_parametros', {})
                params = params_db if params_db and params_db.get('emojis') not in [None, ''] else params_ss
                if params and (not params.get('emojis') or params.get('emojis') == ''):
                    params['emojis'] = 'Nenhum'
            elif personalidade == 'durona':
                params_db = personalidade_repo.obter_personalidade(user_id, perfil_nome_durao)
                params_ss = st.session_state.get('perfil_durao_parametros', {})
                params = params_db if params_db and params_db.get('emojis') not in [None, ''] else params_ss
                if params and (not params.get('emojis') or params.get('emojis') == ''):
                    params['emojis'] = 'Nenhum'

            # Card visual dos parâmetros
            if params:
                st.markdown(f'''
<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 12px 18px; border-radius: 12px; color: #fff; margin-bottom: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); font-size: 15px;">
    <b>Personalidade:</b> {personalidade.capitalize()}<br>
    <b>Formalidade:</b> {params.get('formalidade', '')} &nbsp;|&nbsp;
    <b>Emojis:</b> {params.get('emojis', 'Nenhum')} &nbsp;|&nbsp;
    <b>Tom:</b> {params.get('tom', '')} &nbsp;|&nbsp;
    <b>Foco:</b> {params.get('foco', '')}
</div>
''', unsafe_allow_html=True)

            # Campo de debug visual
            emojis_valor = params.get('emojis', 'Nenhum') or 'Nenhum'
            personalidade = st.session_state.get('ai_personality', 'clara')
            if personalidade == 'clara':
                nome_ia = get_nome_customizado(user_id, perfil_nome_amigavel, 'clara')
            elif personalidade == 'tecnica':
                nome_ia = get_nome_customizado(user_id, perfil_nome_tecnico, 'tecnica')
            elif personalidade == 'durona':
                nome_ia = get_nome_customizado(user_id, perfil_nome_durao, 'durona')
            else:
                nome_ia = ''
            prompt_customizado = f"Nome: {nome_ia}\nFormalidade: {params.get('formalidade', '')}\nEmojis: {emojis_valor}\nTom: {params.get('tom', '')}\nFoco: {params.get('foco', '')}"
            # Prompt final
            prompt_final = None
            if 'chat_history' in st.session_state and st.session_state.chat_history:
                for msg in reversed(st.session_state.chat_history):
                    if isinstance(msg, dict) and msg.get('role') == 'assistant' and 'prompt' in msg:
                        prompt_final = msg['prompt']
                        break
            # Contexto
            context = st.session_state.get('last_context')
            with st.expander('🛠️ Debug: Parâmetros e Prompt Enviados para o LLM', expanded=False):
                st.markdown('**Parâmetros de Personalidade:**')
                st.code(prompt_customizado, language='markdown')
                st.markdown('**Prompt Final Enviado ao LLM:**')
                if prompt_final:
                    st.code(prompt_final, language='markdown')
                else:
                    st.info('Prompt final ainda não disponível. Envie uma mensagem para gerar.')
                st.markdown('**Contexto Enviado ao LLM:**')
                if context:
                    st.code(json.dumps(context, indent=2, ensure_ascii=False), language='json')
                else:
                    st.info('Contexto ainda não disponível. Envie uma mensagem para gerar.')

            # Inicializar histórico de chat
            if 'chat_history' not in st.session_state:
                st.session_state.chat_history = []
            # Inicializar input controlado
            if 'user_message_input' not in st.session_state:
                st.session_state.user_message_input = ''
            # Exibir histórico de chat
            for message in st.session_state.chat_history:
                if message["role"] == "user":
                    with st.chat_message("user", avatar=user_avatar_path):
                        st.write(message["content"])
                else:
                    with st.chat_message("assistant", avatar=avatar_path):
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
                nome_amigavel = get_nome_customizado(user_id, perfil_nome_amigavel, 'clara')
                st.image(
                    "imgs/perfil_amigavel_fem.png",
                    caption=f"{nome_amigavel} (Clara e Acolhedora)",
                    use_container_width=True
                )
                if st.button("Ver detalhes do perfil Clara e Acolhedora", key="btn_perfil_amigavel", help="Clique na imagem para ver detalhes do perfil", use_container_width=True):
                    toggle_perfil_amigavel()
                if st.button("Editar Características", key="btn_editar_caracteristicas_amigavel", use_container_width=True):
                    editar_caracteristicas_amigavel()
                st.markdown("""
                    </div>
                    </div>
                """, unsafe_allow_html=True)

            with col_details1:
                # Garantir existência do dicionário de parâmetros antes do acesso
                if 'perfil_amigavel_parametros' not in st.session_state or not isinstance(st.session_state['perfil_amigavel_parametros'], dict):
                    st.session_state.perfil_amigavel_parametros = {
                        'formalidade': 'Informal',
                        'emojis': 'Alto',
                        'tom': 'Muito Amigável',
                        'foco': 'Motivacional'
                    }
                if st.session_state.show_perfil_amigavel:
                    if st.session_state.show_editar_caracteristicas_amigavel:
                        user_id_db = obter_user_id_do_usuario()
                        if user_id_db is None:
                            st.error("Não foi possível obter o usuário. Faça login novamente.")
                            return
                        # Garantir existência do dicionário de parâmetros após leitura do banco
                        if 'perfil_amigavel_parametros' not in st.session_state or not isinstance(st.session_state['perfil_amigavel_parametros'], dict):
                            st.session_state.perfil_amigavel_parametros = {
                                'formalidade': 'Informal',
                                'emojis': 'Alto',
                                'tom': 'Muito Amigável',
                                'foco': 'Motivacional'
                            }
                        # Carregar nomes customizados do banco ou usar padrão
                        personalidade_repo = PersonalidadeIARepository(DatabaseManager())
                        def get_nome_customizado(user_id, nome_perfil, chave):
                            dados = personalidade_repo.obter_personalidade(user_id, nome_perfil)
                            if dados and dados.get('nome_customizado'):
                                return dados['nome_customizado']
                            return NOMES_PADRAO[chave]

                        nome_amigavel = get_nome_customizado(user_id, perfil_nome_amigavel, 'clara')
                        nome_tecnico = get_nome_customizado(user_id, perfil_nome_tecnico, 'tecnica')
                        nome_durao = get_nome_customizado(user_id, perfil_nome_durao, 'durona')

                        with st.form("form_editar_perfil_amigavel"):
                            nome_val = st.session_state.get('nome_amigavel', nome_amigavel)
                            nome_input = st.text_input(
                                "Nome do Assistente (máx. 20 caracteres)",
                                value=nome_val,
                                max_chars=20,
                                key="input_nome_amigavel"
                            )
                            nome_invalido = len(nome_input.strip()) == 0
                            if nome_invalido:
                                st.warning("O nome não pode ser vazio.")
                            formalidade_opcoes = ["Informal", "Neutro", "Formal"]
                            formalidade_val = st.session_state.perfil_amigavel_parametros.get('formalidade', 'Informal')
                            if formalidade_val not in formalidade_opcoes:
                                formalidade_val = 'Informal'
                            formalidade = st.selectbox(
                                "Formalidade",
                                formalidade_opcoes,
                                index=formalidade_opcoes.index(formalidade_val)
                            )
                            emojis_opcoes = ["Nenhum", "Moderado", "Alto"]
                            emojis_val = st.session_state.perfil_amigavel_parametros.get('emojis', 'Alto')
                            if emojis_val not in emojis_opcoes:
                                emojis_val = 'Alto'
                            emojis = st.selectbox(
                                "Uso de Emojis",
                                emojis_opcoes,
                                index=emojis_opcoes.index(emojis_val)
                            )
                            tom_opcoes = ["Amigável", "Muito Amigável", "Melhor Amiga"]
                            tom_val = st.session_state.perfil_amigavel_parametros.get('tom', 'Muito Amigável')
                            if tom_val not in tom_opcoes:
                                tom_val = 'Muito Amigável'
                            tom = st.selectbox(
                                "Tom",
                                tom_opcoes,
                                index=tom_opcoes.index(tom_val)
                            )
                            foco_opcoes = ["Neutro", "Motivacional", "Voa Meu Bem"]
                            foco_val = st.session_state.perfil_amigavel_parametros.get('foco', 'Motivacional')
                            if foco_val not in foco_opcoes:
                                foco_val = 'Motivacional'
                            foco = st.selectbox(
                                "Foco",
                                foco_opcoes,
                                index=foco_opcoes.index(foco_val)
                            )
                            submit = st.form_submit_button("Salvar alterações")
                            if submit and not nome_invalido:
                                print(f"[DEBUG] Valor de emojis selecionado no formulário (amigável): {emojis}")
                                personalidade_repo = PersonalidadeIARepository(DatabaseManager())
                                emojis_valor = emojis if emojis else 'Nenhum'
                                print(f"[DEBUG] Valor de emojis salvo no session_state (amigável): {emojis_valor}")
                                st.session_state.perfil_amigavel_parametros = {
                                    'formalidade': formalidade,
                                    'emojis': emojis_valor,
                                    'tom': tom,
                                    'foco': foco
                                }
                                print(f"[DEBUG] Salvando no banco (amigável): {emojis_valor}")
                                personalidade_repo.salvar_personalidade(
                                    user_id=user_id_db,
                                    nome_perfil=perfil_nome_amigavel,
                                    formalidade=formalidade,
                                    uso_emojis=emojis_valor,
                                    tom=tom,
                                    foco=foco,
                                    prompt_base=None,
                                    nome_customizado=nome_input.strip()
                                )
                                st.session_state['nome_amigavel'] = nome_input.strip()
                                st.success("Parâmetros atualizados com sucesso!")
                    else:
                        st.markdown(f"""
                            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 24px; border-radius: 16px; color: #fff; box-shadow: 0 4px 18px rgba(0,0,0,0.10);'>
                                <h3 style='margin-top:0;'>🌟 {nome_amigavel} (Clara e Acolhedora)</h3>
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
                nome_tecnico = get_nome_customizado(user_id, perfil_nome_tecnico, 'tecnica')
                st.image(
                    "imgs/perfil_tecnico_masc.png",
                    caption=f"{nome_tecnico} (Técnico e Formal)",
                    use_container_width=True
                )
                if st.button("Ver detalhes do perfil Técnico e Formal", key="btn_perfil_tecnico", help="Clique na imagem para ver detalhes do perfil", use_container_width=True):
                    toggle_perfil_tecnico()
                if st.button("Editar Características", key="btn_editar_caracteristicas_tecnico", use_container_width=True):
                    editar_caracteristicas_tecnico()
                st.markdown("""
                    </div>
                    </div>
                """, unsafe_allow_html=True)

            with col_details2:
                if 'perfil_tecnico_parametros' not in st.session_state or not isinstance(st.session_state['perfil_tecnico_parametros'], dict):
                    st.session_state.perfil_tecnico_parametros = {
                        'formalidade': 'Formal',
                        'emojis': 'Nenhum',
                        'tom': 'Objetivo',
                        'foco': 'Analítico'
                    }
                if st.session_state.show_perfil_tecnico:
                    if st.session_state.show_editar_caracteristicas_tecnico:
                        user_id_db = obter_user_id_do_usuario()
                        if user_id_db is None:
                            st.error("Não foi possível obter o usuário. Faça login novamente.")
                            return
                        if 'perfil_tecnico_parametros' not in st.session_state or not isinstance(st.session_state['perfil_tecnico_parametros'], dict):
                            st.session_state.perfil_tecnico_parametros = {
                                'formalidade': 'Formal',
                                'emojis': 'Nenhum',
                                'tom': 'Objetivo',
                                'foco': 'Analítico'
                            }
                        with st.form("form_editar_perfil_tecnico"):
                            nome_val = st.session_state.get('nome_tecnico', nome_tecnico)
                            nome_input = st.text_input(
                                "Nome do Assistente (máx. 20 caracteres)",
                                value=nome_val,
                                max_chars=20,
                                key="input_nome_tecnico"
                            )
                            nome_invalido = len(nome_input.strip()) == 0
                            if nome_invalido:
                                st.warning("O nome não pode ser vazio.")
                            formalidade_opcoes = ["Informal", "Neutro", "Formal"]
                            formalidade_val = st.session_state.perfil_tecnico_parametros.get('formalidade', 'Formal')
                            if formalidade_val not in formalidade_opcoes:
                                formalidade_val = 'Formal'
                            formalidade = st.selectbox(
                                "Formalidade",
                                formalidade_opcoes,
                                index=formalidade_opcoes.index(formalidade_val)
                            )
                            emojis_opcoes = ["Nenhum", "Moderado", "Alto"]
                            emojis_val = st.session_state.perfil_tecnico_parametros.get('emojis', 'Nenhum')
                            if emojis_val not in emojis_opcoes:
                                emojis_val = 'Nenhum'
                            emojis = st.selectbox(
                                "Uso de Emojis",
                                emojis_opcoes,
                                index=emojis_opcoes.index(emojis_val)
                            )
                            tom_opcoes = ["Objetivo", "Preciso", "Formal"]
                            tom_val = st.session_state.perfil_tecnico_parametros.get('tom', 'Objetivo')
                            if tom_val not in tom_opcoes:
                                tom_val = 'Objetivo'
                            tom = st.selectbox(
                                "Tom",
                                tom_opcoes,
                                index=tom_opcoes.index(tom_val)
                            )
                            foco_opcoes = ["Analítico", "Neutro", "Recomendação"]
                            foco_val = st.session_state.perfil_tecnico_parametros.get('foco', 'Analítico')
                            if foco_val not in foco_opcoes:
                                foco_val = 'Analítico'
                            foco = st.selectbox(
                                "Foco",
                                foco_opcoes,
                                index=foco_opcoes.index(foco_val)
                            )
                            submit = st.form_submit_button("Salvar alterações")
                            if submit and not nome_invalido:
                                print(f"[DEBUG] Valor de emojis selecionado no formulário (técnico): {emojis}")
                                personalidade_repo = PersonalidadeIARepository(DatabaseManager())
                                emojis_valor = emojis if emojis else 'Nenhum'
                                print(f"[DEBUG] Valor de emojis salvo no session_state (técnico): {emojis_valor}")
                                st.session_state.perfil_tecnico_parametros = {
                                    'formalidade': formalidade,
                                    'emojis': emojis_valor,
                                    'tom': tom,
                                    'foco': foco
                                }
                                print(f"[DEBUG] Salvando no banco (técnico): {emojis_valor}")
                                personalidade_repo.salvar_personalidade(
                                    user_id=user_id_db,
                                    nome_perfil=perfil_nome_tecnico,
                                    formalidade=formalidade,
                                    uso_emojis=emojis_valor,
                                    tom=tom,
                                    foco=foco,
                                    prompt_base=None,
                                    nome_customizado=nome_input.strip()
                                )
                                st.session_state['nome_tecnico'] = nome_input.strip()
                                st.success("Parâmetros atualizados com sucesso!")
                    else:
                        st.markdown(f"""
                            <div style='background: linear-gradient(135deg, #232526 0%, #414345 100%); padding: 24px; border-radius: 16px; color: #fff; box-shadow: 0 4px 18px rgba(0,0,0,0.10);'>
                                <h3 style='margin-top:0;'>📊 {nome_tecnico} (Técnico e Formal)</h3>
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
                nome_durao = get_nome_customizado(user_id, perfil_nome_durao, 'durona')
                st.image(
                    "imgs/perfil_durao_mas.png",
                    caption=f"{nome_durao} (Durão e Informal)",
                    use_container_width=True
                )
                if st.button("Ver detalhes do perfil Durão e Informal", key="btn_perfil_durao", help="Clique na imagem para ver detalhes do perfil", use_container_width=True):
                    toggle_perfil_durao()
                if st.button("Editar Características", key="btn_editar_caracteristicas_durao", use_container_width=True):
                    editar_caracteristicas_durao()
                st.markdown("""
                    </div>
                    </div>
                """, unsafe_allow_html=True)

            with col_details3:
                if 'perfil_durao_parametros' not in st.session_state or not isinstance(st.session_state['perfil_durao_parametros'], dict):
                    st.session_state.perfil_durao_parametros = {
                        'formalidade': 'Informal',
                        'emojis': 'Nenhum',
                        'tom': 'Durão',
                        'foco': 'Disciplina'
                    }
                if st.session_state.show_perfil_durao:
                    if st.session_state.show_editar_caracteristicas_durao:
                        user_id_db = obter_user_id_do_usuario()
                        if user_id_db is None:
                            st.error("Não foi possível obter o usuário. Faça login novamente.")
                            return
                        if 'perfil_durao_parametros' not in st.session_state or not isinstance(st.session_state['perfil_durao_parametros'], dict):
                            st.session_state.perfil_durao_parametros = {
                                'formalidade': 'Informal',
                                'emojis': 'Nenhum',
                                'tom': 'Durão',
                                'foco': 'Disciplina'
                            }
                        with st.form("form_editar_perfil_durao"):
                            nome_val = st.session_state.get('nome_durao', nome_durao)
                            nome_input = st.text_input(
                                "Nome do Assistente (máx. 20 caracteres)",
                                value=nome_val,
                                max_chars=20,
                                key="input_nome_durao"
                            )
                            nome_invalido = len(nome_input.strip()) == 0
                            if nome_invalido:
                                st.warning("O nome não pode ser vazio.")
                            formalidade_opcoes = ["Informal", "Neutro", "Formal"]
                            formalidade_val = st.session_state.perfil_durao_parametros.get('formalidade', 'Informal')
                            if formalidade_val not in formalidade_opcoes:
                                formalidade_val = 'Informal'
                            formalidade = st.selectbox(
                                "Formalidade",
                                formalidade_opcoes,
                                index=formalidade_opcoes.index(formalidade_val)
                            )
                            emojis_opcoes = ["Nenhum", "Moderado", "Alto"]
                            emojis_val = st.session_state.perfil_durao_parametros.get('emojis', 'Nenhum')
                            if emojis_val not in emojis_opcoes:
                                emojis_val = 'Nenhum'
                            emojis = st.selectbox(
                                "Uso de Emojis",
                                emojis_opcoes,
                                index=emojis_opcoes.index(emojis_val)
                            )
                            tom_opcoes = ["Durão", "Direto", "Motivacional"]
                            tom_val = st.session_state.perfil_durao_parametros.get('tom', 'Durão')
                            if tom_val not in tom_opcoes:
                                tom_val = 'Durão'
                            tom = st.selectbox(
                                "Tom",
                                tom_opcoes,
                                index=tom_opcoes.index(tom_val)
                            )
                            foco_opcoes = ["Disciplina", "Resultados", "Cobrança"]
                            foco_val = st.session_state.perfil_durao_parametros.get('foco', 'Disciplina')
                            if foco_val not in foco_opcoes:
                                foco_val = 'Disciplina'
                            foco = st.selectbox(
                                "Foco",
                                foco_opcoes,
                                index=foco_opcoes.index(foco_val)
                            )
                            submit = st.form_submit_button("Salvar alterações")
                            if submit and not nome_invalido:
                                print(f"[DEBUG] Valor de emojis selecionado no formulário (durona): {emojis}")
                                personalidade_repo = PersonalidadeIARepository(DatabaseManager())
                                emojis_valor = emojis if emojis else 'Nenhum'
                                print(f"[DEBUG] Valor de emojis salvo no session_state (durona): {emojis_valor}")
                                st.session_state.perfil_durao_parametros = {
                                    'formalidade': formalidade,
                                    'emojis': emojis_valor,
                                    'tom': tom,
                                    'foco': foco
                                }
                                print(f"[DEBUG] Salvando no banco (durona): {emojis_valor}")
                                personalidade_repo.salvar_personalidade(
                                    user_id=user_id_db,
                                    nome_perfil=perfil_nome_durao,
                                    formalidade=formalidade,
                                    uso_emojis=emojis_valor,
                                    tom=tom,
                                    foco=foco,
                                    prompt_base=None,
                                    nome_customizado=nome_input.strip()
                                )
                                st.session_state['nome_durao'] = nome_input.strip()
                                st.success("Parâmetros atualizados com sucesso!")
                    else:
                        st.markdown(f"""
                            <div style='background: linear-gradient(135deg, #b31217 0%, #e52d27 100%); padding: 24px; border-radius: 16px; color: #fff; box-shadow: 0 4px 18px rgba(0,0,0,0.10);'>
                                <h3 style='margin-top:0;'>💪 {nome_durao} (Durão e Informal)</h3>
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
        with tabs[2]:
            st.markdown("### ✨ Criar Novo Perfil IA")
            with st.form("form_criar_perfil_ia"):
                nome_perfil = st.text_input(
                    "Nome do Perfil",
                    max_chars=20,
                    help="Dê um nome para o novo perfil de IA (ex: Consultor Investimentos)"
                )
                foto_perfil = st.session_state.get('foto_perfil_criacao', None)
                col_img, col_upload = st.columns([0.6, 7.4])
                with col_img:
                    st.markdown("<div style='display: flex; align-items: center; height: 100%; justify-content: center;'>", unsafe_allow_html=True)
                    if foto_perfil is not None:
                        st.image(foto_perfil, caption="", width=64)
                    else:
                        st.image("imgs/perfil_tecnico_masc.png", caption="", width=64)
                    st.markdown("</div>", unsafe_allow_html=True)
                with col_upload:
                    uploaded_file = st.file_uploader(
                        "Foto do Perfil (opcional)",
                        type=["png", "jpg", "jpeg"],
                        help="Carregue uma foto para o perfil. Se não carregar, será usada a foto padrão."
                    )
                    if uploaded_file is not None:
                        st.session_state['foto_perfil_criacao'] = uploaded_file
                        foto_perfil = uploaded_file
                st.markdown("---")
                st.markdown("#### Prompt Base do Assistente Financeiro")
                prompt_base = (
                    "Você é um assistente financeiro inteligente, capaz de responder dúvidas, dar dicas e analisar dados financeiros do usuário. "
                    "Personalize seu atendimento conforme os parâmetros abaixo."
                )
                st.code(prompt_base, language="markdown")
                st.markdown("---")
                st.markdown("#### Defina as Características da sua IA (Básico)")
                idioma = st.selectbox("Idioma", ["Português", "Inglês", "Espanhol"], index=0)
                amigavel = st.selectbox("Amigável", ["Não", "Sim", "Muito"], index=1)
                formalidade = st.selectbox("Formalidade", ["Informal", "Neutro", "Formal"], index=1)
                uso_emojis = st.selectbox("Uso de Emojis", ["Nenhum", "Moderado", "Alto"], index=1)
                tom = st.selectbox("Tom", ["Neutro", "Amigável", "Objetivo", "Durão", "Motivacional"], index=0)
                foco = st.selectbox("Foco", ["Neutro", "Motivacional", "Analítico", "Disciplina", "Cobrança"], index=0)
                # Novos parâmetros avançados
                st.markdown("---")
                st.markdown("#### Defina as Características da sua IA (Avançado)")
                arquetipo = st.selectbox(
                    "Arquetipo",
                    ["", "Coach motivacional", "Mentor cauteloso", "Parceiro informal"],
                    index=0,
                    help="Escolha o arquétipo principal do assistente."
                )
                tom_voz = st.selectbox(
                    "Tom de voz",
                    ["", "Amigável", "Formal", "Inspirador"],
                    index=0,
                    help="Como o assistente soa ao conversar."
                )
                estilo_comunicacao = st.selectbox(
                    "Estilo de comunicação",
                    ["", "Sintético e direto", "Explicativo (passo-a-passo)", "Cheio de analogias"],
                    index=0,
                    help="Forma como as respostas são estruturadas."
                )
                nivel_humor = st.selectbox(
                    "Nível de humor",
                    ["", "Sério", "Leve (toques de piada)", "Sarcástico (com cuidado)"],
                    index=0,
                    help="Quanto humor o assistente utiliza."
                )
                empatia = st.selectbox(
                    "Empatia",
                    ["", "Altíssima (aconselha e conforta)", "Média (foca em dados)", "Baixa (apenas fact-check)"],
                    index=0,
                    help="Nível de empatia nas respostas."
                )
                autoridade_conselho = st.selectbox(
                    "Autoridade/tom de conselho",
                    ["", "Eu recomendo", "Você pode", "Que tal tentarmos…?"],
                    index=0,
                    help="Como o assistente sugere ações."
                )
                profundidade_expertise = st.selectbox(
                    "Profundidade de expertise",
                    ["", "Básico (educação financeira 101)", "Intermediário (planejamento mensal)", "Avançado (investimentos complexos)"],
                    index=0,
                    help="Nível de profundidade das respostas."
                )
                perfil_risco = st.selectbox(
                    "Perfil de risco internalizado",
                    ["", "Conservador", "Moderado", "Arrojado"],
                    index=0,
                    help="Tendência do assistente ao sugerir estratégias."
                )
                motivacao_call = st.selectbox(
                    "Motivação e call-to-action",
                    ["", "Gatilhos de positividade (👏 Você mandou bem!)", "Gatilhos de desafio (Será que você consegue economizar 10% a mais?)", "Gatilhos de urgência (Faltam 3 dias para fechar o mês!)"],
                    index=0,
                    help="Tipo de incentivo usado pelo assistente."
                )
                regionalismo = st.selectbox(
                    "Regionalismo",
                    ["", "Gírias paulistas", "Gírias cariocas", "Nordestino arretado", "Mineirês", "Goianês", "Gaúcho raiz", "Sem regionalismo"],
                    index=0,
                    help="Escolha um estilo regional de comunicação."
                )
                cultura = st.selectbox(
                    "Cultura",
                    ["", "Hippie", "Rockeiro", "Geek", "Amante do Futebol", "Religioso"],
                    index=0,
                    help="Escolha um traço cultural para o perfil da IA."
                )
                valores_centrais = st.selectbox(
                    "Valores centrais",
                    ["", "Frugalidade", "Liberdade financeira", "Consumo consciente", "Legado"],
                    index=0,
                    help="Valor principal transmitido pelo assistente."
                )
                reacao_fracasso = st.selectbox(
                    "Reação ao fracasso",
                    ["", "Comfort-coach (abraço e recomeço)", "Realista (análise fria dos números)", "Tough love (puxa a orelha)"],
                    index=0,
                    help="Como o assistente reage a resultados negativos."
                )
                submit = st.form_submit_button("Criar Perfil IA")
                if submit:
                    erros = []
                    nome_perfil_val = nome_perfil.strip()
                    if len(nome_perfil_val) == 0:
                        erros.append("O nome do perfil não pode ser vazio.")
                    if len(nome_perfil) > 20:
                        erros.append("O nome do perfil deve ter no máximo 20 caracteres.")
                    if erros:
                        for erro in erros:
                            st.error(erro)
                    else:
                        st.success("Perfil IA criado (simulação). Em breve será possível salvar e usar este perfil no chat.")
                        st.info(f"Nome: {nome_perfil}\nIdioma: {idioma}\nAmigável: {amigavel}\nFormalidade: {formalidade}\nEmojis: {uso_emojis}\nTom: {tom}\nFoco: {foco}\nArquetipo: {arquetipo}\nTom de voz: {tom_voz}\nEstilo de comunicação: {estilo_comunicacao}\nNível de humor: {nivel_humor}\nEmpatia: {empatia}\nAutoridade/tom de conselho: {autoridade_conselho}\nProfundidade de expertise: {profundidade_expertise}\nPerfil de risco: {perfil_risco}\nMotivação/call-to-action: {motivacao_call}\nRegionalismo: {regionalismo}\nCultura: {cultura}\nValores centrais: {valores_centrais}\nReação ao fracasso: {reacao_fracasso}")
    except Exception as e:
        st.error(f"Erro na interface de chat: {str(e)}")


def process_user_message(user_id: int, message: str):
    """Processa mensagem do usuário e gera resposta"""
    try:
        if user_id is None:
            st.error("Usuário inválido. Não foi possível processar a mensagem.")
            return
        personalidade_repo = PersonalidadeIARepository(DatabaseManager())
        st.session_state.chat_history.append({
            'role': 'user',
            'content': message,
            'timestamp': datetime.now()
        })
        with st.spinner("🤖 Analisando..."):
            # Definir nomes dos perfis
            perfil_nome_amigavel = "Clara e Acolhedora"
            perfil_nome_tecnico = "Técnico e Formal"
            perfil_nome_durao = "Durão e Informal"
            # Inicializar repositório
            personalidade = st.session_state.get('ai_personality', 'clara')
            data_inicio = st.session_state.get('ia_periodo_inicio', '') or ''
            data_fim = st.session_state.get('ia_periodo_fim', '') or ''
            qtd_transacoes = st.session_state.get('ia_qtd_transacoes', 50)

            # Buscar nomes customizados
            def get_nome_customizado(user_id, nome_perfil, chave):
                dados = personalidade_repo.obter_personalidade(user_id, nome_perfil)
                if dados and dados.get('nome_customizado'):
                    return dados['nome_customizado']
                return NOMES_PADRAO[chave]
            nome_amigavel = get_nome_customizado(user_id, perfil_nome_amigavel, 'clara')
            nome_tecnico = get_nome_customizado(user_id, perfil_nome_tecnico, 'tecnica')
            nome_durao = get_nome_customizado(user_id, perfil_nome_durao, 'durona')

            # Buscar características do perfil selecionado
            if personalidade == 'clara':
                params_db = personalidade_repo.obter_personalidade(user_id, perfil_nome_amigavel)
                params_ss = st.session_state.get('perfil_amigavel_parametros', {})
                params = params_db if params_db and params_db.get('emojis') not in [None, ''] else params_ss
                if params and (not params.get('emojis') or params.get('emojis') == ''):
                    params['emojis'] = 'Nenhum'
                nome_ia = nome_amigavel
            elif personalidade == 'tecnica':
                params_db = personalidade_repo.obter_personalidade(user_id, perfil_nome_tecnico)
                params_ss = st.session_state.get('perfil_tecnico_parametros', {})
                params = params_db if params_db and params_db.get('emojis') not in [None, ''] else params_ss
                if params and (not params.get('emojis') or params.get('emojis') == ''):
                    params['emojis'] = 'Nenhum'
                nome_ia = nome_tecnico
            elif personalidade == 'durona':
                params_db = personalidade_repo.obter_personalidade(user_id, perfil_nome_durao)
                params_ss = st.session_state.get('perfil_durao_parametros', {})
                params = params_db if params_db and params_db.get('emojis') not in [None, ''] else params_ss
                if params and (not params.get('emojis') or params.get('emojis') == ''):
                    params['emojis'] = 'Nenhum'
                nome_ia = nome_durao
            else:
                params = {}
                nome_ia = ''

            # Montar prompt customizado
            prompt_customizado = f"Nome: {nome_ia}\nFormalidade: {params.get('formalidade', '')}\nEmojis: {params.get('emojis', '')}\nTom: {params.get('tom', '')}\nFoco: {params.get('foco', '')}"

            # Montar context com nome_ia
            context = {'nome_ia': nome_ia}
            st.session_state['last_context'] = context

            response_data = st.session_state.ai_assistant.process_message_with_personality(
                user_id, message, personalidade, data_inicio, data_fim, qtd_transacoes, prompt_customizado
            )
            response = response_data['response']
            print(f"[DEBUG] Resposta da IA: {response}")
        st.session_state.chat_history.append({
            'role': 'assistant',
            'content': response,
            'timestamp': datetime.now(),
            'prompt': response_data.get('prompt'),
            'personalidade': response_data.get('personalidade')
        })
        st.rerun()
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
        
        st.markdown("### 🎭 Personalidade Assistente")
        
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
        user_id: Optional[int] = obter_user_id_do_usuario()
        if user_id is None:
            st.error("❌ Não foi possível obter os dados do usuário")
            return
        assert user_id is not None
        
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
        st.title("Assistente Financeiro")
        
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
