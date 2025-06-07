#!/usr/bin/env python3
"""
Script de Limpeza do Projeto Richness
Organiza arquivos e remove itens desnecessários de forma segura
"""

import os
import shutil
import sys
from pathlib import Path
from datetime import datetime

def create_cleanup_folders():
    """Cria pastas para organizar os arquivos"""
    folders_to_create = [
        "cleanup_temp/tests",
        "cleanup_temp/docs_antigos", 
        "cleanup_temp/scripts_temporarios",
        "cleanup_temp/relatorios"
    ]
    
    for folder in folders_to_create:
        os.makedirs(folder, exist_ok=True)
        print(f"✅ Pasta criada: {folder}")

def get_files_to_move():
    """Define quais arquivos devem ser movidos para onde"""
    return {
        # Arquivos de teste temporários
        "cleanup_temp/tests": [
            "test_ai_diagnosis.py",
            "test_categorization_improvements.py", 
            "test_categorization_system.py",
            "test_complete_categorization.py",
            "test_dicas_financeiras.py",
            "test_graficos_categoria.py",
            "test_home_changes.py",
            "test_simple.py",
            "simple_auto_cat_test.py",
            "simple_fix.py",
            "health_check.py",
            "quick_check.py",
            "check_all_data.py",
            "check_categories.py",
            "check_data.py", 
            "check_db.py",
            "check_status.py",
            "verify_changes.py",
            "verify_system_ready.py"
        ],
        
        # Scripts de correção temporários
        "cleanup_temp/scripts_temporarios": [
            "categorization_fix_summary.py",
            "cleanup_final.py",
            "execute_fix.py",
            "final_status_report.py",
            "final_system_verification.py",
            "fix_categorization.py",
            "fix_categorization_corrected.py", 
            "fix_user4_categorization.py",
            "run_fix.py",
            "inspect_database.py",
            "verificacao_final_sistema.py",
            "verificacao_sistema_restaurado.py"
        ],
        
        # Relatórios e documentação antiga
        "cleanup_temp/relatorios": [
            "CATEGORIZATION_FIX_DOCUMENTATION.md",
            "CHECKLIST_VERIFICACAO_FINAL.md",
            "CORRECAO_IA_RELATORIO_FINAL.md",
            "GUIA_TESTE_SISTEMA_RESTAURADO.md",
            "IMPLEMENTACAO_FINAL_CATEGORIZAÇÃO.md",
            "RELATORIO_MELHORIAS_CATEGORIZACAO.md",
            "RELATORIO_OTIMIZACAO_GRAFICOS.md",
            "SISTEMA_CATEGORIZAÇÃO_STATUS_FINAL.md",
            "STATUS_FINAL_SISTEMA.md"
        ]
    }

def move_files():
    """Move arquivos para suas respectivas pastas"""
    files_to_move = get_files_to_move()
    moved_files = []
    
    for destination, files in files_to_move.items():
        for filename in files:
            if os.path.exists(filename):
                try:
                    shutil.move(filename, os.path.join(destination, filename))
                    moved_files.append(f"{filename} → {destination}")
                    print(f"📁 Movido: {filename} → {destination}")
                except Exception as e:
                    print(f"⚠️ Erro ao mover {filename}: {e}")
    
    return moved_files

def clean_pycache():
    """Remove arquivos __pycache__ desnecessários"""
    removed_cache = []
    
    for root, dirs, files in os.walk("."):
        if "__pycache__" in dirs:
            cache_path = os.path.join(root, "__pycache__")
            try:
                shutil.rmtree(cache_path)
                removed_cache.append(cache_path)
                print(f"🗑️ Cache removido: {cache_path}")
            except Exception as e:
                print(f"⚠️ Erro ao remover cache {cache_path}: {e}")
    
    return removed_cache

def organize_docs():
    """Organiza documentação mantendo apenas essenciais na raiz"""
    essential_docs = [
        "Readme.md",
        "GUIA_USO_RAPIDO.md", 
        "GUIA_USUARIO_FINAL.md"
    ]
    
    print(f"📚 Documentos essenciais mantidos na raiz:")
    for doc in essential_docs:
        if os.path.exists(doc):
            print(f"  ✅ {doc}")
        else:
            print(f"  ⚠️ {doc} (não encontrado)")

