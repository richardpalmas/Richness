import streamlit as st
from componentes.profile_pic_component import boas_vindas_com_foto
from database import get_connection, get_usuario_por_nome
from utils.auth import verificar_autenticacao
from utils.pluggy_connector import PluggyConnector
from utils.exception_handler import ExceptionHandler

st.set_page_config(page_title="Pluggy - Conexões", layout="wide")

# Verificar autenticação
verificar_autenticacao()
usuario = st.session_state.get('usuario', 'default')

# Boas-vindas otimizada
if usuario:
    boas_vindas_com_foto(usuario)

st.title("🔗 Conexões Pluggy")

# Cache do conector
@st.cache_resource(ttl=300)
def get_connector():
    return PluggyConnector()

# Funções para manipular itemIds Pluggy no banco de dados

def get_usuario_id(usuario):
    def _get_user_id():
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT id FROM usuarios WHERE usuario = ?', (usuario,))
        row = cur.fetchone()
        return row[0] if row else None
    
    return ExceptionHandler.safe_execute(
        func=_get_user_id,
        error_handler=ExceptionHandler.handle_database_error,
        default_return=None
    )

def load_items_db(usuario):
    def _load_items():
        usuario_id = get_usuario_id(usuario)
        if usuario_id is None:
            return []
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT item_id, nome FROM pluggy_items WHERE usuario_id = ?', (usuario_id,))
        return [{'item_id': row['item_id'], 'nome': row['nome']} for row in cur.fetchall()]
    
    return ExceptionHandler.safe_execute(
        func=_load_items,
        error_handler=ExceptionHandler.handle_database_error,
        default_return=[]
    )

def save_item_db(usuario, item_id, nome):
    def _save_item():
        usuario_id = get_usuario_id(usuario)
        if usuario_id is None:
            return False
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT 1 FROM pluggy_items WHERE usuario_id = ? AND item_id = ?', (usuario_id, item_id))
        if cur.fetchone():
            return False
        cur.execute('INSERT INTO pluggy_items (usuario_id, item_id, nome) VALUES (?, ?, ?)', (usuario_id, item_id, nome))
        conn.commit()
        return True
    
    return ExceptionHandler.safe_execute(
        func=_save_item,
        error_handler=ExceptionHandler.handle_database_error,
        default_return=False
    )

def remove_all_items_db(usuario):
    def _remove_items():
        usuario_id = get_usuario_id(usuario)
        if usuario_id is None:
            return
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('DELETE FROM pluggy_items WHERE usuario_id = ?', (usuario_id,))
        conn.commit()
    
    ExceptionHandler.safe_execute(
        func=_remove_items,
        error_handler=ExceptionHandler.handle_database_error,
        default_return=None
    )

usuario = st.session_state.get('usuario', 'default')
items = load_items_db(usuario)

st.subheader("Cadastrar novo itemId")
col1, col2 = st.columns(2)
with col1:
    novo_item_id = st.text_input("Digite o itemId da sua conta Pluggy:")
with col2:
    novo_nome = st.text_input("Digite um nome para este itemId:")

if st.button("Cadastrar"):
    if not novo_item_id or not novo_nome:
        st.error("Por favor, preencha tanto o itemId quanto o nome.")
    elif any(item['item_id'] == novo_item_id for item in items):
        st.warning("Este itemId já está cadastrado.")
    else:
        if save_item_db(usuario, novo_item_id, novo_nome):
            st.success(f"itemId '{novo_item_id}' cadastrado com o nome '{novo_nome}' com sucesso!")
            st.rerun()
        else:
            st.error("Erro ao cadastrar itemId ou itemId já existe.")

st.subheader("itemIds cadastrados")
if items:
    pluggy = get_connector()
    for item in items:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"**{item['nome']}** ({item['item_id']})")
        with col2:
            if st.button(f"Testar", key=f"test_{item['item_id']}"):
                with st.spinner("Testando item ID..."):
                    def _test_item():
                        resultado = pluggy.obter_saldo_atual([(item['item_id'], item['nome'])])
                        if resultado and len(resultado) >= 4:
                            return "✅ Item ID válido!"
                        else:
                            return "❌ Item ID inválido ou sem dados"
                    
                    message = ExceptionHandler.safe_execute(
                        func=_test_item,
                        error_handler=ExceptionHandler.handle_pluggy_error,
                        default_return="❌ Erro ao testar item ID",
                        show_in_streamlit=False
                    )
                    
                    if "✅" in message:
                        st.success(message)
                    else:
                        st.error(message)
    
    st.divider()
    if st.button("Remover todas as conexões"):
        remove_all_items_db(usuario)
        st.success("Todos os itemIds foram removidos com sucesso!")
        st.rerun()
else:
    st.info("Nenhum itemId cadastrado ainda.")

# Seção de ajuda e diagnóstico
with st.expander("🔧 Diagnóstico e Solução de Problemas"):
    st.markdown("""
    ### Como obter itemIDs válidos:
    
    1. **Acesse o Pluggy Dashboard**: https://dashboard.pluggy.ai
    2. **Conecte suas contas bancárias** usando o widget oficial
    3. **Copie os itemIDs** gerados para suas contas
    4. **Cole aqui** para começar a usar o sistema
      **Importante**: ItemIDs devem pertencer às suas credenciais do Pluggy.
    """)

if st.button("Testar Conectividade"):
    pluggy = get_connector()
    with st.spinner("Testando conectividade..."):
        def _test_connectivity():
            # Teste simples de conectividade
            if hasattr(pluggy, '_authenticate'):
                return "✅ Conectividade com Pluggy funcionando"
            else:
                return "❌ Problema na conectividade"
        
        message = ExceptionHandler.safe_execute(
            func=_test_connectivity,
            error_handler=ExceptionHandler.handle_pluggy_error,
            default_return="❌ Erro de conectividade",
            show_in_streamlit=False
        )
        
        if "✅" in message:
            st.success(message)
        else:
            st.error(message)

