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
import time
from datetime import datetime, timedelta

# BACKEND V2 OBRIGATÓRIO - Importações exclusivas
from utils.database_manager_v2 import DatabaseManager
from utils.repositories_v2 import TransacaoRepository, UsuarioRepository
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
        transacao_repo = TransacaoRepository(db_manager)
        usuario_repo = UsuarioRepository(db_manager)
        transacao_service = TransacaoService()
        
        return {
            'db_manager': db_manager,
            'transacao_repo': transacao_repo,
            'usuario_repo': usuario_repo,
            'transacao_service': transacao_service
        }
    except Exception as e:
        st.error(f"❌ Erro ao inicializar Backend V2: {e}")
        st.stop()

backend_v2 = init_backend_v2_gerenciar()

# Funções auxiliares para manipulação do banco de dados
def atualizar_categoria_no_banco(usuario, descricao, nova_categoria):
    """Atualiza categoria de uma transação no banco de dados"""
    try:
        user_data = backend_v2['usuario_repo'].obter_usuario_por_username(usuario)
        if not user_data:
            return False
            
        transacao_repo = backend_v2['transacao_repo']
        
        # Buscar a transação pela descrição para obter dados completos
        df_user = backend_v2['transacao_service'].listar_transacoes_usuario(usuario, limite=10000)
        transacao_match = df_user[df_user['descricao'] == descricao]
        
        if transacao_match.empty:
            st.error(f"Transação não encontrada: {descricao[:50]}...")
            return False
        
        # Usar os dados da primeira transação encontrada
        row = transacao_match.iloc[0]
        data_str = str(row['data'])[:10] if isinstance(row['data'], str) else row['data'].strftime('%Y-%m-%d')
        hash_transacao = transacao_repo.gerar_hash_transacao(data_str, row['descricao'], float(row['valor']))
        
        return transacao_repo.atualizar_categoria_transacao(
            user_data['id'], hash_transacao, nova_categoria
        )
    except Exception as e:
        st.error(f"Erro ao atualizar categoria no banco: {e}")
        return False

def atualizar_categorias_lote_no_banco(usuario, mapeamento_descricoes):
    """Atualiza categorias em lote no banco de dados"""
    try:
        user_data = backend_v2['usuario_repo'].obter_usuario_por_username(usuario)
        if not user_data:
            return 0
            
        transacao_repo = backend_v2['transacao_repo']
        
        # Buscar todas as transações do usuário para obter dados completos
        df_user = backend_v2['transacao_service'].listar_transacoes_usuario(usuario, limite=10000)
        
        # Converter descrições para hashes usando dados reais
        mapeamento_hashes = {}
        transacoes_encontradas = 0
        
        for descricao_normalizada, categoria in mapeamento_descricoes.items():
            # Buscar transações que contenham a descrição (busca mais flexível)
            # Primeiro tenta match exato
            mask = df_user['descricao'].str.lower().str.strip() == descricao_normalizada
            transacoes_match = df_user[mask]
            
            # Se não encontrou com match exato, tenta busca por substring
            if transacoes_match.empty:
                # Remove caracteres especiais e tenta match parcial
                descricao_limpa = descricao_normalizada.replace('-', ' ').replace('*', ' ').strip()
                palavras_chave = [p.strip() for p in descricao_limpa.split() if len(p.strip()) > 2]
                
                if palavras_chave:
                    # Busca por qualquer palavra-chave na descrição
                    pattern = '|'.join(palavras_chave)
                    mask = df_user['descricao'].str.lower().str.contains(pattern, case=False, na=False)
                    transacoes_match = df_user[mask]
            
            # Processar transações encontradas
            for _, row in transacoes_match.iterrows():
                try:
                    data_str = str(row['data'])[:10] if isinstance(row['data'], str) else row['data'].strftime('%Y-%m-%d')
                    hash_transacao = transacao_repo.gerar_hash_transacao(data_str, row['descricao'], float(row['valor']))
                    mapeamento_hashes[hash_transacao] = categoria
                    transacoes_encontradas += 1
                except Exception as ex:
                    st.warning(f"Erro ao processar transação {row.get('descricao', 'N/A')}: {ex}")
                    continue
        
        if not mapeamento_hashes:
            st.warning(f"Nenhuma transação foi encontrada no banco para as {len(mapeamento_descricoes)} descrições fornecidas")
            # Debug: mostrar as descrições que não foram encontradas
            st.info(f"Descrições buscadas: {', '.join(list(mapeamento_descricoes.keys())[:3])}...")
            return 0
        
        resultado = transacao_repo.atualizar_categorias_lote(
            user_data['id'], mapeamento_hashes
        )
        
        if resultado > 0:
            st.info(f"✅ {resultado} transações categorizadas no banco de dados ({transacoes_encontradas} encontradas)")
        
        return resultado
        
    except Exception as e:
        st.error(f"Erro ao atualizar categorias em lote no banco: {e}")
        return 0

def excluir_transacao_no_banco(usuario, row):
    """Exclui uma transação no banco de dados"""
    try:
        user_data = backend_v2['usuario_repo'].obter_usuario_por_username(usuario)
        if not user_data:
            return False
            
        transacao_repo = backend_v2['transacao_repo']
        hash_transacao = gerar_hash_transacao(row)
        
        return transacao_repo.excluir_transacao(user_data['id'], hash_transacao)
    except Exception as e:
        st.error(f"Erro ao excluir transação no banco: {e}")
        return False

def excluir_transacoes_lote_no_banco(usuario, rows):
    """Exclui múltiplas transações no banco de dados"""
    try:
        user_data = backend_v2['usuario_repo'].obter_usuario_por_username(usuario)
        if not user_data:
            return 0
            
        transacao_repo = backend_v2['transacao_repo']
        hashes = [gerar_hash_transacao(row) for row in rows]
        
        return transacao_repo.excluir_transacoes_lote(user_data['id'], hashes)
    except Exception as e:
        st.error(f"Erro ao excluir transações em lote no banco: {e}")
        return 0

