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
    """Analisa variações dos produtos encontrados usando IA para detectar padrões dinamicamente."""

    if not products or len(products) <= 1:
        return {"needs_clarification": False, "variations": {}, "message": ""}

    # Usar IA para categorizar e analisar variações
    prompt = f"""
Você é um especialista em análise de produtos de construção. Analise a lista abaixo de produtos e:

1. AGRUPE os produtos por categoria (ex: caixas d'água, cimentos, tintas, massas, etc.)
2. Para cada categoria com múltiplos produtos, identifique se há VARIAÇÕES SIGNIFICATIVAS
3. Determine se precisa esclarecer alguma categoria (uma de cada vez, por prioridade)

LISTA DE PRODUTOS:
{chr(10).join(f"{i+1}. {p.get('name', '')} - {p.get('description', '')}" for i, p in enumerate(products))}

CRITÉRIOS PARA ESCLARECIMENTO (prioridade):
1. Caixas d'água: volumes (500L, 1000L, 2000L)
2. Cimentos: tipos (CP-II, CP-III, CP-V)
3. Tintas/Massas: volumes/tipos (5kg, 10kg, acrílica, epóxi)
4. Outros: qualquer variação significativa

RESPONDA APENAS com JSON:
{{
    "needs_clarification": true/false,
    "current_category": "categoria_escolhida",
    "clarification_message": "Mensagem clara perguntando sobre a variação",
    "category_products": [índices dos produtos da categoria, começando do 0],
    "detected_variations": ["variação1", "variação2", "variação3"]
}}

Se NÃO precisar esclarecer, retorne:
{{"needs_clarification": false, "current_category": "", "clarification_message": "", "category_products": [], "detected_variations": []}}
"""

    try:
        response = await openai_service.generate_response(message=prompt)
        result = response.strip()

        # Tentar fazer parse do JSON
        import json
        try:
            analysis = json.loads(result)
        except json.JSONDecodeError:
            logger.warning(f"Falha no parse JSON da análise de variações: {result}")
            return {"needs_clarification": False, "variations": {}, "message": ""}

        # Adaptar para o formato esperado
        if analysis.get("needs_clarification"):
            category_indices = analysis.get("category_products", [])
            category_products = [products[i] for i in category_indices if i < len(products)]

            return {
                "needs_clarification": True,
                "variations": {analysis.get("current_category", "outro"): {
                    "volumes": [],  # IA determina internamente
                    "tipos": [],
                    "products": category_products
                }},
                "message": analysis.get("clarification_message", ""),
                "current_category": analysis.get("current_category", ""),
                "total_products": len(products)
            }
        else:
            return {"needs_clarification": False, "variations": {}, "message": ""}

    except Exception as exc:
        logger.error(f"Erro na análise de variações com IA: {exc}")
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
