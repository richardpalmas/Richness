"""
Classe centralizada para tratamento de exceções da aplicação Richness.
Segue os princípios de Clean Code e DRY (Don't Repeat Yourself).
"""
import streamlit as st
from typing import Optional, Callable, Any
import functools


class ExceptionHandler:
    """
    Classe centralizada para tratamento de exceções da aplicação.
    Fornece métodos padronizados para diferentes tipos de erros.
    """
    
    @staticmethod
    def handle_openai_error(error: Exception) -> str:
        """
        Trata erros específicos da OpenAI API de forma padronizada.
        
        Args:
            error: Exceção capturada
            
        Returns:
            Mensagem de erro formatada para o usuário
        """
        error_msg = str(error)
        
        # Erros de API Key
        if "401" in error_msg or "invalid_api_key" in error_msg or "Incorrect API key" in error_msg:
            return (
                "❌ **API Key do OpenAI inválida ou expirada**\n\n"
                "💡 **Solução**:\n"
                "1. Acesse https://platform.openai.com/account/api-keys\n"
                "2. Gere uma nova API key\n"
                "3. Atualize o arquivo .env com a nova chave\n"
                "4. Reinicie a aplicação"
            )
        
        # Erros de cota/limite
        elif "quota" in error_msg.lower() or "rate_limit" in error_msg or "429" in error_msg:
            return (
                "❌ **Limite de uso da API OpenAI atingido**\n\n"
                "💡 **Solução**:\n"
                "1. Aguarde alguns minutos antes de tentar novamente\n"
                "2. Verifique seu plano no OpenAI\n"
                "3. Considere upgradar sua conta se necessário"
            )
        
        # Erros de configuração
        elif "OPENAI_API_KEY não encontrada" in error_msg:
            return (
                "❌ **Configuração da API OpenAI não encontrada**\n\n"
                "💡 **Solução**:\n"
                "1. Crie um arquivo .env na raiz do projeto\n"
                "2. Adicione: OPENAI_API_KEY=sua_chave_aqui\n"
                "3. Reinicie a aplicação"
            )
        
        # Erros de formato de API Key
        elif "parece inválida" in error_msg:
            return (
                "❌ **Formato da API Key incorreto**\n\n"
                "💡 **Solução**:\n"
                "1. Verifique se a chave começa com 'sk-'\n"
                "2. Confirme que não há espaços extras\n"
                "3. Gere uma nova chave se necessário"
            )
        
        # Erro genérico da OpenAI
        else:
            return f"❌ **Erro da IA**: {error_msg}\n\n💡 Tente novamente em alguns instantes."
    
    @staticmethod
    def handle_pluggy_error(error: Exception) -> str:
        """
        Trata erros específicos da API Pluggy de forma padronizada.
        
        Args:
            error: Exceção capturada
            
        Returns:
            Mensagem de erro formatada para o usuário
        """
        error_msg = str(error)
        
        if "403" in error_msg or "Forbidden" in error_msg:
            return (
                "❌ **Acesso negado à API Pluggy**\n\n"
                "💡 **Solução**:\n"
                "1. Verifique suas credenciais\n"
                "2. Confirme se o item ID é válido\n"
                "3. Tente reconectar sua conta bancária"
            )
        
        elif "401" in error_msg or "Unauthorized" in error_msg:
            return (
                "❌ **Credenciais Pluggy inválidas**\n\n"
                "💡 **Solução**:\n"
                "1. Verifique as credenciais no arquivo .env\n"
                "2. Reautentique com a API Pluggy"
            )
        
        elif "429" in error_msg or "rate_limit" in error_msg:
            return (
                "❌ **Limite de requisições atingido**\n\n"
                "💡 **Solução**:\n"
                "Aguarde alguns minutos antes de tentar novamente"
            )
        
        else:
            return f"❌ **Erro nos dados bancários**: {error_msg}"
    
    @staticmethod
    def handle_database_error(error: Exception) -> str:
        """
        Trata erros de banco de dados de forma padronizada.
        
        Args:
            error: Exceção capturada
            
        Returns:
            Mensagem de erro formatada para o usuário
        """
        error_msg = str(error)
        
        if "no such table" in error_msg:
            return (
                "❌ **Banco de dados não inicializado**\n\n"
                "💡 **Solução**:\n"
                "Execute o script de inicialização do banco"
            )
        
        elif "locked" in error_msg:
            return (
                "❌ **Banco de dados ocupado**\n\n"
                "💡 **Solução**:\n"
                "Aguarde um momento e tente novamente"
            )
        
        else:
            return f"❌ **Erro no banco de dados**: {error_msg}"
    
    @staticmethod
    def handle_generic_error(error: Exception, context: str = "") -> str:
        """
        Trata erros genéricos da aplicação.
        
        Args:
            error: Exceção capturada
            context: Contexto adicional sobre onde ocorreu o erro
            
        Returns:
            Mensagem de erro formatada para o usuário
        """
        context_msg = f" em {context}" if context else ""
        return f"❌ **Erro{context_msg}**: {str(error)}"
    
    @staticmethod
    def safe_execute(func: Callable, error_handler: Callable[[Exception], str], 
                    default_return: Any = None, show_in_streamlit: bool = True) -> Any:
        """
        Executa uma função de forma segura com tratamento de exceções.
        
        Args:
            func: Função a ser executada
            error_handler: Função para tratar erros específicos
            default_return: Valor padrão a retornar em caso de erro
            show_in_streamlit: Se deve exibir o erro no Streamlit
            
        Returns:
            Resultado da função ou valor padrão em caso de erro
        """
        try:
            return func()
        except Exception as e:
            error_msg = error_handler(e)
            
            if show_in_streamlit:
                st.error(error_msg)
            else:
                print(error_msg)
            
            return default_return
    
    @staticmethod
    def streamlit_error_decorator(error_handler: Callable[[Exception], str]):
        """
        Decorator para funções que usam Streamlit com tratamento automático de erros.
        
        Args:
            error_handler: Função específica para tratar o tipo de erro esperado
            
        Returns:
            Decorator function
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_msg = error_handler(e)
                    st.error(error_msg)
                    return None
            return wrapper
        return decorator
    
    @staticmethod
    def display_error_info(title: str, details: str, solutions: list):
        """
        Exibe informações de erro formatadas no Streamlit.
        
        Args:
            title: Título do erro
            details: Detalhes do erro
            solutions: Lista de soluções sugeridas
        """
        st.error(f"❌ **{title}**")
        
        if details:
            st.write(f"**Detalhes**: {details}")
        
        if solutions:
            st.info("💡 **Soluções sugeridas**:")
            for i, solution in enumerate(solutions, 1):
                st.write(f"{i}. {solution}")


# Instância global para uso conveniente
exception_handler = ExceptionHandler()
