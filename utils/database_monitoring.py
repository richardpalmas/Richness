"""
Utilitários de monitoramento e configuração para o banco de dados otimizado.
Inclui health checks, métricas, configurações e alertas.
"""

import sqlite3
import time
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd
import logging
from pathlib import Path
import threading

class DatabaseMonitor:
    """Monitor para saúde e performance do banco de dados"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
        self.metrics_history = []
        self.alerts = []
        self._monitoring_active = False
        self._monitor_thread = None
    
    def start_monitoring(self, interval_seconds: int = 300):
        """Inicia monitoramento contínuo"""
        if self._monitoring_active:
            return
        
        self._monitoring_active = True
        self._monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval_seconds,),
            daemon=True
        )
        self._monitor_thread.start()
        self.logger.info(f"Monitoramento iniciado (intervalo: {interval_seconds}s)")
    
    def stop_monitoring(self):
        """Para o monitoramento"""
        self._monitoring_active = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        self.logger.info("Monitoramento parado")
    
    def _monitoring_loop(self, interval_seconds: int):
        """Loop principal do monitoramento"""
        while self._monitoring_active:
            try:
                metrics = self.collect_metrics()
                self.metrics_history.append(metrics)
                
                # Manter apenas últimas 100 métricas
                if len(self.metrics_history) > 100:
                    self.metrics_history = self.metrics_history[-100:]
                
                # Verificar alertas
                self._check_alerts(metrics)
                
                time.sleep(interval_seconds)
                
            except Exception as e:
                self.logger.error(f"Erro no monitoramento: {e}")
                time.sleep(interval_seconds)
    
    def collect_metrics(self) -> Dict[str, Any]:
        """Coleta métricas detalhadas do sistema"""
        start_time = time.time()
        
        # Health check básico
        health = self.db.health_check()
        
        # Estatísticas do banco
        stats = self.db.obter_estatisticas_db()
        
        # Métricas de performance
        performance_metrics = {
            'connection_pool_usage': len(self.db._connection_pool) / self.db.pool_size * 100,
            'cache_hit_ratio': self.db._calculate_cache_hit_ratio(),
            'queries_per_minute': self._calculate_query_rate(),
            'average_query_time': self._calculate_avg_query_time(),
            'database_size_growth': self._calculate_db_growth(),
        }
        
        # Métricas de sistema
        db_path = Path(self.db.db_path)
        system_metrics = {
            'disk_usage_mb': db_path.stat().st_size / (1024 * 1024) if db_path.exists() else 0,
            'wal_size_mb': self._get_wal_size(),
            'last_backup_age_hours': self._get_backup_age(),
        }
        
        collection_time = time.time() - start_time
        
        return {
            'timestamp': datetime.now().isoformat(),
            'collection_time_ms': round(collection_time * 1000, 2),
            'health': health,
            'statistics': stats,
            'performance': performance_metrics,
            'system': system_metrics
        }
    
    def _calculate_query_rate(self) -> float:
        """Calcula taxa de queries por minuto"""
        if len(self.metrics_history) < 2:
            return 0.0
        
        current = self.db._health_stats['queries_executed']
        previous_metric = self.metrics_history[-1] if self.metrics_history else None
        
        if previous_metric:
            previous = previous_metric.get('health', {}).get('performance_stats', {}).get('queries_executed', 0)
            time_diff_minutes = 5  # Assumindo coleta a cada 5 minutos
            return (current - previous) / time_diff_minutes
        
        return 0.0
    
    def _calculate_avg_query_time(self) -> float:
        """Calcula tempo médio de query (estimado)"""
        # Implementação simplificada - poderia ser mais sofisticada
        return 5.0  # ms estimado
    
    def _calculate_db_growth(self) -> float:
        """Calcula crescimento do banco em MB/dia"""
        if len(self.metrics_history) < 2:
            return 0.0
        
        current_size = self.metrics_history[-1]['system']['disk_usage_mb']
        previous_size = self.metrics_history[-2]['system']['disk_usage_mb']
        
        # Crescimento por coleta * coletas por dia (estimado)
        growth_per_collection = current_size - previous_size
        collections_per_day = 24 * 60 / 5  # Assumindo coleta a cada 5 minutos
        
        return growth_per_collection * collections_per_day
    
    def _get_wal_size(self) -> float:
        """Obtém tamanho do arquivo WAL"""
        wal_path = Path(self.db.db_path + '-wal')
        return wal_path.stat().st_size / (1024 * 1024) if wal_path.exists() else 0.0
    
    def _get_backup_age(self) -> float:
        """Obtém idade do último backup em horas"""
        last_backup = self.db._health_stats.get('last_backup')
        if last_backup:
            return (datetime.now() - last_backup).total_seconds() / 3600
        return 999.0  # Valor alto se nunca teve backup
    
    def _check_alerts(self, metrics: Dict[str, Any]):
        """Verifica condições de alerta"""
        alerts = []
        
        # Alertas de performance
        if metrics['performance']['cache_hit_ratio'] < 50:
            alerts.append({
                'level': 'warning',
                'message': f"Cache hit ratio baixo: {metrics['performance']['cache_hit_ratio']:.1f}%",
                'timestamp': metrics['timestamp']
            })
        
        if metrics['performance']['connection_pool_usage'] > 90:
            alerts.append({
                'level': 'warning',
                'message': f"Pool de conexões quase cheio: {metrics['performance']['connection_pool_usage']:.1f}%",
                'timestamp': metrics['timestamp']
            })
        
        # Alertas de sistema
        if metrics['system']['disk_usage_mb'] > 1000:  # 1GB
            alerts.append({
                'level': 'info',
                'message': f"Banco de dados grande: {metrics['system']['disk_usage_mb']:.1f} MB",
                'timestamp': metrics['timestamp']
            })
        
        if metrics['system']['last_backup_age_hours'] > 24:
            alerts.append({
                'level': 'error',
                'message': f"Backup antigo: {metrics['system']['last_backup_age_hours']:.1f} horas",
                'timestamp': metrics['timestamp']
            })
        
        if metrics['system']['wal_size_mb'] > 100:
            alerts.append({
                'level': 'warning',
                'message': f"Arquivo WAL grande: {metrics['system']['wal_size_mb']:.1f} MB",
                'timestamp': metrics['timestamp']
            })
        
        # Alertas de saúde
        if metrics['health']['status'] != 'healthy':
            alerts.append({
                'level': 'error',
                'message': f"Banco não saudável: {metrics['health']['status']}",
                'timestamp': metrics['timestamp']
            })
        
        # Adicionar novos alertas
        for alert in alerts:
            self.alerts.append(alert)
            self.logger.warning(f"ALERT [{alert['level']}]: {alert['message']}")
        
        # Manter apenas últimos 50 alertas
        if len(self.alerts) > 50:
            self.alerts = self.alerts[-50:]
    
    def get_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """Gera relatório de performance das últimas X horas"""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        recent_metrics = [
            m for m in self.metrics_history
            if datetime.fromisoformat(m['timestamp']) > cutoff
        ]
        
        if not recent_metrics:
            return {'error': 'Dados insuficientes para relatório'}
        
        # Calcular médias e tendências
        cache_ratios = [m['performance']['cache_hit_ratio'] for m in recent_metrics]
        query_rates = [m['performance']['queries_per_minute'] for m in recent_metrics]
        db_sizes = [m['system']['disk_usage_mb'] for m in recent_metrics]
        
        return {
            'period_hours': hours,
            'metrics_collected': len(recent_metrics),
            'performance_summary': {
                'avg_cache_hit_ratio': sum(cache_ratios) / len(cache_ratios) if cache_ratios else 0,
                'avg_queries_per_minute': sum(query_rates) / len(query_rates) if query_rates else 0,
                'database_growth_mb': db_sizes[-1] - db_sizes[0] if len(db_sizes) >= 2 else 0,
            },
            'alerts_summary': {
                'total_alerts': len([a for a in self.alerts if datetime.fromisoformat(a['timestamp']) > cutoff]),
                'error_alerts': len([a for a in self.alerts if a['level'] == 'error' and datetime.fromisoformat(a['timestamp']) > cutoff]),
                'warning_alerts': len([a for a in self.alerts if a['level'] == 'warning' and datetime.fromisoformat(a['timestamp']) > cutoff]),
            },
            'recent_alerts': [a for a in self.alerts if datetime.fromisoformat(a['timestamp']) > cutoff][-10:]
        }

class DatabaseOptimizer:
    """Otimizador automático para o banco de dados"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
    
    def analyze_and_optimize(self) -> Dict[str, Any]:
        """Analisa e otimiza automaticamente o banco"""
        optimizations = []
        
        # Analisar uso de índices
        index_analysis = self._analyze_index_usage()
        if index_analysis['suggestions']:
            optimizations.extend(index_analysis['suggestions'])
        
        # Analisar fragmentação
        fragmentation = self._analyze_fragmentation()
        if fragmentation['needs_vacuum']:
            optimizations.append("VACUUM recomendado devido à fragmentação")
        
        # Analisar estatísticas
        stats_analysis = self._analyze_statistics()
        optimizations.extend(stats_analysis['suggestions'])
        
        # Aplicar otimizações automáticas seguras
        applied_optimizations = self._apply_safe_optimizations()
        
        return {
            'analysis_timestamp': datetime.now().isoformat(),
            'suggestions': optimizations,
            'applied_automatically': applied_optimizations,
            'index_analysis': index_analysis,
            'fragmentation_analysis': fragmentation,
            'statistics_analysis': stats_analysis
        }
    
    def _analyze_index_usage(self) -> Dict[str, Any]:
        """Analisa uso dos índices"""
        try:
            # Verificar estatísticas de índices (SQLite tem limitações aqui)
            with self.db.get_connection() as conn:
                # Verificar integridade dos índices
                integrity = conn.execute("PRAGMA integrity_check").fetchall()
                
                # Obter lista de índices
                indexes = conn.execute("""
                    SELECT name, sql FROM sqlite_master 
                    WHERE type = 'index' AND name NOT LIKE 'sqlite_%'
                """).fetchall()
            
            suggestions = []
            
            # Verificações básicas
            if len(indexes) < 10:
                suggestions.append("Considere adicionar mais índices para melhorar performance")
            
            return {
                'total_indexes': len(indexes),
                'integrity_ok': integrity[0][0] == 'ok' if integrity else False,
                'suggestions': suggestions
            }
            
        except Exception as e:
            self.logger.error(f"Erro na análise de índices: {e}")
            return {'error': str(e), 'suggestions': []}
    
    def _analyze_fragmentation(self) -> Dict[str, Any]:
        """Analisa fragmentação do banco"""
        try:
            with self.db.get_connection() as conn:
                # Obter informações sobre páginas
                page_count = conn.execute("PRAGMA page_count").fetchone()[0]
                freelist_count = conn.execute("PRAGMA freelist_count").fetchone()[0]
                
                fragmentation_ratio = freelist_count / page_count if page_count > 0 else 0
                
                return {
                    'page_count': page_count,
                    'freelist_count': freelist_count,
                    'fragmentation_ratio': fragmentation_ratio,
                    'needs_vacuum': fragmentation_ratio > 0.1  # 10% de fragmentação
                }
                
        except Exception as e:
            self.logger.error(f"Erro na análise de fragmentação: {e}")
            return {'error': str(e), 'needs_vacuum': False}
    
    def _analyze_statistics(self) -> Dict[str, Any]:
        """Analisa estatísticas das tabelas"""
        try:
            stats = self.db.obter_estatisticas_db()
            suggestions = []
            
            # Verificar crescimento das tabelas
            if stats.get('total_transacoes', 0) > 10000:
                suggestions.append("Considere arquivamento de transações antigas")
            
            if stats.get('total_system_logs', 0) > 5000:
                suggestions.append("Limpar logs antigos do sistema")
            
            if stats.get('database_size_mb', 0) > 500:
                suggestions.append("Banco de dados grande - considere backup e limpeza")
            
            return {
                'database_stats': stats,
                'suggestions': suggestions
            }
            
        except Exception as e:
            self.logger.error(f"Erro na análise de estatísticas: {e}")
            return {'error': str(e), 'suggestions': []}
    
    def _apply_safe_optimizations(self) -> List[str]:
        """Aplica otimizações seguras automaticamente"""
        applied = []
        
        try:
            # Atualizar estatísticas das tabelas
            with self.db.get_connection() as conn:
                conn.execute("ANALYZE")
            applied.append("ANALYZE executado")
            
            # Limpar cache de query se muito grande
            if len(self.db._query_cache) > 1000:
                with self.db._cache_lock:
                    # Manter apenas os 200 mais recentes
                    items = list(self.db._query_cache.items())[-200:]
                    self.db._query_cache = dict(items)
                applied.append("Cache de queries otimizado")
            
        except Exception as e:
            self.logger.error(f"Erro ao aplicar otimizações: {e}")
        
        return applied

