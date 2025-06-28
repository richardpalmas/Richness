"""
Serviço de Cache de Insights LLM
Gerencia cache inteligente para insights gerados por LLM, otimizando performance e reduzindo custos
"""

import hashlib
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta

from utils.database_manager_v2 import DatabaseManager
from utils.repositories_v2 import CacheInsightsRepository
from services.llm_service import LLMService


class InsightsCacheService:
    """Serviço para gerenciamento inteligente de cache de insights LLM"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.cache_repo = CacheInsightsRepository(self.db)
        self.llm_service = LLMService()
        
        # Configurações de cache por tipo de insight
        self.cache_config = {
            'saldo_mensal': {'expires_hours': 6, 'priority': 'high'},
            'maior_gasto': {'expires_hours': 12, 'priority': 'medium'},
            'economia_potencial': {'expires_hours': 24, 'priority': 'low'},
            'alerta_gastos': {'expires_hours': 4, 'priority': 'high'},
            # Insights específicos do cartão - aumentar TTL para reduzir chamadas LLM
            'total_gastos_cartao': {'expires_hours': 24, 'priority': 'medium'},  # Aumentado de 8 para 24h
            'maior_gasto_cartao': {'expires_hours': 24, 'priority': 'medium'},  # Aumentado de 12 para 24h
            'padrao_gastos_cartao': {'expires_hours': 48, 'priority': 'low'},   # Aumentado de 24 para 48h
            'controle_cartao': {'expires_hours': 12, 'priority': 'high'},       # Aumentado de 6 para 12h
            # Insights específicos de metas e compromissos - TTL muito alto para máxima persistência
            'analise_compromissos_metas': {'expires_hours': 72, 'priority': 'medium'},    # 3 dias
            'progresso_metas_economia': {'expires_hours': 96, 'priority': 'low'},         # 4 dias
            'capacidade_pagamento_metas': {'expires_hours': 48, 'priority': 'medium'},    # 2 dias
            'estrategia_financeira_metas': {'expires_hours': 120, 'priority': 'low'}      # 5 dias
        }
    
    def gerar_data_hash(self, data_context: Dict[str, Any]) -> str:
        """Gera hash dos dados de contexto para identificar mudanças"""
        # Extrair apenas os dados relevantes para o hash
        relevant_data = {
            'saldo_info': data_context.get('saldo', {}),
            'usuario_id': data_context.get('usuario', {}).get('id'),
            'personalidade': data_context.get('personalidade'),
        }
        
        # Detectar e padronizar diferentes estruturas de transações
        transacoes = None
        
        # Tentar diferentes nomes de chaves para transações
        for key in ['ultimas_transacoes', 'ultimas_transacoes_cartao']:
            if key in data_context:
                transacoes = data_context[key]
                break
        
        if transacoes:
            # Contar transações
            if isinstance(transacoes, list):
                relevant_data['transacoes_count'] = len(transacoes)
                # Hash das últimas 5 transações para detectar mudanças
                sample_transacoes = transacoes[:5]
            elif hasattr(transacoes, '__len__'):  # DataFrame ou similar
                relevant_data['transacoes_count'] = len(transacoes)
                # Para DataFrame, converter para lista de dicts
                try:
                    if hasattr(transacoes, 'to_dict'):
                        sample_transacoes = transacoes.head(5).to_dict('records')
                    else:
                        sample_transacoes = list(transacoes)[:5]
                except:
                    sample_transacoes = []
            else:
                relevant_data['transacoes_count'] = 0
                sample_transacoes = []
            
            # Padronizar estrutura das transações para o hash
            relevant_data['transacoes_sample'] = []
            for t in sample_transacoes:
                if isinstance(t, dict):
                    # Padronizar nomes de colunas (minúsculas)
                    transacao_norm = {}
                    for key, value in t.items():
                        key_lower = key.lower()
                        if key_lower in ['valor', 'value']:
                            transacao_norm['valor'] = value
                        elif key_lower in ['categoria', 'category']:
                            transacao_norm['categoria'] = value
                        elif key_lower in ['data', 'date']:
                            # Normalizar formato da data
                            if hasattr(value, 'strftime'):
                                transacao_norm['data'] = value.strftime('%Y-%m-%d')
                            else:
                                transacao_norm['data'] = str(value)[:10]  # Pegar só a data
                    relevant_data['transacoes_sample'].append(transacao_norm)
        else:
            relevant_data['transacoes_count'] = 0
            relevant_data['transacoes_sample'] = []
        
        # Adicionar contextos específicos de diferentes tipos de insight
        # Para insights do cartão
        for key in ['total_gastos', 'maior_gasto', 'gasto_medio', 'valor_maior_gasto', 
                   'categoria_predominante', 'total_transacoes']:
            if key in data_context:
                relevant_data[key] = data_context[key]
        
        # Para insights gerais
        for key in ['saldo', 'maior_gasto', 'sugestao', 'alerta']:
            if key in data_context:
                relevant_data[key] = data_context[key]
        
        # Serializar e gerar hash
        data_str = json.dumps(relevant_data, sort_keys=True, default=str)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def gerar_prompt_hash(self, prompt: str, personalidade_params: Dict[str, Any]) -> str:
        """Gera hash do prompt e parâmetros de personalidade"""
        prompt_data = {
            'prompt': prompt.strip(),
            'personalidade_params': personalidade_params
        }
        
        prompt_str = json.dumps(prompt_data, sort_keys=True)
        return hashlib.md5(prompt_str.encode()).hexdigest()
    
    def obter_insight_cached(self, user_id: int, insight_type: str, personalidade: str,
                           data_context: Dict[str, Any], prompt: str, 
                           personalidade_params: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Obtém insight do cache se disponível e válido"""
        try:
            # Gerar hashes para identificação
            data_hash = self.gerar_data_hash(data_context)
            prompt_hash = self.gerar_prompt_hash(prompt, personalidade_params)
            
            # Buscar no cache
            cached_insight = self.cache_repo.buscar_insight_cache(
                user_id, insight_type, personalidade, data_hash, prompt_hash
            )
            
            if cached_insight:
                return {
                    'titulo': cached_insight['insight_titulo'],
                    'valor': cached_insight['insight_valor'] or '',
                    'comentario': cached_insight['insight_comentario'],
                    'source': 'cache',
                    'created_at': cached_insight['created_at'],
                    'used_count': cached_insight['used_count']
                }
            
            return None
            
        except Exception as e:
            # Em caso de erro, não usar cache - fallback para LLM
            return None
    
    def salvar_insight_cache(self, user_id: int, insight_type: str, personalidade: str,
                           data_context: Dict[str, Any], prompt: str,
                           personalidade_params: Dict[str, Any], titulo: str,
                           valor: str, comentario: str) -> bool:
        """Salva insight no cache"""
        try:
            # Gerar hashes
            data_hash = self.gerar_data_hash(data_context)
            prompt_hash = self.gerar_prompt_hash(prompt, personalidade_params)
            
            # Obter configuração de cache para o tipo
            config = self.cache_config.get(insight_type, {'expires_hours': 6})
            expires_hours = config['expires_hours']
            
            # Salvar no cache
            cache_id = self.cache_repo.salvar_insight_cache(
                user_id=user_id,
                insight_type=insight_type,
                personalidade=personalidade,
                data_hash=data_hash,
                prompt_hash=prompt_hash,
                titulo=titulo,
                valor=valor,
                comentario=comentario,
                expires_hours=expires_hours
            )
            
            return cache_id > 0
            
        except Exception as e:
            # Em caso de erro, não falhar - apenas não cachear
            return False
    
    def gerar_insight_com_cache(self, user_id: int, insight_type: str, personalidade: str,
                              data_context: Dict[str, Any], prompt: str,
                              personalidade_params: Dict[str, Any], 
                              forcar_regeneracao: bool = False) -> Dict[str, Any]:
        """Gera insight usando cache quando possível, senão chama LLM"""
        
        # Verificar se deve forçar regeneração (ignorar cache)
        if not forcar_regeneracao:
            # Tentar obter do cache primeiro
            cached_result = self.obter_insight_cached(
                user_id, insight_type, personalidade, data_context, prompt, personalidade_params
            )
            
            if cached_result:
                return cached_result
        
        # Cache miss - gerar novo insight via LLM
        try:
            response = self.llm_service.generate_response(prompt, data_context)
            comentario = response.get('response', '')
            
            # Extrair título e valor do contexto se disponível
            titulo = self._extrair_titulo_por_tipo(insight_type)
            valor = self._extrair_valor_por_tipo(insight_type, data_context)
            
            # Salvar no cache para próximas consultas
            self.salvar_insight_cache(
                user_id, insight_type, personalidade, data_context,
                prompt, personalidade_params, titulo, valor, comentario
            )
            
            return {
                'titulo': titulo,
                'valor': valor,
                'comentario': comentario,
                'source': 'llm',
                'created_at': datetime.now().isoformat(),
                'used_count': 0
            }
            
        except Exception as e:
            # Fallback em caso de erro
            return {
                'titulo': self._extrair_titulo_por_tipo(insight_type),
                'valor': '',
                'comentario': f'Erro ao gerar insight: {str(e)}',
                'source': 'error',
                'created_at': datetime.now().isoformat(),
                'used_count': 0
            }
    
    def _extrair_titulo_por_tipo(self, insight_type: str) -> str:
        """Extrai título padrão baseado no tipo de insight"""
        titulos = {
            'saldo_mensal': 'Saldo do Mês',
            'maior_gasto': 'Maior Gasto',
            'economia_potencial': 'Economia Potencial',
            'alerta_gastos': 'Alerta de Gastos',
            # Títulos específicos do cartão
            'total_gastos_cartao': 'Total Gastos Cartão',
            'maior_gasto_cartao': 'Maior Gasto Cartão',
            'padrao_gastos_cartao': 'Padrão de Gastos',
            'controle_cartao': 'Controle do Cartão',
            # Títulos específicos de metas e compromissos
            'analise_compromissos_metas': 'Análise de Compromissos e Metas',
            'progresso_metas_economia': 'Progresso de Metas Econômicas',
            'capacidade_pagamento_metas': 'Capacidade de Pagamento de Metas',
            'estrategia_financeira_metas': 'Estratégia Financeira de Metas'
        }
        return titulos.get(insight_type, 'Insight Financeiro')
    
    def _extrair_valor_por_tipo(self, insight_type: str, data_context: Dict[str, Any]) -> str:
        """Extrai valor relevante baseado no tipo de insight"""
        from utils.formatacao import formatar_valor_monetario
        
        try:
            if insight_type == 'saldo_mensal':
                saldo = data_context.get('saldo', {}).get('valor_restante', 0)
                return formatar_valor_monetario(saldo)
            
            elif insight_type == 'maior_gasto':
                maior_gasto = data_context.get('maior_gasto', {})
                if maior_gasto and 'valor' in maior_gasto:
                    return formatar_valor_monetario(maior_gasto['valor'])
            
            elif insight_type == 'economia_potencial':
                sugestao = data_context.get('sugestao', {})
                if sugestao and 'economia_potencial' in sugestao:
                    return formatar_valor_monetario(sugestao['economia_potencial'])
            
            # Valores específicos do cartão
            elif insight_type == 'total_gastos_cartao':
                total_gastos = data_context.get('total_gastos', 0)
                return formatar_valor_monetario(total_gastos)
            
            elif insight_type == 'maior_gasto_cartao':
                valor_maior_gasto = data_context.get('valor_maior_gasto', 0)
                return formatar_valor_monetario(valor_maior_gasto)
            
            elif insight_type == 'padrao_gastos_cartao':
                total_transacoes = data_context.get('total_transacoes', 0)
                return f"{total_transacoes} transações"
            
            elif insight_type == 'controle_cartao':
                return ''  # Recomendações não têm valor específico
            
            # Valores específicos de metas e compromissos
            elif insight_type == 'analise_compromissos_metas':
                return ''  # Análise de compromissos e metas não têm valor específico
            
            elif insight_type == 'progresso_metas_economia':
                return ''  # Progresso de metas econômicas não têm valor específico
            
            elif insight_type == 'capacidade_pagamento_metas':
                return ''  # Capacidade de pagamento de metas não têm valor específico
            
            elif insight_type == 'estrategia_financeira_metas':
                return ''  # Estratégia financeira de metas não têm valor específico
            
            return ''
            
        except Exception:
            return ''
    
    def invalidar_cache_por_mudanca_dados(self, user_id: int) -> int:
        """Invalida cache quando dados financeiros mudam (nova transação, etc.)"""
        return self.cache_repo.invalidar_cache_usuario(user_id)
    
    def limpar_cache_expirado_automatico(self) -> int:
        """Limpa cache expirado automaticamente (para ser chamado periodicamente)"""
        return self.cache_repo.limpar_cache_expirado()
    
    def obter_estatisticas_cache_usuario(self, user_id: int) -> Dict[str, Any]:
        """Obtém estatísticas detalhadas do cache para o usuário"""
        stats = self.cache_repo.obter_estatisticas_cache(user_id)
        
        # Adicionar métricas calculadas
        total_entries = stats.get('total_cache_entries', 0)
        cache_24h = stats.get('cache_criado_24h', 0)
        
        # Calcular eficiência do cache
        cache_por_tipo = stats.get('cache_valido_por_tipo', {})
        total_valido = sum(cache_por_tipo.values())
        
        stats.update({
            'eficiencia_cache': round(total_valido / total_entries * 100, 2) if total_entries > 0 else 0,
            'taxa_criacao_24h': round(cache_24h / 24, 2),  # Insights por hora
            'tipos_cached': list(cache_por_tipo.keys()),
            'recomendacoes': self._gerar_recomendacoes_cache(stats)
        })
        
        return stats
    
    def _gerar_recomendacoes_cache(self, stats: Dict[str, Any]) -> List[str]:
        """Gera recomendações baseadas nas estatísticas de cache"""
        recomendacoes = []
        
        eficiencia = stats.get('eficiencia_cache', 0)
        if eficiencia < 50:
            recomendacoes.append("Cache com baixa eficiência - considere ajustar tempos de expiração")
        
        cache_24h = stats.get('cache_criado_24h', 0)
        if cache_24h > 50:
            recomendacoes.append("Alto volume de cache criado - sistema funcionando bem")
        elif cache_24h < 5:
            recomendacoes.append("Baixo uso de cache - verifique se os insights estão sendo acessados")
        
        mais_usados = stats.get('insights_mais_usados', [])
        if len(mais_usados) > 0:
            top_insight = mais_usados[0]
            recomendacoes.append(f"Insight mais popular: {top_insight['insight_type']} ({top_insight['used_count']} usos)")
        
        return recomendacoes
