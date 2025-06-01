import streamlit as st
import functools

@functools.lru_cache(maxsize=1)
def _gerar_html_aviso_login():
    """
    Função auxiliar que gera o HTML do aviso de login uma única vez
    e mantém em cache para melhorar performance.
    """
    return """
    <div style='padding: 1em; background: #fffde7; border-radius: 8px; border: 1px solid #ffe082; margin-top: 1em;'>
        <span style='font-size:1.1em; color:#795548;'>Por favor, faça login na página inicial<br>
        ou <a href='/Cadastro' target='_self' style='color:#f9a825; text-decoration:underline; font-weight:bold;'>cadastre-se aqui</a></span>
    </div>
    """

def checar_autenticacao():
    """
    Função centralizada para verificar autenticação do usuário.
    Exibe mensagem e interrompe a execução se o usuário não estiver autenticado.
    Retorna True se autenticado, False caso contrário.
    """
    if not st.session_state.get('autenticado'):
        st.markdown(_gerar_html_aviso_login(), unsafe_allow_html=True)
        return False

    # Adicionar botão de logout na barra lateral
    if st.sidebar.button('Sair'):
        st.session_state['autenticado'] = False
        st.session_state['usuario'] = ''
        st.rerun()

    return True

def verificar_autenticacao():
    """
    Versão simplificada que interrompe a execução se o usuário não estiver autenticado.
    Útil para páginas que não devem ser carregadas sem autenticação.
    """
    if not checar_autenticacao():
        st.stop()
