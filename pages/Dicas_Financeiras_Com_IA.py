# -*- coding: utf-8 -*-
"""
Página de Dicas Financeiras com IA - Versão Completa e Funcional
Implementa conexão robusta com LangChain e OpenAI
"""

import streamlit as st
import pandas as pd
import functools
import os
import sys
import logging
import time
from typing import Optional, Tuple, List, Any, Dict
from datetime import datetime, timedelta

# Página configurada via Home.py - não precisa de st.set_page_config aqui

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Importações dos módulos do projeto
try:
    from utils.environment_config import get_config, validate_openai_key
    from componentes.profile_pic_component import boas_vindas_com_foto
    from utils.auth import verificar_autenticacao
    from utils.formatacao import formatar_valor_monetario
    from utils.filtros import filtro_data
    # Imports Backend V2
    from utils.repositories_v2 import (
        UsuarioRepository, 
        TransacaoRepository, 
        ConversaIARepository,
        CompromissoRepository
    )
    from utils.database_manager_v2 import DatabaseManager
    from services.transacao_service_v2 import TransacaoService
    from utils.exception_handler import ExceptionHandler
    
except ImportError as e:
    st.error(f"Erro ao importar módulos do projeto: {e}")
    st.stop()

# === SISTEMA DE INICIALIZAÇÃO DA IA ===

class AIServiceManager:
    """Gerenciador de serviços de IA com inicialização robusta"""
    
    def __init__(self):
        self._openai_client = None
        self._langchain_available = False
        self._initialization_attempted = False
        self._error_message = None
        
    def _check_dependencies(self) -> Tuple[bool, str]:
        """Verifica se todas as dependências estão disponíveis"""
        try:
            # Verificar regex (dependência crítica do LangChain)
            import regex
            logger.info("✅ Módulo regex disponível")
        except ImportError:
            return False, "Módulo 'regex' não encontrado. Execute: pip install regex"
        
        try:
            # Verificar LangChain
            import langchain_openai
            logger.info("✅ LangChain OpenAI disponível")
            return True, "Todas as dependências estão disponíveis"
        except ImportError as e:
            return False, f"LangChain não disponível: {str(e)}"
    
    def _validate_api_key(self) -> Tuple[bool, str]:
        """Valida a chave da API OpenAI"""
        try:
            config = get_config()
            api_key = config.get_openai_api_key()
            
            if not api_key or api_key.strip() == "":
                return False, "Chave da API OpenAI não configurada"
            
            if not api_key.startswith("sk-"):
                return False, "Formato de chave OpenAI inválido"
            
            return True, "Chave API válida"
        except Exception as e:
            return False, f"Erro ao validar chave API: {str(e)}"
    
    def initialize(self) -> bool:
        """Inicializa os serviços de IA com tratamento robusto de erros"""
        if self._initialization_attempted:
            return self._langchain_available
        
        self._initialization_attempted = True
        
        # Verificar dependências
        deps_ok, deps_msg = self._check_dependencies()
        if not deps_ok:
            self._error_message = deps_msg
            logger.warning(f"Dependências não disponíveis: {deps_msg}")
            return False
        
        # Verificar chave da API
        key_ok, key_msg = self._validate_api_key()
        if not key_ok:
            self._error_message = key_msg
            logger.warning(f"Chave API inválida: {key_msg}")
            return False
          # Tentar inicializar o cliente OpenAI
        try:
            from langchain_openai import ChatOpenAI
            
            config = get_config()
            api_key = config.get_openai_api_key()            # Use environment variable approach for better compatibility
            os.environ["OPENAI_API_KEY"] = api_key              # Initialize OpenAI client with specific model
            self._openai_client = ChatOpenAI(
            )
            
            # Simple test without complex invoke
            logger.info("✅ Cliente OpenAI inicializado com sucesso com modelo o4-mini-2025-04-16")
            logger.info("✅ Streaming habilitado para melhor experiência do usuário")
            
            self._langchain_available = True
            return True
            
        except Exception as e:
            self._error_message = f"Erro ao inicializar OpenAI: {str(e)}"
            logger.error(self._error_message)
            return False
    def get_client(self):
        """Retorna o cliente OpenAI se disponível"""
        if not self._langchain_available:
            return None
        return self._openai_client
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna o status do serviço de IA"""
        return {
            "available": self._langchain_available,
            "error": self._error_message,
            "initialized": self._initialization_attempted
        }

# Instância global do gerenciador de IA
ai_manager = AIServiceManager()

# === COMPONENTES DE INTERFACE ===

def display_ai_status():
    """Exibe o status da IA na interface"""
    status = ai_manager.get_status()
    
    if status["available"]:
        st.success("🤖 IA totalmente funcional (modelo: o4-mini-2025-04-16) com streaming habilitado")
    elif status["error"]:
        st.error(f"❌ IA indisponível: {status['error']}")
        if st.button("🔄 Tentar Reconectar"):
            ai_manager._initialization_attempted = False
            ai_manager._langchain_available = False
            ai_manager._error_message = None
            st.rerun()
    else:
        st.info("🔄 Inicializando serviços de IA...")

class FinancialAIService:
    """Serviço de IA para análise financeira"""
    
    def __init__(self, ai_manager: AIServiceManager):
        self.ai_manager = ai_manager
        self.cache = {}

    def analyze_financial_data(self, financial_data: Dict, personalidade: str = "clara") -> str:
        """Analisa dados financeiros usando IA com personalidade específica"""
        if "error" in financial_data:
            raise RuntimeError(f"Erro ao buscar dados financeiros: {financial_data['error']}")

        # Inicialização da IA
        if not self.ai_manager.initialize():
            status = self.ai_manager.get_status()
            raise RuntimeError(f"Erro ao inicializar IA: {status['error']}")

        client = self.ai_manager.get_client()
        if not client:
            status = self.ai_manager.get_status()
            raise RuntimeError(f"Cliente IA não disponível: {status['error']}")

        try:
            # Preparar dados para análise com personalidade
            analysis_prompt = self._prepare_analysis_prompt(financial_data, personalidade)
            cache_key = str(hash(str(financial_data) + personalidade))
            if cache_key in self.cache:
                return self.cache[cache_key]
            response = client.invoke(analysis_prompt)
            result = response.content if hasattr(response, 'content') else str(response)
            if not isinstance(result, str):
                result = str(result)
            self.cache[cache_key] = result
            return result
        except Exception as e:
            logger.error(f"Erro na análise com IA: {str(e)}", exc_info=True)
            raise RuntimeError(f"Erro na análise com IA: {str(e)}")

    def _prepare_analysis_prompt(self, data: Dict, personalidade: str = "clara") -> str:
        """Prepara o prompt para análise financeira com personalidade específica"""
        
        # Definir características da personalidade
        personalidade_configs = {
            "clara": {
                "estilo": "acolhedora, clara e engraçada",
                "instrucoes": "Use uma linguagem amigável, descontraída e ocasionalmente humor apropriado. Seja empática e motivadora. Use emojis para tornar a conversa mais leve."
            },
            "tecnica": {
                "estilo": "técnica e formal",
                "instrucoes": "Use linguagem técnica precisa, terminologia financeira adequada e estruture as informações de forma profissional e objetiva. Mantenha tom formal e acadêmico."
            },
            "durona": {
                "estilo": "durona e informal",
                "instrucoes": "Seja direta, sem rodeios e use linguagem coloquial. Pode ser um pouco 'durona' nas observações, mas sempre construtiva. Fale a verdade de forma clara e sem papas na língua."
            }
        }
        
        config = personalidade_configs.get(personalidade, personalidade_configs["clara"])
        
        # Preparar informações de metas e compromissos
        compromissos_info = data.get('compromissos', {})
        total_compromissos = compromissos_info.get('total', 0)
        valor_total_compromissos = compromissos_info.get('valor_total', 0)
        compromissos_por_categoria = compromissos_info.get('por_categoria', {})
        proximos_compromissos = compromissos_info.get('proximos', [])
        
        compromissos_texto = f"""
