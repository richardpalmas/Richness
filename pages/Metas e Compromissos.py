import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import warnings
import time

# Imports Backend V2
from componentes.profile_pic_component import boas_vindas_com_foto
from utils.repositories_v2 import UsuarioRepository, TransacaoRepository, CompromissoRepository, MetaEconomiaRepository
from utils.database_manager_v2 import DatabaseManager
from utils.auth import verificar_autenticacao
from utils.formatacao import formatar_valor_monetario, formatar_df_monetario
from utils.exception_handler import ExceptionHandler

# Importações para Insights e Personalidade IA
from componentes.personality_selector import render_personality_selector
from componentes.insight_card import exibir_insight_card
from services.llm_service import LLMService
from services.insights_service_v2 import InsightsServiceV2

warnings.filterwarnings('ignore')

st.set_page_config(layout="wide")

# Verificar autenticação
verificar_autenticacao()

# Exibir foto de perfil
if 'usuario' in st.session_state:
    boas_vindas_com_foto(st.session_state['usuario'])

st.title("🎯 Metas e Compromissos")
st.markdown("Gerencie suas metas financeiras e compromissos de forma organizada")

# Função auxiliar para versionar cache de categorias
def get_cache_categorias_version_metas():
    """Gera uma versão do cache baseada nos arquivos de categorias"""
    try:
        from utils.config import get_categorias_personalizadas_file
        import os
        
        version_components = []
        
        # Incluir timestamp do arquivo de categorias personalizadas
        categorias_file = get_categorias_personalizadas_file()
        if os.path.exists(categorias_file):
            version_components.append(str(os.path.getmtime(categorias_file)))
        else:
            version_components.append("0")
        
        # Incluir timestamp atual (atualiza a cada 5 minutos)
        import time
        current_time = int(time.time())
        time_bucket = current_time // 300  # 5 minutos = 300 segundos
        version_components.append(str(time_bucket))
        
        return "_".join(version_components)
    except Exception:
        import time
        return str(int(time.time()))

# Função para carregar categorias do usuário
@st.cache_data(ttl=300)
def carregar_categorias_usuario(usuario, cache_version=None):
    """Carrega TODAS as categorias disponíveis para usar nos compromissos
    cache_version: parâmetro usado para forçar refresh quando categorias mudam"""
    try:
        # 1. CATEGORIAS PADRÃO DO SISTEMA (mesmas da página Gerenciar Transações)
        CATEGORIAS_DISPONIVEIS = [
            "Alimentação",
            "Transporte", 
            "Saúde",
            "Educação",
            "Lazer",
            "Casa e Utilidades",
            "Vestuário",
            "Investimentos",
            "Transferências",
            "Salário",
            "Freelance",
            "Compras Online",
            "Combustível",
            "Farmácia",
            "Supermercado",    
            "Restaurante",
            "Academia",
            "Streaming",
            "Telefone",
            "Internet",
            "Banco/Taxas",
            "Imóvel",  # Categoria comum para compromissos
            "Outros"
        ]
        
        categorias_finais = set(CATEGORIAS_DISPONIVEIS)
        
        # 2. CATEGORIAS PERSONALIZADAS (criadas pelo usuário na página Gerenciar Transações)
        try:
            from utils.config import get_categorias_personalizadas_file, get_current_user
            import json
            import os
            
            categorias_file = get_categorias_personalizadas_file()
            if os.path.exists(categorias_file):
                with open(categorias_file, 'r', encoding='utf-8') as f:
                    categorias_personalizadas = json.load(f)
                    if isinstance(categorias_personalizadas, list):
                        categorias_finais.update(categorias_personalizadas)
        except Exception:
            # Falhar silenciosamente se não conseguir carregar categorias personalizadas
            pass
        
        # 3. CATEGORIAS DAS TRANSAÇÕES EXISTENTES
        try:
            db_manager = DatabaseManager()
            user_repo = UsuarioRepository(db_manager)
            transacao_repo = TransacaoRepository(db_manager)
            
            # Obter usuário
            usuario_atual = user_repo.obter_usuario_por_username(usuario)
            if usuario_atual:
                user_id = usuario_atual.get('id')
                if user_id:
                    # Obter categorias das transações (últimos 2 anos)
                    data_fim = datetime.now().strftime('%Y-%m-%d')
                    data_inicio = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
                    
                    df = transacao_repo.obter_transacoes_periodo(
                        user_id=user_id,
                        data_inicio=data_inicio,
                        data_fim=data_fim,
                        incluir_excluidas=False,
                        limite=2000
                    )
                    
                    if not df.empty and 'categoria' in df.columns:
                        categorias_transacoes = df['categoria'].dropna().unique()
                        # Filtrar categorias válidas (não vazias e não só espaços)
                        categorias_validas = [cat for cat in categorias_transacoes 
                                            if cat and str(cat).strip() and str(cat).strip() != 'nan']
                        categorias_finais.update(categorias_validas)
        except Exception:
            # Falhar silenciosamente se não conseguir carregar categorias das transações
            pass
        
        # 4. GARANTIR QUE SEMPRE TEMOS PELO MENOS CATEGORIAS BÁSICAS
        categorias_essenciais = ["Alimentação", "Transporte", "Saúde", "Casa e Utilidades", "Imóvel", "Outros"]
        categorias_finais.update(categorias_essenciais)
        
        # 5. RETORNAR LISTA ORDENADA E LIMPA
        categorias_lista = sorted([cat for cat in categorias_finais if cat and str(cat).strip()])
        
        # Garantir que "Outros" sempre esteja por último
        if "Outros" in categorias_lista:
            categorias_lista.remove("Outros")
            categorias_lista.append("Outros")
        
        return categorias_lista if categorias_lista else ["Outros"]
        
    except Exception as e:
        st.error(f"Erro ao carregar categorias: {str(e)}")
        # Fallback para categorias básicas em caso de erro
        return [
            "Alimentação", "Transporte", "Saúde", "Educação", "Lazer", 
            "Casa e Utilidades", "Vestuário", "Imóvel", "Outros"
        ]

# Função auxiliar para formatar data de forma segura
def formatar_data_segura(data_valor):
    """Formatar data de forma segura para exibição"""
    try:
        if isinstance(data_valor, str):
            if '-' in data_valor:
                return datetime.strptime(data_valor[:10], '%Y-%m-%d').strftime('%d/%m/%Y')
        else:
            data_convertida = pd.to_datetime(data_valor)
            return data_convertida.strftime('%d/%m/%Y')
    except Exception:
        return "Data inválida"

# Função auxiliar para calcular dias até vencimento
def calcular_dias_vencimento(data_valor):
    """Calcular dias até vencimento de forma segura"""
    try:
        data_obj = None
        if isinstance(data_valor, str):
            if '-' in data_valor:
                data_obj = datetime.strptime(data_valor[:10], '%Y-%m-%d').date()
        else:
            data_convertida = pd.to_datetime(data_valor)
            data_obj = data_convertida.date()
        
        if data_obj is not None:
            hoje = datetime.now().date()
            diferenca = data_obj - hoje
            return diferenca.days
        return None
    except Exception:
        return None

