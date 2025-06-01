import pandas as pd

def formatar_valor_monetario(valor, decimais=2, prefixo="R$ "):
    """
    Formata um valor numérico para formato monetário brasileiro.

    Parameters:
    - valor: Valor numérico a ser formatado
    - decimais: Número de casas decimais (padrão: 2)
    - prefixo: Prefixo monetário (padrão: "R$ ")

    Returns:
    - str: Valor formatado (ex: "R$ 1.234,56")
    """
    return f"{prefixo}{valor:,.{decimais}f}".replace(",", "X").replace(".", ",").replace("X", ".")

def formatar_df_monetario(df, col_valor="Valor", col_destino="ValorFormatado", decimais=2, prefixo="R$ ", sufixo=""):
    """
    Adiciona uma coluna formatada para valores monetários em um dataframe.

    Parameters:
    - df: DataFrame pandas a ser modificado
    - col_valor: Nome da coluna com valores numéricos
    - col_destino: Nome da coluna de destino para os valores formatados
    - decimais: Número de casas decimais
    - prefixo: Prefixo monetário
    - sufixo: Sufixo opcional

    Returns:
    - DataFrame: DataFrame com a coluna formatada adicionada
    """
    # Evitar modificar o DataFrame original
    df_copia = df.copy()

    # Aplicar a formatação
    df_copia[col_destino] = df_copia[col_valor].apply(
        lambda x: formatar_valor_monetario(x, decimais, prefixo) + sufixo if pd.notna(x) else ""
    )

    return df_copia

