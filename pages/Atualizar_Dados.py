import streamlit as st
import os
from pathlib import Path
from utils.ofx_reader import OFXReader
from utils.auth import verificar_autenticacao
import pandas as pd

st.set_page_config(page_title="Atualizar Dados", layout="wide")

# Verificação de autenticação
verificar_autenticacao()
usuario = st.session_state.get('usuario', 'default')

st.title("🔄 Atualizar Dados")

st.markdown("""
Faça upload dos seus arquivos OFX para atualizar suas faturas e extratos.
""")

# Upload de faturas
def handle_upload(files, pasta_destino):
    pasta = Path(pasta_destino)
    pasta.mkdir(exist_ok=True)
    for file in files:
        file_path = pasta / file.name
        with open(file_path, "wb") as f:
            f.write(file.getbuffer())
    st.success(f"{len(files)} arquivo(s) salvo(s) em '{pasta_destino}' com sucesso!")

st.header("📥 Upload de Faturas")
fatura_files = st.file_uploader(
    "Selecione uma ou mais faturas (.ofx)",
    type=["ofx"],
    accept_multiple_files=True,
    key="fatura_upload"
)
if fatura_files:
    handle_upload(fatura_files, "faturas")

st.header("📥 Upload de Extratos")
extrato_files = st.file_uploader(
    "Selecione um ou mais extratos (.ofx)",
    type=["ofx"],
    accept_multiple_files=True,
    key="extrato_upload"
)
if extrato_files:
    handle_upload(extrato_files, "extratos")

# Visualização dos arquivos já carregados
col_extratos, col_faturas = st.columns([1, 1], gap="large")

custom_css = '''
<style>
.file-table {width:100%; border-collapse:collapse; margin-bottom:1em; table-layout:fixed;}
.file-table th, .file-table td {padding:12px 18px; border:none; text-align:left; font-size:1.08em; vertical-align:middle;}
.file-table th {background:#f3f6fa; color:#222; font-weight:700; border-bottom:2px solid #e0e0e0; letter-spacing:0.5px;}
.file-row {background:#fff; box-shadow:0 2px 8px rgba(0,0,0,0.06); border-radius:8px; transition:box-shadow 0.2s, background 0.2s;}
.file-row:hover {background:#eaf6ff; box-shadow:0 4px 16px rgba(0,0,0,0.10);}
.remove-btn {display:block; margin:auto; color:#fff; background:linear-gradient(90deg,#e74c3c 60%,#c0392b 100%); border:none; border-radius:5px; padding:7px 22px; cursor:pointer; font-size:1em; font-weight:600; transition:background 0.2s, box-shadow 0.2s; box-shadow:0 1px 4px rgba(231,76,60,0.10);}
.remove-btn:hover {background:linear-gradient(90deg,#c0392b 60%,#e74c3c 100%); box-shadow:0 2px 8px rgba(231,76,60,0.18);}
.file-name {font-family: 'Segoe UI', Arial, sans-serif; font-size:1.10em; color:#1a1a1a; letter-spacing:0.2px; word-break:break-all;}
.file-table th:nth-child(2), .file-table td:nth-child(2) {width:130px; max-width:130px; text-align:center;}
</style>
'''
st.markdown(custom_css, unsafe_allow_html=True)

with col_extratos:
    st.header("📄 Extratos já carregados")
    extratos_dir = Path("extratos")
    extrato_files = sorted([f.name for f in extratos_dir.glob("*.ofx")])
    if extrato_files:
        st.markdown("<table class='file-table'><tr><th>Arquivo</th><th style='width:130px;'>Ação</th></tr>", unsafe_allow_html=True)
        for file in extrato_files:
            btn_key = f"remover_extrato_{file}"
            remove_btn_html = f"<button class='remove-btn' onclick=\"window.location.search='?{btn_key}=1'\">🗑️ Remover</button>"
            st.markdown(f"<tr class='file-row'><td class='file-name'>{file}</td><td style='text-align:center; vertical-align:middle;'>{remove_btn_html}</td></tr>", unsafe_allow_html=True)
            # Checagem para remoção via query string
            import urllib.parse
            query_params = st.query_params
            if btn_key in query_params:
                (extratos_dir / file).unlink(missing_ok=True)
                st.success(f"Arquivo '{file}' removido com sucesso!")
                st.query_params.clear()  # Limpa a query
                st.rerun()
        st.markdown("</table>", unsafe_allow_html=True)
    else:
        st.info("Nenhum extrato carregado.")

with col_faturas:
    st.header("📄 Faturas já carregadas")
    faturas_dir = Path("faturas")
    fatura_files = sorted([f.name for f in faturas_dir.glob("*.ofx")])
    if fatura_files:
        st.markdown("<table class='file-table'><tr><th>Arquivo</th><th style='width:130px;'>Ação</th></tr>", unsafe_allow_html=True)
        for file in fatura_files:
            btn_key = f"remover_fatura_{file}"
            remove_btn_html = f"<button class='remove-btn' onclick=\"window.location.search='?{btn_key}=1'\">🗑️ Remover</button>"
            st.markdown(f"<tr class='file-row'><td class='file-name'>{file}</td><td style='text-align:center; vertical-align:middle;'>{remove_btn_html}</td></tr>", unsafe_allow_html=True)
            query_params = st.query_params
            if btn_key in query_params:
                (faturas_dir / file).unlink(missing_ok=True)
                st.success(f"Arquivo '{file}' removido com sucesso!")
                st.query_params.clear()
                st.rerun()
        st.markdown("</table>", unsafe_allow_html=True)
    else:
        st.info("Nenhuma fatura carregada.")
