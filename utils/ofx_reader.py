import os
import pandas as pd
import json
from datetime import datetime, date
from pathlib import Path
import xml.etree.ElementTree as ET
import re
from typing import List, Dict, Optional, Tuple
import streamlit as st

class OFXReader:
    """
    Classe para leitura e processamento de arquivos OFX.
    Substitui completamente o PluggyConnector seguindo os princípios de minimalismo e eficiência.
    """
    
    def __init__(self):
        self.extratos_dir = Path("extratos")
        self.faturas_dir = Path("faturas")
        self._cache = {}
        
    def _parse_ofx_file(self, file_path: Path) -> Dict:
        """
        Parse de arquivo OFX individual.
        Retorna dados estruturados das transações.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Tentar com encoding alternativo
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
        
        # Extrair dados básicos do cabeçalho
        transactions = []
        
        # Regex para extrair transações
        transaction_pattern = r'<STMTTRN>(.*?)</STMTTRN>'
        matches = re.findall(transaction_pattern, content, re.DOTALL)
        
        for match in matches:
            transaction = self._parse_transaction(match)
            if transaction:
                transactions.append(transaction)
        
        # Detectar tipo de conta (cartão ou conta corrente)
        account_type = "credit_card" if "<CREDITCARDMSGSRSV1>" in content else "checking"
        
        return {
            'transactions': transactions,
            'account_type': account_type,
            'file_path': str(file_path)
        }
    
    def _parse_transaction(self, transaction_xml: str) -> Optional[Dict]:
        """Parse de transação individual do XML."""
        try:
            # Extrair campos principais
            fields = {}
            
            # Tipo de transação
            type_match = re.search(r'<TRNTYPE>(.*?)</TRNTYPE>', transaction_xml)
            fields['tipo'] = type_match.group(1) if type_match else 'UNKNOWN'
            
            # Data
            date_match = re.search(r'<DTPOSTED>(.*?)</DTPOSTED>', transaction_xml)
            if date_match:
                date_str = date_match.group(1)
                # Converter formato de data OFX para datetime
                date_clean = re.sub(r'\[.*?\]', '', date_str)  # Remove timezone
                try:
                    fields['data'] = datetime.strptime(date_clean[:8], '%Y%m%d').date()
                except:
                    fields['data'] = date.today()
            else:
                fields['data'] = date.today()
            
            # Valor
            amount_match = re.search(r'<TRNAMT>(.*?)</TRNAMT>', transaction_xml)
            if amount_match:
                fields['valor'] = float(amount_match.group(1))
            else:
                return None
            
            # Descrição
            memo_match = re.search(r'<MEMO>(.*?)</MEMO>', transaction_xml)
            fields['descricao'] = memo_match.group(1) if memo_match else 'Sem descrição'
              # ID da transação
            id_match = re.search(r'<FITID>(.*?)</FITID>', transaction_xml)
            fields['id'] = id_match.group(1) if id_match else ''
            
            return fields
            
        except Exception as e:
            return None
    
    def buscar_extratos(self, dias: int = 365) -> pd.DataFrame:
        """
        Busca extratos de conta corrente dos arquivos OFX.
        Equivalente ao método do PluggyConnector.
        """
        cache_key = f"extratos_{dias}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        all_transactions = []
        
        if not self.extratos_dir.exists():
            st.warning("Pasta 'extratos' não encontrada. Certifique-se de que os arquivos OFX estão na pasta correta.")
            return pd.DataFrame()
        
        # Processar todos os arquivos OFX na pasta extratos
        for file_path in self.extratos_dir.glob("*.ofx"):
            try:
                data = self._parse_ofx_file(file_path)
                for transaction in data['transactions']:
                    # Filtrar por período se especificado
                    if dias > 0:
                        cutoff_date = date.today() - pd.Timedelta(days=dias)
                        if transaction['data'] < cutoff_date:
                            continue
                    
                    # Padronizar formato
                    transaction['origem'] = str(file_path.name)
                    transaction['categoria'] = self._categorizar_transacao(transaction['descricao'])
                    all_transactions.append(transaction)
                    
            except Exception as e:
                st.error(f"Erro ao processar arquivo {file_path}: {e}")
        
        # Converter para DataFrame
        df = pd.DataFrame(all_transactions)
        
        if not df.empty:
            # Ordenar por data
            df = df.sort_values('data', ascending=False)
            
            # Padronizar colunas
            df.columns = [col.title() for col in df.columns]
            df = df.rename(columns={
                'Data': 'Data',
                'Valor': 'Valor',
                'Descricao': 'Descrição',
                'Tipo': 'Tipo',
                'Categoria': 'Categoria',
                'Origem': 'Origem'
            })
        
        self._cache[cache_key] = df
        return df
    
    def buscar_cartoes(self, dias: int = 365) -> pd.DataFrame:
        """
        Busca faturas de cartão de crédito dos arquivos OFX.
        Equivalente ao método do PluggyConnector.
        """
        cache_key = f"cartoes_{dias}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        all_transactions = []
        
        if not self.faturas_dir.exists():
            st.warning("Pasta 'faturas' não encontrada. Certifique-se de que os arquivos OFX estão na pasta correta.")
            return pd.DataFrame()
        
        # Processar todos os arquivos OFX na pasta faturas
        for file_path in self.faturas_dir.glob("*.ofx"):
            try:
                data = self._parse_ofx_file(file_path)
                for transaction in data['transactions']:
                    # Filtrar por período se especificado
                    if dias > 0:
                        cutoff_date = date.today() - pd.Timedelta(days=dias)
                        if transaction['data'] < cutoff_date:
                            continue
                    
                    # Padronizar formato
                    transaction['origem'] = str(file_path.name)
                    transaction['categoria'] = self._categorizar_transacao(transaction['descricao'])
                    all_transactions.append(transaction)
                    
            except Exception as e:
                st.error(f"Erro ao processar arquivo {file_path}: {e}")
        
        # Converter para DataFrame
        df = pd.DataFrame(all_transactions)
        
        if not df.empty:
            # Ordenar por data
            df = df.sort_values('data', ascending=False)
            
            # Padronizar colunas
            df.columns = [col.title() for col in df.columns]
            df = df.rename(columns={
                'Data': 'Data',
                'Valor': 'Valor',
                'Descricao': 'Descrição',
                'Tipo': 'Tipo',
                'Categoria': 'Categoria',
                'Origem': 'Origem'
            })
        
        self._cache[cache_key] = df
        return df
    
    def _categorizar_transacao(self, descricao: str) -> str:
        """
        Categorização híbrida: primeiro verifica categorizações personalizadas do usuário,
        depois aplica regras baseadas em palavras-chave.
        """
        # 1. Verificar categorizações personalizadas do usuário
        descricao_normalizada = descricao.lower().strip()
        cache_file = "cache_categorias_usuario.json"
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_usuario = json.load(f)
                
                if descricao_normalizada in cache_usuario:
                    return cache_usuario[descricao_normalizada]
            except:
                pass  # Em caso de erro, continuar com regras padrão
        
        # 2. Aplicar regras baseadas em palavras-chave (fallback)
        descricao = descricao.lower()
        
        # Categorias baseadas em palavras-chave
        categorias = {
            'Alimentação': ['restaurante', 'lanchonete', 'supermercado', 'mercado', 'food', 'comida', 'ifood', 'uber eats', 'delivery', 'padaria', 'acougue'],
            'Transporte': ['uber', 'taxi', 'combustivel', 'posto', 'gas', 'transporte', 'estacionamento', 'pedagio', 'onibus', 'metro'],
            'Saúde': ['farmacia', 'hospital', 'clinica', 'medico', 'plano', 'saude', 'laboratorio', 'exame', 'consulta'],
            'Educação': ['escola', 'faculdade', 'curso', 'livro', 'educacao', 'universidade', 'colegio', 'material escolar'],
            'Lazer': ['cinema', 'teatro', 'netflix', 'spotify', 'youtube', 'steam', 'playstation', 'xbox', 'streaming', 'entretenimento'],
            'Casa e Utilidades': ['aluguel', 'condominio', 'luz', 'agua', 'gas', 'internet', 'telefone', 'limpeza', 'manutencao'],
            'Vestuário': ['roupa', 'calcado', 'vestuario', 'moda', 'sapato', 'camisa', 'calca'],
            'Banco/Taxas': ['ITAU', 'LUIZA CRED', 'Pagamento de fatura', 'taxa', 'juros', 'tarifa', 'anuidade'],
            'Transferências': ['transferencia', 'pix', 'ted', 'doc', 'saque', 'deposito'],
            'Salário': ['salario', 'pagamento', 'remuneracao', 'ordenado'],
            'Investimentos': ['investimento', 'aplicacao', 'cdb', 'tesouro', 'acao', 'fundo'],
            'Compras Online': ['amazon', 'mercado livre', 'shopee', 'aliexpress', 'magazine luiza', 'casas bahia']
        }
        
        for categoria, palavras in categorias.items():
            if any(palavra in descricao for palavra in palavras):
                return categoria
        
        return 'Outros'
    
    def limpar_cache(self):
        """Limpa o cache interno."""
        self._cache.clear()
    
    def get_available_files(self) -> Dict[str, List[str]]:
        """Retorna lista de arquivos disponíveis."""
        return {
            'extratos': [f.name for f in self.extratos_dir.glob("*.ofx")] if self.extratos_dir.exists() else [],
            'faturas': [f.name for f in self.faturas_dir.glob("*.ofx")] if self.faturas_dir.exists() else []
        }
    
    def get_resumo_arquivos(self) -> Dict:
        """Retorna resumo dos arquivos disponíveis."""
        files = self.get_available_files()
        
        total_extratos = len(files['extratos'])
        total_faturas = len(files['faturas'])
        
        # Extrair datas dos nomes dos arquivos para mostrar período
        datas_extratos = []
        datas_faturas = []
        
        for arquivo in files['extratos']:
            # Padrão: NU_45043667_01JAN2025_31JAN2025.ofx
            match = re.search(r'(\d{2}\w{3}\d{4})', arquivo)
            if match:
                try:
                    data = datetime.strptime(match.group(1), '%d%b%Y').date()
                    datas_extratos.append(data)
                except:
                    pass
        
        for arquivo in files['faturas']:
            # Padrão: Nubank_2025-01-03.ofx
            match = re.search(r'(\d{4}-\d{2}-\d{2})', arquivo)
            if match:
                try:
                    data = datetime.strptime(match.group(1), '%Y-%m-%d').date()
                    datas_faturas.append(data)
                except:
                    pass
        
        return {
            'total_extratos': total_extratos,
            'total_faturas': total_faturas,
            'periodo_extratos': {
                'inicio': min(datas_extratos) if datas_extratos else None,
                'fim': max(datas_extratos) if datas_extratos else None
            },
            'periodo_faturas': {
                'inicio': min(datas_faturas) if datas_faturas else None,
                'fim': max(datas_faturas) if datas_faturas else None
            }
        }