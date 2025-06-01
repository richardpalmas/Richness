# Configuração do Pluggy - Guia Completo

## 🚨 Problema Atual

O sistema está retornando erro **403 Forbidden** ao tentar acessar transações porque:

- Os item IDs cadastrados não pertencem às credenciais Pluggy atuais
- O sistema está usando credenciais de demonstração
- Os item IDs foram criados com diferentes credenciais

## 📋 Soluções

### 1. Configurar Credenciais Próprias (RECOMENDADO)

#### Passo 1: Obter Credenciais do Pluggy
1. Acesse https://dashboard.pluggy.ai
2. Crie uma conta ou faça login
3. Obtenha seu `CLIENT_ID` e `CLIENT_SECRET`

#### Passo 2: Configurar no Sistema
Edite o arquivo `.env` na raiz do projeto:

```env
PLUGGY_CLIENT_ID=seu_client_id_aqui
PLUGGY_CLIENT_SECRET=seu_client_secret_aqui
PLUGGY_API_URL=https://api.pluggy.ai
```

#### Passo 3: Conectar Contas
1. Implemente o Pluggy Connect widget
2. Conecte suas contas bancárias
3. Os item IDs serão gerados automaticamente

### 2. Implementar Pluggy Connect Widget

```javascript
// Exemplo de implementação
const connectToken = await fetch('/api/pluggy/connect-token', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' }
}).then(res => res.json());

const pluggy = new PluggyConnect({
  connectToken: connectToken.connectToken,
  onSuccess: (item) => {
    // Salvar item.id no banco de dados
    console.log('Item ID:', item.id);
  }
});
```

### 3. Verificar Item IDs Existentes

Use a página **Cadastro_Pluggy** para:
- Testar se os item IDs atuais são válidos
- Remover item IDs inválidos
- Verificar a autenticação

## 🔧 Diagnóstico

### Testando a Conexão

```python
from utils.pluggy_connector import PluggyConnector

# Testar autenticação
pluggy = PluggyConnector()
pluggy.testar_autenticacao()

# Testar item ID específico
pluggy.testar_item_id('seu-item-id-aqui')
```

### Códigos de Status Comuns

- **200**: Sucesso - tudo funcionando
- **403**: Forbidden - item ID não pertence a este cliente
- **404**: Not Found - item ID não existe
- **401**: Unauthorized - credenciais inválidas

## 📞 Próximos Passos

1. **Imediato**: Remover item IDs inválidos da página Cadastro_Pluggy
2. **Curto prazo**: Configurar credenciais próprias do Pluggy
3. **Longo prazo**: Implementar Pluggy Connect widget para conexão automática

## 🛠️ Estrutura Atual do Sistema

```
utils/config.py         # Configurações das credenciais
utils/pluggy_connector.py  # Lógica de conexão com API
pages/Cadastro_Pluggy.py   # Interface para gerenciar item IDs
Home.py                  # Página principal com transações
```

## 📚 Recursos Úteis

- [Documentação Pluggy](https://docs.pluggy.ai)
- [Dashboard Pluggy](https://dashboard.pluggy.ai)
- [Pluggy Connect Guide](https://docs.pluggy.ai/docs/pluggy-connect-introduction)
- [API Reference](https://docs.pluggy.ai/reference)
