"""
Connector principal para a API Pluggy - Versão refatorada com arquitetura modular
"""
import pandas as pd
import os
import time
import requests
import hashlib
import pickle
from datetime import date, timedelta, datetime
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from typing import Optional, TYPE_CHECKING
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

from utils.api_manager import ApiManager
from utils.cache_manager import CacheManager
from utils.sync_manager import SyncManager
from utils.account_manager import AccountManager
from utils.transaction_manager import TransactionManager
from utils.categorization_service import CategorizationService

class PluggyConnector:
    _instance = None
    
    def __init__(self):
        """Inicialização dos atributos da instância"""
        # Inicializar todos os atributos
        self.api_manager: Optional[ApiManager] = None
        self.cache_manager: Optional[CacheManager] = None
        self.sync_manager: Optional[SyncManager] = None
        self.account_manager: Optional[AccountManager] = None
        self.transaction_manager: Optional[TransactionManager] = None
        self.categorization_service: Optional[CategorizationService] = None
        self.chat_model: Optional[ChatOpenAI] = None

    def __new__(cls):
        """Implementação do padrão Singleton para garantir uma única instância"""
        if cls._instance is None:
            cls._instance = super(PluggyConnector, cls).__new__(cls)
            cls._instance.__init__()  # Chama explicitamente o __init__
            
            # Inicializar componentes
            cls._instance.api_manager = ApiManager()
            cls._instance.cache_manager = CacheManager()
            cls._instance.sync_manager = SyncManager(
                api_url=PLUGGY_API_URL,
                get_headers_func=cls._instance.api_manager.get_headers
            )
            cls._instance.account_manager = AccountManager(
                api_url=PLUGGY_API_URL,
                get_headers_func=cls._instance.api_manager.get_headers,
                cache_manager=cls._instance.cache_manager
            )
            cls._instance.categorization_service = CategorizationService(
                cache_manager=cls._instance.cache_manager
            )
            
            # Inicializar LLM se possível
            cls._instance._init_llm()
            
            # Configurar o Transaction Manager após inicializar o LLM
            cls._instance.transaction_manager = TransactionManager(
                api_url=PLUGGY_API_URL,
                get_headers_func=cls._instance.api_manager.get_headers,
                cache_manager=cls._instance.cache_manager,
                account_manager=cls._instance.account_manager,
                categorization_service=cls._instance.categorization_service
            )
            
        return cls._instance

    def _init_llm(self):
        """Inicializar modelo LLM para uso em várias funcionalidades"""
        try:
            # Tentar obter API key de várias fontes possíveis
            api_key = os.environ.get("OPENAI_API_KEY")
            
            if not api_key:
                # Tentar carregar de arquivo .env
                load_dotenv()
                api_key = os.environ.get("OPENAI_API_KEY")
            
            if not api_key or not api_key.startswith("sk-"):
                print("⚠️ Chave de API OpenAI não encontrada ou inválida. Categorização avançada desabilitada.")
                self.chat_model = None
                return
                
            os.environ["OPENAI_API_KEY"] = api_key  # Garante que a lib OpenAI encontra a chave
            from langchain_openai import ChatOpenAI
            from pydantic import SecretStr
            self.chat_model = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.2,
                max_completion_tokens=150,
                api_key=SecretStr(api_key)
            )
            
            # Configurar o serviço de categorização com o modelo LLM
            if self.categorization_service:
                self.categorization_service.set_llm_model(self.chat_model)
            
            # Teste rápido do modelo
            try:
                from langchain_core.messages import HumanMessage
                result = self.chat_model.invoke([HumanMessage(content="Responda apenas com a palavra 'ok' para testar a conexão.")])
                print(f"✅ Modelo LLM inicializado com sucesso: {result.content}")
            except Exception as e:
                print(f"⚠️ Modelo LLM inicializado, mas teste falhou: {str(e)}")
                
        except Exception as e:
            print(f"❌ Erro ao inicializar LLM: {str(e)}")
            self.chat_model = None

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
        conn.close()
        return items

    def limpar_cache(self):
        """Limpar cache do sistema"""
        if self.cache_manager:
            self.cache_manager.limpar_cache()

    def obter_saldo_atual(self, itemids_data):
        """Obter saldo atual das contas"""
        if self.account_manager:
            return self.account_manager.obter_saldo_atual(itemids_data)
        return pd.DataFrame()

    def buscar_extratos(self, itemids_data, dias=DEFAULT_PERIOD_DAYS):
        """Buscar extratos das contas"""
        if self.transaction_manager:
            return self.transaction_manager.buscar_extratos(itemids_data, dias)
        return pd.DataFrame()

    def buscar_cartoes(self, itemids_data, dias=DEFAULT_PERIOD_DAYS):
        """Buscar transações de cartão"""
        if self.transaction_manager:
            return self.transaction_manager.buscar_cartoes(itemids_data, dias)
        return pd.DataFrame()

    def categorizar_transacoes_com_llm(self, df, coluna_descricao='description', coluna_valor='amount', coluna_tipo='account_type'):
        """Categorizar transações usando LLM"""
        if self.categorization_service:
            return self.categorization_service.categorizar_transacoes_com_llm(df, coluna_descricao, coluna_valor, coluna_tipo)
        return df

    def testar_autenticacao(self):
        """Testar se a autenticação está funcionando"""
        if self.api_manager:
            return self.api_manager.testar_autenticacao()
        return False

    def testar_item_id(self, item_id):
        """Testar se um item_id específico está funcionando"""
        if self.sync_manager:
            return self.sync_manager.testar_item_id(item_id)
        return False

    def forcar_sync_item(self, item_id):
        """Forçar sincronização de um item específico"""
        if self.sync_manager:
            return self.sync_manager.forcar_sync_item(item_id)
        return False

    def enriquecer_descricoes(self, df, coluna_descricao='description'):
        """Enriquecer descrições das transações"""
        if self.categorization_service:
            return self.categorization_service.enriquecer_descricoes(df, coluna_descricao)
        return df

    def aplicar_categorizacao_basica(self, df):
        """Aplicar categorização básica às transações"""
        if self.categorization_service:
            return self.categorization_service.aplicar_categorizacao_basica(df)
        return df

    def executar_sincronizacao_completa(self, itemids_data):
        """Executar sincronização completa dos dados"""
        try:
            # Autenticar primeiro
            if self.api_manager:
                self.api_manager.authenticate()
            
            # Sincronizar itens
            if self.sync_manager:
                sync_result = self.sync_manager.sincronizar_itens(itemids_data)
                return sync_result
            
            return {"success": False, "message": "Managers não inicializados"}
            
        except Exception as e:
            return {"success": False, "message": f"Erro na sincronização: {str(e)}"}

    def atualizar_dados_otimizado(self, itemids_data, modo_rapido=True):
        """
        Atualiza dados com otimizações para melhor performance
        
        Args:
            itemids_data: Lista de itens para sincronizar
            modo_rapido: Se True, usa categorização básica. Se False, usa LLM completo
            
        Returns:
            dict: Resultado da operação com estatísticas
        """
        sync_result = {"itens_sincronizados": 0, "itens_com_erro": 0}
        try:
            print("🔄 Iniciando atualização otimizada de dados...")
            
            # Autenticar primeiro
            if self.api_manager:
                auth_success = self.api_manager.authenticate()
                if not auth_success:
                    return {
                        "success": False, 
                        "message": "Falha na autenticação",
                        "itens_sincronizados": 0,
                        "itens_com_erro": 0
                    }
            
            # FORÇAR SINCRONIZAÇÃO DE CADA ITEM
            for item in itemids_data:
                self.forcar_sync_item(item['item_id'])

            # Sincronizar itens primeiro para garantir dados frescos
            if self.sync_manager:
                sync_result = self.sync_manager.sincronizar_itens(itemids_data)
                print(f"📊 Sincronização: {sync_result['itens_sincronizados']} sucessos, {sync_result['itens_com_erro']} erros")
            
            # Aguardar processamento das sincronizações se houve sucessos
            if sync_result.get("itens_sincronizados", 0) > 0:
                print("⏳ Aguardando processamento...")
                time.sleep(2)
            
            # Buscar dados atualizados
            dados_completos = []
            
            # Extratos bancários
            if self.transaction_manager:
                print("🏦 Buscando extratos bancários...")
                extratos = self.transaction_manager.buscar_extratos(itemids_data)
                if not extratos.empty:
                    dados_completos.append(extratos)
            
            # Cartões de crédito
            if self.transaction_manager:
                print("💳 Buscando transações de cartão...")
                cartoes = self.transaction_manager.buscar_cartoes(itemids_data)
                if not cartoes.empty:
                    dados_completos.append(cartoes)
            
            # Combinar dados
            if dados_completos:
                df_combined = pd.concat(dados_completos, ignore_index=True)
                
                # Aplicar categorização baseada no modo
                if modo_rapido:
                    print("⚡ Aplicando categorização rápida...")
                    df_categorizado = self.aplicar_categorizacao_basica(df_combined)
                else:
                    print("🤖 Aplicando categorização com IA...")
                    df_categorizado = self.categorizar_transacoes_com_llm(df_combined)
                    
                total_transacoes = len(df_categorizado)
                print(f"✅ Processadas {total_transacoes} transações")
                
                return {
                    "success": True,
                    "message": f"Dados atualizados com sucesso - {total_transacoes} transações processadas",
                    "dados": df_categorizado,
                    "total_transacoes": total_transacoes,
                    "itens_sincronizados": sync_result.get("itens_sincronizados", 0),
                    "itens_com_erro": sync_result.get("itens_com_erro", 0),
                    "modo_usado": "rápido" if modo_rapido else "completo"
                }
            else:
                return {
                    "success": True,
                    "message": "Nenhuma transação encontrada",
                    "dados": pd.DataFrame(),
                    "total_transacoes": 0,
                    "itens_sincronizados": sync_result.get("itens_sincronizados", 0),
                    "itens_com_erro": sync_result.get("itens_com_erro", 0),
                    "modo_usado": "rápido" if modo_rapido else "completo"
                }
                
        except Exception as e:
            print(f"❌ Erro na atualização: {str(e)}")
            return {
                "success": False,
                "message": f"Erro na atualização: {str(e)}",
                "itens_sincronizados": sync_result.get("itens_sincronizados", 0) if 'sync_result' in locals() else 0,
                "itens_com_erro": sync_result.get("itens_com_erro", 0) if 'sync_result' in locals() else 0
            }