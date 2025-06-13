"""
Exemplo de integração das melhorias de banco de dados no Home.py
Este arquivo demonstra como usar as novas funcionalidades otimizadas.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any

# Imports das novas funcionalidades otimizadas
from utils.database_manager_v2 import DatabaseManager
from utils.repositories_v2 import (
    UsuarioRepository, TransacaoRepository, CategoriaRepository,
    DescricaoRepository, ExclusaoRepository, CacheIARepository
)
from services.transacao_service_v2 import TransacaoService
from utils.database_monitoring import DatabaseManagementSuite

# Configuração da página
st.set_page_config(
    page_title="Richness - Dashboard Financeiro",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicialização dos serviços otimizados (com cache)
@st.cache_resource
def init_services():
    """Inicializa serviços com cache para performance"""
    db = DatabaseManager()
    service = TransacaoService()
    monitoring = DatabaseManagementSuite(db)
    return db, service, monitoring

# Cache para dados do dashboard
@st.cache_data(ttl=300)  # Cache por 5 minutos
def load_dashboard_data(user_id: int, periodo_meses: int = 3) -> Dict[str, Any]:
    """Carrega dados do dashboard com cache otimizado"""
    _, service, _ = init_services()
    return service.obter_dashboard_data(user_id, periodo_meses)

@st.cache_data(ttl=600)  # Cache por 10 minutos
def load_advanced_analytics(user_id: int, data_inicio: str, data_fim: str) -> Dict[str, Any]:
    """Carrega análises avançadas com cache"""
    _, service, _ = init_services()
    return service.obter_relatorio_avancado(user_id, data_inicio, data_fim, 'completo')

def show_performance_metrics():
    """Mostra métricas de performance do sistema"""
    with st.sidebar:
        st.subheader("🔧 System Health")
        
        _, _, monitoring = init_services()
        
        # Botão para atualizar métricas
        if st.button("🔄 Atualizar Métricas"):
            st.cache_data.clear()  # Limpar cache para forçar atualização
        
        # Status do sistema
        system_status = monitoring.get_system_status()
        
        # Health status
        health_status = system_status['database_health']['status']
        if health_status == 'healthy':
            st.success(f"✅ Sistema: {health_status}")
        else:
            st.error(f"❌ Sistema: {health_status}")
        
        # Métricas de performance
        perf_stats = system_status['database_health'].get('performance_stats', {})
        cache_stats = system_status['database_health'].get('cache_status', {})
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                "Cache Hit Rate",
                f"{cache_stats.get('hit_ratio', 0):.1f}%"
            )
        with col2:
            st.metric(
                "Queries",
                perf_stats.get('queries_executed', 0)
            )
        
        # Mostrar alertas se houver
        if monitoring.monitor.alerts:
            st.warning(f"⚠️ {len(monitoring.monitor.alerts)} alertas")
            
            if st.expander("Ver Alertas"):
                for alert in monitoring.monitor.alerts[-5:]:  # Últimos 5
                    level_emoji = {
                        'error': '🔴',
                        'warning': '🟡', 
                        'info': '🔵'
                    }
                    st.write(f"{level_emoji.get(alert['level'], '⚪')} {alert['message']}")

def show_ai_categorization_panel(user_id: int):
    """Painel de categorização por IA otimizado"""
    st.subheader("🤖 Categorização Inteligente")
    
    _, service, _ = init_services()
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        limite = st.number_input("Transações para processar", 10, 200, 50)
        confianca_minima = st.slider("Confiança mínima", 0.5, 1.0, 0.7, 0.1)
    
    with col2:
        usar_cache = st.checkbox("Usar cache IA", True)
    
    with col3:
        if st.button("🚀 Executar Categorização", type="primary"):
            with st.spinner("Processando com IA..."):
                resultado = service.aplicar_categorizacao_ia_lote(
                    user_id, limite, usar_cache, confianca_minima
                )
                
                if resultado.get('status') == 'sucesso':
                    st.success(f"✅ Processadas: {resultado['processadas']}")
                    
                    col_res1, col_res2, col_res3 = st.columns(3)
                    with col_res1:
                        st.metric("Cache Hits", resultado['cache_hits'])
                    with col_res2:
                        st.metric("Novas IA", resultado['novas_categorizacoes'])
                    with col_res3:
                        st.metric("Aplicadas", resultado['aplicadas'])
                        
                    # Limpar cache para mostrar dados atualizados
                    st.cache_data.clear()
                    st.rerun()
                    
                elif resultado.get('status') == 'nenhuma_pendente':
                    st.info("✨ Todas as transações já estão categorizadas!")
                else:
                    st.error(f"❌ Erro: {resultado.get('erro', 'Erro desconhecido')}")

def show_advanced_dashboard(user_id: int):
    """Dashboard avançado com novas funcionalidades"""
    
    # Configurações do período
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.title("💰 Dashboard Financeiro V2")
    with col2:
        periodo_meses = st.selectbox("Período", [1, 3, 6, 12], index=1)
    with col3:
        if st.button("🔄 Atualizar Dados"):
            st.cache_data.clear()
            st.rerun()
    
    # Carregar dados otimizados
    with st.spinner("Carregando dados..."):
        dashboard_data = load_dashboard_data(user_id, periodo_meses)
    
    if dashboard_data.get('erro'):
        st.error("❌ Erro ao carregar dados do dashboard")
        return
    
    # Métricas principais
    metricas = dashboard_data['metricas']
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "💰 Receitas",
            f"R$ {metricas['receitas_totais']:,.2f}",
            delta=None
        )
    with col2:
        st.metric(
            "💸 Despesas", 
            f"R$ {metricas['despesas_totais']:,.2f}",
            delta=None
        )
    with col3:
        saldo = metricas['saldo_periodo']
        st.metric(
            "💹 Saldo",
            f"R$ {saldo:,.2f}",
            delta=None,
            delta_color="normal" if saldo >= 0 else "inverse"
        )
    with col4:
        st.metric(
            "📊 Transações",
            metricas['total_transacoes'],
            delta=None
        )
    
    # Análise de tendências (nova funcionalidade)
    tendencias = dashboard_data.get('tendencias', {})
    if tendencias:
        st.subheader("📈 Análise de Tendências")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            variacao = tendencias.get('gasto_semanal_variacao', 0)
            st.metric(
                "Variação Semanal",
                f"{variacao:+.1f}%",
                delta=variacao,
                delta_color="inverse" if variacao > 0 else "normal"
            )
        
        with col2:
            tendencia = tendencias.get('tendencia_geral', 'estável')
            emoji_tendencia = {'alta': '📈', 'baixa': '📉', 'estavel': '➡️'}
            st.metric(
                "Tendência Geral",
                tendencia.title(),
                delta=None
            )
        
        with col3:
            categoria_crescimento = tendencias.get('categoria_maior_crescimento', 'N/A')
            st.metric(
                "Categoria em Crescimento",
                categoria_crescimento,
                delta=None
            )
    
    # Gráficos lado a lado
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Evolução Mensal")
        evolucao = pd.DataFrame(dashboard_data['evolucao_mensal'])
        
        if not evolucao.empty:
            fig = px.line(
                evolucao, x='mes', y=['receitas', 'despesas'],
                title="Receitas vs Despesas",
                color_discrete_map={'receitas': '#00ff00', 'despesas': '#ff0000'}
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Dados insuficientes para o gráfico de evolução")
    
    with col2:
        st.subheader("🏷️ Top Categorias")
        categorias_top = dashboard_data['categorias_top']
        
        if categorias_top:
            categorias_df = pd.DataFrame(list(categorias_top.items()), 
                                       columns=['Categoria', 'Valor'])
            categorias_df = categorias_df.head(8)  # Top 8
            
            fig = px.pie(
                categorias_df, 
                values='Valor', 
                names='Categoria',
                title="Distribuição por Categoria"
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhuma categoria encontrada")
    
    # Painel de IA
    show_ai_categorization_panel(user_id)
    
    # Transações recentes com melhor performance
    st.subheader("📋 Transações Recentes")
    transacoes_recentes = pd.DataFrame(dashboard_data['transacoes_recentes'])
    
    if not transacoes_recentes.empty:
        # Formatação melhorada
        transacoes_display = transacoes_recentes[['data', 'descricao', 'valor', 'categoria']].copy()
        transacoes_display['valor'] = transacoes_display['valor'].apply(
            lambda x: f"R$ {x:,.2f}" if x >= 0 else f"-R$ {abs(x):,.2f}"
        )
        
        st.dataframe(
            transacoes_display,
            use_container_width=True,
            height=300,
            column_config={
                "data": st.column_config.DateColumn("Data"),
                "descricao": st.column_config.TextColumn("Descrição", width="large"),
                "valor": st.column_config.TextColumn("Valor", width="small"),
                "categoria": st.column_config.TextColumn("Categoria", width="medium")
            }
        )
    else:
        st.info("Nenhuma transação encontrada no período selecionado")

def show_analytics_tab(user_id: int):
    """Aba de análises avançadas"""
    st.subheader("📊 Análises Avançadas")
    
    # Configuração do período para análises
    col1, col2 = st.columns(2)
    with col1:
        data_inicio = st.date_input(
            "Data Início",
            value=datetime.now() - timedelta(days=90)
        )
    with col2:
        data_fim = st.date_input(
            "Data Fim",
            value=datetime.now()
        )
    
    if st.button("🔍 Gerar Relatório Avançado"):
        with st.spinner("Gerando análises..."):
            relatorio = load_advanced_analytics(
                user_id, 
                data_inicio.strftime('%Y-%m-%d'),
                data_fim.strftime('%Y-%m-%d')
            )
            
            if not relatorio.get('erro'):
                st.success("✅ Relatório gerado com sucesso!")
                
                # Resumo
                resumo = relatorio['resumo']
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Transações", resumo['total_transacoes'])
                with col2:
                    st.metric("Receitas", f"R$ {resumo['receitas']:,.2f}")
                with col3:
                    st.metric("Despesas", f"R$ {resumo['despesas']:,.2f}")
                with col4:
                    st.metric("Ticket Médio", f"R$ {resumo['ticket_medio']:,.2f}")
                
                # Detecção de anomalias
                if 'anomalias' in relatorio:
                    st.subheader("🔍 Detecção de Anomalias")
                    anomalias = relatorio['anomalias']
                    
                    if anomalias['valores_altos']:
                        st.warning(f"⚠️ {len(anomalias['valores_altos'])} transações com valores anômalos")
                        if st.expander("Ver detalhes"):
                            st.dataframe(pd.DataFrame(anomalias['valores_altos']))
                    
                    if anomalias['duplicatas_suspeitas']:
                        st.warning(f"⚠️ {len(anomalias['duplicatas_suspeitas'])} possíveis duplicatas")
                        if st.expander("Ver detalhes"):
                            st.dataframe(pd.DataFrame(anomalias['duplicatas_suspeitas']))
                    
                    if not any(anomalias.values()):
                        st.success("✅ Nenhuma anomalia detectada")
            else:
                st.error("❌ Erro ao gerar relatório")

def main():
    """Função principal da aplicação"""
    
    # Autenticação (simplificada para exemplo)
    if 'username' not in st.session_state:
        st.session_state.username = st.text_input("Username", value="demo_user")
    
    if not st.session_state.username:
        st.warning("Por favor, insira um username")
        return
    
    # Inicializar serviços
    db, service, monitoring = init_services()
    
    # Criar usuário se não existir
    user_repo = UsuarioRepository(db)
    user_id = user_repo.criar_usuario(st.session_state.username)
    
    # Sidebar com informações do sistema
    show_performance_metrics()
    
    # Tabs principais
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏠 Dashboard", 
        "📊 Análises", 
        "⚙️ Sistema",
        "📖 Docs"
    ])
    
    with tab1:
        show_advanced_dashboard(user_id)
    
    with tab2:
        show_analytics_tab(user_id)
    
    with tab3:
        st.subheader("⚙️ Configurações do Sistema")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Database Health Check**")
            health = db.health_check()
            st.json(health)
        
        with col2:
            st.write("**Estatísticas do Banco**")
            stats = db.obter_estatisticas_db()
            st.json(stats)
        
        # Operações de manutenção
        st.subheader("🔧 Operações de Manutenção")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🧹 Limpeza e Otimização"):
                with st.spinner("Executando limpeza..."):
                    resultado = service.cleanup_and_optimize(user_id)
                    st.success("✅ Limpeza concluída")
                    st.json(resultado)
        
        with col2:
            if st.button("💾 Backup Manual"):
                with st.spinner("Criando backup..."):
                    backup_path = db.backup_database()
                    st.success(f"✅ Backup criado: {backup_path}")
        
        with col3:
            if st.button("📊 Relatório Performance"):
                performance = service.obter_metricas_performance()
                st.json(performance)
    
    with tab4:
        st.subheader("📖 Documentação das Melhorias")
        
        st.markdown("""
        ## 🚀 Melhorias Implementadas - Database V2
        
        ### ⚡ Performance
        - **Connection Pooling**: Reutilização de conexões para melhor performance
        - **Query Caching**: Cache inteligente de queries para reduzir tempo de resposta
        - **Batch Operations**: Operações em lote para importação e atualizações
        - **Índices Otimizados**: Índices compostos para queries mais rápidas
        
        ### 🏗️ Arquitetura
        - **Repository Pattern**: Separação da lógica de acesso a dados
        - **Service Layer**: Centralização da lógica de negócio
        - **Dependency Injection**: Maior testabilidade e flexibilidade
        
        ### 📊 Monitoramento
        - **Health Checks**: Verificação automática da saúde do sistema
        - **Métricas em Tempo Real**: Cache hit ratio, queries/minuto, etc.
        - **Sistema de Alertas**: Notificações automáticas de problemas
        - **Performance Tracking**: Histórico de performance
        
        ### 🤖 IA e Automação
        - **Cache de Categorização**: Reutilização de categorizações por IA
        - **Batch Processing**: Categorização em lote otimizada
        - **Detecção de Anomalias**: Identificação automática de transações suspeitas
        - **Regras de Negócio**: Sistema de regras personalizáveis
        
        ### 🔒 Segurança e Integridade
        - **Constraints de Banco**: Validações a nível de banco
        - **Foreign Keys**: Integridade referencial
        - **Audit Trail**: Log de todas as operações
        - **Backup Automático**: Backups programados
        
        ### 📈 Escalabilidade
        - **Paginação**: Carregamento eficiente de grandes datasets
        - **Async Support**: Preparado para operações assíncronas
        - **Migration System**: Sistema de migração de schema
        - **Configuration Management**: Configurações centralizadas
        """)

if __name__ == "__main__":
    main()
