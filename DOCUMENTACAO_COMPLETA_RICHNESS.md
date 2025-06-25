# 💰 Documentação Completa - Richness

## 📋 Visão Geral do Sistema

**Richness** é uma plataforma completa de gestão financeira pessoal desenvolvida em Python com Streamlit, focada em análise inteligente de transações financeiras, categorização automática com IA e insights personalizados.

### 🎯 Características Principais
- **Arquitetura Backend V2**: Sistema robusto com banco SQLite e padrão Repository
- **Inteligência Artificial**: Categorização automática e assistente conversacional
- **Segurança Avançada**: Autenticação, isolamento por usuário, proteção CSRF
- **Multi-usuário**: Sistema completo de gerenciamento de usuários
- **Análise Avançada**: Insights financeiros, alertas e tendências

---

## 🏗️ Arquitetura do Sistema

### 📊 Modelo de Dados (SQLite)

#### Tabela `usuarios`
```sql
- id (INTEGER PRIMARY KEY)
- username (TEXT UNIQUE)
- user_hash (TEXT UNIQUE) - Hash de 16 caracteres para isolamento
- password_hash (TEXT) - Hash bcrypt da senha
- email (TEXT)
- created_at (TIMESTAMP)
- last_login (TIMESTAMP)
- preferences (TEXT JSON)
- is_active (BOOLEAN)
```

#### Tabela `transacoes`
```sql
- id (INTEGER PRIMARY KEY)
- user_id (INTEGER FK)
- hash_transacao (TEXT) - Hash único MD5 da transação
- data (DATE)
- descricao (TEXT)
- valor (DECIMAL)
- categoria (TEXT)
- tipo (TEXT) - 'receita' ou 'despesa'
- origem (TEXT) - 'ofx_extrato', 'ofx_cartao', 'manual'
- conta (TEXT)
- arquivo_origem (TEXT)
```

#### Tabela `compromissos`
```sql
- id (INTEGER PRIMARY KEY)
- user_id (INTEGER FK)
- descricao (TEXT)
- valor (DECIMAL)
- data_vencimento (DATE)
- categoria (TEXT)
- status (TEXT) - 'pendente', 'pago', 'cancelado'
- observacoes (TEXT)
```

#### Tabelas Auxiliares
- `categorias_personalizadas` - Categorias criadas pelo usuário
- `descricoes_personalizadas` - Notas pessoais em transações
- `transacoes_excluidas` - Soft delete de transações
- `transacoes_manuais` - Transações inseridas manualmente
- `cache_categorizacao_ia` - Cache das categorizações da IA
- `conversas_ia` - Histórico de conversas com assistente
- `arquivos_ofx_processados` - Controle de arquivos importados
- `system_logs` - Logs de auditoria do sistema

---

## 📱 Páginas e Funcionalidades

### 🏠 **Home.py** - Dashboard Principal
**Descrição**: Página principal com visão geral das finanças do usuário.

**Funcionalidades**:
- **Autenticação de usuários** com formulário de login profissional
- **Dashboard financeiro** com métricas principais:
  - Total de transações
  - Receitas totais
  - Despesas totais
  - Saldo líquido
  - Ticket médio
- **Insights de IA integrados** com:
  - Saldo mensal disponível
  - Categoria de maior gasto
  - Alertas financeiros
  - Status de categorização automática
- **Gráficos interativos**:
  - Despesas por categoria (pizza)
  - Receitas por categoria (pizza)
  - Evolução temporal (linhas)
- **Análise detalhada por categorias** com abas:
  - Todas as transações
  - Receitas apenas
  - Despesas apenas
  - Por categoria específica
- **Filtros avançados**:
  - Seleção de período customizável
  - Filtro por categorias
  - Filtro por origem (cartão/extrato)
- **Notificações de compromissos** próximos ao vencimento
- **Foto de perfil** personalizada do usuário

**Componentes Visuais**:
- Cards com gradientes coloridos para métricas
- Gráficos Plotly interativos
- Sistema de abas para organização
- Sidebar com controles e filtros

---

### 💳 **Cartao.py** - Análise de Cartão de Crédito
**Descrição**: Página especializada para análise de gastos com cartão de crédito.

