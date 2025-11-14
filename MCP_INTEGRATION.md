# 🔌 MCP Integration - Model Context Protocol

## 📋 Visão Geral

O **MCP (Model Context Protocol)** permite que a IA acesse diretamente os dados de produtos via **function calling**, eliminando a necessidade de múltiplas funções intermediárias e regras hardcoded.

---

## 🏗️ Arquitetura

### **ANTES (Múltiplas Funções):**
```
Usuário → ChatbotService → extract_product_names()
                         → extract_product_specifications()
                         → extract_product_variations()
                         → analyze_product_variations()
                         → get_products()
                         → Resposta
```

### **DEPOIS (MCP Server):**
```
Usuário → ChatbotService → OpenAI (com MCP tools)
                         → IA decide qual tool chamar
                         → ProductMCPServer.search_products()
                         → Resposta
```

---

## 🛠️ Ferramentas Disponíveis no MCP

### 1. **search_products**
Busca produtos no catálogo.

```python
{
    "name": "search_products",
    "description": "Busca produtos no catálogo",
    "parameters": {
        "category": "cimento",           # Obrigatório
        "specification": "CP-II",        # Opcional
        "limit": 20                      # Opcional
    }
}
```

**Exemplo de uso pela IA:**
```
Usuário: "preciso de cimento CP-II"
IA chama: search_products(category="cimento", specification="CP-II")
Retorna: Lista de cimentos CP-II disponíveis
```

### 2. **get_product_variations**
Obtém variações disponíveis de uma categoria.

```python
{
    "name": "get_product_variations",
    "description": "Obtém variações disponíveis",
    "parameters": {
        "category": "cimento"            # Obrigatório
    }
}
```

**Exemplo de uso pela IA:**
```
Usuário: "quais tipos de cimento vocês têm?"
IA chama: get_product_variations(category="cimento")
Retorna: ["CP-II", "CP-III", "CP-V"]
```

### 3. **get_cheapest_product**
Retorna o produto mais barato.

```python
{
    "name": "get_cheapest_product",
    "description": "Retorna o produto mais barato",
    "parameters": {
        "category": "areia",             # Obrigatório
        "specification": "lavada"        # Opcional
    }
}
```

**Exemplo de uso pela IA:**
```
Usuário: "qual a areia lavada mais barata?"
IA chama: get_cheapest_product(category="areia", specification="lavada")
Retorna: Produto mais barato
```

---

## 🔧 Como Integrar

### 1. **Instanciar o MCP Server**

```python
from app.mcp import ProductMCPServer
from app.services.supabase_service import SupabaseService

# Criar serviços
supabase_service = SupabaseService()
mcp_server = ProductMCPServer(supabase_service)

# Obter schema das ferramentas
tools = mcp_server.get_tools_schema()
```

### 2. **Configurar OpenAI com Function Calling**

```python
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Fazer chamada com tools disponíveis
response = await client.chat.completions.create(
    model="gpt-4-turbo-preview",
    messages=[
        {"role": "system", "content": "Você é um assistente de vendas..."},
        {"role": "user", "content": "preciso de cimento CP-II"}
    ],
    tools=tools,  # MCP tools disponíveis
    tool_choice="auto"  # IA decide quando usar
)
```

### 3. **Processar Tool Calls**

```python
# Se a IA decidiu usar uma ferramenta
if response.choices[0].message.tool_calls:
    for tool_call in response.choices[0].message.tool_calls:
        # Extrair nome e argumentos
        tool_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        
        # Executar ferramenta via MCP
        result = await mcp_server.execute_tool(tool_name, arguments)
        
        # Enviar resultado de volta para a IA
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(result)
        })
    
    # IA processa o resultado e gera resposta final
    final_response = await client.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=messages
    )
```

---

## 🎯 Exemplo Completo de Conversa

### **Conversa 1: Busca Simples**

```
👤 Usuário: "preciso de cimento CP-II"

🤖 IA (internamente):
   - Detecta: categoria="cimento", especificação="CP-II"
   - Chama: search_products(category="cimento", specification="CP-II")
   - Recebe: 5 produtos encontrados
   - Chama: get_cheapest_product(category="cimento", specification="CP-II")
   - Recebe: Cimento CP-II 50kg - R$ 32.00

🤖 IA responde:
   "Encontrei Cimento CP-II 50kg por R$ 32,00 na Constrular Express. 
    Deseja adicionar ao orçamento?"
```

### **Conversa 2: Exploração de Opções**

