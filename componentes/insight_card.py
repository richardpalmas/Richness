import streamlit as st
import base64
import os

def img_to_base64(path):
    if not os.path.exists(path):
        return ''
    with open(path, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def exibir_insight_card(
    avatar_path: str,
    nome_ia: str,
    saudacao: str = None,
    tipo: str = 'neutro',  # 'positivo', 'negativo', 'alerta', 'neutro'
    titulo: str = '',
    valor: str = '',
    comentario: str = '',
    assinatura: str = '',
    gradiente: str = None
):
    """
    Exibe um card de insight personalizado com avatar, saudação, título, valor, comentário e assinatura.
    """
    # Gradientes padrão por tipo
    gradientes_padrao = {
        'positivo': 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
        'negativo': 'linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%)',
        'alerta': 'linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%)',
        'neutro': 'linear-gradient(135deg, #74b9ff 0%, #0984e3 100%)',
    }
    cor_texto = '#fff' if tipo in ['positivo', 'negativo', 'neutro'] else '#856404'
    gradiente_bg = gradiente or gradientes_padrao.get(tipo, gradientes_padrao['neutro'])
    avatar_b64 = img_to_base64(avatar_path) if avatar_path else ''
    # CSS inline para o card
    st.markdown(f"""
    <style>
    .insight-card-custom {{
        background: {gradiente_bg};
        padding: 18px 22px;
        border-radius: 14px;
        margin: 12px 0;
        color: {cor_texto};
        box-shadow: 0 2px 10px rgba(0,0,0,0.10);
        position: relative;
    }}
    .insight-avatar-block {{
        display: flex;
        align-items: center;
        gap: 16px;
        margin-bottom: 8px;
    }}
    .insight-avatar-block img {{
        border-radius: 50%;
        border: 2.5px solid #fff;
        box-shadow: 0 2px 8px rgba(102,126,234,0.12);
        width: 64px;
        height: 64px;
        object-fit: cover;
    }}
    .insight-nome-ia {{
        font-size: 1.15em;
        font-weight: bold;
        color: {cor_texto};
    }}
    .insight-saudacao {{
        font-size: 1.02em;
        color: {cor_texto};
        margin-bottom: 8px;
    }}
    .insight-titulo {{
        font-size: 1.18em;
        font-weight: 600;
        margin-bottom: 2px;
        color: {cor_texto};
    }}
    .insight-valor {{
        font-size: 1.35em;
        font-weight: bold;
        margin-bottom: 6px;
        color: {cor_texto};
    }}
    .insight-comentario {{
        font-size: 1.01em;
        margin: 8px 0 4px 0;
        color: {cor_texto};
        font-style: italic;
        min-height: 24px;
    }}
    .insight-assinatura {{
        text-align: right;
        font-size: 0.98em;
        color: {cor_texto};
        margin-top: 10px;
        opacity: 0.92;
    }}
    </style>
    """, unsafe_allow_html=True)
    st.markdown(f"""
    <div class='insight-card-custom'>
        <div class='insight-avatar-block'>
            <img src='data:image/png;base64,{avatar_b64}' alt='avatar'/>
            <span class='insight-nome-ia'>{nome_ia}</span>
        </div>
        {f"<div class='insight-saudacao'>{saudacao}</div>" if saudacao else ''}
        <div class='insight-titulo'>{titulo}</div>
        {f"<div class='insight-valor'>{valor}</div>" if valor else ''}
        <div class='insight-comentario'>{comentario}</div>
        <div class='insight-assinatura'>{assinatura}</div>
    </div>
    """, unsafe_allow_html=True) 