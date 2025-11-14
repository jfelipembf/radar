# 🔄 Fluxo de Detecção e Seleção de Produtos

## 📋 Visão Geral

O sistema agora funciona de forma **inteligente e flexível**, detectando especificações e perguntando apenas quando necessário.

---

## 🎯 Regras do Sistema

### 1. **Produto ESPECIFICADO pelo usuário**
```
Mensagem: "preciso de areia lavada"
         └─> IA detecta: {"areia": "lavada"}
         └─> Sistema busca: produtos com "lavada" no nome/descrição
         └─> Resultado: ✅ Adiciona automaticamente o mais barato
```

**Não pergunta nada** - já sabe o que o usuário quer!

---

### 2. **Produto NÃO especificado + Múltiplas variações**
```
Mensagem: "preciso de areia"
         └─> IA detecta: {"areia": null}
         └─> Sistema busca: todos os produtos de areia
         └─> Encontra: 
             • Areia Lavada - R$ 150
             • Areia Grossa - R$ 140
             • Areia Fina - R$ 145
         └─> Resultado: ❓ PERGUNTA ao usuário qual tipo
```

**Pergunta** - há variações e o usuário precisa escolher!

---

### 3. **Produto NÃO especificado + Apenas 1 variação**
```
Mensagem: "preciso de argamassa"
         └─> IA detecta: {"argamassa": null}
         └─> Sistema busca: todos os produtos de argamassa
         └─> Encontra: 
             • Argamassa AC-II 20kg - R$ 25
         └─> Resultado: ✅ Adiciona automaticamente (única opção)
```

**Não pergunta** - só tem uma opção disponível!

---

## 🔄 Fluxo Completo - Exemplo Real

### Mensagem do Usuário:
```
"preciso de uma orcamento para ua caida dagua, de mil litros, 2 sacos de cimento e 5m3 de areia"
```

### Passo 1: IA Extrai Produtos
```json
{
  "produtos_identificados": ["caixa d'água", "cimento", "areia"]
}
```

### Passo 2: IA Extrai Especificações
```json
{
  "caixa d'água": "1000L",  // ✅ Especificado
  "cimento": null,           // ❌ Não especificado
  "areia": null              // ❌ Não especificado
}
```

### Passo 3: Sistema Busca Produtos

**Caixa d'água (com filtro "1000L"):**
```
Encontrados: 5 produtos
  • Caixa D'água 1000L Fortlev - R$ 629
  • Caixa D'água 1000L Acqualimp - R$ 680
  • Caixa D'água 1000L Tigre - R$ 720
  
Ação: ✅ Adiciona o mais barato (Fortlev - R$ 629)
```

**Cimento (sem filtro):**
```
Encontrados: 15 produtos
  • Cimento CP-II 50kg - R$ 32
  • Cimento CP-III 50kg - R$ 35
  • Cimento CP-V 50kg - R$ 38
  
Ação: ❓ Adiciona para esclarecimento (múltiplas variações)
```

**Areia (sem filtro):**
```
Encontrados: 8 produtos
  • Areia Lavada m³ - R$ 150
  • Areia Grossa m³ - R$ 140
  • Areia Fina m³ - R$ 145
  
Ação: ❓ Adiciona para esclarecimento (múltiplas variações)
```

### Passo 4: Sistema Monta Resposta

**Produtos Selecionados:**
```
📋 PRODUTOS SELECIONADOS:

1. Caixa D'água 1000L
   💰 R$ 629.00 - Constrular Express

Subtotal atual: R$ 629.00
```

**IA Analisa Variações:**
```
IA detecta que há variações de:
  - Cimento (CP-II, CP-III, CP-V)
  - Areia (lavada, grossa, fina)

IA decide perguntar sobre CIMENTO primeiro
```

**Mensagem Final:**
```
📋 PRODUTOS SELECIONADOS:

1. Caixa D'água 1000L
   💰 R$ 629.00 - Constrular Express

Subtotal atual: R$ 629.00

Qual tipo de cimento você precisa?
- CP-II (comum)
- CP-III (resistente)
- CP-V (alta resistência)
```

---

## 🎯 Fluxo de Perguntas Sequenciais

