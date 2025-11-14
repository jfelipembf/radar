"""Templates e formatação de mensagens interativas do chatbot."""

import urllib.parse
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.supabase_service import SupabaseService

from app.utils.formatters import _coerce_price, _format_currency, _format_date, _format_phone, _parse_created_at


def format_interactive_catalog(products: List[dict], supabase_service: "SupabaseService") -> Optional[str]:
    """
    Formata catálogo de produtos com opções interativas.

    Quando há múltiplos produtos, mostra:
    - Valor total por loja (soma de todos os produtos)
    - Loja mais barata destacada
    - Opções para escolher ação
    """
    from collections import defaultdict

    if not products:
        return "Não encontrei produtos correspondentes no catálogo. Pode tentar informar o item com outros detalhes?"

    # Agrupar produtos por loja
    store_totals = defaultdict(lambda: {"products": defaultdict(dict), "total": 0.0, "store_info": {}})

    for product in products:
        store_info = product.get("store", {})
        store_name = store_info.get("name", "Loja")
        store_phone = _format_phone(product.get("store_phone") or store_info.get("phone"))

        product_name = product.get("name", "").strip()
        if not product_name:
            continue

        price_value = _coerce_price(product.get("price"))
        if price_value <= 0:
            continue

        unit_label = product.get("unit_label", "unidade")

        # Se já temos este produto nesta loja, manter o mais barato
        if product_name not in store_totals[store_name]["products"] or \
           price_value < store_totals[store_name]["products"][product_name]["price"]:
            store_totals[store_name]["products"][product_name] = {
                "name": product_name,
                "price": price_value,
                "price_str": _format_currency(price_value),
                "unit_label": unit_label
            }

        # Atualizar informações da loja
        store_totals[store_name]["store_info"] = {
            "name": store_name,
            "phone": store_phone
        }

    # Calcular totais e converter para lista
    for store_name, store_data in store_totals.items():
        # Converter defaultdict para lista e calcular total
        products_list = list(store_data["products"].values())
        store_data["products"] = products_list
        store_data["total"] = sum(p["price"] for p in products_list)

    if not store_totals:
        return "Não há preços válidos disponíveis no momento."

    # Ordenar lojas por preço total (mais barato primeiro) e pegar apenas as 5 melhores
    sorted_stores = sorted(store_totals.items(), key=lambda x: x[1]["total"])[:5]

    # Construir mensagem
    lines = ["🏪 *ORÇAMENTO DE MATERIAIS DE CONSTRUÇÃO*", f"Encontrei as seguintes opções em {len(store_totals)} loja(s) disponível(is):"]

    for idx, (store_name, store_data) in enumerate(sorted_stores, 1):
        total = store_data["total"]
        is_cheapest = idx == 1

        lines.append("")
        lines.append(f"🏪 *{store_name}*" + (" ⭐ MAIS BARATA" if is_cheapest else ""))
        lines.append(f"� *Total estimado: {_format_currency(total)}*")

        # Remover detalhes dos produtos da mensagem inicial
        # if is_cheapest and len(sorted_stores) > 1:
        #     second_store_total = sorted_stores[1][1]["total"]
        #     savings = second_store_total - total
        #     lines.append(f"💸 *Economia: {_format_currency(savings)}* em relação à segunda opção")

    # Adicionar opções interativas
    lines.extend([
        "",
        "📋 *Opções:*",
        "1️⃣ Finalizar compra da loja mais barata",
        "2️⃣ Ver detalhes do melhor preço",
        "3️⃣ Ver detalhes de todas as lojas",
        "",
        "Digite o número da opção desejada:"
    ])

    return "\n".join(lines)