def calcular_resumo_financeiro(df, col_valor="Valor", col_descricao="Descrição", col_categoria="Categoria"):
    """
    Calcula o resumo financeiro (receitas, despesas e saldo) de um dataframe,
    excluindo transações que representam movimentações internas entre contas próprias,
    mas capturando corretamente todas as saídas de dinheiro.

    Parameters:
    - df: DataFrame pandas com valores financeiros
    - col_valor: Nome da coluna que contém os valores
    - col_descricao: Nome da coluna com a descrição da transação
    - col_categoria: Nome da coluna com a categoria da transação

    Returns:
    - dict: Dicionário com receitas, despesas, saldo e dicionários com índices das transações classificadas
    """
    if df.empty:
        return {"receitas": 0, "despesas": 0, "saldo": 0, "é_receita_real": {}, "é_despesa_real": {}}

    # Criar uma cópia do DataFrame para trabalhar
    df_filtrado = df.copy()

    # Separar valores positivos e negativos para análise inicial
    df_positivos = df_filtrado[df_filtrado[col_valor] > 0].copy()
    df_negativos = df_filtrado[df_filtrado[col_valor] < 0].copy()

    # Identificar transações internas entre contas próprias
    # Lista de termos que indicam transações internas
    termos_transacoes_internas = [
        'transferência entre contas', 'transferencia entre contas',
        'mesmo titular', 'mesma titularidade', 'entre minhas contas',
        'para minha conta', 'para minha própria conta'
    ]

    # Palavras-chave para identificar transferências de saída
    transferencias_saida = [
        'transferência', 'transferencia', 'transf ', 'ted ', 'pix ',
        'envio ', 'enviado', 'enviada', 'para ', 'destinatário'
    ]

    # Palavras-chave para identificar transferências de entrada
    transferencias_entrada = [
        'transferência recebida', 'transferencia recebida', 'transf recebida',
        'ted recebida', 'pix recebido', 'recebimento', 'recebido de',
        'crédito de ', 'credito de ', 'depósito', 'deposito'
    ]

    # Termos que sempre indicam entradas reais (receitas)
    receitas_keywords = [
        'salário', 'salario', 'rendimento', 'dividendos', 'bonificação', 'bonificacao',
        'prêmio', 'premio', 'bônus', 'bonus', 'venda', 'reembolso', 'juros', 'restituição',
        'restituicao', 'aluguel', 'freelance', 'comissão', 'comissao', 'estorno',
        'remuneração', 'remuneracao', 'pagto', 'provento',
        'devolução', 'devolucao', 'cashback', 'reembolso', 'indenização', 'indenizacao',
        'pgto salario', 'credito salario', 'crédito salário', 'resgate rdb', 'resgate',
        'resgate de', 'liquidação', 'liquidacao', 'vencimento', 'amortização', 'amortizacao'
    ]

    # Termos que geralmente parecem entradas, mas são falsos positivos
    falsos_positivos_entrada = [
        'pagamento recebido', 'pagamento de fatura', 'pagamento cartao', 'pagamento cartão',
        'fatura', 'pagamento de conta', 'pag conta', 'pag fatura', 'pagamento realizado',
        'fatura paga', 'pagamento efetuado'
    ]

    # Categorias que representam receitas
    receitas_categorias = [
        'salário', 'salario', 'rendimento', 'receita', 'entrada', 'provento', 'renda',
        'remuneração', 'remuneracao', 'ganho', 'transferência recebida', 'resgate'
    ]

    # Palavras-chave para identificar despesas
    despesas_keywords = [
        'compra', 'pagamento', 'supermercado', 'mercado', 'farmácia', 'farmacia',
        'restaurante', 'combustível', 'combustivel', 'conta', 'serviço', 'servico',
        'tarifa', 'assinatura', 'mensalidade', 'aluguel', 'cinema', 'teatro',
        'escola', 'curso', 'academia', 'loja', 'shopping', 'uber', '99', 'taxi',
        'débito', 'debito', 'saque', 'taxa', 'impostos', 'imposto', 'multa',
        'ifood', 'delivery', 'entrega', 'pedido', 'delivery', 'motoboy', 'roupas',
        'calçados', 'calcados', 'medicamento', 'remédio', 'remedio', 'hospital',
        'clinica', 'exame', 'médico', 'medico', 'dentista', 'pet', 'animal', 'veterinário',
        'veterinario', 'netflix', 'spotify', 'amazon', 'prime', 'disney', 'hbo', 'max',
        'globoplay', 'apple', 'google', 'microsoft', 'adobe', 'compras', 'shopping', 'mall',
        'fast food', 'fastfood', 'lanche', 'burger', 'pizza', 'china', 'japonês', 'japones',
        'internet', 'telefone', 'celular', 'luz', 'água', 'agua', 'gás', 'gas', 'condomínio',
        'condominio', 'iptu', 'ipva', 'seguro', 'parcela', 'prestação', 'prestacao',
        'ted para', 'pix para', 'doc para', 'transferência para', 'transferencia para',
        'boleto', 'guia', 'ingresso', 'passagem', 'hotel', 'viagem', 'pacote', 'hospedagem',
        'estacionamento', 'pedágio', 'pedagio', 'material', 'livro', 'plano', 'streaming',
        'app store', 'play store', 'débito automatico', 'debito automatico', 'conta de'
    ]

    # Categorias de despesas
    despesas_categorias = [
        'alimentação', 'alimentacao', 'transporte', 'moradia', 'saúde', 'saude',
        'educação', 'educacao', 'lazer', 'vestuário', 'vestuario', 'outros', 'despesa',
        'compras', 'mercado', 'serviços', 'servicos',
        'transferência enviada', 'transferencia enviada', 'enviado', 'pix enviado',
        'ted enviado', 'doc enviado'
    ]

    # Termos relacionados a cartão de crédito (não devem ser contabilizados diretamente)
    cartao_credito_keywords = [
        'fatura', 'cartão', 'cartao', 'fatura de cartão', 'fatura de cartao',
        'pagamento de cartão', 'pagamento de cartao', 'cartão de crédito',
        'cartao de credito', 'maquininha', 'acquirer', 'pos', 'compra com cartão',
        'pagamento fatura'
    ]

    # Aplicações financeiras (não são despesas nem receitas reais)
    aplicacoes_keywords = [
        'aplicação', 'aplicacao', 'investimento', 'aporte', 'compra de título',
        'compra de titulo', 'tesouro direto', 'cdb', 'lci', 'lca', 'fundo'
    ]

    # Resgates financeiros (são receitas reais)
    resgates_keywords = [
        'resgate', 'liquidação', 'liquidacao', 'vencimento', 'amortização',
        'amortizacao', 'resgate de', 'liquidação de', 'liquidacao de', 'resgate rdb'
    ]

    # Função para verificar se uma descrição ou categoria contém palavras-chave
    def contem_palavras(texto, palavras_chave):
        if pd.isna(texto):
            return False
        texto = str(texto).lower()
        return any(palavra in texto for palavra in palavras_chave)

    # Dicionários para rastrear quais transações são receitas ou despesas
    é_receita_real = {}
    é_despesa_real = {}
    é_transacao_interna = {}
    é_aplicacao = {}
    é_resgate = {}
    é_cartao_credito = {}

    # Função para determinar se uma transação é relacionada a cartão de crédito
    def é_cartao_credito_fn(row):
        if pd.isna(row[col_descricao]) and pd.isna(row[col_categoria]):
            return False

        descricao = str(row[col_descricao]).lower() if not pd.isna(row[col_descricao]) else ""
        categoria = str(row[col_categoria]).lower() if not pd.isna(row[col_categoria]) else ""

        return contem_palavras(descricao, cartao_credito_keywords) or contem_palavras(categoria, ['fatura', 'cartão', 'cartao'])

    # Função para determinar se uma transação é interna (entre contas próprias)
    def é_transacao_interna_fn(row):
        # Se não temos descrição nem categoria, não podemos determinar
        if pd.isna(row[col_descricao]) and pd.isna(row[col_categoria]):
            return False

        descricao = str(row[col_descricao]).lower() if not pd.isna(row[col_descricao]) else ""
        categoria = str(row[col_categoria]).lower() if not pd.isna(row[col_categoria]) else ""

        # Verificar se contém termos explícitos de transação interna
        if contem_palavras(descricao, termos_transacoes_internas):
            return True

        # Verificar padrões de transferência entre contas do mesmo titular
        if "transferência" in descricao or "transferencia" in descricao:
            if "própria" in descricao or "propria" in descricao or "mesmo titular" in descricao:
                return True

        return False

    # Função para determinar se é uma aplicação financeira
    def é_aplicacao_fn(row):
        if pd.isna(row[col_descricao]) and pd.isna(row[col_categoria]):
            return False

        descricao = str(row[col_descricao]).lower() if not pd.isna(row[col_descricao]) else ""
        categoria = str(row[col_categoria]).lower() if not pd.isna(row[col_categoria]) else ""

        return contem_palavras(descricao, aplicacoes_keywords) or "aplicação" in categoria or "aplicacao" in categoria

    # Função para determinar se é um resgate financeiro
    def é_resgate_fn(row):
        if pd.isna(row[col_descricao]) and pd.isna(row[col_categoria]):
            return False

        descricao = str(row[col_descricao]).lower() if not pd.isna(row[col_descricao]) else ""
        categoria = str(row[col_categoria]).lower() if not pd.isna(row[col_categoria]) else ""

        return contem_palavras(descricao, resgates_keywords) or "resgate" in categoria

    # Função para identificar uma transação como receita real
    def é_receita_real_fn(row, idx):
        # Garantir que valores negativos nunca sejam considerados como receitas
        if row[col_valor] <= 0:
            return False

        # Se é uma transferência interna, não é uma receita real
        if é_transacao_interna.get(idx, False):
            return False

        # Se é um resgate de aplicação, É uma receita real (modificado para considerar como receita)
        if é_resgate.get(idx, True):
            return True

        if pd.isna(row[col_descricao]) and pd.isna(row[col_categoria]):
            # Ser conservador: se não há descrição ou categoria, não considerar automaticamente como receita
            return False

        descricao = str(row[col_descricao]).lower() if not pd.isna(row[col_descricao]) else ""
        categoria = str(row[col_categoria]).lower() if not pd.isna(row[col_categoria]) else ""

        # Verificar se é um falso positivo (como pagamento de cartão)
        if contem_palavras(descricao, falsos_positivos_entrada):
            return False

        # Identificar explicitamente o salário ou pagamentos recebidos da empresa
        if "salário" in descricao or "salario" in descricao or "pagamento de salario" in descricao:
            return True

        # Verificar se é uma transferência recebida específica (com nome do usuário)
        if "transferência recebida|richard" in descricao.lower() or "transferencia recebida|richard" in descricao.lower():
            return True

        # Verificar se a categoria indica receita
        if contem_palavras(categoria, receitas_categorias):
            return True

        # Verificar se contém palavras-chave de receitas
        if contem_palavras(descricao, receitas_keywords):
            return True

        # Verificar se é uma transferência recebida (possível receita)
        if contem_palavras(descricao, transferencias_entrada):
            # Se for um valor acima de 100, provavelmente é uma receita real
            if row[col_valor] > 100:
                return True

        # Se não encontramos evidências claras, não considerar automaticamente como receita
        return False

    # Função para identificar uma transação como despesa real
    def é_despesa_real_fn(row, idx):
        # Garantir que valores positivos nunca sejam considerados como despesas
        if row[col_valor] >= 0:
            return False

        # Se é uma transferência interna, não é uma despesa real
        if é_transacao_interna.get(idx, False):
            return False

        # Se é uma aplicação financeira, não é uma despesa real (apenas movimentação)
        if é_aplicacao.get(idx, False):
            return False

        # Se é uma transação de cartão de crédito, não considere como despesa
        # (pois a despesa real é quando pagamos a fatura)
        if é_cartao_credito.get(idx, False):
            return False

        # Por padrão, qualquer valor negativo é considerado despesa,
        # a menos que identifiquemos especificamente como não-despesa
        if pd.isna(row[col_descricao]) and pd.isna(row[col_categoria]):
            return True  # Valores negativos sem descrição são despesas por padrão

        descricao = str(row[col_descricao]).lower() if not pd.isna(row[col_descricao]) else ""
        categoria = str(row[col_categoria]).lower() if not pd.isna(row[col_categoria]) else ""

        # Verificar se a categoria indica despesa
        if contem_palavras(categoria, despesas_categorias):
            return True

        # Verificar se contém palavras-chave de despesas
        if contem_palavras(descricao, despesas_keywords):
            return True

        # Verificar se é uma transferência de saída (provável despesa)
        if contem_palavras(descricao, transferencias_saida) and not é_transacao_interna.get(idx, False):
            return True

        # Se não identificamos especificamente como não-despesa,
        # considerar qualquer valor negativo como despesa
        return True

    # Primeiro passo: identificar transações internas, aplicações, resgates e cartão de crédito
    for idx, row in df_filtrado.iterrows():
        é_transacao_interna[idx] = é_transacao_interna_fn(row)
        é_aplicacao[idx] = é_aplicacao_fn(row)
        é_resgate[idx] = é_resgate_fn(row)
        é_cartao_credito[idx] = é_cartao_credito_fn(row)

    # Segundo passo: classificar receitas e despesas, respeitando as classificações anteriores
    for idx, row in df_filtrado.iterrows():
        é_receita_real[idx] = é_receita_real_fn(row, idx)
        é_despesa_real[idx] = é_despesa_real_fn(row, idx)

    # Calcular receitas e despesas reais
    df_receitas = df_filtrado.loc[[idx for idx, val in é_receita_real.items() if val]]
    df_despesas = df_filtrado.loc[[idx for idx, val in é_despesa_real.items() if val]]

    receitas = df_receitas[col_valor].sum() if not df_receitas.empty else 0
    despesas = abs(df_despesas[col_valor].sum()) if not df_despesas.empty else 0

    # Corrigir valores negativos ou muito pequenos
    receitas = max(0, receitas)
    despesas = max(0, despesas)

    # Calcular o saldo real do período
    saldo = receitas - despesas

    return {
        "receitas": receitas,
        "despesas": despesas,
        "saldo": saldo,
        "é_receita_real": é_receita_real,
        "é_despesa_real": é_despesa_real
    }
