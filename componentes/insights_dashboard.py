"""
Componente de Dashboard de Insights Financeiros
Exibe métricas importantes, alertas e sugestões de otimização
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from typing import Dict, List, Any

from services.insights_service_v2 import InsightsServiceV2
from utils.formatacao import formatar_valor_monetario


def exibir_insights_dashboard(user_id: int):
    """Exibe dashboard completo de insights financeiros"""
    insights_service = InsightsServiceV2()
    
    # Inicializar categorias se necessário
    insights_service.inicializar_categorias_predefinidas(user_id)
    
    st.subheader("📊 Insights Financeiros")
    
    # Linha 1: Valor Restante e Alertas
    col1, col2 = st.columns([2, 1])
    
    with col1:
        _exibir_valor_restante(insights_service, user_id)
    
    with col2:
        _exibir_alertas(insights_service, user_id)
    
    # Linha 2: Análise de Gastos e Sugestões
    col1, col2 = st.columns(2)
    
    with col1:
        _exibir_analise_gastos(insights_service, user_id)
    
    with col2:
        _exibir_sugestoes(insights_service, user_id)
    
    # Linha 3: Comparativo Mensal
    _exibir_comparativo_mensal(insights_service, user_id)


def _exibir_valor_restante(insights_service: InsightsServiceV2, user_id: int):
    """Exibe cartão com valor restante do mês"""
    info = insights_service.obter_valor_restante_mensal(user_id)
    
    # Determinar cor baseada no status
    cores = {
        'positivo': '#28a745',
        'moderado': '#ffc107', 
        'atencao': '#fd7e14',
        'negativo': '#dc3545',
        'sem_dados': '#6c757d'
    }
    cor = cores.get(info['status'], '#6c757d')
    
    # Card principal
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, {cor}15, {cor}05);
        border-left: 4px solid {cor};
        padding: 20px;
        border-radius: 8px;
        margin-bottom: 20px;
    ">
        <h3 style="margin: 0; color: {cor};">💰 Valor Restante - {info['mes_ano']}</h3>
        <h1 style="margin: 10px 0; color: {cor}; font-size: 2.5em;">
            {formatar_valor_monetario(info['valor_restante'])}
        </h1>
        <div style="display: flex; justify-content: space-between; margin-top: 15px;">
            <div>
                <strong>Receitas:</strong> {formatar_valor_monetario(info['total_receitas'])}<br>
                <strong>Gastos:</strong> {formatar_valor_monetario(info['total_gastos'])}
            </div>
            <div style="text-align: right;">
                <strong>% Gasto:</strong> {info['percentual_gasto']:.1f}%<br>
                <strong>Média/dia:</strong> {formatar_valor_monetario(info['media_diaria_disponivel'])}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Barra de progresso dos gastos
    percentual = min(info['percentual_gasto'], 100)
    st.progress(percentual / 100)
    
    if info['dias_restantes'] > 0:
        st.caption(f"📅 {info['dias_restantes']} dias restantes no mês")


def _exibir_alertas(insights_service: InsightsServiceV2, user_id: int):
    """Exibe alertas financeiros importantes"""
    alertas = insights_service.detectar_alertas_financeiros(user_id)
    
    st.markdown("### 🚨 Alertas")
    
    if not alertas:
        st.success("✅ Tudo certo! Nenhum alerta no momento.")
        return
    
    # Cores por severidade
    cores_severidade = {
        'alta': '#dc3545',
        'media': '#ffc107',
        'baixa': '#17a2b8'
    }
    
    for alerta in alertas[:3]:  # Mostrar só os 3 primeiros
        cor = cores_severidade.get(alerta['severidade'], '#6c757d')
        
        st.markdown(f"""
        <div style="
            background: {cor}15;
            border: 1px solid {cor}50;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 10px;
        ">
            <strong style="color: {cor};">{alerta['titulo']}</strong><br>
            <small>{alerta['mensagem']}</small><br>
            <em style="color: {cor}90;">💡 {alerta['acao_sugerida']}</em>
        </div>
        """, unsafe_allow_html=True)


def _exibir_analise_gastos(insights_service: InsightsServiceV2, user_id: int):
    """Exibe análise de gastos por categoria"""
    st.markdown("### 📈 Gastos por Categoria")
    
    analise = insights_service.analisar_gastos_por_categoria(user_id, 3)
    
    if analise.get('status') != 'ok':
        st.info("📊 Dados insuficientes para análise de gastos")
        return
    
    # Preparar dados para gráfico
    categorias = analise['resumo_categorias']
    nomes = list(categorias.keys())[:6]  # Top 6 categorias
    valores = [categorias[cat]['sum'] for cat in nomes]
    percentuais = [categorias[cat]['percentual'] for cat in nomes]
    
    # Gráfico de pizza
    fig = px.pie(
        values=valores,
        names=nomes,
        title="Distribuição de Gastos (3 meses)",
        height=300
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(
        font_size=10,
        margin=dict(t=50, b=0, l=0, r=0)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Resumo textual
    st.caption(f"💰 Total analisado: {formatar_valor_monetario(analise['total_periodo'])}")


def _exibir_sugestoes(insights_service: InsightsServiceV2, user_id: int):
    """Exibe sugestões de otimização"""
    st.markdown("### 💡 Sugestões de Otimização")
    
    sugestoes = insights_service.sugerir_otimizacoes(user_id)
    
    if not sugestoes:
        st.info("🎯 Sem sugestões específicas no momento")
        return
    
    # Cores por dificuldade
    cores_dificuldade = {
        'facil': '#28a745',
        'media': '#ffc107',
        'dificil': '#dc3545'
    }
    
    for i, sugestao in enumerate(sugestoes[:3]):  # Top 3 sugestões
        cor = cores_dificuldade.get(sugestao.get('dificuldade', 'media'), '#ffc107')
        
        with st.expander(f"💰 {sugestao['titulo']}", expanded=(i==0)):
            st.markdown(f"""
            **Economia Potencial:** {formatar_valor_monetario(sugestao['economia_potencial'])}
            
            {sugestao['descricao']}
            
            <small style="color: {cor};">🎯 Dificuldade: {sugestao.get('dificuldade', 'média').title()}</small>
            """, unsafe_allow_html=True)


def _exibir_comparativo_mensal(insights_service: InsightsServiceV2, user_id: int):
    """Exibe comparativo de receitas vs gastos por mês"""
    st.markdown("### 📅 Evolução Mensal (6 meses)")
    
    comparativo = insights_service.obter_comparativo_mensal(user_id, 6)
    dados = comparativo['dados_mensais']
    
    if not dados:
        st.info("📊 Dados insuficientes para análise temporal")
        return
    
    # Preparar dados para gráfico
    meses = [d['mes_ano'] for d in dados]
    receitas = [d['receitas'] for d in dados]
    gastos = [d['gastos'] for d in dados]
    saldos = [d['saldo'] for d in dados]
    
    # Gráfico de barras agrupadas
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Receitas',
        x=meses,
        y=receitas,
        marker_color='#28a745',
        text=[formatar_valor_monetario(v) for v in receitas],
        textposition='outside'
    ))
    
    fig.add_trace(go.Bar(
        name='Gastos',
        x=meses,
        y=gastos,
        marker_color='#dc3545',
        text=[formatar_valor_monetario(v) for v in gastos],
        textposition='outside'
    ))
    
    # Linha do saldo
    fig.add_trace(go.Scatter(
        name='Saldo',
        x=meses,
        y=saldos,
        mode='lines+markers',
        line=dict(color='#007bff', width=3),
        marker=dict(size=8),
        yaxis='y2'
    ))
    
    fig.update_layout(
        title="Receitas vs Gastos vs Saldo",
        xaxis_title="Mês",
        yaxis=dict(title="Valores (R$)", side="left"),
        yaxis2=dict(title="Saldo (R$)", side="right", overlaying="y"),
        height=400,
        legend=dict(x=0, y=1),
        margin=dict(t=50, b=50, l=50, r=50)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Indicadores de tendência
    col1, col2, col3 = st.columns(3)
    
    with col1:
        tendencia_cor = '#28a745' if comparativo['tendencia_saldo'] == 'crescente' else '#dc3545'
        st.markdown(f"""
        <div style="text-align: center; color: {tendencia_cor};">
            <strong>Tendência Saldo</strong><br>
            {comparativo['tendencia_saldo'].title()}
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        tendencia_gastos_cor = '#dc3545' if comparativo['tendencia_gastos'] == 'aumentando' else '#28a745'
        st.markdown(f"""
        <div style="text-align: center; color: {tendencia_gastos_cor};">
            <strong>Tendência Gastos</strong><br>
            {comparativo['tendencia_gastos'].title()}
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div style="text-align: center; color: #007bff;">
            <strong>Média Saldo</strong><br>
            {formatar_valor_monetario(comparativo['media_saldo'])}
        </div>
        """, unsafe_allow_html=True)