Metas e Compromissos:
- Total de compromissos no período: {total_compromissos}
- Valor total dos compromissos: R$ {valor_total_compromissos:.2f}

Compromissos por categoria:
{chr(10).join(f"- {cat}: R$ {info['total']:.2f} ({info['count']} items)" for cat, info in compromissos_por_categoria.items())}

Próximos compromissos importantes:
{chr(10).join(f"- {comp['descricao']}: R$ {comp['valor']:.2f} (vence em {comp['data_vencimento']})" for comp in proximos_compromissos)}
"""
        
        return f"""
Você é um assistente financeiro com personalidade {config['estilo']}. {config['instrucoes']}

Analise os seguintes dados financeiros e forneça dicas personalizadas:

Dados Financeiros:
- Total de transações: {data.get('total_transactions', 0)}
- Período analisado: {data.get('period_days', 0)} dias
- Receitas: R$ {data.get('extratos', {}).get('receitas', 0):.2f}
- Despesas: R$ {data.get('extratos', {}).get('despesas', 0):.2f}
- Gastos no cartão: R$ {data.get('cartoes', {}).get('gastos', 0):.2f}

{compromissos_texto}

Por favor, forneça:
1. Análise do padrão de gastos considerando as metas estabelecidas
2. Avaliação da capacidade de cumprir os compromissos financeiros
3. 3-5 dicas específicas de economia para atingir as metas
4. Sugestões de melhoria no orçamento considerando os compromissos futuros
5. Alertas sobre possíveis problemas no cumprimento das metas e compromissos

Mantenha as dicas práticas e aplicáveis, sempre seguindo sua personalidade {config['estilo']}.
"""

    def prepare_question_prompt(self, financial_data: Dict, user_question: str, personalidade: str = "clara") -> str:
        """Prepara prompt para perguntas do usuário com personalidade específica"""
        
        # Definir características da personalidade
        personalidade_configs = {
            "clara": {
                "estilo": "acolhedora, clara e engraçada",
                "instrucoes": "Use uma linguagem amigável, descontraída e ocasionalmente humor apropriado. Seja empática e motivadora. Use emojis para tornar a conversa mais leve."
            },
            "tecnica": {
                "estilo": "técnica e formal",
                "instrucoes": "Use linguagem técnica precisa, terminologia financeira adequada e estruture as informações de forma profissional e objetiva. Mantenha tom formal e acadêmico."
            },
            "durona": {
                "estilo": "durona e informal",
                "instrucoes": "Seja direta, sem rodeios e use linguagem coloquial. Pode ser um pouco 'durona' nas observações, mas sempre construtiva. Fale a verdade de forma clara e sem papas na língua."
            }
        }
        
        config = personalidade_configs.get(personalidade, personalidade_configs["clara"])
        
        # Preparar informações de metas e compromissos
        compromissos_info = financial_data.get('compromissos', {})
        total_compromissos = compromissos_info.get('total', 0)
        valor_total_compromissos = compromissos_info.get('valor_total', 0)
        compromissos_por_categoria = compromissos_info.get('por_categoria', {})
        proximos_compromissos = compromissos_info.get('proximos', [])
        
        compromissos_texto = f"""
Metas e Compromissos:
- Total de compromissos no período: {total_compromissos}
- Valor total dos compromissos: R$ {valor_total_compromissos:.2f}

Compromissos por categoria:
{chr(10).join(f"- {cat}: R$ {info['total']:.2f} ({info['count']} items)" for cat, info in compromissos_por_categoria.items())}

Próximos compromissos importantes:
{chr(10).join(f"- {comp['descricao']}: R$ {comp['valor']:.2f} (vence em {comp['data_vencimento']})" for comp in proximos_compromissos)}
"""
        
        return f"""
Você é um assistente financeiro com personalidade {config['estilo']}. {config['instrucoes']}

Considere o seguinte histórico financeiro do usuário dos últimos 4 meses:

Dados Financeiros:
- Total de transações: {financial_data.get('total_transactions', 0)}
- Período analisado: {financial_data.get('period_days', 0)} dias
- Receitas: R$ {financial_data.get('extratos', {}).get('receitas', 0):.2f}
- Despesas: R$ {financial_data.get('extratos', {}).get('despesas', 0):.2f}
- Gastos no cartão: R$ {financial_data.get('cartoes', {}).get('gastos', 0):.2f}

{compromissos_texto}

Pergunta do usuário: {user_question}