# Funções auxiliares para manipulação do banco de dados

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
    "Supermercado",    
    "Restaurante",
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
    # Verificar se row é um dicionário ou objeto semelhante
    if isinstance(row, dict) or hasattr(row, '__getitem__'):
        # Usar data, descrição e valor para criar um identificador único
        data = row["Data"]
        data_str = data.strftime("%Y-%m-%d") if hasattr(data, 'strftime') else str(data)
        chave = f"{data_str}|{row['Descrição']}|{row['Valor']}"
        return hashlib.md5(chave.encode()).hexdigest()
    else:
        # Se já for um hash, retornar como está
        return str(row)

# Função principal para carregar transações usando Backend V2
@st.cache_data(ttl=300, show_spinner="Carregando transações...")
def carregar_transacoes_v2(usuario, periodo_dias=365, cache_version=None):
    """Carrega todas as transações usando Backend V2 com personalizações
    cache_version: parâmetro usado para forçar refresh quando cache de categorias muda"""
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
              # Aplicar categorizações do cache apenas para transações sem categoria definida no banco
            cache = carregar_cache_categorias()
            if cache:
                def aplicar_categoria_personalizada(row):
                    # Usar categoria do banco se existir e não for "Outros" ou vazia
                    categoria_banco = row.get("Categoria", "")
                    if categoria_banco and categoria_banco != "Outros" and categoria_banco.strip():
                        return categoria_banco
                    
                    # Caso contrário, verificar cache local como fallback
                    descricao_normalizada = row["Descrição"].lower().strip()
                    if descricao_normalizada in cache:
                        return cache[descricao_normalizada]
                    return "Outros"
                
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
    return carregar_transacoes_v2(usuario_atual, periodo_dias=730, cache_version=get_cache_categorias_version())

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
    """Exclui uma transação específica adicionando-a à lista de excluídas e persistindo no banco"""
    # Persistir no banco primeiro
    usuario = get_current_user()
    success_bd = excluir_transacao_no_banco(usuario, row)
    
    # Também manter no arquivo local para compatibilidade
    transacoes_excluidas = carregar_transacoes_excluidas()
    hash_transacao = gerar_hash_transacao(row)
    
    if hash_transacao not in transacoes_excluidas:
        transacoes_excluidas.append(hash_transacao)
        arquivo_salvo = salvar_transacoes_excluidas(transacoes_excluidas)
        return success_bd or arquivo_salvo
    
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

def salvar_descricao_personalizada(hash_transacao, descricao):
    """Salva uma descrição personalizada para uma transação"""
    descricoes = carregar_descricoes_personalizadas()
    
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
    
    try:        # Preparar dados para envio
        transacoes_para_analisar = []
        for _, row in df_transacoes.iterrows():
            try:
                # Garantir conversão segura para float
                valor = pd.to_numeric(row["Valor"], errors='coerce')
                if pd.isna(valor):
                    valor = 0.0
                    
                transacoes_para_analisar.append({
                    "descricao": row["Descrição"],
                    "valor": float(valor),
                    "categoria_atual": row["Categoria"]
                })
            except (ValueError, TypeError):
                # Pular transações com valores inválidos
                continue
        
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
        6. Para valores positivos (receitas), foque na fonte da receita        TRANSAÇÕES PARA ANALISAR:
        {json.dumps(transacoes_para_analisar, indent=2, ensure_ascii=False)}

        RESPOSTA ESPERADA:
        Retorne um JSON com uma lista onde cada item tem:
        {{"descricao": "descrição da transação", "categoria_sugerida": "categoria escolhida", "confianca": "alta/media/baixa"}}

        Analise todas as transações fornecidas.
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

        # Mapeamento de confiança textual para float
        confianca_map = {"alta": 0.9, "media": 0.7, "baixa": 0.3}
        for sugestao in sugestoes:
            confianca_val = sugestao.get("confianca", 0)
            if isinstance(confianca_val, str):
                sugestao["confianca"] = confianca_map.get(confianca_val.lower(), 0.0)
            elif isinstance(confianca_val, (int, float)):
                sugestao["confianca"] = float(confianca_val)
            else:
                sugestao["confianca"] = 0.0

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

# Selecionar modo de visualização
modo = st.radio(
    "Modo de Visualização",
    ["Transações à Vista", "Transações de Crédito"],
    horizontal=True,
    key="modo_visualizacao"
)

modo_credito = modo == "Transações de Crédito"

# Definir tipo de gestão para exibição
tipo_gestao = "💳 Crédito" if modo_credito else "💰 À Vista"

# Obter o usuário atual
usuario = st.session_state['usuario']

# Função para versionar o cache de categorias
def get_cache_categorias_version():
    """Retorna uma versão baseada no timestamp do arquivo de cache de categorias"""
    cache_file = get_cache_categorias_file()
    if os.path.exists(cache_file):
        return os.path.getmtime(cache_file)
    return 0

# Carregar dados com Backend V2
@st.cache_data(ttl=300, show_spinner="Carregando transações atualizadas...")
def carregar_dados_v2(modo_credito: bool = False, cache_version=None):
    """Carrega dados das transações usando Backend V2
    cache_version: parâmetro usado para forçar refresh quando categorias são atualizadas"""
    try:
        # Obter instância dos repositories
        user_data = backend_v2['usuario_repo'].obter_usuario_por_username(usuario)
        if not user_data:
            st.error("❌ Usuário não encontrado")
            return pd.DataFrame()
        
        transacao_repo = backend_v2['transacao_repo']
        
        # Obtém período dinâmico
        hoje = datetime.now()
        data_fim = hoje
        data_inicio = hoje - timedelta(days=90)  # últimos 90 dias por padrão
        
        # Buscar transações
        df = transacao_repo.obter_transacoes_periodo(
            user_id=user_data['id'],
            data_inicio=data_inicio.strftime("%Y-%m-%d"),
            data_fim=data_fim.strftime("%Y-%m-%d")
        )
        
        if df.empty:
            return pd.DataFrame()
            
        # Renomear colunas para padrão
        df = df.rename(columns={
            'data': 'Data',
            'descricao': 'Descrição',
            'valor': 'Valor',
            'categoria': 'Categoria',
            'nota': 'Nota',
            'excluida': 'Excluída'
        })
        
        return df
        
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {str(e)}")
        return pd.DataFrame()

