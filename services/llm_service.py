"""
Serviço para integração com modelos de linguagem natural (LLM)
Permite interação com OpenAI GPT para respostas inteligentes
"""

import os
import json
from typing import Dict, List, Any, Optional
import requests
from datetime import datetime
import streamlit as st

from utils.environment_config import EnvironmentConfig
from utils.exception_handler import ExceptionHandler


class LLMService:
    """Serviço de integração com modelos de linguagem (LLM)"""
    
    def __init__(self):
        """Inicializa o serviço de LLM"""
        self.env_config = EnvironmentConfig()
        self.api_key = self.env_config.get_openai_api_key()
        
        # Modelo padrão (pode ser ajustado conforme necessidade)
        self.model = "gpt-4o"
        self.api_url = "https://api.openai.com/v1/chat/completions"
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY não encontrada")
    
    def generate_response(self, user_query: str, context: Dict[str, Any]) -> dict:
        """
        Gera uma resposta utilizando o LLM baseado na consulta do usuário e no contexto financeiro
        Agora adapta o prompt do sistema conforme a personalidade selecionada.
        Retorna também o valor da personalidade, o prompt realmente utilizado, o contexto formatado e o payload para debug.
        
        Args:
            user_query: Pergunta ou mensagem do usuário
            context: Contexto financeiro do usuário
            
        Returns:
            Dicionário com a resposta, valor da personalidade, prompt realmente utilizado, contexto formatado e payload para debug
        """
        try:
            if not self.api_key:
                return {"response": "❌ API Key não configurada. Configure a chave da OpenAI para utilizar o assistente.", "personalidade": None, "prompt": None}
                
            # Formatação do contexto financeiro para o prompt
            context_str = self._format_context_for_prompt(context)

            # Definir prompts de sistema para cada personalidade
            personality_prompts = {
                "clara": '''\
Você é um assistente financeiro inteligente que ajuda pessoas a gerenciar suas finanças pessoais.
Seu tom é amigável, acolhedor e descontraído.
Explique conceitos de forma simples e incentive o usuário. Use exemplos práticos quando possível.
Baseie suas respostas nos dados financeiros fornecidos no contexto. Não invente informações que não estejam presentes.
Se não tiver informações suficientes para responder uma pergunta específica, seja honesto sobre essa limitação.
Use formatação Markdown para tornar suas respostas mais organizadas e fáceis de ler.
''',
                "tecnica": '''\
Você é um assistente financeiro altamente técnico e formal, especializado em finanças pessoais.
Utilize linguagem precisa, termos técnicos e explique conceitos financeiros de forma detalhada e objetiva.
Mantenha um tom profissional. Baseie suas respostas estritamente nos dados fornecidos.
Se não houver dados suficientes, informe de maneira clara e objetiva.
Use formatação Markdown para estruturar suas respostas.
''',
                "durona": '''\
Você é um assistente financeiro direto, objetivo e sem rodeios, com um toque de informalidade.
Responda de forma curta, clara, prática e até um pouco "durona", como um coach que não passa a mão na cabeça.
Use frases de impacto, gírias leves e nunca use frases de apoio, frases acolhedoras ou emojis amigáveis.
Não diga "estou aqui para ajudar", "espero que isso ajude" ou qualquer frase polida.
Seja prático, vá direto ao ponto e não enrole.
Exemplo de resposta: "Seu saldo está ok, mas se não controlar os gastos, vai ficar no vermelho. Fique esperto."
Outro exemplo: "Gasto alto com taxas. Corta isso se quiser sobrar dinheiro."
Baseie suas respostas nos dados do contexto e incentive o usuário a agir sem rodeios.
Se não houver dados suficientes, diga isso de forma direta.
Use Markdown para organizar as respostas.
'''
            }
            # Selecionar personalidade
            personalidade = context.get('personalidade', 'clara')
            system_prompt = personality_prompts.get(personalidade, personality_prompts['clara'])

            # Se houver prompt_customizado ou parametros_personalidade, sobrescreva ou complemente o prompt
            prompt_customizado = context.get('prompt_customizado')
            parametros_personalidade = context.get('parametros_personalidade')
            if prompt_customizado or parametros_personalidade:
                # Montar instrução explícita
                if prompt_customizado:
                    custom = prompt_customizado
                else:
                    custom = ''
                    if parametros_personalidade:
                        custom = f"Formalidade: {parametros_personalidade.get('formalidade', '')} | Emojis: {parametros_personalidade.get('emojis', '')} | Tom: {parametros_personalidade.get('tom', '')} | Foco: {parametros_personalidade.get('foco', '')}"
                system_prompt = f"{system_prompt}\n\nConsidere as seguintes características de personalidade ao responder:\n{custom}"

            # Montagem dos messages para a API
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Dados financeiros para contexto:\n{context_str}\n\nPergunta do usuário: {user_query}"}
            ]
            
            # Parâmetros da chamada
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1000
            }
            
            # Chamada à API
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                error_message = f"Erro ao chamar a API: {response.status_code} - {response.text}"
                raise Exception(error_message)
            
            # Processamento da resposta
            response_data = response.json()
            ai_response = response_data["choices"][0]["message"]["content"]
            
            return {
                "response": ai_response,
                "personalidade": personalidade,
                "prompt": system_prompt
            }
            
        except Exception as e:
            # Usa o handler de exceções para formatar erros da OpenAI
            return {"response": ExceptionHandler.handle_openai_error(e), "personalidade": None, "prompt": None}
    
    def _format_context_for_prompt(self, context: Dict[str, Any]) -> str:
        """
        Formata o contexto financeiro para o prompt do LLM
        
        Args:
            context: Contexto financeiro do usuário
            
        Returns:
            String formatada com as informações do contexto
        """
        formatted_context = []
        
        # Formatação dos dados do usuário
        if 'usuario' in context:
            usuario = context['usuario']
            formatted_context.append("## Dados do Usuário")
            formatted_context.append(f"Nome: {usuario.get('nome', 'N/A')}")
            formatted_context.append(f"Username: {usuario.get('username', 'N/A')}")
        
        # Formatação do saldo
        if 'saldo' in context:
            saldo = context['saldo']
            formatted_context.append("\n## Saldo e Situação Financeira")
            formatted_context.append(f"Saldo atual: R$ {saldo.get('valor_restante', 0):,.2f}")
            formatted_context.append(f"Total de receitas: R$ {saldo.get('total_receitas', 0):,.2f}")
            formatted_context.append(f"Total de gastos: R$ {saldo.get('total_gastos', 0):,.2f}")
            formatted_context.append(f"Percentual gasto: {saldo.get('percentual_gasto', 0):.1f}%")
            formatted_context.append(f"Dias restantes no mês: {saldo.get('dias_restantes', 0)}")
            formatted_context.append(f"Status: {saldo.get('status', 'N/A')}")
        
        # Formatação das categorias de gastos
        if 'categorias' in context:
            formatted_context.append("\n## Categorias de Gastos")
            categorias = []
            
            for categoria, dados in context['categorias'].items():
                if 'sum' in dados and 'percentual' in dados:
                    valor = float(dados['sum'])
                    percentual = float(dados['percentual'])
                    categorias.append((categoria, valor, percentual))
            
            # Ordenar por valor
            categorias.sort(key=lambda x: x[1], reverse=True)
            
            for categoria, valor, percentual in categorias[:5]:  # Top 5 categorias
                formatted_context.append(f"{categoria}: R$ {abs(valor):,.2f} ({percentual:.1f}%)")
        
        # Formatação dos alertas
        if 'alertas' in context and context['alertas']:
            formatted_context.append("\n## Alertas Financeiros")
            for alerta in context['alertas']:
                if isinstance(alerta, dict) and 'mensagem' in alerta:
                    formatted_context.append(f"- {alerta['mensagem']}")
                else:
                    formatted_context.append(f"- {alerta}")
        
        # Formatação das últimas transações
        if 'ultimas_transacoes' in context and context['ultimas_transacoes']:
            formatted_context.append("\n## Últimas Transações")
            for transacao in context['ultimas_transacoes'][:3]:  # Limitar a 3 transações
                data = transacao.get('data', 'N/A')
                valor = transacao.get('valor', 0)
                descricao = transacao.get('descricao', 'N/A')
                categoria = transacao.get('categoria', 'N/A')
                
                formatted_context.append(f"- {data}: {descricao} - R$ {valor:,.2f} ({categoria})")
        
        # Formatação das transações detalhadas do período
        if 'todas_transacoes_periodo' in context and context['todas_transacoes_periodo']:
            formatted_context.append("\n## Transações do período selecionado (máx. 100 exibidas)")
            for t in context['todas_transacoes_periodo'][:100]:
                data_fmt = t['data'][:10] if isinstance(t['data'], str) else str(t['data'])[:10]
                formatted_context.append(f"- {data_fmt}: {t['descricao']} - R$ {t['valor']:.2f} ({t['categoria']})")
        
        return "\n".join(formatted_context)
