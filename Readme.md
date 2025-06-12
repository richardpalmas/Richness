
# 💰 Richness - Analisador de Finanças Pessoais

**Sistema completo de análise financeira com OFX e IA** ✨

Este é um projeto que permite analisar suas finanças pessoais baseado em arquivos .ofx, utilizando modelos de linguagem (ChatGPT, Claude, Groq, LLMs locais) para categorizar automaticamente as transações e gerar insights inteligentes.

🎯 **Nova versão com sistema OFX nativo - Mais rápida, segura e confiável!**

## 🚀 **Recursos Principais**

- 📊 **Dashboard Financeiro Completo** - Visão geral de receitas, despesas e saldos
- 💳 **Análise de Cartão de Crédito** - Controle detalhado de gastos no cartão
- 💰 **Minhas Economias** - Acompanhamento de economia e investimentos
- 🤖 **Dicas Financeiras com IA** - Insights personalizados usando LLMs
- 🏷️ **Categorização Automática** - 9 categorias inteligentes para transações
- ⚡ **Performance Superior** - Processamento local de dados OFX
- 🔒 **Privacidade Total** - Seus dados permanecem no seu computador

## 📁 **Sistema OFX Nativo**

**Migração concluída com sucesso!** O sistema agora utiliza arquivos OFX locais ao invés de APIs externas:

- ✅ **Extratos Bancários**: Coloque arquivos .ofx na pasta `extratos/`
- ✅ **Faturas de Cartão**: Coloque arquivos .ofx na pasta `faturas/`  
- ✅ **Atualização Automática**: Sistema detecta novos arquivos automaticamente
- ✅ **Categorização IA**: Processamento inteligente de transações

---

## 📊 **Status Atual**

**🎉 Sistema funcionando perfeitamente!**
- 📈 **597 transações** processadas
- 📄 **12 arquivos OFX** carregados
- ⚡ **Performance otimizada** com cache local
- 🔧 **Zero dependências externas**



## 💻 **Requisitos**

- Python 3.11+
- Streamlit
- Pandas, Plotly
- Arquivos OFX do seu banco/cartão

## 🛠️ **Instalação Rápida**

1. **Clone o repositório:**
   ```bash
   git clone [repo-url]
   cd Richness
   ```

2. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure a IA (opcional):**
   - Crie um arquivo `.env`
   - Adicione: `GROQ_API_KEY=sua-chave`

4. **Adicione seus dados:**
   - Extratos bancários (.ofx) → pasta `extratos/`
   - Faturas de cartão (.ofx) → pasta `faturas/`

5. **Execute a aplicação:**
   ```bash
   streamlit run Home.py
   ```

## 📋 **Como Usar**

### 1. Obtendo Arquivos OFX

**Nubank:**
- App/Site → Extrato → Exportar → Formato OFX

**Outros Bancos:**
- Internet Banking → Extrato → Exportar → OFX

### 2. Organizando Arquivos
```
extratos/     ← Arquivos de conta corrente/poupança
faturas/      ← Arquivos de cartão de crédito  
```

### 3. Acessando o Sistema
- Abra http://localhost:8501
- Faça login/cadastro
- Explore os 4 módulos principais

---

## 🏷️ **Categorização Automática**

O sistema categoriza suas transações automaticamente:

| Categoria | Exemplos |
|-----------|----------|
| 🍽️ Alimentação | Restaurantes, supermercados, iFood |
| 🚗 Transporte | Uber, posto de gasolina, estacionamento |
| 🏥 Saúde | Farmácias, hospitais, planos de saúde |
| 📚 Educação | Escolas, cursos, livros |
| 🎮 Lazer | Cinema, Netflix, games |
| 🏠 Moradia | Aluguel, luz, água, internet |
| 👕 Vestuário | Roupas, calçados |
| 💸 Transferência | PIX, TED, DOC |
| 💰 Salário | Recebimentos de salário |

---

## 📖 **Documentação**

- 📄 [Guia Rápido OFX](GUIA_OFX.md)
- 📊 [Relatório de Migração](docs/MIGRATION_COMPLETE_REPORT.md)
- 🔧 [Fundamentos do Projeto](fundamentos.md)
- 📋 [Guia de Uso Rápido](GUIA_USO_RAPIDO.md)

---

## 🎓 **Aprenda Mais**

Este é o código fonte do projeto apresentado [neste vídeo](https://www.instagram.com/p/C_03fokuu-4/).

Se quer aprender a programar do zero em Python e trabalhar com IAs, [crie uma conta na Asimov Academy](https://hub.asimov.academy/registrar) e acesse nossos cursos gratuitos!