# Carregar dados
df = carregar_dados_v2(modo_credito, cache_version=get_cache_categorias_version())

# Filtrar por tipo (vista/crédito)
if not df.empty:
    if modo_credito:
        df = df[df['origem'] == 'ofx_cartao']
    else:
        df = df[df['origem'] == 'ofx_extrato']

if df.empty:
    st.info(f"Nenhuma transação encontrada para o modo {'crédito' if modo_credito else 'à vista'}.")
    st.stop()

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

# Seção de Categorização Automática com IA
st.subheader("🤖 Categorização Automática com IA")
with st.expander("✨ Usar IA para Categorizar Transações", expanded=False):
    st.markdown("**🎯 Use Inteligência Artificial para categorizar suas transações automaticamente!**")
    st.info("💡 A IA analisa a descrição e valor das transações para sugerir a melhor categoria.")
    
    # Verificar se há transações não categorizadas ou mal categorizadas
    df_nao_categorizadas = df[
        (df["Categoria"].isin(["Outros", "Não Categorizado"])) |        (df["Categoria"].isna())
    ]
    
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    
    with col1:
        st.metric(
            "📊 Transações para categorizar", 
            len(df_nao_categorizadas),
            help="Transações com categoria 'Outros' ou sem categoria"
        )
    
    with col2:
        categorizar_apenas_outros = st.checkbox(
            "Apenas 'Outros'",
            value=True,
            help="Categorizar apenas transações marcadas como 'Outros'"
        )
    
    with col3:
        # Seletor de quantidade de transações para categorizar
        max_disponivel = len(df_nao_categorizadas) if categorizar_apenas_outros else len(df)
        quantidade_categorizar = st.selectbox(
            "Quantidade",
            options=["Todas"] + [10, 25, 50, 100, 200, 500],
            index=0,
            help="Escolha quantas transações categorizar com IA"        )
    
    with col4:
        st.write("")  # Espaçamento
        acionar_categorizacao = st.button("🚀 Categorizar com IA", type="primary", use_container_width=True)

    # Aviso sobre custo da API para grandes quantidades
    if quantidade_categorizar == "Todas" or (quantidade_categorizar != "Todas" and int(quantidade_categorizar) > 100):
        qtd_real = len(df_nao_categorizadas) if categorizar_apenas_outros else len(df)
        if qtd_real > 100:
            st.warning(f"⚠️ **Atenção:** Você está prestes a processar {qtd_real} transações. Isso pode consumir mais tokens da API OpenAI e demorar mais tempo.")

    sugestoes = None
    if acionar_categorizacao:
        # Limpar sugestões anteriores quando iniciar nova categorização
        if 'sugestoes_ia' in st.session_state:
            del st.session_state.sugestoes_ia
        st.session_state.sugestoes_aceitas = set()
        st.session_state.sugestoes_rejeitadas = set()
        st.session_state.pagina_atual = 0
        
        if len(df_nao_categorizadas) == 0:
            st.warning("⚠️ Não há transações para categorizar!")
        else:
            with st.spinner("🤖 IA analisando transações..."):
                try:
                    df_para_categorizar = df_nao_categorizadas if categorizar_apenas_outros else df
                    
                    # Aplicar limitação baseada na seleção do usuário
                    if quantidade_categorizar != "Todas":
                        qtd_limite = int(quantidade_categorizar)
                        if len(df_para_categorizar) > qtd_limite:
                            df_para_categorizar = df_para_categorizar.head(qtd_limite)
                            st.info(f"📋 Processando as {len(df_para_categorizar)} transações mais recentes de {len(df_nao_categorizadas if categorizar_apenas_outros else df)} disponíveis.")
                    else:
                        st.info(f"📋 Processando todas as {len(df_para_categorizar)} transações disponíveis.")
                    
                    categorias_disponiveis = get_todas_categorias()
                    sugestoes = categorizar_transacoes_com_llm(df_para_categorizar, categorias_disponiveis)
                    if sugestoes:
                        # Salvar sugestões no session_state para persistir entre recarregamentos
                        st.session_state.sugestoes_ia = sugestoes
                        st.success(f"✅ IA gerou {len(sugestoes)} sugestões de categorização!")
                        df_categorizado = aplicar_categorizacao_llm(df_para_categorizar, sugestoes)
                    else:                        st.error("❌ IA não conseguiu gerar sugestões. Tente novamente.")
                except Exception as e:
                    st.error(f"❌ Erro na categorização por IA: {str(e)}")
                    st.error("💡 Verifique se a configuração da IA está correta.")
    
    # Exibir prévia das sugestões fora das colunas laterais
    # Usar sugestões do session_state se disponíveis, senão usar a variável local
    if 'sugestoes_ia' in st.session_state:
        sugestoes_para_exibir = st.session_state.sugestoes_ia
    else:
        sugestoes_para_exibir = None
    
    if sugestoes_para_exibir and isinstance(sugestoes_para_exibir, list) and len(sugestoes_para_exibir) > 0:
        st.markdown("**📋 Prévia das sugestões da IA:**")
        
        # Ajuda sobre correção manual em uma caixa de informação
        st.info("""
💡 **Como usar a correção manual:**
- Use o **selectbox de categoria** para corrigir sugestões incorretas da IA
- Sugestões corrigidas são marcadas com 🔧 **CORRIGIDA**  
- As correções são aplicadas automaticamente quando você aceita a sugestão
- Para voltar à categoria original, simplesmente selecione-a novamente no selectbox
        """)
        
        # Inicializar estado da sessão para sugestões aceitas/rejeitadas
        if 'sugestoes_aceitas' not in st.session_state:
            st.session_state.sugestoes_aceitas = set()
        if 'sugestoes_rejeitadas' not in st.session_state:
            st.session_state.sugestoes_rejeitadas = set()
        if 'pagina_atual' not in st.session_state:
            st.session_state.pagina_atual = 0
          # Configuração da paginação
        sugestoes_por_pagina = 10
        total_paginas = (len(sugestoes_para_exibir) - 1) // sugestoes_por_pagina + 1
        
        # Controles de paginação
        col_pag1, col_pag2, col_pag3 = st.columns([1, 2, 1])
        
        with col_pag1:
            if st.button("◀️ Anterior", disabled=st.session_state.pagina_atual == 0):
                st.session_state.pagina_atual = max(0, st.session_state.pagina_atual - 1)
                st.rerun()
        
        with col_pag2:
            st.markdown(f"<div style='text-align: center;'>Página {st.session_state.pagina_atual + 1} de {total_paginas}</div>", unsafe_allow_html=True)
        
        with col_pag3:
            if st.button("Próxima ▶️", disabled=st.session_state.pagina_atual >= total_paginas - 1):
                st.session_state.pagina_atual = min(total_paginas - 1, st.session_state.pagina_atual + 1)
                st.rerun()
        
        # Calcular índices da página atual
        inicio = st.session_state.pagina_atual * sugestoes_por_pagina
        fim = min(inicio + sugestoes_por_pagina, len(sugestoes_para_exibir))
        sugestoes_pagina = sugestoes_para_exibir[inicio:fim]
        
        # Exibir sugestões da página atual
        for i, sugestao in enumerate(sugestoes_pagina):
            idx_global = inicio + i
            descricao = sugestao.get('descricao', 'N/A')
            categoria_sugerida = sugestao.get('categoria_sugerida', sugestao.get('categoria', 'N/A'))
            confianca = sugestao.get('confianca', 0)
              # Cor baseada na confiança
            if confianca > 0.8:
                cor_emoji = "🟢"
            elif confianca > 0.6:
                cor_emoji = "🟡"
            else:
                cor_emoji = "🔴"
            
            # Status da sugestão
            status = ""
            if idx_global in st.session_state.sugestoes_aceitas:
                status = " ✅ **ACEITA**"
            elif idx_global in st.session_state.sugestoes_rejeitadas:
                status = " ❌ **REJEITADA**"
            
            # Inicializar correções manuais se não existir
            if 'correcoes_manuais' not in st.session_state:
                st.session_state.correcoes_manuais = {}
            
            # Verificar se há correção manual para esta sugestão
            categoria_final = st.session_state.correcoes_manuais.get(idx_global, categoria_sugerida)
            icone_corrigido = " 🔧 **CORRIGIDA**" if idx_global in st.session_state.correcoes_manuais else ""
            
            # Exibir sugestão com layout expandido
            col_info, col_categoria, col_aceitar, col_rejeitar = st.columns([2.5, 1.5, 0.7, 0.7])
            
            with col_info:
                st.markdown(f"**📝 {descricao}**")
                st.caption(f"Confiança: {cor_emoji} *{confianca:.0%}*{status}{icone_corrigido}")
            
            with col_categoria:
                # Selectbox para correção manual da categoria
                categoria_corrigida = st.selectbox(
                    "🏷️ Categoria",
                    options=get_todas_categorias(),
                    index=get_todas_categorias().index(categoria_final) if categoria_final in get_todas_categorias() else 0,
                    key=f"categoria_correcao_{idx_global}",
                    help="Corrija a categoria se a IA sugeriu incorretamente"
                )
                
                # Se a categoria foi alterada, salvar a correção
                if categoria_corrigida != categoria_sugerida:
                    st.session_state.correcoes_manuais[idx_global] = categoria_corrigida
                elif idx_global in st.session_state.correcoes_manuais and categoria_corrigida == categoria_sugerida:
                    # Se voltou para a original, remover da lista de correções
                    del st.session_state.correcoes_manuais[idx_global]
            
            with col_aceitar:
                if st.button("✅", key=f"aceitar_{idx_global}", 
                           disabled=idx_global in st.session_state.sugestoes_aceitas,
                           help="Aceitar esta sugestão"):
                    st.session_state.sugestoes_aceitas.add(idx_global)
                    st.session_state.sugestoes_rejeitadas.discard(idx_global)
                    st.rerun()
            
            with col_rejeitar:
                if st.button("❌", key=f"rejeitar_{idx_global}",
                           disabled=idx_global in st.session_state.sugestoes_rejeitadas,
                           help="Rejeitar esta sugestão"):
                    st.session_state.sugestoes_rejeitadas.add(idx_global)
                    st.session_state.sugestoes_aceitas.discard(idx_global)
                    st.rerun()
            
            st.markdown("---")
          # Resumo das ações
        total_aceitas = len(st.session_state.sugestoes_aceitas)
        total_rejeitadas = len(st.session_state.sugestoes_rejeitadas)
        total_corrigidas = len(st.session_state.get('correcoes_manuais', {}))
        
        if total_aceitas > 0 or total_rejeitadas > 0 or total_corrigidas > 0:
            info_text = f"📊 Resumo: {total_aceitas} aceitas, {total_rejeitadas} rejeitadas"
            if total_corrigidas > 0:
                info_text += f", {total_corrigidas} corrigidas manualmente"
            info_text += f" de {len(sugestoes_para_exibir)} sugestões"
            st.info(info_text)
          # Botões para aplicar ou descartar
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("✅ Aplicar Aceitas", type="primary", use_container_width=True,
                        disabled=len(st.session_state.sugestoes_aceitas) == 0):
                aplicacoes_sucesso = 0
                mapeamento_descricoes = {}
                
                # Coletar todas as sugestões aceitas
                for idx in st.session_state.sugestoes_aceitas:
                    if idx < len(sugestoes_para_exibir):
                        sugestao = sugestoes_para_exibir[idx]
                        try:
                            mask = df["Descrição"].str.contains(
                                sugestao["descricao"][:20],
                                case=False,
                                na=False
                            )
                            if mask.any():
                                # Usar categoria corrigida manualmente ou a sugerida pela IA
                                if idx in st.session_state.get('correcoes_manuais', {}):
                                    categoria_para_aplicar = st.session_state.correcoes_manuais[idx]
                                else:
                                    categoria_para_aplicar = sugestao.get("categoria_sugerida", sugestao.get("categoria", "Outros"))
                                
                                descricao_normalizada = sugestao["descricao"].lower().strip()
                                mapeamento_descricoes[descricao_normalizada] = categoria_para_aplicar
                                aplicacoes_sucesso += 1
                        except Exception as e:
                            st.error(f"Erro ao aplicar sugestão: {e}")
                            continue
                
                if aplicacoes_sucesso > 0:
                    # Persistir APENAS no banco de dados (Backend V2) - removendo dependência do cache local
                    categorias_atualizadas_bd = atualizar_categorias_lote_no_banco(usuario, mapeamento_descricoes)
                    
                    if categorias_atualizadas_bd > 0:
                        msg = f"✅ {aplicacoes_sucesso} categorizações aplicadas com sucesso!"
                        msg += f" ({categorias_atualizadas_bd} persistidas no banco de dados)"
                        st.success(msg)
                        
                        # Limpar estados e prévia de sugestões
                        if 'sugestoes_ia' in st.session_state:
                            del st.session_state.sugestoes_ia
                        st.session_state.sugestoes_aceitas = set()
                        st.session_state.sugestoes_rejeitadas = set()
                        st.session_state.correcoes_manuais = {}
                        st.session_state.pagina_atual = 0
                        
                        # Limpar caches para forçar reload dos dados atualizados
                        st.cache_data.clear()
                        st.cache_resource.clear()
                        
                        # Pequeno atraso para garantir que a transação foi commitada
                        time.sleep(0.5)
                        
                        # Recarregar a página
                        st.rerun()
                    else:
                        st.error("❌ Erro ao persistir categorizações no banco de dados!")
                        
                        # Fallback: tentar salvar no cache local apenas se o banco falhou
                        cache = carregar_cache_categorias()
                        cache.update(mapeamento_descricoes)
                        cache_salvo = salvar_cache_categorias(cache)
                        
                        if cache_salvo:
                            st.warning(f"⚠️ {aplicacoes_sucesso} categorizações salvas apenas no cache local")
                            # Limpar estados
                            if 'sugestoes_ia' in st.session_state:
                                del st.session_state.sugestoes_ia
                            st.session_state.sugestoes_aceitas = set()
                            st.session_state.sugestoes_rejeitadas = set()
                            st.session_state.correcoes_manuais = {}
                            st.session_state.pagina_atual = 0
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error("❌ Falha completa ao salvar categorizações!")
                else:
                    st.error("❌ Nenhuma categorização foi aplicada.")
        
        with col2:
            if st.button("✅ Aceitar Todas", use_container_width=True):
                st.session_state.sugestoes_aceitas = set(range(len(sugestoes_para_exibir)))
                st.session_state.sugestoes_rejeitadas = set()
                st.rerun()
        
        with col3:
            if st.button("❌ Limpar Seleções", use_container_width=True):
                st.session_state.sugestoes_aceitas = set()
                st.session_state.sugestoes_rejeitadas = set()
                st.session_state.correcoes_manuais = {}
                st.rerun()    # Estatísticas de categorização
    st.markdown("---")
    st.markdown("**📊 Estatísticas de Categorização:**")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_transacoes = len(df)
        st.metric("📋 Total", total_transacoes)
    
    with col2:
        categorizadas = len(df[~df["Categoria"].isin(["Outros", "Não Categorizado"])])
        st.metric("✅ Categorizadas", categorizadas)
    
    with col3:
        nao_categorizadas = len(df[df["Categoria"].isin(["Outros", "Não Categorizado"])])
        st.metric("❓ Sem Categoria", nao_categorizadas)
    
    with col4:
        if total_transacoes > 0:
            percentual = (categorizadas / total_transacoes) * 100
            st.metric("📊 % Categorizadas", f"{percentual:.1f}%")
        else:
            st.metric("📊 % Categorizadas", "0%")

