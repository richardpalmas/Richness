import streamlit as st
import os
import hashlib
from database import get_connection, create_tables
from utils.config import PROFILE_PICS_DIR

st.set_page_config(page_title="Cadastro", layout="wide")

# Criar diretório se não existir
os.makedirs(PROFILE_PICS_DIR, exist_ok=True)

# Inicializar banco
create_tables()

@st.cache_data(ttl=60)
def usuario_existe_db(username):
    """Verifica se usuário já existe no banco - com cache"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT 1 FROM usuarios WHERE usuario = ?', (username,))
    return cur.fetchone() is not None

def hash_senha(senha):
    """Hash seguro da senha"""
    return hashlib.sha256(senha.encode()).hexdigest()

def cadastrar_usuario_db(nome, usuario, senha, email, profile_pic_path):
    """Cadastra usuário no banco com senha hasheada"""
    conn = get_connection()
    cur = conn.cursor()
    senha_hash = hash_senha(senha)
    cur.execute('''
        INSERT INTO usuarios (nome, usuario, senha, email, profile_pic)
        VALUES (?, ?, ?, ?, ?)
    ''', (nome, usuario, senha_hash, email, profile_pic_path))
    conn.commit()
    return True

st.title('📝 Cadastro de Usuário')

# Verificar se já está autenticado
if st.session_state.get('autenticado', False):
    st.info('✅ Você já está autenticado!')
    if st.button("Ir para Home"):
        st.switch_page("Home.py")
    st.stop()

# Formulário de cadastro
with st.form('cadastro_form', clear_on_submit=True):
    col1, col2 = st.columns(2)
    
    with col1:
        nome = st.text_input('Nome completo*', placeholder="Seu nome completo")
        usuario = st.text_input('Usuário*', placeholder="Escolha um nome de usuário")
        
    with col2:
        senha = st.text_input('Senha*', type='password', placeholder="Mínimo 6 caracteres")
        email = st.text_input('Email (opcional)', placeholder="seu@email.com")
    
    foto = st.file_uploader('📷 Foto de perfil (opcional)', type=['jpg', 'jpeg', 'png'])
    
    st.markdown("*Campos obrigatórios")
    cadastrar = st.form_submit_button('✅ Cadastrar', use_container_width=True)

    if cadastrar:
        # Validações
        if not nome or not usuario or not senha:
            st.error('❌ Preencha todos os campos obrigatórios!')
        elif len(senha) < 6:
            st.error('❌ A senha deve ter pelo menos 6 caracteres!')
        elif usuario_existe_db(usuario):
            st.error('❌ Usuário já existe! Escolha outro nome.')
        else:
            try:
                # Processar foto se fornecida
                profile_pic_path = ''
                if foto is not None:
                    ext = foto.name.split('.')[-1]
                    profile_pic_path = os.path.join(PROFILE_PICS_DIR, f'{usuario}.{ext}')
                    with open(profile_pic_path, 'wb') as f:
                        f.write(foto.read())
                    profile_pic_path = os.path.relpath(profile_pic_path, os.getcwd()).replace('\\', '/')
                
                # Email padrão se não fornecido
                if not email:
                    email = f'{usuario}@email.com'
                  # Cadastrar usuário
                if cadastrar_usuario_db(nome, usuario, senha, email, profile_pic_path):
                    st.success('✅ Usuário cadastrado com sucesso!')
                    st.info('👈 Agora você pode fazer login na página inicial.')
                    # Limpar cache para atualizar dados
                    st.cache_data.clear()
                else:
                    st.error('❌ Erro interno. Tente novamente.')
                    
            except Exception as e:
                st.error(f'❌ Erro ao cadastrar: {str(e)}')

# Link para voltar ao login
st.markdown("---")
col1, col2, col3 = st.columns([1,1,1])
with col2:
    if st.button("🔙 Voltar ao Login", use_container_width=True):
        st.switch_page("Home.py")

