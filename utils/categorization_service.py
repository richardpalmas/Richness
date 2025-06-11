"""
Serviço de Categorização para o Pluggy - Responsável por categorizar transações
"""
import pandas as pd
from langchain_openai import ChatOpenAI
from typing import Optional

class CategorizationService:
    """Gerencia a categorização de transações usando LLM ou regras básicas"""
    
    def __init__(self, cache_manager, llm_model=None):
        self.cache_manager = cache_manager
        self.chat_model = llm_model
        
    def set_llm_model(self, llm_model):
        """Define o modelo LLM a ser usado"""
        self.chat_model = llm_model
    
    def categorizar_transacoes_com_llm(self, df, coluna_descricao="Descrição", coluna_valor="Valor", coluna_tipo="Tipo"):
        """
        Categoriza transações usando LLM para maior precisão, com cache otimizado.
        """
        if df.empty:
            return df

        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers.string import StrOutputParser

        df_temp = df.copy()
        if "Categoria" not in df_temp.columns:
            df_temp["Categoria"] = None

        rows_to_process = df_temp[df_temp["Categoria"].isna()].copy()
        if rows_to_process.empty:
            return df_temp

        batch_size = 10
        total_rows = len(rows_to_process)

        # Prompt melhorado para categorias mais específicas
        prompt = ChatPromptTemplate.from_template(
            """
            Analise a transação financeira brasileira abaixo e crie uma categoria ESPECÍFICA e DESCRITIVA baseada na descrição da transação. 

            REGRAS ESPECÍFICAS (PRIORIDADE MÁXIMA):
            1. Se a descrição contém "Transferência Recebida|RICHARD PALMAS AYRES DA SILVA" ou valor acima de R$ 2.000,00: categorize como "Salário"
            2. Se a descrição contém "Pagamento recebido": categorize como "Pagamento Cartão"
            3. Se a descrição contém "MAGAZINE LUIZA 11007/10": categorize como "Pagamento Cartão"
            4. Se a descrição contém "MP*ISRAEL": categorize como "Veículo"

            INSTRUÇÕES GERAIS:
            1. SEJA ESPECÍFICO: Em vez de "Transferência", use descrições como "Transferência João Silva", "Transferência Conta Poupança", "PIX Mercado"
            2. EVITE GENÉRICOS: Em vez de "Outros", identifique o tipo real como "Farmácia", "Posto Gasolina", "Loja Roupas", etc.
            3. USE A DESCRIÇÃO: Extraia informações úteis da descrição para criar categorias mais informativas
            4. MANTENHA CONCISO: 2-4 palavras no máximo
            5. CONTEXTO BRASILEIRO: Considere estabelecimentos, serviços e padrões brasileiros

            EXEMPLOS:
            - "PIX TRANSFERENCIA JOAO SILVA" → "PIX João Silva"
            - "POSTO IPIRANGA" → "Posto Ipiranga"
            - "MERCADO SAO VICENTE" → "Mercado São Vicente"
            - "FARMACIA DROGA RAIA" → "Farmácia Droga Raia"
            - "TRANSFERENCIA CONTA CORRENTE" → "Transferência Bancária"
            - "Transferência Recebida|RICHARD PALMAS AYRES DA SILVA" → "Salário"
            - "Pagamento recebido" → "Pagamento Cartão"
            - "MAGAZINE LUIZA 11007/10" → "Pagamento Cartão"
            - "MP*ISRAEL COMBUSTIVEL" → "Veículo"

            Descrição: {descricao}
            Valor: {valor}
            Tipo: {tipo}
            
            Responda apenas com a categoria específica, sem explicações.
            """
        )
        
        chain = None
        if self.chat_model is not None:
            chain = prompt | self.chat_model | StrOutputParser()

        for i in range(0, total_rows, batch_size):
            batch = rows_to_process.iloc[i:min(i+batch_size, total_rows)]
            for idx, row in batch.iterrows():
                descricao = str(row[coluna_descricao]) if not pd.isna(row[coluna_descricao]) else ""
                valor = row[coluna_valor] if not pd.isna(row[coluna_valor]) else 0
                tipo = row[coluna_tipo] if not pd.isna(row[coluna_tipo]) else ""
                
                # Aplicar regras específicas antes do LLM
                categoria_especifica = None
                
                # Regra 1: Transferência de salário específica ou valor alto
                if ("Transferência Recebida|RICHARD PALMAS AYRES DA SILVA" in descricao or 
                    (valor > 2000 and "Transferência" in descricao and valor > 0)):
                    categoria_especifica = "Salário"
                elif "Pagamento recebido" in descricao:
                    categoria_especifica = "Pagamento Cartão"
                elif "MAGAZINE LUIZA 11007/10" in descricao:
                    categoria_especifica = "Pagamento Cartão"
                elif "MP*ISRAEL" in descricao:
                    categoria_especifica = "Veículo"
                
                # Se temos uma categoria específica, usar ela
                if categoria_especifica:
                    df_temp.loc[idx, "Categoria"] = categoria_especifica
                    continue
                
                cache_key = self.cache_manager.get_hash(f"{descricao}_{valor}_{tipo}")
                categoria_cache = self.cache_manager.get_from_category_cache(cache_key)
                
                if categoria_cache:
                    df_temp.loc[idx, "Categoria"] = categoria_cache
                    continue
                    
                if chain is not None:
                    try:
                        categoria = chain.invoke({"descricao": descricao, "valor": valor, "tipo": tipo})
                        df_temp.loc[idx, "Categoria"] = categoria
                        self.cache_manager.save_to_category_cache(cache_key, categoria)
                    except Exception as e:
                        print(f"Erro ao categorizar transação: {e}")
                        df_temp.loc[idx, "Categoria"] = "Outros"
                else:
                    df_temp.loc[idx, "Categoria"] = "Outros"
                    
        return df_temp

    def enriquecer_descricoes(self, df, coluna_descricao="Descrição"):
        """
        Melhora as descrições curtas ou confusas usando IA, com sistema de cache otimizado.
        """
        if df.empty or coluna_descricao not in df.columns:
            return df

        # Criar uma cópia para não modificar o original
        df_temp = df.copy()

        # Adicionar coluna de descrição enriquecida se não existir
        if "DescriçãoCompleta" not in df_temp.columns:
            df_temp["DescriçãoCompleta"] = df_temp[coluna_descricao]

        # Identificar descrições que precisam ser enriquecidas (curtas ou confusas)
        mask_curtas = df_temp[coluna_descricao].str.len() < 10
        mask_confusas = df_temp[coluna_descricao].str.contains('|'.join(['trf', 'ted', 'doc', 'transf', 'pix']), case=False, na=False)
        mask_numeros = df_temp[coluna_descricao].str.match(r'^\d+$', na=False)

        rows_to_process = df_temp[mask_curtas | mask_confusas | mask_numeros].copy()

        # Processar em lotes menores para otimizar
        batch_size = 10
        total_rows = len(rows_to_process)

        for i in range(0, total_rows, batch_size):
            batch = rows_to_process.iloc[i:min(i+batch_size, total_rows)]

            for idx, row in batch.iterrows():
                desc_original = str(row[coluna_descricao]) if not pd.isna(row[coluna_descricao]) else ""

                # Pular descrições vazias
                if not desc_original.strip():
                    continue

                # Verificar cache
                cache_key = self.cache_manager.get_hash(desc_original)
                descricao_cache = self.cache_manager.get_from_description_cache(cache_key)
                
                if descricao_cache:
                    df_temp.loc[idx, "DescriçãoCompleta"] = descricao_cache
                    continue

                # Só processar descrições realmente problemáticas para economizar chamadas
                if len(desc_original) >= 10 and not any(term in desc_original.lower() for term in ['trf', 'ted', 'doc', 'transf', 'pix']):
                    continue

                # Enriquecer com IA
                if self.chat_model is not None:
                    from langchain_core.prompts import ChatPromptTemplate
                    from langchain_core.output_parsers.string import StrOutputParser
                    
                    prompt = ChatPromptTemplate.from_template("""
                        Melhore a seguinte descrição de transação financeira para uma versão mais clara e descritiva,
                        em até 10 palavras. Infira o provável significado baseado em padrões comuns.
                        Apenas retorne a descrição melhorada, sem explicações ou comentários adicionais.

                        Descrição original: {descricao}
                    """)

                    chain = prompt | self.chat_model | StrOutputParser()
                    
                    try:
                        descricao_melhorada = chain.invoke({"descricao": desc_original})
                        df_temp.loc[idx, "DescriçãoCompleta"] = descricao_melhorada
                        self.cache_manager.save_to_description_cache(cache_key, descricao_melhorada)
                    except Exception as e:
                        print(f"Erro ao enriquecer descrição: {e}")
            
        return df_temp
    
    def aplicar_categorizacao_basica(self, df):
        """
        Aplica categorização básica sem LLM para carregamento rápido.
        Usa regras simples baseadas em palavras-chave.
        """
        if df.empty:
            return df
            
        df_temp = df.copy()
        
        # Adicionar coluna de categoria se não existir
        if "Categoria" not in df_temp.columns:
            df_temp["Categoria"] = "Outros"
        
        # Aplicar categorização básica por palavras-chave
        for idx, row in df_temp.iterrows():
            descricao = str(row.get("Descrição", ""))
            descricao_lower = descricao.lower()
            valor = row.get("Valor", 0)
            
            # APLICAR REGRAS ESPECÍFICAS PRIMEIRO (PRIORIDADE MÁXIMA)
            # Regra 1: Transferência de salário específica ou valor alto
            if ("Transferência Recebida|RICHARD PALMAS AYRES DA SILVA" in descricao or 
                (valor > 2000 and "Transferência" in descricao and valor > 0)):
                df_temp.loc[idx, "Categoria"] = "Salário"
            # Regra 2: Pagamento recebido
            elif "Pagamento recebido" in descricao:
                df_temp.loc[idx, "Categoria"] = "Pagamento Cartão"
            # Regra 3: Magazine Luiza específica
            elif "MAGAZINE LUIZA 11007/10" in descricao:
                df_temp.loc[idx, "Categoria"] = "Pagamento Cartão"
            # Regra 4: MP*ISRAEL para veículo
            elif "MP*ISRAEL" in descricao:
                df_temp.loc[idx, "Categoria"] = "Veículo"
            # Categorização básica por palavras-chave
            elif any(word in descricao_lower for word in ['salário', 'salario', 'vencimento', 'pagamento salario']):
                df_temp.loc[idx, "Categoria"] = "Salário"
            elif any(word in descricao_lower for word in ['supermercado', 'mercado', 'alimentação', 'restaurante', 'ifood']):
                df_temp.loc[idx, "Categoria"] = "Alimentação"
            elif any(word in descricao_lower for word in ['transferência', 'transferencia', 'pix', 'ted', 'doc']):
                df_temp.loc[idx, "Categoria"] = "Transferência"
            elif any(word in descricao_lower for word in ['transporte', 'uber', 'taxi', '99', 'combustível', 'gasolina']):
                df_temp.loc[idx, "Categoria"] = "Transporte"
            elif any(word in descricao_lower for word in ['moradia', 'aluguel', 'condomínio', 'agua', 'luz', 'gas']):
                df_temp.loc[idx, "Categoria"] = "Moradia"
            elif any(word in descricao_lower for word in ['saúde', 'hospital', 'médico', 'farmácia', 'remédio']):
                df_temp.loc[idx, "Categoria"] = "Saúde"
            elif any(word in descricao_lower for word in ['educação', 'escola', 'curso', 'livro']):
                df_temp.loc[idx, "Categoria"] = "Educação"
            elif any(word in descricao_lower for word in ['lazer', 'cinema', 'teatro', 'netflix', 'spotify']):
                df_temp.loc[idx, "Categoria"] = "Lazer"
            elif any(word in descricao for word in ['vestuário', 'roupa', 'calçado', 'shopping']):
                df_temp.loc[idx, "Categoria"] = "Vestuário"
            # Categoria permanece como "Outros" se não encontrar correspondência
                
        return df_temp