Responda de forma personalizada, prática e clara, considerando o contexto financeiro apresentado, as metas/compromissos estabelecidos e mantendo sempre sua personalidade {config['estilo']}.
"""

    def get_response(self, financial_data: Dict, user_question: str, personalidade: str = "clara"):
        """Gera resposta da IA (método sem streaming)"""
        if not self.ai_manager.initialize():
            status = self.ai_manager.get_status()
            raise RuntimeError(f"IA indisponível: {status['error']}")

        client = self.ai_manager.get_client()
        if not client:
            status = self.ai_manager.get_status()
            raise RuntimeError(f"IA indisponível: {status['error']}")
            
        # Preparar prompt
        prompt = self.prepare_question_prompt(financial_data, user_question, personalidade)
        
        try:
            # o4-mini suporta invoke normal
            response = client.invoke(prompt)
            result = response.content if hasattr(response, 'content') else str(response)
            return str(result).strip() if result else "Desculpe, não foi possível gerar uma resposta."
                    
        except Exception as e:
            logger.error(f"Erro na geração da resposta: {str(e)}")
            return f"❌ Erro na geração da resposta: {str(e)}"
            
    def get_streaming_response(self, financial_data: Dict, user_question: str, personalidade: str = "clara"):
        """Gera resposta da IA em tempo real usando streaming com tratamento robusto de chunks"""
        if not self.ai_manager.initialize():
            status = self.ai_manager.get_status()
            raise RuntimeError(f"IA indisponível: {status['error']}")

        client = self.ai_manager.get_client()
        if not client:
            status = self.ai_manager.get_status()
            raise RuntimeError(f"IA indisponível: {status['error']}")

        # Preparar prompt
        prompt = self.prepare_question_prompt(financial_data, user_question, personalidade)
        
        try:
            # Buffer para armazenar chunks parciais que podem estar cortando palavras
            partial_chunk = ""
            
            # Stream da resposta real com o4-mini
            for chunk in client.stream(prompt):
                # Extração robusta do conteúdo do chunk
                content = None
                
                # Tentar extrair conteúdo do chunk em ordem de prioridade
                if hasattr(chunk, 'content') and chunk.content:
                    content = chunk.content
                elif hasattr(chunk, 'text') and chunk.text:
                    content = chunk.text
                elif isinstance(chunk, str):
                    content = chunk
                elif hasattr(chunk, 'response_metadata'):
                    # Ignorar chunks de metadata
                    continue
                    
                # Limpar e validar conteúdo
                if content:
                    # Converter para string e limpar espaços extras
                    content = str(content).strip()
                    
                    # Verificações de qualidade
                    if content and not any(invalid in content.lower() for invalid in ['<bound method', '.<bound', '.bound']):
                        # Não enviar apenas pontos ou pontos com espaços
                        if content != '.' and not content.strip().startswith('.'):
                            # Acumular no buffer para evitar cortar palavras
                            partial_chunk += content
                            
                            # Verificar se temos uma palavra completa ou uma pontuação antes de enviar
                            if partial_chunk.endswith((' ', '.', ',', '!', '?', ':', ';', '\n')) or len(partial_chunk) > 20:
                                # Pode enviar o buffer acumulado pois termina em espaço ou pontuação
                                yield partial_chunk
                                partial_chunk = ""
            
            # Enviar qualquer texto restante no buffer
            if partial_chunk:
                yield partial_chunk
                    
        except Exception as e:
            logger.error(f"Erro no streaming: {str(e)}")
            yield f"❌ Erro na geração da resposta: {str(e)}"

        client = self.ai_manager.get_client()
        if not client:
            status = self.ai_manager.get_status()
            raise RuntimeError(f"IA indisponível: {status['error']}")

        # Preparar prompt
        prompt = self.prepare_question_prompt(financial_data, user_question, personalidade)
        
        try:
            # Buffer para armazenar chunks parciais que podem estar cortando palavras
            partial_chunk = ""
            
            # Stream da resposta real com o4-mini
            for chunk in client.stream(prompt):
                # Extração robusta do conteúdo do chunk
                content = None
                
                # Tentar extrair conteúdo do chunk em ordem de prioridade
                if hasattr(chunk, 'content') and chunk.content:
                    content = chunk.content
                elif hasattr(chunk, 'text') and chunk.text:
                    content = chunk.text
                elif isinstance(chunk, str):
                    content = chunk
                elif hasattr(chunk, 'response_metadata'):
                    # Ignorar chunks de metadata
                    continue
                    
                # Limpar e validar conteúdo
                if content:
                    # Converter para string e limpar espaços extras
                    content = str(content).strip()
                    
                    # Verificações de qualidade
                    if content and not any(invalid in content.lower() for invalid in ['<bound method', '.<bound', '.bound']):
                        # Não enviar apenas pontos ou pontos com espaços
                        if content != '.' and not content.strip().startswith('.'):
                            # Acumular no buffer para evitar cortar palavras
                            partial_chunk += content
                            
                            # Verificar se temos uma palavra completa ou uma pontuação antes de enviar
                            if partial_chunk.endswith((' ', '.', ',', '!', '?', ':', ';', '\n')) or len(partial_chunk) > 20:
                                # Pode enviar o buffer acumulado pois termina em espaço ou pontuação
                                yield partial_chunk
                                partial_chunk = ""
            
            # Enviar qualquer texto restante no buffer
            if partial_chunk:
                yield partial_chunk
                    
        except Exception as e:
            logger.error(f"Erro no streaming: {str(e)}")
            yield f"❌ Erro na geração da resposta: {str(e)}"
# Instância do serviço financeiro
financial_service = FinancialAIService(ai_manager)

# === FUNÇÕES DE DADOS ===

@functools.lru_cache(maxsize=32)
def get_financial_data(username: str, data_inicio: Optional[str] = None, data_fim: Optional[str] = None) -> Dict[str, Any]:
    """Busca dados financeiros do usuário com cache usando Backend V2"""
    try:
        # Inicializar Backend V2
        db_manager = DatabaseManager()
        user_repo = UsuarioRepository(db_manager)
        transacao_repo = TransacaoRepository(db_manager)
        
        # Obter usuário usando o username da sessão
        usuario_atual = user_repo.obter_usuario_por_username(username)
        
        if not usuario_atual:
            return {"error": "Usuário não encontrado"}
        
        user_id = usuario_atual.get('id')
        if not user_id:
            return {"error": "ID do usuário não encontrado"}

        # Definir período padrão se não fornecido (últimos 4 meses)
        if not data_fim:
            data_fim = datetime.now().strftime('%Y-%m-%d')
        if not data_inicio:
            data_inicio = (datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d')
        
        # Garantir que as datas são strings válidas
        data_inicio_str = str(data_inicio)
        data_fim_str = str(data_fim)
        
        # Buscar dados do período selecionado usando Backend V2
        df_transacoes = transacao_repo.obter_transacoes_periodo(
            user_id=user_id,
            data_inicio=data_inicio_str,
            data_fim=data_fim_str,
            incluir_excluidas=False,
            limite=None
        )
        
        # Verificar se há dados
        if df_transacoes.empty:
            return {"error": "Nenhum dado financeiro encontrado para este usuário no período selecionado"}
        
        # Separar por tipo de transação
        df_receitas = df_transacoes[df_transacoes['valor'] > 0]
        df_despesas = df_transacoes[df_transacoes['valor'] < 0]
        
        # Calcular número de dias do período
        periodo_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d')
        periodo_fim = datetime.strptime(data_fim_str, '%Y-%m-%d')
        period_days = (periodo_fim - periodo_inicio).days + 1
        
        # Buscar metas e compromissos do usuário
        compromissos = get_user_commitments(user_id, data_inicio_str, data_fim_str)
        
        # Análise básica
        analysis = {
            "total_transactions": len(df_transacoes),
            "period_days": period_days,
            "data_inicio": data_inicio_str,
            "data_fim": data_fim_str,
            "extratos": {
                "count": len(df_receitas),
                "receitas": df_receitas['valor'].sum() if not df_receitas.empty else 0,
                "despesas": abs(df_despesas['valor'].sum()) if not df_despesas.empty else 0
            },
            "cartoes": {
                "count": len(df_despesas),
                "gastos": abs(df_despesas['valor'].sum()) if not df_despesas.empty else 0
            },
            "user_id": user_id,
            "username": username,
            "compromissos": compromissos  # Adicionar dados de compromissos
        }
        
        # Análise por categorias (se disponível)
        if not df_transacoes.empty and 'categoria' in df_transacoes.columns:
            gastos_por_categoria = df_transacoes[df_transacoes['valor'] < 0].groupby('categoria')['valor'].sum().abs().sort_values(ascending=False)
            analysis["categorias"] = gastos_por_categoria.to_dict()
        
        return analysis
        
    except Exception as e:
        logger.error(f"Erro ao buscar dados financeiros: {str(e)}")
        return {"error": f"Erro ao carregar dados: {str(e)}"}

@functools.lru_cache(maxsize=32)
def get_user_commitments(user_id: int, data_inicio: str, data_fim: str) -> Dict[str, Any]:
    """Busca metas e compromissos do usuário no período"""
    try:
        # Inicializar repositório
        db_manager = DatabaseManager()
        compromisso_repo = CompromissoRepository(db_manager)
        
        # Buscar todos os compromissos do período
        df_todos = compromisso_repo.obter_compromissos(user_id, "pendente")
        
        if df_todos.empty:
            return {
                "total": 0,
                "valor_total": 0,
                "por_categoria": {},
                "proximos": []
            }
        
        # Filtrar compromissos do período
        df_todos['data_vencimento'] = pd.to_datetime(df_todos['data_vencimento'])
        mask_periodo = (
            df_todos['data_vencimento'] >= pd.to_datetime(data_inicio)
        ) & (
            df_todos['data_vencimento'] <= pd.to_datetime(data_fim)
        )
        df_periodo = df_todos[mask_periodo]
        
        # Análise por categoria
        por_categoria = {}
        if not df_periodo.empty:
            por_categoria = df_periodo.groupby('categoria')['valor'].agg(['sum', 'count']).to_dict('index')
        
        # Lista dos próximos compromissos
        proximos = []
        for _, row in df_todos.iterrows():
            proximos.append({
                "descricao": row['descricao'],
                "valor": float(row['valor']),
                "data_vencimento": row['data_vencimento'].strftime('%Y-%m-%d'),
                "categoria": row['categoria'],
                "observacoes": row['observacoes'] if pd.notna(row['observacoes']) else None
            })
        
        return {
            "total": len(df_periodo),
            "valor_total": float(df_periodo['valor'].sum()) if not df_periodo.empty else 0,
            "por_categoria": {
                cat: {
                    "total": float(data['sum']),
                    "count": int(data['count'])
                }
                for cat, data in por_categoria.items()
            },
            "proximos": proximos[:5]  # Limitar a 5 próximos compromissos
        }
        
    except Exception as e:
        logger.error(f"Erro ao buscar compromissos: {str(e)}")
        return {
            "error": f"Erro ao carregar compromissos: {str(e)}",
            "total": 0,
            "valor_total": 0,
            "por_categoria": {},
            "proximos": []
        }
# === INTERFACE PRINCIPAL ===

def main():
    """Função principal da aplicação"""
    
    # Verificar autenticação
    verificar_autenticacao()
    
    # Componente de boas-vindas
    usuario = st.session_state.get('usuario', 'default')
    boas_vindas_com_foto(usuario)
      # Título principal
    st.title("💡 Dicas Financeiras com IA")
    st.markdown("---")
      # Seletor de personalidade da IA
    st.subheader("🎭 Escolha a Personalidade da IA")
    
    personalidade_selecionada = st.selectbox(
        "Como você gostaria que a IA se comunique com você?",
        options=list(personalidade_opcoes.keys()),
        format_func=lambda x: personalidade_opcoes[x],
        index=0,        help="Escolha o estilo de comunicação que você prefere para suas análises e respostas"
    )
    
    st.markdown("---")
    
    # === FILTRO DE PERÍODO ===
    st.subheader("📅 Selecionar Período de Análise")
    
    # Buscar dados iniciais para configurar o filtro
    username = st.session_state.get('usuario', 'default')
    data_inicio_str = None
    data_fim_str = None
    
    try:
        # Obter dados básicos para o filtro
        db_manager = DatabaseManager()
        user_repo = UsuarioRepository(db_manager)
        transacao_repo = TransacaoRepository(db_manager)
        
        usuario_atual = user_repo.obter_usuario_por_username(username)
        if usuario_atual:
            user_id = usuario_atual.get('id')
            if user_id:
                # Buscar transações para definir range do filtro
                df_for_filter = transacao_repo.obter_transacoes_periodo(
                    user_id=int(user_id),
                    data_inicio='2020-01-01',
                    data_fim=datetime.now().strftime('%Y-%m-%d'),
                    incluir_excluidas=False,
                    limite=None
                )
                
                if not df_for_filter.empty and 'data' in df_for_filter.columns:
                    # Converter coluna de data
                    df_for_filter['Data'] = pd.to_datetime(df_for_filter['data'])
                    data_inicio, data_fim = filtro_data(df_for_filter, key_prefix="dicas_ia")
                    
                    # Converter datas para string
                    data_inicio_str = data_inicio.strftime('%Y-%m-%d')
                    data_fim_str = data_fim.strftime('%Y-%m-%d')
                    
                    st.sidebar.success(f"📅 Período: {data_inicio} a {data_fim}")
    except Exception as e:
        st.sidebar.error(f"❌ Erro no filtro: {str(e)}")
      # Valores padrão se não definidos
    if not data_inicio_str or not data_fim_str:
        data_inicio_str = (datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d')
        data_fim_str = datetime.now().strftime('%Y-%m-%d')
        st.sidebar.info("📅 Período padrão (últimos 4 meses)")
    
    # Salvar datas no session_state para uso no chat
    st.session_state['data_inicio_filtro'] = data_inicio_str
    st.session_state['data_fim_filtro'] = data_fim_str
    
    st.markdown("---")
    
    # Seção principal
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📊 Análise Financeira Personalizada")
        
        if st.button("🔍 Analisar Minhas Finanças", type="primary"):
            with st.spinner("Analisando seus dados financeiros..."):
                try:                    # Buscar dados do usuário logado usando Backend V2
                    username = st.session_state.get('usuario', 'default')
                    financial_data = get_financial_data(username, data_inicio_str, data_fim_str)
                    # Diagnóstico: Exibir dados brutos se necessário
                    # st.write(financial_data)
                    analysis_result = financial_service.analyze_financial_data(financial_data, personalidade_selecionada)
                    with st.expander("📈 Resumo dos Dados", expanded=True):
                        col_a, col_b, col_c = st.columns(3)
                        with col_a:
                            st.metric("Transações Analisadas", financial_data['total_transactions'])
                        with col_b:
                            receitas = financial_data.get('extratos', {}).get('receitas', 0)
                            st.metric("Receitas", formatar_valor_monetario(receitas))
                        with col_c:
                            despesas = financial_data.get('extratos', {}).get('despesas', 0)
                            gastos_cartao = financial_data.get('cartoes', {}).get('gastos', 0)
                            total_gastos = despesas + gastos_cartao
                            st.metric("Total de Gastos", formatar_valor_monetario(total_gastos))
                    
                    st.subheader("🤖 Análise e Dicas Personalizadas")
                    # Aplicar formatação para melhorar legibilidade
                    analysis_result_formatted = format_ai_response(analysis_result)
                    st.markdown(analysis_result_formatted, unsafe_allow_html=True)
                    
                    if "categorias" in financial_data and financial_data["categorias"]:
                        st.subheader("📊 Gastos por Categoria")
                        categorias_df = pd.DataFrame(
                            list(financial_data["categorias"].items()),
                            columns=['Categoria', 'Valor']
                        )
                        st.bar_chart(categorias_df.set_index('Categoria'))
                except Exception as e:
                    st.error(f"❌ Erro ao processar análise: {str(e)}")
                    st.info("Se o erro persistir, envie esta mensagem para o suporte.")
                    logger.error(f"Erro detalhado: {str(e)}", exc_info=True)
    
    with col2:
        # Coluna 2 vazia - conteúdo movido para o final da página
        st.empty()

    # Seção do Chat com IA
    st.markdown("---")
    st.subheader("💬 Chat com IA Financeira")
    exibir_chat_interface(personalidade_selecionada)

    # === SEÇÃO DICAS EDUCATIVAS ===
    st.markdown("---")
    st.subheader("📚 Dicas Educativas")
    
    # Criar abas para diferentes categorias de dicas
    tab1, tab2, tab3, tab4 = st.tabs(["💰 Poupança", "📊 Investimentos", "🏠 Gastos Domésticos", "🎯 Metas Financeiras"])
    
    with tab1:
        st.markdown("""
        ### 💡 Dicas para Economizar no Dia a Dia
        
        **🛒 Compras Inteligentes:**
        - Faça uma lista antes de ir ao mercado e se atenha a ela
        - Compare preços em diferentes estabelecimentos
        - Aproveite promoções e compre produtos não perecíveis em quantidade
        - Evite compras por impulso, espere 24h antes de comprar algo não essencial
        
        **🏠 Economia Doméstica:**
        - Desligue aparelhos da tomada quando não estiver usando
        - Use lâmpadas LED para reduzir o consumo de energia
        - Regule a temperatura do ar-condicionado (24°C é ideal)
        - Conserte vazamentos rapidamente para evitar desperdício de água
        
        **🍽️ Alimentação:**
        - Cozinhe mais em casa, é mais barato e saudável
        - Planeje o cardápio da semana para evitar desperdícios
        - Aproveite sobras para criar novas refeições
        """)
    
    with tab2:
        st.markdown("""
        ### 📈 Primeiros Passos nos Investimentos
        
        **🎯 Princípios Básicos:**
        - Comece criando uma reserva de emergência (6-12 meses de gastos)
        - Estude sobre diferentes tipos de investimento antes de aplicar
        - Diversifique seus investimentos para reduzir riscos
        - Invista apenas o que você pode permitir-se perder
        
        **📋 Tipos de Investimento para Iniciantes:**
        - **Poupança:** Segura, mas com baixo rendimento
        - **Tesouro Direto:** Títulos públicos com boa segurança
        - **CDB:** Certificado de Depósito Bancário, protegido pelo FGC
        - **Fundos de Investimento:** Diversificação profissional
        
        **⚠️ Cuidados Importantes:**
        - Desconfie de promessas de ganhos muito altos
        - Entenda os custos e taxas antes de investir
        - Acompanhe seus investimentos regularmente
        """)
    
    with tab3:
        st.markdown("""
        ### 🏠 Gestão de Gastos Domésticos
        
        **📋 Controle de Orçamento:**
        - Use a regra 50-30-20: 50% necessidades, 30% desejos, 20% poupança
        - Registre todos os gastos por pelo menos um mês
        - Identifique gastos desnecessários e elimine-os
        - Negocie contas fixas como internet, telefone e seguros
        
        **🔧 Manutenção Preventiva:**
        - Faça manutenção regular de eletrodomésticos
        - Limpe filtros de ar-condicionado mensalmente
        - Verifique vazamentos e problemas elétricos periodicamente
        
        **🛍️ Compras Planejadas:**
        - Pesquise preços antes de grandes compras
        - Considere produtos usados em bom estado
        - Avalie se realmente precisa antes de comprar
        """)
    
    with tab4:
        st.markdown("""
        ### 🎯 Definindo e Alcançando Metas Financeiras
        
        **📝 Como Definir Metas:**
        - Seja específico: "poupar R$ 5.000 em 12 meses"
        - Estabeleça prazos realistas
        - Divida metas grandes em objetivos menores
        - Anote suas metas e revise regularmente
        
        **🎯 Exemplos de Metas:**
        - **Curto prazo (até 1 ano):** Reserva de emergência, viagem
        - **Médio prazo (1-5 anos):** Curso, carro, entrada da casa
        - **Longo prazo (5+ anos):** Aposentadoria, casa própria
        
        **💪 Mantendo o Foco:**
        - Visualize o benefício de alcançar sua meta
        - Comemore pequenas conquistas no caminho
        - Ajuste metas se necessário, mas não desista
        - Use aplicativos ou planilhas para acompanhar progresso
        """)
    
    # Dica do dia
    st.markdown("---")
    st.info("""
    💡 **Dica do Dia:** O segredo para o sucesso financeiro não é quanto você ganha, 
    mas quanto você consegue guardar e investir de forma inteligente. Comece pequeno, 
    seja consistente e os resultados aparecerão!
    """)

    # Rodapé
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 20px;'>
        💡 <strong>Richness</strong> - Sua jornada financeira com tecnologia de IA<br>
        🔒 Dados protegidos | 🤖 IA responsável | 📊 Análises precisas
    </div>
    """, unsafe_allow_html=True)

    # Botão sair sempre visível
    if st.session_state.get('autenticado', False):
        if st.button('🚪 Sair', key='logout_btn'):
            st.session_state.clear()
            st.success('Você saiu do sistema.')
            st.rerun()

