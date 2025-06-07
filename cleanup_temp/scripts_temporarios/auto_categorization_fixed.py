import os
import streamlit as st
from typing import Dict, List, Any
from database import get_uncategorized_transactions, save_ai_categorization, update_transaction_category
from utils.pluggy_connector import PluggyConnector


class AutoCategorization:
    """
    Sistema de categorização automática que roda no login
    """
    
    def __init__(self):
        self.skip_ai_processing = os.getenv('SKIP_LLM_PROCESSING', 'false').lower() == 'true'
        self.batch_size = 50  # Processar até 50 transações por vez
        
    def is_ai_available(self) -> bool:
        """
        Verifica se a IA está disponível e configurada
        """
        if self.skip_ai_processing:
            return False
            
        try:
            connector = PluggyConnector()
            return connector._init_llm() is not None
        except Exception:
            return False
    
    def categorize_transactions_on_login(self, usuario_id: int) -> Dict[str, Any]:
        """
        Executa categorização automática no login para transações não categorizadas
        """
        result = {
            'success': False,
            'ai_available': False,
            'processed_count': 0,
            'fallback_count': 0,
            'error_count': 0,
            'message': '',
            'details': []
        }
        
        try:
            # Verificar se IA está disponível
            ai_available = self.is_ai_available()
            result['ai_available'] = ai_available
            
            # Buscar transações não categorizadas
            uncategorized = get_uncategorized_transactions(usuario_id, self.batch_size)
            
            total_uncategorized = (
                len(uncategorized['extratos']) + 
                len(uncategorized['cartoes']) + 
                len(uncategorized['economias'])
            )
            
            if total_uncategorized == 0:
                result['success'] = True
                result['message'] = "Todas as transações já estão categorizadas"
                return result
            
            # Processar cada tipo de transação
            if ai_available:
                # Usar IA para categorização
                processed_count = self._process_with_ai(usuario_id, uncategorized, result)
                result['processed_count'] = processed_count
            else:
                # Usar categorização de fallback
                fallback_count = self._process_with_fallback(usuario_id, uncategorized, result)
                result['fallback_count'] = fallback_count
            
            result['success'] = True
            
            if ai_available:
                result['message'] = f"✨ IA processou {result['processed_count']} novas transações"
            else:
                result['message'] = f"📋 Categorização automática aplicada a {result['fallback_count']} transações"
                
        except Exception as e:
            result['error_count'] += 1
            result['message'] = f"Erro na categorização automática: {str(e)}"
            print(f"Erro na categorização automática: {e}")
        
        return result
    
    def _process_with_ai(self, usuario_id: int, uncategorized: Dict, result: Dict) -> int:
        """
        Processa transações usando IA
        """
        processed_count = 0
        
        try:
            connector = PluggyConnector()
            
            # Preparar dados para a IA
            all_transactions = []
            
            # Adicionar extratos
            for extrato in uncategorized['extratos']:
                all_transactions.append({
                    'type': 'extrato',
                    'id': extrato['id'],
                    'data': extrato['data'],
                    'valor': extrato['valor'],
                    'tipo': extrato['tipo'],
                    'descricao': extrato['descricao'],
                    'categoria_atual': extrato['categoria']
                })
            
            # Adicionar cartões
            for cartao in uncategorized['cartoes']:
                all_transactions.append({
                    'type': 'cartao',
                    'id': cartao['id'],
                    'data': cartao['data'],
                    'valor': cartao['valor'],
                    'tipo': cartao['tipo'],
                    'descricao': cartao['descricao'],
                    'categoria_atual': cartao['categoria'],
                    'cartao_nome': cartao.get('cartao_nome', '')
                })
            
            # Adicionar economias
            for economia in uncategorized['economias']:
                all_transactions.append({
                    'type': 'economia',
                    'id': economia['id'],
                    'data': economia['data'],
                    'valor': economia['valor'],
                    'tipo': economia['tipo'],
                    'descricao': economia['descricao'],
                    'categoria_atual': economia['categoria']
                })
            
            # Processar em lotes menores para IA
            batch_size = 10
            for i in range(0, len(all_transactions), batch_size):
                batch = all_transactions[i:i + batch_size]
                
                try:
                    # Converter batch para DataFrame para usar o método do PluggyConnector
                    import pandas as pd
                    batch_df = pd.DataFrame(batch)
                    
                    # Renomear colunas para compatibilidade
                    if 'descricao' in batch_df.columns:
                        batch_df = batch_df.rename(columns={'descricao': 'Descrição'})
                    if 'valor' in batch_df.columns:
                        batch_df = batch_df.rename(columns={'valor': 'Valor'})
                    if 'tipo' in batch_df.columns:
                        batch_df = batch_df.rename(columns={'tipo': 'Tipo'})
                    
                    # Categorizar lote com IA
                    categorized_df = connector.categorizar_transacoes_com_llm(batch_df)
                    
                    if not categorized_df.empty and 'Categoria' in categorized_df.columns:
                        for j, (_, row) in enumerate(categorized_df.iterrows()):
                            if j < len(batch):
                                transaction = batch[j]
                                new_category = row['Categoria']
                                
                                # Salvar categorização da IA
                                save_ai_categorization(
                                    usuario_id=usuario_id,
                                    transaction_type=transaction['type'],
                                    transaction_id=transaction['id'],
                                    original_description=transaction['descricao'],
                                    original_category=transaction['categoria_atual'],
                                    ai_category=new_category,
                                    ai_confidence=0.8
                                )
                                
                                # Atualizar categoria na tabela original
                                update_transaction_category(
                                    transaction['type'], 
                                    transaction['id'], 
                                    new_category
                                )
                                
                                processed_count += 1
                                
                                result['details'].append({
                                    'type': transaction['type'],
                                    'id': transaction['id'],
                                    'descricao': transaction['descricao'],
                                    'categoria_original': transaction['categoria_atual'],
                                    'categoria_nova': new_category
                                })
                
                except Exception as e:
                    print(f"Erro ao processar lote com IA: {e}")
                    result['error_count'] += 1
        
        except Exception as e:
            print(f"Erro no processamento com IA: {e}")
            result['error_count'] += 1
        
        return processed_count
    
    def _extract_specific_name(self, descricao: str, base_category: str) -> str:
        """Extrai nome específico da descrição"""
        try:
            # Limpar e extrair partes relevantes
            words = descricao.replace('*', '').split()
            if len(words) >= 2:
                # Pegar as primeiras palavras relevantes
                relevant_words = [w for w in words if len(w) > 2 and not w.isdigit()][:3]
                if relevant_words:
                    specific_name = ' '.join(relevant_words[:2])
                    return f"{base_category} {specific_name}"
        except:
            pass
        return base_category
    
    def _extract_transfer_name(self, descricao: str, transfer_type: str) -> str:
        """Extrai nome específico para transferências"""
        try:
            descricao_clean = descricao.replace('*', '').upper()
            words = descricao_clean.split()
            
            # Procurar por nomes de pessoas ou instituições
            for i, word in enumerate(words):
                if word in ['PARA', 'P/', 'DESTINATARIO', 'FAVORECIDO']:
                    if i + 1 < len(words):
                        name_parts = words[i+1:i+3]  # Pegar até 2 palavras do nome
                        name = ' '.join(name_parts)
                        return f"{transfer_type} {name}"
            
            # Se não encontrou indicadores, pegar palavras que parecem nomes
            name_candidates = [w for w in words if len(w) > 3 and w not in ['TRANSFERENCIA', 'PIX', 'TED', 'DOC']]
            if name_candidates:
                name = ' '.join(name_candidates[:2])
                return f"{transfer_type} {name}"
                
        except:
            pass
        return f"{transfer_type} Bancária"
    
    def _extract_establishment_name(self, descricao: str, category: str) -> str:
        """Extrai nome específico do estabelecimento"""
        try:
            descricao_clean = descricao.replace('*', '').strip()
            # Pegar as primeiras palavras da descrição que formam o nome do estabelecimento
            words = descricao_clean.split()[:3]
            establishment_name = ' '.join(words)
            return establishment_name if len(establishment_name) > len(category) else category
        except:
            pass
        return category
    
    def _extract_generic_category(self, descricao: str) -> str:
        """Extrai categoria genérica mas mais específica que 'Outros'"""
        try:
            descricao_clean = descricao.replace('*', '').strip()
            words = descricao_clean.split()
            
            # Se tem poucas palavras, usar a descrição como categoria
            if len(words) <= 3:
                return descricao_clean
            
            # Caso contrário, pegar as primeiras palavras mais relevantes
            relevant_words = [w for w in words[:3] if len(w) > 2]
            if relevant_words:
                return ' '.join(relevant_words[:2])
                
        except:
            pass
        return 'Transação Diversa'
    
    def _process_with_fallback(self, usuario_id: int, uncategorized: Dict, result: Dict) -> int:
        """
        Processa transações usando categorização de fallback baseada em regras
        """
        fallback_count = 0
        
        try:
            # Regras de categorização melhoradas para categorias mais específicas
            categorization_rules = {
                'Supermercado': ['mercado', 'supermercado', 'atacadao', 'carrefour', 'extra', 'walmart', 'big', 'gbarbosa'],
                'Padaria': ['padaria', 'panificadora', 'confeitaria'],
                'Restaurante': ['restaurante', 'lanchonete', 'pizzaria', 'hamburgueria', 'mcdonald', 'burger king', 'subway'],
                'Delivery': ['ifood', 'uber eats', 'rappi', 'delivery', '99food'],
                'Posto Combustivel': ['posto', 'combustivel', 'gasolina', 'etanol', 'shell', 'ipiranga', 'petrobras', 'br'],
                'Transporte App': ['uber', '99', 'cabify', 'taxi'],
                'Transporte Publico': ['onibus', 'metro', 'trem', 'bus', 'bilhete unico'],
                'Farmacia': ['farmacia', 'drogaria', 'droga raia', 'ultrafarma', 'drogasil', 'pague menos'],
                'Hospital': ['hospital', 'clinica', 'laboratorio', 'exame'],
                'Medico': ['medico', 'consulta', 'dentista', 'oftalmologista'],
                'Escola': ['escola', 'colegio', 'faculdade', 'universidade'],
                'Curso': ['curso', 'treinamento', 'aula'],
                'Material Escolar': ['livraria', 'papelaria', 'material escolar'],
                'Cinema': ['cinema', 'ingresso', 'filme'],
                'Bar': ['bar', 'pub', 'boteco'],
                'Viagem': ['hotel', 'pousada', 'hospedagem', 'passagem', 'viagem'],
                'Conta Agua': ['saae', 'embasa', 'copasa', 'sanepar', 'agua'],
                'Conta Luz': ['coelba', 'cemig', 'cpfl', 'light', 'eletrobras', 'energia'],
                'Conta Gas': ['comgas', 'gas', 'botijao'],
                'Internet': ['vivo', 'claro', 'tim', 'oi', 'net', 'internet', 'telefone'],
                'Aluguel': ['aluguel', 'locacao', 'imovel'],
                'Condominio': ['condominio', 'administradora'],
                'Shopping': ['shopping', 'mall'],
                'Loja Roupas': ['c&a', 'riachuelo', 'renner', 'zara', 'roupa'],
                'Loja Eletronicos': ['magazine luiza', 'casas bahia', 'extra', 'eletronico', 'celular'],
                'PIX': ['pix'],
                'TED': ['ted'],
                'DOC': ['doc'],
                'Salario': ['salario', 'ordenado', 'vencimento'],
                'Freelance': ['freelance', 'autonomo', 'consultor'],
                'Rendimento': ['rendimento', 'juros', 'dividendo', 'aplicacao']
            }
            
            def categorize_by_description(descricao: str, valor: float) -> str:
                if not descricao:
                    return 'Sem Descrição'
                
                descricao_lower = descricao.lower()
                descricao_original = descricao.strip()
                
                # Verificar se é receita (valor positivo + palavras-chave)
                if valor > 0:
                    for keyword in categorization_rules['Salario'] + categorization_rules['Freelance'] + categorization_rules['Rendimento']:
                        if keyword in descricao_lower:
                            # Tentar extrair nome específico para receitas
                            if 'salario' in descricao_lower:
                                return self._extract_specific_name(descricao_original, 'Salário')
                            elif 'freelance' in descricao_lower or 'autonomo' in descricao_lower:
                                return self._extract_specific_name(descricao_original, 'Freelance')
                            else:
                                return self._extract_specific_name(descricao_original, 'Rendimento')
                
                # Categorização específica baseada em estabelecimentos conhecidos
                for categoria, keywords in categorization_rules.items():
                    for keyword in keywords:
                        if keyword in descricao_lower:
                            # Para transferências, extrair nome específico
                            if categoria in ['PIX', 'TED', 'DOC']:
                                return self._extract_transfer_name(descricao_original, categoria)
                            # Para estabelecimentos, extrair nome específico
                            elif categoria in ['Supermercado', 'Farmacia', 'Posto Combustivel', 'Restaurante']:
                                return self._extract_establishment_name(descricao_original, categoria)
                            else:
                                return categoria
                
                # Se não encontrou categoria específica, tentar extrair informação útil da descrição
                return self._extract_generic_category(descricao_original)
            
            # Processar extratos
            for extrato in uncategorized['extratos']:
                new_category = categorize_by_description(extrato['descricao'], extrato['valor'])
                
                # Salvar categorização de fallback
                save_ai_categorization(
                    usuario_id=usuario_id,
                    transaction_type='extrato',
                    transaction_id=extrato['id'],
                    original_description=extrato['descricao'],
                    original_category=extrato['categoria'],
                    ai_category=new_category,
                    ai_confidence=0.6  # Menor confiança para fallback
                )
                
                # Atualizar categoria na tabela original
                update_transaction_category('extrato', extrato['id'], new_category)
                fallback_count += 1
            
            # Processar cartões
            for cartao in uncategorized['cartoes']:
                new_category = categorize_by_description(cartao['descricao'], cartao['valor'])
                
                save_ai_categorization(
                    usuario_id=usuario_id,
                    transaction_type='cartao',
                    transaction_id=cartao['id'],
                    original_description=cartao['descricao'],
                    original_category=cartao['categoria'],
                    ai_category=new_category,
                    ai_confidence=0.6
                )
                
                update_transaction_category('cartao', cartao['id'], new_category)
                fallback_count += 1
            
            # Processar economias
            for economia in uncategorized['economias']:
                new_category = categorize_by_description(economia['descricao'], economia['valor'])
                
                save_ai_categorization(
                    usuario_id=usuario_id,
                    transaction_type='economia',
                    transaction_id=economia['id'],
                    original_description=economia['descricao'],
                    original_category=economia['categoria'],
                    ai_category=new_category,
                    ai_confidence=0.6
                )
                
                update_transaction_category('economia', economia['id'], new_category)
                fallback_count += 1
        
        except Exception as e:
            print(f"Erro no processamento de fallback: {e}")
            result['error_count'] += 1
        
        return fallback_count


def run_auto_categorization_on_login(usuario_id: int) -> Dict[str, Any]:
    """
    Função principal para executar categorização automática no login
    """
    auto_cat = AutoCategorization()
    return auto_cat.categorize_transactions_on_login(usuario_id)
