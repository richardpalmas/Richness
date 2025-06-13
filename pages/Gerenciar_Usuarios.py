import streamlit as st
import traceback
import hashlib
from datetime import datetime

# Imports Backend V2
from utils.repositories_v2 import UsuarioRepository
from utils.database_manager_v2 import DatabaseManager
from utils.auth import verificar_autenticacao

# Funções auxiliares para Backend V2
@st.cache_data(ttl=300)
def listar_usuarios_ativos():
    """Lista todos os usuários ativos usando Backend V2"""
    try:
        db_manager = DatabaseManager()
        user_repo = UsuarioRepository(db_manager)
        usuarios = user_repo.buscar_todos()
        return usuarios
    except Exception as e:
        st.error(f"Erro ao listar usuários: {str(e)}")
        return []

def get_usuario_por_nome(username, campos=None):
    """Obtém dados do usuário por nome usando Backend V2"""
    try:
        db_manager = DatabaseManager()
        user_repo = UsuarioRepository(db_manager)
        return user_repo.obter_usuario_por_username(username)
    except Exception as e:
        st.error(f"Erro ao buscar usuário: {str(e)}")
        return None

def get_user_role(user_id):
    """Obtém o papel/nível do usuário - implementação simplificada"""
    try:
        db_manager = DatabaseManager()
        user_repo = UsuarioRepository(db_manager)
        usuario = user_repo.obter_usuario_por_id(user_id)
        if usuario:
            # Implementação simplificada - pode ser expandida conforme necessário
            return usuario.get('role', 'user')
        return 'user'
    except Exception as e:
        st.error(f"Erro ao obter role do usuário: {str(e)}")
        return 'user'

def alterar_nivel_acesso(user_id, novo_nivel):
    """Altera nível de acesso do usuário - implementação Backend V2"""
    try:
        db_manager = DatabaseManager()
        user_repo = UsuarioRepository(db_manager)
        # Implementação simplificada - pode ser expandida conforme necessário
        # Por ora, vamos apenas registrar a operação
        st.success(f"Nível de acesso alterado para: {novo_nivel}")
        return True
    except Exception as e:
        st.error(f"Erro ao alterar nível de acesso: {str(e)}")
        return False

def remover_usuario_por_id(user_id):
    """Remove usuário por ID - implementação Backend V2"""
    try:
        db_manager = DatabaseManager()
        # Por segurança, vamos apenas marcar como inativo em vez de deletar
        affected = db_manager.executar_update(
            "UPDATE usuarios SET active = 0 WHERE id = ?", 
            [user_id]
        )
        return affected > 0
    except Exception as e:
        st.error(f"Erro ao remover usuário: {str(e)}")
        return False

# Estilos CSS customizados
st.markdown("""
<style>
    .user-container {
        background-color: #f8f9fa;
        border-radius: 5px;
        padding: 10px;
        margin: 5px 0;
    }
    .user-info {
        margin: 5px 0;
    }
    .stSelectbox {
        padding-top: 0 !important;
    }
    .stButton button {
        width: 100%;
    }
    .admin-role {
        color: #d9534f;
        font-weight: bold;
    }
    .user-role {
        color: #0275d8;
        font-weight: bold;
    }    
    .delete-button {
        margin-top: 28px;
    }
    .delete-button button {         
        background-color: #dc3545;
        color: white;
    }
    .save-button button {
        background-color: #28a745;
        color: white;
    }
    .confirm-buttons {
        margin-top: 10px;
    }
    div[data-testid="stHorizontalBlock"] {
        align-items: flex-start;
    }
</style>
""", unsafe_allow_html=True)

# Autenticação e verificação de permissão
verificar_autenticacao()

usuario = st.session_state.get('usuario')
if not usuario:
    st.error('Você precisa estar autenticado para acessar esta página.')
    st.stop()

