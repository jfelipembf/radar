"""Regras de negócio específicas para materiais de construção."""

import logging

from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.openai_service import OpenAIService
    from app.services.supabase_service import SupabaseService

from app.business.message_templates import format_interactive_catalog

logger = logging.getLogger(__name__)


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
    """Extrai nomes de produtos específicos mencionados na mensagem usando IA melhorada."""
    if not openai_service:
        return []

    prompt = f"""
Você é um assistente especializado em identificar produtos de construção mencionados em mensagens.

Analise a seguinte mensagem do usuário e extraia APENAS os nomes dos produtos de construção mencionados especificamente.

IMPORTANTE:
- Liste apenas produtos que são claramente mencionados
- Use nomes simples e comuns de produtos de construção
- Corrija automaticamente erros de digitação comuns
- Ignore verbos, adjetivos e outras palavras que não sejam nomes de produtos
- Se não houver produtos específicos mencionados, retorne lista vazia
- Responda apenas com uma lista separada por vírgulas, sem explicações

EXEMPLOS DE CORREÇÃO:
- "caida dagua" → "caixa d'água"
- "cimento" → "cimento"
- "tinta" → "tinta"
- "massa acrilica" → "massa acrílica"
- "areia" → "areia"
- "tijolo" → "tijolo"
- "argamassa" → "argamassa"

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
    """Formata catálogo de produtos para exibição com opções interativas."""
    instruction_lines: List[str] = [
        "INSTRUÇÕES DE CATÁLOGO:",
        "- Utilize exclusivamente as informações listadas abaixo.",
        "- Não invente lojas, preços, telefones ou condições de entrega.",
        "- Se o item solicitado não aparecer aqui, informe ao cliente que o Supabase não retornou resultados e solicite novos detalhes.",
    ]

    # Usar o novo template interativo
    user_message = format_interactive_catalog(products, supabase_service)

    if not user_message:
        instruction_lines.append("")
        instruction_lines.append("Nenhum produto correspondente foi encontrado no Supabase para esta consulta.")
        user_message = (
            "Não encontrei produtos correspondentes no catálogo do Supabase para essa descrição. "
            "Pode tentar informar o item com outros detalhes (ex.: nome completo, marca, unidade)?"
        )
        return "\n".join(instruction_lines), user_message

    # Para o contexto do modelo, manter informações básicas
    instruction_lines.append("")
    instruction_lines.append("CATÁLOGO INTERATIVO - O usuário pode escolher opções 1, 2 ou 3.")

    model_context = "\n".join(instruction_lines)
    return model_context, user_message


async def analyze_product_variations(products: List[Dict[str, Any]], openai_service) -> Dict[str, Any]:
    """Analisa variações dos produtos encontrados com abordagem híbrida: determinística + IA."""

    if not products or len(products) <= 1:
        return {"needs_clarification": False, "variations": {}, "message": ""}

    # ABORDAGEM HÍBRIDA: Primeiro análise determinística, depois IA se necessário
    product_groups = {}

    # 1. AGRUPAR PRODUTOS DETERMINISTICAMENTE
    for product in products:
        name = product.get("name", "").lower()

        # Identificar categoria principal (lógica determinística)
        category = "outros"
        if any(term in name for term in ["caixa d", "caixa d'água", "caixa dagua"]):
            category = "caixa_dagua"
        elif "cimento" in name:
            category = "cimento"
        elif any(term in name for term in ["verniz", "tinta"]):
            category = "verniz"
        elif any(term in name for term in ["massa acrílica", "massa acrilica"]):
            category = "massa_acrilica"
        elif "massa corrida" in name:
            category = "massa_corrida"
        elif "areia" in name:
            category = "areia"

        if category not in product_groups:
            product_groups[category] = []
        product_groups[category].append(product)

    # 2. ANALISAR VARIAÇÕES POR CATEGORIA
    variations_found = {}
    for category, group_products in product_groups.items():
        if len(group_products) <= 1:
            continue

        volumes = set()
        tipos = set()

        for product in group_products:
            name = product.get("name", "").lower()

            # Extrair volumes (para caixas d'água, tintas, massas)
            import re
            volume_match = re.search(r'(\d+)\s*(l|m³|m3|kg)', name)
            if volume_match:
                volume_num = volume_match.group(1)
                unit = volume_match.group(2)
                if unit in ['l', 'm³', 'm3'] and int(volume_num) > 50:
                    volumes.add(f"{volume_num}{unit}")
                elif unit == 'kg' and int(volume_num) > 1:
                    volumes.add(f"{volume_num}{unit}")

            # Extrair tipos específicos
            if "cp-ii" in name:
                tipos.add("CP-II")
            elif "cp-iii" in name:
                tipos.add("CP-III")
            elif "cp-v" in name:
                tipos.add("CP-V")
            elif "epóxi" in name or "epoxi" in name:
                tipos.add("Epóxi")
            elif "acrílica" in name or "acrilica" in name:
                tipos.add("Acrílica")

        # Se encontrou variações, adicionar ao resultado
        if len(volumes) > 1 or len(tipos) > 1:
            variations_found[category] = {
                "volumes": list(volumes),
                "tipos": list(tipos),
                "products": group_products
            }

    # 3. DECIDIR SE PRECISA ESCLARECER (sequencial)
    if variations_found:
        # Ordem de prioridade para esclarecimento
        priority_order = ["caixa_dagua", "cimento", "massa_acrilica", "verniz", "massa_corrida", "areia", "outros"]

        for category in priority_order:
            if category in variations_found:
                variation_info = variations_found[category]

                # Construir mensagem específica baseada na categoria
                if category == "caixa_dagua" and variation_info["volumes"]:
                    volumes_list = sorted(variation_info["volumes"])
                    message = f"Encontrei caixas d'água com diferentes capacidades: {', '.join(volumes_list)}. Qual volume você precisa?"

                elif category == "cimento" and variation_info["tipos"]:
                    tipos_list = sorted(variation_info["tipos"])
                    message = f"Temos diferentes tipos de cimento disponíveis: {', '.join(tipos_list)}. Qual você prefere?"

                elif category in ["verniz", "massa_acrilica"] and (variation_info["volumes"] or variation_info["tipos"]):
                    options = []
                    if variation_info["volumes"]:
                        options.append(f"tamanhos: {', '.join(sorted(variation_info['volumes']))}")
                    if variation_info["tipos"]:
                        options.append(f"tipos: {', '.join(sorted(variation_info['tipos']))}")
                    message = f"Encontrei {category.replace('_', ' ')} com diferentes opções: {', '.join(options)}. Qual você gostaria?"

                else:
                    # Fallback genérico
                    message = f"Encontrei variações no produto {category.replace('_', ' ')}. Poderia especificar melhor?"

                return {
                    "needs_clarification": True,
                    "variations": {category: variation_info},
                    "message": message,
                    "current_category": category,
                    "total_products": len(products)
                }

    return {"needs_clarification": False, "variations": {}, "message": ""}


async def detect_product_switch(user_message: str, conversation_history: List[Dict[str, str]], openai_service) -> Dict[str, Any]:
    """Detecta se o usuário está mudando para outro produto mencionado anteriormente usando IA."""

    if not conversation_history:
        return {"is_switching": False, "target_product": None}

    # Usar IA para analisar a conversa e detectar produtos mencionados
    prompt = f"""