def format_purchase_summary(store_name: str, products: List[dict], customer_phone: str) -> Tuple[str, str]:
    """
    Formata mensagem de finalização de compra.

    Returns:
        Tuple[customer_message, store_message]
    """
    total = sum(_coerce_price(p.get("price", 0)) for p in products)

    # Mensagem para o cliente
    customer_lines = [
        f"✅ *Compra finalizada - {store_name}*",
        "",
        "📦 *Produtos selecionados:*"
    ]

    for product in products:
        price_str = _format_currency(_coerce_price(product.get("price", 0)))
        unit_label = product.get("unit_label", "unidade")
        customer_lines.append(f"• {product['name']}: {price_str} por {unit_label}")

    customer_lines.extend([
        "",
        f"💰 *Valor total: {_format_currency(total)}*",
        "",
        "📱 Você será direcionado para o WhatsApp da loja para finalizar a compra.",
        "Envie esta lista diretamente para a loja!"
    ])

    # Mensagem para a loja
    store_lines = [
        "🛒 *NOVA SOLICITAÇÃO DE ORÇAMENTO*",
        "",
        f"📞 *Cliente:* {customer_phone}",
        "",
        "📦 *Produtos solicitados:*"
    ]

    for product in products:
        price_str = _format_currency(_coerce_price(product.get("price", 0)))
        unit_label = product.get("unit_label", "unidade")
        store_lines.append(f"• {product['name']}: {price_str} por {unit_label}")

    store_lines.extend([
        "",
        f"💰 *Valor total estimado: {_format_currency(total)}*",
        "",
        "📱 Cliente será direcionado via WhatsApp."
    ])

    return "\n".join(customer_lines), "\n".join(store_lines)


def create_whatsapp_link(store_phone: str, message: str) -> str:
    """Cria link do WhatsApp com mensagem pré-preenchida."""
    if not store_phone:
        return ""

    # Remover caracteres não numéricos
    clean_phone = "".join(ch for ch in store_phone if ch.isdigit())

    # Codificar mensagem para URL
    encoded_message = urllib.parse.quote(message)

    return f"https://wa.me/55{clean_phone}?text={encoded_message}"


def format_best_price_details(store_data: dict) -> str:
    """Formata detalhes do melhor preço."""
    store_info = store_data["store_info"]
    products = store_data["products"]
    total = store_data["total"]

    lines = [
        f"⭐ *MELHOR PREÇO - {store_info['name']}*",
        "",
        "📦 *Produtos:*"
    ]

    for product in products:
        lines.append(f"• {product['name']}: {product['price_str']} por {product['unit_label']}")

    lines.extend([
        "",
        f"💰 *Total: {_format_currency(total)}*",
        "",
        "📱 *Contato:*",
        f"WhatsApp: {store_info['phone']}" if store_info.get('phone') else "Telefone não disponível",
        "",
        "1️⃣ Finalizar compra",
        "0️⃣ Voltar ao menu"
    ])

    return "\n".join(lines)


def format_all_stores_details(store_totals: dict) -> str:
    """Formata detalhes de todas as lojas."""
    lines = ["🏪 *TODAS AS LOJAS DISPONÍVEIS*", ""]

    # Ordenar por preço total
    sorted_stores = sorted(store_totals.items(), key=lambda x: x[1]["total"])

    for idx, (store_name, store_data) in enumerate(sorted_stores, 1):
        total = store_data["total"]
        products = store_data["products"]
        store_info = store_data["store_info"]

        lines.append(f"{idx}. *{store_name}*" + (" ⭐ MAIS BARATA" if idx == 1 else ""))

        for product in products:
            lines.append(f"   • {product['name']}: {product['price_str']} por {product['unit_label']}")

        lines.append(f"   💰 Total: {_format_currency(total)}")
        lines.append(f"   📱 WhatsApp: {store_info.get('phone', 'Não informado')}")
        lines.append("")

    lines.extend([
        "📋 *Selecione uma loja digitando o número:*",
        "(Digite 0 para voltar ao menu principal)"
    ])

    return "\n".join(lines)


def get_menu_options() -> Dict[str, str]:
    """Retorna opções do menu principal."""
    return {
        "1": "Finalizar compra da loja mais barata",
        "2": "Ver detalhes do melhor preço",
        "3": "Ver detalhes de todas as lojas"
    }


__all__ = [
    "format_interactive_catalog",
    "format_purchase_summary",
    "create_whatsapp_link",
    "format_best_price_details",
    "format_all_stores_details",
    "get_menu_options"
]