```
👤 Usuário: "quais tipos de cimento vocês têm?"

🤖 IA (internamente):
   - Detecta: pergunta sobre variações
   - Chama: get_product_variations(category="cimento")
   - Recebe: ["CP-II", "CP-III", "CP-V"]

🤖 IA responde:
   "Temos os seguintes tipos de cimento:
    - CP-II (comum)
    - CP-III (resistente a sulfatos)
    - CP-V (alta resistência inicial)
    
    Qual você prefere?"

👤 Usuário: "CP-II"

🤖 IA (internamente):
   - Chama: get_cheapest_product(category="cimento", specification="CP-II")
   - Recebe: Cimento CP-II 50kg - R$ 32.00

🤖 IA responde:
   "Perfeito! Adicionei Cimento CP-II 50kg por R$ 32,00 ao seu orçamento."
```

### **Conversa 3: Orçamento Completo**

```
👤 Usuário: "preciso de caixa d'água 1000L, cimento e areia"

🤖 IA (internamente):
   - Detecta 3 produtos
   - Chama: search_products(category="caixa d'água", specification="1000L")
   - Chama: get_product_variations(category="cimento")
   - Chama: get_product_variations(category="areia")

🤖 IA responde:
   "✅ Caixa d'água 1000L - R$ 629,00 (adicionado)
    
    Para o cimento, temos:
    - CP-II
    - CP-III
    - CP-V
    Qual você prefere?"

👤 Usuário: "CP-II"

🤖 IA (internamente):
   - Chama: get_cheapest_product(category="cimento", specification="CP-II")

🤖 IA responde:
   "✅ Cimento CP-II - R$ 32,00 (adicionado)
    
    Para a areia, temos:
    - Lavada
    - Grossa
    - Fina
    Qual você prefere?"

👤 Usuário: "lavada"

🤖 IA (internamente):
   - Chama: get_cheapest_product(category="areia", specification="lavada")

🤖 IA responde:
   "✅ Areia Lavada - R$ 150,00 (adicionado)
    
    🏪 ORÇAMENTO COMPLETO
    Total: R$ 811,00
    
    1️⃣ Finalizar compra
    2️⃣ Ver detalhes
    3️⃣ Modificar produtos"
```

---

## 🚀 Vantagens do MCP

### 1. **Menos Código**
```python
# ANTES: 5+ funções específicas
extract_product_names()
extract_product_specifications()
extract_product_variations()
analyze_product_variations()
get_products()

# DEPOIS: 1 MCP Server
mcp_server.execute_tool(tool_name, arguments)
```

### 2. **IA Decide**
```python
# ANTES: Código decide o fluxo
if has_specification:
    search_with_filter()
else:
    ask_for_specification()

# DEPOIS: IA decide
# IA analisa contexto e chama a ferramenta apropriada
```

### 3. **Flexível**
```python
# ANTES: Hardcoded para cada produto
if "cimento" in message:
    handle_cement()
elif "areia" in message:
    handle_sand()

# DEPOIS: Genérico
# IA usa as mesmas ferramentas para qualquer produto
```

### 4. **Manutenível**
```python
# ANTES: Adicionar novo produto = novo código
def handle_new_product():
    # Mais 50 linhas de código

# DEPOIS: Adicionar novo produto = zero código
# MCP já suporta automaticamente
```

---

## 📊 Comparação

| Aspecto | Sem MCP | Com MCP |
|---------|---------|---------|
| **Funções necessárias** | 5-10 | 3 (tools) |
| **Linhas de código** | ~500 | ~200 |
| **Lógica hardcoded** | Muita | Nenhuma |
| **Flexibilidade** | Baixa | Alta |
| **Manutenção** | Difícil | Fácil |
| **Novos produtos** | Código novo | Automático |
| **IA decide** | Não | Sim |

---

## 🔄 Próximos Passos

### 1. **Integrar MCP no ChatbotService**
```python
# Em chatbot_service.py
from app.mcp import ProductMCPServer

class ChatbotService:
    def __init__(self, ...):
        self.mcp_server = ProductMCPServer(supabase_service)
        self.tools = self.mcp_server.get_tools_schema()
```

### 2. **Usar Function Calling**
```python
# Fazer chamadas com tools
response = await openai_service.chat_with_tools(
    messages=conversation_history,
    tools=self.tools
)
```

### 3. **Processar Tool Calls**
```python
# Se IA usou ferramentas
if response.tool_calls:
    for tool_call in response.tool_calls:
        result = await self.mcp_server.execute_tool(
            tool_call.name,
            tool_call.arguments
        )
```

---

## 🎯 Resultado Final

**Sistema totalmente orientado por IA:**
- ✅ IA decide quando buscar produtos
- ✅ IA decide quais filtros aplicar
- ✅ IA decide quando perguntar ao usuário
- ✅ IA decide como formatar a resposta
- ✅ Zero lógica hardcoded
- ✅ Funciona com qualquer produto

**Você só precisa:**
1. Definir as ferramentas (tools)
2. Deixar a IA decidir tudo
3. Executar o que a IA pedir

🎉 **Sistema verdadeiramente inteligente e autônomo!**
