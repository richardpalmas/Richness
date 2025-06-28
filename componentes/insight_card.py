import streamlit as st
import base64
import os
import re
import html

def img_to_base64(path):
    if not os.path.exists(path):
        return ''
    with open(path, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def exibir_insight_card(
    avatar_path: str,
    nome_ia: str,
    saudacao: str | None = None,
    tipo: str = 'neutro',  # 'positivo', 'negativo', 'alerta', 'neutro'
    titulo: str = '',
    valor: str = '',
    comentario: str = '',
    assinatura: str = '',
    gradiente: str | None = None
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
    
    # Processar comentário - limpar completamente qualquer HTML e saudações
    def processar_comentario(texto):
        if not texto:
            return ''
        
        # Converter para string
        texto_str = str(texto)
        
        # Remover TODAS as tags HTML (incluindo <div>, <b>, etc.)
        texto_limpo = re.sub(r'<[^>]*>', '', texto_str)
        
        # Remover caracteres especiais de markdown
        texto_limpo = re.sub(r'\*\*([^*]+)\*\*', r'\1', texto_limpo)  # **texto** -> texto
        texto_limpo = re.sub(r'\*([^*]+)\*', r'\1', texto_limpo)      # *texto* -> texto
        texto_limpo = texto_limpo.replace('&nbsp;', ' ')
        texto_limpo = texto_limpo.replace('&amp;', '&')
        
        # Remover saudações no início do texto
        # Padrões de saudação a serem removidos
        padroes_saudacao = [
            r'^Olá[,!]?\s*[a-zA-Z0-9_-]*[,!]?\s*',  # "Olá, nome!" ou "Olá!"
            r'^Oi[,!]?\s*[a-zA-Z0-9_-]*[,!]?\s*',   # "Oi, nome!" ou "Oi!"
            r'^Hello[,!]?\s*[a-zA-Z0-9_-]*[,!]?\s*', # "Hello, nome!" ou "Hello!"
            r'^Bom dia[,!]?\s*[a-zA-Z0-9_-]*[,!]?\s*', # "Bom dia, nome!"
            r'^Boa tarde[,!]?\s*[a-zA-Z0-9_-]*[,!]?\s*', # "Boa tarde, nome!"
            r'^Boa noite[,!]?\s*[a-zA-Z0-9_-]*[,!]?\s*', # "Boa noite, nome!"
            r'^E aí[,!]?\s*[a-zA-Z0-9_-]*[,!]?\s*',  # "E aí, nome!"
        ]
        
        for padrao in padroes_saudacao:
            texto_limpo = re.sub(padrao, '', texto_limpo, flags=re.IGNORECASE)
        
        # Limitar tamanho
        texto_limitado = texto_limpo[:250] + ('...' if len(texto_limpo) > 250 else '')
        
        # Limpar espaços extras
        texto_final = ' '.join(texto_limitado.split())
        
        return texto_final
    
    comentario_limpo = processar_comentario(comentario)
    
    # Usar st.html() para garantir renderização correta
    card_id = f"insight_card_{abs(hash(str(titulo) + str(valor)))}"
    
    # HTML completo do card
    card_html = f"""
    <style>
    #{card_id} {{
        background: {gradiente_bg};
        padding: 18px 22px;
        border-radius: 14px;
        margin: 12px 0;
        color: {cor_texto};
        box-shadow: 0 2px 10px rgba(0,0,0,0.10);
        position: relative;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }}
    #{card_id} .avatar-section {{
        display: flex;
        align-items: center;
        gap: 16px;
        margin-bottom: 8px;
    }}
    #{card_id} .avatar-section img {{
        border-radius: 50%;
        border: 2.5px solid #fff;
        box-shadow: 0 2px 8px rgba(102,126,234,0.12);
        width: 64px;
        height: 64px;
        object-fit: cover;
    }}
    #{card_id} .nome-ia {{
        font-size: 1.15em;
        font-weight: bold;
        color: {cor_texto};
    }}
    #{card_id} .titulo {{
        font-size: 1.18em;
        font-weight: 600;
        margin-bottom: 2px;
        color: {cor_texto};
    }}
    #{card_id} .valor {{
        font-size: 1.35em;
        font-weight: bold;
        margin-bottom: 6px;
        color: {cor_texto};
    }}
    #{card_id} .comentario {{
        font-size: 1.01em;
        margin: 8px 0 4px 0;
        color: {cor_texto};
        font-style: italic;
        min-height: 24px;
        line-height: 1.4;
    }}
    #{card_id} .assinatura {{
        text-align: right;
        font-size: 0.98em;
        color: {cor_texto};
        margin-top: 10px;
        opacity: 0.92;
    }}
    </style>
    
    <div id="{card_id}">
        <div class="avatar-section">
            <img src="data:image/png;base64,{avatar_b64}" alt="avatar"/>
            <span class="nome-ia">{html.escape(str(nome_ia))}</span>
        </div>
        {f'<div style="font-size: 1.02em; margin-bottom: 8px;">{html.escape(str(saudacao))}</div>' if saudacao else ''}
        <div class="titulo"><b>{html.escape(str(titulo))}</b></div>
        <div class="valor"><b>{html.escape(str(valor))}</b></div>
        <div class="comentario">{html.escape(comentario_limpo)}</div>
        <div class="assinatura">— {html.escape(str(assinatura))}</div>
    </div>
    """
    
    # Usar st.html() para renderização garantida
    try:
        st.html(card_html)
    except:
        # Fallback para st.markdown se st.html() não estiver disponível
        st.markdown(card_html, unsafe_allow_html=True)