# Seção de adicionar transação manual (apenas para modo à vista)
if not modo_credito:
    st.subheader("➕ Adicionar Transação Manual")
    with st.expander("💰 Registrar Nova Transação (Espécie/Outros)", expanded=False):
        st.markdown("**Use esta funcionalidade para registrar transações em dinheiro, presentes recebidos, vendas, ou qualquer movimentação financeira que não aparece nos extratos bancários.**")
        
        with st.form("adicionar_transacao_manual"):
            col1, col2 = st.columns(2)
            
            with col1:
                # Data da transação
                data_transacao = st.date_input(
                    "📅 Data da Transação",
                    value=datetime.now().date(),
                    help="Selecione a data em que a transação ocorreu"
                )
                
                # Descrição
                descricao_manual = st.text_input(
                    "📝 Descrição",
                    placeholder="Ex: Almoço restaurante, Venda de item usado, etc.",
                    help="Descreva a transação de forma clara"
                )
                
                # Valor
                valor_manual = st.number_input(
                    "💰 Valor (R$)",
                    min_value=0.01,
                    value=10.0,
                    step=0.01,
                    format="%.2f",
                    help="Digite o valor da transação (sempre positivo)"
                )
            
            with col2:
                # Tipo da transação
                tipo_transacao_manual = st.selectbox(
                    "🔄 Tipo",
                    ["💸 Despesa", "💰 Receita"],
                    help="Escolha se é uma despesa ou receita"
                )
                
                # Categoria
                categoria_manual = st.selectbox(
                    "🏷️ Categoria",
                    get_todas_categorias(),
                    help="Escolha a categoria da transação"
                )
                
                # Descrição personalizada (opcional)
                descricao_personalizada_manual = st.text_input(
                    "📋 Nota Pessoal (Opcional)",
                    placeholder="Ex: Pagamento para João, Presente aniversário...",
                    help="Adicione uma descrição personalizada se desejar"
                )
                
                # Tipo de pagamento
                tipo_pagamento_manual = st.selectbox(
                    "💳 Forma de Pagamento",
                    ["Espécie", "PIX", "Transferência", "Outro"],
                    help="Como foi realizada a transação"
                )
            
            # Botão de envio
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
                        
                        if descricao_personalizada_manual:
                            st.info(f"📋 **Nota:** {descricao_personalizada_manual}")
                    
                    # Aguardar um pouco e recarregar
                    time.sleep(3)
                    st.rerun()

