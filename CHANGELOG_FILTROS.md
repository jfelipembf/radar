# Correção: Sistema de Filtros Diretos para Busca de Produtos

## 📋 Problema Identificado

O sistema **não estava aplicando filtros diretos** quando o usuário especificava produtos com detalhes na mensagem original.

### Exemplo do Problema

**Mensagem do usuário:**
```
"preciso de uma orcamento para ua caida dagua, de mil litros, 2 sacos de cimento e 5m3 de areia"
```

**Comportamento Anterior:**
- Sistema detectava "mil litros" mas não buscava diretamente produtos com essa especificação
- Fazia busca genérica e depois perguntava ao usuário sobre detalhes já fornecidos
- Resultado: **Areia lavada** era o único produto retornado, ignorando caixa d'água e cimento

**Comportamento Esperado:**
- Detectar especificações na mensagem original (1000L, CP-II, lavada, etc.)
- Aplicar filtros diretos na busca de produtos
- Adicionar produtos especificados automaticamente ao orçamento
- Perguntar apenas sobre produtos que realmente precisam esclarecimento

---

## ✅ Correções Implementadas

### 1. **Melhorias no `supabase_service.py`**

#### Adicionado parâmetro `exact_filters` na função `get_products()`

```python
def get_products(
    self,
    segment: Optional[str] = None,
    search_terms: Optional[List[str]] = None,
    limit: int = 50,
    exact_filters: Optional[Dict[str, str]] = None,  # NOVO
) -> List[Dict[str, Any]]:
```

**Funcionalidade:**
- Permite aplicar filtros exatos (ex: `{'specification': '1000L'}`)
- Filtra produtos por nome E descrição
- Busca mais produtos (limit * 3) para garantir resultados após filtros

**Exemplo de uso:**
```python
products = get_products(
    "material_construcao",
    ["caixa d'água"],
    20,
    {"specification": "1000L"}  # Filtra apenas caixas de 1000L
)
```

---

### 2. **Refatoração do `chatbot_service.py` - `build_product_context()`**

#### A. Detecção Melhorada de Especificações

**Antes:**
```python
if "caixa" in search_lower:
    if "1000" in search_lower or "mil" in search_lower:
        specified_products["caixa_dágua"] = "1000L"
```

**Depois:**
```python
if any(term in search_lower for term in ["caixa", "caida"]):  # Corrige erros de digitação
    if "1000" in search_lower or "mil" in search_lower or "1.000" in search_lower:
        specified_products["caixa d'água"] = "1000L"
```

**Melhorias:**
- Detecta variações de escrita ("caida dagua" → "caixa d'água")
- Suporta números formatados ("1.000" ou "mil")
- Detecta tipos de cimento (CP-II, CP-III, CP-V)
- Detecta tipos de areia (lavada, grossa, fina)

#### B. Busca com Filtros Aplicados Diretamente

**Antes:**
```python
# Busca genérica
products = get_products("material_construcao", product_names, 40)
# Depois filtrava em Python
```

**Depois:**
```python
for product_name in product_names:
    exact_filter = None
    
    # Procurar especificação correspondente
    for spec_key, spec_value in specified_products.items():
        if spec_key in product_name:
            exact_filter = {"specification": spec_value}
    
    # Buscar com filtro aplicado
    found_products = get_products(
        "material_construcao",
        [product_name],
        20,
        exact_filter  # Filtro aplicado na busca
    )
```

**Vantagens:**
- Busca mais precisa desde o início
- Reduz produtos irrelevantes retornados
- Melhora performance

#### C. Agrupamento Inteligente por Categoria

**Nova lógica:**
```python
# Agrupar produtos por categoria
products_by_category = {}
for product in unique_products:
    if "caixa" in product_name_lower:
        category = "caixa d'água"
    elif "cimento" in product_name_lower:
        category = "cimento"
    elif "areia" in product_name_lower:
        category = "areia"
    
    products_by_category[category].append(product)
```

**Benefícios:**
- Organiza produtos por tipo
- Facilita seleção automática de produtos especificados
- Identifica rapidamente o que precisa esclarecimento

#### D. Seleção Automática de Produtos Especificados

