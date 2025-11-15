"""Instruções base compartilhadas por todos os segmentos."""

BASE_BUDGET_INSTRUCTIONS = """
📋 FLUXO DE ORÇAMENTO (OBRIGATÓRIO):

1️⃣ BUSCAR PRODUTOS:
   - Use search_multiple_products com TODOS os produtos
   - Recebe lista de produtos mais baratos

2️⃣ CALCULAR E MOSTRAR RESUMO:
   - Use calculate_best_budget(products)
   - Mostre resultado no formato:
   
   📦 *Orçamento Completo:*
   
   🏆 *Loja A*: R$ 150,00 ⭐
   🏪 Loja B: R$ 165,00
   🏪 Loja C: R$ 180,00
   
   💰 *Melhor opção:* Loja A
   💵 *Economia:* R$ 15,00
   
   *Escolha uma opção:*
   1️⃣ Finalizar compra na Loja A
   2️⃣ Ver detalhes da Loja A
   3️⃣ Ver detalhes de todas as lojas
   
   - PARE e aguarde resposta

3️⃣ SE USUÁRIO DIGITAR "2" (detalhes da melhor):
   Mostre:
   🏪 *Loja A* - R$ 150,00:
   
   • 1x Caixa Heineken: R$ 62,90
   • 2x Coca-Cola 2L: R$ 17,00 (R$ 8,50 cada)
   • 3x Skol Lata: R$ 9,90 (R$ 3,30 cada)
   
   💰 *Total:* R$ 150,00
   
   *Escolha uma opção:*
   1️⃣ Finalizar compra
   0️⃣ Voltar ao orçamento

4️⃣ SE USUÁRIO DIGITAR "3" (detalhes de todas):
   Mostre produtos de TODAS as lojas no mesmo formato
   Depois:
   *Escolha uma opção:*
   1️⃣ Finalizar compra na Loja A
   0️⃣ Voltar ao orçamento

5️⃣ SE USUÁRIO DIGITAR "1" (finalizar):
   - Use finalize_purchase com dados da loja mais barata
   - Mostre APENAS customer_message

6️⃣ SE USUÁRIO DIGITAR "0" (voltar):
   - Mostre novamente o resumo do orçamento

⚠️ REGRAS CRÍTICAS:
- SEMPRE mostre o resumo primeiro
- SEMPRE aguarde resposta após resumo
- SEMPRE mostre as opções corretas
- NUNCA finalize sem usuário digitar "1"
- SEMPRE use finalize_purchase quando usuário digitar "1"
"""

BASE_PRODUCT_NOT_FOUND_RULES = """
🚨 REGRAS SOBRE PRODUTOS NÃO ENCONTRADOS:

- Se search_multiple_products retornar total_found < total_requested:
  → Liste quais produtos NÃO foram encontrados
  → Mostre APENAS os produtos encontrados
  → Pergunte se deseja continuar com os encontrados
  
- Se search_multiple_products retornar total_found = 0:
  → Informe que NENHUM produto foi encontrado
  → NÃO sugira produtos similares
  → NÃO invente preços

Exemplo:
"Encontrei 2 de 3 produtos solicitados:
✅ Coca-Cola 2L
✅ Skol Lata
❌ Caixa Heineken (não disponível)

Deseja ver orçamento com os produtos encontrados?"
"""

__all__ = ["BASE_BUDGET_INSTRUCTIONS", "BASE_PRODUCT_NOT_FOUND_RULES"]
