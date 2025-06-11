#!/usr/bin/env python3
"""
🧹 APLICAÇÃO DO 4º PRINCÍPIO: PROJETO LIMPO
Script de limpeza e organização do projeto Richness

Este script implementa o 4º fundamento estabelecido para o projeto:
"🧹 PROJETO LIMPO - Código limpo, legível e bem estruturado"

Funcionalidades:
- Limpeza de arquivos temporários e cache
- Remoção de arquivos de debug obsoletos
- Organização da estrutura de diretórios
- Verificação de boas práticas de código
- Relatório de limpeza detalhado
"""

import os
import shutil
import glob
import sys
from pathlib import Path
from datetime import datetime

class ProjectCleaner:
    """Classe responsável pela limpeza e organização do projeto"""
    
    def __init__(self, project_root=None):
        if project_root is None:
            # Detectar automaticamente o diretório do projeto
            current_file = Path(__file__).absolute()
            self.project_root = current_file.parent.parent
        else:
            self.project_root = Path(project_root)
        
        self.cleaned_files = []
        self.organized_dirs = []
        self.errors = []
        
    def clean_cache_files(self):
        """Remove arquivos de cache Python e temporários"""
        print("🗑️  Limpando arquivos de cache...")
        
        # Padrões de arquivos para limpeza
        cache_patterns = [
            "**/__pycache__",
            "**/*.pyc",
            "**/*.pyo", 
            "**/*.pyd",
            "**/.pytest_cache",
            "**/cache/*.pkl",
            "**/logs/*.log",
            "**/*~",
            "**/.DS_Store"
        ]
        
        for pattern in cache_patterns:
            for path in self.project_root.glob(pattern):
                try:
                    if path.is_file():
                        path.unlink()
                        self.cleaned_files.append(str(path))
                    elif path.is_dir():
                        shutil.rmtree(path)
                        self.cleaned_files.append(str(path))
                except Exception as e:
                    self.errors.append(f"Erro ao remover {path}: {e}")
        
        print(f"   ✅ {len([f for f in self.cleaned_files if 'cache' in f.lower()])} arquivos de cache removidos")
    
    def clean_debug_files(self):
        """Remove arquivos de debug obsoletos"""
        print("🐛 Limpando arquivos de debug...")
        
        debug_files = [
            "debug_*.py",
            "test_*.py",
            "*_test.py",
            "quick_*.py",
            "simple_*.py",
            "direct_*.py",
            "final_*.py",
            "working_*.py",
            "minimal_*.py",
            "comprehensive_*.py",
            "check_*.py",
            "fix_*.py",
            "migrate_*.py",
            "reset_*.py",
            "inspect_*.py",
            "investigate_*.py",
            "find_*.py",
            "search_*.py",
            "rewrite_*.py",
            "*.sql",
            "migration_output.txt",
            "*.db-shm",
            "*.db-wal"
        ]
        
        for pattern in debug_files:
            for file_path in self.project_root.glob(pattern):
                if file_path.is_file() and not file_path.name.startswith("test_refactoring"):
                    try:
                        file_path.unlink()
                        self.cleaned_files.append(str(file_path))
                    except Exception as e:
                        self.errors.append(f"Erro ao remover {file_path}: {e}")
        
        print(f"   ✅ {len([f for f in self.cleaned_files if any(d in f for d in ['debug', 'test', 'fix', 'migrate'])])} arquivos de debug removidos")
    
    def organize_backup_files(self):
        """Organiza arquivos de backup"""
        print("📁 Organizando arquivos de backup...")
        
        backup_dir = self.project_root / "backups"
        backup_dir.mkdir(exist_ok=True)
        
        backup_patterns = [
            "*.bak",
            "*_backup_*.db",
            "*.backup"
        ]
        
        moved_count = 0
        for pattern in backup_patterns:
            for file_path in self.project_root.glob(pattern):
                if file_path.is_file() and file_path.parent != backup_dir:
                    try:
                        dest_path = backup_dir / file_path.name
                        if not dest_path.exists():
                            shutil.move(str(file_path), str(dest_path))
                            moved_count += 1
                            self.organized_dirs.append(f"Moved {file_path.name} to backups/")
                    except Exception as e:
                        self.errors.append(f"Erro ao mover {file_path}: {e}")
        
        print(f"   ✅ {moved_count} arquivos de backup organizados")
    
    def organize_logs(self):
        """Organiza arquivos de log"""
        print("📋 Organizando arquivos de log...")
        
        logs_dir = self.project_root / "logs"
        if not logs_dir.exists():
            logs_dir.mkdir()
            print("   📁 Diretório 'logs' criado")
        
        # Verificar se já existem logs organizados
        existing_logs = list(logs_dir.glob("*.log"))
        if existing_logs:
            print(f"   ✅ {len(existing_logs)} arquivos de log já organizados")
        else:
            print("   ℹ️  Nenhum arquivo de log encontrado para organizar")
    
    def clean_documentation_redundancy(self):
        """Identifica e organiza documentação redundante"""
        print("📚 Verificando documentação...")
        
        doc_files = list(self.project_root.glob("*.md"))
        if doc_files:
            print(f"   📄 {len(doc_files)} arquivos de documentação encontrados")
            
            # Sugerir organização de docs se há muitos arquivos
            if len(doc_files) > 10:
                docs_dir = self.project_root / "docs"
                if not docs_dir.exists():
                    docs_dir.mkdir()
                    print("   📁 Diretório 'docs' criado para organização futura")
        
        print("   ✅ Documentação verificada")
    
    def verify_code_structure(self):
        """Verifica estrutura do código"""
        print("🔍 Verificando estrutura do código...")
        
        # Verificar diretórios essenciais
        essential_dirs = ["pages", "utils", "security", "componentes"]
        missing_dirs = []
        
        for dir_name in essential_dirs:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                missing_dirs.append(dir_name)
            elif not (dir_path / "__init__.py").exists() and dir_name != "pages":
                # Criar __init__.py se não existir (exceto para pages que é do Streamlit)
                try:
                    (dir_path / "__init__.py").touch()
                    print(f"   📝 Criado __init__.py em {dir_name}/")
                except Exception as e:
                    self.errors.append(f"Erro ao criar __init__.py em {dir_name}: {e}")
        
        if missing_dirs:
            print(f"   ⚠️  Diretórios ausentes: {', '.join(missing_dirs)}")
        else:
            print("   ✅ Estrutura de diretórios correta")
    
    def create_gitignore(self):
        """Cria ou atualiza .gitignore"""
        print("📝 Verificando .gitignore...")
        
        gitignore_path = self.project_root / ".gitignore"
        gitignore_content = """# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# PyInstaller
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
.hypothesis/
.pytest_cache/

# Translations
*.mo
*.pot

# Django stuff:
*.log
local_settings.py
db.sqlite3

# Flask stuff:
instance/
.webassets-cache

# Scrapy stuff:
.scrapy

# Sphinx documentation
docs/_build/

# PyBuilder
target/

# Jupyter Notebook
.ipynb_checkpoints

# pyenv
.python-version

# celery beat schedule file
celerybeat-schedule

# SageMath parsed files
*.sage.py

# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Spyder project settings
.spyderproject
.spyproject

# Rope project settings
.ropeproject

# mkdocs documentation
/site

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# Streamlit
.streamlit/

# Project specific
cache/
logs/
profile_pics/
backups/
*.db-shm
*.db-wal
.session_key
.encryption_key

# Debug files
debug_*.py
test_*.py
*_test.py
quick_*.py
simple_*.py
direct_*.py
final_*.py
working_*.py
minimal_*.py
comprehensive_*.py
check_*.py
fix_*.py
migrate_*.py
reset_*.py
inspect_*.py
investigate_*.py
find_*.py
search_*.py
rewrite_*.py
migration_output.txt
"""
        
        if not gitignore_path.exists():
            try:
                gitignore_path.write_text(gitignore_content, encoding='utf-8')
                print("   ✅ .gitignore criado")
            except Exception as e:
                self.errors.append(f"Erro ao criar .gitignore: {e}")
        else:
            print("   ✅ .gitignore já existe")
    
    def generate_clean_report(self):
        """Gera relatório de limpeza"""
        print("\n" + "="*60)
        print("📊 RELATÓRIO DE LIMPEZA - 4º PRINCÍPIO: PROJETO LIMPO")
        print("="*60)
        
        # Estatísticas
        total_cleaned = len(self.cleaned_files)
        total_organized = len(self.organized_dirs)
        total_errors = len(self.errors)
        
        print(f"🗑️  Arquivos removidos: {total_cleaned}")
        print(f"📁 Itens organizados: {total_organized}")
        print(f"❌ Erros encontrados: {total_errors}")
        
        # Detalhes dos arquivos limpos (primeiros 10)
        if self.cleaned_files:
            print(f"\n📋 Alguns arquivos removidos:")
            for file_path in self.cleaned_files[:10]:
                relative_path = os.path.relpath(file_path, self.project_root)
                print(f"   - {relative_path}")
            if len(self.cleaned_files) > 10:
                print(f"   ... e mais {len(self.cleaned_files) - 10} arquivos")
        
        # Organização realizada
        if self.organized_dirs:
            print(f"\n📁 Organização realizada:")
            for item in self.organized_dirs:
                print(f"   - {item}")
        
        # Erros (se houver)
        if self.errors:
            print(f"\n⚠️  Erros encontrados:")
            for error in self.errors[:5]:  # Mostrar apenas os primeiros 5
                print(f"   - {error}")
            if len(self.errors) > 5:
                print(f"   ... e mais {len(self.errors) - 5} erros")
        
        # Status final
        print(f"\n✅ LIMPEZA CONCLUÍDA - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print("🧹 Projeto organizado seguindo o 4º Princípio: PROJETO LIMPO")
        
        # Recomendações
        print(f"\n💡 RECOMENDAÇÕES:")
        print("   - Execute este script periodicamente para manter o projeto limpo")
        print("   - Evite criar arquivos de debug no diretório raiz")
        print("   - Use o diretório 'scripts/' para utilitários")
        print("   - Mantenha a documentação atualizada")
        
        return {
            'cleaned_files': total_cleaned,
            'organized_items': total_organized,
            'errors': total_errors,
            'success': total_errors == 0
        }
    
    def run_full_cleanup(self):
        """Executa limpeza completa do projeto"""
        print("🧹 INICIANDO LIMPEZA DO PROJETO RICHNESS")
        print("Aplicando 4º Princípio: PROJETO LIMPO")
        print("-" * 50)
        
        try:
            self.clean_cache_files()
            self.clean_debug_files()
            self.organize_backup_files()
            self.organize_logs()
            self.clean_documentation_redundancy()
            self.verify_code_structure()
            self.create_gitignore()
            
            return self.generate_clean_report()
            
        except Exception as e:
            print(f"❌ Erro durante limpeza: {e}")
            return {'success': False, 'error': str(e)}

def main():
    """Função principal"""
    try:
        # Detectar diretório do projeto
        if len(sys.argv) > 1:
            project_path = sys.argv[1]
        else:
            # Usar diretório pai do script (assumindo que está em scripts/)
            script_dir = Path(__file__).parent
            project_path = script_dir.parent
        
        print(f"📁 Diretório do projeto: {project_path}")
        
        # Executar limpeza
        cleaner = ProjectCleaner(project_path)
        result = cleaner.run_full_cleanup()
        
        # Código de saída
        if result.get('success', False):
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n❌ Limpeza interrompida pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erro fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