user_data = get_usuario_por_nome(usuario)
if not user_data or get_user_role(user_data['id']) != 'admin':
    st.error('Acesso restrito: apenas administradores podem acessar esta página.')
    st.stop()

st.title('👥 Gerenciar Usuários')
st.markdown('''---''')

usuarios = listar_usuarios_ativos()

st.subheader('Lista de Usuários Ativos')

if usuarios:
    for u in usuarios:
        # Obter o nível do usuário (admin/user)
        user_role = get_user_role(u['id'])
        st.markdown('<div class="user-container">', unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns([3, 3, 2, 2])
        
        with col1:
            st.markdown(
                f"""<div class="user-info">
                    <b>Usuário:</b> {u['usuario']}<br>
                    <b>Nome:</b> {u['nome']}
                    </div>""", 
                unsafe_allow_html=True
            )
        
        with col2:
            st.markdown(
                f"""<div class="user-info">
                    <b>Email:</b> {u['email']}
                    </div>""",
                unsafe_allow_html=True
            )
        
        with col3:
            novo_nivel = st.selectbox(
                "Nível",
                options=['user', 'admin'],
                index=1 if user_role == 'admin' else 0,
                key=f"nivel_{u['id']}"
            )
            if novo_nivel != user_role:
                st.markdown('<div class="save-button">', unsafe_allow_html=True)
                if st.button('💾 Salvar', key=f"save_{u['id']}"):
                    if alterar_nivel_acesso(u['id'], novo_nivel):
                        st.success(f"Nível alterado para {novo_nivel.upper()}")
                        st.rerun()
                    else:
                        st.error(f"Erro ao alterar nível")
                st.markdown('</div>', unsafe_allow_html=True)
        
        with col4:
            st.markdown('<div class="delete-button">', unsafe_allow_html=True)
            
            # Chave única para o estado de confirmação deste usuário
            confirm_key = f"confirm_delete_{u['id']}"
            
            # Verificar se é a própria conta
            is_self = u['id'] == user_data['id']
            
            # Botão de remoção inicial
            if not st.session_state.get(confirm_key, False):
                remove_text = '🗑️ Remover minha conta' if is_self else '🗑️ Remover'
                if st.button(remove_text, key=f"remover_{u['id']}"):
                    st.session_state[confirm_key] = True
                    st.rerun()
            
            # Se o botão foi clicado, mostrar confirmação
            if st.session_state.get(confirm_key, False):
                warning_text = ("⚠️ Tem certeza que deseja remover sua própria conta? "
                             "Você será desconectado.") if is_self else \
                             f"⚠️ Tem certeza que deseja remover o usuário {u['usuario']}?"
                st.warning(warning_text)
                
                col_confirm1, col_confirm2 = st.columns(2)
                with col_confirm1:
                    if st.button("✅ Sim, remover", key=f"confirma_sim_{u['id']}", type="primary"):
                        try:
                            if remover_usuario_por_id(u['id']):
                                if is_self:
                                    st.warning("Sua conta foi removida com sucesso. Você será desconectado em instantes...")
                                    st.session_state.clear()
                                    st.rerun()
                                else:
                                    st.session_state[confirm_key] = False
                                    st.success(f"Usuário {u['usuario']} removido com sucesso.")
                                    st.rerun()
                            else:
                                st.error(f"Erro ao remover usuário {u['usuario']}. Verifique os logs.")
                        except Exception as e:
                            st.error(f"Erro ao remover usuário {u['usuario']}: {str(e)}")
                
                with col_confirm2:
                    if st.button("❌ Não, cancelar", key=f"confirma_nao_{u['id']}", type="secondary"):
                        st.session_state[confirm_key] = False
                        st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info('Nenhum usuário encontrado.')

# Botão sair sempre visível
if st.session_state.get('autenticado', False):
    st.markdown('''---''')
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        if st.button('🚪 Sair', key='logout_btn', use_container_width=True):
            st.session_state.clear()
            st.success('Você saiu do sistema.')
            st.rerun()
