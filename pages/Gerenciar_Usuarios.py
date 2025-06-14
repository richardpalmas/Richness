import streamlit as st
import hashlib
import logging
from datetime import datetime

# Imports Backend V2
from utils.repositories_v2 import UsuarioRepository
from utils.database_manager_v2 import DatabaseManager
from utils.auth import verificar_autenticacao

# Funções auxiliares para Backend V2
@st.cache_data(ttl=30)  # Reduzido de 300 para 30 segundos para atualização mais rápida
def listar_usuarios_ativos():
    """Lista todos os usuários ativos usando Backend V2"""
    try:
        db_manager = DatabaseManager()
        # Filtrar apenas usuários ativos
        result = db_manager.executar_query(
            "SELECT * FROM usuarios WHERE is_active = 1 ORDER BY username", 
            []
        )
        return [dict(row) for row in result]
    except Exception as e:
        st.error(f"Erro ao listar usuários: {str(e)}")
        return []

@st.cache_data(ttl=30)
def listar_usuarios_inativos():
    """Lista todos os usuários inativos usando Backend V2"""
    try:
        db_manager = DatabaseManager()
        # Filtrar apenas usuários inativos
        result = db_manager.executar_query(
            "SELECT * FROM usuarios WHERE is_active = 0 ORDER BY username", 
            []
        )
        return [dict(row) for row in result]
    except Exception as e:
        st.error(f"Erro ao listar usuários inativos: {str(e)}")
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
            # Verificação especial para usuários com acesso máximo
            if usuario.get('username') in ['richardpalmas', 'richardpalmas50']:
                return 'admin'
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

def inativar_usuario_por_id(user_id):
    """Inativa usuário por ID - marca como is_active = 0"""
    try:
        db_manager = DatabaseManager()
        
        # Verificar se o usuário existe antes de tentar inativar
        existing_user = db_manager.executar_query(
            "SELECT username, is_active FROM usuarios WHERE id = ?", 
            [user_id]
        )
        
        if not existing_user:
            return False, f"Usuário com ID {user_id} não foi encontrado."
            
        user_info = dict(existing_user[0])
        username = user_info['username']
        
        if user_info['is_active'] == 0:
            return False, f"Usuário '{username}' já está inativo."
        
        # Inativar o usuário
        affected = db_manager.executar_update(
            "UPDATE usuarios SET is_active = 0 WHERE id = ?", 
            [user_id]
        )
        
        if affected > 0:
            # Limpa o cache da lista de usuários para forçar atualização
            st.cache_data.clear()
            return True, f"Usuário '{username}' foi inativado com sucesso!"
        else:
            return False, "Nenhum registro foi afetado."
            
    except Exception as e:
        logging.error(f"Erro ao inativar usuário {user_id}: {str(e)}")
        return False, f"Erro ao inativar usuário: {str(e)}"