### Primeira Pergunta: Cimento
```
Usuário responde: "CP-II"

Sistema:
  ✅ Adiciona: Cimento CP-II 50kg - R$ 32
  ❓ Próxima pergunta: Areia
```

### Segunda Pergunta: Areia
```
📋 PRODUTOS SELECIONADOS:

1. Caixa D'água 1000L
   💰 R$ 629.00 - Constrular Express

2. Cimento CP-II 50kg
   💰 R$ 32.00 - Constrular Express

Subtotal atual: R$ 661.00

Qual tipo de areia você precisa?
- Lavada
- Grossa
- Fina
```

### Resposta Final: Orçamento Completo
```
Usuário responde: "lavada"

Sistema:
  ✅ Adiciona: Areia Lavada m³ - R$ 150
  ✅ Todos os produtos especificados!
  ✅ Mostra orçamento completo
```

```
📋 PRODUTOS SELECIONADOS:

1. Caixa D'água 1000L
   💰 R$ 629.00 - Constrular Express

2. Cimento CP-II 50kg
   💰 R$ 32.00 - Constrular Express

3. Areia Lavada m³
   💰 R$ 150.00 - Constrular Express

Subtotal atual: R$ 811.00

ORÇAMENTO COMPLETO:

🏪 ORÇAMENTO DE MATERIAIS DE CONSTRUÇÃO
Encontrei as seguintes opções em 1 loja(s) disponível(is):

🏪 Constrular Express ⭐ MAIS BARATA
💰 Total estimado: R$ 811,00

📋 Opções:
1️⃣ Finalizar compra da loja mais barata
2️⃣ Ver detalhes do melhor preço
3️⃣ Ver detalhes de todas as lojas

Digite o número da opção desejada:
```

---

## 🧪 Casos de Teste

### Teste 1: Tudo Especificado
```
Mensagem: "caixa dagua 1000L, cimento CP-II e areia lavada"

Resultado:
  ✅ Caixa d'água 1000L → adicionado
  ✅ Cimento CP-II → adicionado
  ✅ Areia lavada → adicionado
  ✅ Orçamento completo direto (sem perguntas)
```

### Teste 2: Nada Especificado
```
Mensagem: "caixa dagua, cimento e areia"

Resultado:
  ❓ Pergunta 1: Qual capacidade da caixa d'água?
  ❓ Pergunta 2: Qual tipo de cimento?
  ❓ Pergunta 3: Qual tipo de areia?
  ✅ Orçamento completo após respostas
```

### Teste 3: Parcialmente Especificado
```
Mensagem: "caixa dagua 1000L, cimento e areia"

Resultado:
  ✅ Caixa d'água 1000L → adicionado
  ❓ Pergunta 1: Qual tipo de cimento?
  ❓ Pergunta 2: Qual tipo de areia?
  ✅ Orçamento completo após respostas
```

### Teste 4: Produto Único
```
Mensagem: "argamassa"

Resultado:
  ✅ Argamassa AC-II 20kg → adicionado (única opção)
  ✅ Orçamento completo direto (sem perguntas)
```

---

## 🚀 Vantagens do Sistema

1. ✅ **Flexível** - Funciona com qualquer produto
2. ✅ **Inteligente** - Detecta especificações automaticamente
3. ✅ **Eficiente** - Pergunta apenas quando necessário
4. ✅ **Transparente** - Mostra produtos selecionados antes de perguntar
5. ✅ **Genérico** - Não precisa código específico para cada produto

---

## 📝 Logs de Debug

O sistema agora tem logs detalhados:

```
IA - Especificações extraídas: {"caixa d'água": "1000L"}
Processando 1 especificações: ['caixa d'água']
  ✅ Match encontrado: 'caixa d'água'
  ✅ Produto especificado adicionado: caixa d'água 1000L
Categoria 'cimento' não especificada e tem 15 variações - precisa esclarecimento
Categoria 'areia' não especificada e tem 8 variações - precisa esclarecimento

RESUMO:
  Categorias esclarecidas: ['caixa d'água']
  Produtos selecionados: 1
  Produtos que precisam esclarecimento: 23
```

---

## 🎯 Próximos Passos

1. ✅ Testar com mensagem real
2. ✅ Verificar logs para confirmar detecção
3. ✅ Ajustar se necessário
