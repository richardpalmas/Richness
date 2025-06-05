import streamlit as st
import plotly.express as px
import pandas as pd
import functools
import os
from dotenv import load_dotenv
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

from componentes.profile_pic_component import boas_vindas_com_foto
from utils.auth import verificar_autenticacao
from utils.formatacao import formatar_valor_monetario
from utils.pluggy_connector import PluggyConnector
from utils.exception_handler import ExceptionHandler

st.set_page_config(layout="wide")

# --- AUTENTICAÇÃO E USUÁRIO ---
verificar_autenticacao()
usuario = st.session_state.get('usuario', None)

# --- BOAS-VINDAS E FOTO DE PERFIL ---
if usuario:
    boas_vindas_com_foto(usuario)

st.title("Dicas Financeiras Com IA")

st.markdown("""
Bem-vindo à página de **Dicas Financeiras com IA**!  
Aqui você encontra sugestões personalizadas, alertas e pode tirar dúvidas financeiras com o auxílio de inteligência artificial.
""")

# --- FUNÇÕES AUXILIARES ---
@functools.lru_cache(maxsize=1)
def get_openai_model():
    """Inicializa o modelo OpenAI com cache para reutilização"""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        raise ValueError("OPENAI_API_KEY não encontrada nas variáveis de ambiente")
    
    # Verificar se a API key parece válida (começa com sk- e tem tamanho adequado)
    if not api_key.startswith("sk-") or len(api_key) < 40:
        raise ValueError("OPENAI_API_KEY parece inválida. Verifique se está correta.")
    
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.3,
        max_tokens=2000
    )

def exibir_resumo_financeiro(saldos_info):
    """Exibe resumo financeiro otimizado"""
    saldo_positivo, saldo_negativo, contas_detalhes = saldos_info[:3]
    st.subheader("💰 Resumo Financeiro")
    cols = st.columns(3)
    cols[0].metric("📈 Receitas", formatar_valor_monetario(saldo_positivo))
    cols[1].metric("📉 Dívidas", formatar_valor_monetario(abs(saldo_negativo)))
    cols[2].metric("🏦 Contas", len(contas_detalhes))

    # Calcular saldo líquido corretamente
    # saldo_negativo já vem como valor negativo do pluggy_connector
    saldo_liquido = saldo_positivo + saldo_negativo
    
    # Alertas baseados no saldo líquido calculado
    if saldo_liquido < 0:
        st.error("⚠️ Saldo líquido negativo! Suas dívidas superam seus ativos disponíveis.")
    elif saldo_liquido < 1000:
        st.warning("⚠️ Saldo líquido baixo. Monitore seus gastos e considere aumentar suas reservas.")
    else:
        st.success("✅ Situação financeira estável! Você tem mais ativos que dívidas.")

@st.cache_data(ttl=3600, max_entries=10)
def gerar_dicas_ia(resumo_financeiro):
    """Gera dicas personalizadas usando IA - otimizado"""
    def _generate_tips():
        model = get_openai_model()
        
        prompt = ChatPromptTemplate.from_template(
            """
            Baseado nestes dados financeiros, dê 3 dicas práticas e diretas:
            
            Receitas: {receitas}
            Dívidas: {dividas}
            Saldo Líquido: {saldo_liquido}
            
            Seja objetivo e prático. Máximo 200 palavras.
            """
        )
        
        chain = prompt | model | StrOutputParser()
        
        saldo_positivo, saldo_negativo, contas_detalhes = resumo_financeiro[:3]
        saldo_liquido = saldo_positivo + saldo_negativo  # saldo_negativo já é negativo
        
        return chain.invoke({
            "receitas": saldo_positivo,
            "dividas": abs(saldo_negativo),
            "saldo_liquido": saldo_liquido
        })
    
    return ExceptionHandler.safe_execute(
        func=_generate_tips,
        error_handler=ExceptionHandler.handle_openai_error,
        default_return="❌ Não foi possível gerar dicas neste momento.",
        show_in_streamlit=False
    )

@st.cache_resource(ttl=300)
def get_pluggy_data():
    """Obtém dados do Pluggy com cache"""
    return PluggyConnector()

# --- INTERFACE PRINCIPAL ---
with st.spinner("Carregando seus dados financeiros..."):
    pluggy = get_pluggy_data()
    usuario = st.session_state.get('usuario', 'default')
    
    # Buscar dados básicos
    def _load_financial_data():
        itemids_data = pluggy.load_itemids_db(usuario) if usuario else None
        saldos_info = pluggy.obter_saldo_atual(itemids_data) if itemids_data else None
        return saldos_info
    
    saldos_info = ExceptionHandler.safe_execute(
        func=_load_financial_data,
        error_handler=ExceptionHandler.handle_pluggy_error,
        default_return=None,
        show_in_streamlit=True
    )
    
    if saldos_info:
        # Exibir resumo financeiro
        exibir_resumo_financeiro(saldos_info)
        
        # Seção de Dicas com IA
        st.subheader("🤖 Dicas Personalizadas da IA")
        
        if st.button("💡 Gerar Dicas"):
            with st.spinner("IA analisando sua situação financeira..."):
                dicas = gerar_dicas_ia(saldos_info)
                st.write(dicas)
            
        # Chat com IA simplificado
        st.subheader("💬 Pergunte para a IA")
        pergunta = st.text_input("Faça uma pergunta sobre finanças:")
        
        if st.button("🔍 Perguntar") and pergunta:
            with st.spinner("IA pensando..."):
                def _ask_ai():
                    model = get_openai_model()
                    prompt = ChatPromptTemplate.from_template(
                        "Responda esta pergunta sobre finanças de forma simples e prática: {pergunta}"
                    )
                    chain = prompt | model | StrOutputParser()
                    return chain.invoke({"pergunta": pergunta})
                
                resposta = ExceptionHandler.safe_execute(
                    func=_ask_ai,
                    error_handler=ExceptionHandler.handle_openai_error,
                    default_return=None,
                    show_in_streamlit=True
                )
                
                if resposta:
                    st.write("**Resposta da IA:**")
                    st.write(resposta)
    else:
        st.warning("⚠️ Nenhuma conexão Pluggy encontrada!")
        if st.button("➕ Conectar Contas"):
            st.switch_page("pages/Cadastro_Pluggy.py")