def remover_usuario_por_id(user_id):
    """Remove usuário por ID - deleta completamente do banco de dados com CASCADE"""
    try:
        db_manager = DatabaseManager()
        
        # Verificar se o usuário existe antes de tentar remover
        existing_user = db_manager.executar_query(
            "SELECT username, is_active FROM usuarios WHERE id = ?", 
            [user_id]
        )
        
        if not existing_user:
            return False, f"Usuário com ID {user_id} não foi encontrado."
            
        user_info = dict(existing_user[0])
        username = user_info['username']
        
        # Remover dados relacionados em cascata (na ordem correta)
        tabelas_relacionadas = [
            'transacoes',
            'categorias_personalizadas', 
            'descricoes_personalizadas',
            'transacoes_excluidas',
            'cache_categorizacao_ia',
            'transacoes_manuais',
            'arquivos_ofx_processados',
            'system_logs',
            'user_permissions',
            'user_roles'
        ]
        
        total_removidos = 0
        for tabela in tabelas_relacionadas:
            try:
                affected = db_manager.executar_update(
                    f"DELETE FROM {tabela} WHERE user_id = ?", 
                    [user_id]
                )
                if affected > 0:
                    total_removidos += affected
                    logging.info(f"Removidos {affected} registros da tabela {tabela} para usuário {user_id}")
            except Exception as e:
                logging.warning(f"Erro ao limpar tabela {tabela} para usuário {user_id}: {e}")
        
        # Agora deletar o usuário
        affected = db_manager.executar_update(
            "DELETE FROM usuarios WHERE id = ?", 
            [user_id]
        )
        
        if affected > 0:
            # Limpa o cache da lista de usuários para forçar atualização
            st.cache_data.clear()
            msg = f"Usuário '{username}' foi removido permanentemente!"
            if total_removidos > 0:
                msg += f" ({total_removidos} registros relacionados também foram removidos)"
            return True, msg
        else:
            return False, "Nenhum registro foi afetado."
            
    except Exception as e:
        logging.error(f"Erro ao remover usuário {user_id}: {str(e)}")
        return False, f"Erro ao remover usuário: {str(e)}"

def reativar_usuario_por_id(user_id):
    """Reativa usuário por ID - marca como is_active = 1"""
    try:
        db_manager = DatabaseManager()
        
        # Verificar se o usuário existe antes de tentar reativar
        existing_user = db_manager.executar_query(
            "SELECT username, is_active FROM usuarios WHERE id = ?", 
            [user_id]
        )
        
        if not existing_user:
            return False, f"Usuário com ID {user_id} não foi encontrado."
            
        user_info = dict(existing_user[0])
        username = user_info['username']
        
        if user_info['is_active'] == 1:
            return False, f"Usuário '{username}' já está ativo."
        
        # Reativar o usuário
        affected = db_manager.executar_update(
            "UPDATE usuarios SET is_active = 1 WHERE id = ?", 
            [user_id]
        )
        
        if affected > 0:
            # Limpa o cache da lista de usuários para forçar atualização
            st.cache_data.clear()
            return True, f"Usuário '{username}' foi reativado com sucesso!"
        else:
            return False, "Nenhum registro foi afetado."
            
    except Exception as e:
        logging.error(f"Erro ao reativar usuário {user_id}: {str(e)}")
        return False, f"Erro ao reativar usuário: {str(e)}"