def exibir_grid_insights_metas(usuario):
    """Exibe insights personalizados específicos para metas e compromissos com cache ultra-estável"""
    try:
        # Importar o serviço de cache
        from services.insights_cache_service import InsightsCacheService
        
        # Obter user_id
        db = DatabaseManager()
        usuario_repo = UsuarioRepository(db)
        user_data = usuario_repo.obter_usuario_por_username(usuario)
        if not user_data:
            st.error("Usuário não encontrado")
            return
        user_id = user_data.get('id')
        if not user_id:
            st.error("Erro ao identificar o usuário")
            return
        
        # Inicializar serviços
        cache_service = InsightsCacheService()
        compromisso_repo = CompromissoRepository(db)
        
        # Obter personalidade selecionada
        personalidade_sel = st.session_state.get('ai_personality', 'clara')
        
        # Obter nome amigável/avatar
        avatar_map = {
            'clara': 'imgs/perfil_amigavel_fem.png',
            'tecnica': 'imgs/perfil_tecnico_masc.png',
            'durona': 'imgs/perfil_durao_mas.png'
        }
        nome_map = {
            'clara': 'Ana',
            'tecnica': 'Fernando',
            'durona': 'Jorge'
        }
        avatar_path = avatar_map.get(personalidade_sel, 'imgs/perfil_amigavel_fem.png')
        nome_ia = nome_map.get(personalidade_sel, 'Ana')
        
        # DADOS ULTRA-ESTÁVEIS: Criar estruturas determinísticas para cache
        
        # 1. Compromissos estáveis (apenas dados essenciais, sem timestamps)
        compromissos_pendentes = compromisso_repo.obter_compromissos(user_id, "pendente")
        compromissos_estabilizados = []
        total_compromissos_valor = 0.0
        
        if not compromissos_pendentes.empty:
            for idx, row in compromissos_pendentes.iterrows():
                valor_raw = row.get('valor', 0)
                valor = float(valor_raw) if valor_raw is not None and valor_raw != '' else 0.0
                total_compromissos_valor += valor
                compromissos_estabilizados.append({
                    'categoria': str(row.get('categoria', 'Outros')),
                    'valor': round(valor, 2),  # Arredondar para evitar flutuações
                    'tipo': 'compromisso'
                })
        
        # 2. Metas estáveis (versão determinística) - BUSCAR DO BANCO DE DADOS
        meta_repo = MetaEconomiaRepository(db)
        df_metas = meta_repo.obter_metas_usuario(user_id, status='ativa')
        
        # Criar versão ultra-estável das metas (apenas dados essenciais)
        metas_estabilizadas = []
        total_metas_valor = 0.0
        total_economia_mensal = 0.0
        
        if not df_metas.empty:
            for idx, meta in df_metas.iterrows():
                valor_total_raw = meta.get('valor_total', 0)
                valor_mensal_raw = meta.get('valor_mensal', 0)
                valor_economizado_raw = meta.get('valor_economizado', 0)
                
                valor_total = float(valor_total_raw) if valor_total_raw is not None else 0.0
                valor_mensal = float(valor_mensal_raw) if valor_mensal_raw is not None else 0.0
                valor_economizado = float(valor_economizado_raw) if valor_economizado_raw is not None else 0.0
                
                total_metas_valor += valor_total
                total_economia_mensal += valor_mensal
                
                # Criar entrada estável usando apenas dados essenciais
                metas_estabilizadas.append({
                    'index': idx,  # Usar índice como identificador estável
                    'nome': str(meta.get('nome', '')),
                    'valor_total': round(valor_total, 2),
                    'valor_mensal': round(valor_mensal, 2),
                    'valor_economizado': round(valor_economizado, 2),
                    'progresso': round((valor_economizado / valor_total * 100) if valor_total > 0 else 0, 1),
                    'tipo': 'meta_economia'
                })
        
        # 3. Saldo líquido super-estável (calculado uma única vez e arredondado)
        from services.transacao_service_v2 import TransacaoService
        transacao_service = TransacaoService()
        df_transacoes = transacao_service.listar_transacoes_usuario(usuario, limite=1000)
        
        saldo_liquido = 0.0
        if not df_transacoes.empty and 'valor' in df_transacoes.columns:
            # Somar e arredondar para eliminar flutuações de ponto flutuante
            soma_valores = df_transacoes['valor'].sum()
            saldo_liquido = round(float(soma_valores) if soma_valores is not None else 0.0, 2)
        
        # 4. Métricas derivadas estáveis
        total_compromissos_valor = round(total_compromissos_valor, 2)
        total_metas_valor = round(total_metas_valor, 2) 
        total_economia_mensal = round(total_economia_mensal, 2)
        saldo_disponivel = round(saldo_liquido - total_compromissos_valor, 2)
        
        # 5. Obter parâmetros de personalidade estáveis
        from utils.repositories_v2 import PersonalidadeIARepository
        personalidade_repo = PersonalidadeIARepository(db)
        
        # Simplificar parâmetros para reduzir variabilidade
        params_estabilizados = {'personalidade': personalidade_sel}
        
        if personalidade_sel == 'clara':
            params_db = personalidade_repo.obter_personalidade(user_id, "Clara e Acolhedora")
            if params_db and params_db.get('emojis'):
                params_estabilizados['emojis'] = str(params_db.get('emojis', 'Moderado'))
        elif personalidade_sel == 'tecnica':
            params_db = personalidade_repo.obter_personalidade(user_id, "Técnico e Formal")
            if params_db and params_db.get('emojis'):
                params_estabilizados['emojis'] = str(params_db.get('emojis', 'Poucos'))
        elif personalidade_sel == 'durona':
            params_db = personalidade_repo.obter_personalidade(user_id, "Durão e Informal")
            if params_db and params_db.get('emojis'):
                params_estabilizados['emojis'] = str(params_db.get('emojis', 'Muitos'))
        
        # Verificar se deve forçar regeneração
        forcar_regeneracao = st.session_state.get('forcar_regeneracao_insights_metas', False)
        
        # Limpar flag após usar
        if forcar_regeneracao:
            st.session_state['forcar_regeneracao_insights_metas'] = False
        
        # DEBUG: Logs detalhados para investigar problema de cache
        debug_cache_logs = []
        
        # GERAR INSIGHTS COM CONTEXTOS ULTRA-ESTÁVEIS
        insights = []
        
        # Insight 1: Análise de compromissos pendentes
        contexto_compromissos = {
            'user_id': user_id,  # Identificador estável
            'compromissos_count': len(compromissos_estabilizados),
            'compromissos_total': total_compromissos_valor,
            'saldo_liquido': saldo_liquido,
            'situacao': 'positiva' if total_compromissos_valor <= saldo_liquido else 'negativa',
            'personalidade': personalidade_sel,
            'tipo_analise': 'compromissos_metas'  # Constante para estabilidade
        }
        prompt_compromissos = "Com base nos DADOS DE METAS E COMPROMISSOS fornecidos no contexto, analise especificamente os compromissos pendentes cadastrados pelo usuário. Cite nomes e valores reais dos compromissos. Considere o saldo líquido disponível e dê uma avaliação prática da situação financeira em até 250 caracteres. NÃO inclua saudações."
        
        # DEBUG: Gerar e mostrar hashes para debug
        if st.session_state.get('modo_depurador'):
            try:
                data_hash_1 = cache_service.gerar_data_hash(contexto_compromissos)
                prompt_hash_1 = cache_service.gerar_prompt_hash(prompt_compromissos, params_estabilizados)
                debug_cache_logs.append({
                    'insight': 'analise_compromissos_metas',
                    'data_hash': data_hash_1,
                    'prompt_hash': prompt_hash_1,
                    'contexto': contexto_compromissos.copy(),
                    'params': params_estabilizados.copy()
                })
            except Exception as e:
                debug_cache_logs.append({
                    'insight': 'analise_compromissos_metas',
                    'error': str(e)
                })
        
        insight_compromissos = cache_service.gerar_insight_com_cache(
            user_id=user_id,
            insight_type='analise_compromissos_metas',
            personalidade=personalidade_sel,
            data_context=contexto_compromissos,
            prompt=prompt_compromissos,
            personalidade_params=params_estabilizados,
            forcar_regeneracao=forcar_regeneracao
        )
        
        insights.append({
            'tipo': 'neutro' if total_compromissos_valor <= saldo_liquido else 'alerta',
            'titulo': insight_compromissos['titulo'],
            'valor': insight_compromissos['valor'] or formatar_valor_monetario(total_compromissos_valor),
            'comentario': insight_compromissos['comentario'][:250] + ('...' if len(insight_compromissos['comentario']) > 250 else ''),
            'assinatura': nome_ia,
            'avatar': avatar_path,
            'saudacao': None,
            'cache_info': f"Cache: {insight_compromissos['source']}" if st.session_state.get('modo_depurador') else None
        })
        
        # Insight 2: Progresso das metas de economia
        contexto_metas = {
            'user_id': user_id,
            'metas_count': len(metas_estabilizadas),
            'metas_total_valor': total_metas_valor,
            'economia_mensal_necessaria': total_economia_mensal,
            'saldo_liquido': saldo_liquido,
            'viabilidade': 'viavel' if total_economia_mensal <= saldo_liquido * 0.3 else 'dificil',
            'personalidade': personalidade_sel,
            'tipo_analise': 'metas_economia'  # Constante para estabilidade
        }
        prompt_metas = "Com base nas METAS DE ECONOMIA detalhadas no contexto, analise o progresso específico de cada meta cadastrada pelo usuário. Cite nomes das metas, valores e percentuais de progresso reais. Considere a viabilidade da economia mensal necessária e dê conselhos práticos em até 250 caracteres. NÃO inclua saudações."
        
        # DEBUG: Gerar e mostrar hashes para debug
        if st.session_state.get('modo_depurador'):
            try:
                data_hash_2 = cache_service.gerar_data_hash(contexto_metas)
                prompt_hash_2 = cache_service.gerar_prompt_hash(prompt_metas, params_estabilizados)
                debug_cache_logs.append({
                    'insight': 'progresso_metas_economia',
                    'data_hash': data_hash_2,
                    'prompt_hash': prompt_hash_2,
                    'contexto': contexto_metas.copy(),
                    'params': params_estabilizados.copy()
                })
            except Exception as e:
                debug_cache_logs.append({
                    'insight': 'progresso_metas_economia',
                    'error': str(e)
                })
        
        insight_metas = cache_service.gerar_insight_com_cache(
            user_id=user_id,
            insight_type='progresso_metas_economia',
            personalidade=personalidade_sel,
            data_context=contexto_metas,
            prompt=prompt_metas,
            personalidade_params=params_estabilizados,
            forcar_regeneracao=forcar_regeneracao
        )
        
        insights.append({
            'tipo': 'positivo' if total_economia_mensal <= saldo_liquido * 0.3 else 'alerta',
            'titulo': insight_metas['titulo'],
            'valor': insight_metas['valor'] or f"{len(metas_estabilizadas)} metas",
            'comentario': insight_metas['comentario'][:250] + ('...' if len(insight_metas['comentario']) > 250 else ''),
            'assinatura': nome_ia,
            'avatar': avatar_path,
            'saudacao': None,
            'cache_info': f"Cache: {insight_metas['source']}" if st.session_state.get('modo_depurador') else None
        })
        
        # Insight 3: Capacidade de pagamento
        contexto_capacidade = {
            'user_id': user_id,
            'saldo_liquido': saldo_liquido,
            'total_compromissos': total_compromissos_valor,
            'total_economia_mensal': total_economia_mensal,
            'saldo_disponivel': saldo_disponivel,
            'capacidade': 'boa' if saldo_disponivel > 0 else 'limitada',
            'personalidade': personalidade_sel,
            'tipo_analise': 'capacidade_pagamento'  # Constante para estabilidade
        }
        prompt_capacidade = "Com base na CAPACIDADE FINANCEIRA detalhada no contexto, analise a relação entre o saldo líquido, os compromissos específicos e as metas de economia cadastradas pelo usuário. Calcule e comente sobre o saldo disponível real após compromissos e metas. Dê uma avaliação prática da situação em até 250 caracteres. NÃO inclua saudações."
        
        # DEBUG: Gerar e mostrar hashes para debug
        if st.session_state.get('modo_depurador'):
            try:
                data_hash_3 = cache_service.gerar_data_hash(contexto_capacidade)
                prompt_hash_3 = cache_service.gerar_prompt_hash(prompt_capacidade, params_estabilizados)
                debug_cache_logs.append({
                    'insight': 'capacidade_pagamento_metas',
                    'data_hash': data_hash_3,
                    'prompt_hash': prompt_hash_3,
                    'contexto': contexto_capacidade.copy(),
                    'params': params_estabilizados.copy()
                })
            except Exception as e:
                debug_cache_logs.append({
                    'insight': 'capacidade_pagamento_metas',
                    'error': str(e)
                })
        
        insight_capacidade = cache_service.gerar_insight_com_cache(
            user_id=user_id,
            insight_type='capacidade_pagamento_metas',
            personalidade=personalidade_sel,
            data_context=contexto_capacidade,
            prompt=prompt_capacidade,
            personalidade_params=params_estabilizados,
            forcar_regeneracao=forcar_regeneracao
        )
        
        insights.append({
            'tipo': 'positivo' if saldo_disponivel > 0 else 'negativo',
            'titulo': insight_capacidade['titulo'],
            'valor': insight_capacidade['valor'] or formatar_valor_monetario(saldo_disponivel),
            'comentario': insight_capacidade['comentario'][:250] + ('...' if len(insight_capacidade['comentario']) > 250 else ''),
            'assinatura': nome_ia,
            'avatar': avatar_path,
            'saudacao': None,
            'cache_info': f"Cache: {insight_capacidade['source']}" if st.session_state.get('modo_depurador') else None
        })
        
        # Insight 4: Recomendação estratégica
        contexto_estrategia = {
            'user_id': user_id,
            'tem_compromissos': len(compromissos_estabilizados) > 0,
            'tem_metas': len(metas_estabilizadas) > 0,
            'saldo_positivo': saldo_liquido > 0,
            'economia_viavel': total_economia_mensal <= saldo_liquido * 0.5 if saldo_liquido > 0 else False,
            'equilibrio_financeiro': 'bom' if saldo_liquido > (total_compromissos_valor + total_economia_mensal) else 'apertado',
            'personalidade': personalidade_sel,
            'tipo_analise': 'estrategia_financeira'  # Constante para estabilidade
        }
        prompt_estrategia = "Com base na SITUAÇÃO ESTRATÉGICA detalhada no contexto, analise o conjunto de compromissos e metas específicas cadastradas pelo usuário. Considere o equilíbrio financeiro atual e dê uma recomendação estratégica prática e específica para otimizar o planejamento financeiro em até 250 caracteres. NÃO inclua saudações."
        
        # DEBUG: Gerar e mostrar hashes para debug
        if st.session_state.get('modo_depurador'):
            try:
                data_hash_4 = cache_service.gerar_data_hash(contexto_estrategia)
                prompt_hash_4 = cache_service.gerar_prompt_hash(prompt_estrategia, params_estabilizados)
                debug_cache_logs.append({
                    'insight': 'estrategia_financeira_metas',
                    'data_hash': data_hash_4,
                    'prompt_hash': prompt_hash_4,
                    'contexto': contexto_estrategia.copy(),
                    'params': params_estabilizados.copy()
                })
            except Exception as e:
                debug_cache_logs.append({
                    'insight': 'estrategia_financeira_metas',
                    'error': str(e)
                })
        
        insight_estrategia = cache_service.gerar_insight_com_cache(
            user_id=user_id,
            insight_type='estrategia_financeira_metas',
            personalidade=personalidade_sel,
            data_context=contexto_estrategia,
            prompt=prompt_estrategia,
            personalidade_params=params_estabilizados,
            forcar_regeneracao=forcar_regeneracao
        )
        
        insights.append({
            'tipo': 'neutro',
            'titulo': insight_estrategia['titulo'],
            'valor': '',
            'comentario': insight_estrategia['comentario'][:250] + ('...' if len(insight_estrategia['comentario']) > 250 else ''),
            'assinatura': nome_ia,
            'avatar': avatar_path,
            'saudacao': None,
            'cache_info': f"Cache: {insight_estrategia['source']}" if st.session_state.get('modo_depurador') else None
        })
        
        # Modo Depurador: logs visuais e estatísticas de cache
        if st.session_state.get('modo_depurador'):
            st.subheader('🪲 Logs do Modo Depurador (Insights Metas - ULTRA-ESTÁVEL)')
            
            # Mostrar se regeneração foi forçada
            if forcar_regeneracao:
                st.error("⚡ **REGENERAÇÃO FORÇADA ATIVA** - Todos os insights foram gerados via LLM ignorando cache")
                st.info("🔄 Cache foi ignorado propositalmente para esta sessão")
            else:
                st.success("💾 **CACHE ULTRA-ESTÁVEL ATIVO** - Dados determinísticos e estáveis")
                st.info("🛡️ **OTIMIZAÇÕES V2**: Dados ultra-estáveis, contextos simplificados, identificadores determinísticos")
            
            # Estatísticas de cache
            cache_stats = cache_service.obter_estatisticas_cache_usuario(user_id)
            
            col1, col2, col3, col4 = st.columns(4)
            
            cache_hits = len([i for i in insights if i.get('cache_info', '').endswith('cache')])
            llm_calls = len([i for i in insights if i.get('cache_info', '').endswith('llm')])
            total_insights = len(insights)
            
            with col1:
                st.metric("💾 Cache Hits", cache_hits, help="Insights que vieram do cache")
            with col2:
                st.metric("🔄 LLM Calls", llm_calls, help="Insights gerados via LLM")
            with col3:
                efficiency = (cache_hits / total_insights * 100) if total_insights > 0 else 0
                st.metric("⚡ Eficiência Sessão", f"{efficiency:.1f}%", help="% de insights que vieram do cache nesta sessão")
            with col4:
                st.metric("💾 Eficiência Geral", f"{cache_stats.get('eficiencia_cache', 0):.1f}%", help="Eficiência geral do cache do usuário")
            
            with st.expander("📈 Estatísticas Detalhadas do Cache"):
                st.json(cache_stats)
            
            # DEBUG AVANÇADO: Mostrar hashes e contextos detalhados
            with st.expander("🔍 DEBUG AVANÇADO - Investigação de Cache Fails", expanded=True):
                st.write("**🚨 DIAGNÓSTICO DE CACHE - Por que não está funcionando?**")
                
                # Mostrar logs de debug detalhados
                for i, log in enumerate(debug_cache_logs):
                    st.write(f"**Insight #{i+1}: {log.get('insight', 'unknown')}**")
                    
                    if 'error' in log:
                        st.error(f"❌ Erro ao gerar hash: {log['error']}")
                    else:
                        st.write(f"- Data Hash: `{log.get('data_hash', 'N/A')}`")
                        st.write(f"- Prompt Hash: `{log.get('prompt_hash', 'N/A')}`")
                        
                        # Mostrar contexto de forma legível SEM usar expander aninhado
                        if st.button(f"🔍 Ver contexto detalhado do insight #{i+1}", key=f"show_context_{i}"):
                            st.json(log.get('contexto', {}))
                        
                        # Verificar se existe cache para esse hash
                        try:
                            # Usar o prompt correto para cada insight
                            prompts_map = {
                                'analise_compromissos_metas': prompt_compromissos,
                                'progresso_metas_economia': prompt_metas,
                                'capacidade_pagamento_metas': prompt_capacidade,
                                'estrategia_financeira_metas': prompt_estrategia
                            }
                            
                            insight_prompt = prompts_map.get(log.get('insight'), prompt_compromissos)
                            
                            cached_result = cache_service.obter_insight_cached(
                                user_id=user_id,
                                insight_type=log.get('insight'),
                                personalidade=personalidade_sel,
                                data_context=log.get('contexto', {}),
                                prompt=insight_prompt,
                                personalidade_params=log.get('params', {})
                            )
                            
                            if cached_result:
                                st.success(f"✅ Cache ENCONTRADO para insight #{i+1}")
                                st.write(f"- Source: {cached_result.get('source')}")
                                st.write(f"- Created: {cached_result.get('created_at')}")
                                st.write(f"- Used Count: {cached_result.get('used_count')}")
                            else:
                                st.warning(f"⚠️ Cache NÃO ENCONTRADO para insight #{i+1}")
                                
                                # NOVO: Testar o processo completo de salvamento do cache
                                st.write("🧪 **TESTE COMPLETO DE CACHE PARA DEBUG:**")
                                
                                try:
                                    # Chamar o processo completo de cache para debug
                                    test_result = cache_service.gerar_insight_com_cache(
                                        user_id=user_id,
                                        insight_type=log.get('insight'),
                                        personalidade=personalidade_sel,
                                        data_context=log.get('contexto', {}),
                                        prompt=insight_prompt,
                                        personalidade_params=log.get('params', {}),
                                        forcar_regeneracao=False  # Não forçar regeneração para testar cache
                                    )
                                    
                                    if test_result:
                                        st.info(f"📝 **Resultado do teste**: {test_result.get('source')}")
                                        
                                        # Se foi gerado via LLM, verificar se foi salvo
                                        if test_result.get('source') == 'llm':
                                            st.info("🔄 Insight foi gerado via LLM, verificando se foi salvo...")
                                            
                                            # Tentar buscar novamente após o salvamento
                                            time.sleep(0.1)  # Pequena pausa
                                            cached_after_save = cache_service.obter_insight_cached(
                                                user_id=user_id,
                                                insight_type=log.get('insight'),
                                                personalidade=personalidade_sel,
                                                data_context=log.get('contexto', {}),
                                                prompt=insight_prompt,
                                                personalidade_params=log.get('params', {})
                                            )
                                            
                                            if cached_after_save:
                                                st.success("✅ Cache foi SALVO com sucesso!")
                                                st.write(f"- ID: {cached_after_save.get('id')}")
                                                st.write(f"- Created: {cached_after_save.get('created_at')}")
                                            else:
                                                st.error("❌ Cache NÃO foi salvo - problema no processo de salvamento!")
                                                
                                                # Investigar problema no banco
                                                try:
                                                    # Verificar se a tabela existe
                                                    test_query = cache_service.cache_repo.db.executar_query(
                                                        "SELECT name FROM sqlite_master WHERE type='table' AND name='cache_insights_llm';"
                                                    )
                                                    
                                                    if test_query:
                                                        st.info("✅ Tabela cache_insights_llm existe")
                                                        
                                                        # Verificar se há algum cache para este usuário
                                                        user_cache_count = cache_service.cache_repo.db.executar_query(
                                                            "SELECT COUNT(*) as count FROM cache_insights_llm WHERE user_id = ?",
                                                            [user_id]
                                                        )
                                                        
                                                        if user_cache_count and len(user_cache_count) > 0:
                                                            st.info(f"📊 Total de cache do usuário: {user_cache_count[0]['count']}")
                                                        else:
                                                            st.warning("⚠️ Nenhum cache encontrado para este usuário")
                                                        
                                                        # Tentar inserir um cache de teste
                                                        try:
                                                            test_cache_id = cache_service.cache_repo.salvar_insight_cache(
                                                                user_id=user_id,
                                                                insight_type="teste_debug",
                                                                personalidade=personalidade_sel,
                                                                data_hash="test_hash",
                                                                prompt_hash="test_prompt",
                                                                titulo="Teste",
                                                                valor="R$ 0,00",
                                                                comentario="Teste de cache",
                                                                expires_hours=1
                                                            )
                                                            
                                                            if test_cache_id:
                                                                st.success(f"✅ Cache de teste criado com ID: {test_cache_id}")
                                                                
                                                                # Remover cache de teste
                                                                cache_service.cache_repo.db.executar_query(
                                                                    "DELETE FROM cache_insights_llm WHERE id = ?",
                                                                    [test_cache_id]
                                                                )
                                                                st.info("🗑️ Cache de teste removido")
                                                            else:
                                                                st.error("❌ Falha ao criar cache de teste")
                                                                
                                                        except Exception as test_error:
                                                            st.error(f"❌ Erro no teste de inserção: {test_error}")
                                                    else:
                                                        st.error("❌ Tabela cache_insights_llm NÃO EXISTE!")
                                                        
                                                except Exception as db_error:
                                                    st.error(f"❌ Erro ao verificar banco: {db_error}")
                                        
                                        else:
                                            st.info("💾 Cache foi reutilizado (já existia)")
                                    else:
                                        st.error("❌ Falha no teste completo de cache")
                                        
                                except Exception as test_error:
                                    st.error(f"❌ Erro no teste de cache: {test_error}")
                                
                                st.write("🔍 **Possíveis causas:**")
                                st.write("- Hash diferente em execução anterior")
                                st.write("- Cache expirado")
                                st.write("- Primeiro acesso (normal)")
                                st.write("- Dados do contexto mudaram")
                                st.write("- **NOVO**: Problema no salvamento do cache")
                                
                                # Verificar se existe ALGUM cache para este tipo e usuário
                                try:
                                    # Buscar qualquer cache deste tipo para debug
                                    cache_repo = cache_service.cache_repo
                                    any_cache = cache_repo.db.executar_query("""
                                        SELECT insight_type, personalidade, created_at, expires_at, used_count
                                        FROM cache_insights_llm 
                                        WHERE user_id = ? AND insight_type = ?
                                        ORDER BY created_at DESC
                                        LIMIT 3
                                    """, [user_id, log.get('insight')])
                                    
                                    if any_cache:
                                        st.info(f"🔍 **Histórico de cache para {log.get('insight')}:**")
                                        for cache_entry in any_cache:
                                            st.write(f"- {cache_entry['created_at']} | Expira: {cache_entry['expires_at']} | Usos: {cache_entry['used_count']}")
                                    else:
                                        st.warning(f"📭 **Nenhum cache histórico** encontrado para {log.get('insight')}")
                                        
                                except Exception as cache_check_error:
                                    st.error(f"❌ Erro ao verificar histórico: {cache_check_error}")
                                
                        except Exception as e:
                            st.error(f"❌ Erro ao verificar cache: {e}")
                    
                    st.divider()
                
                # Informações sobre configuração do cache
                st.info("🔧 **Configuração do Cache para Metas:**")
                st.write("- analise_compromissos_metas: 72 horas")
                st.write("- progresso_metas_economia: 96 horas") 
                st.write("- capacidade_pagamento_metas: 48 horas")
                st.write("- estrategia_financeira_metas: 120 horas")
            
            # Debug de estabilização ULTRA melhorada
            with st.expander("🔒 Debug Cache - Dados Ultra-Estáveis V2", expanded=False):
                st.write("**Dados ultra-estabilizados para cache persistente:**")
                
                # Mostrar estruturas de dados simplificadas e estáveis
                st.write("**1. Contexto Compromissos:**")
                st.json(contexto_compromissos)
                
                st.write("**2. Contexto Metas:**") 
                st.json(contexto_metas)
                
                st.write("**3. Contexto Capacidade:**")
                st.json(contexto_capacidade)
                
                st.write("**4. Contexto Estratégia:**")
                st.json(contexto_estrategia)
                
                st.write("**5. Parâmetros Estabilizados:**")
                st.json(params_estabilizados)
                
                # Informações de estabilidade
                st.info("🔒 **Garantias de Estabilidade:**")
                st.write("- ✅ Apenas user_id, valores arredondados e flags booleanas")
                st.write("- ✅ Sem timestamps, IDs dinâmicos ou dados do session_state")
                st.write("- ✅ Contextos simplificados e determinísticos")
                st.write("- ✅ Parâmetros de personalidade estáveis")
                st.write("- ✅ Saldo calculado uma única vez e arredondado")
            
            # Informações sobre a situação financeira
            st.info(f"📋 **Dados analisados**: {len(compromissos_estabilizados)} compromissos, {len(metas_estabilizadas)} metas")
            st.info(f"💰 **Situação**: Saldo {formatar_valor_monetario(saldo_liquido)}, Compromissos {formatar_valor_monetario(total_compromissos_valor)}, Disponível {formatar_valor_monetario(saldo_disponivel)}")
            
            for idx, insight in enumerate(insights):
                st.write(f'Insight #{idx+1} - {insight["titulo"]}:')
                st.write(f'- Fonte: {insight.get("cache_info", "N/A")}')
                st.write(f'- Comentário: {insight["comentario"]}')
                st.divider()
        
        # Exibir em grid (2 por linha)
        for i in range(0, len(insights), 2):
            cols = st.columns(2)
            for j, insight in enumerate(insights[i:i+2]):
                with cols[j]:
                    exibir_insight_card(
                        avatar_path=insight['avatar'],
                        nome_ia=nome_ia,
                        saudacao=insight['saudacao'],
                        tipo=insight['tipo'],
                        titulo=insight['titulo'],
                        valor=insight['valor'],
                        comentario=insight['comentario'],
                        assinatura=insight['assinatura']
                    )
                    
                    # Mostrar info de cache se modo depurador ativo
                    if st.session_state.get('modo_depurador') and insight.get('cache_info'):
                        st.caption(f"🔍 {insight['cache_info']}")
    
    except Exception as e:
        st.error(f"Erro ao exibir insights de metas: {str(e)}")
        # Fallback para versão sem cache em caso de erro
        if st.session_state.get('modo_depurador'):
            st.exception(e)

