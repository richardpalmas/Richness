"""
Serviço de Assistente Virtual Financeiro com IA
Sistema conversacional que responde perguntas financeiras baseado em dados do usuário
"""

from typing import Dict, List, Optional, Any
import re
from datetime import datetime, date
import json

from utils.database_manager_v2 import DatabaseManager
from utils.repositories_v2 import TransacaoRepository, UsuarioRepository
from services.insights_service_v2 import InsightsServiceV2


class FinancialAIAssistant:
    """Assistente virtual financeiro com capacidades de IA"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.transacao_repo = TransacaoRepository(self.db)
        self.usuario_repo = UsuarioRepository(self.db)
        self.insights_service = InsightsServiceV2()
        
        # Padrões de intenção para análise de texto
        self.intent_patterns = {
            'saldo': [
                r'qual.*saldo', r'quanto.*tenho', r'saldo.*atual',
                r'quanto.*dinheiro', r'valor.*disponível'
            ],
            'gastos': [
                r'quanto.*gastei', r'gastos.*em', r'despesas.*de',
                r'onde.*gastei', r'categorias.*gasto'
            ],
            'receitas': [
                r'quanto.*recebi', r'receitas.*em', r'ganhos.*de',
                r'entrada.*dinheiro', r'renda.*mensal'
            ],
            'economia': [
                r'como.*economizar', r'dicas.*economia', r'poupar.*dinheiro',
                r'reduzir.*gastos', r'otimizar.*gastos'
            ],
            'meta': [
                r'meta.*financeira', r'objetivo.*economia', r'plano.*poupança',
                r'quanto.*poupar', r'guardar.*dinheiro'
            ],
            'categoria': [
                r'gastos.*categoria', r'categoria.*mais', r'onde.*gasto.*mais',
                r'análise.*categoria', r'despesas.*por.*categoria'
            ],
            'periodo': [
                r'mês.*passado', r'último.*mês', r'período.*de',
                r'semana.*passada', r'ano.*passado'
            ]
        }
    
    def analyze_intent(self, message: str) -> Dict[str, Any]:
        """Analisa a intenção da mensagem do usuário"""
        message_lower = message.lower()
        
        # Detectar intenções principais
        detected_intents = []
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    detected_intents.append(intent)
                    break
        
        # Extrair informações específicas
        context = {
            'intents': detected_intents,
            'categories': self._extract_categories(message_lower),
            'time_period': self._extract_time_period(message_lower),
            'values': self._extract_values(message_lower)
        }
        
        return context
    
    def _extract_categories(self, message: str) -> List[str]:
        """Extrai categorias mencionadas na mensagem"""
        categories = []
        common_categories = [
            'alimentação', 'transporte', 'saúde', 'lazer', 'educação',
            'casa', 'vestuário', 'tecnologia', 'investimento', 'outros'
        ]
        
        for category in common_categories:
            if category in message:
                categories.append(category.title())
        
        return categories
    
    def _extract_time_period(self, message: str) -> Optional[str]:
        """Extrai período temporal da mensagem"""
        if re.search(r'mês.*passado|último.*mês', message):
            return 'last_month'
        elif re.search(r'semana.*passada|última.*semana', message):
            return 'last_week'
        elif re.search(r'ano.*passado|último.*ano', message):
            return 'last_year'
        elif re.search(r'hoje|hoje', message):
            return 'today'
        elif re.search(r'ontem', message):
            return 'yesterday'
        
        return None
    
    def _extract_values(self, message: str) -> List[float]:
        """Extrai valores monetários da mensagem"""
        # Buscar padrões como R$ 100, 50 reais, etc.
        value_patterns = [
            r'r\$\s*(\d+(?:[.,]\d+)?)',
            r'(\d+(?:[.,]\d+)?)\s*reais',
            r'(\d+(?:[.,]\d+)?)\s*r\$'
        ]
        
        values = []
        for pattern in value_patterns:
            matches = re.findall(pattern, message)
            for match in matches:
                try:
                    value = float(match.replace(',', '.'))
                    values.append(value)
                except ValueError:
                    continue
        
        return values
    
    def process_message(self, user_id: int, message: str) -> Dict[str, Any]:
        """Processa mensagem do usuário e gera resposta inteligente"""
        
        # Analisar intenção
        context = self.analyze_intent(message)
        
        # Gerar resposta baseada na intenção
        response = self._generate_response(user_id, context, message)
        
        return {
            'response': response,
            'context': context,
            'timestamp': datetime.now().isoformat()
        }
    
    def process_message_with_personality(self, user_id: int, message: str, personalidade: str = "clara") -> Dict[str, Any]:
        """Processa mensagem do usuário considerando a personalidade selecionada"""
        
        # Analisar intenção
        context = self.analyze_intent(message)
        
        # Gerar resposta baseada na intenção e personalidade
        response = self._generate_response_with_personality(user_id, context, message, personalidade)
        
        return {
            'response': response,
            'context': context,
            'personalidade': personalidade,
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_personality_config(self, personalidade: str) -> Dict[str, str]:
        """Obtém configurações de personalidade"""
        personalidade_configs = {
            "clara": {
                "estilo": "acolhedora, clara e engraçada",
                "tom": "amigável e descontraída",
                "emojis": True,
                "prefixo": "😊",
                "sufixo": " 💫"
            },
            "tecnica": {
                "estilo": "técnica e formal",
                "tom": "profissional e objetiva",
                "emojis": False,
                "prefixo": "📊",
                "sufixo": ""
            },
            "durona": {
                "estilo": "durona e informal",
                "tom": "direta e sem rodeios",
                "emojis": True,
                "prefixo": "💪",
                "sufixo": " 🎯"
            }
        }
        
        return personalidade_configs.get(personalidade, personalidade_configs["clara"])
    
    def _apply_personality_style(self, message: str, personalidade: str) -> str:
        """Aplica estilo da personalidade à mensagem"""
        config = self._get_personality_config(personalidade)
        
        if personalidade == "clara":
            # Estilo amigável com emojis e tom motivador
            if "saldo" in message.lower() and "positivo" in message.lower():
                message = message.replace("✅", "🎉").replace("Continue assim", "Você está arrasando! Continue assim")
            elif "vermelho" in message.lower():
                message = message.replace("⚠️", "🚨").replace("Atenção!", "Ops! Vamos dar uma olhada nisso")
                
        elif personalidade == "tecnica":
            # Remover emojis excessivos e usar linguagem técnica
            message = re.sub(r'[😊🎉💰✅⚠️🚨💪🎯]', '', message)
            message = message.replace("Você está arrasando", "Performance financeira positiva")
            message = message.replace("no vermelho", "em déficit orçamentário")
            
        elif personalidade == "durona":
            # Tom mais direto e informal
            message = message.replace("Considere revisar", "Precisa revisar urgente")
            message = message.replace("Recomendo", "Você tem que")
            message = message.replace("seria interessante", "é obrigatório")
        
        # Adicionar prefixo e sufixo da personalidade
        if config["emojis"]:
            return f"{config['prefixo']} {message}{config['sufixo']}"
        else:
            return message
    
    def _generate_response_with_personality(self, user_id: int, context: Dict[str, Any], original_message: str, personalidade: str) -> str:
        """Gera resposta inteligente baseada no contexto e personalidade"""
        
        # Gerar resposta base
        base_response = self._generate_response(user_id, context, original_message)
        
        # Aplicar estilo da personalidade
        styled_response = self._apply_personality_style(base_response, personalidade)
        
        return styled_response
    
    def _generate_response(self, user_id: int, context: Dict[str, Any], original_message: str) -> str:
        """Gera resposta inteligente baseada no contexto"""
        
        intents = context.get('intents', [])
        
        if not intents:
            return self._get_generic_help_response()
        
        # Priorizar intenção principal
        primary_intent = intents[0]
        
        try:
            if primary_intent == 'saldo':
                return self._handle_saldo_intent(user_id)
            elif primary_intent == 'gastos':
                return self._handle_gastos_intent(user_id, context)
            elif primary_intent == 'receitas':
                return self._handle_receitas_intent(user_id, context)
            elif primary_intent == 'economia':
                return self._handle_economia_intent(user_id)
            elif primary_intent == 'categoria':
                return self._handle_categoria_intent(user_id, context)
            elif primary_intent == 'meta':
                return self._handle_meta_intent(user_id)
            else:
                return self._get_generic_response(user_id)
                
        except Exception as e:
            return f"❌ Ops! Encontrei um problema ao analisar seus dados: {str(e)}"
    
    def _handle_saldo_intent(self, user_id: int) -> str:
        """Responde perguntas sobre saldo"""
        try:
            saldo_info = self.insights_service.obter_valor_restante_mensal(user_id)
            
            if saldo_info:
                saldo = saldo_info.get('valor_restante', 0)
                response = f"💰 **Seu saldo atual:** R$ {saldo:,.2f}\n\n"
                
                if saldo > 0:
                    response += "✅ Você está no azul! Continue assim para manter suas finanças saudáveis."
                elif saldo < 0:
                    response += f"⚠️ Atenção! Você está R$ {abs(saldo):,.2f} no vermelho. Considere revisar seus gastos."
                else:
                    response += "⚖️ Suas receitas e despesas estão equilibradas."
                    
                return response
            else:
                return "📊 Não consegui calcular seu saldo atual. Verifique se você tem transações registradas."
                
        except Exception as e:
            return f"❌ Erro ao consultar saldo: {str(e)}"
    
    def _handle_gastos_intent(self, user_id: int, context: Dict[str, Any]) -> str:
        """Responde perguntas sobre gastos"""
        try:
            # Analisar gastos por categoria
            analise_gastos = self.insights_service.analisar_gastos_por_categoria(user_id)
            
            if not isinstance(analise_gastos, dict) or analise_gastos.get('status') != 'ok':
                return "📊 Não encontrei dados de gastos para analisar."
            
            response = "💸 **Análise dos seus gastos:**\n\n"
            
            try:
                gastos_por_categoria = {}
                for categoria, dados in analise_gastos.get('resumo_categorias', {}).items():
                    if isinstance(dados, dict) and 'sum' in dados:
                        valor = dados['sum']
                        # Garantir que o valor é numérico
                        if isinstance(valor, (int, float)):
                            gastos_por_categoria[categoria] = float(valor)
                
                if not gastos_por_categoria:
                    return "📊 Não encontrei dados de gastos para analisar."
                
                # Ordenar categorias por valor usando comparação segura
                top_categorias = sorted(gastos_por_categoria.items(), key=lambda x: float(x[1]), reverse=True)[:3]
                
                for i, (categoria, valor) in enumerate(top_categorias, 1):
                    response += f"{i}. **{categoria}**: R$ {abs(float(valor)):,.2f}\n"
            except Exception as e:
                return f"😊 ❌ Erro ao analisar categorias: Formato de dados inválido - {str(e)} 💫"
            
            # Categoria específica se mencionada
            categorias_mencionadas = context.get('categories', [])
            if categorias_mencionadas and gastos_por_categoria:
                for cat in categorias_mencionadas:
                    # Procurar a categoria ignorando maiúsculas/minúsculas
                    cat_lower = cat.lower()
                    for categoria_existente, valor in gastos_por_categoria.items():
                        if cat_lower in categoria_existente.lower():
                            response += f"\n🎯 **{categoria_existente}**: R$ {abs(float(valor)):,.2f}"
                            break
            
            return response
            
        except Exception as e:
            return f"❌ Erro ao analisar gastos: {str(e)}"
    
    def _handle_receitas_intent(self, user_id: int, context: Dict[str, Any]) -> str:
        """Responde perguntas sobre receitas"""
        try:
            # Obter dados de receitas através do username
            user_data = self.usuario_repo.obter_usuario_por_id(user_id)
            if not user_data:
                return "❌ Usuário não encontrado."
            
            username = user_data.get('username', '')
            
            # Usar TransacaoService para obter dados
            from services.transacao_service_v2 import TransacaoService
            transacao_service = TransacaoService()
            df_transacoes = transacao_service.listar_transacoes_usuario(username)
            
            if df_transacoes.empty:
                return "📊 Não encontrei dados de receitas para analisar."
              # Filtrar receitas (valores positivos)
            receitas = df_transacoes.loc[df_transacoes['valor'] > 0]
            
            if receitas.empty:
                return "💰 Nenhuma receita encontrada no período analisado."
            
            total_receitas = receitas['valor'].sum()
            qtd_receitas = len(receitas)
            media_receitas = total_receitas / qtd_receitas if qtd_receitas > 0 else 0
            
            response = f"💰 **Análise das suas receitas:**\n\n"
            response += f"📈 **Total**: R$ {total_receitas:,.2f}\n"
            response += f"📊 **Quantidade**: {qtd_receitas} receitas\n"
            response += f"🎯 **Média**: R$ {media_receitas:,.2f} por receita"
            
            return response
            
        except Exception as e:
            return f"❌ Erro ao analisar receitas: {str(e)}"
    
    def _handle_economia_intent(self, user_id: int) -> str:
        """Responde perguntas sobre economia e otimização"""
        try:
            sugestoes = self.insights_service.sugerir_otimizacoes(user_id)
            
            if not sugestoes:
                return "💡 Suas finanças parecem estar bem organizadas! Continue assim."
            
            response = "💡 **Dicas personalizadas para economizar:**\n\n"
            
            for i, sugestao in enumerate(sugestoes[:5], 1):  # Top 5 sugestões
                response += f"{i}. {sugestao}\n"
            
            response += "\n✨ **Dica extra**: Revise seus gastos mensalmente para identificar oportunidades de economia!"
            
            return response
            
        except Exception as e:
            return f"❌ Erro ao gerar dicas de economia: {str(e)}"
    
    def _handle_categoria_intent(self, user_id: int, context: Dict[str, Any]) -> str:
        """Responde perguntas sobre análise por categoria"""
        try:
            analise_gastos = self.insights_service.analisar_gastos_por_categoria(user_id)
            
            if not isinstance(analise_gastos, dict) or analise_gastos.get('status') != 'ok':
                return "📊 Não encontrei dados de categorias para analisar."
            
            try:
                # Extrair categorias e valores do formato correto
                gastos_por_categoria = {}
                for categoria, dados in analise_gastos.get('resumo_categorias', {}).items():
                    if isinstance(dados, dict) and 'sum' in dados:
                        valor = dados['sum']
                        # Garantir que o valor é numérico
                        if isinstance(valor, (int, float)):
                            gastos_por_categoria[categoria] = float(abs(valor))
                
                if not gastos_por_categoria:
                    return "📊 Não encontrei dados de categorias para analisar."
                
                # Encontrar categoria que mais gasta usando chave de comparação segura
                categoria_maior = max(gastos_por_categoria.items(), key=lambda x: float(x[1]))
                
                total_gastos = sum(float(valor) for valor in gastos_por_categoria.values())
                
                response = f"📊 **Análise por categoria:**\n\n"
                response += f"🏆 **Categoria com maior gasto:** {categoria_maior[0]}\n"
                response += f"💰 **Valor:** R$ {float(categoria_maior[1]):,.2f}\n\n"
                
                response += "**Distribuição completa:**\n"
                for categoria, valor in sorted(gastos_por_categoria.items(), key=lambda x: float(x[1]), reverse=True):
                    if total_gastos > 0:
                        porcentagem = (float(valor) / total_gastos) * 100
                        response += f"• {categoria}: R$ {float(valor):,.2f} ({porcentagem:.1f}%)\n"
                    else:
                        response += f"• {categoria}: R$ {float(valor):,.2f}\n"
                
                return response
                
            except Exception as e:
                return f"❌ Erro ao processar dados das categorias: {str(e)}"
        
        except Exception as e:
            return f"❌ Erro ao analisar categorias: {str(e)}"
    
    def _handle_meta_intent(self, user_id: int) -> str:
        """Responde perguntas sobre metas financeiras"""
        try:
            valor_restante = self.insights_service.obter_valor_restante_mensal(user_id)
            
            response = "🎯 **Planejamento de metas financeiras:**\n\n"
            
            if valor_restante and valor_restante.get('valor_restante', 0) > 0:
                valor_disponivel = valor_restante['valor_restante']
                response += f"💰 **Valor disponível para poupança:** R$ {valor_disponivel:,.2f}\n\n"
                response += "**Sugestões de metas:**\n"
                response += f"• Reserva de emergência: R$ {valor_disponivel * 0.3:,.2f} (30%)\n"
                response += f"• Investimentos: R$ {valor_disponivel * 0.5:,.2f} (50%)\n"
                response += f"• Lazer/extras: R$ {valor_disponivel * 0.2:,.2f} (20%)\n"
            else:
                response += "⚠️ **Primeiro, equilibre suas finanças!**\n"
                response += "Para criar metas, você precisa ter sobra mensal. Considere:\n"
                response += "• Reduzir gastos desnecessários\n"
                response += "• Aumentar sua renda\n"
                response += "• Revisar suas prioridades financeiras"
            
            return response
            
        except Exception as e:
            return f"❌ Erro ao sugerir metas: {str(e)}"
    
    def _get_generic_response(self, user_id: int) -> str:
        """Resposta genérica com insights rápidos"""
        try:
            # Obter alguns insights básicos
            alertas = self.insights_service.detectar_alertas_financeiros(user_id)
            
            response = "🤖 **Olá! Sou seu assistente financeiro.**\n\n"
            
            if alertas:
                response += "⚠️ **Alertas importantes:**\n"
                for alerta in alertas[:3]:  # Top 3 alertas
                    response += f"• {alerta}\n"
            else:
                response += "✅ **Tudo parece estar bem com suas finanças!**\n"
            
            response += "\n💡 **Posso te ajudar com:**\n"
            response += "• Análise de saldo e gastos\n"
            response += "• Dicas de economia personalizadas\n"
            response += "• Planejamento de metas financeiras\n"
            response += "• Insights sobre suas categorias de gasto"
            
            return response
            
        except Exception as e:
            return self._get_generic_help_response()
    
    def _get_generic_help_response(self) -> str:
        """Resposta de ajuda padrão"""
        return """🤖 **Olá! Sou seu assistente financeiro pessoal.**