Analise o histórico da conversa abaixo e determine se o usuário está mudando para outro produto que foi mencionado anteriormente.

HISTÓRICO DA CONVERSA:
{chr(10).join(f"{'Usuário' if msg.get('role') == 'user' else 'Assistente'}: {msg.get('content', '')}" for msg in conversation_history[-10:])}

MENSAGEM ATUAL DO USUÁRIO: "{user_message}"

TAREFA:
1. Identifique todos os produtos de construção mencionados no histórico
2. Determine se a mensagem atual está se referindo a um produto mencionado anteriormente
3. Se SIM, retorne o nome do produto que o usuário quer discutir agora

PRODUTOS DE CONSTRUÇÃO comuns incluem: tintas, cimentos, vernizes, argamassas, tijolos, britas, areias, caixas d'água, etc.

RESPONDA APENAS com JSON:
{{
    "is_switching": true/false,
    "target_product": "nome do produto mencionado anteriormente" ou null,
    "reasoning": "breve explicação da decisão"
}}

Se não está mudando de produto, retorne:
{{"is_switching": false, "target_product": null, "reasoning": "explicação"}}
"""

    try:
        response = await openai_service.generate_response(message=prompt)
        import json
        result = json.loads(response.strip())

        return {
            "is_switching": result.get("is_switching", False),
            "target_product": result.get("target_product"),
            "reasoning": result.get("reasoning", "")
        }

    except Exception as exc:
        logger.warning(f"Erro na detecção de troca de produto: {exc}")
        return {"is_switching": False, "target_product": None}


__all__ = [
    "should_search_products",
    "extract_product_names",
    "format_product_catalog",
    "analyze_product_variations",
    "detect_product_switch",
]
