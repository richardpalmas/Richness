"""
Serviço de Insights Financeiros - Versão corrigida
Análises e métricas avançadas baseadas na planilha de referência.
"""

from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import calendar

from utils.database_manager_v2 import DatabaseManager
from utils.repositories_v2 import TransacaoRepository, CategoriaRepository
from utils.formatacao import formatar_valor_monetario


class InsightsServiceV2:
    """Serviço para geração de insights financeiros avançados - versão corrigida"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.transacao_repo = TransacaoRepository(self.db)
        self.categoria_repo = CategoriaRepository(self.db)
        
        # Categorias baseadas na planilha de referência
        self.CATEGORIAS_PREDEFINIDAS = {
            'RECEITAS': {
                'Salário': {'tipo': 'fixo', 'prioridade': 1, 'cor': '#28a745', 'icone': '💰'},
                'Investimentos': {'tipo': 'variável', 'prioridade': 2, 'cor': '#17a2b8', 'icone': '📈'},
                'Crédito': {'tipo': 'variável', 'prioridade': 3, 'cor': '#ffc107', 'icone': '💳'},
                'Outros': {'tipo': 'variável', 'prioridade': 4, 'cor': '#6c757d', 'icone': '🏷️'}
            },
            'GASTOS_FIXOS': {
                'Casa': {'tipo': 'fixo', 'prioridade': 1, 'cor': '#007bff', 'icone': '🏠'},
                'Energia': {'tipo': 'fixo', 'prioridade': 2, 'cor': '#ffc107', 'icone': '⚡'},
                'Água': {'tipo': 'fixo', 'prioridade': 3, 'cor': '#17a2b8', 'icone': '💧'},
                'Internet': {'tipo': 'fixo', 'prioridade': 4, 'cor': '#6f42c1', 'icone': '🌐'},
                'Compra Mensal': {'tipo': 'fixo', 'prioridade': 5, 'cor': '#20c997', 'icone': '🛒'},
                'Imposto/Seguro': {'tipo': 'fixo', 'prioridade': 6, 'cor': '#dc3545', 'icone': '📋'}
            },
            'GASTOS_VARIAVEIS': {
                'Fatura Cartão': {'tipo': 'variável', 'prioridade': 1, 'cor': '#dc3545', 'icone': '💳'},
                'Gasolina': {'tipo': 'variável', 'prioridade': 2, 'cor': '#fd7e14', 'icone': '⛽'},
                'Dízimo e Doações': {'tipo': 'variável', 'prioridade': 3, 'cor': '#6f42c1', 'icone': '🙏'},
                'Carro': {'tipo': 'variável', 'prioridade': 4, 'cor': '#495057', 'icone': '🚗'},
                'Viagem / Outros': {'tipo': 'variável', 'prioridade': 5, 'cor': '#20c997', 'icone': '✈️'}
            },
            'METAS': {
                'Poupança': {'tipo': 'meta', 'prioridade': 1, 'cor': '#28a745', 'icone': '🎯'}
            }
        }
    
    def obter_valor_restante_mensal(self, user_id: int, mes: Optional[int] = None, ano: Optional[int] = None) -> Dict[str, Any]:
        """Calcula o valor restante do mês baseado em receitas menos gastos"""
        if mes is None:
            mes = datetime.now().month
        if ano is None:
            ano = datetime.now().year
        
        # Definir período do mês
        data_inicio = f"{ano}-{mes:02d}-01"
        ultimo_dia = calendar.monthrange(ano, mes)[1]
        data_fim = f"{ano}-{mes:02d}-{ultimo_dia}"
        
        # Obter transações do período
        try:
            df_transacoes = self.transacao_repo.obter_transacoes_periodo(
                user_id, data_inicio, data_fim
            )
        except Exception:
            df_transacoes = pd.DataFrame()
        
        if df_transacoes.empty:
            return {
                'valor_restante': 0.0,
                'total_receitas': 0.0,
                'total_gastos': 0.0,
                'percentual_gasto': 0.0,
                'dias_restantes': 0,
                'media_diaria_disponivel': 0.0,
                'status': 'sem_dados',
                'mes_ano': f"{mes:02d}/{ano}"            }
        
        # Calcular totais
        receitas = df_transacoes.loc[df_transacoes['valor'] > 0, 'valor'].sum()
        gastos = abs(df_transacoes.loc[df_transacoes['valor'] < 0, 'valor'].sum())
        valor_restante = receitas - gastos
        
        # Calcular percentual gasto
        percentual_gasto = (gastos / receitas * 100) if receitas > 0 else 0
        
        # Calcular dias restantes no mês
        hoje = datetime.now()
        if hoje.month == mes and hoje.year == ano:
            ultimo_dia_mes = datetime(ano, mes, ultimo_dia)
            dias_restantes = (ultimo_dia_mes - hoje).days + 1
        else:
            dias_restantes = 0
        
        # Média diária disponível
        media_diaria = valor_restante / dias_restantes if dias_restantes > 0 else 0
        
        # Determinar status
        status = 'positivo'
        if valor_restante < 0:
            status = 'negativo'
        elif percentual_gasto > 90:
            status = 'atencao'
        elif percentual_gasto > 70:
            status = 'moderado'
        
        return {
            'valor_restante': valor_restante,
            'total_receitas': receitas,
            'total_gastos': gastos,
            'percentual_gasto': percentual_gasto,
            'dias_restantes': dias_restantes,
            'media_diaria_disponivel': media_diaria,
            'status': status,
            'mes_ano': f"{mes:02d}/{ano}"
        }
    
    def analisar_gastos_por_categoria(self, user_id: int, meses: int = 6) -> Dict[str, Any]:
        """Analisa distribuição de gastos por categoria nos últimos meses"""
        data_inicio = (datetime.now() - relativedelta(months=meses)).strftime('%Y-%m-%d')
        data_fim = datetime.now().strftime('%Y-%m-%d')
        
        try:
            df_transacoes = self.transacao_repo.obter_transacoes_periodo(
                user_id, data_inicio, data_fim
            )
        except Exception:
            return {'status': 'sem_dados'}
        
        if df_transacoes.empty:
            return {'status': 'sem_dados'}
        
        # Filtrar apenas gastos
        df_gastos = df_transacoes.loc[df_transacoes['valor'] < 0].copy()
        if df_gastos.empty:
            return {'status': 'sem_dados'}
            
        df_gastos['valor_abs'] = abs(df_gastos['valor'])
        
        # Agrupar por categoria
        gastos_categoria = df_gastos.groupby('categoria')['valor_abs'].agg([
            'sum', 'mean', 'count'
        ]).round(2)
        
        # Calcular percentuais
        total_gastos = gastos_categoria['sum'].sum()
        gastos_categoria['percentual'] = (gastos_categoria['sum'] / total_gastos * 100).round(2)
        
        # Ordenar por valor total
        gastos_categoria = gastos_categoria.sort_values('sum', ascending=False)
        
        return {
            'resumo_categorias': gastos_categoria.to_dict('index'),
            'total_periodo': total_gastos,
            'periodo_analisado': f"{meses} meses",
            'status': 'ok'
        }
    
    def detectar_alertas_financeiros(self, user_id: int) -> List[Dict[str, Any]]:
        """Detecta situações que requerem atenção financeira"""
        alertas = []
        
        # Alerta 1: Valor restante negativo
        valor_restante_info = self.obter_valor_restante_mensal(user_id)
        if valor_restante_info['valor_restante'] < 0:
            alertas.append({
                'tipo': 'valor_negativo',
                'severidade': 'alta',
                'titulo': 'Saldo Negativo',
                'mensagem': f"Seu saldo está negativo em {formatar_valor_monetario(valor_restante_info['valor_restante'])}",
                'acao_sugerida': 'Revisar gastos do mês e identificar onde reduzir'
            })
        
        # Alerta 2: Gastos acima de 90% da receita
        elif valor_restante_info['percentual_gasto'] > 90:
            alertas.append({
                'tipo': 'gasto_excessivo',
                'severidade': 'media',
                'titulo': 'Gastos Elevados',
                'mensagem': f"Você já gastou {valor_restante_info['percentual_gasto']:.1f}% da sua receita mensal",
                'acao_sugerida': 'Considere reduzir gastos variáveis nos próximos dias'
            })
        
        return alertas
    
    def sugerir_otimizacoes(self, user_id: int) -> List[Dict[str, Any]]:
        """Sugere otimizações baseadas no padrão de gastos"""
        sugestoes = []
        
        # Analisar últimos 3 meses
        analise = self.analisar_gastos_por_categoria(user_id, 3)
        if analise.get('status') != 'ok':
            return sugestoes
        
        # Sugestão 1: Maior categoria de gasto
        categorias = analise['resumo_categorias']
        if categorias:
            maior_categoria = max(categorias.items(), key=lambda x: x[1]['sum'])
            categoria_nome, dados = maior_categoria
            
            if dados['percentual'] > 30:
                sugestoes.append({
                    'tipo': 'reduzir_categoria_principal',
                    'titulo': f'Otimizar gastos com {categoria_nome}',
                    'economia_potencial': dados['sum'] * 0.1,  # 10% de economia
                    'descricao': f"{categoria_nome} representa {dados['percentual']:.1f}% dos seus gastos. Uma redução de 10% economizaria {formatar_valor_monetario(dados['sum'] * 0.1)}",
                    'dificuldade': 'media'
                })
        
        # Sugestão 2: Meta de poupança baseada na receita
        valor_restante = self.obter_valor_restante_mensal(user_id)
        if valor_restante['total_receitas'] > 0:
            meta_poupanca = valor_restante['total_receitas'] * 0.2  # 20% da receita
            
            sugestoes.append({
                'tipo': 'meta_poupanca',
                'titulo': 'Estabelecer Meta de Poupança',
                'economia_potencial': meta_poupanca,
                'descricao': f"Tente poupar 20% da sua receita mensal: {formatar_valor_monetario(meta_poupanca)}",
                'dificuldade': 'media'
            })
        
        return sugestoes
    
    def obter_comparativo_mensal(self, user_id: int, meses: int = 12) -> Dict[str, Any]:
        """Gera comparativo de receitas vs despesas por mês"""
        dados_mensais = []
        
        for i in range(meses):
            data_ref = datetime.now() - relativedelta(months=i)
            mes, ano = data_ref.month, data_ref.year
            
            info_mes = self.obter_valor_restante_mensal(user_id, mes, ano)
            dados_mensais.append({
                'mes_ano': info_mes['mes_ano'],
                'receitas': info_mes['total_receitas'],
                'gastos': info_mes['total_gastos'],
                'saldo': info_mes['valor_restante'],
                'percentual_gasto': info_mes['percentual_gasto']
            })
        
        # Calcular tendências
        if len(dados_mensais) >= 3:
            ultimos_3_saldos = [d['saldo'] for d in dados_mensais[:3]]
            tendencia_saldo = 'crescente' if ultimos_3_saldos[0] > ultimos_3_saldos[2] else 'decrescente'
            
            ultimos_3_gastos = [d['percentual_gasto'] for d in dados_mensais[:3]]
            tendencia_gastos = 'aumentando' if ultimos_3_gastos[0] > ultimos_3_gastos[2] else 'diminuindo'
        else:
            tendencia_saldo = 'indefinido'
            tendencia_gastos = 'indefinido'
        
        return {
            'dados_mensais': list(reversed(dados_mensais)),  # Do mais antigo para o mais recente
            'tendencia_saldo': tendencia_saldo,
            'tendencia_gastos': tendencia_gastos,
            'media_saldo': sum(d['saldo'] for d in dados_mensais) / len(dados_mensais) if dados_mensais else 0,
            'media_percentual_gasto': sum(d['percentual_gasto'] for d in dados_mensais) / len(dados_mensais) if dados_mensais else 0
        }
    
    def inicializar_categorias_predefinidas(self, user_id: int) -> bool:
        """Inicializa categorias pré-definidas baseadas na planilha de referência"""
        try:
            # Verificar se já existem categorias (usando query direta)
            result = self.db.executar_query(
                "SELECT COUNT(*) as count FROM categorias_personalizadas WHERE user_id = ?",
                [user_id]
            )
            if result and result[0]['count'] > 0:
                return True  # Já inicializadas
            
            # Criar categorias baseadas na planilha
            todas_categorias = {}
            todas_categorias.update(self.CATEGORIAS_PREDEFINIDAS['RECEITAS'])
            todas_categorias.update(self.CATEGORIAS_PREDEFINIDAS['GASTOS_FIXOS'])
            todas_categorias.update(self.CATEGORIAS_PREDEFINIDAS['GASTOS_VARIAVEIS'])
            todas_categorias.update(self.CATEGORIAS_PREDEFINIDAS['METAS'])
            
            # Inserir no banco usando a estrutura correta (nome em vez de descricao)
            for categoria, config in todas_categorias.items():
                self.db.executar_insert("""                    INSERT OR IGNORE INTO categorias_personalizadas (user_id, nome, cor, icone)
                    VALUES (?, ?, ?, ?)
                """, [user_id, categoria, config.get('cor', '#6c757d'), config.get('icone', '🏷️')])
            
            return True
        except Exception as e:
            return False
