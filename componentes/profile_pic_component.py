# Este arquivo é um componente e não deve ser listado como página do Streamlit
import streamlit as st
import os
from PIL import Image
import base64
import io
from database import get_connection, query_with_cache
from utils.config import PROFILE_PICS_DIR
import functools

# Cache para imagens de perfil para evitar carregamentos repetidos
_profile_pic_cache = {}

@functools.lru_cache(maxsize=32)
def image_to_base64(img_path):
    """
    Converte uma imagem em base64 com cache para evitar processamento repetido
    """
    try:
        img = Image.open(img_path)
        # Redimensionar imagem para um tamanho máximo razoável (otimização)
        if img.width > 256 or img.height > 256:
            img.thumbnail((256, 256), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=85, optimize=True)
        byte_im = buf.getvalue()
        return base64.b64encode(byte_im).decode()
    except Exception:
        return None

def get_profile_pic_path(usuario):
    """
    Função otimizada para buscar o caminho da foto de perfil do usuário,
    usando cache de consulta de banco de dados.
    """
    # Usar função de cache para buscar apenas o campo necessário
    query = "SELECT profile_pic FROM usuarios WHERE usuario = ?"
    result = query_with_cache(query, (usuario,), ttl=3600)  # Cache por 1 hora
    return result[0]['profile_pic'] if result else ''

def foto_perfil_inline(usuario, tamanho=64):
    """
    Exibe a foto de perfil do usuário inline com otimização de performance
    """
    # Verificar cache primeiro
    cache_key = f"{usuario}_{tamanho}"
    if cache_key in _profile_pic_cache:
        return _profile_pic_cache[cache_key]

    # Buscar caminho da foto do banco de dados usando função otimizada
    profile_pic_path = get_profile_pic_path(usuario)

    # Verificar se o caminho é absoluto ou relativo
    if profile_pic_path and not os.path.isabs(profile_pic_path):
        # Tornar caminho absoluto se for relativo
        profile_pic_path = os.path.join(os.getcwd(), profile_pic_path)

    if profile_pic_path and os.path.exists(profile_pic_path):
        try:
            img_b64 = image_to_base64(profile_pic_path)
            if img_b64:
                # Pré-computar o tamanho em HTML para evitar reflow do navegador
                width_height = f"width:{tamanho}px;height:{tamanho}px;"
                html_result = f"<img src='data:image/jpeg;base64,{img_b64}' class='profile-pic-hover' style='{width_height}border-radius:50%;object-fit:cover;border:2px solid #eee;background:#fff;margin-right:16px;' loading='lazy' />"
                # Salvar no cache
                _profile_pic_cache[cache_key] = html_result
                return html_result
        except Exception:
            pass

    # Imagem padrão se não houver foto ou ocorrer erro
    default_result = f"<div style='width:{tamanho}px;height:{tamanho}px;border-radius:50%;background:#fff;border:2px solid #eee;display:inline-block;margin-right:16px;'></div>"
    _profile_pic_cache[cache_key] = default_result
    return default_result

@st.cache_resource(ttl=3600)  # Cache por 1 hora
def boas_vindas_com_foto(usuario):
    """
    Exibe a foto de perfil e mensagem de boas-vindas com cache para performance
    """
    # Obter nome do usuário usando função otimizada
    query = "SELECT nome FROM usuarios WHERE usuario = ?"
    result = query_with_cache(query, (usuario,), ttl=3600)
    nome = result[0]['nome'] if result else usuario

    # Obter foto HTML
    foto_html = foto_perfil_inline(usuario)

    # Definir estilo CSS uma única vez
    if 'profile_pic_css_added' not in st.session_state:
        st.markdown("""
        <style>
        .profile-pic-hover {
            transition: transform 0.2s cubic-bezier(.4,2,.6,1);
            cursor: pointer;
        }
        .profile-pic-hover:hover {
            transform: scale(1.35);
            z-index: 10;
        }
        </style>
        """, unsafe_allow_html=True)
        st.session_state['profile_pic_css_added'] = True

    # Exibir a mensagem de boas-vindas
    st.markdown(f"""
    <div style='display:flex;align-items:center;gap:8px;'>
        {foto_html}
        <span style='font-size:1.2em;'>Bem-vindo, <b>{nome}</b>!</span>
    </div>
    """, unsafe_allow_html=True)

def limpar_cache_imagens():
    """Limpa o cache de imagens"""
    global _profile_pic_cache
    _profile_pic_cache = {}
    image_to_base64.cache_clear()
