"""Formatador de orçamentos - usado por todos os segmentos."""

from typing import Dict, List, Any


def format_budget_summary(budget_data: Dict[str, Any]) -> str:
    """
    Formata resumo do orçamento com todas as lojas.
    
    Args:
        budget_data: Resultado de calculate_best_budget
        
    Returns:
        Texto formatado do orçamento
    """
    if not budget_data.get("success"):
        return "❌ Erro ao calcular orçamento."
    
    stores = budget_data.get("stores", [])
    if not stores:
        return "❌ Nenhuma loja encontrada."
    
    cheapest = stores[0]
    
    # Cabeçalho
    lines = ["📦 *Orçamento Completo:*\n"]
    
    # Listar todas as lojas com totais
    for i, store in enumerate(stores):
        store_name = store.get("store", "Loja")
        total = store.get("total", 0)
        
        if i == 0:
            # Loja mais barata
            lines.append(f"🏆 *{store_name}*: R$ {total:.2f} ⭐")
        else:
            lines.append(f"🏪 {store_name}: R$ {total:.2f}")
    
    # Economia
    if len(stores) > 1:
        economy = stores[1]["total"] - cheapest["total"]
        lines.append(f"\n💰 *Melhor opção:* {cheapest['store']}")
        lines.append(f"💵 *Economia:* R$ {economy:.2f}\n")
    else:
        lines.append(f"\n💰 *Melhor opção:* {cheapest['store']}\n")
    
    # Opções
    lines.append("*Escolha uma opção:*")
    lines.append(f"1️⃣ Finalizar compra na {cheapest['store']}")
    lines.append(f"2️⃣ Ver detalhes da {cheapest['store']}")
    if len(stores) > 1:
        lines.append("3️⃣ Ver detalhes de todas as lojas")
    
    return "\n".join(lines)


def format_store_details(store_data: Dict[str, Any]) -> str:
    """
    Formata detalhes de uma loja específica.
    
    Args:
        store_data: Dados da loja com produtos
        
    Returns:
        Texto formatado dos detalhes
    """
    store_name = store_data.get("store", "Loja")
    total = store_data.get("total", 0)
    products = store_data.get("products", [])
    
    lines = [f"🏪 *{store_name}* - R$ {total:.2f}:\n"]
    
    for product in products:
        name = product.get("name", "Produto")
        quantity = product.get("quantity", 1)
        price = product.get("price", 0)
        subtotal = product.get("subtotal", 0)
        
        if quantity > 1:
            lines.append(f"• {quantity}x {name}: R$ {subtotal:.2f} (R$ {price:.2f} cada)")
        else:
            lines.append(f"• {name}: R$ {price:.2f}")
    
    lines.append(f"\n💰 *Total:* R$ {total:.2f}")
    
    return "\n".join(lines)


def format_all_stores_details(budget_data: Dict[str, Any]) -> str:
    """
    Formata detalhes de todas as lojas.
    
    Args:
        budget_data: Resultado de calculate_best_budget
        
    Returns:
        Texto formatado com todas as lojas
    """
    stores = budget_data.get("stores", [])
    if not stores:
        return "❌ Nenhuma loja encontrada."
    
    lines = ["📋 *Detalhes de Todas as Lojas:*\n"]
    
    for i, store in enumerate(stores):
        if i > 0:
            lines.append("\n" + "─" * 30 + "\n")
        
        lines.append(format_store_details(store))
    
    # Opções após detalhes
    cheapest = stores[0]
    lines.append("\n" + "─" * 30)
    lines.append("\n*Escolha uma opção:*")
    lines.append(f"1️⃣ Finalizar compra na {cheapest['store']}")
    lines.append("0️⃣ Voltar ao orçamento")
    
    return "\n".join(lines)


def format_option_2_response(budget_data: Dict[str, Any]) -> str:
    """
    Formata resposta para opção 2 (detalhes da loja mais barata).
    
    Args:
        budget_data: Resultado de calculate_best_budget
        
    Returns:
        Texto formatado
    """
    cheapest = budget_data.get("cheapest_store")
    if not cheapest:
        return "❌ Erro: orçamento não encontrado."
    
    lines = [format_store_details(cheapest)]
    lines.append("\n*Escolha uma opção:*")
    lines.append("1️⃣ Finalizar compra")
    lines.append("0️⃣ Voltar ao orçamento")
    
    return "\n".join(lines)


def format_option_3_response(budget_data: Dict[str, Any]) -> str:
    """
    Formata resposta para opção 3 (detalhes de todas as lojas).
    
    Args:
        budget_data: Resultado de calculate_best_budget
        
    Returns:
        Texto formatado
    """
    return format_all_stores_details(budget_data)


def format_option_0_response(budget_data: Dict[str, Any]) -> str:
    """
    Formata resposta para opção 0 (voltar ao orçamento).
    
    Args:
        budget_data: Resultado de calculate_best_budget
        
    Returns:
        Texto formatado (mesmo que resumo)
    """
    return format_budget_summary(budget_data)


def get_budget_instructions() -> str:
    """
    Retorna instruções para a IA sobre como usar o formatador.
    
    Returns:
        Texto com instruções
    """
    return """
📋 INSTRUÇÕES DE FORMATAÇÃO DE ORÇAMENTO:

Após calculate_best_budget, você DEVE:

1️⃣ MOSTRAR RESUMO (sempre):
   - Use format_budget_summary(budget_data)
   - Mostra todas as lojas com totais
   - Mostra melhor opção e economia
   - Mostra opções: 1, 2, 3
   - PARE e aguarde usuário

2️⃣ SE USUÁRIO DIGITAR "2":
   - Use format_store_details(cheapest_store)
   - Mostra produtos APENAS da loja mais barata
   - Mostra opções: 1 (finalizar), 0 (voltar)

3️⃣ SE USUÁRIO DIGITAR "3":
   - Use format_all_stores_details(budget_data)
   - Mostra produtos de TODAS as lojas
   - Mostra opções: 1 (finalizar), 0 (voltar)

4️⃣ SE USUÁRIO DIGITAR "1":
   - Use finalize_purchase com dados da loja mais barata
   - Mostre APENAS customer_message

5️⃣ SE USUÁRIO DIGITAR "0":
   - Volte ao resumo (format_budget_summary)

⚠️ IMPORTANTE:
- NUNCA formate manualmente
- SEMPRE use as funções do formatador
- SEMPRE mostre as opções corretas
- SEMPRE aguarde resposta após mostrar resumo
"""


__all__ = [
    "format_budget_summary",
    "format_store_details", 
    "format_all_stores_details",
    "format_option_2_response",
    "format_option_3_response",
    "format_option_0_response",
    "get_budget_instructions"
]
