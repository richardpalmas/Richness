# Analisador de finanças pessoais usando LLMs


Este é um projeto que te permite analisar finanças pessoais, baseados em arquivos .ofx, utilizando modelos de linguagem (ChatGPT, Claude, Groq, LLMs locais) para categorizar automaticamente as transações.

<img src="video.gif"/>


Este é o código fonte do projeto apresentado [neste vídeo](https://www.instagram.com/p/C_03fokuu-4/).

Se quer aprender a como programar do zero em Python e a trabalhar com IAs, não deixe de [criar uma conta na Asimov Academy](https://hub.asimov.academy/registrar) e assistir aos nossos cursos gratuitos!


# Estrutura e Manutenção

Este projeto segue o 4º Fundamento: **"PROJETO LIMPO"** com código organizado, legível e bem estruturado.

## 🏗️ Arquitetura Modular

O projeto utiliza uma **arquitetura modular** com serviços especializados:
- **`api_manager.py`** - Gerenciamento de APIs e autenticação
- **`cache_manager.py`** - Sistema de cache persistente
- **`sync_manager.py`** - Sincronização com bancos
- **`account_manager.py`** - Gerenciamento de contas
- **`transaction_manager.py`** - Processamento de transações
- **`categorization_service.py`** - Categorização inteligente com IA

Para informações sobre manutenção e organização do projeto, consulte [MANUTENCAO_PROJETO.md](docs/MANUTENCAO_PROJETO.md).

Para detalhes sobre a migração para arquitetura modular, veja [MIGRACAO_ARQUITETURA_REFATORADA.md](docs/MIGRACAO_ARQUITETURA_REFATORADA.md).

A limpeza periódica pode ser executada com:
```bash
python scripts/limpeza_periodica.py
```


# Requisitos

- `Python 3.6+`

# Instalação

1.	Clone o repositório e navegue até o diretório do projeto.
2.	Instale os pacotes Python necessários:
git 
`pip install -r requirements.txt`

3.	Crie um arquivo .env e adicione sua chave da Groq nele, seguindo o modelo: `GROQ_API_KEY=sua-chave`.
4.  Adicione seus extratos bancários na pasta `extratos`.


# Manutenção do Projeto

O projeto segue o 4º Fundamento: **"PROJETO LIMPO"** para manter o código limpo, legível e bem estruturado.

## Limpeza e Organização

Para manter o projeto organizado:

1. **Limpeza Periódica**
   ```
   python scripts/limpeza_periodica.py
   ```

2. **Limpeza Completa** (quando necessário)
   ```
   python scripts/executar_limpeza_completa.py
   ```

Para mais informações sobre a organização do projeto e boas práticas, consulte o documento [MANUTENCAO_PROJETO.md](docs/MANUTENCAO_PROJETO.md).