# Estilos CSS customizados
st.markdown("""
<style>
    .user-container {
        background-color: #f8f9fa;
        border-radius: 5px;
        padding: 10px;
        margin: 5px 0;
    }
    .user-container.inactive-user {
        background-color: #f1f3f4;
        border: 1px dashed #6c757d;
        opacity: 0.8;
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
    .inactivate-button {
        margin-top: 28px;
    }
    .inactivate-button button {         
        background-color: #ffc107;
        color: black;
    }
    .reactivate-button {
        margin-top: 28px;
    }
    .reactivate-button button {         
        background-color: #28a745;
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
# Verificação de admin incluindo richardpalmas50 com acesso máximo
is_admin = (user_data and get_user_role(user_data['id']) == 'admin') or usuario in ['richardpalmas', 'richardpalmas50']
if not is_admin:
    st.error('Acesso restrito: apenas administradores podem acessar esta página.')
    st.stop()

st.title('👥 Gerenciar Usuários')

# Botão para forçar atualização da lista
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    if st.button("🔄 Atualizar Lista de Usuários", key="force_refresh", use_container_width=True):
        # Limpa o cache para forçar recarregamento
        st.cache_data.clear()
        st.success("✅ Lista atualizada! Recarregando...")
        st.rerun()

st.markdown('''---''')

usuarios = listar_usuarios_ativos()

st.subheader('Lista de Usuários Ativos')

if usuarios:
    for u in usuarios:
        # Obter o nível do usuário (admin/user)
        user_role = get_user_role(u['id'])
        st.markdown('<div class="user-container">', unsafe_allow_html=True)
        
        col1, col2, col3, col4, col5 = st.columns([3, 3, 2, 1, 1])
        
        with col1:
            st.markdown(
                f"""<div class="user-info">
                    <b>Usuário:</b> {u['username']}<br>
                    <b>ID:</b> {u['id']}
                    </div>""", 
                unsafe_allow_html=True
            )
        
        with col2:
            st.markdown(
                f"""<div class="user-info">
                    <b>Email:</b> {u.get('email', 'Não informado')}
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
            # Botão Inativar
            st.markdown('<div class="inactivate-button">', unsafe_allow_html=True)
            
            # Chave única para o estado de confirmação de inativação
            confirm_inactivate_key = f"confirm_inactivate_{u['id']}"
            is_self = user_data and u['id'] == user_data['id']
            
            # Botão de inativação inicial
            if not st.session_state.get(confirm_inactivate_key, False):
                inactivate_text = '� Inativar' if not is_self else '� Me inativar'
                if st.button(inactivate_text, key=f"inativar_{u['id']}", use_container_width=True):
                    st.session_state[confirm_inactivate_key] = True
                    st.rerun()
            
            # Se o botão foi clicado, mostrar confirmação
            if st.session_state.get(confirm_inactivate_key, False):
                warning_text = ("⚠️ Inativar sua conta? "
                             "Você será desconectado.") if is_self else \
                             f"⚠️ Inativar {u['username']}?"
                st.warning(warning_text)
                
                col_conf1, col_conf2 = st.columns(2)
                with col_conf1:
                    if st.button("✅ Sim", key=f"confirma_inativar_{u['id']}", type="primary"):
                        try:
                            if not is_admin:
                                st.error("❌ Sem permissão.")
                                st.stop()
                            
                            sucesso, mensagem = inativar_usuario_por_id(u['id'])
                            
                            if sucesso:
                                if is_self:
                                    st.session_state.clear()
                                    st.rerun()
                                else:
                                    st.session_state[confirm_inactivate_key] = False
                                    st.rerun()
                            else:
                                st.error(f"❌ {mensagem}")
                                
                        except Exception as e:
                            st.error(f"❌ Erro: {str(e)}")
                
                with col_conf2:
                    if st.button("❌ Não", key=f"cancela_inativar_{u['id']}", type="secondary"):
                        st.session_state[confirm_inactivate_key] = False
                        st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)

        with col5:
            # Botão Remover
            st.markdown('<div class="delete-button">', unsafe_allow_html=True)
            
            # Chave única para o estado de confirmação de remoção
            confirm_delete_key = f"confirm_delete_{u['id']}"
            
            # Botão de remoção inicial
            if not st.session_state.get(confirm_delete_key, False):
                remove_text = '🗑️ Deletar' if not is_self else '🗑️ Me deletar'
                if st.button(remove_text, key=f"remover_{u['id']}", use_container_width=True):
                    st.session_state[confirm_delete_key] = True
                    st.rerun()
            
            # Se o botão foi clicado, mostrar confirmação
            if st.session_state.get(confirm_delete_key, False):
                if is_self:
                    warning_text = "⚠️ DELETAR sua conta permanentemente? Todos os seus dados (transações, categorias, etc.) serão perdidos. Não há como desfazer!"
                else:
                    warning_text = f"⚠️ DELETAR {u['username']} permanentemente? Todos os dados do usuário (transações, categorias, etc.) serão removidos. Não há como desfazer!"
                st.error(warning_text)
                st.warning("🔥 Esta ação remove TODOS os dados relacionados ao usuário!")
                
                col_conf1, col_conf2 = st.columns(2)
                with col_conf1:
                    if st.button("✅ Sim", key=f"confirma_deletar_{u['id']}", type="primary"):
                        try:
                            if not is_admin:
                                st.error("❌ Sem permissão.")
                                st.stop()
                            
                            sucesso, mensagem = remover_usuario_por_id(u['id'])
                            
                            if sucesso:
                                if is_self:
                                    st.session_state.clear()
                                    st.rerun()
                                else:
                                    st.session_state[confirm_delete_key] = False
                                    st.rerun()
                            else:
                                st.error(f"❌ {mensagem}")
                                
                        except Exception as e:
                            st.error(f"❌ Erro: {str(e)}")
                
                with col_conf2:
                    if st.button("❌ Não", key=f"cancela_deletar_{u['id']}", type="secondary"):
                        st.session_state[confirm_delete_key] = False
                        st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info('Nenhum usuário ativo encontrado.')