def exibir_cartao_valor_restante_compacto(user_id: int):
    """Versão compacta do cartão de valor restante para sidebar"""
    insights_service = InsightsServiceV2()
    info = insights_service.obter_valor_restante_mensal(user_id)
    
    # Determinar cor e emoji baseado no status
    config_status = {
        'positivo': {'cor': '#28a745', 'emoji': '😊'},
        'moderado': {'cor': '#ffc107', 'emoji': '😐'},
        'atencao': {'cor': '#fd7e14', 'emoji': '😟'},
        'negativo': {'cor': '#dc3545', 'emoji': '😰'},
        'sem_dados': {'cor': '#6c757d', 'emoji': '📊'}
    }
    config = config_status.get(info['status'], config_status['sem_dados'])
    
    st.markdown(f"""
    <div style="
        background: {config['cor']}15;
        border: 1px solid {config['cor']}40;
        padding: 15px;
        border-radius: 8px;
        text-align: center;
    ">
        <div style="font-size: 24px;">{config['emoji']}</div>
        <strong style="color: {config['cor']}; font-size: 18px;">
            {formatar_valor_monetario(info['valor_restante'])}
        </strong><br>
        <small>Valor Restante {info['mes_ano']}</small>
    </div>
    """, unsafe_allow_html=True)
    
    return info['status'] != 'sem_dados'
