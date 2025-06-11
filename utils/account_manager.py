"""
Gerenciador de Contas para o Pluggy - Responsável por operações relacionadas a contas
"""
import requests
from datetime import date, timedelta
import pandas as pd
import os
from typing import Dict, List, Any, Tuple, Optional

class AccountManager:
    """Gerencia operações relacionadas a contas bancárias no Pluggy"""
    
    def __init__(self, api_url, get_headers_func, cache_manager):
        self.api_url = api_url
        self.get_headers = get_headers_func
        self.cache_manager = cache_manager
    
    def obter_saldo_atual(self, itemids_data):
        """
        Obtém o saldo atual das contas do usuário.
        """
        if not itemids_data:
            return None

        # Verificar se o usuário explicitamente solicitou ignorar o cache
        force_refresh = os.environ.get("FORCE_REFRESH", "False").lower() == "true"

        # Gerar chave de cache baseada nos itemIds
        cache_key = self.cache_manager.get_hash("saldos_" + "_".join(sorted([item['item_id'] for item in itemids_data])))
        
        # Verificar cache (ignorar se force_refresh for True)
        cached_data = None if force_refresh else self.cache_manager.get_from_cache(cache_key)
        if cached_data is not None:
            print(f"Usando dados de saldo em cache para {len(itemids_data)} item IDs")
            return cached_data

        # Se chegamos aqui, precisamos buscar dados frescos da API
        print(f"Buscando dados de saldo frescos da API para {len(itemids_data)} item IDs")

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
        self.cache_manager.save_to_cache(cache_key, result)

        return result
        
    def buscar_contas_por_item(self, item_id):
        """
        Busca todas as contas associadas a um item específico
        """
        try:
            accounts_response = requests.get(
                f"{self.api_url}/accounts",
                headers=self.get_headers(),
                params={'itemId': item_id}
            )
            
            if accounts_response.status_code != 200:
                print(f"Erro ao buscar contas para item {item_id}: {accounts_response.status_code}")
                return []
                
            accounts_data = accounts_response.json()
            return accounts_data.get('results', [])
            
        except Exception as e:
            print(f"Erro ao buscar contas para item {item_id}: {str(e)}")
            return []
            
    def buscar_contas_credito(self, itemids_data):
        """
        Busca todas as contas de crédito para os itens fornecidos
        """
        credit_accounts = []
        
        for item in itemids_data:
            try:
                accounts = self.buscar_contas_por_item(item['item_id'])
                # Filtrar apenas contas de crédito
                item_credit_accounts = [
                    {
                        'account_id': acc.get('id'),
                        'account_name': acc.get('name', 'Cartão sem nome'),
                        'item_id': item['item_id'],
                        'item_name': item.get('nome', 'Banco desconhecido')
                    }
                    for acc in accounts if acc.get('type') == 'CREDIT'
                ]
                credit_accounts.extend(item_credit_accounts)
                
            except Exception as e:
                print(f"Erro ao buscar cartões para item {item.get('nome', item['item_id'])}: {str(e)}")
                
        return credit_accounts
