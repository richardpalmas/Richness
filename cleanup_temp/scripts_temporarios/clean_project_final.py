#!/usr/bin/env python3
"""
🧹 APLICAÇÃO DO 4º FUNDAMENTO: PROJETO LIMPO
Script de limpeza e organização final do projeto Richness

Este script implementa o 4º fundamento estabelecido para o projeto:
"🧹 PROJETO LIMPO - Código limpo, legível e bem estruturado"

Funcionalidades:
- Remove arquivos temporários e de teste
- Organiza documentação redundante
- Move relatórios antigos para arquivo
- Limpa cache desnecessário
- Verifica estrutura do projeto
- Gera relatório final de limpeza
"""

import os
import shutil
import glob
import sys
from pathlib import Path
from datetime import datetime

class FinalProjectCleaner:
    """Classe responsável pela limpeza final do projeto"""
    
    def __init__(self, project_root=None):
        if project_root is None:
            current_file = Path(__file__).absolute()
            self.project_root = current_file.parent.parent
        else:
            self.project_root = Path(project_root)
        
        self.cleaned_files = []
        self.organized_files = []
        self.errors = []
        
    def clean_test_files(self):
        """Remove arquivos de teste temporários"""
        print("🧪 Removendo arquivos de teste temporários...")
        
        test_patterns = [
            "test_*.py",
            "*_test.py", 
            "verificacao_*.py",
            "verify_*.py",
            "final_system_verification.py"
        ]
        
        for pattern in test_patterns:
            for file_path in self.project_root.glob(pattern):
                if file_path.is_file():
                    try:
                        file_path.unlink()
                        self.cleaned_files.append(str(file_path.name))
                        print(f"   ✅ Removido: {file_path.name}")
                    except Exception as e:
                        self.errors.append(f"Erro ao remover {file_path.name}: {e}")
        
    def organize_documentation(self):
        """Organiza documentação redundante"""
        print("📚 Organizando documentação...")
        
        # Criar diretório para documentação histórica
        archive_dir = self.project_root / "cleanup_temp" / "docs_historicos"
        archive_dir.mkdir(exist_ok=True)
        
        # Arquivos de documentação para arquivar
        doc_files_to_archive = [
            "CHECKLIST_VERIFICACAO_FINAL.md",
            "CORRECAO_IA_RELATORIO_FINAL.md", 
            "GUIA_TESTE_SISTEMA_RESTAURADO.md",
            "IMPLEMENTACAO_FINAL_CATEGORIZAÇÃO.md",
            "RELATORIO_MELHORIAS_CATEGORIZACAO.md",
            "RELATORIO_OTIMIZACAO_GRAFICOS.md",
            "SISTEMA_CATEGORIZAÇÃO_STATUS_FINAL.md",
            "STATUS_FINAL_SISTEMA.md",
            "RELATORIO_LIMPEZA_FINAL_07_06_2025.md"
        ]
        
        for doc_file in doc_files_to_archive:
            file_path = self.project_root / doc_file
            if file_path.exists():
                try:
                    dest_path = archive_dir / doc_file
                    shutil.move(str(file_path), str(dest_path))
                    self.organized_files.append(f"Movido {doc_file} para docs_historicos/")
                    print(f"   📁 Arquivado: {doc_file}")
                except Exception as e:
                    self.errors.append(f"Erro ao mover {doc_file}: {e}")
    
    def clean_temp_scripts(self):
        """Remove scripts temporários de limpeza"""
        print("🗑️ Removendo scripts temporários...")
        
        temp_scripts = [
            "cleanup.ps1",
            "cleanup_final.py", 
            "cleanup_project.py"
        ]
        
        for script in temp_scripts:
            file_path = self.project_root / script
            if file_path.exists():
                try:
                    # Mover para cleanup_temp em vez de deletar
                    dest_path = self.project_root / "cleanup_temp" / "scripts_temporarios" / script
                    shutil.move(str(file_path), str(dest_path))
                    self.organized_files.append(f"Movido {script} para scripts_temporarios/")
                    print(f"   📦 Movido: {script}")
                except Exception as e:
                    self.errors.append(f"Erro ao mover {script}: {e}")
    
    def clean_cache_files(self):
        """Limpa arquivos de cache Python"""
        print("🗂️ Limpando cache Python...")
        
        cache_patterns = [
            "**/__pycache__",
            "**/*.pyc",
            "**/*.pyo"
        ]
        
        cleaned_count = 0
        for pattern in cache_patterns:
            for path in self.project_root.rglob(pattern.split('/')[-1]):
                try:
                    if path.is_file():
                        path.unlink()
                        cleaned_count += 1
                    elif path.is_dir():
                        shutil.rmtree(str(path))
                        cleaned_count += 1
                except Exception as e:
                    self.errors.append(f"Erro ao remover cache {path}: {e}")
        
        if cleaned_count > 0:
            print(f"   ✅ {cleaned_count} itens de cache removidos")
        else:
            print("   ✅ Cache já limpo")
    
    def verify_structure(self):
        """Verifica estrutura essencial do projeto"""
        print("🔍 Verificando estrutura do projeto...")
        
        essential_dirs = ["pages", "utils", "security", "componentes", "docs", "logs"]
        essential_files = ["Home.py", "database.py", "requirements.txt", "Readme.md"]
        
        # Verificar diretórios
        for dir_name in essential_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists():
                print(f"   ✅ Diretório {dir_name}/ presente")
            else:
                print(f"   ⚠️  Diretório {dir_name}/ ausente")
        
        # Verificar arquivos essenciais
        for file_name in essential_files:
            file_path = self.project_root / file_name
            if file_path.exists():
                print(f"   ✅ Arquivo {file_name} presente")
            else:
                print(f"   ⚠️  Arquivo {file_name} ausente")
    
    def optimize_pages_directory(self):
        """Otimiza diretório de páginas"""
        print("📄 Otimizando diretório pages/...")
        
        pages_dir = self.project_root / "pages"
        if not pages_dir.exists():
            print("   ⚠️  Diretório pages/ não encontrado")
            return
            
        # Verificar se há arquivos duplicados ou temporários em pages/
        pages_files = list(pages_dir.glob("*.py"))
        
        # Procurar por arquivos com sufixos temporários
        temp_suffixes = ["_backup", "_old", "_test", "_temp", "_Fixed"]
        
        for page_file in pages_files:
            if any(suffix in page_file.stem for suffix in temp_suffixes):
                backup_dir = self.project_root / "cleanup_temp" / "pages_backup"
                backup_dir.mkdir(exist_ok=True)
                
                try:
                    dest_path = backup_dir / page_file.name
                    shutil.move(str(page_file), str(dest_path))
                    self.organized_files.append(f"Movido {page_file.name} para pages_backup/")
                    print(f"   📦 Backup: {page_file.name}")
                except Exception as e:
                    self.errors.append(f"Erro ao mover {page_file.name}: {e}")
        
        # Contar páginas ativas restantes
        active_pages = list(pages_dir.glob("*.py"))
        print(f"   ✅ {len(active_pages)} páginas ativas mantidas")
    
    def generate_final_report(self):
        """Gera relatório final de limpeza"""
        print("\n" + "="*60)
        print("📊 RELATÓRIO FINAL - 4º FUNDAMENTO: PROJETO LIMPO")
        print("="*60)
        
        # Estatísticas
        total_cleaned = len(self.cleaned_files)
        total_organized = len(self.organized_files)
        total_errors = len(self.errors)
        
        print(f"🗑️  Arquivos removidos: {total_cleaned}")
        print(f"📁 Itens organizados: {total_organized}")
        print(f"❌ Erros encontrados: {total_errors}")
        
        # Detalhes dos arquivos limpos
        if self.cleaned_files:
            print(f"\n📋 Arquivos removidos:")
            for file_name in self.cleaned_files[:10]:
                print(f"   - {file_name}")
            if len(self.cleaned_files) > 10:
                print(f"   ... e mais {len(self.cleaned_files) - 10} arquivos")
        
        # Organização realizada
        if self.organized_files:
            print(f"\n📁 Organização realizada:")
            for item in self.organized_files:
                print(f"   - {item}")
        
        # Erros (se houver)
        if self.errors:
            print(f"\n⚠️  Erros encontrados:")
            for error in self.errors[:5]:
                print(f"   - {error}")
            if len(self.errors) > 5:
                print(f"   ... e mais {len(self.errors) - 5} erros")
        
        # Status final
        print(f"\n✅ LIMPEZA FINAL CONCLUÍDA - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print("🧹 Projeto organizado segundo o 4º Fundamento: PROJETO LIMPO")
        
        # Estrutura final
        print(f"\n📁 ESTRUTURA FINAL LIMPA:")
        print("   📄 Arquivos principais: Home.py, database.py, requirements.txt")
        print("   📁 pages/ - Páginas ativas da aplicação")
        print("   📁 utils/ - Utilitários essenciais") 
        print("   📁 security/ - Sistema de segurança")
        print("   📁 docs/ - Documentação principal")
        print("   📁 cleanup_temp/ - Arquivos temporários organizados")
        
        # Recomendações
        print(f"\n💡 RECOMENDAÇÕES:")
        print("   - Evite criar arquivos de teste no diretório raiz")
        print("   - Use cleanup_temp/ para arquivos temporários")
        print("   - Mantenha a documentação em docs/")
        print("   - Execute limpeza periódica para manter o projeto organizado")
        
        return {
            'cleaned_files': total_cleaned,
            'organized_items': total_organized,
            'errors': total_errors,
            'success': total_errors == 0
        }
    
    def run_full_cleanup(self):
        """Executa limpeza completa do projeto"""
        print("🧹 INICIANDO LIMPEZA FINAL DO PROJETO RICHNESS")
        print("Aplicando 4º Fundamento: PROJETO LIMPO")
        print("-" * 50)
        
        try:
            self.clean_test_files()
            self.organize_documentation()
            self.clean_temp_scripts()
            self.optimize_pages_directory()
            self.clean_cache_files()
            self.verify_structure()
            
            return self.generate_final_report()
            
        except Exception as e:
            print(f"❌ Erro durante limpeza: {e}")
            return {'success': False, 'error': str(e)}

def main():
    """Função principal"""
    print("🎯 APLICAÇÃO DO 4º FUNDAMENTO: PROJETO LIMPO")
    print("=" * 50)
    
    try:
        cleaner = FinalProjectCleaner()
        result = cleaner.run_full_cleanup()
        
        if result['success']:
            print(f"\n🎉 LIMPEZA CONCLUÍDA COM SUCESSO!")
            print(f"📊 {result['cleaned_files']} arquivos removidos")
            print(f"📁 {result['organized_items']} itens organizados")
        else:
            print(f"\n❌ Limpeza finalizada com erros: {result.get('error', 'Erro desconhecido')}")
            
    except Exception as e:
        print(f"❌ Erro fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
