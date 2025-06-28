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
Você é um assistente financeiro direto, objetivo e sem rodeios, com perfil militar.
Responda de forma curta, clara, prática, firme e bastante "dura", como um militar conversando com um recruta.
Use jargões militares, frases de impacto, gírias leves e nunca use frases de apoio, frases acolhedoras ou emojis amigáveis.
Não diga "estou aqui para ajudar", "espero que isso ajude" ou qualquer frase polida.
Seja prático, vá direto ao ponto e não enrole.
Exemplo de resposta: "“Gastou mais do que devia? Agora aguenta o tranco, recruta. Corta supérfluo, 
ajusta a rota e começa a registrar cada centavo. Sem mimimi. Dinheiro não aceita desaforo.”"
Outro exemplo: "“Tá no vermelho? Culpa sua. Falta de disciplina é o primeiro passo pro buraco. Prioriza dívida, elimina 
gasto inútil e aprende a dizer 'não'. Missão dada é missão cumprida. Sem desculpa, sem moleza.”"
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
        
        # Formatação específica para dados do cartão
        if 'total_gastos' in context:
            formatted_context.append(f"\n## Total de Gastos no Cartão: R$ {context['total_gastos']:,.2f}")
        
        if 'maior_gasto' in context and context['maior_gasto']:
            maior_gasto = context['maior_gasto']
            if isinstance(maior_gasto, dict):
                data = maior_gasto.get('data', 'N/A')
                if hasattr(data, 'strftime'):
                    data_fmt = data.strftime('%Y-%m-%d')
                else:
                    data_fmt = str(data)[:10] if len(str(data)) >= 10 else str(data)
                
                formatted_context.append(f"\n## Maior Gasto do Cartão")
                formatted_context.append(f"Data: {data_fmt}")
                formatted_context.append(f"Descrição: {maior_gasto.get('descricao', 'N/A')}")
                formatted_context.append(f"Valor: R$ {maior_gasto.get('valor', 0):,.2f}")
                formatted_context.append(f"Categoria: {maior_gasto.get('categoria', 'N/A')}")
        
        if 'categoria_predominante' in context and context['categoria_predominante']:
            formatted_context.append(f"\n## Categoria Predominante: {context['categoria_predominante']}")
        
        if 'gasto_medio' in context:
            formatted_context.append(f"\n## Gasto Médio do Cartão: R$ {context['gasto_medio']:,.2f}")
        
        if 'periodo_analise' in context:
            formatted_context.append(f"\n## Período de Análise: {context['periodo_analise']}")
        
        # Formatação das últimas transações
        if 'ultimas_transacoes' in context and context['ultimas_transacoes']:
            formatted_context.append("\n## Últimas Transações")
            for transacao in context['ultimas_transacoes'][:3]:  # Limitar a 3 transações
                data = transacao.get('data', 'N/A')
                valor = transacao.get('valor', 0)
                descricao = transacao.get('descricao', 'N/A')
                categoria = transacao.get('categoria', 'N/A')
                
                formatted_context.append(f"- {data}: {descricao} - R$ {valor:,.2f} ({categoria})")
        
        # Formatação das últimas transações do cartão (específico para insights do cartão)
        if 'ultimas_transacoes_cartao' in context and context['ultimas_transacoes_cartao']:
            formatted_context.append("\n## Últimas 30 Transações do Cartão de Crédito")
            for transacao in context['ultimas_transacoes_cartao']:
                # Adaptar para diferentes formatos de data
                data = transacao.get('data', 'N/A')
                if hasattr(data, 'strftime'):
                    data_fmt = data.strftime('%Y-%m-%d')
                elif isinstance(data, str):
                    data_fmt = data[:10] if len(data) >= 10 else data
                else:
                    data_fmt = str(data)[:10]
                
                valor = transacao.get('valor', 0)
                descricao = transacao.get('descricao', 'N/A')
                categoria = transacao.get('categoria', 'N/A')
                origem = transacao.get('origem', 'N/A')
                
                formatted_context.append(f"- {data_fmt}: {descricao} - R$ {valor:,.2f} ({categoria}) [{origem}]")
        
        # Formatação das transações detalhadas do período
        if 'todas_transacoes_periodo' in context and context['todas_transacoes_periodo']:
            formatted_context.append("\n## Transações do período selecionado (máx. 100 exibidas)")
            for t in context['todas_transacoes_periodo'][:100]:
                data_fmt = t['data'][:10] if isinstance(t['data'], str) else str(t['data'])[:10]
                formatted_context.append(f"- {data_fmt}: {t['descricao']} - R$ {t['valor']:.2f} ({t['categoria']})")
        
        # Formatação específica para insights de METAS E COMPROMISSOS
        if 'tipo_analise' in context:
            tipo_analise = context['tipo_analise']
            
            if tipo_analise in ['compromissos_metas', 'metas_economia', 'capacidade_pagamento', 'estrategia_financeira']:
                formatted_context.append("\n## DADOS DE METAS E COMPROMISSOS")
                
                # Informações básicas
                user_id = context.get('user_id', 'N/A')
                saldo_liquido = context.get('saldo_liquido', 0)
                formatted_context.append(f"Saldo líquido atual: R$ {saldo_liquido:,.2f}")
                
                # Compromissos pendentes
                if 'compromissos_count' in context:
                    count = context['compromissos_count']
                    total = context.get('compromissos_total', 0)
                    situacao = context.get('situacao', 'indefinida')
                    
                    formatted_context.append(f"\n### Compromissos Pendentes:")
                    formatted_context.append(f"- Quantidade: {count} compromissos")
                    formatted_context.append(f"- Valor total: R$ {total:,.2f}")
                    formatted_context.append(f"- Situação: {situacao}")
                    
                    if count > 0:
                        # Buscar detalhes dos compromissos do repositório
                        try:
                            from utils.database_manager_v2 import DatabaseManager
                            from utils.repositories_v2 import CompromissoRepository
                            
                            db = DatabaseManager()
                            compromisso_repo = CompromissoRepository(db)
                            df_compromissos = compromisso_repo.obter_compromissos(user_id, "pendente")
                            
                            if not df_compromissos.empty:
                                formatted_context.append("- Detalhes dos compromissos:")
                                for idx, row in df_compromissos.iterrows():
                                    desc = row.get('descricao', 'N/A')
                                    valor = row.get('valor', 0)
                                    categoria = row.get('categoria', 'N/A')
                                    data_venc = row.get('data_vencimento', 'N/A')
                                    formatted_context.append(f"  * {desc}: R$ {valor:,.2f} ({categoria}) - Vencimento: {data_venc}")
                        except Exception:
                            # Falhar silenciosamente se não conseguir buscar detalhes
                            formatted_context.append("- Detalhes específicos dos compromissos não disponíveis")
                    else:
                        formatted_context.append("- Nenhum compromisso pendente cadastrado")
                
                # Metas de economia
                if 'metas_count' in context:
                    count = context['metas_count']
                    total_valor = context.get('metas_total_valor', 0)
                    economia_mensal = context.get('economia_mensal_necessaria', 0)
                    viabilidade = context.get('viabilidade', 'indefinida')
                    
                    formatted_context.append(f"\n### Metas de Economia:")
                    formatted_context.append(f"- Quantidade: {count} metas ativas")
                    formatted_context.append(f"- Valor total das metas: R$ {total_valor:,.2f}")
                    formatted_context.append(f"- Economia mensal necessária: R$ {economia_mensal:,.2f}")
                    formatted_context.append(f"- Viabilidade: {viabilidade}")
                    
                    if count > 0:
                        # Buscar detalhes das metas do banco de dados
                        try:
                            from utils.repositories_v2 import MetaEconomiaRepository
                            
                            meta_repo = MetaEconomiaRepository(db)
                            df_metas = meta_repo.obter_metas_usuario(user_id, status='ativa')
                            
                            if not df_metas.empty:
                                formatted_context.append("- Detalhes das metas:")
                                for idx, meta in df_metas.iterrows():
                                    nome = meta.get('nome', 'Meta sem nome')
                                    valor_total_raw = meta.get('valor_total', 0)
                                    valor_mensal_raw = meta.get('valor_mensal', 0)
                                    valor_economizado_raw = meta.get('valor_economizado', 0)
                                    prazo_raw = meta.get('prazo_meses', 0)
                                    
                                    valor_total = float(valor_total_raw) if valor_total_raw is not None else 0.0
                                    valor_mensal = float(valor_mensal_raw) if valor_mensal_raw is not None else 0.0
                                    valor_economizado = float(valor_economizado_raw) if valor_economizado_raw is not None else 0.0
                                    prazo = int(prazo_raw) if prazo_raw is not None else 0
                                    progresso = (valor_economizado / valor_total * 100) if valor_total > 0 else 0
                                    
                                    formatted_context.append(f"  * {nome}: R$ {valor_total:,.2f} (economia mensal: R$ {valor_mensal:,.2f})")
                                    formatted_context.append(f"    - Prazo: {prazo} meses | Progresso: {progresso:.1f}% (R$ {valor_economizado:,.2f} economizado)")
                        except Exception:
                            # Falhar silenciosamente se não conseguir buscar detalhes
                            formatted_context.append("- Detalhes específicos das metas não disponíveis")
                    else:
                        formatted_context.append("- Nenhuma meta de economia cadastrada")
                
                # Capacidade de pagamento e saldo disponível
                if 'saldo_disponivel' in context:
                    saldo_disponivel = context['saldo_disponivel']
                    capacidade = context.get('capacidade', 'indefinida')
                    total_economia_mensal = context.get('total_economia_mensal', 0)
                    
                    formatted_context.append(f"\n### Capacidade Financeira:")
                    formatted_context.append(f"- Saldo disponível: R$ {saldo_disponivel:,.2f}")
                    formatted_context.append(f"- Capacidade: {capacidade}")
                    formatted_context.append(f"- Compromisso de economia mensal: R$ {total_economia_mensal:,.2f}")
                
                # Análise estratégica
                if 'tem_compromissos' in context:
                    tem_compromissos = context['tem_compromissos']
                    tem_metas = context.get('tem_metas', False)
                    saldo_positivo = context.get('saldo_positivo', False)
                    economia_viavel = context.get('economia_viavel', False)
                    equilibrio = context.get('equilibrio_financeiro', 'indefinido')
                    
                    formatted_context.append(f"\n### Situação Estratégica:")
                    formatted_context.append(f"- Possui compromissos: {'Sim' if tem_compromissos else 'Não'}")
                    formatted_context.append(f"- Possui metas: {'Sim' if tem_metas else 'Não'}")
                    formatted_context.append(f"- Saldo positivo: {'Sim' if saldo_positivo else 'Não'}")
                    formatted_context.append(f"- Economia viável: {'Sim' if economia_viavel else 'Não'}")
                    formatted_context.append(f"- Equilíbrio financeiro: {equilibrio}")
        
        return "\n".join(formatted_context)
