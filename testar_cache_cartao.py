#!/usr/bin/env python3
"""
Script para testar o funcionamento do cache de insights na página Cartão
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from datetime import datetime
from services.insights_cache_service import InsightsCacheService
from utils.database_manager_v2 import DatabaseManager
from utils.repositories_v2 import UsuarioRepository


def testar_cache_cartao():
    """Testa o sistema de cache para insights do cartão"""
    print("🧪 Testando Sistema de Cache - Página Cartão")
    print("=" * 50)
    
    try:
        # Inicializar serviços
        cache_service = InsightsCacheService()
        db = DatabaseManager()
        usuario_repo = UsuarioRepository(db)
        
        # Simular dados do usuário (substitua por usuário real se necessário)
        usuario_test = "admin"  # ou outro usuário de teste
        user_data = usuario_repo.obter_usuario_por_username(usuario_test)
        
        if not user_data:
            print(f"❌ Usuário '{usuario_test}' não encontrado")
            return False
        
        user_id = user_data.get('id')
        print(f"✅ Usuário encontrado: {usuario_test} (ID: {user_id})")
        
        # Simular dados de contexto do cartão
        contexto_teste = {
            'personalidade': 'clara',
            'total_gastos': 1500.50,
            'ultimas_transacoes_cartao': [
                {'valor': -250.00, 'categoria': 'Alimentação', 'data': '2024-01-15'},
                {'valor': -150.00, 'categoria': 'Transporte', 'data': '2024-01-14'},
                {'valor': -80.00, 'categoria': 'Compras', 'data': '2024-01-13'},
            ],
            'usuario': user_data,
            'periodo_analise': '30 últimas transações'
        }
        
        # Parâmetros de personalidade
        params_teste = {
            'formalidade': 'Informal',
            'emojis': 'Moderado',
            'tom': 'Acolhedor'
        }
        
        # Prompt de teste
        prompt_teste = "Analise o total de gastos no cartão de crédito baseado nas últimas transações, considerando o perfil da IA."
        
        print("\n🔍 Teste 1: Geração inicial do insight (deve usar LLM)")
        print("-" * 40)
        
        # Primeira chamada - deve usar LLM
        resultado1 = cache_service.gerar_insight_com_cache(
            user_id=user_id,
            insight_type='total_gastos_cartao',
            personalidade='clara',
            data_context=contexto_teste,
            prompt=prompt_teste,
            personalidade_params=params_teste,
            forcar_regeneracao=False
        )
        
        print(f"Source: {resultado1['source']}")
        print(f"Título: {resultado1['titulo']}")
        print(f"Comentário: {resultado1['comentario'][:100]}...")
        
        if resultado1['source'] != 'llm':
            print("⚠️  ATENÇÃO: Esperava-se fonte 'llm' na primeira chamada")
        
        print("\n🔍 Teste 2: Segunda chamada (deve usar CACHE)")
        print("-" * 40)
        
        # Segunda chamada - deve usar cache
        resultado2 = cache_service.gerar_insight_com_cache(
            user_id=user_id,
            insight_type='total_gastos_cartao',
            personalidade='clara',
            data_context=contexto_teste,
            prompt=prompt_teste,
            personalidade_params=params_teste,
            forcar_regeneracao=False
        )
        
        print(f"Source: {resultado2['source']}")
        print(f"Título: {resultado2['titulo']}")
        print(f"Used Count: {resultado2.get('used_count', 'N/A')}")
        
        if resultado2['source'] != 'cache':
            print("❌ ERRO: Segunda chamada deveria usar cache!")
            return False
        else:
            print("✅ Cache funcionando corretamente!")
        
        print("\n🔍 Teste 3: Forçar regeneração (deve usar LLM)")
        print("-" * 40)
        
        # Terceira chamada - com força regeneração
        resultado3 = cache_service.gerar_insight_com_cache(
            user_id=user_id,
            insight_type='total_gastos_cartao',
            personalidade='clara',
            data_context=contexto_teste,
            prompt=prompt_teste,
            personalidade_params=params_teste,
            forcar_regeneracao=True
        )
        
        print(f"Source: {resultado3['source']}")
        print(f"Título: {resultado3['titulo']}")
        
        if resultado3['source'] != 'llm':
            print("❌ ERRO: Regeneração forçada deveria usar LLM!")
            return False
        else:
            print("✅ Regeneração forçada funcionando!")
        
        print("\n🔍 Teste 4: Testando hash consistency")
        print("-" * 40)
        
        # Testar se hashes são consistentes
        hash1 = cache_service.gerar_data_hash(contexto_teste)
        hash2 = cache_service.gerar_data_hash(contexto_teste)
        
        if hash1 == hash2:
            print(f"✅ Hashes consistentes: {hash1[:16]}...")
        else:
            print(f"❌ ERRO: Hashes inconsistentes!")
            print(f"Hash 1: {hash1}")
            print(f"Hash 2: {hash2}")
            return False
        
        # Testar mudança nos dados
        contexto_modificado = contexto_teste.copy()
        contexto_modificado['total_gastos'] = 2000.00  # Mudar valor
        
        hash3 = cache_service.gerar_data_hash(contexto_modificado)
        
        if hash1 != hash3:
            print(f"✅ Detecção de mudança funcionando: {hash3[:16]}...")
        else:
            print("❌ ERRO: Mudança nos dados não foi detectada!")
            return False
        
        print("\n📊 Estatísticas do Cache")
        print("-" * 40)
        
        stats = cache_service.obter_estatisticas_cache_usuario(user_id)
        print(f"Total de entradas: {stats.get('total_cache_entries', 0)}")
        print(f"Eficiência: {stats.get('eficiencia_cache', 0)}%")
        print(f"Cache válido por tipo: {stats.get('cache_valido_por_tipo', {})}")
        
        print("\n✅ TODOS OS TESTES PASSARAM!")
        print("🎉 Sistema de cache está funcionando corretamente!")
        return True
        
    except Exception as e:
        print(f"❌ ERRO durante o teste: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    sucesso = testar_cache_cartao()
    sys.exit(0 if sucesso else 1) 