**Funcionalidades**:
- **Análise específica de cartão** separada do extrato bancário
- **Fatura detalhada** com:
  - Total gasto no período
  - Número de transações
  - Ticket médio
  - Maior gasto individual
- **Categorização de gastos** no cartão
- **Gráficos especializados**:
  - Gastos por categoria
  - Evolução mensal de gastos
  - Comparativo com períodos anteriores
- **Filtros específicos**:
  - Por período de fatura
  - Por categoria
  - Por valor mínimo
- **Cache inteligente** para performance
- **Interface otimizada** para análise de crédito

**Diferencial**: Separação clara entre gastos à vista (extrato) e crédito (fatura).

---

### 💰 **Minhas_Economias.py** - Gestão de Economias e Metas
**Descrição**: Página para acompanhamento de economias e gestão de compromissos.

**Funcionalidades**:
- **Dashboard de economias** com análise de saldo positivo
- **Gestão de compromissos/metas**:
  - Adicionar novos compromissos
  - Visualizar compromissos pendentes
  - Marcar como pagos
  - Categorizar por tipo
- **Análise de sobras mensais**
- **Projeções financeiras**
- **Alertas de vencimento** de compromissos
- **Métricas de economia**:
  - Total economizado
  - Meta de economia mensal
  - Percentual de economia sobre receita
- **Gráficos de progresso** das metas
- **Sistema de categorias** para compromissos

**Interface**: Abas organizadas para diferentes tipos de análise financeira.

---

### 🤖 **Assistente_IA.py** - Assistente Virtual Inteligente
**Descrição**: Interface conversacional com IA para análise e consultas financeiras.

**Funcionalidades**:
- **Chat inteligente** com assistente financeiro
- **Personalidades do assistente**:
  - Clara (direta e objetiva)
  - Amigável (calorosa e empática)
  - Analítica (técnica e detalhada)
  - Motivacional (encorajadora)
- **Consultas suportadas**:
  - "Qual meu saldo atual?"
  - "Quanto gastei em alimentação?"
  - "Minhas maiores despesas?"
  - "Como está minha situação financeira?"
- **Insights em tempo real** na sidebar:
  - Saldo mensal atual
  - Categoria de maior gasto
  - Alertas financeiros
  - Sugestões de economia
- **Estatísticas de IA**:
  - Taxa de precisão da categorização
  - Transações categorizadas
  - Performance do aprendizado
- **Histórico de conversas** persistente
- **Respostas contextualizadas** baseadas nos dados do usuário

**Tecnologia**: Integração com OpenAI GPT para respostas inteligentes.

---

### 📊 **Insights_Financeiros.py** - Análises Avançadas
**Descrição**: Dashboard avançado com insights e análises financeiras detalhadas.

**Funcionalidades**:
- **Dashboard de insights completo**:
  - Valor restante do mês
  - Alertas financeiros importantes
  - Análise de gastos por categoria
  - Sugestões de otimização
  - Comparativo mensal
- **Análise de tendências**:
  - Crescimento/redução de gastos
  - Padrões de consumo
  - Sazonalidades
- **Alertas inteligentes**:
  - Gastos acima da média
  - Categorias com crescimento anômalo
  - Metas não cumpridas
- **Sugestões personalizadas**:
  - Áreas para economia
  - Otimizações de gastos
  - Metas realistas
- **Métricas avançadas**:
  - Taxa de economia
  - Efficiency ratio
  - Índices de controle financeiro

**Componentes**: Sistema modular de widgets de insights.

---

### 🏷️ **Gerenciar_Transacoes.py** - Gestão Completa de Transações
**Descrição**: Interface completa para gerenciamento, categorização e organização de transações.

**Funcionalidades**:
- **Visualização dual**:
  - Transações à vista (extrato bancário)
  - Transações de crédito (fatura cartão)
- **Categorização inteligente**:
  - Sugestões de IA para categorização
  - Categorização manual individual
  - Categorização em lote
  - Correção de categorizações da IA
- **Gerenciamento de categorias**:
  - Criar categorias personalizadas
  - Editar categorias existentes
  - Remover categorias não utilizadas