# Gerenciar transações manuais existentes (apenas para modo à vista)
if not modo_credito:
    with st.expander("📋 Gerenciar Transações Manuais", expanded=False):
        transacoes_manuais_existentes = carregar_transacoes_manuais()
        
        if transacoes_manuais_existentes:
            st.markdown(f"**📊 Total de transações manuais: {len(transacoes_manuais_existentes)}**")
            
            # Ordenar por data (mais recente primeiro)
            transacoes_ordenadas = sorted(transacoes_manuais_existentes, key=lambda x: x["data"], reverse=True)
            
            # Mostrar transações em formato organizado
            for i, transacao in enumerate(transacoes_ordenadas):
                with st.container():
                    col1, col2, col3, col4, col5 = st.columns([2, 3, 2, 2, 1])
                    
                    with col1:
                        data_formatada = datetime.strptime(transacao["data"], "%Y-%m-%d").strftime("%d/%m/%Y")
                        st.text(f"📅 {data_formatada}")
                    
                    with col2:
                        descricao_exibida = transacao["descricao"][:40] + ("..." if len(transacao["descricao"]) > 40 else "")
                        st.text(f"📝 {descricao_exibida}")
                    
                    with col3:
                        valor = transacao["valor"]
                        emoji = "💰" if valor > 0 else "💸"
                        cor = "green" if valor > 0 else "red"
                        st.markdown(f"{emoji} <span style='color: {cor}'>R$ {abs(valor):,.2f}</span>", unsafe_allow_html=True)
                    
                    with col4:
                        st.text(f"🏷️ {transacao['categoria']}")
                    
                    with col5:
                        if st.button("🗑️", key=f"delete_manual_{i}", help="Remover transação"):
                            # Remover transação
                            transacoes_manuais_existentes.remove(transacao)
                            salvar_transacoes_manuais(transacoes_manuais_existentes)
                            st.success("✅ Transação removida!")
                            st.rerun()
                    
                    # Mostrar nota pessoal se existir
                    if transacao.get("descricao_personalizada"):
                        st.caption(f"💭 {transacao['descricao_personalizada']}")
                    
                    st.markdown("---")
            
            # Botão para exportar
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📤 Exportar Transações Manuais", use_container_width=True):
                    import json
                    export_data = json.dumps(transacoes_manuais_existentes, indent=2, ensure_ascii=False)
                    
                    st.download_button(
                        label="💾 Baixar Arquivo JSON",
                        data=export_data,
                        file_name=f"transacoes_manuais_{datetime.now().strftime('%Y%m%d')}.json",
                        mime="application/json"
                    )
        else:
            st.info("📝 Nenhuma transação manual registrada ainda.")
            st.markdown("Use o formulário acima para adicionar suas primeiras transações manuais.")

