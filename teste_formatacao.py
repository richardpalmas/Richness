"""Script para testar a formatação da resposta IA"""

import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.abspath('.'))

# Importar funções de formatação
from pages.Dicas_Financeiras_Com_IA import separar_palavras_juntas, format_ai_response

# Texto de exemplo com problemas de formatação
exemplo_texto = """Olhasó, peladaareal: vocêédaturmaquevivenolimiteGastafeitoágua–emmédia3transaçõespordia–, praticamentetudonocartão(R$65kdedespesascontraR$69kdereceitas).

Nãosobraquasenadaprareserva, eospróximoscompromissos(R$8, 7k)vãotedrenardevezsevocênãoseguraraondaResumorápidodoseuperfildeconsumo: •Gastoelevadoequase100%nocartão: viraboladenevesenãopagaremdia•Zerofolgafinanceira: receitamenosdespesas=pouquíssimoespaçopraimprevistos•Consumidorativo: 407comprasem136diasmostramimpulsoefaltadefiltro•Compromissosfixospesados(cartão, imóvel, dízimo, veículo)jáconsomem12–15%doseuganhoOqueissodizdevocê?Vocêcurtemanterumpadrãoaltodevida, mastá"nofiodanavalha"–qualquersolavanco(despesaextra, perdadereceita)tejoganovermelhoÉhoradeparardeacharquedápramanteresseritmosemconsequênciasPróximospassos(sequisersairdesseloop): 1Cortegastossupérfluos: definaumtetomensalnocartãoeobedeça2Monteumareservamínima(pelomenos10%dareceita)antesdemaiscompras3Renegocievencimentosevaloresfixos: aliviaopesoimediato4Acompanhediariamente: semplanilha, semperdãoSecontinuarnessapegada, équestãodetempoatéocartãogritar"chega".

Aescolhaésua–ouvocêpegarédeasnoseubolso, ouseubolsovaitedominar"""

# Testar a separação de palavras
texto_separado = separar_palavras_juntas(exemplo_texto)
print("\n=== TEXTO COM PALAVRAS SEPARADAS ===")
print(texto_separado)
print("\n")

# Testar a formatação completa
texto_formatado = format_ai_response(exemplo_texto)
print("\n=== TEXTO FORMATADO (HTML) ===")
print(texto_formatado)

# Salvar o resultado em um arquivo HTML para visualização
with open("teste_formatacao.html", "w", encoding="utf-8") as f:
    f.write(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Teste de Formatação</title>
        <style>
        body {{
            background-color: #1e1e1e;
            color: #e0e0e0;
            font-family: Arial, sans-serif;
            padding: 20px;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #2a2a2a;
            border-radius: 10px;
        }}
        h2 {{
            color: #a991f7;
            border-bottom: 1px solid #444;
            padding-bottom: 10px;
        }}
        .ai-bubble {{
            background-color: #2a2a2a;
            color: #e0e0e0;
            padding: 16px 20px;
            border-radius: 20px;
            word-wrap: break-word;
            box-shadow: 0 3px 10px rgba(0,0,0,0.2);
            border: 1px solid #404040;
            font-size: 14px;
            line-height: 1.7;
            letter-spacing: 0.02em;
        }}
        .ai-bubble strong {{
            color: #a991f7;
            font-weight: 600;
        }}
        .ai-bubble br + br {{
            content: "";
            display: block;
            margin-top: 10px;
        }}
        .ai-bubble ul, .ai-bubble ol {{
            margin-top: 8px;
            margin-bottom: 8px;
            padding-left: 20px;
        }}
        .ai-bubble li {{
            margin-bottom: 5px;
        }}
        .ai-bubble span[style*="color:#28a745"] {{
            background-color: rgba(40, 167, 69, 0.1);
            padding: 0 3px;
            border-radius: 3px;
        }}
        .ai-bubble span[style*="color:#dc3545"] {{
            background-color: rgba(220, 53, 69, 0.1);
            padding: 0 3px;
            border-radius: 3px;
        }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Texto Original</h2>
            <pre>{exemplo_texto}</pre>
            
            <h2>Texto com Palavras Separadas</h2>
            <pre>{texto_separado}</pre>
            
            <h2>Visualização da Formatação Final</h2>
            <div class="ai-bubble">
                {texto_formatado}
            </div>
        </div>
    </body>
    </html>
    """)

print("\nResultado salvo em teste_formatacao.html para visualização")