# Inicializar repositories
usuario = st.session_state.get('usuario', 'default')

try:
    db_manager = DatabaseManager()
    user_repo = UsuarioRepository(db_manager)
    compromisso_repo = CompromissoRepository(db_manager)
    
    # Obter user_id
    usuario_atual = user_repo.obter_usuario_por_username(usuario)
    user_id = usuario_atual.get('id') if usuario_atual else None
    
    if not user_id:
        st.error("❌ Erro: Usuário não encontrado")
        st.stop()
    
    # Carregar categorias disponíveis (com cache versionado)
    cache_version = get_cache_categorias_version_metas()
    categorias_existentes = carregar_categorias_usuario(usuario, cache_version)
    
    # Sidebar - Configurações
    st.sidebar.header("⚙️ Configurações - Metas")
    st.sidebar.markdown("**Sistema Richness Ativo**")
    
    # Botão para ativar/desativar o modo depurador
    if 'modo_depurador' not in st.session_state:
        st.session_state['modo_depurador'] = False
    if st.sidebar.button(f"{'🛑 Desativar' if st.session_state['modo_depurador'] else '🐞 Ativar'} Modo Depurador", 
                        help="Exibe logs detalhados dos insights na tela", 
                        key="modo_depurador_metas_btn"):
        st.session_state['modo_depurador'] = not st.session_state['modo_depurador']
        st.rerun()
    st.sidebar.write(f"Modo Depurador: {'Ativo' if st.session_state['modo_depurador'] else 'Inativo'}")
    
    # Informações de categorias (apenas para modo depurador)
    if st.session_state.get('modo_depurador'):
        st.sidebar.markdown("### 📊 Debug - Categorias")
        st.sidebar.write(f"📂 **Total de categorias**: {len(categorias_existentes)}")
        st.sidebar.write(f"🔄 **Cache version**: {cache_version[:10]}...")
        
        with st.sidebar.expander("🔍 Ver todas as categorias"):
            for i, cat in enumerate(categorias_existentes, 1):
                st.sidebar.write(f"{i}. {cat}")
    
    # Ferramentas de Cache (apenas para modo depurador)
    if st.session_state.get('modo_depurador'):
        st.sidebar.markdown("### 🗄️ Ferramentas de Cache")
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.sidebar.button("🗑️ Limpar Cache", help="Remove cache expirado do usuário", key="limpar_cache_metas_btn"):
                try:
                    from services.insights_cache_service import InsightsCacheService
                    cache_service = InsightsCacheService()
                    
                    # Limpar apenas cache expirado
                    removidos = cache_service.limpar_cache_expirado_automatico()
                    
                    # Limpar cache do Streamlit
                    st.cache_data.clear()
                    
                    st.sidebar.success(f"✅ {removidos} entradas expiradas removidas")
                    st.sidebar.info("🔄 Cache do Streamlit limpo")
                    
                    # Rerun para atualizar
                    time.sleep(0.5)
                    st.rerun()
                    
                except Exception as e:
                    st.sidebar.error(f"❌ Erro: {e}")
        
        with col2:
            if st.sidebar.button("🔄 Reset Cache", help="Remove TODO cache do usuário e força regeneração", key="reset_cache_metas_btn"):
                try:
                    from services.insights_cache_service import InsightsCacheService
                    cache_service = InsightsCacheService()
                    
                    if user_id:
                        # Invalidar TODO cache do usuário (válido e expirado)
                        removidos = cache_service.invalidar_cache_por_mudanca_dados(user_id)
                        
                        # Limpar cache do Streamlit
                        st.cache_data.clear()
                        st.cache_resource.clear()
                        
                        # Marcar flag para forçar regeneração
                        st.session_state['forcar_regeneracao_insights_metas'] = True
                        
                        st.sidebar.success(f"✅ Cache resetado ({removidos} entradas)")
                        st.sidebar.warning("⚡ Próximos insights serão regenerados via LLM")
                        
                        # Rerun para regenerar
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.sidebar.error("❌ Usuário não encontrado")
                except Exception as e:
                    st.sidebar.error(f"❌ Erro: {e}")
        
        # Botão para forçar regeneração sem limpar cache
        if st.sidebar.button("⚡ Forçar Regeneração", help="Força nova chamada ao LLM sem limpar cache", key="forcar_regeneracao_metas_btn"):
            try:
                if user_id:
                    # NÃO limpar cache - apenas marcar flag para ignorá-lo
                    st.session_state['forcar_regeneracao_insights_metas'] = True
                    
                    # Limpar cache do Streamlit para forçar recarregamento da página
                    st.cache_data.clear()
                    
                    st.sidebar.success("⚡ Regeneração forçada ativada!")
                    st.sidebar.info("🔄 Próximos insights ignorarão cache e usarão LLM")
                    
                    # Rerun imediato
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.sidebar.error("❌ Usuário não encontrado")
            except Exception as e:
                st.sidebar.error(f"❌ Erro: {e}")
    
    # Informações do usuário na sidebar
    if st.sidebar.expander("👤 Informações do Usuário"):
        st.sidebar.write(f"**Usuário**: {usuario}")
        st.sidebar.write(f"**Sistema**: Richness Platform")
    
    # Botão de Sair
    st.sidebar.markdown("---")
    if st.sidebar.button('🚪 Sair', help="Fazer logout da aplicação", type="primary", key="sair_metas_btn"):
        st.session_state.clear()
        st.rerun()
    
    # Abas para organizar compromissos e metas
    tab1, tab2, tab3, tab4 = st.tabs(["➕ Adicionar", "📋 Pendentes", "📊 Todos", "🎯 Metas de Economia"])
    
    with tab1:
        # Formulário para adicionar compromisso
        st.markdown("### ➕ Adicionar Novo Compromisso")
        
        col1, col2 = st.columns(2)
        
        with col1:
            desc_compromisso = st.text_input(
                "Descrição da Meta / Compromisso",
                placeholder="Ex: Conta de luz, Poupança, IPTU, etc.",
                help="Descreva o compromisso financeiro"
            )
            
            valor_compromisso = st.number_input(
                "Valor (R$)",
                min_value=0.01,
                format="%.2f",
                help="Valor do compromisso em reais"
            )
        
        with col2:
            data_vencimento = st.date_input(
                "Data",
                min_value=datetime.now().date() - timedelta(days=120),
                help="Data em que o compromisso deve ser pago"
            )
            
            categoria_compromisso = st.selectbox(
                "Categoria",
                categorias_existentes,
                help="Categoria baseada nas transações existentes"
            )
        
        observacoes = st.text_area(
            "Observações (opcional)",
            placeholder="Informações adicionais sobre o compromisso",
            height=68
        )
        
        if st.button("💾 Salvar Compromisso", type="primary", key="salvar_compromisso_btn"):
            if desc_compromisso and valor_compromisso > 0:
                try:
                    compromisso_id = compromisso_repo.criar_compromisso(
                        user_id=user_id,
                        descricao=desc_compromisso,
                        valor=valor_compromisso,
                        data_vencimento=data_vencimento.strftime('%Y-%m-%d'),
                        categoria=categoria_compromisso,
                        observacoes=observacoes
                    )
                    
                    if compromisso_id:
                        st.success("✅ Compromisso salvo com sucesso!")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("❌ Erro ao salvar compromisso")
                except Exception as e:
                    st.error(f"❌ Erro: {str(e)}")
            else:
                st.warning("⚠️ Preencha todos os campos obrigatórios")
    
    with tab2:
        # Compromissos pendentes
        st.markdown("### 📋 Compromissos Pendentes")
        
        df_pendentes = compromisso_repo.obter_compromissos(user_id, "pendente")
        
        if not df_pendentes.empty:
            # Calcular total pendente
            total_pendente = df_pendentes['valor'].sum()
            
            # Métricas
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("💰 Total Pendente", formatar_valor_monetario(total_pendente))
            with col2:
                st.metric("📋 Quantidade", len(df_pendentes))
            with col3:
                # Verificar compromissos vencidos
                hoje = datetime.now().date()
                vencidos = 0
                for idx in df_pendentes.index:
                    try:
                        data_str = str(df_pendentes.loc[idx, 'data_vencimento'])
                        if '-' in data_str:
                            data_venc = datetime.strptime(data_str[:10], '%Y-%m-%d').date()
                            if data_venc < hoje:
                                vencidos += 1
                    except Exception:
                        continue
                
                if vencidos > 0:
                    st.metric("⚠️ Vencidos", vencidos)
                else:
                    st.metric("✅ Em Dia", len(df_pendentes))
            
            st.divider()
            
            # Exibir compromissos
            for idx, row in df_pendentes.iterrows():
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                    
                    with col1:
                        st.write(f"**{row['descricao']}**")
                        try:
                            obs_val = row['observacoes']
                            obs_str = str(obs_val) if obs_val is not None else ""
                            if obs_str and obs_str.strip() and obs_str != 'nan' and obs_str != 'None':
                                st.caption(obs_str)
                        except:
                            pass
                    
                    with col2:
                        st.write(f"💰 {formatar_valor_monetario(row['valor'])}")
                        data_formatada = formatar_data_segura(row['data_vencimento'])
                        st.caption(f"📅 {data_formatada}")
                    
                    with col3:
                        st.write(f"🏷️ {row['categoria']}")
                        
                        # Verificar se está próximo do vencimento
                        dias_vencimento = calcular_dias_vencimento(row['data_vencimento'])
                        if dias_vencimento is not None and dias_vencimento <= 7:
                            if dias_vencimento < 0:
                                st.error(f"⚠️ Vencido há {abs(dias_vencimento)} dias")
                            elif dias_vencimento == 0:
                                st.warning("⚠️ Vence hoje!")
                            else:
                                st.warning(f"⚠️ Vence em {dias_vencimento} dias")
                    
                    with col4:
                        compromisso_id = int(row['id'])
                        if st.button("✅", key=f"pagar_{compromisso_id}", help="Marcar como pago"):
                            if compromisso_repo.atualizar_status_compromisso(user_id, compromisso_id, "pago"):
                                st.success("Marcado como pago!")
                                st.rerun()
                        
                        if st.button("🗑️", key=f"excluir_{compromisso_id}", help="Excluir compromisso"):
                            if compromisso_repo.excluir_compromisso(user_id, compromisso_id):
                                st.success("Compromisso excluído!")
                                st.rerun()
                    
                    st.divider()
        else:
            st.info("📭 Nenhum compromisso pendente")
            st.markdown("💡 **Dica:** Use a aba 'Adicionar' para criar seus primeiros compromissos!")
    
    with tab3:
        # Todos os compromissos
        st.markdown("### 📊 Histórico de Compromissos")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            status_filter = st.selectbox("Filtrar por status:", ["pendente", "pago", "cancelado"])
        with col2:
            if st.button("🔄 Atualizar Dados", key="atualizar_dados_metas_btn"):
                st.cache_data.clear()
                st.rerun()
        
        df_todos = compromisso_repo.obter_compromissos(user_id, status_filter)
        
        if not df_todos.empty:
            # Métricas do período
            total_valor = df_todos['valor'].sum()
            st.metric(f"💰 Total ({status_filter.title()})", formatar_valor_monetario(total_valor))
            
            # Preparar dados para exibição
            df_display = df_todos[['descricao', 'valor', 'data_vencimento', 'categoria', 'status']].copy()
            df_display = formatar_df_monetario(df_display, 'valor')
            
            # Formatar datas de forma segura
            datas_formatadas = []
            for idx in df_display.index:
                data_valor = df_display.loc[idx, 'data_vencimento']
                datas_formatadas.append(formatar_data_segura(data_valor))
            df_display['data_vencimento_formatada'] = datas_formatadas
            
            # Criar DataFrame para exibição
            df_exibicao = pd.DataFrame({
                'Descrição': df_display['descricao'],
                'Valor': df_display['ValorFormatado'],
                'Vencimento': df_display['data_vencimento_formatada'],
                'Categoria': df_display['categoria'],
                'Status': df_display['status']
            })
            
            st.dataframe(
                df_exibicao,
                use_container_width=True,
                height=400
            )
            
            # Download dos dados
            if st.button("📥 Baixar Histórico (CSV)", key="download_historico_metas_btn"):
                csv = df_exibicao.to_csv(index=False)
                st.download_button(
                    label="💾 Download CSV",
                    data=csv,
                    file_name=f"compromissos_{status_filter}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    key="download_csv_metas_btn"
                )
        else:
            st.info(f"📭 Nenhum compromisso {status_filter}")
    
    with tab4:
        # Metas de Economia
        st.markdown("### 🎯 Metas de Economia")
        st.markdown("Defina suas metas de economia e acompanhe seu progresso!")
        
        # Seção para criar nova meta
        with st.container():
            st.markdown("#### ➕ Nova Meta de Economia")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Nome da meta
                nome_meta = st.text_input(
                    "Nome da Meta",
                    placeholder="Ex: Viagem para Europa, Novo carro, Reserva de emergência",
                    help="Dê um nome descritivo para sua meta",
                    key="input_nome_meta_economia"
                )
                
                # Valor da meta usando slider
                valor_meta = st.slider(
                    "💰 Valor da Meta (R$)",
                    min_value=100.0,
                    max_value=100000.0,
                    value=5000.0,
                    step=100.0,
                    format="R$ %.0f",
                    help="Use o slider para definir o valor que deseja economizar",
                    key="slider_valor_meta_economia"
                )
                
                # Exibir valor formatado
                st.info(f"Meta: **{formatar_valor_monetario(valor_meta)}**")
            
            with col2:
                # Prazo em meses
                prazo_meses = st.number_input(
                    "⏱️ Prazo (meses)",
                    min_value=1,
                    max_value=120,
                    value=12,
                    help="Em quantos meses deseja alcançar esta meta?",
                    key="input_prazo_meta_economia"
                )
                
                # Valor mensal necessário (calculado automaticamente)
                if prazo_meses > 0:
                    valor_mensal = valor_meta / prazo_meses
                    st.metric(
                        "📅 Economia Mensal Necessária", 
                        formatar_valor_monetario(valor_mensal),
                        help="Valor que você precisa economizar por mês"
                    )
                
                # Data prevista para conclusão
                from datetime import datetime, timedelta
                data_conclusao = datetime.now() + timedelta(days=prazo_meses * 30)
                st.info(f"🎯 **Data prevista:** {data_conclusao.strftime('%d/%m/%Y')}")
            
            # Observações da meta
            observacoes_meta = st.text_area(
                "📝 Observações (opcional)",
                placeholder="Detalhes sobre a meta, estratégias, etc.",
                height=80,
                key="textarea_observacoes_meta_economia"
            )
            
            # Botão para salvar meta
            col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
            with col_btn2:
                if st.button("💾 Salvar Meta de Economia", type="primary", use_container_width=True, key="salvar_meta_economia_btn"):
                    if nome_meta and valor_meta > 0 and prazo_meses > 0:
                        try:
                            # Salvar no banco de dados usando MetaEconomiaRepository
                            meta_repo = MetaEconomiaRepository(db_manager)
                            meta_id = meta_repo.criar_meta(
                                user_id=user_id,
                                nome=nome_meta,
                                valor_total=valor_meta,
                                prazo_meses=prazo_meses,
                                observacoes=observacoes_meta or ""
                            )
                            
                            # Invalidar cache dos insights de metas
                            cache_service = InsightsCacheService()
                            cache_service.invalidar_cache_por_mudanca_dados(user_id)
                            
                            if meta_id:
                                st.success("✅ Meta de economia criada com sucesso!")
                                # Limpar cache para recarregar dados
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error("❌ Erro ao salvar meta no banco de dados")
                            
                        except Exception as e:
                            st.error(f"❌ Erro ao salvar meta: {str(e)}")
                    else:
                        st.warning("⚠️ Preencha todos os campos obrigatórios!")
        
        st.divider()
        
        # Seção para exibir metas existentes
        st.markdown("#### 📊 Suas Metas de Economia")
        
        # Carregar metas do banco de dados
        meta_repo = MetaEconomiaRepository(db_manager)
        df_metas_display = meta_repo.obter_metas_usuario(user_id, status='ativa')
        
        if not df_metas_display.empty:
            # Converter DataFrame para lista de dicionários para facilitar uso
            metas_ativas = df_metas_display.to_dict('records')
            
            # Métricas gerais
            total_metas = len(metas_ativas)
            valor_total_metas = sum(float(meta.get('valor_total', 0)) if meta.get('valor_total') is not None else 0.0 for meta in metas_ativas)
            valor_mensal_total = sum(float(meta.get('valor_mensal', 0)) if meta.get('valor_mensal') is not None else 0.0 for meta in metas_ativas)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🎯 Metas Ativas", total_metas)
            with col2:
                st.metric("💰 Valor Total", formatar_valor_monetario(valor_total_metas))
            with col3:
                st.metric("📅 Economia Mensal Total", formatar_valor_monetario(valor_mensal_total))
            
            st.divider()
            
            # Exibir cada meta
            for meta in metas_ativas:
                with st.container():
                    # Calcular progresso
                    valor_total_raw = meta.get('valor_total', 0)
                    valor_economizado_raw = meta.get('valor_economizado', 0)
                    
                    valor_total = float(valor_total_raw) if valor_total_raw is not None else 0.0
                    valor_economizado = float(valor_economizado_raw) if valor_economizado_raw is not None else 0.0
                    progresso_percentual = (valor_economizado / valor_total * 100) if valor_total > 0 else 0
                    valor_restante = valor_total - valor_economizado
                    
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                    
                    with col1:
                        st.write(f"**🎯 {meta['nome']}**")
                        observacoes = meta.get('observacoes')
                        if observacoes and str(observacoes).strip():
                            st.caption(observacoes)
                        
                        # Barra de progresso
                        st.progress(progresso_percentual / 100)
                        st.caption(f"Progresso: {progresso_percentual:.1f}%")
                    
                    with col2:
                        st.metric("💰 Meta", formatar_valor_monetario(valor_total))
                        st.metric("💸 Restante", formatar_valor_monetario(valor_restante))
                    
                    with col3:
                        valor_mensal_meta = meta.get('valor_mensal', 0)
                        valor_mensal_final = float(valor_mensal_meta) if valor_mensal_meta is not None else 0.0
                        st.metric("📅 Mensal", formatar_valor_monetario(valor_mensal_final))
                        st.metric("⏱️ Prazo", f"{meta.get('prazo_meses', 0)} meses")
                    
                    with col4:
                        meta_id = int(meta['id'])
                        # Botão para adicionar valor economizado
                        if st.button("💰", key=f"adicionar_{meta_id}", help="Adicionar valor economizado"):
                            st.session_state[f'show_input_{meta_id}'] = True
                            st.rerun()
                        
                        # Botão para concluir/cancelar meta
                        if st.button("✅", key=f"concluir_{meta_id}", help="Marcar como concluída"):
                            # Atualizar status da meta no banco
                            if meta_repo.atualizar_status_meta(user_id, meta_id, 'concluida'):
                                st.success("Meta marcada como concluída!")
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error("Erro ao atualizar status da meta")
                    
                    # Input para adicionar valor (se ativado)
                    if st.session_state.get(f'show_input_{meta_id}', False):
                        with st.form(f"form_valor_{meta_id}"):
                            valor_adicionar = st.number_input(
                                "Valor economizado (R$)",
                                min_value=0.01,
                                max_value=valor_restante,
                                format="%.2f",
                                key=f"valor_{meta_id}"
                            )
                            
                            col_form1, col_form2 = st.columns(2)
                            with col_form1:
                                if st.form_submit_button("💾 Adicionar"):
                                    # Atualizar valor economizado no banco
                                    if meta_repo.atualizar_valor_economizado(user_id, meta_id, valor_adicionar):
                                        st.session_state[f'show_input_{meta_id}'] = False
                                        st.success(f"Adicionado {formatar_valor_monetario(valor_adicionar)} à meta!")
                                        st.cache_data.clear()
                                        st.rerun()
                                    else:
                                        st.error("Erro ao atualizar valor economizado")
                            
                            with col_form2:
                                if st.form_submit_button("❌ Cancelar"):
                                    st.session_state[f'show_input_{meta_id}'] = False
                                    st.rerun()
                    
                    st.divider()
        else:
            st.info("📭 Nenhuma meta de economia ativa")
            st.markdown("💡 **Dica:** Use o formulário acima para criar sua primeira meta!")