# Funcionalidades específicas para modo crédito
if modo_credito:
    st.subheader("🎯 Funcionalidades Específicas de Crédito")
    
    # Análise por estabelecimento
    with st.expander("🏪 Análise por Estabelecimento", expanded=False):
        st.markdown("**💳 Seus gastos organizados por estabelecimento:**")
        
        if not df.empty:
            # Agrupar por estabelecimento (primeiras palavras da descrição)
            df_estabelecimentos = df.copy()
            df_estabelecimentos["Estabelecimento"] = df_estabelecimentos["Descrição"].str.split().str[:2].str.join(" ")
            
            gastos_estabelecimento = df_estabelecimentos[df_estabelecimentos["Valor"] < 0].groupby("Estabelecimento")["Valor"].agg(['sum', 'count']).reset_index()
            gastos_estabelecimento["Valor_Abs"] = gastos_estabelecimento["sum"].abs()
            gastos_estabelecimento = gastos_estabelecimento.sort_values("Valor_Abs", ascending=False)
            
            # Mostrar top 10 estabelecimentos
            st.markdown("**🏆 Top 10 Estabelecimentos por Gasto:**")
            
            for i, row in gastos_estabelecimento.head(10).iterrows():
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.text(f"🏪 {row['Estabelecimento']}")
                
                with col2:
                    st.metric("💰 Gasto", f"R$ {row['Valor_Abs']:,.0f}")
                
                with col3:
                    st.metric("🧾 Compras", f"{row['count']}")
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
                            # Garantir que a data seja datetime antes de formatar
                            data_obj = pd.to_datetime(transacao["Data"]) if isinstance(transacao["Data"], str) else transacao["Data"]
                            data_formatada = data_obj.strftime("%d/%m/%Y")
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
            
            # Garantir que a coluna Data seja datetime antes da comparação
            df_temp = df.copy()
            df_temp["Data"] = pd.to_datetime(df_temp["Data"])
            df_mes_atual = df_temp[(df_temp["Data"] >= pd.to_datetime(inicio_mes)) & (df_temp["Valor"] < 0)]
            
            if not df_mes_atual.empty:
                gastos_categoria = df_mes_atual.groupby("Categoria")["Valor"].sum().abs().sort_values(ascending=False)
                
                st.markdown(f"**📊 Gastos do mês atual ({hoje.strftime('%m/%Y')}):**")
                
                for categoria, gasto in gastos_categoria.head(5).items():
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        st.text(f"🏷️ {categoria}")
                    
                    with col2:
                        st.metric("💸 Gasto", f"R$ {gasto:,.0f}")
                    
                    with col3:
                        # Simulação de meta (pode ser implementada com configuração do usuário)
                        meta_simulada = gasto * 1.2  # 20% acima do gasto atual
                        progresso = min(gasto / meta_simulada, 1.0)
                        
                        with st.container():
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
    # Filtro por tipo
    if modo_credito:
        tipos_disponiveis = ["Todos", "Compras", "Estornos"]
        tipo_selecionado = st.selectbox("Tipo de Transação", tipos_disponiveis)
    else:
        tipos_disponiveis = ["Todos", "Receitas", "Despesas"]
        tipo_selecionado = st.selectbox("Tipo de Transação", tipos_disponiveis)