# === SISTEMA DE CHAT ===

def inicializar_chat():
    """Inicializa o sistema de chat na sessão do usuário"""
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'chat_input' not in st.session_state:
        st.session_state.chat_input = ""
    if 'processing_message' not in st.session_state:
        st.session_state.processing_message = False

def adicionar_mensagem_chat(pergunta: str, resposta: str, personalidade: str):
    """Adiciona uma mensagem ao histórico do chat"""
    from datetime import datetime
    
    mensagem = {
        'timestamp': datetime.now(),
        'pergunta': pergunta,
        'resposta': resposta,
        'personalidade': personalidade
    }
    
    st.session_state.chat_history.append(mensagem)

def salvar_conversa_bd(user_id: int, pergunta: str, resposta: str, personalidade: str):
    """Salva a conversa no banco de dados"""
    try:
        db_manager = DatabaseManager()
        conversa_repo = ConversaIARepository(db_manager)
        conversa_repo.salvar_conversa(user_id, pergunta, resposta, personalidade)
    except Exception as e:
        logger.error(f"Erro ao salvar conversa: {e}")

def carregar_historico_bd(user_id: int) -> List[Dict]:
    """Carrega histórico de conversas do banco de dados"""
    try:
        db_manager = DatabaseManager()
        conversa_repo = ConversaIARepository(db_manager)
        df_conversas = conversa_repo.obter_conversas_usuario(user_id, limite=20)
        
        if not df_conversas.empty:
            historico = []
            for _, row in df_conversas.iterrows():
                historico.append({
                    'id': row['id'],
                    'timestamp': row['created_at'],
                    'pergunta': row['pergunta'],
                    'resposta': row['resposta'],
                    'personalidade': row['personalidade']
                })
            return historico
        
        return []
    except Exception as e:
        logger.error(f"Erro ao carregar histórico: {e}")
        return []

