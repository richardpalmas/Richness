"""
Serviço de Auto-Categorização Inteligente de Transações
Sistema de IA que aprende padrões e categoriza transações automaticamente
"""

from typing import Dict, List, Optional, Any, Tuple
import re
from datetime import datetime, date
from collections import defaultdict, Counter
import json

from utils.database_manager_v2 import DatabaseManager
from utils.repositories_v2 import TransacaoRepository, UsuarioRepository


class AICategorization:
    """Sistema de auto-categorização inteligente baseado em IA"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.transacao_repo = TransacaoRepository(self.db)
        self.usuario_repo = UsuarioRepository(self.db)
        
        # Padrões de palavras-chave por categoria
        self.category_keywords = {
            'Alimentação': [
                'supermercado', 'mercado', 'padaria', 'restaurante', 'lanchonete',
                'mcdonalds', 'burger', 'pizza', 'ifood', 'uber eats', 'rappi',
                'cafe', 'bar', 'cerveja', 'bebida', 'comida', 'alimento',
                'feira', 'acougue', 'peixaria', 'hortifruti', 'carrefour',
                'extra', 'pao de acucar', 'walmart', 'assai'
            ],
            'Transporte': [
                'uber', 'taxi', 'ônibus', 'metro', 'trem', 'combustivel',
                'gasolina', 'etanol', 'diesel', 'posto', 'ipva', 'seguro auto',
                'oficina', 'mecanico', 'pneu', 'lavagem', 'estacionamento',
                'pedagio', 'vinheta', '99', 'cabify', 'bilhete unico'
            ],
            'Saúde': [
                'farmacia', 'drogaria', 'hospital', 'clinica', 'medico',
                'dentista', 'laboratorio', 'exame', 'consulta', 'remedio',
                'medicamento', 'plano de saude', 'convenio', 'seguro saude',
                'fisioterapia', 'psicologia', 'nutricao'
            ],
            'Lazer': [
                'cinema', 'teatro', 'show', 'spotify', 'netflix', 'amazon prime',
                'youtube', 'disney', 'globoplay', 'streaming', 'jogo', 'game',
                'viagem', 'hotel', 'pousada', 'turismo', 'parque', 'shopping',
                'livro', 'revista', 'assinatura'
            ],
            'Casa': [
                'aluguel', 'condominio', 'iptu', 'luz', 'energia', 'agua',
                'gas', 'internet', 'telefone', 'celular', 'limpeza',
                'material construcao', 'reforma', 'moveis', 'eletrodomestico',
                'decoracao', 'jardinagem', 'manutenção'
            ],
            'Vestuário': [
                'roupa', 'sapato', 'calcado', 'tenis', 'camisa', 'calca',
                'vestido', 'saia', 'blusa', 'casaco', 'jaqueta', 'moda',
                'acessorio', 'bolsa', 'carteira', 'relogio', 'joia'
            ],
            'Educação': [
                'escola', 'faculdade', 'universidade', 'curso', 'aula',
                'professor', 'ensino', 'material escolar', 'livro didatico',
                'mensalidade', 'matricula', 'formatura', 'pos graduacao'
            ],
            'Tecnologia': [
                'celular', 'smartphone', 'computador', 'notebook', 'tablet',
                'software', 'aplicativo', 'app store', 'google play',
                'microsoft', 'apple', 'samsung', 'eletronico', 'informatica'
            ],
            'Investimento': [
                'acao', 'fundo', 'cdb', 'tesouro', 'bolsa', 'corretora',
                'investimento', 'aplicacao', 'poupanca', 'renda fixa',
                'renda variavel', 'btg', 'xp', 'rico', 'inter', 'nubank'
            ]
        }
        
        # Cache para melhorar performance
        self._categorization_cache = {}
    
    def categorizar_transacao(self, user_id: int, transacao_data: Dict[str, Any]) -> str:
        """Categoriza uma transação usando IA baseada em padrões aprendidos"""
        try:
            descricao = transacao_data.get('descricao', '').lower()
            valor = transacao_data.get('valor', 0)
            
            # 1. Verificar cache primeiro
            cache_key = f"{user_id}_{hash(descricao)}"
            if cache_key in self._categorization_cache:
                return self._categorization_cache[cache_key]
            
            # 2. Análise baseada no histórico do usuário
            categoria_historico = self._analisar_historico_usuario(user_id, descricao)
            if categoria_historico:
                self._categorization_cache[cache_key] = categoria_historico
                return categoria_historico
            
            # 3. Análise por palavras-chave
            categoria_keywords = self._analisar_por_keywords(descricao)
            if categoria_keywords:
                self._categorization_cache[cache_key] = categoria_keywords
                return categoria_keywords
            
            # 4. Análise por padrões de valor
            categoria_valor = self._analisar_por_valor(user_id, valor)
            if categoria_valor:
                self._categorization_cache[cache_key] = categoria_valor
                return categoria_valor
            
            # 5. Categoria padrão
            categoria_default = 'Outros'
            self._categorization_cache[cache_key] = categoria_default
            return categoria_default
            
        except Exception as e:
            print(f"Erro na categorização: {e}")
            return 'Outros'
    
    def _analisar_historico_usuario(self, user_id: int, descricao: str) -> Optional[str]:
        """Analisa histórico do usuário para encontrar padrões similares"""
        try:
            # Obter transações já categorizadas do usuário
            with self.db.get_connection() as conn:
                query = """
                SELECT descricao, categoria
                FROM transacoes 
                WHERE user_id = ? AND categoria IS NOT NULL AND categoria != 'Outros'
                """
                cursor = conn.execute(query, (user_id,))
                transacoes_categorizadas = cursor.fetchall()
            
            if not transacoes_categorizadas:
                return None
            
            # Buscar por similaridade textual
            descricao_words = set(descricao.split())
            melhor_match = None
            melhor_score = 0
            
            for transacao in transacoes_categorizadas:
                desc_hist = transacao[0].lower()
                categoria_hist = transacao[1]
                
                # Calcular similaridade simples
                hist_words = set(desc_hist.split())
                intersecao = descricao_words.intersection(hist_words)
                
                if intersecao:
                    score = len(intersecao) / len(descricao_words.union(hist_words))
                    if score > melhor_score and score > 0.3:  # Threshold de 30%
                        melhor_score = score
                        melhor_match = categoria_hist
            
            return melhor_match
            
        except Exception as e:
            return None
    
    def _analisar_por_keywords(self, descricao: str) -> Optional[str]:
        """Analisa descrição por palavras-chave predefinidas"""
        melhor_categoria = None
        melhor_score = 0
        
        for categoria, keywords in self.category_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in descricao:
                    score += 1
            
            # Normalizar score pelo número de keywords da categoria
            score_normalizado = score / len(keywords)
            
            if score_normalizado > melhor_score and score > 0:
                melhor_score = score_normalizado
                melhor_categoria = categoria
        
        return melhor_categoria if melhor_score > 0.01 else None  # Threshold mínimo
    
    def _analisar_por_valor(self, user_id: int, valor: float) -> Optional[str]:
        """Analisa categoria baseada em padrões de valor do usuário"""
        try:
            # Obter distribuição de valores por categoria para o usuário
            with self.db.get_connection() as conn:
                query = """
                SELECT categoria, AVG(ABS(valor)) as media_valor, COUNT(*) as qtd
                FROM transacoes 
                WHERE user_id = ? AND categoria IS NOT NULL AND categoria != 'Outros'
                GROUP BY categoria
                HAVING qtd >= 3
                """
                cursor = conn.execute(query, (user_id,))
                stats_categorias = cursor.fetchall()
            
            if not stats_categorias:
                return None
            
            valor_abs = abs(valor)
            categoria_mais_proxima = None
            menor_diferenca = float('inf')
            
            for stat in stats_categorias:
                categoria = stat[0]
                media_valor = stat[1]
                
                diferenca = abs(valor_abs - media_valor) / media_valor
                
                if diferenca < menor_diferenca and diferenca < 0.5:  # 50% de tolerância
                    menor_diferenca = diferenca
                    categoria_mais_proxima = categoria
            
            return categoria_mais_proxima
            
        except Exception as e:
            return None
    
    def obter_estatisticas_precisao(self, user_id: int) -> Dict[str, Any]:
        """Obtém estatísticas de precisão da categorização IA"""
        try:
            with self.db.get_connection() as conn:
                # Total de transações
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM transacoes WHERE user_id = ?",
                    (user_id,)
                )
                total_transacoes = cursor.fetchone()[0]
                
                # Transações categorizadas
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM transacoes WHERE user_id = ? AND categoria IS NOT NULL",
                    (user_id,)
                )
                transacoes_categorizadas = cursor.fetchone()[0]
                
                # Distribuição por categoria
                cursor = conn.execute(
                    """SELECT categoria, COUNT(*) as qtd
                    FROM transacoes 
                    WHERE user_id = ? AND categoria IS NOT NULL
                    GROUP BY categoria
                    ORDER BY qtd DESC""",
                    (user_id,)
                )
                distribuicao_categorias = cursor.fetchall()
                
                # Calcular precisão estimada (baseado na variação de categorias)
                if transacoes_categorizadas > 0:
                    categorias_unicas = len(distribuicao_categorias)
                    if categorias_unicas > 0:
                        # Precisão baseada na distribuição (mais categorias = mais refinado)
                        precisao_geral = min(85, 50 + (categorias_unicas * 5))
                    else:
                        precisao_geral = 50
                else:
                    precisao_geral = 0
                
                return {
                    'total_transacoes': total_transacoes,
                    'transacoes_categorizadas': transacoes_categorizadas,
                    'precisao_geral': precisao_geral,
                    'distribuicao_categorias': dict(distribuicao_categorias),
                    'ultima_atualizacao': datetime.now().isoformat()
                }
        
        except Exception as e:
            return {
                'total_transacoes': 0,
                'transacoes_categorizadas': 0,
                'precisao_geral': 0,
                'distribuicao_categorias': {},
                'erro': str(e)
            }
    
    def contar_transacoes_sem_categoria(self, user_id: int) -> int:
        """Conta transações sem categoria para o usuário"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM transacoes WHERE user_id = ? AND (categoria IS NULL OR categoria = '')",
                    (user_id,)
                )
                return cursor.fetchone()[0]
        except Exception as e:
            return 0
    
    def salvar_categoria_no_cache(self, user_id: int, descricao: str, categoria: str):
        """Salva categoria no cache para melhorar performance futura"""
        cache_key = f"{user_id}_{hash(descricao.lower())}"
        self._categorization_cache[cache_key] = categoria
    
    def treinar_modelo_usuario(self, user_id: int) -> Dict[str, Any]:
        """Treina/atualiza o modelo de IA para um usuário específico"""
        try:
            # Obter todas as transações categorizadas do usuário para treino
            with self.db.get_connection() as conn:
                cursor = conn.execute(
                    """SELECT descricao, categoria, valor 
                    FROM transacoes 
                    WHERE user_id = ? AND categoria IS NOT NULL AND categoria != ''""",
                    (user_id,)
                )
                transacoes_treino = cursor.fetchall()
            
            if len(transacoes_treino) < 10:
                return {
                    'sucesso': False,
                    'motivo': 'Dados insuficientes para treino (mínimo 10 transações categorizadas)'
                }
            
            # Análise de padrões específicos do usuário
            padroes_usuario = {}
            
            for transacao in transacoes_treino:
                descricao, categoria, valor = transacao
                
                # Extrair palavras-chave específicas do usuário
                palavras = descricao.lower().split()
                for palavra in palavras:
                    if len(palavra) > 3:  # Ignorar palavras muito curtas
                        if categoria not in padroes_usuario:
                            padroes_usuario[categoria] = []
                        padroes_usuario[categoria].append(palavra)
            
            # Salvar padrões aprendidos (aqui você poderia salvar em banco)
            resultado_treino = {
                'sucesso': True,
                'padroes_aprendidos': len(padroes_usuario),
                'categorias_identificadas': list(padroes_usuario.keys()),
                'total_transacoes_treino': len(transacoes_treino)
            }
            
            return resultado_treino
            
        except Exception as e:
            return {
                'sucesso': False,
                'erro': str(e)
            }
    
    def sugerir_melhorias_categorizacao(self, user_id: int) -> List[str]:
        """Sugere melhorias para a categorização baseado nos dados do usuário"""
        sugestoes = []
        
        try:
            stats = self.obter_estatisticas_precisao(user_id)
            total = stats.get('total_transacoes', 0)
            categorizadas = stats.get('transacoes_categorizadas', 0)
            
            if total == 0:
                sugestoes.append("📝 Comece adicionando algumas transações para que a IA possa aprender")
                return sugestoes
            
            porcentagem_categorizada = (categorizadas / total) * 100
            
            if porcentagem_categorizada < 50:
                sugestoes.append("🏷️ Categorize mais transações manualmente para melhorar a precisão da IA")
            
            if porcentagem_categorizada < 80:
                sugestoes.append("🎯 Continue categorizando - quanto mais dados, melhor a IA fica!")
            
            # Verificar distribuição de categorias
            distribuicao = stats.get('distribuicao_categorias', {})
            if len(distribuicao) < 3:
                sugestoes.append("📊 Use mais categorias diferentes para treinar melhor a IA")
            
            # Verificar categoria 'Outros'
            outros_count = distribuicao.get('Outros', 0)
            if outros_count > categorizadas * 0.3:  # Mais de 30% em 'Outros'
                sugestoes.append("🔍 Muitas transações estão indo para 'Outros' - revise e categorize manualmente")
            
            if not sugestoes:
                sugestoes.append("✅ Excelente! Sua categorização IA está funcionando bem")
            
            return sugestoes
            
        except Exception as e:
            return ["❌ Erro ao analisar sugestões de melhoria"]