# Aplicar filtros
df_filtrado = aplicar_filtros(df, data_inicio, data_fim, categorias_selecionadas)

# Aplicar filtro por tipo
if tipo_selecionado != "Todos":
    if modo_credito:
        if tipo_selecionado == "Compras":
            df_filtrado = df_filtrado[df_filtrado["Valor"] < 0]
        elif tipo_selecionado == "Estornos":
            df_filtrado = df_filtrado[df_filtrado["Valor"] > 0]
    else:
        if tipo_selecionado == "Receitas":
            df_filtrado = df_filtrado[df_filtrado["Valor"] > 0]
        elif tipo_selecionado == "Despesas":
            df_filtrado = df_filtrado[df_filtrado["Valor"] < 0]

# Resumo dos dados filtrados
st.subheader("📊 Resumo")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("📋 Transações", len(df_filtrado))

with col2:
    receitas = df_filtrado[df_filtrado["Valor"] > 0]["Valor"].sum()
    st.metric("💰 Receitas", formatar_valor_monetario(receitas))

with col3:
    despesas = abs(df_filtrado[df_filtrado["Valor"] < 0]["Valor"].sum())
    st.metric("💸 Despesas", formatar_valor_monetario(despesas))

with col4:
    saldo = receitas - despesas
    delta_color = "normal" if saldo >= 0 else "inverse"
    st.metric("💳 Saldo", formatar_valor_monetario(saldo), delta_color=delta_color)

# Edição em lote
st.subheader("⚡ Edição em Lote")
modo_edicao_lote = st.toggle(
    "🔄 Ativar Modo Edição em Lote",
    help="Selecione transações e aplique categorias rapidamente"
)

if modo_edicao_lote:
    if 'transacoes_selecionadas' not in st.session_state:
        st.session_state.transacoes_selecionadas = set()    # Interface minimalista - busca, categoria e ações
    col1, col2, col3 = st.columns([3, 2, 2])
    
    with col1:
        # Busca rápida por padrão
        padrao = st.text_input(
            "🔍 Buscar por padrão",
            placeholder="Digite algo para selecionar automaticamente (Ex: PIX, UBER, IFOOD...)",
            help="Seleciona automaticamente transações que contenham este texto",
            key="busca_lote"
        )
        if padrao:
            # Seleção automática ao digitar
            indices = []
            for i, row in df_filtrado.iterrows():
                if padrao.lower() in row['Descrição'].lower():
                    indices.append(df_filtrado.index.get_loc(i))
            st.session_state.transacoes_selecionadas = set(indices)
    
    with col2:
        # Categoria para aplicar
        categoria_lote = st.selectbox(
            "🏷️ Categoria",
            get_todas_categorias(),
            key="cat_lote",
            help="Categoria para aplicar às transações selecionadas"
        )
    
    with col3:
        # Botões de ação lado a lado
        num_selecionadas = len(st.session_state.transacoes_selecionadas)
        col_cat, col_del = st.columns(2)
        
        with col_cat:
            if st.button(
                f"✅ Categorizar ({num_selecionadas})",
                type="primary",
                disabled=num_selecionadas == 0,
                use_container_width=True,
                help=f"Aplicar categoria '{categoria_lote}' a {num_selecionadas} transações"
            ):
                # Preparar mapeamento para persistir no banco
                mapeamento_descricoes = {}
                aplicadas = 0
                
                for idx in st.session_state.transacoes_selecionadas:
                    if idx < len(df_filtrado):
                        row = df_filtrado.iloc[idx]
                        descricao_normalizada = row['Descrição'].lower().strip()
                        mapeamento_descricoes[descricao_normalizada] = categoria_lote
                        aplicadas += 1
                
                if aplicadas > 0:
                    # Persistir no banco de dados (Backend V2)
                    categorias_atualizadas_bd = atualizar_categorias_lote_no_banco(usuario, mapeamento_descricoes)
                    
                    # Também manter no cache para compatibilidade (mas não sobrescrever banco)
                    cache = carregar_cache_categorias()
                    cache.update(mapeamento_descricoes)
                    cache_salvo = salvar_cache_categorias(cache)
                    
                    if categorias_atualizadas_bd > 0:
                        msg = f"✅ {aplicadas} transações categorizadas como '{categoria_lote}'!"
                        msg += f" ({categorias_atualizadas_bd} persistidas no banco de dados)"
                        st.success(msg)
                          # Limpar seleção e forçar recarregamento completo
                        st.session_state.transacoes_selecionadas = set()
                        # Limpar TODOS os caches para forçar reload dos dados do banco
                        st.cache_data.clear()
                        st.cache_resource.clear()
                        # Recarregar página
                        st.rerun()
                    elif cache_salvo:
                        st.warning(f"⚠️ {aplicadas} transações categorizadas apenas no cache local (não persistidas no banco)")
                        st.session_state.transacoes_selecionadas = set()
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("❌ Erro ao salvar categorizações!")
                        st.session_state.transacoes_selecionadas = set()
                else:
                    st.error("❌ Nenhuma transação foi processada!")
                    st.session_state.transacoes_selecionadas = set()
                    st.cache_data.clear()
                    st.rerun()
        
        with col_del:
            if st.button(
                f"🗑️ Excluir ({num_selecionadas})",
                disabled=num_selecionadas == 0,
                use_container_width=True,
                help=f"Excluir {num_selecionadas} transações selecionadas"
            ):
                excluidas = 0
                
                for idx in st.session_state.transacoes_selecionadas:
                    if idx < len(df_filtrado):
                        row = df_filtrado.iloc[idx]
                        if excluir_transacao(row):
                            excluidas += 1
                
                if excluidas > 0:
                    st.success(f"🗑️ {excluidas} transações excluídas!")
                    # Limpar seleção e recarregar página
                    st.session_state.transacoes_selecionadas = set()
                    st.cache_data.clear()
                    st.rerun()
    
    # Mostrar contador (apenas como informação)
    if st.session_state.transacoes_selecionadas:
        st.caption(f"📋 {len(st.session_state.transacoes_selecionadas)} transações selecionadas")
        
