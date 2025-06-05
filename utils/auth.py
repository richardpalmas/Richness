import streamlit as st
import functools

@functools.lru_cache(maxsize=1)
def _gerar_html_aviso_login():
    """
    Função auxiliar que gera o HTML do aviso de login uma única vez
    e mantém em cache para melhorar performance.
    """
    return """
    <div style='padding: 2em; background: #f8f9fa; border-radius: 10px; border: 1px solid #e9ecef; margin: 2em 0; text-align: center;'>
        <h3 style='color: #1f77b4; margin-bottom: 1rem;'>🔐 Acesso Necessário</h3>
        <p style='font-size: 1.1em; color: #495057; margin-bottom: 1rem;'>
            Para acessar esta página, você precisa estar autenticado.
        </p>
        <p style='color: #6c757d;'>
            <a href='/' target='_self' style='color: #1f77b4; text-decoration: none; font-weight: bold;'>🏠 Fazer Login</a>
            ou 
            <a href='/Cadastro' target='_self' style='color: #28a745; text-decoration: none; font-weight: bold;'>📝 Criar Conta</a>
        </p>
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

    # Adicionar botão de logout na barra lateral (consistente com Home.py)
    if st.sidebar.button('🚪 Sair', help="Fazer logout da aplicação"):
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
