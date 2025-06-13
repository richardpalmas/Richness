# -*- coding: utf-8 -*-
"""
🔧 Funcionalidade: Gerenciamento de transações
✅ Backend V2: Migrado para usar database_manager_v2 e repositories_v2
"""

import pandas as pd
import streamlit as st
import json
import os
import hashlib
from datetime import datetime, timedelta

# BACKEND V2 OBRIGATÓRIO - Importações exclusivas
from utils.database_manager_v2 import DatabaseManager
from utils.repositories_v2 import RepositoryManager
from services.transacao_service_v2 import TransacaoService
from utils.filtros import filtro_data, filtro_categorias, aplicar_filtros
from utils.formatacao import formatar_valor_monetario
from utils.ofx_reader import OFXReader
from utils.exception_handler import ExceptionHandler

# Configurações da página
st.set_page_config(
    page_title="Gerenciar Transações - Richness",
    page_icon="🏷️",
    layout="wide"
)

# Verificar autenticação
def verificar_autenticacao():
    if 'authenticated' not in st.session_state or not st.session_state['authenticated']:
        st.error("🔐 Acesso negado. Faça login primeiro.")
        st.stop()

verificar_autenticacao()

# Inicializar Backend V2
@st.cache_resource
def init_backend_v2_gerenciar():
    """Inicializa e retorna instâncias do Backend V2"""
    try:
        db_manager = DatabaseManager()
        repo_manager = RepositoryManager(db_manager)
        transacao_service = TransacaoService()
        
        return {
            'db_manager': db_manager,
            'repo_manager': repo_manager,
            'transacao_service': transacao_service
        }
    except Exception as e:
        st.error(f"❌ Erro ao inicializar Backend V2: {e}")
        st.stop()

backend_v2 = init_backend_v2_gerenciar()

# Constantes
CATEGORIAS_DISPONIVEIS = [
    "Alimentação",
    "Transporte", 
    "Saúde",
    "Educação",
    "Lazer",
    "Casa e Utilidades",
    "Vestuário",
    "Investimentos",
    "Transferências",
    "Salário",
    "Freelance",
    "Compras Online",
    "Combustível",
    "Farmácia",
    "Supermercado",    "Restaurante",
    "Academia",
    "Streaming",
    "Telefone",
    "Internet",
    "Banco/Taxas",
    "Outros"
]

# Importar funções para caminhos isolados por usuário
from utils.config import (
    get_cache_categorias_file,
    get_categorias_personalizadas_file,
    get_transacoes_excluidas_file,
    get_descricoes_personalizadas_file,
    get_transacoes_manuais_file,
    get_current_user
)

# Funções utilitárias para hash de transação (compatibilidade)
def gerar_hash_transacao(row):
    """Gera um hash único para identificar uma transação de forma consistente"""
    # Usar data, descrição e valor para criar um identificador único
    data_str = row["Data"].strftime("%Y-%m-%d") if hasattr(row["Data"], 'strftime') else str(row["Data"])
    chave = f"{data_str}|{row['Descrição']}|{row['Valor']}"
    return hashlib.md5(chave.encode()).hexdigest()

# Função principal para carregar transações usando Backend V2
@st.cache_data(ttl=300, show_spinner="Carregando transações...")
def carregar_transacoes_v2(usuario, periodo_dias=365):
    """Carrega todas as transações usando Backend V2 com personalizações"""
    try:
        transacao_service = backend_v2['transacao_service']
        
        # Carregar transações do usuário
        df_transacoes = transacao_service.listar_transacoes_usuario(usuario, limite=5000)
        
        if not df_transacoes.empty:
            # Converter colunas para o formato esperado pela página (compatibilidade)
            df_transacoes = df_transacoes.rename(columns={
                'data': 'Data',
                'descricao': 'Descrição',
                'valor': 'Valor',
                'categoria': 'Categoria',
                'tipo': 'Tipo',
                'origem': 'Origem',
                'conta': 'Conta'
            })
            
            # Garantir que as colunas estão no formato correto
            df_transacoes["Data"] = pd.to_datetime(df_transacoes["Data"])
            df_transacoes["Valor"] = pd.to_numeric(df_transacoes["Valor"], errors="coerce")
            
            # Remover valores nulos
            df_transacoes = df_transacoes.dropna(subset=["Valor"])
            
            # Aplicar filtro de período se especificado
            if periodo_dias > 0:
                data_limite = datetime.now() - timedelta(days=periodo_dias)
                df_transacoes = df_transacoes[df_transacoes["Data"] >= data_limite]
            
            # Aplicar categorizações personalizadas do usuário (compatibilidade com arquivos JSON)
            cache = carregar_cache_categorias()
            if cache:
                def aplicar_categoria_personalizada(row):
                    descricao_normalizada = row["Descrição"].lower().strip()
                    if descricao_normalizada in cache:
                        return cache[descricao_normalizada]
                    return row.get("Categoria", "Outros")
                
                df_transacoes["Categoria"] = df_transacoes.apply(aplicar_categoria_personalizada, axis=1)
            
            # Adicionar coluna de notas a partir de descrições personalizadas
            descricoes = carregar_descricoes_personalizadas()
            if descricoes:
                def obter_descricao_personalizada(row):
                    hash_transacao = gerar_hash_transacao(row)
                    return descricoes.get(hash_transacao, "")
                df_transacoes["Nota"] = df_transacoes.apply(obter_descricao_personalizada, axis=1)
            else:
                df_transacoes["Nota"] = ""
            
            # Filtrar transações excluídas
            df_transacoes = filtrar_transacoes_excluidas(df_transacoes)
            
            # Ordenar por data (mais recente primeiro)
            df_transacoes = df_transacoes.sort_values("Data", ascending=False)
        
        return df_transacoes
        
    except Exception as e:
        st.error(f"❌ Erro ao carregar transações: {e}")
        return pd.DataFrame()

# Manter funções legadas para compatibilidade com arquivos JSON existentes

def carregar_cache_categorias():
    """Carrega o cache de categorizações personalizadas do usuário"""
    cache_file = get_cache_categorias_file()
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def salvar_cache_categorias(cache):
    """Salva o cache de categorizações personalizadas"""
    try:
        cache_file = get_cache_categorias_file()
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar categorizações: {e}")
        return False