except Exception as e:
    st.error(f"❌ Erro ao carregar compromissos: {str(e)}")
    ExceptionHandler.handle_generic_error(e)

st.markdown("---")

# Layout principal em colunas (dashboard à esquerda, seletor à direita)
col_main, col_persona = st.columns([2.5, 1])

with col_persona:
    render_personality_selector()

with col_main:
    exibir_grid_insights_metas(usuario)

st.markdown("---")

# Dicas e ajuda
with st.expander("💡 Dicas de Uso"):
    st.markdown("""
    ### Como usar Metas e Compromissos:
    
    **➕ Adicionar Compromissos:**
    - Crie compromissos financeiros como contas, metas de poupança, etc.
    - Use categorias consistentes com suas transações para melhor organização
    
    **📋 Pendentes:**
    - Visualize todos os compromissos que ainda precisam ser pagos
    - Receba alertas para compromissos próximos do vencimento
    - Marque como "pago" quando concluído
    
    **📊 Histórico:**
    - Consulte todos os compromissos por status
    - Baixe relatórios em CSV para análise externa
    - Use os filtros para encontrar compromissos específicos
    
    **🎯 Metas de Economia:**
    - Use o slider para definir o valor que deseja economizar
    - Defina um prazo realista para alcançar sua meta
    - Acompanhe seu progresso adicionando valores economizados
    - O sistema calcula automaticamente quanto você precisa economizar por mês
    
    **💡 Dicas Pro:**
    - **Compromissos:** Adicione-os recorrentemente para não esquecer
    - **Metas:** Seja específico no nome (ex: "Viagem Japão 2025")
    - **Progresso:** Atualize regularmente os valores economizados
    - **Planejamento:** Use as observações para estratégias e lembretes
    """) 