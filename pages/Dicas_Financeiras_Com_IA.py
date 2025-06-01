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
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.3,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        max_tokens=2000,
    )

def exibir_resumo_financeiro(saldos_info):
    """Exibe resumo financeiro otimizado"""
    saldo_positivo, saldo_negativo, contas_detalhes, saldo_total = saldos_info
    st.subheader("💰 Resumo Financeiro")
    cols = st.columns(4)
    cols[0].metric("💵 Saldo Total", formatar_valor_monetario(saldo_total))
    cols[1].metric("📈 Receitas", formatar_valor_monetario(saldo_positivo))
    cols[2].metric("📉 Dívidas", formatar_valor_monetario(abs(saldo_negativo)))
    cols[3].metric("🏦 Contas", len(contas_detalhes))

    # Alertas simples e diretos
    if saldo_total < 0:
        st.error("⚠️ Saldo negativo! Reduza gastos urgentemente.")
    elif saldo_total < 1000:
        st.warning("⚠️ Saldo baixo. Monitore seus gastos.")
    else:
        st.success("✅ Situação financeira estável!")

@st.cache_data(ttl=3600, max_entries=10)
def gerar_dicas_ia(resumo_financeiro):
    """Gera dicas personalizadas usando IA - otimizado"""
    try:
        model = get_openai_model()
        
        prompt = ChatPromptTemplate.from_template(
            """
            Baseado nestes dados financeiros, dê 3 dicas práticas e diretas:
            
            Saldo Total: {saldo_total}
            Receitas: {receitas}
            Dívidas: {dividas}
            
            Seja objetivo e prático. Máximo 200 palavras.
            """
        )
        
        chain = prompt | model | StrOutputParser()
        
        return chain.invoke({
            "saldo_total": resumo_financeiro[3],
            "receitas": resumo_financeiro[0], 
            "dividas": resumo_financeiro[1]
        })
    except Exception as e:
        return f"IA temporariamente indisponível: {str(e)}"

@st.cache_resource(ttl=300)
def get_pluggy_data():
    """Obtém dados do Pluggy com cache"""
    return PluggyConnector()

# --- INTERFACE PRINCIPAL ---
with st.spinner("Carregando seus dados financeiros..."):
    pluggy = get_pluggy_data()
    usuario = st.session_state.get('usuario', 'default')
    
    # Buscar dados básicos
    try:
        itemids_data = pluggy.load_itemids_db(usuario) if usuario else None
        saldos_info = pluggy.obter_saldo_atual(itemids_data) if itemids_data else None
        
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
                    try:
                        model = get_openai_model()
                        prompt = ChatPromptTemplate.from_template(
                            "Responda esta pergunta sobre finanças de forma simples e prática: {pergunta}"
                        )
                        chain = prompt | model | StrOutputParser()
                        resposta = chain.invoke({"pergunta": pergunta})
                        st.write("**Resposta da IA:**")
                        st.write(resposta)
                    except Exception as e:
                        st.error(f"Erro: {str(e)}")
        else:
            st.warning("⚠️ Nenhuma conexão Pluggy encontrada!")
            if st.button("➕ Conectar Contas"):
                st.switch_page("pages/Cadastro_Pluggy.py")
            
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
