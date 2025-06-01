#!/usr/bin/env python3
"""
Script de debug para investigar o problema dos saldos zerados na Home
"""
import sys
import os
from utils.pluggy_connector import PluggyConnector
from utils.auth import obter_usuario_logado

def debug_saldos():
    print("=== DEBUG SALDOS ZERADOS NA HOME ===")
    
    # 1. Verificar se há usuário logado
    try:
        usuario = "richardpalmas"  # Usar usuário padrão para teste
        print(f"Usuário para teste: {usuario}")
    except Exception as e:
        print(f"❌ Erro ao obter usuário: {e}")
        return
    
    # 2. Inicializar PluggyConnector
    try:
        pluggy = PluggyConnector()
        print("✅ PluggyConnector inicializado com sucesso")
        
        # Testar autenticação
        if pluggy.testar_autenticacao():
            print("✅ Autenticação funcionando")
        else:
            print("❌ Problema na autenticação")
            return
            
    except Exception as e:
        print(f"❌ Erro ao inicializar PluggyConnector: {e}")
        return
    
    # 3. Carregar item IDs do usuário
    try:
        itemids_data = pluggy.load_itemids_db(usuario)
        print(f"Item IDs encontrados: {len(itemids_data)}")
        
        if not itemids_data:
            print("❌ Nenhum item ID encontrado para o usuário")
            print("   Verifique se o usuário tem contas cadastradas na página Cadastro Pluggy")
            return
        
        for item in itemids_data:
            print(f"   - Item ID: {item['item_id']}, Nome: {item['nome']}")
            
    except Exception as e:
        print(f"❌ Erro ao carregar item IDs: {e}")
        return
    
    # 4. Testar cada item ID individualmente
    print("\n=== TESTANDO CADA ITEM ID ===")
    for item in itemids_data:
        print(f"\nTestando item: {item['nome']} (ID: {item['item_id']})")
        try:
            if pluggy.testar_item_id(item['item_id']):
                print(f"✅ Item ID {item['item_id']} está válido")
            else:
                print(f"❌ Item ID {item['item_id']} tem problemas")
        except Exception as e:
            print(f"❌ Erro ao testar item ID {item['item_id']}: {e}")
    
    # 5. Obter saldos detalhadamente
    print("\n=== OBTENDO SALDOS ===")
    try:
        # Limpar cache para forçar busca fresca
        pluggy.limpar_cache()
        
        saldos_info = pluggy.obter_saldo_atual(itemids_data)
        
        if saldos_info is None:
            print("❌ Saldos retornaram None")
            return
        
        if len(saldos_info) < 4:
            print(f"❌ Formato de saldos inválido: {saldos_info}")
            return
            
        saldo_positivo, saldo_negativo, contas_detalhes, saldo_total = saldos_info
        
        print(f"✅ Saldo Positivo: R$ {saldo_positivo:.2f}")
        print(f"✅ Saldo Negativo: R$ {saldo_negativo:.2f}")
        print(f"✅ Saldo Total: R$ {saldo_total:.2f}")
        print(f"✅ Contas encontradas: {len(contas_detalhes)}")
        
        # Detalhar cada conta
        print("\n=== DETALHES DAS CONTAS ===")
        for i, conta in enumerate(contas_detalhes):
            print(f"Conta {i+1}:")
            print(f"   Nome: {conta.get('Nome da Conta', 'N/A')}")
            print(f"   Tipo: {conta.get('Tipo', 'N/A')}")
            print(f"   Saldo: R$ {conta.get('Saldo', 0):.2f}")
        
        # Se todos os saldos são zero, investigar mais
        if saldo_total == 0 and saldo_positivo == 0 and saldo_negativo == 0:
            print("\n❌ PROBLEMA IDENTIFICADO: Todos os saldos são zero!")
            print("Possíveis causas:")
            print("1. API retornando saldos zerados")
            print("2. Estrutura da resposta da API mudou")
            print("3. Item IDs não têm contas associadas")
            print("4. Problema na lógica de soma dos saldos")
            
            # Investigar resposta raw da API
            print("\n=== INVESTIGANDO RESPOSTA RAW DA API ===")
            import requests
            for item in itemids_data[:1]:  # Testar apenas o primeiro item
                try:
                    response = requests.get(
                        f"{pluggy.api_url}/items/{item['item_id']}/accounts",
                        headers=pluggy.get_headers()
                    )
                    print(f"Status Code: {response.status_code}")
                    if response.status_code == 200:
                        data = response.json()
                        print(f"Resposta JSON: {data}")
                    else:
                        print(f"Erro na resposta: {response.text}")
                except Exception as e:
                    print(f"Erro na requisição: {e}")
        
    except Exception as e:
        print(f"❌ Erro ao obter saldos: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_saldos()
