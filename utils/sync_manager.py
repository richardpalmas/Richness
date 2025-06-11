"""
Gerenciador de Sincronização para o Pluggy - Responsável pela sincronização forçada
"""
import requests
import time
from typing import Dict, List, Any

class SyncManager:
    """Gerencia a sincronização forçada de itens com a API Pluggy"""
    
    def __init__(self, api_url, get_headers_func):
        self.api_url = api_url
        self.get_headers = get_headers_func  # Função para obter headers autenticados
    
    def forcar_sync_item(self, item_id):
        """
        Força sincronização de um item específico usando PATCH /items/{id}
        Isso faz o Pluggy buscar dados frescos dos bancos antes de retornar
        """
        try:
            print(f"🔄 Forçando sincronização do item ID: {item_id}")
            
            # Fazer PATCH para o endpoint de update do item
            # Isso força o Pluggy a sincronizar dados frescos com a instituição bancária
            response = requests.patch(
                f"{self.api_url}/items/{item_id}",
                headers=self.get_headers(),
                json={}  # Corpo vazio - apenas trigger o sync sem atualizar credenciais
            )
            
            print(f"Status da sincronização forçada: {response.status_code}")
            
            if response.status_code == 200:
                sync_data = response.json()
                print(f"✅ Sincronização iniciada com sucesso para item {item_id}")
                print(f"Status do item: {sync_data.get('status', 'N/A')}")
                return True
            elif response.status_code == 400:
                print(f"⚠️ Item {item_id} pode já estar sincronizando ou ter erro de credenciais")
                return False
            elif response.status_code == 403:
                print(f"❌ Item ID não pertence a este cliente Pluggy")
                return False
            elif response.status_code == 404:
                print(f"❌ Item ID não encontrado")
                return False
            else:
                print(f"❌ Erro inesperado na sincronização: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Erro ao forçar sincronização do item ID: {str(e)}")
            return False
            
    def sincronizar_itens(self, itemids_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Sincroniza múltiplos itens com a API Pluggy
        Retorna estatísticas da sincronização
        """
        print("🔄 Iniciando sincronização forçada com instituições bancárias...")
        itens_sincronizados = 0
        itens_com_erro = 0
        
        for item in itemids_data:
            try:
                print(f"🏦 Sincronizando item: {item.get('nome', item['item_id'])}")
                if self.forcar_sync_item(item['item_id']):
                    itens_sincronizados += 1
                    print(f"✅ Item {item['item_id']} sincronizado com sucesso")
                else:
                    itens_com_erro += 1
                    print(f"⚠️ Erro na sincronização do item {item['item_id']}")
                
                # Delay mínimo para evitar sobrecarga da API
                time.sleep(0.5)
            except Exception as e:
                itens_com_erro += 1
                print(f"❌ Erro ao sincronizar item {item['item_id']}: {str(e)}")
        
        print(f"📊 Sincronização concluída: {itens_sincronizados} sucessos, {itens_com_erro} erros")
        
        # Aguardar processamento das sincronizações
        if itens_sincronizados > 0:
            print("⏳ Aguardando processamento das sincronizações...")
            time.sleep(2)  # Delay para permitir processamento das sincronizações
            
        return {
            'itens_sincronizados': itens_sincronizados,
            'itens_com_erro': itens_com_erro
        }
        
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