- **Transações manuais**:
  - Adicionar transações em espécie
  - Editar transações manuais
  - Diferentes tipos de pagamento (PIX, débito, crédito, espécie)
- **Notas personalizadas**:
  - Adicionar descrições detalhadas
  - Editar observações
  - Marcar transações importantes
- **Sistema de exclusão**:
  - Soft delete de transações
  - Restaurar transações excluídas
  - Histórico de exclusões
- **Filtros avançados**:
  - Por período
  - Por categoria
  - Por valor
  - Por origem
- **Estatísticas detalhadas**:
  - Total de transações
  - Taxa de categorização
  - Distribuição por categoria

**Interface**: Sistema de abas com paginação e controles avançados.

---

### 👥 **Gerenciar_Usuarios.py** - Administração de Usuários
**Descrição**: Painel administrativo para gerenciamento completo de usuários (apenas admins).

**Funcionalidades**:
- **Listagem de usuários**:
  - Usuários ativos
  - Usuários inativos
  - Informações detalhadas
- **Gestão de contas**:
  - Criar novos usuários
  - Inativar usuários
  - Reativar usuários
  - Remover usuários (com cascade)
- **Controle de acesso**:
  - Alterar níveis de acesso
  - Definir permissões
  - Gerenciar roles (admin/user)
- **Informações de usuário**:
  - Data de criação
  - Último login
  - Status da conta
  - Estatísticas de uso
- **Segurança**:
  - Logs de atividade
  - Auditoria de alterações
  - Controle de sessões

**Acesso**: Restrito a administradores (richardpalmas, richardpalmas50).

---

### 🔄 **Atualizar_Dados.py** - Upload e Processamento de Arquivos
**Descrição**: Interface para importação de arquivos OFX (extratos e faturas).

**Funcionalidades**:
- **Upload de arquivos OFX**:
  - Extratos bancários
  - Faturas de cartão de crédito
  - Validação de formato
- **Processamento inteligente**:
  - Detecção automática de tipo (extrato/fatura)
  - Prevenção de duplicatas
  - Validação de dados
- **Isolamento por usuário**:
  - Dados separados por usuário
  - Controle de acesso individual
- **Feedback visual**:
  - Progresso de upload
  - Status de processamento
  - Relatório de importação
- **Histórico de importações**:
  - Arquivos processados
  - Data de importação
  - Quantidade de transações

**Segurança**: Validação rigorosa de arquivos e isolamento de dados.

---

### 📝 **Cadastro.py** - Registro de Novos Usuários
**Descrição**: Formulário seguro para criação de novas contas de usuário.

**Funcionalidades**:
- **Formulário de registro**:
  - Username único
  - Senha segura
  - Email (opcional)
  - Foto de perfil (opcional)
- **Validações rigorosas**:
  - Username disponível
  - Força da senha
  - Formato do email
- **Segurança avançada**:
  - Hash bcrypt para senhas
  - Rate limiting
  - Proteção CSRF
  - Validação de entrada
- **Upload de foto**:
  - Suporte a imagens PNG/JPG
  - Redimensionamento automático
  - Armazenamento seguro
- **Auditoria**:
  - Log de criação de contas
  - Registro de atividade

**Proteções**: Sistema completo de segurança na criação de contas.

---

### 🔒 **Security_Dashboard.py** - Dashboard de Segurança
**Descrição**: Painel de monitoramento e status de segurança do sistema (apenas admins).

**Funcionalidades**:
- **Métricas de segurança**:
  - Status do sistema
  - Usuários ativos
  - Status de autenticação
  - Isolamento de dados
- **Status de migração**:
  - Componentes migrados para Backend V2
  - Progresso das migrações
  - Componentes pendentes
- **Logs de segurança**:
  - Tentativas de acesso
  - Ações administrativas
  - Erros de sistema
- **Ações administrativas**:
  - Verificar sistema
  - Gerar relatórios
  - Status de backup
- **Monitoramento**:
  - Performance do sistema
  - Integridade dos dados
  - Status dos serviços

**Acesso**: Exclusivo para administradores do sistema.

---

