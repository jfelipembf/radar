# 🔄 FLUXO COMPLETO DE INTERAÇÃO

## 📊 **DIAGRAMA DE ESTADOS**

```
┌─────────────────┐
│  INÍCIO         │
│  (Nova mensagem)│
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│  FASE 1: ORÇAMENTO          │
│  - IA chama calculate_best  │
│  - Mostra todas as lojas    │
│  - Opções: 1, 2, 3          │
└────┬────────────┬───────┬───┘
     │            │       │
  "1"│         "2"│    "3"│
     │            │       │
     ▼            ▼       ▼
┌─────────┐  ┌────────┐  ┌──────────┐
│ FASE 3  │  │FASE 2A │  │ FASE 2B  │
│FINALIZAR│  │DETALHES│  │DETALHES  │
│         │  │MELHOR  │  │TODAS     │
└─────────┘  └───┬────┘  └────┬─────┘
                 │            │
              "1"│ "0"     "1"│ "0"
                 │   │        │   │
                 ▼   │        ▼   │
            ┌─────────┴────────────┘
            │
            ▼
       ┌─────────┐
       │ VOLTAR  │
       │ FASE 1  │
       └─────────┘
```

---

## 💬 **MENSAGENS POR FASE**

### **FASE 1: Orçamento Inicial**

**Input do usuário:**
```
"quero 1 caixa heineken, 2 coca 2L, 3 skol"
```

**Output do bot:**
```
📦 *Orçamento Completo:*

🏆 *Adega Premium*: R$ 89,80 ⭐
🏪 Gelada Express: R$ 95,00
🏪 Empório das Bebidas: R$ 98,50

💰 *Melhor opção:* Adega Premium
💵 *Economia:* R$ 5,20

*Escolha uma opção:*
1️⃣ Finalizar compra na Adega Premium
2️⃣ Ver detalhes da Adega Premium
3️⃣ Ver detalhes de todas as lojas
```

**Estado salvo:**
- `budget_data`: resultado completo de `calculate_best_budget`
- `phase`: "budget_shown"
- `timestamp`: now()

---

### **FASE 2A: Detalhes da Melhor Loja**

**Input do usuário:**
```
"2"
```

**Output do bot:**
```
🏪 *Adega Premium* - R$ 89,80:

• 1x Caixa Heineken Lata 12un: R$ 62,90
• 2x Coca-Cola 2L: R$ 17,00 (R$ 8,50 cada)
• 3x Cerveja Skol Lata: R$ 9,90 (R$ 3,30 cada)

💰 *Total:* R$ 89,80

*Escolha uma opção:*
1️⃣ Finalizar compra
0️⃣ Voltar ao orçamento
```

**Estado atualizado:**
- `phase`: "details_shown"
- `timestamp`: now()

---

### **FASE 2B: Detalhes de Todas as Lojas**

**Input do usuário:**
```
"3"
```

**Output do bot:**
```
📋 *Detalhes de Todas as Lojas:*

🏪 *Adega Premium* - R$ 89,80:
• 1x Caixa Heineken Lata 12un: R$ 62,90
• 2x Coca-Cola 2L: R$ 17,00 (R$ 8,50 cada)
• 3x Cerveja Skol Lata: R$ 9,90 (R$ 3,30 cada)

──────────────────────────────

🏪 *Gelada Express* - R$ 95,00:
• 1x Caixa Heineken Lata 12un: R$ 65,00
• 2x Coca-Cola 2L: R$ 17,80 (R$ 8,90 cada)
• 3x Cerveja Skol Lata: R$ 10,20 (R$ 3,40 cada)

──────────────────────────────

🏪 *Empório das Bebidas* - R$ 98,50:
• 1x Caixa Heineken Lata 12un: R$ 67,90
• 2x Coca-Cola 2L: R$ 18,40 (R$ 9,20 cada)
• 3x Cerveja Skol Lata: R$ 10,50 (R$ 3,50 cada)

──────────────────────────────

*Escolha uma opção:*
1️⃣ Finalizar compra na Adega Premium
0️⃣ Voltar ao orçamento
```

**Estado atualizado:**
- `phase`: "all_details_shown"
- `timestamp`: now()

