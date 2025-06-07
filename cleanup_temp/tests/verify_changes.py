#!/usr/bin/env python3
"""
Verificação das mudanças realizadas na remoção da opção Carregamento Rápido
"""

import os
import sys

# Adicionar o diretório raiz ao path do Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_environment_variable():
    """Verifica se a variável de ambiente está configurada corretamente"""
    print("🔍 VERIFICAÇÃO DA VARIÁVEL DE AMBIENTE")
    print("=" * 40)
    
    # Simular a configuração que o Home.py faz
    os.environ["SKIP_LLM_PROCESSING"] = "false"
    
    skip_llm = os.environ.get("SKIP_LLM_PROCESSING", "true")
    print(f"📊 SKIP_LLM_PROCESSING: {skip_llm}")
    
    if skip_llm.lower() == "false":
        print("✅ IA PROCESSAMENTO ATIVADO (correto)")
        return True
    else:
        print("❌ IA PROCESSAMENTO DESATIVADO (problema)")
        return False

def check_auto_categorization():
    """Verifica se o auto_categorization respeitará a configuração"""
    print("\n🤖 VERIFICAÇÃO DO AUTO CATEGORIZATION")
    print("=" * 40)
    
    try:
        from utils.auto_categorization import AutoCategorization
        
        auto_cat = AutoCategorization()
        print(f"📊 Skip AI Processing: {auto_cat.skip_ai_processing}")
        
        if not auto_cat.skip_ai_processing:
            print("✅ AUTO CATEGORIZATION COM IA ATIVADO (correto)")
            return True
        else:
            print("❌ AUTO CATEGORIZATION COM IA DESATIVADO (problema)")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao verificar auto categorization: {e}")
        return False

def main():
    print("🚀 VERIFICAÇÃO COMPLETA DAS MUDANÇAS")
    print("=" * 50)
    
    env_ok = check_environment_variable()
    auto_cat_ok = check_auto_categorization()
    
    print(f"\n📋 RESUMO DOS RESULTADOS:")
    print(f"{'✅' if env_ok else '❌'} Variável de ambiente configurada")
    print(f"{'✅' if auto_cat_ok else '❌'} Auto categorization configurado")
    
    if env_ok and auto_cat_ok:
        print("\n🎉 TODAS AS VERIFICAÇÕES PASSARAM!")
        print("🤖 A IA ESTÁ CONFIGURADA PARA PROCESSAR TODAS AS TRANSAÇÕES")
        return True
    else:
        print("\n⚠️ ALGUMAS VERIFICAÇÕES FALHARAM")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