## 🧩 Componentes e Serviços

### 📷 **profile_pic_component.py** - Componente de Foto de Perfil
**Funcionalidades**:
- Exibição de fotos de perfil personalizadas
- Cache otimizado de imagens
- Conversão automática para base64
- Redimensionamento dinâmico
- Integração com boas-vindas

### 📊 **insights_dashboard.py** - Dashboard de Insights Modular
**Componentes**:
- Widget de valor restante mensal
- Alertas financeiros
- Análise de gastos por categoria
- Sugestões de otimização
- Comparativo mensal

### 🤖 **ai_assistant_service.py** - Serviço de Assistente IA
**Funcionalidades**:
- Processamento de linguagem natural
- Análise contextual de perguntas
- Geração de respostas inteligentes
- Integração com dados financeiros
- Cache de respostas otimizado

### 🏷️ **ai_categorization_service.py** - Categorização Inteligente
**Funcionalidades**:
- Categorização automática de transações
- Aprendizado baseado em histórico
- Cache de categorizações
- Melhoria contínua de precisão
- Sugestões contextualizadas

### 💾 **transacao_service_v2.py** - Serviço de Transações
**Operações**:
- CRUD completo de transações
- Cálculos de saldos por origem
- Processamento de arquivos OFX
- Aplicação de regras de negócio
- Migração de dados legados

### 📈 **insights_service_v2.py** - Serviço de Insights
**Análises**:
- Cálculo de valor restante mensal
- Detecção de alertas financeiros
- Análise de gastos por categoria
- Geração de sugestões
- Comparativos temporais

---

## 🔐 Sistema de Segurança

### 🛡️ **Autenticação e Autorização**
- **Hash bcrypt** para senhas
- **JWT tokens** para sessões
- **Rate limiting** contra ataques
- **Dois níveis de acesso**: admin e user
- **Isolamento completo** de dados por usuário

### 🔒 **Proteções Implementadas**
- **Proteção CSRF** em formulários
- **Validação rigorosa** de entrada
- **Headers de segurança** HTTP
- **Auditoria completa** de ações
- **Logs de segurança** detalhados

### 🏗️ **Arquitetura Segura**
- **Backend V2** com padrão Repository
- **Transações de banco** atômicas
- **Soft delete** para dados sensíveis
- **Criptografia** de dados sensíveis
- **Backup automático** do banco

---

## 🎨 Interface de Usuário

### 🖥️ **Design System**
- **Tema moderno** com gradientes
- **Cards visuais** para métricas
- **Ícones consistentes** (emojis)
- **Cores temáticas**:
  - Verde: receitas/positivo
  - Vermelho: despesas/negativo
  - Azul: neutro/informação
  - Amarelo: alertas/avisos

### 📱 **Responsividade**
- **Layout fluido** com colunas dinâmicas
- **Componentes adaptáveis** ao tamanho da tela
- **Sidebars colapsáveis**
- **Tabelas responsivas**

### 🎯 **UX/UI Features**
- **Loading states** em operações longas
- **Feedback visual** imediato
- **Tooltips explicativos**
- **Mensagens de erro** claras
- **Confirmações** para ações críticas

---

## 📊 Métricas e Analytics

### 📈 **Métricas Financeiras**
- **Saldo total** por origem (extrato/cartão)
- **Receitas vs Despesas** por período
- **Ticket médio** de gastos
- **Taxa de economia** mensal
- **Distribuição por categoria**

### 🤖 **Métricas de IA**
- **Taxa de precisão** da categorização
- **Transações categorizadas** automaticamente
- **Performance do aprendizado**
- **Sugestões aceitas** pelo usuário
- **Tempo de resposta** do assistente

### 📊 **Métricas de Sistema**
- **Usuários ativos** por período
- **Transações processadas**
- **Arquivos importados**
- **Tempo de resposta** das páginas
- **Uso de cache** e otimizações

---

## 🚀 Tecnologias e Dependências

### 🐍 **Stack Principal**
- **Python 3.11+** - Linguagem base
- **Streamlit** - Framework web
- **SQLite** - Banco de dados
- **Pandas** - Manipulação de dados
- **Plotly** - Gráficos interativos