---

### **FASE 3: Finalização**

**Input do usuário:**
```
"1"
```

**Output do bot:**
```
✅ *Pedido Confirmado!*

📦 *Resumo do Pedido:*
🏪 Loja: Adega Premium
💰 Total: R$ 89,80

📋 *Produtos:*
• 1x Caixa Heineken Lata 12un: R$ 62,90
• 2x Coca-Cola 2L: R$ 17,00
• 3x Cerveja Skol Lata: R$ 9,90

📞 *Próximos Passos:*
A loja Adega Premium receberá seu pedido e entrará em contato para confirmar a entrega.

Obrigado pela preferência! 🎉
```

**Estado limpo:**
- Estado removido da memória
- Conversa finalizada

---

### **FASE 0: Voltar ao Orçamento**

**Input do usuário:**
```
"0"
```

**Output do bot:**
```
📦 *Orçamento Completo:*

🏆 *Adega Premium*: R$ 89,80 ⭐
🏪 Gelada Express: R$ 95,00
🏪 Empório das Bebidas: R$ 98,50

💰 *Melhor opção:* Adega Premium
💵 *Economia:* R$ 5,20

*Escolha uma opção:*
1️⃣ Finalizar compra na Adega Premium
2️⃣ Ver detalhes da Adega Premium
3️⃣ Ver detalhes de todas as lojas
```

**Estado atualizado:**
- `phase`: "budget_shown"
- `timestamp`: now()

---

## 🎯 **LÓGICA DE DETECÇÃO**

### **Como detectar se é opção ou nova solicitação:**

```python
from app.utils.conversation_state import ConversationState

# Verificar se é opção
option = ConversationState.is_option_response(user_message)

if option:
    # É uma resposta de opção (1, 2, 3, 0)
    budget = ConversationState.get_budget(user_id)
    
    if option == "1":
        # Finalizar compra
        finalize_purchase(...)
    elif option == "2":
        # Mostrar detalhes da melhor
        format_option_2_response(budget)
    elif option == "3":
        # Mostrar detalhes de todas
        format_option_3_response(budget)
    elif option == "0":
        # Voltar ao orçamento
        format_option_0_response(budget)
else:
    # É uma nova solicitação
    # Processar normalmente com calculate_best_budget
    ...
```

---

## ⏱️ **EXPIRAÇÃO DE ESTADO**

- **Tempo de vida:** 30 minutos
- **Após expiração:** Estado é limpo automaticamente
- **Nova mensagem:** Inicia novo orçamento

---

## 🔄 **FLUXO COMPLETO EXEMPLO**

```
Usuário: "quero cerveja"
Bot: [FASE 1] Orçamento com opções 1, 2, 3

Usuário: "3"
Bot: [FASE 2B] Detalhes de todas com opções 1, 0

Usuário: "0"
Bot: [FASE 1] Volta ao orçamento com opções 1, 2, 3

Usuário: "2"
Bot: [FASE 2A] Detalhes da melhor com opções 1, 0

Usuário: "1"
Bot: [FASE 3] Finalização + limpa estado

Usuário: "quero coca"
Bot: [FASE 1] Novo orçamento (estado limpo)
```

---

## 📝 **IMPLEMENTAÇÃO ATUAL**

### **✅ Já Implementado:**
- `ConversationState` - Gerenciamento de estado
- `format_option_2_response()` - Formatação opção 2
- `format_option_3_response()` - Formatação opção 3
- `format_option_0_response()` - Formatação opção 0
- Instruções no prompt sobre detecção de opções

### **🔄 Próximos Passos:**
1. Integrar `ConversationState` no `BaseChatbotService`
2. Adicionar lógica de detecção de opções no `process_message`
3. Atualizar prompt da IA para usar formatadores
4. Testar fluxo completo

---

## 🎯 **BENEFÍCIOS**

- ✅ Usuário pode explorar opções antes de finalizar
- ✅ Usuário pode comparar lojas
- ✅ Usuário pode voltar atrás
- ✅ Fluxo intuitivo e natural
- ✅ Estado gerenciado automaticamente
- ✅ Expiração automática após 30min
