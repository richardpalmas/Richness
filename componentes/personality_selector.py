import streamlit as st
import os
from utils.database_manager_v2 import DatabaseManager
from utils.repositories_v2 import PersonalidadeIARepository

def render_personality_selector():
    """Renderiza o seletor de personalidade da IA"""
    try:
        # Função utilitária para obter user_id do session_state
        user_id = None
        if 'usuario' in st.session_state:
            from utils.repositories_v2 import UsuarioRepository
            usuario = st.session_state['usuario']
            db = DatabaseManager()
            usuario_repo = UsuarioRepository(db)
            user_data = usuario_repo.obter_usuario_por_username(usuario)
            user_id = user_data['id'] if user_data else None
        personalidade_repo = PersonalidadeIARepository(DatabaseManager())
        # Perfis padrão
        NOMES_PADRAO = {'clara': 'Ana', 'tecnica': 'Fernando', 'durona': 'Jorge'}
        personalidade_opcoes = {
            "clara": "🌟 Mais clara, acolhedora e engraçada",
            "tecnica": "📊 Mais técnica e formal", 
            "durona": "💪 Mais durona e informal"
        }
        # Perfis customizados
        perfis_customizados = []
        if 'perfis_customizados' in st.session_state and st.session_state['perfis_customizados']:
            perfis_customizados = [p for p in st.session_state['perfis_customizados'] if p.get('tipo') == 'customizado']
        elif user_id:
            perfis_customizados = [p for p in personalidade_repo.listar_personalidades_usuario(user_id) if p.get('tipo') == 'customizado']
        # Montar opções do seletor
        opcoes = list(personalidade_opcoes.keys())
        nomes_exibicao = {k: personalidade_opcoes[k] for k in personalidade_opcoes}
        for perfil in perfis_customizados:
            nome = perfil.get('nome_customizado') or perfil.get('nome_perfil')
            opcoes.append(perfil['nome_perfil'])
            nomes_exibicao[perfil['nome_perfil']] = f"🧑‍💼 {nome} (Customizado)"
        st.markdown("### 🎭 Personalidade Assistente")
        personalidade_anterior = st.session_state.get('ai_personality', 'clara')
        if personalidade_anterior not in opcoes:
            personalidade_anterior = 'clara'

        # --- Grid de miniaturas ---
        st.markdown('<div style="margin-bottom: 10px;"><b>Como você gostaria que a IA se comunique?</b></div>', unsafe_allow_html=True)
        perfis_todos = [
            {
                'chave': 'clara',
                'nome': personalidade_opcoes['clara'],
                'img': 'imgs/perfil_amigavel_fem.png',
                'tipo': 'padrao'
            },
            {
                'chave': 'tecnica',
                'nome': personalidade_opcoes['tecnica'],
                'img': 'imgs/perfil_tecnico_masc.png',
                'tipo': 'padrao'
            },
            {
                'chave': 'durona',
                'nome': personalidade_opcoes['durona'],
                'img': 'imgs/perfil_durao_mas.png',
                'tipo': 'padrao'
            }
        ]
        for perfil in perfis_customizados:
            perfis_todos.append({
                'chave': perfil.get('nome_perfil'),
                'nome': perfil.get('nome_customizado') or perfil.get('nome_perfil'),
                'nome_customizado': perfil.get('nome_customizado'),
                'nome_perfil': perfil.get('nome_perfil'),
                'img': perfil.get('foto_path') if perfil.get('foto_path') and os.path.exists(perfil.get('foto_path', '')) else 'imgs/perfil_tecnico_masc.png',
                'tipo': 'customizado',
                'descricao_curta': perfil.get('descricao_curta', '')
            })
        # Exibir grid com no máximo 3 perfis por linha
        def chunked(lst, n):
            for i in range(0, len(lst), n):
                yield lst[i:i + n]

        idx_global = 0
        for linha in chunked(perfis_todos, 3):
            cols = st.columns(3)
            for idx, perfil in enumerate(linha):
                # Ignorar perfis sem chave/nome
                if not perfil.get('chave') or not perfil.get('nome'):
                    idx_global += 1
                    continue
                highlight = '4px solid #FFD700' if personalidade_anterior == perfil['chave'] else '2px solid #222'
                with cols[idx]:
                    # Definir nome curto dentro do bloco da coluna
                    if perfil['tipo'] == 'padrao':
                        if perfil['chave'] == 'clara':
                            nome_curto = NOMES_PADRAO['clara']
                            descricao_curta = '🌟 Mais clara, acolhedora e engraçada'
                        elif perfil['chave'] == 'tecnica':
                            nome_curto = NOMES_PADRAO['tecnica']
                            descricao_curta = '📊 Mais técnica e formal'
                        elif perfil['chave'] == 'durona':
                            nome_curto = NOMES_PADRAO['durona']
                            descricao_curta = '💪 Mais durona e informal'
                        else:
                            nome_curto = perfil['chave']
                            descricao_curta = ''
                    else:
                        nome_curto = perfil.get('nome_customizado')
                        if not nome_curto or str(nome_curto).strip() == '':
                            nome_curto = perfil.get('nome_perfil')
                        descricao_curta = perfil.get('descricao_curta', '')
                    st.markdown(
                        f"<div style='font-size:15px; text-align:center; font-weight:bold; margin-bottom:4px;'>{nome_curto}</div>",
                        unsafe_allow_html=True
                    )
                    st.image(perfil['img'], use_container_width=False)
                    st.markdown(
                        f"<div style='font-size:13px; text-align:center; margin-bottom:8px;'>{descricao_curta}</div>",
                        unsafe_allow_html=True
                    )
                    if st.button("Selecionar", key=f"btn_personalidade_{perfil['chave']}_{idx_global}"):
                        st.session_state['ai_personality'] = perfil['chave']
                        st.rerun()
                idx_global += 1
        st.markdown("---")
        # --- Fim do grid de miniaturas ---
    except Exception as e:
        st.error(f"Erro ao renderizar seletor de personalidade: {str(e)}") 