### 🤖 **Inteligência Artificial**
- **OpenAI GPT** - Assistente conversacional
- **LangChain** - Framework de IA
- **Processamento de linguagem natural**

### 🔐 **Segurança**
- **bcrypt** - Hash de senhas
- **PyJWT** - Tokens JWT
- **cryptography** - Criptografia
- **bleach** - Sanitização de entrada

### 📊 **Análise e Visualização**
- **NumPy** - Computação numérica
- **Matplotlib** - Gráficos base
- **Seaborn** - Visualizações estatísticas

---

## 📁 Estrutura de Diretórios

```
Richness/
├── Home.py                     # Página principal
├── pages/                      # Páginas da aplicação
│   ├── Assistente_IA.py
│   ├── Atualizar_Dados.py
│   ├── Cadastro.py
│   ├── Cartao.py
│   ├── Gerenciar_Transacoes.py
│   ├── Gerenciar_Usuarios.py
│   ├── Insights_Financeiros.py
│   ├── Minhas_Economias.py
│   └── Security_Dashboard.py
├── componentes/                # Componentes reutilizáveis
│   ├── insights_dashboard.py
│   └── profile_pic_component.py
├── services/                   # Serviços de negócio
│   ├── ai_assistant_service.py
│   ├── ai_categorization_service.py
│   ├── insights_service_v2.py
│   ├── llm_service.py
│   └── transacao_service_v2.py
├── utils/                      # Utilitários
│   ├── auth.py
│   ├── config.py
│   ├── database_manager_v2.py
│   ├── exception_handler.py
│   ├── filtros.py
│   ├── formatacao.py
│   ├── ofx_reader.py
│   └── repositories_v2.py
├── security/                   # Módulos de segurança
│   ├── auth/
│   ├── middleware/
│   └── validation/
├── profile_pics/              # Fotos de perfil
├── user_data/                 # Dados isolados por usuário
├── backups/                   # Backups automáticos
└── richness_v2.db            # Banco de dados principal
```

---

## 🔄 Fluxos de Trabalho

### 📊 **Fluxo de Análise Financeira**
1. **Upload de dados** via OFX (Atualizar_Dados.py)
2. **Processamento automático** com categorização IA
3. **Visualização** no dashboard (Home.py)
4. **Análise detalhada** por categoria (Gerenciar_Transacoes.py)
5. **Insights avançados** (Insights_Financeiros.py)
6. **Interação com IA** para consultas (Assistente_IA.py)

### 🎯 **Fluxo de Categorização**
1. **Importação** de transações não categorizadas
2. **Sugestão automática** da IA baseada em histórico
3. **Revisão manual** pelo usuário
4. **Aplicação em lote** ou individual
5. **Aprendizado contínuo** da IA
6. **Melhoria da precisão** ao longo do tempo

### 💰 **Fluxo de Gestão de Economias**
1. **Análise de saldo** positivo mensal
2. **Definição de metas** de economia
3. **Criação de compromissos** futuros
4. **Acompanhamento** de progresso
5. **Alertas** de vencimentos
6. **Análise de performance** das metas

---

## 🎯 Funcionalidades para Flutter

### 📱 **Páginas Equivalentes Recomendadas**

#### **1. SplashScreen & Authentication**
- Tela de splash com logo Richness
- Formulário de login (Home.py)
- Formulário de cadastro (Cadastro.py)
- Recuperação de senha

#### **2. Dashboard Principal**
- Cards com métricas principais
- Gráficos interativos (substituir Plotly por FL Chart)
- Lista de transações recentes
- Insights de IA resumidos

#### **3. Transações**
- Lista paginada de transações
- Filtros (período, categoria, valor)
- Categorização individual e em lote
- Adicionar transação manual
- Editar/excluir transações

#### **4. Análise Financeira**
- Gráficos de gastos por categoria
- Evolução temporal
- Comparativos mensais
- Métricas detalhadas

#### **5. Cartão de Crédito**
- Análise específica de fatura
- Gastos por categoria
- Histórico de faturas
- Alertas de limite