**Nova lógica:**
```python
for category, specification in specified_products.items():
    if category in products_by_category:
        # Filtrar produtos que contenham a especificação
        matching_products = [
            p for p in category_products
            if specification.lower() in p.get("name", "").lower()
        ]
        
        if matching_products:
            # Pegar o mais barato e adicionar automaticamente
            cheapest = min(matching_products, key=lambda x: price)
            selected_products.append({
                "type": f"{category.title()} {specification}",
                "product": cheapest,
                ...
            })
            clarified_categories.append(category)
```

**Resultado:**
- Produtos especificados são adicionados automaticamente
- Sistema só pergunta sobre produtos não especificados
- Reduz interações desnecessárias com o usuário

---

## 🎯 Fluxo Corrigido

### Exemplo: "preciso de uma orcamento para ua caida dagua, de mil litros, 2 sacos de cimento e 5m3 de areia"

**1. Detecção de Especificações:**
```
✅ Detectado: caixa d'água 1000L
❌ Cimento: não especificado (tipo CP-II, CP-III, CP-V)
❌ Areia: não especificada (lavada, grossa, fina)
```

**2. Busca com Filtros:**
```
🔍 Buscar "caixa d'água" com filtro {"specification": "1000L"}
🔍 Buscar "cimento" sem filtro (retorna todos os tipos)
🔍 Buscar "areia" sem filtro (retorna todos os tipos)
```

**3. Agrupamento:**
```
📦 Categoria "caixa d'água": 5 produtos (todos 1000L devido ao filtro)
📦 Categoria "cimento": 15 produtos (CP-II, CP-III, CP-V)
📦 Categoria "areia": 8 produtos (lavada, grossa)
```

**4. Seleção Automática:**
```
✅ Caixa d'água 1000L → Produto mais barato adicionado automaticamente
❓ Cimento → Precisa esclarecimento (qual tipo?)
❓ Areia → Precisa esclarecimento (qual tipo?)
```

**5. Resposta ao Usuário:**
```
📋 PRODUTOS SELECIONADOS:
1. Caixa D'água 1000L
   💰 R$ 198.00 - Constrular Express

Qual tipo de cimento você precisa?
- CP-II (comum)
- CP-III (resistente)
- CP-V (alta resistência)
```

---

## 📊 Comparação: Antes vs Depois

| Aspecto | Antes | Depois |
|---------|-------|--------|
| **Detecção de especificações** | Básica, apenas alguns padrões | Avançada, múltiplas variações |
| **Busca de produtos** | Genérica, filtra depois | Com filtros aplicados diretamente |
| **Produtos retornados** | Muitos irrelevantes | Apenas relevantes |
| **Seleção automática** | Não havia | Produtos especificados adicionados automaticamente |
| **Perguntas ao usuário** | Sobre tudo, mesmo já especificado | Apenas sobre o não especificado |
| **Interações necessárias** | 3-4 perguntas | 1-2 perguntas |

---

## 🧪 Testes Recomendados

### Teste 1: Especificação Completa
```
Mensagem: "preciso de caixa dagua 1000L, cimento CP-II e areia lavada"
Esperado: Todos os produtos adicionados automaticamente, orçamento direto
```

### Teste 2: Especificação Parcial
```
Mensagem: "preciso de caixa dagua de mil litros e cimento"
Esperado: 
- Caixa d'água 1000L adicionada automaticamente
- Pergunta sobre tipo de cimento
```

### Teste 3: Sem Especificação
```
Mensagem: "preciso de caixa dagua e cimento"
Esperado: Perguntas sobre capacidade da caixa e tipo de cimento
```

### Teste 4: Erros de Digitação
```
Mensagem: "caida dagua mil litros"
Esperado: Sistema corrige e detecta "caixa d'água 1000L"
```

---

## 🚀 Próximos Passos

1. **Testar com dados reais** do Supabase
2. **Validar logs** para garantir que filtros estão sendo aplicados
3. **Ajustar detecção** se necessário para outros produtos
4. **Expandir para outros segmentos** (não apenas material de construção)

---

## 📝 Arquivos Modificados

- ✅ `/app/services/supabase_service.py` - Adicionado parâmetro `exact_filters`
- ✅ `/app/services/chatbot_service.py` - Refatorado `build_product_context()`

---

## 🔗 Referências

- Issue: Sistema não aplicava filtros diretos
- Exemplo real: Mensagem do Felipe Macedo (14/11/2025, 18:43:56)
