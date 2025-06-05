import requests
import pandas as pd
from datetime import date, timedelta, datetime
import os
import json
import hashlib
import pickle
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from typing import Optional
from langchain_core.output_parsers.string import StrOutputParser
import streamlit as st

from database import get_connection
from utils.config import (
    PLUGGY_CLIENT_ID,
    PLUGGY_CLIENT_SECRET,
    PLUGGY_API_URL,
    DEFAULT_PERIOD_DAYS,
    ENABLE_CACHE,
    CACHE_TTL,
    DEFAULT_CATEGORIES
)

class PluggyConnector:
    _instance = None
    _cache = {}
    _categorias_cache = {}  # Cache específico para categorias
    _descricoes_cache = {}  # Cache específico para descrições enriquecidas
    _CACHE_DIR = Path("cache")  # Diretório para cache persistente
    
    # Instance attributes
    def __init__(self):
        """Inicialização já tratada no __new__, não é necessário repetir aqui"""
        self.client_id: str = ""
        self.client_secret: str = ""
        self.api_url: str = ""
        self.access_token: Optional[str] = None

    def __new__(cls):
        """Implementação do padrão Singleton para garantir uma única instância"""
        if cls._instance is None:
            cls._instance = super(PluggyConnector, cls).__new__(cls)
            cls._instance.client_id = PLUGGY_CLIENT_ID
            cls._instance.client_secret = PLUGGY_CLIENT_SECRET
            cls._instance.api_url = PLUGGY_API_URL
            cls._instance.access_token = None
            # Criar diretório de cache se não existir
            if not cls._CACHE_DIR.exists():
                cls._CACHE_DIR.mkdir(parents=True)
            # Carregar cache persistente
            cls._instance._load_persistent_cache()
            cls._instance._authenticate()
            # Inicializar modelo LLM
            cls._instance._init_llm()
        return cls._instance

    def _authenticate(self):
        """Autenticar com a API Pluggy e obter token de acesso"""
        try:
            # Usar o formato correto para autenticação na API do Pluggy
            auth_data = {
                "clientId": self.client_id,
                "clientSecret": self.client_secret
            }
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            auth_resp = requests.post(
                f"{self.api_url}/auth",
                json=auth_data,
                headers=headers
            )
            
            if auth_resp.status_code != 200:
                raise Exception(f"Falha na autenticação com a API Pluggy: {auth_resp.text}")
                
            if "apiKey" not in auth_resp.json():
                raise Exception("Formato de resposta inválido da API Pluggy")
                
            self.access_token = auth_resp.json()["apiKey"]
            
        except Exception as e:
            raise

    def _init_llm(self):
        """Inicializar modelo LLM para uso em várias funcionalidades"""
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.chat_model = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0,
                max_tokens=150,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
            )
        else:
            self.chat_model = None

    def _load_persistent_cache(self):
        """Carregar cache persistente do disco"""
        cache_file = self._CACHE_DIR / "cache.pkl"
        if cache_file.exists():
            with cache_file.open("rb") as f:
                self._cache = pickle.load(f)

        categorias_cache_file = self._CACHE_DIR / "categorias_cache.pkl"
        if categorias_cache_file.exists():
            with categorias_cache_file.open("rb") as f:
                self._categorias_cache = pickle.load(f)

        descricoes_cache_file = self._CACHE_DIR / "descricoes_cache.pkl"
        if descricoes_cache_file.exists():
            with descricoes_cache_file.open("rb") as f:
                self._descricoes_cache = pickle.load(f)

    def _save_persistent_cache(self):
        """Salvar cache persistente no disco"""
        cache_file = self._CACHE_DIR / "cache.pkl"
        with cache_file.open("wb") as f:
            pickle.dump(self._cache, f)

        categorias_cache_file = self._CACHE_DIR / "categorias_cache.pkl"
        with categorias_cache_file.open("wb") as f:
            pickle.dump(self._categorias_cache, f)

        descricoes_cache_file = self._CACHE_DIR / "descricoes_cache.pkl"
        with descricoes_cache_file.open("wb") as f:
            pickle.dump(self._descricoes_cache, f)

    def get_headers(self):
        """Retornar cabeçalhos de autenticação para requests"""
        if not self.access_token:
            self._authenticate()

        # Testar primeiro com formato X-API-KEY (formato atual)
        headers = {
            "X-API-KEY": self.access_token,
            "Content-Type": "application/json"
        }
        return headers

    def get_bearer_headers(self):
        """Retornar cabeçalhos de autenticação no formato Bearer"""
        if not self.access_token:
            self._authenticate()

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        return headers

    @staticmethod
    def load_itemids_db(usuario):
        """Carregar os itemIds associados ao usuário a partir do banco de dados"""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT id FROM usuarios WHERE usuario = ?', (usuario,))
        row = cur.fetchone()
        if not row:
            return []
        usuario_id = row[0]
        cur.execute('SELECT item_id, nome FROM pluggy_items WHERE usuario_id = ?', (usuario_id,))
        items = [{'item_id': r['item_id'], 'nome': r['nome']} for r in cur.fetchall()]
        return items

    def _get_from_cache(self, cache_key):
        """Recuperar dados do cache se estiverem válidos"""
        if not ENABLE_CACHE:
            return None

        if cache_key in self._cache:
            entry = self._cache[cache_key]
            # Verificar se o cache ainda é válido
            if (datetime.now() - entry['timestamp']).total_seconds() < CACHE_TTL:
                return entry['data']

        return None

    def _save_to_cache(self, cache_key, data):
        """Salvar dados no cache"""
        if not ENABLE_CACHE:
            return

        self._cache[cache_key] = {
            'data': data,
            'timestamp': datetime.now()
        }
        self._save_persistent_cache()

    @staticmethod
    def _get_hash(text):
        """Gera um hash para um texto para usar como chave de cache"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def categorizar_transacoes_com_llm(self, df, coluna_descricao="Descrição", coluna_valor="Valor", coluna_tipo="Tipo"):
        """
        Categoriza transações usando LLM para maior precisão, com cache otimizado.
        """
        if df.empty:
            return df

        # Criar uma cópia para não modificar o original
        df_temp = df.copy()

        # Verificar se já existe coluna de categoria
        if "Categoria" not in df_temp.columns:
            df_temp["Categoria"] = None

        # Processar apenas as transações sem categoria definida (otimização)
        rows_to_process = df_temp[df_temp["Categoria"].isna()].copy()
        if rows_to_process.empty:
            return df_temp

        # Processar transações em lotes para reduzir chamadas à API
        batch_size = 20
        total_rows = len(rows_to_process)

        for i in range(0, total_rows, batch_size):
            batch = rows_to_process.iloc[i:min(i+batch_size, total_rows)]

            # Processar cada item do lote
            for idx, row in batch.iterrows():
                descricao = str(row[coluna_descricao]) if not pd.isna(row[coluna_descricao]) else ""
                valor = row[coluna_valor] if not pd.isna(row[coluna_valor]) else 0
                tipo = row[coluna_tipo] if not pd.isna(row[coluna_tipo]) else ""

                # Gerar chave de cache única
                cache_key = self._get_hash(f"{descricao}_{valor}_{tipo}")

                # Verificar cache antes de chamar a API
                if cache_key in self._categorias_cache:
                    df_temp.loc[idx, "Categoria"] = self._categorias_cache[cache_key]
                    continue

                # Se não está no cache, categorizar com IA
                if self.chat_model is not None:
                    prompt = ChatPromptTemplate.from_template("""
                        Categorize a transação abaixo em uma destas categorias exatas:
                        Salário, Transferência, Alimentação, Transporte, Moradia, Saúde,
                        Educação, Lazer, Vestuário, Outros.

                        Responda APENAS com o nome da categoria, sem explicações.

                        Descrição: {descricao}
                        Valor: {valor}
                        Tipo: {tipo}
                    """)

                    chain = prompt | self.chat_model | StrOutputParser()
                    try:
                        categoria = chain.invoke({"descricao": descricao, "valor": valor, "tipo": tipo}).strip()
                        # Validar categoria
                        if categoria not in DEFAULT_CATEGORIES:
                            categoria = "Outros"

                        # Armazenar no cache
                        self._categorias_cache[cache_key] = categoria
                        df_temp.loc[idx, "Categoria"] = categoria
                    except Exception:
                        df_temp.loc[idx, "Categoria"] = "Outros"
                else:
                    # Se não há modelo LLM disponível, usar categoria padrão
                    df_temp.loc[idx, "Categoria"] = "Outros"

            # Salvar cache a cada lote processado para não perder progresso
            self._save_persistent_cache()

        return df_temp

    def enriquecer_descricoes(self, df, coluna_descricao="Descrição"):
        """
        Melhora as descrições curtas ou confusas usando IA, com sistema de cache otimizado.
        """
        if df.empty or coluna_descricao not in df.columns:
            return df

        # Criar uma cópia para não modificar o original
        df_temp = df.copy()

        # Adicionar coluna de descrição enriquecida se não existir
        if "DescriçãoCompleta" not in df_temp.columns:
            df_temp["DescriçãoCompleta"] = df_temp[coluna_descricao]

        # Identificar descrições que precisam ser enriquecidas (curtas ou confusas)
        mask_curtas = df_temp[coluna_descricao].str.len() < 10
        mask_confusas = df_temp[coluna_descricao].str.contains('|'.join(['trf', 'ted', 'doc', 'transf', 'pix']), case=False, na=False)
        mask_numeros = df_temp[coluna_descricao].str.match(r'^\d+$', na=False)

        rows_to_process = df_temp[mask_curtas | mask_confusas | mask_numeros].copy()

        # Processar em lotes menores para otimizar
        batch_size = 10
        total_rows = len(rows_to_process)

        for i in range(0, total_rows, batch_size):
            batch = rows_to_process.iloc[i:min(i+batch_size, total_rows)]

            for idx, row in batch.iterrows():
                desc_original = str(row[coluna_descricao]) if not pd.isna(row[coluna_descricao]) else ""

                # Pular descrições vazias
                if not desc_original.strip():
                    continue

                # Verificar cache
                cache_key = self._get_hash(desc_original)
                if cache_key in self._descricoes_cache:
                    df_temp.loc[idx, "DescriçãoCompleta"] = self._descricoes_cache[cache_key]
                    continue

                # Só processar descrições realmente problemáticas para economizar chamadas
                if len(desc_original) >= 10 and not any(term in desc_original.lower() for term in ['trf', 'ted', 'doc', 'transf', 'pix']):
                    continue

                # Enriquecer com IA
                if self.chat_model is not None:
                    prompt = ChatPromptTemplate.from_template("""
                        Melhore a seguinte descrição de transação financeira para uma versão mais clara e descritiva,
                        em até 10 palavras. Infira o provável significado baseado em padrões comuns.
                        Apenas retorne a descrição melhorada, sem explicações ou comentários adicionais.

                        Descrição original: {descricao}
                    """)

                    chain = prompt | self.chat_model | StrOutputParser()
                    try:
                        descricao_melhorada = chain.invoke({"descricao": desc_original}).strip()
                        # Verificar se a descrição realmente melhorou
                        if len(descricao_melhorada) > len(desc_original):
                            # Armazenar no cache
                            self._descricoes_cache[cache_key] = descricao_melhorada
                            df_temp.loc[idx, "DescriçãoCompleta"] = descricao_melhorada
                    except Exception:
                        # Em caso de erro, manter a descrição original
                        pass
            
            # Salvar cache a cada lote
            self._save_persistent_cache()
            
        return df_temp
    
    def obter_saldo_atual(self, itemids_data):
        """
        Obtém o saldo atual das contas do usuário.
        """
        if not itemids_data:
            return None

        # Gerar chave de cache baseada nos itemIds
        cache_key = self._get_hash("saldos_" + "_".join(sorted([item['item_id'] for item in itemids_data])))
        
        # Verificar cache
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data

        saldo_positivo = 0
        saldo_negativo = 0
        contas_detalhes = []
          # Processar dados das contas
        for item in itemids_data:
            try:
                # Buscar contas associadas ao item usando endpoint correto
                accounts_response = requests.get(
                    f"{self.api_url}/accounts",
                    headers=self.get_headers(),
                    params={'itemId': item['item_id']}
                )

                if accounts_response.status_code != 200:
                    print(f"Erro ao buscar contas para item {item['nome']}: {accounts_response.status_code}")
                    continue

                accounts_data = accounts_response.json()
                for account in accounts_data.get('results', []):
                    # Usar o campo 'balance' diretamente (não 'available')
                    saldo = account.get('balance', 0) or 0
                    account_type = account.get('type', 'UNKNOWN')
                    
                    # Para cartões de crédito, o saldo representa valor usado (negativo para dívidas)
                    if account_type == 'CREDIT':
                        # Converter saldo usado em dívida (valor negativo)
                        saldo = -abs(saldo) if saldo > 0 else saldo
                    
                    # Adicionar aos totais
                    if saldo > 0:
                        saldo_positivo += saldo
                    else:
                        saldo_negativo += saldo
                    
                    # Adicionar detalhes da conta
                    contas_detalhes.append({
                        'Nome da Conta': account.get('name', 'Conta sem nome'),
                        'Tipo': account_type,
                        'Saldo': saldo,
                        'Item': item.get('nome', 'Item desconhecido')
                    })
                    
            except Exception as e:
                print(f"Erro ao processar item {item.get('nome', 'desconhecido')}: {str(e)}")
                continue

        # Calcular saldo total
        saldo_total = saldo_positivo + saldo_negativo

        # Estruturar resultado
        result = (saldo_positivo, saldo_negativo, contas_detalhes, saldo_total)

        # Salvar no cache
        self._save_to_cache(cache_key, result)

        return result
    
    def buscar_extratos(self, itemids_data, dias=DEFAULT_PERIOD_DAYS):
        if not itemids_data:
            st.warning("Nenhum item ID encontrado. Verifique se você cadastrou os item IDs corretamente na página Cadastro_Pluggy.")
            return pd.DataFrame()

        # Debug: mostrar os item IDs para verificação
        print(f"Buscando extratos para os seguintes item IDs: {itemids_data}")

        # Parâmetros para busca
        from_date = (date.today() - timedelta(days=dias)).isoformat()
        to_date = date.today().isoformat()

        # Verificar se o usuário explicitamente solicitou ignorar o cache
        force_refresh = os.environ.get("FORCE_REFRESH", "False").lower() == "true"

        # Gerar chave de cache
        cache_key = self._get_hash(f"extratos_{from_date}_{to_date}_" + "_".join(sorted([item['item_id'] for item in itemids_data])))

        # Verificar cache (ignorar se force_refresh for True)
        cached_data = None if force_refresh else self._get_from_cache(cache_key)
        if cached_data is not None:
            print(f"Usando dados em cache para {len(itemids_data)} item IDs")
            return cached_data

        # Se chegamos aqui, precisamos buscar dados frescos da API
        print(f"Buscando dados frescos da API para {len(itemids_data)} item IDs")
        
        todas_transacoes = []
        
        # Autenticar novamente para garantir token válido
        self._authenticate()

        for item in itemids_data:
            try:
                # Log para debug
                print(f"Buscando transações para o item ID: {item['item_id']}")
                
                # CORREÇÃO: Primeiro buscar contas do item
                print(f"Buscando contas para o item...")
                accounts_response = requests.get(
                    f"{self.api_url}/accounts",
                    headers=self.get_headers(),
                    params={'itemId': item['item_id']}
                )
                
                print(f"Status das contas: {accounts_response.status_code}")
                
                if accounts_response.status_code != 200:
                    print(f"Erro ao buscar contas: {accounts_response.text}")
                    continue
                
                accounts_data = accounts_response.json()
                accounts = accounts_data.get('results', [])
                print(f"Encontradas {len(accounts)} contas para o item {item['item_id']}")
                
                if not accounts:
                    print(f"Nenhuma conta encontrada para o item {item['item_id']}")
                    continue
                
                # Para cada conta, buscar as transações
                for account in accounts:
                    account_id = account.get('id')
                    account_name = account.get('name', 'Conta sem nome')
                    
                    if not account_id:
                        continue
                        
                    print(f"Buscando transações da conta: {account_name} (ID: {account_id})")
                    
                    # Buscar transações usando accountId (formato que funciona)
                    transactions_response = requests.get(
                        f"{self.api_url}/transactions",
                        headers=self.get_headers(),
                        params={
                            'accountId': account_id,
                            'from': from_date,
                            'to': to_date,
                            'pageSize': 500
                        }
                    )

                    # Log do resultado da requisição para debug
                    print(f"Status das transações da conta {account_name}: {transactions_response.status_code}")
                    
                    if transactions_response.status_code != 200:
                        print(f"Erro ao buscar transações da conta {account_name}: {transactions_response.text}")
                        continue
                    
                    transactions_data = transactions_response.json()
                    transactions_list = transactions_data.get('results', [])
                    print(f"Encontradas {len(transactions_list)} transações para a conta {account_name}")
                    
                    # Processar cada transação
                    for transaction in transactions_list:
                        transacao = {
                            'Data': transaction.get('date', ''),
                            'Valor': transaction.get('amount', 0),
                            'Descrição': transaction.get('description', ''),
                            'Tipo': transaction.get('type', ''),
                            'Conta': f"{item.get('nome', 'Conta desconhecida')} - {account_name}"
                        }
                        todas_transacoes.append(transacao)

            except Exception as e:
                # Log de erro detalhado
                print(f"Erro ao processar item ID {item['item_id']}: {str(e)}")
                continue        # Criar DataFrame com as transações
        if not todas_transacoes:
            print("Nenhuma transação encontrada para nenhum dos item IDs fornecidos")
            return pd.DataFrame()
            
        print(f"Total de {len(todas_transacoes)} transações encontradas")
        df = pd.DataFrame(todas_transacoes)

        # Aplicar categorização com LLM somente se tiver dados
        if not df.empty:
            # Verificar se deve aplicar LLM (pode ser desabilitado para carregamento rápido)
            skip_llm = os.environ.get("SKIP_LLM_PROCESSING", "False").lower() == "true"
            
            if not skip_llm:
                # Aplicar categorização com LLM
                df = self.categorizar_transacoes_com_llm(df)

                # Enriquecer descrições confusas ou curtas
                df = self.enriquecer_descricoes(df)
            else:
                # Aplicar categorização básica sem LLM
                df = self._aplicar_categorizacao_basica(df)
                print("⚡ Carregamento rápido - processamento LLM desabilitado")

            # Converter Data para datetime
            if 'Data' in df.columns:
                df['Data'] = pd.to_datetime(df['Data'])            # Salvar no cache
            self._save_to_cache(cache_key, df)

        return df
        
    def buscar_cartoes(self, itemids_data, dias=DEFAULT_PERIOD_DAYS):
        """
        Buscar transações de cartões de crédito especificamente.
        Filtra apenas contas do tipo CREDIT e suas transações.

        Para uso na página de Cartão de Crédito.
        """
        if not itemids_data:
            return pd.DataFrame()

        # Gerar chave de cache específica para cartões
        cache_key = self._get_hash("cartoes_" + "_".join(sorted([item['item_id'] for item in itemids_data])) + f"_{dias}")
        
        # Verificar cache
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            print(f"Usando dados de cartões em cache para {len(itemids_data)} item IDs")
            return cached_data

        print(f"Buscando dados de cartões da API para {len(itemids_data)} item IDs")
        
        todas_transacoes = []
        
        # Autenticar novamente para garantir token válido
        self._authenticate()

        # Calcular período
        data_fim = date.today()
        data_inicio = data_fim - timedelta(days=dias)
        from_date = data_inicio.strftime('%Y-%m-%d')
        to_date = data_fim.strftime('%Y-%m-%d')

        for item in itemids_data:
            try:
                print(f"Buscando cartões para o item ID: {item['item_id']}")
                
                # Buscar contas do item
                accounts_response = requests.get(
                    f"{self.api_url}/accounts",
                    headers=self.get_headers(),
                    params={'itemId': item['item_id']}
                )
                
                if accounts_response.status_code != 200:
                    print(f"Erro ao buscar contas: {accounts_response.text}")
                    continue
                
                accounts_data = accounts_response.json()
                accounts = accounts_data.get('results', [])
                
                # Filtrar apenas contas de crédito
                credit_accounts = [acc for acc in accounts if acc.get('type') == 'CREDIT']
                print(f"Encontradas {len(credit_accounts)} contas de crédito para o item {item['item_id']}")
                
                if not credit_accounts:
                    print(f"Nenhuma conta de crédito encontrada para o item {item['item_id']}")
                    continue
                
                # Para cada conta de crédito, buscar as transações
                for account in credit_accounts:
                    account_id = account.get('id')
                    account_name = account.get('name', 'Cartão sem nome')
                    
                    if not account_id:
                        continue
                    
                    print(f"Buscando transações do cartão: {account_name} (ID: {account_id})")
                    
                    # Buscar transações da conta de crédito
                    transactions_response = requests.get(
                        f"{self.api_url}/transactions",
                        headers=self.get_headers(),
                        params={
                            'accountId': account_id,
                            'from': from_date,
                            'to': to_date,
                            'pageSize': 500
                        }
                    )

                    if transactions_response.status_code != 200:
                        print(f"Erro ao buscar transações do cartão {account_name}: {transactions_response.text}")
                        continue
                    
                    transactions_data = transactions_response.json()
                    transactions_list = transactions_data.get('results', [])
                    print(f"Encontradas {len(transactions_list)} transações para o cartão {account_name}")
                    
                    # Processar cada transação do cartão
                    for transaction in transactions_list:
                        transacao = {
                            'Data': transaction.get('date', ''),
                            'Valor': transaction.get('amount', 0),
                            'Descrição': transaction.get('description', ''),
                            'Tipo': transaction.get('type', ''),
                            'Conta': f"{item.get('nome', 'Banco desconhecido')} - {account_name}",
                            'TipoConta': 'CREDIT'  # Identificador específico para cartões
                        }
                        todas_transacoes.append(transacao)

            except Exception as e:
                print(f"Erro ao processar item ID {item['item_id']}: {str(e)}")
                continue

        # Criar DataFrame com as transações de cartão
        if not todas_transacoes:
            print("Nenhuma transação de cartão encontrada")
            return pd.DataFrame()

        print(f"Total de {len(todas_transacoes)} transações de cartão encontradas")
        df = pd.DataFrame(todas_transacoes)

        # Aplicar categorização com LLM somente se tiver dados
        if not df.empty:
            # Verificar se deve aplicar LLM
            skip_llm = os.environ.get("SKIP_LLM_PROCESSING", "False").lower() == "true"
            
            if not skip_llm:
                # Aplicar categorização com LLM
                df = self.categorizar_transacoes_com_llm(df)
                
                # Enriquecer descrições confusas ou curtas
                df = self.enriquecer_descricoes(df)
            else:
                # Aplicar categorização básica sem LLM
                df = self._aplicar_categorizacao_basica(df)

        # Salvar no cache
        self._save_to_cache(cache_key, df)
        
        return df

    def limpar_cache(self):
        """Limpa todos os caches para forçar a obtenção de dados atualizados"""
        self._cache = {}
        self._categorias_cache = {}
        self._descricoes_cache = {}
        self._save_persistent_cache()

    def testar_autenticacao(self):
        """
        Testa se a autenticação está funcionando corretamente
        tentando acessar um endpoint básico da API
        """
        try:
            print(f"=== TESTE DE AUTENTICAÇÃO ===")
            print(f"Client ID: {self.client_id}")
            print(f"API URL: {self.api_url}")
            print(f"Access Token: {self.access_token[:20] if self.access_token else 'None'}...")
            
            # Primeiro, testar se conseguimos acessar o endpoint de conectores
            headers = self.get_headers()
            print(f"Headers sendo enviados: {headers}")
            
            response = requests.get(
                f"{self.api_url}/connectors",
                headers=headers
            )
            
            print(f"Teste /connectors - Status: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ Autenticação funcionando - conseguimos acessar /connectors")
                connectors = response.json()
                print(f"Encontrados {len(connectors.get('results', []))} conectores")
                return True
            else:
                print(f"❌ Erro na autenticação - Resposta: {response.text}")
                
                # Testar com header Authorization Bearer em vez de X-API-KEY
                print("Tentando com formato Authorization Bearer...")
                bearer_headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }
                bearer_response = requests.get(
                    f"{self.api_url}/connectors",
                    headers=bearer_headers
                )
                print(f"Teste Bearer - Status: {bearer_response.status_code}")
                if bearer_response.status_code == 200:
                    print("✅ Formato Bearer funcionou!")
                    return True
                else:
                    print(f"❌ Bearer também falhou: {bearer_response.text}")
                
                return False
                
        except Exception as e:
            print(f"❌ Erro no teste de autenticação: {str(e)}")
            return False

    def testar_item_id(self, item_id):
        """
        Testa se um item ID específico está funcionando
        """
        try:
            print(f"Testando item ID: {item_id}")
            
            # Primeiro tentar acessar informações básicas do item
            response = requests.get(
                f"{self.api_url}/items/{item_id}",
                headers=self.get_headers()
            )
            
            print(f"Status do teste: {response.status_code}")
            
            if response.status_code == 200:
                item_data = response.json()
                print(f"✅ Item ID válido: {item_data.get('connector', {}).get('name', 'Nome não disponível')}")
                return True
            elif response.status_code == 403:
                print(f"❌ Item ID não pertence a este cliente Pluggy")
                return False
            elif response.status_code == 404:
                print(f"❌ Item ID não encontrado")
                return False
            else:
                print(f"❌ Erro inesperado: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Erro ao testar item ID: {str(e)}")
            return False
    
    def _aplicar_categorizacao_basica(self, df):
        """
        Aplica categorização básica sem LLM para carregamento rápido.
        Usa regras simples baseadas em palavras-chave.
        """
        if df.empty:
            return df
            
        df_temp = df.copy()
        
        # Adicionar coluna de categoria se não existir
        if "Categoria" not in df_temp.columns:
            df_temp["Categoria"] = "Outros"
        
        # Aplicar categorização básica por palavras-chave
        for idx, row in df_temp.iterrows():
            descricao = str(row.get("Descrição", "")).lower()
            valor = row.get("Valor", 0)
            
            # Categorização básica por palavras-chave
            if any(word in descricao for word in ['salário', 'salario', 'vencimento', 'pagamento salario']):
                df_temp.loc[idx, "Categoria"] = "Salário"
            elif any(word in descricao for word in ['supermercado', 'mercado', 'alimentação', 'restaurante', 'ifood']):
                df_temp.loc[idx, "Categoria"] = "Alimentação"
            elif any(word in descricao for word in ['transferência', 'transferencia', 'pix', 'ted', 'doc']):
                df_temp.loc[idx, "Categoria"] = "Transferência"
            elif any(word in descricao for word in ['transporte', 'uber', 'taxi', '99', 'combustível', 'gasolina']):
                df_temp.loc[idx, "Categoria"] = "Transporte"
            elif any(word in descricao for word in ['moradia', 'aluguel', 'condomínio', 'agua', 'luz', 'gas']):
                df_temp.loc[idx, "Categoria"] = "Moradia"
            elif any(word in descricao for word in ['saúde', 'hospital', 'médico', 'farmácia', 'remédio']):
                df_temp.loc[idx, "Categoria"] = "Saúde"
            elif any(word in descricao for word in ['educação', 'escola', 'curso', 'livro']):
                df_temp.loc[idx, "Categoria"] = "Educação"
            elif any(word in descricao for word in ['lazer', 'cinema', 'teatro', 'netflix', 'spotify']):
                df_temp.loc[idx, "Categoria"] = "Lazer"
            elif any(word in descricao for word in ['vestuário', 'roupa', 'calçado', 'shopping']):
                df_temp.loc[idx, "Categoria"] = "Vestuário"
            # Categoria permanece como "Outros" se não encontrar correspondência
                
        return df_temp