#### **6. Economias e Metas**
- Dashboard de economias
- Criar/editar metas
- Compromissos pendentes
- Progresso das metas

#### **7. Assistente IA (Chat)**
- Interface de chat
- Seletor de personalidade
- Histórico de conversas
- Insights rápidos

#### **8. Configurações e Perfil**
- Dados do usuário
- Foto de perfil
- Preferências
- Categorias personalizadas
- Configurações de notificação

### 🔧 **Componentes Técnicos Flutter**

#### **Widgets Personalizados**
- `MetricCard` (equivalente aos cards de métricas)
- `TransactionTile` (item de transação)
- `CategoryChip` (chip de categoria)
- `InsightWidget` (widget de insight)
- `ChatBubble` (mensagem do chat)

#### **Gerenciamento de Estado**
- `Provider` ou `Riverpod` para estado global
- `SharedPreferences` para dados locais
- `Dio` para requisições HTTP
- `Hive` ou `SQLite` para cache local

#### **Gráficos e Visualizações**
- `FL Chart` para gráficos (substituto do Plotly)
- `Syncfusion Charts` (alternativa premium)
- Animações customizadas para transições

#### **Segurança**
- `flutter_secure_storage` para dados sensíveis
- Biometria para autenticação
- Certificado SSL pinning
- Criptografia local de dados

### 📊 **APIs Necessárias**

#### **Autenticação**
```
POST /api/auth/login
POST /api/auth/register
POST /api/auth/refresh
POST /api/auth/logout
```

#### **Usuário**
```
GET /api/user/profile
PUT /api/user/profile
POST /api/user/avatar
```

#### **Transações**
```
GET /api/transactions
POST /api/transactions
PUT /api/transactions/{id}
DELETE /api/transactions/{id}
POST /api/transactions/upload-ofx
POST /api/transactions/categorize-batch
```

#### **Insights e IA**
```
GET /api/insights/dashboard
GET /api/insights/trends
POST /api/ai/chat
GET /api/ai/categorization-suggestions
POST /api/ai/apply-categorization
```

#### **Análises**
```
GET /api/analytics/summary
GET /api/analytics/by-category
GET /api/analytics/by-period
GET /api/analytics/credit-card
```

---

## 💡 Recomendações para Implementação Flutter

### 🎯 **Prioridades de Desenvolvimento**
1. **Autenticação e segurança** (fundamental)
2. **Dashboard principal** (engajamento)
3. **Lista de transações** (funcionalidade core)
4. **Análises básicas** (valor agregado)
5. **Assistente IA** (diferencial)
6. **Funcionalidades avançadas** (premium)

### 📱 **Adaptações Mobile**
- **Navigation bottom bar** em vez de sidebar
- **Pull-to-refresh** nas listas
- **Swipe actions** para ações rápidas
- **Modal bottom sheets** para formulários
- **Notificações push** para alertas
- **Modo offline** com sincronização

### 🎨 **Design System Mobile**
- **Material Design 3** ou **Cupertino** (iOS)
- **Paleta de cores** consistente com web
- **Tipografia** otimizada para mobile
- **Ícones** padronizados
- **Animações** fluidas e intuitivas

### 🚀 **Performance**
- **Lazy loading** de transações
- **Cache inteligente** de dados
- **Otimização de imagens**
- **Debounce** em filtros
- **Paginação** eficiente

---

## 📚 Conclusões e Próximos Passos

O **Richness** é um sistema completo e robusto de gestão financeira pessoal, com arquitetura moderna, segurança avançada e funcionalidades de IA. A documentação fornece todos os detalhes necessários para:

1. **Compreender** a arquitetura completa do sistema
2. **Mapear** todas as funcionalidades para Flutter
3. **Implementar** APIs e serviços equivalentes
4. **Manter** a consistência de features e UX
5. **Escalar** o sistema conforme necessário

A versão Flutter pode aproveitear toda a inteligência e estrutura já desenvolvida, oferecendo uma experiência mobile nativa de alta qualidade mantendo todas as funcionalidades avançadas do sistema web.

---

*© 2025 Richness - Plataforma de Gestão Financeira Pessoal*
*Documentação gerada automaticamente via análise de código*
