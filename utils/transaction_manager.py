"""
Gerenciador de Transações para o Pluggy - Responsável por buscar e processar transações
"""
import requests
import pandas as pd
import os
from datetime import date, timedelta
import streamlit as st
from utils.config import DEFAULT_PERIOD_DAYS

class TransactionManager:
    """Gerencia operações relacionadas a transações bancárias no Pluggy"""
    
    def __init__(self, api_url, get_headers_func, cache_manager, account_manager, categorization_service):
        self.api_url = api_url
        self.get_headers = get_headers_func
        self.cache_manager = cache_manager
        self.account_manager = account_manager
        self.categorization_service = categorization_service
    
    def buscar_extratos(self, itemids_data, dias=DEFAULT_PERIOD_DAYS):
        """Busca extratos bancários para os item IDs fornecidos"""
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
        cache_key = self.cache_manager.get_hash(f"extratos_{from_date}_{to_date}_" + "_".join(sorted([item['item_id'] for item in itemids_data])))

        # Verificar cache (ignorar se force_refresh for True)
        cached_data = None if force_refresh else self.cache_manager.get_from_cache(cache_key)
        if cached_data is not None:
            print(f"Usando dados em cache para {len(itemids_data)} item IDs")
            return cached_data

        # Se chegamos aqui, precisamos buscar dados frescos da API
        print(f"Buscando dados frescos da API para {len(itemids_data)} item IDs")
        
        # Verificar modo de processamento
        skip_llm = os.environ.get("SKIP_LLM_PROCESSING", "false").lower() == "true"
        if skip_llm:
            print("⚡ MODO RÁPIDO: Processamento LLM desabilitado para performance otimizada")
        
        todas_transacoes = []

        for item in itemids_data:
            try:
                # Log para debug
                print(f"Buscando transações para o item ID: {item['item_id']}")
                
                # Primeiro buscar contas do item
                accounts = self.account_manager.buscar_contas_por_item(item['item_id'])
                
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
                    
                    # Buscar transações usando accountId
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
                            'id': transaction.get('id', ''),
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
                continue
                
        # Criar DataFrame com as transações
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
                df = self.categorization_service.categorizar_transacoes_com_llm(df)

                # Enriquecer descrições confusas ou curtas
                df = self.categorization_service.enriquecer_descricoes(df)
                print("🤖 Processamento IA aplicado - categorização inteligente")
            else:
                # Aplicar categorização básica sem LLM
                df = self.categorization_service.aplicar_categorizacao_basica(df)
                print("⚡ Carregamento rápido - processamento LLM desabilitado")

            # Converter Data para datetime
            if 'Data' in df.columns:
                df['Data'] = pd.to_datetime(df['Data'])

            # Salvar no cache
            self.cache_manager.save_to_cache(cache_key, df)

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
        cache_key = self.cache_manager.get_hash("cartoes_" + "_".join(sorted([item['item_id'] for item in itemids_data])) + f"_{dias}")
        
        # Verificar cache
        cached_data = self.cache_manager.get_from_cache(cache_key)
        if cached_data is not None:
            print(f"Usando dados de cartões em cache para {len(itemids_data)} item IDs")
            return cached_data

        print(f"Buscando dados de cartões da API para {len(itemids_data)} item IDs")
        
        todas_transacoes = []

        # Calcular período
        data_fim = date.today()
        data_inicio = data_fim - timedelta(days=dias)
        from_date = data_inicio.strftime('%Y-%m-%d')
        to_date = data_fim.strftime('%Y-%m-%d')

        # Buscar cartões
        credit_accounts = self.account_manager.buscar_contas_credito(itemids_data)
        
        # Buscar transações para cada cartão
        for card in credit_accounts:
            account_id = card['account_id']
            account_name = card['account_name']
            item_name = card['item_name']
            
            try:
                print(f"Buscando transações do cartão: {account_name}")
                
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
                        'id': transaction.get('id', ''),
                        'Data': transaction.get('date', ''),
                        'Valor': transaction.get('amount', 0),
                        'Descrição': transaction.get('description', ''),
                        'Tipo': transaction.get('type', ''),
                        'Conta': f"{item_name} - {account_name}",
                        'TipoConta': 'CREDIT'  # Identificador específico para cartões
                    }
                    todas_transacoes.append(transacao)

            except Exception as e:
                print(f"Erro ao processar cartão {account_name}: {str(e)}")
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
                df = self.categorization_service.categorizar_transacoes_com_llm(df)
                
                # Enriquecer descrições confusas ou curtas
                df = self.categorization_service.enriquecer_descricoes(df)
            else:
                # Aplicar categorização básica sem LLM
                df = self.categorization_service.aplicar_categorizacao_basica(df)

        # Salvar no cache
        self.cache_manager.save_to_cache(cache_key, df)
        
        return df