# Lista de transações
st.subheader("📋 Transações")

if len(df_filtrado) == 0:
    st.info("🔍 Nenhuma transação encontrada com os filtros aplicados.")
else:
    st.info(f"📊 Exibindo {len(df_filtrado)} transações")
    
    # Paginação
    items_por_pagina = 50
    total_paginas = (len(df_filtrado) - 1) // items_por_pagina + 1
    
    if total_paginas > 1:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            pagina_atual = st.selectbox(
                "📄 Página",
                range(1, total_paginas + 1),
                format_func=lambda x: f"Página {x} de {total_paginas}"
            )
    else:
        pagina_atual = 1
    
    # Calcular índices para paginação
    inicio_idx = (pagina_atual - 1) * items_por_pagina
    fim_idx = min(inicio_idx + items_por_pagina, len(df_filtrado))
    
    df_pagina = df_filtrado.iloc[inicio_idx:fim_idx]
      # Exibir transações
    for idx, (original_idx, row) in enumerate(df_pagina.iterrows()):
        global_idx = inicio_idx + idx
        
        # Checkbox para seleção (apenas no modo lote)
        if modo_edicao_lote:
            is_selected = global_idx in st.session_state.transacoes_selecionadas
            col_select, col_content = st.columns([0.5, 9.5])
            
            with col_select:
                if st.checkbox("", value=is_selected, key=f"select_{global_idx}_{inicio_idx}"):
                    st.session_state.transacoes_selecionadas.add(global_idx)
                else:                    st.session_state.transacoes_selecionadas.discard(global_idx)
            
            with col_content:
                container = st.container()
        else:
            container = st.container()
        
        with container:
            # Indicador visual se está selecionada (no modo lote)
            prefix = "✅ " if modo_edicao_lote and global_idx in st.session_state.transacoes_selecionadas else ""
            
            with st.expander(
                f"{prefix}{'💰' if row['Valor'] > 0 else '💸'} {row['Data']} - {row['Descrição'][:50]}{'...' if len(row['Descrição']) > 50 else ''} - {formatar_valor_monetario(row['Valor'])}",
                expanded=False
            ):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # Informações da transação
                    st.markdown(f"**📅 Data:** {row['Data']}")
                    st.markdown(f"**📝 Descrição:** {row['Descrição']}")
                    st.markdown(f"**💰 Valor:** {formatar_valor_monetario(row['Valor'])}")
                    st.markdown(f"**🏷️ Categoria Atual:** {row['Categoria']}")
                    if 'Origem' in row:
                        st.markdown(f"**🏦 Origem:** {row['Origem']}")
                      # Exibir descrição personalizada se existir
                    descricoes = carregar_descricoes_personalizadas()
                    hash_transacao = gerar_hash_transacao(row)
                    if hash_transacao in descricoes:
                        st.markdown(f"**📋 Nota Pessoal:** {descricoes[hash_transacao]}")
                
                with col2:
                    if modo_edicao_lote:
                        # Interface minimalista para modo lote
                        st.markdown("**🔄 Modo Lote**")
                        st.info("Use os controles acima para aplicar categorias em lote. Selecione/deselecione com o checkbox à esquerda.")
                    else:
                        # Interface completa para modo individual
                        nova_categoria = st.selectbox(
                            "🏷️ Nova Categoria",
                            get_todas_categorias(),
                            index=get_todas_categorias().index(row['Categoria']) if row['Categoria'] in get_todas_categorias() else 0,
                            key=f"cat_{idx}_{inicio_idx}"                        )
                        
                        if nova_categoria != row['Categoria']:
                            # Aplicar mudança imediatamente no modo individual
                            if st.button(f"✅ Alterar", key=f"change_{idx}_{inicio_idx}", type="primary"):
                                # Persistir no banco de dados
                                success_bd = atualizar_categoria_no_banco(usuario, row['Descrição'], nova_categoria)
                                
                                # Também salvar no cache para compatibilidade
                                cache = carregar_cache_categorias()
                                descricao_normalizada = row['Descrição'].lower().strip()
                                cache[descricao_normalizada] = nova_categoria
                                cache_salvo = salvar_cache_categorias(cache)
                                
                                if success_bd or cache_salvo:
                                    msg = f"✅ Categoria alterada para: {nova_categoria}"
                                    if success_bd:
                                        msg += " (persistido no banco)"
                                    st.success(msg)
                                    st.cache_data.clear()
                                    st.rerun()
                                else:
                                    st.error("❌ Erro ao salvar categoria no banco de dados!")
                        
                        # Adicionar/editar descrição personalizada
                        st.markdown("---")
                        nova_descricao = st.text_area(
                            "📋 Nota Pessoal",
                            value=descricoes.get(hash_transacao, ""),
                            placeholder="Adicione uma nota pessoal...",
                            key=f"desc_{idx}_{inicio_idx}",
                            help="Esta nota será salva apenas para esta transação específica"                        )                        
                        col_save, col_delete = st.columns(2)
                        with col_save:
                            if st.button(f"💾 Salvar Nota", key=f"save_desc_{idx}_{inicio_idx}"):
                                if salvar_descricao_personalizada(hash_transacao, nova_descricao):
                                    st.success("✅ Nota salva!")
                                    st.rerun()
                        
                        with col_delete:
                            if st.button(f"🗑️ Excluir Transação", key=f"delete_{idx}_{inicio_idx}", help="Excluir esta transação"):
                                if excluir_transacao(row):
                                    st.success("🗑️ Transação excluída!")
                                    st.cache_data.clear()
                                    st.rerun()