💬 **Pergunte-me sobre:**
• "Qual meu saldo atual?"
• "Quanto gastei em alimentação?"
• "Como posso economizar?"
• "Onde gasto mais dinheiro?"
• "Quais são minhas receitas?"
• "Como criar uma meta de poupança?"

🎯 **Estou aqui para te ajudar a ter controle total das suas finanças!**"""

    def get_quick_insights(self, user_id: int) -> Dict[str, Any]:
        """Retorna insights rápidos para exibição na interface"""
        try:
            insights = {}
            
            # Debug: Verificar se user_id é válido
            if not user_id or user_id <= 0:
                return {'erro': f"User ID inválido: {user_id}"}
              # Valor restante do mês
            try:
                valor_restante = self.insights_service.obter_valor_restante_mensal(user_id)
                if valor_restante and valor_restante.get('valor_restante') is not None:
                    insights['saldo_mensal'] = valor_restante.get('valor_restante', 0)
            except Exception as e:
                insights['erro_saldo'] = str(e)
              
            # Alertas financeiros
            try:
                alertas_data = self.insights_service.detectar_alertas_financeiros(user_id)
                if alertas_data:
                    # Converter alertas para strings simples
                    alertas_texto = []
                    for alerta in alertas_data:
                        if isinstance(alerta, dict):
                            alertas_texto.append(alerta.get('mensagem', str(alerta)))
                        else:
                            alertas_texto.append(str(alerta))
                    insights['alertas'] = alertas_texto[:3]
                else:
                    insights['alertas'] = []
            except Exception as e:
                insights['erro_alertas'] = str(e)
                
            # Top categoria de gasto
            try:
                gastos_data = self.insights_service.analisar_gastos_por_categoria(user_id)
                if gastos_data and gastos_data.get('status') == 'ok':
                    resumo_categorias = gastos_data.get('resumo_categorias', {})
                    if resumo_categorias:
                        # Encontrar categoria com maior soma usando comparação segura
                        categorias_validas = {}
                        for categoria, dados in resumo_categorias.items():
                            if isinstance(dados, dict) and 'sum' in dados:
                                valor = dados['sum']
                                if isinstance(valor, (int, float)):
                                    categorias_validas[categoria] = float(valor)
                        
                        if categorias_validas:
                            top_categoria_nome = max(categorias_validas.keys(), 
                                                   key=lambda x: categorias_validas[x])
                            top_categoria_valor = categorias_validas[top_categoria_nome]
                            
                            insights['top_categoria'] = {
                                'nome': top_categoria_nome,
                                'valor': top_categoria_valor
                            }
            except Exception as e:
                insights['erro_categoria'] = str(e)
            
            # Sugestões de otimização
            try:
                sugestoes = self.insights_service.sugerir_otimizacoes(user_id)
                insights['sugestoes'] = sugestoes[:2] if sugestoes else []
            except Exception as e:
                insights['erro_sugestoes'] = str(e)
            
            return insights
            
        except Exception as e:
            return {'erro': f"Erro ao obter insights: {str(e)}"}

    def get_conversation_starters(self) -> List[str]:
        """Retorna sugestões de perguntas para iniciar conversa"""
        return [
            "💰 Qual meu saldo atual?",
            "📊 Onde estou gastando mais dinheiro?",
            "💡 Como posso economizar este mês?",
            "🎯 Quanto posso poupar mensalmente?",
            "📈 Como estão minhas receitas?",
            "⚠️ Há algo que devo me preocupar?"
        ]