def create_cleanup_report(moved_files, removed_cache):
    """Cria relatório da limpeza"""
    report_content = f"""# 🧹 RELATÓRIO DE LIMPEZA DO PROJETO RICHNESS

## 📊 **RESUMO DA LIMPEZA**
**Data**: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

### 📁 **Arquivos Reorganizados**: {len(moved_files)}
### 🗑️ **Caches Removidos**: {len(removed_cache)}

## 📋 **ESTRUTURA APÓS LIMPEZA**

### 🏠 **Arquivos Principais (Raiz)**
- `Home.py` - Página principal
- `database.py` - Configuração do banco
- `requirements.txt` - Dependências
- `richness.db*` - Banco de dados
- `.env` - Variáveis de ambiente

### 📚 **Documentação Essencial**
- `Readme.md` - Documentação principal
- `GUIA_USO_RAPIDO.md` - Guia de uso
- `GUIA_USUARIO_FINAL.md` - Manual do usuário

### 📂 **Pastas Principais**
- `pages/` - Páginas da aplicação
- `utils/` - Utilitários e helpers
- `security/` - Sistema de segurança
- `componentes/` - Componentes reutilizáveis
- `profile_pics/` - Fotos de perfil
- `logs/` - Logs do sistema

### 🧹 **Arquivos Temporários Organizados**
- `cleanup_temp/tests/` - Scripts de teste
- `cleanup_temp/scripts_temporarios/` - Scripts de correção
- `cleanup_temp/relatorios/` - Relatórios antigos

## 📁 **ARQUIVOS MOVIDOS**

### 🧪 **Testes Temporários**
{chr(10).join([f'- {f}' for f in moved_files if 'test' in f or 'check' in f or 'verify' in f])}

### 🔧 **Scripts de Correção**
{chr(10).join([f'- {f}' for f in moved_files if 'fix' in f or 'execute' in f or 'run' in f])}

### 📄 **Relatórios Antigos**
{chr(10).join([f'- {f}' for f in moved_files if '.md' in f and 'cleanup_temp/relatorios' in f])}

## 🗑️ **Caches Removidos**
{chr(10).join([f'- {cache}' for cache in removed_cache])}

## ✅ **ESTRUTURA FINAL LIMPA**

O projeto agora está organizado com:
- ✅ Arquivos principais na raiz
- ✅ Documentação essencial visível
- ✅ Arquivos temporários organizados
- ✅ Cache desnecessário removido
- ✅ Estrutura clara e profissional

## 🚀 **PRÓXIMOS PASSOS**

1. **Verificar funcionamento**: Testar se aplicação ainda funciona
2. **Revisar arquivos temporários**: Decidir quais manter/remover definitivamente
3. **Atualizar .gitignore**: Incluir pasta cleanup_temp se necessário
4. **Backup**: Fazer backup antes de remover definitivamente

---
**Status**: ✅ Limpeza concluída com sucesso
**Arquivos organizados**: {len(moved_files)}
**Caches removidos**: {len(removed_cache)}
"""
    
    with open("cleanup_temp/RELATORIO_LIMPEZA.md", "w", encoding="utf-8") as f:
        f.write(report_content)
    
    print(f"📄 Relatório criado: cleanup_temp/RELATORIO_LIMPEZA.md")

def main():
    """Função principal de limpeza"""
    print("🧹 INICIANDO LIMPEZA DO PROJETO RICHNESS")
    print("=" * 50)
    
    try:
        # Criar pastas de organização
        print("\n📁 Criando pastas de organização...")
        create_cleanup_folders()
        
        # Mover arquivos temporários
        print("\n📦 Movendo arquivos temporários...")
        moved_files = move_files()
        
        # Limpar cache
        print("\n🗑️ Removendo caches desnecessários...")
        removed_cache = clean_pycache()
        
        # Organizar documentação
        print("\n📚 Verificando documentação essencial...")
        organize_docs()
        
        # Criar relatório
        print("\n📄 Criando relatório de limpeza...")
        create_cleanup_report(moved_files, removed_cache)
        
        print(f"\n🎉 LIMPEZA CONCLUÍDA COM SUCESSO!")
        print(f"📊 Resumo:")
        print(f"   📁 Arquivos movidos: {len(moved_files)}")
        print(f"   🗑️ Caches removidos: {len(removed_cache)}")
        print(f"   📄 Relatório: cleanup_temp/RELATORIO_LIMPEZA.md")
        
        print(f"\n⚠️ IMPORTANTE:")
        print(f"   • Teste a aplicação para garantir que tudo funciona")
        print(f"   • Revise os arquivos em cleanup_temp/")
        print(f"   • Remova definitivamente quando confirmar que não são necessários")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro durante a limpeza: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
