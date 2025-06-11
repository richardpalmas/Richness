"""
Gerenciador de API para o Pluggy - Responsável pela autenticação e operações base da API
"""
import requests
from utils.config import (
    PLUGGY_CLIENT_ID, 
    PLUGGY_CLIENT_SECRET,
    PLUGGY_API_URL
)

class ApiManager:
    """Gerencia a autenticação e operações base com a API Pluggy"""
    
    def __init__(self):
        self.client_id = PLUGGY_CLIENT_ID
        self.client_secret = PLUGGY_CLIENT_SECRET
        self.api_url = PLUGGY_API_URL
        self.access_token = None
    
    def authenticate(self):
        """Autenticar com a API Pluggy e obter token de acesso"""
        try:
            # Se já tiver um token, retorna
            if self.access_token:
                return True
                
            print("🔑 Autenticando com API Pluggy...")
            response = requests.post(
                f"{self.api_url}/auth",
                json={
                    "clientId": self.client_id,
                    "clientSecret": self.client_secret
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("apiKey")
                print("✅ Autenticação bem-sucedida")
                return True
            else:
                print(f"❌ Erro na autenticação: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Erro ao autenticar: {str(e)}")
            return False
    
    def get_headers(self):
        """Retornar cabeçalhos de autenticação para requests"""
        if not self.access_token:
            self.authenticate()

        # Formato X-API-KEY (formato atual)
        headers = {
            "X-API-KEY": self.access_token,
            "Content-Type": "application/json"
        }
        return headers

    def get_bearer_headers(self):
        """Retornar cabeçalhos de autenticação no formato Bearer"""
        if not self.access_token:
            self.authenticate()

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        return headers
    
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
