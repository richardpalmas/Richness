import streamlit as st
import os
from pathlib import Path
import pandas as pd
from datetime import datetime

# Imports Backend V2
from utils.repositories_v2 import UsuarioRepository, TransacaoRepository
from utils.database_manager_v2 import DatabaseManager
from services.transacao_service_v2 import TransacaoService
from utils.auth import verificar_autenticacao
from utils.user_data_manager import UserDataManager

st.set_page_config(page_title="Atualizar Dados", layout="wide")

# Verificação de autenticação
verificar_autenticacao()
usuario = st.session_state.get('usuario', 'default')

st.title("🔄 Atualizar Dados")

st.markdown("""
Faça upload dos seus arquivos OFX para atualizar suas faturas e extratos.
Os dados serão isolados e seguros para seu usuário.
""")

# Função para processar uploads usando Backend V2 - VERSÃO MELHORADA
def handle_upload_v2(files, tipo_arquivo, usuario):
    """Processa upload de arquivos OFX usando Backend V2 - VERSÃO MELHORADA"""
    try:
        # Inicializar repositórios
        db_manager = DatabaseManager()
        usuario_repo = UsuarioRepository(db_manager)
        transacao_repo = TransacaoRepository(db_manager)        # Verificar se usuário existe
        user_data = usuario_repo.obter_usuario_por_username(usuario)
        if not user_data:
            st.error("❌ Usuário não encontrado")
            return False
        
        user_id = user_data['id']
        
        # Criar diretório específico do usuário
        user_dir = Path(f"user_data/{usuario}/{tipo_arquivo}")
        user_dir.mkdir(parents=True, exist_ok=True)
        
        arquivos_processados = 0
        total_transacoes = 0
        arquivos_com_erro = 0
        
        # Processar cada arquivo
        for file in files:
            try:
                # 1. Salvar arquivo no diretório do usuário
                file_path = user_dir / file.name
                with open(file_path, "wb") as f:
                    f.write(file.getbuffer())

                # 2. Processar arquivo OFX e extrair transações
                try:
                    # Usar o OFXReader existente para fazer parse do arquivo
                    from utils.ofx_reader import OFXReader
                    
                    # Criar instância do OFXReader
                    ofx_reader = OFXReader(username=usuario)
                    
                    # Fazer parse direto do arquivo
                    parsed_data = ofx_reader._parse_ofx_file(file_path)
                    
                    if parsed_data and len(parsed_data) > 0:
                        # 3. Converter para formato do banco de dados
                        transacoes_para_inserir = []
                        
                        for transacao in parsed_data:
                            try:
                                transacao_data = {
                                    'data': transacao.get('data'),
                                    'descricao': transacao.get('descricao', ''),
                                    'valor': float(transacao.get('valor', 0)),
                                    'categoria': transacao.get('categoria', 'Outros'),
                                    'origem': f"{file.name}",
                                    'hash_transacao': transacao.get('hash_transacao', ''),
                                    'tipo_conta': transacao.get('tipo_conta', 'corrente')
                                }
                                
                                transacoes_para_inserir.append(transacao_data)
                                    
                            except Exception as e:
                                continue
                        
                        # 4. Inserir transações em lote (mais eficiente)
                        if transacoes_para_inserir:
                            try:
                                transacao_repo.criar_transacoes_lote(
                                    user_id=user_id,
                                    transacoes=transacoes_para_inserir
                                )
                                
                                total_transacoes += len(transacoes_para_inserir)
                                
                            except Exception as e:
                                # Fallback: inserir uma por uma
                                transacoes_inseridas = 0
                                for transacao_data in transacoes_para_inserir:
                                    try:
                                        transacao_repo.criar_ou_atualizar_transacao(
                                            user_id=user_id,
                                            transacao=transacao_data
                                        )
                                        transacoes_inseridas += 1
                                    except Exception as e_individual:
                                        continue
                                
                                total_transacoes += transacoes_inseridas
                    
                except Exception as e:
                    arquivos_com_erro += 1
                    continue
                
                arquivos_processados += 1
                    
            except Exception as e:
                arquivos_com_erro += 1
                continue
        
        # Resultado final - MENSAGEM ÚNICA
        if arquivos_processados > 0:
            if arquivos_com_erro == 0:
                st.success(f"✅ **Upload concluído com sucesso!** {arquivos_processados} arquivo(s) processado(s) e {total_transacoes} transações importadas.")
            else:
                st.warning(f"⚠️ **Upload parcialmente concluído.** {arquivos_processados} arquivo(s) processado(s), {arquivos_com_erro} com erro(s). {total_transacoes} transações importadas.")
        else:
            st.error("❌ **Falha no upload.** Nenhum arquivo foi processado com sucesso.")
        
        # Limpar caches para forçar recarregamento
        st.cache_data.clear()
        
        return arquivos_processados > 0
            
    except Exception as e:
        st.error(f"❌ **Erro crítico:** Falha no sistema de upload.")
        return False

st.header("📥 Upload de Faturas")
fatura_files = st.file_uploader(
    "Selecione uma ou mais faturas (.ofx)",
    type=["ofx"],
    accept_multiple_files=True,
    key="fatura_upload"
)
if fatura_files:
    handle_upload_v2(fatura_files, "faturas", usuario)

st.header("📥 Upload de Extratos")
extrato_files = st.file_uploader(
    "Selecione um ou mais extratos (.ofx)",
    type=["ofx"],
    accept_multiple_files=True,
    key="extrato_upload"
)
if extrato_files:
    handle_upload_v2(extrato_files, "extratos", usuario)

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
    extratos_dir = Path(f"user_data/{usuario}/extratos")
    extrato_files = []
    if extratos_dir.exists():
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
    faturas_dir = Path(f"user_data/{usuario}/faturas")
    fatura_files = []
    if faturas_dir.exists():
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