def carregar_categorias_personalizadas():
    """Carrega as categorias personalizadas criadas pelo usuário"""
    categorias_file = get_categorias_personalizadas_file()
    if os.path.exists(categorias_file):
        try:
            with open(categorias_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def salvar_categorias_personalizadas(categorias):
    """Salva as categorias personalizadas"""
    try:
        categorias_file = get_categorias_personalizadas_file()
        with open(categorias_file, 'w', encoding='utf-8') as f:
            json.dump(categorias, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar categorias personalizadas: {e}")
        return False

def get_todas_categorias():
    """Retorna todas as categorias disponíveis (padrão + personalizadas)"""
    categorias_personalizadas = carregar_categorias_personalizadas()
    todas_categorias = CATEGORIAS_DISPONIVEIS + categorias_personalizadas
    return sorted(list(set(todas_categorias)))

@st.cache_data(ttl=300)
def carregar_transacoes():
    """Carrega todas as transações disponíveis - MIGRADO PARA BACKEND V2"""
    # Redirecionar para nova função Backend V2
    usuario_atual = get_current_user()
    return carregar_transacoes_v2(usuario_atual, periodo_dias=730)  # 2 anos de dados

# Funções para gerenciar transações excluídas
def carregar_transacoes_excluidas():
    """Carrega a lista de transações excluídas pelo usuário"""
    excluidas_file = get_transacoes_excluidas_file()
    if os.path.exists(excluidas_file):
        try:
            with open(excluidas_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def salvar_transacoes_excluidas(transacoes_excluidas):
    """Salva a lista de transações excluídas"""
    try:
        excluidas_file = get_transacoes_excluidas_file()
        with open(excluidas_file, 'w', encoding='utf-8') as f:
            json.dump(transacoes_excluidas, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar transações excluídas: {e}")
        return False

def excluir_transacao(row):
    """Exclui uma transação específica adicionando-a à lista de excluídas"""
    transacoes_excluidas = carregar_transacoes_excluidas()
    hash_transacao = gerar_hash_transacao(row)
    
    if hash_transacao not in transacoes_excluidas:
        transacoes_excluidas.append(hash_transacao)
        return salvar_transacoes_excluidas(transacoes_excluidas)
    
    return True  # Já estava excluída

def restaurar_transacao(row):
    """Remove uma transação da lista de excluídas (restaura)"""
    transacoes_excluidas = carregar_transacoes_excluidas()
    hash_transacao = gerar_hash_transacao(row)
    
    if hash_transacao in transacoes_excluidas:
        transacoes_excluidas.remove(hash_transacao)
        return salvar_transacoes_excluidas(transacoes_excluidas)
    
    return True  # Não estava excluída

def filtrar_transacoes_excluidas(df):
    """Filtra as transações excluídas do DataFrame"""
    if df.empty:
        return df
    
    transacoes_excluidas = carregar_transacoes_excluidas()
    if not transacoes_excluidas:
        return df
    
    # Aplicar filtro
    def nao_esta_excluida(row):
        hash_transacao = gerar_hash_transacao(row)
        return hash_transacao not in transacoes_excluidas
    
    df_filtrado = df[df.apply(nao_esta_excluida, axis=1)]
    return df_filtrado

# Funções para gerenciar descrições personalizadas
def carregar_descricoes_personalizadas():
    """Carrega o cache de descrições personalizadas do usuário"""
    descricoes_file = get_descricoes_personalizadas_file()
    if os.path.exists(descricoes_file):
        try:
            with open(descricoes_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def salvar_descricoes_personalizadas(descricoes):
    """Salva o cache de descrições personalizadas"""
    try:
        descricoes_file = get_descricoes_personalizadas_file()
        with open(descricoes_file, 'w', encoding='utf-8') as f:
            json.dump(descricoes, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar descrições personalizadas: {e}")
        return False

def obter_descricao_personalizada(row):
    """Obtém a descrição personalizada de uma transação, se existir"""
    descricoes = carregar_descricoes_personalizadas()
    hash_transacao = gerar_hash_transacao(row)
    return descricoes.get(hash_transacao, "")

def salvar_descricao_personalizada(row, descricao):
    """Salva uma descrição personalizada para uma transação"""
    descricoes = carregar_descricoes_personalizadas()
    hash_transacao = gerar_hash_transacao(row)
    
    if descricao.strip():
        # Limitar a 250 caracteres
        descricao = descricao.strip()[:250]
        descricoes[hash_transacao] = descricao
    else:
        # Remover descrição se estiver vazia
        descricoes.pop(hash_transacao, None)
    
    return salvar_descricoes_personalizadas(descricoes)

def remover_descricao_personalizada(row):
    """Remove a descrição personalizada de uma transação"""
    descricoes = carregar_descricoes_personalizadas()
    hash_transacao = gerar_hash_transacao(row)
    
    if hash_transacao in descricoes:
        descricoes.pop(hash_transacao)
        return salvar_descricoes_personalizadas(descricoes)
    
    return True  # Já estava removida

# Funções para gerenciar transações manuais
def carregar_transacoes_manuais():
    """Carrega as transações manuais criadas pelo usuário"""
    manuais_file = get_transacoes_manuais_file()
    if os.path.exists(manuais_file):
        try:
            with open(manuais_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def salvar_transacoes_manuais(transacoes):
    """Salva as transações manuais"""
    try:
        manuais_file = get_transacoes_manuais_file()
        with open(manuais_file, 'w', encoding='utf-8') as f:
            json.dump(transacoes, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar transações manuais: {e}")
        return False

def gerar_id_transacao_manual():
    """Gera um ID único para uma nova transação manual"""
    import uuid
    return f"manual_{uuid.uuid4().hex[:8]}"

def adicionar_transacao_manual(data, descricao, valor, categoria, descricao_personalizada="", tipo_pagamento="Espécie"):
    """Adiciona uma nova transação manual"""
    transacoes_manuais = carregar_transacoes_manuais()
    
    # Criar nova transação
    nova_transacao = {
        "id": gerar_id_transacao_manual(),
        "data": data.strftime("%Y-%m-%d"),
        "descricao": descricao.strip(),
        "valor": float(valor),
        "categoria": categoria,
        "tipo": "DEBIT" if valor < 0 else "CREDIT",
        "origem": "Manual",
        "tipo_pagamento": tipo_pagamento,
        "data_criacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Adicionar descrição personalizada se fornecida
    if descricao_personalizada.strip():
        nova_transacao["descricao_personalizada"] = descricao_personalizada.strip()[:250]
    
    transacoes_manuais.append(nova_transacao)
    
    return salvar_transacoes_manuais(transacoes_manuais)

def remover_transacao_manual(transacao_id):
    """Remove uma transação manual pelo ID"""
    transacoes_manuais = carregar_transacoes_manuais()
    transacoes_atualizadas = [t for t in transacoes_manuais if t.get("id") != transacao_id]
    
    if len(transacoes_atualizadas) != len(transacoes_manuais):
        return salvar_transacoes_manuais(transacoes_atualizadas)
    
    return False  # Transação não encontrada

def converter_transacoes_manuais_para_df(transacoes_manuais):
    """Converte a lista de transações manuais para DataFrame no formato padrão"""
    if not transacoes_manuais:
        return pd.DataFrame()
    
    dados = []
    for transacao in transacoes_manuais:
        dados.append({
            "Data": pd.to_datetime(transacao["data"]),
            "Descrição": transacao["descricao"],
            "Valor": transacao["valor"],
            "Categoria": transacao["categoria"],
            "Tipo": transacao["tipo"],
            "Origem": transacao["origem"],
            "Id": transacao["id"],
            "tipo_pagamento": transacao.get("tipo_pagamento", "Espécie"),
            "data_criacao": transacao.get("data_criacao", "")
        })
    
    return pd.DataFrame(dados)

# Funções para categorização automática com LLM
def configurar_openai():
    """Configura a API da OpenAI"""
    try:
        # Verificar se a chave API está configurada
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            # Tentar carregar de arquivo de configuração local
            config_file = "config_openai.json"
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    api_key = config.get("api_key")
        
        if api_key:
            return api_key
        return None
    except Exception:
        return None

def categorizar_transacoes_com_llm(df_transacoes, categorias_disponiveis):
    """Categoriza transações usando LLM"""
    api_key = configurar_openai()
    if not api_key:
        st.error("❌ API da OpenAI não configurada. Configure a chave API para usar esta funcionalidade.")
        return None
    
    try:
        # Preparar dados para envio
        transacoes_para_analisar = []
        for _, row in df_transacoes.iterrows():
            transacoes_para_analisar.append({
                "descricao": row["Descrição"],
                "valor": float(row["Valor"]),
                "categoria_atual": row["Categoria"]
            })
        
        # Criar prompt para a LLM
        prompt = f"""
        Você é um especialista em categorização de transações financeiras. Analise as transações abaixo e sugira a melhor categoria para cada uma baseado na descrição e valor.

        CATEGORIAS DISPONÍVEIS: {', '.join(categorias_disponiveis)}

        INSTRUÇÕES:
        1. Use APENAS as categorias da lista fornecida
        2. Considere a descrição da transação como principal indicador
        3. Use o valor como contexto adicional
        4. Seja consistente: transações similares devem ter a mesma categoria
        5. Para valores negativos (despesas), foque no tipo de gasto
        6. Para valores positivos (receitas), foque na fonte da receita

        TRANSAÇÕES PARA ANALISAR:
        {json.dumps(transacoes_para_analisar[:50], indent=2, ensure_ascii=False)}

        RESPOSTA ESPERADA:
        Retorne um JSON com uma lista onde cada item tem:
        {{"descricao": "descrição da transação", "categoria_sugerida": "categoria escolhida", "confianca": "alta/media/baixa"}}

        Analise apenas as primeiras 50 transações se houver mais que isso.
        """        # Chamar a API da OpenAI
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18",  # Modelo mais recente disponível
            messages=[
                {"role": "system", "content": "Você é um especialista em categorização de transações financeiras. Sempre responda em formato JSON válido."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=4000
        )        # Processar resposta
        resposta_texto = response.choices[0].message.content
        if resposta_texto:
            resposta_texto = resposta_texto.strip()
        else:
            st.error("❌ Resposta vazia da LLM")
            return None
        
        # Tentar extrair JSON da resposta
        if "```json" in resposta_texto:
            resposta_texto = resposta_texto.split("```json")[1].split("```")[0]
        elif "```" in resposta_texto:
            resposta_texto = resposta_texto.split("```")[1].split("```")[0]
        
        # Parse do JSON
        sugestoes = json.loads(resposta_texto)
        
        return sugestoes
        
    except json.JSONDecodeError as e:
        st.error(f"❌ Erro ao processar resposta da LLM: {e}")
        return None
    except Exception as e:
        st.error(f"❌ Erro ao categorizar com LLM: {e}")
        return None

def aplicar_categorizacao_llm(df_transacoes, sugestoes_llm):
    """Aplica as sugestões da LLM ao DataFrame"""
    df_resultado = df_transacoes.copy()
    
    # Criar mapeamento de descrição para categoria sugerida
    mapeamento = {}
    for sugestao in sugestoes_llm:
        descricao = sugestao.get("descricao", "")
        categoria = sugestao.get("categoria_sugerida", "")
        if descricao and categoria:
            mapeamento[descricao] = categoria
    
    # Aplicar mapeamento
    def aplicar_categoria_llm(row):
        descricao = row["Descrição"]
        if descricao in mapeamento:
            return mapeamento[descricao]
        return row["Categoria"]  # Manter categoria original se não houver sugestão
    
    df_resultado["Categoria_LLM"] = df_resultado.apply(aplicar_categoria_llm, axis=1)
    return df_resultado

# Interface principal
st.title("🏷️ Gerenciar Transações")
st.markdown("**Corrija e personalize a categorização das suas transações**")

# Sistema de escolha do tipo de transações
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    tipo_gestao = st.selectbox(
        "📋 Escolha o tipo de transações para gerenciar:",
        options=["💳 Transações à Vista", "🎯 Transações de Crédito"],
        index=0,
        help="Selecione se deseja gerenciar transações à vista (conta corrente + manuais) ou transações de crédito (cartão de crédito)"
    )

st.markdown("---")

# Definir se é modo crédito ou à vista
modo_credito = tipo_gestao == "🎯 Transações de Crédito"

# Carregar dados
df = carregar_transacoes()

if df.empty:
    st.warning("📭 Nenhuma transação encontrada!")
    st.info("💡 **Possíveis motivos:**")
    st.markdown("""
    1. 📁 Nenhum arquivo foi importado
    2. 🗓️ O período selecionado não contém transações
    3. 🔍 Os dados não foram migrados para o Backend V2
    """)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Tentar Recarregar", type="primary"):
            st.cache_data.clear()
            st.rerun()
    
    with col2:
        if st.button("📁 Ir para Atualizar Dados"):
            st.switch_page("pages/Atualizar_Dados.py")
    
    st.stop()

# Filtrar por tipo de transação baseado na escolha
if modo_credito:
    # Filtrar apenas transações de cartão de crédito (origem de faturas)
    if "Origem" in df.columns:
        df = df[df["Origem"].str.contains("Nubank_|fatura", case=False, na=False) | 
                ((df["Origem"] == "Manual") & (df.get("tipo_pagamento", "") != "Espécie"))]
    st.info("🎯 **Modo Crédito ativado** - Exibindo apenas transações de cartão de crédito e transações manuais não em espécie")
else:
    # Filtrar transações à vista (extratos + manuais em espécie)
    if "Origem" in df.columns:
        df = df[~df["Origem"].str.contains("Nubank_|fatura", case=False, na=False) | 
                ((df["Origem"] == "Manual") & (df.get("tipo_pagamento", "") == "Espécie"))]
    st.info("💳 **Modo À Vista ativado** - Exibindo transações de conta corrente e transações manuais em espécie")

# Remover transações excluídas
df = filtrar_transacoes_excluidas(df)

# Métricas de resumo
col1, col2, col3, col4, col5, col6, col7 = st.columns(7)

with col1:
    st.metric("📊 Total de Transações", len(df))

with col2:
    cache = carregar_cache_categorias()
    st.metric("🏷️ Categorizações Personalizadas", len(cache))

with col3:
    descricoes = carregar_descricoes_personalizadas()
    st.metric("📝 Descrições Personalizadas", len(descricoes))

with col4:
    transacoes_excluidas = carregar_transacoes_excluidas()
    st.metric("🗑️ Transações Excluídas", len(transacoes_excluidas))

with col5:
    transacoes_manuais = carregar_transacoes_manuais()
    st.metric("➕ Transações Manuais", len(transacoes_manuais))

with col6:
    receitas = len(df[df["Valor"] > 0])
    st.metric("📈 Receitas", receitas)

with col7:
    despesas = len(df[df["Valor"] < 0])
    st.metric("📉 Despesas", despesas)

# Seção de gerenciamento de categorias
st.subheader("🎨 Gerenciar Categorias")
with st.expander("➕ Criar Nova Categoria"):
    col1, col2 = st.columns([3, 1])
    
    with col1:
        nova_categoria = st.text_input(
            "Nome da nova categoria",
            placeholder="Ex: Pets, Doações, Hobby, etc.",
            help="Digite o nome da categoria que deseja criar"
        )
    
    with col2:
        st.write("")  # Espaçamento
        criar_categoria = st.button("✨ Criar", type="primary")
    
    if criar_categoria and nova_categoria:
        nova_categoria = nova_categoria.strip()
        
        # Validações
        if len(nova_categoria) < 2:
            st.error("❌ A categoria deve ter pelo menos 2 caracteres.")
        elif len(nova_categoria) > 30:
            st.error("❌ A categoria deve ter no máximo 30 caracteres.")
        elif nova_categoria in get_todas_categorias():
            st.warning("⚠️ Esta categoria já existe.")
        else:
            # Criar nova categoria
            categorias_personalizadas = carregar_categorias_personalizadas()
            categorias_personalizadas.append(nova_categoria)
            
            if salvar_categorias_personalizadas(categorias_personalizadas):
                st.success(f"✅ Categoria '{nova_categoria}' criada com sucesso!")
                st.rerun()
    
    # Mostrar categorias personalizadas existentes
    categorias_personalizadas = carregar_categorias_personalizadas()
    if categorias_personalizadas:
        st.markdown("**📋 Suas categorias personalizadas:**")
        
        for i, categoria in enumerate(categorias_personalizadas):
            col1, col2 = st.columns([4, 1])
            
            with col1:
                st.text(f"• {categoria}")
            
            with col2:
                if st.button("🗑️", key=f"del_cat_{i}", help=f"Remover '{categoria}'"):
                    # Confirmar remoção
                    if st.button(f"⚠️ Confirmar remoção de '{categoria}'", key=f"confirm_del_{i}", type="secondary"):
                        categorias_personalizadas.remove(categoria)
                        salvar_categorias_personalizadas(categorias_personalizadas)
                        
                        # Também remover do cache de categorizações se existir
                        cache = carregar_cache_categorias()
                        cache_atualizado = {k: v for k, v in cache.items() if v != categoria}
                        if len(cache_atualizado) != len(cache):
                            salvar_cache_categorias(cache_atualizado)
                        
                        st.success(f"✅ Categoria '{categoria}' removida!")
                        st.rerun()

# Seção de adicionar transação manual (apenas para modo à vista)
if not modo_credito:
    st.subheader("➕ Adicionar Transação Manual")
    with st.expander("💰 Registrar Nova Transação (Espécie/Outros)", expanded=False):
        st.markdown("**Use esta funcionalidade para registrar transações em dinheiro, presentes recebidos, vendas, ou qualquer movimentação financeira que não aparece nos extratos bancários.**")
        
        with st.form("nova_transacao_manual"):
            col1, col2 = st.columns(2)
            
            with col1:
                # Data da transação
                data_transacao = st.date_input(
                    "📅 Data da Transação",
                    value=datetime.now().date(),
                    max_value=datetime.now().date(),
                    help="Selecione a data em que a transação ocorreu"
                )
                
                # Tipo de transação
                tipo_transacao_manual = st.selectbox(
                    "📊 Tipo de Transação",
                    options=["💸 Despesa", "💰 Receita"],
                    help="Selecione se é uma entrada ou saída de dinheiro"
                )
                
                # Categoria
                categoria_manual = st.selectbox(
                    "🏷️ Categoria",
                    options=get_todas_categorias(),
                    help="Escolha a categoria que melhor descreve esta transação"
                )
            
            with col2:
                # Descrição
                descricao_manual = st.text_input(
                    "📝 Descrição",
                    placeholder="Ex: Compra no mercado, Venda de produto, Presente recebido...",
                    max_chars=100,
                    help="Descreva a transação de forma clara e objetiva"
                )
                
                # Valor
                valor_manual = st.number_input(
                    "💵 Valor (R$)",
                    min_value=0.01,
                    value=0.01,
                    step=0.01,
                    format="%.2f",
                    help="Digite o valor da transação em reais"
                )
                
                # Tipo de pagamento (ajustado para modo à vista)
                tipo_pagamento_manual = st.selectbox(
                    "💳 Forma de Pagamento",
                    options=["Espécie", "PIX", "Transferência", "Cheque"],
                    help="Como esta transação foi realizada?"
                )
            
            # Descrição personalizada (opcional)
            descricao_personalizada_manual = st.text_area(
                "📋 Observações Detalhadas (Opcional)",
                placeholder="Adicione detalhes extras, contexto, local, pessoas envolvidas, etc...",
                max_chars=250,
                height=80,
                help="Campo opcional para observações mais detalhadas sobre esta transação"
            )
            
            # Botão de submit
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                submit_transacao = st.form_submit_button(
                    "✅ Adicionar Transação",
                    type="primary",
                    use_container_width=True
                )
        
        # Processar o envio
        if submit_transacao:
            # Validações
            if not descricao_manual.strip():
                st.error("❌ A descrição da transação é obrigatória.")
            elif valor_manual <= 0:
                st.error("❌ O valor deve ser maior que zero.")
            else:
                # Ajustar o sinal do valor baseado no tipo
                valor_final = -abs(valor_manual) if tipo_transacao_manual == "💸 Despesa" else abs(valor_manual)
                
                # Adicionar a transação
                sucesso = adicionar_transacao_manual(
                    data=data_transacao,
                    descricao=descricao_manual,
                    valor=valor_final,
                    categoria=categoria_manual,
                    descricao_personalizada=descricao_personalizada_manual,
                    tipo_pagamento=tipo_pagamento_manual
                )
                
                if sucesso:
                    emoji = "💸" if valor_final < 0 else "💰"
                    st.success(f"✅ {emoji} Transação adicionada com sucesso!")
                    st.balloons()  # Efeito visual de celebração
                    
                    # Limpar cache para recarregar os dados
                    st.cache_data.clear()
                    
                    # Mostrar resumo da transação adicionada
                    with st.container():
                        st.markdown("**📋 Resumo da transação adicionada:**")
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric("📅 Data", data_transacao.strftime("%d/%m/%Y"))
                        
                        with col2:
                            st.metric("💵 Valor", f"R$ {abs(valor_final):,.2f}")
                        
                        with col3:
                            st.metric("🏷️ Categoria", categoria_manual)
                        
                        with col4:
                            st.metric("💳 Pagamento", tipo_pagamento_manual)
                    
                    # Sugestão para o usuário
                    st.info("💡 **Dica:** A nova transação já aparece nos filtros e pode ser editada na seção abaixo. Ela também será incluída nos gráficos da página Home.")
                else:
                    st.error("❌ Erro ao adicionar a transação. Tente novamente.")

# Seção para gerenciar transações manuais existentes (apenas para modo à vista)
if not modo_credito:
    transacoes_manuais_existentes = carregar_transacoes_manuais()
    if transacoes_manuais_existentes:
        with st.expander(f"📊 Gerenciar Transações Manuais ({len(transacoes_manuais_existentes)})", expanded=False):
            st.markdown("**Suas transações manuais registradas:**")
            
            # Organizar por data mais recente primeiro
            transacoes_ordenadas = sorted(transacoes_manuais_existentes, key=lambda x: x["data"], reverse=True)
            
            for i, transacao in enumerate(transacoes_ordenadas[:10]):  # Mostrar até 10 mais recentes
                col1, col2, col3, col4, col5, col6 = st.columns([1.5, 2.5, 1.5, 1.5, 1, 0.8])
                
                with col1:
                    data_formatada = datetime.strptime(transacao["data"], "%Y-%m-%d").strftime("%d/%m/%Y")
                    st.text(data_formatada)
                
                with col2:
                    descricao_exibida = transacao["descricao"][:35] + ("..." if len(transacao["descricao"]) > 35 else "")
                    st.text(descricao_exibida)
                
                with col3:
                    valor = transacao["valor"]
                    valor_formatado = f"R$ {abs(valor):,.2f}"
                    emoji = "💰" if valor > 0 else "💸"
                    st.text(f"{emoji} {valor_formatado}")
                
                with col4:
                    st.text(transacao["categoria"])
                
                with col5:
                    st.text(transacao.get("tipo_pagamento", "Espécie"))
                
                with col6:
                    if st.button("🗑️", key=f"del_manual_{i}", help=f"Remover transação manual"):
                        if remover_transacao_manual(transacao["id"]):
                            st.success("✅ Transação removida!")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error("❌ Erro ao remover transação")
            
            if len(transacoes_manuais_existentes) > 10:
                st.caption(f"... e mais {len(transacoes_manuais_existentes) - 10} transações manuais")
            
            # Estatísticas das transações manuais
            total_receitas = sum(t["valor"] for t in transacoes_manuais_existentes if t["valor"] > 0)
            total_despesas = sum(abs(t["valor"]) for t in transacoes_manuais_existentes if t["valor"] < 0)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("💰 Total Receitas Manuais", f"R$ {total_receitas:,.2f}")
            with col2:
                st.metric("💸 Total Despesas Manuais", f"R$ {total_despesas:,.2f}")
            with col3:
                saldo = total_receitas - total_despesas
                st.metric("⚖️ Saldo das Manuais", f"R$ {saldo:,.2f}")
            
            # Exportar transações manuais
            st.markdown("---")
            if st.button("📥 Exportar Transações Manuais", help="Baixar todas as transações manuais em JSON"):
                export_data = json.dumps(transacoes_manuais_existentes, indent=2, ensure_ascii=False)
                st.download_button(
                    "💾 Download JSON",
                    data=export_data,
                    file_name=f"transacoes_manuais_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )

# Seções específicas para modo crédito
if modo_credito:
    st.subheader("🎯 Funcionalidades Específicas de Crédito")
    
    # Análise de gastos por estabelecimento
    with st.expander("🏪 Análise por Estabelecimento", expanded=False):
        if not df.empty:
            # Agrupar gastos por descrição (estabelecimento)
            gastos_estabelecimento = df[df["Valor"] < 0].groupby("Descrição")["Valor"].agg(["sum", "count"]).reset_index()
            gastos_estabelecimento["Valor Total"] = gastos_estabelecimento["sum"].abs()
            gastos_estabelecimento = gastos_estabelecimento.sort_values("Valor Total", ascending=False)
            
            if not gastos_estabelecimento.empty:
                st.markdown("**🏆 Top 10 estabelecimentos com maiores gastos:**")
                
                for i, row in gastos_estabelecimento.head(10).iterrows():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        estabelecimento = row["Descrição"][:50] + ("..." if len(row["Descrição"]) > 50 else "")
                        st.text(estabelecimento)
                    
                    with col2:
                        st.metric("💸 Total", f"R$ {row['Valor Total']:,.2f}")
                    
                    with col3:
                        st.metric("📊 Transações", int(row["count"]))
                
                # Gráfico de gastos por estabelecimento
                import plotly.express as px
                top_estabelecimentos = gastos_estabelecimento.head(10)
                
                fig = px.bar(
                    top_estabelecimentos,
                    x="Valor Total",
                    y="Descrição",
                    orientation="h",
                    title="💳 Top 10 Gastos por Estabelecimento",
                    labels={"Valor Total": "Valor (R$)", "Descrição": "Estabelecimento"}
                )
                fig.update_layout(yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📊 Nenhuma transação de crédito encontrada para análise.")
    
    # Análise de parcelamentos (simulação)
    with st.expander("💳 Análise de Parcelamentos", expanded=False):
        st.markdown("**📋 Identificação de possíveis parcelamentos:**")
        st.info("💡 **Dica:** Transações com valores similares em datas próximas podem indicar parcelamentos.")
        
        if not df.empty:
            # Buscar transações com valores similares
            df_despesas = df[df["Valor"] < 0].copy()
            df_despesas["Valor_Abs"] = df_despesas["Valor"].abs()
            
            # Agrupar por valor aproximado (arredondado)
            df_despesas["Valor_Arredondado"] = df_despesas["Valor_Abs"].round(0)
            valores_frequentes = df_despesas.groupby("Valor_Arredondado").size()
            valores_suspeitos = valores_frequentes[valores_frequentes >= 2].index
            
            if len(valores_suspeitos) > 0:
                st.markdown("**🔍 Valores que aparecem múltiplas vezes (possíveis parcelamentos):**")
                
                for valor in valores_suspeitos[:5]:  # Mostrar top 5
                    transacoes_valor = df_despesas[df_despesas["Valor_Arredondado"] == valor]
                    
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        st.metric("💰 Valor", f"R$ {valor:,.0f}")
                        st.metric("📊 Ocorrências", len(transacoes_valor))
                    
                    with col2:
                        st.markdown(f"**Transações de ~R$ {valor:,.0f}:**")
                        for _, transacao in transacoes_valor.head(5).iterrows():
                            data_formatada = transacao["Data"].strftime("%d/%m/%Y")
                            descricao = transacao["Descrição"][:40] + ("..." if len(transacao["Descrição"]) > 40 else "")
                            st.text(f"• {data_formatada} - {descricao}")
                    
                    st.markdown("---")
            else:
                st.info("✅ Nenhum padrão de parcelamento identificado.")
    
    # Metas de gastos por categoria (específico para crédito)
    with st.expander("🎯 Controle de Gastos por Categoria", expanded=False):
        st.markdown("**💡 Defina metas de gastos mensais para suas categorias mais usadas no cartão de crédito:**")
        
        if not df.empty:
            # Calcular gastos por categoria no mês atual
            from datetime import datetime, date
            hoje = date.today()
            inicio_mes = hoje.replace(day=1)
            
            df_mes_atual = df[(df["Data"] >= pd.to_datetime(inicio_mes)) & (df["Valor"] < 0)]
            
            if not df_mes_atual.empty:
                gastos_categoria = df_mes_atual.groupby("Categoria")["Valor"].sum().abs().sort_values(ascending=False)
                
                st.markdown(f"**📊 Gastos do mês atual ({hoje.strftime('%m/%Y')}):**")
                
                for categoria, gasto in gastos_categoria.head(5).items():
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        st.text(f"🏷️ {categoria}")
                    
                    with col2:
                        st.metric("💸 Gasto", f"R$ {gasto:,.2f}")
                    
                    with col3:
                        # Campo para definir meta (simulado - poderia ser salvo em arquivo)
                        meta = st.number_input(
                            f"Meta para {categoria}",
                            min_value=0.0,
                            value=float(gasto * 1.2),  # Sugestão: 20% acima do gasto atual
                            step=50.0,
                            key=f"meta_{categoria}",
                            label_visibility="collapsed"
                        )
                        
                        # Indicador de progresso
                        if meta > 0:
                            progresso = min(gasto / meta, 1.0)
                            cor = "🟢" if progresso <= 0.8 else "🟡" if progresso <= 1.0 else "🔴"
                            st.progress(progresso)
                            st.caption(f"{cor} {progresso*100:.1f}% da meta")
            else:
                st.info("📊 Nenhum gasto no cartão de crédito encontrado para o mês atual.")

# Seção de filtros
st.subheader("🔍 Filtros")
col1, col2, col3 = st.columns(3)

with col1:
    data_inicio, data_fim = filtro_data(df)

with col2:
    # Atualizar o DataFrame com todas as categorias antes de aplicar o filtro
    df_com_todas_categorias = df.copy()
    categorias_selecionadas = st.multiselect(
        "Categorias",
        options=sorted(df_com_todas_categorias["Categoria"].unique()),
        default=None,
        help="Selecione uma ou mais categorias para filtrar"
    )

with col3:
    if modo_credito:
        tipo_transacao = st.selectbox(
            "Tipo de Transação",
            options=["Todas", "Compras", "Estornos"],
            help="Filtrar por tipo de transação de crédito"
        )
    else:
        tipo_transacao = st.selectbox(
            "Tipo de Transação",
            options=["Todas", "Receitas", "Despesas"],
            help="Filtrar por tipo de transação"
        )

# Aplicar filtros
df_filtrado = aplicar_filtros(df, data_inicio, data_fim, categorias_selecionadas)

# Filtro adicional por tipo
if modo_credito:
    if tipo_transacao == "Compras":
        df_filtrado = df_filtrado[df_filtrado["Valor"] < 0]
    elif tipo_transacao == "Estornos":
        df_filtrado = df_filtrado[df_filtrado["Valor"] > 0]
else:
    if tipo_transacao == "Receitas":
        df_filtrado = df_filtrado[df_filtrado["Valor"] > 0]
    elif tipo_transacao == "Despesas":
        df_filtrado = df_filtrado[df_filtrado["Valor"] < 0]

if df_filtrado.empty:
    st.warning("🔍 Nenhuma transação encontrada com os filtros aplicados.")
    st.stop()

# Seção de categorização automática com LLM
st.subheader("🤖 Categorização Automática com IA")
with st.expander("🧠 Categorizar Transações com Inteligência Artificial", expanded=False):
    st.markdown(f"""
    **🚀 Use Inteligência Artificial para categorizar suas transações automaticamente!**
    
    A IA irá analisar a descrição e valor de cada transação para sugerir a melhor categoria.
    
    {"🎯 **Modo Crédito**: Ideal para categorizar compras no cartão de crédito" if modo_credito else "💳 **Modo À Vista**: Ideal para categorizar transações de conta corrente"}
    """)
    
    # Verificar se há transações para categorizar
    transacoes_para_categorizar = df_filtrado.copy()
    
    if not transacoes_para_categorizar.empty:
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.metric("📊 Transações Disponíveis", len(transacoes_para_categorizar))
            
            # Opção para limitar número de transações
            limite_transacoes = st.slider(
                "Número máximo de transações para analisar",
                min_value=5,
                max_value=min(50, len(transacoes_para_categorizar)),
                value=min(20, len(transacoes_para_categorizar)),
                help="Limite para evitar custos altos da API"
            )
        
        with col2:
            st.markdown("**🎯 Categorias Disponíveis:**")
            categorias_disponiveis = get_todas_categorias()
            st.caption(f"{len(categorias_disponiveis)} categorias")
        
        with col3:
            st.markdown("**💡 Dicas:**")
            st.caption("• A IA usa descrição e valor")
            st.caption("• Processo pode levar 10-30s")
            st.caption("• Você pode revisar antes de salvar")
        
        # Botão para iniciar categorização
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button(
                "🤖 Categorizar com IA",
                type="primary",
                use_container_width=True,
                help="Inicia o processo de categorização automática"
            ):
                # Inicializar estado de sessão para categorização LLM
                if 'categorizacao_llm_resultados' not in st.session_state:
                    st.session_state.categorizacao_llm_resultados = None
                
                # Pegar amostra das transações
                df_amostra = transacoes_para_categorizar.head(limite_transacoes)
                
                with st.spinner("🤖 Analisando transações com IA... Isso pode levar alguns segundos."):
                    sugestoes = categorizar_transacoes_com_llm(df_amostra, categorias_disponiveis)
                
                if sugestoes:
                    st.session_state.categorizacao_llm_resultados = {
                        'df_original': df_amostra,
                        'sugestoes': sugestoes,
                        'categorias_disponiveis': categorias_disponiveis
                    }
                    st.success("✅ Categorização concluída! Revise os resultados abaixo.")
                    st.rerun()
                else:
                    st.error("❌ Falha na categorização. Verifique a configuração da API.")
        
        # Mostrar resultados da categorização se existirem
        if 'categorizacao_llm_resultados' in st.session_state and st.session_state.categorizacao_llm_resultados:
            resultados = st.session_state.categorizacao_llm_resultados
            df_original = resultados['df_original']
            sugestoes = resultados['sugestoes']
            
            st.markdown("---")
            st.markdown("### 📋 Resultados da Categorização IA")
            
            # Estatísticas dos resultados
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("📊 Analisadas", len(sugestoes))
            
            with col2:
                alta_confianca = len([s for s in sugestoes if s.get('confianca') == 'alta'])
                st.metric("🎯 Alta Confiança", alta_confianca)
            
            with col3:
                media_confianca = len([s for s in sugestoes if s.get('confianca') == 'media'])
                st.metric("⚖️ Média Confiança", media_confianca)
            
            with col4:
                baixa_confianca = len([s for s in sugestoes if s.get('confianca') == 'baixa'])
                st.metric("⚠️ Baixa Confiança", baixa_confianca)
            
            # Tabela de resultados com aprovação individual
            st.markdown("**✅ Revisar e Aprovar Sugestões:**")
            
            # Inicializar aprovações se não existir
            if 'aprovacoes_llm' not in st.session_state:
                st.session_state.aprovacoes_llm = {}
            
            # Mostrar transações com sugestões
            transacoes_modificadas = 0
            
            for i, sugestao in enumerate(sugestoes[:20]):  # Mostrar até 20
                col1, col2, col3, col4, col5, col6 = st.columns([2.5, 1.5, 1.5, 1.5, 0.8, 0.8])
                
                # Buscar transação original
                descricao_sugestao = sugestao.get('descricao', '')
                transacao_original = df_original[df_original['Descrição'] == descricao_sugestao]
                
                if not transacao_original.empty:
                    row = transacao_original.iloc[0]
                    
                    with col1:
                        st.text(f"{descricao_sugestao[:35]}...")
                    
                    with col2:
                        categoria_atual = row['Categoria']
                        st.text(f"📂 {categoria_atual}")
                    
                    with col3:
                        categoria_sugerida = sugestao.get('categoria_sugerida', '')
                        st.text(f"🤖 {categoria_sugerida}")
                    
                    with col4:
                        confianca = sugestao.get('confianca', 'baixa')
                        emoji_confianca = {"alta": "🎯", "media": "⚖️", "baixa": "⚠️"}
                        st.text(f"{emoji_confianca.get(confianca, '⚠️')} {confianca}")
                    
                    with col5:
                        key_aprovacao = f"aprovar_llm_{i}"
                        if categoria_atual != categoria_sugerida:
                            aprovado = st.checkbox(
                                "✅",
                                key=key_aprovacao,
                                help="Aprovar esta sugestão"
                            )
                            if aprovado:
                                st.session_state.aprovacoes_llm[descricao_sugestao] = categoria_sugerida
                                transacoes_modificadas += 1
                            elif descricao_sugestao in st.session_state.aprovacoes_llm:
                                del st.session_state.aprovacoes_llm[descricao_sugestao]
                        else:
                            st.text("✅")  # Já está correto
                    
                    with col6:
                        valor_formatado = f"R$ {abs(row['Valor']):.0f}"
                        emoji_valor = "💰" if row['Valor'] > 0 else "💸"
                        st.caption(f"{emoji_valor} {valor_formatado}")
            
            # Botões de ação para aprovações em lote
            if len(sugestoes) > 20:
                st.caption(f"... e mais {len(sugestoes) - 20} sugestões")
            
            st.markdown("---")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                aprovacoes_count = len(st.session_state.aprovacoes_llm)
                st.metric("✅ Aprovadas", aprovacoes_count)
            
            with col2:
                if st.button("✅ Aprovar Todas de Alta Confiança"):
                    for sugestao in sugestoes:
                        if sugestao.get('confianca') == 'alta':
                            descricao = sugestao.get('descricao', '')
                            categoria = sugestao.get('categoria_sugerida', '')
                            if descricao and categoria:
                                st.session_state.aprovacoes_llm[descricao] = categoria
                    st.rerun()
            
            with col3:
                if aprovacoes_count > 0:
                    if st.button("💾 Salvar Aprovadas", type="primary"):                        # Aplicar aprovações ao cache de categorias
                        cache = carregar_cache_categorias()
                        
                        for descricao, categoria in st.session_state.aprovacoes_llm.items():
                            descricao_normalizada = descricao.lower().strip()
                            cache[descricao_normalizada] = categoria
                        
                        if salvar_cache_categorias(cache):
                            st.success(f"✅ {aprovacoes_count} categorizações salvas com sucesso!")
                            # Limpar estados
                            st.session_state.categorizacao_llm_resultados = None
                            st.session_state.aprovacoes_llm = {}
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error("❌ Erro ao salvar categorizações")
            
            with col4:
                if st.button("🗑️ Descartar Resultados"):
                    st.session_state.categorizacao_llm_resultados = None
                    st.session_state.aprovacoes_llm = {}
                    st.rerun()
    
    else:
        st.info("📊 Nenhuma transação disponível para categorização com os filtros atuais.")

# Configuração da API OpenAI (seção separada)
with st.expander("⚙️ Configuração da API OpenAI"):
    st.markdown("""
    **🔑 Para usar a categorização com IA, você precisa configurar sua chave da API OpenAI:**
    
    **Método 1 - Variável de Ambiente:**
    - Defina a variável `OPENAI_API_KEY` no seu sistema
    
    **Método 2 - Arquivo de Configuração:**
    - Crie um arquivo `config_openai.json` na pasta do projeto
    - Formato: `{"api_key": "sua-chave-aqui"}`
    
    **💡 Obtendo a chave:**
    1. Acesse https://platform.openai.com/api-keys
    2. Faça login em sua conta OpenAI
    3. Crie uma nova chave API
    4. Configure usando um dos métodos acima
    
    **💰 Custos estimados:**
    - ~50 transações: $0.01 - $0.05 USD
    - Modelo usado: GPT-4o-mini (mais econômico)
    """)
    
    # Teste de configuração
    if st.button("🔍 Testar Configuração"):
        api_key = configurar_openai()
        if api_key:
            st.success("✅ API configurada corretamente!")
        else:
            st.error("❌ API não configurada. Siga as instruções acima.")

# Seção de edição em lote
st.subheader("⚡ Edição em Lote")
with st.expander("📝 Alterar categoria de múltiplas transações"):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filtro_descricao = st.text_input(
            "Filtrar por descrição",
            placeholder="Ex: PIX, MERCADO, POSTO",
            help="Digite parte da descrição para filtrar transações similares"
        )
    
    with col2:
        categoria_lote = st.selectbox(
            "Nova categoria",
            options=get_todas_categorias(),
            key="categoria_lote"
        )
    
    with col3:
        st.write("")  # Espaçamento
        aplicar_lote = st.button("🔄 Aplicar em Lote", type="primary")
    
    if filtro_descricao:
        transacoes_similares = df_filtrado[
            df_filtrado["Descrição"].str.contains(filtro_descricao, case=False, na=False)
        ]
        
        if not transacoes_similares.empty:
            st.info(f"📊 {len(transacoes_similares)} transações encontradas com '{filtro_descricao}'")
            
            # Preview das transações que serão alteradas
            preview_df = transacoes_similares[["Data", "Descrição", "Categoria", "Valor"]].head(5)
            st.dataframe(preview_df, use_container_width=True)
            
            if len(transacoes_similares) > 5:
                st.caption(f"... e mais {len(transacoes_similares) - 5} transações")
            
            if aplicar_lote:
                cache = carregar_cache_categorias()
                alteracoes = 0
                
                for _, row in transacoes_similares.iterrows():
                    descricao_normalizada = row["Descrição"].lower().strip()
                    cache[descricao_normalizada] = categoria_lote
                    alteracoes += 1
                
                if salvar_cache_categorias(cache):
                    st.success(f"✅ {alteracoes} transações categorizadas como '{categoria_lote}'!")
                    st.cache_data.clear()  # Limpar cache para recarregar dados
                    st.rerun()
        else:
            st.warning("❌ Nenhuma transação encontrada com essa descrição.")

# Seção de edição individual
st.subheader("📋 Transações")

# Inicializar estado de sessão para mudanças pendentes
if 'mudancas_pendentes' not in st.session_state:
    st.session_state.mudancas_pendentes = {}

# Preparar dados para exibição
df_display = df_filtrado.copy()
df_display = df_display.sort_values("Data", ascending=False)

# Paginação
itens_por_pagina = 20
total_paginas = len(df_display) // itens_por_pagina + (1 if len(df_display) % itens_por_pagina > 0 else 0)

if total_paginas > 1:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pagina_atual = st.selectbox(
            "Página",
            options=list(range(1, total_paginas + 1)),
            format_func=lambda x: f"Página {x} de {total_paginas}"
        )
else:
    pagina_atual = 1

# Controles de edição em lote
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)

with col1:
    mudancas_count = len(st.session_state.mudancas_pendentes)
    st.metric("📝 Mudanças Pendentes", mudancas_count)

with col2:
    if mudancas_count > 0:
        if st.button("💾 Salvar Todas", type="primary", help=f"Salvar {mudancas_count} alterações"):
            cache = carregar_cache_categorias()
            
            # Aplicar todas as mudanças pendentes
            for descricao_norm, nova_categoria in st.session_state.mudancas_pendentes.items():
                cache[descricao_norm] = nova_categoria
            
            if salvar_cache_categorias(cache):
                st.success(f"✅ {mudancas_count} alterações salvas com sucesso!")
                st.session_state.mudancas_pendentes = {}  # Limpar mudanças pendentes
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("❌ Erro ao salvar alterações")

with col3:
    if mudancas_count > 0:
        if st.button("🗑️ Descartar Todas", help="Descartar todas as mudanças pendentes"):
            st.session_state.mudancas_pendentes = {}
            st.rerun()

with col4:
    modo_edicao = st.toggle("⚡ Modo Edição em Lote", help="Ativar para fazer múltiplas edições antes de salvar")

# Informação adicional sobre o modo de edição ativo
if modo_edicao:
    st.info("🔄 **Modo Edição em Lote ativado**: As alterações serão acumuladas e podem ser salvas todas de uma vez.")
else:
    st.info("💾 **Modo Individual ativado**: Cada alteração será salva imediatamente ao clicar no botão de salvar.")

st.markdown("---")

# Calcular índices da página
inicio = (pagina_atual - 1) * itens_por_pagina
fim = inicio + itens_por_pagina
df_pagina = df_display.iloc[inicio:fim]

# Exibir transações com opção de edição, exclusão e descrição personalizada
for idx, row in df_pagina.iterrows():
    with st.container():
        # Primeira linha: Dados principais da transação
        col1, col2, col3, col4, col5, col6 = st.columns([1.5, 3, 1.5, 2, 0.8, 0.8])
        
        with col1:
            st.text(row["Data"].strftime("%d/%m/%Y"))
        
        with col2:
            st.text(row["Descrição"][:45] + ("..." if len(row["Descrição"]) > 45 else ""))
        
        with col3:
            valor_formatado = formatar_valor_monetario(row["Valor"])
            cor = "🟢" if row["Valor"] > 0 else "🔴"
            st.text(f"{cor} {valor_formatado}")
        
        with col4:
            categoria_atual = row["Categoria"]
            todas_categorias = get_todas_categorias()
            descricao_normalizada = row["Descrição"].lower().strip()
            
            # Verificar se há mudança pendente para esta transação
            categoria_exibida = categoria_atual
            if descricao_normalizada in st.session_state.mudancas_pendentes:
                categoria_exibida = st.session_state.mudancas_pendentes[descricao_normalizada]
            
            nova_categoria = st.selectbox(
                "Categoria",
                options=todas_categorias,
                index=todas_categorias.index(categoria_exibida) if categoria_exibida in todas_categorias else 0,
                key=f"cat_{idx}",
                label_visibility="collapsed"
            )
            
            # Detectar mudanças
            if nova_categoria != categoria_atual:
                if modo_edicao:
                    # Modo lote: adicionar à lista de mudanças pendentes
                    st.session_state.mudancas_pendentes[descricao_normalizada] = nova_categoria
                    st.caption("⏳ Mudança pendente")
                else:
                    # Modo individual: manter comportamento original
                    st.session_state.mudancas_pendentes.pop(descricao_normalizada, None)  # Remove das pendentes se existir
            else:
                # Se voltou à categoria original, remover das pendentes
                st.session_state.mudancas_pendentes.pop(descricao_normalizada, None)
        
        with col5:
            if not modo_edicao and nova_categoria != categoria_atual:
                # Modo individual: salvar imediatamente
                if st.button("💾", key=f"save_{idx}", help="Salvar alteração"):
                    cache = carregar_cache_categorias()
                    cache[descricao_normalizada] = nova_categoria
                    
                    if salvar_cache_categorias(cache):
                        st.success("✅ Salvo!")
                        st.cache_data.clear()
                        st.rerun()
            elif modo_edicao and descricao_normalizada in st.session_state.mudancas_pendentes:
                # Modo lote: mostrar indicador de mudança pendente
                st.markdown("🔄")
        
        with col6:
            # Botão de exclusão
            if st.button("🗑️", key=f"delete_{idx}", help="Excluir transação"):
                # Confirmar exclusão
                if f"confirm_delete_{idx}" not in st.session_state:
                    st.session_state[f"confirm_delete_{idx}"] = True
                    st.rerun()
            
            # Mostrar confirmação se solicitada
            if st.session_state.get(f"confirm_delete_{idx}", False):
                col_sim, col_nao = st.columns(2)
                with col_sim:
                    if st.button("✅", key=f"confirm_yes_{idx}", help="Confirmar exclusão"):
                        if excluir_transacao(row):
                            st.success("🗑️ Transação excluída!")
                            st.session_state[f"confirm_delete_{idx}"] = False
                            st.cache_data.clear()  # Limpar cache para recarregar dados
                            st.rerun()
                        else:
                            st.error("❌ Erro ao excluir transação")
                
                with col_nao:
                    if st.button("❌", key=f"confirm_no_{idx}", help="Cancelar exclusão"):
                        st.session_state[f"confirm_delete_{idx}"] = False
                        st.rerun()
          # Segunda linha: Descrição personalizada
        col_desc, col_save_desc = st.columns([5, 1])
        
        with col_desc:
            # Obter descrição personalizada existente
            descricao_atual = obter_descricao_personalizada(row)
              # Campo de texto para descrição personalizada
            nova_descricao = st.text_area(
                "Descrição personalizada",
                value=descricao_atual,
                max_chars=250,
                height=68,
                key=f"desc_{idx}",
                label_visibility="collapsed",
                placeholder="Adicione uma descrição personalizada (máx. 250 caracteres)..."
            )
            
            # Garantir que nova_descricao não seja None
            if nova_descricao is None:
                nova_descricao = ""
            
            # Mostrar contador de caracteres
            chars_count = len(nova_descricao)
            if chars_count > 200:
                st.caption(f"🔤 {chars_count}/250 caracteres")
            elif nova_descricao:
                st.caption(f"📝 {chars_count} caracteres")
        
        with col_save_desc:
            # Botão para salvar descrição
            nova_descricao = nova_descricao or ""  # Garantir que não seja None
            if nova_descricao != descricao_atual:
                if st.button("💾📝", key=f"save_desc_{idx}", help="Salvar descrição"):
                    if salvar_descricao_personalizada(row, nova_descricao):
                        if nova_descricao.strip():
                            st.success("✅ Descrição salva!")
                        else:
                            st.success("✅ Descrição removida!")
                        st.rerun()
                    else:
                        st.error("❌ Erro ao salvar descrição")
            
            # Mostrar indicador se há descrição
            elif descricao_atual:
                st.markdown("📝✅")
        
        st.divider()

# Estatísticas da página
if total_paginas > 1:
    st.caption(f"Exibindo {len(df_pagina)} de {len(df_display)} transações (Página {pagina_atual} de {total_paginas})")

# Mostrar detalhes das mudanças pendentes
if st.session_state.mudancas_pendentes:
    with st.expander(f"📋 Detalhes das Mudanças Pendentes ({len(st.session_state.mudancas_pendentes)})"):
        st.markdown("**Transações que serão alteradas:**")
        
        for i, (descricao_norm, nova_categoria) in enumerate(st.session_state.mudancas_pendentes.items(), 1):
            # Encontrar a transação original para mostrar mais detalhes
            transacao_original = df_filtrado[df_filtrado["Descrição"].str.lower().str.strip() == descricao_norm]
            
            if not transacao_original.empty:
                row_original = transacao_original.iloc[0]
                col1, col2, col3 = st.columns([3, 2, 2])
                
                with col1:
                    st.text(f"{i}. {row_original['Descrição'][:40]}...")
                
                with col2:
                    st.text(f"{row_original['Categoria']} → {nova_categoria}")
                
                with col3:
                    if st.button("❌", key=f"remove_pending_{i}", help="Remover desta mudança"):
                        st.session_state.mudancas_pendentes.pop(descricao_norm)
                        st.rerun()
        
        # Botões de ação na seção de detalhes
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Salvar Todas as Mudanças", type="primary", key="save_all_details"):
                cache = carregar_cache_categorias()
                mudancas_count = len(st.session_state.mudancas_pendentes)
                
                for descricao_norm, nova_categoria in st.session_state.mudancas_pendentes.items():
                    cache[descricao_norm] = nova_categoria
                
                if salvar_cache_categorias(cache):
                    st.success(f"✅ {mudancas_count} alterações salvas com sucesso!")
                    st.session_state.mudancas_pendentes = {}
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("❌ Erro ao salvar alterações")
        
        with col2:
            if st.button("🗑️ Descartar Todas", key="discard_all_details"):
                st.session_state.mudancas_pendentes = {}
                st.rerun()

# Seção de gerenciamento do cache
st.subheader("🔧 Gerenciamento")
with st.expander("⚙️ Opções Avançadas"):
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ Limpar Todas as Categorizações", type="secondary"):
            if st.button("⚠️ Confirmar Limpeza", type="secondary"):
                cache_file = get_cache_categorias_file()
                if os.path.exists(cache_file):
                    os.remove(cache_file)
                    st.success("✅ Todas as categorizações personalizadas foram removidas!")
                    st.cache_data.clear()
                    st.rerun()
    
    with col2:
        cache = carregar_cache_categorias()
        if cache:
            # Exportar categorizações
            cache_json = json.dumps(cache, indent=2, ensure_ascii=False)
            st.download_button(
                "📥 Exportar Categorizações",
                data=cache_json,
                file_name=f"categorizacoes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )

# Seção de gerenciamento de transações excluídas
with st.expander("🗑️ Gerenciar Transações Excluídas"):
    transacoes_excluidas_ids = carregar_transacoes_excluidas()
    
    if transacoes_excluidas_ids:
        st.markdown(f"**{len(transacoes_excluidas_ids)} transações excluídas encontradas:**")
        
        # Mostrar detalhes das transações excluídas
        df_todas = carregar_transacoes()  # Carregar todas as transações (incluindo excluídas)
        
        transacoes_excluidas_detalhes = []
        for hash_id in transacoes_excluidas_ids:
            # Tentar encontrar a transação correspondente
            for _, row in df_todas.iterrows():
                if gerar_hash_transacao(row) == hash_id:
                    transacoes_excluidas_detalhes.append(row)
                    break
        
        if transacoes_excluidas_detalhes:
            for i, row in enumerate(transacoes_excluidas_detalhes[:10]):  # Mostrar até 10
                col1, col2, col3, col4 = st.columns([2, 3, 2, 1])
                
                with col1:
                    st.text(row["Data"].strftime("%d/%m/%Y"))
                
                with col2:
                    st.text(row["Descrição"][:40] + ("..." if len(row["Descrição"]) > 40 else ""))
                
                with col3:
                    valor_formatado = formatar_valor_monetario(row["Valor"])
                    cor = "🟢" if row["Valor"] > 0 else "🔴"
                    st.text(f"{cor} {valor_formatado}")
                
                with col4:
                    if st.button("🔄", key=f"restore_{i}", help="Restaurar transação"):
                        if restaurar_transacao(row):
                            st.success("✅ Transação restaurada!")
                            st.cache_data.clear()
                            st.rerun()
            
            if len(transacoes_excluidas_detalhes) > 10:
                st.caption(f"... e mais {len(transacoes_excluidas_detalhes) - 10} transações excluídas")
        
        # Botão para limpar todas as exclusões
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Restaurar Todas", type="primary"):
                if st.button("⚠️ Confirmar Restauração de Todas", type="secondary"):
                    if salvar_transacoes_excluidas([]):
                        st.success(f"✅ {len(transacoes_excluidas_ids)} transações restauradas!")
                        st.cache_data.clear()
                        st.rerun()
        
        with col2:
            # Exportar lista de transações excluídas
            export_data = json.dumps(transacoes_excluidas_ids, indent=2, ensure_ascii=False)
            st.download_button(
                "📥 Exportar Lista de Exclusões",
                data=export_data,
                file_name=f"transacoes_excluidas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    else:
        st.info("✨ Nenhuma transação foi excluída ainda.")
        st.markdown("Use o botão 🗑️ ao lado das transações para excluí-las temporariamente.")

# Seção de gerenciamento de descrições personalizadas
with st.expander("📝 Gerenciar Descrições Personalizadas"):
    descricoes_personalizadas = carregar_descricoes_personalizadas()
    
    if descricoes_personalizadas:
        st.markdown(f"**{len(descricoes_personalizadas)} descrições personalizadas encontradas:**")
        
        # Mostrar detalhes das descrições personalizadas
        df_todas = carregar_transacoes()  # Carregar todas as transações
        
        descricoes_detalhes = []
        for hash_id, descricao in descricoes_personalizadas.items():
            # Tentar encontrar a transação correspondente
            for _, row in df_todas.iterrows():
                if gerar_hash_transacao(row) == hash_id:
                    descricoes_detalhes.append((row, descricao))
                    break
        
        if descricoes_detalhes:
            for i, (row, descricao) in enumerate(descricoes_detalhes[:10]):  # Mostrar até 10
                col1, col2, col3, col4 = st.columns([1.5, 2.5, 3, 0.8])
                
                with col1:
                    st.text(row["Data"].strftime("%d/%m/%Y"))
                
                with col2:
                    st.text(row["Descrição"][:25] + ("..." if len(row["Descrição"]) > 25 else ""))
                
                with col3:
                    st.text(f"📝 {descricao[:40]}{'...' if len(descricao) > 40 else ''}")
                
                with col4:
                    if st.button("🗑️", key=f"remove_desc_{i}", help="Remover descrição"):
                        if remover_descricao_personalizada(row):
                            st.success("✅ Descrição removida!")
                            st.rerun()
            
            if len(descricoes_detalhes) > 10:
                st.caption(f"... e mais {len(descricoes_detalhes) - 10} descrições personalizadas")
        
        # Botão para limpar todas as descrições
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🗑️ Remover Todas as Descrições", type="secondary"):
                if st.button("⚠️ Confirmar Remoção de Todas", type="secondary"):
                    if salvar_descricoes_personalizadas({}):
                        st.success(f"✅ {len(descricoes_personalizadas)} descrições removidas!")
                        st.rerun()
        
        with col2:
            # Exportar descrições personalizadas
            export_data = json.dumps(descricoes_personalizadas, indent=2, ensure_ascii=False)
            st.download_button(
                "📥 Exportar Descrições",
                data=export_data,
                file_name=f"descricoes_personalizadas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    else:
        st.info("✨ Nenhuma descrição personalizada foi adicionada ainda.")
        st.markdown("Use o campo de texto abaixo de cada transação para adicionar descrições personalizadas.")

# Informações de ajuda
with st.expander("ℹ️ Como usar esta página"):
    modo_info = """
    **🎯 Modo Crédito Ativado:**
    - Exibe apenas transações de cartão de crédito
    - Funcionalidades específicas: análise por estabelecimento, identificação de parcelamentos
    - Controle de metas de gastos por categoria
    - Filtros adaptados para compras e estornos
    """ if modo_credito else """
    **💳 Modo À Vista Ativado:**
    - Exibe transações de conta corrente e transações manuais em espécie
    - Permite adicionar transações manuais (dinheiro, PIX, transferências)
    - Funcionalidades completas de gerenciamento de transações manuais
    - Filtros para receitas e despesas
    """
    
    st.markdown(f"""
    ### 🎯 Objetivo
    Esta página permite corrigir e personalizar a categorização das suas transações.
    
    ### 📋 Modo Atual: {tipo_gestao}
    
    {modo_info}
    
    ### 🔧 Funcionalidades Disponíveis
    
    **🤖 Categorização Automática com IA (NOVO):**
    - Use Inteligência Artificial para categorizar transações automaticamente
    - IA analisa descrição e valor para sugerir melhor categoria
    - Revise e aprove sugestões antes de salvar
    - Funciona nos modos à vista e crédito
    
    **🎨 Criar Categorias Personalizadas:**
    - Crie suas próprias categorias (Ex: Pets, Doações, Hobby)
    - Gerencie e remova categorias criadas
    - Use em qualquer transação após criadas
    
    **⚡ Edição em Lote:**
    - Ative o "Modo Edição em Lote" para fazer múltiplas alterações
    - Faça quantas mudanças quiser não salvar imediatamente
    - Visualize todas as mudanças pendentes antes de confirmar
    - Salve todas de uma vez ou descarte se não estiver satisfeito
    
    **🔍 Edição por Descrição Similar:**
    - Digite parte da descrição para encontrar transações similares
    - Aplique uma nova categoria a todas elas de uma vez
    - Use categorias padrão ou suas categorias personalizadas
    
    **🗑️ Exclusão de Transações:**
    - Clique no botão 🗑️ para excluir uma transação temporariamente
    - Transações excluídas não aparecem nos gráficos e relatórios
    - Acesse "Gerenciar Transações Excluídas" para restaurar se necessário
    
    **📝 Descrições Personalizadas:**
    - Adicione descrições detalhadas de até 250 caracteres a qualquer transação
    - Use o campo de texto abaixo de cada transação
    - Clique em 💾📝 para salvar a descrição personalizada
    
    ### 💡 Dicas para Edição em Lote
    
    **⚡ Modo Edição em Lote (Recomendado):**
    1. Ative o toggle "Modo Edição em Lote"
    2. Navegue pelas páginas fazendo as alterações desejadas
    3. Acompanhe o contador de "Mudanças Pendentes"
    4. Revise os detalhes das mudanças na seção expandível
    5. Clique em "Salvar Todas" quando estiver satisfeito
    
    **📋 Modo Individual:**
    - Ideal para correções pontuais
    - Cada mudança é salva imediatamente
    - Não acumula mudanças pendentes    ### 📝 Dicas para Descrições Personalizadas
    
    **Quando usar:**
    - Adicionar contexto importante sobre uma transação
    - Lembrar motivos específicos de um gasto
    - Anotar detalhes do local ou evento
    - Registrar observações sobre fornecedores
    
    **Exemplos úteis:**
    - "Jantar de aniversário da Maria"
    - "Compra de material para projeto X"
    - "Medicamento prescrito pelo Dr. João"
    - "Presente para formatura do filho"
    - "Manutenção preventiva do carro"
    
    **Funcionalidades:**
    - Máximo de 250 caracteres por descrição
    - Salvamento instantâneo ao clicar 💾📝
    - Remoção fácil deixando o campo vazio
    - Contador de caracteres quando próximo do limite
    - Backup e exportação de todas as descrições
    
    ### ➕ Dicas para Transações Manuais
    
    **Quando usar:**
    - Pagamentos em dinheiro (espécie)
    - Presentes recebidos ou dados
    - Vendas de produtos pessoais
    - Reembolsos recebidos
    - Ganhos extras (freelances, trabalhos eventuais)
    - Despesas não rastreadas pelo banco
    
    **Exemplos práticos:**
    - "💸 Compra no mercadinho da esquina - R$ 25,00"
    - "💰 Venda de livros usados - R$ 150,00"
    - "💸 Presente de aniversário para amigo - R$ 80,00"
    - "💰 Freelance design de logo - R$ 500,00"
    - "💸 Lanche na cantina da escola - R$ 12,00"
    
    **Categorização inteligente:**
    - Use as mesmas categorias das transações bancárias
    - Crie categorias personalizadas se necessário
    - Transações manuais seguem as mesmas regras de categorização
    
    **Organização:**
    - Registre as transações assim que elas acontecem
    - Use observações detalhadas para contexto extra
    - Exporte regularmente como backup
    - Monitore o saldo manual separadamente
    
    ### 🗑️ Dicas para Exclusão de Transações
    
    **Quando usar:**
    - Transações duplicadas
    - Transações de teste ou erro
    - Movimentações internas que não representam gastos reais
    - Transferências entre contas próprias
    
    **Segurança:**
    - Exclusões são reversíveis - você pode restaurar a qualquer momento
    - Use "Gerenciar Transações Excluídas" para ver e restaurar
    - Exporte a lista de exclusões como backup
    
    ### 🏷️ Exemplos de Categorias Personalizadas
    - **Pets**: Ração, veterinário, petshop
    - **Doações**: Instituições de caridade, causas sociais
    - **Hobby**: Coleções, artesanato, instrumentos musicais
    - **Negócios**: Despesas de trabalho freelance
    - **Família**: Presentes, eventos familiares
      ### ⚠️ Importante
    - **Mudanças pendentes** são perdidas se você sair da página sem salvar
    - **Filtros aplicados** não afetam as mudanças pendentes de outras páginas
    - **Categorias personalizadas** são aplicadas em todo o sistema automaticamente
    - **Transações excluídas** não aparecem nos gráficos da página Home
    - **Exclusões são temporárias** e podem ser restauradas a qualquer momento
    - **Descrições personalizadas** são salvas permanentemente e podem ser exportadas
    - **Transações manuais** são permanentes e integradas ao sistema completo
    - **Backup regular** das transações manuais é recomendado via exportação JSON
    """)