class ConfigurationManager:
    """Gerenciador de configurações do banco de dados"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.config_file = "database_config.json"
        self.logger = logging.getLogger(__name__)
        self.default_config = {
            'backup': {
                'auto_backup_enabled': True,
                'backup_interval_hours': 24,
                'max_backups_to_keep': 7,
                'backup_directory': 'backups'
            },
            'performance': {
                'cache_size': 10000,
                'connection_pool_size': 5,
                'query_timeout_seconds': 30,
                'enable_query_cache': True,
                'max_query_cache_size': 500
            },
            'monitoring': {
                'monitoring_enabled': True,
                'monitoring_interval_seconds': 300,
                'alert_thresholds': {
                    'cache_hit_ratio_min': 50,
                    'connection_pool_usage_max': 90,
                    'backup_age_max_hours': 24,
                    'wal_size_max_mb': 100,
                    'database_size_warning_mb': 1000
                }
            },
            'maintenance': {
                'auto_vacuum_enabled': True,
                'vacuum_frequency_days': 7,
                'auto_cleanup_logs_days': 30,
                'auto_optimize_enabled': True,
                'optimize_frequency_hours': 168  # 1 semana
            }
        }
    
    def load_config(self) -> Dict[str, Any]:
        """Carrega configurações do arquivo"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # Mesclar com configurações padrão
                return self._merge_configs(self.default_config, config)
            else:
                return self.default_config.copy()
                
        except Exception as e:
            self.logger.error(f"Erro ao carregar configurações: {e}")
            return self.default_config.copy()
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """Salva configurações no arquivo"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            self.logger.error(f"Erro ao salvar configurações: {e}")
            return False
    
    def _merge_configs(self, default: Dict, user: Dict) -> Dict:
        """Mescla configurações do usuário com as padrão"""
        result = default.copy()
        
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def apply_config(self, config: Dict[str, Any]) -> List[str]:
        """Aplica configurações ao banco de dados"""
        applied = []
        
        try:
            # Aplicar configurações de performance
            perf_config = config.get('performance', {})
            
            if 'connection_pool_size' in perf_config:
                self.db.pool_size = perf_config['connection_pool_size']
                applied.append(f"Pool size alterado para {self.db.pool_size}")
            
            if 'max_query_cache_size' in perf_config:
                max_cache = perf_config['max_query_cache_size']
                with self.db._cache_lock:
                    if len(self.db._query_cache) > max_cache:
                        items = list(self.db._query_cache.items())[-max_cache:]
                        self.db._query_cache = dict(items)
                applied.append(f"Cache de queries limitado a {max_cache}")
            
            # Aplicar configurações de backup
            backup_config = config.get('backup', {})
            if backup_config.get('auto_backup_enabled'):
                applied.append("Auto backup habilitado")
            
            return applied
            
        except Exception as e:
            self.logger.error(f"Erro ao aplicar configurações: {e}")
            return []

# Classe principal que integra todos os componentes
class DatabaseManagementSuite:
    """Suite completo de gerenciamento do banco de dados"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.monitor = DatabaseMonitor(db_manager)
        self.optimizer = DatabaseOptimizer(db_manager)
        self.config_manager = ConfigurationManager(db_manager)
        self.logger = logging.getLogger(__name__)
        
        # Carregar e aplicar configurações
        self.config = self.config_manager.load_config()
        self.config_manager.apply_config(self.config)
        
        # Iniciar monitoramento se habilitado
        if self.config.get('monitoring', {}).get('monitoring_enabled', True):
            interval = self.config.get('monitoring', {}).get('monitoring_interval_seconds', 300)
            self.monitor.start_monitoring(interval)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Obtém status completo do sistema"""
        return {
            'database_health': self.db.health_check(),
            'monitoring_status': {
                'active': self.monitor._monitoring_active,
                'metrics_collected': len(self.monitor.metrics_history),
                'recent_alerts': len(self.monitor.alerts),
            },
            'configuration': self.config,
            'last_optimization': getattr(self, '_last_optimization', 'Nunca'),
            'system_timestamp': datetime.now().isoformat()
        }
    
    def run_optimization(self) -> Dict[str, Any]:
        """Executa otimização completa"""
        result = self.optimizer.analyze_and_optimize()
        self._last_optimization = datetime.now().isoformat()
        return result
    
    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Gera relatório abrangente do sistema"""
        return {
            'system_status': self.get_system_status(),
            'performance_report': self.monitor.get_performance_report(24),
            'optimization_analysis': self.run_optimization(),
            'database_statistics': self.db.obter_estatisticas_db(),
            'configuration': self.config,
            'generated_at': datetime.now().isoformat()
        }
    
    def shutdown(self):
        """Finaliza todos os componentes"""
        self.monitor.stop_monitoring()
        self.config_manager.save_config(self.config)
        self.db.close_pool()
        self.logger.info("Database Management Suite finalizado")
