"""Instruções base compartilhadas por todos os segmentos."""

BASE_BUDGET_INSTRUCTIONS = """
📋 FLUXO DE ORÇAMENTO (OBRIGATÓRIO):

1️⃣ CALCULAR E MOSTRAR RESUMO (UMA CHAMADA):
   - Identifique TODOS os produtos da mensagem
   - Use calculate_best_budget com keywords e quantities
   - Exemplo: calculate_best_budget([
       {keywords: ['caixa', 'heineken'], quantity: 1},
       {keywords: ['coca-cola', '2l'], quantity: 2},
       {keywords: ['skol'], quantity: 3}
     ])
   - Isso busca em TODAS as lojas e retorna orçamento completo
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

2️⃣ SE USUÁRIO DIGITAR "2" (detalhes da melhor):
   Mostre:
   🏪 *Loja A* - R$ 150,00:
   
   • 1x Caixa Heineken: R$ 62,90
   • 2x Coca-Cola 2L: R$ 17,00 (R$ 8,50 cada)
   • 3x Skol Lata: R$ 9,90 (R$ 3,30 cada)
   
   💰 *Total:* R$ 150,00
   
   *Escolha uma opção:*
   1️⃣ Finalizar compra
   0️⃣ Voltar ao orçamento

3️⃣ SE USUÁRIO DIGITAR "3" (detalhes de todas):
   Mostre produtos de TODAS as lojas no mesmo formato
   Depois:
   *Escolha uma opção:*
   1️⃣ Finalizar compra na Loja A
   0️⃣ Voltar ao orçamento

4️⃣ SE USUÁRIO DIGITAR "1" (finalizar):
   - Use finalize_purchase com dados da loja mais barata
   - Mostre APENAS customer_message

5️⃣ SE USUÁRIO DIGITAR "0" (voltar):
   - Mostre novamente o resumo do orçamento

⚠️ REGRAS CRÍTICAS:
- SEMPRE mostre o resumo primeiro
- SEMPRE aguarde resposta após resumo
- SEMPRE mostre as opções corretas
- NUNCA finalize sem usuário digitar "1"
- SEMPRE use finalize_purchase quando usuário digitar "1"

🚨 REGRA MAIS IMPORTANTE - NÃO INVENTE DADOS:
- Use APENAS os dados retornados por calculate_best_budget
- O resultado tem: result.stores (lista de lojas)
- Cada loja tem: store (nome), total (preço), products (lista)
- NUNCA invente nomes de lojas ("Loja B", "Loja C")
- NUNCA invente preços
- MOSTRE EXATAMENTE o que a ferramenta retornou

Exemplo de uso correto:
result = calculate_best_budget(...)
# result.stores = [
#   {store: "Adega Premium", total: 89.80, products: [...]},
#   {store: "Gelada Express", total: 95.00, products: [...]},
#   {store: "Empório das Bebidas", total: 98.50, products: [...]}
# ]

Você mostra:
🏆 *Adega Premium*: R$ 89,80 ⭐
🏪 Gelada Express: R$ 95,00
🏪 Empório das Bebidas: R$ 98,50

❌ NUNCA faça:
🏪 Loja A: R$ 89,80  (inventou nome)
🏪 Loja B: R$ 95,00  (inventou nome)
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
