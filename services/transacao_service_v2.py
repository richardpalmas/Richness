"""
Service Layer - Camada de serviços com lógica de negócio otimizada.
Versão 2.0 com melhorias de performance e funcionalidades avançadas.
"""

from typing import List, Dict, Optional, Tuple, Any
import pandas as pd
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor
import asyncio

from utils.database_manager_v2 import DatabaseManager
from utils.repositories_v2 import (
    UsuarioRepository, TransacaoRepository, CategoriaRepository,
    DescricaoRepository, ExclusaoRepository, CacheIARepository,
    ArquivoOFXRepository, SystemLogRepository
)
from utils.exception_handler import ExceptionHandler

class TransacaoService:
    """Serviço otimizado para operações com transações"""
    
    def __init__(self):
        self.db = DatabaseManager()
        
        # Inicializar repositories
        self.usuario_repo = UsuarioRepository(self.db)
        self.transacao_repo = TransacaoRepository(self.db)
        self.categoria_repo = CategoriaRepository(self.db)
        self.descricao_repo = DescricaoRepository(self.db)
        self.exclusao_repo = ExclusaoRepository(self.db)
        self.cache_ia_repo = CacheIARepository(self.db)
        self.arquivo_repo = ArquivoOFXRepository(self.db)
        self.log_repo = SystemLogRepository(self.db)
        
        # Configurar executor para operações assíncronas
        self.executor = ThreadPoolExecutor(max_workers=3)
        
        # Logger
        self.logger = logging.getLogger(__name__)
    
    def importar_ofx_arquivo(self, user_id: int, arquivo_ofx: str, tipo: str = 'extrato') -> Dict[str, Any]:
        """Importa transações de arquivo OFX com deduplicação automática e otimizações"""
        def _import_data():
            try:
                # Calcular hash do arquivo para evitar reprocessamento
                with open(arquivo_ofx, 'rb') as f:
                    hash_arquivo = hashlib.md5(f.read()).hexdigest()
                
                # Verificar se já foi processado
                if self.arquivo_repo.arquivo_ja_processado(user_id, hash_arquivo):
                    return {
                        'importadas': 0,
                        'duplicadas': 0,
                        'total': 0,
                        'status': 'ja_processado',
                        'mensagem': 'Arquivo já foi processado anteriormente'
                    }
                
                # Importar usando o OFXReader existente
                from utils.ofx_reader import OFXReader
                  # Obter nome do usuário para o OFXReader
                usuario_info = self.usuario_repo.obter_usuario_por_id(user_id)
                username = usuario_info['username'] if usuario_info else 'default'
                
                reader = OFXReader(username)
                
                # Ler transações do arquivo
                if tipo == 'cartao':
                    df_transacoes = reader.buscar_cartoes(dias=365)
                else:
                    df_transacoes = reader.buscar_extratos(dias=365)
                
                if df_transacoes.empty:
                    return {
                        'importadas': 0,
                        'duplicadas': 0,
                        'total': 0,
                        'status': 'arquivo_vazio'
                    }
                
                # Preparar transações para importação em lote
                transacoes_para_importar = []
                for _, row in df_transacoes.iterrows():
                    transacao_data = {
                        'data': row['Data'].strftime('%Y-%m-%d'),
                        'descricao': row['Descrição'],
                        'valor': float(row['Valor']),
                        'categoria': row.get('Categoria', 'Outros'),
                        'origem': f'ofx_{tipo}',
                        'conta': row.get('Conta', ''),
                        'arquivo_origem': os.path.basename(arquivo_ofx)
                    }
                    transacoes_para_importar.append(transacao_data)
                
                # Importação em lote
                importadas = self.transacao_repo.criar_transacoes_lote(user_id, transacoes_para_importar)
                duplicadas = len(transacoes_para_importar) - importadas
                
                # Marcar arquivo como processado
                self.arquivo_repo.marcar_arquivo_processado(
                    user_id, os.path.basename(arquivo_ofx), hash_arquivo, tipo, len(transacoes_para_importar)
                )
                
                # Log da operação
                self.log_repo.log_action(
                    user_id, 'importacao_ofx',
                    f'Arquivo: {os.path.basename(arquivo_ofx)}, Tipo: {tipo}, Importadas: {importadas}'
                )
                
                return {
                    'importadas': importadas,
                    'duplicadas': duplicadas,
                    'total': len(transacoes_para_importar),
                    'status': 'sucesso',
                    'hash_arquivo': hash_arquivo
                }
                
            except Exception as e:
                self.logger.error(f"Erro na importação OFX: {e}")
                return {
                    'importadas': 0,
                    'duplicadas': 0,
                    'total': 0,
                    'status': 'erro',
                    'erro': str(e)
                }
        
        return ExceptionHandler.safe_execute(
            func=_import_data,
            error_handler=ExceptionHandler.handle_generic_error,
            default_return={'importadas': 0, 'duplicadas': 0, 'total': 0, 'erro': True}
        )
    
    def obter_dashboard_data(self, user_id: int, periodo_meses: int = 3) -> Dict[str, Any]:
        """Dados consolidados para dashboard com cache otimizado"""
        def _load_dashboard():
            data_inicio = (datetime.now() - timedelta(days=periodo_meses * 30)).strftime('%Y-%m-%d')
            data_fim = datetime.now().strftime('%Y-%m-%d')
            
            # Obter dados usando queries otimizadas
            transacoes = self.transacao_repo.obter_transacoes_periodo(
                user_id, data_inicio, data_fim, limite=1000
            )
              # Calcular métricas usando pandas para performance
            if not transacoes.empty:
                # Garantir que valores estão em formato numérico
                transacoes['valor'] = pd.to_numeric(transacoes['valor'], errors='coerce')
                transacoes = transacoes.dropna(subset=['valor'])
                
                receitas = transacoes[transacoes['valor'] > 0]['valor'].sum()
                despesas = abs(transacoes[transacoes['valor'] < 0]['valor'].sum())
                saldo = receitas - despesas
                
                # Estatísticas por categoria
                estatisticas_cat = transacoes.groupby('categoria').agg({
                    'valor': ['count', 'sum'],
                    'data': 'max'
                }).round(2)
                
                # Top categorias por gasto
                despesas_por_cat = transacoes[transacoes['valor'] < 0].groupby('categoria')['valor'].sum().abs().sort_values(ascending=False).head(10)
                
            else:
                receitas = despesas = saldo = 0
                estatisticas_cat = pd.DataFrame()
                despesas_por_cat = pd.Series()
            
            # Evolução mensal
            evolucao = self.transacao_repo.obter_evolucao_mensal(user_id, periodo_meses)
            
            # Estatísticas do usuário
            stats_usuario = self.usuario_repo.obter_estatisticas_usuario(user_id)
            
            # Análise de tendências
            tendencias = self._analisar_tendencias(transacoes) if not transacoes.empty else {}
            
            return {
                'periodo': {
                    'inicio': data_inicio,
                    'fim': data_fim,
                    'meses': periodo_meses
                },
                'metricas': {
                    'total_transacoes': len(transacoes),
                    'receitas_totais': float(receitas),
                    'despesas_totais': float(despesas),
                    'saldo_periodo': float(saldo),
                    'ticket_medio': float(despesas / len(transacoes[transacoes['valor'] < 0])) if len(transacoes[transacoes['valor'] < 0]) > 0 else 0
                },
                'categorias_top': despesas_por_cat.to_dict() if not despesas_por_cat.empty else {},
                'evolucao_mensal': evolucao.to_dict('records') if not evolucao.empty else [],
                'transacoes_recentes': transacoes.head(20).to_dict('records') if not transacoes.empty else [],
                'estatisticas_usuario': stats_usuario,
                'tendencias': tendencias,
                'health_check': self.db.health_check()
            }
        
        return ExceptionHandler.safe_execute(            func=_load_dashboard,
            error_handler=ExceptionHandler.handle_generic_error,
            default_return={'erro': True}
        )
    
    def _analisar_tendencias(self, transacoes_df: pd.DataFrame) -> Dict[str, Any]:
        """Análise de tendências baseada nos dados"""
        if transacoes_df.empty:
            return {}
        
        try:
            # Converter data para datetime e valor para numeric
            transacoes_df['data'] = pd.to_datetime(transacoes_df['data'])
            transacoes_df['valor'] = pd.to_numeric(transacoes_df['valor'], errors='coerce')
            transacoes_df = transacoes_df.dropna(subset=['valor'])
            
            # Agrupar por semana
            transacoes_df['semana'] = transacoes_df['data'].dt.isocalendar().week
            gastos_semanais = transacoes_df[transacoes_df['valor'] < 0].groupby('semana')['valor'].sum().abs()
            
            # Calcular tendência
            if len(gastos_semanais) >= 2:
                variacao = ((gastos_semanais.iloc[-1] - gastos_semanais.iloc[0]) / gastos_semanais.iloc[0] * 100)
                tendencia = 'alta' if variacao > 5 else 'baixa' if variacao < -5 else 'estavel'
            else:
                variacao = 0
                tendencia = 'estavel'
            
            # Categoria com maior crescimento
            cat_crescimento = transacoes_df[transacoes_df['valor'] < 0].groupby(['categoria', 'semana'])['valor'].sum().abs()
            cat_tendencias = {}
            
            for categoria in cat_crescimento.index.get_level_values(0).unique():
                cat_data = cat_crescimento[categoria]
                if len(cat_data) >= 2:
                    cat_var = ((cat_data.iloc[-1] - cat_data.iloc[0]) / cat_data.iloc[0] * 100)
                    cat_tendencias[categoria] = cat_var
            
            categoria_maior_crescimento = max(cat_tendencias.items(), key=lambda x: x[1]) if cat_tendencias else ('N/A', 0)
            
            return {
                'gasto_semanal_variacao': round(variacao, 2),
                'tendencia_geral': tendencia,
                'categoria_maior_crescimento': categoria_maior_crescimento[0],
                'categoria_crescimento_pct': round(categoria_maior_crescimento[1], 2),
                'gastos_semanais': gastos_semanais.to_dict()
            }
            
        except Exception as e:
            self.logger.error(f"Erro na análise de tendências: {e}")
            return {}
    
    def aplicar_categorizacao_ia_lote(self, user_id: int, limite: int = 50, 
                                    usar_cache: bool = True, confianca_minima: float = 0.7) -> Dict[str, Any]:
        """Categorização em lote com cache de IA e otimizações"""
        def _process_batch():
            # Obter transações sem categoria
            transacoes_sem_categoria = self.transacao_repo.obter_transacoes_sem_categoria(user_id, limite)
            
            if transacoes_sem_categoria.empty:
                return {
                    'processadas': 0,
                    'cache_hits': 0,
                    'novas_categorizacoes': 0,
                    'aplicadas': 0,
                    'status': 'nenhuma_pendente'
                }
            
            cache_hits = 0
            novas_categorizacoes = 0
            aplicadas = 0
            
            mapeamento_categorias = {}
            sugestoes_para_cache = []
            
            for _, transacao in transacoes_sem_categoria.iterrows():
                descricao = transacao['descricao']
                hash_transacao = transacao['hash_transacao']
                
                categoria_sugerida = None
                
                # Verificar cache primeiro se habilitado
                if usar_cache:
                    cache_result = self.cache_ia_repo.obter_sugestao_cache(user_id, descricao)
                    
                    if cache_result and cache_result['aprovada'] and cache_result['confianca'] >= confianca_minima:
                        # Cache hit - usar categoria do cache
                        categoria_sugerida = cache_result['categoria_sugerida']
                        cache_hits += 1
                
                # Se não encontrou no cache, processar com IA
                if not categoria_sugerida:
                    categoria_sugerida, confianca = self._categorizar_com_ia_mock(descricao)
                    
                    if categoria_sugerida and confianca >= confianca_minima:
                        # Salvar no cache
                        sugestoes_para_cache.append({
                            'descricao': descricao,
                            'categoria': categoria_sugerida,
                            'confianca': confianca
                        })
                        novas_categorizacoes += 1
                
                # Aplicar categorização se confiança suficiente
                if categoria_sugerida:
                    mapeamento_categorias[hash_transacao] = categoria_sugerida
                    aplicadas += 1
            
            # Salvar sugestões no cache em lote
            if sugestoes_para_cache:
                self.cache_ia_repo.salvar_sugestoes_lote(user_id, sugestoes_para_cache)
            
            # Aplicar categorizações em lote
            if mapeamento_categorias:
                self.transacao_repo.atualizar_categoria_lote(user_id, mapeamento_categorias)
            
            # Log da operação
            self.log_repo.log_action(
                user_id, 'categorizacao_ia_lote',
                f'Processadas: {len(transacoes_sem_categoria)}, Aplicadas: {aplicadas}'
            )
            
            return {
                'processadas': len(transacoes_sem_categoria),
                'cache_hits': cache_hits,
                'novas_categorizacoes': novas_categorizacoes,
                'aplicadas': aplicadas,
                'status': 'sucesso',
                'confianca_minima_usada': confianca_minima
            }
        
        return ExceptionHandler.safe_execute(
            func=_process_batch,
            error_handler=ExceptionHandler.handle_generic_error,
            default_return={'erro': True}
        )
    
    def _categorizar_com_ia_mock(self, descricao: str) -> Tuple[Optional[str], float]:
        """Mock da categorização por IA - substituir pela implementação real"""
        descricao_lower = descricao.lower()
        
        # Padrões simples para demonstração
        padroes = {
            'supermercado': ['supermercado', 'mercado', 'extra', 'carrefour', 'pao de acucar'],
            'combustivel': ['posto', 'gasolina', 'etanol', 'shell', 'ipiranga', 'petrobras'],
            'restaurante': ['restaurante', 'lanchonete', 'pizza', 'burger', 'mcdonald'],
            'farmacia': ['farmacia', 'drogaria', 'droga', 'remedios'],
            'transporte': ['uber', '99', 'taxi', 'metro', 'onibus', 'passagem'],
            'streaming': ['netflix', 'spotify', 'amazon prime', 'disney', 'youtube'],
            'banco': ['tarifa', 'anuidade', 'juros', 'iof', 'taxa'],
        }
        
        for categoria, palavras in padroes.items():
            for palavra in palavras:
                if palavra in descricao_lower:
                    return categoria.title(), 0.85
        
        # Retorna categoria padrão com baixa confiança
        return 'Outros', 0.3
    
    def obter_relatorio_avancado(self, user_id: int, data_inicio: str, data_fim: str, 
                                tipo_relatorio: str = 'completo') -> Dict[str, Any]:
        """Gera relatório avançado com análises detalhadas"""
        def _generate_report():            # Obter transações do período
            transacoes = self.transacao_repo.obter_transacoes_periodo(
                user_id, data_inicio, data_fim, incluir_excluidas=False
            )
            
            if transacoes.empty:
                return {
                    'tipo': tipo_relatorio,
                    'periodo': f'{data_inicio} a {data_fim}',
                    'mensagem': 'Nenhuma transação encontrada no período',
                    'dados': {}
                }
            
            # Garantir que valores estão em formato numérico
            transacoes['valor'] = pd.to_numeric(transacoes['valor'], errors='coerce')
            transacoes = transacoes.dropna(subset=['valor'])
            
            # Análises básicas
            receitas = transacoes[transacoes['valor'] > 0]['valor'].sum()
            despesas = abs(transacoes[transacoes['valor'] < 0]['valor'].sum())
            
            relatorio = {
                'tipo': tipo_relatorio,
                'periodo': f'{data_inicio} a {data_fim}',
                'resumo': {
                    'total_transacoes': len(transacoes),
                    'receitas': float(receitas),
                    'despesas': float(despesas),
                    'saldo': float(receitas - despesas),
                    'ticket_medio': float(despesas / len(transacoes[transacoes['valor'] < 0])) if len(transacoes[transacoes['valor'] < 0]) > 0 else 0
                }
            }
            
            if tipo_relatorio in ['completo', 'categorias']:
                # Análise por categorias
                cat_analysis = transacoes.groupby('categoria').agg({
                    'valor': ['count', 'sum', 'mean'],
                    'data': ['min', 'max']
                }).round(2)
                
                relatorio['analise_categorias'] = cat_analysis.to_dict()
            
            if tipo_relatorio in ['completo', 'temporal']:
                # Análise temporal
                transacoes['data'] = pd.to_datetime(transacoes['data'])
                transacoes['mes'] = transacoes['data'].dt.to_period('M')
                
                temporal_analysis = transacoes.groupby('mes').agg({
                    'valor': ['count', 'sum'],
                    'categoria': 'nunique'
                })
                
                relatorio['analise_temporal'] = temporal_analysis.to_dict()
            
            if tipo_relatorio in ['completo', 'deteccao_anomalias']:
                # Detecção de anomalias
                anomalias = self._detectar_anomalias(transacoes)
                relatorio['anomalias'] = anomalias
            
            return relatorio
        
        return ExceptionHandler.safe_execute(
            func=_generate_report,
            error_handler=ExceptionHandler.handle_generic_error,
            default_return={'erro': True}
        )
    
    def _detectar_anomalias(self, transacoes_df: pd.DataFrame) -> Dict[str, List]:
        """Detecta transações anômalas"""
        anomalias = {
            'valores_altos': [],
            'duplicatas_suspeitas': [],
            'frequencia_anormal': []
        }
        
        try:
            # Detectar valores muito altos (outliers)
            despesas = transacoes_df[transacoes_df['valor'] < 0]['valor'].abs()
            if not despesas.empty:
                q75, q25 = despesas.quantile([0.75, 0.25])
                iqr = q75 - q25
                threshold = q75 + 1.5 * iqr
                
                valores_altos = transacoes_df[
                    (transacoes_df['valor'] < 0) & 
                    (transacoes_df['valor'].abs() > threshold)
                ]
                
                anomalias['valores_altos'] = valores_altos[['data', 'descricao', 'valor']].to_dict('records')
            
            # Detectar possíveis duplicatas
            duplicatas = self.transacao_repo.obter_duplicatas_potenciais(
                transacoes_df['id'].iloc[0] if not transacoes_df.empty else 0  # user_id aproximado
            )
            
            if not duplicatas.empty:
                anomalias['duplicatas_suspeitas'] = duplicatas.to_dict('records')            # Detectar frequência anormal por categoria (versão básica)
            try:
                # Simples contagem por categoria
                cat_counts = transacoes_df['categoria'].value_counts()
                anomalias_freq = []
                
                # Se uma categoria tem mais de 20 transações, pode ser interessante
                for categoria, count in cat_counts.items():
                    if count > 20:
                        anomalias_freq.append({
                            'categoria': str(categoria),
                            'total_transacoes': int(count),
                            'tipo': 'alta_frequencia'
                        })
                
                if anomalias_freq:
                    anomalias['frequencia_anormal'] = anomalias_freq
                    
            except Exception:
                # Se der erro, apenas ignora essa detecção
                pass
                
        except Exception as e:
            self.logger.error(f"Erro na detecção de anomalias: {e}")
        
        return anomalias
    
    def aplicar_regras_negocio(self, user_id: int, regras: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aplica regras de negócio personalizadas"""
        def _apply_rules():
            aplicadas = 0
            erros = []
            
            for regra in regras:
                try:
                    if regra['tipo'] == 'categorizacao_automatica':
                        # Aplicar categorização baseada em padrão
                        padrao = regra['padrao']
                        categoria = regra['categoria']
                        
                        # Buscar transações que correspondem ao padrão
                        transacoes = self.db.executar_query("""
                            SELECT hash_transacao FROM transacoes 
                            WHERE user_id = ? AND descricao LIKE ? AND categoria = 'Outros'
                        """, [user_id, f'%{padrao}%'])
                        
                        if transacoes:
                            mapeamento = {t['hash_transacao']: categoria for t in transacoes}
                            self.transacao_repo.atualizar_categoria_lote(user_id, mapeamento)
                            aplicadas += len(mapeamento)
                    
                    elif regra['tipo'] == 'exclusao_automatica':
                        # Excluir transações baseadas em critério
                        criterio = regra['criterio']
                        
                        # Implementar lógica de exclusão baseada no critério
                        # (exemplo simplificado)
                        pass
                    
                except Exception as e:
                    erros.append(f"Erro na regra {regra.get('nome', 'sem nome')}: {str(e)}")
            
            return {
                'regras_processadas': len(regras),
                'transacoes_afetadas': aplicadas,
                'erros': erros,
                'status': 'sucesso' if not erros else 'sucesso_com_erros'
            }
        
        return ExceptionHandler.safe_execute(
            func=_apply_rules,
            error_handler=ExceptionHandler.handle_generic_error,
            default_return={'erro': True}
        )
    
    def migrar_dados_json_para_db(self, user_id: int, dados_json_path: str) -> Dict[str, Any]:
        """Migra dados existentes do formato JSON para o banco de dados"""
        def _migrate_data():
            migradas = 0
            erros = []
            
            try:
                # Carregar dados JSON existentes
                if os.path.exists(dados_json_path):
                    with open(dados_json_path, 'r', encoding='utf-8') as f:
                        dados_json = json.load(f)
                    
                    # Migrar transações
                    if 'transacoes' in dados_json:
                        transacoes_para_migrar = []
                        
                        for transacao in dados_json['transacoes']:
                            transacao_data = {
                                'data': transacao.get('Data'),
                                'descricao': transacao.get('Descrição'),
                                'valor': float(transacao.get('Valor', 0)),
                                'categoria': transacao.get('Categoria', 'Outros'),
                                'origem': 'migração_json',
                                'conta': transacao.get('Conta', ''),
                                'arquivo_origem': 'migração'
                            }
                            transacoes_para_migrar.append(transacao_data)
                        
                        if transacoes_para_migrar:
                            migradas = self.transacao_repo.criar_transacoes_lote(user_id, transacoes_para_migrar)
                    
                    # Migrar categorias personalizadas
                    if 'categorias_personalizadas' in dados_json:
                        for categoria in dados_json['categorias_personalizadas']:
                            try:
                                self.categoria_repo.criar_categoria_personalizada(
                                    user_id, categoria['nome'], categoria.get('cor'), categoria.get('icone')
                                )
                            except Exception as e:
                                erros.append(f"Erro ao migrar categoria {categoria.get('nome')}: {str(e)}")
                    
                    # Migrar descrições personalizadas
                    if 'descricoes_personalizadas' in dados_json:
                        mapeamento_descricoes = {}
                        for hash_trans, descricao in dados_json['descricoes_personalizadas'].items():
                            mapeamento_descricoes[hash_trans] = descricao
                        
                        if mapeamento_descricoes:
                            self.descricao_repo.salvar_descricoes_lote(user_id, mapeamento_descricoes)
                    
                    # Migrar exclusões
                    if 'transacoes_excluidas' in dados_json:
                        hashes_excluidas = list(dados_json['transacoes_excluidas'])
                        if hashes_excluidas:
                            self.exclusao_repo.excluir_transacoes_lote(user_id, hashes_excluidas, 'Migração JSON')
                    
                    # Log da migração
                    self.log_repo.log_action(
                        user_id, 'migracao_dados',
                        f'Migradas {migradas} transações de {dados_json_path}'
                    )
                    
                    return {
                        'migradas': migradas,
                        'erros': erros,
                        'status': 'sucesso',
                        'arquivo_origem': dados_json_path
                    }
                
                else:
                    return {
                        'migradas': 0,
                        'erros': ['Arquivo JSON não encontrado'],
                        'status': 'arquivo_nao_encontrado'
                    }
                    
            except Exception as e:
                erros.append(f"Erro geral na migração: {str(e)}")
                return {
                    'migradas': migradas,
                    'erros': erros,
                    'status': 'erro'
                }
        
        return ExceptionHandler.safe_execute(
            func=_migrate_data,
            error_handler=ExceptionHandler.handle_generic_error,
            default_return={'erro': True}
        )
    
    def obter_metricas_performance(self) -> Dict[str, Any]:
        """Obtém métricas de performance do sistema"""
        return {
            'database_health': self.db.health_check(),
            'cache_stats': {
                'hit_ratio': self.db._calculate_cache_hit_ratio(),
                'cache_size': len(self.db._query_cache)
            },
            'statistics': self.db.obter_estatisticas_db()
        }
    
    def cleanup_and_optimize(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Executa limpeza e otimização do banco de dados"""
        def _cleanup():
            operacoes_realizadas = []
            
            # Backup antes da limpeza
            backup_path = self.db.backup_database()
            operacoes_realizadas.append(f"Backup criado: {backup_path}")
            
            # Vacuum do banco
            with self.db.get_connection() as conn:
                conn.execute("VACUUM")
            operacoes_realizadas.append("VACUUM executado")
            
            # Limpar logs antigos (mais de 30 dias)
            logs_removidos = self.db.executar_update("""
                DELETE FROM system_logs 
                WHERE timestamp < date('now', '-30 days')
            """)
            operacoes_realizadas.append(f"Logs antigos removidos: {logs_removidos}")
            
            # Reindexar tabelas
            with self.db.get_connection() as conn:
                conn.execute("REINDEX")
            operacoes_realizadas.append("Reindex executado")
            
            return {
                'status': 'sucesso',
                'operacoes': operacoes_realizadas,
                'backup_path': backup_path
            }
        
        return ExceptionHandler.safe_execute(
            func=_cleanup,
            error_handler=ExceptionHandler.handle_generic_error,
            default_return={'erro': True}
        )
    
    def listar_transacoes_usuario(self, usuario: str, limite: int = 1000) -> pd.DataFrame:
        """Lista todas as transações de um usuário"""
        try:            # Buscar usuário pelo username
            user_data = self.usuario_repo.obter_usuario_por_username(usuario)
            if not user_data:
                return pd.DataFrame()
            
            user_id = user_data['id']
            
            # Usar método do repository para obter transações
            from datetime import datetime, timedelta
            data_fim = datetime.now().strftime('%Y-%m-%d')
            data_inicio = (datetime.now() - timedelta(days=365*2)).strftime('%Y-%m-%d')  # 2 anos
            
            return self.transacao_repo.obter_transacoes_periodo(
                user_id, data_inicio, data_fim, 
                categorias=None, incluir_excluidas=False, limite=limite
            )
            
        except Exception as e:
            self.logger.error(f"Erro ao listar transações do usuário {usuario}: {e}")
            return pd.DataFrame()
    
    def listar_transacoes_cartao(self, usuario: str, dias_limite: int = 365) -> pd.DataFrame:
        """Lista transações de cartão de crédito de um usuário"""
        try:
            # Buscar todas as transações do usuário
            df_todas = self.listar_transacoes_usuario(usuario, limite=5000)
            
            if df_todas.empty:
                return pd.DataFrame()
            
            # Filtrar apenas transações de cartão (origem contém 'fatura' ou 'cartao')
            mask_cartao = (
                df_todas['origem'].str.contains('fatura', case=False, na=False) |
                df_todas['origem'].str.contains('cartao', case=False, na=False) |
                df_todas['origem'].str.contains('credit', case=False, na=False)
            )
            
            df_cartao = df_todas[mask_cartao].copy()
            
            # Filtrar por período se especificado
            if dias_limite > 0:
                from datetime import datetime, timedelta
                data_limite = datetime.now() - timedelta(days=dias_limite)
                df_cartao = df_cartao[pd.to_datetime(df_cartao['data']) >= data_limite]
            
            # Converter colunas para o formato esperado pela página Cartão (compatibilidade)
            if not df_cartao.empty:
                df_cartao = df_cartao.rename(columns={
                    'data': 'Data',
                    'descricao': 'Descrição',
                    'valor': 'Valor',
                    'categoria': 'Categoria',
                    'origem': 'Origem'
                })
            
            return df_cartao
            
        except Exception as e:
            self.logger.error(f"Erro ao listar transações de cartão do usuário {usuario}: {e}")
            return pd.DataFrame()
    
    def calcular_saldos_por_origem(self, usuario: str) -> Dict[str, Dict[str, Any]]:
        """Calcula saldos agrupados por origem para um usuário"""
        try:
            df_transacoes = self.listar_transacoes_usuario(usuario)
            
            if df_transacoes.empty:
                return {}
            
            # Agrupar por origem e calcular saldos
            saldos = {}
            for origem in df_transacoes['Origem'].unique():
                df_origem = df_transacoes[df_transacoes['Origem'] == origem]
                saldo_total = df_origem['Valor'].sum()
                
                # Determinar tipo (conta corrente ou cartão)
                tipo = 'credit_card' if any(
                    palavra in origem.lower() 
                    for palavra in ['fatura', 'cartao', 'credit', 'nubank']
                ) else 'checking'
                
                saldos[origem] = {
                    'saldo_total': saldo_total,
                    'tipo': tipo,
                    'total_transacoes': len(df_origem),
                    'ultima_transacao': df_origem['Data'].max() if not df_origem.empty else None
                }
            
            return saldos
            
        except Exception as e:
            self.logger.error(f"Erro ao calcular saldos por origem do usuário {usuario}: {e}")
            return {}
    
    def processar_categorizacao_ai(self, usuario: str) -> Dict[str, Any]:
        """Processa categorização automática com IA para um usuário"""
        try:
            user_data = self.usuario_repo.obter_usuario_por_username(usuario)
            if not user_data:
                return {'success': False, 'error': 'Usuário não encontrado'}
            
            user_id = user_data['id']
            
            # Usar método existente do serviço
            resultado = self.aplicar_categorizacao_ia_lote(user_id, limite=100)
            
            return {
                'success': True,
                'categorized_count': resultado.get('categorized_count', 0),
                'message': f"Categorização concluída: {resultado.get('categorized_count', 0)} transações processadas"
            }
            
        except Exception as e:
            self.logger.error(f"Erro na categorização IA para usuário {usuario}: {e}")
            return {'success': False, 'error': str(e)}
    
    def detectar_anomalias_usuario(self, usuario: str) -> List[Dict[str, Any]]:
        """Detecta anomalias nas transações de um usuário"""
        try:
            df_transacoes = self.listar_transacoes_usuario(usuario)
            
            if df_transacoes.empty:
                return []
            
            # Usar método interno de detecção de anomalias
            anomalias_dict = self._detectar_anomalias(df_transacoes)
            
            # Converter para formato esperado pelo frontend
            anomalias_list = []
            for tipo, anomalias in anomalias_dict.items():
                for anomalia in anomalias:
                    anomalias_list.append({
                        'tipo': tipo,
                        'descricao': anomalia.get('descricao', 'N/A'),
                        'motivo': anomalia.get('motivo', 'N/A'),
                        'valor': anomalia.get('valor', 0),
                        'data': anomalia.get('data', '')
                    })
            
            return anomalias_list
            
        except Exception as e:
            self.logger.error(f"Erro na detecção de anomalias para usuário {usuario}: {e}")
            return []
    
    def gerar_relatorio_tendencias(self, usuario: str) -> Dict[str, Any]:
        """Gera relatório de tendências para um usuário"""
        try:
            user_data = self.usuario_repo.obter_usuario_por_username(usuario)
            if not user_data:
                return {'success': False, 'error': 'Usuário não encontrado'}
            
            user_id = user_data['id']
            
            # Usar método existente para obter dados do dashboard
            dashboard_data = self.obter_dashboard_data(user_id, periodo_meses=6)
            
            # Extrair métricas de tendências
            metricas = {}
            if 'insights' in dashboard_data:
                insights = dashboard_data['insights']
                metricas = {
                    'crescimento_mensal': insights.get('crescimento_gastos', 0),
                    'categoria_dominante': insights.get('categoria_mais_gasta', 'N/A'),
                    'padrao_gastos': insights.get('padrao_semanal', 'N/A'),
                    'economia_potencial': insights.get('economia_potencial', 0)
                }
            
            return {
                'success': True,
                'metricas': metricas,
                'message': 'Relatório de tendências gerado com sucesso'
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao gerar relatório de tendências para usuário {usuario}: {e}")
            return {'success': False, 'error': str(e)}
    
    def importar_ofx_file(self, username: str, file_path: str, tipo: str = 'extrato') -> int:
        """
        Importa arquivo OFX específico para um usuário (método simplificado para migração)
        
        Args:
            username: Nome do usuário
            file_path: Caminho para o arquivo OFX
            tipo: Tipo do arquivo ('extrato' ou 'fatura')
            
        Returns:
            Número de transações importadas
        """
        try:
            # Verificar se usuário existe
            user_data = self.usuario_repo.obter_usuario_por_username(username)
            if not user_data:
                self.logger.error(f"Usuário {username} não encontrado")
                return 0
            
            user_id = user_data.get('id')
            if not user_id:
                self.logger.error(f"ID do usuário {username} não encontrado")
                return 0
            
            # Verificar se arquivo existe
            if not os.path.exists(file_path):
                self.logger.error(f"Arquivo não encontrado: {file_path}")
                return 0
            
            # Importar usando o método existente (versão simplificada)
            resultado = self.importar_ofx_arquivo(user_id, file_path, tipo)
            
            # Retornar número de transações importadas
            if resultado.get('status') == 'sucesso':
                return resultado.get('importadas', 0)
            else:
                self.logger.error(f"Erro na importação: {resultado.get('erro', 'Erro desconhecido')}")
                return 0
                
        except Exception as e:
            self.logger.error(f"Erro ao importar arquivo OFX {file_path}: {e}")
            return 0
