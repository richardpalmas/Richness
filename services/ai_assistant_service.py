"""
Serviço de Assistente Virtual Financeiro com IA
Sistema conversacional que responde perguntas financeiras baseado em dados do usuário
"""

from typing import Dict, List, Any
import re
from datetime import datetime
import json
import pandas as pd

from utils.database_manager_v2 import DatabaseManager
from utils.repositories_v2 import TransacaoRepository, UsuarioRepository
from services.insights_service_v2 import InsightsServiceV2
from services.transacao_service_v2 import TransacaoService
from services.llm_service import LLMService


class FinancialAIAssistant:
    """Assistente virtual financeiro com capacidades de IA"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.transacao_repo = TransacaoRepository(self.db)
        self.usuario_repo = UsuarioRepository(self.db)
        self.insights_service = InsightsServiceV2()
        self.transacao_service = TransacaoService()
        self.llm_service = LLMService()
    
    def _get_user_financial_context(self, user_id: int, data_inicio: str = '', data_fim: str = '', qtd_transacoes: int = 50) -> Dict[str, Any]:
        """Obtém o contexto financeiro completo do usuário para o LLM, considerando período e quantidade de transações"""
        context = {}
        try:
            # Saldo e informações mensais (usar período se fornecido)
            data_inicio_str = str(data_inicio) if data_inicio else ''
            data_fim_str = str(data_fim) if data_fim else ''
            if data_inicio_str and data_fim_str:
                # Buscar transações do período
                df_transacoes = self.transacao_repo.obter_transacoes_periodo(user_id, data_inicio_str, data_fim_str)
                # Adicionar todas as transações do período (limitadas)
                if not df_transacoes.empty:
                    transacoes_periodo = df_transacoes[['data', 'descricao', 'valor', 'categoria']].copy()
                    if not isinstance(transacoes_periodo, pd.DataFrame):
                        transacoes_periodo = pd.DataFrame(transacoes_periodo)
                    transacoes_periodo['data'] = pd.to_datetime(transacoes_periodo['data'])
                    transacoes_periodo = transacoes_periodo.sort_values('data', ascending=False).head(qtd_transacoes)
                    context['todas_transacoes_periodo'] = transacoes_periodo.to_dict('records')
                # Calcular receitas e gastos do período
                receitas = df_transacoes.loc[df_transacoes['valor'] > 0, 'valor'].sum() if not df_transacoes.empty else 0
                gastos = abs(df_transacoes.loc[df_transacoes['valor'] < 0, 'valor'].sum()) if not df_transacoes.empty else 0
                valor_restante = receitas - gastos
                percentual_gasto = (gastos / receitas * 100) if receitas > 0 else 0
                context['saldo'] = {
                    'valor_restante': valor_restante,
                    'total_receitas': receitas,
                    'total_gastos': gastos,
                    'percentual_gasto': percentual_gasto,
                    'dias_restantes': 0,
                    'media_diaria_disponivel': 0,
                    'status': 'positivo' if valor_restante >= 0 else 'negativo',
                    'periodo': f'{data_inicio_str} a {data_fim_str}'
                }
                # Gastos por categoria
                if not df_transacoes.empty:
                    df_gastos = df_transacoes.loc[df_transacoes['valor'] < 0].copy()
                    if not df_gastos.empty:
                        df_gastos['valor_abs'] = abs(df_gastos['valor'])
                        gastos_categoria = df_gastos.groupby('categoria')['valor_abs'].agg(['sum', 'mean', 'count']).round(2)
                        total_gastos = gastos_categoria['sum'].sum()
                        gastos_categoria['percentual'] = (gastos_categoria['sum'] / total_gastos * 100).round(2) if total_gastos > 0 else 0
                        context['categorias'] = gastos_categoria.to_dict('index')
                        context['total_gastos_periodo'] = total_gastos
                        context['periodo_analise'] = f'{data_inicio_str} a {data_fim_str}'
                # Últimas transações do período
                if not df_transacoes.empty:
                    df_transacoes = df_transacoes.sort_values('data', ascending=False).head(5)
                    context['ultimas_transacoes'] = df_transacoes.to_dict('records')
            else:
                # Fallback: usar métodos padrão (mês atual)
                saldo_info = self.insights_service.obter_valor_restante_mensal(user_id)
                if saldo_info:
                    context['saldo'] = {
                        'valor_restante': saldo_info.get('valor_restante', 0),
                        'total_receitas': saldo_info.get('total_receitas', 0),
                        'total_gastos': saldo_info.get('total_gastos', 0),
                        'percentual_gasto': saldo_info.get('percentual_gasto', 0),
                        'dias_restantes': saldo_info.get('dias_restantes', 0),
                        'media_diaria_disponivel': saldo_info.get('media_diaria_disponivel', 0),
                        'status': saldo_info.get('status', '')
                    }
                gastos_info = self.insights_service.analisar_gastos_por_categoria(user_id)
                if gastos_info and gastos_info.get('status') == 'ok':
                    context['categorias'] = gastos_info.get('resumo_categorias', {})
                    context['total_gastos_periodo'] = gastos_info.get('total_periodo', 0)
                    context['periodo_analise'] = gastos_info.get('periodo_analisado', '')
                alertas = self.insights_service.detectar_alertas_financeiros(user_id)
                if alertas:
                    context['alertas'] = alertas
                # Últimas transações padrão
                user_data = self.usuario_repo.obter_usuario_por_id(user_id)
                if user_data:
                    username = user_data.get('username', '')
                    df_transacoes = self.transacao_service.listar_transacoes_usuario(username)
                    if not df_transacoes.empty:
                        df_transacoes = df_transacoes.sort_values('data', ascending=False).head(5)
                        context['ultimas_transacoes'] = df_transacoes.to_dict('records')
            # Dados do usuário
            user_data = self.usuario_repo.obter_usuario_por_id(user_id)
            if user_data:
                context['usuario'] = {
                    'username': user_data.get('username', ''),
                    'nome': user_data.get('nome', ''),
                    'email': user_data.get('email', '')
                }
        except Exception as e:
            context['erro'] = str(e)
        return context
    
    def process_message(self, user_id: int, message: str, data_inicio: str = '', data_fim: str = '', qtd_transacoes: int = 50) -> Dict[str, Any]:
        """Processa mensagem do usuário e gera resposta inteligente baseada nos dados do usuário, período e quantidade de transações"""
        try:
            data_inicio_str = str(data_inicio) if data_inicio else ''
            data_fim_str = str(data_fim) if data_fim else ''
            context = self._get_user_financial_context(user_id, data_inicio_str, data_fim_str, qtd_transacoes)
            response = self.llm_service.generate_response(message, context)
            return {
                'response': response,
                'context': context,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            raise e
    
    def process_message_with_personality(self, user_id: int, message: str, personalidade: str = "clara", data_inicio: str = '', data_fim: str = '', qtd_transacoes: int = 50) -> Dict[str, Any]:
        """Processa mensagem do usuário considerando a personalidade selecionada, período e quantidade de transações"""
        try:
            data_inicio_str = str(data_inicio) if data_inicio else ''
            data_fim_str = str(data_fim) if data_fim else ''
            context = self._get_user_financial_context(user_id, data_inicio_str, data_fim_str, qtd_transacoes)
            context['personalidade'] = personalidade
            llm_result = self.llm_service.generate_response(message, context)
            response = llm_result['response']
            personalidade_usada = llm_result.get('personalidade')
            prompt_usado = llm_result.get('prompt')
            return {
                'response': response,
                'context': context,
                'personalidade': personalidade_usada,
                'prompt': prompt_usado,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            raise e

    def get_quick_insights(self, user_id: int) -> Dict[str, Any]:
        """Retorna insights rápidos para exibição na interface"""
        try:
            # Verificar se user_id é válido
            if not user_id or user_id <= 0:
                return {'erro': f"User ID inválido: {user_id}"}
                
            # Obter contexto financeiro completo do usuário
            context = self._get_user_financial_context(user_id)
            insights = {}
            
            # Extrair informações principais do contexto
            if 'saldo' in context:
                insights['saldo_mensal'] = context['saldo'].get('valor_restante', 0)
            
            if 'alertas' in context:
                insights['alertas'] = []
                for alerta in context['alertas']:
                    if isinstance(alerta, dict):
                        insights['alertas'].append(alerta.get('mensagem', str(alerta)))
                    else:
                        insights['alertas'].append(str(alerta))
                insights['alertas'] = insights['alertas'][:3]  # Limitar a 3 alertas
            else:
                insights['alertas'] = []
            
            if 'categorias' in context:
                # Encontrar categoria com maior gasto
                categorias_validas = {}
                for categoria, dados in context['categorias'].items():
                    if 'sum' in dados:
                        valor = dados['sum']
                        if isinstance(valor, (int, float)) or (isinstance(valor, str) and valor.replace('.', '').isdigit()):
                            categorias_validas[categoria] = float(valor)
                
                if categorias_validas:
                    top_categoria = max(categorias_validas.items(), key=lambda x: float(x[1]))
                    insights['top_categoria'] = {
                        'nome': top_categoria[0],
                        'valor': float(top_categoria[1])
                    }
            
            return insights
            
        except Exception as e:
            return {'erro': f"Erro ao obter insights: {str(e)}"}
