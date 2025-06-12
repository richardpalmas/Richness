"""
Classe de manutenção para limpeza do projeto.
Implementa o 4º princípio dos fundamentos: manter o projeto sempre limpo.
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict
import sqlite3

class Maintenance:
    """
    Classe responsável pela manutenção e limpeza do projeto.
    Remove arquivos desnecessários, métodos obsoletos e componentes do Pluggy.
    """
    
    def __init__(self):
        self.project_root = Path(".")
        self.removed_files = []
        self.cleaned_methods = []
        self.database_changes = []
        
    def remove_pluggy_files(self) -> Dict[str, List[str]]:
        """Remove todos os arquivos relacionados ao Pluggy."""
        removed = {
            'files': [],
            'cache': [],
            'configs': []
        }
        
        # Arquivos específicos do Pluggy
        pluggy_files = [
            "utils/pluggy_connector.py",
            "pages/Cadastro_Pluggy.py"
        ]
        
        for file_path in pluggy_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                try:
                    full_path.unlink()
                    removed['files'].append(str(file_path))
                    print(f"✅ Removido: {file_path}")
                except Exception as e:
                    print(f"❌ Erro ao remover {file_path}: {e}")
        
        # Cache do Pluggy
        cache_files = [
            "cache/cache.pkl",
            "cache/categorias_cache.pkl", 
            "cache/descricoes_cache.pkl"
        ]
        
        for cache_file in cache_files:
            full_path = self.project_root / cache_file
            if full_path.exists():
                try:
                    full_path.unlink()
                    removed['cache'].append(str(cache_file))
                    print(f"✅ Cache removido: {cache_file}")
                except Exception as e:
                    print(f"❌ Erro ao remover cache {cache_file}: {e}")
        
        self.removed_files.extend(removed['files'])
        return removed
    
    def clean_database_pluggy_tables(self) -> List[str]:
        """Remove tabelas e dados relacionados ao Pluggy do banco."""
        changes = []
        conn = None
        
        try:
            conn = sqlite3.connect('richness.db')
            cur = conn.cursor()
            
            # Verificar se a tabela pluggy_items existe
            cur.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='pluggy_items'
            """)
            
            if cur.fetchone():
                # Remover dados da tabela
                cur.execute("DELETE FROM pluggy_items")
                changes.append("Dados da tabela pluggy_items removidos")
                
                # Remover a tabela
                cur.execute("DROP TABLE pluggy_items")
                changes.append("Tabela pluggy_items removida")
                
                # Remover índices relacionados
                indices = [
                    "idx_pluggy_items_usuario_id",
                    "idx_pluggy_items_item_id"
                ]
                
                for indice in indices:
                    try:
                        cur.execute(f"DROP INDEX IF EXISTS {indice}")
                        changes.append(f"Índice {indice} removido")
                    except:
                        pass
                
                conn.commit()
                print("✅ Limpeza do banco de dados concluída")
            else:
                changes.append("Tabela pluggy_items não encontrada (já removida)")
                
        except Exception as e:
            print(f"❌ Erro ao limpar banco de dados: {e}")
            changes.append(f"Erro: {e}")
        finally:
            if conn is not None:
                conn.close()
        
        self.database_changes = changes
        return changes
    
    def remove_pluggy_imports_and_references(self) -> Dict[str, List[str]]:
        """Remove imports e referências do Pluggy de outros arquivos."""
        cleaned = {
            'files_modified': [],
            'imports_removed': [],
            'references_removed': []
        }
        
        # Arquivos que podem ter referências ao Pluggy
        files_to_check = [
            "Home.py",
            "pages/Cartao.py",
            "pages/Minhas_Economias.py",
            "pages/Dicas_Financeiras_Com_IA.py",
            "utils/exception_handler.py"
        ]
        
        for file_path in files_to_check:
            full_path = self.project_root / file_path
            if full_path.exists():
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    original_content = content
                    
                    # Remover imports do PluggyConnector
                    if "from utils.pluggy_connector import PluggyConnector" in content:
                        content = content.replace("from utils.pluggy_connector import PluggyConnector\n", "")
                        cleaned['imports_removed'].append(f"{file_path}: import PluggyConnector")
                    
                    # Remover referências em comentários e código comentado
                    lines = content.split('\n')
                    new_lines = []
                    
                    for line in lines:
                        # Pular linhas que referenciam Pluggy
                        if ('pluggy' in line.lower() and 
                            ('def ' not in line or line.strip().startswith('#') or line.strip().startswith('//'))):
                            cleaned['references_removed'].append(f"{file_path}: {line.strip()}")
                            continue
                        new_lines.append(line)
                    
                    content = '\n'.join(new_lines)
                    
                    # Salvar se houve mudanças
                    if content != original_content:
                        with open(full_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        cleaned['files_modified'].append(str(file_path))
                        print(f"✅ Arquivo limpo: {file_path}")
                        
                except Exception as e:
                    print(f"❌ Erro ao limpar {file_path}: {e}")
        
        return cleaned
    
    def remove_debug_files(self) -> List[str]:
        """Remove arquivos de debug e teste temporários."""
        debug_patterns = [
            "**/*debug*",
            "**/*test*",
            "**/*.tmp",
            "**/*.temp",
            "**/*.bak",
            "**/*~",
            "**/debug.log",
            "**/test.log"
        ]
        
        removed = []
        
        for pattern in debug_patterns:
            for file_path in self.project_root.glob(pattern):
                if file_path.is_file() and not file_path.name.startswith('.'):
                    try:
                        file_path.unlink()
                        removed.append(str(file_path))
                        print(f"✅ Debug file removido: {file_path}")
                    except Exception as e:
                        print(f"❌ Erro ao remover {file_path}: {e}")
        
        return removed
    
    def clean_empty_directories(self) -> List[str]:
        """Remove diretórios vazios."""
        removed_dirs = []
        
        # Verificar diretórios que podem ficar vazios
        check_dirs = [
            "cache",
            "__pycache__",
            "temp",
            "tmp"
        ]
        
        for dir_name in check_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists() and dir_path.is_dir():
                try:
                    # Verificar se está vazio
                    if not any(dir_path.iterdir()):
                        shutil.rmtree(dir_path)
                        removed_dirs.append(str(dir_name))
                        print(f"✅ Diretório vazio removido: {dir_name}")
                except Exception as e:
                    print(f"❌ Erro ao remover diretório {dir_name}: {e}")
        
        return removed_dirs
    
    def run_full_cleanup(self) -> Dict:
        """Executa limpeza completa do projeto."""
        print("🧹 Iniciando limpeza completa do projeto...")
        print("=" * 50)
        
        results = {
            'pluggy_files': self.remove_pluggy_files(),
            'database_cleanup': self.clean_database_pluggy_tables(),
            'code_cleanup': self.remove_pluggy_imports_and_references(),
            'debug_cleanup': self.remove_debug_files(),
            'empty_dirs': self.clean_empty_directories()
        }
        
        print("=" * 50)
        print("✅ Limpeza completa finalizada!")
        print(f"📁 Arquivos removidos: {len(self.removed_files)}")
        print(f"🗄️ Mudanças no banco: {len(self.database_changes)}")
        
        return results
    
    def generate_cleanup_report(self, results: Dict) -> str:
        """Gera relatório detalhado da limpeza."""
        report = []
        report.append("# Relatório de Limpeza do Projeto")
        report.append(f"**Data:** {os.popen('date /T').read().strip()}")
        report.append("")
        
        # Arquivos Pluggy removidos
        if results['pluggy_files']['files']:
            report.append("## Arquivos Pluggy Removidos:")
            for file in results['pluggy_files']['files']:
                report.append(f"- {file}")
            report.append("")
        
        # Cache removido
        if results['pluggy_files']['cache']:
            report.append("## Cache Limpo:")
            for cache in results['pluggy_files']['cache']:
                report.append(f"- {cache}")
            report.append("")
        
        # Mudanças no banco
        if results['database_cleanup']:
            report.append("## Banco de Dados:")
            for change in results['database_cleanup']:
                report.append(f"- {change}")
            report.append("")
        
        # Arquivos modificados
        if results['code_cleanup']['files_modified']:
            report.append("## Arquivos Modificados:")
            for file in results['code_cleanup']['files_modified']:
                report.append(f"- {file}")
            report.append("")
        
        report.append("---")
        report.append("**Status:** Limpeza concluída com sucesso ✅")
        
        return "\n".join(report)
