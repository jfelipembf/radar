"""Regras de negócio específicas para materiais de construção."""

from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.openai_service import OpenAIService
    from app.services.supabase_service import SupabaseService

from app.utils.formatters import _coerce_price, _format_currency, _format_date, _format_phone, _parse_created_at
from app.utils.parsers import _extract_search_terms


async def should_search_products(message: str, openai_service: "OpenAIService") -> bool:
    """Pergunta à IA se deve buscar produtos baseado na mensagem do usuário."""
    if not openai_service:
        return False

    prompt = f"""
Você é um assistente de chatbot para uma loja de materiais de construção.

Analise a seguinte mensagem do usuário e determine se ela indica interesse em:
- Comprar ou consultar preços de materiais/produtos de construção
- Perguntar sobre disponibilidade de produtos
- Buscar informações sobre itens da loja

IMPORTANTE: Responda apenas com "SIM" ou "NAO" (sem aspas).

Mensagem do usuário: "{message}"

A mensagem indica interesse em produtos de construção?
""".strip()

    try:
        response = await openai_service.generate_response(message=prompt)
        result = response.strip().upper()
        return result == "SIM"
    except Exception:
        return False


async def extract_product_names(message: str, openai_service: "OpenAIService") -> List[str]:
    """Extrai nomes de produtos específicos mencionados na mensagem usando IA."""
    if not openai_service:
        return []

    prompt = f"""
Você é um assistente especializado em identificar produtos de construção mencionados em mensagens.

Analise a seguinte mensagem do usuário e extraia APENAS os nomes dos produtos de construção mencionados especificamente.

IMPORTANTE:
- Liste apenas produtos que são claramente mencionados
- Use nomes simples e comuns de produtos de construção
- Ignore verbos, adjetivos e outras palavras que não sejam nomes de produtos
- Se não houver produtos específicos mencionados, retorne lista vazia
- Responda apenas com uma lista separada por vírgulas, sem explicações

Exemplos:
Mensagem: "Quanto custa o cimento e a areia?"
Resposta: cimento,areia

Mensagem: "Preciso de tinta acrílica branca e tijolos"
Resposta: tinta acrílica,tijolo

Mensagem: "Oi, tudo bem?"
Resposta: (lista vazia)

Mensagem: "{message}"

Quais produtos de construção são mencionados?
""".strip()

    try:
        response = await openai_service.generate_response(message=prompt)
        result = response.strip()
        if not result or result.lower() in ['nenhum', 'vazio', 'empty', 'none', '(lista vazia)']:
            return []

        # Processar a resposta em lista
        products = [p.strip().lower() for p in result.split(',') if p.strip()]
        return products
    except Exception:
        return []


def format_product_catalog(products: List[dict], supabase_service: "SupabaseService") -> tuple[Optional[str], Optional[str]]:
    """Formata catálogo de produtos para exibição."""
    instruction_lines: List[str] = [
        "INSTRUÇÕES DE CATÁLOGO:",
        "- Utilize exclusivamente as informações listadas abaixo.",
        "- Não invente lojas, preços, telefones ou condições de entrega.",
        "- Se o item solicitado não aparecer aqui, informe ao cliente que o Supabase não retornou resultados e solicite novos detalhes.",
    ]

    from collections import defaultdict
    grouped = defaultdict(list)
    for product in products:
        name = product.get("name")
        if not name:
            continue
        grouped[name].append(product)

    if not grouped:
        instruction_lines.append("")
        instruction_lines.append("Nenhum produto correspondente foi encontrado no Supabase para esta consulta.")
        user_message = (
            "Não encontrei produtos correspondentes no catálogo do Supabase para essa descrição. "
            "Pode tentar informar o item com outros detalhes (ex.: nome completo, marca, unidade)?"
        )
        return "\n".join(instruction_lines), user_message

    instruction_lines.append("")
    instruction_lines.append("CATÁLOGO SUPABASE (ordenado por preço crescente por produto):")

    user_lines: List[str] = [
        "Encontrei as seguintes ofertas no catálogo do Supabase:",
    ]

    for product_name in sorted(grouped.keys()):
        instruction_lines.append("")
        instruction_lines.append(f"Produto: {product_name}")

        entries = []
        for product in grouped[product_name]:
            store_info = product.get("store") or {}
            store_name = store_info.get("name") or "Loja"
            phone = _format_phone(product.get("store_phone") or store_info.get("phone"))
            price_value = _coerce_price(product.get("price"))
            price_str = _format_currency(price_value)
            unit_label = product.get("unit_label") or "unidade"
            updated_at = _parse_created_at(product.get("updated_at"))
            updated_str = _format_date(updated_at)
            delivery = product.get("delivery_info") or "Entrega a combinar"

            entries.append({
                "store_name": store_name,
                "phone": phone,
                "price": price_value,
                "price_str": price_str,
                "unit_label": unit_label,
                "updated": updated_str,
                "delivery": delivery,
            })

        entries = [entry for entry in entries if entry["price"] > 0]
        if not entries:
            continue

        entries.sort(key=lambda item: item["price"])

        user_lines.append("")
        user_lines.append(f"Produto: {product_name}")

        for index, entry in enumerate(entries):
            highlight = " ← melhor preço" if index == 0 else ""
            phone_part = f" (WhatsApp: {entry['phone']})" if entry["phone"] else ""
            instruction_lines.append(
                f"• {entry['store_name']}{phone_part}: {entry['price_str']} por {entry['unit_label']} | atual. {entry['updated']} | frete: {entry['delivery']}{highlight}"
            )
            user_lines.append(
                f"  • {entry['store_name']}: {entry['price_str']} por {entry['unit_label']} (atualizado {entry['updated']}){highlight}"
            )

        if len(entries) > 1:
            economy = entries[1]["price"] - entries[0]["price"]
            if economy > 0:
                user_lines.append(
                    f"  Economia aproximada em relação à segunda opção: {_format_currency(economy)}"
                )

    if not user_lines or len(user_lines) == 1:
        return "\n".join(instruction_lines), None

    model_context = "\n".join(instruction_lines)
    user_message = "\n".join(user_lines)
    return model_context, user_message


__all__ = [
    "should_search_products",
    "extract_product_names",
    "format_product_catalog",
]
