# -*- coding: utf-8 -*-
"""
Página de Dicas Financeiras com IA - Versão Corrigida
Implementa conexão robusta com LangChain e OpenAI
"""

import streamlit as st
import pandas as pd
import functools
import os
import sys
import logging
from typing import Optional, Tuple, List, Any, Dict
from datetime import datetime, timedelta
from pydantic import SecretStr

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
    from utils.pluggy_connector import PluggyConnector
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
            from pydantic import SecretStr
            
            config = get_config()
            api_key = config.get_openai_api_key()
            # Use environment variable approach for better compatibility
            os.environ["OPENAI_API_KEY"] = api_key
            
            self._openai_client = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.2,
                max_completion_tokens=150,
                api_key=SecretStr(api_key)
            )
            
            # Teste básico do cliente
            test_response = self._openai_client.invoke("Teste")
            logger.info("✅ Cliente OpenAI inicializado com sucesso")
            
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
        st.success("🤖 IA totalmente funcional e conectada")
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

    def analyze_financial_data(self, financial_data: Dict) -> str:
        """Analisa dados financeiros usando IA"""
        # Diagnóstico: Verificar se dados do Pluggy vieram com erro
        if "error" in financial_data:
            raise RuntimeError(f"Erro ao buscar dados financeiros: {financial_data['error']}")

        # Diagnóstico: Inicialização da IA
        if not self.ai_manager.initialize():
            status = self.ai_manager.get_status()
            raise RuntimeError(f"Erro ao inicializar IA: {status['error']}")

        client = self.ai_manager.get_client()
        if not client:
            status = self.ai_manager.get_status()
            raise RuntimeError(f"Cliente IA não disponível: {status['error']}")

        try:
            # Preparar dados para análise
            analysis_prompt = self._prepare_analysis_prompt(financial_data)
            cache_key = str(hash(str(financial_data)))
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

    def _prepare_analysis_prompt(self, data: Dict) -> str:
        """Prepara o prompt para análise financeira"""
        return f"""
Analise os seguintes dados financeiros e forneça dicas personalizadas:

Dados Financeiros:
- Total de transações: {data.get('total_transactions', 0)}
- Período analisado: {data.get('period_days', 0)} dias
- Receitas: R$ {data.get('extratos', {}).get('receitas', 0):.2f}
- Despesas: R$ {data.get('extratos', {}).get('despesas', 0):.2f}
- Gastos no cartão: R$ {data.get('cartoes', {}).get('gastos', 0):.2f}

Por favor, forneça:
1. Análise do padrão de gastos
2. 3-5 dicas específicas de economia
3. Sugestões de melhoria no orçamento
4. Alertas sobre possíveis problemas

Mantenha as dicas práticas e aplicáveis.
"""

# Instância do serviço financeiro
financial_service = FinancialAIService(ai_manager)

# === FUNÇÕES DE DADOS ===