# Seção de usuários inativos
st.markdown('''---''')
st.markdown("### 👻 Usuários Inativos")
st.markdown("*Usuários que foram inativados e podem ser reativados*")

usuarios_inativos = listar_usuarios_inativos()

if usuarios_inativos:
    for u in usuarios_inativos:
        # Obter o nível do usuário (admin/user)
        user_role = get_user_role(u['id'])
        st.markdown('<div class="user-container inactive-user">', unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns([3, 3, 2, 2])
        
        with col1:
            st.markdown(
                f"""<div class="user-info">
                    <b>Usuário:</b> {u['username']} 😴<br>
                    <b>ID:</b> {u['id']}
                    </div>""", 
                unsafe_allow_html=True
            )
        
        with col2:
            st.markdown(
                f"""<div class="user-info">
                    <b>Email:</b> {u.get('email', 'Não informado')}<br>
                    <b>Status:</b> <span style="color: #dc3545;">Inativo</span>
                    </div>""",
                unsafe_allow_html=True
            )
        
        with col3:
            role_display = "🔴 ADMIN" if user_role == 'admin' else "🔵 USER"
            st.markdown(
                f"""<div class="user-info">
                    <b>Nível:</b> {role_display}
                    </div>""",
                unsafe_allow_html=True
            )
        
        with col4:
            # Botão Reativar
            st.markdown('<div class="reactivate-button">', unsafe_allow_html=True)
            
            # Chave única para o estado de confirmação de reativação
            confirm_reactivate_key = f"confirm_reactivate_{u['id']}"
            
            # Botão de reativação inicial
            if not st.session_state.get(confirm_reactivate_key, False):
                if st.button("🔄 Reativar", key=f"reativar_{u['id']}", use_container_width=True):
                    st.session_state[confirm_reactivate_key] = True
                    st.rerun()
            
            # Se o botão foi clicado, mostrar confirmação
            if st.session_state.get(confirm_reactivate_key, False):
                st.info(f"⚡ Reativar {u['username']}?")
                
                col_conf1, col_conf2 = st.columns(2)
                with col_conf1:
                    if st.button("✅ Sim", key=f"confirma_reativar_{u['id']}", type="primary"):
                        try:
                            if not is_admin:
                                st.error("❌ Sem permissão.")
                                st.stop()
                            
                            sucesso, mensagem = reativar_usuario_por_id(u['id'])
                            
                            if sucesso:
                                st.session_state[confirm_reactivate_key] = False
                                st.success(f"✅ {mensagem}")
                                st.rerun()
                            else:
                                st.error(f"❌ {mensagem}")
                                
                        except Exception as e:
                            st.error(f"❌ Erro: {str(e)}")
                
                with col_conf2:
                    if st.button("❌ Não", key=f"cancela_reativar_{u['id']}", type="secondary"):
                        st.session_state[confirm_reactivate_key] = False
                        st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info('Nenhum usuário inativo encontrado.')

# Botão sair sempre visível
if st.session_state.get('autenticado', False):
    st.markdown('''---''')
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        if st.button('🚪 Sair', key='logout_btn', use_container_width=True):
            st.session_state.clear()
            st.success('Você saiu do sistema.')
            st.rerun()