def exibir_chat_interface(personalidade_selecionada: str):
    """Exibe a interface de chat interativo"""
    # CSS customizado para chat moderno
    st.markdown("""
    <style>
    .chat-container {
        background-color: #1e1e1e;
        border-radius: 15px;
        padding: 20px;
        max-height: 500px;
        overflow-y: auto;
        margin-bottom: 20px;
        scroll-behavior: smooth;
        border: 1px solid #333;
    }
    
    .chat-container::-webkit-scrollbar {
        width: 6px;
    }
    
    .chat-container::-webkit-scrollbar-track {
        background: #2a2a2a;
        border-radius: 10px;
    }
    
    .chat-container::-webkit-scrollbar-thumb {
        background: #555;
        border-radius: 10px;
    }
    
    .chat-container::-webkit-scrollbar-thumb:hover {
        background: #777;
    }
    
    .user-message {
        display: flex;
        justify-content: flex-end;
        margin-bottom: 15px;
    }
    
    .user-bubble {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 12px 18px;
        border-radius: 20px 20px 5px 20px;
        max-width: 70%;
        word-wrap: break-word;
        box-shadow: 0 3px 10px rgba(102, 126, 234, 0.3);
        font-size: 14px;
        line-height: 1.4;
    }
    
    .ai-message {
        display: flex;
        justify-content: flex-start;
        margin-bottom: 15px;
    }    .ai-bubble {
        background-color: #2a2a2a;
        color: #e0e0e0;
        padding: 16px 20px;
        border-radius: 20px 20px 20px 5px;
        max-width: 70%;
        word-wrap: break-word;
        box-shadow: 0 3px 10px rgba(0,0,0,0.2);
        border: 1px solid #404040;
        font-size: 14px;
        line-height: 1.7;
        letter-spacing: 0.02em;
    }
    
    /* Melhorias de estilo para conteúdo formatado */
    .ai-bubble strong {
        color: #a991f7;
        font-weight: 600;
    }
    
    .ai-bubble br + br {
        content: "";
        display: block;
        margin-top: 10px;
    }
    
    /* Espaçamento melhorado para elementos específicos */
    .ai-bubble ul, .ai-bubble ol {
        margin-top: 8px;
        margin-bottom: 8px;
        padding-left: 20px;
    }
    
    .ai-bubble li {
        margin-bottom: 5px;
    }
    
    /* Melhoria para realce de texto importante */
    .ai-bubble span[style*="color:#28a745"] {
        background-color: rgba(40, 167, 69, 0.1);
        padding: 0 3px;
        border-radius: 3px;
    }
    
    .ai-bubble span[style*="color:#dc3545"] {
        background-color: rgba(220, 53, 69, 0.1);
        padding: 0 3px;
        border-radius: 3px;
    }
    
    /* Container principal do input */
    .input-wrapper {
        max-width: 800px;
        margin: 15px auto;
        padding: 0 10px;
    }
    
    .input-container {
        background-color: #2a2a2a;
        padding: 6px 6px 6px 16px;
        border-radius: 30px;
        box-shadow: 0 2px 15px rgba(0,0,0,0.2);
        display: flex;
        align-items: center;
        gap: 8px;
        border: 1px solid #404040;
    }
    
    .input-field {
        flex: 1 1 auto;
    }
    
    /* Estilização do input */
    .input-field .stTextInput {
        width: 100%;
    }
    
    .input-field .stTextInput > div {
        border: none !important;
        background: transparent !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    
    .input-field .stTextInput > div > div {
        min-height: auto !important;
        padding: 0 !important;
    }
    
    .input-field .stTextInput > div > div > input {
        border: none !important;
        padding: 8px 0 !important;
        font-size: 15px !important;
        background-color: transparent !important;
        color: #e0e0e0 !important;
        width: 100% !important;
        line-height: 1.2 !important;
        min-height: unset !important;
        box-shadow: none !important;
    }
    
    .input-field .stTextInput > div > div > input::placeholder {
        color: rgba(255,255,255,0.5) !important;
        font-size: 15px !important;
    }
    
    /* Estilo do botão de envio do chat */
    .chat-send-button {
        flex: 0 0 auto;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-left: 4px;
    }
    
    .chat-send-button button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        border: none !important;
        border-radius: 50% !important;
        width: 36px !important;
        height: 36px !important;
        min-width: 36px !important;
        min-height: 36px !important;
        color: white !important;
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3) !important;
        transition: all 0.2s ease !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        padding: 0 !important;
        margin: 0 !important;
        font-size: 20px !important;
        cursor: pointer !important;
    }
    
    .chat-send-button button:hover {
        transform: scale(1.05) !important;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.6) !important;
    }
    
    .chat-send-button button:active {
        transform: scale(0.95) !important;
        box-shadow: 0 1px 4px rgba(102, 126, 234, 0.4) !important;
    }
    
    .chat-send-button button:disabled {
        background: #555 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.2) !important;
        transform: none !important;
        opacity: 0.6 !important;
        cursor: not-allowed !important;
    }
    
    /* Efeito focus no input */
    .stTextInput > div > div > input:focus {
        outline: none !important;
        box-shadow: none !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Inicializar chat
    inicializar_chat()
    
    # Obter user_id
    username = st.session_state.get('usuario', 'default')
    try:
        db_manager = DatabaseManager()
        user_repo = UsuarioRepository(db_manager)
        usuario_atual = user_repo.obter_usuario_por_username(username)
        user_id = usuario_atual.get('id') if usuario_atual else None
    except:
        user_id = None
    
    # Container para o histórico do chat
    chat_container = st.container()
    
    with chat_container:
        # Botões de controle
        col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([1, 1, 2])
        
        with col_ctrl1:
            if st.button("🔄 Nova Conversa", help="Limpar chat atual"):
                st.session_state.chat_history = []
                st.rerun()
        
        with col_ctrl2:
            if user_id and st.button("📂 Carregar Histórico", help="Carregar conversas salvas"):
                historico_bd = carregar_historico_bd(user_id)
                if historico_bd:
                    st.session_state.chat_history = historico_bd
                    st.success(f"✅ {len(historico_bd)} conversas carregadas!")
                    st.rerun()
                else:
                    st.info("📝 Nenhuma conversa encontrada no histórico")
        
        # Área de chat
        chat_area = st.container()
        
        # Exibir histórico
        if st.session_state.chat_history:
            with chat_area:
                # Container do chat com estilo moderno
                st.markdown('<div class="chat-container">', unsafe_allow_html=True)
                
                for idx, msg in enumerate(st.session_state.chat_history):
                    # Mensagem do usuário (alinhada à direita)
                    st.markdown(f"""
                    <div class="user-message">
                        <div class="user-bubble">
                            👤 <strong>Você:</strong> {msg['pergunta']}
                            <br><small style='opacity: 0.7; font-size: 0.7em;'>{msg['timestamp'].strftime('%d/%m/%Y %H:%M')}</small>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                      # Mensagem da IA (alinhada à esquerda)
                    if msg['resposta'] != "🔄 Gerando resposta...":
                        # Aplicar formatação na resposta da IA
                        resposta_formatada = format_ai_response(msg['resposta'])
                        st.markdown(f"""
                        <div class="ai-message">
                            <div class="ai-bubble">
                                🤖 <strong>IA:</strong><br><br>{resposta_formatada}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        # Indicador de digitando com animação
                        st.markdown(f"""
                        <div class="ai-message">
                            <div class="ai-bubble">
                                🤖 <strong>IA:</strong> <span style='animation: blink 1.5s infinite;'>✨ Digitando...</span>
                            </div>
                        </div>
                        <style>
                        @keyframes blink {{
                            0%, 50% {{ opacity: 1; }}
                            51%, 100% {{ opacity: 0.3; }}
                        }}
                        </style>
                        """, unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Script para rolar automaticamente para o final do chat
                st.markdown("""
                <script>
                setTimeout(function() {
                    var chatContainer = document.querySelector('.chat-container');
                    if (chatContainer) {
                        chatContainer.scrollTop = chatContainer.scrollHeight;
                    }
                }, 100);
                </script>
                """, unsafe_allow_html=True)
        
        # Container personalizado para input e botão
        st.markdown("""
        <div class="input-wrapper">
            <div class="input-container">
                <div class="input-field">
        """, unsafe_allow_html=True)
        
        # Input field
        user_question = st.text_input(
            "",
            value="",  # Sempre limpo
            placeholder="Envie uma mensagem...",
            key=f"chat_input_field_{len(st.session_state.chat_history)}",  # Key única para resetar
            label_visibility="collapsed"
        )
        
        # Fechamento do input-field e abertura do container do botão
        st.markdown("""
                </div>
                <div class="chat-send-button">
        """, unsafe_allow_html=True)
        
        # Botão de envio
        enviar = st.button(
            "➤", 
            type="primary",
            disabled=not (user_question and user_question.strip()),
            help="Enviar mensagem",
            key=f"send_btn_{len(st.session_state.chat_history)}"
        )
        
        # Fechamento dos containers
        st.markdown("""
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if enviar and user_question and user_question.strip():
            # Adicionar pergunta ao histórico imediatamente
            adicionar_mensagem_chat(user_question, "🔄 Gerando resposta...", personalidade_selecionada)
            
            # Processar resposta em background
            try:
                # Buscar dados financeiros com período do filtro
                data_inicio_filtro = st.session_state.get('data_inicio_filtro')
                data_fim_filtro = st.session_state.get('data_fim_filtro')
                financial_data = get_financial_data(username, data_inicio_filtro, data_fim_filtro)
                
                # Container para resposta em tempo real
                message_placeholder = st.empty()
                resposta_completa = ""
                  # Gerar e exibir resposta completa (sem streaming)
                resposta_completa = financial_service.get_response(financial_data, user_question, personalidade_selecionada)
                resposta_formatada = format_ai_response(resposta_completa)
                message_placeholder.markdown(f"""
                <div class="ai-message">
                    <div class="ai-bubble">
                        🤖 <strong>IA:</strong><br><br>{resposta_formatada}
                    </div>
                </div>
                <script>
                setTimeout(function() {{
                    var chatContainer = document.querySelector('.chat-container');
                    if (chatContainer) {{
                        chatContainer.scrollTop = chatContainer.scrollHeight;
                    }}
                }}, 50);
                </script>
                """, unsafe_allow_html=True)
                # Atualizar histórico com resposta completa
                if st.session_state.chat_history:
                    st.session_state.chat_history[-1]['resposta'] = resposta_completa
                # Salvar no banco de dados (salvar texto puro, não formatado)
                if user_id:
                    salvar_conversa_bd(user_id, user_question, resposta_completa, personalidade_selecionada)
                # Limpar placeholder após conclusão
                message_placeholder.empty()
            
            except Exception as e:
                # Atualizar com erro
                if st.session_state.chat_history:
                    st.session_state.chat_history[-1]['resposta'] = f"❌ Erro: {str(e)}"
                logger.error(f"Erro no chat: {e}")
            
            # Recarregar para mostrar resposta atualizada e limpar campo
            st.rerun()

def format_ai_response(text):
    """Formata a resposta da IA para melhor legibilidade, sem tentar separar ou juntar palavras."""
    if not text or not isinstance(text, str):
        return ""
    import re
    # Apenas formatação visual básica, sem manipular palavras
    text = text.strip()
    text = text.replace("\u200b", "")
    text = text.replace("\u00a0", " ")
    # Quebras de linha para parágrafos
    text = text.replace("\n", "<br>")
    # Destaque de valores monetários
    text = re.sub(r'(R\$\s*\d+[\d\.,]*)', r'<span style="color:#28a745;font-weight:bold">\1</span>', text)
    # Destaque de percentuais
    text = re.sub(r'(\+\s*\d+[\d\.,]*\s*%)', r'<span style="color:#28a745;font-weight:bold">\1</span>', text)
    text = re.sub(r'(\-\s*\d+[\d\.,]*\s*%)', r'<span style="color:#dc3545;font-weight:bold">\1</span>', text)
    text = re.sub(r'(\d+[\d\.,]*\s*%)', r'<span style="font-weight:bold">\1</span>', text)
    return text

def separar_palavras_juntas(text):
    """Função auxiliar para separar palavras que estão juntas (sem espaço) e corrigir espaçamento incorreto entre letras"""
    import re
    
    # ETAPA 1: Corrigir problemas de espaçamento entre letras
    
    # Padrão para detectar e corrigir sequências de letras espaçadas incorretamente
    # Exemplo: "e s t a" -> "esta", "p a l a v r a" -> "palavra"
    
    # Corrige padrões onde letras individuais estão separadas por espaços
    # mas claramente formam uma palavra
    text = re.sub(
        r'(?<!\w)([a-zA-ZáàâãéèêíìîóòôõúùûçÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ])\s([a-zA-ZáàâãéèêíìîóòôõúùûçÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ])(?:\s([a-zA-ZáàâãéèêíìîóòôõúùûçÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ]))?(?:\s([a-zA-ZáàâãéèêíìîóòôõúùûçÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ]))?(?:\s([a-zA-ZáàâãéèêíìîóòôõúùûçÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ]))?(?:\s([a-zA-ZáàâãéèêíìîóòôõúùûçÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ]))?(?:\s([a-zA-ZáàâãéèêíìîóòôõúùûçÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ]))?(?:\s([a-zA-ZáàâãéèêíìîóòôõúùûçÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ]))?(?:\s([a-zA-ZáàâãéèêíìîóòôõúùûçÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ]))?(?:\s([a-zA-ZáàâãéèêíìîóòôõúùûçÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ]))?(?!\w)',
        lambda m: ''.join(c for c in m.groups() if c is not None),
        text
    )
    
    # Remove espaços entre letras individuais que quebram palavras
    text = re.sub(r'(?<=[a-zA-ZáàâãéèêíìîóòôõúùûçÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ])\s(?=[a-zA-ZáàâãéèêíìîóòôõúùûçÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ])', '', text)
    
    # ETAPA 2: Normalização de espaços
    
    # Normalizar múltiplos espaços em um único espaço
    text = re.sub(r'\s+', ' ', text)
    
    # ETAPA 3: Separar palavras grudadas
    
    # Lista de padrões para identificar palavras grudadas
    padroes = [
        # Separa palavras onde uma minúscula é seguida por maiúscula (padrão camelCase)
        (r'([a-záàâãéèêíìîóòôõúùûç])([A-ZÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ])', r'\1 \2'),
        
        # Separa números de letras
        (r'(\d)([A-Za-záàâãéèêíìîóòôõúùûçÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ])', r'\1 \2'),
        (r'([A-Za-záàâãéèêíìîóòôõúùûçÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ])(\d)', r'\1 \2'),
        
        # Separa ponto final de palavra sem espaço
        (r'(\.)([A-Z])', r'\1 \2'),
        
        # Separa sinais de pontuação de palavras (quando não há espaço)
        (r'([,:;!?])([A-Za-z0-9])', r'\1 \2'),
        
        # Separa parênteses do conteúdo
        (r'([A-Za-z0-9])(\()', r'\1 \2'),
        (r'(\))([A-Za-z0-9])', r'\1 \2'),
        
        # Separar R$ de valores sem espaço
        (r'(R\$)(\d)', r'\1 \2')
    ]
    
    # Aplicar padrões para separar palavras grudadas
    resultado = text
    for padrao, substituicao in padroes:
        resultado = re.sub(padrao, substituicao, resultado, flags=re.IGNORECASE)
    
    return resultado

def corrigir_html(html):
    """Corrige problemas comuns em tags HTML que podem causar erros no DOM"""
    import re
    
    # Adicionar espaço entre nome da tag e atributos
    # Exemplo: <spanstyle="color:#28a745"> -> <span style="color:#28a745">
    html = re.sub(r'<([\w]+)(style=)', r'<\1 \2', html)
    
    # Garantir que todas as tags tenham espaço antes de atributos
    html = re.sub(r'<([\w]+)([^>]*?)(style=)', r'<\1 \3', html)
    
    # Corrigir possíveis tags não fechadas
    tags_abertas = re.findall(r'<(span|strong|div|p)(?:\s[^>]*)?>', html)
    for tag in tags_abertas:
        # Verificar se há tag de fechamento correspondente
        if f'</{tag}>' not in html:
            # Adicionar tag de fechamento ao final se não existir
            html += f'</{tag}>'
    
    # Sanitizar aspas em atributos HTML para evitar problemas de sintaxe
    html = re.sub(r'(style=)(["\'])([^"\']*?)(["\'])', r'\1"\3"', html)
    
    return html

# Definir opções de personalidade globalmente para uso no chat
personalidade_opcoes = {
    "clara": "😊 Mais clara, acolhedora e engraçada",
    "tecnica": "🎓 Mais técnica e formal", 
    "durona": "💪 Mais durona e informal"
}

# Executar a aplicação
main()