@functools.lru_cache(maxsize=32)
def get_financial_data(user_id: str) -> Dict[str, Any]:
    """Busca dados financeiros do usuário com cache"""
    try:
        pluggy = PluggyConnector()
        
        # Buscar dados do usuário
        itemids_data = pluggy.load_itemids_db(user_id)
        if not itemids_data:
            return {"error": "Nenhuma conta conectada encontrada"}
        
        # Buscar dados dos últimos 4 meses
        df_extratos = pluggy.buscar_extratos(itemids_data, dias=120)
        df_cartoes = pluggy.buscar_cartoes(itemids_data, dias=120)
        
        # Análise básica
        analysis = {
            "total_transactions": len(df_extratos) + len(df_cartoes),
            "period_days": 120,
            "extratos": {
                "count": len(df_extratos),
                "receitas": df_extratos[df_extratos['Valor'] > 0]['Valor'].sum() if not df_extratos.empty else 0,
                "despesas": abs(df_extratos[df_extratos['Valor'] < 0]['Valor'].sum()) if not df_extratos.empty else 0
            },
            "cartoes": {
                "count": len(df_cartoes),
                "gastos": abs(df_cartoes[df_cartoes['Valor'] < 0]['Valor'].sum()) if not df_cartoes.empty else 0
            }
        }
        
        # Análise por categorias (se disponível)
        if not df_extratos.empty and 'Categoria' in df_extratos.columns:
            gastos_por_categoria = df_extratos[df_extratos['Valor'] < 0].groupby('Categoria')['Valor'].sum().abs().sort_values(ascending=False)
            analysis["categorias"] = gastos_por_categoria.to_dict()
        
        return analysis
        
    except Exception as e:
        logger.error(f"Erro ao buscar dados financeiros: {str(e)}")
        return {"error": f"Erro ao carregar dados: {str(e)}"}

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

    # Status da IA
    display_ai_status()

    # Seção principal
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📊 Análise Financeira Personalizada")
        
        if st.button("🔍 Analisar Minhas Finanças", type="primary"):
            with st.spinner("Analisando seus dados financeiros..."):
                try:
                    # Buscar dados do usuário logado
                    user_id = st.session_state.get('usuario', 'default')
                    financial_data = get_financial_data(user_id)
                    
                    analysis_result = financial_service.analyze_financial_data(financial_data)
                    
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
                    st.markdown(analysis_result)
                    
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
        
        # Campo de perguntas para a IA
        st.markdown("---")
        st.subheader("🤖 Pergunte à IA sobre suas finanças")
        user_question = st.text_input("Digite sua pergunta para a IA:", key="pergunta_ia")
        
        if st.button("Perguntar para a IA"):
            if user_question:
                with st.spinner("A IA está analisando sua pergunta e seu histórico financeiro..."):
                    try:
                        user_id = st.session_state.get('usuario', 'default')
                        financial_data = get_financial_data(user_id)
                        
                        # Inicializar IA antes de obter o client
                        if not ai_manager.initialize():
                            status = ai_manager.get_status()
                            raise RuntimeError(f"IA indisponível: {status['error']}")
                        
                        client = ai_manager.get_client()
                        if not client:
                            status = ai_manager.get_status()
                            raise RuntimeError(f"IA indisponível: {status['error']}")
                        
                        # Montar prompt combinando histórico e pergunta
                        prompt = f"""
Você é um assistente financeiro. Considere o seguinte histórico financeiro do usuário dos últimos 4 meses:

Dados Financeiros:
- Total de transações: {financial_data.get('total_transactions', 0)}
- Período analisado: {financial_data.get('period_days', 0)} dias
- Receitas: R$ {financial_data.get('extratos', {}).get('receitas', 0):.2f}
- Despesas: R$ {financial_data.get('extratos', {}).get('despesas', 0):.2f}
- Gastos no cartão: R$ {financial_data.get('cartoes', {}).get('gastos', 0):.2f}

Pergunta do usuário: {user_question}

Responda de forma personalizada, prática e clara, considerando o contexto financeiro apresentado."""
                        
                        resposta = client.invoke(prompt)
                        resposta_texto = resposta.content if hasattr(resposta, 'content') else str(resposta)
                        st.markdown(f"**Resposta da IA:**\n{resposta_texto}")
                        
                    except Exception as e:
                        st.error(f"❌ Erro ao processar pergunta: {str(e)}")
                        logger.error(f"Erro detalhado na pergunta IA: {str(e)}", exc_info=True)
            else:
                st.warning("Por favor, digite uma pergunta.")
    
    with col2:
        st.subheader("📚 Dicas Educativas")
        
        with st.expander("💰 Controle Financeiro Básico"):
            st.markdown("""
**🎯 Passos Essenciais:**
- ✅ Anote todos os gastos diários
- ✅ Crie um orçamento mensal realista  
- ✅ Separe necessidades de desejos
- ✅ Revise suas finanças semanalmente

**📊 Regra 50/30/20:**
- 50% para necessidades (moradia, alimentação)
- 30% para desejos (lazer, compras)
- 20% para poupança e investimentos
""")
        
        with st.expander("🛡️ Reserva de Emergência"):
            st.markdown("""
**🆘 Importância da Reserva:**
- Meta: 6-12 meses de gastos essenciais
- Mantenha em aplicações de liquidez imediata
- Use apenas para emergências reais
- Exemplo: perda de emprego, problemas de saúde

**💡 Como Construir:**
- Comece com R$ 50-100 por mês
- Aumente gradualmente o valor
- Use o 13º salário e bonificações
""")
        
        with st.expander("📈 Dicas de Investimento"):
            st.markdown("""
**🎯 Primeiros Passos:**
- Quite dívidas de juros altos primeiro
- Estude antes de investir
- Diversifique seus investimentos
- Tenha objetivos claros

**💰 Opções para Iniciantes:**
- Tesouro Direto (renda fixa)
- CDBs de bancos sólidos
- Fundos de investimento simples
""")
        
        with st.expander("🔍 Análise de Gastos"):
            st.markdown("""
**📊 Como Analisar:**
- Categorize todos os gastos
- Identifique gastos desnecessários
- Compare com meses anteriores
- Estabeleça metas de redução

**⚠️ Sinais de Alerta:**
- Gastos > 80% da renda
- Uso frequente do cartão de crédito
- Não conseguir poupar nada
""")

    # Rodapé
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 20px;'>
        💡 <strong>Richness</strong> - Sua jornada financeira com tecnologia de IA<br>
        🔒 Dados protegidos | 🤖 IA responsável | 📊 Análises precisas
    </div>
    """, unsafe_allow_html=True)

# Executar a aplicação
if __name__ == "__main__":
    main()
